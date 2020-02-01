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

r"""Tektronix extended HEX format.

See Also:
    `<https://en.wikipedia.org/wiki/Tektronix_extended_HEX>`_
"""

import enum
import re
from typing import Any
from typing import Iterator
from typing import Optional
from typing import Sequence
from typing import Type
from typing import Union

from ..records import Record as _Record
from ..records import RecordSequence
from ..records import Tag as _Tag
from ..utils import AnyBytes
from ..utils import check_empty_args_kwargs
from ..utils import chop
from ..utils import hexlify
from ..utils import sum_bytes
from ..utils import unhexlify


@enum.unique
class Tag(_Tag):
    DATA = 6
    TERMINATOR = 8

    @classmethod
    def is_data(
        cls: Type['Tag'],
        value: Union[int, 'Tag'],
    ) -> bool:
        r"""bool: `value` is a data record tag."""
        return value == cls.DATA


class Record(_Record):
    r"""Tektronix extended HEX record.

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

    TAG_TYPE: Optional[Type[Tag]] = Tag
    r"""Associated Python class for tags."""

    REGEX = re.compile(r'^%(?P<count>[0-9A-Fa-f]{2})'
                       r'(?P<tag>[68])'
                       r'(?P<checksum>[0-9A-Fa-f]{2})'
                       r'8(?P<address>[0-9A-Fa-f]{8})'
                       r'(?P<data>([0-9A-Fa-f]{2}){,255})$')
    r"""Regular expression for parsing a record text line."""

    EXTENSIONS: Sequence[str] = ('.tek',)
    r"""File extensions typically mapped to this record type."""

    def __init__(
        self: 'Record',
        address: int,
        tag: Tag,
        data: AnyBytes,
        checksum: Union[int, type(Ellipsis)] = Ellipsis,
    ) -> None:
        super().__init__(address, self.TAG_TYPE(tag), data, checksum)

    def __str__(
        self: 'Record',
    ) -> str:
        self.check()
        text = (f'%'
                f'{self.count:02X}'
                f'{self.tag:01X}'
                f'{self._get_checksum():02X}'
                f'8'
                f'{self.address:08X}'
                f'{hexlify(self.data)}')
        return text

    def compute_count(
        self: 'Record',
    ) -> int:
        count = 9 + (len(self.data) * 2)
        return count

    def compute_checksum(
        self: 'Record',
    ) -> int:
        text = (f'{self.count:02X}'
                f'{self.tag:01X}'
                f'8'
                f'{self.address:08X}'
                f'{hexlify(self.data)}')
        checksum = sum_bytes(int(c, 16) for c in text) & 0xFF
        return checksum

    def check(
        self: 'Record',
    ) -> None:
        super().check()
        tag = self.TAG_TYPE(self.tag)

        if tag == self.TAG_TYPE.TERMINATOR and self.data:
            raise ValueError('invalid data')

        if self.count != self.compute_count():
            raise ValueError('count error')

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

        address = int(groups['address'], 16)
        tag = cls.TAG_TYPE(int(groups['tag'], 16))
        count = int(groups['count'], 16)
        data = unhexlify(groups['data'] or '')
        checksum = int(groups['checksum'], 16)

        if count != 9 + (len(data) * 2):
            raise ValueError('count error')

        record = cls(address, tag, data, checksum)
        return record

    @classmethod
    def build_data(
        cls: Type['Record'],
        address: int,
        data: AnyBytes,
    ) -> 'Record':
        r"""Builds a data record.

        Arguments:
            address (int):
                Record address.

            data (bytes):
                Record data.

        Returns:
            record: Data record.

        Example:
            >>> str(Record.build_data(0x12345678, b'Hello, World!'))
            '%236E081234567848656C6C6F2C20576F726C6421'
        """
        record = cls(address, cls.TAG_TYPE.DATA, data)
        return record

    @classmethod
    def build_terminator(
        cls: Type['Record'],
        start: int,
    ) -> 'Record':
        r"""Builds a terminator record.

        Arguments:
            start (int):
                Program start address.

        Returns:
            record: Terminator record.

        Example:
            >>> str(Record.build_terminator(0x12345678))
            '%0983D812345678'
        """
        record = cls(start, cls.TAG_TYPE.TERMINATOR, b'')
        return record

    @classmethod
    def split(
        cls: Type['Record'],
        data: AnyBytes,
        address: int = 0,
        columns: int = 16,
        align: Union[int, type(Ellipsis)] = Ellipsis,
        standalone: bool = True,
        start: Optional[int] = None,
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

            start (int):
                Program start address.
                If ``None``, it is assigned the minimum data record address.

        Yields:
            record: Data split into records.

        Raises:
            :obj:`ValueError`: Address, size, or column overflow.
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        if not 0 < columns < 128:
            raise ValueError('column overflow')
        if align is Ellipsis:
            align = columns

        align_base = (address % align) if align else 0
        offset = address

        for chunk in chop(data, columns, align_base):
            yield cls.build_data(offset, chunk)
            offset += len(chunk)

        if standalone:
            yield cls.build_terminator(address if start is None else start)

    @classmethod
    def build_standalone(
        cls: Type['Record'],
        data_records: RecordSequence,
        *args: Any,
        start: Optional[int] = None,
        **kwargs: Any,
    ) -> Iterator['Record']:
        r"""Makes a sequence of data records standalone.

        Arguments:
            data_records (list of record):
                A sequence of data records.

            start (int):
                Program start address.
                If ``None``, it is assigned the minimum data record address.

        Yields:
            record: Records for a standalone record file.
        """
        check_empty_args_kwargs(args, kwargs)

        for record in data_records:
            yield record

        if start is None:
            if not data_records:
                data_records = [cls.build_data(0, b'')]
            start = min(record.address for record in data_records)

        yield cls.build_terminator(start)

    @classmethod
    def check_sequence(
        cls: Type['Record'],
        records: RecordSequence,
    ) -> None:
        super().check_sequence(records)

        if len(records) < 1:
            raise ValueError('missing terminator')

        for i in range(len(records) - 1):
            record = records[i]
            if record.tag != cls.TAG_TYPE.DATA:
                raise ValueError('tag error')

        record = records[-1]
        if record.tag != cls.TAG_TYPE.TERMINATOR:
            raise ValueError('missing terminator')
