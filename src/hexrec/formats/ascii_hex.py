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

r"""ASCII-hex format.

See Also:
    `<https://srecord.sourceforge.net/man/man5/srec_ascii_hex.5.html>`_
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


class Record(_Record):
    r"""ASCII-hex record.

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

    REGEX = re.compile(r"^(\$A(?P<address>[0-9A-Fa-f]{4})[,.][ %',]?)?"
                       r"(?P<data>([0-9A-Fa-f]{2}[ %',])*([0-9A-Fa-f]{2})?)"
                       r"(\$S(?P<checksum>[0-9A-Fa-f]{4})[,.][ %',]?)?$")
    r"""Regular expression for parsing a record text line."""

    def __init__(
        self,
        address: Optional[int],
        tag: Optional[Tag],
        data: Optional[AnyBytes],
        checksum: Union[int, EllipsisType] = None,
    ) -> None:
        super().__init__(address, tag, data, checksum)

    def __repr__(
        self,
    ) -> str:
        address, data, checksum = None, None, None

        if self.address is not None:
            address = f'0x{self.address:04X}'

        if self.data is not None:
            data = f'{self.data!r}'

        if self.checksum is not None:
            checksum = f'0x{(self._get_checksum() or 0):04X}'

        text = (f'{type(self).__name__}('
                f'address={address}, '
                f'tag={self.tag!r}, '
                f'count={self.count:d}, '
                f'data={data}, '
                f'checksum={checksum}'
                f')')
        return text

    def __str__(
        self,
    ) -> str:
        address, data, checksum = '', '', ''

        if self.address is not None:
            address = f'$A{self.address:04X},'

        if self.data:
            data = f'{hexlify(self.data, sep=" ")} '

        if self.checksum is not None:
            checksum = f'$S{self._get_checksum():04X},'

        text = ''.join([address, data, checksum])
        return text

    def is_data(
        self,
    ) -> bool:
        return self.data is not None

    def compute_checksum(
        self,
    ) -> Optional[int]:
        checksum = sum(self.data or b'') & 0xFFFF
        return checksum

    def check(
        self,
    ) -> None:
        if self.address is not None and not 0 <= self.address < (1 << 16):
            raise ValueError('address overflow')

        if self.tag is not None:
            raise ValueError('wrong tag')

        if not 0 <= self.count < (1 << 16):
            raise ValueError('count overflow')

        if self.count != len(self.data or b''):
            raise ValueError('count error')

        if self.checksum is not None:
            if not 0 <= self.checksum < (1 << 16):
                raise ValueError('checksum overflow')

    @classmethod
    def build_data(
        cls,
        address: Optional[int],
        data: Optional[AnyBytes],
    ) -> 'Record':
        r"""Builds a data record.

        Arguments:
            address (int):
                Record address, or ``None``.

            data (bytes):
                Record data, or ``None``.

        Returns:
            record: A data record.

        Examples:
            >>> Record.build_data(0x1234, b'Hello, World!')
            ... #doctest: +NORMALIZE_WHITESPACE
            Record(address=0x1234, tag=None, count=13,
                   data=b'Hello, World!', checksum=None)

            >>> Record.build_data(None, b'Hello, World!')
            ... #doctest: +NORMALIZE_WHITESPACE
            Record(address=None, tag=None, count=13,
                   data=b'Hello, World!', checksum=None)

            >>> Record.build_data(0x1234, None)
            ... #doctest: +NORMALIZE_WHITESPACE
            Record(address=0x1234, tag=None, count=0, data=None, checksum=None)
        """
        record = cls(address, None, data)
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
        checksum = 0

        if standalone:
            record = cls.build_data(offset, None)
            yield record

        for chunk in chop(data, columns, align_base):
            if standalone:
                record = cls.build_data(None, chunk)
            else:
                record = cls.build_data(offset, chunk)
            yield record
            checksum = (checksum + record.compute_checksum()) & 0xFFFF
            offset += len(chunk)

        if standalone:
            record = cls(None, None, None, checksum)
            yield record

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

        address = groups['address']
        if address is not None:
            address = int(address, 16)

        data = groups['data']
        if data:
            for c in " %',":
                data = data.replace(c, '')
            data = unhexlify(data)
        else:
            data = None

        checksum = groups['checksum']
        if checksum is not None:
            checksum = int(checksum, 16)

        record = cls(address, None, data, checksum)
        return record

    @classmethod
    def build_standalone(
        cls,
        data_records: RecordSequence,
        *args: Any,
        **kwargs: Any,
    ) -> Iterator['Record']:
        check_empty_args_kwargs(args, kwargs)

        checksum = 0
        for record in data_records:
            yield record
            checksum = (checksum + record.compute_checksum()) & 0xFFFF

        record = cls(None, None, None, checksum)
        yield record

    @classmethod
    def readdress(
        cls,
        records: RecordSequence,
    ) -> None:
        offset = 0
        for record in records:
            if record.address is None:
                record.address = offset
            offset = record.address + len(record.data or b'')

    @classmethod
    def read_records(
        cls,
        stream: IO,
    ) -> RecordSequence:
        text = stream.read()
        stx = text.index('\x02')
        etx = text.index('\x03')
        text = text[(stx + 1):etx]
        return super().read_records(io.StringIO(text))

    @classmethod
    def write_records(
        cls,
        stream: IO,
        records: RecordSequence,
    ) -> None:
        stream.write('\x02')
        super().write_records(stream, records)
        stream.write('\x03')


