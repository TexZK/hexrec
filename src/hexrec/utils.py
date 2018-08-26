# -*- coding: utf-8 -*-

# Copyright (c) 2013-2018, Andrea Zoppi
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

import binascii
import re

import six

BIN8_TO_STR = tuple(bin(i)[2:].zfill(8) for i in range(256))
STR_TO_BIN8 = {s: i for i, s in enumerate(BIN8_TO_STR)}

INT_REGEX = re.compile(r'^\s*(?P<sign>[+-]?)\s*'
                       r'(?P<prefix>(0x|0b|0o|0)?)'
                       r'(?P<value>[a-f0-9]+)'
                       r'(?P<suffix>h?)'
                       r'(?P<scale>[km]?)\s*$')


def parse_int(value):
    r"""Parses an integer.

    Arguments:
        value: A generic object to convert to integer.
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
            raise ValueError('invalid syntax: {!r}'.format(value))
        g = m.groupdict()
        sign = g['sign']
        prefix = g['prefix']
        value = g['value']
        suffix = g['suffix']
        scale = g['scale']
        if prefix in ('0b', '0o') and suffix == 'h':
            raise ValueError('invalid syntax: {!r}'.format(value))

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


def chop(vector, window, align_base=0):
    r"""Chops a vector.

    Iterates through the vector grouping its items into windows.

    Arguments:
        vector (list): Vector to chop.
        window (:obj:`int`): Window length.
        align_base (:obj:`int`): Offset of the first window.

    Yields:
        list: `vector` slices of up to `window` elements.

    Examples:
        >>> list(chop('ABCDEFG', 2))
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


def columnize(line, width, sep='', newline='\n', window=1):
    r"""Splits and wraps a line into columns.

    A text line is wrapped up to a width limit, separated by a given newline
    string. Each wrapped line is then split into columns by some window size,
    separated by a given separator string.

    Arguments:
        line (:obj:`str`): Line of text to columnize.
        width (:obj:`int`): Maximum line width.
        sep (:obj:`str`): Column separator string.
        newline (:obj:`str`): Line separator string.
        window (:obj:`int`): Splitted column length.

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


def columnize_lists(vector, width, window=1):
    r"""Splits and wraps a line into columns.

    A vector is wrapped up to a width limit; wrapped slices are collected
    into a :obj:`list`. Each slice is then split into columns by some window
    size, collected into a nested :obj:`list`.

    Arguments:
        vector (list): Vector to columnize.
        width (:obj:`int`): Maximum line width.
        window (:obj:`int`): Splitted column length.

    Returns:
        list: The vector wrapped and columnized into list-of-lists.

    Example:
        >>> columnize_lists('ABCDEFG', 5, window=2)
        [['AB', 'CD', 'E'], ['FG']]
    """
    nested = list(list(chop(token, window))
                  for token in chop(vector, width))
    return nested


def bitlify(data, width=None, sep='', newline='\n', window=8):
    r"""Splits ans wraps byte data into columns.

    A chunk of byte data is converted into a text line, and then
    columnized as per :func:`columnize`.

    Arguments:
        data (:obj:`bytes`): Byte data. Sequence generator supported if
            `width` is not ``None``.
        width (:obj:`int`): Maximum line width, or ``None``.
        sep (:obj:`str`): Column separator string.
        newline (:obj:`str`): Line separator string.
        window (:obj:`int`): Splitted column length.

    Returns:
        str: A wrapped and columnized binary representation of the data.

    Example:
        >>> bitlify(b'ABCDEFG', 8*3, sep=' ')
        '01000001 01000010 01000011\n01000100 01000101 01000110\n01000111'
    """
    if width is None:
        width = 8 * len(data)
    bitstr = ''.join(BIN8_TO_STR[b] for b in six.iterbytes(data))
    return columnize(bitstr, width, sep, newline, window)


def unbitlify(binstr):
    r"""Converts a binary text line into bytes.

    Arguments:
        binstr (:obj:`str`): A binary text line. Whitespace is removed, and
            the resulting total length must be a multiple of 8.

    Returns:
        bytes: Text converted into byte data.

    Example:
        >>> unbitlify('010010000110100100100001')
        b'Hi!'
    """
    binstr = ''.join(binstr.split())
    data = bytes(bytearray(STR_TO_BIN8[c] for c in chop(binstr, 8)))
    return data


def hexlify(data, width=None, sep='', newline='\n', window=2, upper=True):
    r"""Splits ans wraps byte data into hexadecimal columns.

    A chunk of byte data is converted into a hexadecimal text line, and then
    columnized as per :func:`columnize`.

    Arguments:
        data (:obj:`bytes`): Byte data.
        width (:obj:`int`): Maximum line width, or ``None``.
        sep (:obj:`str`): Column separator string.
        newline (:obj:`str`): Line separator string.
        window (:obj:`int`): Splitted column length.
        upper (:obj:`bool`): Uppercase hexadecimal digits.

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


