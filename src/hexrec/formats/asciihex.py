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
import re
from typing import IO
from typing import Mapping
from typing import Optional
from typing import Type
from typing import cast as _cast

from ..base import AnyBytes
from ..base import BaseFile
from ..base import BaseRecord
from ..base import BaseTag


class AsciiHexTag(BaseTag, enum.IntEnum):
    r"""ASCII-HEX tag."""

    DATA = 0
    r"""Data."""

    ADDRESS = 1
    r"""Address."""

    CHECKSUM = 2
    r"""Checksum."""

    _DATA = DATA

    def is_address(self) -> bool:
        # TODO: __doc__

        return self == 1

    def is_checksum(self) -> bool:
        # TODO: __doc__

        return self == 2

    def is_data(self) -> bool:

        return self == 0


class AsciiHexRecord(BaseRecord):
    # TODO: __doc__

    Tag: Type[AsciiHexTag] = AsciiHexTag

    LINE_REGEX = re.compile(
        b'\\s*('
        b"(?P<data>([0-9A-Fa-f]{2}[ \t\v\f\r%',]?)+)|"
        b'(\\$[Aa](?P<address>[0-9A-Fa-f]+)[,.])|'
        b'(\\$[Ss](?P<checksum>[0-9A-Fa-f]+)[,.])'
        b')\\s*'
    )
    # TODO: __doc__

    DATA_EXECHARS: bytes = b" \t\v\f\r%',"
    # TODO: __doc__

    def compute_checksum(self) -> Optional[int]:
        # TODO: __doc__

        Tag = self.Tag
        tag = self.tag

        if tag == Tag.CHECKSUM:
            return self.checksum  # loopback
        else:
            return None  # not supported

    def compute_count(self) -> Optional[int]:
        # TODO: __doc__

        Tag = self.Tag
        tag = self.tag

        if tag == Tag.ADDRESS:
            return self.count  # loopback
        else:
            return None  # not supported

    @classmethod
    def create_address(
        cls,
        address: int,
        addrlen: int = 8,
    ) -> 'AsciiHexRecord':
        # TODO: __doc__

        record = cls(cls.Tag.ADDRESS, address=address, count=addrlen)
        return record

    @classmethod
    def create_checksum(
        cls,
        checksum: int,
    ) -> 'AsciiHexRecord':
        # TODO: __doc__

        record = cls(cls.Tag.CHECKSUM, checksum=checksum)
        return record

    @classmethod
    def create_data(
        cls,
        address: int,
        data: AnyBytes,
    ) -> 'AsciiHexRecord':
        # TODO: __doc__

        record = cls(cls.Tag.DATA, data=data, address=address)
        return record

    @classmethod
    def parse(
        cls,
        line: AnyBytes,
        address: int = 0,
        validate: bool = True,
    ) -> 'AsciiHexRecord':
        # TODO: __doc__

        match = cls.LINE_REGEX.match(line)
        if not match:
            raise ValueError('syntax error')

        coords = match.span()
        groups = match.groupdict()
        groups_address = groups['address']
        groups_checksum = groups['checksum']
        groups_data = groups['data'] or b''

        Tag = cls.Tag
        checksum = None
        count = None
        data = b''

        if groups_address:
            tag = Tag.ADDRESS
            address = int(groups_address, 16)
            count = len(groups_address)

        elif groups_checksum:
            tag = Tag.CHECKSUM
            checksum = int(groups_checksum, 16)

        else:
            tag = Tag.DATA
            data = groups_data.translate(None, delete=cls.DATA_EXECHARS)
            data = binascii.unhexlify(data)

        record = cls(tag,
                     address=address,
                     data=data,
                     checksum=checksum,
                     count=count,
                     coords=coords,
                     validate=validate)
        return record

    def to_bytestr(
        self,
        exechar: AnyBytes = b' ',
        exelast: bool = True,
        dollarend: AnyBytes = b',',
        end: AnyBytes = b'\r\n',
    ) -> bytes:
        # TODO: __doc__

        self.validate(checksum=False, count=False)
        valstr = b''

        if self.tag == AsciiHexTag.ADDRESS:
            count = self.count or 1
            valstr = (b'$A%%0%dX%s' % (count, dollarend)) % (self.address & 0xFFFFFFFF)

        elif self.tag == AsciiHexTag.CHECKSUM:
            valstr = b'$S%04X%s' % ((self.checksum & 0xFFFF), dollarend)

        elif self.data:
            valstr = binascii.hexlify(self.data, exechar)
            if exelast:
                valstr += exechar
            valstr = valstr.upper()

        bytestr = b'%s%s%s%s' % (self.before, valstr, self.after, end)
        return bytestr

    def to_tokens(
        self,
        exechar: bytes = b' ',
        exelast: bool = True,
        dollarend: AnyBytes = b',',
        end: AnyBytes = b'\r\n',
    ) -> Mapping[str, bytes]:

        self.validate(checksum=False, count=False)
        tag = _cast(AsciiHexTag, self.tag)
        addrstr = b''
        chksstr = b''
        datastr = b''

        if tag == tag.ADDRESS:
            count = self.count or 1
            addrstr = (b'$A%%0%dX%s' % (count, dollarend)) % (self.address & 0xFFFFFFFF)

        elif tag == tag.CHECKSUM:
            chksstr = b'$S%04X%s' % ((self.checksum & 0xFFFF), dollarend)

        elif self.data:
            datastr = binascii.hexlify(self.data, exechar)
            if exelast:
                datastr += exechar
            datastr = datastr.upper()

        return {
            'before': self.before,
            'address': addrstr,
            'data': datastr,
            'checksum': chksstr,
            'after': self.after,
            'end': end,
        }

    def validate(
        self,
        checksum: bool = True,
        count: bool = True,
    ) -> 'AsciiHexRecord':

        super().validate(checksum=checksum, count=count)
        Tag = self.Tag
        tag = self.tag

        if self.after and not self.after.isspace():
            raise ValueError('junk after')

        if self.before and not self.before.isspace():
            raise ValueError('junk before')

        if checksum:
            if self.checksum is None:
                if tag == Tag.CHECKSUM:
                    raise ValueError('checksum required')
            else:
                if not 0 <= self.checksum <= 0xFFFF:
                    raise ValueError('checksum overflow')

        if count:
            if self.count is None:
                if tag == Tag.ADDRESS:
                    raise ValueError('count required')
            else:
                addrstr = b'%X' % self.address
                if self.count < len(addrstr):
                    raise ValueError('count overflow')

        if self.data:
            if tag != Tag.DATA:
                raise ValueError('unexpected data')

        return self


