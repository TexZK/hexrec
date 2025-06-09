import glob
import os
from pathlib import Path
from typing import cast as _cast

import pytest
from click.core import Command
from click.testing import CliRunner

from hexrec import IhexFile
from hexrec import SrecFile
from hexrec import __version__ as _version
from hexrec.__main__ import main as _main
from hexrec.cli import *

main = _cast(Command, main)  # suppress warnings


@pytest.fixture
def tmppath(tmpdir):
    return Path(str(tmpdir))


@pytest.fixture(scope='module')
def datadir(request):
    dir_path, _ = os.path.splitext(request.module.__file__)
    assert os.path.isdir(str(dir_path))
    return dir_path


@pytest.fixture
def datapath(datadir):
    return Path(str(datadir))


def read_text(path):
    path = str(path)
    with open(path, 'rt') as file:
        data = file.read()
    data = data.replace('\r\n', '\n').replace('\r', '\n')  # normalize
    return data


class TestSingleFileInOutCtxMgr:

    def test___init__(self):
        ctx = SingleFileInOutCtxMgr('in.mot', 'srec', 'out.hex', 'ihex', 33)
        assert ctx.input_path == 'in.mot'
        assert ctx.input_format == 'srec'
        assert ctx.output_path == 'out.hex'
        assert ctx.output_format == 'ihex'
        assert ctx.output_width == 33

    def test___init__no_out(self):
        ctx = SingleFileInOutCtxMgr('in.mot', 'srec', '', 'ihex', 33)
        assert ctx.input_path == 'in.mot'
        assert ctx.input_format == 'srec'
        assert ctx.output_path == 'in.mot'
        assert ctx.output_format == 'ihex'
        assert ctx.output_width == 33


class TestMultiFileInOutCtxMgr:

    def test___init__(self):
        ctx = MultiFileInOutCtxMgr(['in.mot'], ['srec'], 'out.hex', 'ihex', 33)
        assert ctx.input_paths == ['in.mot']
        assert ctx.input_formats == ['srec']
        assert ctx.output_path == 'out.hex'
        assert ctx.output_format == 'ihex'
        assert ctx.output_width == 33

    def test___init__no_out(self):
        ctx = MultiFileInOutCtxMgr(['in.mot'], ['srec'], '', 'ihex', 33)
        assert ctx.input_paths == ['in.mot']
        assert ctx.input_formats == ['srec']
        assert ctx.output_path == 'in.mot'
        assert ctx.output_format == 'ihex'
        assert ctx.output_width == 33


def test_main():
    try:
        _main('__main__')
    except SystemExit:
        pass


def test_guess_input_type():
    assert guess_input_type('x.mot') is SrecFile
    assert guess_input_type('-', 'ihex') is IhexFile
    assert guess_input_type('x.tek', 'ihex') is IhexFile

    match = 'standard input requires input format'
    with pytest.raises(ValueError, match=match):
        guess_input_type('-')


def test_guess_output_type():
    assert guess_output_type('y.mot') is SrecFile
    assert guess_output_type('-', 'ihex') is IhexFile
    assert guess_output_type('y.tek', 'ihex') is IhexFile


def test_missing_input_format():
    commands = ('clear', 'convert', 'crop', 'delete', 'fill', 'flood', 'merge',
                'shift')
    match = 'standard input requires input format'
    runner = CliRunner()

    for command in commands:
        result = runner.invoke(main, [command, '-', '-'])
        assert result.exit_code != 0
        assert isinstance(result.exception, ValueError)
        assert match in str(result.exception)


def test_help():
    commands = ('clear', 'convert', 'crop', 'delete', 'fill', 'flood', 'merge',
                'shift', 'xxd')
    runner = CliRunner()

    for command in commands:
        result = runner.invoke(main, [command, '--help'])
        assert result.exit_code == 0
        assert result.output.strip().startswith('Usage:')


def test_by_filename(tmppath, datapath):
    prefix = 'test_hexrec_'
    test_filenames: List[str] = glob.glob(str(datapath / (prefix + '*')))

    for filename in test_filenames:
        filename = os.path.basename(str(filename))
        path_out = str(tmppath / filename)
        path_ref = str(datapath / filename)

        cmdline = filename[len(prefix):].replace('_', ' ')
        args: List[str] = cmdline.split()
        path_in = str(datapath / args[-1])
        args = args[:-1] + [path_in, path_out]

        runner = CliRunner()
        runner.invoke(main, args, catch_exceptions=False)

        ans_out = read_text(path_out)
        ans_ref = read_text(path_ref)
        assert ans_out == ans_ref, filename


