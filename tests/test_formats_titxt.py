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

from hexrec.formats.titxt import TiTxtFile
from hexrec.formats.titxt import TiTxtRecord
from hexrec.formats.titxt import TiTxtTag


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


class TestTiTxtTag(BaseTestTag):

    Tag = TiTxtTag

    def test_enum(self):
        assert TiTxtTag.DATA == 0
        assert TiTxtTag.ADDRESS == 1
        assert TiTxtTag.EOF == 2

    def test_is_address(self):
        assert TiTxtTag.DATA.is_address() is False
        assert TiTxtTag.ADDRESS.is_address() is True
        assert TiTxtTag.EOF.is_address() is False

    def test_is_data(self):
        assert TiTxtTag.DATA.is_data() is True
        assert TiTxtTag.ADDRESS.is_data() is False
        assert TiTxtTag.EOF.is_data() is False

    def test_is_eof(self):
        assert TiTxtTag.DATA.is_eof() is False
        assert TiTxtTag.ADDRESS.is_eof() is False
        assert TiTxtTag.EOF.is_eof() is True

    def test_is_file_termination(self):
        assert TiTxtTag.DATA.is_file_termination() is False
        assert TiTxtTag.ADDRESS.is_file_termination() is False
        assert TiTxtTag.EOF.is_file_termination() is True


