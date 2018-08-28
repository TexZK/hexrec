# -*- coding: utf-8 -*-
import os
from distutils import dir_util
from pathlib import Path

import pytest
import six

from hexrec.blocks import chop_blocks
from hexrec.records import *
from hexrec.utils import chop

BYTES = bytes(bytearray(range(256)))
HEXBYTES = bytes(bytearray(range(16)))

# ============================================================================

# Quick and dirty fix for string prefixes
@pytest.mark.skip(reason='depends on the Python version')
def str_bytes_quickfix(text):
    if six.PY2:
        text = text.replace("='", "=b'")
        text = text.replace("=u'", "='")
    return text

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

def read_bytes(path):
    path = str(path)
    with open(path, 'rb') as file:
        data = file.read()
    return data

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

def test_get_data_records_doctest():
    data = bytes(bytearray(range(256)))
    blocks = list(chop_blocks(data, 16))
    records = blocks_to_records(blocks, MotorolaRecord)
    assert all(r.is_data() for r in get_data_records(records))

# ============================================================================

def test_find_corrupted_records_doctest():
    data = bytes(bytearray(range(256)))
    records = list(MotorolaRecord.split(data))
    records[3].checksum ^= 0xFF
    records[5].checksum ^= 0xFF
    records[7].checksum ^= 0xFF
    ans_out = find_corrupted_records(records)
    ans_ref = [3, 5, 7]
    assert ans_out == ans_ref

# ============================================================================

def test_records_to_blocks_doctest():
    data = bytes(bytearray(range(256)))
    blocks = list(chop_blocks(data, 16))
    records = blocks_to_records(blocks, MotorolaRecord)
    ans_ref = merge(blocks)
    ans_out = records_to_blocks(records)
    assert ans_ref == ans_out

# ============================================================================

def test_blocks_to_records_doctest():
    data = bytes(bytearray(range(256)))
    blocks = list(chop_blocks(data, 16))
    records = blocks_to_records(blocks, MotorolaRecord)
    ans_ref = merge(blocks)
    ans_out = records_to_blocks(records)
    assert ans_ref == ans_out

# ============================================================================

def test_merge_records_doctest():
    data1 = bytes(bytearray(range(0, 32)))
    data2 = bytes(bytearray(range(96, 128)))
    blocks1 = list(chop_blocks(data1, 16, start=0))
    blocks2 = list(chop_blocks(data2, 16, start=96))
    records1 = blocks_to_records(blocks1, MotorolaRecord)
    records2 = blocks_to_records(blocks2, IntelRecord)
    IntelRecord.readdress(records2)
    data_records1 = get_data_records(records1)
    data_records2 = get_data_records(records2)
    merged_records = merge_records([data_records1, data_records2])
    merged_blocks = records_to_blocks(merged_records)
    ans_ref = merge(blocks1 + blocks2)
    ans_out = merged_blocks
    assert ans_ref == ans_out

# ============================================================================

def test_convert_records_doctest():
    motorola = list(MotorolaRecord.split(BYTES))
    intel = list(IntelRecord.split(BYTES))
    converted = convert_records(motorola, output_type=IntelRecord)
    assert converted == intel

    motorola = list(MotorolaRecord.split(BYTES))
    intel = list(IntelRecord.split(BYTES))
    converted = convert_records(intel, output_type=MotorolaRecord)
    assert converted == motorola


def test_convert_records():
    motorola1 = list(MotorolaRecord.split(BYTES))
    motorola2 = list(MotorolaRecord.split(BYTES))
    converted = convert_records(motorola1, input_type=MotorolaRecord)
    assert converted == motorola2

    intel1 = list(IntelRecord.split(BYTES))
    intel2 = list(IntelRecord.split(BYTES))
    converted = convert_records(intel1, output_type=IntelRecord)
    assert converted == intel2

# ============================================================================

def test_merge_files_doctest(tmppath, datapath):
    path_merge1 = str(datapath / 'merge1.mot')
    path_merge2 = str(datapath / 'merge2.hex')
    path_merged_out = str(tmppath / 'merged.tek')
    path_merged_ref = str(datapath / 'merged.tek')
    merge_files([path_merge1, path_merge2], path_merged_out)
    ans_out = load_records(path_merged_out)
    ans_ref = load_records(path_merged_ref)
    assert ans_out == ans_ref


def test_merge_files(tmppath, datapath):
    path_merge1 = str(datapath / 'merge1.mot')
    path_merge2 = str(datapath / 'merge2.hex')
    path_merged_out = str(tmppath / 'merged.tek')
    path_merged_ref = str(datapath / 'merged.tek')
    merge_files([path_merge1, path_merge2], path_merged_out,
                [MotorolaRecord, IntelRecord], TektronixRecord)
    ans_out = load_records(path_merged_out)
    ans_ref = load_records(path_merged_ref)
    assert ans_out == ans_ref

# ============================================================================

def test_convert_file_doctest(tmppath):
    path_mot = str(tmppath / 'bytes.mot')
    path_hex = str(tmppath / 'bytes.hex')
    motorola = list(MotorolaRecord.split(BYTES))
    intel = list(IntelRecord.split(BYTES))
    save_records(path_mot, motorola)
    convert_file(path_mot, path_hex)
    ans_out = load_records(path_hex)
    ans_ref = intel
    assert ans_out == ans_ref

# ============================================================================

def test_load_records_doctest(tmppath):
    path = str(tmppath / 'bytes.mot')
    records = list(MotorolaRecord.split(BYTES))
    save_records(path, records)
    ans_out = load_records(path)
    ans_ref = records
    assert ans_out == ans_ref


