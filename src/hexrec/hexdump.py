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

r"""Emulation of the hexdump utility."""

import io
import os
import sys
from typing import IO
from typing import Callable
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Union

from bytesparse.base import ImmutableMemory

from .base import AnyBytes
from .utils import SparseMemoryIO

CHAR_PRINTABLE: Sequence[bytes] = [b.to_bytes(1, 'big') for b in (
    b'................'
    b'................'
    b' !"#$%&\'()*+,-./'
    b'0123456789:;<=>?'
    b'@ABCDEFGHIJKLMNO'
    b'PQRSTUVWXYZ[\\]^_'
    b'`abcdefghijklmno'
    b'pqrstuvwxyz{|}~.'
    b'................'
    b'................'
    b'................'
    b'................'
    b'................'
    b'................'
    b'................'
    b'................'
    b' ><'
)]
r"""Printable characters lookup table."""

CHAR_TOKENS: Sequence[bytes] = [
    b'  \\0', b' 001', b' 002', b' 003', b' 004', b' 005', b' 006', b'  \\a',
    b'  \\b', b'  \\t', b'  \\n', b'  \\v', b'  \\f', b'  \\r', b' 016', b' 017',
    b' 020', b' 021', b' 022', b' 023', b' 024', b' 025', b' 026', b' 027',
    b' 030', b' 031', b' 032', b' 033', b' 034', b' 035', b' 036', b' 037',
    b'    ', b'   !', b'   "', b'   #', b'   $', b'   %', b'   &', b"   '",
    b'   (', b'   )', b'   *', b'   +', b'   ,', b'   -', b'   .', b'   /',
    b'   0', b'   1', b'   2', b'   3', b'   4', b'   5', b'   6', b'   7',
    b'   8', b'   9', b'   :', b'   ;', b'   <', b'   =', b'   >', b'   ?',
    b'   @', b'   A', b'   B', b'   C', b'   D', b'   E', b'   F', b'   G',
    b'   H', b'   I', b'   J', b'   K', b'   L', b'   M', b'   N', b'   O',
    b'   P', b'   Q', b'   R', b'   S', b'   T', b'   U', b'   V', b'   W',
    b'   X', b'   Y', b'   Z', b'   [', b'   \\', b'   ]', b'   ^', b'   _',
    b'   `', b'   a', b'   b', b'   c', b'   d', b'   e', b'   f', b'   g',
    b'   h', b'   i', b'   j', b'   k', b'   l', b'   m', b'   n', b'   o',
    b'   p', b'   q', b'   r', b'   s', b'   t', b'   u', b'   v', b'   w',
    b'   x', b'   y', b'   z', b'   {', b'   |', b'   }', b'   ~', b' 177',
    b' 200', b' 201', b' 202', b' 203', b' 204', b' 205', b' 206', b' 207',
    b' 210', b' 211', b' 212', b' 213', b' 214', b' 215', b' 216', b' 217',
    b' 220', b' 221', b' 222', b' 223', b' 224', b' 225', b' 226', b' 227',
    b' 230', b' 231', b' 232', b' 233', b' 234', b' 235', b' 236', b' 237',
    b' 240', b' 241', b' 242', b' 243', b' 244', b' 245', b' 246', b' 247',
    b' 250', b' 251', b' 252', b' 253', b' 254', b' 255', b' 256', b' 257',
    b' 260', b' 261', b' 262', b' 263', b' 264', b' 265', b' 266', b' 267',
    b' 270', b' 271', b' 272', b' 273', b' 274', b' 275', b' 276', b' 277',
    b' 300', b' 301', b' 302', b' 303', b' 304', b' 305', b' 306', b' 307',
    b' 310', b' 311', b' 312', b' 313', b' 314', b' 315', b' 316', b' 317',
    b' 320', b' 321', b' 322', b' 323', b' 324', b' 325', b' 326', b' 327',
    b' 330', b' 331', b' 332', b' 333', b' 334', b' 335', b' 336', b' 337',
    b' 340', b' 341', b' 342', b' 343', b' 344', b' 345', b' 346', b' 347',
    b' 350', b' 351', b' 352', b' 353', b' 354', b' 355', b' 356', b' 357',
    b' 360', b' 361', b' 362', b' 363', b' 364', b' 365', b' 366', b' 367',
    b' 370', b' 371', b' 372', b' 373', b' 374', b' 375', b' 376', b' 377',
    b' ---', b' >>>', b' <<<'
]
r"""Character tokens lookup table."""

_HEX_LOWER = [b'%02x' % b for b in range(256)] + [b'--', b'>>', b'<<']
_HEX_UPPER = [b'%02X' % b for b in range(256)] + [b'--', b'>>', b'<<']