class TestTiTxtRecord(BaseTestRecord):

    Record = TiTxtRecord

    def test_compute_count(self):
        assert TiTxtRecord.create_address(0x00000000).count == 4
        assert TiTxtRecord.create_address(0x00001234).count == 4
        assert TiTxtRecord.create_address(0x12345678, addrlen=8).count == 8
        assert TiTxtRecord.create_address(0, addrlen=1).count == 1
        assert TiTxtRecord.create_address(0, addrlen=2).count == 2
        assert TiTxtRecord.create_address(0, addrlen=3).count == 3
        assert TiTxtRecord.create_data(0, b'abc').count is None
        assert TiTxtRecord.create_eof().count is None

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
            record = TiTxtRecord.create_address(address, addrlen=addrlen)
            record.validate()
            assert record.tag == TiTxtTag.ADDRESS
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
                TiTxtRecord.create_address(address, addrlen=addrlen)

        with pytest.raises(ValueError, match='address overflow'):
            TiTxtRecord.create_address(-1)

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
                record = TiTxtRecord.create_data(address, data)
                record.validate()
                assert record.tag == TiTxtTag.DATA
                assert record.address == address
                assert record.checksum is None
                assert record.count is None
                assert record.data == data

    def test_create_eof(self):
        record = TiTxtRecord.create_eof()
        record.validate()
        assert record.tag == TiTxtTag.EOF
        assert record.address == 0
        assert record.checksum is None
        assert record.count is None
        assert record.data == b''

    def test_parse(self):
        lines = [
            b'@FFFF',
            b'@FFFFFFFF',
            b'FF',
            b'FF ' * 0x1000,
            b'q',
        ]
        records = [
            TiTxtRecord.create_address(0xFFFF),
            TiTxtRecord.create_address(0xFFFFFFFF, addrlen=8),
            TiTxtRecord.create_data(0, b'\xFF'),
            TiTxtRecord.create_data(0, b'\xFF' * 0x1000),
            TiTxtRecord.create_eof(),
        ]
        for line, expected in zip(lines, records):
            actual = TiTxtRecord.parse(line)
            assert actual == expected
            assert actual.before == b''
            assert actual.after == b''

    def test_parse_raises_syntax(self):
        lines = [
            b'@',
            b'@@FFFF',
            b'@FFFF.',
            b'.@FFFF',

            b'',
            b'XX',
            b'00.',
            b'FF.',

            b'Q',
        ]
        for line in lines:
            with pytest.raises(ValueError, match='syntax error'):
                TiTxtRecord.parse(line)

    # SRecord test script "t0112a.sh"
    def test_parse_srecord_t0112a(self):
        lines = [
            b'@F000',
            b'31 40 00 03 B2 40 80 5A 20 01 D2 D3 22 00 D2 E3',
            b'21 00 3F 40 E8 FD 1F 83 FE 23 F9 3F',
            b'@FFFE',
            b'00 F0',
            b'q',
        ]
        records = [
            TiTxtRecord.create_address(0xF000),
            TiTxtRecord.create_data(0x0000, b'\x31\x40\x00\x03\xB2\x40\x80\x5A\x20\x01\xD2\xD3\x22\x00\xD2\xE3'),
            TiTxtRecord.create_data(0x0000, b'\x21\x00\x3F\x40\xE8\xFD\x1F\x83\xFE\x23\xF9\x3F'),
            TiTxtRecord.create_address(0xFFFE),
            TiTxtRecord.create_data(0x0000, b'\x00\xF0'),
            TiTxtRecord.create_eof(),
        ]
        for line, expected in zip(lines, records):
            actual = TiTxtRecord.parse(line)
            assert actual == expected

    def test_parse_syntax(self):
        lines = [
            b'@0',
            b'@0000',
            b'@00000000',
            b'@FFFF',
            b'@FFFFFFFF',
            b'@00000000',
            b'@FFFFFFFF',
            b' \t\v\f\r@FFFFFFFF',
            b'@FFFFFFFF \t\v\f\r',
            b'@FFFFFFFF\r\n',
            b'@FFFFFFFF\n',
            b'@ffffffff',

            b'00',
            b'FF',
            b'FF' * 0x1000,
            b'FF ' * 0x1000,
            b'FF\t' * 0x1000,
            b' \t\v\f\rFF',
            b'FF \t\v\f\r',
            b'FF\r\n',
            b'FF\n',
            b'ff ' * 0x1000,

            b'q',
            b' \t\v\f\rq',
            b'q \t\v\f\r',
        ]
        records = [
            TiTxtRecord.create_address(0x00000000, addrlen=1),
            TiTxtRecord.create_address(0x00000000),
            TiTxtRecord.create_address(0x00000000, addrlen=8),
            TiTxtRecord.create_address(0x0000FFFF),
            TiTxtRecord.create_address(0xFFFFFFFF, addrlen=8),
            TiTxtRecord.create_address(0x00000000, addrlen=8),
            TiTxtRecord.create_address(0xFFFFFFFF, addrlen=8),
            TiTxtRecord.create_address(0xFFFFFFFF, addrlen=8),
            TiTxtRecord.create_address(0xFFFFFFFF, addrlen=8),
            TiTxtRecord.create_address(0xFFFFFFFF, addrlen=8),
            TiTxtRecord.create_address(0xFFFFFFFF, addrlen=8),
            TiTxtRecord.create_address(0xFFFFFFFF, addrlen=8),

            TiTxtRecord.create_data(0, b'\x00'),
            TiTxtRecord.create_data(0, b'\xFF'),
            TiTxtRecord.create_data(0, b'\xFF' * 0x1000),
            TiTxtRecord.create_data(0, b'\xFF' * 0x1000),
            TiTxtRecord.create_data(0, b'\xFF' * 0x1000),
            TiTxtRecord.create_data(0, b'\xFF'),
            TiTxtRecord.create_data(0, b'\xFF'),
            TiTxtRecord.create_data(0, b'\xFF'),
            TiTxtRecord.create_data(0, b'\xFF'),
            TiTxtRecord.create_data(0, b'\xFF' * 0x1000),

            TiTxtRecord.create_eof(),
            TiTxtRecord.create_eof(),
            TiTxtRecord.create_eof(),
        ]
        for line, expected in zip(lines, records):
            actual = TiTxtRecord.parse(line)
            assert actual == expected

    def test_to_bytestr(self):
        lines = [
            b'@0000\r\n',
            b'@FFFF\r\n',
            b'@00000000\r\n',
            b'@FFFFFFFF\r\n',

            b'00\r\n',
            b'FF\r\n',
            (b'FF ' * 0xFFF) + b'FF\r\n',

            b'q\r\n',
        ]
        records = [
            TiTxtRecord.create_address(0x00000000),
            TiTxtRecord.create_address(0x0000FFFF),
            TiTxtRecord.create_address(0x00000000, addrlen=8),
            TiTxtRecord.create_address(0xFFFFFFFF, addrlen=8),

            TiTxtRecord.create_data(0, b'\x00'),
            TiTxtRecord.create_data(0, b'\xFF'),
            TiTxtRecord.create_data(0, b'\xFF' * 0x1000),

            TiTxtRecord.create_eof(),
        ]
        for expected, record in zip(lines, records):
            record = _cast(TiTxtRecord, record)
            actual = record.to_bytestr()
            assert actual == expected

    def test_to_bytestr_end(self):
        record = TiTxtRecord.create_address(0x1234)
        assert record.to_bytestr() == b'@1234\r\n'
        assert record.to_bytestr(end=b'\n') == b'@1234\n'

        record = TiTxtRecord.create_data(0, b'\x11\x22\x33\x44')
        assert record.to_bytestr() == b'11 22 33 44\r\n'
        assert record.to_bytestr(end=b'\n') == b'11 22 33 44\n'

        record = TiTxtRecord.create_eof()
        assert record.to_bytestr() == b'q\r\n'
        assert record.to_bytestr(end=b'\n') == b'q\n'

    def test_to_tokens(self):
        lines = [
            b'||@0000|||\r\n',
            b'||@FFFF|||\r\n',
            b'||@00000000|||\r\n',
            b'||@FFFFFFFF|||\r\n',

            b'|||||\r\n',
            b'|||00||\r\n',
            b'|||FF||\r\n',
            b'|||' + (b'FF ' * 0xFFF) + b'FF||\r\n',

            b'|q||||\r\n',
        ]
        records = [
            TiTxtRecord.create_address(0x00000000),
            TiTxtRecord.create_address(0x0000FFFF),
            TiTxtRecord.create_address(0x00000000, addrlen=8),
            TiTxtRecord.create_address(0xFFFFFFFF, addrlen=8),

            TiTxtRecord.create_data(0, b''),
            TiTxtRecord.create_data(0, b'\x00'),
            TiTxtRecord.create_data(0, b'\xFF'),
            TiTxtRecord.create_data(0, b'\xFF' * 0x1000),

            TiTxtRecord.create_eof(),
        ]
        keys = [
            'before',
            'begin',
            'address',
            'data',
            'after',
            'end',
        ]
        for expected, record in zip(lines, records):
            tokens = record.to_tokens()
            assert all((key in keys) for key in tokens.keys())
            actual = b'|'.join(tokens.get(key, b'?') for key in keys)
            assert actual == expected

    def test_validate_raises(self):
        matches = [
            'junk after',
            'junk before',

            'count required',
            'count overflow',
            'count overflow',
            'unexpected data',

            'unexpected data',
        ]
        records = [
            TiTxtRecord(TiTxtTag.DATA, after=b'?', validate=False),
            TiTxtRecord(TiTxtTag.DATA, before=b'?', validate=False),

            TiTxtRecord(TiTxtTag.ADDRESS, count=None, validate=False),
            TiTxtRecord(TiTxtTag.ADDRESS, count=-1, validate=False),
            TiTxtRecord(TiTxtTag.ADDRESS, count=4, address=0x10000, validate=False),
            TiTxtRecord(TiTxtTag.ADDRESS, count=4, data=b'abc', validate=False),

            TiTxtRecord(TiTxtTag.EOF, data=b'abc', validate=False),
        ]
        for match, record in zip(matches, records):
            record = _cast(TiTxtRecord, record)
            with pytest.raises(ValueError, match=match):
                record.validate()

    def test_validate_samples(self):
        records = [
            TiTxtRecord.create_address(0x00000000),
            TiTxtRecord.create_address(0x0000FFFF),
            TiTxtRecord.create_address(0x00000000, addrlen=8),
            TiTxtRecord.create_address(0xFFFFFFFF, addrlen=8),

            TiTxtRecord.create_data(0, b'\x00'),
            TiTxtRecord.create_data(0, b'\xFF'),
            TiTxtRecord.create_data(0, b'\xFF' * 0x1000),

            TiTxtRecord.create_eof(),
        ]
        for record in records:
            returned = record.validate()
            assert returned is record


