# Copyright (c) 2013-2023, Andrea Zoppi
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

# TODO: module docs

import abc
import os
import sys
from typing import IO
from typing import Any
from typing import List
from typing import Literal
from typing import Mapping
from typing import MutableMapping
from typing import MutableSequence
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import Union
from typing import cast as _cast

import colorama
from bytesparse import Memory
from bytesparse.base import ImmutableMemory
from bytesparse.base import MutableMemory

from .utils import AnyBytes
from .utils import EllipsisType


FILE_TYPES: MutableMapping[str, Type['BaseFile']] = {}
r"""Registered record file types."""


TOKEN_COLOR_CODES: Mapping[str, bytes] = {
    '<':        colorama.Style.RESET_ALL.encode(),
    '>':        colorama.Style.RESET_ALL.encode(),
    'address':  colorama.Fore.RED.encode(),
    'addrlen':  colorama.Fore.YELLOW.encode(),
    'after':    colorama.Style.RESET_ALL.encode(),
    'before':   colorama.Style.RESET_ALL.encode(),
    'begin':    colorama.Fore.YELLOW.encode(),
    'checksum': colorama.Fore.MAGENTA.encode(),
    'count':    colorama.Fore.BLUE.encode(),
    'data':     colorama.Fore.CYAN.encode(),
    'dataalt':  colorama.Fore.LIGHTCYAN_EX.encode(),
    'end':      colorama.Style.RESET_ALL.encode(),
    'tag':      colorama.Fore.GREEN.encode(),
}


def colorize_tokens(
    tokens: Mapping[str, bytes],
    altdata: bool = True,
) -> Mapping[str, bytes]:
    # TODO: __doc__

    # noinspection PyDictCreation
    colorized = {}
    colorized['<'] = TOKEN_COLOR_CODES['<']

    for key, value in tokens.items():
        if value:
            code = TOKEN_COLOR_CODES[key]

            if key == 'data' and altdata:
                altcode = TOKEN_COLOR_CODES['dataalt']
                buffer = bytearray()

                for i in range(0, len(value), 2):
                    buffer.extend(altcode if i & 2 else code)
                    buffer.append(value[i])
                    buffer.append(value[i + 1])

                colorized[key] = bytes(buffer)
            else:
                colorized[key] = code + value

    colorized['>'] = TOKEN_COLOR_CODES['>']
    return colorized


def guess_type_name(file_path: str) -> str:
    # TODO: __doc__

    file_ext = os.path.splitext(file_path)[1]
    names_found = []

    for name in FILE_TYPES.keys():
        file_type = FILE_TYPES[name]

        if file_ext in file_type.FILE_EXT:
            names_found.append(name)

    if not names_found:
        raise ValueError(f'extension not found: {file_ext!r}')

    if len(names_found) == 1:
        return names_found[0]

    has_raw = 'raw' in names_found
    if has_raw:
        names_found.remove('raw')
    names_found.sort()

    for name in names_found:
        file_type = FILE_TYPES[name]
        try:
            with open(file_path, 'rb') as stream:
                file_type.parse(stream)
            return name
        except Exception:
            pass

    if has_raw:
        return 'raw'
    raise ValueError(f'cannot guess record file type')


def guess_type_class(file_path: str) -> Type['BaseFile']:
    # TODO: __doc__

    name = guess_type_name(file_path)
    return FILE_TYPES[name]


# TODO: class RecordError
# embeds also information about line, field, etc


class BaseTag:
    # TODO: __doc__

    def is_data(self) -> bool:
        # TODO: __doc__

        return False


