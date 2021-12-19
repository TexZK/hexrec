# -*- coding: utf-8 -*-
import io
import os
from pathlib import Path

import pytest

from hexrec.blocks import Memory
from hexrec.blocks import chop_blocks
from hexrec.blocks import merge
from hexrec.formats.binary import Record as BinaryRecord
from hexrec.formats.intel import Record as IntelRecord
from hexrec.formats.intel import Tag as IntelTag
from hexrec.formats.motorola import Record as MotorolaRecord
from hexrec.formats.motorola import Tag as MotorolaTag
from hexrec.formats.tektronix import Record as TektronixRecord
from hexrec.records import RECORD_TYPES
from hexrec.records import Record
from hexrec.records import Tag
from hexrec.records import blocks_to_records
from hexrec.records import convert_file
from hexrec.records import convert_records
from hexrec.records import find_corrupted_records
from hexrec.records import find_record_type
from hexrec.records import find_record_type_name
from hexrec.records import get_data_records
from hexrec.records import get_max_data_length
from hexrec.records import load_blocks
from hexrec.records import load_memory
from hexrec.records import load_records
from hexrec.records import merge_files
from hexrec.records import merge_records
from hexrec.records import records_to_blocks
from hexrec.records import save_blocks
from hexrec.records import save_chunk
from hexrec.records import save_memory
from hexrec.records import save_records

BYTES = bytes(range(256))


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

def test_get_data_records_doctest():
    data = bytes(range(256))
    blocks = list(chop_blocks(data, 16))
    records = blocks_to_records(blocks, MotorolaRecord)
    assert all(r.is_data() for r in get_data_records(records))


# ============================================================================

def test_get_max_data_length_doctest():
    data = bytes(range(256))
    blocks = list(chop_blocks(data, 16))
    records = blocks_to_records(blocks, MotorolaRecord)
    data_records = get_data_records(records)
    assert get_max_data_length(data_records) == 16


# ============================================================================

def test_find_corrupted_records_doctest():
    data = bytes(range(256))
    records = list(MotorolaRecord.split(data))
    records[3].checksum ^= 0xFF
    records[5].checksum ^= 0xFF
    records[7].checksum ^= 0xFF
    ans_out = find_corrupted_records(records)
    ans_ref = [3, 5, 7]
    assert ans_out == ans_ref


# ============================================================================

def test_records_to_blocks_doctest():
    data = bytes(range(256))
    blocks = list(chop_blocks(data, 16))
    records = blocks_to_records(blocks, MotorolaRecord)
    ans_ref = merge(blocks)
    ans_out = records_to_blocks(records)
    assert ans_ref == ans_out


# ============================================================================

def test_blocks_to_records_doctest():
    data = bytes(range(256))
    blocks = list(chop_blocks(data, 16))
    records = blocks_to_records(blocks, MotorolaRecord)
    ans_ref = merge(blocks)
    ans_out = records_to_blocks(records)
    assert ans_ref == ans_out


# ============================================================================

def test_merge_records_doctest():
    data1 = bytes(range(0, 32))
    data2 = bytes(range(96, 128))
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
    blocks = [(offset, bytes(range(offset, offset + 16)))
              for offset in range(0, 256, 16)]
    save_blocks(path, blocks)
    ans_out = load_blocks(path)
    ans_ref = merge(blocks)
    assert ans_out == ans_ref


def test_load_blocks(tmppath):
    path = str(tmppath / 'bytes.mot')
    blocks = [(offset, bytes(range(offset, offset + 16)))
              for offset in range(0, 256, 16)]
    save_blocks(path, blocks)
    ans_out = load_blocks(path, MotorolaRecord)
    ans_ref = merge(blocks)
    assert ans_out == ans_ref


# ============================================================================

def test_save_blocks_doctest(tmppath):
    path = str(tmppath / 'bytes.hex')
    blocks = [(offset, bytes(range(offset, offset + 16)))
              for offset in range(0, 256, 16)]
    save_blocks(path, blocks)
    ans_out = load_blocks(path)
    ans_ref = merge(blocks)
    assert ans_out == ans_ref


