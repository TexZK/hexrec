import io
import os
from pathlib import Path

import pytest
from bytesparse import Memory
from test_base import BaseTestFile
from test_base import BaseTestRecord
from test_base import BaseTestTag
from test_base import replace_stdin
from test_base import replace_stdout

from hexrec.formats.xtek import XtekFile
from hexrec.formats.xtek import XtekRecord
from hexrec.formats.xtek import XtekTag


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


class TestXtekTag(BaseTestTag):

    Tag = XtekTag

    def test_enum(self):
        assert XtekTag.DATA == 6
        assert XtekTag.EOF == 8

    def test_is_data(self):
        assert XtekTag.DATA.is_data() is True
        assert XtekTag.EOF.is_data() is False

    def test_is_eof(self):
        assert XtekTag.DATA.is_eof() is False
        assert XtekTag.EOF.is_eof() is True

    def test_is_file_termination(self):
        assert XtekTag.DATA.is_file_termination() is False
        assert XtekTag.EOF.is_file_termination() is True


class TestXtekRecord(BaseTestRecord):

    Record = XtekRecord

    def test___init___addrlen(self):
        XtekRecord(XtekTag.EOF, addrlen=1)
        XtekRecord(XtekTag.EOF, addrlen=2)
        XtekRecord(XtekTag.EOF, addrlen=3)
        XtekRecord(XtekTag.EOF, addrlen=4)
        XtekRecord(XtekTag.EOF, addrlen=5)
        XtekRecord(XtekTag.EOF, addrlen=6)
        XtekRecord(XtekTag.EOF, addrlen=7)
        XtekRecord(XtekTag.EOF, addrlen=8)
        XtekRecord(XtekTag.EOF, addrlen=9)
        XtekRecord(XtekTag.EOF, addrlen=10)
        XtekRecord(XtekTag.EOF, addrlen=11)
        XtekRecord(XtekTag.EOF, addrlen=12)
        XtekRecord(XtekTag.EOF, addrlen=13)
        XtekRecord(XtekTag.EOF, addrlen=14)
        XtekRecord(XtekTag.EOF, addrlen=15)

    def test___init___raises_addrlen(self):
        with pytest.raises(ValueError, match='invalid address length'):
            XtekRecord(XtekTag.EOF, addrlen=0)
        with pytest.raises(ValueError, match='invalid address length'):
            XtekRecord(XtekTag.EOF, addrlen=16)

    def test_compute_address_max(self):
        vector = [
            (0x_0000_0000_0000_000F, 1),
            (0x_0000_0000_0000_00FF, 2),
            (0x_0000_0000_0000_0FFF, 3),
            (0x_0000_0000_0000_FFFF, 4),
            (0x_0000_0000_000F_FFFF, 5),
            (0x_0000_0000_00FF_FFFF, 6),
            (0x_0000_0000_0FFF_FFFF, 7),
            (0x_0000_0000_FFFF_FFFF, 8),
            (0x_0000_000F_FFFF_FFFF, 9),
            (0x_0000_00FF_FFFF_FFFF, 10),
            (0x_0000_0FFF_FFFF_FFFF, 11),
            (0x_0000_FFFF_FFFF_FFFF, 12),
            (0x_000F_FFFF_FFFF_FFFF, 13),
            (0x_00FF_FFFF_FFFF_FFFF, 14),
            (0x_0FFF_FFFF_FFFF_FFFF, 15),
        ]
        for address, addrlen in vector:
            assert XtekRecord.compute_address_max(addrlen) == address

    def test_compute_address_max_raises(self):
        with pytest.raises(ValueError, match='invalid address length'):
            XtekRecord.compute_address_max(0)
        with pytest.raises(ValueError, match='invalid address length'):
            XtekRecord.compute_address_max(16)

    def test_compute_checksum(self):
        vector = [
            (0x14, XtekRecord.create_data(0x00000000, b'', addrlen=4)),
            (0x1C, XtekRecord.create_data(0x00000000, b'', addrlen=8)),
            (0x1E, XtekRecord.create_data(0x00001234, b'', addrlen=4)),
            (0x40, XtekRecord.create_data(0x12345678, b'', addrlen=8)),
            (0x23, XtekRecord.create_data(0x00000000, b'abc', addrlen=4)),
            (0x2B, XtekRecord.create_data(0x00000000, b'abc', addrlen=8)),
            (0x2D, XtekRecord.create_data(0x00001234, b'abc', addrlen=4)),
            (0x4F, XtekRecord.create_data(0x12345678, b'abc', addrlen=8)),
            (0x16, XtekRecord.create_eof(0x00000000, addrlen=4)),
            (0x1E, XtekRecord.create_eof(0x00000000, addrlen=8)),
            (0x20, XtekRecord.create_eof(0x00001234, addrlen=4)),
            (0x42, XtekRecord.create_eof(0x12345678, addrlen=8)),
        ]
        for expected, record in vector:
            record.validate()
            actual = record.compute_checksum()
            assert actual == expected

    # https://web.archive.org/web/20200301021742/https://www.cypress.com/file/74296/download
    def test_compute_checksum_cypress(self):
        vector = [
            (0x06, b'%1A60641000FFFFFFFFFFFFFFFF\r\n'),
            (0x0E, b'%1A60E41008FFFFFFFFFFFFFFFF\r\n'),
            (0x07, b'%1A60741010FFFFFFFFFFFFFFFF\r\n'),
            (0x16, b'%0A81640000\r\n'),
        ]
        for expected, line in vector:
            record = XtekRecord.parse(line)
            record.validate()
            actual = record.compute_checksum()
            assert actual == expected

    def test_compute_checksum_raises(self):
        record = XtekRecord.create_data(0x00000000, b'', addrlen=4)
        record.count = None
        with pytest.raises(ValueError, match='missing count'):
            record.compute_checksum()

    def test_compute_count(self):
        vector = [
            (10, XtekRecord.create_data(0x00000000, b'', addrlen=4)),
            (14, XtekRecord.create_data(0x00000000, b'', addrlen=8)),
            (10, XtekRecord.create_data(0x00001234, b'', addrlen=4)),
            (14, XtekRecord.create_data(0x12345678, b'', addrlen=8)),
            (16, XtekRecord.create_data(0x00000000, b'abc', addrlen=4)),
            (20, XtekRecord.create_data(0x00000000, b'abc', addrlen=8)),
            (16, XtekRecord.create_data(0x00001234, b'abc', addrlen=4)),
            (20, XtekRecord.create_data(0x12345678, b'abc', addrlen=8)),
            (10, XtekRecord.create_eof(0x00000000, addrlen=4)),
            (14, XtekRecord.create_eof(0x00000000, addrlen=8)),
            (10, XtekRecord.create_eof(0x00001234, addrlen=4)),
            (14, XtekRecord.create_eof(0x12345678, addrlen=8)),
            (255, XtekRecord.create_data(0, b'X' * 124, addrlen=1)),
            (254, XtekRecord.create_data(0, b'X' * 123, addrlen=2)),
            (255, XtekRecord.create_data(0, b'X' * 123, addrlen=3)),
            (254, XtekRecord.create_data(0, b'X' * 122, addrlen=4)),
            (255, XtekRecord.create_data(0, b'X' * 122, addrlen=5)),
            (254, XtekRecord.create_data(0, b'X' * 121, addrlen=6)),
            (255, XtekRecord.create_data(0, b'X' * 121, addrlen=7)),
            (254, XtekRecord.create_data(0, b'X' * 120, addrlen=8)),
            (255, XtekRecord.create_data(0, b'X' * 120, addrlen=9)),
            (254, XtekRecord.create_data(0, b'X' * 119, addrlen=10)),
            (255, XtekRecord.create_data(0, b'X' * 119, addrlen=11)),
            (254, XtekRecord.create_data(0, b'X' * 118, addrlen=12)),
            (255, XtekRecord.create_data(0, b'X' * 118, addrlen=13)),
            (254, XtekRecord.create_data(0, b'X' * 117, addrlen=14)),
            (255, XtekRecord.create_data(0, b'X' * 117, addrlen=15)),
        ]
        for expected, record in vector:
            record.validate()
            actual = record.compute_count()
            assert actual == expected

    def test_compute_data_max(self):
        vector = [
            (124, 1),
            (123, 2),
            (123, 3),
            (122, 4),
            (122, 5),
            (121, 6),
            (121, 7),
            (120, 8),
            (120, 9),
            (119, 10),
            (119, 11),
            (118, 12),
            (118, 13),
            (117, 14),
            (117, 15),
        ]
        for datamax, addrlen in vector:
            assert XtekRecord.compute_data_max(addrlen) == datamax

    def test_compute_data_max_raises(self):
        with pytest.raises(ValueError, match='invalid address length'):
            XtekRecord.compute_data_max(0)
        with pytest.raises(ValueError, match='invalid address length'):
            XtekRecord.compute_data_max(16)

    def test_create_data(self):
        vector = [
            (0x00000000, b'', 4),
            (0x00001234, b'', 4),
            (0x00000000, b'abc', 4),
            (0x00001234, b'abc', 4),
            (0x00000000, b'', 8),
            (0x00001234, b'', 8),
            (0x00000000, b'abc', 8),
            (0x00001234, b'abc', 8),
            (0x12345678, b'abc', 8),
            (0, b'X' * 124, 1),
            (0, b'X' * 123, 2),
            (0, b'X' * 123, 3),
            (0, b'X' * 122, 4),
            (0, b'X' * 122, 5),
            (0, b'X' * 121, 6),
            (0, b'X' * 121, 7),
            (0, b'X' * 120, 8),
            (0, b'X' * 120, 9),
            (0, b'X' * 119, 10),
            (0, b'X' * 119, 11),
            (0, b'X' * 118, 12),
            (0, b'X' * 118, 13),
            (0, b'X' * 117, 14),
            (0, b'X' * 117, 15),
        ]
        for address, data, addrlen in vector:
            record = XtekRecord.create_data(address, data, addrlen=addrlen)
            record.validate()
            assert record.tag == XtekTag.DATA
            assert record.addrlen == addrlen
            assert record.address == address
            assert record.data == data

    def test_create_data_raises_address(self):
        vector = [
            (1, -1),
            (4, -1),
            (8, -1),
            (15, -1),
            (1, 0x10),
            (4, 0x1_0000),
            (8, 0x1_0000_0000),
            (15, 0x_1000_0000_0000_0000),
        ]
        for addrlen, address in vector:
            with pytest.raises(ValueError, match='address overflow'):
                XtekRecord.create_data(address, b'abc', addrlen=addrlen)

    def test_create_data_raises_addrlen(self):
        with pytest.raises(ValueError, match='invalid address length'):
            XtekRecord.create_data(0, b'abc', addrlen=0)
        with pytest.raises(ValueError, match='invalid address length'):
            XtekRecord.create_data(0, b'abc', addrlen=16)

    def test_create_data_raises_data(self):
        vector = [
            (1, b'X' * 125),
            (2, b'X' * 124),
            (3, b'X' * 124),
            (4, b'X' * 123),
            (5, b'X' * 123),
            (6, b'X' * 122),
            (7, b'X' * 122),
            (8, b'X' * 121),
            (9, b'X' * 121),
            (10, b'X' * 120),
            (11, b'X' * 120),
            (12, b'X' * 119),
            (13, b'X' * 119),
            (14, b'X' * 118),
            (15, b'X' * 118),
        ]
        for addrlen, data in vector:
            with pytest.raises(ValueError, match='data size overflow'):
                XtekRecord.create_data(0, data, addrlen=addrlen)

    def test_create_eof(self):
        vector = [
            (0x_0000_0000_0000_000F, 1),
            (0x_0000_0000_0000_00FF, 2),
            (0x_0000_0000_0000_0FFF, 3),
            (0x_0000_0000_0000_FFFF, 4),
            (0x_0000_0000_000F_FFFF, 5),
            (0x_0000_0000_00FF_FFFF, 6),
            (0x_0000_0000_0FFF_FFFF, 7),
            (0x_0000_0000_FFFF_FFFF, 8),
            (0x_0000_000F_FFFF_FFFF, 9),
            (0x_0000_00FF_FFFF_FFFF, 10),
            (0x_0000_0FFF_FFFF_FFFF, 11),
            (0x_0000_FFFF_FFFF_FFFF, 12),
            (0x_000F_FFFF_FFFF_FFFF, 13),
            (0x_00FF_FFFF_FFFF_FFFF, 14),
            (0x_0FFF_FFFF_FFFF_FFFF, 15),
        ]
        for address, addrlen in vector:
            record = XtekRecord.create_eof(address, addrlen=addrlen)
            record.validate()
            assert record.tag == XtekTag.EOF
            assert record.addrlen == addrlen
            assert record.address == address
            assert record.data == b''

    def test_create_eof_raises_address(self):
        vector = [
            (1, -1),
            (4, -1),
            (8, -1),
            (15, -1),
            (1, 0x10),
            (4, 0x1_0000),
            (8, 0x1_0000_0000),
            (15, 0x_1000_0000_0000_0000),
        ]
        for addrlen, address in vector:
            with pytest.raises(ValueError, match='address overflow'):
                XtekRecord.create_eof(address, addrlen=addrlen)

    def test_create_eof_raises_addrlen(self):
        with pytest.raises(ValueError, match='invalid address length'):
            XtekRecord.create_eof(0, addrlen=0)
        with pytest.raises(ValueError, match='invalid address length'):
            XtekRecord.create_eof(0, addrlen=16)

    def test_get_address_max(self):
        vector = [
            (0x_0000_0000_0000_000F, 1),
            (0x_0000_0000_0000_00FF, 2),
            (0x_0000_0000_0000_0FFF, 3),
            (0x_0000_0000_0000_FFFF, 4),
            (0x_0000_0000_000F_FFFF, 5),
            (0x_0000_0000_00FF_FFFF, 6),
            (0x_0000_0000_0FFF_FFFF, 7),
            (0x_0000_0000_FFFF_FFFF, 8),
            (0x_0000_000F_FFFF_FFFF, 9),
            (0x_0000_00FF_FFFF_FFFF, 10),
            (0x_0000_0FFF_FFFF_FFFF, 11),
            (0x_0000_FFFF_FFFF_FFFF, 12),
            (0x_000F_FFFF_FFFF_FFFF, 13),
            (0x_00FF_FFFF_FFFF_FFFF, 14),
            (0x_0FFF_FFFF_FFFF_FFFF, 15),
        ]
        for address, addrlen in vector:
            record = XtekRecord.create_eof(0, addrlen=addrlen)
            record.validate()
            assert record.get_address_max() == address

    def test_get_data_max(self):
        vector = [
            (124, 1),
            (123, 2),
            (123, 3),
            (122, 4),
            (122, 5),
            (121, 6),
            (121, 7),
            (120, 8),
            (120, 9),
            (119, 10),
            (119, 11),
            (118, 12),
            (118, 13),
            (117, 14),
            (117, 15),
        ]
        for datamax, addrlen in vector:
            record = XtekRecord.create_data(0, b'abc', addrlen=addrlen)
            record.validate()
            assert record.get_data_max() == datamax

    def test_get_meta(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'b', after=b'a', coords=(33, 44), validate=False, addrlen=4)
        actual = record.get_meta()
        expected = {
            'address': 0x1234,
            'addrlen': 4,
            'after': b'a',
            'before': b'b',
            'checksum': 0xA5,
            'coords': (33, 44),
            'count': 3,
            'data': b'xyz',
            'tag': Tag._DATA,
        }
        assert actual == expected

    def test_parse(self):
        lines = [
            b'%1A60741010FFFFFFFFFFFFFFFF\r\n',
            b'%0A81640000\r\n',
        ]
        records = [
            XtekRecord.create_data(0x1010, b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF', addrlen=4),
            XtekRecord.create_eof(addrlen=4),
        ]
        for line, expected in zip(lines, records):
            actual = XtekRecord.parse(line)
            actual.validate()
            assert actual == expected
            assert actual.after == b''
            assert actual.before == b''

    def test_parse_syntax(self):
        lines = [
            b'%%0E61C800000000\r\n',
            b'%..61C800000000\r\n',
            b'%0E.1C800000000\r\n',
            b'%0E6..800000000\r\n',
            b'%0E61C.00000000\r\n',
            b'%0E61C8........\r\n',
            b'%0E61C800000000\n\r\n',
            b'%1561BF00000000000000\r\n',
            b'%14619E0000000000000\r\n',
            b'%13617D000000000000\r\n',
            b'%12615C00000000000\r\n',
            b'%11613B0000000000\r\n',
            b'%10611A000000000\r\n',
            b'%0F61E900000000\r\n',
            b'%0E61C80000000\r\n',
            b'%0D61A7000000\r\n',
            b'%0C618600000\r\n',
            b'%0B61650000\r\n',
            b'%0A6144000\r\n',
            b'%09612300\r\n',
            b'%0861020\r\n',
            b'%0760E1\r\n',
        ]
        for line in lines:
            with pytest.raises(ValueError, match='syntax error'):
                XtekRecord.parse(line)

    def test_to_bytestr(self):
        lines = [
            b'%14635800001234616263\r\n',
            b'%1464D80000432178797A\r\n',
            b'%0E84C80000ABCD\r\n',
        ]
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_eof(0xABCD),
        ]
        for expected, record in zip(lines, records):
            actual = record.to_bytestr()
            assert actual == expected

    def test_to_tokens(self):
        lines = [
            b'|%|14|6|35|8|00001234|616263||\r\n',
            b'|%|0E|8|4C|8|0000ABCD|||\r\n',
        ]
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_eof(0xABCD),
        ]
        keys = [
            'before',
            'begin',
            'count',
            'tag',
            'checksum',
            'addrlen',
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

            'checksum overflow',
            'checksum overflow',

            'count overflow',
            'count overflow',

            'invalid address length',
            'invalid address length',

            'address overflow',
            'address overflow',

            'data size overflow',

            'unexpected data',
        ]
        records = [
            XtekRecord(XtekTag.DATA, validate=False, address=0x1234, data=b'abc', after=b'?'),
            XtekRecord(XtekTag.DATA, validate=False, address=0x1234, data=b'abc', before=b'%'),

            XtekRecord(XtekTag.DATA, validate=False, address=0x1234, data=b'abc', checksum=-1),
            XtekRecord(XtekTag.DATA, validate=False, address=0x1234, data=b'abc', checksum=0x100),

            XtekRecord(XtekTag.DATA, validate=False, address=0x1234, data=b'abc', count=-1),
            XtekRecord(XtekTag.DATA, validate=False, address=0x1234, data=b'abc', count=0x100),

            XtekRecord(XtekTag.DATA, validate=False, address=0x1234, data=b'abc', addrlen=0),
            XtekRecord(XtekTag.DATA, validate=False, address=0x1234, data=b'abc', addrlen=16),

            XtekRecord(XtekTag.DATA, validate=False, address=-1, data=b'abc', addrlen=4),
            XtekRecord(XtekTag.DATA, validate=False, address=0x10000, data=b'abc', addrlen=4),

            XtekRecord(XtekTag.DATA, validate=False, address=0x1234, data=(b'x' * 123), count=0xFF),

            XtekRecord(XtekTag.EOF, validate=False, address=0xABCD, data=b'x'),
        ]
        for match, record in zip(matches, records):
            record.compute_checksum = lambda: record.checksum  # fake
            record.compute_count = lambda: record.count  # fake

            with pytest.raises(ValueError, match=match):
                record.validate()


