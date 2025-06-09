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

r"""MOS Technology format.

See Also:
    `<https://srecord.sourceforge.net/man/man5/srec_mos_tech.5.html>`_
"""

import enum
import io
import re
from typing import IO
from typing import Any
from typing import Mapping
from typing import Type
from typing import TypeVar
from typing import cast as _cast

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


class MosTag(BaseTag, enum.IntEnum):
    r"""MOS Technology tag."""

    DATA = 0
    r"""Data."""

    EOF = 1
    r"""End Of File."""

    _DATA = DATA

    def is_data(self) -> bool:

        return self == self.DATA

    def is_eof(self) -> bool:
        r"""Tells whether this is an End Of File record tag.

        This method returns true if this record tag is used for *End Of File*
        records.

        Returns:
            bool: This is an End Of File record tag.

        Examples:
            >>> from hexrec import MosFile
            >>> MosTag = MosFile.Record.Tag
            >>> MosTag.EOF.is_eof()
            True
            >>> MosTag.DATA.is_eof()
            False
        """

        return self == self.EOF

    def is_file_termination(self) -> bool:

        return self.is_eof()


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='MosRecord')


class MosRecord(BaseRecord):
    r"""MOS Technology record object."""

    Tag: Type[MosTag] = MosTag

    LINE_REGEX = re.compile(
        b'^\0*(?P<before>[^;]*);'
        b'(?P<count>[0-9A-Fa-f]{2})'
        b'(?P<address>[0-9A-Fa-f]{4})'
        b'(?P<data>([0-9A-Fa-f]{2}){,255})'
        b'(?P<checksum>[0-9A-Fa-f]{4})'
        b'(?P<after>[^\\r\\n]*)\\r?\\n?\0*$'
    )
    r"""Line parser regex."""

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
    ) -> Self:

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
    ) -> Self:
        r"""Creates an End Of File record.

        The End Of File record also carries the *record count*.

        Args:
            record_count (int):
                Number of preceding records.

        Returns:
            :class:`MosRecord`: End Of File record object.

        Examples:
            >>> from hexrec import MosFile
            >>> record = MosFile.Record.create_eof(123)
            >>> str(record)
            ';00007B007B\r\n\x00\x00\x00\x00\x00\x00'
        """

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
    ) -> Self:
        r"""Parses a record from bytes.

        Please refer to the actual implementation provided by the record
        *format* for more details.

        Args:
            line (bytes):
                String of bytes to parse.

            eof (bool):
                Parsing an *End Of File* record.

            validate (bool):
                Perform validation checks.

        Returns:
            :class:`BaseRecord`: Parsed record.

        Raises:
            ValueError: Syntax error.

        Examples:
            >>> from hexrec import MosFile
            >>> record = MosFile.Record.parse(b';0000010001\r\n', eof=True)
            >>> record.tag
            <MosTag.EOF: 1>
            >>> MosFile.Record.parse(b';;0000010001\r\n', eof=True)
            Traceback (most recent call last):
                ...
            ValueError: syntax error
        """

        match = cls.LINE_REGEX.match(line)
        if not match:
            raise ValueError('syntax error')

        groups = match.groupdict()
        before = groups['before']
        count = int(groups['count'], 16)
        address = int(groups['address'], 16)
        data = unhexlify(groups['data'])
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
            hexlify(self.data),
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
            'data': hexlify(self.data),
            'checksum': b'%04X' % ((self.checksum or 0) & 0xFFFF),
            'after': self.after,
            'end': end,
            'nuls': nulstr,
        }

    def validate(
        self,
        checksum: bool = True,
        count: bool = True,
    ) -> Self:

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


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='MosFile')


