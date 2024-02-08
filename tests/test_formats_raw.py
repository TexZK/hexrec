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

from hexrec.formats.raw import RawFile
from hexrec.formats.raw import RawRecord
from hexrec.formats.raw import RawTag

BYTES = bytes(range(256))
HEXBYTES = bytes(range(16))


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


class TestRawTag(BaseTestTag):

    Tag = RawTag

    def test_is_data(self):
        assert RawTag.DATA.is_data() is True

    def test_is_file_termination(self):
        assert RawTag.DATA.is_file_termination() is False


class TestRawRecord(BaseTestRecord):

    Record = RawRecord

    def test_compute_checksum(self):
        record = RawRecord.create_data(123, b'abc')
        assert record.compute_checksum() is None

    def test_compute_count(self):
        record = RawRecord.create_data(123, b'abc')
        assert record.compute_count() is None

    def test_create_data(self):
        record = RawRecord.create_data(123, b'abc')
        record.validate()
        assert record.tag == RawTag.DATA
        assert record.address == 123
        assert record.data == b'abc'

        record = RawRecord.create_data(0, b'abc')
        record.validate()
        assert record.tag == RawTag.DATA
        assert record.address == 0
        assert record.data == b'abc'

        record = RawRecord.create_data(123, b'')
        record.validate()
        assert record.tag == RawTag.DATA
        assert record.address == 123
        assert record.data == b''

        with pytest.raises(ValueError, match='address overflow'):
            RawRecord.create_data(-1, b'abc')

    def test_parse(self):
        record = RawRecord.parse(b'abc')
        assert record.tag == RawTag.DATA
        assert record.address == 0
        assert record.data == b'abc'

        record = RawRecord.parse(b'abc', address=123)
        assert record.tag == RawTag.DATA
        assert record.address == 123
        assert record.data == b'abc'

    def test_to_bytestr(self):
        record = RawRecord.create_data(123, b'abc')
        assert record.to_bytestr() == b'abc'

        record.count = -1
        with pytest.raises(ValueError, match='count overflow'):
            record.to_bytestr()

    def test_to_tokens(self):
        record = RawRecord.create_data(123, b'abc')
        tokens = record.to_tokens()
        assert tokens == {'data': b'abc'}

        record.count = -1
        with pytest.raises(ValueError, match='count overflow'):
            record.to_bytestr()


