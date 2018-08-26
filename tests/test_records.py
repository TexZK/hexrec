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

@pytest.fixture(scope='module')
def datadir(request):
    dir_path, _ = os.path.splitext(request.module.__file__)
    assert os.path.isdir(str(dir_path))
    return dir_path

# ============================================================================

@pytest.mark.skip
def read_bytes(path):
    path = str(path)
    with open(path, 'rb') as file:
        data = file.read()
    return data

# ============================================================================

@pytest.mark.skip
def read_text(path):
    path = str(path)
    with open(path, 'rt') as file:
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

def test_get_data_records_doctest():
    data = bytes(bytearray(range(256)))
    blocks = list(chop_blocks(data, 16))
    records = blocks_to_records(blocks, MotorolaRecord)
    assert all(r.is_data() for r in get_data_records(records))

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
    motorola = list(MotorolaRecord.split(bytes(range(256))))
    intel = list(IntelRecord.split(bytes(range(256))))
    converted = convert_records(motorola, output_type=IntelRecord)
    assert converted == intel

    motorola = list(MotorolaRecord.split(bytes(range(256))))
    intel = list(IntelRecord.split(bytes(range(256))))
    converted = convert_records(intel, output_type=MotorolaRecord)
    assert converted == motorola

# ============================================================================

def test_merge_files_doctest():
    pass  # TODO

# ============================================================================

def test_convert_file_doctest(tmpdir):
    path_mot = str(Path(str(tmpdir)) / 'bytes.mot')
    path_hex = str(Path(str(tmpdir)) / 'bytes.hex')
    motorola = list(MotorolaRecord.split(bytes(range(256))))
    intel = list(IntelRecord.split(bytes(range(256))))
    save_records(path_mot, motorola)
    convert_file(path_mot, path_hex)
    ans_out = load_records(path_hex)
    ans_ref = intel
    assert ans_out == ans_ref

# ============================================================================

def test_load_records_doctest(tmpdir):
    path = str(Path(str(tmpdir)) / 'bytes.mot')
    records = list(MotorolaRecord.split(bytes(range(256))))
    save_records(path, records)
    ans_out = load_records(path)
    ans_ref = records
    assert ans_out == ans_ref

# ============================================================================

def test_save_records_doctest(tmpdir):
    path = str(Path(str(tmpdir)) / 'bytes.hex')
    records = list(IntelRecord.split(bytes(range(256))))
    save_records(path, records)
    ans_out = load_records(path)
    ans_ref = records
    assert ans_out == ans_ref

# ============================================================================

def test_load_blocks_doctest(tmpdir):
    path = str(Path(str(tmpdir)) / 'bytes.mot')
    blocks = [(offset, bytes(bytearray(range(offset, offset + 16))))
              for offset in range(0, 256, 16)]
    save_blocks(path, blocks)
    ans_out = load_blocks(path)
    ans_ref = merge(blocks)
    assert ans_out == ans_ref

# ============================================================================

