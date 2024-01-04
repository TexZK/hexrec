# Copyright (c) 2013-2024, Andrea Zoppi
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

r"""MOS Technology format.

See Also:
    `<https://srecord.sourceforge.net/man/man5/srec_mos_tech.5.html>`_
"""

import binascii
import enum
import io
import re
from typing import IO
from typing import Any
from typing import Iterator
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Type
from typing import Union
from typing import cast as _cast

from ..records import Record as _Record
from ..records import RecordSequence
from ..records import Tag
from ..records2 import BaseFile
from ..records2 import BaseRecord
from ..records2 import BaseTag
from ..utils import AnyBytes
from ..utils import EllipsisType
from ..utils import check_empty_args_kwargs
from ..utils import chop
from ..utils import hexlify
from ..utils import unhexlify


class Record(_Record):  # pragma: no cover
    r"""MOS Technology record.

    Attributes:
        address (int):
            Tells where its `data` starts in the memory addressing space,
            or an address with a special meaning.

        tag (int):
            Defines the logical meaning of the `address` and `data` fields.

        data (bytes):
            Byte data as required by the `tag`.

        count (int):
            Counts its fields as required by the :class:`Record` subclass
            implementation.

        checksum (int):
            Computes the checksum as required by most :class:`Record`
            implementations.

    Arguments:
        address (int):
            Record `address` field.

        tag (int):
            Record `tag` field.

        data (bytes):
            Record `data` field.

        checksum (int):
            Record `checksum` field.
            ``Ellipsis`` makes the constructor compute its actual value
            automatically.
            ``None`` assigns ``None``.
    """

    TAG_TYPE: Optional[Type[Tag]] = None
    r"""Associated Python class for tags."""

    REGEX = re.compile(r'^;(?P<count>[0-9A-Fa-f]{2})'
                       r'(?P<address>[0-9A-Fa-f]{4})'
                       r'(?P<data>([0-9A-Fa-f]{2}){,255})'
                       r'(?P<checksum>[0-9A-Fa-f]{4})$')
    r"""Regular expression for parsing a record text line."""

    EXTENSIONS: Sequence[str] = ('.mos',)
    r"""File extensions typically mapped to this record type."""

    def __init__(
        self,
        address: int,
        tag: Optional[Tag],
        data: AnyBytes,
        checksum: Union[int, EllipsisType] = Ellipsis,
    ) -> None:
        super().__init__(address, tag, data, checksum)

    def __repr__(
        self,
    ) -> str:
        text = (f'{type(self).__name__}('
                f'address=0x{self.address:04X}, '
                f'tag={self.tag!r}, '
                f'count={self.count:d}, '
                f'data={self.data!r}, '
                f'checksum=0x{(self._get_checksum() or 0):04X}'
                f')')
        return text

    def __str__(
        self,
    ) -> str:
        text = (f';'
                f'{self.count:02X}'
                f'{self.address:04X}'
                f'{hexlify(self.data)}'
                f'{self._get_checksum():04X}')
        return text

    def is_data(
        self,
    ) -> bool:
        return self.count > 0

    def compute_checksum(
        self,
    ) -> int:
        if self.count:
            checksum = (self.count +
                        (self.address >> 16) +
                        (self.address & 0xFF) +
                        sum(self.data or b'')) & 0xFFFF
        else:
            checksum = self.address
        return checksum

    def check(
        self,
    ) -> None:
        if not 0 <= self.address < (1 << 16):
            raise ValueError('address overflow')

        if self.tag is not None:
            raise ValueError('wrong tag')

        if not 0 <= self.count < (1 << 8):
            raise ValueError('count overflow')

        if self.data is None:
            raise ValueError('no data')

        if self.count != len(self.data):
            raise ValueError('count error')

        if self.checksum is not None:
            if not 0 <= self.checksum < (1 << 16):
                raise ValueError('checksum overflow')

            if self.checksum != self.compute_checksum():
                raise ValueError('checksum error')

    @classmethod
    def build_data(
        cls,
        address: int,
        data: AnyBytes,
    ) -> 'Record':
        r"""Builds a data record.

        Arguments:
            address (int):
                Record address.

            data (bytes):
                Record data.

        Returns:
            record: Data record.

        Example:
            >>> Record.build_data(0x1234, b'Hello, World!')
            ... #doctest: +NORMALIZE_WHITESPACE
            Record(address=0x1234, tag=None, count=13,
                   data=b'Hello, World!', checksum=0x04AA)
        """
        record = cls(address, None, data)
        return record

    @classmethod
    def build_terminator(
        cls,
        record_count: int,
    ) -> 'Record':
        r"""Builds a terminator record.

        The terminator record holds the number of data records in the
        `address` fields.
        Also the `checksum` field is actually set to the record count.

        Arguments:
            record_count (int):
                Number of previous records.

        Returns:
            record: A terminator record.

        Example:
            >>> Record.build_data(0x1234, b'Hello, World!')
            ... #doctest: +NORMALIZE_WHITESPACE
            Record(address=0x00001234, tag=0, count=13,
                   data=b'Hello, World!', checksum=0x69)
        """
        record = cls(record_count, None, b'', record_count)
        return record

    @classmethod
    def split(
        cls,
        data: AnyBytes,
        address: int = 0,
        columns: int = 16,
        align: Union[int, EllipsisType] = Ellipsis,
        standalone: bool = True,
    ) -> Iterator['Record']:
        r"""Splits a chunk of data into records.

        Arguments:
            data (bytes):
                Byte data to split.

            address (int):
                Start address of the first data record being split.

            columns (int):
                Maximum number of columns per data record.
                Maximum of 128 columns.

            align (int):
                Aligns record addresses to such number.
                If ``Ellipsis``, its value is resolved after `columns`.

            standalone (bool):
                Generates a sequence of records that can be saved as a
                standalone record file.

        Yields:
            record: Data split into records.

        Raises:
            :obj:`ValueError`: Address, size, or column overflow.
        """
        if not 0 <= address < (1 << 16):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 16):
            raise ValueError('size overflow')
        if not 0 < columns < (1 << 8):
            raise ValueError('column overflow')
        if align is Ellipsis:
            align = columns

        align_base = (address % align) if align else 0
        offset = address
        record_count = 0

        for chunk in chop(data, columns, align_base):
            record_count += 1
            yield cls.build_data(offset, chunk)
            offset += len(chunk)

        if standalone:
            yield cls.build_terminator(record_count)

    @classmethod
    def parse_record(
        cls,
        line: str,
        *args: Any,
        **kwargs: Any,
    ) -> 'Record':
        check_empty_args_kwargs(args, kwargs)

        line = str(line).strip()
        match = cls.REGEX.match(line)
        if not match:
            raise ValueError('regex error')
        groups = match.groupdict()

        address = int(groups['address'], 16)
        count = int(groups['count'], 16)
        data = unhexlify(groups['data'] or '')
        checksum = int(groups['checksum'], 16)

        if count != len(data):
            raise ValueError('count error')

        record = cls(address, None, data, checksum)
        return record

    @classmethod
    def build_standalone(
        cls,
        data_records: RecordSequence,
        *args: Any,
        **kwargs: Any,
    ) -> Iterator['Record']:
        r"""Makes a sequence of data records standalone.

        Arguments:
            data_records (list of records):
                A sequence of data records.

        Yields:
            record: Records for a standalone record file.
        """
        check_empty_args_kwargs(args, kwargs)

        record_count = 0
        for record in data_records:
            record_count += 1
            yield record

        yield cls.build_terminator(record_count)

    @classmethod
    def check_sequence(
        cls,
        records: RecordSequence,
    ) -> None:
        super().check_sequence(records)

        if len(records) < 1:
            raise ValueError('missing terminator')

        record_count = len(records) - 1
        record = records[-1]

        if record.address != record_count or record.checksum != record_count:
            raise ValueError('wrong terminator')


