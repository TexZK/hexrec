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

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""
import click
import six

from .__init__ import __version__ as _version
from .records import RECORD_TYPES as _RECORD_TYPES
from .records import convert_file as _convert_file
from .records import find_record_type as _find_record_type
from .records import load_memory as _load_memory
from .records import merge_files as _merge_files
from .records import save_memory as _save_memory
from .utils import parse_int as _parse_int
from .xxd import xxd as _xxd

# ----------------------------------------------------------------------------


class BasedIntParamType(click.ParamType):
    name = 'integer'

    def convert(self, value, param, ctx):
        try:
            return _parse_int(value)
        except ValueError:
            self.fail('%s is not a valid integer' % value, param, ctx)


class ByteIntParamType(click.ParamType):
    name = 'byte'

    def convert(self, value, param, ctx):
        try:
            b = _parse_int(value)
            if not 0 <= b <= 255:
                raise ValueError()
            return b
        except ValueError:
            self.fail('%s is not a valid byte' % value, param, ctx)


BASED_INT = BasedIntParamType()
BYTE_INT = ByteIntParamType()

FILE_PATH_IN = click.Path(dir_okay=False, allow_dash=True, readable=True,
                          exists=True)
FILE_PATH_OUT = click.Path(dir_okay=False, allow_dash=True, writable=True)

RECORD_FORMAT_CHOICE = click.Choice(list(sorted(six.iterkeys(_RECORD_TYPES))))

# ----------------------------------------------------------------------------


def find_types(input_format, output_format, infile, outfile):
    if input_format:
        input_type = _RECORD_TYPES[input_format]
    elif infile == '-':
        raise ValueError('standard input requires input format')
    else:
        input_type = _RECORD_TYPES[_find_record_type(infile)]

    if output_format:
        output_type = _RECORD_TYPES[output_format]
    elif outfile == '-':
        output_type = input_type
    else:
        output_type = _RECORD_TYPES[_find_record_type(outfile)]

    return input_type, output_type


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(str(_version))
    ctx.exit()


# ============================================================================

@click.group()
def main():
    """
    A set of command line utilities for common operations with record files.

    Being built with `Click <https://click.palletsprojects.com/>`_, all the
    commands follow POSIX-like syntax rules, as well as reserving the virtual
    file path ``-`` for command chaining via standard output/input buffering.
    """
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
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
def clear(input_format, output_format, start, endex, infile, outfile):
    r"""Clears an address range.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    """
    input_type, output_type = find_types(input_format, output_format,
                                         infile, outfile)

    m = _load_memory(infile, record_type=input_type)
    m.clear(start, endex)
    _save_memory(outfile, m, record_type=output_type)


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
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
def convert(input_format, output_format, infile, outfile):
    r"""Converts a file to another format.

    ``INFILE`` is the list of paths of the input files.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    """
    input_type, output_type = find_types(input_format, output_format,
                                         infile, outfile)

    _convert_file(infile, outfile,
                  input_type=input_type, output_type=output_type)


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
@click.option('-v', '--value', type=BYTE_INT, help="""
Byte value used to flood the address range.
By default, no flood is performed.
""")
@click.option('-s', '--start', type=BASED_INT, help="""
Inclusive start address. Negative values are referred to the end of the data.
By default it applies from the start of the data contents.
""")
@click.option('-e', '--endex', type=BASED_INT, help="""
Exclusive end address. Negative values are referred to the end of the data.
By default it applies till the end of the data contents.
""")
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
def cut(input_format, output_format, value, start, endex, infile, outfile):
    r"""Selects data from an address range.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    """
    input_type, output_type = find_types(input_format, output_format,
                                         infile, outfile)

    m = _load_memory(infile, record_type=input_type)
    m.cut(start, endex)
    if value is not None:
        m.flood(start, endex, bytes(bytearray([value])))
    _save_memory(outfile, m, record_type=output_type)


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
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
def delete(input_format, output_format, start, endex, infile, outfile):
    r"""Deletes an address range.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    """
    input_type, output_type = find_types(input_format, output_format,
                                         infile, outfile)

    m = _load_memory(infile, record_type=input_type)
    m.delete(start, endex)
    _save_memory(outfile, m, record_type=output_type)


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
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
def fill(input_format, output_format, value, start, endex, infile, outfile):
    r"""Fills an address range with a byte value.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    """
    input_type, output_type = find_types(input_format, output_format,
                                         infile, outfile)

    m = _load_memory(infile, record_type=input_type)
    m.fill(start, endex, bytes(bytearray([value])))
    _save_memory(outfile, m, record_type=output_type)


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
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
def flood(input_format, output_format, value, start, endex, infile, outfile):
    r"""Fills emptiness of an address range with a byte value.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    """
    input_type, output_type = find_types(input_format, output_format,
                                         infile, outfile)

    m = _load_memory(infile, record_type=input_type)
    m.flood(start, endex, bytes(bytearray([value])))
    _save_memory(outfile, m, record_type=output_type)


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
@click.argument('infiles', type=FILE_PATH_IN, nargs=-1, required=True)
@click.argument('outfile', type=FILE_PATH_OUT)
def merge(input_format, output_format, infiles, outfile):
    r"""Merges multiple files.

    ``INFILES`` is the list of paths of the input files.
    Set any to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.

    Every file of ``INFILES`` will overwrite data of previous files of the list
    where addresses overlap.
    """
    for infile in infiles:
        if infile != '-':
            break
    else:
        infile = '-'
    input_type, output_type = find_types(input_format, output_format,
                                         infile, outfile)
    input_types = [input_type] * len(infiles)

    _merge_files(infiles, outfile,
                 input_types=input_types, output_type=output_type)


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
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
def reverse(input_format, output_format, infile, outfile):
    r"""Reverses data.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    """
    input_type, output_type = find_types(input_format, output_format,
                                         infile, outfile)

    m = _load_memory(infile, record_type=input_type)
    m.reverse()
    _save_memory(outfile, m, record_type=output_type)


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
@click.option('-n', '--shift', type=BASED_INT, default=0, help="""
Address shift to apply.
""")
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
def shift(input_format, output_format, shift, infile, outfile):
    r"""Shifts data addresses.

    ``INFILE`` is the path of the input file.
    Set to ``-`` to read from standard input; input format required.

    ``OUTFILE`` is the path of the output file.
    Set to ``-`` to write to standard output.
    """
    input_type, output_type = find_types(input_format, output_format,
                                         infile, outfile)

    m = _load_memory(infile, record_type=input_type)
    m.shift(shift)
    _save_memory(outfile, m, record_type=output_type)


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
@click.option('-v', '--version', is_flag=True, is_eager=True,
              expose_value=False,
              callback=print_version, help="""
Prints the package version number.
""")
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
def xxd(autoskip, bits, cols, ebcdic, endian, groupsize, include, length,
        offset, postscript, quadword, revert, oseek, iseek, upper_all, upper,
        infile, outfile):
    r"""Emulates the xxd command.

    Please refer to the xxd manual page to know its features and caveats.

    Some parameters were changed to satisfy the POSIX-like command line parser.
    """
    _xxd(infile=infile,
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
         upper=upper)
