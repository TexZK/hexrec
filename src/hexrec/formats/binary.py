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

r"""Binary format.

This format is actually used to hold binary chunks of raw data (`bytes`).
"""

from typing import Any
from typing import Iterator
from typing import Optional
from typing import Sequence
from typing import Type
from typing import Union

from ..records import Record as _Record
from ..records import Tag as _Tag
from ..utils import AnyBytes
from ..utils import check_empty_args_kwargs
from ..utils import chop
from ..utils import hexlify
from ..utils import unhexlify


class Record(_Record):
    r"""Binary record.

    This record type is actually just a container for binary data.

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

    TAG_TYPE: Optional[Type[_Tag]] = None
    r"""Associated Python class for tags."""

    LINE_SEP: Union[bytes, str] = b''
    r"""Separator between record lines.

    If subclass of :obj:`bytes`, it is considered as a binary file.
    """

    EXTENSIONS: Sequence[str] = ('.bin', '.dat', '.raw')
    r"""File extensions typically mapped to this record type."""

    def __init__(
        self: 'Record',
        address: int,
        tag: Optional[_Tag],
        data: AnyBytes,
        checksum: Union[int, type(Ellipsis)] = Ellipsis,
    ) -> None:
        super().__init__(address, tag, data, checksum)

    def __str__(
        self: 'Record',
    ) -> str:
        text = hexlify(self.data)
        return text

    def is_data(
        self: 'Record',
    ) -> bool:
        del self
        return True

    def check(
        self: 'Record',
    ) -> None:
        r"""Performs consistency checks.

        Raises:
            :obj:`ValueError`: a field is inconsistent.
        """
        if not 0 <= self.address:
            raise ValueError('address overflow')

        if self.tag is not None:
            raise ValueError('tag error')

        if self.data is None:
            raise ValueError('no data')

        if self.count != len(self.data):
            raise ValueError('count error')

        if self.checksum is not None:
            if not 0x00 <= self.checksum <= 0xFF:
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
                Data address.

            data (bytes):
                Record data.

        Returns:
            record: Data record.

        Example:
            >>> Record.build_data(0x1234, b'Hello, World!')
            ... #doctest: +NORMALIZE_WHITESPACE
            Record(address=0x00001234, tag=0, count=13,
                   data=b'Hello, World!', checksum=0x69)
        """
        record = cls(address, None, data)
        return record

    @classmethod
    def parse_record(
        cls: Type['Record'],
        line: str,
        *args: Any,
        **kwargs: Any,
    ) -> 'Record':
        r"""Parses a hexadecimal record line.

        Arguments:
            line (str):
                Text line to parse.

        Returns:
            record: Parsed record.

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
        check_empty_args_kwargs(args, kwargs)

        line = str(line).strip()
        data = unhexlify(line)
        return cls.unmarshal(data)

    def marshal(
        self: 'Record',
    ) -> AnyBytes:
        return self.data

    @classmethod
    def unmarshal(
        cls: Type['Record'],
        data: AnyBytes,
        *args: Any,
        address: int = 0,
        **kwargs: Any,
    ) -> 'Record':
        check_empty_args_kwargs(args, kwargs)

        record = cls.build_data(address, data)
        return record

    @classmethod
    def split(
        cls: Type['Record'],
        data: AnyBytes,
        address: int = 0,
        columns: Optional[int] = None,
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

            align (int):
                Aligns record addresses to such number.
                If ``Ellipsis``, its value is resolved after `columns`.

            standalone (bool):
                Generates a sequence of records that can be saved as a
                standalone record file.

        Yields:
            record: Data split into records.

        Raises:
            :obj:`ValueError`: Address or size overflow.
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        if align is Ellipsis:
            align = columns

        if columns is None:
            yield cls.build_data(address, data)
        else:
            align_base = (address % align) if align else 0
            for chunk in chop(data, columns, align_base):
                yield cls.build_data(address, chunk)
                address += len(chunk)
