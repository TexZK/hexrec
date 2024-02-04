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

import enum
import re
from typing import IO
from typing import Any
from typing import Mapping
from typing import Sequence
from typing import Type
from typing import TypeVar
from typing import cast as _cast

from bytesparse import Memory

from ..base import AnyBytes
from ..base import BaseFile
from ..base import BaseRecord
from ..base import BaseTag
from ..base import TypeAlias
from ..utils import hexlify
from ..utils import unhexlify

try:
    from typing import Self
except ImportError:  # pragma: no cover
    Self: TypeAlias = Any
__TYPING_HAS_SELF = Self is not Any


class XtekTag(BaseTag, enum.IntEnum):
    r"""Tektronix Extended tag."""

    DATA = 6
    r"""Data."""

    EOF = 8
    r"""End Of File."""

    _DATA = DATA

    def is_data(self) -> bool:

        return self == 6

    def is_eof(self) -> bool:
        # TODO: __doc__

        return self == 8


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='XtekRecord')


class XtekRecord(BaseRecord):
    # TODO: __doc__

    Tag: Type[XtekTag] = XtekTag

    EQUALITY_KEYS: Sequence[str] = list(BaseRecord.EQUALITY_KEYS) + ['addrlen']

    META_KEYS: Sequence[str] = list(BaseRecord.META_KEYS) + ['addrlen']

    LINE1_REGEX = re.compile(
        b'^(?P<before>[^%]*)%'
        b'(?P<count>[0-9A-Fa-f]{2})'
        b'(?P<tag>[68])'
        b'(?P<checksum>[0-9A-Fa-f]{2})'
        b'(?P<addrlen>[1-9A-Fa-f])'
    )
    # TODO: __doc__

    LINE2_REGEX = [re.compile(
        b'^(?P<address>[0-9A-Fa-f]{%d})'
        b'(?P<data>([0-9A-Fa-f]{2}){,%d})'
        b'(?P<after>[^\\r\\n]*)\\r?\\n$'
        % (i, ((249 - i) // 2))
    ) for i in range(1, 16)]
    # TODO: __doc__

    def __init__(
        self,
        *super_init_args,
        addrlen: int = 8,
        validate: bool = True,
        **super_init_kwargs,
    ):

        if validate:
            addrlen = addrlen.__index__()
            if not 1 <= addrlen <= 15:
                raise ValueError('invalid address length')

        self.addrlen = addrlen
        super().__init__(*super_init_args, validate=validate, **super_init_kwargs)

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

        tag = _cast(XtekTag, self.tag)
        checksum = (count_sum + tag + self.addrlen + address_sum + data_sum) & 0xFF
        return checksum

    def compute_count(self) -> int:

        count = 6 + self.addrlen + (len(self.data) * 2)
        return count

    @classmethod
    def compute_data_max(cls, addrlen: int) -> int:
        # TODO: __doc__

        if not 1 <= addrlen <= 15:
            raise ValueError('invalid address length')

        datamax = (249 - addrlen) // 2
        return datamax

    @classmethod
    def create_data(
        cls,
        address: int,
        data: AnyBytes,
        addrlen: int = 8,
    ) -> Self:
        # TODO: __doc__

        addrlen = addrlen.__index__()
        if not 1 <= addrlen <= 15:
            raise ValueError('invalid address length')
        addrmax = cls.compute_address_max(addrlen)

        address = address.__index__()
        if not 0 <= address <= addrmax:
            raise ValueError('address overflow')

        datamax = cls.compute_data_max(addrlen)
        if len(data) > datamax:
            raise ValueError('data size overflow')

        return cls(cls.Tag.DATA, address=address, data=data, addrlen=addrlen)

    @classmethod
    def create_eof(
        cls,
        start: int = 0,
        addrlen: int = 8,
    ) -> Self:
        # TODO: __doc__

        addrlen = addrlen.__index__()
        if not 1 <= addrlen <= 15:
            raise ValueError('invalid address length')
        addrmax = cls.compute_address_max(addrlen)

        startaddr = start.__index__()
        if not 0 <= startaddr <= addrmax:
            raise ValueError('start address overflow')

        return cls(cls.Tag.EOF, address=startaddr, addrlen=addrlen)

    def get_address_max(self) -> int:
        # TODO: __doc__

        return self.compute_address_max(self.addrlen)

    def get_data_max(self) -> int:
        # TODO: __doc__

        return self.compute_data_max(self.addrlen)

    @classmethod
    def parse(
        cls,
        line: AnyBytes,
        validate: bool = True,
    ) -> Self:
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
        data = unhexlify(groups['data'])
        after = groups['after']

        record = cls(tag,
                     address=address,
                     data=data,
                     count=count,
                     checksum=checksum,
                     before=before,
                     after=after,
                     addrlen=addrlen,
                     validate=validate)
        return record

    def to_bytestr(self, end: AnyBytes = b'\r\n') -> bytes:

        self.validate(checksum=False, count=False)

        bytestr = b'%s%%%02X%X%02X%X%s%s%s%s' % (
            self.before,
            (self.count or 0) & 0xFF,
            _cast(XtekTag, self.tag) & 0xF,
            (self.checksum or 0) & 0xFF,
            self.addrlen & 0xF,
            (b'%%0%dX' % self.addrlen) % (self.address & 0xFFFFFFFF),
            hexlify(self.data),
            self.after,
            end,
        )
        return bytestr

    def to_tokens(self, end: AnyBytes = b'\r\n') -> Mapping[str, bytes]:

        self.validate(checksum=False, count=False)
        return {
            'before': self.before,
            'begin': b'%',
            'count': b'%02X' % ((self.count or 0) & 0xFF),
            'tag': b'%X' % (_cast(XtekTag, self.tag) & 0xF),
            'checksum': b'%02X' % ((self.checksum or 0) & 0xFF),
            'addrlen': b'%X' % (self.addrlen & 0xF),
            'address': (b'%%0%dX' % self.addrlen) % (self.address & 0xFFFFFFFF),
            'data': hexlify(self.data),
            'after': self.after,
            'end': end,
        }

    def validate(
        self,
        checksum: bool = True,
        count: bool = True,
    ) -> Self:

        super().validate(checksum=checksum, count=count)

        if self.after and not self.after.isspace():
            raise ValueError('junk after is not whitespace')

        if b'%' in self.before:
            raise ValueError('junk before contains "%"')

        if self.checksum is not None:
            if not 0 <= self.checksum <= 0xFF:
                raise ValueError('checksum overflow')

        if self.count is not None:
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

        if self.tag == XtekTag.EOF and data_size:
            raise ValueError('unexpected data')

        return self


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='XtekFile')


class XtekFile(BaseFile):

    FILE_EXT: Sequence[int] = ['.tek', '.xtek']

    META_KEYS: Sequence[str] = ['maxdatalen', 'startaddr']

    Record: Type[XtekRecord] = XtekRecord

    def __init__(self):

        super().__init__()

        self._startaddr: int = 0

    def apply_records(self) -> Self:
        # TODO: __doc__

        if not self._records:
            raise ValueError('records required')

        memory = Memory()
        startaddr = 0

        for record in self._records:
            tag = _cast(XtekTag, record.tag)

            if tag == XtekTag.DATA:
                memory.write(record.address, record.data)

            else:  # elif tag == XtekTag.EOF:
                startaddr = record.address

        self.discard_memory()
        self._memory = memory
        self._startaddr = startaddr
        return self

    @classmethod
    def parse(cls, stream: IO, ignore_errors: bool = False) -> Self:

        file = super().parse(stream, ignore_errors=ignore_errors)
        return _cast(XtekFile, file)

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
        align: bool = False,
        addrlen: int = 8,
    ) -> Self:
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
    ) -> Self:
        # TODO: __doc__

        records = self._records
        if records is None:
            raise ValueError('records required')

        eof_record = None
        last_data_endex = 0

        for index, record in enumerate(records):
            record = _cast(XtekRecord, record)
            record.validate()
            tag = _cast(XtekTag, record.tag)

            if data_ordering:
                if tag == tag.DATA:
                    address = record.address
                    if address < last_data_endex:
                        raise ValueError('unordered data record')
                    last_data_endex = address + len(record.data)

            if tag == tag.EOF:
                if index != len(records) - 1:
                    raise ValueError('end of file record not last')
                eof_record = record

        if eof_record is None:
            raise ValueError('missing end of file record')

        if startaddr_within_data:
            start_datum = self.memory.peek(eof_record.address)
            if start_datum is None:
                raise ValueError('no data at start address')

        return self


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