# =============================================================================

@enum.unique
class MosTag(BaseTag, enum.IntEnum):
    r"""MOS Technology tag."""

    DATA = 0
    r"""Data."""

    EOF = 1  # FIXME: add full support
    r"""End Of File."""

    def is_data(self) -> bool:

        return self == 0

    def is_eof(self) -> bool:
        # TODO: __doc__

        return self == 1


class MosRecord(BaseRecord):
    # TODO: __doc__

    TAG_TYPE: Type[MosTag] = MosTag

    LINE_REGEX = re.compile(
        b'^\0*(?P<before>[^;]*);'
        b'(?P<count>[0-9A-Fa-f]{2})'
        b'(?P<address>[0-9A-Fa-f]{4})'
        b'(?P<data>([0-9A-Fa-f]{2}){,255})'
        b'(?P<checksum>[0-9A-Fa-f]{4})'
        b'(?P<after>[^\\r\\n]*)\\r?\\n?\0*$'
    )
    # TODO: __doc__

    @classmethod
    def build_data(
        cls,
        address: int,
        data: AnyBytes,
    ) -> 'MosRecord':
        # TODO: __doc__

        address = address.__index__()
        if not 0 <= address <= 0xFFFF:
            raise ValueError('address overflow')

        size = len(data)
        if size > 0xFF:
            raise ValueError('size overflow')

        record = cls(cls.TAG_TYPE.DATA, address=address, data=data)
        return record

    @classmethod
    def build_eof(
        cls,
        record_count: int,
    ) -> 'MosRecord':
        # TODO: __doc__

        record_count = record_count.__index__()
        if not 0 <= record_count <= 0xFFFF:
            raise ValueError('record count overflow')

        record = cls(cls.TAG_TYPE.EOF, address=record_count)
        return record

    def compute_checksum(self) -> int:

        if self.count is None:
            raise ValueError('missing count')

        count = self.count & 0xFF
        address = self.address & 0xFFFF
        sum_address = (address >> 8) + (address & 0xFF)
        sum_data = sum(iter(self.data))
        checksum = (count + sum_address + sum_data) & 0xFFFF
        return checksum

    def compute_count(self) -> int:

        return len(self.data)

    @classmethod
    def parse(cls, line: AnyBytes) -> 'MosRecord':
        # TODO: __doc__

        match = cls.LINE_REGEX.match(line)
        if not match:
            raise ValueError('syntax error')

        groups = match.groupdict()
        before = groups['before']
        count = int(groups['count'], 16)
        address = int(groups['address'], 16)
        data = binascii.unhexlify(groups['data'])
        checksum = int(groups['checksum'], 16)
        after = groups['after']

        record = cls(cls.TAG_TYPE.DATA,
                     address=address,
                     data=data,
                     count=count,
                     checksum=checksum,
                     before=before,
                     after=after)
        return record

    def to_bytestr(
        self,
        end: AnyBytes = b'\r\n',
        nuls: bool = True,
    ) -> bytes:

        self.validate()
        nulstr = b'\0\0\0\0\0\0' if nuls else b''

        line = b'%s;%02X%04X%s%04X%s%s%s' % (
            self.before,
            self.count & 0xFF,
            self.address & 0xFFFF,
            binascii.hexlify(self.data).upper(),
            self.checksum & 0xFFFF,
            self.after,
            end,
            nulstr,
        )
        return line

    def to_tokens(
        self,
        end: AnyBytes = b'\r\n',
        nuls: bool = True,
    ) -> Mapping[str, bytes]:

        self.validate()
        nulstr = b'\0\0\0\0\0\0' if nuls else b''

        return {
            'before': self.before,
            'begin': b';',
            'count': b'%02X' % (self.count & 0xFF),
            'address': b'%04X' % (self.address & 0xFFFF),
            'data': binascii.hexlify(self.data).upper(),
            'checksum': b'%04X' % (self.checksum & 0xFFFF),
            'after': self.after,
            'end': end,
            'nuls': nulstr,
        }

    def validate(self) -> 'MosRecord':

        super().validate()

        if self.after and not self.after.isspace():
            raise ValueError('junk after is not whitespace')

        if b';' in self.before:
            raise ValueError('junk before contains ";"')

        if not 0 <= self.checksum <= 0xFFFF:
            raise ValueError('checksum overflow')

        if not 0 <= self.count <= 0xFF:
            raise ValueError('count overflow')

        data_size = len(self.data)
        if data_size > 0xFF:
            raise ValueError('data size overflow')

        if not 0 <= self.address <= 0xFFFF:
            raise ValueError('address overflow')

        return self


