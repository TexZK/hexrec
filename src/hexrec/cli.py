"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -mhexrec` python will execute
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


# ----------------------------------------------------------------------------

BASED_INT = BasedIntParamType()

FILE_PATH_IN = click.Path(dir_okay=False, allow_dash=True, readable=True,
                          exists=True)
FILE_PATH_OUT = click.Path(dir_okay=False, allow_dash=True, writable=True)

RECORD_FORMAT_CHOICE = click.Choice(list(six.iterkeys(_RECORD_TYPES)))

# ----------------------------------------------------------------------------


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(str(_version))
    ctx.exit()


# ============================================================================

@click.group()
def main(): pass


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=RECORD_FORMAT_CHOICE)
@click.option('-o', '--output-format', type=RECORD_FORMAT_CHOICE)
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
def convert(input_format, output_format, infile, outfile):
    input_type = _find_record_type(input_format) if input_format else None
    output_type = _find_record_type(output_format) if output_format else None
    _convert_file(infile, outfile,
                  input_type=input_type, output_type=output_type)


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=RECORD_FORMAT_CHOICE)
@click.option('-o', '--output-format', type=RECORD_FORMAT_CHOICE)
@click.argument('infiles', type=FILE_PATH_IN, nargs=-1, required=True)
@click.argument('outfile', type=FILE_PATH_OUT)
def merge(input_format, output_format, infiles, outfile):
    input_type = _find_record_type(input_format) if input_format else None
    output_type = _find_record_type(output_format) if output_format else None
    input_types = [input_type if fn == '-' else None for fn in infiles]
    _merge_files(infiles, outfile,
                 input_types=input_types, output_type=output_type)


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=RECORD_FORMAT_CHOICE)
@click.option('-o', '--output-format', type=RECORD_FORMAT_CHOICE)
@click.argument('start', type=BASED_INT)
@click.argument('endex', type=BASED_INT)
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
def select(input_format, output_format, start, endex, infile, outfile):
    input_type = _find_record_type(input_format) if input_format else None
    output_type = _find_record_type(output_format) if output_format else None
    m = _load_memory(infile, record_type=input_type)
    m = m[start:endex]
    _save_memory(outfile, m, record_type=output_type)


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=RECORD_FORMAT_CHOICE)
@click.option('-o', '--output-format', type=RECORD_FORMAT_CHOICE)
@click.argument('value', type=BASED_INT)
@click.argument('start', type=BASED_INT)
@click.argument('endex', type=BASED_INT)
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
def fill(input_format, output_format, value, start, endex, infile, outfile):
    input_type = _find_record_type(input_format) if input_format else None
    output_type = _find_record_type(output_format) if output_format else None
    m = _load_memory(infile, record_type=input_type)
    m[start:endex] = bytearray([value])
    _save_memory(outfile, m, record_type=output_type)


# ----------------------------------------------------------------------------

@main.command()
@click.option('-i', '--input-format', type=RECORD_FORMAT_CHOICE)
@click.option('-o', '--output-format', type=RECORD_FORMAT_CHOICE)
@click.argument('shift', type=BASED_INT)
@click.argument('infile', type=FILE_PATH_IN)
@click.argument('outfile', type=FILE_PATH_OUT)
def shift(input_format, output_format, shift, infile, outfile):
    input_type = _find_record_type(input_format) if input_format else None
    output_type = _find_record_type(output_format) if output_format else None
    m = _load_memory(infile, record_type=input_type)
    m.shift(shift)
    _save_memory(outfile, m, record_type=output_type)


# ----------------------------------------------------------------------------

@main.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option('-a', '--autoskip', is_flag=True, help="""
Toggles autoskip.

A single '*' replaces null lines.
""")
@click.option('-b', '--bits', is_flag=True, help="""
Binary digits.

Switches to bits (binary digits) dump, rather than
hexdump. This option writes octets as eight digits of '1' and '0'
instead of a normal hexadecimal dump. Each line is preceded by a
line number in hexadecimal and followed by an ASCII (or EBCDIC)
representation.
The argument switches -r, -p, -i do not work with this mode.
""")
@click.option('-c', '--cols', type=BASED_INT, help="""
Formats <cols> octets per line. Max 256.

Defaults: normal 16, -i 12, -p 30, -b 6.
""")
@click.option('-E', '--EBCDIC', is_flag=True, help="""
Uses EBCDIC charset.

Changes the character encoding in the right-hand
column from ASCII to EBCDIC.
This does not change the hexadecimal representation.
The option is meaningless in combinations with -r, -p or -i.
""")
@click.option('-e', '--endian', is_flag=True, help="""
Switches to little-endian hexdump.

This option treats  byte groups as words in little-endian byte order.
The default grouping of 4 bytes may be changed using -g.
This option only applies to hexdump, leaving the ASCII (or EBCDIC)
representation unchanged.
The switches -r, -p, -i do not work with this mode.
""")
@click.option('-g', '--groupsize', type=BASED_INT, help="""
Byte group size.

Separates the output of every <groupsize> bytes (two hex
characters or eight bit-digits each) by a whitespace.
Specify <groupsize> 0 to suppress grouping.
<groupsize> defaults to 2 in normal mode, 4 in little-endian mode and 1
in bits mode. Grouping does not apply to -p or -i.
""")
@click.option('-i', '--include', is_flag=True, help="""
Output in C include file style.

A complete static array definition is written (named after the
input file), unless reading from standard input.
""")
@click.option('-l', '--len', '--length', type=BASED_INT, help="""
Stops after writing <length> octets.
""")
@click.option('-o', '--offset', type=BASED_INT, help="""
Adds <offset> to the displayed file position.
""")
@click.option('-p', '--ps', '--plain', '--postscript', is_flag=True, help="""
Outputs in postscript continuous hexdump style.

Also known as plain hexdump style.
""")
@click.option('-q', '--quadword', is_flag=True, help="""
Uses 64-bit addressing.
""")
@click.option('-r', '--revert', is_flag=True, help="""
Reverse operation.

Convert (or patch) hexdump into binary.
If not writing to standard output, it writes into its
output file without truncating it.
Use the combination -r and -p to read plain hexadecimal dumps
without line number information and without a particular column
layout. Additional Whitespace and line breaks are allowed anywhere.
""")
@click.option('--seek', 'oseek', type=BASED_INT, help="""
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
@click.option('-U', '--upper-all', is_flag=True, help="""
Uses upper case hex letters on address and data.
""")
@click.option('-u', '--upper', is_flag=True, help="""
Uses upper case hex letters on data.
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
