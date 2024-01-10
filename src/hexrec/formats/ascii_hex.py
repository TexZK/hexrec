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
from typing import Union
from typing import cast as _cast

from ..records2 import BaseFile
from ..records2 import BaseRecord
from ..records2 import BaseTag
from ..utils import AnyBytes


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

    Tag: Type[AsciiHexTag] = AsciiHexTag

    LINE_REGEX = re.compile(
        b'\\s*(\\$[Aa](?P<address>[0-9A-Fa-f]+)[,.])?\\s*'
        b"(?P<data>([0-9A-Fa-f]{2}[\\s%',]?)*)\\s*"
    )
    # TODO: __doc__

    DATA_SEPS: bytes = b" \t\n\r\v\f%',"
    # TODO: __doc__

    def compute_count(self) -> Optional[int]:

        if self.tag == self.Tag.ADDRESS_DATA:
            return self.count  # loopback
        else:
            return None

    @classmethod
    def create_address(
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

        record = cls(cls.Tag.ADDRESS_DATA, address=address, data=data, count=addrlen)
        return record

    @classmethod
    def create_data(
        cls,
        address: int,
        data: AnyBytes,
    ) -> 'AsciiHexRecord':
        # TODO: __doc__

        del address
        record = cls(cls.Tag.DATA, data=data)
        return record

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
            tag = cls.Tag.ADDRESS_DATA
            address = int(address_group, 16)
            if addrlen is None:
                addrlen = len(address_group)
        else:
            tag = cls.Tag.DATA
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

        self.validate(checksum=False, count=False)
        tag = _cast(AsciiHexTag, self.tag)
        addrstr = b''
        datastr = b''

        if tag == tag.ADDRESS_DATA:
            addrstr = (b'$A%%0%dX' % self.count) % (self.address & 0xFFFFFFFF)

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

        self.validate(checksum=False, count=False)
        tag = _cast(AsciiHexTag, self.tag)
        addrstr = b''
        datastr = b''

        if tag == tag.ADDRESS_DATA:
            addrstr = (b'$A%%0%dX' % self.count) % (self.address & 0xFFFFFFFF)

        if self.data:
            datastr = binascii.hexlify(self.data, exechar).upper()

        return {
            'before': self.before,
            'address': addrstr,
            'data': datastr,
            'after': self.after,
            'end': end,
        }

    def validate(
        self,
        checksum: bool = True,
        count: bool = True,
    ) -> 'AsciiHexRecord':

        super().validate(checksum=checksum, count=count)

        if self.after and not self.after.isspace():
            raise ValueError('junk after')

        if self.before and not self.before.isspace():
            raise ValueError('junk before')

        if self.count < 1:
            raise ValueError('invalid count')

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
                record = Record.parse(chunk, address=address)
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
        Record = self.Record
        last_data_endex = 0
        chunk_views = []
        try:
            for chunk_start, chunk_view in memory.chop(self.maxdatalen, align=align):
                chunk_views.append(chunk_view)
                data = bytes(chunk_view)

                if chunk_start == last_data_endex:
                    record = Record.create_data(data)
                else:
                    record = Record.create_address(chunk_start, data, addrlen=addrlen)

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
        address_data_tag = self.Record.Tag.ADDRESS_DATA

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
