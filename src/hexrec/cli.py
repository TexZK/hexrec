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

  Also see (1) from https://click.palletsprojects.com/en/5.x/setuptools/#setuptools-integration
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
from .__init__ import FILE_TYPES
from .formats.motorola import SrecFile
from .formats.motorola import SrecRecord
from .records import BaseFile
from .records import guess_type_name
from .utils import hexlify
from .utils import parse_int
from .utils import unhexlify
from .xxd import xxd as xxd_core


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


BASED_INT = BasedIntParamType()
BYTE_INT = ByteIntParamType()

FILE_PATH_IN = click.Path(dir_okay=False, allow_dash=True, readable=True, exists=True)
FILE_PATH_OUT = click.Path(dir_okay=False, allow_dash=True, writable=True)

RECORD_FORMAT_CHOICE = click.Choice(list(sorted(FILE_TYPES.keys())))

DATA_FMT_FORMATTERS: Mapping[str, Callable[[bytes], str]] = {
    'ascii': lambda b: b.decode('ascii'),
    'hex': lambda b: hexlify(b, upper=False),
    'HEX': lambda b: hexlify(b, upper=True),
    'hex.': lambda b: hexlify(b, sep='.', upper=False),
    'HEX.': lambda b: hexlify(b, sep='.', upper=True),
    'hex-': lambda b: hexlify(b, sep='-', upper=False),
    'HEX-': lambda b: hexlify(b, sep='-', upper=True),
    'hex:': lambda b: hexlify(b, sep=':', upper=False),
    'HEX:': lambda b: hexlify(b, sep=':', upper=True),
    'hex_': lambda b: hexlify(b, sep='_', upper=False),
    'HEX_': lambda b: hexlify(b, sep='_', upper=True),
    'hex ': lambda b: hexlify(b, sep=' ', upper=False),
    'HEX ': lambda b: hexlify(b, sep=' ', upper=True),
}

DATA_FMT_PARSERS: Mapping[str, Callable[[str], bytes]] = {
    'ascii': lambda t: t.encode('ascii'),
    'hex': lambda t: unhexlify(t),
    'HEX': lambda t: unhexlify(t),
    'hex.': lambda t: unhexlify(t.replace('.', '')),
    'HEX.': lambda t: unhexlify(t.replace('.', '')),
    'hex-': lambda t: unhexlify(t.replace('-', '')),
    'HEX-': lambda t: unhexlify(t.replace('-', '')),
    'hex:': lambda t: unhexlify(t.replace(':', '')),
    'HEX:': lambda t: unhexlify(t.replace(':', '')),
    'hex_': lambda t: unhexlify(t.replace('_', '')),
    'HEX_': lambda t: unhexlify(t.replace('_', '')),
    'hex ': lambda t: unhexlify(t),
    'HEX ': lambda t: unhexlify(t),
}

DATA_FMT_CHOICE = click.Choice(list(DATA_FMT_FORMATTERS.keys()))


# ----------------------------------------------------------------------------

def guess_input_type(
    input_path: str,
    input_format: Optional[str] = None,
) -> Type[BaseFile]:

    if input_format:
        input_type = FILE_TYPES[input_format]
    elif input_path == '-':
        raise ValueError('standard input requires input format')
    else:
        name = guess_type_name(input_path)
        input_type = FILE_TYPES[name]
    return input_type


def guess_output_type(
    output_path: str,
    output_format: Optional[str] = None,
    input_type: Optional[Type[BaseFile]] = None,
) -> Type[BaseFile]:

    if output_format:
        output_type = FILE_TYPES[output_format]
    elif output_path == '-':
        output_type = input_type
    else:
        name = guess_type_name(output_path)
        output_type = FILE_TYPES[name]
    return output_type


