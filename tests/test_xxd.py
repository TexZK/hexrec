import glob
import io
import os
import shutil
import sys
from pathlib import Path
from typing import Any
from typing import cast as _cast

import pytest
from click.testing import CliRunner
from test_base import replace_stdin
from test_base import replace_stdout

from hexrec.cli import main as cli_main
from hexrec.xxd import ZERO_BLOCK_SIZE
from hexrec.xxd import parse_seek
from hexrec.xxd import xxd_core


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


def read_bytes(path):
    path = str(path)
    with open(path, 'rb') as file:
        data = file.read()
    return data


def normalize_whitespace(text):
    return ' '.join(text.split())


def test_normalize_whitespace():
    ans_ref = 'abc def'
    ans_out = normalize_whitespace('abc\tdef')
    assert ans_ref == ans_out


def test_parse_seek():
    assert parse_seek(None) == ('', 0)


def test_by_filename_text(tmppath, datapath):
    prefix = 'test_xxd_'
    test_filenames = glob.glob(str(datapath / (prefix + '*.c')))
    test_filenames += glob.glob(str(datapath / (prefix + '*.hexstr')))
    test_filenames += glob.glob(str(datapath / (prefix + '*.mot')))
    test_filenames += glob.glob(str(datapath / (prefix + '*.xxd')))

    for filename in test_filenames:
        filename = os.path.basename(filename)
        print('@', filename, file=sys.stderr)
        path_out = tmppath / filename
        path_ref = datapath / filename

        cmdline = filename[len(prefix):].replace('_', ' ')
        args = cmdline.split()
        path_in = datapath / os.path.splitext(args[-1])[0]
        args = ['xxd'] + args[:-1] + [str(path_in), str(path_out)]

        runner = CliRunner()
        result = runner.invoke(_cast(Any, cli_main), args)
        assert result.exit_code == 0

        ans_out = read_text(path_out)
        ans_ref = read_text(path_ref)
        # if ans_out != ans_ref: raise AssertionError(str(path_ref))
        assert ans_out == ans_ref


def test_by_filename_bytes(tmppath, datapath):
    copy_filenames = [
        (r'xxd.1', r'test_xxd_-r_xxd.1.patch.xxd.bin'),
    ]
    for path_ref, path_out in copy_filenames:
        path_ref = str(datapath / path_ref)
        path_out = str(tmppath / path_out)
        shutil.copy(path_ref, path_out)

    prefix = 'test_xxd_'
    test_filenames = glob.glob(str(datapath / (prefix + '*.bin')))

    for filename in test_filenames:
        filename = os.path.basename(filename)
        print('@', filename, file=sys.stderr)
        path_out = tmppath / filename
        path_ref = datapath / filename

        cmdline = filename[len(prefix):].replace('_', ' ')
        args = cmdline.split()
        path_in = datapath / os.path.splitext(args[-1])[0]
        args = ['xxd'] + args[:-1] + [str(path_in), str(path_out)]

        runner = CliRunner()
        result = runner.invoke(_cast(Any, cli_main), args)
        assert result.exit_code == 0

        ans_out = read_bytes(path_out)
        ans_ref = read_bytes(path_ref)
        # if ans_out != ans_ref: raise AssertionError(str(path_ref))
        assert ans_out == ans_ref


