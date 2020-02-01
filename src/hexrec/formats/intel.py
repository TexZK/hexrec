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

r"""Intel HEX format.

See Also:
    `<https://en.wikipedia.org/wiki/Intel_HEX>`_
"""

import enum
import re
import struct
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
    r"""Intel HEX tag."""

    DATA = 0
    r"""Binary data."""

    END_OF_FILE = 1
    r"""End of file."""

    EXTENDED_SEGMENT_ADDRESS = 2
    r"""Extended segment address."""

    START_SEGMENT_ADDRESS = 3
    r"""Start segment address."""

    EXTENDED_LINEAR_ADDRESS = 4
    r"""Extended linear address."""

    START_LINEAR_ADDRESS = 5
    r"""Start linear address."""

    @classmethod
    def is_data(
        cls: Type['Tag'],
        value: Union[int, 'Tag'],
    ) -> bool:
        r"""bool: `value` is a data record tag."""
        return value == cls.DATA


class Record(_Record):
    r"""Intel HEX record.

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

    REGEX = re.compile(r'^:(?P<count>[0-9A-Fa-f]{2})'
                       r'(?P<offset>[0-9A-Fa-f]{4})'
                       r'(?P<tag>[0-9A-Fa-f]{2})'
                       r'(?P<data>([0-9A-Fa-f]{2}){,255})'
                       r'(?P<checksum>[0-9A-Fa-f]{2})$')
    r"""Regular expression for parsing a record text line."""

    EXTENSIONS: Sequence[str] = ('.hex', '.ihex', '.mcs')
    r"""Automatically supported file extensions."""

    def __init__(
        self: 'Record',
        address: int,
        tag: 'Tag',
        data: AnyBytes,
        checksum: Union[int, type(Ellipsis)] = Ellipsis,
    ) -> None:
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        super().__init__(address, self.TAG_TYPE(tag), data, checksum)

    def __str__(
        self: 'Record',
    ) -> str:
        self.check()
        data = self.data or b''
        text = (f':{len(data):02X}'
                f'{((self.address or 0) & 0xFFFF):04X}'
                f'{self.tag:02X}'
                f'{hexlify(data)}'
                f'{self._get_checksum():02X}')
        return text

    def compute_count(
        self: 'Record',
    ) -> int:
        return len(self.data)

    def compute_checksum(
        self: 'Record',
    ) -> int:
        offset = (self.address or 0) & 0xFFFF

        checksum = (self.count +
                    sum_bytes(struct.pack('H', offset)) +
                    self.tag +
                    sum_bytes(self.data))

        checksum = (0x100 - int(checksum & 0xFF)) & 0xFF
        return checksum

    def check(
        self: 'Record',
    ) -> None:
        super().check()

        if self.count != self.compute_count():
            raise ValueError('count error')

        self.TAG_TYPE(self.tag)
        # TODO: check values

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
            >>> str(Record.build_data(0x1234, b'Hello, World!'))
            ':0D12340048656C6C6F2C20576F726C642144'
        """
        record = cls(address, cls.TAG_TYPE.DATA, data)
        return record

    @classmethod
    def build_extended_segment_address(
        cls: Type['Record'],
        address: int,
    ) -> 'Record':
        r"""Builds an extended segment address record.

        Arguments:
            address (int):
                Extended segment address.
                The 20 least significant bits are ignored.

        Returns:
            record: Extended segment address record.

        Example:
            >>> str(Record.build_extended_segment_address(0x12345678))
            ':020000020123D8'
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        segment = address >> (16 + 4)
        tag = cls.TAG_TYPE.EXTENDED_SEGMENT_ADDRESS
        record = cls(0, tag, struct.pack('>H', segment))
        return record

    @classmethod
    def build_start_segment_address(
        cls: Type['Record'],
        address: int,
    ) -> 'Record':
        r"""Builds an start segment address record.

        Arguments:
            address (int):
                Start segment address.

        Returns:
            record: Start segment address record.

        Raises:
            :obj:`ValueError`: Address overflow.

        Example:
            >>> str(Record.build_start_segment_address(0x12345678))
            ':0400000312345678E5'
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')

        tag = cls.TAG_TYPE.START_SEGMENT_ADDRESS
        record = cls(0, tag, struct.pack('>L', address))
        return record

    @classmethod
    def build_end_of_file(
        cls: Type['Record'],
    ) -> 'Record':
        r"""Builds an end-of-file record.

        Returns:
            record: End-of-file record.

        Example:
            >>> str(Record.build_end_of_file())
            ':00000001FF'
        """
        tag = cls.TAG_TYPE.END_OF_FILE
        return cls(0, tag, b'')

    @classmethod
    def build_extended_linear_address(
        cls: Type['Record'],
        address: int,
    ) -> 'Record':
        r"""Builds an extended linear address record.

        Arguments:
            address (int):
                Extended linear address.
                The 16 least significant bits are ignored.

        Returns:
            record: Extended linear address record.

        Raises:
            :obj:`ValueError`: Address overflow.

        Example:
            >>> str(Record.build_extended_linear_address(0x12345678))
            ':020000041234B4'
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')

        segment = address >> 16
        tag = cls.TAG_TYPE.EXTENDED_LINEAR_ADDRESS
        record = cls(0, tag, struct.pack('>H', segment))
        return record

    @classmethod
    def build_start_linear_address(
        cls: Type['Record'],
        address: int,
    ) -> 'Record':
        r"""Builds an start linear address record.

        Arguments:
            address (int):
                Start linear address.

        Returns:
            record: Start linear address record.

        Raises:
            :obj:`ValueError`: Address overflow.

        Example:
            >>> str(Record.build_start_linear_address(0x12345678))
            ':0400000512345678E3'
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')

        tag = cls.TAG_TYPE.START_LINEAR_ADDRESS
        record = cls(0, tag, struct.pack('>L', address))
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
                Maximum of 255 columns.

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
        if not 0 < columns < 255:
            raise ValueError('column overflow')
        if align is Ellipsis:
            align = columns
        if start is None:
            start = address

        align_base = (address % align) if align else 0
        address_old = 0

        for chunk in chop(data, columns, align_base):
            length = len(chunk)
            endex = address + length
            overflow = endex & 0xFFFF

            if overflow and (address ^ endex) & 0xFFFF0000:
                pivot = length - overflow

                yield cls.build_data(address, chunk[:pivot])
                address += pivot

                yield cls.build_extended_linear_address(address)

                yield cls.build_data(address, chunk[pivot:])
                address_old = address
                address += overflow

            else:
                if (address ^ address_old) & 0xFFFF0000:
                    yield cls.build_extended_linear_address(address)

                yield cls.build_data(address, chunk)
                address_old = address
                address += length

        if standalone:
            for record in cls.terminate(start):
                yield record

    @classmethod
    def build_standalone(
        cls: Type['Record'],
        data_records: RecordSequence,
        start: Optional[int] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Iterator['Record']:
        r"""Makes a sequence of data records standalone.

        Arguments:
            data_records (list of records):
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

        for record in cls.terminate(start):
            yield record

    @classmethod
    def terminate(
        cls: Type['Record'],
        start: int,
    ) -> Sequence['Record']:
        r"""Builds a record termination sequence.

        The termination sequence is made of:

        # An extended linear address record at ``0``.
        # A start linear address record at `start`.
        # An end-of-file record.

        Arguments:
            start (int):
                Program start address.

        Returns:
            list of records: Termination sequence.

        Example:
            >>> list(map(str, Record.terminate(0x12345678)))
            [':020000040000FA', ':0400000512345678E3', ':00000001FF']
        """
        return [cls.build_extended_linear_address(0),
                cls.build_start_linear_address(start),
                cls.build_end_of_file()]

    @classmethod
    def readdress(
        cls: Type['Record'],
        records: RecordSequence,
    ) -> None:
        r"""Converts to flat addressing.

        *Intel HEX*, stores records by *segment/offset* addressing.
        As this library adopts *flat* addressing instead, all the record
        addresses should be converted to *flat* addressing after loading.
        This procedure readdresses a sequence of records in-place.

        Warning:
            Only the `address` field is modified. All the other fields hold
            their previous value.

        Arguments:
            records (list of records):
                Sequence of records to be converted to *flat* addressing,
                in-place.

        Example:
            >>> records = [
            ...     Record.build_extended_linear_address(0x76540000),
            ...     Record.build_data(0x00003210, b'Hello, World!'),
            ... ]
            >>> records  #doctest: +NORMALIZE_WHITESPACE
            [Record(address=0x00000000,
                         tag=<Tag.EXTENDED_LINEAR_ADDRESS: 4>, count=2,
                         data=b'vT', checksum=0x30),
             Record(address=0x00003210, tag=<Tag.DATA: 0>, count=13,
                         data=b'Hello, World!', checksum=0x48)]
            >>> Record.readdress(records)
            >>> records  #doctest: +NORMALIZE_WHITESPACE
            [Record(address=0x76540000,
                         tag=<Tag.EXTENDED_LINEAR_ADDRESS: 4>, count=2,
                         data=b'vT', checksum=0x30),
             Record(address=0x76543210, tag=<Tag.DATA: 0>, count=13,
                         data=b'Hello, World!', checksum=0x48)]
        """
        esa = cls.TAG_TYPE.EXTENDED_SEGMENT_ADDRESS
        ela = cls.TAG_TYPE.EXTENDED_LINEAR_ADDRESS
        base = 0

        for record in records:
            tag = record.tag
            if tag == esa:
                base = struct.unpack('>H', record.data)[0] << 4
                address = base
            elif tag == ela:
                base = struct.unpack('>H', record.data)[0] << 16
                address = base
            else:
                address = base + record.address

            record.address = address

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

        offset = int(groups['offset'], 16)
        tag = cls.TAG_TYPE(int(groups['tag'], 16))
        count = int(groups['count'], 16)
        data = unhexlify(groups['data'] or '')
        checksum = int(groups['checksum'], 16)

        if count != len(data):
            raise ValueError('count error')
        record = cls(offset, tag, data, checksum)
        return record
