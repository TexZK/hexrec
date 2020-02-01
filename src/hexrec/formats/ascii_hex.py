# -*- coding: utf-8 -*-

# Copyright (c) 2013-2020, Andrea Zoppi
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
    `<http://srecord.sourceforge.net/man/man5/srec_ascii_hex.html>`_
"""

import io
import re
from typing import IO
from typing import Any
from typing import Iterator
from typing import Optional
from typing import Type
from typing import Union

from ..records import Record as _Record
from ..records import RecordSequence
from ..records import Tag
from ..utils import AnyBytes
from ..utils import check_empty_args_kwargs
from ..utils import chop
from ..utils import hexlify
from ..utils import unhexlify


class Record(_Record):
    r"""ASCII-hex record.

    Attributes:
        address (int):
            Tells where its `data` starts in the memory addressing space,
            or an address with a special meaning.

        tag (int):
            Defines the logical meaning of the `address` and `data` fields.

        data (bytes):
            Byte data as required by the `tag`.

        count (int):
            Counts its fields as required by the :class:`Record` subclass
            implementation.

        checksum (int):
            Computes the checksum as required by most :class:`Record`
            implementations.

    Arguments:
        address (int):
            Record `address` field.

        tag (int):
            Record `tag` field.

        data (bytes):
            Record `data` field.

        checksum (int):
            Record `checksum` field.
            ``Ellipsis`` makes the constructor compute its actual value
            automatically.
            ``None`` assigns ``None``.
    """

    TAG_TYPE: Optional[Type[Tag]] = None
    r"""Associated Python class for tags."""

    REGEX = re.compile(r"^(\$A(?P<address>[0-9A-Fa-f]{4})[,.][ %',]?)?"
                       r"(?P<data>([0-9A-Fa-f]{2}[ %',])*([0-9A-Fa-f]{2})?)"
                       r"(\$S(?P<checksum>[0-9A-Fa-f]{4})[,.][ %',]?)?$")
    r"""Regular expression for parsing a record text line."""

    def __init__(
        self: 'Record',
        address: Optional[int],
        tag: Optional[Tag],
        data: Optional[AnyBytes],
        checksum: Union[int, type(Ellipsis)] = None,
    ) -> None:
        super().__init__(address, tag, data, checksum)

    def __repr__(
        self: 'Record',
    ) -> str:
        address, data, checksum = None, None, None

        if self.address is not None:
            address = f'0x{self.address:04X}'

        if self.data is not None:
            data = f'{self.data!r}'

        if self.checksum is not None:
            checksum = f'0x{(self._get_checksum() or 0):04X}'

        text = (f'{type(self).__name__}('
                f'address={address}, '
                f'tag={self.tag!r}, '
                f'count={self.count:d}, '
                f'data={data}, '
                f'checksum={checksum}'
                f')')
        return text

    def __str__(
        self: 'Record',
    ) -> str:
        address, data, checksum = '', '', ''

        if self.address is not None:
            address = f'$A{self.address:04X},'

        if self.data:
            data = f'{hexlify(self.data, sep=" ")} '

        if self.checksum is not None:
            checksum = f'$S{self._get_checksum():04X},'

        text = ''.join([address, data, checksum])
        return text

    def is_data(
        self: 'Record',
    ) -> bool:
        return self.data is not None

    def compute_checksum(
        self: 'Record',
    ) -> Optional[int]:
        checksum = sum(self.data or b'') & 0xFFFF
        return checksum

    def check(
        self: 'Record',
    ) -> None:
        if self.address is not None and not 0 <= self.address < (1 << 16):
            raise ValueError('address overflow')

        if self.tag is not None:
            raise ValueError('wrong tag')

        if not 0 <= self.count < (1 << 16):
            raise ValueError('count overflow')

        if self.count != len(self.data or b''):
            raise ValueError('count error')

        if self.checksum is not None:
            if not 0 <= self.checksum < (1 << 16):
                raise ValueError('checksum overflow')

    @classmethod
    def build_data(
        cls: Type['Record'],
        address: Optional[int],
        data: Optional[AnyBytes],
    ) -> 'Record':
        r"""Builds a data record.

        Arguments:
            address (int):
                Record address, or ``None``.

            data (bytes):
                Record data, or ``None``.

        Returns:
            record: A data record.

        Examples:
            >>> Record.build_data(0x1234, b'Hello, World!')
            ... #doctest: +NORMALIZE_WHITESPACE
            Record(address=0x1234, tag=None, count=13,
                   data=b'Hello, World!', checksum=None)

            >>> Record.build_data(None, b'Hello, World!')
            ... #doctest: +NORMALIZE_WHITESPACE
            Record(address=None, tag=None, count=13,
                   data=b'Hello, World!', checksum=None)

            >>> Record.build_data(0x1234, None)
            ... #doctest: +NORMALIZE_WHITESPACE
            Record(address=0x1234, tag=None, count=0, data=None, checksum=None)
        """
        record = cls(address, None, data)
        return record

    @classmethod
    def split(
        cls: Type['Record'],
        data: AnyBytes,
        address: int = 0,
        columns: int = 16,
        align: Union[int, type(Ellipsis)] = Ellipsis,
        standalone: bool = True,
    ) -> Iterator['Record']:
        r"""Splits a chunk of data into records.

        Arguments:
            data (bytes):
                Byte data to split.

            address (int):
                Start address of the first data record being split.

            columns (int):
                Maximum number of columns per data record.
                If ``None``, the whole `data` is put into a single record.
                Maximum of 128 columns.

            align (int):
                Aligns record addresses to such number.
                If ``Ellipsis``, its value is resolved after `columns`.

            standalone (bool):
                Generates a sequence of records that can be saved as a
                standalone record file.

        Yields:
            record: Data split into records.

        Raises:
            :obj:`ValueError`: Address, size, or column overflow.
        """
        if not 0 <= address < (1 << 16):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 16):
            raise ValueError('size overflow')
        if not 0 < columns < (1 << 8):
            raise ValueError('column overflow')
        if align is Ellipsis:
            align = columns

        align_base = (address % align) if align else 0
        offset = address
        checksum = 0

        if standalone:
            record = cls.build_data(offset, None)
            yield record

        for chunk in chop(data, columns, align_base):
            if standalone:
                record = cls.build_data(None, chunk)
            else:
                record = cls.build_data(offset, chunk)
            yield record
            checksum = (checksum + record.compute_checksum()) & 0xFFFF
            offset += len(chunk)

        if standalone:
            record = cls(None, None, None, checksum)
            yield record

    @classmethod
    def parse_record(
        cls: Type['Record'],
        line: str,
        *args: Any,
        **kwargs: Any,
    ) -> 'Record':
        check_empty_args_kwargs(args, kwargs)

        line = str(line).strip()
        match = cls.REGEX.match(line)
        if not match:
            raise ValueError('regex error')
        groups = match.groupdict()

        address = groups['address']
        if address is not None:
            address = int(address, 16)

        data = groups['data']
        if data:
            for c in " %',":
                data = data.replace(c, '')
            data = unhexlify(data)
        else:
            data = None

        checksum = groups['checksum']
        if checksum is not None:
            checksum = int(checksum, 16)

        record = cls(address, None, data, checksum)
        return record

    @classmethod
    def build_standalone(
        cls: Type['Record'],
        data_records: RecordSequence,
        *args: Any,
        **kwargs: Any,
    ) -> Iterator['Record']:
        check_empty_args_kwargs(args, kwargs)

        checksum = 0
        for record in data_records:
            yield record
            checksum = (checksum + record.compute_checksum()) & 0xFFFF

        record = cls(None, None, None, checksum)
        yield record

    @classmethod
    def readdress(
        cls: Type['Record'],
        records: RecordSequence,
    ) -> None:
        offset = 0
        for record in records:
            if record.address is None:
                record.address = offset
            offset = record.address + len(record.data or b'')

    @classmethod
    def read_records(
        cls: Type['Record'],
        stream: IO,
    ) -> RecordSequence:
        text = stream.read()
        stx = text.index('\x02')
        etx = text.index('\x03')
        text = text[(stx + 1):etx]
        return super().read_records(io.StringIO(text))

    @classmethod
    def write_records(
        cls: Type['Record'],
        stream: IO,
        records: RecordSequence,
    ) -> None:
        stream.write('\x02')
        super().write_records(stream, records)
        stream.write('\x03')
