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

r"""Motorola S-record format.

See Also:
    `<https://en.wikipedia.org/wiki/SREC_(file_format)>`_
"""

import enum
import re
from typing import Any
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Type
from typing import TypeVar
from typing import cast as _cast

from bytesparse import Memory

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


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='SrecTag')


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

    _DATA = DATA_16

    @classmethod
    def fit_count_tag(cls, count: int) -> Self:
        r"""Fits count record tag.

        Given the record sequence count, it fits the most compact *count* tag.

        Args:
            count (int):
                Record sequence *count*.

        Returns:
            :class:`SrecTag`: *Count* record tag.

        Raises:
            ValueError: invalid `count`.

        Examples:
            >>> from hexrec import SrecFile
            >>> SrecTag = SrecFile.Record.Tag
            >>> SrecTag.fit_count_tag(0xFFFF)
            <SrecTag.COUNT_16: 5>
            >>> SrecTag.fit_count_tag(0xFFFFFF)
            <SrecTag.COUNT_24: 6>
            >>> SrecTag.fit_count_tag(0x1000000)
            Traceback (most recent call last):
                ...
            ValueError: count overflow
        """

        if count < 0:
            raise ValueError('count overflow')
        if count <= 0xFFFF:
            return cls.COUNT_16
        if count <= 0xFFFFFF:
            return cls.COUNT_24
        raise ValueError('count overflow')

    @classmethod
    def fit_data_tag(cls, address_max: int) -> Self:
        r"""Fits data record tag.

        Given the maximum *address* of the involved *data* records, it fits the
        most compact *data* tag.

        Args:
            address_max (int):
                Maximum *address* of the involved *data* records.

        Returns:
            :class:`SrecTag`: *Data* record tag.

        Raises:
            ValueError: invalid `address_max`.

        Examples:
            >>> from hexrec import SrecFile
            >>> SrecTag = SrecFile.Record.Tag
            >>> SrecTag.fit_data_tag(0xFFFF)
            <SrecTag.DATA_16: 1>
            >>> SrecTag.fit_data_tag(0xFFFFFF)
            <SrecTag.DATA_24: 2>
            >>> SrecTag.fit_data_tag(0xFFFFFFFF)
            <SrecTag.DATA_32: 3>
            >>> SrecTag.fit_data_tag(0x100000000)
            Traceback (most recent call last):
                ...
            ValueError: address overflow
        """

        if address_max < 0:
            raise ValueError('address overflow')
        if address_max <= 0xFFFF:
            return cls.DATA_16
        if address_max <= 0xFFFFFF:
            return cls.DATA_24
        if address_max <= 0xFFFFFFFF:
            return cls.DATA_32
        raise ValueError('address overflow')

    @classmethod
    def fit_start_tag(cls, address: int) -> Self:
        r"""Fits data record tag.

        Given the *start address*, it fits the most compact *start address* tag.

        Args:
            address (int):
                Start address.

        Returns:
            :class:`SrecTag`: *Start address* record tag.

        Raises:
            ValueError: invalid `address`.

        Examples:
            >>> from hexrec import SrecFile
            >>> SrecTag = SrecFile.Record.Tag
            >>> SrecTag.fit_start_tag(0xFFFF)
            <SrecTag.START_16: 9>
            >>> SrecTag.fit_start_tag(0xFFFFFF)
            <SrecTag.START_24: 8>
            >>> SrecTag.fit_start_tag(0xFFFFFFFF)
            <SrecTag.START_32: 7>
            >>> SrecTag.fit_start_tag(0x100000000)
            Traceback (most recent call last):
                ...
            ValueError: address overflow
        """

        if address < 0:
            raise ValueError('address overflow')
        if address <= 0xFFFF:
            return cls.START_16
        if address <= 0xFFFFFF:
            return cls.START_24
        if address <= 0xFFFFFFFF:
            return cls.START_32
        raise ValueError('address overflow')

    def get_address_max(self) -> Optional[int]:
        r"""Calculates the maximum address.

        It calculates the maximum *address* field for the calling tag.
        If the *address* field is not supported, it returns ``None``.

        Returns:
            int: Maximum *address* value, or ``None``.

        Examples:
            >>> from hexrec import SrecFile
            >>> SrecTag = SrecFile.Record.Tag
            >>> hex(SrecTag.DATA_32.get_address_max())
            '0xffffffff'
            >>> hex(SrecTag.START_32.get_address_max())
            '0xffffffff'
            >>> hex(SrecTag.COUNT_24.get_address_max())
            '0xffffff'
            >>> SrecTag.RESERVED.get_address_max()
            0
        """

        mask = self.get_address_size()
        if mask:
            mask = (1 << (mask << 3)) - 1
        return mask

    def get_address_size(self) -> Optional[int]:
        r"""Calculates the maximum address size.

        It calculates the maximum *address* field size for the calling tag.
        If the *address* field is not supported, it returns zero.

        Returns:
            int: Maximum *address* size, or ``None``.

        Examples:
            >>> from hexrec import SrecFile
            >>> SrecTag = SrecFile.Record.Tag
            >>> SrecTag.DATA_32.get_address_size()
            4
            >>> SrecTag.START_32.get_address_size()
            4
            >>> SrecTag.COUNT_24.get_address_size()
            3
            >>> SrecTag.RESERVED.get_address_size()
            0
        """

        SIZES = (2, 2, 3, 4, 0, 2, 3, 4, 3, 2)
        size = SIZES[self]
        return size

    def get_data_max(self) -> Optional[int]:
        r"""Calculates the maximum data size.

        It calculates the maximum *data* field size for the calling tag.
        If the *data* field is not supported, it returns ``None``.

        Returns:
            int: Maximum *data* size, or ``None``.

        Examples:
            >>> from hexrec import SrecFile
            >>> SrecTag = SrecFile.Record.Tag
            >>> SrecTag.DATA_16.get_data_max()
            252
            >>> SrecTag.DATA_32.get_data_max()
            250
            >>> SrecTag.START_32.get_data_max()
            0
        """

        SIZES = (2, 2, 3, 4, 0, 0, 0, 0, 0, 0)
        size = SIZES[self]
        if size:
            size = 0xFE - size
        return size

    def get_tag_match(self) -> Optional['SrecTag']:
        r"""Calculates the matching tag.

        Given *data* or *start address* records, it returns the matching tag.

        Returns:
            :class:`SrecTag`: Matching tag for *self*, or ``None``

        Examples:
            >>> from hexrec import SrecFile
            >>> SrecTag = SrecFile.Record.Tag
            >>> SrecTag.DATA_16.get_tag_match()
            <SrecTag.START_16: 9>
            >>> SrecTag.START_32.get_tag_match()
            <SrecTag.DATA_32: 3>
            >>> SrecTag.HEADER.get_tag_match() is None
            True
        """

        MATCHES = (None, 9, 8, 7, None, None, None, 3, 2, 1)
        match = MATCHES[self]
        if match is None:
            return None
        tag_type = type(self)
        return tag_type(match)

    def is_count(self) -> bool:
        r"""Tells whether this is a record count tag.

        This method returns true if this record tag is used for *record count*
        records.

        Returns:
            bool: This is a record count tag.

        Examples:
            >>> from hexrec import SrecFile
            >>> SrecTag = SrecFile.Record.Tag
            >>> SrecTag.COUNT_16.is_count()
            True
            >>> SrecTag.COUNT_24.is_count()
            True
            >>> SrecTag.DATA_16.is_count()
            False
        """

        return ((self == self.COUNT_16) or
                (self == self.COUNT_24))

    def is_data(self) -> bool:
        r"""Tells whether this is a data record tag.

        This method returns true if this record tag is used for *data* records.

        Returns:
            bool: This is a data record tag.

        Examples:
            >>> from hexrec import SrecFile
            >>> SrecTag = SrecFile.Record.Tag
            >>> SrecTag.DATA_16.is_data()
            True
            >>> SrecTag.DATA_32.is_data()
            True
            >>> SrecTag.HEADER.is_data()
            False
        """

        return ((self == self.DATA_16) or
                (self == self.DATA_24) or
                (self == self.DATA_32))

    def is_file_termination(self) -> bool:

        return self.is_start()

    def is_header(self) -> bool:
        r"""Tells whether this is a header record tag.

        This method returns true if this record tag is used for *header*
        records.

        Returns:
            bool: This is a header record tag.

        Examples:
            >>> from hexrec import SrecFile
            >>> SrecTag = SrecFile.Record.Tag
            >>> SrecTag.HEADER.is_header()
            True
            >>> SrecTag.DATA_16.is_header()
            False
        """

        return self == self.HEADER

    def is_start(self) -> bool:
        r"""Tells whether this is a start address record tag.

        This method returns true if this record tag is used for *start address*
        records.

        Returns:
            bool: This is a start address record tag.

        Examples:
            >>> from hexrec import SrecFile
            >>> SrecTag = SrecFile.Record.Tag
            >>> SrecTag.START_16.is_start()
            True
            >>> SrecTag.START_32.is_start()
            True
            >>> SrecTag.DATA_16.is_start()
            False
        """

        return ((self == self.START_16) or
                (self == self.START_24) or
                (self == self.START_32))