class BaseRecord(abc.ABC):
    # TODO: __doc__

    META_KEYS: Sequence[str] = [
        'address',
        'after',
        'before',
        'checksum',
        'coords',
        'count',
        'data',
        'tag',
    ]

    TAG_TYPE: Type[BaseTag] = None  # override
    # TODO: __doc__

    def __bytes__(self) -> bytes:
        # TODO: __doc__

        return self.to_bytestr()

    def __init__(
        self,
        tag: BaseTag,
        address: int = 0,
        data: AnyBytes = b'',
        count: Optional[Union[int, EllipsisType]] = Ellipsis,
        checksum: Optional[Union[int, EllipsisType]] = Ellipsis,
        before: Union[bytes, bytearray] = b'',
        after: Union[bytes, bytearray] = b'',
        coords: Tuple[int, int] = (-1, -1),
    ):

        self.address: int = address.__index__()
        self.after: Union[bytes, bytearray] = after
        self.before: Union[bytes, bytearray] = before
        self.checksum: Optional[int] = None
        self.coords: Tuple[int, int] = coords
        self.count: Optional[int] = None
        self.data: AnyBytes = data
        self.tag: BaseTag = tag

        if count is Ellipsis:
            self.update_count()
        elif count is not None:
            self.count = count.__index__()

        if checksum is Ellipsis:
            self.update_checksum()
        elif checksum is not None:
            self.checksum = checksum.__index__()

    def __str__(self) -> str:
        # TODO: __doc__

        return self.to_bytestr().decode()

    @abc.abstractmethod
    def compute_checksum(self) -> int:
        # TODO: __doc__
        ...

    @abc.abstractmethod
    def compute_count(self) -> int:
        # TODO: __doc__
        ...

    def copy(self) -> 'BaseRecord':  # shallow
        # TODO: __doc__

        meta = self.get_meta()
        tag = meta.pop('tag')
        cls = type(self)
        return cls(tag, **meta)

    def data_to_int(
        self,
        byteorder: Literal['big', 'little'] = 'big',
        signed: bool = False,
    ) -> int:
        # TODO: __doc__

        value = int.from_bytes(self.data, byteorder=byteorder, signed=signed)
        return value

    def get_meta(self) -> MutableMapping[str, Any]:
        # TODO: __doc__

        meta = {key: getattr(self, key) for key in self.META_KEYS}
        return meta

    @classmethod
    @abc.abstractmethod
    def parse(cls, line: AnyBytes) -> 'BaseRecord':
        # TODO: __doc__
        ...

    def print(
        self,
        stream: Optional[IO] = None,
        color: bool = False,
    ) -> 'BaseRecord':
        # TODO: __doc__

        tokens = self.to_tokens()
        if color:
            tokens = colorize_tokens(tokens)
        text = ''.join(token.decode() for token in tokens.values())
        print(text, file=stream, end='')
        return self

    def serialize(self, stream: IO, *args, **kwargs) -> 'BaseRecord':
        # TODO: __doc__

        stream.write(self.to_bytestr(*args, **kwargs))
        return self

    @abc.abstractmethod
    def to_bytestr(self, *args, **kwargs) -> bytes:
        # TODO: __doc__
        ...

    @abc.abstractmethod
    def to_tokens(self, *args, **kwargs) -> Mapping[str, bytes]:
        # TODO: __doc__
        ...

    def update_checksum(self) -> 'BaseRecord':
        # TODO: __doc__

        self.checksum = self.compute_checksum()
        return self

    def update_count(self) -> 'BaseRecord':
        # TODO: __doc__

        self.count = self.compute_count()
        return self

    def validate(self) -> 'BaseRecord':
        # TODO: __doc__

        if self.address < 0:
            raise ValueError('negative address')

        if self.checksum is None:
            raise ValueError('null checksum')

        if self.checksum != self.compute_checksum():
            raise ValueError('wrong checksum')

        if self.count is None:
            raise ValueError('null count')

        if self.count < 0:
            raise ValueError('negative count')

        if self.count != self.compute_count():
            raise ValueError('wrong count')

        if self.tag not in self.TAG_TYPE:
            raise ValueError('invalid tag')

        if self.data is None:
            raise ValueError('no data')

        return self