_HEX_LOWER_TOKENS = [b' %02x' % b for b in range(256)] + [b' --', b' >>', b' <<']
_HEX_UPPER_TOKENS = [b' %02X' % b for b in range(256)] + [b' --', b' >>', b' <<']

_OCTAL_TOKENS = [b' %03o' % b for b in range(256)] + [b' ---', b' >>>', b' <<<']

DEFAULT_FORMAT_ORDER: Sequence[str] = [
    'one_byte_octal',
    'one_byte_hex',
    'one_byte_char',
    'canonical',
    'two_bytes_decimal',
    'two_bytes_octal',
    'two_bytes_hex',
]
r"""Default order of display options."""


def _format_default(
    address: int,
    chunk: AnyBytes,
    width: int,
    upper: bool,
) -> List[bytes]:

    address_fmt = b'%07X' if upper else b'%07x'
    tokens = [address_fmt % address]

    table = _HEX_UPPER if upper else _HEX_LOWER
    size = len(chunk)
    tokens.extend((b' ' + table[chunk[offset+1]] + table[chunk[offset]])
                  for offset in range(0, size-1, 2))

    if size & 1:
        tokens.append(b' 00' + table[chunk[size-1]])

    if size < width:
        tokens.extend(b'     ' for _ in range(1, width - size, 2))

    return tokens


def _format_one_byte_octal(
    address: int,
    chunk: AnyBytes,
    width: int,
    upper: bool,
) -> List[bytes]:

    address_fmt = b'%07X' if upper else b'%07x'
    tokens = [address_fmt % address]

    table = _OCTAL_TOKENS
    tokens.extend(table[b] for b in chunk)

    size = len(chunk)
    if size < width:
        tokens.extend(b'    ' for _ in range(width - size))

    return tokens


def _format_one_byte_hex(
    address: int,
    chunk: AnyBytes,
    width: int,
    upper: bool,
) -> List[bytes]:

    address_fmt = b'%08X' if upper else b'%08x'
    tokens = [address_fmt % address]

    table = _HEX_UPPER_TOKENS if upper else _HEX_LOWER_TOKENS
    tokens.extend(table[b] for b in chunk)

    size = len(chunk)
    if size < width:
        tokens.extend(b'   ' for _ in range(width - size))

    return tokens


def _format_one_byte_char(
    address: int,
    chunk: AnyBytes,
    width: int,
    upper: bool,
) -> List[bytes]:

    address_fmt = b'%07X' if upper else b'%07x'
    tokens = [address_fmt % address]

    table = CHAR_TOKENS
    tokens.extend(table[b] for b in chunk)

    size = len(chunk)
    if size < width:
        tokens.extend(b'    ' for _ in range(width - size))

    return tokens


def _format_canonical(
    address: int,
    chunk: AnyBytes,
    width: int,
    upper: bool,
) -> List[bytes]:

    address_fmt = b'%08X' if upper else b'%08x'
    tokens = [address_fmt % address]

    table = _HEX_UPPER_TOKENS if upper else _HEX_LOWER_TOKENS
    size = len(chunk)
    offset = 0
    append = tokens.append

    for offset in range(size):
        if (offset & 7) == 0:
            append(b' ')
        append(table[chunk[offset]])

    for offset in range(offset + 1, width):
        if (offset & 7) == 0:
            append(b' ')
        append(b'   ')

    table = CHAR_PRINTABLE
    append(b'  |')
    tokens.extend(table[b] for b in chunk)
    append(b'|')

    return tokens


def _format_two_bytes_decimal(
    address: int,
    chunk: AnyBytes,
    width: int,
    upper: bool,
) -> List[bytes]:

    address_fmt = b'%07X' if upper else b'%07x'
    tokens = [address_fmt % address]

    size = len(chunk)
    tokens.extend(b'   %05d' % (chunk[offset] | (chunk[offset+1] << 8))
                  for offset in range(0, size-1, 2))

    if size & 1:
        tokens.append(b'   %05d' % chunk[size-1])

    if size < width:
        tokens.extend(b'        ' for _ in range(1, width - size, 2))

    return tokens


def _format_two_bytes_octal(
    address: int,
    chunk: AnyBytes,
    width: int,
    upper: bool,
) -> List[bytes]:

    address_fmt = b'%07X' if upper else b'%07x'
    tokens = [address_fmt % address]

    del upper
    size = len(chunk)
    tokens.extend(b'  %06o' % (chunk[offset] | (chunk[offset+1] << 8))
                  for offset in range(0, size-1, 2))

    if size & 1:
        tokens.append(b'  %06o' % chunk[size-1])

    if size < width:
        tokens.extend(b'        ' for _ in range(1, width - size, 2))

    return tokens