def test_load_records(tmppath):
    path = str(tmppath / 'bytes.mot')
    records = list(MotorolaRecord.split(BYTES))
    save_records(path, records)
    ans_out = load_records(path, MotorolaRecord)
    ans_ref = records
    assert ans_out == ans_ref

# ============================================================================

def test_save_records_doctest(tmppath):
    path = str(tmppath / 'bytes.hex')
    records = list(IntelRecord.split(BYTES))
    save_records(path, records)
    ans_out = load_records(path)
    ans_ref = records
    assert ans_out == ans_ref


def test_save_records(tmppath):
    path = str(tmppath / 'bytes.hex')
    records = list(IntelRecord.split(BYTES))
    save_records(path, records, IntelRecord)
    ans_out = load_records(path)
    ans_ref = records
    assert ans_out == ans_ref

    records = []
    save_records(path, records, IntelRecord)
    ans_out = load_records(path)
    ans_ref = records
    assert ans_out == ans_ref

    path = str(tmppath / 'bytes.mot')
    intel = list(IntelRecord.split(BYTES))
    motorola = list(MotorolaRecord.split(BYTES))
    save_records(path, intel, MotorolaRecord)
    ans_out = load_records(path)
    ans_ref = motorola
    assert ans_out == ans_ref

# ============================================================================

def test_load_blocks_doctest(tmppath):
    path = str(tmppath / 'bytes.mot')
    blocks = [(offset, bytes(bytearray(range(offset, offset + 16))))
              for offset in range(0, 256, 16)]
    save_blocks(path, blocks)
    ans_out = load_blocks(path)
    ans_ref = merge(blocks)
    assert ans_out == ans_ref


def test_load_blocks(tmppath):
    path = str(tmppath / 'bytes.mot')
    blocks = [(offset, bytes(bytearray(range(offset, offset + 16))))
              for offset in range(0, 256, 16)]
    save_blocks(path, blocks)
    ans_out = load_blocks(path, MotorolaRecord)
    ans_ref = merge(blocks)
    assert ans_out == ans_ref

# ============================================================================

def test_save_blocks_doctest(tmppath):
    path = str(tmppath / 'bytes.hex')
    blocks = [(offset, bytes(bytearray(range(offset, offset + 16))))
              for offset in range(0, 256, 16)]
    save_blocks(path, blocks)
    ans_out = load_blocks(path)
    ans_ref = merge(blocks)
    assert ans_out == ans_ref


def test_save_blocks(tmppath):
    path = str(tmppath / 'bytes.hex')
    blocks = [(offset, bytes(bytearray(range(offset, offset + 16))))
              for offset in range(0, 256, 16)]
    save_blocks(path, blocks, IntelRecord)
    ans_out = load_blocks(path)
    ans_ref = merge(blocks)
    assert ans_out == ans_ref

# ============================================================================

def test_load_memory_doctest(tmppath):
    path = str(tmppath / 'bytes.mot')
    blocks = [(offset, bytes(bytearray(range(offset, offset + 16))))
              for offset in range(0, 256, 16)]
    sparse_items = SparseItems(blocks=blocks)
    save_memory(path, sparse_items)
    ans_out = load_memory(path)
    ans_ref = sparse_items
    assert ans_out == ans_ref

# ============================================================================

def test_save_memory_doctest(tmppath):
    path = str(tmppath / 'bytes.hex')
    blocks = [(offset, bytes(bytearray(range(offset, offset + 16))))
              for offset in range(0, 256, 16)]
    sparse_items = SparseItems(blocks=blocks)
    save_memory(path, sparse_items)
    ans_out = load_memory(path)
    ans_ref = sparse_items
    assert ans_out == ans_ref

# ============================================================================

