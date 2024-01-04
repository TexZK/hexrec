# -*- coding: utf-8 -*-
import os
from binascii import unhexlify
from pathlib import Path
from typing import cast as _cast

import pytest
from bytesparse import Memory

from hexrec.formats.intel import IhexFile
from hexrec.formats.intel import IhexRecord
from hexrec.formats.intel import IhexTag
from hexrec.formats.intel import Record
from hexrec.formats.intel import Tag

DATA = IhexTag.DATA
EOF = IhexTag.END_OF_FILE
ESA = IhexTag.EXTENDED_SEGMENT_ADDRESS
SSA = IhexTag.START_SEGMENT_ADDRESS
ELA = IhexTag.EXTENDED_LINEAR_ADDRESS
SLA = IhexTag.START_LINEAR_ADDRESS


# ============================================================================

@pytest.fixture(scope='module')
def datadir(request):
    dir_path, _ = os.path.splitext(request.module.__file__)
    assert os.path.isdir(str(dir_path))
    return dir_path


@pytest.fixture
def datapath(datadir):
    return Path(str(datadir))


# ============================================================================

class TestIhexTag:

    def test_enum(self):
        assert IhexTag.DATA == 0
        assert IhexTag.END_OF_FILE == 1
        assert IhexTag.EXTENDED_SEGMENT_ADDRESS == 2
        assert IhexTag.START_SEGMENT_ADDRESS == 3
        assert IhexTag.EXTENDED_LINEAR_ADDRESS == 4
        assert IhexTag.START_LINEAR_ADDRESS == 5

    def test_is_data(self):
        assert IhexTag.DATA.is_data() is True
        assert IhexTag.END_OF_FILE.is_data() is False
        assert IhexTag.EXTENDED_SEGMENT_ADDRESS.is_data() is False
        assert IhexTag.START_SEGMENT_ADDRESS.is_data() is False
        assert IhexTag.EXTENDED_LINEAR_ADDRESS.is_data() is False
        assert IhexTag.START_LINEAR_ADDRESS.is_data() is False

    def test_is_eof(self):
        assert IhexTag.DATA.is_eof() is False
        assert IhexTag.END_OF_FILE.is_eof() is True
        assert IhexTag.EXTENDED_SEGMENT_ADDRESS.is_eof() is False
        assert IhexTag.START_SEGMENT_ADDRESS.is_eof() is False
        assert IhexTag.EXTENDED_LINEAR_ADDRESS.is_eof() is False
        assert IhexTag.START_LINEAR_ADDRESS.is_eof() is False

    def test_is_start(self):
        assert IhexTag.DATA.is_start() is False
        assert IhexTag.END_OF_FILE.is_start() is False
        assert IhexTag.EXTENDED_SEGMENT_ADDRESS.is_start() is False
        assert IhexTag.START_SEGMENT_ADDRESS.is_start() is True
        assert IhexTag.EXTENDED_LINEAR_ADDRESS.is_start() is False
        assert IhexTag.START_LINEAR_ADDRESS.is_start() is True

    def test_is_extension(self):
        assert IhexTag.DATA.is_extension() is False
        assert IhexTag.END_OF_FILE.is_extension() is False
        assert IhexTag.EXTENDED_SEGMENT_ADDRESS.is_extension() is True
        assert IhexTag.START_SEGMENT_ADDRESS.is_extension() is False
        assert IhexTag.EXTENDED_LINEAR_ADDRESS.is_extension() is True
        assert IhexTag.START_LINEAR_ADDRESS.is_extension() is False


# ============================================================================

