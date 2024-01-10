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
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Type
from typing import cast as _cast

from ..records2 import BaseFile
from ..records2 import BaseRecord
from ..records2 import BaseTag
from ..utils import AnyBytes


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

    Tag: Type[TekExtTag] = TekExtTag

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
    def create_data(
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

        return cls(cls.Tag.EOF, address=address, data=data, addrlen=addrlen)

    @classmethod
    def create_eof(
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

        return cls(cls.Tag.EOF, address=startaddr, addrlen=addrlen)

    @classmethod
    def compute_address_max(cls, addrlen: int) -> int:
        # TODO: __doc__

        if not 1 <= addrlen <= 15:
            raise ValueError('invalid address length')

        addrmax = (1 << (addrlen * 4)) - 1
        return addrmax

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
        tag = cls.Tag(int(groups['tag'], 16))
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

        self.validate(checksum=False, count=False)

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

        self.validate(checksum=False, count=False)
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

    def validate(
        self,
        checksum: bool = True,
        count: bool = True,
    ) -> 'TekExtRecord':

        super().validate(checksum=checksum, count=count)

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

    Record: Type[TekExtRecord] = TekExtRecord

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
        Record = self.Record
        chunk_views = []
        try:
            for chunk_start, chunk_view in memory.chop(self.maxdatalen, align=align):
                chunk_views.append(chunk_view)
                data = bytes(chunk_view)
                record = Record.create_data(chunk_start, data, addrlen=addrlen)
                records.append(record)

            record = Record.create_eof(self.startaddr, addrlen=addrlen)
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
