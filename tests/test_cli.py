# -*- coding: utf-8 -*-
import glob
import os
from pathlib import Path
from typing import List

import pytest
from click.testing import CliRunner

from hexrec.__init__ import __version__ as _version
from hexrec.__main__ import main as _main
from hexrec.cli import *
from hexrec.formats.intel import Record as IntelRecord
from hexrec.formats.motorola import Record as MotorolaRecord

# ============================================================================

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


# ============================================================================

def read_text(path):
    path = str(path)
    with open(path, 'rt') as file:
        data = file.read()
    data = data.replace('\r\n', '\n').replace('\r', '\n')  # normalize
    return data


# ============================================================================

def test_main():
    value = None
    try:
        _main('__main__')
    except SystemExit as e:
        value = str(e)
    assert value == '2'


# ============================================================================

def test_find_types():
    input_type, output_type = find_types(None, None, 'x.mot', 'y.hex')
    assert input_type is MotorolaRecord
    assert output_type is IntelRecord

    match = 'standard input requires input format'
    with pytest.raises(ValueError, match=match):
        find_types(None, None, '-', 'y.hex')

    input_type, output_type = find_types(None, None, 'x.mot', '-')
    assert input_type is MotorolaRecord
    assert output_type is MotorolaRecord

    input_type, output_type = find_types('intel', None, '-', '-')
    assert input_type is IntelRecord
    assert output_type is IntelRecord

    input_type, output_type = find_types('intel', 'motorola', '-', '-')
    assert input_type is IntelRecord
    assert output_type is MotorolaRecord

    input_type, output_type = find_types('intel', 'motorola', 'x.tek', 'y.tek')
    assert input_type is IntelRecord
    assert output_type is MotorolaRecord


# ============================================================================

def test_missing_input_format():
    commands = ('clear', 'convert', 'cut', 'delete', 'fill', 'flood', 'merge',
                'reverse', 'shift')
    match = 'standard input requires input format'
    runner = CliRunner()

    for command in commands:
        result = runner.invoke(main, [command, '-', '-'])
        assert result.exit_code != 0
        assert isinstance(result.exception, ValueError)
        assert match in str(result.exception)


# ============================================================================

def test_help():
    commands = ('clear', 'convert', 'cut', 'delete', 'fill', 'flood', 'merge',
                'reverse', 'shift', 'xxd')
    runner = CliRunner()

    for command in commands:
        result = runner.invoke(main, [command, '--help'])
        assert result.exit_code == 0
        assert result.output.strip().startswith('Usage:')


# ============================================================================

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
        args = args[:-1] + [str(path_in), str(path_out)]

        runner = CliRunner()
        runner.invoke(main, args)

        ans_out = read_text(path_out)
        ans_ref = read_text(path_ref)
        # if ans_out != ans_ref: raise AssertionError(str(path_ref))
        assert ans_out == ans_ref


# ============================================================================

def test_fill_parse_byte_fail():
    runner = CliRunner()
    result = runner.invoke(main, 'fill -v 256 - -'.split())

    assert result.exit_code == 2
    assert '256 is not a valid byte' in result.output


# ============================================================================

def test_merge_nothing():
    runner = CliRunner()
    result = runner.invoke(main, 'merge -i binary - -'.split())

    assert result.exit_code == 0
    assert result.output == ''


# ============================================================================

def test_xxd_version():
    runner = CliRunner()
    result = runner.invoke(main, 'xxd -v'.split())

    assert result.exit_code == 0
    assert result.output.strip() == str(_version)


# ----------------------------------------------------------------------------

def test_xxd_empty():
    runner = CliRunner()
    result = runner.invoke(main, 'xxd - -'.split())

    assert result.exit_code == 0
    assert result.output == ''


# ----------------------------------------------------------------------------

def test_xxd_parse_int_pass():
    runner = CliRunner()
    result = runner.invoke(main, 'xxd -c 0x10 - -'.split())

    assert result.exit_code == 0
    assert result.output == ''


# ----------------------------------------------------------------------------

def test_xxd_parse_int_fail():
    runner = CliRunner()
    result = runner.invoke(main, 'xxd -c ? - -'.split())

    assert result.exit_code == 2
    assert '? is not a valid integer' in result.output