class MosFile(BaseFile):
    r"""MOS Technology file object."""

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
        ignore_after_termination: bool = True,
        eof_record: bool = True,
    ) -> Self:
        r"""Parses records from a byte stream.

        It executes :meth:`MosRecord.parse` for each line of the incoming
        `stream`, creating a new file object with the collected records calling
        :meth:`from_records`.

        Lines resulting empty by :meth:`_is_empty_line` are just discarded.

        Notes:
            Please refer to the actual implementation of each record file
            *format*, because it may be more specialized.

        Args:
            stream (bytes IO):
                Stream to serialize records onto.

            ignore_errors (bool):
                Ignore :class:`Exception` raised by :meth:`MosRecord.parse`.

            ignore_after_termination (bool):
                Ignore anything after the *End Of File* record was parsed.

            eof_record (bool):
                Interpret the last record as the *End Of File* record.

        Returns:
            :class:`MosFile`: *self*.

        See Also:
            :meth:`parse`
            :meth:`MosRecord.parse`
            :meth:`from_records`
            :meth:`_is_empty_line`

        Examples:
            >>> from hexrec import MosFile
            >>> buffer = b'''
            ...     ;031234616263016F
            ...     ;0000010001
            ... '''
            >>> import io
            >>> stream = io.BytesIO(buffer)
            >>> file = MosFile.parse(stream)
            >>> file.memory.to_blocks()
            [[4660, b'abc']]
            >>> file.get_meta()
            {'maxdatalen': 3}
        """

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

        file = super().parse(stream, ignore_errors=ignore_errors,
                             ignore_after_termination=ignore_after_termination)
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
        r"""Serializes records onto a byte stream.

        It executes :meth:`MosRecord.serialize` for each of the stored
        :attr:`records`.

        Args:
            stream (bytes IO):
                Stream to serialize records onto.

            end (bytes):
                Line ending suffix bytes.

            nuls (bool):
                Append six ASCII ``NUL`` (zero) bytes after each line, as
                prescribed by the original specifications.

            xoff (bool):
                Append the ASCII ``XOFF`` byte at the end of the whole
                serialization.

        Returns:
            :class:`MosFile`: *self*.

        See Also:
            :meth:`parse`
            :meth:`MosRecord.serialize`

        Examples:
            >>> from hexrec import MosFile
            >>> file = MosFile.from_blocks([[0xDA7A, b'abc']])
            >>> import sys
            >>> _ = file.serialize(sys.stdout.buffer, nuls=False, xoff=False)
            ;03DA7A616263027D
            ;0000010001
        """

        for record in self.records:
            record.serialize(stream, end=end, nuls=nuls)

        if xoff:
            stream.write(b'\x13')

        return self

    def update_records(
        self,
        align: bool = False,
    ) -> Self:
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
            :class:`MosFile`: *self*.

        Raises:
            ValueError: :attr:`memory` attribute not populated.

        See Also:
            :attr:`records`
            :attr:`memory`
            :meth:`get_meta`
            :meth:`apply_records`

        Examples:
            >>> from hexrec import MosFile
            >>> blocks = [[123, b'abc']]
            >>> file = MosFile.from_blocks(blocks, maxdatalen=16)
            >>> file.memory.to_blocks()
            [[123, b'abc']]
            >>> file.get_meta()
            {'maxdatalen': 16}
            >>> _ = file.update_records()
            >>> len(file.records)
            2
            >>> _ = file.print(nuls=False)
            ;03007B61626301A4
            ;0000010001
        """

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
    ) -> Self:
        r"""Validates records.

        It performs consistency checks for the underlying :attr:`records`.

        Args:
            data_ordering (bool):
                Checks that the *data* record sequence has monotonically
                increasing addresses, without any overlapping.

            eof_record_required (bool):
                Requires the *End Of File* record be present.

        Returns:
            :class:`MosFile`: *self*.

        Raises:
            ValueError: Invalid record sequence.

        Examples:
            >>> from hexrec import MosFile
            >>> records = [MosFile.Record.create_data(123, b'abc')]
            >>> file = MosFile.from_records(records)
            >>> _ = file.validate_records()
            Traceback (most recent call last):
                ...
            ValueError: missing end of file record
        """

        records = self._records
        if records is None:
            raise ValueError('records required')

        eof_record = None
        last_data_endex = 0

        for index, record in enumerate(records):
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


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