def test_xxd(datapath):
    with open(str(datapath / 'bytes.bin'), 'rb') as stream:
        data_in = memoryview(stream.read())

    with pytest.raises(ValueError, match='invalid column count'):
        xxd_core(cols=-1)

    with pytest.raises(ValueError, match='invalid column count'):
        xxd_core(cols=257)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd_core(bits=True, postscript=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd_core(bits=True, include=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd_core(bits=True, revert=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd_core(endian=True, postscript=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd_core(endian=True, include=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd_core(endian=True, revert=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd_core(postscript=True, include=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd_core(postscript=True, bits=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd_core(include=True, bits=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd_core(revert=False, oseek=0)

    with pytest.raises(ValueError, match='invalid seeking'):
        xxd_core(revert=True, oseek=-1)

    with pytest.raises(ValueError, match='invalid syntax'):
        xxd_core(data_in, iseek='invalid')

    with pytest.raises(ValueError, match='invalid seeking'):
        xxd_core(data_in, iseek='+')

    with pytest.raises(ValueError, match='invalid grouping'):
        xxd_core(data_in, groupsize=-1)

    with pytest.raises(ValueError, match='invalid grouping'):
        xxd_core(data_in, groupsize=257)

    with pytest.raises(ValueError, match='offset overflow'):
        xxd_core(data_in, offset=-1)

    with pytest.raises(ValueError, match='offset overflow'):
        xxd_core(data_in, offset=(1 << 32))


def test_xxd_stdinout(datapath):
    with open(str(datapath / 'bytes.bin'), 'rb') as stream:
        data_in = stream.read()
    stream_in = io.BytesIO(data_in)
    stream_out = io.BytesIO()

    with replace_stdin(stream_in), replace_stdout(stream_out):
        xxd_core()

    with open(str(datapath / 'test_xxd_bytes.bin.xxd'), 'rb') as stream:
        text_ref = stream.read().replace(b'\r\n', b'\n')

    text_out = stream_out.getvalue().replace(b'\r\n', b'\n')
    assert text_out == text_ref


def test_xxd_bytes(datapath):
    with open(str(datapath / 'bytes.bin'), 'rb') as stream:
        data_in = stream.read()
    text_out = io.BytesIO()

    xxd_core(data_in, text_out)

    with open(str(datapath / 'test_xxd_bytes.bin.xxd'), 'rb') as stream:
        text_ref = stream.read().replace(b'\r\n', b'\n')

    text_out = text_out.getvalue().replace(b'\r\n', b'\n')
    assert text_out == text_ref


def test_xxd_bytes_seek(datapath):
    with open(str(datapath / 'bytes.bin'), 'rb') as stream:
        data_in = stream.read()
    stream_in = io.BytesIO(data_in)
    stream_out = io.BytesIO()

    with replace_stdin(stream_in), replace_stdout(stream_out):
        sys.stdin.buffer.seek(96, io.SEEK_CUR)
        xxd_core(iseek='+-64')

    filename = 'test_xxd_-s_32_bytes.bin.xxd'
    with open(str(datapath / filename), 'rb') as stream:
        text_ref = stream.read().replace(b'\r\n', b'\n')

    text_out = stream_out.getvalue().replace(b'\r\n', b'\n')
    assert text_out == text_ref


def test_xxd_include_stdin(datapath):
    with open(str(datapath / 'bytes.bin'), 'rb') as stream:
        data_in = stream.read()
    text_out = io.BytesIO()

    xxd_core(data_in, text_out, include=True)

    with open(str(datapath / 'bytes-stdin.c'), 'rb') as stream:
        text_ref = stream.read().replace(b'\r\n', b'\n')
    text_out = text_out.getvalue().replace(b'\r\n', b'\n')

    assert text_out == text_ref


def test_xxd_include_stdin_cli(tmppath, datapath):
    filename = 'xxd_-i_STDIN_file.c'
    path_out = tmppath / filename
    path_ref = datapath / filename
    path_in = datapath / 'file'

    args = 'xxd -i - '.split() + [str(path_out)]

    runner = CliRunner()
    data_in = read_bytes(path_in)
    result = runner.invoke(_cast(Any, cli_main), args, input=data_in)
    assert result.exit_code == 0

    ans_out = read_text(path_out)
    ans_ref = read_text(path_ref)
    assert ans_out == ans_ref


def test_xxd_none(datapath):
    with open(str(datapath / 'test_xxd_bytes.bin.xxd'), 'rb') as stream:
        text_ref = stream.read().replace(b'\r\n', b'\n')

    fake_stdout = io.BytesIO()
    with replace_stdout(fake_stdout):
        with open(str(datapath / 'bytes.bin'), 'rb') as stream_in:
            xxd_core(stream_in, linesep=b'\n')

    text_out = fake_stdout.getvalue()
    assert text_out == text_ref


def test_xxd_none_revert(datapath):
    with open(str(datapath / 'bytes.bin'), 'rb') as stream:
        data_ref = stream.read()

    fake_stdout = io.BytesIO()
    with replace_stdout(fake_stdout):
        with open(str(datapath / 'bytes.xxd'), 'rb') as stream_in:
            xxd_core(stream_in, revert=True)

    data_out = fake_stdout.getvalue()
    assert data_out == data_ref


def test_xxd_none_revert_oseek(datapath):
    skip = (ZERO_BLOCK_SIZE * 2) + (ZERO_BLOCK_SIZE // 4)
    data_in = b'ABCD'

    stream_in = io.BytesIO(data_in)
    stream_out = io.BytesIO()
    xxd_core(stream_in, stream_out)
    xxd_in = stream_out.getvalue()

    stream_in = io.BytesIO(xxd_in)
    stream_out = io.BytesIO()
    xxd_core(stream_in, stream_out, oseek=skip, revert=True)

    data_out = stream_out.getvalue()
    data_ref = (b'\0' * skip) + data_in
    assert data_out == data_ref


def test_xxd_none_revert_offset(datapath):
    skip = (ZERO_BLOCK_SIZE * 2) + (ZERO_BLOCK_SIZE // 4)
    data_in = b'ABCD'

    stream_in = io.BytesIO(data_in)
    stream_out = io.BytesIO()
    xxd_core(stream_in, stream_out, offset=skip)
    xxd_in = stream_out.getvalue()

    stream_in = io.BytesIO(xxd_in)
    stream_out = io.BytesIO()
    xxd_core(stream_in, stream_out, revert=True)

    data_out = stream_out.getvalue()
    data_ref = (b'\0' * skip) + data_in
    assert data_out == data_ref
