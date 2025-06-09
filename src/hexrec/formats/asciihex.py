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

r"""ASCII-hex format.

See Also:
    `<https://srecord.sourceforge.net/man/man5/srec_ascii_hex.5.html>`_
"""

import enum
import re
from typing import IO
from typing import Any
from typing import Mapping
from typing import Optional
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
        r"""Tells whether this is an address record.

        This method returns true if this record tag is used for *address*
        records.

        Returns:
            bool: This is an address record tag.

        Examples:
            >>> from hexrec import AsciiHexFile
            >>> AsciiHexTag = AsciiHexFile.Record.Tag
            >>> AsciiHexTag.ADDRESS.is_address()
            True
            >>> AsciiHexTag.DATA.is_address()
            False
        """

        return self == self.ADDRESS

    def is_checksum(self) -> bool:
        r"""Tells whether this is a checksum record.

        This method returns true if this record tag is used for *checksum*
        records.

        Returns:
            bool: This is a checksum record tag.

        Examples:
            >>> from hexrec import AsciiHexFile
            >>> AsciiHexTag = AsciiHexFile.Record.Tag
            >>> AsciiHexTag.CHECKSUM.is_checksum()
            True
            >>> AsciiHexTag.DATA.is_checksum()
            False
        """

        return self == self.CHECKSUM

    def is_data(self) -> bool:

        return self == self.DATA

    def is_file_termination(self) -> bool:

        return super().is_file_termination()


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='AsciiHexRecord')


