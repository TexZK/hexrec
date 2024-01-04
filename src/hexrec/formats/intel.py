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

r"""Intel HEX format.

See Also:
    `<https://en.wikipedia.org/wiki/Intel_HEX>`_
"""

import binascii
import enum
import re
import struct
from typing import IO
from typing import Any
from typing import Iterator
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Type
from typing import Union
from typing import cast as _cast

from bytesparse import Memory

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
class Tag(_Tag):  # pragma: no cover  # TODO: remove
    r"""Intel HEX tag."""

    DATA = 0
    r"""Binary data."""

    END_OF_FILE = 1
    r"""End of file."""

    EXTENDED_SEGMENT_ADDRESS = 2
    r"""Extended segment address."""

    START_SEGMENT_ADDRESS = 3
    r"""Start segment address."""

    EXTENDED_LINEAR_ADDRESS = 4
    r"""Extended linear address."""

    START_LINEAR_ADDRESS = 5
    r"""Start linear address."""

    @classmethod
    def is_data(
        cls,
        value: Union[int, 'Tag'],
    ) -> bool:
        r"""bool: `value` is a data record tag."""
        return value == cls.DATA


class Record(_Record):  # pragma: no cover  # TODO: remove
    r"""Intel HEX record.

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

    REGEX = re.compile(r'^:(?P<count>[0-9A-Fa-f]{2})'
                       r'(?P<offset>[0-9A-Fa-f]{4})'
                       r'(?P<tag>[0-9A-Fa-f]{2})'
                       r'(?P<data>([0-9A-Fa-f]{2}){,255})'
                       r'(?P<checksum>[0-9A-Fa-f]{2})$')
    r"""Regular expression for parsing a record text line."""

    EXTENSIONS: Sequence[str] = ('.h86', '.hex', '.ihex', '.mcs')
    r"""Automatically supported file extensions."""

    def __init__(
        self,
        address: int,
        tag: 'Tag',
        data: AnyBytes,
        checksum: Union[int, EllipsisType] = Ellipsis,
    ) -> None:
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        super().__init__(address, self.TAG_TYPE(tag), data, checksum)

    def __str__(
        self,
    ) -> str:
        self.check()
        data = self.data or b''
        text = (f':{len(data):02X}'
                f'{((self.address or 0) & 0xFFFF):04X}'
                f'{self.tag:02X}'
                f'{hexlify(data)}'
                f'{self._get_checksum():02X}')
        return text

    def compute_count(
        self,
    ) -> int:
        return len(self.data)

    def compute_checksum(
        self,
    ) -> int:
        offset = (self.address or 0) & 0xFFFF

        checksum = (self.count +
                    sum(struct.pack('H', offset)) +
                    self.tag +
                    sum(self.data or b''))

        checksum = (0x100 - int(checksum & 0xFF)) & 0xFF
        return checksum

    def check(
        self,
    ) -> None:
        super().check()

        if self.count != self.compute_count():
            raise ValueError('count error')

        self.TAG_TYPE(self.tag)
        # TODO: check values

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
            >>> str(Record.build_data(0x1234, b'Hello, World!'))
            ':0D12340048656C6C6F2C20576F726C642144'
        """
        record = cls(address, cls.TAG_TYPE.DATA, data)
        return record

    @classmethod
    def build_extended_segment_address(
        cls,
        address: int,
    ) -> 'Record':
        r"""Builds an extended segment address record.

        Arguments:
            address (int):
                Extended segment address.
                The 20 least significant bits are ignored.

        Returns:
            record: Extended segment address record.

        Example:
            >>> str(Record.build_extended_segment_address(0x12345678))
            ':020000020123D8'
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        segment = address >> (16 + 4)
        tag = cls.TAG_TYPE.EXTENDED_SEGMENT_ADDRESS
        record = cls(0, tag, struct.pack('>H', segment))
        return record

    @classmethod
    def build_start_segment_address(
        cls,
        address: int,
    ) -> 'Record':
        r"""Builds an start segment address record.

        Arguments:
            address (int):
                Start segment address.

        Returns:
            record: Start segment address record.

        Raises:
            :obj:`ValueError`: Address overflow.

        Example:
            >>> str(Record.build_start_segment_address(0x12345678))
            ':0400000312345678E5'
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')

        tag = cls.TAG_TYPE.START_SEGMENT_ADDRESS
        record = cls(0, tag, struct.pack('>L', address))
        return record

    @classmethod
    def build_end_of_file(
        cls,
    ) -> 'Record':
        r"""Builds an end-of-file record.

        Returns:
            record: End-of-file record.

        Example:
            >>> str(Record.build_end_of_file())
            ':00000001FF'
        """
        tag = cls.TAG_TYPE.END_OF_FILE
        return cls(0, tag, b'')

    @classmethod
    def build_extended_linear_address(
        cls,
        address: int,
    ) -> 'Record':
        r"""Builds an extended linear address record.

        Arguments:
            address (int):
                Extended linear address.
                The 16 least significant bits are ignored.

        Returns:
            record: Extended linear address record.

        Raises:
            :obj:`ValueError`: Address overflow.

        Example:
            >>> str(Record.build_extended_linear_address(0x12345678))
            ':020000041234B4'
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')

        segment = address >> 16
        tag = cls.TAG_TYPE.EXTENDED_LINEAR_ADDRESS
        record = cls(0, tag, struct.pack('>H', segment))
        return record

    @classmethod
    def build_start_linear_address(
        cls,
        address: int,
    ) -> 'Record':
        r"""Builds an start linear address record.

        Arguments:
            address (int):
                Start linear address.

        Returns:
            record: Start linear address record.

        Raises:
            :obj:`ValueError`: Address overflow.

        Example:
            >>> str(Record.build_start_linear_address(0x12345678))
            ':0400000512345678E3'
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')

        tag = cls.TAG_TYPE.START_LINEAR_ADDRESS
        record = cls(0, tag, struct.pack('>L', address))
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
                Maximum of 255 columns.

            align (int):
                Aligns record addresses to such number.
                If ``Ellipsis``, its value is resolved after `columns`.

            standalone (bool):
                Generates a sequence of records that can be saved as a
                standalone record file.

            start (int):
                Program start address.
                If ``Ellipsis``, it is assigned the minimum data record address.
                If ``None``, no start address records are output.

        Yields:
            record: Data split into records.

        Raises:
            :obj:`ValueError`: Address, size, or column overflow.
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        if not 0 < columns < 255:
            raise ValueError('column overflow')
        if align is Ellipsis:
            align = columns
        if start is Ellipsis:
            start = address

        align_base = (address % align) if align else 0
        address_old = 0

        for chunk in chop(data, columns, align_base):
            length = len(chunk)
            endex = address + length
            overflow = endex & 0xFFFF

            if overflow and (address ^ endex) & 0xFFFF0000:
                pivot = length - overflow

                yield cls.build_data(address, chunk[:pivot])
                address += pivot

                yield cls.build_extended_linear_address(address)

                yield cls.build_data(address, chunk[pivot:])
                address_old = address
                address += overflow

            else:
                if (address ^ address_old) & 0xFFFF0000:
                    yield cls.build_extended_linear_address(address)

                yield cls.build_data(address, chunk)
                address_old = address
                address += length

        if standalone:
            for record in cls.terminate(start):
                yield record

    @classmethod
    def build_standalone(
        cls,
        data_records: RecordSequence,
        start: Optional[Union[int, Type['Ellipsis']]] = Ellipsis,
        *args: Any,
        **kwargs: Any,
    ) -> Iterator['Record']:
        r"""Makes a sequence of data records standalone.

        Arguments:
            data_records (list of records):
                A sequence of data records.

            start (int):
                Program start address.
                If ``Ellipsis``, it is assigned the minimum data record address.
                If ``None``, the start address records are not output.

        Yields:
            record: Records for a standalone record file.
        """
        check_empty_args_kwargs(args, kwargs)

        for record in data_records:
            yield record

        if start is Ellipsis:
            if not data_records:
                data_records = [cls.build_data(0, b'')]
            start = min(record.address for record in data_records)

        for record in cls.terminate(start):
            yield record

    @classmethod
    def terminate(
        cls,
        start: Optional[int] = None,
    ) -> Sequence['Record']:
        r"""Builds a record termination sequence.

        The termination sequence is made of:

        # An extended linear address record at ``0``.
        # A start linear address record at `start`.
        # An end-of-file record.

        Arguments:
            start (int):
                Program start address.
                If ``None``, the start address records are not output.

        Returns:
            list of records: Termination sequence.

        Example:
            >>> list(map(str, Record.terminate(0x12345678)))
            [':020000040000FA', ':0400000512345678E3', ':00000001FF']
        """
        if start is None:
            return [cls.build_end_of_file()]
        else:
            return [cls.build_extended_linear_address(0),
                    cls.build_start_linear_address(start),
                    cls.build_end_of_file()]

    @classmethod
    def readdress(
        cls,
        records: RecordSequence,
    ) -> None:
        r"""Converts to flat addressing.

        *Intel HEX*, stores records by *segment/offset* addressing.
        As this library adopts *flat* addressing instead, all the record
        addresses should be converted to *flat* addressing after loading.
        This procedure readdresses a sequence of records in-place.

        Warning:
            Only the `address` field is modified. All the other fields hold
            their previous value.

        Arguments:
            records (list of records):
                Sequence of records to be converted to *flat* addressing,
                in-place.

        Example:
            >>> records = [
            ...     Record.build_extended_linear_address(0x76540000),
            ...     Record.build_data(0x00003210, b'Hello, World!'),
            ... ]
            >>> records  #doctest: +NORMALIZE_WHITESPACE
            [Record(address=0x00000000,
                         tag=<Tag.EXTENDED_LINEAR_ADDRESS: 4>, count=2,
                         data=b'vT', checksum=0x30),
             Record(address=0x00003210, tag=<Tag.DATA: 0>, count=13,
                         data=b'Hello, World!', checksum=0x48)]
            >>> Record.readdress(records)
            >>> records  #doctest: +NORMALIZE_WHITESPACE
            [Record(address=0x76540000,
                         tag=<Tag.EXTENDED_LINEAR_ADDRESS: 4>, count=2,
                         data=b'vT', checksum=0x30),
             Record(address=0x76543210, tag=<Tag.DATA: 0>, count=13,
                         data=b'Hello, World!', checksum=0x48)]
        """
        esa = cls.TAG_TYPE.EXTENDED_SEGMENT_ADDRESS
        ela = cls.TAG_TYPE.EXTENDED_LINEAR_ADDRESS
        base = 0

        for record in records:
            tag = record.tag
            if tag == esa:
                base = struct.unpack('>H', record.data)[0] << 4
                address = base
            elif tag == ela:
                base = struct.unpack('>H', record.data)[0] << 16
                address = base
            else:
                address = base + record.address

            record.address = address

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

        offset = int(groups['offset'], 16)
        tag = cls.TAG_TYPE(int(groups['tag'], 16))
        count = int(groups['count'], 16)
        data = unhexlify(groups['data'] or '')
        checksum = int(groups['checksum'], 16)

        if count != len(data):
            raise ValueError('count error')
        record = cls(offset, tag, data, checksum)
        return record