class TestRawFile(BaseTestFile):

    File = RawFile

    def test__is_line_empty(self):
        assert RawFile._is_line_empty(b'')

        assert not RawFile._is_line_empty(b' ')
        assert not RawFile._is_line_empty(b'\r\n')
        assert not RawFile._is_line_empty(b'0')

    def test_load_file(self, datapath):
        path = str(datapath / 'hexbytes.bin')
        records = [
            RawRecord.create_data(0, HEXBYTES),
        ]
        file = RawFile.load(path)
        assert file.records == records

    def test_load_stdin(self):
        buffer = HEXBYTES
        records = [
            RawRecord.create_data(0, HEXBYTES),
        ]
        stream = io.BytesIO(buffer)
        with replace_stdin(stream):
            file = RawFile.load(None)
        assert file._records == records

    def test_parse(self):
        with io.BytesIO(BYTES) as stream:
            file = RawFile.parse(stream)
        assert len(file.records) == 1
        assert file.memory == BYTES

    def test_parse_chunks(self):
        with io.BytesIO(BYTES) as stream:
            file = RawFile.parse(stream, maxdatalen=16, address=0x1000)
        assert len(file.records) == 16
        assert file.memory == BYTES

        for index, record in enumerate(file.records):
            assert record.tag == RawTag.DATA
            offset = index * 16
            assert record.address == 0x1000 + offset
            assert len(record.data) == 16
            assert record.data == BYTES[offset:(offset + 16)]

    def test_parse_empty(self):
        with io.BytesIO(b'') as stream:
            file = RawFile.parse(stream)
        assert len(file.records) == 0
        assert file.memory == b''

    def test_parse_file_hexbytes(self, datapath):
        path = str(datapath / 'hexbytes.bin')
        with open(path, 'rb') as stream:
            file = RawFile.parse(stream)
        assert len(file.records) == 1
        assert file.memory == HEXBYTES

    def test_parse_raises(self):
        with pytest.raises(ValueError, match='invalid maximum data length'):
            with io.BytesIO(BYTES) as stream:
                RawFile.parse(stream, maxdatalen=0)

        with pytest.raises(ValueError, match='invalid maximum data length'):
            with io.BytesIO(BYTES) as stream:
                RawFile.parse(stream, maxdatalen=-1)

    def test_records_getter(self):
        File = self.File
        Record = File.Record
        Tag = Record.Tag
        records = [
            Record(Tag.DATA, address=0, data=b'abc'),
            Record(Tag.DATA, address=3, data=b'xyz'),
        ]
        memory = Memory.from_bytes(b'abcxyz')
        file = File.from_memory(memory, maxdatalen=3)
        file._records = None
        assert file._memory == b'abcxyz'
        actual = file.records
        assert actual is file._records
        assert actual == records
        assert file._memory is memory
        file._memory = None
        actual = file.records
        assert actual is file._records
        assert actual == records
        assert file._memory is None

    def test_save_file(self, tmppath):
        path = str(tmppath / 'test_save_file.bin')
        file = RawFile.from_bytes(HEXBYTES)
        returned = file.save(path)
        assert returned is file
        with open(path, 'rb') as stream:
            actual = stream.read()
        assert actual == HEXBYTES

    def test_save_stdout(self):
        stream = io.BytesIO()
        file = RawFile.from_bytes(HEXBYTES)
        with replace_stdout(stream):
            returned = file.save(None)
        assert returned is file
        actual = stream.getvalue()
        assert actual == HEXBYTES

    def test_update_records(self):
        memory = Memory.from_bytes(BYTES, offset=0x1000)
        file = RawFile.from_memory(memory, maxdatalen=16)
        file.update_records()
        assert len(file.records) == 16
        assert all(r.tag == RawTag.DATA for r in file.records)

    def test_update_records_empty(self):
        file = RawFile.from_memory(maxdatalen=16)
        file.update_records()
        assert len(file.records) == 0

    def test_update_records_raises_hole(self):
        memory = Memory.from_bytes(BYTES)
        memory.clear(start=16, endex=32)
        file = RawFile.from_memory(memory, maxdatalen=16)
        with pytest.raises(ValueError, match='contiguous'):
            file.update_records()

    def test_update_records_raises_memory(self):
        records = [RawRecord.create_data(123, b'abc')]
        file = RawFile.from_records(records)
        with pytest.raises(ValueError, match='memory instance required'):
            file.update_records()

    def test_validate_records(self):
        records = [RawRecord.create_data(0, b'abc'),
                   RawRecord.create_data(3, b'xyz')]
        file = RawFile.from_records(records)
        file.validate_records()

        file.validate_records(data_start=True,
                              data_contiguity=True,
                              data_ordering=True)

        file.validate_records(data_start=False,
                              data_contiguity=False,
                              data_ordering=False)

    def test_validate_records_contiguity(self):
        records = [RawRecord.create_data(10, b'abc'),
                   RawRecord.create_data(13, b'xyz')]
        file = RawFile.from_records(records)
        file.validate_records(data_start=False,
                              data_contiguity=True,
                              data_ordering=False)

        records = [RawRecord.create_data(10, b'abc'),
                   RawRecord.create_data(13, b'xyz')]
        file = RawFile.from_records(records)
        file.validate_records(data_start=False,
                              data_contiguity=True,
                              data_ordering=False)

    def test_validate_records_ordering(self):
        records = [RawRecord.create_data(10, b'abc'),
                   RawRecord.create_data(13, b'xyz')]
        file = RawFile.from_records(records)
        file.validate_records(data_start=False,
                              data_contiguity=False,
                              data_ordering=True)

        records = [RawRecord.create_data(10, b'abc'),
                   RawRecord.create_data(14, b'xyz')]
        file = RawFile.from_records(records)
        file.validate_records(data_start=False,
                              data_contiguity=False,
                              data_ordering=True)

    def test_validate_records_start(self):
        records = [RawRecord.create_data(0, b'abc'),
                   RawRecord.create_data(3, b'xyz')]
        file = RawFile.from_records(records)
        file.validate_records(data_start=True,
                              data_contiguity=False,
                              data_ordering=False)

    def test_validate_records_raises_contiguity(self):
        records = [RawRecord.create_data(0, b'abc'),
                   RawRecord.create_data(4, b'xyz')]
        file = RawFile.from_records(records)
        with pytest.raises(ValueError, match='contiguous'):
            file.validate_records(data_start=False,
                                  data_contiguity=True,
                                  data_ordering=False)

    def test_validate_records_raises_ordering(self):
        records = [RawRecord.create_data(3, b'xyz'),
                   RawRecord.create_data(0, b'abc')]
        file = RawFile.from_records(records)
        with pytest.raises(ValueError, match='unordered data record'):
            file.validate_records(data_start=False,
                                  data_contiguity=False,
                                  data_ordering=True)

        records = [RawRecord.create_data(0, b'abc'),
                   RawRecord.create_data(0, b'xyz')]
        file = RawFile.from_records(records)
        with pytest.raises(ValueError, match='unordered data record'):
            file.validate_records(data_start=False,
                                  data_contiguity=False,
                                  data_ordering=True)

        records = [RawRecord.create_data(0, b'abc'),
                   RawRecord.create_data(2, b'xyz')]
        file = RawFile.from_records(records)
        with pytest.raises(ValueError, match='unordered data record'):
            file.validate_records(data_start=False,
                                  data_contiguity=False,
                                  data_ordering=True)

    def test_validate_records_raises_records(self):
        file = RawFile.from_memory(maxdatalen=16)
        with pytest.raises(ValueError, match='records required'):
            file.validate_records(data_start=False,
                                  data_contiguity=False,
                                  data_ordering=False)

    def test_validate_records_raises_start(self):
        records = [RawRecord.create_data(10, b'abc'),
                   RawRecord.create_data(13, b'xyz')]
        file = RawFile.from_records(records)
        with pytest.raises(ValueError, match='first record address not zero'):
            file.validate_records(data_start=True,
                                  data_contiguity=False,
                                  data_ordering=False)