def _format_two_bytes_hex(
    address: int,
    chunk: AnyBytes,
    width: int,
    upper: bool,
) -> List[bytes]:

    address_fmt = b'%07X' if upper else b'%07x'
    tokens = [address_fmt % address]

    table = _HEX_UPPER if upper else _HEX_LOWER
    size = len(chunk)
    tokens.extend((b'    ' + table[chunk[offset+1]] + table[chunk[offset]])
                  for offset in range(0, size-1, 2))

    if size & 1:
        tokens.append(b'    00' + table[chunk[size-1]])

    if size < width:
        tokens.extend(b'        ' for _ in range(1, width - size, 2))

    return tokens


_FormatHandler = Callable[[int, AnyBytes, int, bool], List[bytes]]

_FORMAT_HANDLERS: Mapping[str, _FormatHandler] = {
    'default': _format_default,
    'one_byte_octal': _format_one_byte_octal,
    'one_byte_hex': _format_one_byte_hex,
    'one_byte_char': _format_one_byte_char,
    'canonical': _format_canonical,
    'two_bytes_decimal': _format_two_bytes_decimal,
    'two_bytes_octal': _format_two_bytes_octal,
    'two_bytes_hex': _format_two_bytes_hex,
}

_ADDRESS_FMT: Mapping[str, bytes] = {
    'default': b'%07x',
    'one_byte_octal': b'%07x',
    'one_byte_hex': b'%08x',
    'one_byte_char': b'%07x',
    'canonical': b'%08x',
    'two_bytes_decimal': b'%07x',
    'two_bytes_octal': b'%07x',
    'two_bytes_hex': b'%07x',
}


