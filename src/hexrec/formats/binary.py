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

r"""Binary format.

This format is actually used to hold binary chunks of raw data (`bytes`).
"""

import enum
import sys
from typing import IO
from typing import Mapping
from typing import Sequence
from typing import Type

from ..records2 import BaseFile
from ..records2 import BaseRecord
from ..records2 import BaseTag
from ..utils import AnyBytes


@enum.unique
class RawTag(BaseTag, enum.Enum):
    r"""Binary tag."""

    DATA = ...
    r"""Data."""

    def is_data(self) -> bool:

        return True


class RawRecord(BaseRecord):
    # TODO: __doc__

    Tag: Type[RawTag] = RawTag

    @classmethod
    def create_data(
        cls,
        address: int,
        data: AnyBytes,
    ) -> 'RawRecord':
        # TODO: __doc__

        address = address.__index__()
        if address < 0:
            raise ValueError('address overflow')

        record = cls(cls.Tag.DATA, address=address, data=data)
        return record

    @classmethod
    def parse(cls, line: AnyBytes, address: int = 0) -> 'RawRecord':

        return cls.create_data(address, line)

    def to_bytestr(self) -> bytes:

        self.validate(checksum=False, count=False)
        return bytes(self.data)

    def to_tokens(self) -> Mapping[str, bytes]:

        self.validate(checksum=False, count=False)
        return {
            'data': self.data,
        }


class RawFile(BaseFile):

    DEFAULT_DATALEN: int = sys.maxsize

    FILE_EXT: Sequence[str] = [
        # A very generic list
        '.bin', '.dat', '.eep', '.raw',
    ]

    Record: Type[RawRecord] = RawRecord

    @classmethod
    def _is_line_empty(cls, line: AnyBytes) -> bool:

        return not line

    @classmethod
    def parse(
        cls,
        stream: IO,
        ignore_errors: bool = False,
        maxdatalen: int = sys.maxsize,
        address: int = 0,
    ) -> 'RawFile':
        # TODO: __doc__

        maxdatalen = maxdatalen.__index__()
        if maxdatalen < 1:
            raise ValueError('invalid maximum data length')
        if maxdatalen == sys.maxsize:
            maxdatalen = -1

        records = []
        Record = cls.Record

        chunk = b'...'
        while chunk:
            chunk = stream.read(maxdatalen)
            if chunk:
                record = Record.create_data(address, chunk)
                record.coords = (0, address)
                records.append(record)
                size = len(chunk)
                address += size

        file = cls.from_records(records)
        file._maxdatalen = maxdatalen
        return file

    def update_records(
        self,
        align: bool = True,
    ) -> 'RawFile':
        # TODO: __doc__

        memory = self._memory
        if memory is None:
            raise ValueError('memory instance required')
        with memory.view():  # contiguity check
            pass

        records = []
        Record = self.Record
        chunk_views = []
        try:
            for chunk_start, chunk_view in memory.chop(self.maxdatalen, align=align):
                chunk_views.append(chunk_view)
                data = bytes(chunk_view)
                record = Record.create_data(chunk_start, data)
                records.append(record)

        finally:
            for chunk_view in chunk_views:
                chunk_view.release()

        self.discard_records()
        self._records = records
        return self

    def validate_records(
        self,
        data_contiguity: bool = True,
        data_ordering: bool = True,
    ) -> 'RawFile':
        # TODO: __doc__

        if self._records is None:
            raise ValueError('records required')

        last_data_end = None

        for record in self._records:
            record.validate()
            address = record.address
            if last_data_end is None:
                last_data_end = address

            if data_contiguity and address != last_data_end:
                raise ValueError('data not contiguous')

            if data_ordering and address < last_data_end:
                raise ValueError('unordered data record')

            last_data_end = address + len(record.data)

        return self