class TestXtekFile(BaseTestFile):

    File = XtekFile

    def test_apply_records(self):
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_eof(0xABCD),
        ]
        blocks = [
            [0x1234, b'abc'],
            [0x4321, b'xyz'],
        ]
        file = XtekFile.from_records(records)
        file._memory = Memory.from_bytes(b'discarded')
        file.apply_records()
        assert file._memory.to_blocks() == blocks
        assert file._startaddr == 0xABCD

    def test_apply_records_raises_records(self):
        file = XtekFile()
        with pytest.raises(ValueError, match='records required'):
            file.apply_records()

    def test_load_file(self, datapath):
        path = str(datapath / 'simple.xtek')
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_eof(0xABCD),
        ]
        file = XtekFile.load(path)
        assert file.records == records

    def test_load_stdin(self):
        buffer = (
            b'%14635800001234616263\r\n'
            b'%1464D80000432178797A\r\n'
            b'%0E84C80000ABCD\r\n'
        )
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_eof(0xABCD),
        ]
        stream = io.BytesIO(buffer)
        with replace_stdin(stream):
            file = XtekFile.load(None)
        assert file._records == records

    def test_parse(self):
        buffer = (
            b'%14635800001234616263\r\n'
            b'%1464D80000432178797A\r\n'
            b'%0E84C80000ABCD\r\n'
        )
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_eof(0xABCD),
        ]
        with io.BytesIO(buffer) as stream:
            file = XtekFile.parse(stream)
        assert file._records == records

    # https://web.archive.org/web/20200301021742/https://www.cypress.com/file/74296/download
    def test_parse_cypress(self, datapath):
        path = str(datapath / 'cypress.xtek')
        records = [
            XtekRecord.create_data(0x1000, b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF', addrlen=4),
            XtekRecord.create_data(0x1008, b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF', addrlen=4),
            XtekRecord.create_data(0x1010, b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF', addrlen=4),
            XtekRecord.create_eof(0x0000, addrlen=4),
        ]
        with open(path, 'rb') as stream:
            file = XtekFile.parse(stream)
        assert file.records == records

    def test_parse_junk(self):
        buffer = (
            b'%14635800001234616263\r\n'
            b'%1464D80000432178797A\r\n'
            b'%0E84C80000ABCD\r\n'
            b'junk\r\nafter'
        )
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_eof(0xABCD),
        ]
        with io.BytesIO(buffer) as stream:
            file = XtekFile.parse(stream, ignore_after_termination=True)
        assert file._records == records

    def test_parse_raises_junk(self):
        buffer = (
            b'%14635800001234616263\r\n'
            b'%1464D80000432178797A\r\n'
            b'%0E84C80000ABCD\r\n'
            b'junk\r\nafter'
        )
        with pytest.raises(ValueError, match='syntax error'):
            with io.BytesIO(buffer) as stream:
                XtekFile.parse(stream, ignore_after_termination=False)

    def test_save_file(self, tmppath):
        path = str(tmppath / 'test_save_file.xtek')
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_eof(0xABCD),
        ]
        expected = (
            b'%14635800001234616263\r\n'
            b'%1464D80000432178797A\r\n'
            b'%0E84C80000ABCD\r\n'
        )
        file = XtekFile.from_records(records)
        returned = file.save(path)
        assert returned is file
        with open(path, 'rb') as stream:
            actual = stream.read()
        assert actual == expected

    def test_save_stdout(self):
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_eof(0xABCD),
        ]
        expected = (
            b'%14635800001234616263\r\n'
            b'%1464D80000432178797A\r\n'
            b'%0E84C80000ABCD\r\n'
        )
        stream = io.BytesIO()
        file = XtekFile.from_records(records)
        with replace_stdout(stream):
            returned = file.save(None)
        assert returned is file
        actual = stream.getvalue()
        assert actual == expected

    def test_startaddr_getter(self):
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_eof(0xABCD),
        ]
        file = XtekFile.from_records(records)
        file._memory = None
        file._startaddr = 0
        assert file.startaddr == 0xABCD
        assert file._memory
        assert file._startaddr == 0xABCD

    def test_startaddr_setter(self):
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_eof(0xABCD),
        ]
        file = XtekFile.from_records(records)
        assert file.startaddr == 0xABCD
        assert file._startaddr == 0xABCD
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
        file = XtekFile()
        with pytest.raises(ValueError, match='invalid start address'):
            file.startaddr = -1
        with pytest.raises(ValueError, match='invalid start address'):
            file.startaddr = 0x100000000

    def test_update_records(self):
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_eof(0xABCD),
        ]
        blocks = [
            [0x1234, b'abc'],
            [0x4321, b'xyz'],
        ]
        file = XtekFile.from_blocks(blocks, startaddr=0xABCD)
        returned = file.update_records()
        assert returned is file
        assert file._records == records

    def test_update_records_addrlen(self):
        records = [
            XtekRecord.create_data(0x1234, b'abc', addrlen=4),
            XtekRecord.create_data(0x4321, b'xyz', addrlen=4),
            XtekRecord.create_eof(0xABCD, addrlen=4),
        ]
        blocks = [
            [0x1234, b'abc'],
            [0x4321, b'xyz'],
        ]
        file = XtekFile.from_blocks(blocks, startaddr=0xABCD)
        returned = file.update_records(addrlen=4)
        assert returned is file
        assert file._records == records

    def test_update_records_empty(self):
        file = XtekFile.from_blocks([], startaddr=0xABCD)
        returned = file.update_records()
        assert returned is file
        assert file._records == [XtekRecord.create_eof(0xABCD)]

    def test_update_records_raises_address(self):
        blocks = [
            [0x1234, b'abc'],
            [0x4321, b'xyz'],
        ]
        file = XtekFile.from_blocks(blocks, startaddr=0xABCD)
        with pytest.raises(ValueError, match='address overflow'):
            file.update_records(addrlen=3)

    def test_update_records_raises_addrlen(self):
        file = XtekFile()
        with pytest.raises(ValueError, match='invalid address length'):
            file.update_records(addrlen=0)
        with pytest.raises(ValueError, match='invalid address length'):
            file.update_records(addrlen=16)

    def test_update_records_raises_memory(self):
        file = XtekFile.from_records([])
        with pytest.raises(ValueError, match='memory instance required'):
            file.update_records()

    def test_validate_records(self):
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_eof(0xABCD),
        ]
        file = XtekFile.from_records(records)
        file.validate_records()

    def test_validate_records_data_ordering(self):
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_eof(0xABCD),
        ]
        file = XtekFile.from_records(records)
        file.validate_records(data_ordering=True)
        file.validate_records(data_ordering=False)

    def test_validate_records_raises_records(self):
        file = XtekFile()
        with pytest.raises(ValueError, match='records required'):
            file.validate_records()

    def test_validate_records_raises_data_ordering(self):
        records = [
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_eof(0xABCD),
        ]
        file = XtekFile.from_records(records)
        with pytest.raises(ValueError, match='unordered data record'):
            file.validate_records(data_ordering=True)

    def test_validate_records_raises_eof_last(self):
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_eof(0xABCD),
            XtekRecord.create_data(0x4321, b'xyz'),
        ]
        file = XtekFile.from_records(records)
        with pytest.raises(ValueError, match='end of file record not last'):
            file.validate_records()

    def test_validate_records_raises_eof_missing(self):
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
        ]
        file = XtekFile.from_records(records)
        with pytest.raises(ValueError, match='missing end of file record'):
            file.validate_records()

    def test_validate_records_raises_start_within_data(self):
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_eof(0xABCD),
        ]
        file = XtekFile.from_records(records)
        with pytest.raises(ValueError, match='no data at start address'):
            file.validate_records(start_within_data=True)

    def test_validate_records_start_within_data(self):
        records = [
            XtekRecord.create_data(0x1234, b'abc'),
            XtekRecord.create_data(0x4321, b'xyz'),
            XtekRecord.create_eof(0x1234),
        ]
        file = XtekFile.from_records(records)
        assert file.startaddr == 0x1234
        file.validate_records(start_within_data=True)
        file.validate_records(start_within_data=False)
