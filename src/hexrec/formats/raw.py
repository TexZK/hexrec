# Copyright (c) 2013-2025, Andrea Zoppi
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
from typing import Any
from typing import Mapping
from typing import Sequence
from typing import Type
from typing import TypeVar

from ..base import AnyBytes
from ..base import BaseFile
from ..base import BaseRecord
from ..base import BaseTag
from ..base import TypeAlias

try:
    from typing import Self
except ImportError:  # pragma: no cover
    Self: TypeAlias = Any  # Python < 3.11
__TYPING_HAS_SELF = Self is not Any


class RawTag(BaseTag, enum.Enum):
    r"""Raw binary tag."""

    DATA = ...
    r"""Data."""

    _DATA = DATA

    def is_data(self) -> bool:

        return True

    def is_file_termination(self) -> bool:

        return super().is_file_termination()


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='RawRecord')


class RawRecord(BaseRecord):
    r"""Raw binary record object."""

    Tag: Type[RawTag] = RawTag

    @classmethod
    def create_data(
        cls,
        address: int,
        data: AnyBytes,
    ) -> 'RawRecord':

        address = address.__index__()
        if address < 0:
            raise ValueError('address overflow')

        record = cls(cls.Tag.DATA, address=address, data=data)
        return record

    @classmethod
    def parse(
        cls,
        line: AnyBytes,
        address: int = 0,
        validate: bool = True,
    ) -> 'RawRecord':
        r"""Parses a record from bytes.

        Please refer to the actual implementation provided by the record
        *format* for more details.

        Args:
            line (bytes):
                String of bytes to parse.

            address (int):
                Record address.

            validate (bool):
                Perform validation checks.

        Returns:
            :class:`RawRecord`: Parsed record.

        Raises:
            ValueError: Syntax error.

        Examples:
            >>> from hexrec import RawFile
            >>> record = RawFile.Record.parse(b'abc', address=123)
            >>> record.address
            123
            >>> record.data
            b'abc'
        """

        del validate
        return cls.create_data(address, line)

    def to_bytestr(self) -> bytes:

        self.validate(checksum=False, count=False)
        return bytes(self.data)

    def to_tokens(self) -> Mapping[str, bytes]:

        self.validate(checksum=False, count=False)
        return {
            'data': self.data,
        }


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='RawFile')


class RawFile(BaseFile):
    r"""Raw binary file object."""

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
        r"""Parses records from a byte stream.

        It executes :meth:`RawRecord.parse` for each line of the incoming
        `stream`, creating a new file object with the collected records calling
        :meth:`from_records`.

        Notes:
            Please refer to the actual implementation of each record file
            *format*, because it may be more specialized.

        Args:
            stream (bytes IO):
                Stream to serialize records onto.

            ignore_errors (bool):
                Ignore :class:`Exception` raised by :meth:`RawRecord.parse`.

            maxdatalen (int):
                Maximum *data* record data size, to chop the incoming stream.

            address (int):
                Initial address.

        Returns:
            :class:`RawFile`: *self*.

        See Also:
            :meth:`parse`
            :meth:`BaseRecord.parse`
            :meth:`from_records`

        Examples:
            >>> from hexrec import RawFile
            >>> import io
            >>> stream = io.BytesIO(b'Hello, World!')
            >>> file = RawFile.parse(stream, maxdatalen=5, address=1000)
            >>> for record in file.records:
            ...     print(f'{record.address}: {record.data!r}')
            1000: b'Hello'
            1005: b', Wor'
            1010: b'ld!'
            >>> file.get_meta()
            {'maxdatalen': 5}
        """

        del ignore_errors  # unused
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
        align: bool = False,
    ) -> 'RawFile':
        r"""Applies memory and meta to records.

        This method processes the stored :attr:`memory` and *meta* information
        to generate the sequence of :attr:`records`.

        This effectively converts the *memory role* into the *records role*
        (keeping both).

        The :attr:`records` is assigned upon return.
        Any exceptions being raised should not alter the file object.

        Args:
            align (bool):
                Aligns data record chunk address bounds to :attr:`maxdatalen`.

        Returns:
            :class:`RawFile`: *self*.

        Raises:
            ValueError: :attr:`memory` attribute not populated.

        See Also:
            :attr:`records`
            :attr:`memory`
            :meth:`get_meta`
            :meth:`apply_records`

        Examples:
            >>> from hexrec import RawFile
            >>> blocks = [[123, b'abc']]
            >>> file = RawFile.from_blocks(blocks, maxdatalen=16)
            >>> file.memory.to_blocks()
            [[123, b'abc']]
            >>> file.get_meta()
            {'maxdatalen': 16}
            >>> _ = file.update_records()
            >>> len(file.records)
            1
            >>> _ = file.print()
            abc
        """

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
        data_start: bool = True,
        data_contiguity: bool = True,
        data_ordering: bool = True,
    ) -> 'RawFile':
        r"""Validates records.

        It performs consistency checks for the underlying :attr:`records`.

        Args:
            data_start (bool):
                Data records must start from address zero.

            data_contiguity (bool):
                Requires *data* records be ordered and contiguous.

            data_ordering (bool):
                Checks that the *data* record sequence has monotonically
                increasing addresses, without any overlapping.

        Returns:
            :class:`RawFile`: *self*.

        Raises:
            ValueError: Invalid record sequence.

        Examples:
            >>> from hexrec import RawFile
            >>> records = [RawFile.Record.create_data(123, b'abc')]
            >>> file = RawFile.from_records(records)
            >>> _ = file.validate_records()
            Traceback (most recent call last):
                ...
            ValueError: first record address not zero
        """

        if self._records is None:
            raise ValueError('records required')

        if data_start and self._records:
            if self._records[0].address != 0:
                raise ValueError('first record address not zero')

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


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
