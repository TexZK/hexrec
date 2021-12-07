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

r"""Motorola S-record format.

See Also:
    `<https://en.wikipedia.org/wiki/SREC_(file_format)>`_
"""

import enum
import re
import struct
from typing import Any
from typing import Iterator
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Type
from typing import Union

from ..records import Record as _Record
from ..records import RecordSequence
from ..records import Tag as _Tag
from ..records import get_data_records
from ..utils import AnyBytes
from ..utils import check_empty_args_kwargs
from ..utils import chop
from ..utils import expmsg
from ..utils import hexlify
from ..utils import sum_bytes
from ..utils import unhexlify


@enum.unique
class Tag(_Tag):
    r"""Motorola S-record tag."""

    HEADER = 0
    r"""Header string. Optional."""

    DATA_16 = 1
    r"""16-bit address data record."""

    DATA_24 = 2
    r"""24-bit address data record."""

    DATA_32 = 3
    r"""32-bit address data record."""

    _RESERVED = 4
    r"""Reserved tag."""

    COUNT_16 = 5
    r"""16-bit record count. Optional."""

    COUNT_24 = 6
    r"""24-bit record count. Optional."""

    START_32 = 7
    r"""32-bit start address. Terminates :attr:`DATA_32`."""

    START_24 = 8
    r"""24-bit start address. Terminates :attr:`DATA_24`."""

    START_16 = 9
    r"""16-bit start address. Terminates :attr:`DATA_16`."""

    @classmethod
    def is_data(
        cls: Type['Tag'],
        value: Union[int, 'Tag'],
    ) -> bool:
        r"""bool: `value` is a data record tag."""
        return 1 <= value <= 3


