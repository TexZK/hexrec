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

INT_REGEX = re.compile('^(?P<sign>[+-]?)'
                       '(?P<prefix>(0x|0X|0b|0B|0)?)'
                       '(?P<value>[A-Fa-f0-9]+)'
                       '(?P<suffix>[hHbBkm]?)$')


def parse_int(value):
    if value is None:
        return None

    elif isinstance(value, str):
        m = INT_REGEX.match(value)
        if not m:
            raise ValueError('invalid syntax')
        sign, prefix, suffix, value = m.groups()

        if prefix in ('0x', '0X'):
            i = int(value, 16)
        elif prefix in ('0b', '0B'):
            i = int(value, 2)
        elif suffix in ('h', 'H'):
            i = int(value, 16)
        elif suffix in ('b', 'B'):
            i = int(value, 2)
        elif prefix == '0':
            i = int(value, 8)
        else:
            i = int(value, 10)

        if suffix in ('k', 'K'):
            i <<= 10
        elif suffix in ('m', 'M'):
            i <<= 20

        if sign == '-':
            i = -i

        return i

    else:
        return int(value)


def chop(vector, window, align_base=0):
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
    nested = list(list(chop(token, window))
                  for token in chop(vector, width))
    return nested


def bitlify(data, width=None, sep='', newline='\n', window=1):
    if width is None:
        width = len(data)

    bitstr = ''.join(BIN8_TO_STR[b] for b in data)

    return columnize(bitstr, width, sep, newline, window)


def unbitlify(binstr):
    data = bytes(STR_TO_BIN8[b] for b in binstr)
    return data


def hexlify(data, width=None, sep='', newline='\n', window=2, upper=True):
    if width is None:
        width = 2 * len(data)

    if upper:
        hexstr = binascii.hexlify(data).upper().decode()
    else:
        hexstr = binascii.hexlify(data).decode()

    return columnize(hexstr, width, sep, newline, window)


def unhexlify(hexstr):
    data = binascii.unhexlify(''.join(hexstr.split()))
    return data


def hexlify_lists(data, width=None, window=2, upper=True):
    if width is None:
        width = 2 * len(data)

    if upper:
        hexstr = binascii.hexlify(data).upper().decode()
    else:
        hexstr = binascii.hexlify(data).decode()

    return columnize_lists(hexstr, width, window)


def humanize_ascii(data, replace='.'):
    text = ''.join(chr(b) if 0x20 <= b < 0x7F else replace for b in data)
    return text


def humanize_ebcdic(data, replace='.'):
    return humanize_ascii((ord(c) for c in data.decode('cp500')), replace)


def bytes_to_c_array(name_label, data, width=16, window=2, upper=True,
                     type_label='unsigned char', size_label='',
                     indent='    ', comment=True, offset=0):

    hexstr_lists = hexlify_lists(data, 2 * width, window, upper)
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
    if start1 > endex1:
        start1, endex1 = endex1, start1
    if start2 > endex2:
        start2, endex2 = endex2, start2
    return (endex1 > start2 and endex2 > start1)


def merge_blocks(sorted_blocks, invalid_start=-1):
    last_block = (invalid_start, None, ())  # (start, level, items)
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
