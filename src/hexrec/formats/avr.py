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

r"""Atmel Generic format.

See Also:
    `<https://srecord.sourceforge.net/man/man5/srec_atmel_generic.5.html>`_
"""

import enum
import re
from typing import Any
from typing import Mapping
from typing import Sequence
from typing import Type
from typing import TypeVar

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
    Self: TypeAlias = Any  # Python < 3.11
__TYPING_HAS_SELF = Self is not Any


class AvrTag(BaseTag, enum.Enum):
    r"""Atmel Generic tag."""

    DATA = ...
    r"""Data."""

    _DATA = DATA

    def is_data(self) -> bool:

        return self == self.DATA


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='AvrRecord')


class AvrRecord(BaseRecord):
    r"""Atmel Generic record object."""

    Tag: Type[AvrTag] = AvrTag

    LINE_REGEX = re.compile(
        b'^(?P<before>[ \\t]*)'
        b'(?P<address>[0-9A-Fa-f]{6})'
        b'[ \\t]*:[ \\t]*'
        b'(?P<data>([0-9A-Fa-f]{4}))'
        b'(?P<after>[ \\t]*)\\r?\\n?$'
    )
    r"""Line parser regex."""

    @classmethod
    def create_data(
        cls,
        address: int,
        data: AnyBytes,
    ) -> Self:

        address = address.__index__()
        if not 0 <= address <= 0xFFFFFF:
            raise ValueError('address overflow')

        size = len(data)
        if size != 2:
            raise ValueError('size overflow')

        record = cls(cls.Tag.DATA, address=address, data=data)
        return record

    @classmethod
    def parse(
        cls,
        line: AnyBytes,
        validate: bool = True,
    ) -> Self:
        r"""Parses a record from bytes.

        Args:
            line (bytes):
                String of bytes to parse.

            validate (bool):
                Perform validation checks.

        Returns:
            :class:`BaseRecord`: Parsed record.

        Raises:
            ValueError: Syntax error.

        Examples:
            >>> from hexrec import AvrFile
            >>> record = AvrFile.Record.parse(b'000080:4865\r\n')
            >>> record.tag
            <AvrTag.EOF: 1>
            >>> AvrFile.Record.parse(b'000080::4865\r\n')
            Traceback (most recent call last):
                ...
            ValueError: syntax error
        """

        match = cls.LINE_REGEX.match(line)
        if not match:
            raise ValueError('syntax error')

        groups = match.groupdict()
        before = groups['before']
        address = int(groups['address'], 16)
        data = unhexlify(groups['data'])
        after = groups['after']

        record = cls(cls.Tag.DATA,
                     address=address,
                     data=data,
                     before=before,
                     after=after,
                     validate=validate)
        return record

    def to_bytestr(
        self,
        end: AnyBytes = b'\r\n',
    ) -> bytes:

        self.validate()

        line = b'%s%06X:%s%s%s' % (
            self.before,
            self.address & 0xFFFFFF,
            hexlify(self.data),
            self.after,
            end,
        )
        return line

    def to_tokens(
        self,
        end: AnyBytes = b'\r\n',
    ) -> Mapping[str, bytes]:

        self.validate()

        return {
            'before': self.before,
            'address': b'%06X' % (self.address & 0xFFFFFF),
            'begin': b':',
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

        if self.before and not self.before.isspace():
            raise ValueError('junk before is not whitespace')

        data_size = len(self.data)
        if data_size != 2:
            raise ValueError('data size overflow')

        if not 0 <= self.address <= 0xFFFFFF:
            raise ValueError('address overflow')

        return self


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='AvrFile')


class AvrFile(BaseFile):
    r"""Atmel Generic file object."""

    DEFAULT_DATALEN: int = 2

    FILE_EXT: Sequence[str] = ['.rom']

    Record: Type[AvrRecord] = AvrRecord

    def apply_records(self) -> Self:

        if self._records is None:
            raise ValueError('records required')

        memory = Memory()

        for record in self._records:
            byte_address = record.address * 2
            memory.write(byte_address, record.data)

        self.discard_memory()
        self._memory = memory
        return self

    def update_records(self) -> Self:
        r"""Applies memory and meta to records.

        This method processes the stored :attr:`memory` and *meta* information
        to generate the sequence of :attr:`records`.

        This effectively converts the *memory role* into the *records role*
        (keeping both).

        The :attr:`records` is assigned upon return.
        Any exceptions being raised should not alter the file object.

        Returns:
            :class:`AvrFile`: *self*.

        Raises:
            ValueError: :attr:`memory` attribute not populated.

        See Also:
            :attr:`records`
            :attr:`memory`
            :meth:`get_meta`
            :meth:`apply_records`

        Examples:
            >>> from hexrec import AvrFile
            >>> blocks = [[124, b'abcd']]
            >>> file = AvrFile.from_blocks(blocks)
            >>> file.memory.to_blocks()
            [[124, b'abcd']]
            >>> file.get_meta()
            {'maxdatalen': 2}
            >>> _ = file.update_records()
            >>> len(file.records)
            2
            >>> _ = file.print()
            00003E:6162
            00003F:6364
        """

        memory = self._memory
        if memory is None:
            raise ValueError('memory instance required')
        if self.maxdatalen != 2:
            raise ValueError('invalid maximum data length')

        records = []
        Record = self.Record
        chunk_views = []
        try:
            for chunk_start, chunk_view in memory.chop(2):
                if chunk_start & 1:
                    raise ValueError('invalid word alignment')
                if len(chunk_view) != 2:
                    raise ValueError('invalid word size')
                word_address = chunk_start // 2
                chunk_views.append(chunk_view)
                word_data = bytes(chunk_view)
                record = Record.create_data(word_address, word_data)
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
    ) -> Self:
        r"""Validates records.

        It performs consistency checks for the underlying :attr:`records`.

        Args:
            data_ordering (bool):
                Checks that the *data* record sequence has monotonically
                increasing addresses, without any overlapping.

        Returns:
            :class:`AvrFile`: *self*.

        Raises:
            ValueError: Invalid record sequence.

        Examples:
            >>> from hexrec import AvrFile
            >>> records = [AvrFile.Record.create_data(62, b'ab'),
            ...            AvrFile.Record.create_data(61, b'cd')]
            >>> file = AvrFile.from_records(records)
            >>> _ = file.validate_records(data_ordering=True)
            Traceback (most recent call last):
                ...
            ValueError: unordered data record
        """

        records = self._records
        if records is None:
            raise ValueError('records required')

        last_data_endex = 0

        for record in records:
            record.validate()

            if data_ordering:
                byte_address = record.address * 2
                if byte_address < last_data_endex:
                    raise ValueError('unordered data record')
                last_data_endex = byte_address + len(record.data)

        return self


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