class TestRecord(object):

    def test___init___doctest(self):
        r = BinaryRecord(0x1234, 0, b'Hello, World!')
        ans_out = str_bytes_quickfix(normalize_whitespace(repr(r)))
        ans_ref = normalize_whitespace('''
        BinaryRecord(address=0x00001234, tag=0, count=13,
                     data=b'Hello, World!', checksum=0x69)
        ''')
        assert ans_out == ans_ref

        r = MotorolaRecord(0x1234, MotorolaTag.DATA_16, b'Hello, World!')
        ans_out = str_bytes_quickfix(normalize_whitespace(repr(r)))
        ans_ref = normalize_whitespace('''
        MotorolaRecord(address=0x00001234, tag=<MotorolaTag.DATA_16: 1>,
                       count=16, data=b'Hello, World!', checksum=0x40)
        ''')
        assert ans_out == ans_ref

        r = IntelRecord(0x1234, IntelTag.DATA, b'Hello, World!')
        ans_out = str_bytes_quickfix(normalize_whitespace(repr(r)))
        ans_ref = normalize_whitespace('''
        IntelRecord(address=0x00001234, tag=<IntelTag.DATA: 0>, count=13,
                    data=b'Hello, World!', checksum=0x44)
        ''')
        assert ans_out == ans_ref

    def test___str___doctest(self):
        ans_out = str(BinaryRecord(0x1234, 0, b'Hello, World!'))
        ans_ref = '48656C6C6F2C20576F726C6421'
        assert ans_out == ans_ref

        ans_out = str(MotorolaRecord(0x1234, MotorolaTag.DATA_16,
                                     b'Hello, World!'))
        ans_ref = 'S110123448656C6C6F2C20576F726C642140'
        assert ans_out == ans_ref

        ans_out = str(IntelRecord(0x1234, IntelTag.DATA, b'Hello, World!'))
        ans_ref = ':0D12340048656C6C6F2C20576F726C642144'
        assert ans_out == ans_ref

    def test___str__(self):
        ans_out = str(Record(0x1234, 0, b'Hello, World!'))
        ans_out = str_bytes_quickfix(normalize_whitespace(ans_out))
        ans_ref = ("Record(address=0x00001234, tag=0, count=13, "
                   "data=b'Hello, World!', checksum=0x69)")
        ans_ref = normalize_whitespace(ans_ref)
        assert ans_out == ans_ref

    def test___eq___doctest(self):
        record1 = BinaryRecord.build_data(0, b'Hello, World!')
        record2 = BinaryRecord.build_data(0, b'Hello, World!')
        assert (record1 == record2) == True

        record1 = BinaryRecord.build_data(0, b'Hello, World!')
        record2 = BinaryRecord.build_data(1, b'Hello, World!')
        assert (record1 == record2) == False

        record1 = BinaryRecord.build_data(0, b'Hello, World!')
        record2 = BinaryRecord.build_data(0, b'hello, world!')
        assert (record1 == record2) == False

        record1 = MotorolaRecord.build_header(b'Hello, World!')
        record2 = MotorolaRecord.build_data(0, b'hello, world!')
        assert (record1 == record2) == False

    def test___hash__(self):
        hash(BinaryRecord(0x1234, 0, b'Hello, World!'))
        hash(MotorolaRecord(0x1234, MotorolaTag.DATA_16, b'Hello, World!'))
        hash(IntelRecord(0x1234, IntelTag.DATA, b'Hello, World!'))

    def test___lt___doctest(self):
        record1 = BinaryRecord(0x1234, 0, b'')
        record2 = BinaryRecord(0x4321, 0, b'')
        assert (record1 < record2) == True

        record1 = BinaryRecord(0x4321, 0, b'')
        record2 = BinaryRecord(0x1234, 0, b'')
        assert (record1 < record2) == False

    def test_is_data_doctest(self):
        record = BinaryRecord(0, 0, b'Hello, World!')
        assert record.is_data() == True

        record = MotorolaRecord(0, MotorolaTag.DATA_16, b'Hello, World!')
        assert record.is_data() == True

        record = MotorolaRecord(0, MotorolaTag.HEADER, b'Hello, World!')
        assert record.is_data() == False

        record = IntelRecord(0, IntelTag.DATA, b'Hello, World!')
        assert record.is_data() == True

        record = IntelRecord(0, IntelTag.END_OF_FILE, b'')
        assert record.is_data() == False

    def test_compute_count_doctest(self):
        record = BinaryRecord(0, 0, b'Hello, World!')
        assert str(record) == '48656C6C6F2C20576F726C6421'
        assert record.compute_count() == 13

        record = MotorolaRecord(0, MotorolaTag.DATA_16, b'Hello, World!')
        assert str(record) == 'S110000048656C6C6F2C20576F726C642186'
        assert record.compute_count() == 16

        record = IntelRecord(0, IntelTag.DATA, b'Hello, World!')
        assert str(record) == ':0D00000048656C6C6F2C20576F726C64218A'
        assert record.compute_count() == 13

    def test_update_count(self):
        record = BinaryRecord(0, 0, b'Hello, World!')
        record.count = None
        record.update_count()
        assert str(record) == '48656C6C6F2C20576F726C6421'
        assert record.count == 13

        record = MotorolaRecord(0, MotorolaTag.DATA_16, b'Hello, World!')
        record.count = None
        record.update_count()
        assert str(record) == 'S110000048656C6C6F2C20576F726C642186'
        assert record.count == 16

        record = IntelRecord(0, IntelTag.DATA, b'Hello, World!')
        record.count = None
        record.update_count()
        assert str(record) == ':0D00000048656C6C6F2C20576F726C64218A'
        assert record.count == 13

    def test_compute_checksum_doctest(self):
        record = BinaryRecord(0, 0, b'Hello, World!')
        assert str(record) == '48656C6C6F2C20576F726C6421'
        assert hex(record.compute_checksum()) == '0x69'

        record = MotorolaRecord(0, MotorolaTag.DATA_16, b'Hello, World!')
        assert str(record) == 'S110000048656C6C6F2C20576F726C642186'
        assert hex(record.compute_checksum()) == '0x86'

        record = IntelRecord(0, IntelTag.DATA, b'Hello, World!')
        assert str(record) == ':0D00000048656C6C6F2C20576F726C64218A'
        assert hex(record.compute_checksum()) == '0x8a'

    def test_update_checksum(self):
        record = BinaryRecord(0, 0, b'Hello, World!')
        record.checksum = None
        record.update_checksum()
        assert str(record) == '48656C6C6F2C20576F726C6421'
        assert hex(record.checksum) == '0x69'

        record = MotorolaRecord(0, MotorolaTag.DATA_16, b'Hello, World!')
        record.checksum = None
        record.update_checksum()
        assert str(record) == 'S110000048656C6C6F2C20576F726C642186'
        assert hex(record.checksum) == '0x86'

        record = IntelRecord(0, IntelTag.DATA, b'Hello, World!')
        record.checksum = None
        record.update_checksum()
        assert str(record) == ':0D00000048656C6C6F2C20576F726C64218A'
        assert hex(record.checksum) == '0x8a'

    def test_check(self):
        with pytest.raises(ValueError):
            Record(-1, 0, b'Hello, World!').check()

        with pytest.raises(ValueError):
            Record(0, -1, b'Hello, World!').check()

        with pytest.raises(ValueError):
            Record(0, 256, b'Hello, World!').check()

        record = Record(0, 0, b'')
        record.data = None
        with pytest.raises(ValueError): record.check()

        record = Record(0, 0, b'#' * 256)
        with pytest.raises(ValueError): record.check()

        record = Record(0, 0, b'Hello, World!')
        record.checksum = -1
        with pytest.raises(ValueError): record.check()

        record = Record(0, 0, b'Hello, World!')
        record.checksum = 256
        with pytest.raises(ValueError): record.check()

        record = Record(0, 0, b'')
        record.checksum ^= 0xFF
        with pytest.raises(ValueError): record.check()

    def test__get_checksum(self):
        record = BinaryRecord(0, 0, b'Hello, World!')
        assert hex(record._get_checksum()) == '0x69'
        record.checksum = None
        assert hex(record._get_checksum()) == '0x69'

        record = MotorolaRecord(0, MotorolaTag.DATA_16, b'Hello, World!')
        assert hex(record._get_checksum()) == '0x86'
        record.checksum = None
        assert hex(record._get_checksum()) == '0x86'

        record = IntelRecord(0, IntelTag.DATA, b'Hello, World!')
        assert hex(record._get_checksum()) == '0x8a'
        record.checksum = None
        assert hex(record._get_checksum()) == '0x8a'

    def test_overlaps_doctest(self):
        record1 = BinaryRecord(0, 0, b'abc')
        record2 = BinaryRecord(1, 0, b'def')
        assert record1.overlaps(record2) == True

        record1 = BinaryRecord(0, 0, b'abc')
        record2 = BinaryRecord(3, 0, b'def')
        assert record1.overlaps(record2) == False

    def test_overlaps(self):
        record1 = BinaryRecord(0, 0, b'abc')
        record1.address = None
        record2 = BinaryRecord(3, 0, b'def')
        assert record1.overlaps(record2) == False

        record1 = BinaryRecord(0, 0, b'abc')
        record2 = BinaryRecord(3, 0, b'def')
        record2.address = None
        assert record1.overlaps(record2) == False

    def test_parse(self):
        with pytest.raises(NotImplementedError):
            Record.parse('')

    def test_split(self):
        with pytest.raises(NotImplementedError):
            Record.split(b'')

    def test_build_standalone(self):
        data = bytes(bytearray(range(256)))
        blocks = list(chop_blocks(data, 16))
        records = blocks_to_records(blocks, BinaryRecord)
        data_records = get_data_records(records)
        data_records2 = list(BinaryRecord.build_standalone(records))
        assert data_records == data_records2

    def test_check_sequence(self):
        record1 = BinaryRecord(0, 0, b'abc')
        record2 = BinaryRecord(3, 0, b'def')
        records = [record1, record2]
        BinaryRecord.check_sequence(records)

        record2.address = 1
        record2.update_checksum()
        with pytest.raises(ValueError):
            BinaryRecord.check_sequence(records)

        record1.address = 3
        record2.address = 0
        record1.update_checksum()
        record2.update_checksum()
        with pytest.raises(ValueError):
            BinaryRecord.check_sequence(records)

    def test_readdress(self):
        pass

