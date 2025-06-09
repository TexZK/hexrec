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

r"""Texas Instruments TI-TXT format.

See Also:
    `<https://downloads.ti.com/docs/esd/SPNU118/ti-txt-hex-format-ti-txt-option-stdz0795656.html>`_
"""

import enum
import re
from typing import IO
from typing import Any
from typing import Mapping
from typing import Optional
from typing import Sequence
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


class TiTxtTag(BaseTag, enum.IntEnum):
    r"""Texas Instruments TI-TXT tag."""

    DATA = 0
    r"""Data."""

    ADDRESS = 1
    r"""Address."""

    EOF = 2
    r"""End Of File."""

    _DATA = DATA

    def is_address(self) -> bool:
        r"""Tells whether this is an address record.

        This method returns true if this record tag is used for *address*
        records.

        Returns:
            bool: This is an address record tag.

        Examples:
            >>> from hexrec import TiTxtFile
            >>> TiTxtTag = TiTxtFile.Record.Tag
            >>> TiTxtTag.ADDRESS.is_address()
            True
            >>> TiTxtTag.DATA.is_address()
            False
        """

        return self == self.ADDRESS

    def is_data(self) -> bool:

        return self == self.DATA

    def is_eof(self) -> bool:
        r"""Tells whether this is an End Of File record.

        This method returns true if this record tag is used for *End Of File*
        records.

        Returns:
            bool: This is an End Of File record tag.

        Examples:
            >>> from hexrec import TiTxtFile
            >>> TiTxtTag = TiTxtFile.Record.Tag
            >>> TiTxtTag.EOF.is_eof()
            True
            >>> TiTxtTag.DATA.is_eof()
            False
        """

        return self == self.EOF

    def is_file_termination(self) -> bool:

        return self.is_eof()


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='TiTxtRecord')