# =============================================================================

@enum.unique
class IhexTag(BaseTag, enum.IntEnum):
    r"""Intel HEX tag."""

    DATA = 0
    r"""Binary data."""

    END_OF_FILE = 1
    r"""End of file."""

    EXTENDED_SEGMENT_ADDRESS = 2
    r"""Extended segment address."""

    START_SEGMENT_ADDRESS = 3
    r"""Start segment address."""

    EXTENDED_LINEAR_ADDRESS = 4
    r"""Extended linear address."""

    START_LINEAR_ADDRESS = 5
    r"""Start linear address."""

    def is_data(self) -> bool:

        return self == 0

    def is_eof(self) -> bool:
        # TODO: __doc__

        return self == 1

    def is_start(self) -> bool:
        # TODO: __doc__

        return self == 3 or self == 5

    def is_extension(self) -> bool:
        # TODO: __doc__

        return self == 2 or self == 4


class IhexRecord(BaseRecord):
    # TODO: __doc__

    TAG_TYPE: Type[IhexTag] = IhexTag

    LINE_REGEX = re.compile(
        b'^(?P<before>[^:]*):'
        b'(?P<count>[0-9A-Fa-f]{2})'
        b'(?P<address>[0-9A-Fa-f]{4})'
        b'(?P<tag>[0-9A-Fa-f]{2})'
        b'(?P<data>([0-9A-Fa-f]{2}){,255})'
        b'(?P<checksum>[0-9A-Fa-f]{2})'
        b'(?P<after>[^\\r\\n]*)\\r?\\n?$'
    )
    # TODO: __doc__

    @classmethod
    def build_data(
        cls,
        address: int,
        data: AnyBytes,
    ) -> 'IhexRecord':
        # TODO: __doc__

        address = address.__index__()
        if not 0 <= address <= 0xFFFF:
            raise ValueError('address overflow')

        size = len(data)
        if size > 0xFF:
            raise ValueError('data size overflow')

        record = cls(cls.TAG_TYPE.DATA, address=address, data=data)
        return record

    @classmethod
    def build_end_of_file(cls) -> 'IhexRecord':
        # TODO: __doc__

        record = cls(cls.TAG_TYPE.END_OF_FILE)
        return record

    @classmethod
    def build_extended_linear_address(cls, extension: int) -> 'IhexRecord':
        # TODO: __doc__

        extension = extension.__index__()
        if not 0 <= extension <= 0xFFFF:
            raise ValueError('extension overflow')

        data = extension.to_bytes(2, byteorder='big')
        record = cls(cls.TAG_TYPE.EXTENDED_LINEAR_ADDRESS, data=data)
        return record

    @classmethod
    def build_extended_segment_address(cls, extension: int) -> 'IhexRecord':
        # TODO: __doc__

        extension = extension.__index__()
        if not 0 <= extension <= 0xFFFF:
            raise ValueError('extension overflow')

        data = extension.to_bytes(2, byteorder='big')
        record = cls(cls.TAG_TYPE.EXTENDED_SEGMENT_ADDRESS, data=data)
        return record

    @classmethod
    def build_start_linear_address(cls, address: int) -> 'IhexRecord':
        # TODO: __doc__

        address = address.__index__()
        if not 0 <= address <= 0xFFFFFFFF:
            raise ValueError('address overflow')

        data = address.to_bytes(4, byteorder='big')
        record = cls(cls.TAG_TYPE.START_LINEAR_ADDRESS, data=data)
        return record

    @classmethod
    def build_start_segment_address(cls, address: int) -> 'IhexRecord':
        # TODO: __doc__

        address = address.__index__()
        if not 0 <= address <= 0xFFFFFFFF:
            raise ValueError('address overflow')

        data = address.to_bytes(4, byteorder='big')
        record = cls(cls.TAG_TYPE.START_SEGMENT_ADDRESS, data=data)
        return record

    def compute_checksum(self) -> int:

        if self.count is None:
            raise ValueError('missing count')

        count = self.count & 0xFF
        address = self.address & 0xFFFF
        sum_address = (address >> 8) + (address & 0xFF)
        sum_data = sum(iter(self.data))
        tag = _cast(IhexTag, self.tag) & 0xFF
        checksum = (count + sum_address + tag + sum_data)
        checksum = (0x100 - (checksum & 0xFF)) & 0xFF
        return checksum

    def compute_count(self) -> int:

        return len(self.data)

    @classmethod
    def parse(cls, line: AnyBytes) -> 'IhexRecord':
        # TODO: __doc__

        match = cls.LINE_REGEX.match(line)
        if not match:
            raise ValueError('syntax error')

        groups = match.groupdict()
        before = groups['before']
        count = int(groups['count'], 16)
        address = int(groups['address'], 16)
        tag = cls.TAG_TYPE(int(groups['tag'], 16))
        data = binascii.unhexlify(groups['data'])
        checksum = int(groups['checksum'], 16)
        after = groups['after']

        record = cls(tag,
                     address=address,
                     data=data,
                     count=count,
                     checksum=checksum,
                     before=before,
                     after=after)
        return record

    def to_bytestr(self, end: AnyBytes = b'\r\n') -> bytes:

        self.validate()

        bytestr = b'%s:%02X%04X%02X%s%02X%s%s' % (
            self.before,
            self.count & 0xFF,
            self.address & 0xFFFF,
            _cast(IhexTag, self.tag) & 0xFF,
            binascii.hexlify(self.data).upper(),
            self.checksum & 0xFF,
            self.after,
            end,
        )
        return bytestr

    def to_tokens(self, end: AnyBytes = b'\r\n') -> Mapping[str, bytes]:

        self.validate()
        return {
            'before': self.before,
            'begin': b':',
            'count': b'%02X' % (self.count & 0xFF),
            'address': b'%04X' % (self.address & 0xFFFF),
            'tag': b'%02X' % (_cast(IhexTag, self.tag) & 0xFF),
            'data': binascii.hexlify(self.data).upper(),
            'checksum': b'%02X' % (self.checksum & 0xFF),
            'after': self.after,
            'end': end,
        }

    def validate(self) -> 'IhexRecord':

        super().validate()

        # if self.after and not self.after.isspace():
        #     raise ValueError('junk after is not whitespace')

        if b':' in self.before:
            raise ValueError('junk before contains ":"')

        if not 0 <= self.checksum <= 0xFF:
            raise ValueError('checksum overflow')

        if not 0 <= self.count <= 0xFF:
            raise ValueError('count overflow')

        data_size = len(self.data)
        if data_size > 0xFF:
            raise ValueError('data size overflow')

        if not 0 <= self.address <= 0xFFFF:
            raise ValueError('address overflow')

        tag = _cast(IhexTag, self.tag)

        if tag.is_data():
            pass

        elif tag.is_start():
            if data_size != 4:
                raise ValueError('start address data size overflow')

        elif tag.is_extension():
            if data_size != 2:
                raise ValueError('extension data size overflow')

        else:  # elif tag.is_eof():
            if data_size:
                raise ValueError('end of file record data')

        return self