# ============================================================================

class TestBinaryTag(object):

    def test_is_data(self):
        for tag in range(256):
            assert BinaryTag.is_data(tag)

# ============================================================================

class TestBinaryRecord(object):

    def test_build_data_doctest(self):
        record = BinaryRecord.build_data(0x1234, b'Hello, World!')
        ans_out = str_bytes_quickfix(normalize_whitespace(repr(record)))
        ans_ref = normalize_whitespace('''
        BinaryRecord(address=0x00001234, tag=0, count=13,
                     data=b'Hello, World!', checksum=0x69)
        ''')
        assert ans_out == ans_ref

    def test_parse_doctest(self):
        line = '48656C6C 6F2C2057 6F726C64 21'
        record = BinaryRecord.parse(line)
        ans_out = str_bytes_quickfix(normalize_whitespace(repr(record)))
        ans_ref = normalize_whitespace('''
        BinaryRecord(address=0x00000000, tag=0, count=13,
                     data=b'Hello, World!', checksum=0x69)
        ''')
        assert ans_out == ans_ref

    def test_split(self):
        with pytest.raises(ValueError):
            list(BinaryRecord.split(b'', -1))

        with pytest.raises(ValueError):
            list(BinaryRecord.split(b'', 1 << 32))

        with pytest.raises(ValueError):
            list(BinaryRecord.split(b'abc', (1 << 32) - 1))

        ans_out = list(BinaryRecord.split(BYTES))
        ans_ref = [BinaryRecord.build_data(0, BYTES)]
        assert ans_out == ans_ref

        ans_out = list(BinaryRecord.split(BYTES, columns=8))
        ans_ref = [BinaryRecord.build_data(offset, BYTES[offset:(offset + 8)])
                   for offset in range(0, 256, 8)]
        assert ans_out == ans_ref

    def test_load(self, datapath):
        path_ref = datapath / 'hexbytes.bin'
        ans_out = list(BinaryRecord.load(str(path_ref)))
        ans_ref = [BinaryRecord.build_data(0, HEXBYTES)]
        assert ans_out == ans_ref

    def test_save(self, tmppath, datapath):
        path_out = tmppath / 'hexbytes.bin'
        path_ref = datapath / 'hexbytes.bin'
        records = [BinaryRecord.build_data(0, HEXBYTES)]
        BinaryRecord.save(str(path_out), records)
        ans_out = read_text(path_out)
        ans_ref = read_text(path_ref)
        assert ans_out == ans_ref

# ============================================================================

class TestMotorolaTag(object):

    def test_is_data(self):
        DATA_INTS = {1, 2, 3}
        for tag in MotorolaTag:
            assert MotorolaTag.is_data(tag) == (tag in DATA_INTS)
            assert MotorolaTag.is_data(int(tag)) == (tag in DATA_INTS)

