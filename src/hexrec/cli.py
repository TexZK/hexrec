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

"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -m hexrec` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``hexrec.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``hexrec.__main__`` in ``sys.modules``.

  Also see (1) from https://click.palletsprojects.com/en/stable/setuptools/#setuptools-integration
"""

from typing import Callable
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Type
from typing import cast as _cast

import click

from .__init__ import __version__
from .__init__ import file_types
from .base import BaseFile
from .base import guess_format_name
from .formats.srec import SrecFile
from .formats.srec import SrecRecord
from .hexdump import hexdump_core
from .utils import hexlify
from .utils import parse_int
from .utils import unhexlify
from .xxd import xxd_core


class BasedIntParamType(click.ParamType):
    name = 'integer'

    def convert(self, value, param, ctx):
        try:
            return parse_int(value)
        except ValueError:
            self.fail(f'invalid integer: {value!r}', param, ctx)


class ByteIntParamType(click.ParamType):
    name = 'byte'

    def convert(self, value, param, ctx):
        try:
            b = parse_int(value)
            if not 0 <= b <= 255:
                raise ValueError()
            return b
        except ValueError:
            self.fail(f'invalid byte: {value!r}', param, ctx)


class OrderedOptionsCommand(click.Command):

    def parse_args(self, ctx, args):

        parser = self.make_parser(ctx)
        opts, _, order = parser.parse_args(args=list(args))
        ordered_options = [(param, opts[param.name]) for param in order]
        setattr(self, 'ordered_options', ordered_options)
        return super().parse_args(ctx, args)


BASED_INT = BasedIntParamType()
BYTE_INT = ByteIntParamType()

FILE_PATH_IN = click.Path(dir_okay=False, allow_dash=True, readable=True, exists=True)
FILE_PATH_OUT = click.Path(dir_okay=False, allow_dash=True, writable=True)

FORMAT_CHOICE = click.Choice(list(sorted(file_types.keys())))

DATA_FMT_FORMATTERS: Mapping[str, Callable[[bytes], bytes]] = {
    'ascii': lambda b: b,
    'hex': lambda b: hexlify(b, upper=False),
    'HEX': lambda b: hexlify(b, upper=True),
    'hex.': lambda b: hexlify(b, sep=b'.', upper=False),
    'HEX.': lambda b: hexlify(b, sep=b'.', upper=True),
    'hex-': lambda b: hexlify(b, sep=b'-', upper=False),
    'HEX-': lambda b: hexlify(b, sep=b'-', upper=True),
    'hex:': lambda b: hexlify(b, sep=b':', upper=False),
    'HEX:': lambda b: hexlify(b, sep=b':', upper=True),
    'hex_': lambda b: hexlify(b, sep=b'_', upper=False),
    'HEX_': lambda b: hexlify(b, sep=b'_', upper=True),
    'hex ': lambda b: hexlify(b, sep=b' ', upper=False),
    'HEX ': lambda b: hexlify(b, sep=b' ', upper=True),
}

DATA_FMT_PARSERS: Mapping[str, Callable[[bytes], bytes]] = {
    'ascii': lambda b: b,
    'hex': lambda b: unhexlify(b),
    'HEX': lambda b: unhexlify(b),
    'hex.': lambda b: unhexlify(b, delete=b'.'),
    'HEX.': lambda b: unhexlify(b, delete=b'.'),
    'hex-': lambda b: unhexlify(b, delete=b'-'),
    'HEX-': lambda b: unhexlify(b, delete=b'-'),
    'hex:': lambda b: unhexlify(b, delete=b':'),
    'HEX:': lambda b: unhexlify(b, delete=b':'),
    'hex_': lambda b: unhexlify(b, delete=b'_'),
    'HEX_': lambda b: unhexlify(b, delete=b'_'),
    'hexs': lambda b: unhexlify(b, delete=b' \t'),
    'HEXs': lambda b: unhexlify(b, delete=b' \t'),
}

DATA_FMT_CHOICE = click.Choice(list(DATA_FMT_FORMATTERS.keys()))


# ----------------------------------------------------------------------------

def guess_input_type(
    input_path: Optional[str],
    input_format: Optional[str] = None,
) -> Type[BaseFile]:

    if input_format:
        input_type = file_types[input_format]
    elif input_path is None or input_path == '-':
        raise ValueError('standard input requires input format')
    else:
        name = guess_format_name(input_path)
        input_type = file_types[name]
    return input_type


def guess_output_type(
    output_path: Optional[str],
    output_format: Optional[str] = None,
    input_type: Optional[Type[BaseFile]] = None,
) -> Type[BaseFile]:

    if output_format:
        output_type = file_types[output_format]
    elif output_path is None or output_path == '-':
        output_type = input_type
    else:
        name = guess_format_name(output_path)
        output_type = file_types[name]
    return output_type


def print_version(ctx, _, value):

    if not value or ctx.resilient_parsing:
        return

    click.echo(str(__version__))
    ctx.exit()


def print_hexdump_version(ctx, _, value):

    if not value or ctx.resilient_parsing:
        return

    click.echo(f'hexdump from Python hexrec {__version__!s}')
    ctx.exit()


# ----------------------------------------------------------------------------

class SingleFileInOutCtxMgr:

    def __init__(
        self,
        input_path: str,
        input_format: Optional[str],
        output_path: str,
        output_format: Optional[str],
        output_width: Optional[int],
    ):

        if input_path == '-':
            input_path = None

        if not output_path:
            output_path = input_path
        if output_path == '-':
            output_path = None

        self.input_path: Optional[str] = input_path
        self.input_format: Optional[str] = input_format
        self.input_type: Optional[Type[BaseFile]] = None
        self.input_file: Optional[BaseFile] = None

        self.output_path: Optional[str] = output_path
        self.output_format: Optional[str] = output_format
        self.output_type: Optional[Type[BaseFile]] = None
        self.output_file: Optional[BaseFile] = None
        self.output_width: Optional[int] = output_width

    def __enter__(self) -> 'SingleFileInOutCtxMgr':

        self.input_type = guess_input_type(self.input_path, self.input_format)
        self.input_file = self.input_type.load(self.input_path)

        self.output_type = guess_output_type(self.output_path, self.output_format, self.input_type)

        if self.output_type is self.input_type:
            self.output_file = self.input_file
            self.output_file.apply_records()
        else:
            self.output_file = self.output_type.convert(self.input_file)

        if self.output_width is not None:
            self.output_file.maxdatalen = self.output_width

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:

        self.output_file.save(self.output_path)


class MultiFileInOutCtxMgr:

    def __init__(
        self,
        input_paths: Sequence[str],
        input_formats: Sequence[Optional[str]],
        output_path: str,
        output_format: Optional[str],
        output_width: Optional[int],
    ):

        input_paths = list(input_paths)
        for i, input_path in enumerate(input_paths):
            if input_path == '-':
                input_paths[i] = None

        if not output_path:
            output_path = input_paths[0]
        if output_path == '-':
            output_path = None

        self.input_paths: Sequence[Optional[str]] = input_paths
        self.input_formats: Sequence[Optional[str]] = input_formats
        self.input_types: List[Optional[Type[BaseFile]]] = [None] * len(self.input_paths)
        self.input_files: List[Optional[BaseFile]] = [None] * len(self.input_paths)

        self.output_path: Optional[str] = output_path
        self.output_format: Optional[str] = output_format
        self.output_type: Optional[Type[BaseFile]] = None
        self.output_file: Optional[BaseFile] = None
        self.output_width: Optional[int] = output_width

    def __enter__(self) -> 'MultiFileInOutCtxMgr':

        for i in range(len(self.input_paths)):
            self.input_types[i] = guess_input_type(self.input_paths[i], self.input_formats[i])
            self.input_files[i] = self.input_types[i].load(self.input_paths[i])

        self.output_type = guess_output_type(self.output_path, self.output_format, self.input_types[0])
        self.output_file = self.output_type()

        if self.output_width is not None:
            self.output_file.maxdatalen = self.output_width

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:

        self.output_file.save(self.output_path)


# ============================================================================

@click.group()
def main() -> None:
    """
    A set of command line utilities for common operations with record files.

    Being built with `Click <https://click.palletsprojects.com/en/stable/>`_, all the
    commands follow POSIX-like syntax rules, as well as reserving the virtual
    file path ``-`` for command chaining via standard output/input buffering.
    """


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=FORMAT_CHOICE, help="""
    Forces the input file format.
    Required for the standard input.
