# -*- coding: utf-8 -*-
import glob
import os
from distutils import dir_util
from pathlib import Path

import pytest
import six

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