class BaseFile(abc.ABC):
    # TODO: __doc__

    DEFAULT_DATALEN: int = 16
    # TODO: __doc__

    FILE_EXT: Sequence[str] = []
    # TODO: __doc__

    META_KEYS: Sequence[str] = ['maxdatalen']
    # TODO: __doc__

    RECORD_TYPE: Type[BaseRecord] = None  # override
    # TODO: __doc__

    def __add__(
        self,
        other: Union['BaseFile', AnyBytes],
    ) -> 'BaseFile':
        # TODO: __doc__

        return self.copy().extend(other)

    def __getitem__(self, key: Union[slice, int]) -> Union[bytes, int, None]:
        # TODO: __doc__

        item = self.memory[key]
        if isinstance(key, slice):
            item = bytes(item)
        return item

    def __iadd__(
        self,
        other: Union['BaseFile', AnyBytes],
    ) -> 'BaseFile':
        # TODO: __doc__

        return self.extend(other)

    def __init__(self):

        self._records: Optional[MutableSequence[BaseRecord]] = None
        self._memory: Optional[MutableMemory] = Memory()
        self._maxdatalen: int = self.DEFAULT_DATALEN

    def __ior__(self, other: 'BaseFile') -> 'BaseFile':
        # TODO: __doc__

        return self.merge(other)

    def __or__(self, other: 'BaseFile') -> 'BaseFile':
        # TODO: __doc__

        return self.copy().merge(other)

    def append(self, item: Union[AnyBytes, int]) -> 'BaseFile':
        # TODO: __doc__

        self.memory.append(item)
        self.discard_records()
        return self

    def apply_records(self) -> 'BaseFile':
        # TODO: __doc__

        if self._records is None:
            raise ValueError('records required')

        memory = Memory()

        for record in self._records:
            if record.tag.is_data():
                memory.write(record.address, record.data)

        self.discard_memory()
        self._memory = memory
        return self

    def clear(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
    ) -> 'BaseFile':
        # TODO: __doc__

        self.memory.clear(start=start, endex=endex)
        self.discard_records()
        return self

    @classmethod
    def convert(
        cls,
        other: 'BaseFile',
        copy: bool = False,
        meta: bool = True,
    ) -> 'BaseFile':
        # TODO: __doc__

        converted_memory = other.memory
        if copy:
            converted_memory = converted_memory.copy()

        if meta:
            other_meta = other.get_meta()
            converted_meta = {key: other_meta[key]
                              for key in cls.META_KEYS
                              if key in other_meta}
        else:
            converted_meta = {}

        converted = cls.from_memory(memory=converted_memory, **converted_meta)
        return converted

    def copy(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
        records: bool = False,
        memory: bool = True,
        meta: bool = True,
    ) -> 'BaseFile':
        # TODO: __doc__

        other_records = None
        if records:
            other_records = [record.copy() for record in self.records]

        other_memory = None
        if memory:
            other_memory = self.memory.extract(start=start, endex=endex, bound=False)

        other_meta = self.get_meta() if meta else {}

        other = self.from_memory(memory=other_memory, **other_meta)
        other._records = other_records
        return other

    def crop(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
    ) -> 'BaseFile':
        # TODO: __doc__

        self.memory.crop(start=start, endex=endex)
        self.discard_records()
        return self

    def cut(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
        meta: bool = False,
    ) -> 'BaseFile':
        # TODO: __doc__

        memory = self.memory.cut(start=start, endex=endex, bound=False)
        memory = _cast(MutableMemory, memory)
        other = self.copy(records=False, memory=False, meta=meta)
        other._memory = memory
        self.discard_records()
        return other

    def delete(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
    ) -> 'BaseFile':
        # TODO: __doc__

        self.memory.delete(start=start, endex=endex)
        self.discard_records()
        return self

    def discard_records(self, release_views: bool = True) -> 'BaseFile':
        # TODO: __doc__

        if release_views and self._records:
            for record in self._records:
                if isinstance(record.data, memoryview):
                    record.data.release()

        self._records = None
        if self._memory is None:
            self._memory = Memory()
        return self

    def discard_memory(self) -> 'BaseFile':
        # TODO: __doc__

        self._memory = None
        if self._records is None:
            self._memory = Memory()
        return self

    def extend(
        self,
        other: Union['BaseFile', ImmutableMemory, AnyBytes],
    ) -> 'BaseFile':
        # TODO: __doc__

        if isinstance(other, BaseFile):
            other = other.memory
        self.memory.extend(other)
        self.discard_records()
        return self

    def fill(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
        pattern: Union[int, AnyBytes] = 0,
    ) -> 'BaseFile':
        # TODO: __doc__

        self.memory.fill(start=start, endex=endex, pattern=pattern)
        self.discard_records()
        return self

    def find(
        self,
        item: Union[AnyBytes, int],
        start: Optional[int] = None,
        endex: Optional[int] = None,
    ) -> int:
        # TODO: __doc__

        offset = self.memory.find(item, start=start, endex=endex)
        return offset

    def flood(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
        pattern: Union[int, AnyBytes] = 0,
    ) -> 'BaseFile':
        # TODO: __doc__

        self.memory.flood(start=start, endex=endex, pattern=pattern)
        self.discard_records()
        return self

    @classmethod
    def from_records(cls, records: MutableSequence[BaseRecord]) -> 'BaseFile':
        # TODO: __doc__

        if records:
            maxdatalen = max(len(r.data) for r in records if r.tag.is_data())
            if maxdatalen < 1:
                maxdatalen = cls.DEFAULT_DATALEN
        else:
            maxdatalen = cls.DEFAULT_DATALEN

        file = cls()
        file._records = records
        file._memory = None
        file._maxdatalen = maxdatalen
        return file

    @classmethod
    def from_memory(cls, memory: Optional[MutableMemory] = None, **meta) -> 'BaseFile':
        # TODO: __doc__

        file = cls()

        if memory is not None:
            file._memory = memory

        for key, value in meta.items():
            if key in cls.META_KEYS:
                setattr(file, key, value)
            else:
                raise KeyError(f'invalid meta: {key}')

        return file

    def get_address_max(self) -> int:
        # TODO: __doc__

        return self.memory.endin

    def get_address_min(self) -> int:
        # TODO: __doc__

        return self.memory.start

    def get_holes(self) -> List[Tuple[int, int]]:
        # TODO: __doc__

        memory = self.memory
        holes = list(memory.gaps(memory.start, memory.endex))
        return holes

    def get_spans(self) -> List[Tuple[int, int]]:
        # TODO: __doc__

        spans = list(self.memory.intervals())
        return spans

    def get_meta(self) -> Mapping[str, Any]:
        # TODO: __doc__

        meta = {key: getattr(self, key) for key in self.META_KEYS}
        return meta

    def index(
        self,
        item: Union[AnyBytes, int],
        start: Optional[int] = None,
        endex: Optional[int] = None,
    ) -> int:
        # TODO: __doc__

        offset = self.memory.index(item, start=start, endex=endex)
        return offset

    @classmethod
    def load(cls, path: Any, ignore_errors: bool = True) -> 'BaseFile':
        # TODO: __doc__

        if path == '-':
            return cls.parse(sys.stdin, ignore_errors=ignore_errors)
        else:
            with open(path, 'rb') as stream:
                return cls.parse(stream, ignore_errors=ignore_errors)

    @property
    def maxdatalen(self) -> int:

        return self._maxdatalen

    @maxdatalen.setter
    def maxdatalen(self, maxdatalen: int) -> None:

        maxdatalen = maxdatalen.__index__()
        if maxdatalen < 1:
            raise ValueError('invalid maximum data length')

        if maxdatalen != self._maxdatalen:
            self.discard_records()
        self._maxdatalen = maxdatalen

    @property
    def memory(self) -> MutableMemory:

        if self._memory is None:
            self.apply_records()
        return self._memory

    @classmethod
    def merge(cls, *files: 'BaseFile', clear: bool = False) -> 'BaseFile':
        # TODO: __doc__

        merged = cls()
        for file in files:
            merged.write(0, file.memory, clear=clear)
        return merged

    @classmethod
    def parse(cls, stream: IO, ignore_errors: bool = False) -> 'BaseFile':
        # TODO: __doc__

        records = []
        record_type = cls.RECORD_TYPE
        row = 0

        for line in stream:
            row += 1
            if not line or line.isspace():
                continue
            try:
                record = record_type.parse(line)
            except Exception:
                if ignore_errors:
                    continue
                raise
            record.coords = (row, 0)
            records.append(record)

        file = cls.from_records(records)
        return file

    def print(
        self,
        stream: Optional[IO] = None,
        color: bool = False,
        start: Optional[int] = None,
        stop: Optional[int] = None,
    ) -> 'BaseFile':
        # TODO: __doc__

        records = self.records
        if start is None:
            start = 0
        if stop is None:
            stop = len(records)

        for index in range(start, stop):
            record = records[index]
            record.print(stream=stream, color=color)

        return self

    def read(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
        fill: Union[int, AnyBytes] = 0,
    ) -> bytes:
        # TODO: __doc__

        memory = self.memory.extract(start=start, endex=endex, pattern=fill)
        chunk = memory.to_bytes()
        return chunk

    @property
    def records(self) -> MutableSequence[BaseRecord]:
        # TODO: __doc__

        if self._records is None:
            self.update_records()
        return self._records

    def reverse(self) -> 'BaseFile':
        # TODO: __doc__

        self.memory.reverse()
        self.discard_records()
        return self

    def save(self, path: Any) -> 'BaseFile':
        # TODO: __doc__

        if path == '-':
            return self.serialize(sys.stdout)
        else:
            with open(path, 'wb') as stream:
                return self.serialize(stream)

    def set_meta(
        self,
        meta: Mapping[str, Any],
        strict: bool = True,
    ) -> 'BaseFile':
        # TODO: __doc__

        for key, value in meta:
            if key in self.META_KEYS:
                setattr(self, key, value)
            elif strict:
                raise KeyError(f'unknown meta: {key!r}')
        self.discard_records()
        return self

    def serialize(self, stream: IO, *args, **kwargs) -> 'BaseFile':
        # TODO: __doc__

        for record in self.records:
            record.serialize(stream, *args, **kwargs)
        return self

    def shift(self, offset: int) -> 'BaseFile':
        # TODO: __doc__

        self.memory.shift(offset)
        self.discard_records()
        return self

    def split(
        self,
        *addresses: int,
        meta: bool = False,
    ) -> List['BaseFile']:
        # TODO: __doc__

        pivots: List[Optional[int]] = list(addresses)
        pivots.sort()
        pivots.append(None)
        previous = None
        parts: List[BaseFile] = []

        if self._memory is None:
            self.apply_records()

        for address in pivots:
            part = self.copy(start=previous, endex=address, meta=meta)
            parts.append(part)
            previous = address

        return parts

    @abc.abstractmethod
    def update_records(self) -> 'BaseFile':
        # TODO: __doc__
        ...

    @abc.abstractmethod
    def validate_records(self) -> 'BaseFile':
        # TODO: __doc__
        ...

    def view(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
    ) -> memoryview:
        # TODO: __doc__

        view = self.memory.view(start=start, endex=endex)
        return view

    def write(
        self,
        address: int,
        data: Union[AnyBytes, int, ImmutableMemory],
        clear: bool = False,
    ) -> 'BaseFile':
        # TODO: __doc__

        self.memory.write(address, data, clear=clear)
        self.discard_records()
        return self