""")
@click.option('-o', '--output-format', type=FORMAT_CHOICE, help="""
    Forces the output file format.
    By default it is that of the input file.
""")
@click.option('-m', '--modulo', type=BYTE_INT, default=4, show_default=True, help="""
    Alignment modulo.
""")
@click.option('-s', '--start', type=BASED_INT, help="""
    Inclusive start address. Negative values are referred to the end of the data.
    By default it applies from the start of the data contents.
""")
@click.option('-e', '--endex', type=BASED_INT, help="""
    Exclusive end address. Negative values are referred to the end of the data.
    By default it applies till the end of the data contents.
""")
@click.option('-v', '--value', type=BYTE_INT, default=0, show_default=True, help="""
    Byte value used to flood alignment padding.
""")
@click.option('-w', '--width', type=BASED_INT, help="""
    Sets the length of the record data field, in bytes.
    By default it is that of the input file.
""")
@click.argument('infile', type=FILE_PATH_IN, required=False)
@click.argument('outfile', type=FILE_PATH_OUT, required=False)
def align(
    input_format: Optional[str],
    output_format: Optional[str],
    modulo: int,
    start: Optional[int],
    endex: Optional[int],
    value: Optional[int],
    width: Optional[int],
    infile: str,
    outfile: str,
) -> None:
    r"""Pads blocks to align their boundaries.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    Leave empty to overwrite ``INFILE``.
    """

    with SingleFileInOutCtxMgr(infile, input_format, outfile, output_format, width) as ctx:
        ctx.output_file.align(modulo, start=start, endex=endex, pattern=value)


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=FORMAT_CHOICE, help="""
    Forces the input file format.
    Required for the standard input.