class TestIhexRecord:

    def test_build_data(self):
        contents = [
            b'',
            b'abc',
            b'a' * 0xFF,
        ]
        addresses = [
            0x0000,
            0xFFFF,
        ]
        for data in contents:
            for address in addresses:
                record = IhexRecord.build_data(address, data)
                record.validate()
                assert record.tag == IhexTag.DATA
                assert record.address == address
                assert record.count == len(data)
                assert record.data == data

    def test_build_data_raises_address(self):
        addresses = [
            -1,
            0x10000,
        ]
        for address in addresses:
            with pytest.raises(ValueError, match='address overflow'):
                IhexRecord.build_data(address, b'abc')

    def test_build_data_raises_data(self):
        with pytest.raises(ValueError, match='data size overflow'):
            IhexRecord.build_data(0, b'a' * 0x100)

    def test_build_eof(self):
        record = IhexRecord.build_end_of_file()
        record.validate()
        assert record.tag == IhexTag.END_OF_FILE
        assert record.address == 0x0000
        assert record.count == 0x00
        assert record.data == b''

    def test_build_ela(self):
        extensions = [
            0x0000,
            0xFFFF,
        ]
        for extension in extensions:
            record = IhexRecord.build_extended_linear_address(extension)
            record.validate()
            assert record.tag == IhexTag.EXTENDED_LINEAR_ADDRESS
            assert record.address == 0
            assert record.count == 2
            assert record.data == extension.to_bytes(2, byteorder='big', signed=False)
            assert record.data_to_int() == extension

    def test_build_ela_raises_extension(self):
        extensions = [
            -1,
            0x10000,
        ]
        for extension in extensions:
            with pytest.raises(ValueError, match='extension overflow'):
                IhexRecord.build_extended_linear_address(extension)

    def test_build_esa(self):
        extensions = [
            0x0000,
            0xFFFF,
        ]
        for extension in extensions:
            record = IhexRecord.build_extended_segment_address(extension)
            record.validate()
            assert record.tag == IhexTag.EXTENDED_SEGMENT_ADDRESS
            assert record.address == 0
            assert record.count == 2
            assert record.data == extension.to_bytes(2, byteorder='big', signed=False)
            assert record.data_to_int() == extension

    def test_build_esa_raises_extension(self):
        extensions = [
            -1,
            0x10000,
        ]
        for extension in extensions:
            with pytest.raises(ValueError, match='extension overflow'):
                IhexRecord.build_extended_segment_address(extension)

    def test_build_sla(self):
        addresses = [
            0x00000000,
            0xFFFFFFFF,
        ]
        for address in addresses:
            record = IhexRecord.build_start_linear_address(address)
            record.validate()
            assert record.tag == IhexTag.START_LINEAR_ADDRESS
            assert record.address == 0
            assert record.count == 4
            assert record.data == address.to_bytes(4, byteorder='big', signed=False)
            assert record.data_to_int() == address

    def test_build_sla_raises_extension(self):
        addresses = [
            -1,
            0x100000000,
        ]
        for address in addresses:
            with pytest.raises(ValueError, match='address overflow'):
                IhexRecord.build_start_linear_address(address)

    def test_build_ssa(self):
        addresses = [
            0x00000000,
            0xFFFFFFFF,
        ]
        for address in addresses:
            record = IhexRecord.build_start_segment_address(address)
            record.validate()
            assert record.tag == IhexTag.START_SEGMENT_ADDRESS
            assert record.address == 0
            assert record.count == 4
            assert record.data == address.to_bytes(4, byteorder='big', signed=False)
            assert record.data_to_int() == address

    def test_build_ssa_raises_extension(self):
        addresses = [
            -1,
            0x100000000,
        ]
        for address in addresses:
            with pytest.raises(ValueError, match='address overflow'):
                IhexRecord.build_start_segment_address(address)

    # https://en.wikipedia.org/wiki/Intel_HEX#Record_types
    def test_compute_checksum_misc(self):
        vector = [
            (0xA7, b':0B0010006164647265737320676170A7\r\n'),
            (0xFF, b':00000001FF\r\n'),
            (0xEA, b':020000021200EA\r\n'),
            (0xC1, b':0400000300003800C1\r\n'),
            (0xF2, b':020000040800F2\r\n'),
            (0x2A, b':04000005000000CD2A\r\n'),
        ]
        for expected, line in vector:
            record = IhexRecord.parse(line)
            record.validate()
            actual = record.compute_checksum()
            assert actual == expected

    def test_compute_checksum_raises_count(self):
        record = IhexRecord(IhexTag.END_OF_FILE, checksum=None, count=None)
        with pytest.raises(ValueError, match='missing count'):
            record.compute_checksum()

    # https://en.wikipedia.org/wiki/Intel_HEX#Checksum_calculation
    def test_compute_checksum_wikipedia(self):
        line = b':0300300002337A1E\r\n'
        record = IhexRecord.parse(line)
        record.validate()
        checksum = record.compute_checksum()
        assert checksum == 0x1E

    def test_compute_count(self):
        contents = [
            b'',
            b'abc',
            b'a' * 0xFF,
        ]
        addresses = [
            0x0000,
            0xFFFF,
        ]
        for data in contents:
            for address in addresses:
                record = IhexRecord.build_data(address, data)
                record.validate()
                assert record.count == len(data)
                assert record.compute_count() == len(data)

    def test_parse(self):
        lines = [
            b':0000000000\r\n',
            b':00FFFF0002\r\n',
            b':FF000000' + (b'FF' * 0xFF) + b'00\r\n',
            b':FFFFFF00' + (b'FF' * 0xFF) + b'02\r\n',

            b':00000001FF\r\n',
            b':00FFFF0101\r\n',

            b':020000020000FC\r\n',
            b':02FFFF020000FE\r\n',
            b':02000002FFFFFE\r\n',
            b':02FFFF02FFFF00\r\n',

            b':0400000300000000F9\r\n',
            b':04FFFF0300000000FB\r\n',
            b':04000003FFFFFFFFFD\r\n',
            b':04FFFF03FFFFFFFFFF\r\n',

            b':020000040000FA\r\n',
            b':02FFFF040000FC\r\n',
            b':02000004FFFFFC\r\n',
            b':02FFFF04FFFFFE\r\n',

            b':0400000500000000F7\r\n',
            b':04FFFF0500000000F9\r\n',
            b':04000005FFFFFFFFFB\r\n',
            b':04FFFF05FFFFFFFFFD\r\n',
        ]
        records = [
            IhexRecord(DATA, count=0x00, address=0x0000, checksum=0x00, data=b''),
            IhexRecord(DATA, count=0x00, address=0xFFFF, checksum=0x02, data=b''),
            IhexRecord(DATA, count=0xFF, address=0x0000, checksum=0x00, data=(b'\xFF' * 0xFF)),
            IhexRecord(DATA, count=0xFF, address=0xFFFF, checksum=0x02, data=(b'\xFF' * 0xFF)),

            IhexRecord(EOF, count=0x00, address=0x0000, checksum=0xFF, data=b''),
            IhexRecord(EOF, count=0x00, address=0xFFFF, checksum=0x01, data=b''),

            IhexRecord(ESA, count=0x02, address=0x0000, checksum=0xFC, data=b'\x00\x00'),
            IhexRecord(ESA, count=0x02, address=0xFFFF, checksum=0xFE, data=b'\x00\x00'),
            IhexRecord(ESA, count=0x02, address=0x0000, checksum=0xFE, data=b'\xFF\xFF'),
            IhexRecord(ESA, count=0x02, address=0xFFFF, checksum=0x00, data=b'\xFF\xFF'),

            IhexRecord(SSA, count=0x04, address=0x0000, checksum=0xF9, data=b'\x00\x00\x00\x00'),
            IhexRecord(SSA, count=0x04, address=0xFFFF, checksum=0xFB, data=b'\x00\x00\x00\x00'),
            IhexRecord(SSA, count=0x04, address=0x0000, checksum=0xFD, data=b'\xFF\xFF\xFF\xFF'),
            IhexRecord(SSA, count=0x04, address=0xFFFF, checksum=0xFF, data=b'\xFF\xFF\xFF\xFF'),

            IhexRecord(ELA, count=0x02, address=0x0000, checksum=0xFA, data=b'\x00\x00'),
            IhexRecord(ELA, count=0x02, address=0xFFFF, checksum=0xFC, data=b'\x00\x00'),
            IhexRecord(ELA, count=0x02, address=0x0000, checksum=0xFC, data=b'\xFF\xFF'),
            IhexRecord(ELA, count=0x02, address=0xFFFF, checksum=0xFE, data=b'\xFF\xFF'),

            IhexRecord(SLA, count=0x04, address=0x0000, checksum=0xF7, data=b'\x00\x00\x00\x00'),
            IhexRecord(SLA, count=0x04, address=0xFFFF, checksum=0xF9, data=b'\x00\x00\x00\x00'),
            IhexRecord(SLA, count=0x04, address=0x0000, checksum=0xFB, data=b'\xFF\xFF\xFF\xFF'),
            IhexRecord(SLA, count=0x04, address=0xFFFF, checksum=0xFD, data=b'\xFF\xFF\xFF\xFF'),
        ]
        for line, expected in zip(lines, records):
            actual = IhexRecord.parse(line)
            actual.validate()
            expected = _cast(IhexRecord, expected)
            expected.validate()
            assert actual == expected

    def test_parse_raises_syntax(self):
        lines = [
            b'::02000000FFFF00\r\n',
            b':..000000FFFF00\r\n',
            b':02....00FFFF00\r\n',
            b':020000..FFFF00\r\n',
            b':02000000....00\r\n',
            b':00000000..\r\n',
            b':02000000FFFF00\n\r\n',
            b':02000000FFFF00\r\r\n',
        ]
        for line in lines:
            with pytest.raises(ValueError, match='syntax error'):
                IhexRecord.parse(line)

    def test_parse_syntax(self):
        lines = [
            b':02000000FFFF00\r\n',
            b':02000000ffff00\r\n',
            b':02000000FFFF00',
            b':02000000FFFF00 ',
            b':02000000FFFF00\r',
            b':02000000FFFF00\n',
            b':02000000FFFF00 \t\v\r\n',
            b' \t\v\r:02000000FFFF00\r\n',
            b'.:02000000FFFF00\r\n',
            b':02000000FFFF00.\r\n',
        ]
        for line in lines:
            record = IhexRecord.parse(line)
            record.validate()

    # https://en.wikipedia.org/wiki/Intel_HEX#Record_types
    def test_parse_wikipedia(self):
        lines = [
            b':0B0010006164647265737320676170A7\r\n',
            b':00000001FF\r\n',
            b':020000021200EA\r\n',
            b':0400000300003800C1\r\n',
            b':020000040800F2\r\n',
            b':04000005000000CD2A\r\n',
        ]
        records = [
            IhexRecord(DATA, count=0x0B, address=0x0010, checksum=0xA7,
                       data=b'\x61\x64\x64\x72\x65\x73\x73\x20\x67\x61\x70'),
            IhexRecord(EOF, count=0x00, address=0x0000, checksum=0xFF, data=b''),
            IhexRecord(ESA, count=0x02, address=0x0000, checksum=0xEA, data=b'\x12\x00'),
            IhexRecord(SSA, count=0x04, address=0x0000, checksum=0xC1, data=b'\x00\x00\x38\x00'),
            IhexRecord(ELA, count=0x02, address=0x0000, checksum=0xF2, data=b'\x08\x00'),
            IhexRecord(SLA, count=0x04, address=0x0000, checksum=0x2A, data=b'\x00\x00\x00\xCD'),
        ]
        for line, expected in zip(lines, records):
            actual = IhexRecord.parse(line)
            actual.validate()
            expected = _cast(IhexRecord, expected)
            expected.validate()
            assert actual == expected

    def test_to_bytestr(self):
        lines = [
            b':0000000000\r\n',
            b':00FFFF0002\r\n',
            b':FF000000' + (b'FF' * 0xFF) + b'00\r\n',
            b':FFFFFF00' + (b'FF' * 0xFF) + b'02\r\n',

            b':00000001FF\r\n',

            b':020000020000FC\r\n',
            b':02000002FFFFFE\r\n',

            b':0400000300000000F9\r\n',
            b':04000003FFFFFFFFFD\r\n',

            b':020000040000FA\r\n',
            b':02000004FFFFFC\r\n',

            b':0400000500000000F7\r\n',
            b':04000005FFFFFFFFFB\r\n',
        ]
        records = [
            IhexRecord.build_data(0x0000, b''),
            IhexRecord.build_data(0xFFFF, b''),
            IhexRecord.build_data(0x0000, (b'\xFF' * 0xFF)),
            IhexRecord.build_data(0xFFFF, (b'\xFF' * 0xFF)),

            IhexRecord.build_end_of_file(),

            IhexRecord.build_extended_segment_address(0x0000),
            IhexRecord.build_extended_segment_address(0xFFFF),

            IhexRecord.build_start_segment_address(0x00000000),
            IhexRecord.build_start_segment_address(0xFFFFFFFF),

            IhexRecord.build_extended_linear_address(0x0000),
            IhexRecord.build_extended_linear_address(0xFFFF),

            IhexRecord.build_start_linear_address(0x00000000),
            IhexRecord.build_start_linear_address(0xFFFFFFFF),
        ]
        for expected, record in zip(lines, records):
            record = _cast(IhexRecord, record)
            actual = record.to_bytestr()
            assert actual == expected

    def test_to_tokens(self):
        lines = [
            b':0000000000\r\n',
            b':00FFFF0002\r\n',
            b':FF000000' + (b'FF' * 0xFF) + b'00\r\n',
            b':FFFFFF00' + (b'FF' * 0xFF) + b'02\r\n',

            b':00000001FF\r\n',

            b':020000020000FC\r\n',
            b':02000002FFFFFE\r\n',

            b':0400000300000000F9\r\n',
            b':04000003FFFFFFFFFD\r\n',

            b':020000040000FA\r\n',
            b':02000004FFFFFC\r\n',

            b':0400000500000000F7\r\n',
            b':04000005FFFFFFFFFB\r\n',
        ]
        records = [
            IhexRecord.build_data(0x0000, b''),
            IhexRecord.build_data(0xFFFF, b''),
            IhexRecord.build_data(0x0000, (b'\xFF' * 0xFF)),
            IhexRecord.build_data(0xFFFF, (b'\xFF' * 0xFF)),

            IhexRecord.build_end_of_file(),

            IhexRecord.build_extended_segment_address(0x0000),
            IhexRecord.build_extended_segment_address(0xFFFF),

            IhexRecord.build_start_segment_address(0x00000000),
            IhexRecord.build_start_segment_address(0xFFFFFFFF),

            IhexRecord.build_extended_linear_address(0x0000),
            IhexRecord.build_extended_linear_address(0xFFFF),

            IhexRecord.build_start_linear_address(0x00000000),
            IhexRecord.build_start_linear_address(0xFFFFFFFF),
        ]
        keys = [
            'before',
            'begin',
            'count',
            'address',
            'tag',
            'data',
            'checksum',
            'after',
            'end',
        ]
        for expected, record in zip(lines, records):
            record = _cast(IhexRecord, record)
            tokens = record.to_tokens()
            assert all((key in keys) for key in tokens.keys())
            actual = b''.join(tokens.get(key, b'?') for key in keys)
            assert actual == expected

    def test_validate_raises(self):
        matches = [
            # 'junk after',
            'junk before',

            'checksum overflow',
            'checksum overflow',

            'count overflow',
            'count overflow',

            'data size overflow',

            'address overflow',
            'address overflow',

            'extension data size overflow',
            'extension data size overflow',

            'start address data size overflow',
            'start address data size overflow',

            'end of file record data',

            'is not a valid IhexTag',
        ]
        records = [
            # IhexRecord(IhexTag.DATA, after=b'?'),
            IhexRecord(IhexTag.DATA, before=b':'),

            IhexRecord(IhexTag.DATA, checksum=-1),
            IhexRecord(IhexTag.DATA, checksum=0x100),

            IhexRecord(IhexTag.DATA, count=-1),
            IhexRecord(IhexTag.DATA, count=0x100),

            IhexRecord(IhexTag.DATA, data=(b'x' * 0x100), count=0xFF),

            IhexRecord(IhexTag.DATA, address=-1),
            IhexRecord(IhexTag.DATA, address=0x10000),

            IhexRecord(IhexTag.EXTENDED_SEGMENT_ADDRESS, data=b'00000'),
            IhexRecord(IhexTag.EXTENDED_LINEAR_ADDRESS, data=b'00000'),

            IhexRecord(IhexTag.START_SEGMENT_ADDRESS, data=b'000000000'),
            IhexRecord(IhexTag.START_LINEAR_ADDRESS, data=b'000000000'),

            IhexRecord(IhexTag.END_OF_FILE, data=b'0'),

            IhexRecord(_cast(IhexTag, 666)),
        ]
        for match, record in zip(matches, records):
            record = _cast(IhexRecord, record)
            record.compute_checksum = lambda: record.checksum  # fake
            record.compute_count = lambda: record.count  # fake

            with pytest.raises(ValueError, match=match):
                record.validate()

    def test_validate_samples(self):
        records = [
            IhexRecord(DATA, count=0x00, address=0x0000, checksum=0x00, data=b''),
            IhexRecord(DATA, count=0x00, address=0xFFFF, checksum=0x02, data=b''),
            IhexRecord(DATA, count=0xFF, address=0x0000, checksum=0x00, data=(b'\xFF' * 0xFF)),
            IhexRecord(DATA, count=0xFF, address=0xFFFF, checksum=0x02, data=(b'\xFF' * 0xFF)),

            IhexRecord(EOF, count=0x00, address=0x0000, checksum=0xFF, data=b''),
            IhexRecord(EOF, count=0x00, address=0xFFFF, checksum=0x01, data=b''),

            IhexRecord(ESA, count=0x02, address=0x0000, checksum=0xFC, data=b'\x00\x00'),
            IhexRecord(ESA, count=0x02, address=0xFFFF, checksum=0xFE, data=b'\x00\x00'),
            IhexRecord(ESA, count=0x02, address=0x0000, checksum=0xFE, data=b'\xFF\xFF'),
            IhexRecord(ESA, count=0x02, address=0xFFFF, checksum=0x00, data=b'\xFF\xFF'),

            IhexRecord(SSA, count=0x04, address=0x0000, checksum=0xF9, data=b'\x00\x00\x00\x00'),
            IhexRecord(SSA, count=0x04, address=0xFFFF, checksum=0xFB, data=b'\x00\x00\x00\x00'),
            IhexRecord(SSA, count=0x04, address=0x0000, checksum=0xFD, data=b'\xFF\xFF\xFF\xFF'),
            IhexRecord(SSA, count=0x04, address=0xFFFF, checksum=0xFF, data=b'\xFF\xFF\xFF\xFF'),

            IhexRecord(ELA, count=0x02, address=0x0000, checksum=0xFA, data=b'\x00\x00'),
            IhexRecord(ELA, count=0x02, address=0xFFFF, checksum=0xFC, data=b'\x00\x00'),
            IhexRecord(ELA, count=0x02, address=0x0000, checksum=0xFC, data=b'\xFF\xFF'),
            IhexRecord(ELA, count=0x02, address=0xFFFF, checksum=0xFE, data=b'\xFF\xFF'),

            IhexRecord(SLA, count=0x04, address=0x0000, checksum=0xF7, data=b'\x00\x00\x00\x00'),
            IhexRecord(SLA, count=0x04, address=0xFFFF, checksum=0xF9, data=b'\x00\x00\x00\x00'),
            IhexRecord(SLA, count=0x04, address=0x0000, checksum=0xFB, data=b'\xFF\xFF\xFF\xFF'),
            IhexRecord(SLA, count=0x04, address=0xFFFF, checksum=0xFD, data=b'\xFF\xFF\xFF\xFF'),
        ]
        for record in records:
            returned = record.validate()
            assert returned is record