class IhexFile(BaseFile):

    FILE_EXT: Sequence[str] = [
        # https://en.wikipedia.org/wiki/Intel_HEX
        # General - purpose:
        '.hex', '.mcs', '.int', '.ihex', '.ihe', '.ihx',
        # Platform-specific:
        # '.h80', '.h86', '.a43', '.a90',  # (currently unsupported)
        # Split, banked, or paged:
        # '.hxl', '.hxh', '.h00', '.h15', '.p00', '.pff'  # (currently unsupported)
        # Binary or Intel hex:
        # '.obj', '.obl', '.obh', '.rom', '.eep'  # (currently unsupported)
    ]

    META_KEYS: Sequence[str] = ['linear', 'maxdatalen', 'startaddr']

    RECORD_TYPE: Type[IhexRecord] = IhexRecord

    def __init__(self):

        super().__init__()

        self._linear: bool = True
        self._startaddr: Optional[int] = None

    def apply_records(self) -> 'IhexFile':

        if not self._records:
            raise ValueError('records required')

        tag_type = _cast(IhexTag, self.RECORD_TYPE.TAG_TYPE)
        data_tag = tag_type.DATA
        ela_tag = tag_type.EXTENDED_LINEAR_ADDRESS
        esa_tag = tag_type.EXTENDED_SEGMENT_ADDRESS
        memory = Memory()
        extension = 0
        startaddr = None
        has_ela = False
        has_esa = False

        for record in self._records:
            tag = _cast(IhexTag, record.tag)

            if tag == data_tag:
                memory.write(record.address + extension, record.data)

            elif tag == ela_tag:
                has_ela = True
                extension = record.data_to_int() << 16

            elif tag == esa_tag:
                has_esa = True
                extension = record.data_to_int() << 4

            elif tag.is_start():
                startaddr = record.data_to_int()

        self.discard_memory()
        self._memory = memory
        self._startaddr = startaddr
        self._linear = has_ela or not has_esa
        return self

    @property
    def linear(self) -> bool:

        if self._memory is None:
            self.apply_records()
        return self._linear

    @linear.setter
    def linear(self, linear: bool) -> None:

        linear = bool(linear)
        if linear != self._linear:
            self.discard_records()
        self._linear = linear

    @classmethod
    def parse(cls, stream: IO, ignore_errors: bool = False) -> 'IhexFile':

        file = super().parse(stream, ignore_errors=ignore_errors)
        return _cast(IhexFile, file)

    @property
    def startaddr(self) -> Optional[int]:

        if self._memory is None:
            self.apply_records()
        return self._startaddr

    @startaddr.setter
    def startaddr(self, address: Optional[int]) -> None:

        if address is not None:
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
    ) -> 'IhexFile':
        # TODO: __doc__

        memory = self._memory
        if memory is None:
            raise ValueError('memory instance required')

        records = []
        record_type = self.RECORD_TYPE
        last_start = 0
        linear = self.linear
        chunk_views = []
        try:
            for chunk_start, chunk_view in memory.chop(self.maxdatalen, align=align):
                chunk_views.append(chunk_view)

                if linear:
                    if (chunk_start ^ last_start) & 0xFFFF0000:
                        extension = chunk_start >> 16
                        record = record_type.build_extended_linear_address(extension)
                        records.append(record)
                else:
                    if chunk_start > 0x000FFFFF:
                        raise ValueError('segment overflow')

                    if (chunk_start ^ last_start) & 0x000F0000:
                        extension = (chunk_start & 0x000F0000) >> 4
                        record = record_type.build_extended_segment_address(extension)
                        records.append(record)

                address = chunk_start & 0xFFFF
                data = bytes(chunk_view)
                record = record_type.build_data(address, data)
                setattr(record, '_extended_address', chunk_start)  # for debug
                records.append(record)
                last_start = chunk_start

            startaddr = self._startaddr
            if start and startaddr is not None:
                if linear:
                    record = record_type.build_start_linear_address(startaddr)
                else:
                    record = record_type.build_start_segment_address(startaddr)
                records.append(record)

            record = record_type.build_end_of_file()
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
        start_required: bool = False,
        start_penultimate: bool = True,
        start_within_data: bool = False,
    ) -> 'IhexFile':
        # TODO: __doc__

        records = self._records
        if records is None:
            raise ValueError('records required')

        start_record = None
        eof_record = None
        last_data_endex = 0
        extension = 0

        for index, record in enumerate(records):
            record = _cast(IhexRecord, record)
            record.validate()
            tag = _cast(IhexTag, record.tag)

            if data_ordering:
                if tag == tag.DATA:
                    extended_address = record.address + extension
                    if extended_address < last_data_endex:
                        raise ValueError('unordered data record')
                    last_data_endex = extended_address + len(record.data)

                elif tag == tag.EXTENDED_LINEAR_ADDRESS:
                    extension = record.data_to_int() << 16

                elif tag == tag.EXTENDED_SEGMENT_ADDRESS:
                    extension = record.data_to_int() << 4

            if tag == tag.END_OF_FILE:
                if index != len(records) - 1:
                    raise ValueError('end of file record not last')
                eof_record = record

            if tag.is_start():
                if start_penultimate:
                    if index != len(records) - 2:
                        raise ValueError('start record not penultimate')
                start_record = record

        if eof_record is None:
            raise ValueError('missing end of file record')

        if start_required:
            if start_record is None:
                raise ValueError('missing start record')

        if start_within_data:
            if start_record is not None:
                startaddr = start_record.data_to_int()
                start_datum = self.memory.peek(startaddr)
                if start_datum is None:
                    raise ValueError('no data at start address')

        return self
