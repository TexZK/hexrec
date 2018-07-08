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

BIN8_TO_STR = tuple('{:08b}'.format(i) for i in range(256))
STR_TO_BIN8 = {s: i for i, s in enumerate(BIN8_TO_STR)}

INT_REGEX = re.compile(r'^(?P<sign>[+-]?)'
                       r'(?P<prefix>(0x|0b|0)?)'
                       r'(?P<value>[a-f0-9]+)'
                       r'(?P<suffix>h?)'
                       r'(?P<scale>[km]?)$')


def parse_int(value):
    """Parses an integer.

    Arguments:
        value: A generic object to convert to integer.
            In case ``value`` is a ``str`` (case-insensitive), it can be either
            prefixed with ``0x`` or postfixed with ``h`` to convert from an
            hexadecimal representation, or prefixed with ``0b`` from binary;
            a prefix of only ``0`` converts from octal.
            A further suffix of ``k`` or ``m`` scales as kibibyte or mebibyte.
            A ``None`` value evaluates as ``None``.
            Any other object class will call the standard :func:`int`.

    Returns:
        int: None if ``value`` is ``None``, its integer conversion otherwise.

    Examples:
        >>> parse_int('-0xABk')
        -175104

        >>> parse_int(None)
        None

        >>> parse_int(123)
        123
    """
    if value is None:
        return None

    elif isinstance(value, str):
        value = value.lower()
        m = INT_REGEX.match(value)
        if not m:
            raise ValueError('invalid syntax')
        g = m.groupdict()
        sign = g['sign']
        prefix = g['prefix']
        value = g['value']
        suffix = g['suffix']
        scale = g['scale']
        if prefix == '0b' and suffix == 'h':
            raise ValueError('invalid syntax')

        if prefix == '0x' or suffix == 'h':
            i = int(value, 16)
        elif prefix == '0b':
            i = int(value, 2)
        elif prefix == '0':
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
    """Chops a vector.

    Iterates through the vector grouping its items into windows.

    Arguments:
        vector (list): Vector to chop.
        window (int): Window length.
        align_base (int): Offset of the first window.

    Yields:
        list: ``vector`` slices of up to ``window`` elements.
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
    """Splits and wraps a line into columns.

    A text line is wrapped up to a width limit, separated by a given newline
    string. Each wrapped line is then split into columns by some window size,
    separated by a given separator string.

    Arguments:
        line (str): Line of text to columnize.
        width (int): Maximum line width.
        sep (str): Column separator string.
        newline (str): Line separator string.
        window (int): Splitted column length.

    Returns:
        str: A wrapped and columnized text.

    Examples:
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
    """Splits and wraps a line into columns.

    A vector is wrapped up to a width limit; wrapped slices are collected
    into a :obj:`list`. Each slice is then split into columns by some window
    size, collected into a nested :obj:`list`.

    Arguments:
        vector (list): Vector to columnize.
        width (int): Maximum line width.
        window (int): Splitted column length.

    Returns:
        list: The vector wrapped and columnized into *list-of-lists*.

    Examples:
        >>> columnize_lists('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 6, window=3)
        [['ABC', 'DEF'], ['GHI', 'JKL'], ['MNO', 'PQR'], ['STU', 'VWX'], ['YZ']]
    """
    nested = list(list(chop(token, window))
                  for token in chop(vector, width))
    return nested


def bitlify(data, width=None, sep='', newline='\n', window=8):
    """Splits ans wraps byte data into columns.

    A chunk of byte data is converted into a text line, and then
    columnized as per :func:`columnize`.

    Arguments:
        data (bytes): Byte data. Sequence generator supported if ``width`` is
            not ``None``.
        width (int): Maximum line width, or ``None``.
        sep (str): Column separator string.
        newline (str): Line separator string.
        window (int): Splitted column length.

    Returns:
        str: A wrapped and columnized binary representation of the data.

    Examples:
        >>> bitlify(b'ABCDEFG', 8*3, sep=' ')
        '01000001 01000010 01000011\n01000100 01000101 01000110\n01000111'
    """
    if width is None:
        width = 8 * len(data)

    bitstr = ''.join(BIN8_TO_STR[b] for b in data)

    return columnize(bitstr, width, sep, newline, window)


def unbitlify(binstr):
    """Converts a binary text line into bytes.

    Arguments:
        binstr (str): A binary text line. Whitespace is removed, and the
            resulting total length must be a multiple of 8.

    Returns:
        bytes: Text converted into byte data.

    Examples:
        >>> unbitlify('010010000110100100100001')
        b'Hi!'
    """
    binstr = ''.join(binstr.split())
    data = bytes(STR_TO_BIN8[b] for b in chop(binstr, 8))
    return data


def hexlify(data, width=None, sep='', newline='\n', window=2, upper=True):
    """Splits ans wraps byte data into hexadecimal columns.

    A chunk of byte data is converted into a hexadecimal text line, and then
    columnized as per :func:`columnize`.

    Arguments:
        data (bytes): Byte data.
        width (int): Maximum line width, or ``None``.
        sep (str): Column separator string.
        newline (str): Line separator string.
        window (int): Splitted column length.
        upper (bool): Uppercase hexadecimal digits.

    Returns:
        str: A wrapped and columnized hexadecimal representation of the data.

    Examples:
        >>> hexlify(b'Hello, World!', sep='.')
        '48.65.6C.6C.6F.2C.20.57.6F.72.6C.64.21'
    """
    if width is None:
        width = 2 * len(data)

    if upper:
        hexstr = binascii.hexlify(data).upper().decode()
    else:
        hexstr = binascii.hexlify(data).decode()

    return columnize(hexstr, width, sep, newline, window)


