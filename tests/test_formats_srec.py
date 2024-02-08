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

from hexrec.formats.srec import SrecFile
from hexrec.formats.srec import SrecRecord
from hexrec.formats.srec import SrecTag


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


class TestSrecTag(BaseTestTag):

    Tag = SrecTag

    def test_enum(self):
        assert SrecTag.HEADER == 0
        assert SrecTag.DATA_16 == 1
        assert SrecTag.DATA_24 == 2
        assert SrecTag.DATA_32 == 3
        assert SrecTag.RESERVED == 4
        assert SrecTag.COUNT_16 == 5
        assert SrecTag.COUNT_24 == 6
        assert SrecTag.START_32 == 7
        assert SrecTag.START_24 == 8
        assert SrecTag.START_16 == 9

    def test_fit_count_tag_16(self):
        assert SrecTag.fit_count_tag(0x000000) == SrecTag.COUNT_16
        assert SrecTag.fit_count_tag(0x00FFFF) == SrecTag.COUNT_16

    def test_fit_count_tag_24(self):
        assert SrecTag.fit_count_tag(0x010000) == SrecTag.COUNT_24
        assert SrecTag.fit_count_tag(0xFFFFFF) == SrecTag.COUNT_24

    def test_fit_count_tag_raises(self):
        with pytest.raises(ValueError, match='count overflow'):
            SrecTag.fit_count_tag(-1)

        with pytest.raises(ValueError, match='count overflow'):
            SrecTag.fit_count_tag(0x1000000)

    def test_fit_data_tag_16(self):
        assert SrecTag.fit_data_tag(0x00000000) == SrecTag.DATA_16
        assert SrecTag.fit_data_tag(0x0000FFFF) == SrecTag.DATA_16

    def test_fit_data_tag_24(self):
        assert SrecTag.fit_data_tag(0x00010000) == SrecTag.DATA_24
        assert SrecTag.fit_data_tag(0x00FFFFFF) == SrecTag.DATA_24

    def test_fit_data_tag_32(self):
        assert SrecTag.fit_data_tag(0x01000000) == SrecTag.DATA_32
        assert SrecTag.fit_data_tag(0xFFFFFFFF) == SrecTag.DATA_32

    def test_fit_data_tag_raises(self):
        with pytest.raises(ValueError, match='address overflow'):
            SrecTag.fit_data_tag(-1)

        with pytest.raises(ValueError, match='address overflow'):
            SrecTag.fit_data_tag(0x100000000)

    def test_fit_start_tag_16(self):
        assert SrecTag.fit_start_tag(0x00000000) == SrecTag.START_16
        assert SrecTag.fit_start_tag(0x0000FFFF) == SrecTag.START_16

    def test_fit_start_tag_24(self):
        assert SrecTag.fit_start_tag(0x00010000) == SrecTag.START_24
        assert SrecTag.fit_start_tag(0x00FFFFFF) == SrecTag.START_24

    def test_fit_start_tag_32(self):
        assert SrecTag.fit_start_tag(0x01000000) == SrecTag.START_32
        assert SrecTag.fit_start_tag(0xFFFFFFFF) == SrecTag.START_32

    def test_fit_start_tag_raises(self):
        with pytest.raises(ValueError, match='address overflow'):
            SrecTag.fit_start_tag(-1)

        with pytest.raises(ValueError, match='address overflow'):
            SrecTag.fit_start_tag(0x100000000)

    def test_get_address_max(self):
        assert SrecTag.HEADER.get_address_max() == 0x0000FFFF
        assert SrecTag.DATA_16.get_address_max() == 0x0000FFFF
        assert SrecTag.DATA_24.get_address_max() == 0x00FFFFFF
        assert SrecTag.DATA_32.get_address_max() == 0xFFFFFFFF
        assert SrecTag.RESERVED.get_address_max() == 0
        assert SrecTag.COUNT_16.get_address_max() == 0x0000FFFF
        assert SrecTag.COUNT_24.get_address_max() == 0x00FFFFFF
        assert SrecTag.START_32.get_address_max() == 0xFFFFFFFF
        assert SrecTag.START_24.get_address_max() == 0x00FFFFFF
        assert SrecTag.START_16.get_address_max() == 0x0000FFFF

    def test_get_address_size(self):
        assert SrecTag.HEADER.get_address_size() == 2
        assert SrecTag.DATA_16.get_address_size() == 2
        assert SrecTag.DATA_24.get_address_size() == 3
        assert SrecTag.DATA_32.get_address_size() == 4
        assert SrecTag.RESERVED.get_address_size() == 0
        assert SrecTag.COUNT_16.get_address_size() == 2
        assert SrecTag.COUNT_24.get_address_size() == 3
        assert SrecTag.START_32.get_address_size() == 4
        assert SrecTag.START_24.get_address_size() == 3
        assert SrecTag.START_16.get_address_size() == 2

    def test_get_data_max(self):
        assert SrecTag.HEADER.get_data_max() == 0xFC
        assert SrecTag.DATA_16.get_data_max() == 0xFC
        assert SrecTag.DATA_24.get_data_max() == 0xFB
        assert SrecTag.DATA_32.get_data_max() == 0xFA
        assert SrecTag.RESERVED.get_data_max() == 0
        assert SrecTag.COUNT_16.get_data_max() == 0
        assert SrecTag.COUNT_24.get_data_max() == 0
        assert SrecTag.START_32.get_data_max() == 0
        assert SrecTag.START_24.get_data_max() == 0
        assert SrecTag.START_16.get_data_max() == 0

    def test_get_tag_match(self):
        assert SrecTag.HEADER.get_tag_match() is None
        assert SrecTag.DATA_16.get_tag_match() == SrecTag.START_16
        assert SrecTag.DATA_24.get_tag_match() == SrecTag.START_24
        assert SrecTag.DATA_32.get_tag_match() == SrecTag.START_32
        assert SrecTag.RESERVED.get_tag_match() is None
        assert SrecTag.COUNT_16.get_tag_match() is None
        assert SrecTag.COUNT_24.get_tag_match() is None
        assert SrecTag.START_32.get_tag_match() == SrecTag.DATA_32
        assert SrecTag.START_24.get_tag_match() == SrecTag.DATA_24
        assert SrecTag.START_16.get_tag_match() == SrecTag.DATA_16

    def test_is_count(self):
        assert SrecTag.HEADER.is_count() is False
        assert SrecTag.DATA_16.is_count() is False
        assert SrecTag.DATA_24.is_count() is False
        assert SrecTag.DATA_32.is_count() is False
        assert SrecTag.RESERVED.is_count() is False
        assert SrecTag.COUNT_16.is_count() is True
        assert SrecTag.COUNT_24.is_count() is True
        assert SrecTag.START_32.is_count() is False
        assert SrecTag.START_24.is_count() is False
        assert SrecTag.START_16.is_count() is False

    def test_is_data(self):
        assert SrecTag.HEADER.is_data() is False
        assert SrecTag.DATA_16.is_data() is True
        assert SrecTag.DATA_24.is_data() is True
        assert SrecTag.DATA_32.is_data() is True
        assert SrecTag.RESERVED.is_data() is False
        assert SrecTag.COUNT_16.is_data() is False
        assert SrecTag.COUNT_24.is_data() is False
        assert SrecTag.START_32.is_data() is False
        assert SrecTag.START_24.is_data() is False
        assert SrecTag.START_16.is_data() is False

    def test_is_file_termination(self):
        assert SrecTag.HEADER.is_file_termination() is False
        assert SrecTag.DATA_16.is_file_termination() is False
        assert SrecTag.DATA_24.is_file_termination() is False
        assert SrecTag.DATA_32.is_file_termination() is False
        assert SrecTag.RESERVED.is_file_termination() is False
        assert SrecTag.COUNT_16.is_file_termination() is False
        assert SrecTag.COUNT_24.is_file_termination() is False
        assert SrecTag.START_32.is_file_termination() is True
        assert SrecTag.START_24.is_file_termination() is True
        assert SrecTag.START_16.is_file_termination() is True

    def test_is_header(self):
        assert SrecTag.HEADER.is_header() is True
        assert SrecTag.DATA_16.is_header() is False
        assert SrecTag.DATA_24.is_header() is False
        assert SrecTag.DATA_32.is_header() is False
        assert SrecTag.RESERVED.is_header() is False
        assert SrecTag.COUNT_16.is_header() is False
        assert SrecTag.COUNT_24.is_header() is False
        assert SrecTag.START_32.is_header() is False
        assert SrecTag.START_24.is_header() is False
        assert SrecTag.START_16.is_header() is False

    def test_is_start(self):
        assert SrecTag.HEADER.is_start() is False
        assert SrecTag.DATA_16.is_start() is False
        assert SrecTag.DATA_24.is_start() is False
        assert SrecTag.DATA_32.is_start() is False
        assert SrecTag.RESERVED.is_start() is False
        assert SrecTag.COUNT_16.is_start() is False
        assert SrecTag.COUNT_24.is_start() is False
        assert SrecTag.START_32.is_start() is True
        assert SrecTag.START_24.is_start() is True
        assert SrecTag.START_16.is_start() is True


