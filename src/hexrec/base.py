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

r""" Base types and classes."""

import abc
import io
import os
import sys
from typing import IO
from typing import Any
from typing import List
from typing import Mapping
from typing import MutableMapping
from typing import MutableSequence
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union
from typing import cast as _cast

import colorama
from bytesparse import Memory
from bytesparse.base import BlockSequence
from bytesparse.base import ImmutableMemory
from bytesparse.base import MutableMemory

try:
    from typing import TypeAlias
except ImportError:  # pragma: no cover
    TypeAlias = Any  # Python < 3.10

try:
    from typing import Literal
    ByteOrder: TypeAlias = Literal['big', 'little']
except ImportError:  # pragma: no cover
    Literal: TypeAlias = str  # Python < 3.8
    ByteOrder: TypeAlias = Literal

try:
    from typing import Self
except ImportError:  # pragma: no cover
    Self: TypeAlias = Any  # Python < 3.11
__TYPING_HAS_SELF = Self is not Any

AnyBytes: TypeAlias = Union[bytes, bytearray, memoryview]
AnyPath: TypeAlias = Union[bytes, bytearray, str, os.PathLike]
EllipsisType: TypeAlias = Type['Ellipsis']

file_types: MutableMapping[str, Type['BaseFile']] = {}
r"""Registered record file types.

This is an ordered mapping, where the first item has top priority."""

TOKEN_COLOR_CODES: Mapping[str, bytes] = {
    '':         colorama.Style.RESET_ALL.encode(),
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
r"""ANSI color codes for each possible token type."""


def colorize_tokens(
    tokens: Mapping[str, bytes],
    altdata: bool = True,
) -> Mapping[str, bytes]:
    r"""Prepends ANSI color codes to record field tokens.

    For each token within `tokens`, its key is used to look up the ANSI color
    code from :data:`TOKEN_COLOR_CODES`.
    The retrieved code (byte string) is prepended to the token.
    All the modified tokens are then collected and returned.

    Args:
        tokens (dict):
            A mapping of each token key name to token byte string.

        altdata (bool):
            If true, it alternates each byte (two hex digits) between the ANSI
            color codes mapped with keys ``data`` (even byte index) and
            ``dataalt`` (odd byte index).
            If false, only the ``data`` code is prepended.

    Returns:
        dict: `tokens` with prepended ANSI color codes.

    Examples:
        >>> from hexrec.base import colorize_tokens
        >>> from hexrec import IhexFile
        >>> from pprint import pprint

        >>> record = IhexFile.Record.create_end_of_file()
        >>> tokens = record.to_tokens()
        >>> pprint(tokens)  # doctest: +NORMALIZE_WHITESPACE
        {'address': b'0000',
         'after': b'',
         'before': b'',
         'begin': b':',
         'checksum': b'FF',
         'count': b'00',
         'data': b'',
         'end': b'\r\n',
         'tag': b'01'}
        >>> colorized = colorize_tokens(tokens)
        >>> pprint(colorized)  # doctest: +NORMALIZE_WHITESPACE
        {'<': b'\x1b[0m',
         '>': b'\x1b[0m',
         'address': b'\x1b[31m0000',
         'begin': b'\x1b[33m:',
         'checksum': b'\x1b[35mFF',
         'count': b'\x1b[34m00',
         'end': b'\x1b[0m\r\n',
         'tag': b'\x1b[32m01'}
    """

    codes = TOKEN_COLOR_CODES
    colorized = {}
    colorized.setdefault('<', codes['<'])

    for key, value in tokens.items():
        if key not in codes:
            key = ''
        if value:
            code = codes[key]

            if key == 'data' and altdata:
                altcode = codes['dataalt']
                buffer = bytearray()
                length = len(value)
                i = 0

                for i in range(0, length - 1, 2):
                    buffer.extend(altcode if i & 2 else code)
                    buffer.append(value[i])
                    buffer.append(value[i + 1])

                if length & 1:
                    buffer.extend(code if i & 2 else altcode)
                    buffer.append(value[length - 1])

                colorized[key] = bytes(buffer)
            else:
                colorized[key] = code + value

    colorized.setdefault('>', codes['>'])
    return colorized


def convert(
    in_path_or_stream: Union[str, IO],
    out_path: str,
    in_format: Optional[str] = None,
    out_format: Optional[str] = None,
) -> Tuple['BaseFile', 'BaseFile']:
    r"""Converts a file into another format.

    This is a simple helper function for basic conversion of a file on the
    filesystem into another record format.

    The function returns the input and output file objects, for further
    processing by the user.

    Args:
        in_path_or_stream (str):
            Input file path or stream.

        out_path (str):
            Output file path. It can be the same as `in_path`.

        in_format (str):
            Name of the input format, within :data:`file_types`.
            If ``None``, it is guessed via brute-force :func:`load`.

        out_format (str):
            Name of the output format, within :data:`file_types`.
            If ``None``, it is guessed via :func:`guess_format_name`.

    Returns:
        (in_file, out_file): Input and output file objects used internally.

    See Also:
        :data:`file_types`
        :meth:`BaseFile.convert`
        :meth:`BaseFile.load`
        :meth:`BaseFile.save`

    Examples:
        >>> from hexrec import convert
        >>> convert('simple.hex', 'simple.srec')
        >>> convert('simple.hex', 'simple.srec', in_format='ihex', out_format='srec')
    """

    if out_format is None:
        out_format = guess_format_name(out_path)
    out_type = file_types[out_format]
    in_file = load(in_path_or_stream, in_format)
    out_file = out_type.convert(in_file)
    out_file.save(out_path)
    return in_file, out_file


def guess_format_name(file_path: str) -> str:
    r"""Guesses the record format name.

    It analyzes the file extension by `file_path` against all the record
    formats registered into :data:`file_types`.
    The first record format to match the extension within its own
    :attr:`BaseFile.FILE_EXT` is returned.

    Args:
        file_path (str):
            File path to analyze.

    Returns:
        str: Record format registered within :data:`file_types`.

    Raises:
        ValueError: Cannot guess record file format.

    See Also:
        :data:`file_types`

    Examples:
        >>> from hexrec import guess_format_name
        >>> guess_format_name('simple.hex')
        'ihex'
        >>> guess_format_name('simple.srec')
        'srec'
        >>> guess_format_name('simple.s19')
        'srec'
        >>> guess_format_name('simple.mot')
        'srec'
        >>> guess_format_name('data.dat')
        'raw'
    """

    file_ext = os.path.splitext(file_path)[1]
    names_found = []

    for name in file_types.keys():
        file_type = file_types[name]

        if file_ext in file_type.FILE_EXT:
            names_found.append(name)

    if not names_found:
        raise ValueError(f'extension not found: {file_ext!r}')

    return names_found[0]


def guess_format_type(file_path: str) -> Type['BaseFile']:
    r"""Guesses the record format object type.

    It calls :func:`guess_format_name` to return the registered object type
    within :data:`file_types`.

    Args:
        file_path (str):
            File path to analyze.

    Returns:
        str: Record object type registered within :data:`file_types`.

    Raises:
        ValueError: Cannot guess record file format.

    See Also:
        :data:`file_types`

    Examples:
        >>> from hexrec import guess_format_type
        >>> guess_format_type('simple.hex')
        <class 'hexrec.formats.ihex.IhexFile'>
        >>> guess_format_type('simple.srec')
        <class 'hexrec.formats.srec.SrecFile'>
        >>> guess_format_type('simple.s19')
        <class 'hexrec.formats.srec.SrecFile'>
        >>> guess_format_type('simple.mot')
        <class 'hexrec.formats.srec.SrecFile'>
        >>> guess_format_type('data.dat')
        <class 'hexrec.formats.raw.RawFile'>
    """

    name = guess_format_name(file_path)
    return file_types[name]


def load(
    in_path_or_stream: Optional[Union[str, IO]],
    *load_args: Any,
    in_format: Optional[str] = None,
    **load_kwargs: Any,
) -> 'BaseFile':
    r"""Loads a file.

    This is a simple helper function to load a record file from the filesystem.

    All the custom `load_args` and `load_kwargs` are forwarded to the actual
    underlying call to :meth:`BaseFile.load`.

    Args:
        in_path_or_stream (str):
            Input file path or stream.
            If ``None``, ``sys.stdin.buffer`` is used.

        in_format (str):
            Name of the input format, within :data:`file_types`.
            If ``None``, it is guessed via brute-force :meth:`BaseFile.load`.

    Returns:
        :class:`BaseFile`: The loaded record file object.

    See Also:
        :data:`file_types`
        :func:`guess_format_name`
        :meth:`BaseFile.load`

    Examples:
        >>> from hexrec import load
        >>> load('simple.hex')  # doctest:+ELLIPSIS
        <hexrec.formats.ihex.IhexFile object at ...>
        >>> load('simple.hex', in_format='ihex')  # doctest:+ELLIPSIS
        <hexrec.formats.ihex.IhexFile object at ...>
        >>> load('simple.hex', ignore_errors=True)  # doctest:+ELLIPSIS
        <hexrec.formats.ihex.IhexFile object at ...>
    """

    if in_path_or_stream is None:
        in_path_or_stream = sys.stdin.buffer

    if in_format is None:
        last_exc = RuntimeError
        if isinstance(in_path_or_stream, io.IOBase):
            stream = in_path_or_stream
            in_offset = stream.tell()
            for file_type in file_types.values():
                try:
                    return file_type.load(stream, *load_args, **load_kwargs)
                except Exception as exc:
                    last_exc = exc
                    stream.seek(in_offset)
        else:
            in_path = str(in_path_or_stream)
            try:
                file_type = guess_format_type(in_path)
                return file_type.load(in_path, *load_args, **load_kwargs)
            except Exception as exc:
                last_exc = exc

            for file_type in file_types.values():
                try:
                    return file_type.load(in_path, *load_args, **load_kwargs)
                except Exception as exc:
                    last_exc = exc
        raise last_exc
    else:
        file_type = file_types[in_format]
        return file_type.load(in_path_or_stream, *load_args, **load_kwargs)


def merge(
    in_paths_or_streams: Sequence[Union[str, IO]],
    out_path_or_stream: Optional[Union[str, IO, EllipsisType]] = Ellipsis,
    in_formats: Optional[Sequence[Optional[str]]] = None,
    out_format: Optional[str] = None,
) -> Tuple[Sequence['BaseFile'], 'BaseFile']:
    r"""Merges multiple files.

    This is a simple helper function to load multiple files from the filesystem
    and merge into a new one.

    The function returns the list of input file objects and the output file
    object, for further processing by the user.

    Args:
        in_paths_or_streams (str list):
            Sequence of input file paths or streams, in merging order.

        out_path_or_stream (str):
            Output file path. It can be the same one of `in_paths_or_streams`.
            If ``None``, ``sys.stdout.buffer`` is used.
            If ``Ellipsis``, no output is performed (return values only).

        in_formats (str list):
            Name of the input formats, within :data:`file_types`.
            If the sequence or an item is ``None``, that is guessed via
            :func:`guess_format_name`.

        out_format (str):
            Name of the output format, within :data:`file_types`.
            If ``None``, it is guessed via :func:`guess_format_name`.

    Returns:
        (in_files, out_file): The record file objects used internally.

    See Also:
        :data:`file_types`
        :func:`guess_format_name`
        :meth:`BaseFile.load`
        :meth:`BaseFile.merge`
        :meth:`BaseFile.save`

    Examples:
        >>> from hexrec import merge
        >>> merge(['data.dat', 'simple.hex'], 'merge.xtek')  # doctest:+ELLIPSIS,+NORMALIZE_WHITESPACE
        ([<hexrec.formats.raw.RawFile object at ...>,
          <hexrec.formats.ihex.IhexFile object at ...>],
         <hexrec.formats.xtek.XtekFile object at ...>)
        >>> merge(['data.dat', 'simple.hex'], 'merge.xtek',
        ...       in_formats=['raw', None], out_format='xtek')  # doctest:+ELLIPSIS,+NORMALIZE_WHITESPACE
        ([<hexrec.formats.raw.RawFile object at ...>,
          <hexrec.formats.ihex.IhexFile object at ...>],
         <hexrec.formats.xtek.XtekFile object at ...>)
    """

    in_formats = list(in_formats or ())
    in_formats += [None] * (len(in_paths_or_streams) - len(in_formats))

    if out_format is None and out_path_or_stream not in (None, Ellipsis):
        out_format = guess_format_name(out_path_or_stream)
    out_type = file_types[out_format]

    in_files = []
    for i, in_path_or_stream in enumerate(in_paths_or_streams):
        in_file = load(in_path_or_stream, in_format=in_formats[i])
        in_files.append(in_file)

    out_file = out_type()
    out_file.merge(*in_files)

    if out_path_or_stream is not Ellipsis:
        out_file.save(out_path_or_stream)

    return in_files, out_file


class BaseTag:
    r"""Record tag.

    The *record tag* indicates the *nature* of a record.
    The record tag class usually enumerates all the possible natures of a
    record within a *record file format*.

    The tag is commonly (but not necessarily) an integer, directly written into
    the *serialized* representation of a record.
    """

    _DATA: Optional['BaseTag'] = None
    r"""Alias to a common data record tag.

    This tag is used internally to build a generic data record.
    """

    @abc.abstractmethod
    def is_data(self) -> bool:
        r"""Tells whether this is a data record tag.

        This method returns true if this data record is used for records
        containing plain data (i.e. without special meaning for the record file
        format).

        Returns:
            bool: This is a data record tag.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseTag`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.create_data(123, b'abc')
            >>> record.tag.is_data()
            True
            >>> record = IhexFile.Record.create_end_of_file()
            >>> record.tag.is_data()
            False

            >>> from hexrec import SrecFile
            >>> record = SrecFile.Record.create_data(123, b'abc')
            >>> record.tag.is_data()
            True
            >>> record = SrecFile.Record.create_header(b'HDR\0')
            >>> record.tag.is_data()
            False
        """
        ...

    # noinspection PyMethodMayBeStatic
    def is_file_termination(self) -> bool:
        r"""Tells whether this is record tag terminates a record file.

        This method returns true if this record is used to terminate a record
        file.

        This is usually the case for *End Of File* or *start address* records,
        depending on the specific file *format*, if supported.

        Returns:
            bool: This is a file termination tag.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseTag`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.create_data(123, b'abc')
            >>> record.tag.is_file_termination()
            False
            >>> record = IhexFile.Record.create_end_of_file()
            >>> record.tag.is_file_termination()
            True

            >>> from hexrec import SrecFile
            >>> record = SrecFile.Record.create_data(123, b'abc')
            >>> record.tag.is_file_termination()
            False
            >>> record = SrecFile.Record.create_start()
            >>> record.tag.is_file_termination()
            True
        """

        return False


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='BaseRecord')