# ============================================================================

class TestMotorolaRecord(object):

    def test___init___doctest(self):
        pass  # TODO

    def test___init__(self):
        pass  # TODO

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

    def test_check_doctest(self):
        pass  # TODO

    def test_check(self):
        record = MotorolaRecord.build_data(0, b'')
        for tag in range(len(MotorolaTag), 256):
            record.tag = tag
            record.update_checksum()
            with pytest.raises(ValueError): record.check()

        record = MotorolaRecord.build_data(0, b'Hello, World!')
        record.check()
        record.tag = len(MotorolaTag)
        with pytest.raises(ValueError): record.check()

        record = MotorolaRecord.build_header(b'')
        record.address = 1
        record.update_checksum()
        with pytest.raises(ValueError): record.check()

        record = MotorolaRecord.build_count(0x1234)
        record.address = 1
        record.update_checksum()
        with pytest.raises(ValueError): record.check()

        record = MotorolaRecord.build_count(0x123456)
        record.address = 1
        record.update_checksum()
        with pytest.raises(ValueError): record.check()

        record = MotorolaRecord.build_data(0, b'Hello, World!')
        record.count += 1
        record.update_checksum()
        with pytest.raises(ValueError): record.check()

    def test_fit_data_tag_doctest(self):
        ans_out = repr(MotorolaRecord.fit_data_tag(0x00000000))
        ans_ref = '<MotorolaTag.DATA_16: 1>'
        assert ans_out == ans_ref

        ans_out = repr(MotorolaRecord.fit_data_tag(0x0000FFFF))
        ans_ref = '<MotorolaTag.DATA_16: 1>'
        assert ans_out == ans_ref

        ans_out = repr(MotorolaRecord.fit_data_tag(0x00010000))
        ans_ref = '<MotorolaTag.DATA_16: 1>'
        assert ans_out == ans_ref

        ans_out = repr(MotorolaRecord.fit_data_tag(0x00FFFFFF))
        ans_ref = '<MotorolaTag.DATA_24: 2>'
        assert ans_out == ans_ref

        ans_out = repr(MotorolaRecord.fit_data_tag(0x01000000))
        ans_ref = '<MotorolaTag.DATA_24: 2>'
        assert ans_out == ans_ref

        ans_out = repr(MotorolaRecord.fit_data_tag(0xFFFFFFFF))
        ans_ref = '<MotorolaTag.DATA_32: 3>'
        assert ans_out == ans_ref

    def test_fit_data_tag(self):
        with pytest.raises(ValueError):
            MotorolaRecord.fit_data_tag(-1)

        with pytest.raises(ValueError):
            MotorolaRecord.fit_data_tag(1 << 32)

    def test_fit_count_tag_doctest(self):
        ans_out = repr(MotorolaRecord.fit_count_tag(0x0000000))
        ans_ref = '<MotorolaTag.COUNT_16: 5>'
        assert ans_out == ans_ref

        ans_out = repr(MotorolaRecord.fit_count_tag(0x00FFFF))
        ans_ref = '<MotorolaTag.COUNT_16: 5>'
        assert ans_out == ans_ref

        ans_out = repr(MotorolaRecord.fit_count_tag(0x010000))
        ans_ref = '<MotorolaTag.COUNT_24: 6>'
        assert ans_out == ans_ref

        ans_out = repr(MotorolaRecord.fit_count_tag(0xFFFFFF))
        ans_ref = '<MotorolaTag.COUNT_24: 6>'
        assert ans_out == ans_ref

    def test_fit_count_tag(self):
        with pytest.raises(ValueError):
            MotorolaRecord.fit_count_tag(-1)

        with pytest.raises(ValueError):
            MotorolaRecord.fit_count_tag(1 << 24)

    def test_build_header_doctest(self):
        ans_out = str(MotorolaRecord.build_header(b'Hello, World!'))
        ans_ref = 'S010000048656C6C6F2C20576F726C642186'
        assert ans_out == ans_ref

    def test_build_data_doctest(self):
        ans_out = str(MotorolaRecord.build_data(0x1234, b'Hello, World!'))
        ans_ref = 'S110123448656C6C6F2C20576F726C642140'
        assert ans_out == ans_ref

        ans_out = str(MotorolaRecord.build_data(0x1234, b'Hello, World!',
                                                tag=MotorolaTag.DATA_16))
        ans_ref = 'S110123448656C6C6F2C20576F726C642140'
        assert ans_out == ans_ref

        ans_out = str(MotorolaRecord.build_data(0x123456, b'Hello, World!',
                                                tag=MotorolaTag.DATA_24))
        ans_ref = 'S21112345648656C6C6F2C20576F726C6421E9'
        assert ans_out == ans_ref

        ans_out = str(MotorolaRecord.build_data(0x12345678, b'Hello, World!',
                                                tag=MotorolaTag.DATA_32))
        ans_ref = 'S3121234567848656C6C6F2C20576F726C642170'
        assert ans_out == ans_ref

    def test_build_data_tag(self):
        for tag in [0] + list(range(4, len(MotorolaTag))):
            with pytest.raises(ValueError):
                MotorolaRecord.build_data(0x1234, b'Hello, World!', tag=tag)

    def test_build_terminator_doctest(self):
        ans_out = str(MotorolaRecord.build_terminator(0x1234))
        ans_ref = 'S9031234B6'
        assert ans_out == ans_ref

        ans_out = str(MotorolaRecord.build_terminator(0x1234,
                                                      MotorolaTag.DATA_16))
        ans_ref = 'S9031234B6'
        assert ans_out == ans_ref

        ans_out = str(MotorolaRecord.build_terminator(0x123456,
                                                      MotorolaTag.DATA_24))
        ans_ref = 'S8041234565F'
        assert ans_out == ans_ref

        ans_out = str(MotorolaRecord.build_terminator(0x12345678,
                                                      MotorolaTag.DATA_32))
        ans_ref = 'S70512345678E6'
        assert ans_out == ans_ref

    def test_build_count_doctest(self):
        ans_out = str(MotorolaRecord.build_count(0x1234))
        ans_ref = 'S5031234B6'
        assert ans_out == ans_ref

        ans_out = str(MotorolaRecord.build_count(0x123456))
        ans_ref = 'S6041234565F'
        assert ans_out == ans_ref

    def test_parse_doctest(self):
        pass  # TODO

    def test_parse(self):
        with pytest.raises(ValueError):
            MotorolaRecord.parse('Hello, World!')

    def test_build_standalone(self):
        ans_out = list(MotorolaRecord.build_standalone(
            [],
            tag=MotorolaTag.DATA_32,
            header_data=b'Hello, World!',
            start=0
        ))
        ans_ref = [
            MotorolaRecord(0, MotorolaTag.HEADER, b'Hello, World!'),
            MotorolaRecord(0, MotorolaTag.COUNT_16, b'\x00\x01'),
            MotorolaRecord(0, MotorolaTag.START_32, b''),
        ]
        assert ans_out == ans_ref

    def test_check_sequence_doctest(self):
        pass  # TODO

    def test_check_sequence(self):
        pass  # TODO

    def test_split_doctest(self):
        pass  # TODO

    def test_split(self):
        with pytest.raises(ValueError):
            list(MotorolaRecord.split(BYTES, address=-1))

        with pytest.raises(ValueError):
            list(MotorolaRecord.split(BYTES, address=(1 << 32)))

        with pytest.raises(ValueError):
            list(MotorolaRecord.split(BYTES, address=((1 << 32) - 128)))

        with pytest.raises(ValueError):
            list(MotorolaRecord.split(BYTES, columns=129))

        ans_out = list(MotorolaRecord.split(HEXBYTES,
                                            header_data=b'Hello, World!'))
        ans_ref = [
            MotorolaRecord(0, MotorolaTag.HEADER, b'Hello, World!'),
            MotorolaRecord(0, MotorolaTag.DATA_16, HEXBYTES),
            MotorolaRecord(0, MotorolaTag.COUNT_16, b'\x00\x01'),
            MotorolaRecord(0, MotorolaTag.START_16, b''),
        ]
        assert ans_out == ans_ref

    def test_fix_tags_doctest(self):
        pass  # TODO

    def test_fix_tags(self):
        ans_out = [
            MotorolaRecord(0, MotorolaTag.HEADER, b'Hello, World!'),
            MotorolaRecord(0x12345678, MotorolaTag.DATA_16, HEXBYTES),
            MotorolaRecord(0, MotorolaTag.COUNT_16, b'\x12\x34\x56'),
            MotorolaRecord(0x1234, MotorolaTag.START_16, b''),
        ]
        MotorolaRecord.fix_tags(ans_out)
        ans_ref = [
            MotorolaRecord(0, MotorolaTag.HEADER, b'Hello, World!'),
            MotorolaRecord(0x12345678, MotorolaTag.DATA_32, HEXBYTES),
            MotorolaRecord(0, MotorolaTag.COUNT_24, b'\x12\x34\x56'),
            MotorolaRecord(0x1234, MotorolaTag.START_32, b''),
        ]
        assert ans_out == ans_ref

    def test_load(self, datapath):
        path_ref = datapath / 'bytes.mot'
        ans_out = list(MotorolaRecord.load(str(path_ref)))
        ans_ref = list(MotorolaRecord.split(BYTES))
        assert ans_out == ans_ref

    def test_save(self, tmppath, datapath):
        path_out = tmppath / 'bytes.mot'
        path_ref = datapath / 'bytes.mot'
        records = list(MotorolaRecord.split(BYTES))
        MotorolaRecord.save(str(path_out), records)
        ans_out = read_text(path_out)
        ans_ref = read_text(path_ref)
        assert ans_out == ans_ref