class TestSrecRecord(BaseTestRecord):

    Record = SrecRecord

    def test_compute_checksum(self):
        vector = [
            (0xFC, SrecRecord.create_header(b'')),
            (0xD3, SrecRecord.create_header(b'abc')),
            (0xFC, SrecRecord.create_data(0x00000000, b'')),
            (0xB6, SrecRecord.create_data(0x00001234, b'')),
            (0x5F, SrecRecord.create_data(0x00123456, b'')),
            (0xE6, SrecRecord.create_data(0x12345678, b'')),
            (0xD3, SrecRecord.create_data(0x00000000, b'abc')),
            (0x8D, SrecRecord.create_data(0x00001234, b'abc')),
            (0x36, SrecRecord.create_data(0x00123456, b'abc')),
            (0xBD, SrecRecord.create_data(0x12345678, b'abc')),
        ]
        for expected, record in vector:
            record.validate()
            actual = record.compute_checksum()
            assert actual == expected

    # https://en.wikipedia.org/wiki/SREC_(file_format)#Checksum_calculation
    def test_compute_checksum_wikipedia(self):
        line = b'S1137AF00A0A0D0000000000000000000000000061\r\n'
        record = SrecRecord.parse(line)
        record.validate()
        checksum = record.compute_checksum()
        assert checksum == 0x61

    def test_compute_count(self):
        vector = [
            (3, SrecRecord.create_header(b'')),
            (6, SrecRecord.create_header(b'abc')),
            (3, SrecRecord.create_data(0x00000000, b'')),
            (6, SrecRecord.create_data(0x00000000, b'abc')),
            (3, SrecRecord.create_data(0x00001234, b'')),
            (6, SrecRecord.create_data(0x00001234, b'abc')),
            (4, SrecRecord.create_data(0x00123456, b'')),
            (7, SrecRecord.create_data(0x00123456, b'abc')),
            (5, SrecRecord.create_data(0x12345678, b'')),
            (8, SrecRecord.create_data(0x12345678, b'abc')),
        ]
        for expected, record in vector:
            record.validate()
            actual = record.compute_count()
            assert actual == expected

    def test_create_count(self):
        vector = [
            (0x000000, SrecTag.COUNT_16, None),
            (0x00FFFF, SrecTag.COUNT_16, None),
            (0x000000, SrecTag.COUNT_16, SrecTag.COUNT_16),
            (0x00FFFF, SrecTag.COUNT_16, SrecTag.COUNT_16),
            (0x000000, SrecTag.COUNT_24, SrecTag.COUNT_24),
            (0x00FFFF, SrecTag.COUNT_24, SrecTag.COUNT_24),
            (0x010000, SrecTag.COUNT_24, None),
            (0xFFFFFF, SrecTag.COUNT_24, None),
            (0x010000, SrecTag.COUNT_24, SrecTag.COUNT_24),
            (0xFFFFFF, SrecTag.COUNT_24, SrecTag.COUNT_24),
        ]
        for count, tag_out, tag_in in vector:
            record = SrecRecord.create_count(count, tag=tag_in)
            record.validate()
            assert record.tag == tag_out
            assert record.address == count
            assert record.count == tag_out.get_address_size() + 1
            assert record.data == b''

    def test_create_count_raises_count(self):
        vector = [
            (SrecTag.COUNT_16, -1),
            (SrecTag.COUNT_16, 0x0010000),
            (SrecTag.COUNT_24, -1),
            (SrecTag.COUNT_24, 0x1000000),
            (None, -1),
            (None, 0x1000000),
        ]
        for tag, count in vector:
            with pytest.raises(ValueError, match='count overflow'):
                SrecRecord.create_count(count, tag=tag)

    def test_create_count_raises_tag(self):
        tags = [tag for tag in SrecTag if not tag.is_count()]
        assert tags
        for tag in tags:
            with pytest.raises(ValueError, match='invalid count tag'):
                SrecRecord.create_count(0, tag=tag)

    def test_create_data(self):
        contents = [
            b'',
            b'abc',
            b'a' * 0xFA,
        ]
        vector = [
            (0x00000000, SrecTag.DATA_16, None),
            (0x0000FFFF, SrecTag.DATA_16, None),
            (0x00000000, SrecTag.DATA_16, SrecTag.DATA_16),
            (0x0000FFFF, SrecTag.DATA_16, SrecTag.DATA_16),
            (0x00000000, SrecTag.DATA_24, SrecTag.DATA_24),
            (0x0000FFFF, SrecTag.DATA_24, SrecTag.DATA_24),
            (0x00000000, SrecTag.DATA_32, SrecTag.DATA_32),
            (0x0000FFFF, SrecTag.DATA_32, SrecTag.DATA_32),
            (0x00010000, SrecTag.DATA_24, None),
            (0x00FFFFFF, SrecTag.DATA_24, None),
            (0x00010000, SrecTag.DATA_24, SrecTag.DATA_24),
            (0x00FFFFFF, SrecTag.DATA_24, SrecTag.DATA_24),
            (0x00010000, SrecTag.DATA_32, SrecTag.DATA_32),
            (0x00FFFFFF, SrecTag.DATA_32, SrecTag.DATA_32),
            (0x01000000, SrecTag.DATA_32, None),
            (0xFFFFFFFF, SrecTag.DATA_32, None),
            (0x00010000, SrecTag.DATA_32, SrecTag.DATA_32),
            (0xFFFFFFFF, SrecTag.DATA_32, SrecTag.DATA_32),
        ]
        for data in contents:
            for address, tag_out, tag_in in vector:
                record = SrecRecord.create_data(address, data, tag=tag_in)
                record.validate()
                assert record.tag == tag_out
                assert record.address == address
                assert record.count == tag_out.get_address_size() + len(data) + 1
                assert record.data == data

    def test_create_data_raises_address(self):
        vector = [
            (SrecTag.DATA_16, -1),
            (SrecTag.DATA_16, 0x000010000),
            (SrecTag.DATA_24, -1),
            (SrecTag.DATA_24, 0x001000000),
            (SrecTag.DATA_32, -1),
            (SrecTag.DATA_32, 0x100000000),
            (None, -1),
            (None, 0x100000000),
        ]
        for tag, address in vector:
            with pytest.raises(ValueError, match='address overflow'):
                SrecRecord.create_data(address, b'abc', tag=tag)

    def test_create_data_raises_data(self):
        vector = [
            (SrecTag.DATA_16, b'a' * 0xFD),
            (SrecTag.DATA_24, b'a' * 0xFC),
            (SrecTag.DATA_32, b'a' * 0xFB),
            (None, b'a' * 0xFD),
        ]
        for tag, data in vector:
            with pytest.raises(ValueError, match='data size overflow'):
                SrecRecord.create_data(0, data, tag=tag)

    def test_create_data_raises_tag(self):
        tags = [tag for tag in SrecTag if not tag.is_data()]
        assert tags
        for tag in tags:
            with pytest.raises(ValueError, match='invalid data tag'):
                SrecRecord.create_data(0, b'abc', tag=tag)

    def test_create_header(self):
        contents = [
            b'',
            b'abc',
            b'a' * 0xFA,
        ]
        for data in contents:
            record = SrecRecord.create_header(data)
            record.validate()
            assert record.tag == SrecTag.HEADER
            assert record.address == 0
            assert record.count == 3 + len(data)
            assert record.data == data

    def test_create_header_raises_data(self):
        with pytest.raises(ValueError, match='data size overflow'):
            SrecRecord.create_header(b'a' * 0xFD)

    def test_create_start(self):
        vector = [
            (0x00000000, SrecTag.START_16, None),
            (0x0000FFFF, SrecTag.START_16, None),
            (0x00000000, SrecTag.START_16, SrecTag.START_16),
            (0x0000FFFF, SrecTag.START_16, SrecTag.START_16),
            (0x00000000, SrecTag.START_24, SrecTag.START_24),
            (0x0000FFFF, SrecTag.START_24, SrecTag.START_24),
            (0x00000000, SrecTag.START_32, SrecTag.START_32),
            (0x0000FFFF, SrecTag.START_32, SrecTag.START_32),
            (0x00010000, SrecTag.START_24, None),
            (0x00FFFFFF, SrecTag.START_24, None),
            (0x00010000, SrecTag.START_24, SrecTag.START_24),
            (0x00FFFFFF, SrecTag.START_24, SrecTag.START_24),
            (0x00010000, SrecTag.START_32, SrecTag.START_32),
            (0x00FFFFFF, SrecTag.START_32, SrecTag.START_32),
            (0x01000000, SrecTag.START_32, None),
            (0xFFFFFFFF, SrecTag.START_32, None),
            (0x00010000, SrecTag.START_32, SrecTag.START_32),
            (0xFFFFFFFF, SrecTag.START_32, SrecTag.START_32),
        ]
        for address, tag_out, tag_in in vector:
            record = SrecRecord.create_start(address, tag=tag_in)
            record.validate()
            assert record.tag == tag_out
            assert record.address == address
            assert record.count == tag_out.get_address_size() + 1
            assert record.data == b''

    def test_create_start_raises_address(self):
        vector = [
            (SrecTag.START_16, -1),
            (SrecTag.START_16, 0x000010000),
            (SrecTag.START_24, -1),
            (SrecTag.START_24, 0x001000000),
            (SrecTag.START_32, -1),
            (SrecTag.START_32, 0x100000000),
            (None, -1),
            (None, 0x100000000),
        ]
        for tag, address in vector:
            with pytest.raises(ValueError, match='address overflow'):
                SrecRecord.create_start(address, tag=tag)

    def test_create_start_raises_tag(self):
        tags = [tag for tag in SrecTag if not tag.is_start()]
        assert tags
        for tag in tags:
            with pytest.raises(ValueError, match='invalid start tag'):
                SrecRecord.create_start(0, tag=tag)

    def test_parse(self):
        lines = [
            b'S0030000FC\r\n',
            b'S0FF0000' + (b'00' * 0xFC) + b'00\r\n',
            b'S0FF0000' + (b'FF' * 0xFC) + b'FC\r\n',

            b'S1030000FC\r\n',
            b'S1FF0000' + (b'00' * 0xFC) + b'00\r\n',
            b'S1FF0000' + (b'FF' * 0xFC) + b'FC\r\n',
            b'S103FFFFFE\r\n',
            b'S1FFFFFF' + (b'00' * 0xFC) + b'02\r\n',
            b'S1FFFFFF' + (b'FF' * 0xFC) + b'FE\r\n',

            b'S204000000FB\r\n',
            b'S2FF000000' + (b'00' * 0xFB) + b'00\r\n',
            b'S2FF000000' + (b'FF' * 0xFB) + b'FB\r\n',
            b'S204FFFFFFFE\r\n',
            b'S2FFFFFFFF' + (b'00' * 0xFB) + b'03\r\n',
            b'S2FFFFFFFF' + (b'FF' * 0xFB) + b'FE\r\n',

            b'S30500000000FA\r\n',
            b'S3FF00000000' + (b'00' * 0xFA) + b'00\r\n',
            b'S3FF00000000' + (b'FF' * 0xFA) + b'FA\r\n',
            b'S305FFFFFFFFFE\r\n',
            b'S3FFFFFFFFFF' + (b'00' * 0xFA) + b'04\r\n',
            b'S3FFFFFFFFFF' + (b'FF' * 0xFA) + b'FE\r\n',

            b'S5030000FC\r\n',
            b'S503FFFFFE\r\n',

            b'S604000000FB\r\n',
            b'S604FFFFFFFE\r\n',

            b'S70500000000FA\r\n',
            b'S705FFFFFFFFFE\r\n',

            b'S804000000FB\r\n',
            b'S804FFFFFFFE\r\n',

            b'S9030000FC\r\n',
            b'S903FFFFFE\r\n',
        ]
        records = [
            SrecRecord(SrecTag.HEADER, count=0x03, checksum=0xFC, data=b''),
            SrecRecord(SrecTag.HEADER, count=0xFF, checksum=0x00, data=(b'\x00' * 0xFC)),
            SrecRecord(SrecTag.HEADER, count=0xFF, checksum=0xFC, data=(b'\xFF' * 0xFC)),

            SrecRecord(SrecTag.DATA_16, count=0x03, address=0x00000000, checksum=0xFC, data=b''),
            SrecRecord(SrecTag.DATA_16, count=0xFF, address=0x00000000, checksum=0x00, data=(b'\x00' * 0xFC)),
            SrecRecord(SrecTag.DATA_16, count=0xFF, address=0x00000000, checksum=0xFC, data=(b'\xFF' * 0xFC)),
            SrecRecord(SrecTag.DATA_16, count=0x03, address=0x0000FFFF, checksum=0xFE, data=b''),
            SrecRecord(SrecTag.DATA_16, count=0xFF, address=0x0000FFFF, checksum=0x02, data=(b'\x00' * 0xFC)),
            SrecRecord(SrecTag.DATA_16, count=0xFF, address=0x0000FFFF, checksum=0xFE, data=(b'\xFF' * 0xFC)),

            SrecRecord(SrecTag.DATA_24, count=0x04, address=0x00000000, checksum=0xFB, data=b''),
            SrecRecord(SrecTag.DATA_24, count=0xFF, address=0x00000000, checksum=0x00, data=(b'\x00' * 0xFB)),
            SrecRecord(SrecTag.DATA_24, count=0xFF, address=0x00000000, checksum=0xFB, data=(b'\xFF' * 0xFB)),
            SrecRecord(SrecTag.DATA_24, count=0x04, address=0x00FFFFFF, checksum=0xFE, data=b''),
            SrecRecord(SrecTag.DATA_24, count=0xFF, address=0x00FFFFFF, checksum=0x03, data=(b'\x00' * 0xFB)),
            SrecRecord(SrecTag.DATA_24, count=0xFF, address=0x00FFFFFF, checksum=0xFE, data=(b'\xFF' * 0xFB)),

            SrecRecord(SrecTag.DATA_32, count=0x05, address=0x00000000, checksum=0xFA, data=b''),
            SrecRecord(SrecTag.DATA_32, count=0xFF, address=0x00000000, checksum=0x00, data=(b'\x00' * 0xFA)),
            SrecRecord(SrecTag.DATA_32, count=0xFF, address=0x00000000, checksum=0xFA, data=(b'\xFF' * 0xFA)),
            SrecRecord(SrecTag.DATA_32, count=0x05, address=0xFFFFFFFF, checksum=0xFE, data=b''),
            SrecRecord(SrecTag.DATA_32, count=0xFF, address=0xFFFFFFFF, checksum=0x04, data=(b'\x00' * 0xFA)),
            SrecRecord(SrecTag.DATA_32, count=0xFF, address=0xFFFFFFFF, checksum=0xFE, data=(b'\xFF' * 0xFA)),

            SrecRecord(SrecTag.COUNT_16, count=0x03, address=0x00000000, checksum=0xFC),
            SrecRecord(SrecTag.COUNT_16, count=0x03, address=0x0000FFFF, checksum=0xFE),

            SrecRecord(SrecTag.COUNT_24, count=0x04, address=0x00000000, checksum=0xFB),
            SrecRecord(SrecTag.COUNT_24, count=0x04, address=0x00FFFFFF, checksum=0xFE),

            SrecRecord(SrecTag.START_32, count=0x05, address=0x00000000, checksum=0xFA),
            SrecRecord(SrecTag.START_32, count=0x05, address=0xFFFFFFFF, checksum=0xFE),

            SrecRecord(SrecTag.START_24, count=0x04, address=0x00000000, checksum=0xFB),
            SrecRecord(SrecTag.START_24, count=0x04, address=0x00FFFFFF, checksum=0xFE),

            SrecRecord(SrecTag.START_16, count=0x03, address=0x00000000, checksum=0xFC),
            SrecRecord(SrecTag.START_16, count=0x03, address=0x0000FFFF, checksum=0xFE),
        ]
        for line, expected in zip(lines, records):
            actual = SrecRecord.parse(line)
            actual.validate()
            expected.validate()
            assert actual == expected

    def test_parse_raises_syntax(self):
        lines = [
            b'SS1030000FC\r\n',
            b'.S1030000FC\r\n',
            b'51030000FC\r\n',
            b'S.030000FC\r\n',
            b'S1..0000FC\r\n',
            b'S103....FC\r\n',
            b'S1030000..\r\n',
            b'S1030000\r\n',
            b'S1030000FC\r\r\n',
            b'S1030000FC\n\r\n',

            b'S10300FC\r\n',
            b'S2030000FC\r\n',
            b'S303000000FC\r\n',
            b'S50300FC\r\n',
            b'S6030000FC\r\n',
            b'S703000000FC\r\n',
            b'S8030000FC\r\n',
            b'S90300FC\r\n',
        ]
        for line in lines:
            with pytest.raises(ValueError, match='syntax error'):
                SrecRecord.parse(line)

    def test_parse_syntax(self):
        lines = [
            b'S0030000FC\r\n',
            b's0030000fc\r\n',
            b'S0030000FC',
            b'S0030000FC ',
            b'S0030000FC\r',
            b'S0030000FC\n',
            b' \t\v\rS1030000FC\r\n',
            b'S1030000FC \t\v\r\n',
            b'S1030000FC;\r\n',
        ]
        for line in lines:
            record = SrecRecord.parse(line)
            record.validate()

    # https://en.wikipedia.org/wiki/SREC_(file_format)#16-bit_memory_address
    def test_parse_wikipedia(self):
        lines = [
            b'S00F000068656C6C6F202020202000003C\r\n',
            b'S11F00007C0802A6900100049421FFF07C6C1B787C8C23783C6000003863000026\r\n',
            b'S11F001C4BFFFFE5398000007D83637880010014382100107C0803A64E800020E9\r\n',
            b'S111003848656C6C6F20776F726C642E0A0042\r\n',
            b'S5030003F9\r\n',
            b'S9030000FC\r\n',
        ]
        records = [
            SrecRecord(SrecTag.HEADER, count=0x0F, checksum=0x3C,
                       data=b'\x68\x65\x6C\x6C\x6F\x20\x20\x20\x20\x20\x00\x00'),
            SrecRecord(SrecTag.DATA_16, count=0x1F, address=0x0000, checksum=0x26,
                       data=(b'\x7C\x08\x02\xA6\x90\x01\x00\x04\x94\x21\xFF\xF0\x7C\x6C\x1B\x78'
                             b'\x7C\x8C\x23\x78\x3C\x60\x00\x00\x38\x63\x00\x00')),
            SrecRecord(SrecTag.DATA_16, count=0x1F, address=0x001C, checksum=0xE9,
                       data=(b'\x4B\xFF\xFF\xE5\x39\x80\x00\x00\x7D\x83\x63\x78\x80\x01\x00\x14'
                             b'\x38\x21\x00\x10\x7C\x08\x03\xA6\x4E\x80\x00\x20')),
            SrecRecord(SrecTag.DATA_16, count=0x11, address=0x0038, checksum=0x42,
                       data=b'\x48\x65\x6C\x6C\x6F\x20\x77\x6F\x72\x6C\x64\x2E\x0A\x00'),
            SrecRecord(SrecTag.COUNT_16, count=0x03, address=0x0003, checksum=0xF9),
            SrecRecord(SrecTag.START_16, count=0x03, address=0x0000, checksum=0xFC),
        ]
        for line, expected in zip(lines, records):
            actual = SrecRecord.parse(line)
            actual.validate()
            expected.validate()
            assert actual == expected

    def test_to_bytestr(self):
        lines = [
            b'S0030000FC\r\n',
            b'S0FF0000' + (b'00' * 0xFC) + b'00\r\n',
            b'S0FF0000' + (b'FF' * 0xFC) + b'FC\r\n',

            b'S1030000FC\r\n',
            b'S1FF0000' + (b'00' * 0xFC) + b'00\r\n',
            b'S1FF0000' + (b'FF' * 0xFC) + b'FC\r\n',
            b'S103FFFFFE\r\n',
            b'S1FFFFFF' + (b'00' * 0xFC) + b'02\r\n',
            b'S1FFFFFF' + (b'FF' * 0xFC) + b'FE\r\n',

            b'S204000000FB\r\n',
            b'S2FF000000' + (b'00' * 0xFB) + b'00\r\n',
            b'S2FF000000' + (b'FF' * 0xFB) + b'FB\r\n',
            b'S204FFFFFFFE\r\n',
            b'S2FFFFFFFF' + (b'00' * 0xFB) + b'03\r\n',
            b'S2FFFFFFFF' + (b'FF' * 0xFB) + b'FE\r\n',

            b'S30500000000FA\r\n',
            b'S3FF00000000' + (b'00' * 0xFA) + b'00\r\n',
            b'S3FF00000000' + (b'FF' * 0xFA) + b'FA\r\n',
            b'S305FFFFFFFFFE\r\n',
            b'S3FFFFFFFFFF' + (b'00' * 0xFA) + b'04\r\n',
            b'S3FFFFFFFFFF' + (b'FF' * 0xFA) + b'FE\r\n',

            b'S5030000FC\r\n',
            b'S503FFFFFE\r\n',

            b'S604000000FB\r\n',
            b'S604FFFFFFFE\r\n',

            b'S70500000000FA\r\n',
            b'S705FFFFFFFFFE\r\n',

            b'S804000000FB\r\n',
            b'S804FFFFFFFE\r\n',

            b'S9030000FC\r\n',
            b'S903FFFFFE\r\n',
        ]
        records = [
            SrecRecord.create_header(b''),
            SrecRecord.create_header(b'\x00' * 0xFC),
            SrecRecord.create_header(b'\xFF' * 0xFC),

            SrecRecord.create_data(0x00000000, b'', tag=SrecTag.DATA_16),
            SrecRecord.create_data(0x00000000, (b'\x00' * 0xFC), tag=SrecTag.DATA_16),
            SrecRecord.create_data(0x00000000, (b'\xFF' * 0xFC), tag=SrecTag.DATA_16),
            SrecRecord.create_data(0x0000FFFF, b'', tag=SrecTag.DATA_16),
            SrecRecord.create_data(0x0000FFFF, (b'\x00' * 0xFC), tag=SrecTag.DATA_16),
            SrecRecord.create_data(0x0000FFFF, (b'\xFF' * 0xFC), tag=SrecTag.DATA_16),

            SrecRecord.create_data(0x00000000, b'', tag=SrecTag.DATA_24),
            SrecRecord.create_data(0x00000000, (b'\x00' * 0xFB), tag=SrecTag.DATA_24),
            SrecRecord.create_data(0x00000000, (b'\xFF' * 0xFB), tag=SrecTag.DATA_24),
            SrecRecord.create_data(0x00FFFFFF, b'', tag=SrecTag.DATA_24),
            SrecRecord.create_data(0x00FFFFFF, (b'\x00' * 0xFB), tag=SrecTag.DATA_24),
            SrecRecord.create_data(0x00FFFFFF, (b'\xFF' * 0xFB), tag=SrecTag.DATA_24),

            SrecRecord.create_data(0x00000000, b'', tag=SrecTag.DATA_32),
            SrecRecord.create_data(0x00000000, (b'\x00' * 0xFA), tag=SrecTag.DATA_32),
            SrecRecord.create_data(0x00000000, (b'\xFF' * 0xFA), tag=SrecTag.DATA_32),
            SrecRecord.create_data(0xFFFFFFFF, b'', tag=SrecTag.DATA_32),
            SrecRecord.create_data(0xFFFFFFFF, (b'\x00' * 0xFA), tag=SrecTag.DATA_32),
            SrecRecord.create_data(0xFFFFFFFF, (b'\xFF' * 0xFA), tag=SrecTag.DATA_32),

            SrecRecord.create_count(0x00000000, tag=SrecTag.COUNT_16),
            SrecRecord.create_count(0x0000FFFF, tag=SrecTag.COUNT_16),

            SrecRecord.create_count(0x00000000, tag=SrecTag.COUNT_24),
            SrecRecord.create_count(0x00FFFFFF, tag=SrecTag.COUNT_24),

            SrecRecord.create_start(0x00000000, tag=SrecTag.START_32),
            SrecRecord.create_start(0xFFFFFFFF, tag=SrecTag.START_32),

            SrecRecord.create_start(0x00000000, tag=SrecTag.START_24),
            SrecRecord.create_start(0x00FFFFFF, tag=SrecTag.START_24),

            SrecRecord.create_start(0x00000000, tag=SrecTag.START_16),
            SrecRecord.create_start(0x0000FFFF, tag=SrecTag.START_16),
        ]
        for expected, record in zip(lines, records):
            actual = record.to_bytestr()
            assert actual == expected

    def test_to_tokens(self):
        lines = [
            b'|S|0|03|0000||FC||\r\n',
            b'|S|0|FF|0000|' + (b'00' * 0xFC) + b'|00||\r\n',
            b'|S|0|FF|0000|' + (b'FF' * 0xFC) + b'|FC||\r\n',

            b'|S|1|03|0000||FC||\r\n',
            b'|S|1|FF|0000|' + (b'00' * 0xFC) + b'|00||\r\n',
            b'|S|1|FF|0000|' + (b'FF' * 0xFC) + b'|FC||\r\n',
            b'|S|1|03|FFFF||FE||\r\n',
            b'|S|1|FF|FFFF|' + (b'00' * 0xFC) + b'|02||\r\n',
            b'|S|1|FF|FFFF|' + (b'FF' * 0xFC) + b'|FE||\r\n',

            b'|S|2|04|000000||FB||\r\n',
            b'|S|2|FF|000000|' + (b'00' * 0xFB) + b'|00||\r\n',
            b'|S|2|FF|000000|' + (b'FF' * 0xFB) + b'|FB||\r\n',
            b'|S|2|04|FFFFFF||FE||\r\n',
            b'|S|2|FF|FFFFFF|' + (b'00' * 0xFB) + b'|03||\r\n',
            b'|S|2|FF|FFFFFF|' + (b'FF' * 0xFB) + b'|FE||\r\n',

            b'|S|3|05|00000000||FA||\r\n',
            b'|S|3|FF|00000000|' + (b'00' * 0xFA) + b'|00||\r\n',
            b'|S|3|FF|00000000|' + (b'FF' * 0xFA) + b'|FA||\r\n',
            b'|S|3|05|FFFFFFFF||FE||\r\n',
            b'|S|3|FF|FFFFFFFF|' + (b'00' * 0xFA) + b'|04||\r\n',
            b'|S|3|FF|FFFFFFFF|' + (b'FF' * 0xFA) + b'|FE||\r\n',

            b'|S|5|03|0000||FC||\r\n',
            b'|S|5|03|FFFF||FE||\r\n',

            b'|S|6|04|000000||FB||\r\n',
            b'|S|6|04|FFFFFF||FE||\r\n',

            b'|S|7|05|00000000||FA||\r\n',
            b'|S|7|05|FFFFFFFF||FE||\r\n',

            b'|S|8|04|000000||FB||\r\n',
            b'|S|8|04|FFFFFF||FE||\r\n',

            b'|S|9|03|0000||FC||\r\n',
            b'|S|9|03|FFFF||FE||\r\n',
        ]
        records = [
            SrecRecord.create_header(b''),
            SrecRecord.create_header(b'\x00' * 0xFC),
            SrecRecord.create_header(b'\xFF' * 0xFC),

            SrecRecord.create_data(0x00000000, b'', tag=SrecTag.DATA_16),
            SrecRecord.create_data(0x00000000, (b'\x00' * 0xFC), tag=SrecTag.DATA_16),
            SrecRecord.create_data(0x00000000, (b'\xFF' * 0xFC), tag=SrecTag.DATA_16),
            SrecRecord.create_data(0x0000FFFF, b'', tag=SrecTag.DATA_16),
            SrecRecord.create_data(0x0000FFFF, (b'\x00' * 0xFC), tag=SrecTag.DATA_16),
            SrecRecord.create_data(0x0000FFFF, (b'\xFF' * 0xFC), tag=SrecTag.DATA_16),

            SrecRecord.create_data(0x00000000, b'', tag=SrecTag.DATA_24),
            SrecRecord.create_data(0x00000000, (b'\x00' * 0xFB), tag=SrecTag.DATA_24),
            SrecRecord.create_data(0x00000000, (b'\xFF' * 0xFB), tag=SrecTag.DATA_24),
            SrecRecord.create_data(0x00FFFFFF, b'', tag=SrecTag.DATA_24),
            SrecRecord.create_data(0x00FFFFFF, (b'\x00' * 0xFB), tag=SrecTag.DATA_24),
            SrecRecord.create_data(0x00FFFFFF, (b'\xFF' * 0xFB), tag=SrecTag.DATA_24),

            SrecRecord.create_data(0x00000000, b'', tag=SrecTag.DATA_32),
            SrecRecord.create_data(0x00000000, (b'\x00' * 0xFA), tag=SrecTag.DATA_32),
            SrecRecord.create_data(0x00000000, (b'\xFF' * 0xFA), tag=SrecTag.DATA_32),
            SrecRecord.create_data(0xFFFFFFFF, b'', tag=SrecTag.DATA_32),
            SrecRecord.create_data(0xFFFFFFFF, (b'\x00' * 0xFA), tag=SrecTag.DATA_32),
            SrecRecord.create_data(0xFFFFFFFF, (b'\xFF' * 0xFA), tag=SrecTag.DATA_32),

            SrecRecord.create_count(0x00000000, tag=SrecTag.COUNT_16),
            SrecRecord.create_count(0x0000FFFF, tag=SrecTag.COUNT_16),

            SrecRecord.create_count(0x00000000, tag=SrecTag.COUNT_24),
            SrecRecord.create_count(0x00FFFFFF, tag=SrecTag.COUNT_24),

            SrecRecord.create_start(0x00000000, tag=SrecTag.START_32),
            SrecRecord.create_start(0xFFFFFFFF, tag=SrecTag.START_32),

            SrecRecord.create_start(0x00000000, tag=SrecTag.START_24),
            SrecRecord.create_start(0x00FFFFFF, tag=SrecTag.START_24),

            SrecRecord.create_start(0x00000000, tag=SrecTag.START_16),
            SrecRecord.create_start(0x0000FFFF, tag=SrecTag.START_16),
        ]
        keys = [
            'before',
            'begin',
            'tag',
            'count',
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

    def test_validate_raises(self):
        matches = [
            # 'junk after',
            'junk before',

            'checksum overflow',
            'checksum overflow',

            'count overflow',
            'count overflow',

            'reserved tag',

            'unexpected data',
            'unexpected data',
            'unexpected data',
            'unexpected data',
            'unexpected data',

            'data size overflow',
            'data size overflow',
            'data size overflow',

            'address overflow',
            'address overflow',
            'address overflow',
            'address overflow',
            'address overflow',
            'address overflow',
            'address overflow',
            'address overflow',
        ]
        records = [
            # SrecRecord(SrecTag.DATA_16, validate=False, after=b'?'),
            SrecRecord(SrecTag.DATA_16, validate=False, before=b'?'),

            SrecRecord(SrecTag.DATA_16, validate=False, checksum=-1),
            SrecRecord(SrecTag.DATA_16, validate=False, checksum=0x100),

            SrecRecord(SrecTag.DATA_16, validate=False, count=2),
            SrecRecord(SrecTag.DATA_16, validate=False, count=0x100),

            SrecRecord(SrecTag.RESERVED, validate=False, count=3, checksum=0),

            SrecRecord(SrecTag.COUNT_16, validate=False, data=b'x'),
            SrecRecord(SrecTag.COUNT_24, validate=False, data=b'x'),
            SrecRecord(SrecTag.START_32, validate=False, data=b'x'),
            SrecRecord(SrecTag.START_24, validate=False, data=b'x'),
            SrecRecord(SrecTag.START_16, validate=False, data=b'x'),

            SrecRecord(SrecTag.DATA_16, validate=False, data=(b'x' * 0xFD), count=0xFF),
            SrecRecord(SrecTag.DATA_24, validate=False, data=(b'x' * 0xFC), count=0xFF),
            SrecRecord(SrecTag.DATA_32, validate=False, data=(b'x' * 0xFB), count=0xFF),

            SrecRecord(SrecTag.HEADER, validate=False, address=0x10000),
            SrecRecord(SrecTag.DATA_16, validate=False, address=0x10000),
            SrecRecord(SrecTag.DATA_24, validate=False, address=0x1000000),
            SrecRecord(SrecTag.DATA_32, validate=False, address=0x100000000),
            SrecRecord(SrecTag.COUNT_16, validate=False, address=0x10000),
            SrecRecord(SrecTag.COUNT_24, validate=False, address=0x1000000),
            SrecRecord(SrecTag.START_32, validate=False, address=0x100000000),
            SrecRecord(SrecTag.START_24, validate=False, address=0x1000000),
            SrecRecord(SrecTag.START_16, validate=False, address=0x10000),
        ]
        for match, record in zip(matches, records):
            record.compute_checksum = lambda: record.checksum  # fake
            record.compute_count = lambda: record.count  # fake

            with pytest.raises(ValueError, match=match):
                record.validate()

    def test_validate_samples(self):
        records = [
            SrecRecord(SrecTag.HEADER, count=0x03, checksum=0xFC, data=b''),
            SrecRecord(SrecTag.HEADER, count=0xFF, checksum=0x00, data=(b'\x00' * 0xFC)),
            SrecRecord(SrecTag.HEADER, count=0xFF, checksum=0xFC, data=(b'\xFF' * 0xFC)),

            SrecRecord(SrecTag.DATA_16, count=0x03, address=0x00000000, checksum=0xFC, data=b''),
            SrecRecord(SrecTag.DATA_16, count=0xFF, address=0x00000000, checksum=0x00, data=(b'\x00' * 0xFC)),
            SrecRecord(SrecTag.DATA_16, count=0xFF, address=0x00000000, checksum=0xFC, data=(b'\xFF' * 0xFC)),
            SrecRecord(SrecTag.DATA_16, count=0x03, address=0x0000FFFF, checksum=0xFE, data=b''),
            SrecRecord(SrecTag.DATA_16, count=0xFF, address=0x0000FFFF, checksum=0x02, data=(b'\x00' * 0xFC)),
            SrecRecord(SrecTag.DATA_16, count=0xFF, address=0x0000FFFF, checksum=0xFE, data=(b'\xFF' * 0xFC)),

            SrecRecord(SrecTag.DATA_24, count=0x04, address=0x00000000, checksum=0xFB, data=b''),
            SrecRecord(SrecTag.DATA_24, count=0xFF, address=0x00000000, checksum=0x00, data=(b'\x00' * 0xFB)),
            SrecRecord(SrecTag.DATA_24, count=0xFF, address=0x00000000, checksum=0xFB, data=(b'\xFF' * 0xFB)),
            SrecRecord(SrecTag.DATA_24, count=0x04, address=0x00FFFFFF, checksum=0xFE, data=b''),
            SrecRecord(SrecTag.DATA_24, count=0xFF, address=0x00FFFFFF, checksum=0x03, data=(b'\x00' * 0xFB)),
            SrecRecord(SrecTag.DATA_24, count=0xFF, address=0x00FFFFFF, checksum=0xFE, data=(b'\xFF' * 0xFB)),

            SrecRecord(SrecTag.DATA_32, count=0x05, address=0x00000000, checksum=0xFA, data=b''),
            SrecRecord(SrecTag.DATA_32, count=0xFF, address=0x00000000, checksum=0x00, data=(b'\x00' * 0xFA)),
            SrecRecord(SrecTag.DATA_32, count=0xFF, address=0x00000000, checksum=0xFA, data=(b'\xFF' * 0xFA)),
            SrecRecord(SrecTag.DATA_32, count=0x05, address=0xFFFFFFFF, checksum=0xFE, data=b''),
            SrecRecord(SrecTag.DATA_32, count=0xFF, address=0xFFFFFFFF, checksum=0x04, data=(b'\x00' * 0xFA)),
            SrecRecord(SrecTag.DATA_32, count=0xFF, address=0xFFFFFFFF, checksum=0xFE, data=(b'\xFF' * 0xFA)),

            SrecRecord(SrecTag.COUNT_16, count=0x03, address=0x00000000, checksum=0xFC),
            SrecRecord(SrecTag.COUNT_16, count=0x03, address=0x0000FFFF, checksum=0xFE),

            SrecRecord(SrecTag.COUNT_24, count=0x04, address=0x00000000, checksum=0xFB),
            SrecRecord(SrecTag.COUNT_24, count=0x04, address=0x00FFFFFF, checksum=0xFE),

            SrecRecord(SrecTag.START_32, count=0x05, address=0x00000000, checksum=0xFA),
            SrecRecord(SrecTag.START_32, count=0x05, address=0xFFFFFFFF, checksum=0xFE),

            SrecRecord(SrecTag.START_24, count=0x04, address=0x00000000, checksum=0xFB),
            SrecRecord(SrecTag.START_24, count=0x04, address=0x00FFFFFF, checksum=0xFE),

            SrecRecord(SrecTag.START_16, count=0x03, address=0x00000000, checksum=0xFC),
            SrecRecord(SrecTag.START_16, count=0x03, address=0x0000FFFF, checksum=0xFE),
        ]
        for record in records:
            returned = record.validate()
            assert returned is record


# ----------------------------------------------------------------------------

class TestSrecFile(BaseTestFile):

    File = SrecFile

    def test_apply_records(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        blocks = [
            [0x1234, b'abc'],
            [0x4321, b'xyz'],
        ]
        file = SrecFile.from_records(records)
        file._memory = Memory.from_bytes(b'discarded')
        file.apply_records()
        assert file._memory.to_blocks() == blocks
        assert file._header == b'HDR\0'
        assert file._startaddr == 0xABCD

    def test_apply_records_raises_records(self):
        file = SrecFile()
        with pytest.raises(ValueError, match='records required'):
            file.apply_records()

    def test_header_getter(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        file._memory = None
        file._header = None
        assert file.header == b'HDR\0'
        assert file._memory
        assert file._header == b'HDR\0'

    def test_header_setter(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        assert file.header == b'HDR\0'
        assert file._header == b'HDR\0'
        assert file._records
        file.header = b'NEW'
        assert file._records is None
        assert file._header == b'NEW'
        assert file.header == b'NEW'
        assert file._records is None
        file.header = b'NEW'
        assert file._records is None
        assert file._header == b'NEW'
        assert file.header == b'NEW'
        assert file._records is None
        file.header = b''
        file.header = bytes(range(0xFC))

    def test_header_setter_raises(self):
        file = SrecFile()
        with pytest.raises(ValueError, match='data size overflow'):
            file.header = bytes(range(0xFD))

    def test_load_file(self, datapath):
        path = str(datapath / 'simple.srec')
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x12345678, b'abc'),
            SrecRecord.create_count(1),
            SrecRecord.create_start(0x89ABCDEF),
        ]
        file = SrecFile.load(path)
        assert file.records == records

    def test_load_stdin(self):
        buffer = (
            b'S0070000484452001A\r\n'
            b'S30812345678616263BD\r\n'
            b'S5030001FB\r\n'
            b'S70589ABCDEF0A\r\n'
        )
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x12345678, b'abc'),
            SrecRecord.create_count(1),
            SrecRecord.create_start(0x89ABCDEF),
        ]
        stream = io.BytesIO(buffer)
        with replace_stdin(stream):
            file = SrecFile.load(None)
        assert file._records == records

    def test_parse(self):
        buffer = (
            b'S0070000484452001A\r\n'
            b'S30812345678616263BD\r\n'
            b'S5030001FB\r\n'
            b'S70589ABCDEF0A\r\n'
        )
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x12345678, b'abc'),
            SrecRecord.create_count(1),
            SrecRecord.create_start(0x89ABCDEF),
        ]
        with io.BytesIO(buffer) as stream:
            file = SrecFile.parse(stream)
        assert file._records == records

    def test_parse_file_wikipedia(self, datapath):
        path = str(datapath / 'wikipedia.s19')
        records = [
            SrecRecord(SrecTag.HEADER, count=0x0F, checksum=0x3C,
                       data=b'\x68\x65\x6C\x6C\x6F\x20\x20\x20\x20\x20\x00\x00'),
            SrecRecord(SrecTag.DATA_16, count=0x1F, address=0x0000, checksum=0x26,
                       data=(b'\x7C\x08\x02\xA6\x90\x01\x00\x04\x94\x21\xFF\xF0\x7C\x6C\x1B\x78'
                             b'\x7C\x8C\x23\x78\x3C\x60\x00\x00\x38\x63\x00\x00')),
            SrecRecord(SrecTag.DATA_16, count=0x1F, address=0x001C, checksum=0xE9,
                       data=(b'\x4B\xFF\xFF\xE5\x39\x80\x00\x00\x7D\x83\x63\x78\x80\x01\x00\x14'
                             b'\x38\x21\x00\x10\x7C\x08\x03\xA6\x4E\x80\x00\x20')),
            SrecRecord(SrecTag.DATA_16, count=0x11, address=0x0038, checksum=0x42,
                       data=b'\x48\x65\x6C\x6C\x6F\x20\x77\x6F\x72\x6C\x64\x2E\x0A\x00'),
            SrecRecord(SrecTag.COUNT_16, count=0x03, address=0x0003, checksum=0xF9),
            SrecRecord(SrecTag.START_16, count=0x03, address=0x0000, checksum=0xFC),
        ]
        with open(path, 'rb') as stream:
            file = SrecFile.parse(stream)
        assert file.records == records

    def test_parse_junk(self):
        buffer = (
            b'S0070000484452001A\r\n'
            b'S30812345678616263BD\r\n'
            b'S5030001FB\r\n'
            b'S70589ABCDEF0A\r\n'
            b'junk\r\nafter'
        )
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x12345678, b'abc'),
            SrecRecord.create_count(1),
            SrecRecord.create_start(0x89ABCDEF),
        ]
        with io.BytesIO(buffer) as stream:
            file = SrecFile.parse(stream, ignore_after_termination=True)
        assert file._records == records

    def test_parse_raises_junk(self):
        buffer = (
            b'S0070000484452001A\r\n'
            b'S30812345678616263BD\r\n'
            b'S5030001FB\r\n'
            b'S70589ABCDEF0A\r\n'
            b'junk\r\nafter'
        )
        with pytest.raises(ValueError, match='syntax error'):
            with io.BytesIO(buffer) as stream:
                SrecFile.parse(stream, ignore_after_termination=False)

    def test_save_file(self, tmppath):
        path = str(tmppath / 'test_save_file.srec')
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x12345678, b'abc'),
            SrecRecord.create_count(1),
            SrecRecord.create_start(0x89ABCDEF),
        ]
        expected = (
            b'S0070000484452001A\r\n'
            b'S30812345678616263BD\r\n'
            b'S5030001FB\r\n'
            b'S70589ABCDEF0A\r\n'
        )
        file = SrecFile.from_records(records)
        returned = file.save(path)
        assert returned is file
        with open(path, 'rb') as stream:
            actual = stream.read()
        assert actual == expected

    def test_save_stdout(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x12345678, b'abc'),
            SrecRecord.create_count(1),
            SrecRecord.create_start(0x89ABCDEF),
        ]
        expected = (
            b'S0070000484452001A\r\n'
            b'S30812345678616263BD\r\n'
            b'S5030001FB\r\n'
            b'S70589ABCDEF0A\r\n'
        )
        stream = io.BytesIO()
        file = SrecFile.from_records(records)
        with replace_stdout(stream):
            returned = file.save(None)
        assert returned is file
        actual = stream.getvalue()
        assert actual == expected

    def test_startaddr_empty(self):
        file = SrecFile()
        assert not file._memory
        assert file._startaddr == 0
        assert file.startaddr == 0
        file.startaddr = 0xFFFFFFFF
        assert file._startaddr == 0xFFFFFFFF
        assert file.startaddr == 0xFFFFFFFF

    def test_startaddr_getter(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        file._memory = None
        file._startaddr = 0
        assert file.startaddr == 0xABCD
        assert file._memory
        assert file._startaddr == 0xABCD

    def test_startaddr_setter(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
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
        file = SrecFile()
        with pytest.raises(ValueError, match='invalid start address'):
            file.startaddr = -1
        with pytest.raises(ValueError, match='invalid start address'):
            file.startaddr = 0x100000000

    def test_update_records(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        blocks = [
            [0x1234, b'abc'],
            [0x4321, b'xyz'],
        ]
        file = SrecFile.from_blocks(blocks, header=b'HDR\0', startaddr=0xABCD)
        returned = file.update_records(header=True, count=True, start=True)
        assert returned is file
        assert file._records == records

    def test_update_records_address_max(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc', tag=SrecTag.DATA_32),
            SrecRecord.create_data(0x4321, b'xyz', tag=SrecTag.DATA_32),
            SrecRecord.create_count(2, tag=SrecTag.COUNT_24),
            SrecRecord.create_start(0xABCD, tag=SrecTag.START_32),
        ]
        blocks = [
            [0x1234, b'abc'],
            [0x4321, b'xyz'],
        ]
        file = SrecFile.from_blocks(blocks, header=b'HDR\0', startaddr=0xABCD)
        file.update_records(header=True, data=True, count=True, start=True,
                            data_tag=SrecTag.DATA_32, count_tag=SrecTag.COUNT_24)
        assert file._records == records

    def test_update_records_empty(self):
        records = [
            SrecRecord.create_header(),
            SrecRecord.create_data(0, b''),
            SrecRecord.create_count(1),
            SrecRecord.create_start(),
        ]
        file = SrecFile()
        file.update_records(header=True, data=True, count=True, start=True)
        assert file._records == records

    def test_update_records_header_none(self):
        records = [
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        blocks = [
            [0x1234, b'abc'],
            [0x4321, b'xyz'],
        ]
        file = SrecFile.from_blocks(blocks, header=None, startaddr=0xABCD)
        file.update_records(header=False, count=True, start=True)
        assert file._records == records

    def test_update_records_no_count(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_start(0xABCD),
        ]
        blocks = [
            [0x1234, b'abc'],
            [0x4321, b'xyz'],
        ]
        file = SrecFile.from_blocks(blocks, header=b'HDR\0', startaddr=0xABCD)
        file.update_records(header=True, count=False, start=True)
        assert file._records == records

    def test_update_records_no_data(self):
        records = [
            SrecRecord.create_header(),
            SrecRecord.create_count(0),
            SrecRecord.create_start(),
        ]
        file = SrecFile()
        file.update_records(header=True, data=False, count=True, start=True)
        assert file._records == records

    def test_update_records_no_header(self):
        records = [
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        blocks = [
            [0x1234, b'abc'],
            [0x4321, b'xyz'],
        ]
        file = SrecFile.from_blocks(blocks, header=b'HDR\0', startaddr=0xABCD)
        file.update_records(header=False, count=True, start=True)
        assert file._records == records

    def test_update_records_no_startaddr(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0x0000),
        ]
        blocks = [
            [0x1234, b'abc'],
            [0x4321, b'xyz'],
        ]
        file = SrecFile.from_blocks(blocks, header=b'HDR\0', startaddr=0xABCD)
        file.update_records(header=True, count=True, start=False)
        assert file._records == records

    def test_update_records_raises(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        file._memory = None
        with pytest.raises(ValueError, match='memory instance required'):
            file.update_records()

    def test_validate_records(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        file.validate_records()

    def test_validate_records_count_penultimate(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        file.validate_records(count_required=False, count_penultimate=True)
        file.validate_records(count_required=False, count_penultimate=False)

    def test_validate_records_count_required(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        file.validate_records(count_required=True, count_penultimate=False)
        file.validate_records(count_required=False, count_penultimate=False)

    def test_validate_records_data_uniform(self):
        tags = [
            SrecTag.DATA_16,
            SrecTag.DATA_24,
            SrecTag.DATA_32,
        ]
        for tag in tags:
            records = [
                SrecRecord.create_header(b'HDR\0'),
                SrecRecord.create_data(0x4321, b'xyz', tag=tag),
                SrecRecord.create_data(0x1234, b'abc', tag=tag),
                SrecRecord.create_count(2),
                SrecRecord.create_start(0xABCD, tag=tag.get_tag_match()),
            ]
            file = SrecFile.from_records(records)
            file.validate_records(data_ordering=False, data_uniform=True)
            file.validate_records(data_ordering=False, data_uniform=False)

    def test_validate_records_raises_count_multi(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_count(2),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        with pytest.raises(ValueError, match='multiple count records'):
            file.validate_records(count_required=False, count_penultimate=False)

    def test_validate_records_raises_count_penultimate(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_count(2),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        with pytest.raises(ValueError, match='count record not penultimate'):
            file.validate_records(count_required=False, count_penultimate=True)

    def test_validate_records_raises_count_required(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        with pytest.raises(ValueError, match='missing count record'):
            file.validate_records(count_required=True, count_penultimate=False)

    def test_validate_records_raises_count_wrong(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_count(3),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        with pytest.raises(ValueError, match='wrong data record count'):
            file.validate_records(count_required=False, count_penultimate=False)

    def test_validate_records_raises_data_ordering(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        with pytest.raises(ValueError, match='unordered data record'):
            file.validate_records(data_ordering=True, data_uniform=False)

    def test_validate_records_raises_data_uniform(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc', tag=SrecTag.DATA_16),
            SrecRecord.create_data(0x4321, b'xyz', tag=SrecTag.DATA_32),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        with pytest.raises(ValueError, match='data record tags not uniform'):
            file.validate_records(data_ordering=False, data_uniform=True)

        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD, tag=SrecTag.START_32),
        ]
        file = SrecFile.from_records(records)
        with pytest.raises(ValueError, match='start record tag not uniform'):
            file.validate_records(data_ordering=False, data_uniform=True)

    def test_validate_records_raises_header_required(self):
        records = [
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        with pytest.raises(ValueError, match='missing header record'):
            file.validate_records(header_required=True, header_first=False)

        records = [
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        file.validate_records(header_required=True, header_first=False)

    def test_validate_records_raises_header_first(self):
        records = [
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        with pytest.raises(ValueError, match='header record not first'):
            file.validate_records(header_required=False, header_first=True)

        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        with pytest.raises(ValueError, match='header record not first'):
            file.validate_records(header_required=False, header_first=True)

    def test_validate_records_raises_records(self):
        file = SrecFile()
        with pytest.raises(ValueError, match='records required'):
            file.validate_records()

    def test_validate_records_raises_start_last(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_start(0xABCD),
            SrecRecord.create_count(2),
        ]
        file = SrecFile.from_records(records)
        with pytest.raises(ValueError, match='start record not last'):
            file.validate_records(start_last=True, count_penultimate=False)

    def test_validate_records_raises_start_missing(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
        ]
        file = SrecFile.from_records(records)
        with pytest.raises(ValueError, match='missing start record'):
            file.validate_records(start_last=False, count_penultimate=False)

    def test_validate_records_raises_start_multi(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        with pytest.raises(ValueError, match='multiple start records'):
            file.validate_records(start_last=False, count_penultimate=False)

    def test_validate_records_raises_start_within_data(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0xABCD),
        ]
        file = SrecFile.from_records(records)
        with pytest.raises(ValueError, match='no data at start address'):
            file.validate_records(start_within_data=True)

    def test_validate_records_start_within_data(self):
        records = [
            SrecRecord.create_header(b'HDR\0'),
            SrecRecord.create_data(0x1234, b'abc'),
            SrecRecord.create_data(0x4321, b'xyz'),
            SrecRecord.create_count(2),
            SrecRecord.create_start(0x1234),
        ]
        file = SrecFile.from_records(records)
        file.validate_records(start_within_data=True)
        file.validate_records(start_within_data=False)