SIZE_TO_ADDRESS_FORMAT: Mapping[int, bytes] = {
    2: b'%04X',
    3: b'%06X',
    4: b'%08X',
}
r"""Format byte string for each supported address size."""


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='SrecRecord')


class SrecRecord(BaseRecord):
    r"""Motorola S-record record object."""

    Tag: Type[SrecTag] = SrecTag

    LINE1_REGEX = re.compile(
        b'^(?P<before>\\s*)[Ss]'
        b'(?P<tag>[0-9A-Fa-f])'
        b'(?P<count>[0-9A-Fa-f]{2})'
    )
    r"""Line parser regex, part 1."""

    LINE2_REGEX = [re.compile(
        b'^(?P<address>[0-9A-Fa-f]{%d})' % (4 + (i * 2))
    ) for i in range(3)]
    r"""Line parser regex, part 2."""

    LINE3_REGEX = re.compile(
        b'^(?P<data>([0-9A-Fa-f]{2})*)'
        b'(?P<checksum>[0-9A-Fa-f]{2})'
        b'(?P<after>[^\\r\\n]*)\\r?\\n?$'
    )
    r"""Line parser regex, part 3."""

    def compute_checksum(self) -> int:

        checksum = self.count & 0xFF
        address = self.address & 0xFFFFFFFF
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
    def create_count(
        cls,
        count: int,
        tag: Optional[SrecTag] = None,
    ) -> Self:
        r"""Creates a record count record.

        This is method instantiates a *record count* record, optionally
        choosing the desired count size.

        Args:
            count (int):
                Number of preceding *data* records.

            tag (:class:`SrecTag`):
                Chosen *record count* tag.
                If ``None``, it uses the one returned by
                :meth:`SrecTag.fit_count_tag`.

        Returns:
            :class:`SrecRecord`: Record count record object.

        Examples:
            >>> from hexrec import SrecFile
            >>> record = SrecFile.Record.create_count(0x1234)
            >>> str(record)
            'S5031234B6\r\n'
            >>> tag = SrecFile.Record.Tag.COUNT_24
            >>> record = SrecFile.Record.create_count(0x1234, tag=tag)
            >>> str(record)
            'S604001234B5\r\n'
        """

        Tag = cls.Tag
        if tag is None:
            tag = Tag.fit_count_tag(count)
        else:
            if not Tag.COUNT_16 <= tag <= Tag.COUNT_24:
                raise ValueError('invalid count tag')

        if not 0 <= count <= tag.get_address_max():
            raise ValueError('count overflow')

        record = cls(tag, address=count)
        return record

    @classmethod
    def create_data(
        cls,
        address: int,
        data: AnyBytes,
        tag: Optional[SrecTag] = None,
    ) -> Self:
        r"""Creates a data record.

        This is method instantiates a *data* record, optionally choosing the
        desired address size.

        Args:
            address (int):
                Record address.

            data (bytes):
                Record byte data.

            tag (:class:`SrecTag`):
                Chosen *data* tag.
                If ``None``, it uses the one returned by
                :meth:`SrecTag.fit_data_tag`.

        Returns:
            :class:`SrecRecord`: Data record object.

        Examples:
            >>> from hexrec import SrecFile
            >>> record = SrecFile.Record.create_data(0x1234, b'abc')
            >>> str(record)
            'S10612346162638D\r\n'
            >>> tag = SrecFile.Record.Tag.DATA_32
            >>> record = SrecFile.Record.create_data(0x1234, b'abc', tag=tag)
            >>> str(record)
            'S308000012346162638B\r\n'
        """

        Tag = cls.Tag
        if tag is None:
            tag = Tag.fit_data_tag(address)
        else:
            if not Tag.DATA_16 <= tag <= Tag.DATA_32:
                raise ValueError('invalid data tag')

        if not 0 <= address <= tag.get_address_max():
            raise ValueError('address overflow')

        if len(data) > tag.get_data_max():
            raise ValueError('data size overflow')

        record = cls(tag, address=address, data=data)
        return record

    @classmethod
    def create_header(cls, data: AnyBytes = b'') -> Self:
        r"""Creates a header record.

        Args:
            data (bytes):
                Header byte data.

        Returns:
            :class:`IhexRecord`: Header record.

        Raises:
            ValueError: data size overflow.

        Examples:
            >>> from hexrec import SrecFile
            >>> record = SrecFile.Record.create_header()
            >>> str(record)
            'S0030000FC\r\n'
            >>> record = SrecFile.Record.create_header(b'HDR\0')
            >>> str(record)
            'S0070000484452001A\r\n'
        """

        if len(data) > 0xFC:
            raise ValueError('data size overflow')

        Tag = cls.Tag
        record = cls(Tag.HEADER, data=data)
        return record

    @classmethod
    def create_start(
        cls,
        address: int = 0,
        tag: Optional[SrecTag] = None,
    ) -> Self:
        r"""Creates a start address record.

        This is method instantiates a *start address* record, optionally
        choosing the desired address size.

        Args:
            address (int):
                Start address.

            tag (:class:`SrecTag`):
                Chosen *start* tag.
                If ``None``, it uses the one matching
                :meth:`SrecTag.fit_start_tag`.

        Returns:
            :class:`SrecRecord`: Start address record object.

        Examples:
            >>> from hexrec import SrecFile
            >>> record = SrecFile.Record.create_start(0x1234)
            >>> str(record)
            'S9031234B6\r\n'
            >>> tag = SrecFile.Record.Tag.START_32
            >>> record = SrecFile.Record.create_start(0x1234, tag=tag)
            >>> str(record)
            'S70500001234B4\r\n'
        """

        Tag = cls.Tag
        if tag is None:
            tag = Tag.fit_start_tag(address)
        else:
            if not Tag.START_32 <= tag <= Tag.START_16:
                raise ValueError('invalid start tag')

        if not 0 <= address <= tag.get_address_max():
            raise ValueError('address overflow')

        record = cls(tag, address=address)
        return record

    @classmethod
    def parse(
        cls,
        line: AnyBytes,
        validate: bool = True,
    ) -> Self:

        Tag = cls.Tag
        line = memoryview(line)

        match = cls.LINE1_REGEX.match(line)
        if not match:
            raise ValueError('syntax error')
        groups = match.groupdict()
        before = groups['before']
        tag = Tag(int(groups['tag'], 16))
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
        data = unhexlify(groups['data'])
        checksum = int(groups['checksum'], 16)
        after = groups['after']

        record = cls(tag,
                     address=address,
                     data=data,
                     count=count,
                     checksum=checksum,
                     before=before,
                     after=after,
                     validate=validate)
        return record

    def to_bytestr(self, end: AnyBytes = b'\r\n') -> bytes:

        self.validate(checksum=False, count=False)
        tag = _cast(SrecTag, self.tag)
        addrfmt = SIZE_TO_ADDRESS_FORMAT[tag.get_address_size()]

        bytestr = b'%sS%X%02X%s%s%02X%s%s' % (
            self.before,
            tag & 0xF,
            (self.count or 0) & 0xFF,
            addrfmt % (self.address & 0xFFFFFFFF),
            hexlify(self.data),
            (self.checksum or 0) & 0xFF,
            self.after,
            end,
        )
        return bytestr

    def to_tokens(self, end: AnyBytes = b'\r\n') -> Mapping[str, bytes]:

        self.validate(checksum=False, count=False)
        tag = _cast(SrecTag, self.tag)
        addrfmt = SIZE_TO_ADDRESS_FORMAT[tag.get_address_size()]

        return {
            'before': self.before,
            'begin': b'S',
            'tag': b'%X' % (tag & 0xF),
            'count': b'%02X' % ((self.count or 0) & 0xFF),
            'address': addrfmt % (self.address & 0xFFFFFFFF),
            'data': hexlify(self.data),
            'checksum': b'%02X' % ((self.checksum or 0) & 0xFF),
            'after': self.after,
            'end': end,
        }

    def validate(
        self,
        checksum: bool = True,
        count: bool = True,
    ) -> Self:

        super().validate(checksum=checksum, count=count)
        address = self.address

        # if self.after and not self.after.isspace():
        #     raise ValueError('junk after')

        if self.before and not self.before.isspace():
            raise ValueError('junk before')

        if self.checksum is not None:
            if not 0 <= self.checksum <= 0xFF:
                raise ValueError('checksum overflow')

        if self.count is not None:
            if not 3 <= self.count <= 0xFF:
                raise ValueError('count overflow')

        Tag = _cast(SrecTag, self.Tag)
        tag = _cast(SrecTag, self.tag)
        if tag == Tag.RESERVED:
            raise ValueError('reserved tag')

        data_size = len(self.data)

        if not Tag.HEADER <= tag <= Tag.DATA_32:
            if data_size:
                raise ValueError('unexpected data')

        if data_size > tag.get_data_max():
            raise ValueError('data size overflow')

        if not 0 <= address <= tag.get_address_max():
            raise ValueError('address overflow')

        return self


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='SrecFile')