# ============================================================================

class TestIntelTag(object):

    def test_is_data(self):
        DATA_INTS = {0}
        for tag in IntelTag:
            assert IntelTag.is_data(tag) == (tag in DATA_INTS)
            assert IntelTag.is_data(int(tag)) == (tag in DATA_INTS)

# ============================================================================

class TestIntelRecord(object):

    def test___init___doctest(self):
        pass  # TODO

    def test___init__(self):
        with pytest.raises(ValueError):
            IntelRecord.build_data(-1, BYTES)

        with pytest.raises(ValueError):
            IntelRecord.build_data(1 << 32, BYTES)

        with pytest.raises(ValueError):
            IntelRecord.build_data((1 << 32) - 128, BYTES)

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
        record = IntelRecord.build_data(0x1234, b'Hello, World!')
        record.count += 1
        record.update_checksum()
        with pytest.raises(ValueError): record.check()

    def test_build_data_doctest(self):
        ans_out = str(IntelRecord.build_data(0x1234, b'Hello, World!'))
        ans_ref = ':0D12340048656C6C6F2C20576F726C642144'
        assert ans_out == ans_ref

    def test_build_extended_segment_address_doctest(self):
        ans_out = str(IntelRecord.build_extended_segment_address(0x12345678))
        ans_ref = ':020000020123D8'
        assert ans_out == ans_ref

    def test_build_extended_segment_address(self):
        with pytest.raises(ValueError):
            IntelRecord.build_extended_segment_address(-1)

        with pytest.raises(ValueError):
            IntelRecord.build_extended_segment_address(1 << 32)

    def test_build_start_segment_address_doctest(self):
        ans_out = str(IntelRecord.build_start_segment_address(0x12345678))
        ans_ref = ':0400000312345678E5'
        assert ans_out == ans_ref

    def test_build_start_segment_address(self):
        with pytest.raises(ValueError):
            IntelRecord.build_start_segment_address(-1)

        with pytest.raises(ValueError):
            IntelRecord.build_start_segment_address(1 << 32)

    def test_build_end_of_file_doctest(self):
        ans_out = str(IntelRecord.build_end_of_file())
        ans_ref = ':00000001FF'
        assert ans_out == ans_ref

    def test_build_extended_linear_address_doctest(self):
        ans_out = str(IntelRecord.build_extended_linear_address(0x12345678))
        ans_ref = ':020000041234B4'
        assert ans_out == ans_ref

    def test_build_extended_linear_address(self):
        with pytest.raises(ValueError):
            IntelRecord.build_extended_linear_address(-1)

        with pytest.raises(ValueError):
            IntelRecord.build_extended_linear_address(1 << 32)

    def test_build_start_linear_address_doctest(self):
        ans_out = str(IntelRecord.build_start_linear_address(0x12345678))
        ans_ref = ':0400000512345678E3'
        assert ans_out == ans_ref

    def test_build_start_linear_address(self):
        with pytest.raises(ValueError):
            IntelRecord.build_start_linear_address(-1)

        with pytest.raises(ValueError):
            IntelRecord.build_start_linear_address(1 << 32)

    def test_parse_doctest(self):
        pass  # TODO

    def test_parse(self):
        with pytest.raises(ValueError):
            IntelRecord.parse('Hello, World!')

        with pytest.raises(ValueError):
            IntelRecord.parse(':01000001FF')

    def test_split_doctest(self):
        pass  # TODO

    def test_split(self):
        with pytest.raises(ValueError):
            list(IntelRecord.split(BYTES, address=-1))

        with pytest.raises(ValueError):
            list(IntelRecord.split(BYTES, address=(1 << 32)))

        with pytest.raises(ValueError):
            list(IntelRecord.split(BYTES, address=((1 << 32) - 128)))

        with pytest.raises(ValueError):
            list(IntelRecord.split(BYTES, columns=256))

        ans_out = list(IntelRecord.split(HEXBYTES, address=0x12345678))
        ans_ref = [
            IntelRecord(0, IntelTag.EXTENDED_LINEAR_ADDRESS, b'\x124'),
            IntelRecord(0x12345678, IntelTag.DATA,
                        b'\x00\x01\x02\x03\x04\x05\x06\x07'),
            IntelRecord(0x12345680, IntelTag.DATA,
                        b'\x08\t\n\x0b\x0c\r\x0e\x0f'),
            IntelRecord(0, IntelTag.EXTENDED_LINEAR_ADDRESS, b'\x00\x00'),
            IntelRecord(0, IntelTag.START_LINEAR_ADDRESS, b'\x124Vx'),
            IntelRecord(0, IntelTag.END_OF_FILE, b''),
        ]
        assert ans_out == ans_ref

        ans_out = list(IntelRecord.split(HEXBYTES, address=0x0000FFF8))
        ans_ref = [
            IntelRecord(0xFFF8, IntelTag.DATA,
                        b'\x00\x01\x02\x03\x04\x05\x06\x07'),
            IntelRecord(0, IntelTag.EXTENDED_LINEAR_ADDRESS, b'\x00\x01'),
            IntelRecord(0x10000, IntelTag.DATA, b'\x08\t\n\x0b\x0c\r\x0e\x0f'),
            IntelRecord(0, IntelTag.EXTENDED_LINEAR_ADDRESS, b'\x00\x00'),
            IntelRecord(0, IntelTag.START_LINEAR_ADDRESS, b'\x00\x00\xff\xf8'),
            IntelRecord(0, IntelTag.END_OF_FILE, b'')
        ]
        assert ans_out == ans_ref

        ans_out = list(IntelRecord.split(HEXBYTES, address=0x0000FFF8,
                                         align=False))
        assert ans_out == ans_ref

    def test_build_standalone(self):
        ans_out = list(IntelRecord.build_standalone([], start=0))
        ans_ref = [
            IntelRecord(0, IntelTag.EXTENDED_LINEAR_ADDRESS, b'\x00\x00'),
            IntelRecord(0, IntelTag.START_LINEAR_ADDRESS, b'\x00\x00\x00\x00'),
            IntelRecord(0, IntelTag.END_OF_FILE, b''),
        ]
        assert ans_out == ans_ref

        data_records = [IntelRecord.build_data(0x1234, HEXBYTES)]
        ans_out = list(IntelRecord.build_standalone(data_records))
        ans_ref = [
            IntelRecord(0x1234, IntelTag.DATA, HEXBYTES),
            IntelRecord(0, IntelTag.EXTENDED_LINEAR_ADDRESS, b'\x00\x00'),
            IntelRecord(0, IntelTag.START_LINEAR_ADDRESS, b'\x00\x00\x12\x34'),
            IntelRecord(0, IntelTag.END_OF_FILE, b''),
        ]
        assert ans_out == ans_ref

    def test_terminate_doctest(self):
        ans_out = list(map(str, IntelRecord.terminate(0x12345678)))
        ans_ref = [':020000040000FA', ':0400000512345678E3', ':00000001FF']
        assert ans_out == ans_ref

    def test_readdress_doctest(self):
        ans_out = [
            IntelRecord.build_extended_linear_address(0x76540000),
            IntelRecord.build_data(0x00003210, b'Hello, World!'),
        ]
        IntelRecord.readdress(ans_out)
        ans_ref = [
            IntelRecord(0x76540000, IntelTag.EXTENDED_LINEAR_ADDRESS, b'vT'),
            IntelRecord(0x76543210, IntelTag.DATA, b'Hello, World!'),
        ]
        assert ans_out == ans_ref

    def test_readdress(self):
        ans_out = [
            IntelRecord.build_extended_segment_address(0x76540000),
            IntelRecord.build_data(0x00001000, b'Hello, World!'),
        ]
        IntelRecord.readdress(ans_out)
        ans_ref = [
            IntelRecord(0x00007650, IntelTag.EXTENDED_SEGMENT_ADDRESS,
                        b'\x07\x65'),
            IntelRecord(0x00008650, IntelTag.DATA, b'Hello, World!'),
        ]
        assert ans_out == ans_ref

    def test_load(self, datapath):
        path_ref = datapath / 'bytes.hex'
        ans_out = list(IntelRecord.load(str(path_ref)))
        ans_ref = list(IntelRecord.split(BYTES))
        assert ans_out == ans_ref

    def test_save(self, tmppath, datapath):
        path_out = tmppath / 'bytes.hex'
        path_ref = datapath / 'bytes.hex'
        records = list(IntelRecord.split(BYTES))
        IntelRecord.save(str(path_out), records)
        ans_out = read_text(path_out)
        ans_ref = read_text(path_ref)
        assert ans_out == ans_ref