""")
@click.option('-o', '--output-format', type=FORMAT_CHOICE, help="""
    Forces the output file format.
    By default it is that of the input file.
""")
@click.option('-s', '--start', type=BASED_INT, help="""
    Inclusive start address. Negative values are referred to the end of the data.
    By default it applies from the start of the data contents.
""")
@click.option('-e', '--endex', type=BASED_INT, help="""
    Exclusive end address. Negative values are referred to the end of the data.
    By default it applies till the end of the data contents.
""")
@click.option('-w', '--width', type=BASED_INT, help="""
    Sets the length of the record data field, in bytes.
    By default it is that of the input file.
""")
@click.argument('infile', type=FILE_PATH_IN, required=False)
@click.argument('outfile', type=FILE_PATH_OUT, required=False)
def clear(
    input_format: Optional[str],
    output_format: Optional[str],
    start: Optional[int],
    endex: Optional[int],
    width: Optional[int],
    infile: str,
    outfile: str,
) -> None:
    r"""Clears an address range.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    Leave empty to overwrite ``INFILE``.
    """

    with SingleFileInOutCtxMgr(infile, input_format, outfile, output_format, width) as ctx:
        ctx.output_file.clear(start=start, endex=endex)


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=FORMAT_CHOICE, help="""
    Forces the input file format.
    Required for the standard input.
""")
@click.option('-o', '--output-format', type=FORMAT_CHOICE, help="""
    Forces the output file format.
    By default it is that of the input file.
""")
@click.option('-w', '--width', type=BASED_INT, help="""
    Sets the length of the record data field, in bytes.
    By default it is that of the input file.
""")
@click.argument('infile', type=FILE_PATH_IN, required=False)
@click.argument('outfile', type=FILE_PATH_OUT, required=False)
def convert(
    input_format: Optional[str],
    output_format: Optional[str],
    width: Optional[int],
    infile: str,
    outfile: str,
) -> None:

    r"""Converts a file to another format.

    ``INFILE`` is the list of paths of the input files.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    Leave empty to overwrite ``INFILE``.
    """

    with SingleFileInOutCtxMgr(infile, input_format, outfile, output_format, width):
        pass


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=FORMAT_CHOICE, help="""
    Forces the input file format.
    Required for the standard input.
""")
@click.option('-o', '--output-format', type=FORMAT_CHOICE, help="""
    Forces the output file format.
    By default it is that of the input file.
""")
@click.option('-s', '--start', type=BASED_INT, help="""
    Inclusive start address. Negative values are referred to the end of the data.
    By default it applies from the start of the data contents.
""")
@click.option('-e', '--endex', type=BASED_INT, help="""
    Exclusive end address. Negative values are referred to the end of the data.
    By default it applies till the end of the data contents.
""")
@click.option('-v', '--value', type=BYTE_INT, help="""
    Byte value used to flood the address range.
    By default, no flood is performed.
""")
@click.option('-w', '--width', type=BASED_INT, help="""
    Sets the length of the record data field, in bytes.
    By default it is that of the input file.
""")
@click.argument('infile', type=FILE_PATH_IN, required=False)
@click.argument('outfile', type=FILE_PATH_OUT, required=False)
def crop(
    input_format: Optional[str],
    output_format: Optional[str],
    start: Optional[int],
    endex: Optional[int],
    value: Optional[int],
    width: Optional[int],
    infile: str,
    outfile: str,
) -> None:
    r"""Selects data from an address range.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    Leave empty to overwrite ``INFILE``.
    """

    with SingleFileInOutCtxMgr(infile, input_format, outfile, output_format, width) as ctx:
        ctx.output_file.crop(start=start, endex=endex)

        if value is not None:
            ctx.output_file.flood(start=start, endex=endex, pattern=value)


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=FORMAT_CHOICE, help="""
    Forces the input file format.
    Required for the standard input.
""")
@click.option('-o', '--output-format', type=FORMAT_CHOICE, help="""
    Forces the output file format.
    By default it is that of the input file.
""")
@click.option('-s', '--start', type=BASED_INT, help="""
    Inclusive start address. Negative values are referred to the end of the data.
    By default it applies from the start of the data contents.
""")
@click.option('-e', '--endex', type=BASED_INT, help="""
    Exclusive end address. Negative values are referred to the end of the data.
    By default it applies till the end of the data contents.
""")
@click.option('-w', '--width', type=BASED_INT, help="""
    Sets the length of the record data field, in bytes.
    By default it is that of the input file.
""")
@click.argument('infile', type=FILE_PATH_IN, required=False)
@click.argument('outfile', type=FILE_PATH_OUT, required=False)
def delete(
    input_format: Optional[str],
    output_format: Optional[str],
    start: Optional[int],
    endex: Optional[int],
    width: Optional[int],
    infile: str,
    outfile: str,
) -> None:
    r"""Deletes an address range.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    Leave empty to overwrite ``INFILE``.
    """

    with SingleFileInOutCtxMgr(infile, input_format, outfile, output_format, width) as ctx:
        ctx.output_file.delete(start=start, endex=endex)


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=FORMAT_CHOICE, help="""
    Forces the input file format.
    Required for the standard input.
