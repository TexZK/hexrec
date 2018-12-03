# -*- coding: utf-8 -*-
import glob
import io
import os
import sys
from distutils import dir_util
from pathlib import Path

import pytest

from hexrec.xxd import *

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

def read_bytes(path):
    path = str(path)
    with open(path, 'rb') as file:
        data = file.read()
    return data

# ============================================================================

def normalize_whitespace(text):
    return ' '.join(text.split())


def test_normalize_whitespace():
    ans_ref = 'abc def'
    ans_out = normalize_whitespace('abc\tdef')
    assert ans_ref == ans_out

# ============================================================================

def test_by_filename_xxd(tmppath, datapath):
    prefix = 'test_xxd_'
    test_filenames = glob.glob(str(datapath / (prefix + '*.xxd')))

    for filename in test_filenames:
        filename = os.path.basename(filename)
        path_out = tmppath / filename
        path_ref = datapath / filename

        cmdline = filename[len(prefix):].replace('_', ' ')
        args = cmdline.split()
        path_in = datapath / os.path.splitext(args[-1])[0]
        args = args[:-1] + [str(path_in), str(path_out)]

        main(args)

        ans_out = read_text(path_out)
        ans_ref = read_text(path_ref)
        if ans_out != ans_ref: raise AssertionError(str(path_ref))
        assert ans_out == ans_ref


def test_by_filename_bin(tmppath, datapath):
    prefix = 'test_xxd_'
    test_filenames = glob.glob(str(datapath / (prefix + '*.bin')))

    for filename in test_filenames:
        filename = os.path.basename(filename)
        path_out = tmppath / filename
        path_ref = datapath / filename

        cmdline = filename[len(prefix):].replace('_', ' ')
        args = cmdline.split()
        path_in = datapath / os.path.splitext(args[-1])[0]
        args = args[:-1] + [str(path_in), str(path_out)]

        print(args)
        main(args)

        ans_out = read_bytes(path_out)
        ans_ref = read_bytes(path_ref)
        if ans_out != ans_ref: raise AssertionError(str(path_ref))
        assert ans_out == ans_ref


def test_help():
    main(['-h'])


def test_xxd(datapath):
    with open(str(datapath / 'bytes.bin'), 'rb') as stream:
        data_in = memoryview(stream.read())

    with pytest.raises(ValueError, match='invalid column count'):
        xxd(c=-1)

    with pytest.raises(ValueError, match='invalid column count'):
        xxd(c=257)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd(b=True, p=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd(b=True, i=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd(b=True, r=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd(e=True, p=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd(e=True, i=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd(e=True, r=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd(p=True, i=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd(p=True, b=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd(i=True, b=True)

    with pytest.raises(ValueError, match='incompatible options'):
        xxd(r=False, seek=0)

    with pytest.raises(ValueError, match='invalid seeking'):
        xxd(r=True, seek=-1)

    with pytest.raises(ValueError, match='invalid syntax'):
        xxd(data_in, s='invalid')

    with pytest.raises(ValueError, match='invalid seeking'):
        xxd(data_in, s='', ss='+')

    with pytest.raises(ValueError, match='invalid grouping'):
        xxd(data_in, g=-1)

    with pytest.raises(ValueError, match='invalid grouping'):
        xxd(data_in, g=257)

    with pytest.raises(ValueError, match='offset overflow'):
        xxd(data_in, o=-1)

    with pytest.raises(ValueError, match='offset overflow'):
        xxd(data_in, o=(1 << 32))


def test_xxd_stdinout(datapath):
    stdin_backup = sys.stdin
    stdout_backup = sys.stdout
    text_out = None
    text_ref = None

    try:
        with open(str(datapath / 'bytes.bin'), 'rb') as stream:
            data_in = memoryview(stream.read())
        sys.stdin = io.BytesIO(data_in)
        sys.stdout = io.StringIO()

        xxd()

        with open(str(datapath / 'test_xxd_bytes.bin.xxd'), 'rt') as stream:
            text_ref = stream.read().replace('\r\n', '\n')
        text_out = sys.stdout.getvalue().replace('\r\n', '\n')

    finally:
        sys.stdin = stdin_backup
        sys.stdout = stdout_backup

    assert text_out == text_ref


def test_xxd_bytes(datapath):
    with open(str(datapath / 'bytes.bin'), 'rb') as stream:
        data_in = memoryview(stream.read())
    text_out = io.StringIO()

    xxd(data_in, text_out)

    with open(str(datapath / 'test_xxd_bytes.bin.xxd'), 'rt') as stream:
        text_ref = stream.read().replace('\r\n', '\n')
    text_out = text_out.getvalue().replace('\r\n', '\n')

    assert text_out == text_ref


def test_xxd_ellipsis(datapath):
    with open(str(datapath / 'bytes.bin'), 'rb') as stream_in:
        text_out = Ellipsis

        xxd(stream_in, text_out)
