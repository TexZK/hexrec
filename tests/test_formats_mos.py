import io
import os
from pathlib import Path

import pytest
from test_base import BaseTestFile
from test_base import BaseTestRecord
from test_base import BaseTestTag
from test_base import replace_stdin
from test_base import replace_stdout

from hexrec.formats.mos import MosFile
from hexrec.formats.mos import MosRecord
from hexrec.formats.mos import MosTag


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


class TestMosTag(BaseTestTag):

    Tag = MosTag

    def test_enum(self):
        assert MosTag.DATA == 0
        assert MosTag.EOF == 1

    def test_is_data(self):
        assert MosTag.DATA.is_data() is True
        assert MosTag.EOF.is_data() is False

    def test_is_eof(self):
        assert MosTag.DATA.is_eof() is False
        assert MosTag.EOF.is_eof() is True

    def test_is_file_termination(self):
        assert MosTag.DATA.is_file_termination() is False
        assert MosTag.EOF.is_file_termination() is True


class TestMosRecord(BaseTestRecord):

    Record = MosRecord

    def test_compute_checksum(self):
        record = MosRecord.create_data(0, b'')
        assert record.compute_checksum() == 0

        record = MosRecord.create_data(0x1234, b'')
        assert record.compute_checksum() == (0x12 + 0x34)

        record = MosRecord.create_data(0, b'\x56\x78')
        assert record.compute_checksum() == (2 + 0x56 + 0x78)

        record = MosRecord.create_data(0x1234, b'\x56\x78')
        assert record.compute_checksum() == (0x12 + 0x34 + 2 + 0x56 + 0x78)

        record = MosRecord.create_data(0, b'\0\0\0')
        assert record.compute_checksum() == 3

        record = MosRecord.create_data(0xFFFF, b'\xFF' * 0xFF)
        max_sum = (2 + 1 + 0xFF) * 0xFF  # address + count + data
        assert max_sum > 0xFFFF
        assert record.compute_checksum() == max_sum & 0xFFFF

    def test_compute_checksum_raises(self):
        record = MosRecord(MosTag.DATA, checksum=None, count=None)
        with pytest.raises(ValueError, match='missing count'):
            record.compute_checksum()

    def test_compute_count(self):
        record = MosRecord.create_data(0, b'')
        assert record.compute_count() == 0

        record = MosRecord.create_data(0x1234, b'')
        assert record.compute_count() == 0

        record = MosRecord.create_data(0, b'\x56\x78')
        assert record.compute_count() == 2

        record = MosRecord.create_data(0x1234, b'\x56\x78')
        assert record.compute_count() == 2

    def test_create_data(self):
        record = MosRecord.create_data(123, b'abc')
        record.validate()
        assert record.tag == MosTag.DATA
        assert record.address == 123
        assert record.data == b'abc'

        record = MosRecord.create_data(0, b'abc')
        record.validate()
        assert record.tag == MosTag.DATA
        assert record.address == 0
        assert record.data == b'abc'

        record = MosRecord.create_data(123, b'')
        record.validate()
        assert record.tag == MosTag.DATA
        assert record.address == 123
        assert record.data == b''

    def test_create_data_raises_address(self):
        MosRecord.create_data(0, b'abc')
        MosRecord.create_data(0xFFFF, b'abc')

        with pytest.raises(ValueError, match='address overflow'):
            MosRecord.create_data(-1, b'abc')

        with pytest.raises(ValueError, match='address overflow'):
            MosRecord.create_data(0x10000, b'abc')

    def test_create_data_raises_data(self):
        MosRecord.create_data(123, b'.' * 0xFF)

        with pytest.raises(ValueError, match='size overflow'):
            MosRecord.create_data(123, b'.' * 0x100)

    def test_create_eof(self):
        record = MosRecord.create_eof(123)
        record.validate()
        assert record.tag == MosTag.EOF
        assert record.address == 123
        assert record.data == b''

    def test_create_eof_raises_count(self):
        MosRecord.create_eof(0)
        MosRecord.create_eof(0xFFFF)

        with pytest.raises(ValueError, match='count overflow'):
            MosRecord.create_eof(-1)

        with pytest.raises(ValueError, match='count overflow'):
            MosRecord.create_eof(0x10000)

    def test_parse(self):
        lines = [
            b';180000FFEEDDCCBBAA0099887766554433221122334455667788990AFC\r\n\0\0\0\0\0\0',
            b';180000FFEEDDCCBBAA0099887766554433221122334455667788990AFC\r\n',
            b';0000010001\r\n\0\0\0\0\0\0',
            b';0000010001\r\n',
        ]
        data = (b'\xFF\xEE\xDD\xCC\xBB\xAA\x00\x99'
                b'\x88\x77\x66\x55\x44\x33\x22\x11'
                b'\x22\x33\x44\x55\x66\x77\x88\x99')
        records = [
            MosRecord.create_data(0x0000, data),
            MosRecord.create_data(0x0000, data),
            MosRecord.create_eof(1),
            MosRecord.create_eof(1),
        ]
        for index, (line, expected) in enumerate(zip(lines, records)):
            actual = MosRecord.parse(line, eof=(index >= 2))
            actual.validate()
            assert actual == expected
            assert actual.after == b''
            assert actual.before == b''

    def test_parse_syntax(self):
        lines = [
            b'(;0000000000\r\n',
            b';0000000000)\r\n',
            b';0000000000\n',
            b';0000000000\r\n\0',
            b';0000000000\r\n\0\0\0\0\0\0\0',
            b';0000000000\r',
            b';0000000000',
        ]
        expected = MosRecord.create_data(0x0000, b'')
        for line in lines:
            actual = MosRecord.parse(line, validate=False)
            assert actual == expected

    def test_parse_syntax_raises(self):
        lines = [
            b'.0000000000\r\n',
            b';..00000000\r\n',
            b';00....0000\r\n',
            b';000000....\r\n',
        ]
        for line in lines:
            with pytest.raises(ValueError, match='syntax error'):
                MosRecord.parse(line)

    def test_to_bytestr(self):
        self.test_to_bytestr_data_nul()

    def test_to_bytestr_data_nul(self):
        data = (b'\xFF\xEE\xDD\xCC\xBB\xAA\x00\x99'
                b'\x88\x77\x66\x55\x44\x33\x22\x11'
                b'\x22\x33\x44\x55\x66\x77\x88\x99')
        record = MosRecord.create_data(0x0000, data)
        line = record.to_bytestr(nuls=True)
        ref = b';180000FFEEDDCCBBAA0099887766554433221122334455667788990AFC\r\n\0\0\0\0\0\0'
        assert line == ref

    def test_to_bytestr_data_wonul(self):
        data = (b'\xFF\xEE\xDD\xCC\xBB\xAA\x00\x99'
                b'\x88\x77\x66\x55\x44\x33\x22\x11'
                b'\x22\x33\x44\x55\x66\x77\x88\x99')
        record = MosRecord.create_data(0x0000, data)
        line = record.to_bytestr(nuls=False)
        ref = b';180000FFEEDDCCBBAA0099887766554433221122334455667788990AFC\r\n'
        assert line == ref

    def test_to_bytestr_eof_checksum(self):
        record = MosRecord.create_eof(0x1234)
        line = record.to_bytestr(nuls=True)
        ref = b';0012340046\r\n\0\0\0\0\0\0'
        assert line == ref

    def test_to_bytestr_eof_nul(self):
        record = MosRecord.create_eof(0x0001)
        line = record.to_bytestr(nuls=True)
        ref = b';0000010001\r\n\0\0\0\0\0\0'
        assert line == ref

    def test_to_bytestr_eof_wonul(self):
        record = MosRecord.create_eof(0x0001)
        line = record.to_bytestr(nuls=False)
        ref = b';0000010001\r\n'
        assert line == ref

    def test_to_bytestr_eof_wonul_end(self):
        record = MosRecord.create_eof(0x0001)
        line = record.to_bytestr(end=b'\n', nuls=False)
        ref = b';0000010001\n'
        assert line == ref

    def test_to_tokens(self):
        self.test_to_tokens_data_nul()

    def test_to_tokens_data_nul(self):
        data = (b'\xFF\xEE\xDD\xCC\xBB\xAA\x00\x99'
                b'\x88\x77\x66\x55\x44\x33\x22\x11'
                b'\x22\x33\x44\x55\x66\x77\x88\x99')
        record = MosRecord.create_data(0x0000, data)
        tokens = record.to_tokens(nuls=True)
        ref = {
            'before': b'',
            'begin': b';',
            'count': b'18',
            'address': b'0000',
            'data': b'FFEEDDCCBBAA009988776655443322112233445566778899',
            'checksum': b'0AFC',
            'after': b'',
            'end': b'\r\n',
            'nuls': b'\0\0\0\0\0\0',
        }
        assert tokens == ref

    def test_to_tokens_data_wonul(self):
        data = (b'\xFF\xEE\xDD\xCC\xBB\xAA\x00\x99'
                b'\x88\x77\x66\x55\x44\x33\x22\x11'
                b'\x22\x33\x44\x55\x66\x77\x88\x99')
        record = MosRecord.create_data(0x0000, data)
        tokens = record.to_tokens(nuls=False)
        ref = {
            'before': b'',
            'begin': b';',
            'count': b'18',
            'address': b'0000',
            'data': b'FFEEDDCCBBAA009988776655443322112233445566778899',
            'checksum': b'0AFC',
            'after': b'',
            'end': b'\r\n',
            'nuls': b'',
        }
        assert tokens == ref

    def test_to_tokens_eof_checksum(self):
        record = MosRecord.create_eof(0x1234)
        tokens = record.to_tokens(end=b'\n', nuls=True)
        ref = {
            'before': b'',
            'begin': b';',
            'count': b'00',
            'address': b'1234',
            'data': b'',
            'checksum': b'0046',
            'after': b'',
            'end': b'\n',
            'nuls': b'\0\0\0\0\0\0',
        }
        assert tokens == ref

    def test_validate_after(self):
        record = MosRecord(MosTag.DATA, after=b' ')
        record.validate()

        record = MosRecord(MosTag.DATA, after=b'?', validate=False)
        with pytest.raises(ValueError, match='junk after is not whitespace'):
            record.validate()

    def test_validate_before(self):
        record = MosRecord(MosTag.DATA, before=b'?', validate=False)
        record.validate()

        record = MosRecord(MosTag.DATA, before=b';', validate=False)
        with pytest.raises(ValueError, match='junk before contains ";"'):
            record.validate()

    def test_validate_checksum(self):
        record = MosRecord(MosTag.DATA, checksum=-1, validate=False)
        # record.compute_checksum = lambda: record.checksum  # fake
        with pytest.raises(ValueError, match='checksum'):
            record.validate()

        record = MosRecord(MosTag.DATA, checksum=0, address=0, data=b'')
        record.validate()

        record = MosRecord(MosTag.DATA, checksum=0xFFFF, address=0x00FF, data=(b'\xFF' * 0xFF))
        record.validate()

        record = MosRecord(MosTag.DATA, checksum=0x10000, validate=False)
        record.compute_checksum = lambda: record.checksum  # fake
        with pytest.raises(ValueError, match='checksum'):
            record.validate()

    def test_validate_count(self):

        record = MosRecord(MosTag.DATA, count=-1, validate=False)
        with pytest.raises(ValueError, match='count'):
            record.validate()

        record = MosRecord(MosTag.DATA, count=0, data=b'')
        record.validate()

        record = MosRecord(MosTag.DATA, count=0xFF, data=(b'\0' * 0xFF))
        record.validate()

        record = MosRecord(MosTag.DATA, count=0x100, validate=False)
        record.compute_count = lambda: record.count  # fake
        with pytest.raises(ValueError, match='count'):
            record.validate()

    def test_validate_data(self):
        record = MosRecord(MosTag.DATA, data=b'')
        record.validate()

        record = MosRecord(MosTag.DATA, data=(b'\0' * 0xFF))
        record.validate()

        record = MosRecord(MosTag.DATA, data=(b'\0' * 0xFF))
        record.compute_count = lambda: record.count  # fake
        record.data += b'\0'
        with pytest.raises(ValueError, match='data size'):
            record.validate()

    def test_validate_address(self):
        record = MosRecord(MosTag.DATA, address=-1, validate=False)
        with pytest.raises(ValueError, match='address'):
            record.validate()

        record = MosRecord(MosTag.DATA, address=0)
        record.validate()

        record = MosRecord(MosTag.DATA, address=0xFFFF)
        record.validate()

        record = MosRecord(MosTag.DATA, address=0x10000, validate=False)
        with pytest.raises(ValueError, match='address'):
            record.validate()