class BaseRecord(abc.ABC):
    r"""Record.

    A *record* is the basic means to transfer data across systems.
    It is usually a line of text containing some binary data in hexadecimal
    representation, or some *meta* information (e.g. *start address*,
    *record count*), often allocated at some *address* into the target system.

    Most *formats* also contain information for *consistency checks*, such as
    the amount of data/characters within the record itself (*count*), and their
    *checksum*.

    The :class:`BaseRecord` class should provide a very generic description of
    a common record (see *Attributes*).
    Wherever the *format* requires some additional special information, a child
    class can provide it.

    The *constructor* (:meth:`__init__`) allows direct assignment of attribute
    values, as well as skipping *validation*.
    This is considered an advanced feature, typically leveraged for testing or
    experimental purposes.

    Instead, a :class:`BaseRecord` child class should provide factory methods
    to create records of each specific *nature*
    (e.g. the mandatory :meth:`create_data` for *data* records).

    Attributes:
        tag (:class:`BaseTag`):
            The mandatory *tag*, indicating the *nature* of the record.

        address (int):
            The *address* usually tells the position in memory where the
            provided *data* must be stored.
            Some *formats* use this attribute to store other *meta*
            information, such as the *start address* of some program, or the
            *record count*.

        data (bytes):
            This attribute is most commonly used to store some chunk of binary
            data to be allocated at the specified *address*.
            Some *formats* might store some *meta* information within the
            *data* field of the serialized record, such as the *header string*.

        count (int):
            Most *formats* indicate the number of bytes or characters within
            the serialized record itself.
            Some might store other counting information, like the number of
            characters for the serialized *address* field.

        checksum (int):
            Most *formats* provide some kind of *checksum* to check for
            consistency of the serialized record itself.

        before (bytes):
            Some *formats* allow to serialize some data before the canonical
            syntax, like comments or custom/experimental data.
            This is a non-standard feature; please leave empty if in doubt.

        after (bytes):
            Some *formats* allow to serialize some data after the canonical
            syntax, like comments or custom/experimental data.
            This is a non-standard feature; please leave empty if in doubt.

        coords (int couple):
            Some *parsers* may use this attribute to store the coordinates of
            the parsed record, such as the line number, or the byte offset.
            This is a non-standard feature, useful for debug only.

    Args:
        tag (:class:`BaseTag`):
            See :attr:`tag` attribute.

        address (int):
            See :attr:`address` attribute.

        data (bytes):
            See :attr:`data` attribute.

        count (int):
            See :attr:`count` attribute.
            ``Ellipsis`` initializes :attr:`count` via :meth:`compute_count`.
            ``None`` assigns ``None``, skipping further validation.

        checksum (int):
            See :attr:`checksum` attribute.
            ``Ellipsis`` initializes :attr:`checksum` via
            :meth:`compute_checksum`.
            ``None`` assigns ``None``, skipping further validation.

        before (bytes):
            See :attr:`before` attribute.

        after (bytes):
            See :attr:`after` attribute.

        coords (int couple):
            See :attr:`coords` attribute.

        validate (bool):
            If true, :meth:`validate` is called upon initialization.
    """

    EQUALITY_KEYS: Sequence[str] = [
        'address',
        'checksum',
        'count',
        'data',
        'tag',
    ]
    r"""Meta keys for equality checks.

    Equality methods (:meth:`__eq__` and :meth:`__ne__`) check against these
    *meta* keys only.
    Any other *meta* keys are just ignored.
    """

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
    r"""Meta keys.

    This sequence holds the *meta* keys for copying (see :meth:`copy`).
    """

    Tag: Type[BaseTag] = None  # override
    r"""Tag object type.

    This class attribute indicates the :class:`BaseTag` class used by this
    :class:`BaseRecord` class.
    """

    def __bytes__(self) -> bytes:
        r"""Serializes the record into bytes.

        Returns:
            bytes: Byte serialization.

        See Also:
            :meth:`to_bytestr`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.create_end_of_file()
            >>> bytes(record)
            b':00000001FF\r\n'

            >>> from hexrec import RawFile
            >>> record = RawFile.Record.create_data(0, b'abc')
            >>> bytes(record)
            b'abc'
        """

        return self.to_bytestr()

    def __eq__(self, other: 'BaseRecord') -> bool:
        r"""Equality test.

        This method returns true if `self` is considered equal to `other`.

        As inequality is usually easier to check, this method is usually
        implemented as a trivial ``not self != other`` (:meth:`__ne__`).

        Args:
             other (:class:`BaseRecord`):
                Record to compare to.

        Returns:
            bool: `self` equals `other`.

        See Also:
            :meth:`__ne__`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile, RawFile
            >>> ihex1 = IhexFile.Record.create_data(0, b'abc')
            >>> ihex2 = IhexFile.Record.create_data(0, b'abc')
            >>> ihex1 is ihex2
            False
            >>> ihex1 == ihex2
            True
            >>> ihex3 = IhexFile.Record.create_data(0, b'xyz')
            >>> ihex1 == ihex3
            False
            >>> raw = RawFile.Record.create_data(0, b'abc')
            >>> ihex1 == raw
            False
        """

        return not self != other

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
        validate: bool = True,
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

        if validate:
            _count = count is not None
            _checksum = checksum is not None and _count
            self.validate(checksum=_checksum, count=_count)

    def __ne__(self, other: 'BaseRecord') -> bool:
        r"""Ineuality test.

        This method returns true if `self` is considered unequal to `other`.

        Each attribute listed by :attr:`EQUALITY_KEYS` is compared between
        `self` and `other`.
        This method returns whether any attributes do not match.

        Args:
             other (:class:`BaseRecord`):
                Record to compare to.

        Returns:
            bool: `self` and `other` are unequal.

        See Also:
            :meth:`__eq__`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile, RawFile
            >>> ihex1 = IhexFile.Record.create_data(0, b'abc')
            >>> ihex2 = IhexFile.Record.create_data(0, b'abc')
            >>> ihex1 is ihex2
            False
            >>> ihex1 != ihex2
            False
            >>> ihex3 = IhexFile.Record.create_data(0, b'xyz')
            >>> ihex1 != ihex3
            True
            >>> raw = RawFile.Record.create_data(0, b'abc')
            >>> ihex1 != raw
            True
        """

        for key in self.EQUALITY_KEYS:
            if not hasattr(other, key):
                return True
            self_value = getattr(self, key)
            other_value = getattr(other, key)
            if self_value != other_value:
                return True

        return False

    def __repr__(self) -> str:
        r"""String representation.

        It returns a string representation of the record content, for human
        understanding only.

        Returns:
            str: String representation.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.create_end_of_file()
            >>> repr(record)  # doctest:+NORMALIZE_WHITESPACE,+ELLIPSIS
            "<<class 'hexrec.formats.ihex.IhexRecord'> @...
              address:=0 after:=b'' before:=b'' checksum:=255 coords:=(-1, -1)
              count:=0 data:=b'' tag:=<IhexTag.END_OF_FILE: 1>>"
        """

        meta = self.get_meta()
        text = f'<{self.__class__!s} @0x{id(self):08X} '
        text += ' '.join(f'{key!s}:={value!r}' for key, value in meta.items())
        text += '>'
        return text

    def __str__(self) -> str:
        r"""Serializes the record into a string.

        Returns:
            str: String serialization.

        See Also:
            :meth:`to_bytestr`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.create_end_of_file()
            >>> str(record)
            ':00000001FF\r\n'

            >>> from hexrec import RawFile
            >>> record = RawFile.Record.create_data(0, b'abc')
            >>> str(record)
            'abc'
        """

        return self.to_bytestr().decode()

    def compute_checksum(self) -> Optional[int]:
        r"""Computes the checksum field value.

        It computes and returns the format-specific :attr:`checksum` value of a
        record.

        When not specialized, it returns ``None`` by default.

        Returns:
            int: Computed checksum value.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.create_data(0, b'abc')
            >>> record.compute_checksum()
            215

            >>> from hexrec import RawFile
            >>> record = RawFile.Record.create_data(0, b'abc')
            >>> repr(record.compute_checksum())
            'None'
        """

        return None

    def compute_count(self) -> Optional[int]:
        r"""Compute the count field value.

        It computes and returns the format-specific :attr:`count` value of a
        record.

        When not specialized, it returns ``None`` by default.

        Returns:
            int: Computed checksum value.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.create_data(0, b'abc')
            >>> record.compute_count()
            3

            >>> from hexrec import RawFile
            >>> record = RawFile.Record.create_data(0, b'abc')
            >>> repr(record.compute_count())
            'None'
        """

        return None

    def copy(self, validate: bool = True) -> Self:  # shallow
        r"""Shallow copy.

        It calls the record constructor, passing *meta* to it.

        Args:
             validate (bool):
                Performs validation on instantiation (:meth:`__init__`).

        Returns:
            :class:`BaseRecord`: Shallow copy.

        See Also:
            :meth:`__init__`
            :meth:`get_meta`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record1 = IhexFile.Record.create_data(0x1234, b'abc')
            >>> record2 = record1.copy()
            >>> record1 is record2
            False
            >>> record1 == record2
            True
        """

        meta = self.get_meta()
        tag = meta.pop('tag')
        cls = type(self)
        return cls(tag, validate=validate, **meta)

    @classmethod
    @abc.abstractmethod
    def create_data(cls, address: int, data: AnyBytes) -> Self:
        r"""Creates a data record.

        This is a mandatory class method to instantiate a *data* record.

        Args:
            address (int):
                Record address. If not supported, set zero.

            data (bytes):
                Record byte data.

        Returns:
            :class:`BaseRecord`: Data record object.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.create_data(0x1234, b'abc')
            >>> str(record)
            ':0312340061626391\r\n'
        """
        ...

    def data_to_int(
        self,
        byteorder: ByteOrder = 'big',
        signed: bool = False,
    ) -> int:
        r"""Interprets data bytes as integer.

        It creates an integer from bytes of the :attr:`data` field.

        Args:
            byteorder ('big' or 'little'):
                Byte order (endianness): either ``'big'`` (default) or
                ``'little'``.

            signed (bool):
                Signed integer (2-complement); default false.

        Returns:
            int: Interpreted integer value.

        See Also:
            :meth:`int.from_bytes`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.create_extended_linear_address(0xABCD)
            >>> record.data
            b'\xab\xcd'
            >>> addrext = record.data_to_int()
            >>> addrext, hex(addrext)
            (43981, '0xabcd')
        """

        value = int.from_bytes(self.data, byteorder=byteorder, signed=signed)
        return value

    def get_meta(self) -> MutableMapping[str, Any]:
        r"""Gets meta information.

        It returns all the object attributes whose keys are listed by
        :attr:`META_KEYS`.

        Returns:
             dict: Attribute values listed by :attr:`META_KEYS`.

        See Also:
            :attr:`META_KEYS`
            :meth:`set_meta`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.create_end_of_file()
            >>> record.get_meta()  # doctest:+NORMALIZE_WHITESPACE
            {'address': 0, 'after': b'', 'before': b'', 'checksum': 255,
             'coords': (-1, -1), 'count': 0, 'data': b'',
             'tag': <IhexTag.END_OF_FILE: 1>}
        """

        meta = {key: getattr(self, key) for key in self.META_KEYS}
        return meta

    @classmethod
    @abc.abstractmethod
    def parse(
        cls,
        line: AnyBytes,
        validate: bool = True,
    ) -> Self:
        r"""Parses a record from bytes.

        Please refer to the actual implementation provided by the record
        *format* for more details.

        Args:
            line (bytes):
                String of bytes to parse.

            validate (bool):
                Perform validation checks.

        Returns:
            :class:`BaseRecord`: Parsed record.

        Raises:
            ValueError: Syntax error.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.parse(b':00000001FF\r\n')
            >>> record.tag
            <IhexTag.END_OF_FILE: 1>
            >>> IhexFile.Record.parse(b'::00000001FF\r\n')
            Traceback (most recent call last):
                ...
            ValueError: syntax error
        """
        ...

    def print(
        self,
        *args,
        stream: Optional[IO] = None,
        color: bool = False,
        **kwargs,
    ) -> Self:
        r"""Prints a record.

        The record is converted into tokens (eventually colorized) then joined
        and written onto a byte stream (*stdout* by default).

        Args:
            args:
                Forwarded to the underlying call to :meth:`to_tokens`.

            stream (bytes IO):
                The byte stream where the record tokens are printed.
                If ``None``, *stdout* is selected.

            color (bool):
                Tokens are colorized before printing.

            kwargs:
                Forwarded to the underlying call to :meth:`to_tokens`.

        Returns:
            :class:`BaseRecord`: *self*.

        See Also:
            :meth:`to_tokens`
            :func:`colorize_tokens`
            :class:`io.IOBase`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.create_data(0x1234, b'abc')
            >>> _ = record.print()
            :0312340061626391
            >>> import io
            >>> stream = io.BytesIO()
            >>> _ = record.print(stream=stream, color=True)
            >>> stream.getvalue()
            b'\x1b[0m\x1b[33m:\x1b[34m03\x1b[31m1234\x1b[32m00\x1b[36m61\x1b[96m62\x1b[36m63\x1b[35m91\x1b[0m\r\n\x1b[0m'
        """

        if stream is None:
            stream = sys.stdout.buffer
        tokens = self.to_tokens(*args, **kwargs)
        if color:
            tokens = colorize_tokens(tokens)
        stream.writelines(tokens.values())
        return self

    def serialize(self, stream: IO, *args, **kwargs) -> Self:
        r"""Serializes onto a stream.

        This wraps a call to :meth:`to_bytestr` and ``stream.write``.

        Args:
            stream (:class:`io.IOBase`):
                Stream to write.

            args:
                Forwarded to :meth:`to_bytestr`.

            kwargs:
                Forwarded to :meth:`to_bytestr`.

        Returns:
            :class:`BaseRecord`: *self*.

        See Also:
            :meth:`to_bytestr`
            :class:`io.IOBase`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.create_data(0x1234, b'abc')
            >>> import io
            >>> stream = io.BytesIO()
            >>> _ = record.serialize(stream, end=b'\n')
            >>> stream.getvalue()
            b':0312340061626391\n'
        """

        stream.write(self.to_bytestr(*args, **kwargs))
        return self

    @abc.abstractmethod
    def to_bytestr(self, *args, **kwargs) -> bytes:
        r"""Converts into a byte string.

        Args:
            args:
                Implementation specific.

            kwargs:
                Implementation specific.

        Returns:
            bytes: Byte string representation.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.create_data(0x1234, b'abc')
            >>> record.to_bytestr(end=b'\n')
            b':0312340061626391\n'
        """
        ...

    @abc.abstractmethod
    def to_tokens(self, *args, **kwargs) -> Mapping[str, bytes]:
        r"""Converts into byte string tokens.

        Args:
            args:
                Implementation specific.

            kwargs:
                Implementation specific.

        Returns:
            bytes: Mapping of token keys to token byte strings.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.create_data(0x1234, b'abc')
            >>> record.to_tokens(end=b'\n')  # doctest:+NORMALIZE_WHITESPACE
            {'before': b'', 'begin': b':', 'count': b'03', 'address': b'1234',
             'tag': b'00', 'data': b'616263', 'checksum': b'91', 'after': b'',
             'end': b'\n'}
        """
        ...

    def update_checksum(self) -> Self:
        r"""Updates the checksum field.

        It updates the :attr:`checksum` attribute, assigning to it the value
        returned by :meth:`compute_checksum`.

        Returns:
            :class:`BaseRecord`: *self*.

        See Also:
            :attr:`checksum`
            :meth:`compute_checksum`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> IhexRecord = IhexFile.Record
            >>> record = IhexRecord(IhexRecord.Tag.END_OF_FILE, checksum=None)
            >>> record.compute_checksum()
            255
            >>> record.checksum is None
            True
            >>> _ = record.update_checksum()
            >>> record.checksum
            255
        """

        self.checksum = self.compute_checksum()
        return self

    def update_count(self) -> Self:
        r"""Updates the count field.

        It updates the :attr:`count` attribute, assigning to it the value
        returned by :meth:`compute_count`.

        Returns:
            :class:`BaseRecord`: *self*.

        See Also:
            :attr:`count`
            :meth:`compute_count`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> Record = IhexFile.Record
            >>> Tag = Record.Tag
            >>> record = Record(Tag.DATA, data=b'abc', count=None, checksum=None)
            >>> record.compute_count()
            3
            >>> record.count is None
            True
            >>> _ = record.update_count()
            >>> record.count
            3
        """

        self.count = self.compute_count()
        return self

    def validate(
        self,
        checksum: bool = True,
        count: bool = True,
    ) -> Self:
        r"""Validates consistency of attribute values.

        All the record attributes are checked for consistency.

        Please refer to the implementation for more details.

        Args:
            checksum (bool):
                Check the consistency of the :attr:`checksum` attribute.

            count (bool):
                Check the consistency of the :attr:`count` attribute.

        Returns:
            :class:`BaseRecord`: *self*.

        Raises:
            ValueError: Some targeted attributes are inconsistent.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseRecord`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> record = IhexFile.Record.create_end_of_file()
            >>> _ = record.validate()
            >>> record.data = b'abc'
            >>> _ = record.update_count().update_checksum().validate()
            Traceback (most recent call last):
                ...
            ValueError: unexpcted data
        """

        if self.address < 0:
            raise ValueError('address overflow')

        if self.checksum is not None:
            if self.checksum < 0:
                raise ValueError('checksum overflow')

            if checksum:
                if self.checksum != self.compute_checksum():
                    raise ValueError('wrong checksum')

        if self.count is not None:
            if self.count < 0:
                raise ValueError('count overflow')

            if count:
                if self.count != self.compute_count():
                    raise ValueError('wrong count')

        TagType = _cast(Any, self.Tag)
        TagType(self.tag)

        return self


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
    Self = TypeVar('Self', bound='BaseFile')