class TestTiTxtFile(BaseTestFile):

    File = TiTxtFile

    def test_load_file(self, datapath):
        path = str(datapath / 'simple.txt')
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_data(0x1234, b'xyz'),
            TiTxtRecord.create_eof(),
        ]
        file = TiTxtFile.load(path)
        assert file.records == records

    def test_load_stdin(self):
        buffer = (
            b'61 62 63\r\n'
            b'@1234\r\n'
            b'78 79 7A\r\n'
            b'q\r\n'
        )
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_data(0x1234, b'xyz'),
            TiTxtRecord.create_eof(),
        ]
        stream = io.BytesIO(buffer)
        with replace_stdin(stream):
            file = TiTxtFile.load(None)
        assert file._records == records

    def test_parse(self):
        buffer = (
            b'61 62 63\r\n'
            b'@1234\r\n'
            b'78 79 7A\r\n'
            b'q\r\n'
        )
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_data(0x1234, b'xyz'),
            TiTxtRecord.create_eof(),
        ]
        with io.BytesIO(buffer) as stream:
            file = TiTxtFile.parse(stream)
        assert file._records == records

    # SRecord test script "t0112a.sh"
    def test_parse_file_srecord_t0112a(self, datapath):
        path = str(datapath / 'srecord_t0112a_sh.txt')
        records = [
            TiTxtRecord.create_address(0xF000),
            TiTxtRecord.create_data(0xF000, b'\x31\x40\x00\x03\xB2\x40\x80\x5A\x20\x01\xD2\xD3\x22\x00\xD2\xE3'),
            TiTxtRecord.create_data(0xF010, b'\x21\x00\x3F\x40\xE8\xFD\x1F\x83\xFE\x23\xF9\x3F'),
            TiTxtRecord.create_address(0xFFFE),
            TiTxtRecord.create_data(0xFFFE, b'\x00\xF0'),
            TiTxtRecord.create_eof(),
        ]
        with open(path, 'rb') as stream:
            file = TiTxtFile.parse(stream)
        assert file._records == records

    def test_parse_ignore_errors(self):
        buffer = (
            b'61 62 63\r\n'
            b'@@1234\r\n'
            b'78 79 7A\r\n'
            b'q\r\n'
        )
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_data(0x0003, b'xyz'),
            TiTxtRecord.create_eof(),
        ]
        with io.BytesIO(buffer) as stream:
            file = TiTxtFile.parse(stream, ignore_errors=True)
        assert file._records == records

    def test_parse_plain(self):
        buffer = (
            b'61 62 63\r\n'
            b'@1234\r\n'
            b'78 79 7A\r\n'
        )
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_data(0x1234, b'xyz'),
        ]
        with io.BytesIO(buffer) as stream:
            file = TiTxtFile.parse(stream)
        assert file._records == records

    def test_parse_raises_syntax_error(self):
        buffer = (
            b'61 62 63\r\n'
            b'@@1234\r\n'
            b'78 79 7A\r\n'
            b'q\r\n'
        )
        with pytest.raises(ValueError, match='syntax error'):
            with io.BytesIO(buffer) as stream:
                TiTxtFile.parse(stream, ignore_errors=False)

    def test_save_file(self, tmppath):
        path = str(tmppath / 'test_save_file.txt')
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_data(0x1234, b'xyz'),
            TiTxtRecord.create_eof(),
        ]
        expected = (
            b'61 62 63\r\n'
            b'@1234\r\n'
            b'78 79 7A\r\n'
            b'q\r\n'
        )
        file = TiTxtFile.from_records(records)
        returned = file.save(path)
        assert returned is file
        with open(path, 'rb') as stream:
            actual = stream.read()
        assert actual == expected

    def test_save_stdout(self):
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_data(0x1234, b'xyz'),
            TiTxtRecord.create_eof(),
        ]
        expected = (
            b'61 62 63\r\n'
            b'@1234\r\n'
            b'78 79 7A\r\n'
            b'q\r\n'
        )
        stream = io.BytesIO()
        file = TiTxtFile.from_records(records)
        with replace_stdout(stream):
            returned = file.save(None)
        assert returned is file
        actual = stream.getvalue()
        assert actual == expected

    def test_serialize(self):
        expected = (
            b'61 62 63\r\n'
            b'@1234\r\n'
            b'78 79 7A\r\n'
            b'q\r\n'
        )
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_data(0x1234, b'xyz'),
            TiTxtRecord.create_eof(),
        ]
        file = TiTxtFile.from_records(records)
        stream = io.BytesIO()
        file.serialize(stream)
        actual = stream.getvalue()
        assert actual == expected

    def test_serialize_plain(self):
        expected = (
            b'61 62 63\r\n'
            b'@1234\r\n'
            b'78 79 7A\r\n'
        )
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_data(0x1234, b'xyz'),
        ]
        file = TiTxtFile.from_records(records)
        stream = io.BytesIO()
        file.serialize(stream)
        actual = stream.getvalue()
        assert actual == expected

    def test_update_records(self):
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_data(0x1234, b'xyz'),
            TiTxtRecord.create_eof(),
        ]
        blocks = [
            [0x0000, b'abc'],
            [0x1234, b'xyz'],
        ]
        file = TiTxtFile.from_blocks(blocks)
        file._records = None
        returned = file.update_records()
        assert returned is file
        assert file._records == records

    def test_update_records_addrlen(self):
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234, addrlen=8),
            TiTxtRecord.create_data(0x1234, b'xyz'),
            TiTxtRecord.create_eof(),
        ]
        blocks = [
            [0x0000, b'abc'],
            [0x1234, b'xyz'],
        ]
        file = TiTxtFile.from_blocks(blocks)
        file._records = None
        returned = file.update_records(addrlen=8)
        assert returned is file
        assert file._records == records

    def test_update_records_empty(self):
        file = TiTxtFile.from_memory()
        file._records = None
        file.update_records()
        assert file._records is not None
        assert file._records == [TiTxtRecord.create_eof()]

    def test_update_records_raises_addrlen(self):
        file = TiTxtFile()
        with pytest.raises(ValueError, match='invalid address length'):
            file.update_records(addrlen=0)

    def test_update_records_raises_memory(self):
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_data(0x1234, b'xyz'),
            TiTxtRecord.create_eof(),
        ]
        file = TiTxtFile.from_records(records)
        with pytest.raises(ValueError, match='memory instance required'):
            file.update_records()

    def test_validate_records(self):
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_data(0x1234, b'xyz'),
            TiTxtRecord.create_eof(),
        ]
        file = TiTxtFile.from_records(records)
        file.validate_records()

    def test_validate_records_address_even(self):
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_data(0x1234, b'xyz'),
            TiTxtRecord.create_eof(),
        ]
        file = TiTxtFile.from_records(records)
        file.validate_records(address_even=True)
        file.validate_records(address_even=False)

    def test_validate_records_data_ordering(self):
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_data(0x1234, b'xyz'),
            TiTxtRecord.create_eof(),
        ]
        file = TiTxtFile.from_records(records)
        file.validate_records(data_ordering=True)
        file.validate_records(data_ordering=False)

    def test_validate_records_raises_address_even(self):
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1235),
            TiTxtRecord.create_data(0x1235, b'xyz'),
            TiTxtRecord.create_eof(),
        ]
        file = TiTxtFile.from_records(records)
        with pytest.raises(ValueError, match='address not even'):
            file.validate_records(address_even=True)

    def test_validate_records_raises_data_ordering(self):
        records = [
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_data(0x1234, b'xyz'),
            TiTxtRecord.create_address(0x0000),
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_eof(),
        ]
        file = TiTxtFile.from_records(records)
        with pytest.raises(ValueError, match='unordered data record'):
            file.validate_records(data_ordering=True)

    def test_validate_records_raises_eof_missing(self):
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_data(0x1234, b'xyz'),
        ]
        file = TiTxtFile.from_records(records)
        with pytest.raises(ValueError, match='missing end of file record'):
            file.validate_records()

    def test_validate_records_raises_eof_not_last(self):
        records = [
            TiTxtRecord.create_data(0x0000, b'abc'),
            TiTxtRecord.create_address(0x1234),
            TiTxtRecord.create_eof(),
            TiTxtRecord.create_data(0x1234, b'xyz'),
        ]
        file = TiTxtFile.from_records(records)
        with pytest.raises(ValueError, match='end of file record not last'):
            file.validate_records()

    def test_validate_records_raises_records(self):
        file = TiTxtFile.from_memory(Memory.from_bytes(b'abc'))
        with pytest.raises(ValueError, match='records required'):
            file.validate_records()
