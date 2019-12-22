# -*- coding: utf-8 -*-
import enum
from typing import Any
from typing import ByteString
from typing import Optional
from typing import Sequence
from typing import Union

from ..records import Record as _Record
from ..records import Tag as _Tag
from ..utils import chop
from ..utils import hexlify
from ..utils import unhexlify


@enum.unique
class Tag(_Tag):
    """Hexadecimal record tag."""

    @classmethod
    def is_data(cls, value: Union[int, 'Tag']) -> bool:
        r""":obj:`bool`: `value` is a data record tag."""
        return True


class Record(_Record):

    LINE_SEP = b''

    EXTENSIONS = ('.bin', '.dat', '.raw')

    def __init__(self, address: int,
                 tag: Tag,
                 data: ByteString,
                 checksum: Union[int, type(Ellipsis)] = Ellipsis) -> None:

        super().__init__(address, None, data, checksum)

    def __str__(self) -> str:
        text = hexlify(self.data)
        return text

    def is_data(self) -> bool:
        return True

    @classmethod
    def build_data(cls, address: int, data: ByteString) -> 'Record':
        r"""Builds a data record.

        Example:
            >>> Record.build_data(0x1234, b'Hello, World!')
            ... #doctest: +NORMALIZE_WHITESPACE
            Record(address=0x00001234, tag=0, count=13,
                         data=b'Hello, World!', checksum=0x69)
        """
        record = cls(address, None, data)
        return record

    @classmethod
    def parse_record(cls, line: str) -> Sequence['Record']:
        r"""Parses a hexadecimal record line.

        Warning:
            Since it parses raw hex data, it is not possible to set address
            to a value different than ``0``.

        Example:
            >>> line = '48656C6C 6F2C2057 6F726C64 21'
            >>> Record.parse_record(line)
            ... #doctest: +NORMALIZE_WHITESPACE
            Record(address=0x00000000, tag=0, count=13,
                         data=b'Hello, World!', checksum=0x69)
        """
        line = str(line).strip()
        data = unhexlify(line)
        return cls.unmarshal(data)

    def marshal(self) -> ByteString:
        return self.data

    @classmethod
    def unmarshal(cls, data: ByteString,
                  *args: Any,
                  **kwargs: Any) -> 'Record':

        address = kwargs.get('address', 0)
        record = cls.build_data(address, data)
        return record

    @classmethod
    def split(cls, data: ByteString,
              address: int = 0,
              columns: Optional[int] = None,
              align: bool = True,
              standalone: bool = True) -> Sequence['Record']:
        r"""Splits a chunk of data into records.

        Arguments:
            data (:obj:`bytes`): Byte data to split.
            address (:obj:`int`): Start address of the first data record being
                split.
            columns (:obj:`int`): Maximum number of columns per data record.
                If ``None``, the whole `data` is put into a single record.
            align (:obj:`int`): Byte Alignment of record start addresses.
            standalone (:obj:`bool`): Generates a sequence of records that can
                be saved as a standlone record file.

        Yields:
            :obj:`MotorolaRecord`: Data split into records.

        Raises:
            :obj:`ValueError` Address or size overflow.
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')

        if columns is None:
            yield cls.build_data(address, data)
        else:
            align_base = (address % columns) if align else 0
            for chunk in chop(data, columns, align_base):
                yield cls.build_data(address, chunk)
                address += len(chunk)