class TiTxtRecord(BaseRecord):
    r"""Texas Instruments TI-TXT record object."""

    Tag: Type[TiTxtTag] = TiTxtTag

    LINE_REGEX = re.compile(
        b'^\\s*('
        b"(?P<data>([0-9A-Fa-f]{2}[ \\t]?)+)|"
        b'(@(?P<address>[0-9A-Fa-f]+))|'
        b'(?P<eof>q)'
        b')\\s*\\r?\\n?$'
    )
    r"""Line parser regex."""

    def compute_count(self) -> Optional[int]:

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
        addrlen: int = 4,
    ) -> Self:
        r"""Creates an address record.

        Args:
            address (int):
                Address value.

            addrlen (int):
                Address length, in *nibbles* (4-bit units).

        Returns:
            :class:`TiTxtRecord`: Address record object.

        Raises:
            ValueError: invalid parameter.

        Examples:
            >>> from hexrec import TiTxtFile
            >>> record = TiTxtFile.Record.create_address(0x1234)
            >>> str(record)
            '@1234\r\n'
        """

        record = cls(cls.Tag.ADDRESS, address=address, count=addrlen)
        return record

    @classmethod
    def create_data(
        cls,
        address: int,
        data: AnyBytes,
    ) -> Self:
        r"""Creates a data record.

        Args:
            address (int):
                Ignored; please provide zero.

            data (bytes):
                Record byte data.

        Returns:
            :class:`TiTxtRecord`: Data record object.

        Raises:
            ValueError: invalid parameter.

        Examples:
            >>> from hexrec import TiTxtFile
            >>> record = TiTxtFile.Record.create_data(0, b'abc')
            >>> str(record)
            '61 62 63\r\n'
        """

        record = cls(cls.Tag.DATA, data=data, address=address)
        return record

    @classmethod
    def create_eof(cls) -> Self:
        r"""Creates an End Of File record.

        Returns:
            :class:`TiTxtRecord`: End Of File record object.

        Raises:
            ValueError: invalid parameter.

        Examples:
            >>> from hexrec import TiTxtFile
            >>> record = TiTxtFile.Record.create_eof()
            >>> str(record)
            'q\r\n'
        """

        record = cls(cls.Tag.EOF)
        return record

    @classmethod
    def parse(
        cls,
        line: AnyBytes,
        address: int = 0,
        validate: bool = True,
    ) -> Self:
        r"""Parses a record from bytes.

        Args:
            line (bytes):
                String of bytes to parse.

            address (int):
                Default record address for *data* records.

            validate (bool):
                Perform validation checks.

        Returns:
            :class:`BaseRecord`: Parsed record.

        Raises:
            ValueError: Syntax error.

        Examples:
            >>> from hexrec import TiTxtFile
            >>> record = TiTxtFile.Record.parse(b'@ABCD\r\n')
            >>> record.tag
            <TiTxtTag.ADDRESS: 1>
            >>> record = TiTxtFile.Record.parse(b'61 62 63\r\n', address=123)
            >>> record.address, record.data
            (123, b'abc')
            >>> TiTxtFile.Record.parse(b':ABCD\r\n')
            Traceback (most recent call last):
                ...
            ValueError: syntax error
        """

        match = cls.LINE_REGEX.match(line)
        if not match:
            raise ValueError('syntax error')

        coords = match.span()
        groups = match.groupdict()
        groups_address = groups['address']
        groups_eof = groups['eof']
        groups_data = groups['data'] or b''

        Tag = cls.Tag
        count = None
        data = b''

        if groups_address:
            tag = Tag.ADDRESS
            address = int(groups_address, 16)
            count = len(groups_address)

        elif groups_eof:
            tag = Tag.EOF

        else:
            tag = Tag.DATA
            data = groups_data.translate(None, delete=b' \t')
            data = unhexlify(data)

        record = cls(tag,
                     address=address,
                     data=data,
                     count=count,
                     coords=coords,
                     validate=validate)
        return record

    def to_bytestr(
        self,
        end: AnyBytes = b'\r\n',
    ) -> bytes:
        r"""Converts into a byte string.

        Args:
            end (bytes):
                End of record termination bytes.

        Returns:
            bytes: Byte string representation.

        Examples:
            >>> from hexrec import TiTxtFile
            >>> record = TiTxtFile.Record.create_data(0, b'abc')
            >>> record.to_bytestr(end=b'\n')
            b'61 62 63\n'
        """

        self.validate(checksum=False, count=False)
        valstr = b''

        if self.tag == TiTxtTag.ADDRESS:
            count = self.count or 1
            mask = (1 << (4 * count)) - 1
            valstr = (b'@%%0%dX' % count) % (self.address & mask)

        elif self.tag == TiTxtTag.EOF:
            valstr = b'q'

        elif self.data:
            valstr = hexlify(self.data, b' ')

        bytestr = b'%s%s%s%s' % (self.before, valstr, self.after, end)
        return bytestr

    def to_tokens(
        self,
        end: AnyBytes = b'\r\n',
    ) -> Mapping[str, bytes]:
        r"""Converts into byte string tokens.

        Args:
            end (bytes):
                End of record termination bytes.

        Returns:
            bytes: Mapping of token keys to token byte strings.

        Examples:
            >>> from hexrec import TiTxtFile
            >>> record = TiTxtFile.Record.create_data(0, b'abc')
            >>> record.to_tokens(end=b'\n')  # doctest:+NORMALIZE_WHITESPACE
            {'before': b'', 'begin': b'', 'address': b'', 'data': b'61 62 63',
             'after': b'', 'end': b'\n'}
        """

        self.validate(checksum=False, count=False)
        tag = _cast(TiTxtTag, self.tag)
        addrstr = b''
        eofstr = b''
        datastr = b''

        if tag == tag.ADDRESS:
            count = self.count or 1
            mask = (1 << (4 * count)) - 1
            addrstr = (b'@%%0%dX' % count) % (self.address & mask)

        elif tag == tag.EOF:
            eofstr = b'q'

        elif self.data:
            datastr = hexlify(self.data, b' ')

        return {
            'before': self.before,
            'begin': eofstr,
            'address': addrstr,
            'data': datastr,
            'after': self.after,
            'end': end,
        }

    def validate(
        self,
        checksum: bool = True,
        count: bool = True,
    ) -> Self:

        super().validate(checksum=checksum, count=count)
        Tag = self.Tag
        tag = self.tag

        if self.after and not self.after.isspace():
            raise ValueError('junk after')

        if self.before and not self.before.isspace():
            raise ValueError('junk before')

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


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='TiTxtFile')


