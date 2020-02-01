# -*- coding: utf-8 -*-
import os
from pathlib import Path

import pytest

from hexrec.formats.tektronix import Record
from hexrec.formats.tektronix import Tag

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

class TestTag:

    def test_is_data(self):
        DATA_INTS = {6}
        for tag in Tag:
            assert Tag.is_data(tag) == (tag in DATA_INTS)
            assert Tag.is_data(int(tag)) == (tag in DATA_INTS)


# ============================================================================

class TestRecord:

    def test___init___doctest(self):
        pass  # TODO

    def test___init__(self):
        pass  # TODO

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
        record = Record.build_terminator(0)
        record.data = b'Hello, World!'
        record.update_count()
        record.update_checksum()
        with pytest.raises(ValueError): record.check()

        record = Record.build_data(0, b'Hello, World!')
        record.count += 1
        record.update_checksum()
        with pytest.raises(ValueError): record.check()

        record = Record.build_data(0, b'Hello, World!')
        record.check()
        for tag in range(256):
            if tag not in (6, 8):
                record.tag = tag
                with pytest.raises(ValueError): record.check()

    def test_parse_doctest(self):
        pass  # TODO

    def test_parse_record(self):
        with pytest.raises(ValueError):
            Record.parse_record('Hello, World!')

        with pytest.raises(ValueError, match='count error'):
            Record.parse_record('%336E081234567848656C6C6F2C20576F726C6421')

    def test_build_data_doctest(self):
        ans_out = str(Record.build_data(0x12345678, b'Hello, World!'))
        ans_ref = '%236E081234567848656C6C6F2C20576F726C6421'
        assert ans_out == ans_ref

    def test_build_terminator_doctest(self):
        ans_out = str(Record.build_terminator(0x12345678))
        ans_ref = '%0983D812345678'
        assert ans_out == ans_ref

    def test_split(self):
        with pytest.raises(ValueError):
            list(Record.split(BYTES, address=-1))

        with pytest.raises(ValueError):
            list(Record.split(BYTES, address=(1 << 32)))

        with pytest.raises(ValueError):
            list(Record.split(BYTES, address=((1 << 32) - 128)))

        with pytest.raises(ValueError):
            list(Record.split(BYTES, columns=129))

        ans_out = list(Record.split(HEXBYTES))
        ans_ref = [
            Record(0, Tag.DATA, HEXBYTES),
            Record(0, Tag.TERMINATOR, b''),
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
        ans_out = list(Record.build_standalone([], start=0))
        ans_ref = [Record(0, Tag.TERMINATOR, b'')]
        assert ans_out == ans_ref

        ans_out = list(Record.build_standalone([]))
        ans_ref = [Record(0, Tag.TERMINATOR, b'')]
        assert ans_out == ans_ref

        data_records = [Record.build_data(0x1234, b'Hello, World!')]
        ans_out = list(Record.build_standalone(data_records))
        ans_ref = [
            Record(0x1234, Tag.DATA, b'Hello, World!'),
            Record(0x1234, Tag.TERMINATOR, b''),
        ]
        assert ans_out == ans_ref

    def test_check_sequence_doctest(self):
        pass  # TODO

    def test_check_sequence(self):
        records = [
            Record(0x1234, Tag.DATA, b'Hello, World!'),
            Record(0x1234, Tag.TERMINATOR, b''),
        ]
        Record.check_sequence(records)

        with pytest.raises(ValueError, match='missing terminator'):
            Record.check_sequence(records[0:0])

        with pytest.raises(ValueError, match='missing terminator'):
            Record.check_sequence(records[:-1])

        with pytest.raises(ValueError, match='tag error'):
            Record.check_sequence(records[::-1])

        with pytest.raises(ValueError, match='tag error'):
            record = Record(0x4321, Tag.DATA, b'dummy')
            Record.check_sequence(records + [record])

    def test_load_records(self, datapath):
        path_ref = datapath / 'bytes.tek'
        ans_out = list(Record.load_records(str(path_ref)))
        ans_ref = list(Record.split(BYTES))
        assert ans_out == ans_ref

    def test_save_records(self, tmppath, datapath):
        path_out = tmppath / 'bytes.tek'
        path_ref = datapath / 'bytes.tek'
        records = list(Record.split(BYTES))
        Record.save_records(str(path_out), records)
        ans_out = read_text(path_out)
        ans_ref = read_text(path_ref)
        assert ans_out == ans_ref
