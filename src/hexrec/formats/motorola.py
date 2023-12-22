# Copyright (c) 2013-2024, Andrea Zoppi
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

import binascii
import enum
import re
import struct
from typing import IO
from typing import Any
from typing import Iterator
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Type
from typing import Union
from typing import cast as _cast

from bytesparse import Memory

from ..records import Record as _Record
from ..records import RecordSequence
from ..records import Tag as _Tag
from ..records import get_data_records
from ..records2 import BaseFile
from ..records2 import BaseRecord
from ..records2 import BaseTag
from ..utils import AnyBytes
from ..utils import EllipsisType
from ..utils import check_empty_args_kwargs
from ..utils import chop
from ..utils import hexlify
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
        cls,
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
        self,
        address: int,
        tag: Tag,
        data: AnyBytes,
        checksum: Union[int, EllipsisType] = Ellipsis,
    ) -> None:
        super().__init__(address, self.TAG_TYPE(tag), data, checksum)

    def __str__(
        self,
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
        self,
    ) -> int:
        tag = int(self.tag)
        address_length = self.TAG_TO_ADDRESS_LENGTH[tag] or 0
        return address_length + len(self.data) + 1

    def compute_checksum(
        self,
    ) -> int:
        checksum = sum(struct.pack('HL', self.count, self.address))
        checksum += sum(self.data or b'')
        checksum = (checksum & 0xFF) ^ 0xFF
        return checksum

    def check(
        self,
    ) -> None:
        super().check()

        tag = int(self.TAG_TYPE(self.tag))

        if tag in (0, 4, 5, 6) and self.address:
            raise ValueError('address error')

        if self.count != self.compute_count():
            raise ValueError('count error')

    @classmethod
    def fit_data_tag(
        cls,
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
        cls,
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
        cls,
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
        cls,
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
        cls,
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
        cls,
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
        cls,
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
        cls,
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
        cls,
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
                    raise ValueError('tag error')

                data_count += 1

            elif record_tag == 5:
                if count_found:
                    raise ValueError('misplaced count')
                count_found = True
                expected_count = unpack('>H', record.data)[0]
                if expected_count != data_count:
                    raise ValueError('record count error')

            elif record_tag == 6:
                if count_found:
                    raise ValueError('misplaced count')
                count_found = True
                u, hl = unpack('>BH', record.data)
                expected_count = (u << 16) | hl
                if expected_count != data_count:
                    raise ValueError('record count error')

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
                raise ValueError('matching tag error')

        try:
            next(it)
        except StopIteration:
            pass
        else:
            raise ValueError('sequence length error')

    @classmethod
    def get_metadata(
        cls,
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
        cls,
        data: AnyBytes,
        address: int = 0,
        columns: int = 16,
        align: Union[int, EllipsisType] = Ellipsis,
        standalone: bool = True,
        start: Optional[Union[int, EllipsisType]] = 0,
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
                Maximum columns: 252 for `S1`, 251 for `S2`, 250 for `S3`.

            align (int):
                Aligns record addresses to such number.
                If ``Ellipsis``, its value is resolved after `columns`.

            standalone (bool):
                Generates a sequence of records that can be saved as a
                standalone record file.

            start (int):
                Program start address.
                If ``Ellipsis``, it is assigned the minimum data record address.
                If ``None``, no start address records are output.

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
        if start is Ellipsis:
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
            if start is not None:
                yield cls.build_terminator(start, tag)

    @classmethod
    def fix_tags(
        cls,
        records: RecordSequence,
    ) -> None:
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
                record.update_count()
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

    @classmethod
    def get_header(
        cls,
        records: RecordSequence,
    ) -> Optional['Record']:
        r"""Gets the header record.

        Arguments:
            records (list of records):
                A sequence of records.

        Returns:
            record: The header record, or ``None``.
        """
        header_tag = cls.TAG_TYPE.HEADER
        for record in records:
            if record.tag == header_tag:
                return record
        return None

    @classmethod
    def set_header(
        cls,
        records: RecordSequence,
        data: AnyBytes,
    ) -> RecordSequence:
        r"""Sets the header data.

        If existing, the header record is updated in-place.
        If missing, the header record is prepended.

        Arguments:
            records (list of records):
                A sequence of records.

            data (bytes):
                Optional header data.

        Returns:
            list of records: Updated record list.
        """
        header_tag = cls.TAG_TYPE.HEADER
        found = None
        for record in records:
            if record.tag == header_tag:
                found = record
                break

        if found is None:
            records = list(records)
            records.insert(0, cls.build_header(data))
        else:
            found.data = data
            found.address = 0
            found.update_count()
            found.update_checksum()
        return records


# =============================================================================

@enum.unique
class SrecTag(BaseTag, enum.IntEnum):
    r"""Motorola S-record tag."""

    HEADER = 0
    r"""Header string. Optional."""

    DATA_16 = 1
    r"""16-bit address data record."""

    DATA_24 = 2
    r"""24-bit address data record."""

    DATA_32 = 3
    r"""32-bit address data record."""

    RESERVED = 4
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
    def fit_count_tag(cls, count: int) -> 'SrecTag':
        # TODO: __doc__

        if count < 0:
            raise ValueError('count overflow')
        if count <= 0xFFFF:
            return cls.COUNT_16
        if count <= 0xFFFFFF:
            return cls.COUNT_24
        raise ValueError('count overflow')

    @classmethod
    def fit_data_tag(cls, address_max: int) -> 'SrecTag':
        # TODO: __doc__

        if address_max < 0:
            raise ValueError('address overflow')
        if address_max <= 0xFFFF:
            return cls.DATA_16
        if address_max <= 0xFFFFFF:
            return cls.DATA_24
        if address_max <= 0xFFFFFFFF:
            return cls.DATA_32
        raise ValueError('address overflow')

    def get_address_max(self) -> Optional[int]:
        # TODO: __doc__

        size = self.get_address_size()
        mask = (1 << (size << 3)) - 1
        return mask

    def get_address_size(self) -> Optional[int]:
        # TODO: __doc__

        SIZES = (2, 2, 3, 4, None, 2, 3, 4, 3, 2)
        size = SIZES[self]
        return size

    def get_tag_match(self) -> Optional['SrecTag']:
        # TODO: __doc__

        MATCHES = (None, 9, 8, 7, None, None, None, 3, 2, 1)
        match = MATCHES[self]
        if match is None:
            return None
        tag_type = type(self)
        return tag_type(match)

    def is_count(self) -> bool:
        # TODO: __doc__

        return self == 5 or self == 6

    def is_data(self) -> bool:
        # TODO: __doc__

        return self == 1 or self == 2 or self == 3

    def is_header(self) -> bool:
        # TODO: __doc__

        return self == 0

    def is_start(self) -> bool:
        # TODO: __doc__

        return self == 7 or self == 8 or self == 9


SIZE_TO_ADDRESS_FORMAT: Mapping[int, bytes] = {
    2: b'%04X',
    3: b'%06X',
    4: b'%08X',
}
# TODO: __doc__


class SrecRecord(BaseRecord):
    # TODO: __doc__

    TAG_TYPE: Type[SrecTag] = SrecTag

    LINE1_REGEX = re.compile(
        b'^(?P<before>[^S]*)S'
        b'(?P<tag>[0-9A-Fa-f])'
        b'(?P<count>[0-9A-Fa-f]{2})'
    )
    # TODO: __doc__

    LINE2_REGEX = [re.compile(
        b'^(?P<address>[0-9A-Fa-f]{%d})' % (4 + (i * 2))
    ) for i in range(3)]
    # TODO: __doc__

    LINE3_REGEX = re.compile(
        b'^(?P<data>([0-9A-Fa-f]{2}){,252})'
        b'(?P<checksum>[0-9A-Fa-f]{2})'
        b'(?P<after>[^\\r\\n]*)\\r?\\n$'
    )
    # TODO: __doc__

    @classmethod
    def build_count(
        cls,
        count: int,
        tag: Optional[SrecTag] = None,
    ) -> 'SrecRecord':
        # TODO: __doc__

        tag_type = cls.TAG_TYPE
        if tag is None:
            tag = tag_type.fit_count_tag(count)
        else:
            if not tag_type.COUNT_16 <= tag <= tag_type.COUNT_24:
                raise ValueError('invalid count tag')

        if not 0 <= count <= tag.get_address_max():
            raise ValueError('count overflow')

        record = cls(tag, address=count)
        return record

    @classmethod
    def build_data(
        cls,
        address: int,
        data: AnyBytes,
        tag: Optional[SrecTag] = None,
    ) -> 'SrecRecord':
        # TODO: __doc__

        tag_type = cls.TAG_TYPE
        if tag is None:
            tag = tag_type.fit_data_tag(address)
        else:
            if not tag_type.DATA_16 <= tag <= tag_type.DATA_32:
                raise ValueError('invalid data tag')

        if not 0 <= address <= tag.get_address_max():
            raise ValueError('address overflow')

        record = cls(tag, address=address, data=data)
        return record

    @classmethod
    def build_header(cls, data: AnyBytes) -> 'SrecRecord':
        # TODO: __doc__

        tag_type = cls.TAG_TYPE
        record = cls(tag_type.HEADER, data=data)
        return record

    @classmethod
    def build_start(
        cls,
        address: int,
        tag: Optional[SrecTag] = None,
    ) -> 'SrecRecord':
        # TODO: __doc__

        tag_type = cls.TAG_TYPE
        if tag is None:
            tag = tag_type.fit_data_tag(address).get_tag_match()
        else:
            if not tag_type.START_32 <= tag <= tag_type.START_16:
                raise ValueError('invalid start tag')

        if not 0 <= address <= tag.get_address_max():
            raise ValueError('start address overflow')

        record = cls(tag, address=address)
        return record

    def compute_checksum(self) -> int:

        checksum = self.count
        address = self.address
        while address > 0:
            checksum += address & 0xFF
            address >>= 8
        checksum += sum(iter(self.data))
        checksum = (checksum & 0xFF) ^ 0xFF
        return checksum

    def compute_count(self) -> int:

        tag = _cast(SrecTag, self.tag)
        count = tag.get_address_size() + len(self.data) + 1
        return count

    @classmethod
    def parse(cls, line: AnyBytes) -> 'SrecRecord':
        # TODO: __doc__

        tag_type = cls.TAG_TYPE
        line = memoryview(line)

        match = cls.LINE1_REGEX.match(line)
        if not match:
            raise ValueError('syntax error')
        groups = match.groupdict()
        before = groups['before']
        tag = tag_type(int(groups['tag'], 16))
        count = int(groups['count'], 16)

        addridx = tag.get_address_size() - 2
        line = line[match.span()[1]:]
        match = cls.LINE2_REGEX[addridx].match(line)
        if not match:
            raise ValueError('syntax error')
        groups = match.groupdict()
        address = int(groups['address'], 16)

        line = line[match.span()[1]:]
        match = cls.LINE3_REGEX.match(line)
        if not match:
            raise ValueError('syntax error')
        groups = match.groupdict()
        data = binascii.unhexlify(groups['data'])
        checksum = int(groups['checksum'], 16)
        after = groups['after']

        record = cls(tag,
                     address=address,
                     data=data,
                     count=count,
                     checksum=checksum,
                     before=before,
                     after=after)
        return record

    def to_bytestr(self, end: AnyBytes = b'\r\n') -> bytes:

        self.validate()
        tag = _cast(SrecTag, self.tag)
        addrfmt = SIZE_TO_ADDRESS_FORMAT[tag.get_address_size()]

        bytestr = b'%sS%X%02X%s%s%02X%s%s' % (
            self.before,
            tag,
            self.count,
            addrfmt % self.address,
            binascii.hexlify(self.data).upper(),
            self.checksum,
            self.after,
            end,
        )
        return bytestr

    def to_tokens(self, end: AnyBytes = b'\r\n') -> Mapping[str, bytes]:

        self.validate()
        tag = _cast(SrecTag, self.tag)
        addrfmt = SIZE_TO_ADDRESS_FORMAT[tag.get_address_size()]

        return {
            'before': self.before,
            'begin': b'S',
            'tag': b'%X' % tag,
            'count': b'%02X' % self.count,
            'address': addrfmt % self.address,
            'data': binascii.hexlify(self.data).upper(),
            'checksum': b'%02X' % self.checksum,
            'after': self.after,
            'end': end,
        }

    def validate(self) -> 'SrecRecord':

        super().validate()
        address = self.address

        if self.after and not self.after.isspace():
            raise ValueError('junk after')

        if self.before and not self.before.isspace():
            raise ValueError('junk before')

        if not 0 <= self.checksum <= 0xFF:
            raise ValueError('checksum overflow')

        if not 3 <= self.count <= 0xFF:
            raise ValueError('count overflow')

        tag_type = _cast(SrecTag, self.TAG_TYPE)
        tag = _cast(SrecTag, self.tag)
        if tag == tag_type.RESERVED:
            raise ValueError('reserved tag')

        data_size = len(self.data)
        address_max = tag.get_address_max()

        if not tag_type.HEADER <= tag <= tag_type.DATA_32:
            if data_size:
                raise ValueError('unexpected data')

            if tag == tag_type.HEADER:
                address_max = 0

        if data_size > 0xFF:
            raise ValueError('data size overflow')

        if not 0 <= address <= address_max:
            raise ValueError('address overflow')

        return self


class SrecFile(BaseFile):
    # TODO: __doc__

    FILE_EXT: Sequence[str] = [
        # https://en.wikipedia.org/wiki/SREC_(file_format)
        '.s19', '.s28', '.s37', '.s',
        '.s1', '.s2', '.s3', '.sx',
        '.srec', '.exo', '.mot', '.mxt',
    ]

    META_KEYS: Sequence[str] = ['header', 'maxdatalen', 'startaddr']

    RECORD_TYPE: Type[SrecRecord] = SrecRecord

    def __init__(self):

        super().__init__()

        self._header: Optional[AnyBytes] = b''
        self._startaddr: int = 0

    def apply_records(self) -> 'SrecFile':

        if not self._records:
            raise ValueError('records required')

        memory = Memory()
        startaddr = 0
        header = None

        for record in self._records:
            tag = _cast(SrecTag, record.tag)

            if tag.is_data():
                memory.write(record.address, record.data)

            elif tag.is_start():
                startaddr = record.address

            elif tag.is_header():
                header = record.data

        self.discard_memory()
        self._memory = memory
        self._startaddr = startaddr
        self._header = header
        return self

    @property
    def header(self) -> Optional[AnyBytes]:

        if self._memory is None:
            self.apply_records()
        return self._header

    @header.setter
    def header(self, header: Optional[AnyBytes]) -> None:

        if header != self._header:
            self.discard_records()
        self._header = header

    @classmethod
    def parse(cls, stream: IO, ignore_errors: bool = False) -> 'SrecFile':

        file = super().parse(stream, ignore_errors=ignore_errors)
        return _cast(SrecFile, file)

    @property
    def startaddr(self) -> int:

        if self._memory is None:
            self.apply_records()
        return self._startaddr

    @startaddr.setter
    def startaddr(self, address: int = 0) -> None:

        address = address.__index__()
        if not 0 <= address <= 0xFFFFFFFF:
            raise ValueError('invalid start address')

        if self._startaddr != address:
            self.discard_records()
        self._startaddr = address

    def update_records(
        self,
        align: bool = True,
        header: bool = True,
        count: bool = True,
        start: bool = True,
        data_tag: Optional[SrecTag] = None,
        count_tag: Optional[SrecTag] = None,
    ) -> 'SrecFile':
        # TODO: __doc__

        memory = self._memory
        if memory is None:
            raise ValueError('memory instance required')

        records = []
        record_type = self.RECORD_TYPE
        tag_type = record_type.TAG_TYPE
        if data_tag is None:
            data_tag = tag_type.fit_data_tag(max(0, memory.endin))
        chunk_views = []
        data_record_count = 0
        try:
            if header and self._header is not None:
                record = record_type.build_header(self._header)
                records.append(record)

            for chunk_start, chunk_view in memory.chop(self.maxdatalen, align=align):
                chunk_views.append(chunk_view)
                data = bytes(chunk_view)
                record = record_type.build_data(chunk_start, data, tag=data_tag)
                records.append(record)
                data_record_count += 1

            if not data_record_count:
                record = record_type.build_data(0, b'', tag=data_tag)
                records.append(record)
                data_record_count += 1

            if count:
                if count_tag is None:
                    count_tag = tag_type.fit_count_tag(data_record_count)
                record = record_type.build_count(data_record_count, tag=count_tag)
                records.append(record)

            start_tag = data_tag.get_tag_match()
            address = self._startaddr if start else 0
            record = record_type.build_start(address, tag=start_tag)
            records.append(record)

        finally:
            for chunk_view in chunk_views:
                chunk_view.release()

        self.discard_records()
        self._records = records
        return self

    def validate_records(
        self,
        header_required: bool = False,
        data_ordering: bool = False,
        data_uniform: bool = True,
        count_required: bool = False,
        startaddr_within_data: bool = False,
    ) -> 'SrecFile':
        # TODO: __doc__

        records = self._records
        if records is None:
            raise ValueError('records required')

        start_record = None
        count_record = None
        last_data_endex = 0
        data_tag_sample = None
        data_count = 0

        for index, record in enumerate(records):
            record = _cast(SrecRecord, record)
            record.validate()
            tag = _cast(SrecTag, record.tag)

            if tag.is_data():
                data_count += 1

                if data_uniform:
                    if data_tag_sample is None:
                        data_tag_sample = tag
                    elif tag != data_tag_sample:
                        raise ValueError('data record tags not uniform')

                if data_ordering:
                    address = record.address
                    if address < last_data_endex:
                        raise ValueError('unordered data record')
                    last_data_endex = address + len(record.data)

            elif tag.is_count():
                if count_record is not None:
                    raise ValueError('multiple count records')
                count_record = record

                if record.address != data_count:
                    raise ValueError('wrong data record count')

                if index != len(records) - 2:
                    raise ValueError('count record not penultimate')

            elif tag.is_start():
                if start_record is not None:
                    raise ValueError('multiple start records')
                start_record = record

                if index != len(records) - 1:
                    raise ValueError('count record not last')

            elif tag.is_header():
                if index:
                    raise ValueError('header record not first')

        if count_required:
            if count_record is None:
                raise ValueError('missing count record')

        if start_record is None:
            raise ValueError('missing start record')

        if startaddr_within_data:
            startaddr = start_record.data_to_int()
            start_datum = self.memory.peek(startaddr)
            if start_datum is None:
                raise ValueError('no data at start address')

        if data_uniform:
            if start_record.tag != data_tag_sample.get_tag_match():
                raise ValueError('start record tag not uniform')

        return self