""")
@click.option('-o', '--output-format', type=FORMAT_CHOICE, help="""
    Forces the output file format.
    By default it is that of the input file.
""")
@click.option('-v', '--value', type=BYTE_INT, default=0, show_default=True, help="""
    Byte value used to fill the address range.
""")
@click.option('-s', '--start', type=BASED_INT, help="""
    Inclusive start address. Negative values are referred to the end of the data.
    By default it applies from the start of the data contents.
""")
@click.option('-e', '--endex', type=BASED_INT, help="""
    Exclusive end address. Negative values are referred to the end of the data.
    By default it applies till the end of the data contents.
""")
@click.option('-w', '--width', type=BASED_INT, help="""
    Sets the length of the record data field, in bytes.
    By default it is that of the input file.
""")
@click.argument('infile', type=FILE_PATH_IN, required=False)
@click.argument('outfile', type=FILE_PATH_OUT, required=False)
def fill(
    input_format: Optional[str],
    output_format: Optional[str],
    value: int,
    start: Optional[int],
    endex: Optional[int],
    width: Optional[int],
    infile: str,
    outfile: str,
) -> None:
    r"""Fills an address range with a byte value.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    Leave empty to overwrite ``INFILE``.
    """

    with SingleFileInOutCtxMgr(infile, input_format, outfile, output_format, width) as ctx:
        ctx.output_file.fill(start=start, endex=endex, pattern=value)


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=FORMAT_CHOICE, help="""
    Forces the input file format.
    Required for the standard input.
""")
@click.option('-o', '--output-format', type=FORMAT_CHOICE, help="""
    Forces the output file format.
    By default it is that of the input file.
""")
@click.option('-v', '--value', type=BYTE_INT, default=0, show_default=True, help="""
    Byte value used to flood the address range.
""")
@click.option('-s', '--start', type=BASED_INT, help="""
    Inclusive start address. Negative values are referred to the end of the data.
    By default it applies from the start of the data contents.
""")
@click.option('-e', '--endex', type=BASED_INT, help="""
    Exclusive end address. Negative values are referred to the end of the data.
    By default it applies till the end of the data contents.
""")
@click.option('-w', '--width', type=BASED_INT, help="""
    Sets the length of the record data field, in bytes.
    By default it is that of the input file.
""")
@click.argument('infile', type=FILE_PATH_IN, required=False)
@click.argument('outfile', type=FILE_PATH_OUT, required=False)
def flood(
    input_format: Optional[str],
    output_format: Optional[str],
    value: int,
    start: Optional[int],
    endex: Optional[int],
    width: Optional[int],
    infile: str,
    outfile: str,
) -> None:
    r"""Fills emptiness of an address range with a byte value.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    Leave empty to overwrite ``INFILE``.
    """

    with SingleFileInOutCtxMgr(infile, input_format, outfile, output_format, width) as ctx:
        ctx.output_file.flood(start=start, endex=endex, pattern=value)


# ----------------------------------------------------------------------------

# noinspection PyShadowingBuiltins
@main.command(cls=OrderedOptionsCommand,
              context_settings=dict(help_option_names=['-h', '--help']))
@click.option('-b', '--one-byte-octal', 'one_byte_octal', is_flag=True,
              multiple=True, help="""
    One-byte octal display. Display the input offset in
    hexadecimal, followed by sixteen space-separated,
    three-column, zero-filled bytes of input data, in octal, per
    line.
""")
@click.option('-X', '--one-byte-hex', 'one_byte_hex', is_flag=True,
              multiple=True, help="""
    One-byte hexadecimal display. Display the input offset in
    hexadecimal, followed by sixteen space-separated, two-column,
    zero-filled bytes of input data, in hexadecimal, per line.
""")
@click.option('-c', '--one-byte-char', 'one_byte_char', is_flag=True,
              multiple=True, help="""
    One-byte character display. Display the input offset in
    hexadecimal, followed by sixteen space-separated,
    three-column, space-filled characters of input data per line.
""")
@click.option('-C', '--canonical', 'canonical', is_flag=True,
              multiple=True, help="""
    Canonical hex+ASCII display. Display the input offset in
    hexadecimal, followed by sixteen space-separated, two-column,
    hexadecimal bytes, followed by the same sixteen bytes in %_p
    format enclosed in | characters. Invoking the program as hd
    implies this option.
""")
@click.option('-d', '--two-bytes-decimal', 'two_bytes_decimal', is_flag=True,
              multiple=True, help="""
    Two-byte decimal display. Display the input offset in
    hexadecimal, followed by eight space-separated, five-column,
    zero-filled, two-byte units of input data, in unsigned
    decimal, per line.
""")
@click.option('-o', '--two-bytes-octal', 'two_bytes_octal', is_flag=True,
              multiple=True, help="""
    Two-byte octal display. Display the input offset in
    hexadecimal, followed by eight space-separated, six-column,
    zero-filled, two-byte quantities of input data, in octal, per
    line.