class SrecFile(BaseFile):
    r"""Motorola S-record file object."""

    FILE_EXT: Sequence[str] = [
        # https://en.wikipedia.org/wiki/SREC_(file_format)
        '.s19', '.s28', '.s37', '.s',
        '.s1', '.s2', '.s3', '.sx',
        '.srec', '.exo', '.mot', '.mxt',
    ]

    META_KEYS: Sequence[str] = [
        'header',
        'maxdatalen',
        'startaddr',
    ]

    Record: Type[SrecRecord] = SrecRecord

    def __init__(self):

        super().__init__()

        self._header: Optional[AnyBytes] = b''
        self._startaddr: int = 0

    def apply_records(self) -> Self:

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
        r"""bytes: Header byte string.

        This property sets the file *header* byte string; ``None`` to disable.

        This is usually taken into account by :meth:`update_records` while
        splitting :attr:`memory` into :attr:`records`.

        Setting a different value triggers :meth:`discard_records`.

        Raises:
            ValueError: data size overflow.

        See Also:
            :meth:`update_records`
            :meth:`discard_records`

        Examples:
            >>> from hexrec import SrecFile
            >>> file = SrecFile()
            >>> file.header
            b''
            >>> _ = file.print()
            S0030000FC
            S5030000FC
            S9030000FC
            >>> file.header = b'HDR\0'
            >>> _ = file.print()
            S0070000484452001A
            S5030000FC
            S9030000FC
            >>> file.header = None
            >>> _ = file.print()
            S5030000FC
            S9030000FC
        """

        if self._memory is None:
            self.apply_records()
        return self._header

    @header.setter
    def header(self, header: Optional[AnyBytes]) -> None:

        if header is not None:
            size = len(header)
            if size > self.Record.Tag.HEADER.get_data_max():
                raise ValueError('data size overflow')

        if header != self._header:
            self.discard_records()
        self._header = header

    @property
    def startaddr(self) -> int:
        r"""Start address.

        This property sets the *start address* of the serialized record file.

        This is usually taken into account by :meth:`update_records` while
        splitting :attr:`memory` into :attr:`records`.

        Setting a different value triggers :meth:`discard_records`.

        Examples:
            >>> from hexrec import SrecFile
            >>> file = SrecFile()
            >>> file.startaddr
            0
            >>> _ = file.print()
            S0030000FC
            S5030000FC
            S9030000FC
            >>> file.startaddr = 0x87654321
            >>> _ = file.print()
            S0030000FC
            S5030000FC
            S70587654321AA
        """

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
        align: bool = False,
        header: bool = True,
        data: bool = False,
        count: bool = True,
        start: bool = True,
        data_tag: Optional[SrecTag] = None,
        count_tag: Optional[SrecTag] = None,
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

            header (bool):
                Generates the *header* record if :attr:`header`.

            data (bool):
                Requires at least one *data* record be present, even if empty.

            count (bool):
                Generates the *count* record.

            start (bool):
                Generates the *start address* record.

            data_tag (:class:`SrecTag`):
                Specific *data* record tag to use.

            count_tag (:class:`SrecTag`git):
                Specific *count* record tag to use.

        Returns:
            :class:`SrecFile`: *self*.

        Raises:
            ValueError: :attr:`memory` attribute not populated.

        See Also:
            :attr:`records`
            :attr:`memory`
            :meth:`get_meta`
            :meth:`apply_records`

        Examples:
            >>> from hexrec import SrecFile
            >>> blocks = [[123, b'abc']]
            >>> file = SrecFile.from_blocks(blocks, maxdatalen=16, startaddr=456)
            >>> file.memory.to_blocks()
            [[123, b'abc']]
            >>> file.get_meta()
            {'header': b'', 'maxdatalen': 16, 'startaddr': 456}
            >>> _ = file.update_records()
            >>> len(file.records)
            4
            >>> _ = file.print()
            S0030000FC
            S106007B61626358
            S5030001FB
            S90301C833
        """

        memory = self._memory
        if memory is None:
            raise ValueError('memory instance required')

        records = []
        Record = self.Record
        Tag = Record.Tag
        if data_tag is None:
            address_max = max(0, memory.endin) if memory else self.startaddr
            data_tag = Tag.fit_data_tag(address_max)
        chunk_views = []
        data_record_count = 0
        try:
            if header and self._header is not None:
                record = Record.create_header(self._header)
                records.append(record)

            for chunk_start, chunk_view in memory.chop(self.maxdatalen, align=align):
                chunk_views.append(chunk_view)
                chunk_data = bytes(chunk_view)
                record = Record.create_data(chunk_start, chunk_data, tag=data_tag)
                records.append(record)
                data_record_count += 1

            if data and not data_record_count:
                record = Record.create_data(0, b'', tag=data_tag)
                records.append(record)
                data_record_count += 1

            if count:
                if count_tag is None:
                    count_tag = Tag.fit_count_tag(data_record_count)
                record = Record.create_count(data_record_count, tag=count_tag)
                records.append(record)

            start_tag = data_tag.get_tag_match()
            address = self._startaddr if start else 0
            record = Record.create_start(address, tag=start_tag)
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
        header_first: bool = True,
        data_ordering: bool = False,
        data_uniform: bool = True,
        count_required: bool = False,
        count_penultimate: bool = True,
        start_last: bool = True,
        start_within_data: bool = False,
    ) -> Self:
        r"""Validates records.

        It performs consistency checks for the underlying :attr:`records`.

        Args:
            header_required (bool):
                Requires the *header* record be present.

            header_first (bool):
                Requires the *header* record be the first of the sequence.

            data_ordering (bool):
                Checks that the *data* record sequence has monotonically
                increasing addresses, without any overlapping.

            data_uniform (bool):
                Requires *data* records have the same tag.

            count_required (bool):
                Requires the *count* record be present.

            count_penultimate (bool):
                Requires the *start address* record be the penultimate one.

            start_last (bool):
                Requires the *start address* record be the last of the sequence.

            start_within_data (bool):
                Requires *start address* fall within data carried by some
                *data* record.

        Returns:
            :class:`SrecFile`: *self*.

        Raises:
            ValueError: Invalid record sequence.

        Examples:
            >>> from hexrec import SrecFile
            >>> records = [SrecFile.Record.create_data(123, b'abc')]
            >>> file = SrecFile.from_records(records)
            >>> _ = file.validate_records()
            Traceback (most recent call last):
                ...
            ValueError: missing start record
        """

        records = self._records
        if records is None:
            raise ValueError('records required')

        header_record = None
        start_record = None
        count_record = None
        last_data_endex = 0
        data_tag_sample = None
        data_count = 0

        for index, record in enumerate(records):
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

                if count_penultimate:
                    if index != len(records) - 2:
                        raise ValueError('count record not penultimate')

            elif tag.is_start():
                if start_record is not None:
                    raise ValueError('multiple start records')
                start_record = record

                if start_last:
                    if index != len(records) - 1:
                        raise ValueError('start record not last')

            else:  # elif tag.is_header():
                if header_first:
                    if index != 0:
                        raise ValueError('header record not first')
                header_record = record

        if header_required:
            if header_record is None:
                raise ValueError('missing header record')

        if count_required:
            if count_record is None:
                raise ValueError('missing count record')

        if start_record is None:
            raise ValueError('missing start record')

        if start_within_data:
            startaddr = start_record.address
            start_datum = self.memory.peek(startaddr)
            if start_datum is None:
                raise ValueError('no data at start address')

        if data_uniform:
            if start_record.tag != data_tag_sample.get_tag_match():
                raise ValueError('start record tag not uniform')

        return self


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