# =============================================================================

@enum.unique
class AsciiHexTag(BaseTag, enum.IntEnum):
    r"""ASCII-HEX tag."""

    DATA = 0
    r"""Data."""

    ADDRESS_DATA = 1
    r"""Address and data."""

    def is_data(self) -> bool:

        return self == 0

    def is_address(self) -> bool:
        # TODO: __doc__

        return self == 1


class AsciiHexRecord(BaseRecord):
    # TODO: __doc__

    TAG_TYPE: Type[AsciiHexTag] = AsciiHexTag

    LINE_REGEX = re.compile(
        b'\\s*(\\$[Aa](?P<address>[0-9A-Fa-f]+)[,.])?\\s*'
        b"(?P<data>([0-9A-Fa-f]{2}[\\s%',]?)*)\\s*"
    )
    # TODO: __doc__

    DATA_SEPS: bytes = b" \t\n\r\v\f%',"
    # TODO: __doc__

    @classmethod
    def build_address(
        cls,
        address: int,
        data: AnyBytes,
        addrlen: int = 8,
    ) -> 'AsciiHexRecord':
        # TODO: __doc__

        address = address.__index__()
        if address < 0:
            raise ValueError('address overflow')

        addrlen = addrlen.__index__()
        if addrlen < 1:
            raise ValueError('invalid address length')

        record = cls(cls.TAG_TYPE.ADDRESS_DATA, address=address, data=data, count=addrlen)
        return record

    @classmethod
    def build_data(
        cls,
        data: AnyBytes,
    ) -> 'AsciiHexRecord':
        # TODO: __doc__

        record = cls(cls.TAG_TYPE.DATA, data=data)
        return record

    def compute_checksum(self) -> int:

        return 0  # unused

    def compute_count(self) -> int:

        if self.tag == self.TAG_TYPE.ADDRESS_DATA:
            return self.count  # loopback
        return 0  # unused

    @classmethod
    def parse(
        cls,
        line: Union[bytes, bytearray],
        addrlen: Optional[int] = None,
        address: int = 0,
    ) -> 'AsciiHexRecord':
        # TODO: __doc__

        if addrlen is not None:
            addrlen = addrlen.__index__()
            if addrlen < 1:
                raise ValueError('invalid address length')

        match = cls.LINE_REGEX.match(line)
        if not match:
            raise ValueError('syntax error')

        coords = match.span()
        groups = match.groupdict()
        data = b''

        address_group = groups['address']
        if address_group:
            tag = cls.TAG_TYPE.ADDRESS_DATA
            address = int(address_group, 16)
            if addrlen is None:
                addrlen = len(address_group)
        else:
            tag = cls.TAG_TYPE.DATA
            addrlen = 0

        data_group = groups['data']
        if data_group:
            data = data_group.translate(None, delete=cls.DATA_SEPS)
            data = binascii.unhexlify(data)

        record = cls(tag,
                     address=address,
                     data=data,
                     count=addrlen,
                     coords=coords)
        return record

    def to_bytestr(
        self,
        exechar: bytes = b' ',
        end: AnyBytes = b'\r\n',
    ) -> bytes:
        # TODO: __doc__

        self.validate()
        tag = _cast(AsciiHexTag, self.tag)
        addrstr = b''
        datastr = b''

        if tag == tag.ADDRESS_DATA:
            addrstr = (b'$A%%0%dX' % self.count) % self.address

        if self.data:
            datastr = binascii.hexlify(self.data, exechar).upper()

        bytestr = b'%s%s%s%s%s' % (
            self.before,
            addrstr,
            datastr,
            self.after,
            end,
        )
        return bytestr

    def to_tokens(
        self,
        exechar: bytes = b' ',
        end: AnyBytes = b'\r\n',
    ) -> Mapping[str, bytes]:

        self.validate()
        tag = _cast(AsciiHexTag, self.tag)
        addrstr = b''
        datastr = b''

        if tag == tag.ADDRESS_DATA:
            addrstr = (b'$A%%0%dX' % self.count) % self.address

        if self.data:
            datastr = binascii.hexlify(self.data, exechar).upper()

        return {
            'before': self.before,
            'address': addrstr,
            'data': datastr,
            'after': self.after,
            'end': end,
        }

    def validate(self) -> 'AsciiHexRecord':

        super().validate()

        if self.after and not self.after.isspace():
            raise ValueError('junk after')

        if self.before and not self.before.isspace():
            raise ValueError('junk before')

        if self.count < 1:
            raise ValueError('invalid count')

        return self