def test_save_blocks_doctest(tmpdir):
    path = str(Path(str(tmpdir)) / 'bytes.hex')
    blocks = [(offset, bytes(bytearray(range(offset, offset + 16))))
              for offset in range(0, 256, 16)]
    save_blocks(path, blocks)
    ans_out = load_blocks(path)
    ans_ref = merge(blocks)
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

    def test___eq___doctest(self):
        pass  # TODO

    def test___eq__(self):
        pass  # TODO

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

    def test___copy___doctest(self):
        pass  # TODO

    def test___copy__(self):
        pass  # TODO

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

    def test_check_doctest(self):
        pass  # TODO

    def test_check(self):
        pass  # TODO

    def test_overlaps_doctest(self):
        record1 = BinaryRecord(0, 0, b'abc')
        record2 = BinaryRecord(1, 0, b'def')
        assert record1.overlaps(record2) == True

        record1 = BinaryRecord(0, 0, b'abc')
        record2 = BinaryRecord(3, 0, b'def')
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

    def test_check_sequence_doctest(self):
        pass  # TODO

    def test_check_sequence(self):
        pass  # TODO

    def test_readdress(self):
        pass

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

    def test_load(self, datadir):
        path_ref = Path(str(datadir)) / 'hexbytes.bin'
        ans_out = list(BinaryRecord.load(str(path_ref)))
        ans_ref = [BinaryRecord.build_data(0, HEXBYTES)]
        assert ans_out == ans_ref

    def test_save(self, tmpdir, datadir):
        path_out = Path(str(tmpdir)) / 'hexbytes.bin'
        path_ref = Path(str(datadir)) / 'hexbytes.bin'
        records = [BinaryRecord.build_data(0, HEXBYTES)]
        BinaryRecord.save(str(path_out), records)
        ans_out = read_bytes(path_out)
        ans_ref = read_bytes(path_ref)
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
        pass  # TODO

    def test_fit_data_tag_doctest(self):
        pass  # TODO

    def test_fit_data_tag(self):
        pass  # TODO

    def test_fit_count_tag_doctest(self):
        pass  # TODO

    def test_fit_count_tag(self):
        pass  # TODO

    def test_build_header_doctest(self):
        pass  # TODO

    def test_build_header_tag(self):
        pass  # TODO

    def test_build_data_doctest(self):
        pass  # TODO

    def test_build_data_tag(self):
        pass  # TODO

    def test_build_terminator_doctest(self):
        pass  # TODO

    def test_build_terminator_tag(self):
        pass  # TODO

    def test_build_count_doctest(self):
        pass  # TODO

    def test_build_count_tag(self):
        pass  # TODO

    def test_parse_doctest(self):
        pass  # TODO

    def test_parse(self):
        pass  # TODO

    def test_build_standalone_doctest(self):
        pass  # TODO

    def test_build_standalone(self):
        pass  # TODO

    def test_check_sequence_doctest(self):
        pass  # TODO

    def test_check_sequence(self):
        pass  # TODO

    def test_split_doctest(self):
        pass  # TODO

    def test_split(self):
        pass  # TODO

    def test_fix_tags_doctest(self):
        pass  # TODO

    def test_fix_tags(self):
        pass  # TODO

    def test_load(self, datadir):
        path_ref = Path(str(datadir)) / 'bytes.mot'
        ans_out = list(MotorolaRecord.load(str(path_ref)))
        ans_ref = list(MotorolaRecord.split(BYTES))
        assert ans_out == ans_ref

    def test_save(self, tmpdir, datadir):
        path_out = Path(str(tmpdir)) / 'bytes.mot'
        path_ref = Path(str(datadir)) / 'bytes.mot'
        records = list(MotorolaRecord.split(BYTES))
        MotorolaRecord.save(str(path_out), records)
        ans_out = read_bytes(path_out)
        ans_ref = read_bytes(path_ref)
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
        pass  # TODO

    def test_build_data_doctest(self):
        pass  # TODO

    def test_build_data(self):
        pass  # TODO

    def test_build_extended_segment_addres_doctest(self):
        pass  # TODO

    def test_build_extended_segment_addres(self):
        pass  # TODO

    def test_build_start_segment_address_doctest(self):
        pass  # TODO

    def test_build_start_segment_address(self):
        pass  # TODO

    def test_build_end_of_file_doctest(self):
        pass  # TODO

    def test_build_end_of_file(self):
        pass  # TODO

    def test_build_extended_linear_address_doctest(self):
        pass  # TODO

    def test_build_extended_linear_address(self):
        pass  # TODO

    def test_build_start_linear_address_doctest(self):
        pass  # TODO

    def test_build_start_linear_address(self):
        pass  # TODO

    def test_parse_doctest(self):
        pass  # TODO

    def test_parse(self):
        pass  # TODO

    def test_split_doctest(self):
        pass  # TODO

    def test_split(self):
        pass  # TODO

    def test_build_standalone_doctest(self):
        pass  # TODO

    def test_build_standalone(self):
        pass  # TODO

    def test_terminate_doctest(self):
        pass  # TODO

    def test_terminate(self):
        pass  # TODO

    def test_readdress_doctest(self):
        pass  # TODO

    def test_readdress(self):
        pass  # TODO

    def test_load(self, datadir):
        path_ref = Path(str(datadir)) / 'bytes.hex'
        ans_out = list(IntelRecord.load(str(path_ref)))
        ans_ref = list(IntelRecord.split(BYTES))
        assert ans_out == ans_ref

    def test_save(self, tmpdir, datadir):
        path_out = Path(str(tmpdir)) / 'bytes.hex'
        path_ref = Path(str(datadir)) / 'bytes.hex'
        records = list(IntelRecord.split(BYTES))
        IntelRecord.save(str(path_out), records)
        ans_out = read_bytes(path_out)
        ans_ref = read_bytes(path_ref)
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

    def test_check_doctest(self):
        pass  # TODO

    def test_check(self):
        pass  # TODO

    def test_parse_doctest(self):
        pass  # TODO

    def test_parse(self):
        pass  # TODO

    def test_build_data_doctest(self):
        pass  # TODO

    def test_build_data(self):
        pass  # TODO

    def test_build_terminator_doctest(self):
        pass  # TODO

    def test_build_terminator(self):
        pass  # TODO

    def test_split_doctest(self):
        pass  # TODO

    def test_split(self):
        pass  # TODO

    def test_build_standalone_doctest(self):
        pass  # TODO

    def test_build_standalone(self):
        pass  # TODO

    def test_check_sequence_doctest(self):
        pass  # TODO

    def test_check_sequence(self):
        pass  # TODO

    def test_load(self, datadir):
        path_ref = Path(str(datadir)) / 'bytes.tek'
        ans_out = list(TektronixRecord.load(str(path_ref)))
        ans_ref = list(TektronixRecord.split(BYTES))
        assert ans_out == ans_ref

    def test_save(self, tmpdir, datadir):
        path_out = Path(str(tmpdir)) / 'bytes.tek'
        path_ref = Path(str(datadir)) / 'bytes.tek'
        records = list(TektronixRecord.split(BYTES))
        TektronixRecord.save(str(path_out), records)
        ans_out = read_bytes(path_out)
        ans_ref = read_bytes(path_ref)
        assert ans_out == ans_ref

# ============================================================================

def test_find_record_type():
    for name, record_type in six.iteritems(RECORD_TYPES):
        for ext in record_type.EXTENSIONS:
            assert find_record_type('filename' + ext.lower()) == name
            assert find_record_type('filename' + ext.upper()) == name

    with pytest.raises(KeyError):
        find_record_type('filename.invalid')