""")
@click.option('-x', '--two-bytes-hex', 'two_bytes_hex', is_flag=True,
              multiple=True, help="""
    Two-byte hexadecimal display. Display the input offset in
    hexadecimal, followed by eight space-separated, four-column,
    zero-filled, two-byte quantities of input data, in
    hexadecimal, per line.
""")
@click.option('-n', '--length', 'length', type=BASED_INT, help="""
    Interpret only length bytes of input.
""")
@click.option('-s', '--skip', 'skip', type=BASED_INT, help="""
    Skip offset bytes from the beginning of the input.
""")
@click.option('-v', '--no_squeezing', 'no_squeezing', is_flag=True, help="""
    The -v option causes hexdump to display all input data.
    Without the -v option, any number of groups of output lines
    which would be identical to the immediately preceding group
    of output lines (except for the input offsets), are replaced
    with a line comprised of a single asterisk.
""")
@click.option('-U', '--upper', 'upper', is_flag=True, help="""
    Uses upper case hex letters on address and data.
""")
@click.option('-I', '--input-format', type=FORMAT_CHOICE, help="""
    Forces the input file format.
""")
@click.option('-V', '--version', is_flag=True, is_eager=True,
              expose_value=False, callback=print_hexdump_version, help="""
    Print version and exit.
""")
@click.argument('infile', type=FILE_PATH_IN, required=False)
def hexdump(
    infile: str,
    one_byte_octal: Sequence[bool],
    one_byte_hex: Sequence[bool],
    one_byte_char: Sequence[bool],
    canonical: Sequence[bool],
    two_bytes_decimal: Sequence[bool],
    two_bytes_octal: Sequence[bool],
    two_bytes_hex: Sequence[bool],
    length: Optional[int],
    skip: Optional[int],
    no_squeezing: bool,
    upper: bool,
    input_format: Optional[str],
) -> None:
    r"""Display file contents in hexadecimal, decimal, octal, or ascii.

    The hexdump utility is a filter which displays the specified
    files, or standard input if no files are specified, in a
    user-specified format.

    Below, the length and offset arguments may be followed by the
    multiplicative suffixes KiB (=1024), MiB (=1024*1024), and so on
    for GiB, TiB, PiB, EiB, ZiB and YiB (the "iB" is optional, e.g.,
    "K" has the same meaning as "KiB"), or the suffixes KB (=1000),
    MB (=1000*1000), and so on for GB, TB, PB, EB, ZB and YB.

    For each input file, hexdump sequentially copies the input to
    standard output, transforming the data according to the format
    strings specified by the -e and -f options, in the order that
    they were specified.
    """

    kwargs = {
        'one_byte_octal': any(one_byte_octal),
        'one_byte_hex': any(one_byte_hex),
        'one_byte_char': any(one_byte_char),
        'canonical': any(canonical),
        'two_bytes_decimal': any(two_bytes_decimal),
        'two_bytes_octal': any(two_bytes_octal),
        'two_bytes_hex': any(two_bytes_hex),
    }
    format_order = [param.name
                    for param, value in hexdump.ordered_options
                    if (param.name in kwargs) and value]

    if input_format:
        input_type = guess_input_type(infile, input_format)
        input_file = input_type.load(infile)
        infile = input_file.memory

    hexdump_core(
        infile=infile,
        length=length,
        skip=skip,
        no_squeezing=no_squeezing,
        upper=upper,
        format_order=format_order,
        **kwargs,
    )


# ----------------------------------------------------------------------------

# noinspection PyShadowingBuiltins
@main.command(cls=OrderedOptionsCommand,
              context_settings=dict(help_option_names=['-h', '--help']))
@click.option('-b', '--one-byte-octal', 'one_byte_octal', is_flag=True,
              multiple=True, help="""
    One-byte octal display. Display the input offset in
    hexadecimal, followed by sixteen space-separated,
    three-column, zero-filled bytes of input data, in octal, per
    line.
""")
@click.option('-X', '--one-byte-hex', 'one_byte_hex', is_flag=True,
              multiple=True, help="""
    One-byte hexadecimal display. Display the input offset in
    hexadecimal, followed by sixteen space-separated, two-column,
    zero-filled bytes of input data, in hexadecimal, per line.
""")
@click.option('-c', '--one-byte-char', 'one_byte_char', is_flag=True,
              multiple=True, help="""
    One-byte character display. Display the input offset in
    hexadecimal, followed by sixteen space-separated,
    three-column, space-filled characters of input data per line.
""")
@click.option('-d', '--two-bytes-decimal', 'two_bytes_decimal', is_flag=True,
              multiple=True, help="""
    Two-byte decimal display. Display the input offset in
    hexadecimal, followed by eight space-separated, five-column,
    zero-filled, two-byte units of input data, in unsigned
    decimal, per line.
""")
@click.option('-o', '--two-bytes-octal', 'two_bytes_octal', is_flag=True,
              multiple=True, help="""
    Two-byte octal display. Display the input offset in
    hexadecimal, followed by eight space-separated, six-column,
    zero-filled, two-byte quantities of input data, in octal, per
    line.
