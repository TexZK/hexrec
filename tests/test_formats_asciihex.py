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

from hexrec.formats.asciihex import AsciiHexFile
from hexrec.formats.asciihex import AsciiHexRecord
from hexrec.formats.asciihex import AsciiHexTag


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


class TestAsciiHexTag(BaseTestTag):

    Tag = AsciiHexTag

    def test_enum(self):
        assert AsciiHexTag.DATA == 0
        assert AsciiHexTag.ADDRESS == 1
        assert AsciiHexTag.CHECKSUM == 2

    def test_is_address(self):
        assert AsciiHexTag.DATA.is_address() is False
        assert AsciiHexTag.ADDRESS.is_address() is True
        assert AsciiHexTag.CHECKSUM.is_address() is False

    def test_is_checksum(self):
        assert AsciiHexTag.DATA.is_checksum() is False
        assert AsciiHexTag.ADDRESS.is_checksum() is False
        assert AsciiHexTag.CHECKSUM.is_checksum() is True

    def test_is_data(self):
        assert AsciiHexTag.DATA.is_data() is True
        assert AsciiHexTag.ADDRESS.is_data() is False
        assert AsciiHexTag.CHECKSUM.is_data() is False

    def test_is_file_termination(self):
        assert AsciiHexTag.DATA.is_file_termination() is False
        assert AsciiHexTag.ADDRESS.is_file_termination() is False
        assert AsciiHexTag.CHECKSUM.is_file_termination() is False