def unhexlify(hexstr):
    r"""Converts a hexadecimal text line into bytes.

    Arguments:
        binstr (:obj:`str`): A hexadecimal text line. Whitespace is removed,
            and the resulting total length must be a multiple of 2.

    Returns:
        bytes: Text converted into byte data.

    Example:
        >>> unhexlify('48656C6C 6F2C2057 6F726C64 21')
        b'Hello, World!'
    """
    data = binascii.unhexlify(''.join(hexstr.split()))
    return data


def hexlify_lists(data, width=None, window=2, upper=True):
    r"""Splits and columnizes an hexadecimal representation.

    Converts some byte data into text as per :func:`hexlify`, then
    splits ans columnize as per :func:`columnize_lists`.

    Arguments:
        data (:obj:`bytes`): Byte data.
        width (:obj:`int`): Maximum line width, or ``None``.
        window (:obj:`int`): Splitted column length.
        upper (:obj:`bool`): Uppercase hexadecimal digits.

    Returns:
        list: The hexadecimal text wrapped and columnized into list-of-lists.

    Example:
        >>> hexlify_lists(b'Hello, World!')
        ... #doctest: +NORMALIZE_WHITESPACE
        [['48', '65', '6C', '6C', '6F', '2C', '20',
          '57', '6F', '72', '6C', '64', '21']]

        >>> hexlify_lists(b'Hello, World!', 6)
        ... #doctest: +NORMALIZE_WHITESPACE
        [['48', '65', '6C'],
         ['6C', '6F', '2C'],
         ['20', '57', '6F'],
         ['72', '6C', '64'],
         ['21']]
    """
    if width is None:
        width = 2 * len(data)

    if upper:
        hexstr = binascii.hexlify(data).upper().decode()
    else:
        hexstr = binascii.hexlify(data).decode()

    return columnize_lists(hexstr, width, window)


def humanize_ascii(data, replace='.'):
    r"""ASCII for human readers.

    Simplifies the ASCII representation replacing all non-human-readable
    characters with a generic placeholder.

    Arguments:
        data (:obj:`bytes`): Byte data. Sequence generator supported.
        replace (:obj:`str`): String replacement of non-human-readable
            characters.

    Returns:
        str: ASCII representation with only human-readable characters.

    Example:
        >>> humanize_ascii(b'\x89PNG\r\n\x1a\n')
        '.PNG....'
    """
    text = ''.join(chr(b) if 0x20 <= b < 0x7F else replace
                   for b in six.iterbytes(data))
    return text


def humanize_ebcdic(data, replace='.'):
    r"""EBCDIC for human readers.

    Simplifies the EBCDIC representation replacing all non-human-readable
    characters with a generic placeholder.

    Arguments:
        data (:obj:`bytes`): Byte data.
        replace (:obj:`str`): String replacement of non-human-readable
            characters.

    Returns:
        str: EBCDIC representation with only human-readable characters.

    Example:
        >>> humanize_ebcdic(bytearray(range(0xC0, 0xD0)))
        '{ABCDEFGHI......'
    """
    data = data.decode('cp500')
    text = ''.join(c if 0x20 <= ord(c) < 0x7F else replace for c in data)
    return text


def sum_bytes(data):
    r"""Sums bytes.

    Supports both Python 2.7 and Python 3.

    Arguments:
        data (:obj:`bytes`): Data bytes. Actually supports any sequence with
            integers in it.

    Returns:
        :obj:`int`: The sum of all items in `data`.

    Examples:
        >>> sum_bytes(bytes(bytearray(range(16))))
        120

        >>> sum_bytes(range(16))
        120
    """
    if isinstance(data, str):
        return sum(ord(c) for c in data)
    else:
        return sum(data)


def do_overlap(start1, endex1, start2, endex2):
    r"""Do ranges overlap?

    Arguments:
        start1 (:obj:`int`): Inclusive start index of the first range.
        endex1 (:obj:`int`): Exclusive end index of the first range.
        start2 (:obj:`int`): Inclusive start index of the second range.
        endex2 (:obj:`int`): Exclusive end index of the second range.

    Note:
        Start and end of each range are sorted before the final comparison.

    Returns:
        bool: Ranges do overlap.

    Examples:
        >>> do_overlap(0, 4, 4, 8)
        False

        >>> do_overlap(0, 4, 2, 6)
        True

        >>> do_overlap(4, 0, 2, 6)
        True

        >>> do_overlap(8, 4, 4, 0)
        False
    """
    if start1 > endex1:
        start1, endex1 = endex1, start1
    if start2 > endex2:
        start2, endex2 = endex2, start2
    return (endex1 > start2 and endex2 > start1)


def straighten_index(index, length):
    """Wraps negative vector index.

    Arguments:
        index (:obj:`int`): Vector index, or ``None``.
        length (:obj:`int`): Vector length.

    Returns:
        :obj:`int`: Wrapped vector index.

    Examples:
        >>> straighten_index(3, 7)
        3

        >>> straighten_index(-3, 7)
        4

        >>> straighten_index(9, 7)
        2

        >>> straighten_index(-8, 7)
        6

        >>> straighten_index(None, 3)
        None

        >>> straighten_index(3, None)
        0
    """
    if index is None:
        return None
    elif not length:
        index = 0
    elif index < 0:
        index %= length
    return index


