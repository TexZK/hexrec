import glob
import io
import os
from pathlib import Path
from typing import Any
from typing import cast as _cast

import pytest
from click.testing import CliRunner
from test_base import replace_stdin
from test_base import replace_stdout

from hexrec.cli import main as cli_main
from hexrec.hexdump import hexdump_core


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


def test_by_filename_hexdump(tmppath, datapath):
    prefix = 'test_hexdump_'
    test_filenames = glob.glob(str(datapath / (prefix + '*.hexdump')))

    for filename in test_filenames:
        filename = os.path.basename(filename)
        print(filename)
        path_out = tmppath / filename
        path_ref = datapath / filename

        cmdline = filename[len(prefix):].replace('_', ' ')
        args = cmdline.split()
        path_in = datapath / os.path.splitext(args[-1])[0]
        args = ['hexdump'] + args[:-1] + [str(path_in)]

        runner = CliRunner()
        result = runner.invoke(_cast(Any, cli_main), args)

        ans_out = result.output
        with open(str(path_out), 'wt') as f:
            f.write(ans_out)
        ans_ref = read_text(path_ref)
        # if ans_out != ans_ref: raise AssertionError(str(path_ref))
        assert ans_out == ans_ref


def test_by_filename_hd(tmppath, datapath):
    prefix = 'test_hd_'
    test_filenames = glob.glob(str(datapath / (prefix + '*.hd')))

    for filename in test_filenames:
        filename = os.path.basename(filename)
        print(filename)
        path_out = tmppath / filename
        path_ref = datapath / filename

        cmdline = filename[len(prefix):].replace('_', ' ')
        args = cmdline.split()
        path_in = datapath / os.path.splitext(args[-1])[0]
        args = ['hd'] + args[:-1] + [str(path_in)]

        runner = CliRunner()
        result = runner.invoke(_cast(Any, cli_main), args)

        ans_out = result.output
        with open(str(path_out), 'wt') as f:
            f.write(ans_out)
        ans_ref = read_text(path_ref)
        # if ans_out != ans_ref: raise AssertionError(str(path_ref))
        assert ans_out == ans_ref


def test_hexdump_io(datapath):
    with open(str(datapath / 'bytes.bin'), 'rb') as stream:
        data_in = stream.read()
    text_out = io.BytesIO()

    hexdump_core(data_in, text_out)

    text_out = text_out.getvalue().replace(b'\r\n', b'\n').decode()
    text_ref = read_text(str(datapath / 'test_hexdump_bytes.bin.hexdump'))
    assert text_out == text_ref


def test_hexdump_raises(datapath, tmppath):
    with open(str(datapath / 'bytes.bin'), 'rb') as stream:
        data_in = memoryview(stream.read())

    with pytest.raises(NotImplementedError, match='"color" option is not supported'):
        hexdump_core(data_in, color='')

    with pytest.raises(NotImplementedError, match='"format" option is not supported'):
        hexdump_core(data_in, format='')

    with pytest.raises(NotImplementedError, match='"format_file" option is not supported'):
        hexdump_core(data_in, format_file='')

    with pytest.raises(ValueError, match='negative skip'):
        hexdump_core(data_in, skip=-1)

    with pytest.raises(ValueError, match='negative length'):
        hexdump_core(data_in, length=-1)

    with pytest.raises(ValueError, match='invalid width'):
        hexdump_core(data_in, width=0)

    with pytest.raises(ValueError, match='unknown format option'):
        hexdump_core(data_in, format_order=['(this is a non-existing format)'])


def test_hexdump_stdin_stdout(datapath):
    with open(str(datapath / 'bytes.bin'), 'rb') as stream:
        data_in = stream.read()
    fake_stdin = io.BytesIO(data_in)
    fake_stdout = io.BytesIO()

    with replace_stdin(fake_stdin), replace_stdout(fake_stdout):
        hexdump_core(linesep=b'\n')

    text_out = fake_stdout.getvalue().decode()
    text_ref = read_text(str(datapath / 'test_hexdump_bytes.bin.hexdump'))
    assert text_out == text_ref


def test_hexdump_str(datapath, tmppath):
    with open(str(datapath / 'bytes.bin'), 'rb') as stream:
        data_in = stream.read()
    path_out = str(tmppath / 'test_hexdump_str.hexdump')

    hexdump_core(data_in, path_out)

    text_out = read_text(path_out)
    text_ref = read_text(str(datapath / 'test_hexdump_bytes.bin.hexdump'))
    assert text_out == text_ref


def test_hexdump_stream(datapath):
    fake_stdout = io.BytesIO()
    with replace_stdout(fake_stdout):
        with open(str(datapath / 'bytes.bin'), 'rb') as stream_in:
            hexdump_core(stream_in, linesep=b'\n')

    text_out = fake_stdout.getvalue().decode()
    text_ref = read_text(str(datapath / 'test_hexdump_bytes.bin.hexdump'))
    assert text_out == text_ref
