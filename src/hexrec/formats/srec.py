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

r"""Motorola S-record format.

See Also:
    `<https://en.wikipedia.org/wiki/SREC_(file_format)>`_
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

from ..base import AnyBytes
from ..base import BaseFile
from ..base import BaseRecord
from ..base import BaseTag


class SrecTag(BaseTag, enum.IntEnum):
    r"""Motorola S-record tag."""

    HEADER = 0
    r"""Header string. Optional."""

    DATA_16 = 1
    r"""16-bit address data record."""

    DATA_24 = 2
    r"""24-bit address data record."""

    DATA_32 = 3
    r"""32-bit address data record."""

    RESERVED = 4
    r"""Reserved tag."""

    COUNT_16 = 5
    r"""16-bit record count. Optional."""

    COUNT_24 = 6
    r"""24-bit record count. Optional."""

    START_32 = 7
    r"""32-bit start address. Terminates :attr:`DATA_32`."""

    START_24 = 8
    r"""24-bit start address. Terminates :attr:`DATA_24`."""

    START_16 = 9
    r"""16-bit start address. Terminates :attr:`DATA_16`."""

    _DATA = DATA_16

    @classmethod
    def fit_count_tag(cls, count: int) -> 'SrecTag':
        # TODO: __doc__

        if count < 0:
            raise ValueError('count overflow')
        if count <= 0xFFFF:
            return cls.COUNT_16
        if count <= 0xFFFFFF:
            return cls.COUNT_24
        raise ValueError('count overflow')

    @classmethod
    def fit_data_tag(cls, address_max: int) -> 'SrecTag':
        # TODO: __doc__

        if address_max < 0:
            raise ValueError('address overflow')
        if address_max <= 0xFFFF:
            return cls.DATA_16
        if address_max <= 0xFFFFFF:
            return cls.DATA_24
        if address_max <= 0xFFFFFFFF:
            return cls.DATA_32
        raise ValueError('address overflow')

    def get_address_max(self) -> Optional[int]:
        # TODO: __doc__

        size = self.get_address_size()
        mask = (1 << (size << 3)) - 1
        return mask

    def get_address_size(self) -> Optional[int]:
        # TODO: __doc__

        SIZES = (2, 2, 3, 4, None, 2, 3, 4, 3, 2)
        size = SIZES[self]
        return size

    def get_data_max(self) -> Optional[int]:
        # TODO: __doc__

        size = 0xFE - self.get_address_size()
        return size

    def get_tag_match(self) -> Optional['SrecTag']:
        # TODO: __doc__

        MATCHES = (None, 9, 8, 7, None, None, None, 3, 2, 1)
        match = MATCHES[self]
        if match is None:
            return None
        tag_type = type(self)
        return tag_type(match)

    def is_count(self) -> bool:
        # TODO: __doc__

        return self == 5 or self == 6

    def is_data(self) -> bool:
        # TODO: __doc__

        return self == 1 or self == 2 or self == 3

    def is_header(self) -> bool:
        # TODO: __doc__

        return self == 0

    def is_start(self) -> bool:
        # TODO: __doc__

        return self == 7 or self == 8 or self == 9


SIZE_TO_ADDRESS_FORMAT: Mapping[int, bytes] = {
    2: b'%04X',
    3: b'%06X',
    4: b'%08X',
}
# TODO: __doc__


class SrecRecord(BaseRecord):
    # TODO: __doc__

    Tag: Type[SrecTag] = SrecTag

    LINE1_REGEX = re.compile(
        b'^(?P<before>\\s*)[Ss]'
        b'(?P<tag>[0-9A-Fa-f])'
        b'(?P<count>[0-9A-Fa-f]{2})'
    )
    # TODO: __doc__

    LINE2_REGEX = [re.compile(
        b'^(?P<address>[0-9A-Fa-f]{%d})' % (4 + (i * 2))
    ) for i in range(3)]
    # TODO: __doc__

    LINE3_REGEX = re.compile(
        b'^(?P<data>([0-9A-Fa-f]{2})*)'
        b'(?P<checksum>[0-9A-Fa-f]{2})'
        b'(?P<after>[^\\r\\n]*)\\r?\\n?$'
    )
    # TODO: __doc__

    def compute_checksum(self) -> int:

        checksum = self.count & 0xFF
        address = self.address & 0xFFFFFFFF
        while address > 0:
            checksum += address & 0xFF
            address >>= 8
        checksum += sum(iter(self.data))
        checksum = (checksum & 0xFF) ^ 0xFF
        return checksum

    def compute_count(self) -> int:

        tag = _cast(SrecTag, self.tag)
        count = tag.get_address_size() + len(self.data) + 1
        return count

    @classmethod
    def create_count(
        cls,
        count: int,
        tag: Optional[SrecTag] = None,
    ) -> 'SrecRecord':
        # TODO: __doc__

        Tag = cls.Tag
        if tag is None:
            tag = Tag.fit_count_tag(count)
        else:
            if not Tag.COUNT_16 <= tag <= Tag.COUNT_24:
                raise ValueError('invalid count tag')

        if not 0 <= count <= tag.get_address_max():
            raise ValueError('count overflow')

        record = cls(tag, address=count)
        return record

    @classmethod
    def create_data(
        cls,
        address: int,
        data: AnyBytes,
        tag: Optional[SrecTag] = None,
    ) -> 'SrecRecord':
        # TODO: __doc__

        Tag = cls.Tag
        if tag is None:
            tag = Tag.fit_data_tag(address)
        else:
            if not Tag.DATA_16 <= tag <= Tag.DATA_32:
                raise ValueError('invalid data tag')

        if not 0 <= address <= tag.get_address_max():
            raise ValueError('address overflow')

        if len(data) > tag.get_data_max():
            raise ValueError('data size overflow')

        record = cls(tag, address=address, data=data)
        return record

    @classmethod
    def create_header(cls, data: AnyBytes = b'') -> 'SrecRecord':
        # TODO: __doc__

        if len(data) > 0xFC:
            raise ValueError('data size overflow')

        Tag = cls.Tag
        record = cls(Tag.HEADER, data=data)
        return record

    @classmethod
    def create_start(
        cls,
        address: int = 0,
        tag: Optional[SrecTag] = None,
    ) -> 'SrecRecord':
        # TODO: __doc__

        Tag = cls.Tag
        if tag is None:
            tag = Tag.fit_data_tag(address).get_tag_match()
        else:
            if not Tag.START_32 <= tag <= Tag.START_16:
                raise ValueError('invalid start tag')

        if not 0 <= address <= tag.get_address_max():
            raise ValueError('address overflow')

        record = cls(tag, address=address)
        return record

    @classmethod
    def parse(
        cls,
        line: AnyBytes,
        validate: bool = True,
    ) -> 'SrecRecord':
        # TODO: __doc__

        Tag = cls.Tag
        line = memoryview(line)

        match = cls.LINE1_REGEX.match(line)
        if not match:
            raise ValueError('syntax error')
        groups = match.groupdict()
        before = groups['before']
        tag = Tag(int(groups['tag'], 16))
        count = int(groups['count'], 16)

        addridx = tag.get_address_size() - 2
        line = line[match.span()[1]:]
        match = cls.LINE2_REGEX[addridx].match(line)
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
        checksum = int(groups['checksum'], 16)
        after = groups['after']

        record = cls(tag,
                     address=address,
                     data=data,
                     count=count,
                     checksum=checksum,
                     before=before,
                     after=after,
                     validate=validate)
        return record

    def to_bytestr(self, end: AnyBytes = b'\r\n') -> bytes:

        self.validate(checksum=False, count=False)
        tag = _cast(SrecTag, self.tag)
        addrfmt = SIZE_TO_ADDRESS_FORMAT[tag.get_address_size()]

        bytestr = b'%sS%X%02X%s%s%02X%s%s' % (
            self.before,
            tag & 0xF,
            (self.count or 0) & 0xFF,
            addrfmt % (self.address & 0xFFFFFFFF),
            binascii.hexlify(self.data).upper(),
            (self.checksum or 0) & 0xFF,
            self.after,
            end,
        )
        return bytestr

    def to_tokens(self, end: AnyBytes = b'\r\n') -> Mapping[str, bytes]:

        self.validate(checksum=False, count=False)
        tag = _cast(SrecTag, self.tag)
        addrfmt = SIZE_TO_ADDRESS_FORMAT[tag.get_address_size()]

        return {
            'before': self.before,
            'begin': b'S',
            'tag': b'%X' % (tag & 0xF),
            'count': b'%02X' % ((self.count or 0) & 0xFF),
            'address': addrfmt % (self.address & 0xFFFFFFFF),
            'data': binascii.hexlify(self.data).upper(),
            'checksum': b'%02X' % ((self.checksum or 0) & 0xFF),
            'after': self.after,
            'end': end,
        }

    def validate(
        self,
        checksum: bool = True,
        count: bool = True,
    ) -> 'SrecRecord':

        super().validate(checksum=checksum, count=count)
        address = self.address

        # if self.after and not self.after.isspace():
        #     raise ValueError('junk after')

        if self.before and not self.before.isspace():
            raise ValueError('junk before')

        if self.checksum is not None:
            if not 0 <= self.checksum <= 0xFF:
                raise ValueError('checksum overflow')

        if self.count is not None:
            if not 3 <= self.count <= 0xFF:
                raise ValueError('count overflow')

        Tag = _cast(SrecTag, self.Tag)
        tag = _cast(SrecTag, self.tag)
        if tag == Tag.RESERVED:
            raise ValueError('reserved tag')

        data_size = len(self.data)

        if not Tag.HEADER <= tag <= Tag.DATA_32:
            if data_size:
                raise ValueError('unexpected data')

        if data_size > tag.get_data_max():
            raise ValueError('data size overflow')

        if not 0 <= address <= tag.get_address_max():
            raise ValueError('address overflow')

        return self


class SrecFile(BaseFile):
    # TODO: __doc__

    FILE_EXT: Sequence[str] = [
        # https://en.wikipedia.org/wiki/SREC_(file_format)
        '.s19', '.s28', '.s37', '.s',
        '.s1', '.s2', '.s3', '.sx',
        '.srec', '.exo', '.mot', '.mxt',
    ]

    META_KEYS: Sequence[str] = ['header', 'maxdatalen', 'startaddr']

    Record: Type[SrecRecord] = SrecRecord

    def __init__(self):

        super().__init__()

        self._header: Optional[AnyBytes] = b''
        self._startaddr: int = 0

    def apply_records(self) -> 'SrecFile':

        if not self._records:
            raise ValueError('records required')

        memory = Memory()
        startaddr = 0
        header = None

        for record in self._records:
            tag = _cast(SrecTag, record.tag)

            if tag.is_data():
                memory.write(record.address, record.data)

            elif tag.is_start():
                startaddr = record.address

            elif tag.is_header():
                header = record.data

        self.discard_memory()
        self._memory = memory
        self._startaddr = startaddr
        self._header = header
        return self

    @property
    def header(self) -> Optional[AnyBytes]:

        if self._memory is None:
            self.apply_records()
        return self._header

    @header.setter
    def header(self, header: Optional[AnyBytes]) -> None:

        if header != self._header:
            self.discard_records()
        self._header = header

    @classmethod
    def parse(
        cls, stream: IO,
        ignore_errors: bool = False,
        # TODO: ignore_after_termination: bool = True,
    ) -> 'SrecFile':

        file = super().parse(stream, ignore_errors=ignore_errors)
        return _cast(SrecFile, file)

    @property
    def startaddr(self) -> int:

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
        header: bool = True,
        data: bool = False,
        count: bool = True,
        start: bool = True,
        data_tag: Optional[SrecTag] = None,
        count_tag: Optional[SrecTag] = None,
    ) -> 'SrecFile':
        # TODO: __doc__

        memory = self._memory
        if memory is None:
            raise ValueError('memory instance required')

        records = []
        Record = self.Record
        Tag = Record.Tag
        if data_tag is None:
            data_tag = Tag.fit_data_tag(max(0, memory.endin))
        chunk_views = []
        data_record_count = 0
        try:
            if header and self._header is not None:
                record = Record.create_header(self._header)
                records.append(record)

            for chunk_start, chunk_view in memory.chop(self.maxdatalen, align=align):
                chunk_views.append(chunk_view)
                data = bytes(chunk_view)
                record = Record.create_data(chunk_start, data, tag=data_tag)
                records.append(record)
                data_record_count += 1

            if data and not data_record_count:
                record = Record.create_data(0, b'', tag=data_tag)
                records.append(record)
                data_record_count += 1

            if count:
                if count_tag is None:
                    count_tag = Tag.fit_count_tag(data_record_count)
                record = Record.create_count(data_record_count, tag=count_tag)
                records.append(record)

            start_tag = data_tag.get_tag_match()
            address = self._startaddr if start else 0
            record = Record.create_start(address, tag=start_tag)
            records.append(record)

        finally:
            for chunk_view in chunk_views:
                chunk_view.release()

        self.discard_records()
        self._records = records
        return self

    def validate_records(
        self,
        header_required: bool = False,
        header_first: bool = True,
        data_ordering: bool = False,
        data_uniform: bool = True,
        count_required: bool = False,
        count_penultimate: bool = True,
        start_last: bool = True,
        start_within_data: bool = False,
    ) -> 'SrecFile':
        # TODO: __doc__

        records = self._records
        if records is None:
            raise ValueError('records required')

        header_record = None
        start_record = None
        count_record = None
        last_data_endex = 0
        data_tag_sample = None
        data_count = 0

        for index, record in enumerate(records):
            record = _cast(SrecRecord, record)
            record.validate()
            tag = _cast(SrecTag, record.tag)

            if tag.is_data():
                data_count += 1

                if data_uniform:
                    if data_tag_sample is None:
                        data_tag_sample = tag
                    elif tag != data_tag_sample:
                        raise ValueError('data record tags not uniform')

                if data_ordering:
                    address = record.address
                    if address < last_data_endex:
                        raise ValueError('unordered data record')
                    last_data_endex = address + len(record.data)

            elif tag.is_count():
                if count_record is not None:
                    raise ValueError('multiple count records')
                count_record = record

                if record.address != data_count:
                    raise ValueError('wrong data record count')

                if count_penultimate:
                    if index != len(records) - 2:
                        raise ValueError('count record not penultimate')

            elif tag.is_start():
                if start_record is not None:
                    raise ValueError('multiple start records')
                start_record = record

                if start_last:
                    if index != len(records) - 1:
                        raise ValueError('start record not last')

            else:  # elif tag.is_header():
                if header_first:
                    if index != 0:
                        raise ValueError('header record not first')
                header_record = record

        if header_required:
            if header_record is None:
                raise ValueError('missing header record')

        if count_required:
            if count_record is None:
                raise ValueError('missing count record')

        if start_record is None:
            raise ValueError('missing start record')

        if start_within_data:
            startaddr = start_record.address
            start_datum = self.memory.peek(startaddr)
            if start_datum is None:
                raise ValueError('no data at start address')

        if data_uniform:
            if start_record.tag != data_tag_sample.get_tag_match():
                raise ValueError('start record tag not uniform')

        return self
