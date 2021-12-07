# -*- coding: utf-8 -*-
import os
from pathlib import Path

import pytest

from hexrec.formats.motorola import Record
from hexrec.formats.motorola import Tag

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
        tags = {1, 2, 3}
        for tag in Tag:
            assert Tag.is_data(tag) == (tag in tags)
            assert Tag.is_data(int(tag)) == (tag in tags)


# ============================================================================

class TestRecord:

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
        record = Record.build_data(0, b'')
        for tag in range(len(Tag), 256):
            record.tag = tag
            record.update_checksum()
            with pytest.raises(ValueError):
                record.check()

        record = Record.build_data(0, b'Hello, World!')
        record.check()
        record.tag = len(Tag)
        with pytest.raises(ValueError):
            record.check()

        record = Record.build_header(b'')
        record.address = 1
        record.update_checksum()
        with pytest.raises(ValueError, match='address error'):
            record.check()

        record = Record.build_count(0x1234)
        record.address = 1
        record.update_checksum()
        with pytest.raises(ValueError, match='address error'):
            record.check()

        record = Record.build_count(0x123456)
        record.address = 1
        record.update_checksum()
        with pytest.raises(ValueError, match='address error'):
            record.check()

        record = Record.build_data(0, bytearray(252))
        record.data.append(1)
        record.update_count()
        record.update_checksum()
        with pytest.raises(ValueError, match='count overflow'):
            record.check()

        record = Record.build_data(0, b'Hello, World!')
        record.count += 1
        record.update_checksum()
        with pytest.raises(ValueError, match='count error'):
            record.check()

    def test_fit_data_tag_doctest(self):
        ans_out = repr(Record.fit_data_tag(0x00000000))
        ans_ref = '<Tag.DATA_16: 1>'
        assert ans_out == ans_ref

        ans_out = repr(Record.fit_data_tag(0x0000FFFF))
        ans_ref = '<Tag.DATA_16: 1>'
        assert ans_out == ans_ref

        ans_out = repr(Record.fit_data_tag(0x00010000))
        ans_ref = '<Tag.DATA_16: 1>'
        assert ans_out == ans_ref

        ans_out = repr(Record.fit_data_tag(0x00FFFFFF))
        ans_ref = '<Tag.DATA_24: 2>'
        assert ans_out == ans_ref

        ans_out = repr(Record.fit_data_tag(0x01000000))
        ans_ref = '<Tag.DATA_24: 2>'
        assert ans_out == ans_ref

        ans_out = repr(Record.fit_data_tag(0xFFFFFFFF))
        ans_ref = '<Tag.DATA_32: 3>'
        assert ans_out == ans_ref

        ans_out = repr(Record.fit_data_tag(0x100000000))
        ans_ref = '<Tag.DATA_32: 3>'
        assert ans_out == ans_ref

    def test_fit_data_tag(self):
        with pytest.raises(ValueError):
            Record.fit_data_tag(-1)

        with pytest.raises(ValueError):
            Record.fit_data_tag((1 << 32) + 1)

    def test_fit_count_tag_doctest(self):
        ans_out = repr(Record.fit_count_tag(0x0000000))
        ans_ref = '<Tag.COUNT_16: 5>'
        assert ans_out == ans_ref

        ans_out = repr(Record.fit_count_tag(0x00FFFF))
        ans_ref = '<Tag.COUNT_16: 5>'
        assert ans_out == ans_ref

        ans_out = repr(Record.fit_count_tag(0x010000))
        ans_ref = '<Tag.COUNT_24: 6>'
        assert ans_out == ans_ref

        ans_out = repr(Record.fit_count_tag(0xFFFFFF))
        ans_ref = '<Tag.COUNT_24: 6>'
        assert ans_out == ans_ref

    def test_fit_count_tag(self):
        with pytest.raises(ValueError):
            Record.fit_count_tag(-1)

        with pytest.raises(ValueError):
            Record.fit_count_tag(1 << 24)

    def test_build_header_doctest(self):
        ans_out = str(Record.build_header(b'Hello, World!'))
        ans_ref = 'S010000048656C6C6F2C20576F726C642186'
        assert ans_out == ans_ref

    def test_build_data_doctest(self):
        ans_out = str(Record.build_data(0x1234, b'Hello, World!'))
        ans_ref = 'S110123448656C6C6F2C20576F726C642140'
        assert ans_out == ans_ref

        ans_out = str(Record.build_data(0x1234, b'Hello, World!',
                                        tag=Tag.DATA_16))
        ans_ref = 'S110123448656C6C6F2C20576F726C642140'
        assert ans_out == ans_ref

        ans_out = str(Record.build_data(0x123456, b'Hello, World!',
                                        tag=Tag.DATA_24))
        ans_ref = 'S21112345648656C6C6F2C20576F726C6421E9'
        assert ans_out == ans_ref

        ans_out = str(Record.build_data(0x12345678, b'Hello, World!',
                                        tag=Tag.DATA_32))
        ans_ref = 'S3121234567848656C6C6F2C20576F726C642170'
        assert ans_out == ans_ref

    def test_build_data_tag(self):
        for tag in [0] + list(range(4, len(Tag))):
            tag = Tag(tag)
            with pytest.raises(ValueError):
                Record.build_data(0x1234, b'Hello, World!', tag=tag)

    def test_build_data_max_columns(self):
        for tag in (1, 2, 3):
            tag = Tag(tag)
            max_columns = Record.TAG_TO_COLUMN_SIZE[tag]
            record = Record.build_data(0x1234, bytes(max_columns), tag=tag)
            assert len(record.data) == max_columns
            assert record.count == 255

    def test_build_terminator_doctest(self):
        ans_out = str(Record.build_terminator(0x1234))
        ans_ref = 'S9031234B6'
        assert ans_out == ans_ref

        ans_out = str(Record.build_terminator(0x1234, Tag.DATA_16))
        ans_ref = 'S9031234B6'
        assert ans_out == ans_ref

        ans_out = str(Record.build_terminator(0x123456, Tag.DATA_24))
        ans_ref = 'S8041234565F'
        assert ans_out == ans_ref

        ans_out = str(Record.build_terminator(0x12345678, Tag.DATA_32))
        ans_ref = 'S70512345678E6'
        assert ans_out == ans_ref

    def test_build_count_doctest(self):
        ans_out = str(Record.build_count(0x1234))
        ans_ref = 'S5031234B6'
        assert ans_out == ans_ref

        ans_out = str(Record.build_count(0x123456))
        ans_ref = 'S6041234565F'
        assert ans_out == ans_ref

    def test_parse_doctest(self):
        pass  # TODO

    def test_parse_record(self):
        with pytest.raises(ValueError, match='regex error'):
            Record.parse_record('Hello, World!')

        with pytest.raises(ValueError, match='count error'):
            Record.parse_record('S1FF0000FF')

    def test_build_standalone(self):
        ans_out = list(Record.build_standalone(
            [],
            tag=Tag.DATA_32,
            header=b'Hello, World!',
            start=0,
        ))
        ans_ref = [
            Record(0, Tag.HEADER, b'Hello, World!'),
            Record(0, Tag.COUNT_16, b'\x00\x00'),
            Record(0, Tag.START_32, b''),
        ]
        assert ans_out == ans_ref

        ans_out = list(Record.build_standalone(
            [],
            tag=Tag.DATA_32,
            header=b'Hello, World!',
        ))
        ans_ref = [
            Record(0, Tag.HEADER, b'Hello, World!'),
            Record(0, Tag.COUNT_16, b'\x00\x00'),
            Record(0, Tag.START_32, b''),
        ]
        assert ans_out == ans_ref

    def test_check_sequence_doctest(self):
        pass  # TODO

    def test_check_sequence(self):
        records = list(Record.split(BYTES, header=b'Hello, World!'))
        Record.check_sequence(records)

        records = list(Record.split(BYTES, header=b'Hello, World!'))
        assert records[0].tag == Tag.HEADER
        del records[0]
        with pytest.raises(ValueError, match='missing header'):
            Record.check_sequence(records)

        records = list(Record.split(BYTES, header=b'Hello, World!'))
        assert records[0].tag == Tag.HEADER
        records.insert(1, records[0])
        with pytest.raises(ValueError, match='header error'):
            Record.check_sequence(records)

        records = list(Record.split(BYTES, header=b'Hello, World!'))
        assert records[0].tag == Tag.HEADER
        records.insert(1, Record(0, Tag._RESERVED, b''))
        with pytest.raises(ValueError, match='missing count'):
            Record.check_sequence(records)

        records = list(Record.split(BYTES, header=b'Hello, World!'))
        assert records[2].tag == Tag.DATA_16
        records[2].tag = Tag.DATA_24
        records[2].update_count()
        records[2].update_checksum()
        with pytest.raises(ValueError, match='tag error'):
            Record.check_sequence(records)

        records = list(Record.split(BYTES))
        assert records[2].tag == Tag.DATA_16
        records[2].address -= 1
        records[2].update_count()
        records[2].update_checksum()
        with pytest.raises(ValueError, match='overlapping records'):
            Record.check_sequence(records)

        records = list(Record.split(BYTES))
        assert records[2].tag == Tag.DATA_16
        assert records[-2].tag == Tag.COUNT_16
        del records[2]
        with pytest.raises(ValueError, match='record count error'):
            Record.check_sequence(records)

        records = list(Record.split(BYTES))
        assert records[-2].tag == Tag.COUNT_16
        del records[-2]
        with pytest.raises(ValueError, match='missing count'):
            Record.check_sequence(records)

        records = list(Record.split(BYTES))
        assert records[-2].tag == Tag.COUNT_16
        records.insert(-2, records[-2])
        with pytest.raises(ValueError, match='misplaced count'):
            Record.check_sequence(records)

        records = list(Record.split(BYTES))
        assert records[-2].tag == Tag.COUNT_16
        records[-2].tag = Tag.COUNT_24
        records[-2].data = b'\x00' + records[-2].data
        records[-2].update_count()
        records[-2].update_checksum()
        Record.check_sequence(records)

        records = list(Record.split(BYTES))
        assert records[-2].tag == Tag.COUNT_16
        records[-2].tag = Tag.COUNT_24
        records[-2].data = b'\x00' + records[-2].data
        records[-2].update_count()
        records[-2].update_checksum()
        records.insert(-2, records[-2])
        with pytest.raises(ValueError, match='misplaced count'):
            Record.check_sequence(records)

        records = list(Record.split(BYTES))
        assert records[-2].tag == Tag.COUNT_16
        records[-2].tag = Tag.COUNT_24
        records[-2].data = b'\x00' + records[-2].data
        records[-2].update_count()
        records[-2].update_checksum()
        assert records[2].tag == Tag.DATA_16
        del records[2]
        with pytest.raises(ValueError, match='record count error'):
            Record.check_sequence(records)

        records = list(Record.split(BYTES))
        assert records[1].tag == Tag.DATA_16
        assert records[-1].tag == Tag.START_16
        records[-1].tag = Tag.START_24
        records[-1].update_count()
        records[-1].update_checksum()
        with pytest.raises(ValueError):
            Record.check_sequence(records)

        records = list(Record.split(BYTES))
        assert records[-1].tag == Tag.START_16
        del records[-1]
        with pytest.raises(ValueError, match='missing start'):
            Record.check_sequence(records)

        records = list(Record.split(BYTES))
        assert records[-1].tag == Tag.START_16
        records.insert(-1, Record(0, Tag._RESERVED, b''))
        with pytest.raises(ValueError, match='tag error'):
            Record.check_sequence(records)

        records = list(Record.split(BYTES))
        assert records[-1].tag == Tag.START_16
        records.append(Record(0, Tag._RESERVED, b''))
        with pytest.raises(ValueError, match='sequence length error'):
            Record.check_sequence(records)

    def test_get_metadata_doctest(self):
        pass  # TODO

    def test_get_metadata(self):
        records = list(Record.split(BYTES, header=b'header', start=0x1234))
        ans_out = Record.get_metadata(records)
        ans_ref = {
            'header': b'header',
            'columns': 16,
            'count': 16,
            'start': 0x1234,
        }
        assert ans_out == ans_ref

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
            list(Record.split(BYTES, columns=257))

        with pytest.raises(ValueError):
            list(Record.split(BYTES, columns=253, tag=Record.TAG_TYPE.DATA_16))

        with pytest.raises(ValueError):
            list(Record.split(BYTES, columns=252, tag=Record.TAG_TYPE.DATA_24))

        with pytest.raises(ValueError):
            list(Record.split(BYTES, columns=251, tag=Record.TAG_TYPE.DATA_32))

        ans_out = list(Record.split(HEXBYTES, header=b'Hello, World!',
                                    start=0, tag=Tag.DATA_16))
        ans_ref = [
            Record(0, Tag.HEADER, b'Hello, World!'),
            Record(0, Tag.DATA_16, HEXBYTES),
            Record(0, Tag.COUNT_16, b'\x00\x01'),
            Record(0, Tag.START_16, b''),
        ]
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

    def test_fix_tags_doctest(self):
        pass  # TODO

    def test_fix_tags(self):
        ans_out = []
        Record.fix_tags(ans_out)
        assert ans_out == []

        ans_out = [
            Record(0, Tag.HEADER, b'Hello, World!'),
            Record(0x12345678, Tag.DATA_16, HEXBYTES),
            Record(0, Tag.COUNT_16, b'\x12\x34'),
            Record(0, Tag.COUNT_16, b'\x12\x34\x56'),
            Record(0x1234, Tag.START_16, b''),
        ]
        Record.fix_tags(ans_out)
        ans_ref = [
            Record(0, Tag.HEADER, b'Hello, World!'),
            Record(0x12345678, Tag.DATA_32, HEXBYTES),
            Record(0, Tag.COUNT_16, b'\x12\x34'),
            Record(0, Tag.COUNT_24, b'\x12\x34\x56'),
            Record(0x1234, Tag.START_32, b''),
        ]
        assert ans_out == ans_ref

    def test_load_records(self, datapath):
        path_ref = datapath / 'bytes.mot'
        ans_out = list(Record.load_records(str(path_ref)))
        ans_ref = list(Record.split(BYTES))
        assert ans_out == ans_ref

    def test_save_records(self, tmppath, datapath):
        path_out = tmppath / 'bytes.mot'
        path_ref = datapath / 'bytes.mot'
        records = list(Record.split(BYTES))
        Record.save_records(str(path_out), records)
        ans_out = read_text(path_out)
        ans_ref = read_text(path_ref)
        assert ans_out == ans_ref
