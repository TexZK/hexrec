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

r"""Generic utility functions.
"""
import binascii
import os
import re
from typing import Any
from typing import AnyStr
from typing import ByteString
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import Union

try:
    from typing import TypeAlias
except ImportError:  # pragma: no cover
    TypeAlias = Any  # Python < 3.10

AnyBytes: TypeAlias = Union[ByteString, bytes, bytearray, memoryview]
AnyPath: TypeAlias = Union[bytes, bytearray, str, os.PathLike]
EllipsisType: TypeAlias = Type['Ellipsis']

BIN8_TO_STR: Tuple[str] = tuple(bin(i)[2:].zfill(8) for i in range(256))
STR_TO_BIN8: Mapping[str, int] = {s: i for i, s in enumerate(BIN8_TO_STR)}

INT_REGEX = re.compile(r'^\s*(?P<sign>[+-]?)\s*'
                       r'(?P<prefix>(0x|0b|0o|0)?)'
                       r'(?P<value>[a-f0-9]+)'
                       r'(?P<suffix>h?)'
                       r'(?P<scale>[km]?)\s*$')


def check_empty_args_kwargs(
    args: Optional[Sequence[Any]],
    kwargs: Optional[Mapping[Any, Any]],
) -> None:
    r"""Checks for empty positional and keyword arguments.

    Both `args` and `kwargs` must be either ``None`` or equivalent to
    ``False``.
    If the check is not satisfied, a :obj:`ValueError` exception is raised.

    Arguments:
        args (list):
            List of unexpected positional arguments, or ``Null``.

        kwargs (dict):
            List of unexpected keyword arguments, or ``Null``.

    Raises:
        ValueError: Condition not satisfied.
    """
    if args:
        raise ValueError('unexpected positional argument(s)')
    if kwargs:
        raise ValueError('unexpected keyword argument(s): '
                         f'{", ".join(kwargs.keys())}')


def parse_int(
    value: Union[str, Any],
) -> Optional[int]:
    r"""Parses an integer.

    Arguments:
        value:
            A generic object to convert to integer.
            In case `value` is a :obj:`str` (case-insensitive), it can be
            either prefixed with ``0x`` or postfixed with ``h`` to convert
            from an hexadecimal representation, or prefixed with ``0b`` from
            binary; a prefix of only ``0`` converts from octal.
            A further suffix of ``k`` or ``m`` scales as *kibibyte* or
            *mebibyte*.
            A ``None`` value evaluates as ``None``.
            Any other object class will call the standard :func:`int`.

    Returns:
        int: None if `value` is ``None``, its integer conversion otherwise.

    Examples:
        >>> parse_int('-0xABk')
        -175104

        >>> parse_int(None)


        >>> parse_int(123)
        123

        >>> parse_int(135.7)
        135
    """
    if value is None:
        return None

    elif isinstance(value, str):
        value = value.lower()
        m = INT_REGEX.match(value)
        if not m:
            raise ValueError(f'invalid syntax: {value!r}')
        g = m.groupdict()
        sign = g['sign']
        prefix = g['prefix']
        value = g['value']
        suffix = g['suffix']
        scale = g['scale']
        if prefix in ('0b', '0o') and suffix == 'h':
            raise ValueError(f'invalid syntax: {value!r}')

        if prefix == '0x' or suffix == 'h':
            i = int(value, 16)
        elif prefix == '0b':
            i = int(value, 2)
        elif prefix == '0' or prefix == '0o':
            i = int(value, 8)
        else:
            i = int(value, 10)

        if scale == 'k':
            i <<= 10
        elif scale == 'm':
            i <<= 20

        if sign == '-':
            i = -i

        return i

    else:
        return int(value)


def chop(
    vector: Sequence[Any],
    window: int,
    align_base: int = 0,
) -> Iterator[Any]:
    r"""Chops a vector.

    Iterates through the vector grouping its items into windows.

    Arguments:
        vector (items):
            Vector to chop.

        window (int):
            Window length.

        align_base (int):
            Offset of the first window.

    Yields:
        list or items: `vector` slices of up to `window` elements.

    Examples:
        >>> list(chop(b'ABCDEFG', 2))
        ['AB', 'CD', 'EF', 'G']

        >>> ':'.join(chop('ABCDEFG', 2))
        'AB:CD:EF:G'

        >>> list(chop('ABCDEFG', 4, 3))
        ['A', 'BCDE', 'FG']
    """
    window = int(window)
    if window <= 0:
        raise ValueError('non-positive window')

    align_base = int(align_base)
    if align_base:
        offset = -align_base % window
        chunk = vector[:offset]
        yield chunk
    else:
        offset = 0

    for i in range(offset, len(vector), window):
        yield vector[i:(i + window)]