""")
@click.option('-x', '--two-bytes-hex', 'two_bytes_hex', is_flag=True,
              multiple=True, help="""
    Two-byte hexadecimal display. Display the input offset in
    hexadecimal, followed by eight space-separated, four-column,
    zero-filled, two-byte quantities of input data, in
    hexadecimal, per line.
""")
@click.option('-n', '--length', 'length', type=BASED_INT, help="""
    Interpret only length bytes of input.
""")
@click.option('-s', '--skip', 'skip', type=BASED_INT, help="""
    Skip offset bytes from the beginning of the input.
""")
@click.option('-v', '--no_squeezing', 'no_squeezing', is_flag=True, help="""
    The -v option causes hexdump to display all input data.
    Without the -v option, any number of groups of output lines
    which would be identical to the immediately preceding group
    of output lines (except for the input offsets), are replaced
    with a line comprised of a single asterisk.
""")
@click.option('-U', '--upper', 'upper', is_flag=True, help="""
    Uses upper case hex letters on address and data.
""")
@click.option('-I', '--input-format', type=FORMAT_CHOICE, help="""
    Forces the input file format.
""")
@click.option('-V', '--version', is_flag=True, is_eager=True,
              expose_value=False, callback=print_hexdump_version, help="""
    Print version and exit.
""")
@click.argument('infile', type=FILE_PATH_IN, required=False)
def hd(
    infile: str,
    one_byte_octal: Sequence[bool],
    one_byte_hex: Sequence[bool],
    one_byte_char: Sequence[bool],
    two_bytes_decimal: Sequence[bool],
    two_bytes_octal: Sequence[bool],
    two_bytes_hex: Sequence[bool],
    length: Optional[int],
    skip: Optional[int],
    no_squeezing: bool,
    upper: bool,
    input_format: Optional[str],
) -> None:
    r"""Display file contents in hexadecimal, decimal, octal, or ascii.

    The hexdump utility is a filter which displays the specified
    files, or standard input if no files are specified, in a
    user-specified format.

    Below, the length and offset arguments may be followed by the
    multiplicative suffixes KiB (=1024), MiB (=1024*1024), and so on
    for GiB, TiB, PiB, EiB, ZiB and YiB (the "iB" is optional, e.g.,
    "K" has the same meaning as "KiB"), or the suffixes KB (=1000),
    MB (=1000*1000), and so on for GB, TB, PB, EB, ZB and YB.

    For each input file, hexdump sequentially copies the input to
    standard output, transforming the data according to the format
    strings specified by the -e and -f options, in the order that
    they were specified.
    """

    kwargs = {
        'one_byte_octal': any(one_byte_octal),
        'one_byte_hex': any(one_byte_hex),
        'one_byte_char': any(one_byte_char),
        'two_bytes_decimal': any(two_bytes_decimal),
        'two_bytes_octal': any(two_bytes_octal),
        'two_bytes_hex': any(two_bytes_hex),
    }
    format_order = [param.name
                    for param, value in hd.ordered_options
                    if (param.name in kwargs) and value]
    format_order.insert(0, 'canonical')
    kwargs['canonical'] = True

    if input_format:
        input_type = guess_input_type(infile, input_format)
        input_file = input_type.load(infile)
        infile = input_file.memory

    hexdump_core(
        infile=infile,
        length=length,
        skip=skip,
        no_squeezing=no_squeezing,
        upper=upper,
        format_order=format_order,
        **kwargs,
    )


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=FORMAT_CHOICE, help="""
    Forces the input file format for all input files.
    Required for the standard input.
""")
@click.option('-o', '--output-format', type=FORMAT_CHOICE, help="""
    Forces the output file format.
    By default it is that of the input file.
""")
@click.option('-w', '--width', type=BASED_INT, help="""
    Sets the length of the record data field, in bytes.
    By default it is that of the input file.
""")
@click.option('--clear-holes', is_flag=True, help="""
    Merges memory holes, clearing data at their place.
""")
@click.argument('infiles', type=FILE_PATH_IN, nargs=-1)
@click.argument('outfile', type=FILE_PATH_OUT)
def merge(
    input_format: Optional[str],
    output_format: Optional[str],
    width: Optional[int],
    clear_holes: bool,
    infiles: Sequence[str],
    outfile: str,
) -> None:
    r"""Merges multiple files.

    ``INFILES`` is the list of paths of the input files.
    Set any to ``-`` or none to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.

    Every file of ``INFILES`` will overwrite data of previous files of the
    list where addresses overlap.
    """

    if not infiles:
        infiles = [None]
    input_formats = [input_format] * len(infiles)

    with MultiFileInOutCtxMgr(infiles, input_formats, outfile, output_format, width) as ctx:
        ctx.output_file.merge(*ctx.input_files, clear=clear_holes)


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=FORMAT_CHOICE, help="""
    Forces the input file format.
    Required for the standard input.
""")
@click.option('-o', '--output-format', type=FORMAT_CHOICE, help="""
    Forces the output file format.
    By default it is that of the input file.
""")
@click.option('-n', '--amount', type=BASED_INT, default=0, help="""
    Address shift to apply.
