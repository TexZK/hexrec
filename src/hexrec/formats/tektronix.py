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

r"""Tektronix extended HEX format.

See Also:
    `<https://en.wikipedia.org/wiki/Tektronix_extended_HEX>`_
"""

import binascii
import enum
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
from ..records import Tag as _Tag
from ..records2 import BaseFile
from ..records2 import BaseRecord
from ..records2 import BaseTag
from ..utils import AnyBytes
from ..utils import EllipsisType
from ..utils import check_empty_args_kwargs
from ..utils import chop
from ..utils import hexlify
from ..utils import unhexlify


@enum.unique
class Tag(_Tag):  # pragma: no cover
    DATA = 6
    TERMINATOR = 8

    @classmethod
    def is_data(
        cls: Type['Tag'],
        value: Union[int, 'Tag'],
    ) -> bool:
        r"""bool: `value` is a data record tag."""
        return value == cls.DATA


class Record(_Record):  # pragma: no cover
    r"""Tektronix extended HEX record.

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

    TAG_TYPE: Optional[Type[Tag]] = Tag
    r"""Associated Python class for tags."""

    REGEX = re.compile(r'^%(?P<count>[0-9A-Fa-f]{2})'
                       r'(?P<tag>[68])'
                       r'(?P<checksum>[0-9A-Fa-f]{2})'
                       r'8(?P<address>[0-9A-Fa-f]{8})'
                       r'(?P<data>([0-9A-Fa-f]{2}){,255})$')
    r"""Regular expression for parsing a record text line."""

    EXTENSIONS: Sequence[str] = ('.tek',)
    r"""File extensions typically mapped to this record type."""

    def __init__(
        self,
        address: int,
        tag: Tag,
        data: AnyBytes,
        checksum: Union[int, EllipsisType] = Ellipsis,
    ) -> None:
        super().__init__(address, self.TAG_TYPE(tag), data, checksum)

    def __str__(
        self,
    ) -> str:
        self.check()
        text = (f'%'
                f'{self.count:02X}'
                f'{self.tag:01X}'
                f'{self._get_checksum():02X}'
                f'8'
                f'{self.address:08X}'
                f'{hexlify(self.data)}')
        return text

    def compute_count(
        self,
    ) -> int:
        count = 9 + (len(self.data) * 2)
        return count

    def compute_checksum(
        self,
    ) -> int:
        text = (f'{self.count:02X}'
                f'{self.tag:01X}'
                f'8'
                f'{self.address:08X}'
                f'{hexlify(self.data)}')
        checksum = sum(int(c, 16) for c in text) & 0xFF
        return checksum

    def check(
        self,
    ) -> None:
        super().check()
        tag = self.TAG_TYPE(self.tag)

        if tag == self.TAG_TYPE.TERMINATOR and self.data:
            raise ValueError('invalid data')

        if self.count != self.compute_count():
            raise ValueError('count error')

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
        tag = cls.TAG_TYPE(int(groups['tag'], 16))
        count = int(groups['count'], 16)
        data = unhexlify(groups['data'] or '')
        checksum = int(groups['checksum'], 16)

        if count != 9 + (len(data) * 2):
            raise ValueError('count error')

        record = cls(address, tag, data, checksum)
        return record

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
            >>> str(Record.build_data(0x12345678, b'Hello, World!'))
            '%236E081234567848656C6C6F2C20576F726C6421'
        """
        record = cls(address, cls.TAG_TYPE.DATA, data)
        return record

    @classmethod
    def build_terminator(
        cls,
        start: int,
    ) -> 'Record':
        r"""Builds a terminator record.

        Arguments:
            start (int):
                Program start address.

        Returns:
            record: Terminator record.

        Example:
            >>> str(Record.build_terminator(0x12345678))
            '%0983D812345678'
        """
        record = cls(start, cls.TAG_TYPE.TERMINATOR, b'')
        return record

    @classmethod
    def split(
        cls,
        data: AnyBytes,
        address: int = 0,
        columns: int = 16,
        align: Union[int, EllipsisType] = Ellipsis,
        standalone: bool = True,
        start: Optional[Union[int, EllipsisType]] = None,
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

            start (int):
                Program start address.
                If ``Ellipsis``, it is assigned the minimum data record address.
                If ``None``, no start address is set.

        Yields:
            record: Data split into records.

        Raises:
            :obj:`ValueError`: Address, size, or column overflow.
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        if not 0 < columns < 128:
            raise ValueError('column overflow')
        if align is Ellipsis:
            align = columns
        if start is Ellipsis:
            start = address
        if start is None:
            start = 0

        align_base = (address % align) if align else 0
        offset = address

        for chunk in chop(data, columns, align_base):
            yield cls.build_data(offset, chunk)
            offset += len(chunk)

        if standalone:
            yield cls.build_terminator(start)

    @classmethod
    def build_standalone(
        cls,
        data_records: RecordSequence,
        *args: Any,
        start: Optional[int] = None,
        **kwargs: Any,
    ) -> Iterator['Record']:
        r"""Makes a sequence of data records standalone.

        Arguments:
            data_records (list of record):
                A sequence of data records.

            start (int):
                Program start address.
                If ``None``, it is assigned the minimum data record address.

        Yields:
            record: Records for a standalone record file.
        """
        check_empty_args_kwargs(args, kwargs)

        for record in data_records:
            yield record

        if start is None:
            if not data_records:
                data_records = [cls.build_data(0, b'')]
            start = min(record.address for record in data_records)

        yield cls.build_terminator(start)

    @classmethod
    def check_sequence(
        cls,
        records: RecordSequence,
    ) -> None:
        super().check_sequence(records)

        if len(records) < 1:
            raise ValueError('missing terminator')

        for i in range(len(records) - 1):
            record = records[i]
            if record.tag != cls.TAG_TYPE.DATA:
                raise ValueError('tag error')

        record = records[-1]
        if record.tag != cls.TAG_TYPE.TERMINATOR:
            raise ValueError('missing terminator')


# =============================================================================

@enum.unique
class TekExtTag(BaseTag, enum.IntEnum):
    r"""Tektronix Extended tag."""

    DATA = 6
    r"""Data."""

    EOF = 8
    r"""End Of File."""

    def is_data(self) -> bool:

        return self == 6

    def is_eof(self) -> bool:
        # TODO: __doc__

        return self == 8


class TekExtRecord(BaseRecord):
    # TODO: __doc__

    TAG_TYPE: Type[TekExtTag] = TekExtTag

    LINE1_REGEX = re.compile(
        r'^(?P<before>[^%]*)%'
        r'(?P<count>[0-9A-Fa-f]{2})'
        r'(?P<tag>[68])'
        r'(?P<checksum>[0-9A-Fa-f]{2})'
        r'(?P<addrlen>[1-9A-Fa-f])'
    )
    # TODO: __doc__

    LINE2_REGEX = [re.compile(
        f'^(?P<address>[0-9A-Fa-f]{{{1 + i}}})'
    ) for i in range(15)]
    # TODO: __doc__

    LINE3_REGEX = re.compile(
        r'^(?P<data>([0-9A-Fa-f]{2}){,255})'
        r'(?P<after>\\s*)\\r?$'
    )
    # TODO: __doc__

    def __init__(
        self,
        *super_init_args,
        addrlen: int = 8,
        **super_init_kwargs,
    ):

        addrlen = addrlen.__index__()
        if not 1 <= addrlen <= 15:
            raise ValueError('invalid address length')

        super().__init__(*super_init_args, **super_init_kwargs)
        self.addrlen = addrlen

    @classmethod
    def build_data(
        cls,
        address: int,
        data: AnyBytes,
        addrlen: int = 8,
    ) -> 'TekExtRecord':
        # TODO: __doc__

        addrlen = addrlen.__index__()
        if not 1 <= addrlen <= 15:
            raise ValueError('invalid address length')
        addrmax = cls.compute_address_max(addrlen)

        address = address.__index__()
        if not 0 <= address <= addrmax:
            raise ValueError('address overflow')

        return cls(cls.TAG_TYPE.EOF, address=address, data=data, addrlen=addrlen)

    @classmethod
    def build_eof(
        cls,
        start: int = 0,
        addrlen: int = 8,
    ) -> 'TekExtRecord':
        # TODO: __doc__

        addrlen = addrlen.__index__()
        if not 1 <= addrlen <= 15:
            raise ValueError('invalid address length')
        addrmax = cls.compute_address_max(addrlen)

        startaddr = start.__index__()
        if not 0 <= startaddr <= addrmax:
            raise ValueError('start address overflow')

        return cls(cls.TAG_TYPE.EOF, address=startaddr, addrlen=addrlen)

    @classmethod
    def compute_address_max(cls, addrlen: int) -> int:
        # TODO: __doc__

        if not 1 <= addrlen <= 15:
            raise ValueError('invalid address length')

        addrmax = (1 << (addrlen * 4)) - 1
        return addrmax

    def compute_checksum(self) -> int:

        count = self.count
        if count is None:
            raise ValueError('missing count')
        count_sum = (count >> 4) + (count & 0xF)

        address = self.address
        address_sum = 0
        while address > 0:
            address_sum += address & 0xF
            address >>= 4

        data_sum = 0
        for datum in self.data:
            data_sum += (datum >> 4) + (datum & 0xF)

        tag = _cast(TekExtTag, self.tag)
        checksum = (count_sum + tag + self.addrlen + address_sum + data_sum)
        return checksum

    def compute_count(self) -> int:

        count = 6 + self.addrlen + (len(self.data) * 2)
        return count

    @classmethod
    def parse(cls, line: AnyBytes) -> 'TekExtRecord':
        # TODO: __doc__

        line = memoryview(line)
        match = cls.LINE1_REGEX.match(line)
        if not match:
            raise ValueError('syntax error')
        groups = match.groupdict()
        before = groups['before']
        count = int(groups['count'], 16)
        tag = cls.TAG_TYPE(int(groups['tag'], 16))
        checksum = int(groups['checksum'], 16)
        addrlen = int(groups['addrlen'], 16)

        line = line[match.span()[1]:]
        match = cls.LINE2_REGEX[addrlen - 1].match(line)
        if not match:
            raise ValueError('syntax error')
        groups = match.groupdict()
        address = int(groups['address'], 16)

        line = line[match.span()[1]:]
        match = cls.LINE3_REGEX.match(line)
        if not match:
            raise ValueError('syntax error')
        groups = match.groupdict()
        data = binascii.unhexlify(groups['data'])
        after = groups['after']

        record = cls(tag,
                     address=address,
                     data=data,
                     count=count,
                     checksum=checksum,
                     before=before,
                     after=after,
                     addrlen=addrlen)
        return record

    def to_bytestr(self, end: AnyBytes = b'\n') -> bytes:

        self.validate()

        bytestr = b'%s%%%02X%X%02X%X%s%s%s%s' % (
            self.before,
            self.count & 0xFF,
            _cast(TekExtTag, self.tag) & 0xF,
            self.checksum & 0xFF,
            self.addrlen & 0xF,
            (b'%%0%dX' % self.addrlen) % (self.address & 0xFFFFFFFF),
            binascii.hexlify(self.data).upper(),
            self.after,
            end,
        )
        return bytestr

    def to_tokens(self, end: AnyBytes = b'\r\n') -> Mapping[str, bytes]:

        self.validate()
        return {
            'before': self.before,
            'begin': b'%',
            'count': b'%02X' % (self.count & 0xFF),
            'tag': b'%X' % (_cast(TekExtTag, self.tag) & 0xF),
            'checksum': b'%02X' % (self.checksum & 0xFF),
            'addrlen': b'%X' % (self.addrlen & 0xF),
            'address': (b'%%0%dX' % self.addrlen) % (self.address & 0xFFFFFFFF),
            'data': binascii.hexlify(self.data).upper(),
            'after': self.after,
            'end': end,
        }

    def validate(self) -> 'TekExtRecord':

        super().validate()

        if self.after and not self.after.isspace():
            raise ValueError('junk after is not whitespace')

        if b'%' in self.before:
            raise ValueError('junk before contains "%"')

        if not 0 <= self.checksum <= 0xFF:
            raise ValueError('checksum overflow')

        if not 0 <= self.count <= 0xFF:
            raise ValueError('count overflow')

        addrlen = self.addrlen
        if not 1 <= addrlen <= 15:
            raise ValueError('invalid address length')

        addrmax = self.compute_address_max(addrlen)
        if not 0 <= self.address <= addrmax:
            raise ValueError('address overflow')

        datamax = (0xFA - addrlen) // 2
        data_size = len(self.data)
        if data_size > datamax:
            raise ValueError('data size overflow')

        tag = _cast(TekExtTag, self.tag)

        if tag.is_data():
            pass
        elif tag.is_eof():
            if data_size:
                raise ValueError('end of file record data')
        else:
            raise ValueError('unsupported tag')

        return self


class TekExtFile(BaseFile):

    FILE_EXT: Sequence[int] = ['.tek']

    META_KEYS: Sequence[str] = ['maxdatalen', 'startaddr']

    RECORD_TYPE: Type[TekExtRecord] = TekExtRecord

    def __init__(self):

        super().__init__()

        self._startaddr: int = 0

    @classmethod
    def parse(cls, stream: IO, ignore_errors: bool = False) -> 'TekExtFile':

        file = super().parse(stream, ignore_errors=ignore_errors)
        return _cast(TekExtFile, file)

    @property
    def startaddr(self) -> Optional[int]:

        if self._memory is None:
            self.apply_records()
        return self._startaddr

    @startaddr.setter
    def startaddr(self, address: int = 0) -> None:

        address = address.__index__()
        if not 0 <= address <= 0xFFFFFFFF:
            raise ValueError('invalid start address')

        if self._startaddr != address:
            self.discard_records()
        self._startaddr = address

    def update_records(
        self,
        align: bool = True,
        start: bool = True,
        addrlen: int = 8,
    ) -> 'TekExtFile':
        # TODO: __doc__

        memory = self._memory
        if memory is None:
            raise ValueError('memory instance required')

        addrlen = addrlen.__index__()
        if not 1 <= addrlen <= 15:
            raise ValueError('invalid address length')

        records = []
        record_type = self.RECORD_TYPE
        chunk_views = []
        try:
            for chunk_start, chunk_view in memory.chop(self.maxdatalen, align=align):
                chunk_views.append(chunk_view)
                data = bytes(chunk_view)
                record = record_type.build_data(chunk_start, data, addrlen=addrlen)
                records.append(record)

            record = record_type.build_eof(self.startaddr, addrlen=addrlen)
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
        startaddr_within_data: bool = False,
    ) -> 'TekExtFile':
        # TODO: __doc__

        records = self._records
        if records is None:
            raise ValueError('records required')

        eof_record = None
        last_data_endex = 0

        for index, record in enumerate(records):
            record = _cast(TekExtRecord, record)
            record.validate()
            tag = _cast(TekExtTag, record.tag)

            if data_ordering:
                if tag == tag.DATA:
                    address = record.address
                    if address < last_data_endex:
                        raise ValueError('unordered data record')
                    last_data_endex = address + len(record.data)

            if tag == tag.EOF:
                if eof_record is not None:
                    raise ValueError('multiple end of file records')
                eof_record = record

                if index != len(records) - 1:
                    raise ValueError('end of file record not last')

        if eof_record is None:
            raise ValueError('missing end of file record')

        if startaddr_within_data:
            start_datum = self.memory.peek(eof_record.address)
            if start_datum is None:
                raise ValueError('no data at start address')

        return self