class AsciiHexRecord(BaseRecord):
    r"""ASCII-HEX record object."""

    Tag: Type[AsciiHexTag] = AsciiHexTag

    LINE_REGEX = re.compile(
        b'\\s*('
        b"(?P<data>([0-9A-Fa-f]{2}[ \t\v\f\r%',]?)+)|"
        b'(\\$[Aa](?P<address>[0-9A-Fa-f]+)[,.])|'
        b'(\\$[Ss](?P<checksum>[0-9A-Fa-f]+)[,.])'
        b')\\s*'
    )
    r"""Line parser regex."""

    DATA_EXECHARS: bytes = b" \t\v\f\r%',"
    r"""Supported execution characters."""

    def compute_checksum(self) -> Optional[int]:

        Tag = self.Tag
        tag = self.tag

        if tag == Tag.CHECKSUM:
            return self.checksum  # loopback
        else:
            return None  # not supported

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
        addrlen: int = 8,
    ) -> Self:
        r"""Creates an address record.

        Args:
            address (int):
                Address value.

            addrlen (int):
                Address length, in *nibbles* (4-bit units).

        Returns:
            :class:`AsciiHexRecord`: Address record object.

        Raises:
            ValueError: invalid parameter.

        Examples:
            >>> from hexrec import AsciiHexFile
            >>> record = AsciiHexFile.Record.create_address(0x1234, addrlen=4)
            >>> str(record)
            '$A1234,\r\n'
        """

        record = cls(cls.Tag.ADDRESS, address=address, count=addrlen)
        return record

    @classmethod
    def create_checksum(
        cls,
        checksum: int,
    ) -> Self:
        r"""Creates a checksum record.

        Args:
            checksum (int):
                16-bit checksum value.

        Returns:
            :class:`AsciiHexRecord`: Checksum record object.

        Raises:
            ValueError: invalid parameter.

        Examples:
            >>> from hexrec import AsciiHexFile
            >>> record = AsciiHexFile.Record.create_checksum(0x1234)
            >>> str(record)
            '$S1234,\r\n'
        """

        record = cls(cls.Tag.CHECKSUM, checksum=checksum)
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
            :class:`AsciiHexRecord`: Data record object.

        Raises:
            ValueError: invalid parameter.

        Examples:
            >>> from hexrec import AsciiHexFile
            >>> record = AsciiHexFile.Record.create_data(0, b'abc')
            >>> str(record)
            '61 62 63 \r\n'
        """

        record = cls(cls.Tag.DATA, data=data, address=address)
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
            >>> from hexrec import AsciiHexFile
            >>> record = AsciiHexFile.Record.parse(b'$A1234,\r\n')
            >>> record.tag
            <AsciiHexTag.ADDRESS: 1>
            >>> record = AsciiHexFile.Record.parse(b'61 62 63\r\n', address=123)
            >>> record.address, record.data
            (123, b'abc')
            >>> AsciiHexFile.Record.parse(b'@ABCD\r\n')
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
            data = unhexlify(data)

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
        r"""Converts into a byte string.

        Args:
            exechar (byte):
                *Execution character* value.

            exelast (bool):
                Append *execution character* also to the last byte of the
                serialized record.

            dollarend (byte):
                End character of *dollar* records (i.e. *address* and
                *checksum* records).

            end (bytes):
                End of record termination bytes.

        Returns:
            bytes: Byte string representation.

        Examples:
            >>> from hexrec import AsciiHexFile
            >>> record = AsciiHexFile.Record.create_data(0, b'abc')
            >>> record.to_bytestr(exechar=b"'", exelast=False, end=b'\n')
            b'61.62.63\n'
            >>> record = AsciiHexFile.Record.create_address(0x1234)
            >>> record.to_bytestr(dollarend=b'.')
            b'$A00001234.\r\n'
        """

        self.validate(checksum=False, count=False)
        valstr = b''

        if self.tag == AsciiHexTag.ADDRESS:
            count = self.count or 1
            mask = (1 << (4 * count)) - 1
            valstr = (b'$A%%0%dX%s' % (count, dollarend)) % (self.address & mask)

        elif self.tag == AsciiHexTag.CHECKSUM:
            valstr = b'$S%04X%s' % ((self.checksum & 0xFFFF), dollarend)

        elif self.data:
            valstr = hexlify(self.data, exechar)
            if exelast:
                valstr += exechar

        bytestr = b'%s%s%s%s' % (self.before, valstr, self.after, end)
        return bytestr

    def to_tokens(
        self,
        exechar: bytes = b' ',
        exelast: bool = True,
        dollarend: AnyBytes = b',',
        end: AnyBytes = b'\r\n',
    ) -> Mapping[str, bytes]:
        r"""Converts into byte string tokens.

        Args:
            exechar (byte):
                *Execution character* value.

            exelast (bool):
                Append *execution character* also to the last byte of the
                serialized record.

            dollarend (byte):
                End character of *dollar* records (i.e. *address* and
                *checksum* records).

            end (bytes):
                End of record termination bytes.

        Returns:
            bytes: Mapping of token keys to token byte strings.

        Examples:
            >>> from hexrec import AsciiHexFile
            >>> record = AsciiHexFile.Record.create_data(0, b'abc')
            >>> record.to_tokens(exechar=b"'", exelast=False, end=b'\n')  # doctest:+NORMALIZE_WHITESPACE
            {'before': b'', 'address': b'', 'data': b"61'62'63",
             'checksum': b'', 'after': b'', 'end': b'\n'}
            >>> record = AsciiHexFile.Record.create_address(0x1234)
            >>> record.to_tokens(dollarend=b'.')  # doctest:+NORMALIZE_WHITESPACE
            {'before': b'', 'address': b'$A00001234.', 'data': b'',
             'checksum': b'', 'after': b'', 'end': b'\r\n'}
        """

        self.validate(checksum=False, count=False)
        tag = _cast(AsciiHexTag, self.tag)
        addrstr = b''
        chksstr = b''
        datastr = b''

        if tag == tag.ADDRESS:
            count = self.count or 1
            mask = (1 << (4 * count)) - 1
            addrstr = (b'$A%%0%dX%s' % (count, dollarend)) % (self.address & mask)

        elif tag == tag.CHECKSUM:
            chksstr = b'$S%04X%s' % ((self.checksum & 0xFFFF), dollarend)

        elif self.data:
            datastr = hexlify(self.data, exechar)
            if exelast:
                datastr += exechar

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
    ) -> Self:

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


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='AsciiHexFile')


class AsciiHexFile(BaseFile):
    r"""ASCII-HEX file object."""

    Record: Type[AsciiHexRecord] = AsciiHexRecord

    @classmethod
    def parse(
        cls,
        stream: IO,
        ignore_errors: bool = False,
        stxetx: bool = True,
    ) -> Self:
        r"""Parses records from a byte stream.

        It executes :meth:`AsciiHexRecord.parse` for each line of the incoming
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
                Ignore :class:`Exception` raised by
                :meth:`AsciiHexRecord.parse`.

            stxetx (bool):
                Require record data be enclosed within ASCII ``STX`` and
                ``ETX`` bytes.

        Returns:
            :class:`AsciiHexFile`: *self*.

        See Also:
            :meth:`parse`
            :meth:`AsciiHexRecord.parse`
            :meth:`from_records`
            :meth:`_is_empty_line`

        Examples:
            >>> from hexrec import AsciiHexFile
            >>> buffer = b'''
            ...     \x02
            ...     $A1234,
            ...     61 62 63
            ...     \x03
            ... '''
            >>> import io
            >>> stream = io.BytesIO(buffer)
            >>> file = AsciiHexFile.parse(stream)
            >>> file.memory.to_blocks()
            [[4660, b'abc']]
            >>> file.get_meta()
            {'maxdatalen': 3}
        """

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
        exechar: bytes = b' ',
        exelast: bool = True,
        dollarend: AnyBytes = b',',
        end: AnyBytes = b'\r\n',
        stxetx: bool = True,
    ) -> 'BaseFile':
        r"""Serializes records onto a byte stream.

        It executes :meth:`MosRecord.serialize` for each of the stored
        :attr:`records`.

        Args:
            stream (bytes IO):
                Stream to serialize records onto.

            exechar (byte):
                *Execution character* value.

            exelast (bool):
                Append *execution character* also to the last byte of the
                serialized record.

            dollarend (byte):
                End character of *dollar* records (i.e. *address* and
                *checksum* records).

            end (bytes):
                End of record termination bytes.

            stxetx (bool):
                Enclose the whole serialized file within ASCII ``STX`` and
                ``ETX`` bytes.

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

        if stxetx:
            stream.write(b'\x02')

        for record in self.records:
            record.serialize(stream, exechar=exechar, exelast=exelast,
                             dollarend=dollarend, end=end)

        if stxetx:
            stream.write(b'\x03')

        return self

    def update_records(
        self,
        align: bool = False,
        checksum: bool = False,
        addrlen: int = 8,
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

            checksum (bool):
                Generate a final *checksum* record.

            addrlen (int):
                Address length, in *nibbles* (4-bit units).

        Returns:
            :class:`AsciiHexFile`: *self*.

        Raises:
            ValueError: :attr:`memory` attribute not populated.

        See Also:
            :attr:`records`
            :attr:`memory`
            :meth:`get_meta`
            :meth:`apply_records`

        Examples:
            >>> from hexrec import AsciiHexFile
            >>> blocks = [[123, b'abc']]
            >>> file = AsciiHexFile.from_blocks(blocks, maxdatalen=16)
            >>> file.memory.to_blocks()
            [[123, b'abc']]
            >>> file.get_meta()
            {'maxdatalen': 16}
            >>> _ = file.update_records()
            >>> len(file.records)
            2
            >>> _ = file.print(exelast=False)
            $A0000007B,
            61 62 63
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
    ) -> Self:
        r"""Validates records.

        It performs consistency checks for the underlying :attr:`records`.

        Args:
            data_ordering (bool):
                Checks that the *data* record sequence has monotonically
                increasing addresses, without any overlapping.

            checksum_values (bool):
                Checks for valid *checksum* values.

        Returns:
            :class:`AsciiHexFile`: *self*.

        Raises:
            ValueError: Invalid record sequence.

        Examples:
            >>> from hexrec import AsciiHexFile
            >>> records = [AsciiHexFile.Record.create_data(123, b'abc'),
            ...            AsciiHexFile.Record.create_checksum(0xFFFF)]
            >>> file = AsciiHexFile.from_records(records)
            >>> file.validate_records()
            Traceback (most recent call last):
                ...
            ValueError: wrong checksum
        """

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


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
