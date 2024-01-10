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
from typing import IO
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Type
from typing import cast as _cast

from bytesparse import Memory

from ..records import BaseFile
from ..records import BaseRecord
from ..records import BaseTag
from ..utils import AnyBytes


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

    _DATA = DATA

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

    Tag: Type[IhexTag] = IhexTag

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
    def create_data(
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

        record = cls(cls.Tag.DATA, address=address, data=data)
        return record

    @classmethod
    def create_end_of_file(cls) -> 'IhexRecord':
        # TODO: __doc__

        record = cls(cls.Tag.END_OF_FILE)
        return record

    @classmethod
    def create_extended_linear_address(cls, extension: int) -> 'IhexRecord':
        # TODO: __doc__

        extension = extension.__index__()
        if not 0 <= extension <= 0xFFFF:
            raise ValueError('extension overflow')

        data = extension.to_bytes(2, byteorder='big')
        record = cls(cls.Tag.EXTENDED_LINEAR_ADDRESS, data=data)
        return record

    @classmethod
    def create_extended_segment_address(cls, extension: int) -> 'IhexRecord':
        # TODO: __doc__

        extension = extension.__index__()
        if not 0 <= extension <= 0xFFFF:
            raise ValueError('extension overflow')

        data = extension.to_bytes(2, byteorder='big')
        record = cls(cls.Tag.EXTENDED_SEGMENT_ADDRESS, data=data)
        return record

    @classmethod
    def create_start_linear_address(cls, address: int) -> 'IhexRecord':
        # TODO: __doc__

        address = address.__index__()
        if not 0 <= address <= 0xFFFFFFFF:
            raise ValueError('address overflow')

        data = address.to_bytes(4, byteorder='big')
        record = cls(cls.Tag.START_LINEAR_ADDRESS, data=data)
        return record

    @classmethod
    def create_start_segment_address(cls, address: int) -> 'IhexRecord':
        # TODO: __doc__

        address = address.__index__()
        if not 0 <= address <= 0xFFFFFFFF:
            raise ValueError('address overflow')

        data = address.to_bytes(4, byteorder='big')
        record = cls(cls.Tag.START_SEGMENT_ADDRESS, data=data)
        return record

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
        tag = cls.Tag(int(groups['tag'], 16))
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

        self.validate(checksum=False, count=False)

        bytestr = b'%s:%02X%04X%02X%s%02X%s%s' % (
            self.before,
            (self.count or 0) & 0xFF,
            self.address & 0xFFFF,
            _cast(IhexTag, self.tag) & 0xFF,
            binascii.hexlify(self.data).upper(),
            (self.checksum or 0) & 0xFF,
            self.after,
            end,
        )
        return bytestr

    def to_tokens(self, end: AnyBytes = b'\r\n') -> Mapping[str, bytes]:

        self.validate(checksum=False, count=False)
        return {
            'before': self.before,
            'begin': b':',
            'count': b'%02X' % ((self.count or 0) & 0xFF),
            'address': b'%04X' % (self.address & 0xFFFF),
            'tag': b'%02X' % (_cast(IhexTag, self.tag) & 0xFF),
            'data': binascii.hexlify(self.data).upper(),
            'checksum': b'%02X' % ((self.checksum or 0) & 0xFF),
            'after': self.after,
            'end': end,
        }

    def validate(
        self,
        checksum: bool = True,
        count: bool = True,
    ) -> 'IhexRecord':

        super().validate(checksum=checksum, count=count)

        # if self.after and not self.after.isspace():
        #     raise ValueError('junk after is not whitespace')

        if b':' in self.before:
            raise ValueError('junk before contains ":"')

        if self.checksum is not None:
            if not 0 <= self.checksum <= 0xFF:
                raise ValueError('checksum overflow')

        if self.count is not None:
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

    Record: Type[IhexRecord] = IhexRecord

    def __init__(self):

        super().__init__()

        self._linear: bool = True
        self._startaddr: Optional[int] = None

    def apply_records(self) -> 'IhexFile':

        if not self._records:
            raise ValueError('records required')

        tag_type = _cast(IhexTag, self.Record.Tag)
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
        Record = self.Record
        last_start = 0
        linear = self.linear
        chunk_views = []
        try:
            for chunk_start, chunk_view in memory.chop(self.maxdatalen, align=align):
                chunk_views.append(chunk_view)

                if linear:
                    if (chunk_start ^ last_start) & 0xFFFF0000:
                        extension = chunk_start >> 16
                        record = Record.create_extended_linear_address(extension)
                        records.append(record)
                else:
                    if chunk_start > 0x000FFFFF:
                        raise ValueError('segment overflow')

                    if (chunk_start ^ last_start) & 0x000F0000:
                        extension = (chunk_start & 0x000F0000) >> 4
                        record = Record.create_extended_segment_address(extension)
                        records.append(record)

                address = chunk_start & 0xFFFF
                data = bytes(chunk_view)
                record = Record.create_data(address, data)
                setattr(record, '_extended_address', chunk_start)  # for debug
                records.append(record)
                last_start = chunk_start

            startaddr = self._startaddr
            if start and startaddr is not None:
                if linear:
                    record = Record.create_start_linear_address(startaddr)
                else:
                    record = Record.create_start_segment_address(startaddr)
                records.append(record)

            record = Record.create_end_of_file()
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
