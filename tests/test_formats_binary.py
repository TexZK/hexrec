# -*- coding: utf-8 -*-
import os
from pathlib import Path

import pytest

from hexrec.formats.binary import Record

BYTES = bytes(range(256))
HEXBYTES = bytes(range(16))


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

class TestRecord:

    def test_build_data_doctest(self):
        record = Record.build_data(0x1234, b'Hello, World!')
        ans_out = normalize_whitespace(repr(record))
        ans_ref = normalize_whitespace('''
        Record(address=0x00001234, tag=None, count=13,
               data=b'Hello, World!', checksum=0x69)
        ''')
        assert ans_out == ans_ref

    def test_parse_doctest(self):
        line = '48656C6C 6F2C2057 6F726C64 21'
        record = Record.parse_record(line)
        ans_out = normalize_whitespace(repr(record))
        ans_ref = normalize_whitespace('''
        Record(address=0x00000000, tag=None, count=13,
               data=b'Hello, World!', checksum=0x69)
        ''')
        assert ans_out == ans_ref

    def test_is_data(self):
        assert Record.build_data(0, b'').is_data()

    def test_check(self):
        with pytest.raises(ValueError):
            Record(-1, None, b'Hello, World!').check()

        record = Record(0, None, b'')
        record.data = None
        with pytest.raises(ValueError):
            record.check()

        record = Record(0, None, b'Hello, World!')
        record.checksum = None
        record.check()

        record = Record(0, None, b'Hello, World!')
        record.checksum = -1
        with pytest.raises(ValueError):
            record.check()

        record = Record(0, None, b'Hello, World!')
        record.checksum = 256
        with pytest.raises(ValueError):
            record.check()

        record = Record(0, None, b'')
        record.checksum ^= 0xFF
        with pytest.raises(ValueError):
            record.check()

        record = Record(0, None, b'')
        record.tag = -1
        with pytest.raises(ValueError):
            record.check()

        record = Record(0, None, b'')
        record.count = -1
        with pytest.raises(ValueError):
            record.check()

    def test_split(self):
        with pytest.raises(ValueError):
            list(Record.split(b'', -1))

        with pytest.raises(ValueError):
            list(Record.split(b'', 1 << 32))

        with pytest.raises(ValueError):
            list(Record.split(b'abc', (1 << 32) - 1))

        ans_out = list(Record.split(BYTES))
        ans_ref = [Record.build_data(0, BYTES)]
        assert ans_out == ans_ref

        ans_out = list(Record.split(BYTES, columns=8))
        ans_ref = [Record.build_data(offset, BYTES[offset:(offset + 8)])
                   for offset in range(0, 256, 8)]
        assert ans_out == ans_ref

        ans_out = list(Record.split(HEXBYTES, standalone=False,
                                    address=7, columns=5, align=3))
        ans_ref = [
            Record.build_data(7, HEXBYTES[:4]),
            Record.build_data(11, HEXBYTES[4:9]),
            Record.build_data(16, HEXBYTES[9:14]),
            Record.build_data(21, HEXBYTES[14:]),
        ]
        assert ans_out == ans_ref

    def test_load_records(self, datapath):
        path_ref = datapath / 'hexbytes.bin'
        ans_out = list(Record.load_records(str(path_ref)))
        ans_ref = [Record.build_data(0, HEXBYTES)]
        assert ans_out == ans_ref

    def test_save_records(self, tmppath, datapath):
        path_out = tmppath / 'hexbytes.bin'
        path_ref = datapath / 'hexbytes.bin'
        records = [Record.build_data(0, HEXBYTES)]
        Record.save_records(str(path_out), records)
        ans_out = read_text(path_out)
        ans_ref = read_text(path_ref)
        assert ans_out == ans_ref