def test_fill_parse_byte_fail():
    runner = CliRunner()
    result = runner.invoke(main, 'fill -v 256 - -'.split())
    assert result.exit_code == 2
    assert "invalid byte: '256'" in result.output


def test_merge_nothing():
    runner = CliRunner()
    result = runner.invoke(main, 'merge -i raw -'.split())
    assert result.exit_code == 0
    assert result.output == ''


def test_merge_multi(datapath, tmppath):
    runner = CliRunner()
    path_ins = [str(datapath / 'reversed.mot'),
                str(datapath / 'holes.mot')]
    path_out = str(tmppath / 'test_merge_multi.hex')
    args = ['merge'] + path_ins + [path_out]
    result = runner.invoke(main, args)
    assert result.exit_code == 0
    assert result.output == ''

    path_ref = str(datapath / 'merge_reversed_holes.hex')
    ans_out = read_text(path_out)
    ans_ref = read_text(path_ref)
    assert ans_out == ans_ref


def test_validate(datapath):
    runner = CliRunner()
    path_in = str(datapath / 'bytes.mot')
    result = runner.invoke(main, f'validate {path_in}'.split())
    assert result.exit_code == 0
    assert result.output == ''


def test_srec_dummy(datapath):
    runner = CliRunner()
    result = runner.invoke(main, f'srec -h'.split())
    assert result.exit_code == 2


def test_srec_get_header_headless(datapath):
    runner = CliRunner()
    path_in = str(datapath / 'headless.mot')
    result = runner.invoke(main, f'srec get-header {path_in}'.split())
    assert result.exit_code == 0
    assert result.output == ''


def test_srec_get_header_empty(datapath):
    runner = CliRunner()
    path_in = str(datapath / 'bytes.mot')
    result = runner.invoke(main, f'srec get-header {path_in}'.split())
    assert result.exit_code == 0
    assert result.output == '\n'


def test_srec_get_header_ascii(datapath):
    runner = CliRunner()
    path_in = str(datapath / 'header.mot')
    result = runner.invoke(main, f'srec get-header -f ascii {path_in}'.split())
    assert result.exit_code == 0
    assert result.output == 'ABC\n'


def test_srec_get_header_hex(datapath):
    runner = CliRunner()
    path_in = str(datapath / 'header.mot')
    result = runner.invoke(main, f'srec get-header -f hex {path_in}'.split())
    assert result.exit_code == 0
    assert result.output == '414243\n'


def test_hexdump_version():
    expected = f'hexdump from Python hexrec {_version!s}'
    runner = CliRunner()
    result = runner.invoke(main, 'hexdump --version'.split())
    assert result.exit_code == 0
    assert result.output.strip() == expected

    runner = CliRunner()
    result = runner.invoke(main, 'hexdump -V'.split())
    assert result.exit_code == 0
    assert result.output.strip() == expected


def test_hd_version():
    expected = f'hexdump from Python hexrec {_version!s}'
    runner = CliRunner()
    result = runner.invoke(main, 'hd --version'.split())
    assert result.exit_code == 0
    assert result.output.strip() == expected

    runner = CliRunner()
    result = runner.invoke(main, 'hd -V'.split())
    assert result.exit_code == 0
    assert result.output.strip() == expected


def test_xxd_version():
    expected = f'{_version!s}'
    runner = CliRunner()
    result = runner.invoke(main, 'xxd --version'.split())
    assert result.exit_code == 0
    assert result.output.strip() == expected

    runner = CliRunner()
    result = runner.invoke(main, 'xxd -v'.split())
    assert result.exit_code == 0
    assert result.output.strip() == expected


def test_xxd_empty():
    runner = CliRunner()
    result = runner.invoke(main, 'xxd - -'.split())
    assert result.exit_code == 0
    assert result.output == ''


def test_xxd_parse_int_pass():
    runner = CliRunner()
    result = runner.invoke(main, 'xxd -c 0x10 - -'.split())
    assert result.exit_code == 0
    assert result.output == ''


def test_xxd_parse_int_fail():
    runner = CliRunner()
    result = runner.invoke(main, 'xxd -c ? - -'.split())
    assert result.exit_code == 2
    assert "invalid integer: '?'" in result.output