# noinspection PyShadowingBuiltins
def hexdump_core(
    infile: Optional[Union[str, AnyBytes, IO]] = None,
    outfile: Optional[Union[str, AnyBytes, IO]] = None,
    one_byte_octal: bool = False,
    one_byte_hex: bool = False,
    one_byte_char: bool = False,
    canonical: bool = False,
    two_bytes_decimal: bool = False,
    two_bytes_octal: bool = False,
    two_bytes_hex: bool = False,
    color: Optional[str] = None,
    format: Optional[str] = None,
    format_file: Optional[str] = None,
    length: Optional[int] = None,
    skip: Optional[int] = None,
    no_squeezing: bool = False,
    upper: bool = False,
    width: int = 16,
    linesep: Optional[AnyBytes] = None,
    format_order: Optional[Sequence[str]] = None,
) -> IO:
    r"""Emulation of the `hexdump` utility core.

    Args:
        infile (str or bytes):
            Input data.
            If :obj:`str`, it is considered as the input file path.
            If :obj:`bytes`, it is the input byte chunk.
            If ``None``, it reads from the standard input.

        outfile (str or bytes):
            Output data.
            If :obj:`str`, it is considered as the output file path.
            If :obj:`bytes`, it is the output byte chunk.
            If ``None``, it writes to the standard output.

        one_byte_octal (bool):
            One-byte octal display. Display the input offset in
            hexadecimal, followed by sixteen space-separated,
            three-column, zero-filled bytes of input data, in octal, per
            line.

        one_byte_hex (bool):
            One-byte hexadecimal display. Display the input offset in
            hexadecimal, followed by sixteen space-separated, two-column,
            zero-filled bytes of input data, in hexadecimal, per line.

        one_byte_char (bool):
            One-byte character display. Display the input offset in
            hexadecimal, followed by sixteen space-separated,
            three-column, space-filled characters of input data per line.

        canonical (bool):
            Canonical hex+ASCII display. Display the input offset in
            hexadecimal, followed by sixteen space-separated, two-column,
            hexadecimal bytes, followed by the same sixteen bytes in %_p
            format enclosed in | characters. Invoking the program as hd
            implies this option.

        two_bytes_decimal (bool):
            Two-byte decimal display. Display the input offset in
            hexadecimal, followed by eight space-separated, five-column,
            zero-filled, two-byte units of input data, in unsigned
            decimal, per line.

        two_bytes_octal (bool):
            Two-byte octal display. Display the input offset in
            hexadecimal, followed by eight space-separated, six-column,
            zero-filled, two-byte quantities of input data, in octal, per
            line.

        two_bytes_hex (bool):
            Two-byte hexadecimal display. Display the input offset in
            hexadecimal, followed by eight space-separated, four-column,
            zero-filled, two-byte quantities of input data, in
            hexadecimal, per line.

        color (str):
            *CURRENTLY NOT SUPPORTED*. Please provide ``None``.

        format (str):
            *CURRENTLY NOT SUPPORTED*. Please provide ``None``.

        format_file (str):
            *CURRENTLY NOT SUPPORTED*. Please provide ``None``.

        length (int):
            Interpret only length bytes of input.

        skip (int):
            Skip offset bytes from the beginning of the input.

        no_squeezing (bool):
            The -v option causes hexdump to display all input data.
            Without the -v option, any number of groups of output lines
            which would be identical to the immediately preceding group
            of output lines (except for the input offsets), are replaced
            with a line comprised of a single asterisk.

        upper (bool):
            Uses upper case hex letters on address and data.

        width (int):
            Number of bytes per line.

        linesep (bytes):
            Line separator bytes.

        format_order (list of str):
            If not ``None``, it indicates the order of display options
            (``one_byte_octal``, ``one_byte_hex``, ``one_byte_char``,
            ``canonical``, ``two_bytes_decimal``, ``two_bytes_octal``,
            ``two_bytes_hex``).
            Duplicates are allowed.
            Only those with the corresponding boolean argument true are used.

    Returns:
        stream: The handle to the output stream.
    """

    if color is not None:
        raise NotImplementedError('"color" option is not supported')
    if format is not None:
        raise NotImplementedError('"format" option is not supported')
    if format_file is not None:
        raise NotImplementedError('"format_file" option is not supported')

    skip = 0 if skip is None else skip.__index__()
    if skip < 0:
        raise ValueError('negative skip')

    if length is not None:
        length = length.__index__()
        if length < 0:
            raise ValueError('negative length')

    width = width.__index__()
    width_min = 2 if two_bytes_decimal or two_bytes_octal or two_bytes_hex else 1
    if width < width_min:
        raise ValueError('invalid width')

    if linesep is None:
        linesep = os.linesep.encode()

    format_flags = {
        'one_byte_octal': one_byte_octal,
        'one_byte_hex': one_byte_hex,
        'one_byte_char': one_byte_char,
        'canonical': canonical,
        'two_bytes_decimal': two_bytes_decimal,
        'two_bytes_octal': two_bytes_octal,
        'two_bytes_hex': two_bytes_hex,
    }
    if format_order is None:
        format_order = DEFAULT_FORMAT_ORDER
    else:
        for format_name in format_order:
            if format_name not in format_flags:
                raise ValueError(f'unknown format option: {format_name!r}')

    format_handlers = [_FORMAT_HANDLERS[format_name]
                       for format_name in format_order
                       if format_flags[format_name]]
    if not format_handlers:
        format_order = ['default']
        format_handlers = [_format_default]

    do_squeezing = not no_squeezing
    instream: Optional[IO, SparseMemoryIO] = None
    outstream: Optional[IO] = None
    try:
        # Input stream binding
        if infile is None:
            infile = None
            instream = sys.stdin.buffer
        elif isinstance(infile, str):
            instream = open(infile, 'rb')
        elif isinstance(infile, (bytes, bytearray, memoryview)):
            instream = io.BytesIO(infile)
        elif isinstance(infile, ImmutableMemory):
            instream = SparseMemoryIO(memory=infile)
        else:
            instream = infile

        # Output stream binding
        if outfile is None:
            outfile = None
            outstream = sys.stdout.buffer
        elif isinstance(outfile, str):
            outstream = open(outfile, 'wb')
        else:
            outstream = outfile

        if skip:
            instream.seek(skip, io.SEEK_CUR)

        offset = 0
        last_chunk = None
        squeezing = False
        read = instream.read
        write = outstream.write

        while True:
            if length is None:
                chunk = read(width)
            else:
                chunk = read(min(width, length - offset))

            if not chunk:
                break

            if do_squeezing and chunk == last_chunk:
                if not squeezing:
                    write(b'*')
                    write(linesep)
                    squeezing = True
            else:
                squeezing = False
                address = skip + offset

                for format_handler in format_handlers:
                    tokens = format_handler(address, chunk, width, upper)
                    tokens.append(linesep)
                    line = b''.join(tokens)
                    write(line)

            last_chunk = chunk
            offset += len(chunk)

        address_fmt = _ADDRESS_FMT[format_order[-1]]
        if upper:
            address_fmt = address_fmt.upper()
        write(address_fmt % (skip + offset))
        write(linesep)

    finally:
        if instream is not None and isinstance(infile, str):
            instream.close()

        if outstream is not None and isinstance(outfile, str):
            outstream.close()

    return outstream
