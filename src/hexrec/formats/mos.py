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

r"""MOS Technology format.

See Also:
    `<http://srecord.sourceforge.net/man/man5/srec_mos_tech.html>`_
"""

import re
from typing import Any
from typing import Iterator
from typing import Optional
from typing import Sequence
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
    r"""MOS Technology record.

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

    REGEX = re.compile(r'^;(?P<count>[0-9A-Fa-f]{2})'
                       r'(?P<address>[0-9A-Fa-f]{4})'
                       r'(?P<data>([0-9A-Fa-f]{2}){,255})'
                       r'(?P<checksum>[0-9A-Fa-f]{4})$')
    r"""Regular expression for parsing a record text line."""

    EXTENSIONS: Sequence[str] = ('.mos',)
    r"""File extensions typically mapped to this record type."""

    def __init__(
        self: 'Record',
        address: int,
        tag: Optional[Tag],
        data: AnyBytes,
        checksum: Union[int, type(Ellipsis)] = Ellipsis,
    ) -> None:
        super().__init__(address, tag, data, checksum)

    def __repr__(
        self: 'Record',
    ) -> str:
        text = (f'{type(self).__name__}('
                f'address=0x{self.address:04X}, '
                f'tag={self.tag!r}, '
                f'count={self.count:d}, '
                f'data={self.data!r}, '
                f'checksum=0x{(self._get_checksum() or 0):04X}'
                f')')
        return text

    def __str__(
        self: 'Record',
    ) -> str:
        text = (f';'
                f'{self.count:02X}'
                f'{self.address:04X}'
                f'{hexlify(self.data)}'
                f'{self._get_checksum():04X}')
        return text

    def is_data(
        self: 'Record',
    ) -> bool:
        return self.count > 0

    def compute_checksum(
        self: 'Record',
    ) -> int:
        if self.count:
            checksum = (self.count +
                        (self.address >> 16) +
                        (self.address & 0xFF) +
                        sum(self.data)) & 0xFFFF
        else:
            checksum = self.address
        return checksum

    def check(
        self: 'Record',
    ) -> None:
        if not 0 <= self.address < (1 << 16):
            raise ValueError('address overflow')

        if self.tag is not None:
            raise ValueError('wrong tag')

        if not 0 <= self.count < (1 << 8):
            raise ValueError('count overflow')

        if self.data is None:
            raise ValueError('no data')

        if self.count != len(self.data):
            raise ValueError('count error')

        if self.checksum is not None:
            if not 0 <= self.checksum < (1 << 16):
                raise ValueError('checksum overflow')

            if self.checksum != self.compute_checksum():
                raise ValueError('checksum error')

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
            >>> Record.build_data(0x1234, b'Hello, World!')
            ... #doctest: +NORMALIZE_WHITESPACE
            Record(address=0x1234, tag=None, count=13,
                   data=b'Hello, World!', checksum=0x04AA)
        """
        record = cls(address, None, data)
        return record

    @classmethod
    def build_terminator(
        cls: Type['Record'],
        record_count: int,
    ) -> 'Record':
        r"""Builds a terminator record.

        The terminator record holds the number of data records in the
        `address` fields.
        Also the `checksum` field is actually set to the record count.

        Arguments:
            record_count (int):
                Number of previous records.

        Returns:
            record: A terminator record.

        Example:
            >>> Record.build_data(0x1234, b'Hello, World!')
            ... #doctest: +NORMALIZE_WHITESPACE
            Record(address=0x00001234, tag=0, count=13,
                   data=b'Hello, World!', checksum=0x69)
        """
        record = cls(record_count, None, b'', record_count)
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
        record_count = 0

        for chunk in chop(data, columns, align_base):
            record_count += 1
            yield cls.build_data(offset, chunk)
            offset += len(chunk)

        if standalone:
            yield cls.build_terminator(record_count)

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
        count = int(groups['count'], 16)
        data = unhexlify(groups['data'] or '')
        checksum = int(groups['checksum'], 16)

        if count != len(data):
            raise ValueError('count error')

        record = cls(address, None, data, checksum)
        return record

    @classmethod
    def build_standalone(
        cls: Type['Record'],
        data_records: RecordSequence,
        *args: Any,
        **kwargs: Any,
    ) -> Iterator['Record']:
        r"""Makes a sequence of data records standalone.

        Arguments:
            data_records (list of records):
                A sequence of data records.

        Yields:
            record: Records for a standalone record file.
        """
        check_empty_args_kwargs(args, kwargs)

        record_count = 0
        for record in data_records:
            record_count += 1
            yield record

        yield cls.build_terminator(record_count)

    @classmethod
    def check_sequence(
        cls: Type['Record'],
        records: RecordSequence,
    ) -> None:
        super().check_sequence(records)

        if len(records) < 1:
            raise ValueError('missing terminator')

        record_count = len(records) - 1
        record = records[-1]

        if record.address != record_count or record.checksum != record_count:
            raise ValueError('wrong terminator')