class Record(_Record):
    r"""Motorola S-record.

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

    TAG_TO_ADDRESS_LENGTH: Sequence[Optional[int]] = (2, 2, 3, 4, None, None, None, 4, 3, 2)
    r"""Maps a tag to its address byte length, if available."""

    TAG_TO_COLUMN_SIZE: Sequence[Optional[int]] = (None, 252, 251, 250, None, None, None, None, None, None)
    r"""Maps a tag to its maximum column size, if available."""

    MATCHING_TAG: Sequence[Optional[int]] = (None, None, None, None, None, None, None, 3, 2, 1)
    r"""Maps the terminator tag to its matching data tag."""

    REGEX = re.compile(r'^S[0-9]([0-9A-Fa-f]{2}){4,264}$')
    r"""Regular expression for parsing a record text line."""

    EXTENSIONS: Sequence[str] = ('.mot', '.s19', '.s28', '.s37', '.srec', '.exo')
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
        tag_text = f'S{self.tag:d}'

        address_length = self.TAG_TO_ADDRESS_LENGTH[self.tag]
        if address_length is None:
            address_text = ''
            count_text = f'{(len(self.data) + 1):02X}'
        else:
            count_text = f'{(address_length + len(self.data) + 1):02X}'
            offset = 2 * (4 - address_length)
            address_text = f'{self.address:08X}'[offset:]

        data_text = hexlify(self.data)

        checksum_text = f'{self._get_checksum():02X}'

        text = ''.join((tag_text,
                        count_text,
                        address_text,
                        data_text,
                        checksum_text))
        return text

    def compute_count(
        self: 'Record',
    ) -> int:
        tag = int(self.tag)
        address_length = self.TAG_TO_ADDRESS_LENGTH[tag] or 0
        return address_length + len(self.data) + 1

    def compute_checksum(
        self: 'Record',
    ) -> int:
        checksum = sum_bytes(struct.pack('HL', self.count, self.address))
        checksum += sum_bytes(self.data)
        checksum = (checksum & 0xFF) ^ 0xFF
        return checksum

    def check(
        self: 'Record',
    ) -> None:
        super().check()

        tag = int(self.TAG_TYPE(self.tag))

        if tag in (0, 4, 5, 6) and self.address:
            raise ValueError('address error')

        if self.count != self.compute_count():
            raise ValueError('count error')

    @classmethod
    def fit_data_tag(
        cls: Type['Record'],
        endex: int,
    ) -> 'Tag':
        r"""Fits a data tag by address.

        Depending on the value of `endex`, get the data tag with the smallest
        supported address.

        Arguments:
            endex (int):
                Exclusive end address of the data.

        Returns:
            tag: Fitting data tag.

        Raises:
            :obj:`ValueError`: Address overflow.

        Examples:
            >>> Record.fit_data_tag(0x00000000)
            <Tag.DATA_16: 1>

            >>> Record.fit_data_tag(0x0000FFFF)
            <Tag.DATA_16: 1>

            >>> Record.fit_data_tag(0x00010000)
            <Tag.DATA_16: 1>

            >>> Record.fit_data_tag(0x00FFFFFF)
            <Tag.DATA_24: 2>

            >>> Record.fit_data_tag(0x01000000)
            <Tag.DATA_24: 2>

            >>> Record.fit_data_tag(0xFFFFFFFF)
            <Tag.DATA_32: 3>

            >>> Record.fit_data_tag(0x100000000)
            <Tag.DATA_32: 3>
        """

        if not 0 <= endex <= (1 << 32):
            raise ValueError('address overflow')

        elif endex <= (1 << 16):
            return cls.TAG_TYPE.DATA_16

        elif endex <= (1 << 24):
            return cls.TAG_TYPE.DATA_24

        else:
            return cls.TAG_TYPE.DATA_32

    @classmethod
    def fit_count_tag(
        cls: Type['Record'],
        record_count: int,
    ) -> 'Tag':
        r"""Fits the record count tag.

        Arguments:
            record_count (int):
                Record count.

        Returns:
            tag: Fitting record count tag.

        Raises:
            :obj:`ValueError`: Count overflow.

        Examples:
            >>> Record.fit_count_tag(0x0000000)
            <Tag.COUNT_16: 5>

            >>> Record.fit_count_tag(0x00FFFF)
            <Tag.COUNT_16: 5>

            >>> Record.fit_count_tag(0x010000)
            <Tag.COUNT_24: 6>

            >>> Record.fit_count_tag(0xFFFFFF)
            <Tag.COUNT_24: 6>
        """

        if not 0 <= record_count < (1 << 24):
            raise ValueError('count overflow')

        elif record_count < (1 << 16):
            return cls.TAG_TYPE.COUNT_16

        else:  # record_count < (1 << 24)
            return cls.TAG_TYPE.COUNT_24

    @classmethod
    def build_header(
        cls: Type['Record'],
        data: AnyBytes,
    ) -> 'Record':
        r"""Builds a header record.

        Arguments:
            data (bytes):
                Header string data.

        Returns:
            record: Header record.

        Example:
            >>> str(Record.build_header(b'Hello, World!'))
            'S010000048656C6C6F2C20576F726C642186'
        """
        return cls(0, cls.TAG_TYPE.HEADER, data)

    @classmethod
    def build_data(
        cls: Type['Record'],
        address: int,
        data: AnyBytes,
        tag: Optional[Tag] = None,
    ) -> 'Record':
        r"""Builds a data record.

        Arguments:
            address (int):
                Record start address.

            data (bytes):
                Some program data.

            tag (tag):
                Data tag record.
                If ``None``, automatically selects the fitting one.

        Returns:
            record: Data record.

        Raises:
            :obj:`ValueError`: Tag error.

        Examples:
            >>> str(Record.build_data(0x1234, b'Hello, World!'))
            'S110123448656C6C6F2C20576F726C642140'

            >>> str(Record.build_data(0x1234, b'Hello, World!',
            ...                               tag=Tag.DATA_16))
            'S110123448656C6C6F2C20576F726C642140'

            >>> str(Record.build_data(0x123456, b'Hello, World!',
            ...                               tag=Tag.DATA_24))
            'S21112345648656C6C6F2C20576F726C6421E9'

            >>> str(Record.build_data(0x12345678, b'Hello, World!',
            ...                               tag=Tag.DATA_32))
            'S3121234567848656C6C6F2C20576F726C642170'
        """
        if tag is None:
            tag = cls.fit_data_tag(address + len(data))

        if tag not in (1, 2, 3):
            raise ValueError('tag error')

        record = cls(address, tag, data)
        return record

    @classmethod
    def build_terminator(
        cls: Type['Record'],
        start: int,
        last_data_tag: Tag = Tag.DATA_16,
    ) -> 'Record':
        r"""Builds a terminator record.

        Arguments:
            start (int):
                Program start address.

            last_data_tag (tag):
                Last data record tag to match.

        Returns:
            record: Terminator record.

        Examples:
            >>> str(Record.build_terminator(0x1234))
            'S9031234B6'

            >>> str(Record.build_terminator(0x1234, Tag.DATA_16))
            'S9031234B6'

            >>> str(Record.build_terminator(0x123456, Tag.DATA_24))
            'S8041234565F'

            >>> str(Record.build_terminator(0x12345678, Tag.DATA_32))
            'S70512345678E6'
        """
        tag = cls.TAG_TYPE(cls.MATCHING_TAG.index(int(last_data_tag)))
        terminator_record = cls(start, tag, b'')
        return terminator_record

    @classmethod
    def build_count(
        cls: Type['Record'],
        record_count: int,
    ) -> 'Record':
        r"""Builds a count record.

        Arguments:
            record_count (int):
                Record count.

        Returns:
            record: Count record.

        Raises:
            :obj:`ValueError`: Count error.

        Examples:
             >>> str(Record.build_count(0x1234))
             'S5031234B6'

             >>> str(Record.build_count(0x123456))
             'S6041234565F'
        """
        tag = cls.fit_count_tag(record_count)
        count_data = struct.pack('>L', record_count)
        count_record = cls(0, tag, count_data[(7 - tag):])
        return count_record

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

        tag = cls.TAG_TYPE(int(line[1:2]))
        count = int(line[2:4], 16)
        if 2 * count != len(line) - 4:
            raise ValueError('count error')

        address_length = cls.TAG_TO_ADDRESS_LENGTH[tag] or 0
        address = int('0' + line[4:(4 + 2 * address_length)], 16)
        data = unhexlify(line[(4 + 2 * address_length):-2])
        checksum = int(line[-2:], 16)

        record = cls(address, tag, data, checksum)
        return record

    @classmethod
    def build_standalone(
        cls: Type['Record'],
        data_records: RecordSequence,
        start: Optional[int] = None,
        tag: Optional[Tag] = None,
        header: AnyBytes = b'',
    ) -> Iterator['Record']:
        r"""Makes a sequence of data records standalone.

        Arguments:
            data_records (list of records):
                A sequence of data records.

            start (int):
                Program start address.
                If ``None``, it is assigned the minimum data record address.

            tag (tag):
                Data tag record.
                If ``None``, automatically selects the fitting one.

            header (bytes):
                Header byte data.

        Yields:
            record: Records for a standalone record file.
        """
        address = 0
        count = 0
        if tag is None:
            if not data_records:
                data_records = [cls.build_data(0, b'')]
            tag = max(record.tag for record in data_records)

        yield cls.build_header(header)

        for record in data_records:
            yield record
            count += 1
            address = max(address, record.address + len(record.data))
            tag = max(tag, record.tag)

        yield cls.build_count(count)

        if start is None:
            if not data_records:
                data_records = [cls.build_data(0, b'')]
            start = min(record.address for record in data_records)

        yield cls.build_terminator(start, tag)

    @classmethod
    def check_sequence(
        cls: Type['Record'],
        records: RecordSequence,
    ) -> None:
        super().check_sequence(records)

        unpack = struct.unpack
        first_tag = None
        data_count = 0
        it = iter(records)
        header_found = False
        count_found = False
        record_index = -1

        while True:
            try:
                record = next(it)
            except StopIteration:
                record = None
                break
            record_index += 1

            record_tag = int(record.tag)

            if record_tag == 0:
                if header_found or record_index:
                    raise ValueError('header error')

                header_found = True

            elif record_tag in (1, 2, 3):
                if first_tag is None:
                    first_tag = record_tag

                elif record_tag != first_tag:
                    raise ValueError(expmsg(record_tag, 'in (1, 2, 3)',
                                            'tag error'))

                data_count += 1

            elif record_tag == 5:
                if count_found:
                    raise ValueError('misplaced count')
                count_found = True
                expected_count = unpack('>H', record.data)[0]
                if expected_count != data_count:
                    raise ValueError(expmsg(data_count, expected_count,
                                            'record count error'))

            elif record_tag == 6:
                if count_found:
                    raise ValueError('misplaced count')
                count_found = True
                u, hl = unpack('>BH', record.data)
                expected_count = (u << 16) | hl
                if expected_count != data_count:
                    raise ValueError(expmsg(data_count, expected_count,
                                            'record count error'))

            else:
                break

        if not count_found:
            raise ValueError('missing count')

        if not header_found:
            raise ValueError('missing header')

        if record is None:
            raise ValueError('missing start')
        elif record.tag not in (7, 8, 9):
            raise ValueError('tag error')
        else:
            matching_tag = cls.MATCHING_TAG[record.tag]
            if first_tag != matching_tag:
                raise ValueError(expmsg(matching_tag, first_tag,
                                        'matching tag error'))

        try:
            next(it)
        except StopIteration:
            pass
        else:
            raise ValueError('sequence length error')

    @classmethod
    def get_metadata(
        cls: 'Record',
        records: RecordSequence,
    ) -> Mapping[str, Any]:
        r"""Retrieves metadata from records.

        Collected metadata:

        * `columns`: maximum data columns per line found, or ``None``.
        * `start`: program execution start address found, or ``None``.
        * `count`: last `count` record found, or ``None``.
        * `header`: last `header` record data found, or ``None``.

        Arguments:
            records (list of records):
                Records to scan for metadata.

        Returns:
            dict: Collected metadata.
        """
        header = None
        columns = 0
        count = None
        start = None

        for record in records:
            tag = record.tag

            if tag == 0:
                header = record.data

            elif tag in (5, 6) and record.data:
                count = int.from_bytes(record.data, 'big')

            elif tag in (7, 8, 9):
                start = record.address

            else:
                columns = max(columns, len(record.data or b''))

        metadata = {
            'header': header,
            'columns': columns,
            'count': count,
            'start': start,
        }
        return metadata

    @classmethod
    def split(
        cls: Type['Record'],
        data: AnyBytes,
        address: int = 0,
        columns: int = 16,
        align: Union[int, type(Ellipsis)] = Ellipsis,
        standalone: bool = True,
        start: Optional[int] = None,
        tag: Optional[Tag] = None,
        header: AnyBytes = b'',
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
                Maximum columns: 252 for `S1`, 251 for `S2`, 250 for `S3`.

            align (int):
                Aligns record addresses to such number.
                If ``Ellipsis``, its value is resolved after `columns`.

            standalone (bool):
                Generates a sequence of records that can be saved as a
                standalone record file.

            start (int):
                Program start address.
                If ``None``, it is assigned the minimum data record address.

            tag (tag):
                Data tag record.
                If ``None``, automatically selects the fitting one.

            header (bytes):
                Header byte data.

        Yields:
            record: Data split into records.

        Raises:
            :obj:`ValueError`: Address, size, or column overflow.
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        if align is Ellipsis:
            align = columns
        if start is None:
            start = address
        if tag is None:
            tag = cls.fit_data_tag(address + len(data))

        max_columns = cls.TAG_TO_COLUMN_SIZE[tag]
        if not 0 < columns <= max_columns:
            raise ValueError('column overflow')

        if standalone:
            yield cls.build_header(header)

        skip = (address % align) if align else 0
        count = 0
        for chunk in chop(data, columns, skip):
            yield cls.build_data(address, chunk, tag)
            count += 1
            address += len(chunk)

        if standalone:
            yield cls.build_count(count)
            yield cls.build_terminator(start, tag)

    @classmethod
    def fix_tags(
        cls: Type['Record'],
        records: RecordSequence,
    ) -> None:
        r"""Fix record tags.

        Updates record tags to reflect modified size and count.
        All the checksums are updated too.
        Operates in-place.

        Arguments:
            records (list of records):
                A sequence of records.
                Must be in-line mutable.
        """
        if records:
            max_address = max(record.address + len(record.data)
                              for record in records)
        else:
            max_address = 0
        tag = cls.TAG_TYPE(cls.fit_data_tag(max_address))
        count_16 = cls.TAG_TYPE.COUNT_16
        start_tags = (cls.TAG_TYPE.START_16,
                      cls.TAG_TYPE.START_24,
                      cls.TAG_TYPE.START_32)
        start_ids = []

        for index, record in enumerate(records):
            if record.tag == count_16:
                count = struct.unpack('>L', record.data.rjust(4, b'\0'))[0]
                if count >= (1 << 16):
                    record.tag = cls.TAG_TYPE.COUNT_24
                    record.data = struct.pack('>L', count)[1:]
                    record.update_count()
                    record.update_checksum()

            elif record.is_data():
                record.tag = tag
                record.update_checksum()

            elif record.tag in start_tags:
                start_ids.append(index)

        data_records = get_data_records(records)
        if not data_records:
            data_records = [cls.build_data(0, b'')]
        max_tag = int(max(record.tag for record in data_records))
        start_tag = cls.TAG_TYPE(cls.MATCHING_TAG.index(max_tag))
        for index in start_ids:
            records[index].tag = start_tag