class AsciiHexFile(BaseFile):

    RECORD_TYPE: Type[AsciiHexRecord] = AsciiHexRecord

    @classmethod
    def parse(
        cls,
        stream: IO,
        ignore_errors: bool = False,
        stxetx: bool = True,
    ) -> 'AsciiHexFile':
        # TODO: __doc__

        buffer: bytes = stream.read()

        records = []
        record_type = cls.RECORD_TYPE

        if stxetx:
            stx_offset = buffer.find(0x02)
            if stx_offset < 0:
                raise ValueError('missing STX character')

            etx_offset = buffer.find(0x03, stx_offset)
            if etx_offset < 0:
                raise ValueError('missing ETX character')
        else:
            stx_offset = 0
            etx_offset = len(buffer)

        view = memoryview(buffer)
        offset = stx_offset
        address = 0

        while offset < etx_offset:
            chunk = _cast(bytes, view[offset:etx_offset])
            try:
                record = record_type.parse(chunk, address=address)
            except Exception:
                if ignore_errors:
                    continue
                raise

            pos, endpos = record.coords
            pos += offset
            endpos += offset
            record.coords = pos, endpos
            offset = endpos

            address = record.address + len(record.data)

        file = cls.from_records(records)
        return file

    def serialize(
        self,
        stream: IO,
        end: AnyBytes = b'\r\n',
        exechar: bytes = b' ',
        stxetx: bool = True,
    ) -> 'BaseFile':
        # TODO: __doc__

        if stxetx:
            stream.write(b'\x02')

        for record in self.records:
            record.serialize(stream, exechar=exechar, end=end)

        if stxetx:
            stream.write(b'\x03')

        return self

    def update_records(
        self,
        align: bool = True,
        addrlen: int = 8,
    ) -> 'AsciiHexFile':
        # TODO: __doc__

        memory = self._memory
        if memory is None:
            raise ValueError('memory instance required')

        addrlen = addrlen.__index__()
        if addrlen < 1:
            raise ValueError('invalid address length')

        records = []
        record_type = self.RECORD_TYPE
        last_data_endex = 0
        chunk_views = []
        try:
            for chunk_start, chunk_view in memory.chop(self.maxdatalen, align=align):
                chunk_views.append(chunk_view)
                data = bytes(chunk_view)

                if chunk_start == last_data_endex:
                    record = record_type.build_data(data)
                else:
                    record = record_type.build_address(chunk_start, data, addrlen=addrlen)

                records.append(record)
                last_data_endex = chunk_start + len(chunk_view)

        finally:
            for chunk_view in chunk_views:
                chunk_view.release()

        self.discard_records()
        self._records = records
        return self

    def validate_records(
        self,
        data_ordering: bool = False,
    ) -> 'AsciiHexFile':
        # TODO: __doc__

        records = self._records
        if records is None:
            raise ValueError('records required')

        last_data_endex = 0
        address_data_tag = self.RECORD_TYPE.TAG_TYPE.ADDRESS_DATA

        for index, record in enumerate(records):
            record = _cast(AsciiHexRecord, record)
            record.validate()

            if data_ordering:
                if record.tag == address_data_tag:
                    if record.address < last_data_endex:
                        raise ValueError('unordered data record')
                    last_data_endex = record.address + len(record.data)
                else:
                    last_data_endex += len(record.data)

        return self