class BaseFile(abc.ABC):
    r"""Record file.

    A *record file* contains a sequence of *records* (:class:`BaseRecord`),
    which can be serialized to transfer some *binary* data across systems,
    usually an executable program of some configuration data for an
    *embedded system*.

    The :class:`BaseFile` class provides a useful abstraction of a record file,
    to create, edit, or convert across file *formats*.

    A :class:`BaseFile` instance has a dual role:

    * *records role*: to host the sequence of *records* for parsing and
      serialization;

    * *memory role*: to host the equivalent *memory* image and *meta*
      information.

    Both roles can be active at the same time only when both representations
    are coherent.

    The *records* role is useful to :meth:`load` or :meth:`save` the instance
    against the filesystem.
    The individual records can be edited via the :attr:`records` attribute.
    This is considered an advanced feature, for debug or experimentation.

    The *memory* role is for editing the equivalent *memory image*.
    The :class:`BaseFile` provides common methods to :meth:`read`,
    :meth:`write`, :meth:`cut`, :meth:`crop`, :meth:`clear`, :meth:`delete`,
    :meth:`fill`, :meth:`flood`, and more.
    Furthermore, this role also abstracts *meta* information, like the maximum
    *data* size (:attr:`maxdatalen`), or the *start address* (if available for
    the specific file *format*).
    Advanced editing can be performed via the underlying :attr:`memory`
    attribute, thanks to  the powerful :class:`bytesparse.Memory` class (from
    the `bytesparse Python package <https://pypi.org/project/bytesparse/>`_),
    the :meth:`get_meta` and :meth:`set_meta` methods, or their equivalent
    Python property wrappers.
    The :attr:`memory` also provides additional methods and properties for
    in-depth analysis (min/max address, gaps, spans, find, etc.).

    A :class:`BaseFile` instance can impersonate each role via:

    * :meth:`apply_records` to mirror the :attr:`records` sequence into the
      equivalent :attr:`memory` and *meta*.

    * :meth:`update_records` to mirror the :attr:`memory` and *meta* into
      an actual :attr:`records` sequence.

    Please note that reading from the :attr:`records` or :attr:`memory`
    properties automatically activates the corresponding role if inactive
    (i.e. :meth:`update_records` if :attr:`_records` is ``None``,
    :meth:`apply_records` if :attr:`_memory` is ``None``).

    Beware that any editing done within a role may invalidate the other role,
    if both :attr:`records` and :attr:`memory` + *meta* are instantiated.
    For example, setting the :attr:`maxdatalen` property means that records
    must be updated to mirror the new maximum *data* field length.
    Records must also be invalidated whenever the :attr:`memory` is altered.

    Usually, *meta* property setters automatically invalidate :attr:`records`
    on change (via :meth:`discard_records`).
    Instead, only the explicit *memory* methods of :meth:`BaseFile` do it
    automatically; any operations on the :attr:`memory` itself require
    :meth:`update_records` be called to mirror any changes.

    Instantiation of a new :class:`BaseFile` instance should be performed via:

    * :class:`BaseFile` for an empty file (only!);
      *memory* role.

    * :meth:`from_bytes`, :meth:`from_blocks`, :meth:`from_memory` to create
      from existing byte-like, blocks, or :class:`bytesparse.Memory`;
      *memory* role.

    * :meth:`copy`, :meth:`convert` to clone an existing :class:`BaseFile`;
      *memory* role.

    * :meth:`from_records` to create from existing records;
      *records* role.

    * :meth:`load` to load records from the filesystem (via :func:`open`);
      *records* role.

    * :meth:`parse` to load records from a byte stream;
      *records* role.

    Validation of :attr:`records` is performed via :meth:`validate`.

    Most methods return *self*, and as such they can be *chained*, instead of
    being forced to call each method in a separate statement.
    This comes handy to write some one-liners or generally shorter scripts.

    Please note that within the examples of this documentation *chaining* is
    rarely used, for easier reading.
    Any places where interactive console commands would return *self*, the
    returned value is suppressed by assigning ``_``, not to disrupt the output
    (e.g.: ``_ = file.print()`` outputs only record content to *stdout*).
    """

    DEFAULT_DATALEN: int = 16
    r"""Default data attribute length.

    Default value for the :attr:`maxdatalen` *meta*, which sets the maximum
    size of :attr:`BaseRecord.data` field values.
    """

    FILE_EXT: Sequence[str] = []
    r"""Supported filename extensions.

    Sequence of file name extension substrings (e.g. ``.hex``).
    This list is used by functions like :func:`guess_format_name` to manage
    mapping of file *formats*.
    """

    META_KEYS: Sequence[str] = ['maxdatalen']
    r"""Meta information key names.

    Sequence of key strings listing the supported *meta* information of this
    file *format*.
    """

    Record: Type[BaseRecord] = None  # override
    r"""Record object type.

    This class attribute indicates the :class:`BaseRecord` class used by this
    :class:`BaseFile` class.
    """

    def __add__(
        self,
        other: Union['BaseFile', AnyBytes],
    ) -> Self:
        r"""Concatenates with another file.

        Equivalent to :meth:`copy` then :meth:`extend`.

        Args:
            other (:class:`BaseFile` or bytes):
                Other file or bytes to concatenate.

        Returns:
            :class:`BaseFile`: Concatenation of *self* and *other*.

        See Also:
            :meth:`copy`
            :meth:`extend`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file1 = SrecFile.from_bytes(b'abc', offset=123)
            >>> file2 = SrecFile.from_bytes(b'xyz', offset=456)
            >>> file3 = file1 + file2
            >>> file3.memory.to_blocks()
            [[123, b'abc'], [582, b'xyz']]
            >>> file4 = file3 + b'789'
            >>> file4.memory.to_blocks()
            [[123, b'abc'], [582, b'xyz789']]
        """

        return self.copy().extend(other)

    def __bool__(self) -> bool:
        r"""bool: Has data records or memory.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

             >>> from hexrec import IhexFile
             >>> file = IhexFile()
             >>> bool(file)
             False
             >>> _ = file.append(0)
             >>> bool(file)
             True

             >>> from hexrec import IhexFile
             >>> IhexRecord = IhexFile.Record
             >>> file = IhexFile.from_records([IhexRecord.create_end_of_file()])
             >>> bool(file)
             False
             >>> file.records.insert(0, IhexRecord.create_data(0, b'\0'))
             >>> bool(file)
             True
        """

        if self._memory:
            return True

        if self._records:
            for record in self._records:
                if record.tag.is_data() and record.data:
                    return True

        return False

    def __delitem__(self, key: Union[slice, int]) -> None:
        r"""Deletes a range.

        Args:
            key (slice or int):
                Range to delete.

        See Also:
            :meth:`bytesparse.base.MutableMemory.__delitem__`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [456, b'xyz']])
            >>> del file[457]
            >>> file.memory.to_blocks()
            [[123, b'abc'], [456, b'xz']]
            >>> del file[125:457]
            >>> file.memory.to_blocks()
            [[123, b'abz']]
        """

        del self.memory[key]

    def __getitem__(self, key: Union[slice, int]) -> Union[AnyBytes, int, None]:
        r"""Extracts a range.

        Args:
            key (slice or int):
                Range to extract.

        Raises:
            ValueError: invalid range.

        See Also:
            :meth:`bytesparse.base.ImmutableMemory.__getitem__`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [456, b'xyz']])
            >>> chr(file[457])
            'y'
            >>> repr(file[333])
            'None'
            >>> file[123:125]
            b'ab'
            >>> file[125:457]
            Traceback (most recent call last):
                ...
            ValueError: non-contiguous data within range
        """

        item = self.memory[key]
        if isinstance(key, slice):
            item = bytes(item)
        return item

    def __eq__(self, other: 'BaseFile') -> bool:
        r"""Equality test.

        The file objects `self` and `other` are considered *equal* if the
        inequality tests of :meth:`__ne__` result false.

        Returns:
            bool: `self` and `other` are *equal*.

        See Also
            :meth:`__ne__`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file1 = SrecFile.from_bytes(b'abc', offset=123)
            >>> file2 = SrecFile.from_bytes(b'abc', offset=123)
            >>> file1 is file2
            False
            >>> file1 == file2
            True
            >>> file3 = SrecFile.from_bytes(b'xyz', offset=123)
            >>> file1 == file3
            False
            >>> file4 = SrecFile.from_bytes(b'abc', offset=456)
            >>> file1 == file4
            False

            >>> from hexrec import SrecFile, IhexFile
            >>> srec_file = SrecFile.from_bytes(b'abc', offset=123)
            >>> ihex_file = IhexFile.from_bytes(b'abc', offset=123)
            >>> srec_file == ihex_file
            False
            >>> srec_file.memory == ihex_file.memory
            True
            >>> set(srec_file.META_KEYS) - set(ihex_file.META_KEYS)
            {'header'}
        """

        return not self != other

    def __iadd__(
        self,
        other: Union['BaseFile', AnyBytes],
    ) -> Self:
        r"""Concatenates data.

        Equivalent to :meth:`extend`.

        It concatenates `other` to the underlyng :attr:`memory`.

        Any stored :attr:`records` are discarded upon return.

        Args:
            other (:class:`BaseFile` or bytes):
                Other file or bytes to concatenate.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :attr:`memory`
            :meth:`extend`
            :meth:`discard_records`
            :meth:`bytesparse.base.MutableMemory.extend`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file1 = SrecFile.from_bytes(b'abc', offset=123)
            >>> file2 = SrecFile.from_bytes(b'xyz', offset=456)
            >>> file1 += file2
            >>> file1.memory.to_blocks()
            [[123, b'abc'], [582, b'xyz']]
            >>> file1 += b'789'
            >>> file1.memory.to_blocks()
            [[123, b'abc'], [582, b'xyz789']]
        """

        return self.extend(other)

    def __init__(self):

        self._records: Optional[MutableSequence[BaseRecord]] = None
        self._memory: Optional[MutableMemory] = Memory()
        self._maxdatalen: int = self.DEFAULT_DATALEN

    def __ior__(self, other: 'BaseFile') -> Self:
        r"""Merges with another file.

        Equivalent to :meth:`merge`.

        Any stored :attr:`records` are discarded upon return.

        Args:
            other (:class:`BaseFile` or bytes):
                Other file or bytes to merge.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :meth:`merge`
            :meth:`discard_records`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file1 = SrecFile.from_bytes(b'abc', offset=123)
            >>> file2 = SrecFile.from_bytes(b'xyz', offset=456)
            >>> file1 |= file2
            >>> file1.memory.to_blocks()
            [[123, b'abc'], [456, b'xyz']]
            >>> file1 |= b'789'
            >>> file1.memory.to_blocks()
            [[0, b'789'], [123, b'abc'], [456, b'xyz']]
        """

        self.merge(other)
        return self

    def __ne__(self, other: 'BaseFile') -> bool:
        r"""Inequality test.

        The file objects `self` and `other` are considered *unequal* if any of
        the following tests result true:

        * Both have *memory role* (i.e. :attr:`memory`), resulting unequal;
        * Both have *records role* (i.e. :attr:`records`), resulting unequal;
        * `other` does not have a *meta* listed by :attr:`META_KEYS`;
        * A *meta* value (among those of :attr:`META_KEYS`) is different.

        Returns:
            bool: `self` and `other` are *unequal*.

        See Also:
            :meth:`__eq__`
            :attr:`memory`
            :attr:`records`
            :attr:`META_KEYS`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file1 = SrecFile.from_bytes(b'abc', offset=123)
            >>> file2 = SrecFile.from_bytes(b'abc', offset=123)
            >>> file1 is file2
            False
            >>> file1 != file2
            False
            >>> file3 = SrecFile.from_bytes(b'xyz', offset=123)
            >>> file1 != file3
            True
            >>> file4 = SrecFile.from_bytes(b'abc', offset=456)
            >>> file1 != file4
            True

            >>> from hexrec import SrecFile, IhexFile
            >>> srec_file = SrecFile.from_bytes(b'abc', offset=123)
            >>> ihex_file = IhexFile.from_bytes(b'abc', offset=123)
            >>> srec_file != ihex_file
            True
            >>> srec_file.memory != ihex_file.memory
            False
            >>> set(srec_file.META_KEYS) - set(ihex_file.META_KEYS)
            {'header'}
        """

        self_records = self._records
        other_records = other._records
        self_memory = self._memory
        other_memory = other._memory

        if self_memory is not None and other_memory is not None:
            if self_memory != other_memory:
                return True
        elif self_records is not None and other_records is not None:
            if self_records != other_records:
                return True
        else:
            raise ValueError('both memory or both records required')

        for key in self.META_KEYS:
            if not hasattr(other, key):  # ensure
                return True

            self_value = getattr(self, key)
            other_value = getattr(other, key)

            if self_value != other_value:
                return True

        return False

    def __or__(
        self,
        other: Union['BaseFile', AnyBytes],
    ) -> Self:
        r"""Merges with another file.

        Equivalent to :meth:`copy` then :meth:`merge`.

        Args:
            other (:class:`BaseFile` or bytes):
                Other file or bytes to merge.

        Returns:
            :class:`BaseFile`: *self* merged with *other*.

        See Also:
            :meth:`copy`
            :meth:`merge`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file1 = SrecFile.from_bytes(b'abc', offset=123)
            >>> file2 = SrecFile.from_bytes(b'xyz', offset=456)
            >>> file3 = file1 | file2
            >>> file3.memory.to_blocks()
            [[123, b'abc'], [456, b'xyz']]
            >>> file4 = file3 | b'789'
            >>> file4.memory.to_blocks()
            [[0, b'789'], [123, b'abc'], [456, b'xyz']]
        """

        return self.copy().merge(other)

    def __setitem__(
        self,
        key: Union[slice, int],
        value: Union[AnyBytes, ImmutableMemory, int, None],
    ) -> None:
        r"""Sets a range.

        Args:
            key (slice or int):
                Range to set.

            value (bytes, :class:`bytesparse.base.ImmutableMemory`, ``None``):
                Value(s) to set.
                ``None`` acts like :meth:`clear`.

        Raises:
            ValueError: invalid range.

        See Also:
            :meth:`bytesparse.base.MutableMemory.__setitem__`
            :meth:`clear`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [456, b'xyz']])
            >>> file[124] = b'?'
            >>> file.memory.to_blocks()
            [[123, b'a?c'], [456, b'xyz']]
            >>> file[:125] = None
            >>> file.memory.to_blocks()
            [[125, b'c'], [456, b'xyz']]
            >>> file[457:458] = b'789'
            >>> file.memory.to_blocks()
            [[125, b'c'], [456, b'x789z']]
        """

        self.memory[key] = value

    @classmethod
    def _is_line_empty(cls, line: AnyBytes) -> bool:
        r"""Empty line check.

        Tells whether a `line` has no meaningful content (e.g. all whitespace).
        The check itself depends on the implementing file *format*.
        It may be used internally to skip empty lines, e.g. by :meth:`parse`.

        Args:
            line (bytes):
                A line, byte string.

        Returns:
            :bool: The `line` is empty.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> IhexFile._is_line_empty(b'')
            True
            >>> IhexFile._is_line_empty(b' \t\v\r\n')
            True
            >>> IhexFile._is_line_empty(b':00000001FF\r\n')
            False
        """

        return not line or line.isspace()

    def align(
        self,
        modulo: int,
        start: Optional[int] = None,
        endex: Optional[int] = None,
        pattern: Union[int, AnyBytes] = 0,
    ) -> Self:
        r"""Pads blocks to align their boundaries.

        It fills memory holes of the underlying :attr:`memory` within the
        specified range with a `pattern`, so that memory blocks are aligned to
        the required `modulo`.

        Any stored :attr:`records` are discarded upon return.

        Args:
            modulo (int):
                Alignment modulo.

            start (int):
                Inclusive start address of the specified range.
                If ``None``, start from the beginning of the :attr:`memory`.

            endex (int):
                Exclusive end address of the specified range.
                If ``None``, extend after the end of the :attr:`memory`.

            pattern (bytes or int):
                Byte pattern for flooding.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :attr:`memory`
            :meth:`discard_records`
            :meth:`bytesparse.base.MutableMemory.align`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [134, b'xyz']])
            >>> _ = file.align(4, pattern=b'.')
            >>> file.memory.to_blocks()
            [[120, b'...abc..'], [132, b'..xyz...']]
        """

        self.memory.align(modulo, start=start, endex=endex, pattern=pattern)
        self.discard_records()
        return self

    def append(self, item: Union[AnyBytes, int]) -> Self:
        r"""Appends a byte.

        It appends the `item` to the underlyng :attr:`memory`.

        Any stored :attr:`records` are discarded upon return.

        Args:
            item (byte or int):
                Byte to append.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :attr:`memory`
            :meth:`discard_records`
            :meth:`bytesparse.base.MutableMemory.append`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_bytes(b'abc', offset=123)
            >>> _ = file.append(b'.')
            >>> _ = file.append(0)
            >>> file.memory.to_blocks()
            [[123, b'abc.\x00']]
        """

        self.memory.append(item)
        self.discard_records()
        return self

    def apply_records(self) -> Self:
        r"""Applies records to memory and meta.

        This method processes the stored :attr:`records`, converting *data* as
        :attr:`memory`, and special records into their *meta* counterparts.

        This effectively converts the *records role* into the *memory role*
        (keeping both).

        The :attr:`memory` and *meta* are assigned upon return.
        Any exceptions being raised should not alter the file object.

        Returns:
            :class:`BaseFile`: *self*.

        Raises:
            ValueError: :attr:`records` attribute not populated.

        See Also:
            :attr:`records`
            :attr:`memory`
            :meth:`get_meta`
            :meth:`update_records`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> IhexRecord = IhexFile.Record
            >>> records = [IhexRecord.create_data(123, b'abc'),
            ...            IhexRecord.create_start_linear_address(456),
            ...            IhexRecord.create_end_of_file()]
            >>> file = IhexFile.from_records(records, maxdatalen=16)
            >>> _ = file.apply_records()
            >>> file.memory.to_blocks()
            [[123, b'abc']]
            >>> file.get_meta()
            {'linear': True, 'maxdatalen': 16, 'startaddr': 456}
        """

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
    ) -> Self:
        r"""Clears data within a range.

        It clears the specified range of underlying :attr:`memory` object,
        making a memory hole.

        Any stored :attr:`records` are discarded upon return.

        Args:
            start (int):
                Inclusive start address of the specified range.
                If ``None``, start from the beginning of the :attr:`memory`.

            endex (int):
                Exclusive end address of the specified range.
                If ``None``, extend after the end of the :attr:`memory`.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :attr:`memory`
            :meth:`discard_records`
            :meth:`bytesparse.base.MutableMemory.clear`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [130, b'xyz']])
            >>> _ = file.clear(start=124, endex=132)
            >>> file.memory.to_blocks()
            [[123, b'a'], [132, b'z']]
        """

        self.memory.clear(start=start, endex=endex)
        self.discard_records()
        return self

    @classmethod
    def convert(
        cls,
        source: 'BaseFile',
        meta: bool = True,
    ) -> Self:
        r"""Converts a file object to another format.

        It copies the :attr:`memory` and *meta* of the `source` file object,
        creating a new one of the target :class:`BaseFile` format type.

        Args:
            source (:class:`BaseFile`):
                Source file object to convert.

            meta (bool):
                Copy *meta* information to the target file object.
                Only the keys of the target :attr:`META_KEYS` are processed.

        Returns:
            :class:`BaseFile`: Converted copy of `source` to the target format.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile, SrecFile
            >>> blocks = [[123, b'abc'], [456, b'xyz']]
            >>> source = IhexFile.from_blocks(blocks, startaddr=789)
            >>> target = SrecFile.convert(source)
            >>> target.memory is source.memory
            False
            >>> target.memory == source.memory
            True
            >>> target.get_meta()
            {'header': b'', 'maxdatalen': 16, 'startaddr': 789}
        """

        if meta:
            source_meta = source.get_meta()
            target_meta = {key: source_meta[key]
                           for key in cls.META_KEYS
                           if key in source_meta}
        else:
            target_meta = {}

        target_memory = source.memory.copy()
        target = cls.from_memory(memory=target_memory, **target_meta)
        return target

    def copy(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
        meta: bool = True,
    ) -> Self:
        r"""Copies within a range.

        It copied data within the specified range of the file object, creating
        a new one carrying the inner slice.

        Args:
            start (int):
                Inclusive start address of the specified range.
                If ``None``, start from the beginning of the :attr:`memory`.

            endex (int):
                Exclusive end address of the specified range.
                If ``None``, extend after the end of the :attr:`memory`.

            meta (bool):
                Copy *meta* information to the created file object.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :attr:`memory`
            :meth:`get_meta`
            :meth:`discard_records`
            :meth:`bytesparse.base.MutableMemory.cut`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [130, b'xyz']])
            >>> inner = file.copy(start=124, endex=132)
            >>> inner.memory.to_blocks()
            [[124, b'bc'], [130, b'xy']]
            >>> file.memory.to_blocks()
            [[123, b'abc'], [130, b'xyz']]
        """

        copied_memory = self.memory.extract(start=start, endex=endex, bound=False)
        copied_meta = self.get_meta() if meta else {}
        copied = self.from_memory(memory=copied_memory, **copied_meta)
        return copied

    def crop(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
    ) -> Self:
        r"""Clears data outside a range.

        It clears outside the specified range of underlying :attr:`memory`
        object, timming it.

        Any stored :attr:`records` are discarded upon return.

        Args:
            start (int):
                Inclusive start address of the specified range.
                If ``None``, start from the beginning of the :attr:`memory`.

            endex (int):
                Exclusive end address of the specified range.
                If ``None``, extend after the end of the :attr:`memory`.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :attr:`memory`
            :meth:`discard_records`
            :meth:`bytesparse.base.MutableMemory.crop`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [130, b'xyz']])
            >>> _ = file.crop(start=124, endex=132)
            >>> file.memory.to_blocks()
            [[124, b'bc'], [130, b'xy']]
        """

        self.memory.crop(start=start, endex=endex)
        self.discard_records()
        return self

    def cut(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
        meta: bool = False,
    ) -> Self:
        r"""Cuts data within a range.

        It takes data within the specified range away from the file object,
        creating a new one carrying the inner slice.
        The inner slice is cleared from *self*.

        Any stored :attr:`records` are discarded upon return.

        Args:
            start (int):
                Inclusive start address of the specified range.
                If ``None``, start from the beginning of the :attr:`memory`.

            endex (int):
                Exclusive end address of the specified range.
                If ``None``, extend after the end of the :attr:`memory`.

            meta (bool):
                Copy *meta* information to the created file object.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :attr:`memory`
            :meth:`clear`
            :meth:`get_meta`
            :meth:`discard_records`
            :meth:`bytesparse.base.MutableMemory.cut`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [130, b'xyz']])
            >>> inner = file.cut(start=124, endex=132)
            >>> inner.memory.to_blocks()
            [[124, b'bc'], [130, b'xy']]
            >>> file.memory.to_blocks()
            [[123, b'a'], [132, b'z']]
        """

        inner_memory = self.memory.cut(start=start, endex=endex, bound=False)
        inner_memory = _cast(MutableMemory, inner_memory)
        inner_meta = self.get_meta() if meta else {}
        inner = self.from_memory(memory=inner_memory, **inner_meta)
        self.discard_records()
        return inner

    def delete(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
    ) -> Self:
        r"""Deletes data within a range.

        It deletes the specified range of underlying :attr:`memory` object,
        shifting all subsequent data towards the collapsed range.

        Any stored :attr:`records` are discarded upon return.

        Args:
            start (int):
                Inclusive start address of the specified range.
                If ``None``, start from the beginning of the :attr:`memory`.

            endex (int):
                Exclusive end address of the specified range.
                If ``None``, extend after the end of the :attr:`memory`.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :attr:`memory`
            :meth:`discard_records`
            :meth:`bytesparse.base.MutableMemory.delete`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [130, b'xyz']])
            >>> _ = file.delete(start=124, endex=132)
            >>> file.memory.to_blocks()
            [[123, b'az']]
        """

        self.memory.delete(start=start, endex=endex)
        self.discard_records()
        return self

    def discard_records(self) -> Self:
        r"""Discards underlying records.

        The underlying :attr:`records` object is assigned ``None``.

        If the underlying :attr:`memory` object is ``None``, it is assigned
        a new empty memory object.

        Returns:
            :class:`BaseFile`: *self*.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> IhexRecord = IhexFile.Record
            >>> records = [IhexRecord.create_data(123, b'abc'),
            ...            IhexRecord.create_end_of_file()]
            >>> file = IhexFile.from_records(records)
            >>> _ = file.validate_records()
            >>> _ = file.discard_records()
            >>> _ = file.validate_records()
            Traceback (most recent call last):
                ...
            ValueError: records required
        """

        self._records = None
        if self._memory is None:
            self._memory = Memory()
        return self

    def discard_memory(self) -> Self:
        r"""Discards underlying memory.

        The underlying :attr:`memory` object is assigned ``None``.

        If the underlying :attr:`records` object is ``None``, it is assigned
        a new empty memory object.

        Returns:
            :class:`BaseFile`: *self*.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> file = IhexFile.from_bytes(b'abc', offset=123)
            >>> _ = file.update_records()
            >>> _ = file.discard_memory()
            >>> _ = file.update_records()
            Traceback (most recent call last):
                ...
            ValueError: memory instance required
        """

        self._memory = None
        if self._records is None:
            self._memory = Memory()
        return self

    def extend(
        self,
        other: Union['BaseFile', ImmutableMemory, AnyBytes],
    ) -> Self:
        r"""Concatenates data.

        It concatenates `other` to the underlyng :attr:`memory`.

        Any stored :attr:`records` are discarded upon return.

        Args:
            other (:class:`BaseFile` or bytes):
                Other file or bytes to concatenate.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :attr:`memory`
            :meth:`discard_records`
            :meth:`bytesparse.base.MutableMemory.extend`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file1 = SrecFile.from_bytes(b'abc', offset=123)
            >>> file2 = SrecFile.from_bytes(b'xyz', offset=456)
            >>> _ = file1.extend(file2)
            >>> file1.memory.to_blocks()
            [[123, b'abc'], [582, b'xyz']]
            >>> _ = file1.extend(b'789')
            >>> file1.memory.to_blocks()
            [[123, b'abc'], [582, b'xyz789']]
        """

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
    ) -> Self:
        r"""Fills a range.

        It writes a `pattern` of bytes onto the underlying :attr:`memory`
        object, overwriting anything within the specified range.

        Any stored :attr:`records` are discarded upon return.

        Args:
            start (int):
                Inclusive start address of the specified range.
                If ``None``, start from the beginning of the :attr:`memory`.

            endex (int):
                Exclusive end address of the specified range.
                If ``None``, extend after the end of the :attr:`memory`.

            pattern (bytes or int):
                Byte pattern for filling.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :attr:`memory`
            :meth:`discard_records`
            :meth:`bytesparse.base.MutableMemory.fill`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [130, b'xyz']])
            >>> _ = file.fill(start=124, endex=132, pattern=b'.')
            >>> file.memory.to_blocks()
            [[123, b'a........z']]
        """

        self.memory.fill(start=start, endex=endex, pattern=pattern)
        self.discard_records()
        return self

    def find(
        self,
        item: Union[AnyBytes, int],
        start: Optional[int] = None,
        endex: Optional[int] = None,
    ) -> int:
        r"""Finds a substring.

        It searches the provided `item` within the specified address range,
        returning the first matching address.

        If not found, it returns ``-1``.

        Args:
            item (bytes or int):
                Byte pattern to find.

            start (int):
                Inclusive start address of the specified range.
                If ``None``, start from the beginning of the :attr:`memory`.

            endex (int):
                Exclusive end address of the specified range.
                If ``None``, extend after the end of the :attr:`memory`.

        Returns:
            int: `item` beginning address; ``-1`` if not found.

        See Also:
            :attr:`index`
            :meth:`bytesparse.base.ImmutableMemory.find`

        Notes:
             The internal :attr:`memory` might allow negative addresses for its
             stored data.
             In that case, :meth:`index` would be more appropriate, because it
             raises an exception when the `item` is not found.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [456, b'xyz']])
            >>> file.find(b'yz')
            457
            >>> file.find(ord('b'))
            124
            >>> file.find(b'?')
            -1
        """

        offset = self.memory.find(item, start=start, endex=endex)
        return offset

    def flood(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
        pattern: Union[int, AnyBytes] = 0,
    ) -> Self:
        r"""Floods a range.

        It fills memory holes of the underlying :attr:`memory` within the
        specified range with a `pattern`.

        Any stored :attr:`records` are discarded upon return.

        Args:
            start (int):
                Inclusive start address of the specified range.
                If ``None``, start from the beginning of the :attr:`memory`.

            endex (int):
                Exclusive end address of the specified range.
                If ``None``, extend after the end of the :attr:`memory`.

            pattern (bytes or int):
                Byte pattern for flooding.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :attr:`memory`
            :meth:`discard_records`
            :meth:`bytesparse.base.MutableMemory.flood`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [130, b'xyz']])
            >>> file.get_holes()
            [(126, 130)]
            >>> _ = file.flood(start=124, endex=132, pattern=b'.')
            >>> file.memory.to_blocks()
            [[123, b'abc....xyz']]
        """

        self.memory.flood(start=start, endex=endex, pattern=pattern)
        self.discard_records()
        return self

    @classmethod
    def from_blocks(cls, blocks: BlockSequence, **meta) -> Self:
        r"""Creates a file object from a memory object.

        The `blocks` are put into the :attr:`memory` of the created file object.

        This method creates a file object in *memory role*.
        This means that only its :attr:`memory` is internally instanced, while
        the :attr:`records` requires manual or lazy instancing (i.e. either via
        direct call to :meth:`update_records`, or any other methods indirectly
        calling it).

        Args:
            blocks (list of blocks):
                Memory blocks to put into :attr:`memory`.

            meta:
                *Meta* attributes to set, among :attr:`META_KEYS`.

        Returns:
            :class:`BaseFile`: The created file object.

        Raises:
            KeyError: invalid `meta` key.

        See Also:
            :attr:`META_KEYS`
            :meth:`from_memory`
            :meth:`bytesparse.base.ImmutableMemory.from_blocks`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> blocks = [[123, b'abc'], [456, b'xyz']]
            >>> file = SrecFile.from_blocks(blocks, maxdatalen=8)
            >>> file.memory.to_blocks()
            [[123, b'abc'], [456, b'xyz']]
            >>> file.maxdatalen
            8
        """

        memory = Memory.from_blocks(blocks)
        file = cls.from_memory(memory, **meta)
        return file

    @classmethod
    def from_bytes(cls, data: AnyBytes, offset: int = 0, **meta) -> Self:
        r"""Creates a file object from a byte string.

        The byte string makes a single *data* block, placed at some offset
        within the :attr:`memory` of the created file object.

        This method creates a file object in *memory role*.
        This means that only its :attr:`memory` is internally instanced, while
        the :attr:`records` requires manual or lazy instancing (i.e. either via
        direct call to :meth:`update_records`, or any other methods indirectly
        calling it).

        Args:
            data (bytes):
                A byte string used to make a single data block.

            offset (int):
                Offset of the single data block within :attr:`memory`.

            meta:
                *Meta* attributes to set, among :attr:`META_KEYS`.

        Returns:
            :class:`BaseFile`: The created file object.

        Raises:
            KeyError: invalid `meta` key.

        See Also:
            :attr:`META_KEYS`
            :meth:`from_memory`
            :meth:`bytesparse.base.ImmutableMemory.from_bytes`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_bytes(b'abc', offset=123, maxdatalen=8)
            >>> file.memory.to_blocks()
            [[123, b'abc']]
            >>> file.maxdatalen
            8
        """

        memory = Memory.from_bytes(data, offset=offset)
        file = cls.from_memory(memory, **meta)
        return file

    @classmethod
    def from_memory(cls, memory: Optional[MutableMemory] = None, **meta) -> Self:
        r"""Creates a file object from a memory object.

        The `memory` is set as the :attr:`memory` of the created file object.

        This method creates a file object in *memory role*.
        This means that only its :attr:`memory` is internally instanced, while
        the :attr:`records` requires manual or lazy instancing (i.e. either via
        direct call to :meth:`update_records`, or any other methods indirectly
        calling it).

        Args:
            memory (:class:`bytesparse.base.MutableMemory`):
                Memory object to set as :attr:`memory`.
                If ``None``, an empty memory object is automatically created.

            meta:
                *Meta* attributes to set, among :attr:`META_KEYS`.

        Returns:
            :class:`BaseFile`: The created file object.

        Raises:
            KeyError: invalid `meta` key.

        See Also:
            :attr:`META_KEYS`
            :class:`bytesparse.base.MutableMemory`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from bytesparse import Memory
            >>> blocks = [[123, b'abc'], [456, b'xyz']]
            >>> memory = Memory.from_blocks(blocks)
            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_memory(memory, maxdatalen=8)
            >>> file.memory.to_blocks()
            [[123, b'abc'], [456, b'xyz']]
            >>> file.maxdatalen
            8
        """

        file = cls()

        if memory is not None:
            file._memory = memory

        for key, value in meta.items():
            if key in cls.META_KEYS:
                setattr(file, key, value)
            else:
                raise KeyError(f'invalid meta: {key}')

        return file

    @classmethod
    def from_records(
        cls,
        records: MutableSequence[BaseRecord],
        maxdatalen: Optional[int] = None,
    ) -> Self:
        r"""Creates a file object from records.

        The `records` sequence is set as the :attr:`record` attribute of the
        created file object.

        This method creates a file object in *records role*.
        This means that only its :attr:`records` is internally instanced, while
        the :attr:`memory` requires manual or lazy instancing (i.e. either via
        direct call to :meth:`apply_records`, or any other methods indirectly
        calling it).

        Args:
            records (list of :class:`BaseRecord`):
                Record sequence to set as :attr:`records`.

            maxdatalen:
                Maximum record *data* field size.
                If ``None``, the maximum non-zero size of the *data* field from
                the `records` sequence is used.
                If all the `records` have zero sized *data* field, the class
                attribute :attr:`DEFAULT_DATALEN` is used.

        Returns:
            :class:`BaseFile`: The created file object.

        Raises:
            ValueError: invalid *meta* values.

        See Also:
            :class:`BaseRecord`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> IhexRecord = IhexFile.Record
            >>> records = [IhexRecord.create_data(123, b'abc'),
            ...            IhexRecord.create_end_of_file()]
            >>> file = IhexFile.from_records(records)
            >>> file.memory.to_blocks()
            [[123, b'abc']]
            >>> file.maxdatalen
            3
        """

        if maxdatalen is None:
            dataiter = (len(r.data) for r in records if r.tag.is_data())
            maxdatalen = max(dataiter, default=0)
            if maxdatalen < 1:
                maxdatalen = cls.DEFAULT_DATALEN
        else:
            maxdatalen = maxdatalen.__index__()
            if maxdatalen < 1:
                raise ValueError('invalid maximum data length')

        file = cls()
        file._records = records
        file._memory = None
        file._maxdatalen = maxdatalen
        return file

    def get_address_max(self) -> int:
        r"""Maximum address within memory.

        It returns the maximum address of the underlying :attr:`memory` object.

        Returns:
            int: Maximum address.

        See Also:
            :attr:`bytesparse.base.ImmutableMemory.endin`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [456, b'xyz']])
            >>> file.get_address_max()
            458
        """

        return self.memory.endin

    def get_address_min(self) -> int:
        r"""Minimum address within memory.

        It returns the minimum address of the underlying :attr:`memory` object.

        Returns:
            int: Minimum address.

        See Also:
            :attr:`bytesparse.base.ImmutableMemory.start`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [456, b'xyz']])
            >>> file.get_address_min()
            123
        """

        return self.memory.start

    def get_holes(self) -> List[Tuple[int, int]]:
        r"""List of memory holes.

        It scans the underlying :attr:`memory` and returns the list of memory
        holes/gaps.

        Each hole is a couple of ``(start, stop)`` addresses
        (as per :class:`slice` or :func:`range`).

        Returns:
            list of couples: List of memory hole boundaries.

        See Also:
            :meth:`bytesparse.base.ImmutableMemory.gaps`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> blocks = [[123, b'abc'], [456, b'xyz'], [789, b'?!']]
            >>> file = SrecFile.from_blocks(blocks)
            >>> file.get_holes()
            [(126, 456), (459, 789)]
        """

        memory = self.memory
        holes = list(memory.gaps(memory.start, memory.endex))
        return holes

    def get_spans(self) -> List[Tuple[int, int]]:
        r"""List of memory block spans.

        It scans the underlying :attr:`memory` and returns the list of memory
        block spans/intervals.

        Each span is a couple of ``(start, stop)`` addresses
        (as per :class:`slice` or :func:`range`).

        Returns:
            list of couples: List of memory block boundaries.

        See Also:
            :meth:`bytesparse.base.ImmutableMemory.intervals`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> blocks = [[123, b'abc'], [456, b'xyz'], [789, b'?!']]
            >>> file = SrecFile.from_blocks(blocks)
            >>> file.get_spans()
            [(123, 126), (456, 459), (789, 791)]
        """

        spans = list(self.memory.intervals())
        return spans

    def get_meta(self) -> Mapping[str, Any]:
        r"""Meta information.

        It builds and returns a dictionary of *meta* information.
        Meta keys are taken from the :attr:`META_KEYS` class attribute.

        Returns:
            dict: Meta information dictionary.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> blocks = [[123, b'abc'], [456, b'xyz'], [789, b'?!']]
            >>> file = SrecFile.from_blocks(blocks, header=b'HDR\0')
            >>> file.get_meta()
            {'header': b'HDR\x00', 'maxdatalen': 16, 'startaddr': 0}
        """

        meta = {key: getattr(self, key) for key in self.META_KEYS}
        return meta

    def index(
        self,
        item: Union[AnyBytes, int],
        start: Optional[int] = None,
        endex: Optional[int] = None,
    ) -> int:
        r"""Finds a substring.

        It searches the provided `item` within the specified address range,
        returning the first matching address.

        If not found, it raises :class:`ValueError`.

        Args:
            item (bytes or int):
                Byte pattern to find.

            start (int):
                Inclusive start address of the specified range.
                If ``None``, start from the beginning of the :attr:`memory`.

            endex (int):
                Exclusive end address of the specified range.
                If ``None``, extend after the end of the :attr:`memory`.

        Returns:
            int: `item` beginning address.

        Raises:
            ValueError: `item` not found.

        See Also:
            :attr:`find`
            :meth:`bytesparse.base.ImmutableMemory.index`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [456, b'xyz']])
            >>> file.index(b'yz')
            457
            >>> file.index(ord('b'))
            124
            >>> file.index(b'?')
            Traceback (most recent call last):
                ...
            ValueError: subsection not found
        """

        offset = self.memory.index(item, start=start, endex=endex)
        return offset

    @classmethod
    def load(
        cls,
        in_path_or_stream: Optional[Union[AnyPath, IO]],
        *args,
        **kwargs,
    ) -> Self:
        r"""Loads a file object from the filesystem.

        The :func:`open` function creates a *stream* from the filesystem,
        allowing :meth:`parse` to load a file object.

        Args:
            path_or_stream (str or bytes IO):
                Path of the file within the filesystem, or byte input stream.
                If ``None``, ``sys.stdin.buffer`` is used.

            args:
                Forwarded to :meth:`parse`.

            kwargs:
                Forwarded to :meth:`parse`.

        Returns:
            :class:`BaseFile`: Loaded file object.

        See Also:
            :meth:`save`
            :meth:`parse`
            :func:`open`
            :attr:`sys.stdin.buffer`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> file = IhexFile.load('data.hex')
            >>> file.memory.to_blocks()
            [[55930, b'abc']]
            >>> file.get_meta()
            {'linear': True, 'maxdatalen': 3, 'startaddr': 51966}
        """

        if in_path_or_stream is None:
            in_path_or_stream = sys.stdin.buffer

        if isinstance(in_path_or_stream, io.IOBase):
            stream = in_path_or_stream
            return cls.parse(stream, *args, **kwargs)
        else:
            path = str(in_path_or_stream)
            with open(path, 'rb') as stream:
                return cls.parse(stream, *args, **kwargs)

    @property
    def maxdatalen(self) -> int:
        r"""int: Maximum byte size of the data field.

        This property sets the maximum byte size of the *data* field of a
        serialized record.

        This is usually taken into account by :meth:`update_records` while
        splitting :attr:`memory` into :attr:`records`.

        Setting a different value triggers :meth:`discard_records`.

        Raises:
            ValueError: Invalid maximum data length.

        See Also:
            :meth:`update_records`
            :meth:`discard_records`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> buffer = bytes(range(64))
            >>> file = SrecFile.from_bytes(buffer)
            >>> file.maxdatalen
            16
            >>> _ = file.print()
            S0030000FC
            S1130000000102030405060708090A0B0C0D0E0F74
            S1130010101112131415161718191A1B1C1D1E1F64
            S1130020202122232425262728292A2B2C2D2E2F54
            S1130030303132333435363738393A3B3C3D3E3F44
            S5030004F8
            S9030000FC
            >>> file.maxdatalen = 8
            >>> _ = file.print()
            S0030000FC
            S10B00000001020304050607D8
            S10B000808090A0B0C0D0E0F90
            S10B0010101112131415161748
            S10B001818191A1B1C1D1E1F00
            S10B00202021222324252627B8
            S10B002828292A2B2C2D2E2F70
            S10B0030303132333435363728
            S10B003838393A3B3C3D3E3FE0
            S5030008F4
            S9030000FC
            >>> file.maxdatalen = 0
            Traceback (most recent call last):
                ...
            ValueError: invalid maximum data length
        """

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
        r""":class:`bytesparse.Memory`: Memory object stored by records role.

        This readonly property exposes the memory object stored by the file
        object while in *memory role*.

        If this property is accessed while the file object is not in
        *memory role*, it automatically activates it by an implicit call to
        :meth:`apply_records`, with default arguments.

        For more control activating the *memory role*, please call
        :meth:`apply_records` manually, providing the desired arguments.

        Notes:
            Most methods acting on the *records role* (i.e. altering content of
            :attr:`records`) would implicitly discard :attr:`memory` via
            :meth:`discard_memory`.

        See Also:
            :meth:`apply_records`
            :meth:`discard_memory`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> blocks = [[123, b'abc'], [456, b'xyz']]
            >>> file = SrecFile.from_blocks(blocks)
            >>> file.memory.to_blocks()
            [[123, b'abc'], [456, b'xyz']]
            >>> _ = file.write(789, b'?!')
            >>> file.memory.to_blocks()
            [[123, b'abc'], [456, b'xyz'], [789, b'?!']]
        """

        if self._memory is None:
            self.apply_records()
        return self._memory

    def merge(self, *files: 'BaseFile', clear: bool = False) -> Self:
        r"""Merges data onto the file.

        It writes the provided `files` onto *self*, in the provided order.
        Any common address ranges are overwritten.

        Any stored :attr:`records` are discarded upon return.

        Args:
            files (:class:`BaseFile`):
                Files to merge.

            clear (bool):
                :meth:`clear` the target address range before writing.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :meth:`clear`
            :meth:`discard_records`
            :meth:`write`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file1 = SrecFile.from_bytes(b'abc', offset=123)
            >>> file2 = SrecFile.from_bytes(b'xyz', offset=456)
            >>> file3 = SrecFile.from_bytes(b'<<<?????>>>', offset=450)
            >>> _ = file3.merge(file1, file2)
            >>> file3.memory.to_blocks()
            [[123, b'abc'], [450, b'<<<???xyz>>']]
        """

        for file in files:
            self.write(0, file, clear=clear)
        return self

    @classmethod
    def parse(
        cls,
        stream: Union[AnyBytes, IO],
        ignore_errors: bool = False,
        ignore_after_termination: bool = True,
    ) -> Self:
        r"""Parses records from a byte stream.

        It executes :meth:`BaseRecord.parse` for each line of the incoming
        `stream`, creating a new file object with the collected records calling
        :meth:`from_records`.

        Lines resulting empty by :meth:`_is_empty_line` are just discarded.

        Notes:
            Please refer to the actual implementation of each record file
            *format*, because it may be more specialized.

        Args:
            stream (bytes IO or buffer):
                Stream or byte buffer to parse records from.

            ignore_errors (bool):
                Ignore :class:`Exception` raised by :meth:`BaseRecord.parse`.

            ignore_after_termination (bool):
                Ignore anything after the termination record was parsed, if
                supported (e.g. *End Of File* or *start address* record,
                depending on the specific file *format*).

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :meth:`parse`
            :meth:`BaseRecord.parse`
            :meth:`from_records`
            :meth:`_is_empty_line`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> buffer = b'''
            ...     :03DA7A0061626383
            ...     :040000050000CAFE2F
            ...     :00000001FF
            ... '''
            >>> import io
            >>> stream = io.BytesIO(buffer)
            >>> file = IhexFile.parse(stream)
            >>> file.memory.to_blocks()
            [[55930, b'abc']]
            >>> file.get_meta()
            {'linear': True, 'maxdatalen': 3, 'startaddr': 51966}
            >>> file = IhexFile.parse(buffer)
            >>> file.memory.to_blocks()
            [[55930, b'abc']]
            >>> file.get_meta()
            {'linear': True, 'maxdatalen': 3, 'startaddr': 51966}
        """

        if isinstance(stream, (bytes, bytearray, memoryview)):
            stream = io.BytesIO(stream)

        Record = cls.Record
        records = []
        row = 0

        for line in stream:
            row += 1

            if cls._is_line_empty(line):
                continue

            try:
                record = Record.parse(line)
            except Exception:
                if ignore_errors:
                    continue
                raise

            record.coords = (row, 0)
            records.append(record)

            if ignore_after_termination:
                if record.tag.is_file_termination():
                    break

        file = cls.from_records(records)
        return file

    def print(
        self,
        *args,
        stream: Optional[IO] = None,
        color: bool = False,
        start: Optional[int] = None,
        stop: Optional[int] = None,
        **kwargs,
    ) -> Self:
        r"""Prints record content to stdout.

        This helper method prints each record of :attr:`records` via
        :meth:`BaseRecord.print`.
        As such, it also supports colored tokens and streams different from
        *stdout*.

        It is possible to print subset of the records by specifying the record
        index range.

        Warnings:
            This method is **NOT** equivalent to :meth:`serialize`, because it
            just prints each record from :attr:`records`.
            Please use :meth:`serialize` for an actual serialization of the
            whole file.

        Args:
            args:
                Forwarded to the underlying call to :meth:`to_tokens`.

            stream (byte stream):
                Stream to print onto.
                If ``None``, *stdout* is used.

            color (bool):
                Colorize record tokens with ANSI color codes.

            start (int):
                Inclusive start record index of the specified range.
                If ``None``, start from the first record.

            stop (int):
                Exclusive end record index of the specified range.
                If negative, look back from the last index.
                If ``None``, print up to the last record.

            kwargs:
                Forwarded to the underlying call to :meth:`to_tokens`.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :meth:`BaseRecord.print`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> buffer = bytes(range(64))
            >>> file = SrecFile.from_bytes(buffer)
            >>> _ = file.print()
            S0030000FC
            S1130000000102030405060708090A0B0C0D0E0F74
            S1130010101112131415161718191A1B1C1D1E1F64
            S1130020202122232425262728292A2B2C2D2E2F54
            S1130030303132333435363738393A3B3C3D3E3F44
            S5030004F8
            S9030000FC
            >>> _ = file.print(color=True, start=1, stop=-2)
            S1130000000102030405060708090A0B0C0D0E0F74
            S1130010101112131415161718191A1B1C1D1E1F64
            S1130020202122232425262728292A2B2C2D2E2F54
            S1130030303132333435363738393A3B3C3D3E3F44
        """

        for record in self.records[start:stop]:
            record.print(*args, stream=stream, color=color, **kwargs)
        return self

    def read(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
        fill: Union[int, AnyBytes] = 0,
    ) -> bytes:
        r"""Extracts a substring.

        It extracts a byte string from the specified range, filling any memory
        holes/gaps (without altering :attr:`memory`).

        Args:
            start (int):
                Inclusive start address of the specified range.
                If ``None``, start from the beginning of the :attr:`memory`.

            endex (int):
                Exclusive end address of the specified range.
                If ``None``, extend after the end of the :attr:`memory`.

            fill (bytes or int):
                Byte pattern for filling.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :attr:`memory`
            :meth:`bytesparse.base.MutableMemory.extract`
            :meth:`bytesparse.base.MutableMemory.to_bytes`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [130, b'xyz']])
            >>> file.read(start=124, endex=132)
            b'bc\x00\x00\x00\x00xy'
            >>> file.read(start=124, endex=132, fill=b'.')
            b'bc....xy'
            >>> file.memory.to_blocks()
            [[123, b'abc'], [130, b'xyz']]
        """

        memory = self.memory.extract(start=start, endex=endex, pattern=fill)
        chunk = memory.to_bytes()
        return chunk

    @property
    def records(self) -> MutableSequence[BaseRecord]:
        r"""list of :class:`BaseRecord`: Records stored by records role.

        This readonly property exposes the list of records stored by the file
        object while in *records role*.

        If this property is accessed while the file object is not in
        *records role*, it automatically activates it by an implicit call to
        :meth:`update_records`, with default arguments.

        For more control activating the *records role*, please call
        :meth:`update_records` manually, providing the desired arguments.

        Notes:
            Most methods acting on the *memory role* (i.e. altering content of
            :attr:`memory`) would implicitly discard :attr:`records` via
            :meth:`discard_records`.

        See Also:
            :meth:`update_records`
            :meth:`discard_records`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> blocks = [[123, b'abc'], [456, b'xyz']]
            >>> file = SrecFile.from_blocks(blocks, startaddr=789)
            >>> len(file.records)
            5
            >>> _ = file.print()
            S0030000FC
            S106007B61626358
            S10601C878797AC5
            S5030002FA
            S9030315E4
            >>> _ = file.update_records(data_tag=SrecFile.Record.Tag.DATA_32)
            >>> _ = file.print()
            S0030000FC
            S3080000007B61626356
            S308000001C878797AC3
            S5030002FA
            S70500000315E2
        """

        if self._records is None:
            self.update_records()
        return self._records

    def save(
        self,
        out_path_or_stream: Optional[Union[AnyPath, IO]],
        *args,
        **kwargs,
    ) -> Self:
        r"""Saves a file object into the filesystem.

        The :func:`open` function creates a *stream* from the filesystem,
        allowing :meth:`serialize` to save a file object.

        Args:
            out_path_or_stream (str or bytes IO):
                Path of the file within the filesystem, or output byte stream.
                If ``None``, ``sys.stdout.buffer`` is used.

            args:
                Forwarded to :meth:`serialize`.

            kwargs:
                Forwarded to :meth:`serialize`.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :meth:`load`
            :meth:`serialize`
            :func:`open`
            :attr:`sys.stdout.buffer`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> file = IhexFile.from_blocks([[0xDA7A, b'abc']], startaddr=0xCAFE)
            >>> _ = file.save('data.hex')
        """

        if out_path_or_stream is None:
            out_path_or_stream = sys.stdout.buffer

        if isinstance(out_path_or_stream, io.IOBase):
            stream = out_path_or_stream
            return self.serialize(stream, *args, **kwargs)
        else:
            path = str(out_path_or_stream)
            with open(path, 'wb') as stream:
                return self.serialize(stream, *args, **kwargs)

    def set_meta(
        self,
        meta: Mapping[str, Any],
        strict: bool = True,
    ) -> Self:
        r"""Sets meta information.

        It sets the provided *kwargs* to their matching *meta* attributes, as
        listed by :attr:`META_KEYS`.

        Args:
            meta (dict):
                Mapping of the *meta* information to set.

            strict (bool):
                All the keys within `meta` must exist within :attr:`META_KEYS`.

        Returns:
             dict: Attribute values listed by :attr:`META_KEYS`.

        Raises:
            KeyError: invalid *meta* key.

        See Also:
            :attr:`META_KEYS`
            :meth:`get_meta`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> blocks = [[123, b'abc'], [456, b'xyz'], [789, b'?!']]
            >>> file = SrecFile.from_blocks(blocks)
            >>> file.get_meta()
            {'header': b'', 'maxdatalen': 16, 'startaddr': 0}
            >>> _ = file.set_meta(dict(header=b'HDR\0', startaddr=456))
            >>> file.get_meta()
            {'header': b'HDR\x00', 'maxdatalen': 16, 'startaddr': 456}
        """

        for key, value in meta.items():
            if key in self.META_KEYS or not strict:
                setattr(self, key, value)
            else:
                raise KeyError(f'unknown meta: {key!r}')
        self.discard_records()
        return self

    def serialize(self, stream: io.IOBase, *args, **kwargs) -> Self:
        r"""Serializes records onto a byte stream.

        It executes :meth:`BaseRecord.serialize` for each of the stored
        :attr:`records`.

        Args:
            stream (bytes IO):
                Stream to serialize records onto.

            args:
                Forwarded to :meth:`BaseRecord.serialize` of each record.

            kwargs:
                Forwarded to :meth:`BaseRecord.serialize` of each record.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :meth:`parse`
            :meth:`BaseRecord.serialize`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> file = IhexFile.from_blocks([[0xDA7A, b'abc']], startaddr=0xCAFE)
            >>> import sys
            >>> _ = file.serialize(sys.stdout.buffer, end=b'\n')
            :03DA7A0061626383
            :040000050000CAFE2F
            :00000001FF
        """

        for record in self.records:
            record.serialize(stream, *args, **kwargs)
        return self

    def shift(self, offset: int) -> Self:
        r"""Shifts data addresses by an offset.

        It shifts addresses of the underlying :attr:`memory` object data blocks
        by the provided `offset` amount.

        Any stored :attr:`records` are discarded upon return.

        Args:
            offset (int):
                Offset to apply to the underlying data block addresses.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :attr:`memory`
            :meth:`discard_records`
            :meth:`bytesparse.base.MutableMemory.shift`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [456, b'xyz']])
            >>> _ = file.shift(1000)
            >>> file.memory.to_blocks()
            [[1123, b'abc'], [1456, b'xyz']]
        """

        self.memory.shift(offset)
        self.discard_records()
        return self

    def split(
        self,
        *addresses: int,
        meta: bool = True,
    ) -> List['BaseFile']:
        r"""Splits into parts.

        The provided `addresses` are sorted and used as markers to split `self`
        into parts.

        Each part is the :meth:`copy` of *self* within the range of that part,
        in *memory role* (i.e., :attr:`records` is not populated).

        Args:
            addresses (int):
                Split points.

            meta (bool):
                Each part inherits *meta* from `self`.

        Returns:
            list of :class:`BaseFile`: Parts after splitting.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_bytes(b'Hello, World!', offset=123)
            >>> parts = file.split(128, 130)
            >>> for part in parts: print(part.memory.to_blocks())
            [[123, b'Hello']]
            [[128, b', ']]
            [[130, b'World!']]
            >>> file.memory.to_blocks()
            [[123, b'Hello, World!']]
        """

        pivots: List[Optional[int]] = list(addresses)
        pivots.sort()
        pivots.append(None)
        previous = None
        parts: List[BaseFile] = []

        for address in pivots:
            part = self.copy(start=previous, endex=address, meta=meta)
            parts.append(part)
            previous = address

        return parts

    @abc.abstractmethod
    def update_records(self) -> Self:
        r"""Applies memory and meta to records.

        This method processes the stored :attr:`memory` and *meta* information
        to generate the sequence of :attr:`records`.

        This effectively converts the *memory role* into the *records role*
        (keeping both).

        The :attr:`records` is assigned upon return.
        Any exceptions being raised should not alter the file object.

        Returns:
            :class:`BaseFile`: *self*.

        Raises:
            ValueError: :attr:`memory` attribute not populated.

        See Also:
            :attr:`records`
            :attr:`memory`
            :meth:`get_meta`
            :meth:`apply_records`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> blocks = [[123, b'abc']]
            >>> file = IhexFile.from_blocks(blocks, maxdatalen=16, startaddr=456)
            >>> file.memory.to_blocks()
            [[123, b'abc']]
            >>> file.get_meta()
            {'linear': True, 'maxdatalen': 16, 'startaddr': 456}
            >>> _ = file.update_records()
            >>> len(file.records)
            3
            >>> _ = file.print()
            :03007B006162635C
            :04000005000001C82E
            :00000001FF
        """
        ...

    @abc.abstractmethod
    def validate_records(self) -> Self:
        r"""Validates records.

        It performs consistency checks for the underlying :attr:`records`.

        Please refer to the record *format* implementation for more details.

        Raises:
            ValueError: Invalid record sequence.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import IhexFile
            >>> records = [IhexFile.Record.create_data(123, b'abc')]
            >>> file = IhexFile.from_records(records)
            >>> file.validate_records()
            Traceback (most recent call last):
                ...
            ValueError: missing end of file record
        """
        ...

    def view(
        self,
        start: Optional[int] = None,
        endex: Optional[int] = None,
    ) -> memoryview:
        r"""Memory view.

        It returns a :class:`memoryview` over the specified range, which must
        cover a *contiguous* data region (i.e. no memory holes within).

        Args:
            start (int):
                Inclusive start address of the specified range.
                If ``None``, start from the beginning of the :attr:`memory`.

            endex (int):
                Exclusive end address of the specified range.
                If ``None``, extend after the end of the :attr:`memory`.

        Returns:
            memoryview: View of the specified range.

        Raises:
            ValueError: non-contiguous data within range.

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile.from_blocks([[123, b'abc'], [456, b'xyz']])
            >>> bytes(file.view(start=456, endex=458))
            b'xy'
            >>> bytes(file.view())
            Traceback (most recent call last):
                ...
            ValueError: non-contiguous data within range
        """

        view = self.memory.view(start=start, endex=endex)
        return view

    def write(
        self,
        address: int,
        data: Union['BaseFile', AnyBytes, int, ImmutableMemory],
        clear: bool = False,
    ) -> Self:
        r"""Writes data into the file.

        It writes the provided `data` into the underlying :attr:`memory` object.

        Any stored :attr:`records` are discarded upon return.

        Args:
            address (int):
                Address where `data` has to be written.

            data (bytes or memory):
                Byte data to write.

            clear (bool):
                :meth:`clear` the target address range before writing.

        Returns:
            :class:`BaseFile`: *self*.

        See Also:
            :attr:`memory`
            :meth:`clear`
            :meth:`discard_records`
            :meth:`bytesparse.base.MutableMemory.write`

        Examples:
            **NOTE:** These examples are provided by :class:`BaseFile`.
            Inherited classes for specific *formats* may require an adaptation.

            >>> from hexrec import SrecFile
            >>> file = SrecFile()
            >>> _ = file.write(123, b'abc')
            >>> _ = file.write(555, ord('?'))
            >>> _ = file.write(1000, SrecFile.from_bytes(b'xyz', offset=456))
            >>> file.memory.to_blocks()
            [[123, b'abc'], [555, b'?'], [1456, b'xyz']]
        """

        if isinstance(data, BaseFile):
            data = data.memory
        self.memory.write(address, data, clear=clear)
        self.discard_records()
        return self


if not __TYPING_HAS_SELF:  # pragma: no cover
    del Self
