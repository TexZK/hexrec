#!/usr/bin/env python
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

r"""Emulation of the xxd utility."""

import io
import os
import re
import sys

import six

from .utils import BIN8_TO_STR
from .utils import chop
from .utils import hexlify
from .utils import parse_int
from .utils import unhexlify

_SEEKING_REGEX = re.compile(r'^(?P<sign>\+?-?)-?(?P<absolute>\w+)$')

_REVERSE_REGEX = re.compile(r'^\s*(?P<address>[A-Fa-f0-9]+)\s*:\s*'
                            r'(?P<data>([A-Fa-f0-9]{2}\s*)+)'
                            r'(?P<garbage>.*)$')

HUMAN_ASCII = (r'................'
               r'................'
               r' !"#$%&' r"'()*+,-./"
               r'0123456789:;<=>?'
               r'@ABCDEFGHIJKLMNO'
               r'PQRSTUVWXYZ[\]^_'
               r'`abcdefghijklmno'
               r'pqrstuvwxyz{|}~.'
               r'................'
               r'................'
               r'................'
               r'................'
               r'................'
               r'................'
               r'................'
               r'................')
r"""Mapping from byte to human-readable ASCII characters."""

HUMAN_EBCDIC = (r'................'
                r'................'
                r'................'
                r'................'
                r' ...........<(+|'
                r'&.........!$*);~'
                r'-/.........,%_>?'
                r".........`:#@'=" r'"'
                r'.abcdefghi......'
                r'.jklmnopqr^.....'
                r'..stuvwxyz...[..'
                r'.............]..'
                r'{ABCDEFGHI......'
                r'}JKLMNOPQR......'
                r'\.STUVWXYZ......'
                r'0123456789......')
r"""Mapping from byte to human-readable EBCDIC characters."""


def humanize(chunk, charset):
    r"""Translates bytes to a human-readable representation.

    Arguments:
        chunk (:obj:`bytes`): A chunk of bytes.
        charset (:obj:`list`): A mapping from byte (index) to character.

    Returns:
        :obj:`str`: Human-readable byte string.
    """
    return ''.join(charset[b] for b in six.iterbytes(chunk))


def parse_seek(value):
    r"""Parses the seek option string.

    Argument:
        value (:obj:`str` or ``None``): The value to convert. It is converted
            to :obj:`str` before processing. ``None`` equals zero.

    Returns:
        tuple: ``(sign_string, unsigned_value)``.
    """
    if value is None:
        return '', 0
    else:
        m = _SEEKING_REGEX.match(str(value))
        if not m:
            raise ValueError('invalid seeking')
        ss, sv = m.groups()
        sv = parse_int(sv)
        return ss, sv