def unhexlify(hexstr):
    """Converts a hexadecimal text line into bytes.

    Arguments:
        binstr (str): A hexadecimal text line. Whitespace is removed, and the
            resulting total length must be a multiple of 2.

    Returns:
        bytes: Text converted into byte data.

    Examples:
        >>> unhexlify('48656C6C6F2C20576F726C6421')
        b'Hello, World!'
    """
    data = binascii.unhexlify(''.join(hexstr.split()))
    return data


def hexlify_lists(data, width=None, window=2, upper=True):
    """Splits and columnize an hexadecimal representation.

    Converts some byte data into text as per :func:`hexlify`, then
    splits ans columnize as per :func:`columnize_lists`.

    Arguments:
        data (bytes): Byte data.
        width (int): Maximum line width, or ``None``.
        window (int): Splitted column length.
        upper (bool): Uppercase hexadecimal digits.

    Returns:
        list: The hexadecimal representation wrapped and columnized into
            *list-of-lists*.
    """
    if width is None:
        width = 2 * len(data)

    if upper:
        hexstr = binascii.hexlify(data).upper().decode()
    else:
        hexstr = binascii.hexlify(data).decode()

    return columnize_lists(hexstr, width, window)


def humanize_ascii(data, replace='.'):
    """ASCII for human readers.

    Simplifies the ASCII representation replacing all non-human-readable
    characters with a generic placeholder.

    Arguments:
        data (bytes): Byte data. Sequence generator supported.
        replace (str): String replacement of non-human-readable characters.

    Returns:
        str: ASCII representation with only human-readable characters.

    Examples:
        >>> humanize_ascii(b'\x89PNG\r\n\x1a\n')
        '.PNG....'
    """
    text = ''.join(chr(b) if 0x20 <= b < 0x7F else replace for b in data)
    return text


def humanize_ebcdic(data, replace='.'):
    """EBCDIC for human readers.

    Simplifies the EBCDIC representation replacing all non-human-readable
    characters with a generic placeholder.

    Arguments:
        data (bytes): Byte data.
        replace (str): String replacement of non-human-readable characters.

    Returns:
        str: EBCDIC representation with only human-readable characters.
    """
    return humanize_ascii((ord(c) for c in data.decode('cp500')), replace)


def bytes_to_c_array(name_label, data, width=16, upper=True,
                     type_label='unsigned char', size_label='',
                     indent='    ', comment=True, offset=0):
    """Converts bytes into a C array.

    Arguments:
        name_label (str): Array name.
        data (bytes): Array byte data.
        width (int): Number of bytes per line.
        upper (bool): Uppercase hexadecimal digits.
        type_label (str): Array type label.
        size_label (str): Array size label (if needed).
        indent (str): Line indentation text.
        comment (bool): Comment with the line offset (8-digit hex).
        offset (int): Offset of the first byte to represent.

    Returns:
        str: Some C code with the byte data represented as an array.
    """
    hexstr_lists = hexlify_lists(data, 2 * width, 1, upper)
    lines = []
    for tokens in hexstr_lists:
        line = indent + ', '.join('0x' + token for token in tokens) + ','
        if comment:
            line += '  /* 0x{:08X} */'.format(offset)
        lines.append(line)
        offset += 2 * len(tokens)

    open = '{} {}[{}] ='.format(type_label, name_label, size_label)
    lines = [open, '{'] + lines + ['};']
    text = '\n'.join(lines)
    return text


def do_overlap(start1, endex1, start2, endex2):
    """Do ranges overlap?

    Arguments:
        start1 (int): Inclusive start index of the first range.
        endex1 (int): Exclusive end index of the first range.
        start2 (int): Inclusive start index of the second range.
        endex2 (int): Exclusive end index of the second range.

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


def merge_blocks(sorted_blocks, invalid_start=-1):
    """Merges blocks of items.

    Given a sequence of blocks, they are merged so that those with a higher
    priority level overwrite the overlapping ones with a lower priority level.

    A block is ``(start, level, items)`` where ``start`` is the start address,
    ``level`` is the priority level, and ``items`` is the container of items
    (e.g. a :obj:`bytes` object). The length of the block is ``len(items)``.

    Arguments:
        sorted_blocks (list): A sequence of blocks, sorted by start address
            and priority level. Sequence generators supported.

        invlid_start (int): An invalid start index, in case the default ``-1``
            is a valid start address.

    Returns:
        list: A sequence of merged blocks.
    """
    last_block = (invalid_start, None, ())
    merged_blocks = []

    for start, level, items in sorted_blocks:
        if items:
            endex = start + len(items)
            merged_block = None
            split_block = None

            last_start, last_level, last_items = last_block
            last_endex = last_start + len(last_items)

            if endex <= last_endex or start < last_endex:
                if last_level <= level:
                    merged_blocks.pop()
                    if start > last_start:
                        split_items = last_items[:(start - last_start)]
                        last_block = (last_start, last_level, split_items)
                        merged_blocks.append(last_block)

                    if endex <= last_endex:
                        split_items = last_items[(endex - last_start):]
                        if split_items:
                            split_block = (endex, last_level, split_items)

                    merged_block = (start, level, items)
            else:
                merged_block = (start, level, items)

            if merged_block:
                merged_blocks.append(merged_block)
                last_block = merged_block

            if split_block:
                merged_blocks.append(split_block)
                last_block = split_block

    return merged_blocks