class TestMosFile(BaseTestFile):

    File = MosFile

    def test__is_line_empty(self):
        assert MosFile._is_line_empty(b'')
        assert MosFile._is_line_empty(b' \t\v\r\n')
        assert MosFile._is_line_empty(b'\0')
        assert MosFile._is_line_empty(b'\0 \t\v\r\n')
        assert MosFile._is_line_empty(b' \t\v\r\n\0')
        assert MosFile._is_line_empty(b' \t\v\0\r\n')

        assert not MosFile._is_line_empty(b';')
        assert not MosFile._is_line_empty(b'; \t\v\r\n')
        assert not MosFile._is_line_empty(b' \t\v\r\n;')
        assert not MosFile._is_line_empty(b' \t\v;\r\n')
        assert not MosFile._is_line_empty(b';\0 \t\v\r\n')
        assert not MosFile._is_line_empty(b' \t\v\r\n\0;')
        assert not MosFile._is_line_empty(b' \t\v\0;\r\n')

    def test_apply_records_tags(self):
        data = (b'\xFF\xEE\xDD\xCC\xBB\xAA\x00\x99'
                b'\x88\x77\x66\x55\x44\x33\x22\x11'
                b'\x22\x33\x44\x55\x66\x77\x88\x99')
        records = [
            MosRecord.create_data(0x0000, data),
            MosRecord.create_eof(1),
        ]
        file = MosFile.from_records(records)
        assert file._records is records
        returned = file.apply_records()
        assert returned is file
        assert file._memory.to_blocks() == [[0, data]]
        assert file._records is records

    def test_load_file(self, datapath):
        path = str(datapath / 'basic_nul_xoff.mos')
        data = (b'\xFF\xEE\xDD\xCC\xBB\xAA\x00\x99'
                b'\x88\x77\x66\x55\x44\x33\x22\x11'
                b'\x22\x33\x44\x55\x66\x77\x88\x99')
        records = [
            MosRecord.create_data(0x0000, data),
            MosRecord.create_eof(1),
        ]
        file = MosFile.load(path)
        assert file.records == records

    def test_load_stdin(self):
        buffer = (
            b';180000FFEEDDCCBBAA0099887766554433221122334455667788990AFC\r\n\0\0\0\0\0\0'
            b';0000010001\r\n\0\0\0\0\0\0'
            b'\x13'
        )
        data = (b'\xFF\xEE\xDD\xCC\xBB\xAA\x00\x99'
                b'\x88\x77\x66\x55\x44\x33\x22\x11'
                b'\x22\x33\x44\x55\x66\x77\x88\x99')
        records = [
            MosRecord.create_data(0x0000, data),
            MosRecord.create_eof(1),
        ]
        stream = io.BytesIO(buffer)
        with replace_stdin(stream):
            file = MosFile.load(None)
        assert file._records == records

    def test_parse(self):
        buffer = (
            b';031234616263016F\r\n\x00\x00\x00\x00\x00\x00'
            b';0000010001\r\n\x00\x00\x00\x00\x00\x00'
            b'\x13'
        )
        records = [
            MosRecord.create_data(0x1234, b'abc'),
            MosRecord.create_eof(1),
        ]
        with io.BytesIO(buffer) as stream:
            file = MosFile.parse(stream)
        assert file._records == records

    def test_parse_empty(self):
        line = b';0000000000\r\n'
        records = [
            MosRecord.create_eof(0),
        ]
        with io.BytesIO(line) as stream:
            file = MosFile.parse(stream)
        assert file._records == records

    def test_parse_file_basic(self, datapath):
        path = str(datapath / 'basic.mos')
        data = (b'\xFF\xEE\xDD\xCC\xBB\xAA\x00\x99'
                b'\x88\x77\x66\x55\x44\x33\x22\x11'
                b'\x22\x33\x44\x55\x66\x77\x88\x99')
        records = [
            MosRecord.create_data(0x0000, data),
            MosRecord.create_eof(1),
        ]
        with open(path, 'rb') as stream:
            file = MosFile.parse(stream)
        assert file._records == records

    def test_parse_file_junk(self, datapath):
        path = str(datapath / 'basic_nul_xoff_junk.mos')
        data = (b'\xFF\xEE\xDD\xCC\xBB\xAA\x00\x99'
                b'\x88\x77\x66\x55\x44\x33\x22\x11'
                b'\x22\x33\x44\x55\x66\x77\x88\x99')
        records = [
            MosRecord.create_data(0x0000, data),
            MosRecord.create_eof(1),
        ]
        with open(path, 'rb') as stream:
            file = MosFile.parse(stream, ignore_after_termination=True)
        assert file._records == records

    def test_parse_ignore_eof(self):
        with io.BytesIO(b'') as stream:
            file = MosFile.parse(stream, ignore_errors=True)
        assert len(file.records) == 0

        with io.BytesIO(b'') as stream:
            file = MosFile.parse(stream, eof_record=False)
        assert len(file.records) == 0

        with io.BytesIO(b'\x13;') as stream:
            file = MosFile.parse(stream, ignore_errors=True)
        assert len(file.records) == 0

    def test_parse_raises_eof(self):
        with pytest.raises(ValueError, match='missing end of file record'):
            with io.BytesIO(b'') as stream:
                MosFile.parse(stream)

    def test_parse_raises_file_junk(self, datapath):
        path = str(datapath / 'basic_junk.mos')
        with pytest.raises(ValueError, match='syntax error'):
            with open(path, 'rb') as stream:
                MosFile.parse(stream, ignore_after_termination=False)

    def test_save_file(self, tmppath):
        path = str(tmppath / 'test_save_file.mos')
        records = [
            MosRecord.create_data(0x1234, b'abc'),
            MosRecord.create_eof(1),
        ]
        expected = (
            b';031234616263016F\r\n\x00\x00\x00\x00\x00\x00'
            b';0000010001\r\n\x00\x00\x00\x00\x00\x00'
            b'\x13'
        )
        file = MosFile.from_records(records)
        returned = file.save(path)
        assert returned is file
        with open(path, 'rb') as stream:
            actual = stream.read()
        assert actual == expected

    def test_save_stdout(self):
        records = [
            MosRecord.create_data(0x1234, b'abc'),
            MosRecord.create_eof(1),
        ]
        expected = (
            b';031234616263016F\r\n\x00\x00\x00\x00\x00\x00'
            b';0000010001\r\n\x00\x00\x00\x00\x00\x00'
            b'\x13'
        )
        stream = io.BytesIO()
        file = MosFile.from_records(records)
        with replace_stdout(stream):
            returned = file.save(None)
        assert returned is file
        actual = stream.getvalue()
        assert actual == expected

    def test_serialize(self):
        File = self.File
        file = File.from_bytes(b'abc')
        file.update_records()
        stream = io.BytesIO()
        returned = file.serialize(stream)
        assert returned is file
        actual = stream.getvalue()
        expected = b''.join(r.to_bytestr() for r in file._records)
        expected += b'\x13'
        assert actual == expected

    def test_serialize_nul_xoff(self, datapath):
        data = (b'\xFF\xEE\xDD\xCC\xBB\xAA\x00\x99'
                b'\x88\x77\x66\x55\x44\x33\x22\x11'
                b'\x22\x33\x44\x55\x66\x77\x88\x99')
        records = [
            MosRecord.create_data(0x0000, data),
            MosRecord.create_eof(1),
        ]
        file = MosFile.from_records(records)

        outstream = io.BytesIO()
        file.serialize(outstream, nuls=True, xoff=True)
        outdata = outstream.getvalue()

        refpath = str(datapath / 'basic_nul_xoff.mos')
        with open(refpath, 'rb') as stream:
            refdata = stream.read()
        assert outdata == refdata

    def test_serialize_plain(self, datapath):
        data = (b'\xFF\xEE\xDD\xCC\xBB\xAA\x00\x99'
                b'\x88\x77\x66\x55\x44\x33\x22\x11'
                b'\x22\x33\x44\x55\x66\x77\x88\x99')
        records = [
            MosRecord.create_data(0x0000, data),
            MosRecord.create_eof(1),
        ]
        file = MosFile.from_records(records)

        outstream = io.BytesIO()
        file.serialize(outstream, nuls=False, xoff=False)
        outdata = outstream.getvalue()

        refpath = str(datapath / 'basic.mos')
        with open(refpath, 'rb') as stream:
            refdata = stream.read()
        assert outdata == refdata

    def test_serialize_xoff(self, datapath):
        data = (b'\xFF\xEE\xDD\xCC\xBB\xAA\x00\x99'
                b'\x88\x77\x66\x55\x44\x33\x22\x11'
                b'\x22\x33\x44\x55\x66\x77\x88\x99')
        records = [
            MosRecord.create_data(0x0000, data),
            MosRecord.create_eof(1),
        ]
        file = MosFile.from_records(records)

        outstream = io.BytesIO()
        file.serialize(outstream, nuls=False, xoff=True)
        outdata = outstream.getvalue()

        refpath = str(datapath / 'basic_xoff.mos')
        with open(refpath, 'rb') as stream:
            refdata = stream.read()
        assert outdata == refdata

    def test_update_records(self):
        file = MosFile().write(0x1234, b'abc')
        file.update_records()
        records = file._records
        assert len(records) == 2

        record0 = records[0]
        assert record0.tag == MosTag.DATA
        assert record0.count == 3
        assert record0.address == 0x1234
        assert record0.data == b'abc'
        assert record0.checksum == (3 + 0x12 + 0x34 + sum(b'abc'))

        record1 = records[1]
        assert record1.tag == MosTag.EOF
        assert record1.count == 0
        assert record1.address == 1
        assert record1.data == b''
        assert record1.checksum == (0 + 0x00 + 0x01 + 0)

    def test_update_records_empty(self):
        file = MosFile()
        file.update_records()
        records = file._records
        assert len(records) == 1

        record = records[0]
        assert record.tag == MosTag.EOF
        assert record.count == 0
        assert record.address == 0
        assert record.data == b''
        assert record.checksum == 0

    def test_update_records_raises_memory(self):
        data = (b'\xFF\xEE\xDD\xCC\xBB\xAA\x00\x99'
                b'\x88\x77\x66\x55\x44\x33\x22\x11'
                b'\x22\x33\x44\x55\x66\x77\x88\x99')
        records = [
            MosRecord.create_data(0x0000, data),
            MosRecord.create_eof(1),
        ]
        file = MosFile.from_records(records)
        with pytest.raises(ValueError, match='memory instance required'):
            file.update_records()

    def test_validate_records(self):
        data = (b'\xFF\xEE\xDD\xCC\xBB\xAA\x00\x99'
                b'\x88\x77\x66\x55\x44\x33\x22\x11'
                b'\x22\x33\x44\x55\x66\x77\x88\x99')
        records = [
            MosRecord.create_data(0x0000, data),
            MosRecord.create_eof(1),
        ]
        file = MosFile.from_records(records)
        file.validate_records(data_ordering=True, eof_record_required=True)

    def test_validate_records_data_order(self):
        records = [MosRecord.create_data(10, b'xyz'),
                   MosRecord.create_data(13, b'abc'),
                   MosRecord.create_eof(2)]
        file = MosFile.from_records(records)
        file.validate_records(data_ordering=True)
        file.validate_records(data_ordering=False)

        records = [MosRecord.create_data(10, b'xyz'),
                   MosRecord.create_data(14, b'abc'),
                   MosRecord.create_eof(2)]
        file = MosFile.from_records(records)
        file.validate_records(data_ordering=True)
        file.validate_records(data_ordering=False)

    def test_validate_records_raises_records(self):
        file = MosFile()
        with pytest.raises(ValueError, match='records required'):
            file.validate_records()

    def test_validate_records_raises_data_order(self):
        records = [MosRecord.create_data(14, b'xyz'),
                   MosRecord.create_data(10, b'abc'),
                   MosRecord.create_eof(2)]
        file = MosFile.from_records(records)
        with pytest.raises(ValueError, match='unordered data record'):
            file.validate_records(data_ordering=True)

        records = [MosRecord.create_data(13, b'xyz'),
                   MosRecord.create_data(10, b'abc'),
                   MosRecord.create_eof(2)]
        file = MosFile.from_records(records)
        with pytest.raises(ValueError, match='unordered data record'):
            file.validate_records(data_ordering=True)

        records = [MosRecord.create_data(10, b'abc'),
                   MosRecord.create_data(10, b'xyz'),
                   MosRecord.create_eof(2)]
        file = MosFile.from_records(records)
        with pytest.raises(ValueError, match='unordered data record'):
            file.validate_records(data_ordering=True)

        records = [MosRecord.create_data(10, b'abc'),
                   MosRecord.create_data(12, b'xyz'),
                   MosRecord.create_eof(2)]
        file = MosFile.from_records(records)
        with pytest.raises(ValueError, match='unordered data record'):
            file.validate_records(data_ordering=True)

    def test_validate_records_raises_eof_order(self):
        records = [MosRecord.create_eof(0),
                   MosRecord.create_data(0x1234, b'abc')]
        file = MosFile.from_records(records)
        with pytest.raises(ValueError, match='end of file record not last'):
            file.validate_records(data_ordering=False)

    def test_validate_records_raises_eof_address(self):
        records = [MosRecord.create_eof(1)]
        file = MosFile.from_records(records)
        with pytest.raises(ValueError, match='wrong record count as address'):
            file.validate_records(data_ordering=False)

    def test_validate_records_raises_eof_missing(self):
        records = [MosRecord.create_data(0x1234, b'abc')]
        file = MosFile.from_records(records)
        with pytest.raises(ValueError, match='missing end of file record'):
            file.validate_records(eof_record_required=True)