# ============================================================================

class TestTektronixTag(object):

    def test_is_data(self):
        DATA_INTS = {6}
        for tag in TektronixTag:
            assert TektronixTag.is_data(tag) == (tag in DATA_INTS)
            assert TektronixTag.is_data(int(tag)) == (tag in DATA_INTS)

# ============================================================================

class TestTektronixRecord(object):

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
        record = TektronixRecord.build_terminator(0)
        record.data = b'Hello, World!'
        record.update_count()
        record.update_checksum()
        with pytest.raises(ValueError): record.check()

        record = TektronixRecord.build_data(0, b'Hello, World!')
        record.count += 1
        record.update_checksum()
        with pytest.raises(ValueError): record.check()

        record = TektronixRecord.build_data(0, b'Hello, World!')
        record.check()
        for tag in range(256):
            if tag not in (6, 8):
                record.tag = tag
                with pytest.raises(ValueError): record.check()

    def test_parse_doctest(self):
        pass  # TODO

    def test_parse(self):
        with pytest.raises(ValueError):
            TektronixRecord.parse('Hello, World!')

    def test_build_data_doctest(self):
        ans_out = str(TektronixRecord.build_data(0x12345678,
                                                 b'Hello, World!'))
        ans_ref = '%236E081234567848656C6C6F2C20576F726C6421'
        assert ans_out == ans_ref

    def test_build_terminator_doctest(self):
        ans_out = str(TektronixRecord.build_terminator(0x12345678))
        ans_ref = '%0983D812345678'
        assert ans_out == ans_ref

    def test_split(self):
        with pytest.raises(ValueError):
            list(TektronixRecord.split(BYTES, address=-1))

        with pytest.raises(ValueError):
            list(TektronixRecord.split(BYTES, address=(1 << 32)))

        with pytest.raises(ValueError):
            list(TektronixRecord.split(BYTES, address=((1 << 32) - 128)))

        with pytest.raises(ValueError):
            list(TektronixRecord.split(BYTES, columns=129))

        ans_out = list(TektronixRecord.split(HEXBYTES))
        ans_ref = [
            TektronixRecord(0, TektronixTag.DATA, HEXBYTES),
            TektronixRecord(0, TektronixTag.TERMINATOR, b''),
        ]
        assert ans_out == ans_ref

    def test_build_standalone(self):
        ans_out = list(TektronixRecord.build_standalone([], start=0))
        ans_ref = [TektronixRecord(0, TektronixTag.TERMINATOR, b'')]
        assert ans_out == ans_ref

        data_records = [TektronixRecord.build_data(0x1234, b'Hello, World!')]
        ans_out = list(TektronixRecord.build_standalone(data_records))
        ans_ref = [
            TektronixRecord(0x1234, TektronixTag.DATA, b'Hello, World!'),
            TektronixRecord(0x1234, TektronixTag.TERMINATOR, b''),
        ]
        assert ans_out == ans_ref

    def test_check_sequence_doctest(self):
        pass  # TODO

    def test_check_sequence(self):
        pass  # TODO

    def test_load(self, datapath):
        path_ref = datapath / 'bytes.tek'
        ans_out = list(TektronixRecord.load(str(path_ref)))
        ans_ref = list(TektronixRecord.split(BYTES))
        assert ans_out == ans_ref

    def test_save(self, tmppath, datapath):
        path_out = tmppath / 'bytes.tek'
        path_ref = datapath / 'bytes.tek'
        records = list(TektronixRecord.split(BYTES))
        TektronixRecord.save(str(path_out), records)
        ans_out = read_text(path_out)
        ans_ref = read_text(path_ref)
        assert ans_out == ans_ref

# ============================================================================

def test_find_record_type():
    for name, record_type in six.iteritems(RECORD_TYPES):
        for ext in record_type.EXTENSIONS:
            assert find_record_type('filename' + ext.lower()) == name
            assert find_record_type('filename' + ext.upper()) == name

    with pytest.raises(KeyError):
        find_record_type('filename.invalid')