""")
@click.option('-w', '--width', type=BASED_INT, help="""
    Sets the length of the record data field, in bytes.
    By default it is that of the input file.
""")
@click.argument('infile', type=FILE_PATH_IN, required=False)
@click.argument('outfile', type=FILE_PATH_OUT, required=False)
def shift(
    input_format: Optional[str],
    output_format: Optional[str],
    amount: int,
    width: Optional[int],
    infile: str,
    outfile: str,
) -> None:
    r"""Shifts data addresses.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    Leave empty to overwrite ``INFILE``.
    """

    with SingleFileInOutCtxMgr(infile, input_format, outfile, output_format, width) as ctx:
        ctx.output_file.shift(amount)


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=FORMAT_CHOICE, help="""
    Forces the input file format.
    Required for the standard input.
""")
@click.argument('infile', type=FILE_PATH_IN, required=False)
def validate(
    input_format: Optional[str],
    infile: str,
) -> None:
    r"""Validates a record file.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.
    """

    input_type = guess_input_type(infile, input_format)
    input_file = input_type.load(infile)
    input_file.validate_records()


# ----------------------------------------------------------------------------

@main.group()
def srec() -> None:
    """Motorola SREC specific"""


# ----------------------------------------------------------------------------

# noinspection PyShadowingBuiltins
@srec.command()
@click.option('-f', '--format', 'format', type=DATA_FMT_CHOICE,
              default='ascii', show_default=True, help="""
    Header data format.
""")
@click.argument('infile', type=FILE_PATH_IN, required=False)
def get_header(
    format: str,
    infile: str,
) -> None:
    r"""Gets the header data.

    ``INFILE`` is the path of the input file; 'srec' record type.
    Set to ``-`` to read from standard input.
    """

    input_file = SrecFile.load(infile)
    records = input_file.records

    if records and records[0].tag == 0:
        formatter = DATA_FMT_FORMATTERS[format]
        text = formatter(records[0].data).decode()
        print(text)


# ----------------------------------------------------------------------------

# noinspection PyShadowingBuiltins
@srec.command()
@click.option('-f', '--format', 'format', type=DATA_FMT_CHOICE,
              default='ascii', show_default=True, help="""
    Header data format.
""")
@click.argument('header', type=str)
@click.argument('infile', type=FILE_PATH_IN, required=False)
@click.argument('outfile', type=FILE_PATH_OUT, required=False)
def set_header(
    format: str,
    header: str,
    infile: str,
    outfile: str,
) -> None:
    r"""Sets the header data record.

    The header record is expected to be the first.
    All other records are kept as-is.
    No file-wise validation occurs.

    ``INFILE`` is the path of the input file; 'srec' record type.
    Set to ``-`` to read from standard input.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    Leave empty to overwrite ``INFILE``.
    """

    parser = DATA_FMT_PARSERS[format]
    header_data = parser(header.encode())
    file = SrecFile.load(infile)
    records = _cast(List[SrecRecord], file.records)

    if records and records[0].tag == 0:
        record = records[0]
        record.data = header_data
        record.update_count()
        record.update_checksum()
    else:
        record = SrecRecord.create_header(header_data)
        records.insert(0, record)

    file.save(outfile)


# ----------------------------------------------------------------------------

# noinspection PyShadowingBuiltins
@srec.command()
@click.argument('infile', type=FILE_PATH_IN, required=False)
@click.argument('outfile', type=FILE_PATH_OUT, required=False)
def del_header(
    infile: str,
    outfile: str,
) -> None:
    r"""Deletes the header data record.

    The header record is expected to be the first.
    All other records are kept as-is.
    No file-wise validation occurs.

    ``INFILE`` is the path of the input file; 'srec' record type.
    Set to ``-`` to read from standard input.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    Leave empty to overwrite ``INFILE``.
    """

    file = SrecFile.load(infile)
    records = file.records

    if records and records[0].tag == 0:
        del records[0]

    file.save(outfile)


# ----------------------------------------------------------------------------

@main.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option('-a', '--autoskip', 'autoskip', is_flag=True, help="""
    Toggles autoskip.

    A single '*' replaces null lines.
""")
@click.option('-b', '--bits', 'bits', is_flag=True, help="""
    Binary digits.

    Switches to bits (binary digits) dump, rather than
    hexdump. This option writes octets as eight digits of '1' and '0'
    instead of a normal hexadecimal dump. Each line is preceded by a
    line number in hexadecimal and followed by an ASCII (or EBCDIC)
    representation.
    The argument switches -r, -p, -i do not work with this mode.
""")
@click.option('-c', '--cols', 'cols', type=BASED_INT, help="""
    Formats <cols> octets per line. Max 256.

    Defaults: normal 16, -i 12, -p 30, -b 6.
""")
@click.option('-E', '--ebcdic', '--EBCDIC', 'ebcdic', is_flag=True, help="""
    Uses EBCDIC charset.

    Changes the character encoding in the right-hand
    column from ASCII to EBCDIC.
    This does not change the hexadecimal representation.
    The option is meaningless in combinations with -r, -p or -i.