def straighten_slice(start, stop, step, length):
    """Wraps negative slice indices.

    Arguments:
        start (:obj:`int`): :attr:`slice.start` index, or ``None``.
        stop (:obj:`int`): :attr:`slice.stop` index, or ``None``.
        step (:obj:`int`): :attr:`slice.step` value, or ``None``.
        length (:obj:`int`): Exclusive end of the virtual range to wrap.

    Returns:
        :obj:`slice`: Wrapped slice.

    Examples:
        >>> straighten_slice(3, 5, 1, 7)
        (3, 5, 1)

        >>> straighten_slice(-3, 5, 1, 7)
        (4, 5, 1)

        >>> straighten_slice(3, -5, 1, 7)
        (3, 2, 1)

        >>> straighten_slice(-3, -5, 1, 7)
        (4, 2, 1)

        >>> straighten_slice(None, 5, 1, 7)
        (0, 5, 1)

        >>> straighten_slice(3, None, 1, 7)
        (3, 7, 1)

        >>> straighten_slice(3, 5, None, 7)
        (3, 5, None)

        >>> straighten_slice(3, 5, 1, None)
        (0, 0, 1)
    """
    if length:
        if start is None:
            start = 0
        elif start < 0:
            start %= length

        if stop is None:
            stop = length
        elif stop < 0:
            stop %= length
    else:
        start = 0
        stop = 0

    return start, stop, step


def wrap_index(index, length):
    """Wraps vector index into a window.

    Arguments:
        index (:obj:`int`): Vector index, or ``None``.
        length (:obj:`int`): Vector length.

    Returns:
        :obj:`int`: Wrapped vector index.

    Examples:
        >>> straighten_index(3, 7)
        3

        >>> straighten_index(-3, 7)
        4

        >>> straighten_index(9, 7)
        2

        >>> straighten_index(-8, 7)
        6

        >>> straighten_index(None, 3)
        0

        >>> straighten_index(3, None)
        0
    """
    if not index or not length:
        index = 0
    elif not 0 <= index < length:
        index %= length
    return index


def wrap_slice(start, stop, step, length):
    """Wraps slice indices into a window.

    Arguments:
        start (:obj:`int`): :attr:`slice.start` index, or ``None``.
        stop (:obj:`int`): :attr:`slice.stop` index, or ``None``.
        step (:obj:`int`): :attr:`slice.step` value, or ``None``.
        length (:obj:`int`): Exclusive end of the virtual range to wrap.

    Returns:
        :obj:`slice`: Wrapped slice.

    Examples:
        >>> wrap_slice(3, 5, 1, 7)
        (3, 5, 1)

        >>> wrap_slice(-3, 5, 1, 7)
        (4, 5, 1)

        >>> wrap_slice(3, -5, 1, 7)
        (3, 2, 1)

        >>> wrap_slice(-3, -5, 1, 7)
        (4, 2, 1)

        >>> wrap_slice(None, 5, 1, 7)
        (0, 5, 1)

        >>> wrap_slice(3, None, 1, 7)
        (3, 7, 1)

        >>> wrap_slice(3, 5, None, 7)
        (3, 5, 1)

        >>> wrap_slice(3, 5, 1, None)
        (0, 0, 1)
    """
    if step is None:
        step = 1

    if length:
        if start is None:
            start = 0
        elif not 0 <= start < length:
            start %= length

        if stop is None:
            stop = length
        elif not 0 <= stop < length:
            stop %= length
    else:
        start = 0
        stop = 0

    return start, stop, step


def makefill(pattern, start, endex, join=b''.join):
    r"""Builds a filling pattern.

    Arguments:
        pattern (items): A non-null pattern of items to repeat for filling.
        start (:obj:`int`): Inclusive start offset within the pattern.
        endex (:obj:`int`): Exclusive end offset within the pattern.
        join (callable): A function to join a sequence of items.

    Returns:
        items: Repeated pattern for filling.

    Examples:
        >>> makefill(b'0123456789ABCDEF', 0, 8)
        b'01234567'

        >>> makefill(b'0123456789ABCDEF', 8, 16)
        b'89ABCDEF'

        >>> makefill(b'0123456789ABCDEF', 4, 44)
        b'456789ABCDEF0123456789ABCDEF0123456789AB'
    """
    if not pattern:
        raise ValueError('invalid pattern')
    if start < 0:
        raise ValueError('negative start')
    if endex < 0:
        raise ValueError('negative endex')
    if endex <= start:
        raise ValueError('non-positive length')

    length = len(pattern)
    if length < 64:
        length = (64 - 1 + length) // length
        pattern = join(pattern for _ in range(length))
        length = len(pattern)

    offset = start % length
    pattern = pattern[offset:] + pattern[:offset]
    offset = endex - start
    chunks = [pattern] * (offset // length)
    offset %= length
    chunks.append(pattern[:offset])
    filling = join(chunks)
    return filling
