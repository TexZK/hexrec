# -*- coding: utf-8 -*-
import os
from pathlib import Path

import pytest

from hexrec.formats.intel import Record
from hexrec.formats.intel import Tag

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
        tags = {0}
        for tag in Tag:
            assert Tag.is_data(tag) == (tag in tags), tag
            assert Tag.is_data(int(tag)) == (tag in tags), tag


# ============================================================================

class TestRecord:

    def test___init___doctest(self):
        pass  # TODO

    def test___init__(self):
        with pytest.raises(ValueError):
            Record.build_data(-1, BYTES)

        with pytest.raises(ValueError):
            Record.build_data(1 << 32, BYTES)

        with pytest.raises(ValueError):
            Record.build_data((1 << 32) - 128, BYTES)

    def test___str___doctest(self):
        pass  # TODO

    def test___str__(self):
        pass  # TODO

    def test_is_data_doctest(self):
        pass  # TODO

    def test_is_data(self):
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
        record = Record.build_data(0x1234, b'Hello, World!')
        record.count += 1
        record.update_checksum()
        with pytest.raises(ValueError):
            record.check()

    def test_build_data_doctest(self):
        ans_out = str(Record.build_data(0x1234, b'Hello, World!'))
        ans_ref = ':0D12340048656C6C6F2C20576F726C642144'
        assert ans_out == ans_ref

    def test_build_extended_segment_address_doctest(self):
        ans_out = str(Record.build_extended_segment_address(0x12345678))
        ans_ref = ':020000020123D8'
        assert ans_out == ans_ref

    def test_build_extended_segment_address(self):
        with pytest.raises(ValueError):
            Record.build_extended_segment_address(-1)

        with pytest.raises(ValueError):
            Record.build_extended_segment_address(1 << 32)

    def test_build_start_segment_address_doctest(self):
        ans_out = str(Record.build_start_segment_address(0x12345678))
        ans_ref = ':0400000312345678E5'
        assert ans_out == ans_ref

    def test_build_start_segment_address(self):
        with pytest.raises(ValueError):
            Record.build_start_segment_address(-1)

        with pytest.raises(ValueError):
            Record.build_start_segment_address(1 << 32)

    def test_build_end_of_file_doctest(self):
        ans_out = str(Record.build_end_of_file())
        ans_ref = ':00000001FF'
        assert ans_out == ans_ref

    def test_build_extended_linear_address_doctest(self):
        ans_out = str(Record.build_extended_linear_address(0x12345678))
        ans_ref = ':020000041234B4'
        assert ans_out == ans_ref

    def test_build_extended_linear_address(self):
        with pytest.raises(ValueError):
            Record.build_extended_linear_address(-1)

        with pytest.raises(ValueError):
            Record.build_extended_linear_address(1 << 32)

    def test_build_start_linear_address_doctest(self):
        ans_out = str(Record.build_start_linear_address(0x12345678))
        ans_ref = ':0400000512345678E3'
        assert ans_out == ans_ref

    def test_build_start_linear_address(self):
        with pytest.raises(ValueError):
            Record.build_start_linear_address(-1)

        with pytest.raises(ValueError):
            Record.build_start_linear_address(1 << 32)

    def test_parse_doctest(self):
        pass  # TODO

    def test_parse_record(self):
        with pytest.raises(ValueError):
            Record.parse_record('Hello, World!')

        with pytest.raises(ValueError):
            Record.parse_record(':01000001FF')

    def test_split_doctest(self):
        pass  # TODO

    def test_split(self):
        with pytest.raises(ValueError):
            list(Record.split(BYTES, address=-1))

        with pytest.raises(ValueError):
            list(Record.split(BYTES, address=(1 << 32)))

        with pytest.raises(ValueError):
            list(Record.split(BYTES, address=((1 << 32) - 128)))

        with pytest.raises(ValueError):
            list(Record.split(BYTES, columns=256))

        ans_out = list(Record.split(HEXBYTES, address=0x12345678))
        ans_ref = [
            Record(0, Tag.EXTENDED_LINEAR_ADDRESS, b'\x124'),
            Record(0x12345678, Tag.DATA,
                   b'\x00\x01\x02\x03\x04\x05\x06\x07'),
            Record(0x12345680, Tag.DATA,
                   b'\x08\t\n\x0b\x0c\r\x0e\x0f'),
            Record(0, Tag.EXTENDED_LINEAR_ADDRESS, b'\x00\x00'),
            Record(0, Tag.START_LINEAR_ADDRESS, b'\x124Vx'),
            Record(0, Tag.END_OF_FILE, b''),
        ]
        assert ans_out == ans_ref

        ans_out = list(Record.split(HEXBYTES, address=0x0000FFF8,
                                    start=0x0000FFF8))
        ans_ref = [
            Record(0xFFF8, Tag.DATA,
                   b'\x00\x01\x02\x03\x04\x05\x06\x07'),
            Record(0, Tag.EXTENDED_LINEAR_ADDRESS, b'\x00\x01'),
            Record(0x10000, Tag.DATA, b'\x08\t\n\x0b\x0c\r\x0e\x0f'),
            Record(0, Tag.EXTENDED_LINEAR_ADDRESS, b'\x00\x00'),
            Record(0, Tag.START_LINEAR_ADDRESS, b'\x00\x00\xff\xf8'),
            Record(0, Tag.END_OF_FILE, b'')
        ]
        assert ans_out == ans_ref

        ans_out = list(Record.split(HEXBYTES, address=0x0000FFF8,
                                    align=False))
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
        ans_ref = [
            Record(0, Tag.EXTENDED_LINEAR_ADDRESS, b'\x00\x00'),
            Record(0, Tag.START_LINEAR_ADDRESS, b'\x00\x00\x00\x00'),
            Record(0, Tag.END_OF_FILE, b''),
        ]
        assert ans_out == ans_ref

        ans_out = list(Record.build_standalone([], start=0))
        ans_ref = [
            Record(0, Tag.EXTENDED_LINEAR_ADDRESS, b'\x00\x00'),
            Record(0, Tag.START_LINEAR_ADDRESS, b'\x00\x00\x00\x00'),
            Record(0, Tag.END_OF_FILE, b''),
        ]
        assert ans_out == ans_ref

        data_records = [Record.build_data(0x1234, HEXBYTES)]
        ans_out = list(Record.build_standalone(data_records))
        ans_ref = [
            Record(0x1234, Tag.DATA, HEXBYTES),
            Record(0, Tag.EXTENDED_LINEAR_ADDRESS, b'\x00\x00'),
            Record(0, Tag.START_LINEAR_ADDRESS, b'\x00\x00\x12\x34'),
            Record(0, Tag.END_OF_FILE, b''),
        ]
        assert ans_out == ans_ref

    def test_terminate_doctest(self):
        ans_out = list(map(str, Record.terminate(0x12345678)))
        ans_ref = [':020000040000FA', ':0400000512345678E3', ':00000001FF']
        assert ans_out == ans_ref

    def test_readdress_doctest(self):
        ans_out = [
            Record.build_extended_linear_address(0x76540000),
            Record.build_data(0x00003210, b'Hello, World!'),
        ]
        Record.readdress(ans_out)
        ans_ref = [
            Record(0x76540000, Tag.EXTENDED_LINEAR_ADDRESS, b'vT'),
            Record(0x76543210, Tag.DATA, b'Hello, World!'),
        ]
        assert ans_out == ans_ref

    def test_readdress(self):
        ans_out = [
            Record.build_extended_segment_address(0x76540000),
            Record.build_data(0x00001000, b'Hello, World!'),
        ]
        Record.readdress(ans_out)
        ans_ref = [
            Record(0x00007650, Tag.EXTENDED_SEGMENT_ADDRESS,
                   b'\x07\x65'),
            Record(0x00008650, Tag.DATA, b'Hello, World!'),
        ]
        assert ans_out == ans_ref

    def test_load_records(self, datapath):
        path_ref = datapath / 'bytes.hex'
        ans_out = list(Record.load_records(str(path_ref)))
        ans_ref = list(Record.split(BYTES))
        assert ans_out == ans_ref

    def test_save_records(self, tmppath, datapath):
        path_out = tmppath / 'bytes.hex'
        path_ref = datapath / 'bytes.hex'
        records = list(Record.split(BYTES))
        Record.save_records(str(path_out), records)
        ans_out = read_text(path_out)
        ans_ref = read_text(path_ref)
        assert ans_out == ans_ref