def test_save_blocks(tmppath):
    path = str(tmppath / 'bytes.hex')
    blocks = [(offset, bytes(range(offset, offset + 16)))
              for offset in range(0, 256, 16)]
    save_blocks(path, blocks, IntelRecord)
    ans_out = load_blocks(path)
    ans_ref = merge(blocks)
    assert ans_out == ans_ref


# ============================================================================

def test_load_memory_doctest(tmppath):
    path = str(tmppath / 'bytes.mot')
    blocks = [(offset, bytes(range(offset, offset + 16)))
              for offset in range(0, 256, 16)]
    sparse_items = Memory(blocks=blocks)
    save_memory(path, sparse_items)
    ans_out = load_memory(path)
    ans_ref = sparse_items
    assert ans_out == ans_ref


# ============================================================================

def test_save_memory_doctest(tmppath):
    path = str(tmppath / 'bytes.hex')
    blocks = [(offset, bytes(range(offset, offset + 16)))
              for offset in range(0, 256, 16)]
    sparse_items = Memory(blocks=blocks)
    save_memory(path, sparse_items)
    ans_out = load_memory(path)
    ans_ref = sparse_items
    assert ans_out == ans_ref


# ============================================================================

def test_save_chunk_doctest(tmppath):
    path = str(tmppath / 'bytes.mot')
    data = bytes(range(256))
    save_chunk(path, data, 0x12345678)
    ans_out = load_blocks(path)
    ans_ref = [(0x12345678, data)]
    assert ans_out == ans_ref


# ============================================================================

class TestTag:

    def test_is_data(self):
        assert Tag.is_data(None)


# ============================================================================