def chop_blocks(
    items: AnyBytes,
    window: int,
    align_base: int = 0,
    start: int = 0,
) -> Iterator[List[Union[int, AnyBytes]]]:
    r"""Chops a sequence of items into blocks.

    Iterates through the vector grouping its items into windows.

    Arguments:
        items (items):
            Sequence of items to chop.

        window (int):
            Window length.

        align_base (int):
            Offset of the first window.

        start (int):
            Start address.

    Yields:
        items: `items` slices of up to `window` elements.

    Examples:
        +---+---+---+---+---+---+---+---+---+
        | 9 | 10| 11| 12| 13| 14| 15| 16| 17|
        +===+===+===+===+===+===+===+===+===+
        |   |[A | B]|[C | D]|[E | F]|[G]|   |
        +---+---+---+---+---+---+---+---+---+

        >>> list(chop_blocks(b'ABCDEFG', 2, start=10))
        [[10, b'AB'], [12, b'CD'], [14, b'EF'], [16, b'G']]

        ~~~

        +---+---+---+---+---+---+---+---+---+
        | 12| 13| 14| 15| 16| 17| 18| 19| 20|
        +===+===+===+===+===+===+===+===+===+
        |   |[A]|[B | C | D | E]|[F | G]|   |
        +---+---+---+---+---+---+---+---+---+

        >>> list(chop_blocks(b'ABCDEFG', 4, 3, 10))
        [[13, b'A'], [14, b'BCDE'], [18, b'FG']]
    """
    offset = start + align_base
    for chunk in chop(items, window, align_base):
        yield [offset, chunk]
        offset += len(chunk)


def columnize(
    line: AnyStr,
    width: int,
    sep: AnyStr = '',
    newline: AnyStr = '\n',
    window: int = 1,
) -> str:
    r"""Splits and wraps a line into columns.

    A text line is wrapped up to a width limit, separated by a given newline
    string. Each wrapped line is then split into columns by some window size,
    separated by a given separator string.

    Arguments:
        line (str):
            Line of text to columnize.

        width (int):
            Maximum line width.

        sep (str):
            Column separator string.

        newline (str):
            Line separator string.

        window (int):
            Splitted column length.

    Returns:
        str: A wrapped and columnized text.

    Examples:
        >>> columnize('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 6)
        'ABCDEF\nGHIJKL\nMNOPQR\nSTUVWX\nYZ'

        >>> columnize('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 6, sep=' ', window=3)
        'ABC DEF\nGHI JKL\nMNO PQR\nSTU VWX\nYZ'
    """
    if sep and window:
        flat = newline.join(sep.join(chop(token, window))
                            for token in chop(line, width))
    else:
        if width >= len(line):
            flat = line
        else:
            flat = newline.join(chop(line, width))
    return flat


def hexlify(
    data: ByteString,
    width: int = None,
    sep: str = '',
    newline: str = '\n',
    window: int = 2,
    upper: bool = True,
) -> str:
    r"""Splits ans wraps byte data into hexadecimal columns.

    A chunk of byte data is converted into a hexadecimal text line, and then
    columnized as per :func:`columnize`.

    Arguments:
        data (bytes):
            Byte data.

        width (int):
            Maximum line width, or ``None``.

        sep (str):
            Column separator string.

        newline (str):
            Line separator string.

        window (int):
            Splitted column length.

        upper (bool):
            Uppercase hexadecimal digits.

    Returns:
        str: A wrapped and columnized hexadecimal representation of the data.

    Example:
        >>> hexlify(b'Hello, World!', sep='.')
        '48.65.6C.6C.6F.2C.20.57.6F.72.6C.64.21'

        >>> hexlify(b'Hello, World!', 6, ' ')
        '48 65 6C\n6C 6F 2C\n20 57 6F\n72 6C 64\n21'
    """
    if width is None:
        width = 2 * len(data)

    if upper:
        hexstr = binascii.hexlify(data).upper().decode()
    else:
        hexstr = binascii.hexlify(data).decode()

    return columnize(hexstr, width, sep, newline, window)


def unhexlify(
    hexstr: str,
) -> bytes:
    r"""Converts a hexadecimal text line into bytes.

    Arguments:
        hexstr (str):
            A hexadecimal text line. Whitespace is removed, and the resulting
            total length must be a multiple of 2.

    Returns:
        bytes: Text converted into byte data.

    Example:
        >>> unhexlify('48656C6C 6F2C2057 6F726C64 21')
        b'Hello, World!'
    """
    data = binascii.unhexlify(''.join(hexstr.split()))
    return data