class TestAsciiHexRecord(BaseTestRecord):

    Record = AsciiHexRecord

    def test_compute_checksum(self):
        assert AsciiHexRecord.create_checksum(0x0000).checksum == 0x0000
        assert AsciiHexRecord.create_checksum(0x0001).checksum == 0x0001
        assert AsciiHexRecord.create_checksum(0x0012).checksum == 0x0012
        assert AsciiHexRecord.create_checksum(0x0123).checksum == 0x0123
        assert AsciiHexRecord.create_checksum(0x1234).checksum == 0x1234
        assert AsciiHexRecord.create_address(0x1234).checksum is None
        assert AsciiHexRecord.create_data(0, b'abc').checksum is None

    def test_compute_count(self):
        assert AsciiHexRecord.create_address(0x00000000).count == 8
        assert AsciiHexRecord.create_address(0x00001234).count == 8
        assert AsciiHexRecord.create_address(0x12345678).count == 8
        assert AsciiHexRecord.create_address(0, addrlen=1).count == 1
        assert AsciiHexRecord.create_address(0, addrlen=2).count == 2
        assert AsciiHexRecord.create_address(0, addrlen=3).count == 3
        assert AsciiHexRecord.create_checksum(0x1234).count is None
        assert AsciiHexRecord.create_data(0, b'abc').count is None

    def test_create_address(self):
        vector = [
            (1, 0x00000000),
            (4, 0x00000000),
            (4, 0x0000FFFF),
            (8, 0x00000000),
            (8, 0x0000FFFF),
            (8, 0xFFFFFFFF),
        ]
        for addrlen, address in vector:
            record = AsciiHexRecord.create_address(address, addrlen=addrlen)
            record.validate()
            assert record.tag == AsciiHexTag.ADDRESS
            assert record.address == address
            assert record.checksum is None
            assert record.count == addrlen
            assert record.data == b''

    def test_create_address_raises(self):
        vector = [
            (0, 0x00000000),
            (3, 0x0000FFFF),
            (4, 0x00010000),
            (7, 0xFFFFFFFF),
            (8, 0x100000000),
        ]
        for addrlen, address in vector:
            with pytest.raises(ValueError, match='count overflow'):
                AsciiHexRecord.create_address(address, addrlen=addrlen)

        with pytest.raises(ValueError, match='address overflow'):
            AsciiHexRecord.create_address(-1)

    def test_create_checksum(self):
        checksums = [
            0x0000,
            0x1234,
            0xFFFF,
        ]
        for checksum in checksums:
            record = AsciiHexRecord.create_checksum(checksum)
            record.validate()
            assert record.tag == AsciiHexTag.CHECKSUM
            assert record.address == 0
            assert record.checksum == checksum
            assert record.count is None
            assert record.data == b''

    def test_create_checksum_raises(self):
        checksums = [
            -1,
            0x10000,
        ]
        for checksum in checksums:
            with pytest.raises(ValueError, match='checksum overflow'):
                AsciiHexRecord.create_checksum(checksum)

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
                record = AsciiHexRecord.create_data(address, data)
                record.validate()
                assert record.tag == AsciiHexTag.DATA
                assert record.address == address
                assert record.checksum is None
                assert record.count is None
                assert record.data == data

    def test_parse(self):
        lines = [
            b'$AFFFF,',
            b'$AFFFFFFFF,',
            b'$SFFFF,',
            b'FF',
            b'FF ' * 0x1000,
        ]
        records = [
            AsciiHexRecord.create_address(0xFFFF, addrlen=4),
            AsciiHexRecord.create_address(0xFFFFFFFF),
            AsciiHexRecord.create_checksum(0xFFFF),
            AsciiHexRecord.create_data(0, b'\xFF'),
            AsciiHexRecord.create_data(0, b'\xFF' * 0x1000),
        ]
        for line, expected in zip(lines, records):
            actual = AsciiHexRecord.parse(line)
            assert actual == expected
            assert actual.before == b''
            assert actual.after == b''

    def test_parse_raises_syntax(self):
        lines = [
            b'$A,',
            # b'AFFFF,',  # regex does not consume trailing b'F,'
            b'$AFFFF?',
            b'.$AFFFF,',
            # b'$AFFFF,.',  # regex does not consume trailing b'.'

            b'$S,',
            b'SFFFF,',
            b'$SFFFF?',
            b'.$SFFFF,',
            # b'$SFFFF,.',  # regex does not consume trailing b'.'

            b'',
            b'XX',
            # b'00.',  # regex does not consume trailing b'.'
            # b'FF.',  # regex does not consume trailing b'.'
        ]
        for line in lines:
            with pytest.raises(ValueError, match='syntax error'):
                AsciiHexRecord.parse(line)

    # SRecord test script "t0110a.sh"
    def test_parse_srecord_t0110a(self):
        lines = [
            b'$A0000,',
            b'7F D2 43 A6 7F F3 43 A6 3F C0 00 3F 3B DE 70 0C ',
            b'3B E0 00 01 93 FE 00 00 7F FA 02 A6 93 FE 00 04 ',
            b'7F FB 02 A6 93 FE 00 08 7F D2 42 A6 7F F3 42 A6 ',
            b'48 00 1F 04 00 00 00 00 00 00 00 00 00 00 00 00 ',
            b'00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ',
            b'00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ',
            b'00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ',
        ]
        records = [
            AsciiHexRecord.create_address(0x0000, addrlen=4),
            AsciiHexRecord.create_data(0x0000, b'\x7F\xD2\x43\xA6\x7F\xF3\x43\xA6\x3F\xC0\x00\x3F\x3B\xDE\x70\x0C'),
            AsciiHexRecord.create_data(0x0000, b'\x3B\xE0\x00\x01\x93\xFE\x00\x00\x7F\xFA\x02\xA6\x93\xFE\x00\x04'),
            AsciiHexRecord.create_data(0x0000, b'\x7F\xFB\x02\xA6\x93\xFE\x00\x08\x7F\xD2\x42\xA6\x7F\xF3\x42\xA6'),
            AsciiHexRecord.create_data(0x0000, b'\x48\x00\x1F\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
            AsciiHexRecord.create_data(0x0000, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
            AsciiHexRecord.create_data(0x0000, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
            AsciiHexRecord.create_data(0x0000, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
        ]
        for line, expected in zip(lines, records):
            actual = AsciiHexRecord.parse(line)
            assert actual == expected

    def test_parse_syntax(self):
        lines = [
            b'$A0,',
            b'$A0000,',
            b'$A00000000,',
            b'$AFFFF,',
            b'$AFFFFFFFF,',
            b'$A00000000.',
            b'$AFFFFFFFF.',
            b' \t\v\f\r$AFFFFFFFF,',
            b'$AFFFFFFFF, \t\v\f\r',
            b'$AFFFFFFFF,\r\n',
            b'$AFFFFFFFF,\n',
            b'$affffffff,',

            b'$S0000,',
            b'$SFFFF,',
            b'$S0000.',
            b'$SFFFF.',
            b' \t\v\f\r$SFFFF,',
            b'$SFFFF, \t\v\f\r',
            b'$SFFFF,\r\n',
            b'$SFFFF,\n',
            b'$sffff,',

            b'00',
            b'FF',
            b'FF' * 0x1000,
            b'FF ' * 0x1000,
            b'FF\t' * 0x1000,
            b'FF\v' * 0x1000,
            b'FF\f' * 0x1000,
            b'FF\r' * 0x1000,
            b'FF%' * 0x1000,
            b"FF'" * 0x1000,
            b'FF,' * 0x1000,
            b' \t\v\f\rFF,',
            b'FF, \t\v\f\r',
            b'FF\r\n',
            b'FF\n',
            b'ff ' * 0x1000,
        ]
        records = [
            AsciiHexRecord.create_address(0x00000000, addrlen=1),
            AsciiHexRecord.create_address(0x00000000, addrlen=4),
            AsciiHexRecord.create_address(0x00000000, addrlen=8),
            AsciiHexRecord.create_address(0x0000FFFF, addrlen=4),
            AsciiHexRecord.create_address(0xFFFFFFFF, addrlen=8),
            AsciiHexRecord.create_address(0x00000000, addrlen=8),
            AsciiHexRecord.create_address(0xFFFFFFFF, addrlen=8),
            AsciiHexRecord.create_address(0xFFFFFFFF, addrlen=8),
            AsciiHexRecord.create_address(0xFFFFFFFF, addrlen=8),
            AsciiHexRecord.create_address(0xFFFFFFFF, addrlen=8),
            AsciiHexRecord.create_address(0xFFFFFFFF, addrlen=8),
            AsciiHexRecord.create_address(0xFFFFFFFF, addrlen=8),

            AsciiHexRecord.create_checksum(0x0000),
            AsciiHexRecord.create_checksum(0xFFFF),
            AsciiHexRecord.create_checksum(0x0000),
            AsciiHexRecord.create_checksum(0xFFFF),
            AsciiHexRecord.create_checksum(0xFFFF),
            AsciiHexRecord.create_checksum(0xFFFF),
            AsciiHexRecord.create_checksum(0xFFFF),
            AsciiHexRecord.create_checksum(0xFFFF),
            AsciiHexRecord.create_checksum(0xffff),

            AsciiHexRecord.create_data(0, b'\x00'),
            AsciiHexRecord.create_data(0, b'\xFF'),
            AsciiHexRecord.create_data(0, b'\xFF' * 0x1000),
            AsciiHexRecord.create_data(0, b'\xFF' * 0x1000),
            AsciiHexRecord.create_data(0, b'\xFF' * 0x1000),
            AsciiHexRecord.create_data(0, b'\xFF' * 0x1000),
            AsciiHexRecord.create_data(0, b'\xFF' * 0x1000),
            AsciiHexRecord.create_data(0, b'\xFF' * 0x1000),
            AsciiHexRecord.create_data(0, b'\xFF' * 0x1000),
            AsciiHexRecord.create_data(0, b'\xFF' * 0x1000),
            AsciiHexRecord.create_data(0, b'\xFF' * 0x1000),
            AsciiHexRecord.create_data(0, b'\xFF'),
            AsciiHexRecord.create_data(0, b'\xFF'),
            AsciiHexRecord.create_data(0, b'\xFF'),
            AsciiHexRecord.create_data(0, b'\xFF'),
            AsciiHexRecord.create_data(0, b'\xFF' * 0x1000),
        ]
        for line, expected in zip(lines, records):
            actual = AsciiHexRecord.parse(line)
            assert actual == expected

    def test_to_bytestr(self):
        lines = [
            b'$A0000,\r\n',
            b'$AFFFF,\r\n',
            b'$A00000000,\r\n',
            b'$AFFFFFFFF,\r\n',

            b'$S0000,\r\n',
            b'$SFFFF,\r\n',

            b'00 \r\n',
            b'FF \r\n',
            (b'FF ' * 0x1000) + b'\r\n',
        ]
        records = [
            AsciiHexRecord.create_address(0x00000000, addrlen=4),
            AsciiHexRecord.create_address(0x0000FFFF, addrlen=4),
            AsciiHexRecord.create_address(0x00000000, addrlen=8),
            AsciiHexRecord.create_address(0xFFFFFFFF, addrlen=8),

            AsciiHexRecord.create_checksum(0x0000),
            AsciiHexRecord.create_checksum(0xFFFF),

            AsciiHexRecord.create_data(0, b'\x00'),
            AsciiHexRecord.create_data(0, b'\xFF'),
            AsciiHexRecord.create_data(0, b'\xFF' * 0x1000),
        ]
        for expected, record in zip(lines, records):
            record = _cast(AsciiHexRecord, record)
            actual = record.to_bytestr()
            assert actual == expected

    def test_to_bytestr_dollarend(self):
        record = AsciiHexRecord.create_address(0x12345678)
        assert record.to_bytestr() == b'$A12345678,\r\n'
        assert record.to_bytestr(dollarend=b'.') == b'$A12345678.\r\n'

        record = AsciiHexRecord.create_checksum(0x1234)
        assert record.to_bytestr() == b'$S1234,\r\n'
        assert record.to_bytestr(dollarend=b'.') == b'$S1234.\r\n'

    def test_to_bytestr_end(self):
        record = AsciiHexRecord.create_address(0x12345678)
        assert record.to_bytestr() == b'$A12345678,\r\n'
        assert record.to_bytestr(end=b'\n') == b'$A12345678,\n'

        record = AsciiHexRecord.create_checksum(0x1234)
        assert record.to_bytestr() == b'$S1234,\r\n'
        assert record.to_bytestr(end=b'\n') == b'$S1234,\n'

        record = AsciiHexRecord.create_data(0, b'\x11\x22\x33\x44')
        assert record.to_bytestr() == b'11 22 33 44 \r\n'
        assert record.to_bytestr(end=b'\n') == b'11 22 33 44 \n'

    def test_to_bytestr_exechars(self):
        record = AsciiHexRecord.create_data(0, b'\x11\x22\x33\x44')
        assert record.to_bytestr() == b'11 22 33 44 \r\n'
        assert record.to_bytestr(exelast=False) == b'11 22 33 44\r\n'
        assert record.to_bytestr(exechar=b',') == b'11,22,33,44,\r\n'
        assert record.to_bytestr(exechar=b',', exelast=False) == b'11,22,33,44\r\n'

    def test_to_tokens(self):
        lines = [
            b'|$A0000,||||\r\n',
            b'|$AFFFF,||||\r\n',
            b'|$A00000000,||||\r\n',
            b'|$AFFFFFFFF,||||\r\n',

            b'|||$S0000,||\r\n',
            b'|||$SFFFF,||\r\n',

            b'|||||\r\n',
            b'||00 |||\r\n',
            b'||FF |||\r\n',
            b'||' + (b'FF ' * 0x1000) + b'|||\r\n',
        ]
        records = [
            AsciiHexRecord.create_address(0x00000000, addrlen=4),
            AsciiHexRecord.create_address(0x0000FFFF, addrlen=4),
            AsciiHexRecord.create_address(0x00000000, addrlen=8),
            AsciiHexRecord.create_address(0xFFFFFFFF, addrlen=8),

            AsciiHexRecord.create_checksum(0x0000),
            AsciiHexRecord.create_checksum(0xFFFF),

            AsciiHexRecord.create_data(0, b''),
            AsciiHexRecord.create_data(0, b'\x00'),
            AsciiHexRecord.create_data(0, b'\xFF'),
            AsciiHexRecord.create_data(0, b'\xFF' * 0x1000),
        ]
        keys = [
            'before',
            'address',
            'data',
            'checksum',
            'after',
            'end',
        ]
        for expected, record in zip(lines, records):
            tokens = record.to_tokens()
            assert all((key in keys) for key in tokens.keys())
            actual = b'|'.join(tokens.get(key, b'?') for key in keys)
            assert actual == expected

    def test_to_tokens_no_exelast(self):
        lines = [
            b'||00|||\r\n',
            b'||FF|||\r\n',
            b'||' + (b'FF ' * 0xFFF) + b'FF|||\r\n',
        ]
        records = [
            AsciiHexRecord.create_data(0, b'\x00'),
            AsciiHexRecord.create_data(0, b'\xFF'),
            AsciiHexRecord.create_data(0, b'\xFF' * 0x1000),
        ]
        keys = [
            'before',
            'address',
            'data',
            'checksum',
            'after',
            'end',
        ]
        for expected, record in zip(lines, records):
            tokens = record.to_tokens(exelast=False)
            assert all((key in keys) for key in tokens.keys())
            actual = b'|'.join(tokens.get(key, b'?') for key in keys)
            assert actual == expected

    def test_validate_raises(self):
        matches = [
            'junk after',
            'junk before',

            'checksum required',
            'checksum overflow',
            'checksum overflow',

            'count required',
            'count overflow',
            'count overflow',

            'unexpected data',
        ]
        records = [
            AsciiHexRecord(AsciiHexTag.DATA, after=b'?', validate=False),
            AsciiHexRecord(AsciiHexTag.DATA, before=b'?', validate=False),

            AsciiHexRecord(AsciiHexTag.CHECKSUM, checksum=None, validate=False),
            AsciiHexRecord(AsciiHexTag.CHECKSUM, checksum=-1, validate=False),
            AsciiHexRecord(AsciiHexTag.CHECKSUM, checksum=0x10000, validate=False),

            AsciiHexRecord(AsciiHexTag.ADDRESS, count=None, validate=False),
            AsciiHexRecord(AsciiHexTag.ADDRESS, count=-1, validate=False),
            AsciiHexRecord(AsciiHexTag.ADDRESS, count=4, address=0x10000, validate=False),

            AsciiHexRecord(AsciiHexTag.ADDRESS, count=4, data=b'abc', validate=False),
        ]
        for match, record in zip(matches, records):
            record = _cast(AsciiHexRecord, record)
            with pytest.raises(ValueError, match=match):
                record.validate()

    def test_validate_samples(self):
        records = [
            AsciiHexRecord.create_address(0x00000000, addrlen=4),
            AsciiHexRecord.create_address(0x0000FFFF, addrlen=4),
            AsciiHexRecord.create_address(0x00000000, addrlen=8),
            AsciiHexRecord.create_address(0xFFFFFFFF, addrlen=8),

            AsciiHexRecord.create_checksum(0x0000),
            AsciiHexRecord.create_checksum(0xFFFF),

            AsciiHexRecord.create_data(0, b'\x00'),
            AsciiHexRecord.create_data(0, b'\xFF'),
            AsciiHexRecord.create_data(0, b'\xFF' * 0x1000),
        ]
        for record in records:
            returned = record.validate()
            assert returned is record


class TestAsciiHexFile(BaseTestFile):

    File = AsciiHexFile

    def test_load_file(self, datapath):
        path = str(datapath / 'simple.ascii_hex')
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
        ]
        file = AsciiHexFile.load(path)
        assert file.records == records

    def test_load_stdin(self):
        buffer = (
            b'\x02'
            b'61 62 63 \r\n'
            b'$A1234,\r\n'
            b'78 79 7A \r\n'
            b'\x03'
        )
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
        ]
        stream = io.BytesIO(buffer)
        with replace_stdin(stream):
            file = AsciiHexFile.load(None)
        assert file._records == records

    def test_parse(self):
        buffer = (
            b'\x02'
            b'61 62 63 \r\n'
            b'$A1234,\r\n'
            b'78 79 7A \r\n'
            b'\x03'
        )
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
        ]
        with io.BytesIO(buffer) as stream:
            file = AsciiHexFile.parse(stream)
        assert file._records == records

    # SRecord test script "t0110a.sh"
    def test_parse_file_srecord_t0110a(self, datapath):
        path = str(datapath / 'srecord_t0110a_sh.ascii_hex')
        records = [
            AsciiHexRecord.create_address(0x0000, addrlen=4),
            AsciiHexRecord.create_data(0x0000, b'\x7F\xD2\x43\xA6\x7F\xF3\x43\xA6\x3F\xC0\x00\x3F\x3B\xDE\x70\x0C'),
            AsciiHexRecord.create_data(0x0010, b'\x3B\xE0\x00\x01\x93\xFE\x00\x00\x7F\xFA\x02\xA6\x93\xFE\x00\x04'),
            AsciiHexRecord.create_data(0x0020, b'\x7F\xFB\x02\xA6\x93\xFE\x00\x08\x7F\xD2\x42\xA6\x7F\xF3\x42\xA6'),
            AsciiHexRecord.create_data(0x0030, b'\x48\x00\x1F\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
            AsciiHexRecord.create_data(0x0040, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
            AsciiHexRecord.create_data(0x0050, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
            AsciiHexRecord.create_data(0x0060, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
        ]
        with open(path, 'rb') as stream:
            file = AsciiHexFile.parse(stream)
        assert file._records == records

    def test_parse_ignore_errors(self):
        buffer = (
            b'\x02'
            b'61 62 63 \r\n'
            b'$$A1234,\r\n'
            b'78 79 7A \r\n'
            b'\x03'
        )
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
        ]
        with io.BytesIO(buffer) as stream:
            file = AsciiHexFile.parse(stream, ignore_errors=True)
        assert file._records == records

    def test_parse_plain(self):
        buffer = (
            b'61 62 63 \r\n'
            b'$A1234,\r\n'
            b'78 79 7A \r\n'
        )
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
        ]
        with io.BytesIO(buffer) as stream:
            file = AsciiHexFile.parse(stream, stxetx=False)
        assert file._records == records

    def test_parse_raises_etx(self):
        buffer = (
            b'\x02'
            b'61 62 63 \r\n'
            b'$A1234,\r\n'
            b'78 79 7A \r\n'
        )
        with pytest.raises(ValueError, match='missing ETX character'):
            with io.BytesIO(buffer) as stream:
                AsciiHexFile.parse(stream, stxetx=True)

    def test_parse_raises_stx(self):
        buffer = (
            b'61 62 63 \r\n'
            b'$A1234,\r\n'
            b'78 79 7A \r\n'
            b'\x03'
        )
        with pytest.raises(ValueError, match='missing STX character'):
            with io.BytesIO(buffer) as stream:
                AsciiHexFile.parse(stream, stxetx=True)

    def test_parse_raises_syntax_error(self):
        buffer = (
            b'\x02'
            b'61 62 63 \r\n'
            b'$$A1234,\r\n'
            b'78 79 7A \r\n'
            b'\x03'
        )
        with pytest.raises(ValueError, match='syntax error'):
            with io.BytesIO(buffer) as stream:
                AsciiHexFile.parse(stream, ignore_errors=False)

    def test_save_file(self, tmppath):
        path = str(tmppath / 'test_save_file.ascii_hex')
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
        ]
        expected = (
            b'\x02'
            b'61 62 63 \r\n'
            b'$A1234,\r\n'
            b'78 79 7A \r\n'
            b'\x03'
        )
        file = AsciiHexFile.from_records(records)
        returned = file.save(path)
        assert returned is file
        with open(path, 'rb') as stream:
            actual = stream.read()
        assert actual == expected

    def test_save_stdout(self):
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
        ]
        expected = (
            b'\x02'
            b'61 62 63 \r\n'
            b'$A1234,\r\n'
            b'78 79 7A \r\n'
            b'\x03'
        )
        stream = io.BytesIO()
        file = AsciiHexFile.from_records(records)
        with replace_stdout(stream):
            returned = file.save(None)
        assert returned is file
        actual = stream.getvalue()
        assert actual == expected

    def test_serialize(self):
        expected = (
            b'\x02'
            b'61 62 63 \r\n'
            b'$A1234,\r\n'
            b'78 79 7A \r\n'
            b'\x03'
        )
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
        ]
        file = AsciiHexFile.from_records(records)
        stream = io.BytesIO()
        file.serialize(stream)
        actual = stream.getvalue()
        assert actual == expected

    def test_serialize_plain(self):
        expected = (
            b'61 62 63 \r\n'
            b'$A1234,\r\n'
            b'78 79 7A \r\n'
        )
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
        ]
        file = AsciiHexFile.from_records(records)
        stream = io.BytesIO()
        file.serialize(stream, stxetx=False)
        actual = stream.getvalue()
        assert actual == expected

    def test_update_records(self):
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
        ]
        blocks = [
            [0x0000, b'abc'],
            [0x1234, b'xyz'],
        ]
        file = AsciiHexFile.from_blocks(blocks)
        file._records = None
        returned = file.update_records(checksum=False)
        assert returned is file
        assert file._records == records

    def test_update_records_addrlen(self):
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
        ]
        blocks = [
            [0x0000, b'abc'],
            [0x1234, b'xyz'],
        ]
        file = AsciiHexFile.from_blocks(blocks)
        file._records = None
        returned = file.update_records(checksum=False, addrlen=4)
        assert returned is file
        assert file._records == records

    def test_update_records_checksum(self):
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
            AsciiHexRecord.create_checksum(sum(b'abcxyz') & 0xFFFF),
        ]
        blocks = [
            [0x0000, b'abc'],
            [0x1234, b'xyz'],
        ]
        file = AsciiHexFile.from_blocks(blocks)
        file._records = None
        returned = file.update_records(checksum=True)
        assert returned is file
        assert file._records == records

    def test_update_records_empty(self):
        file = AsciiHexFile.from_memory()
        file._records = None
        file.update_records()
        assert file._records is not None
        assert file._records == []

    def test_update_records_raises_addrlen(self):
        file = AsciiHexFile()
        with pytest.raises(ValueError, match='invalid address length'):
            file.update_records(addrlen=0)

    def test_update_records_raises_memory(self):
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
        ]
        file = AsciiHexFile.from_records(records)
        with pytest.raises(ValueError, match='memory instance required'):
            file.update_records()

    def test_validate_records(self):
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
        ]
        file = AsciiHexFile.from_records(records)
        file.validate_records()

    def test_validate_records_checksum_values(self):
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
            AsciiHexRecord.create_checksum(sum(b'abcxyz') & 0xFFFF)
        ]
        file = AsciiHexFile.from_records(records)
        file.validate_records(checksum_values=True)
        file.validate_records(checksum_values=False)

    def test_validate_records_data_ordering(self):
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
        ]
        file = AsciiHexFile.from_records(records)
        file.validate_records(data_ordering=True)
        file.validate_records(data_ordering=False)

    def test_validate_records_raises_checksum_values(self):
        records = [
            AsciiHexRecord.create_data(0x0000, b'abc'),
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
            AsciiHexRecord.create_checksum((sum(b'abcxyz') & 0xFFFF) ^ 0xFFFF)
        ]
        file = AsciiHexFile.from_records(records)
        with pytest.raises(ValueError, match='wrong checksum'):
            file.validate_records(checksum_values=True)

    def test_validate_records_raises_data_ordering(self):
        records = [
            AsciiHexRecord.create_address(0x1234, addrlen=4),
            AsciiHexRecord.create_data(0x1234, b'xyz'),
            AsciiHexRecord.create_address(0x0000, addrlen=4),
            AsciiHexRecord.create_data(0x0000, b'abc'),
        ]
        file = AsciiHexFile.from_records(records)
        with pytest.raises(ValueError, match='unordered data record'):
            file.validate_records(data_ordering=True)

    def test_validate_records_raises_records(self):
        file = AsciiHexFile.from_memory(Memory.from_bytes(b'abc'))
        with pytest.raises(ValueError, match='records required'):
            file.validate_records()
