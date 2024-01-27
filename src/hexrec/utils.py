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

r"""Generic utility functions."""

import binascii
import re
import sys
from typing import Any
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Optional
from typing import Union

from .base import AnyBytes
from .base import EllipsisType

BIN8_TO_STR: List[str] = [bin(i)[2:].zfill(8) for i in range(256)]
STR_TO_BIN8: Mapping[str, int] = {s: i for i, s in enumerate(BIN8_TO_STR)}

BIN8_TO_BYTES: List[bytes] = [bin(i)[2:].zfill(8).encode() for i in range(256)]
BYTES_TO_BIN8: Mapping[bytes, int] = {s: i for i, s in enumerate(BIN8_TO_BYTES)}

INT_REGEX = re.compile(r'^\s*(?P<sign>[+-]?)\s*'
                       r'(?P<prefix>(0x|0b|0o|0)?)'
                       r'(?P<value>[a-f0-9]+)'
                       r'(?P<suffix>h?)'
                       r'(?P<scale>[km]?)\s*$')

DEFAULT_DELETE: bytes = b' \t.-:\r\n'
r"""Delete from hex strings.

Default values to delete from hexadecimal strings via :meth:`unhexlify`.
These are commonly used as byte separators or whitespace in hex strings.
"""

__BINASCII_HEXLIFY_HAS_SEP = (sys.version_info >= (3, 8))


def chop(
    vector: AnyBytes,
    window: int,
    align_base: int = 0,
) -> Iterator[AnyBytes]:
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

        >>> b':'.join(chop(b'ABCDEFG', 2))
        b'AB:CD:EF:G'

        >>> list(chop(b'ABCDEFG', 4, 3))
        [b'A', b'BCDE', b'FG']
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


def hexlify(
    bytestr: Union[bytes, bytearray],
    sep: Optional[Union[bytes, bytearray]] = None,
    upper: bool = True,
) -> bytes:
    r"""Converts raw bytes into a hexadecimal byte string.

    Args:
        bytestr (bytes):
            Source byte string.

        sep (bytes):
            Optional byte separator.

        upper (bool):
            Uppercase hexadecimal string.

    Returns:
        bytes: Hexadecimal byte string.

    Examples:
        >>> from hexrec.utils import hexlify
        >>> hexlify(b'\xAA\xBB\xCC')
        b'AABBCC'
        >>> hexlify(b'\xAA\xBB\xCC', sep=b' ')
        b'AA BB CC'
        >>> hexlify(b'\xAA\xBB\xCC', sep=b'-')
        b'AA-BB-CC'
        >>> hexlify(b'\xAA\xBB\xCC', upper=False)
        b'aabbcc'
    """

    if sep:
        pass  # coverage
        if __BINASCII_HEXLIFY_HAS_SEP:  # pragma: no cover
            hexstr = binascii.hexlify(bytestr, sep)
        else:  # pragma: no cover
            hexstr = sep.join(b'%02x' % b for b in bytestr)
    else:
        hexstr = binascii.hexlify(bytestr)

    if upper:
        hexstr = hexstr.upper()

    return hexstr


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

        >>> parse_int(None) is None
        True

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


def unhexlify(
    hexstr: Union[bytes, bytearray],
    delete: Optional[Union[bytes, bytearray, EllipsisType]] = None,
) -> bytes:
    r"""Converts a hexadecimal byte string into raw bytes.

    If `delete`, its byte values are deleted from `hexstr` before evaluation.
    Useful to remove whitespace and separators.

    Args:
        hexstr (bytes):
            Source hexadecimal byte string.

        delete (bytes):
            If empty or ``None``, no deletion occurs.
            If ``Ellipsis``, :data:``DEFAULT_DELETE`` is used.

    Returns:
        bytes: Raw byte string.

    Examples:
        >>> from hexrec.utils import unhexlify
        >>> unhexlify(b'AABBCC')
        b'\xaa\xbb\xcc'
        >>> unhexlify(b'AA BB CC', delete=...)
        b'\xaa\xbb\xcc'
        >>> unhexlify(b'AA-BB-CC', delete=...)
        b'\xaa\xbb\xcc'
        >>> unhexlify(b'AA/BB/CC', delete=b'/')
        b'\xaa\xbb\xcc'
    """

    if delete:
        if delete is Ellipsis:
            delete = DEFAULT_DELETE
        hexstr = hexstr.translate(None, delete)

    bytestr = binascii.unhexlify(hexstr)
    return bytestr
