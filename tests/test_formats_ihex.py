import io
import os
from pathlib import Path
from typing import cast as _cast

import pytest
from bytesparse import Memory
from test_base import BaseTestFile
from test_base import BaseTestRecord
from test_base import BaseTestTag
from test_base import replace_stdin
from test_base import replace_stdout

from hexrec.formats.ihex import IhexFile
from hexrec.formats.ihex import IhexRecord
from hexrec.formats.ihex import IhexTag

DATA = IhexTag.DATA
EOF = IhexTag.END_OF_FILE
ESA = IhexTag.EXTENDED_SEGMENT_ADDRESS
SSA = IhexTag.START_SEGMENT_ADDRESS
ELA = IhexTag.EXTENDED_LINEAR_ADDRESS
SLA = IhexTag.START_LINEAR_ADDRESS


@pytest.fixture
def tmppath(tmpdir):  # pragma: no cover
    return Path(str(tmpdir))


@pytest.fixture(scope='module')
def datadir(request):
    dir_path, _ = os.path.splitext(request.module.__file__)
    assert os.path.isdir(str(dir_path))
    return dir_path


@pytest.fixture
def datapath(datadir):
    return Path(str(datadir))


class TestIhexTag(BaseTestTag):

    Tag = IhexTag

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

    def test_is_extension(self):
        assert IhexTag.DATA.is_extension() is False
        assert IhexTag.END_OF_FILE.is_extension() is False
        assert IhexTag.EXTENDED_SEGMENT_ADDRESS.is_extension() is True
        assert IhexTag.START_SEGMENT_ADDRESS.is_extension() is False
        assert IhexTag.EXTENDED_LINEAR_ADDRESS.is_extension() is True
        assert IhexTag.START_LINEAR_ADDRESS.is_extension() is False

    def test_is_file_termination(self):
        assert IhexTag.DATA.is_file_termination() is False
        assert IhexTag.END_OF_FILE.is_file_termination() is True
        assert IhexTag.EXTENDED_SEGMENT_ADDRESS.is_file_termination() is False
        assert IhexTag.START_SEGMENT_ADDRESS.is_file_termination() is False
        assert IhexTag.EXTENDED_LINEAR_ADDRESS.is_file_termination() is False
        assert IhexTag.START_LINEAR_ADDRESS.is_file_termination() is False

    def test_is_start(self):
        assert IhexTag.DATA.is_start() is False
        assert IhexTag.END_OF_FILE.is_start() is False
        assert IhexTag.EXTENDED_SEGMENT_ADDRESS.is_start() is False
        assert IhexTag.START_SEGMENT_ADDRESS.is_start() is True
        assert IhexTag.EXTENDED_LINEAR_ADDRESS.is_start() is False
        assert IhexTag.START_LINEAR_ADDRESS.is_start() is True