class MosFile(BaseFile):

    DEFAULT_DATALEN: int = 24

    RECORD_TYPE: Type[MosRecord] = MosRecord

    @classmethod
    def _is_line_empty(cls, line: AnyBytes) -> bool:

        if b'\0' in line:
            line = line.replace(b'\0', b'')
        return not line or line.isspace()

    @classmethod
    def parse(
        cls,
        stream: IO,
        ignore_errors: bool = False,
        eof_record: bool = True,
    ) -> 'MosFile':
        # TODO: __doc__

        data = stream.read()
        data = _cast(bytes, data)

        start = data.find(b';')
        if start < 0:
            start = len(data)

        endex = data.find(b'\x13')
        if endex < 0:
            endex = len(data)

        if start > endex:
            start = endex

        data = data[start:endex]
        stream = io.BytesIO(data)

        file = super().parse(stream, ignore_errors=ignore_errors)
        file = _cast(MosFile, file)

        if eof_record:
            if file._records:
                file._records[-1].tag = cls.RECORD_TYPE.TAG_TYPE.EOF  # patch
            elif not ignore_errors:
                raise ValueError('missing end of file record')

        return file

    def serialize(
        self,
        stream: IO,
        end: AnyBytes = b'\r\n',
        nuls: bool = True,
        xoff: bool = True,
    ) -> 'BaseFile':
        # TODO: __doc__

        for record in self.records:
            record.serialize(stream, end=end, nuls=nuls)

        if xoff:
            stream.write(b'\x13')

        return self

    def update_records(
        self,
        align: bool = True,
        start: bool = True,
    ) -> 'MosFile':
        # TODO: __doc__

        memory = self._memory
        if memory is None:
            raise ValueError('memory instance required')

        records = []
        record_type = self.RECORD_TYPE
        chunk_views = []
        try:
            for chunk_start, chunk_view in memory.chop(self.maxdatalen, align=align):
                chunk_views.append(chunk_view)
                data = bytes(chunk_view)
                record = record_type.build_data(chunk_start, data)
                records.append(record)

            record = record_type.build_eof(len(records))
            records.append(record)

        finally:
            for chunk_view in chunk_views:
                chunk_view.release()

        self.discard_records()
        self._records = records
        return self

    def validate_records(
        self,
        data_ordering: bool = False,
        eof_record_required: bool = True,
    ) -> 'MosFile':
        # TODO: __doc__

        records = self._records
        if records is None:
            raise ValueError('records required')

        eof_record = None
        last_data_endex = 0

        for index, record in enumerate(records):
            record = _cast(MosRecord, record)
            record.validate()
            tag = _cast(MosTag, record.tag)

            if data_ordering:
                if tag == tag.DATA:
                    address = record.address
                    if address < last_data_endex:
                        raise ValueError('unordered data record')
                    last_data_endex = address + len(record.data)

            if tag == tag.EOF:
                eof_record = record

                expected_eof_index = len(records) - 1
                if index != expected_eof_index:
                    raise ValueError('end of file record not last')

                if record.address != expected_eof_index:
                    raise ValueError('wrong record count as address')

        if eof_record_required and eof_record is None:
            raise ValueError('missing end of file record')

        return self