# ============================================================================

class TestIhexFile:

    def test___init__(self):
        file = IhexFile()
        assert file._records is None
        assert file._memory == b''
        assert file._linear is True
        assert file._startaddr is None

    def test_apply_records_linear(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_linear_address(0xABCD),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_linear_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        blocks = [
            [0x00001234, b'abc'],
            [0xABCD4321, b'xyz'],
        ]
        file = IhexFile.from_records(records)
        file = _cast(IhexFile, file)
        file._memory = Memory.from_bytes(b'discarded')
        file.apply_records()
        assert file._memory.to_blocks() == blocks
        assert file._linear is True
        assert file._startaddr == 0x12345678

    def test_apply_records_segment(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_segment_address(0xA000),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_segment_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        blocks = [
            [0x00001234, b'abc'],
            [0x000A4321, b'xyz'],
        ]
        file = IhexFile.from_records(records)
        file = _cast(IhexFile, file)
        file._memory = Memory.from_bytes(b'discarded')
        file.apply_records()
        assert file._memory.to_blocks() == blocks
        assert file._linear is False
        assert file._startaddr == 0x12345678

    def test_apply_records_raises_records(self):
        file = IhexFile()
        with pytest.raises(ValueError, match='records required'):
            file.apply_records()

    def test_linear_getter_linear(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_linear_address(0xABCD),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_linear_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file = _cast(IhexFile, file)
        assert file.linear is True

    def test_linear_getter_segment(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_segment_address(0xA000),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_segment_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file = _cast(IhexFile, file)
        assert file.linear is False

    def test_linear_setter_linear_to_segment(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_linear_address(0xABCD),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_linear_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file = _cast(IhexFile, file)
        assert file.linear is True
        assert file._linear is True
        assert file._records
        file.linear = False
        assert file._records is None
        assert file._linear is False
        assert file.linear is False
        assert file._records is None
        file.linear = False
        assert file._records is None
        assert file._linear is False
        assert file.linear is False
        assert file._records is None

    def test_linear_setter_segmented_to_linear(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_segment_address(0xA000),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_segment_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file = _cast(IhexFile, file)
        assert file.linear is False
        assert file._linear is False
        assert file._records
        file.linear = True
        assert file._records is None
        assert file._linear is True
        assert file.linear is True
        assert file._records is None
        file.linear = True
        assert file._records is None
        assert file._linear is True
        assert file.linear is True
        assert file._records is None

    # https://en.wikipedia.org/wiki/Intel_HEX#File_example
    def test_parse_wikipedia(self, datapath):
        path = str(datapath / 'wikipedia.hex')
        records = [
            IhexRecord(IhexTag.DATA, count=0x10, address=0x0100, checksum=0x40,
                       data=unhexlify(b'214601360121470136007EFE09D21901')),
            IhexRecord(IhexTag.DATA, count=0x10, address=0x0110, checksum=0x28,
                       data=unhexlify(b'2146017E17C20001FF5F160021480119')),
            IhexRecord(IhexTag.DATA, count=0x10, address=0x0120, checksum=0xA7,
                       data=unhexlify(b'194E79234623965778239EDA3F01B2CA')),
            IhexRecord(IhexTag.DATA, count=0x10, address=0x0130, checksum=0xC7,
                       data=unhexlify(b'3F0156702B5E712B722B732146013421')),
            IhexRecord(IhexTag.END_OF_FILE, count=0x00, address=0x0000, checksum=0xFF, data=b''),
        ]
        with open(path, 'rb') as stream:
            file = IhexFile.parse(stream)

        file = _cast(IhexFile, file)
        assert len(file.records) == len(records)

        for actual, expected in zip(file._records, records):
            actual = _cast(IhexRecord, actual)
            expected = _cast(IhexRecord, expected)
            assert actual == expected

    def test_startaddr_getter_linear(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_linear_address(0xABCD),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_linear_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file = _cast(IhexFile, file)
        file._memory = None
        file._startaddr = 0
        assert file.startaddr == 0x12345678
        assert file._memory
        assert file._startaddr == 0x12345678

    def test_startaddr_getter_none(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_linear_address(0xABCD),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file = _cast(IhexFile, file)
        file._memory = None
        file._startaddr = 0
        assert file.startaddr is None
        assert file._memory
        assert file._startaddr is None

    def test_startaddr_getter_segment(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_segment_address(0xA000),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_segment_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file = _cast(IhexFile, file)
        file._memory = None
        file._startaddr = 0
        assert file.startaddr == 0x12345678
        assert file._memory
        assert file._startaddr == 0x12345678

    def test_startaddr_setter_linear(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_segment_address(0xA000),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_segment_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file = _cast(IhexFile, file)
        assert file.startaddr == 0x12345678
        assert file._startaddr == 0x12345678
        assert file._records
        file.startaddr = 0x5678
        assert file._records is None
        assert file._startaddr == 0x5678
        assert file.startaddr == 0x5678
        assert file._records is None
        file.startaddr = 0x5678
        assert file._records is None
        assert file._startaddr == 0x5678
        assert file.startaddr == 0x5678
        assert file._records is None
        file.startaddr = 0x00000000
        assert file._startaddr == 0x00000000
        assert file.startaddr == 0x00000000
        file.startaddr = 0xFFFFFFFF
        assert file._startaddr == 0xFFFFFFFF
        assert file.startaddr == 0xFFFFFFFF

    def test_startaddr_setter_none(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_linear_address(0xABCD),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_linear_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file = _cast(IhexFile, file)
        assert file.startaddr == 0x12345678
        assert file._startaddr == 0x12345678
        assert file._records
        file.startaddr = None
        assert file._records is None
        assert file._startaddr is None
        assert file.startaddr is None
        assert file._records is None
        file.startaddr = 0x5678
        assert file._records is None
        assert file._startaddr == 0x5678
        assert file.startaddr == 0x5678
        assert file._records is None

    def test_startaddr_setter_segment(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_linear_address(0xABCD),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_linear_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file = _cast(IhexFile, file)
        assert file.startaddr == 0x12345678
        assert file._startaddr == 0x12345678
        assert file._records
        file.startaddr = 0x5678
        assert file._records is None
        assert file._startaddr == 0x5678
        assert file.startaddr == 0x5678
        assert file._records is None
        file.startaddr = 0x5678
        assert file._records is None
        assert file._startaddr == 0x5678
        assert file.startaddr == 0x5678
        assert file._records is None
        file.startaddr = 0x00000000
        assert file._startaddr == 0x00000000
        assert file.startaddr == 0x00000000
        file.startaddr = 0xFFFFFFFF
        assert file._startaddr == 0xFFFFFFFF
        assert file.startaddr == 0xFFFFFFFF

    def test_startaddr_setter_raises(self):
        file = IhexFile()
        with pytest.raises(ValueError, match='invalid start address'):
            file.startaddr = -1
        with pytest.raises(ValueError, match='invalid start address'):
            file.startaddr = 0x100000000

    def test_update_records_basic_linear(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_linear_address(0xABCD),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_linear_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        blocks = [
            [0x00001234, b'abc'],
            [0xABCD4321, b'xyz'],
        ]
        memory = Memory.from_blocks(blocks)
        file = IhexFile.from_memory(memory, startaddr=0x12345678, linear=True)
        file = _cast(IhexFile, file)
        file._records = []
        returned = file.update_records(start=True)
        assert returned is file
        assert file._records == records

    def test_update_records_basic_segment(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_segment_address(0xA000),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_segment_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        blocks = [
            [0x00001234, b'abc'],
            [0x000A4321, b'xyz'],
        ]
        memory = Memory.from_blocks(blocks)
        file = IhexFile.from_memory(memory, startaddr=0x12345678, linear=False)
        file = _cast(IhexFile, file)
        file._records = []
        returned = file.update_records(start=True)
        assert returned is file
        assert file._records == records

    def test_update_records_empty(self):
        records = [
            IhexRecord.build_end_of_file(),
        ]
        memory = Memory()
        file = IhexFile.from_memory(memory)
        file = _cast(IhexFile, file)
        file._records = []
        file.update_records(start=False)
        assert file._records == records

    def test_update_records_empty_start_linear(self):
        records = [
            IhexRecord.build_start_linear_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        memory = Memory()
        file = IhexFile.from_memory(memory, startaddr=0x12345678, linear=True)
        file = _cast(IhexFile, file)
        file._records = []
        file.update_records(start=True)
        assert file._records == records

    def test_update_records_empty_start_segment(self):
        records = [
            IhexRecord.build_start_segment_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        memory = Memory()
        file = IhexFile.from_memory(memory, startaddr=0x12345678, linear=False)
        file = _cast(IhexFile, file)
        file._records = []
        file.update_records(start=True)
        assert file._records == records

    def test_update_records_raises_memory(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_linear_address(0xABCD),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_linear_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        with pytest.raises(ValueError, match='memory instance required'):
            file.update_records()

    def test_update_records_raises_segment_overflow(self):
        memory = Memory.from_bytes(b'abc', offset=0x00100000)
        file = IhexFile.from_memory(memory, linear=False)
        with pytest.raises(ValueError, match='segment overflow'):
            file.update_records()

    def test_validate_records_basic_linear(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_linear_address(0xABCD),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_linear_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        returned = file.validate_records(data_ordering=True)
        assert returned is file

    def test_validate_records_basic_segment(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_extended_segment_address(0xA000),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_segment_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        returned = file.validate_records(data_ordering=True)
        assert returned is file

    def test_validate_records_data_ordering(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file.validate_records(data_ordering=True)
        file.validate_records(data_ordering=False)

    def test_validate_records_raises_data_ordering(self):
        records = [
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        with pytest.raises(ValueError, match='unordered data record'):
            file.validate_records(data_ordering=True)

    def test_validate_records_raises_eof_last(self):
        records = [
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_end_of_file(),
            IhexRecord.build_data(0x1234, b'abc'),
        ]
        file = IhexFile.from_records(records)
        with pytest.raises(ValueError, match='end of file record not last'):
            file.validate_records()

    def test_validate_records_raises_eof_missing(self):
        records = [
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_data(0x1234, b'abc'),
        ]
        file = IhexFile.from_records(records)
        with pytest.raises(ValueError, match='missing end of file record'):
            file.validate_records()

    def test_validate_records_raises_records(self):
        file = IhexFile()
        with pytest.raises(ValueError, match='records required'):
            file.validate_records()

    def test_validate_records_raises_start_missing(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        with pytest.raises(ValueError, match='missing start record'):
            file.validate_records(start_required=True)

    def test_validate_records_raises_start_multi(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_segment_address(0x12345678),
            IhexRecord.build_start_segment_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        with pytest.raises(ValueError, match='start record not penultimate'):
            file.validate_records(start_penultimate=True)

    def test_validate_records_raises_start_penultimate(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_start_segment_address(0x12345678),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        with pytest.raises(ValueError, match='start record not penultimate'):
            file.validate_records(start_penultimate=True)

    def test_validate_records_raises_start_within_data(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_segment_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        with pytest.raises(ValueError, match='no data at start address'):
            file.validate_records(start_within_data=True)

    def test_validate_records_start(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_segment_address(0x12345678),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file.validate_records(start_required=True, start_penultimate=True)
        file.validate_records(start_required=True, start_penultimate=False)
        file.validate_records(start_required=False, start_penultimate=True)
        file.validate_records(start_required=False, start_penultimate=False)

    def test_validate_records_start_within_data(self):
        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_start_segment_address(0x1234),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file.validate_records(start_within_data=True)
        file.validate_records(start_within_data=False)

        records = [
            IhexRecord.build_data(0x1234, b'abc'),
            IhexRecord.build_data(0x4321, b'xyz'),
            IhexRecord.build_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file.validate_records(start_within_data=True)
        file.validate_records(start_within_data=False)