class TestRecord:

    def test___init___doctest(self):
        r = BinaryRecord(0x1234, None, b'Hello, World!')
        ans_out = normalize_whitespace(repr(r))
        ans_ref = normalize_whitespace('''
        Record(address=0x00001234, tag=None, count=13,
               data=b'Hello, World!', checksum=0x69)
        ''')
        assert ans_out == ans_ref

        r = MotorolaRecord(0x1234, MotorolaTag.DATA_16, b'Hello, World!')
        ans_out = normalize_whitespace(repr(r))
        ans_ref = normalize_whitespace('''
        Record(address=0x00001234, tag=<Tag.DATA_16: 1>,
               count=16, data=b'Hello, World!', checksum=0x40)
        ''')
        assert ans_out == ans_ref

        r = IntelRecord(0x1234, IntelTag.DATA, b'Hello, World!')
        ans_out = normalize_whitespace(repr(r))
        ans_ref = normalize_whitespace('''
        Record(address=0x00001234, tag=<Tag.DATA: 0>, count=13,
               data=b'Hello, World!', checksum=0x44)
        ''')
        assert ans_out == ans_ref

    def test___str___doctest(self):
        ans_out = str(BinaryRecord(0x1234, None, b'Hello, World!'))
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
        ans_out = str(Record(0x1234, None, b'Hello, World!'))
        ans_out = normalize_whitespace(ans_out)
        ans_ref = ("Record(address=0x00001234, tag=None, count=13, "
                   "data=b'Hello, World!', checksum=0x69)")
        ans_ref = normalize_whitespace(ans_ref)
        assert ans_out == ans_ref

    def test___eq___doctest(self):
        record1 = BinaryRecord.build_data(0, b'Hello, World!')
        record2 = BinaryRecord.build_data(0, b'Hello, World!')
        assert record1 == record2

        record1 = BinaryRecord.build_data(0, b'Hello, World!')
        record2 = BinaryRecord.build_data(1, b'Hello, World!')
        assert record1 != record2

        record1 = BinaryRecord.build_data(0, b'Hello, World!')
        record2 = BinaryRecord.build_data(0, b'hello, world!')
        assert record1 != record2

        record1 = MotorolaRecord.build_header(b'Hello, World!')
        record2 = MotorolaRecord.build_data(0, b'hello, world!')
        assert record1 != record2

    def test___hash__(self):
        hash(BinaryRecord(0x1234, None, b'Hello, World!'))
        hash(MotorolaRecord(0x1234, MotorolaTag.DATA_16, b'Hello, World!'))
        hash(IntelRecord(0x1234, IntelTag.DATA, b'Hello, World!'))

    def test___lt___doctest(self):
        record1 = BinaryRecord(0x1234, None, b'')
        record2 = BinaryRecord(0x4321, None, b'')
        assert (record1 < record2)

        record1 = BinaryRecord(0x4321, None, b'')
        record2 = BinaryRecord(0x1234, None, b'')
        assert not (record1 < record2)

    def test_is_data_doctest(self):
        record = BinaryRecord(0, None, b'Hello, World!')
        assert record.is_data()

        record = MotorolaRecord(0, MotorolaTag.DATA_16, b'Hello, World!')
        assert record.is_data()

        record = MotorolaRecord(0, MotorolaTag.HEADER, b'Hello, World!')
        assert not record.is_data()

        record = IntelRecord(0, IntelTag.DATA, b'Hello, World!')
        assert record.is_data()

        record = IntelRecord(0, IntelTag.END_OF_FILE, b'')
        assert not record.is_data()

    def test_compute_count_doctest(self):
        record = BinaryRecord(0, None, b'Hello, World!')
        assert str(record) == '48656C6C6F2C20576F726C6421'
        assert record.compute_count() == 13

        record = MotorolaRecord(0, MotorolaTag.DATA_16, b'Hello, World!')
        assert str(record) == 'S110000048656C6C6F2C20576F726C642186'
        assert record.compute_count() == 16

        record = IntelRecord(0, IntelTag.DATA, b'Hello, World!')
        assert str(record) == ':0D00000048656C6C6F2C20576F726C64218A'
        assert record.compute_count() == 13

    def test_update_count(self):
        record = BinaryRecord(0, None, b'Hello, World!')
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
        record = BinaryRecord(0, None, b'Hello, World!')
        assert str(record) == '48656C6C6F2C20576F726C6421'
        assert hex(record.compute_checksum()) == '0x69'

        record = MotorolaRecord(0, MotorolaTag.DATA_16, b'Hello, World!')
        assert str(record) == 'S110000048656C6C6F2C20576F726C642186'
        assert hex(record.compute_checksum()) == '0x86'

        record = IntelRecord(0, IntelTag.DATA, b'Hello, World!')
        assert str(record) == ':0D00000048656C6C6F2C20576F726C64218A'
        assert hex(record.compute_checksum()) == '0x8a'

    def test_update_checksum(self):
        record = BinaryRecord(0, None, b'Hello, World!')
        record.checksum = None
        record.update_checksum()
        assert str(record) == '48656C6C6F2C20576F726C6421'
        assert hex(record.checksum or -1) == '0x69'

        record = MotorolaRecord(0, MotorolaTag.DATA_16, b'Hello, World!')
        record.checksum = None
        record.update_checksum()
        assert str(record) == 'S110000048656C6C6F2C20576F726C642186'
        assert hex(record.checksum or -1) == '0x86'

        record = IntelRecord(0, IntelTag.DATA, b'Hello, World!')
        record.checksum = None
        record.update_checksum()
        assert str(record) == ':0D00000048656C6C6F2C20576F726C64218A'
        assert hex(record.checksum or -1) == '0x8a'

    def test_check(self):
        with pytest.raises(ValueError):
            Record(-1, 0, b'Hello, World!').check()

        with pytest.raises(ValueError):
            Record(0, -1, b'Hello, World!').check()

        with pytest.raises(ValueError):
            Record(0, 256, b'Hello, World!').check()

        record = Record(0, None, b'')
        record.data = None
        with pytest.raises(ValueError):
            record.check()

        record = Record(0, None, b'#' * 256)
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

    def test__get_checksum(self):
        record = BinaryRecord(0, None, b'Hello, World!')
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
        record1 = BinaryRecord(0, None, b'abc')
        record2 = BinaryRecord(1, None, b'def')
        assert record1.overlaps(record2)

        record1 = BinaryRecord(0, None, b'abc')
        record2 = BinaryRecord(3, None, b'def')
        assert not record1.overlaps(record2)

    def test_overlaps(self):
        record1 = BinaryRecord(0, None, b'abc')
        record1.address = None
        record2 = BinaryRecord(3, None, b'def')
        assert not record1.overlaps(record2)

        record1 = BinaryRecord(0, None, b'abc')
        record2 = BinaryRecord(3, None, b'def')
        record2.address = None
        assert not record1.overlaps(record2)

    def test_parse_record(self):
        with pytest.raises(NotImplementedError):
            Record.parse_record('')

    def test_get_metadata_doctest(self):
        pass  # TODO

    def test_get_metadata(self):
        ans_out = Record.get_metadata([])
        ans_ref = dict(columns=0)
        assert ans_out == ans_ref

        data = bytes(range(256))
        records = list(MotorolaRecord.split(data))
        ans_out = Record.get_metadata(records)
        ans_ref = dict(columns=16)
        assert ans_out == ans_ref

    def test_split(self):
        assert not list(Record.split(b''))

    def test_build_standalone(self):
        data = bytes(range(256))
        blocks = list(chop_blocks(data, 16))
        records = blocks_to_records(blocks, BinaryRecord)
        data_records = get_data_records(records)
        data_records2 = list(BinaryRecord.build_standalone(records))
        assert data_records == data_records2

        with pytest.raises(ValueError, match='unexpected positional arg'):
            next(BinaryRecord.build_standalone((), Ellipsis))

        with pytest.raises(ValueError, match='unexpected keyword arg'):
            next(BinaryRecord.build_standalone((), _=Ellipsis))

    def test_check_sequence(self):
        record1 = BinaryRecord(0, None, b'abc')
        record2 = BinaryRecord(3, None, b'def')
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

    def test_read_blocks_doctest(self):
        blocks = [(0, b'abc'), (16, b'def')]
        stream = io.StringIO()
        MotorolaRecord.write_blocks(stream, blocks)
        stream.seek(0, io.SEEK_SET)
        ans_out = MotorolaRecord.read_blocks(stream)
        ans_ref = blocks
        assert ans_out == ans_ref

    def test_write_blocks_doctest(self):
        blocks = [(0, b'abc'), (16, b'def')]
        stream = io.StringIO()
        MotorolaRecord.write_blocks(stream, blocks)
        ans_out = stream.getvalue()
        ans_ref = ('S0030000FC\n'
                   'S1060000616263D3\n'
                   'S1060010646566BA\n'
                   'S5030002FA\n'
                   'S9030000FC\n')
        assert ans_out == ans_ref

    def test_load_blocks_doctest(self, tmppath):
        path = str(tmppath / 'load_blocks.mot')
        with open(path, 'wt') as f:
            f.write('S0030000FC\n')
            f.write('S1060000616263D3\n')
            f.write('S1060010646566BA\n')
            f.write('S5030002FA\n')
            f.write('S9030000FC\n')
        ans_out = MotorolaRecord.load_blocks(path)
        ans_ref = [(0, b'abc'), (16, b'def')]
        assert ans_out == ans_ref

    def test_save_blocks_doctest(self, tmppath):
        path = str(tmppath / 'save_blocks.mot')
        blocks = [(0, b'abc'), (16, b'def')]
        MotorolaRecord.save_blocks(path, blocks)
        with open(path, 'rt') as f:
            ans_out = f.read()
        ans_ref = ('S0030000FC\n'
                   'S1060000616263D3\n'
                   'S1060010646566BA\n'
                   'S5030002FA\n'
                   'S9030000FC\n')
        assert ans_out == ans_ref

    def test_read_memory_doctest(self):
        blocks = [(0, b'abc'), (16, b'def')]
        stream = io.StringIO()
        MotorolaRecord.write_blocks(stream, blocks)
        stream.seek(0, io.SEEK_SET)
        memory = MotorolaRecord.read_memory(stream)
        ans_out = memory.blocks
        ans_ref = [(0, b'abc'), (16, b'def')]
        assert ans_out == ans_ref

    def test_write_memory_doctest(self):
        memory = Memory(blocks=[(0, b'abc'), (16, b'def')])
        stream = io.StringIO()
        MotorolaRecord.write_memory(stream, memory)
        ans_out = stream.getvalue()
        ans_ref = ('S0030000FC\n'
                   'S1060000616263D3\n'
                   'S1060010646566BA\n'
                   'S5030002FA\n'
                   'S9030000FC\n')
        assert ans_out == ans_ref

    def test_load_memory_doctest(self, tmppath):
        path = str(tmppath / 'load_memory.mot')
        with open(path, 'wt') as f:
            f.write('S0030000FC\n')
            f.write('S1060000616263D3\n')
            f.write('S1060010646566BA\n')
            f.write('S5030002FA\n')
            f.write('S9030000FC\n')
        memory = MotorolaRecord.load_memory(path)
        ans_out = memory.blocks
        ans_ref = [(0, b'abc'), (16, b'def')]
        assert ans_out == ans_ref

    def test_save_memory_doctest(self, tmppath):
        path = str(tmppath / 'save_memory.mot')
        blocks = [(0, b'abc'), (16, b'def')]
        MotorolaRecord.save_blocks(path, blocks)
        with open(path, 'rt') as f:
            ans_out = f.read()
        ans_ref = ('S0030000FC\n'
                   'S1060000616263D3\n'
                   'S1060010646566BA\n'
                   'S5030002FA\n'
                   'S9030000FC\n')
        assert ans_out == ans_ref

    def test_read_records_doctest(self):
        blocks = [(0, b'abc'), (16, b'def')]
        stream = io.StringIO()
        MotorolaRecord.write_blocks(stream, blocks)
        stream.seek(0, io.SEEK_SET)
        records = MotorolaRecord.read_records(stream)
        ans_out = list(map(str, records))
        ans_ref = ['S0030000FC',
                   'S1060000616263D3',
                   'S1060010646566BA',
                   'S5030002FA',
                   'S9030000FC']
        assert ans_out == ans_ref

    def test_write_records_doctest(self):
        blocks = [(0, b'abc'), (16, b'def')]
        records = blocks_to_records(blocks, MotorolaRecord)
        stream = io.StringIO()
        MotorolaRecord.write_records(stream, records)
        ans_out = stream.getvalue()
        ans_ref = ('S0030000FC\n'
                   'S1060000616263D3\n'
                   'S1060010646566BA\n'
                   'S5030002FA\n'
                   'S9030000FC\n')
        assert ans_out == ans_ref

    def test_load_records_doctest(self, tmppath):
        path = str(tmppath / 'load_records.mot')
        with open(path, 'wt') as f:
            f.write('S0030000FC\n')
            f.write('S1060000616263D3\n')
            f.write('S1060010646566BA\n')
            f.write('S5030002FA\n')
            f.write('S9030000FC\n')
        records = MotorolaRecord.load_records(path)
        ans_out = list(map(str, records))
        ans_ref = ['S0030000FC',
                   'S1060000616263D3',
                   'S1060010646566BA',
                   'S5030002FA',
                   'S9030000FC']
        assert ans_out == ans_ref

    def test_save_records_doctest(self, tmppath):
        path = str(tmppath / 'save_records.mot')
        blocks = [(0, b'abc'), (16, b'def')]
        records = blocks_to_records(blocks, MotorolaRecord)
        MotorolaRecord.save_records(path, records)
        with open(path, 'rt') as f:
            ans_out = f.read()
        ans_ref = ('S0030000FC\n'
                   'S1060000616263D3\n'
                   'S1060010646566BA\n'
                   'S5030002FA\n'
                   'S9030000FC\n')
        assert ans_out == ans_ref


# ============================================================================

def test_find_record_type_name_doctest():
    assert find_record_type_name('dummy.mot') == 'motorola'


def test_find_record_type_name():
    for name, record_type in RECORD_TYPES.items():
        for ext in record_type.EXTENSIONS:
            assert find_record_type_name('filename' + ext.lower()) == name
            assert find_record_type_name('filename' + ext.upper()) == name

    with pytest.raises(KeyError):
        find_record_type_name('filename.invalid')


# ============================================================================

def test_find_record_type_doctest():
    assert find_record_type('dummy.mot') is MotorolaRecord