""")
@click.option('-e', '--endian', 'endian', is_flag=True, help="""
    Switches to little-endian hexdump.

    This option treats  byte groups as words in little-endian byte order.
    The default grouping of 4 bytes may be changed using -g.
    This option only applies to hexdump, leaving the ASCII (or EBCDIC)
    representation unchanged.
    The switches -r, -p, -i do not work with this mode.
""")
@click.option('-g', '--groupsize', 'groupsize', type=BASED_INT, help="""
    Byte group size.

    Separates the output of every <groupsize> bytes (two hex
    characters or eight bit-digits each) by a whitespace.
    Specify <groupsize> 0 to suppress grouping.
    <groupsize> defaults to 2 in normal mode, 4 in little-endian mode and 1
    in bits mode. Grouping does not apply to -p or -i.
""")
@click.option('-i', '--include', 'include', is_flag=True, help="""
    Output in C include file style.

    A complete static array definition is written (named after the
    input file), unless reading from standard input.
""")
@click.option('-l', '--length', '--len', 'length', type=BASED_INT, help="""
    Stops after writing <length> octets.
""")
@click.option('-o', '--offset', 'offset', type=BASED_INT, help="""
    Adds <offset> to the displayed file position.
""")
@click.option('-p', '--postscript', '--plain', '--ps', 'postscript',
              is_flag=True, help="""
    Outputs in postscript continuous hexdump style.

    Also known as plain hexdump style.
""")
@click.option('-q', '--quadword', 'quadword', is_flag=True, help="""
    Uses 64-bit addressing.
""")
@click.option('-r', '--revert', 'revert', is_flag=True, help="""
    Reverse operation.

    Convert (or patch) hexdump into binary.
    If not writing to standard output, it writes into its
    output file without truncating it.
    Use the combination -r and -p to read plain hexadecimal dumps
    without line number information and without a particular column
    layout. Additional Whitespace and line breaks are allowed anywhere.
""")
@click.option('-k', '--seek', 'oseek', type=BASED_INT, help="""
    Output seeking.

    When used after -r reverts with -o added to
    file positions found in hexdump.
""")
@click.option('-s', 'iseek', help="""
    Input seeking.

    Starts at <s> bytes absolute (or relative) input offset.
    Without -s option, it starts at the current file position.
    The prefix is used to compute the offset.
    '+' indicates that the seek is relative to the current input
    position.
    '-' indicates that the seek should be that many characters from
    the end of the input.
    '+-' indicates that the seek should be that many characters
    before the current stdin file position.
""")
@click.option('-U', '--upper-all', 'upper_all', is_flag=True, help="""
    Uses upper case hex letters on address and data.
""")
@click.option('-u', '--upper', 'upper', is_flag=True, help="""
    Uses upper case hex letters on data only.
""")
@click.option('-I', '--input-format', type=FORMAT_CHOICE, help="""
    Forces the input file format.
""")
@click.option('-O', '--output-format', type=FORMAT_CHOICE, help="""
    Forces the output file format.
""")
@click.option('--seek-zeroes/--no-seek-zeroes', 'oseek_zeroes', is_flag=True,
              default=True, show_default=True, help="""
    Output seeking writes zeroes while seeking.
""")
@click.option('-v', '--version', is_flag=True, is_eager=True,
              expose_value=False, callback=print_version, help="""
    Prints the package version number.
""")
@click.argument('infile', type=FILE_PATH_IN, required=False)
@click.argument('outfile', type=FILE_PATH_OUT, required=False)
def xxd(
    autoskip: bool,
    bits: bool,
    cols: int,
    ebcdic: bool,
    endian: bool,
    groupsize: int,
    include: bool,
    length: int,
    offset: int,
    postscript: bool,
    quadword: bool,
    revert: bool,
    oseek: int,
    iseek: int,
    upper_all: bool,
    upper: bool,
    input_format: str,
    output_format: str,
    oseek_zeroes: bool,
    infile: str,
    outfile: str,
) -> None:
    r"""Emulates the xxd command.

    Please refer to the xxd manual page to know its features and caveats.

    Some parameters were changed to satisfy the POSIX-like command line parser.
    """

    infile = None if infile == '-' else infile
    outfile = None if outfile == '-' else outfile
    output_path = outfile
    output_file = None
    input_type = None

    if input_format:
        input_type = guess_input_type(infile, input_format)
        input_file = input_type.load(infile)
        infile = input_file.memory

    if output_format:
        output_type = guess_output_type(outfile, input_format, input_type)
        output_file = output_type()
        outfile = output_file.memory

    xxd_core(
        infile=infile,
        outfile=outfile,
        autoskip=autoskip,
        bits=bits,
        cols=cols,
        ebcdic=ebcdic,
        endian=endian,
        groupsize=groupsize,
        include=include,
        length=length,
        offset=offset,
        postscript=postscript,
        quadword=quadword,
        revert=revert,
        oseek=oseek,
        iseek=iseek,
        upper_all=upper_all,
        upper=upper,
        oseek_zeroes=oseek_zeroes,
    )

    if output_format:
        output_file.save(output_path)
