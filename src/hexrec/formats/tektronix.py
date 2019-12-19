# -*- coding: utf-8 -*-
import enum
import re
from typing import ByteString
from typing import Iterator
from typing import Optional
from typing import Union

from ..records import Record as _Record
from ..records import RecordSeq
from ..records import Tag as _Tag
from ..utils import chop
from ..utils import hexlify
from ..utils import sum_bytes
from ..utils import unhexlify


@enum.unique
class Tag(_Tag):
    DATA = 6
    TERMINATOR = 8

    @classmethod
    def is_data(cls, value: Union[int, 'Tag']) -> bool:
        r""":obj:`bool`: `value` is a data record tag."""
        return value == cls.DATA


class Record(_Record):
    r"""Tektronix extended HEX record.

    See:
        `<https://en.wikipedia.org/wiki/Tektronix_extended_HEX>`_

    """

    TAG_TYPE = Tag
    """Associated Python class for tags."""

    REGEX = re.compile(r'^%(?P<count>[0-9A-Fa-f]{2})'
                       r'(?P<tag>[68])'
                       r'(?P<checksum>[0-9A-Fa-f]{2})'
                       r'8(?P<address>[0-9A-Fa-f]{8})'
                       r'(?P<data>([0-9A-Fa-f]{2}){,255})$')
    """Regular expression for parsing a record text line."""

    EXTENSIONS = ('.tek',)
    """Automatically supported file extensions."""

    def __init__(self, address: int,
                 tag: Tag,
                 data: ByteString,
                 checksum: Union[int, type(Ellipsis)] = Ellipsis) -> None:

        super().__init__(address, self.TAG_TYPE(tag), data, checksum)

    def __str__(self) -> str:
        self.check()
        text = (f'%{self.count:02X}'
                f'{self.tag:01X}'
                f'{self._get_checksum():02X}'
                f'8'
                f'{self.address:08X}'
                f'{hexlify(self.data)}')
        return text

    def compute_count(self) -> int:
        count = 9 + (len(self.data) * 2)
        return count

    def compute_checksum(self) -> int:
        text = (f'{self.count:02X}'
                f'{self.tag:01X}'
                f'8'
                f'{self.address:08X}'
                f'{hexlify(self.data)}')
        checksum = sum_bytes(int(c, 16) for c in text) & 0xFF
        return checksum

    def check(self) -> None:
        super().check()
        tag = self.TAG_TYPE(self.tag)

        if tag == self.TAG_TYPE.TERMINATOR and self.data:
            raise ValueError('invalid data')

        if self.count != self.compute_count():
            raise ValueError('count error')

    @classmethod
    def parse_record(cls, line: str) -> 'Record':
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

        assert count == 9 + (len(data) * 2)
        record = cls(address, tag, data, checksum)
        return record

    @classmethod
    def build_data(cls, address: int, data: ByteString) -> 'Record':
        r"""Builds a data record.

        Arguments:
            address (:obj:`int`): Record start address.
            data (:obj:`bytes`): Some program data.

        Returns:
            :obj:`Record`: Data record.

        Example:
            >>> str(Record.build_data(0x12345678, b'Hello, World!'))
            '%236E081234567848656C6C6F2C20576F726C6421'
        """
        record = cls(address, cls.TAG_TYPE.DATA, data)
        return record

    @classmethod
    def build_terminator(cls, start: int) -> 'Record':
        r"""Builds a terminator record.

        Arguments:
            start (:obj:`int`): Program start address.

        Returns:
            :obj:`Record`: Terminator record.

        Example:
            >>> str(Record.build_terminator(0x12345678))
            '%0983D812345678'
        """
        record = cls(start, cls.TAG_TYPE.TERMINATOR, b'')
        return record

    @classmethod
    def split(cls, data: ByteString,
              address: int = 0,
              columns: int = 16,
              align: bool = True,
              standalone: bool = True,
              start: Optional[int] = None) \
            -> Iterator['Record']:
        r"""Splits a chunk of data into records.

        Arguments:
            data (:obj:`bytes`): Byte data to split.
            address (:obj:`int`): Start address of the first data record being
                split.
            columns (:obj:`int`): Maximum number of columns per data record.
                If ``None``, the whole `data` is put into a single record.
                Maximum of 128 columns.
            align (:obj:`bool`): Aligns record addresses to the column length.
            standalone (:obj:`bool`): Generates a sequence of records that can
                be saved as a standlone record file.
            start (:obj:`int`): Program start address.
                If ``None``, it is assigned the minimum data record address.

        Yields:
            :obj:`Record`: Data split into records.

        Raises:
            :obj:`ValueError` Address, size, or column overflow.
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        if not 0 < columns < 128:
            raise ValueError('column overflow')

        align_base = (address % columns) if align else 0
        offset = address
        for chunk in chop(data, columns, align_base):
            yield cls.build_data(offset, chunk)
            offset += len(chunk)

        if standalone:
            yield cls.build_terminator(address if start is None else start)

    @classmethod
    def build_standalone(cls, data_records: RecordSeq,
                         start: Optional[int] = None) \
            -> Iterator['Record']:
        r"""Makes a sequence of data records standalone.

        Arguments:
            data_records (:obj:`list` of :class:`Record`): A sequence of data
                records.
            start (:obj:`int`): Program start address.
                If ``None``, it is assigned the minimum data record address.

        Yields:
            :obj:`Record`: Records for a standalone record file.
        """
        for record in data_records:
            yield record

        if start is None:
            if not data_records:
                data_records = [cls.build_data(0, b'')]
            start = min(record.address for record in data_records)

        yield cls.build_terminator(start)

    @classmethod
    def check_sequence(cls, records: RecordSeq) -> None:
        super().check_sequence(records)

        if len(records) < 1:
            raise ValueError('missing terminator')

        for i in range(len(records) - 1):
            record = records[i]
            record.check()
            if record.tag != cls.TAG_TYPE.DATA:
                raise ValueError('tag error')

        record = records[-1]
        record.check()
        if record.tag != cls.TAG_TYPE.TERMINATOR:
            raise ValueError('missing terminator')