def print_version(ctx, _, value):

    if not value or ctx.resilient_parsing:
        return

    click.echo(str(__version__))
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

        if not output_path:
            output_path = input_path

        self.input_path: str = input_path
        self.input_format: Optional[str] = input_format
        self.input_type: Optional[Type[BaseFile]] = None
        self.input_file: Optional[BaseFile] = None

        self.output_path: str = output_path
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

        if not output_path:
            output_path = input_paths[0]

        self.input_paths: Sequence[str] = input_paths
        self.input_formats: Sequence[Optional[str]] = input_formats
        self.input_types: List[Optional[Type[BaseFile]]] = [None] * len(self.input_paths)
        self.input_files: List[Optional[BaseFile]] = [None] * len(self.input_paths)

        self.output_path: str = output_path
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

    Being built with `Click <https://click.palletsprojects.com/>`_, all the
    commands follow POSIX-like syntax rules, as well as reserving the virtual
    file path ``-`` for command chaining via standard output/input buffering.
    """


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=RECORD_FORMAT_CHOICE, help="""
Forces the input file format.
Required for the standard input.
""")
@click.option('-o', '--output-format', type=RECORD_FORMAT_CHOICE, help="""
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
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
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
@click.option('-i', '--input-format', type=RECORD_FORMAT_CHOICE, help="""
Forces the input file format.
Required for the standard input.
""")
@click.option('-o', '--output-format', type=RECORD_FORMAT_CHOICE, help="""
Forces the output file format.
By default it is that of the input file.
""")
@click.option('-w', '--width', type=BASED_INT, help="""
Sets the length of the record data field, in bytes.
By default it is that of the input file.
""")
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
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
@click.option('-i', '--input-format', type=RECORD_FORMAT_CHOICE, help="""
Forces the input file format.
Required for the standard input.
""")
@click.option('-o', '--output-format', type=RECORD_FORMAT_CHOICE, help="""
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
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
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
@click.option('-i', '--input-format', type=RECORD_FORMAT_CHOICE, help="""
Forces the input file format.
Required for the standard input.
""")
@click.option('-o', '--output-format', type=RECORD_FORMAT_CHOICE, help="""
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
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
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
@click.option('-i', '--input-format', type=RECORD_FORMAT_CHOICE, help="""
Forces the input file format.
Required for the standard input.
""")
@click.option('-o', '--output-format', type=RECORD_FORMAT_CHOICE, help="""
Forces the output file format.
By default it is that of the input file.
""")
@click.option('-v', '--value', type=BYTE_INT, default=0xFF, help="""
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
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
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
@click.option('-i', '--input-format', type=RECORD_FORMAT_CHOICE, help="""
Forces the input file format.
Required for the standard input.
""")
@click.option('-o', '--output-format', type=RECORD_FORMAT_CHOICE, help="""
Forces the output file format.
By default it is that of the input file.
""")
@click.option('-v', '--value', type=BYTE_INT, default=0xFF, help="""
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
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
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

@main.command()
@click.option('-i', '--input-format', type=RECORD_FORMAT_CHOICE, help="""
Forces the input file format for all input files.
Required for the standard input.
""")
@click.option('-o', '--output-format', type=RECORD_FORMAT_CHOICE, help="""
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
        infiles = ['-']
    input_formats = [input_format] * len(infiles)

    with MultiFileInOutCtxMgr(infiles, input_formats, outfile, output_format, width) as ctx:
        for input_file in ctx.input_files:
            ctx.output_file.merge(input_file, clear=clear_holes)


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=RECORD_FORMAT_CHOICE, help="""
Forces the input file format.
Required for the standard input.
""")
@click.option('-o', '--output-format', type=RECORD_FORMAT_CHOICE, help="""
Forces the output file format.
By default it is that of the input file.
""")
@click.option('-w', '--width', type=BASED_INT, help="""
Sets the length of the record data field, in bytes.
By default it is that of the input file.
""")
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
def reverse(
    input_format: Optional[str],
    output_format: Optional[str],
    width: Optional[int],
    infile: str,
    outfile: str,
) -> None:
    r"""Reverses data.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    Leave empty to overwrite ``INFILE``.
    """

    with SingleFileInOutCtxMgr(infile, input_format, outfile, output_format, width) as ctx:
        ctx.output_file.reverse()


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=RECORD_FORMAT_CHOICE, help="""
Forces the input file format.
Required for the standard input.
""")
@click.option('-o', '--output-format', type=RECORD_FORMAT_CHOICE, help="""
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
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
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
@click.option('-i', '--input-format', type=RECORD_FORMAT_CHOICE, help="""
Forces the input file format.
Required for the standard input.
""")
@click.argument('infile', type=FILE_PATH_IN)
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
def motorola() -> None:
    """Motorola SREC specific"""


# ----------------------------------------------------------------------------

# noinspection PyShadowingBuiltins
@motorola.command()
@click.option('-f', '--format', 'format', type=DATA_FMT_CHOICE,
              default='ascii', help='Header data format.')
@click.argument('infile', type=FILE_PATH_IN)
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
        text = formatter(records[0].data)
        print(text)


# ----------------------------------------------------------------------------

# noinspection PyShadowingBuiltins
@motorola.command()
@click.option('-f', '--format', 'format', type=DATA_FMT_CHOICE,
              default='ascii', help='Header data format.')
@click.argument('header', type=str)
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
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
    header_data = parser(header)
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
@motorola.command()
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
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
@click.option('-v', '--version', is_flag=True, is_eager=True, expose_value=False,
              callback=print_version, help="""
Prints the package version number.
""")
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
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
    infile: str,
    outfile: str,
) -> None:
    r"""Emulates the xxd command.

    Please refer to the xxd manual page to know its features and caveats.

    Some parameters were changed to satisfy the POSIX-like command line parser.
    """

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
    )
