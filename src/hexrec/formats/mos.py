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
from typing import Mapping
from typing import Type
from typing import cast as _cast

from ..records import BaseFile
from ..records import BaseRecord
from ..records import BaseTag
from ..utils import AnyBytes


class MosTag(BaseTag, enum.IntEnum):
    r"""MOS Technology tag."""

    DATA = 0
    r"""Data."""

    EOF = 1  # FIXME: add full support
    r"""End Of File."""

    _DATA = DATA

    def is_data(self) -> bool:

        return self == 0

    def is_eof(self) -> bool:
        # TODO: __doc__

        return self == 1


class MosRecord(BaseRecord):
    # TODO: __doc__

    Tag: Type[MosTag] = MosTag

    LINE_REGEX = re.compile(
        b'^\0*(?P<before>[^;]*);'
        b'(?P<count>[0-9A-Fa-f]{2})'
        b'(?P<address>[0-9A-Fa-f]{4})'
        b'(?P<data>([0-9A-Fa-f]{2}){,255})'
        b'(?P<checksum>[0-9A-Fa-f]{4})'
        b'(?P<after>[^\\r\\n]*)\\r?\\n?\0*$'
    )
    # TODO: __doc__

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
    def create_data(
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

        record = cls(cls.Tag.DATA, address=address, data=data)
        return record

    @classmethod
    def create_eof(
        cls,
        record_count: int,
    ) -> 'MosRecord':
        # TODO: __doc__

        record_count = record_count.__index__()
        if not 0 <= record_count <= 0xFFFF:
            raise ValueError('record count overflow')

        record = cls(cls.Tag.EOF, address=record_count)
        return record

    @classmethod
    def parse(
        cls,
        line: AnyBytes,
        eof: bool = False,
        validate: bool = True,
    ) -> 'MosRecord':
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

        record = cls(cls.Tag.EOF if eof else cls.Tag.DATA,
                     address=address,
                     data=data,
                     count=count,
                     checksum=checksum,
                     before=before,
                     after=after,
                     validate=validate)
        return record

    def to_bytestr(
        self,
        end: AnyBytes = b'\r\n',
        nuls: bool = True,
    ) -> bytes:

        self.validate(checksum=False, count=False)
        nulstr = b'\0\0\0\0\0\0' if nuls else b''

        line = b'%s;%02X%04X%s%04X%s%s%s' % (
            self.before,
            (self.count or 0) & 0xFF,
            self.address & 0xFFFF,
            binascii.hexlify(self.data).upper(),
            (self.checksum or 0) & 0xFFFF,
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

        self.validate(checksum=False, count=False)
        nulstr = b'\0\0\0\0\0\0' if nuls else b''

        return {
            'before': self.before,
            'begin': b';',
            'count': b'%02X' % ((self.count or 0) & 0xFF),
            'address': b'%04X' % (self.address & 0xFFFF),
            'data': binascii.hexlify(self.data).upper(),
            'checksum': b'%04X' % ((self.checksum or 0) & 0xFFFF),
            'after': self.after,
            'end': end,
            'nuls': nulstr,
        }

    def validate(
        self,
        checksum: bool = True,
        count: bool = True,
    ) -> 'MosRecord':

        super().validate(checksum=checksum, count=count)

        if self.after and not self.after.isspace():
            raise ValueError('junk after is not whitespace')

        if b';' in self.before:
            raise ValueError('junk before contains ";"')

        if self.checksum is not None:
            if not 0 <= self.checksum <= 0xFFFF:
                raise ValueError('checksum overflow')

        if self.count is not None:
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

    Record: Type[MosRecord] = MosRecord

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
                file._records[-1].tag = cls.Record.Tag.EOF  # patch
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
        Record = self.Record
        chunk_views = []
        try:
            for chunk_start, chunk_view in memory.chop(self.maxdatalen, align=align):
                chunk_views.append(chunk_view)
                data = bytes(chunk_view)
                record = Record.create_data(chunk_start, data)
                records.append(record)

            record = Record.create_eof(len(records))
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
