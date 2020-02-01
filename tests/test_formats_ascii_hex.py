# -*- coding: utf-8 -*-
import os
from pathlib import Path

import pytest

from hexrec.formats.ascii_hex import Record

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

def normalize_whitespace(text):
    return ' '.join(text.split())


def test_normalize_whitespace():
    ans_ref = 'abc def'
    ans_out = normalize_whitespace('abc\tdef')
    assert ans_ref == ans_out


# ============================================================================

def read_text(path):
    path = str(path)
    with open(path, 'rt') as file:
        data = file.read()
    data = data.replace('\r\n', '\n').replace('\r', '\n')  # normalize
    return data


# ============================================================================

class TestRecord:

    def test___init___doctest(self):
        pass  # TODO

    def test___init__(self):
        pass  # TODO

    def test___repr__(self):
        r = Record(0x1234, None, b'Hello, World!', Ellipsis)
        ans_out = normalize_whitespace(repr(r))
        ans_ref = normalize_whitespace('''
        Record(address=0x1234, tag=None, count=13,
               data=b'Hello, World!', checksum=0x0469)
        ''')
        assert ans_out == ans_ref

        r = Record(0x1234, None, None, None)
        ans_out = normalize_whitespace(repr(r))
        ans_ref = normalize_whitespace('''
        Record(address=0x1234, tag=None, count=0,
               data=None, checksum=None)
        ''')
        assert ans_out == ans_ref

        r = Record(None, None, b'Hello, World!', None)
        ans_out = normalize_whitespace(repr(r))
        ans_ref = normalize_whitespace('''
        Record(address=None, tag=None, count=13,
               data=b'Hello, World!', checksum=None)
        ''')
        assert ans_out == ans_ref

        r = Record(None, None, None, Ellipsis)
        ans_out = normalize_whitespace(repr(r))
        ans_ref = normalize_whitespace('''
        Record(address=None, tag=None, count=0,
               data=None, checksum=0x0000)
        ''')
        assert ans_out == ans_ref

    def test___str___doctest(self):
        pass  # TODO

    def test___str__(self):
        pass  # TODO

    def test_compute_count_doctest(self):
        pass  # TODO

    def test_compute_count(self):
        pass  # TODO

    def test_compute_checksum_doctest(self):
        pass  # TODO

    def test_compute_checksum(self):
        pass  # TODO

    def test_check(self):
        record = Record.build_data(0, b'Hello, World!')
        record.count += 1
        record.update_checksum()
        with pytest.raises(ValueError):
            record.check()

        record = Record.build_data(-1, b'Hello, World!')
        with pytest.raises(ValueError):
            record.check()

        record = Record.build_data((1 << 16), b'Hello, World!')
        with pytest.raises(ValueError):
            record.check()

        record = Record.build_data(0, b'Hello, World!')
        record.tag = 1
        with pytest.raises(ValueError):
            record.check()

        record = Record.build_data(0, b'Hello, World!')
        record.data = None
        with pytest.raises(ValueError):
            record.check()
        record.update_count()
        record.check()

        record = Record.build_data(0, BYTES)
        record.check()
        record.count = 1
        with pytest.raises(ValueError):
            record.check()
        record.count = -1
        with pytest.raises(ValueError):
            record.check()
        record.count = 1 << 16
        with pytest.raises(ValueError):
            record.check()

        record = Record.build_data(0, b'Hello, World!')
        record.checksum = None
        record.check()
        record.checksum = -1
        with pytest.raises(ValueError):
            record.check()
        record.checksum = 1 << 16
        with pytest.raises(ValueError):
            record.check()
        record.checksum = 1
        record.check()

    def test_parse_doctest(self):
        pass  # TODO

    def test_parse_record(self):
        with pytest.raises(ValueError):
            Record.parse_record('Hello, World!')

    def test_build_data_doctest(self):
        ans_out = str(Record.build_data(0x1234, b'Hello, World!'))
        ans_ref = '$A1234,48 65 6C 6C 6F 2C 20 57 6F 72 6C 64 21 '
        assert ans_out == ans_ref

        ans_out = str(Record.build_data(None, b'Hello, World!'))
        ans_ref = '48 65 6C 6C 6F 2C 20 57 6F 72 6C 64 21 '
        assert ans_out == ans_ref

        ans_out = str(Record.build_data(0x1234, None))
        ans_ref = '$A1234,'
        assert ans_out == ans_ref

    def test_split(self):
        with pytest.raises(ValueError):
            list(Record.split(BYTES, address=-1))

        with pytest.raises(ValueError):
            list(Record.split(BYTES, address=(1 << 16)))

        with pytest.raises(ValueError):
            list(Record.split(BYTES, address=((1 << 16) - 128)))

        with pytest.raises(ValueError):
            list(Record.split(BYTES, columns=256))

        ans_out = list(Record.split(HEXBYTES))
        ans_ref = [
            Record(0, None, None, None),
            Record(None, None, HEXBYTES, None),
            Record(None, None, None, sum(HEXBYTES)),
        ]
        assert ans_out == ans_ref

        ans_out = list(Record.split(HEXBYTES, standalone=False))
        ans_ref = [
            Record(0, None, HEXBYTES, None),
        ]
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

    def test_build_standalone(self):
        ans_out = list(Record.build_standalone([]))
        ans_ref = [Record(None, None, None, 0)]
        assert ans_out == ans_ref

        data_records = [Record.build_data(0x1234, b'Hello, World!')]
        ans_out = list(Record.build_standalone(data_records))
        ans_ref = [
            Record(0x1234, None, b'Hello, World!'),
            Record(None, None, None, 0x0469),
        ]
        assert ans_out == ans_ref

    def test_check_sequence_doctest(self):
        pass  # TODO

    def test_check_sequence(self):
        records = [
            Record(0x1234, None, b'Hello, World!'),
        ]
        Record.check_sequence(records)

    def test_load_blocks(self, datapath):
        path_ref = datapath / 'bytes.ascii_hex'
        ans_out = list(Record.load_blocks(str(path_ref)))
        ans_ref = [(0, BYTES)]
        assert ans_out == ans_ref

    def test_load_records(self, datapath):
        path_ref = datapath / 'bytes.ascii_hex'
        ans_out = list(Record.load_records(str(path_ref)))
        ans_ref = list(Record.split(BYTES))
        assert ans_out == ans_ref

    def test_save_records(self, tmppath, datapath):
        path_out = tmppath / 'bytes.ascii_hex'
        path_ref = datapath / 'bytes.ascii_hex'
        records = list(Record.split(BYTES))
        Record.save_records(str(path_out), records)
        ans_out = read_text(path_out)
        ans_ref = read_text(path_ref)
        assert ans_out == ans_ref