class AsciiHexFile(BaseFile):

    Record: Type[AsciiHexRecord] = AsciiHexRecord

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
        Record = cls.Record

        if stxetx:
            stx_offset = buffer.find(0x02)
            if stx_offset < 0:
                raise ValueError('missing STX character')
            stx_offset += 1

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
            chunk = view[offset:etx_offset]
            try:
                record = Record.parse(chunk, address=address)
            except Exception:
                if ignore_errors:
                    offset += 1
                    continue
                raise
            pos, endpos = record.coords
            pos += offset
            endpos += offset
            record.coords = pos, endpos
            offset = endpos
            address = record.address + len(record.data)
            records.append(record)

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
        checksum: bool = False,
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
        Record = self.Record
        last_data_endex = 0
        file_checksum = 0
        chunk_views = []
        try:
            for chunk_start, chunk_view in memory.chop(self.maxdatalen, align=align):
                chunk_views.append(chunk_view)
                data = bytes(chunk_view)
                if checksum:
                    sum_data = sum(data) & 0xFFFF
                    file_checksum = (file_checksum + sum_data) & 0xFFFF

                if chunk_start != last_data_endex:
                    record = Record.create_address(chunk_start, addrlen=addrlen)
                    records.append(record)

                record = Record.create_data(chunk_start, data)
                records.append(record)
                last_data_endex = chunk_start + len(chunk_view)

        finally:
            for chunk_view in chunk_views:
                chunk_view.release()

        if checksum:
            record = Record.create_checksum(file_checksum)
            records.append(record)

        self.discard_records()
        self._records = records
        return self

    def validate_records(
        self,
        data_ordering: bool = False,
        checksum_values: bool = True,
    ) -> 'AsciiHexFile':
        # TODO: __doc__

        records = self._records
        if records is None:
            raise ValueError('records required')

        Tag = self.Record.Tag
        last_data_endex = 0
        file_checksum = 0

        for index, record in enumerate(records):
            record = _cast(AsciiHexRecord, record)
            record.validate()
            tag = record.tag

            if tag == Tag.ADDRESS:
                if data_ordering:
                    if record.address < last_data_endex:
                        raise ValueError('unordered data record')
                last_data_endex = record.address

            elif tag == Tag.CHECKSUM:
                if checksum_values:
                    if record.checksum != file_checksum:
                        raise ValueError('wrong checksum')

            else:  # elif tag == Tag.DATA:
                last_data_endex += len(record.data)
                sum_data = sum(iter(record.data)) & 0xFFFF
                file_checksum = (file_checksum + sum_data) & 0xFFFF

        return self