class TiTxtFile(BaseFile):
    r"""Texas Instruments TI-TXT file object."""

    FILE_EXT: Sequence[str] = ['.txt']

    Record: Type[TiTxtRecord] = TiTxtRecord

    @classmethod
    def parse(
        cls,
        stream: IO,
        ignore_errors: bool = False,
        ignore_after_termination: bool = True,
    ) -> Self:

        file = super().parse(stream, ignore_errors=ignore_errors,
                             ignore_after_termination=ignore_after_termination)
        last_data_endex = 0

        for record in file.records:
            tag = _cast(TiTxtTag, record.tag)

            if tag.is_data():
                record.address = last_data_endex
                last_data_endex += len(record.data)

            elif tag.is_address():
                last_data_endex = record.address

        return file

    def update_records(
        self,
        align: bool = False,
        addrlen: int = 4,
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

            addrlen (int):
                Address length, in *nibbles* (4-bit units).

        Returns:
            :class:`TiTxtFile`: *self*.

        Raises:
            ValueError: :attr:`memory` attribute not populated.

        See Also:
            :attr:`records`
            :attr:`memory`
            :meth:`get_meta`
            :meth:`apply_records`

        Examples:
            >>> from hexrec import TiTxtFile
            >>> blocks = [[456, b'abc']]
            >>> file = TiTxtFile.from_blocks(blocks, maxdatalen=8)
            >>> file.memory.to_blocks()
            [[456, b'abc']]
            >>> file.get_meta()
            {'maxdatalen': 8}
            >>> _ = file.update_records()
            >>> len(file.records)
            3
            >>> _ = file.print()
            @01C8
            61 62 63
            q
        """

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

                if chunk_start != last_data_endex:
                    record = Record.create_address(chunk_start, addrlen=addrlen)
                    records.append(record)

                record = Record.create_data(chunk_start, data)
                records.append(record)
                last_data_endex = chunk_start + len(chunk_view)

        finally:
            for chunk_view in chunk_views:
                chunk_view.release()

        record = Record.create_eof()
        records.append(record)

        self.discard_records()
        self._records = records
        return self

    def validate_records(
        self,
        data_ordering: bool = False,
        address_even: bool = True,
    ) -> Self:
        r"""Validates records.

        It performs consistency checks for the underlying :attr:`records`.

        Args:
            data_ordering (bool):
                Checks that the *data* record sequence has monotonically
                increasing addresses, without any overlapping.

            address_even (bool):
                Addresses must be even.

        Returns:
            :class:`TiTxtFile`: *self*.

        Raises:
            ValueError: Invalid record sequence.

        Examples:
            >>> from hexrec import TiTxtFile
            >>> records = [TiTxtFile.Record.create_data(456, b'abc')]
            >>> file = TiTxtFile.from_records(records)
            >>> _ = file.validate_records()
            Traceback (most recent call last):
                ...
            ValueError: missing end of file record
        """

        records = self._records
        if records is None:
            raise ValueError('records required')

        Tag = self.Record.Tag
        last_data_endex = 0
        eof_record = None

        for index, record in enumerate(records):
            record.validate()
            tag = record.tag

            if tag == Tag.ADDRESS:
                if address_even:
                    if record.address & 1:
                        raise ValueError('address not even')

                if data_ordering:
                    if record.address < last_data_endex:
                        raise ValueError('unordered data record')
                last_data_endex = record.address

            elif tag == Tag.EOF:
                if index != len(records) - 1:
                    raise ValueError('end of file record not last')
                eof_record = record

            else:  # elif tag == Tag.DATA:
                last_data_endex += len(record.data)

        if eof_record is None:
            raise ValueError('missing end of file record')

        return self


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