class TestIhexRecord(BaseTestRecord):

    Record = IhexRecord

    # https://en.wikipedia.org/wiki/Intel_HEX#Record_types
    def test_compute_checksum(self):
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
                record = IhexRecord.create_data(address, data)
                record.validate()
                assert record.count == len(data)
                assert record.compute_count() == len(data)

    def test_create_data(self):
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
                record = IhexRecord.create_data(address, data)
                record.validate()
                assert record.tag == IhexTag.DATA
                assert record.address == address
                assert record.count == len(data)
                assert record.data == data

    def test_create_data_raises_address(self):
        addresses = [
            -1,
            0x10000,
        ]
        for address in addresses:
            with pytest.raises(ValueError, match='address overflow'):
                IhexRecord.create_data(address, b'abc')

    def test_create_data_raises_data(self):
        with pytest.raises(ValueError, match='data size overflow'):
            IhexRecord.create_data(0, b'a' * 0x100)

    def test_create_eof(self):
        record = IhexRecord.create_end_of_file()
        record.validate()
        assert record.tag == IhexTag.END_OF_FILE
        assert record.address == 0x0000
        assert record.count == 0x00
        assert record.data == b''

    def test_create_ela(self):
        extensions = [
            0x0000,
            0xFFFF,
        ]
        for extension in extensions:
            record = IhexRecord.create_extended_linear_address(extension)
            record.validate()
            assert record.tag == IhexTag.EXTENDED_LINEAR_ADDRESS
            assert record.address == 0
            assert record.count == 2
            assert record.data == extension.to_bytes(2, byteorder='big', signed=False)
            assert record.data_to_int() == extension

    def test_create_ela_raises_extension(self):
        extensions = [
            -1,
            0x10000,
        ]
        for extension in extensions:
            with pytest.raises(ValueError, match='extension overflow'):
                IhexRecord.create_extended_linear_address(extension)

    def test_create_esa(self):
        extensions = [
            0x0000,
            0xFFFF,
        ]
        for extension in extensions:
            record = IhexRecord.create_extended_segment_address(extension)
            record.validate()
            assert record.tag == IhexTag.EXTENDED_SEGMENT_ADDRESS
            assert record.address == 0
            assert record.count == 2
            assert record.data == extension.to_bytes(2, byteorder='big', signed=False)
            assert record.data_to_int() == extension

    def test_create_esa_raises_extension(self):
        extensions = [
            -1,
            0x10000,
        ]
        for extension in extensions:
            with pytest.raises(ValueError, match='extension overflow'):
                IhexRecord.create_extended_segment_address(extension)

    def test_create_sla(self):
        addresses = [
            0x00000000,
            0xFFFFFFFF,
        ]
        for address in addresses:
            record = IhexRecord.create_start_linear_address(address)
            record.validate()
            assert record.tag == IhexTag.START_LINEAR_ADDRESS
            assert record.address == 0
            assert record.count == 4
            assert record.data == address.to_bytes(4, byteorder='big', signed=False)
            assert record.data_to_int() == address

    def test_create_sla_raises_extension(self):
        addresses = [
            -1,
            0x100000000,
        ]
        for address in addresses:
            with pytest.raises(ValueError, match='address overflow'):
                IhexRecord.create_start_linear_address(address)

    def test_create_ssa(self):
        addresses = [
            0x00000000,
            0xFFFFFFFF,
        ]
        for address in addresses:
            record = IhexRecord.create_start_segment_address(address)
            record.validate()
            assert record.tag == IhexTag.START_SEGMENT_ADDRESS
            assert record.address == 0
            assert record.count == 4
            assert record.data == address.to_bytes(4, byteorder='big', signed=False)
            assert record.data_to_int() == address

    def test_create_ssa_raises_extension(self):
        addresses = [
            -1,
            0x100000000,
        ]
        for address in addresses:
            with pytest.raises(ValueError, match='address overflow'):
                IhexRecord.create_start_segment_address(address)

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
            assert actual.after == b''
            assert actual.before == b''

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
            IhexRecord.create_data(0x0000, b''),
            IhexRecord.create_data(0xFFFF, b''),
            IhexRecord.create_data(0x0000, (b'\xFF' * 0xFF)),
            IhexRecord.create_data(0xFFFF, (b'\xFF' * 0xFF)),

            IhexRecord.create_end_of_file(),

            IhexRecord.create_extended_segment_address(0x0000),
            IhexRecord.create_extended_segment_address(0xFFFF),

            IhexRecord.create_start_segment_address(0x00000000),
            IhexRecord.create_start_segment_address(0xFFFFFFFF),

            IhexRecord.create_extended_linear_address(0x0000),
            IhexRecord.create_extended_linear_address(0xFFFF),

            IhexRecord.create_start_linear_address(0x00000000),
            IhexRecord.create_start_linear_address(0xFFFFFFFF),
        ]
        for expected, record in zip(lines, records):
            record = _cast(IhexRecord, record)
            actual = record.to_bytestr()
            assert actual == expected

    def test_to_tokens(self):
        lines = [
            b'|:|00|0000|00||00||\r\n',
            b'|:|00|FFFF|00||02||\r\n',

            b'|:|FF|0000|00|' + (b'FF' * 0xFF) + b'|00||\r\n',
            b'|:|FF|FFFF|00|' + (b'FF' * 0xFF) + b'|02||\r\n',

            b'|:|00|0000|01||FF||\r\n',

            b'|:|02|0000|02|0000|FC||\r\n',
            b'|:|02|0000|02|FFFF|FE||\r\n',

            b'|:|04|0000|03|00000000|F9||\r\n',
            b'|:|04|0000|03|FFFFFFFF|FD||\r\n',

            b'|:|02|0000|04|0000|FA||\r\n',
            b'|:|02|0000|04|FFFF|FC||\r\n',

            b'|:|04|0000|05|00000000|F7||\r\n',
            b'|:|04|0000|05|FFFFFFFF|FB||\r\n',
        ]
        records = [
            IhexRecord.create_data(0x0000, b''),
            IhexRecord.create_data(0xFFFF, b''),
            IhexRecord.create_data(0x0000, (b'\xFF' * 0xFF)),
            IhexRecord.create_data(0xFFFF, (b'\xFF' * 0xFF)),

            IhexRecord.create_end_of_file(),

            IhexRecord.create_extended_segment_address(0x0000),
            IhexRecord.create_extended_segment_address(0xFFFF),

            IhexRecord.create_start_segment_address(0x00000000),
            IhexRecord.create_start_segment_address(0xFFFFFFFF),

            IhexRecord.create_extended_linear_address(0x0000),
            IhexRecord.create_extended_linear_address(0xFFFF),

            IhexRecord.create_start_linear_address(0x00000000),
            IhexRecord.create_start_linear_address(0xFFFFFFFF),
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
            actual = b'|'.join(tokens.get(key, b'?') for key in keys)
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

            'unexpected data',

            'is not a valid IhexTag',
        ]
        records = [
            # IhexRecord(IhexTag.DATA, after=b'?'),
            IhexRecord(IhexTag.DATA, validate=False, before=b':'),

            IhexRecord(IhexTag.DATA, validate=False, checksum=-1),
            IhexRecord(IhexTag.DATA, validate=False, checksum=0x100),

            IhexRecord(IhexTag.DATA, validate=False, count=-1),
            IhexRecord(IhexTag.DATA, validate=False, count=0x100),

            IhexRecord(IhexTag.DATA, validate=False, data=(b'x' * 0x100), count=0xFF),

            IhexRecord(IhexTag.DATA, validate=False, address=-1),
            IhexRecord(IhexTag.DATA, validate=False, address=0x10000),

            IhexRecord(IhexTag.EXTENDED_SEGMENT_ADDRESS, validate=False, data=b'00000'),
            IhexRecord(IhexTag.EXTENDED_LINEAR_ADDRESS, validate=False, data=b'00000'),

            IhexRecord(IhexTag.START_SEGMENT_ADDRESS, validate=False, data=b'000000000'),
            IhexRecord(IhexTag.START_LINEAR_ADDRESS, validate=False, data=b'000000000'),

            IhexRecord(IhexTag.END_OF_FILE, validate=False, data=b'0'),

            IhexRecord(_cast(IhexTag, 666), validate=False),
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


class TestIhexFile(BaseTestFile):

    File = IhexFile

    def test___init__(self):
        file = IhexFile()
        assert file._records is None
        assert file._memory == b''
        assert file._linear is True
        assert file._startaddr is None

    def test_apply_records_linear(self):
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_linear_address(0x12345678),
            IhexRecord.create_end_of_file(),
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
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_segment_address(0xA000),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_segment_address(0x12345678),
            IhexRecord.create_end_of_file(),
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
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_linear_address(0x12345678),
            IhexRecord.create_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file = _cast(IhexFile, file)
        assert file.linear is True

    def test_linear_getter_segment(self):
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_segment_address(0xA000),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_segment_address(0x12345678),
            IhexRecord.create_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file = _cast(IhexFile, file)
        assert file.linear is False

    def test_linear_setter_linear_to_segment(self):
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_linear_address(0x12345678),
            IhexRecord.create_end_of_file(),
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
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_segment_address(0xA000),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_segment_address(0x12345678),
            IhexRecord.create_end_of_file(),
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

    def test_load_file(self, datapath):
        path = str(datapath / 'simple.hex')
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x5678, b'xyz'),
            IhexRecord.create_start_linear_address(0xABCD5678),
            IhexRecord.create_end_of_file(),
        ]
        file = IhexFile.load(path)
        assert file.records == records

    def test_load_stdin(self):
        buffer = (
            b':0312340061626391\r\n'
            b':02000004ABCD82\r\n'
            b':0356780078797AC4\r\n'
            b':04000005ABCD5678B1\r\n'
            b':00000001FF\r\n'
        )
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x5678, b'xyz'),
            IhexRecord.create_start_linear_address(0xABCD5678),
            IhexRecord.create_end_of_file(),
        ]
        stream = io.BytesIO(buffer)
        with replace_stdin(stream):
            file = IhexFile.load(None)
        assert file._records == records

    def test_parse(self):
        buffer = (
            b':0312340061626391\r\n'
            b':02000004ABCD82\r\n'
            b':0356780078797AC4\r\n'
            b':04000005ABCD5678B1\r\n'
            b':00000001FF\r\n'
        )
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x5678, b'xyz'),
            IhexRecord.create_start_linear_address(0xABCD5678),
            IhexRecord.create_end_of_file(),
        ]
        with io.BytesIO(buffer) as stream:
            file = IhexFile.parse(stream)
        assert file._records == records

    def test_parse_errors(self):
        buffer = (
            b'::0312340061626391\r\n'
            b':00000001FF\r\n'
        )
        with pytest.raises(ValueError, match='syntax error'):
            with io.BytesIO(buffer) as stream:
                IhexFile.parse(stream, ignore_errors=False)

    # https://en.wikipedia.org/wiki/Intel_HEX#File_example
    def test_parse_file_wikipedia(self, datapath):
        path = str(datapath / 'wikipedia.hex')
        records = [
            IhexRecord(IhexTag.DATA, count=0x10, address=0x0100, checksum=0x40,
                       data=b'\x21\x46\x01\x36\x01\x21\x47\x01\x36\x00\x7E\xFE\x09\xD2\x19\x01'),
            IhexRecord(IhexTag.DATA, count=0x10, address=0x0110, checksum=0x28,
                       data=b'\x21\x46\x01\x7E\x17\xC2\x00\x01\xFF\x5F\x16\x00\x21\x48\x01\x19'),
            IhexRecord(IhexTag.DATA, count=0x10, address=0x0120, checksum=0xA7,
                       data=b'\x19\x4E\x79\x23\x46\x23\x96\x57\x78\x23\x9E\xDA\x3F\x01\xB2\xCA'),
            IhexRecord(IhexTag.DATA, count=0x10, address=0x0130, checksum=0xC7,
                       data=b'\x3F\x01\x56\x70\x2B\x5E\x71\x2B\x72\x2B\x73\x21\x46\x01\x34\x21'),
            IhexRecord(IhexTag.END_OF_FILE, count=0x00, address=0x0000, checksum=0xFF, data=b''),
        ]
        with open(path, 'rb') as stream:
            file = IhexFile.parse(stream)
        assert file._records == records

    def test_parse_ignore_errors(self):
        buffer = (
            b'::0312340061626391\r\n'
            b':00000001FF\r\n'
        )
        records = [
            # IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_end_of_file(),
        ]
        with io.BytesIO(buffer) as stream:
            file = IhexFile.parse(stream, ignore_errors=True)
        assert file._records == records

    def test_parse_junk(self):
        buffer = (
            b':0312340061626391\r\n'
            b':02000004ABCD82\r\n'
            b':0356780078797AC4\r\n'
            b':04000005ABCD5678B1\r\n'
            b':00000001FF\r\n'
            b'junk\r\nafter'
        )
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x5678, b'xyz'),
            IhexRecord.create_start_linear_address(0xABCD5678),
            IhexRecord.create_end_of_file(),
        ]
        with io.BytesIO(buffer) as stream:
            file = IhexFile.parse(stream, ignore_after_termination=True)
        assert file._records == records

    def test_parse_raises_junk(self):
        buffer = (
            b':0312340061626391\r\n'
            b':02000004ABCD82\r\n'
            b':0356780078797AC4\r\n'
            b':04000005ABCD5678B1\r\n'
            b':00000001FF\r\n'
            b'junk\r\nafter'
        )
        with pytest.raises(ValueError, match='syntax error'):
            with io.BytesIO(buffer) as stream:
                IhexFile.parse(stream, ignore_after_termination=False)

    def test_save_file(self, tmppath):
        path = str(tmppath / 'test_save_file.hex')
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x5678, b'xyz'),
            IhexRecord.create_start_linear_address(0xABCD5678),
            IhexRecord.create_end_of_file(),
        ]
        expected = (
            b':0312340061626391\r\n'
            b':02000004ABCD82\r\n'
            b':0356780078797AC4\r\n'
            b':04000005ABCD5678B1\r\n'
            b':00000001FF\r\n'
        )
        file = IhexFile.from_records(records)
        returned = file.save(path)
        assert returned is file
        with open(path, 'rb') as stream:
            actual = stream.read()
        assert actual == expected

    def test_save_stdout(self):
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x5678, b'xyz'),
            IhexRecord.create_start_linear_address(0xABCD5678),
            IhexRecord.create_end_of_file(),
        ]
        expected = (
            b':0312340061626391\r\n'
            b':02000004ABCD82\r\n'
            b':0356780078797AC4\r\n'
            b':04000005ABCD5678B1\r\n'
            b':00000001FF\r\n'
        )
        stream = io.BytesIO()
        file = IhexFile.from_records(records)
        with replace_stdout(stream):
            returned = file.save(None)
        assert returned is file
        actual = stream.getvalue()
        assert actual == expected

    def test_startaddr_getter_linear(self):
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_linear_address(0x12345678),
            IhexRecord.create_end_of_file(),
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
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_end_of_file(),
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
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_segment_address(0xA000),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_segment_address(0x12345678),
            IhexRecord.create_end_of_file(),
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
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_segment_address(0xA000),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_segment_address(0x12345678),
            IhexRecord.create_end_of_file(),
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
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_linear_address(0x12345678),
            IhexRecord.create_end_of_file(),
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
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_linear_address(0x12345678),
            IhexRecord.create_end_of_file(),
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

    def test_update_records(self):
        self.test_update_records_basic_linear()

    def test_update_records_basic_linear(self):
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_linear_address(0x12345678),
            IhexRecord.create_end_of_file(),
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
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_segment_address(0xA000),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_segment_address(0x12345678),
            IhexRecord.create_end_of_file(),
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
            IhexRecord.create_end_of_file(),
        ]
        memory = Memory()
        file = IhexFile.from_memory(memory)
        file = _cast(IhexFile, file)
        file._records = []
        file.update_records(start=False)
        assert file._records == records

    def test_update_records_empty_start_linear(self):
        records = [
            IhexRecord.create_start_linear_address(0x12345678),
            IhexRecord.create_end_of_file(),
        ]
        memory = Memory()
        file = IhexFile.from_memory(memory, startaddr=0x12345678, linear=True)
        file = _cast(IhexFile, file)
        file._records = []
        file.update_records(start=True)
        assert file._records == records

    def test_update_records_empty_start_segment(self):
        records = [
            IhexRecord.create_start_segment_address(0x12345678),
            IhexRecord.create_end_of_file(),
        ]
        memory = Memory()
        file = IhexFile.from_memory(memory, startaddr=0x12345678, linear=False)
        file = _cast(IhexFile, file)
        file._records = []
        file.update_records(start=True)
        assert file._records == records

    def test_update_records_raises_memory(self):
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_linear_address(0x12345678),
            IhexRecord.create_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        with pytest.raises(ValueError, match='memory instance required'):
            file.update_records()

    def test_update_records_raises_segment_overflow(self):
        memory = Memory.from_bytes(b'abc', offset=0x00100000)
        file = IhexFile.from_memory(memory, linear=False)
        with pytest.raises(ValueError, match='segment overflow'):
            file.update_records()

    def test_validate_records(self):
        self.test_validate_records_basic_linear()

    def test_validate_records_basic_linear(self):
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_linear_address(0xABCD),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_linear_address(0x12345678),
            IhexRecord.create_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        returned = file.validate_records(data_ordering=True)
        assert returned is file

    def test_validate_records_basic_segment(self):
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_extended_segment_address(0xA000),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_segment_address(0x12345678),
            IhexRecord.create_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        returned = file.validate_records(data_ordering=True)
        assert returned is file

    def test_validate_records_data_ordering(self):
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file.validate_records(data_ordering=True)
        file.validate_records(data_ordering=False)

    def test_validate_records_raises_data_ordering(self):
        records = [
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        with pytest.raises(ValueError, match='unordered data record'):
            file.validate_records(data_ordering=True)

    def test_validate_records_raises_eof_last(self):
        records = [
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_end_of_file(),
            IhexRecord.create_data(0x1234, b'abc'),
        ]
        file = IhexFile.from_records(records)
        with pytest.raises(ValueError, match='end of file record not last'):
            file.validate_records()

    def test_validate_records_raises_eof_missing(self):
        records = [
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_data(0x1234, b'abc'),
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
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        with pytest.raises(ValueError, match='missing start record'):
            file.validate_records(start_required=True)

    def test_validate_records_raises_start_multi(self):
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_segment_address(0x12345678),
            IhexRecord.create_start_segment_address(0x12345678),
            IhexRecord.create_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        with pytest.raises(ValueError, match='start record not penultimate'):
            file.validate_records(start_penultimate=True)

    def test_validate_records_raises_start_penultimate(self):
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_start_segment_address(0x12345678),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        with pytest.raises(ValueError, match='start record not penultimate'):
            file.validate_records(start_penultimate=True)

    def test_validate_records_raises_start_within_data(self):
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_segment_address(0x12345678),
            IhexRecord.create_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        with pytest.raises(ValueError, match='no data at start address'):
            file.validate_records(start_within_data=True)

    def test_validate_records_start(self):
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_segment_address(0x12345678),
            IhexRecord.create_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file.validate_records(start_required=True, start_penultimate=True)
        file.validate_records(start_required=True, start_penultimate=False)
        file.validate_records(start_required=False, start_penultimate=True)
        file.validate_records(start_required=False, start_penultimate=False)

    def test_validate_records_start_within_data(self):
        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_start_segment_address(0x1234),
            IhexRecord.create_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file.validate_records(start_within_data=True)
        file.validate_records(start_within_data=False)

        records = [
            IhexRecord.create_data(0x1234, b'abc'),
            IhexRecord.create_data(0x4321, b'xyz'),
            IhexRecord.create_end_of_file(),
        ]
        file = IhexFile.from_records(records)
        file.validate_records(start_within_data=True)
        file.validate_records(start_within_data=False)
