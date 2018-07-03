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

import argparse
import io
import re
import sys

from .utils import BIN8_TO_STR
from .utils import chop
from .utils import hexlify
from .utils import humanize_ascii
from .utils import humanize_ebcdic
from .utils import parse_int
from .utils import unhexlify

_SEEKING_REGEX = re.compile(r'^(\+?-?)-?(\w+)$')

_REVERSE_REGEX = re.compile(r'^\s*(?P<address>[A-Fa-f0-9]+)\s*:\s*'
                            r'(?P<data>)([A-Fa-f0-9]{2}\s*)+'
                            r'(?P<garbage>.*)$')


def xxd(infile=None, outfile=None, a=None, b=None, c=None, e=None,
        E=None, g=None, i=None, l=None, o=None, p=False, q=False, r=False,  # noqa: E741
        seek=None, s=None, ss='', u=False, U=False):

    if c is not None and not 1 <= c <= 256:
        raise ValueError('invalid column count')

    if U:
        u = U

    if (b or e) and (p or i or r):
        raise ValueError('incompatible options')

    if sum(bool(_) for _ in [p, i, b]) > 1:
        raise ValueError('incompatible options')

    if not r and seek is not None:
        raise ValueError('incompatible options')
    elif seek is not None and seek < 0:
        raise ValueError('invalid seeking')

    instream = None
    outstream = None
    try:
        # Input stream binding
        if infile is None or infile == '-':
            infile = None
            instream = sys.stdin
        elif isinstance(infile, str):
            if r:
                instream = open(infile, 'rt')
            else:
                instream = open(infile, 'rb')
        elif isinstance(infile, (bytes, bytearray, memoryview)):
            instream = io.BytesIO(infile)

        # Output stream binding
        if outfile is None or outfile == '-':
            outfile = None
            outstream = sys.stdout
        elif isinstance(outfile, str):
            if r:
                if seek:
                    outstream = open(outfile, 'r+b')
                else:
                    outstream = open(outfile, 'wb')
            else:
                outstream = open(outfile, 'wt')
        elif outfile is Ellipsis:
            outstream = io.BytesIO()

        # Input seeking
        if s is not None:
            s = ss + str(s)
            m = _SEEKING_REGEX.match(s)
            if not m:
                raise ValueError('invalid seeking')
            ss, s = m.groups()
            s = parse_int(s)

            if ss == '':
                instream.seek(s, io.SEEK_SET)
            elif ss == '+':
                instream.seek(s, io.SEEK_CUR)
            elif ss == '+-':
                instream.seek(-s, io.SEEK_CUR)
            elif ss == '-':
                instream.seek(-s, io.SEEK_END)

        # Output seeking
        if r and seek:
            if outstream.seekable():
                outstream.seek(seek, io.SEEK_END)
                endex = outstream.tell()
                outstream.write(bytes(seek - endex))
                outstream.seek(seek, io.SEEK_SET)
            else:
                outstream.write(bytes(seek))
                outoffset = seek

        # Output mode handling
        if p:
            # Plain output
            if c is None:
                c = 30

            while True:
                chunk = instream.read(c)
                if chunk:
                    outstream.write(hexlify(chunk, upper=u))
                    outstream.write('\n')
                else:
                    # End of input stream
                    raise StopIteration

        elif r:
            if c is None:
                c = 16

            for line in instream:
                m = _REVERSE_REGEX.match(line)
                if m:
                    # Interpret line contents
                    groups = m.groupdict()
                    address = int(groups['address'], 16)
                    data = unhexlify(''.join(groups['data'].split()))
                    data = data[:c]

                    # Write line data (fill gaps if needed)
                    if outstream.seekable():
                        outstream.seek(address, io.SEEK_SET)
                    else:
                        if address < outoffset:
                            raise RuntimeError('negative seeking')
                        outstream.write(bytes(address - outoffset))
                        outoffset = address + len(data)
                    outstream.write(data)

            # End of input stream
            raise StopIteration

        elif b:
            if c is None:
                c = 6
            if g is None:
                g = 1

        elif i:
            if c is None:
                c = 12
            raise NotImplementedError

        else:
            if c is None:
                c = 16

        if g is None:
            g = 4 if e else 2
        if not 0 <= g <= 256:
            raise ValueError('invalid grouping')

        if g and not b:
            g_fmt = '{{:0{}X}}' if u else '{{:0{}x}}'
            g_fmt = g_fmt.format(2 * g if g else 2)
            bo = 'little' if e else 'big'

        data_width = c * (8 if b else 2) + ((c - 1) // g if g else 0)
        line_fmt = '{{:0{}{}}}: {{:{}s}}  {{}}\n'
        line_fmt = line_fmt.format(16 if q else 8,
                                   'X' if U else 'x',
                                   data_width)

        # Hex dump
        offset = parse_int(o) if o else 0
        if not 0 <= offset < 0xFFFFFFFF:
            raise ValueError('offset overflow')

        last_zero = None
        count = 0

        while True:
            # Input byte columns
            if l is None:
                chunk = instream.read(c)
            else:
                chunk = instream.read(min(c, l - count))

            if chunk:
                # Null line skipping
                if a and not any(chunk):
                    if last_zero:
                        offset += len(chunk)
                        count += len(chunk)
                        continue
                    else:
                        last_zero = Ellipsis

                # Byte grouping
                if g:
                    tokens = chop(chunk, g)
                else:
                    tokens = (chunk,)

                if b:
                    tokens = ' '.join(''.join(BIN8_TO_STR[b] for b in token)
                                      for token in tokens)
                elif g:
                    tokens = ' '.join(g_fmt.format(int.from_bytes(token, bo))
                                      [-(2 * len(token)):]
                                      for token in tokens)
                else:
                    tokens = hexlify(*tokens, upper=u)

                # Comment text generation
                if E:
                    text = humanize_ebcdic(chunk)
                else:
                    text = humanize_ascii(chunk)

                # Line output
                line = line_fmt.format(offset, tokens, text)
                outstream.write(line)

                offset += len(chunk)
                count += len(chunk)

                if last_zero is Ellipsis:
                    last_zero = True
                    outstream.write('*\n')

            else:
                # End of input stream
                raise StopIteration

    except StopIteration:
        pass

    finally:
        # Output file cleanup
        if instream is not None and isinstance(infile, str):
            instream.close()

        if outstream is not None and isinstance(outfile, str):
            outstream.close()

    return outstream


def build_argparser():
    parser = argparse.ArgumentParser(prog='xxd', add_help=False,
                                     description='Emulates the xxd command distributed by vim.')  # noqa E501

    parser.add_argument('-a', '-autoskip', action='store_true',
                        help="toggle autoskip: A single '*' replaces nul-lines. Default off.")  # noqa E501

    parser.add_argument('-b', '-bits', action='store_true',
                        help='Switch to bits (binary digits) dump, rather than hexdump. This option writes octets as eight digits "1"s and "0"s instead of a normal hexadecimal dump. Each line is preceded by a line number in hexadecimal and followed by an ascii (or ebcdic) representation. The command line switches -r, -p, -i do not work with this mode.')  # noqa E501

    parser.add_argument('-c', '-cols', metavar='cols', type=parse_int,
                        help='format <cols> octets per line. Default 16 (-i: 12, -ps: 30, -b: 6). Max 256.')  # noqa E501

    parser.add_argument('-E', '-EBCDIC', action='store_true',
                        help='Change the character encoding in the righthand column from ASCII to EBCDIC. This does not change the hexadecimal representation. The option is meaningless in combinations with -r, -p or -i.')  # noqa E501

    parser.add_argument('-e', action='store_true',
                        help='Switch to little-endian hexdump. This option treats byte groups as words in little-endian byte order. The default grouping of 4 bytes may be changed using -g. This option only applies to hexdump, leaving the ASCII (or EBCDIC) representation unchanged. The command line switches -r, -p, -i do not work with this mode.')  # noqa E501

    parser.add_argument('-g', '-groupsize', metavar='bytes', type=parse_int,
                        help='separate the output of every <bytes> bytes (two hex characters or eight bit-digits each) by a whitespace. Specify -g 0 to suppress grouping. <Bytes> defaults to 2 in normal mode, 4 in little-endian mode and 1 in bits mode. Grouping does not apply to postscript or include style.')  # noqa E501

    parser.add_argument('-i', '-include', action='store_true',
                        help='output in C include file style. A complete static array definition is written (named after the input file), unless xxd reads from stdin.')  # noqa E501

    parser.add_argument('-h', '-help', action='store_true',
                        help='print a summary of available commands and exit. No hex dumping is performed.')  # noqa E501

    parser.add_argument('-l', '-len', metavar='len', type=parse_int,
                        help='stop after writing <len> octets.')  # noqa E501

    parser.add_argument('-o', metavar='offset', type=parse_int,
                        help='add <offset> to the displayed file position.')  # noqa E501

    parser.add_argument('-p', '-ps', '-postscript', '-plain', action='store_true',
                        help='output in postscript continuous hexdump style. Also known as plain hexdump style.')  # noqa E501

    parser.add_argument('-q', action='store_true',
                        help='use 64-bit addressing')  # noqa E501

    parser.add_argument('-r', '-revert', action='store_true',
                        help='reverse operation: convert (or patch) hexdump into binary. If not writing to stdout, xxd writes into its output file without truncating it. Use the combination -r -p to read plain hexadecimal dumps without line number information and without a particular column layout. Additional Whitespace and line-breaks are allowed anywhere.')  # noqa E501

    parser.add_argument('-seek', metavar='offset', type=parse_int,
                        help='When used after -r: revert with <offset> added to file positions found in hexdump.')  # noqa E501

    parser.add_argument('-s', metavar='seek',
                        help='start at <seek> bytes abs. (or rel.) infile offset. + indicates that the seek is relative to the current stdin file position (meaningless when not reading from stdin). - indicates that the seek should be that many characters from the end of the input (or if combined with +: before the current stdin file position). Without -s option, xxd starts at the current file position.')  # noqa E501

    parser.add_argument('-u', action='store_true',
                        help='use upper case hex letters. Default is lower case.')  # noqa E501

    parser.add_argument('-U', action='store_true',
                        help='use upper case hex letters globally. Default is lower case.')  # noqa E501

    parser.add_argument('-v', '-version', action='store_true',
                        help='show version string.')  # noqa E501

    parser.add_argument('infile', nargs='?',
                        help="If no infile is given, standard input is read. If infile is specified as a '-' character, then input is taken from standard input.")  # noqa E501

    parser.add_argument('outfile', nargs='?',
                        help="If no outfile is given (or a '-' character is in its place), results are sent to standard output.")  # noqa E501

    return parser


def _main():
    parser = build_argparser()
    args = parser.parse_args()

    if args.h:
        parser.print_help()
        return

    kwargs = vars(args)
    del kwargs['h']
    del kwargs['v']

    xxd(**kwargs)


if __name__ == '__main__':
    _main()