def xxd(infile=None, outfile=None, autoskip=None, bits=None, cols=None,
        ebcdic=None, endian=None, groupsize=None, include=None, length=None,
        offset=None, postscript=False, quadword=False, revert=False,
        oseek=None, iseek=None, upper_all=False, upper=False):
    r"""Emulation of the xxd utility core.

    Arguments:
        infile (:obj:`str` or :obj:`bytes` or ``None``): Input data.
            If :obj:`str`, it is considered as the input file path.
            If :obj:`bytes`, it is the input byte chunk.
            If ``None`` or ``'-'``, it reads from the standard input.

        outfile (:obj:`str` or :obj:`bytes` or ``None``): Output data.
            If :obj:`str`, it is considered as the output file path.
            If :obj:`bytes`, it is the output byte chunk.
            If ``None`` or ``'-'``, it writes to the standard output.

        autoskip (:obj:`bool`): Toggles autoskip. A single ``'*'`` replaces
            null lines.

        bits (:obj:`bool`): Switches to bits (binary digits) dump, rather than
            hexdump. This option writes octets as eight digits of '1' and '0'
            instead of a normal hexadecimal dump. Each line is preceded by a
            line number in hexadecimal and followed by an ASCII (or EBCDIC)
            representation. The argument switches ``revert``, ``postscript``,
            ``include`` do not work with this mode.

        cols (:obj:`int`): Formats ``cols`` octets per line. Max 256.
            Defaults: normal 16, ``include`` 12, ``postscript`` 30, ``bits`` 6.

        ebcdic (:obj:`bool`): Changes the character encoding in the right-hand
            column from ASCII to EBCDIC.
            This does not change the hexadecimal representation.
            The option is meaningless in combinations with ``revert``,
            ``postscript`` or ``include``.

        endian (:obj:`bool`): Switches to little-endian hexdump.
            This option treats  byte groups as words in little-endian byte
            order.
            The default grouping of 4 bytes may be changed using ``groupsize``.
            This option only applies to hexdump, leaving the ASCII (or EBCDIC)
            representation unchanged.
            The switches ``revert``, ``postscript``, ``include`` do not work
            with this mode.

        groupsize (:obj:`int`): Separates the output of every ``groupsize``
            bytes (two hex characters or eight bit-digits each) by a whitespace.
            Specify ``groupsize`` 0 to suppress grouping.
            ``groupsize`` defaults to 2 in normal mode, 4 in little-endian mode
            and 1 in bits mode. Grouping does not apply to ``postscript`` or
            ``include``.

        include (:obj:`bool`): Output in C include file style.
            A complete static array definition is written (named after the
            input file), unless reading from standard input.

        length (:obj:`int`): Stops after writing ``length`` octets.

        offset (:obj:`int`): Adds ``offset`` to the displayed file position.

        postscript (:obj:`bool`): Outputs in postscript continuous hexdump
            style. Also known as plain hexdump style.

        quadword (:obj:`bool`): Uses 64-bit addressing.

        revert (:obj:`bool`): Reverse operation: convert (or patch) hexdump
            into binary. If not writing to standard output, it writes into its
            output file without truncating it.
            Use the combination ``revert`` and ``postscript`` to read plain
            hexadecimal dumps without line number information and without a
            particular column layout. Additional Whitespace and line breaks are
            allowed anywhere.

        oseek (:obj:`int`): When used after ``revert`` reverts with ``offset``
            added to file positions found in hexdump.

        iseek (:obj:`int` or :obj:`str`): Starts at ``iseej`` bytes absolute
            (or relative) input offset.
            Without ``iseek`` option, it starts at the current file position.
            The prefix is used to compute the offset.
            ``+`` indicates that the seek is relative to the current input
            position.
            ``-`` indicates that the seek should be that many characters from
            the end of the input.
            ``+-`` indicates that the seek should be that many characters
            before the current stdin file position.

        upper_all (:obj:`bool`): Uses upper case hex letters on address and
            data.

        upper (:obj:`bool`): Uses upper case hex letters on data only.

    Returns:
        stream: The handle to the output stream.
    """
    if cols is not None and not 1 <= cols <= 256:
        raise ValueError('invalid column count')

    if upper_all:
        upper = upper_all

    if (bits or endian) and (postscript or include or revert):
        raise ValueError('incompatible options')

    if sum(bool(_) for _ in [postscript, include, bits]) > 1:
        raise ValueError('incompatible options')

    if not revert and oseek is not None:
        raise ValueError('incompatible options')
    elif oseek is not None and oseek < 0:
        raise ValueError('invalid seeking')

    instream = None
    outstream = None
    try:
        # Input stream binding
        if infile is None or infile == '-':
            infile = None
            instream = sys.stdin
        elif isinstance(infile, str):
            if revert:
                instream = open(infile, 'rt')
            else:
                instream = open(infile, 'rb')
        elif isinstance(infile, (bytes, bytearray, memoryview)):
            instream = io.BytesIO(infile)
        else:
            instream = infile

        # Output stream binding
        if outfile is None or outfile == '-':
            outfile = None
            outstream = sys.stdout
        elif isinstance(outfile, str):
            if revert:
                if oseek:
                    outstream = open(outfile, 'w+b')
                else:
                    outstream = open(outfile, 'wb')
            else:
                outstream = open(outfile, 'wt')
        elif outfile is Ellipsis:
            if revert:
                outstream = io.BytesIO()
            else:
                outstream = io.StringIO()
        else:
            outstream = outfile

        # Input seeking
        offset = parse_int(offset) if offset else 0

        if iseek is not None:
            ss, sv = parse_seek(str(iseek))

            if ss == '+':
                instream.seek(sv, io.SEEK_CUR)
            elif ss == '+-':
                instream.seek(-sv, io.SEEK_CUR)
            elif ss == '-':
                instream.seek(-sv, io.SEEK_END)
            else:  # ss == ''
                instream.seek(sv, io.SEEK_SET)

            offset += instream.tell()

        # Output seeking
        if revert:
            outstream.write(bytearray(oseek or 0))

        # Output mode handling
        if revert:
            if postscript:
                # Plain hexadecimal input
                for line in instream:
                    data = unhexlify(line)
                    outstream.write(data)

            else:
                if cols is None:
                    cols = 16

                for line in instream:
                    m = _REVERSE_REGEX.match(line)
                    if m:
                        # Interpret line contents
                        groups = m.groupdict()
                        address = (oseek or 0) + int(groups['address'], 16)
                        data = unhexlify(''.join(groups['data'].split()))
                        data = data[:cols]

                        # Write line data (fill gaps if needed)
                        outstream.seek(0, io.SEEK_END)
                        outoffset = outstream.tell()
                        if outoffset < address:
                            outstream.write(bytearray(address - outoffset))
                        outstream.seek(address, io.SEEK_SET)
                        outstream.write(data)

            raise StopIteration  # End of input stream

        elif postscript:
            # Plain hexadecimal output
            if cols is None:
                cols = 30

            count = 0
            while True:
                if length is None:
                    chunk = instream.read(cols)
                else:
                    chunk = instream.read(min(cols, length - count))

                if chunk:
                    outstream.write(hexlify(chunk, upper=upper))
                    outstream.write(u'\n')
                    count += len(chunk)
                else:
                    raise StopIteration  # End of input stream

        elif bits:
            if cols is None:
                cols = 6
            if groupsize is None:
                groupsize = 1

        elif include:
            if cols is None:
                cols = 12

            # Data variable definition
            if isinstance(infile, str):
                label = os.path.basename(infile)
                label = re.sub('[^0-9a-zA-Z]+', '_', label)
                fmt = u'unsigned char {}[] = {{\n'
                outstream.write(fmt.format(label))

            indent = u'  0X' if upper_all else u'  0x'
            sep = u', 0X' if upper_all else u', 0x'

            count = 0
            while True:
                if length is None:
                    chunk = instream.read(cols)
                else:
                    chunk = instream.read(min(cols, length - count))

                if chunk:
                    if count:
                        outstream.write(u',\n')
                    outstream.write(indent)
                    outstream.write(hexlify(chunk, upper=upper, sep=sep))
                    count += len(chunk)

                else:
                    # Data end and length variable definition
                    if isinstance(infile, str):
                        fmt = u'\n}};\nunsigned int {}_len = {};\n'
                        outstream.write(fmt.format(label, count))
                    else:
                        outstream.write(u'\n')

                    raise StopIteration  # End of input stream

        else:
            if cols is None:
                cols = 16

        if groupsize is None:
            groupsize = 4 if endian else 2
        if not 0 <= groupsize <= 256:
            raise ValueError('invalid grouping')

        data_width = (cols * (8 if bits else 2) +
                      ((cols - 1) // groupsize if groupsize else 0))
        line_fmt = '{{:0{}{}}}: {{:{}s}}  {{}}\n'
        line_fmt = line_fmt.format(16 if quadword else 8,
                                   'X' if upper_all else 'x',
                                   data_width)

        # Hex dump
        if not 0 <= offset < 0xFFFFFFFF:
            raise ValueError('offset overflow')

        last_zero = None
        count = 0
        iterbytes = six.iterbytes

        while True:
            # Input byte columns
            if length is None:
                chunk = instream.read(cols)
            else:
                chunk = instream.read(min(cols, length - count))

            if chunk:
                # Null line skipping
                if autoskip and not any(iterbytes(chunk)):
                    if last_zero:
                        offset += len(chunk)
                        count += len(chunk)
                        continue
                    else:
                        last_zero = Ellipsis

                # Byte grouping
                if groupsize:
                    tokens = chop(chunk, groupsize)
                else:
                    tokens = (chunk,)

                if bits:
                    tokens = ' '.join(''.join(BIN8_TO_STR[bits]
                                              for bits in iterbytes(token))
                                      for token in tokens)
                elif groupsize:
                    tokens = ' '.join(hexlify(token[::-1] if endian else token,
                                              upper=upper)
                                      for token in tokens)
                else:
                    tokens = hexlify(*tokens, upper=upper)

                # Comment text generation
                if ebcdic:
                    text = humanize(chunk, HUMAN_EBCDIC)
                else:
                    text = humanize(chunk, HUMAN_ASCII)

                # Line output
                line = line_fmt.format(offset, tokens, text)
                line = line.decode() if six.PY2 else line
                outstream.write(line)

                offset += len(chunk)
                count += len(chunk)

                if last_zero is Ellipsis:
                    last_zero = True
                    outstream.write('*\n')

            else:
                raise StopIteration  # End of input stream

    except StopIteration:
        pass

    finally:
        if instream is not None and isinstance(infile, str):
            instream.close()

        if outstream is not None and isinstance(outfile, str):
            outstream.close()

    return outstream
