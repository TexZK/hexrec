import io
import os
import sys
from pathlib import Path

import pytest
from bytesparse import Memory
from test_base import BaseTestFile
from test_base import BaseTestRecord
from test_base import BaseTestTag
from test_base import replace_stdin
from test_base import replace_stdout

from hexrec.formats.avr import AvrFile
from hexrec.formats.avr import AvrRecord
from hexrec.formats.avr import AvrTag


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


class TestAvrTag(BaseTestTag):

    Tag = AvrTag

    def test_enum(self):
        assert AvrTag.DATA.value == Ellipsis

    def test_is_data(self):
        assert AvrTag.DATA.is_data() is True

    def test_is_file_termination(self):
        assert AvrTag.DATA.is_file_termination() is False


class TestAvrRecord(BaseTestRecord):

    Record = AvrRecord

    def test___bytes__(self):
        Record = self.Record
        record = Record(self.Record.Tag._DATA, address=0x654321, data=b'\xAB\xCD')
        assert bytes(record) == record.to_bytestr()

    def test___init___default(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, data=b'\x00\x00')
        assert record.address == 0
        assert record.after == b''
        assert record.before == b''
        assert record.checksum == record.compute_checksum()
        assert record.coords == (-1, -1)
        assert record.count == record.compute_count()
        assert record.data == b'\x00\x00'
        assert record.tag == Tag._DATA

    def test___str___type(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xy', count=None, checksum=None,
                        before=b'', after=b'', coords=(33, 44), validate=False)
        text = str(record)
        assert isinstance(text, str)
        assert text

    def test_compute_checksum(self):
        record = AvrRecord.create_data(62, b'ab')
        record.validate()
        assert record.compute_checksum() is None

    def test_compute_count(self):
        record = AvrRecord.create_data(62, b'ab')
        record.validate()
        assert record.compute_count() is None

    def test_create_data(self):
        record = AvrRecord.create_data(62, b'ab')
        record.validate()
        assert record.tag == AvrTag.DATA
        assert record.address == 62
        assert record.data == b'ab'

    def test_create_data_raises_address(self):
        AvrRecord.create_data(0, b'ab')
        AvrRecord.create_data(0xFFFFFF, b'ab')

        with pytest.raises(ValueError, match='address overflow'):
            AvrRecord.create_data(-1, b'ab')

        with pytest.raises(ValueError, match='address overflow'):
            AvrRecord.create_data(0x1000000, b'ab')

    def test_create_data_raises_data(self):
        AvrRecord.create_data(0, b'ab')

        with pytest.raises(ValueError, match='size overflow'):
            AvrRecord.create_data(62, b'a')

        with pytest.raises(ValueError, match='size overflow'):
            AvrRecord.create_data(62, b'abc')

    def test_data_to_int(self):
        Tag = self.Record.Tag
        Record = self.Record
        vector = [
            (0x0000, Record(Tag._DATA, data=b'\x00\x00')),
            (0xFFFF, Record(Tag._DATA, data=b'\xFF\xFF')),
            (0x1234, Record(Tag._DATA, data=b'\x12\x34')),
            (0xABCD, Record(Tag._DATA, data=b'\xAB\xCD')),
        ]
        for expected, record in vector:
            actual = record.data_to_int()
            assert actual == expected

    def test_data_to_int_big_signed(self):
        Tag = self.Record.Tag
        Record = self.Record
        vector = [
            (+0x0000, Record(Tag._DATA, data=b'\x00\x00')),
            (-0x0001, Record(Tag._DATA, data=b'\xFF\xFF')),
            (+0x1234, Record(Tag._DATA, data=b'\x12\x34')),
            (-0x5433, Record(Tag._DATA, data=b'\xAB\xCD')),
        ]
        for expected, record in vector:
            actual = record.data_to_int(byteorder='big', signed=True)
            assert actual == expected

    def test_data_to_int_big_unsigned(self):
        Tag = self.Record.Tag
        Record = self.Record
        vector = [
            (0x0000, Record(Tag._DATA, data=b'\x00\x00')),
            (0xFFFF, Record(Tag._DATA, data=b'\xFF\xFF')),
            (0x1234, Record(Tag._DATA, data=b'\x12\x34')),
            (0xABCD, Record(Tag._DATA, data=b'\xAB\xCD')),
        ]
        for expected, record in vector:
            actual = record.data_to_int(byteorder='big', signed=False)
            assert actual == expected

    def test_data_to_int_little_signed(self):
        Tag = self.Record.Tag
        Record = self.Record
        vector = [
            (+0x0000, Record(Tag._DATA, data=b'\x00\x00')),
            (-0x0001, Record(Tag._DATA, data=b'\xFF\xFF')),
            (+0x3412, Record(Tag._DATA, data=b'\x12\x34')),
            (-0x3255, Record(Tag._DATA, data=b'\xAB\xCD')),
        ]
        for expected, record in vector:
            actual = record.data_to_int(byteorder='little', signed=True)
            assert actual == expected

    def test_data_to_int_little_unsigned(self):
        Tag = self.Record.Tag
        Record = self.Record
        vector = [
            (0x0000, Record(Tag._DATA, data=b'\x00\x00')),
            (0xFFFF, Record(Tag._DATA, data=b'\xFF\xFF')),
            (0x3412, Record(Tag._DATA, data=b'\x12\x34')),
            (0xCDAB, Record(Tag._DATA, data=b'\xAB\xCD')),
        ]
        for expected, record in vector:
            actual = record.data_to_int(byteorder='little', signed=False)
            assert actual == expected

    def test_parse(self):
        lines = [
            b'000000:0000\r\n',
            b'000000:FFFF\r\n',
            b'FFFFFF:0000\r\n',
            b'FFFFFF:FFFF\r\n',
        ]
        records = [
            AvrRecord.create_data(0x000000, b'\x00\x00'),
            AvrRecord.create_data(0x000000, b'\xFF\xFF'),
            AvrRecord.create_data(0xFFFFFF, b'\x00\x00'),
            AvrRecord.create_data(0xFFFFFF, b'\xFF\xFF'),
        ]
        for index, (line, expected) in enumerate(zip(lines, records)):
            actual = AvrRecord.parse(line)
            actual.validate()
            assert actual == expected
            assert actual.after == b''
            assert actual.before == b''

    def test_parse_syntax(self):
        lines = [
            b'000000:0000\r\n',
            b' \t000000:0000\r\n',
            b'000000:0000 \t\r\n',
            b'000000 \t:0000\r\n',
            b'000000: \t0000\r\n',
            b'000000:0000\n',
            b'000000:0000\r',
            b'000000:0000',
        ]
        expected = AvrRecord.create_data(0x0000, b'\x00\x00')
        for line in lines:
            actual = AvrRecord.parse(line, validate=False)
            assert actual == expected

    def test_parse_syntax_raises(self):
        lines = [
            b'00000000:0000\r\n',
            b'0000000:0000\r\n',
            b'00000:0000\r\n',
            b'0000:0000\r\n',
            b':0000\r\n',

            b'000000:000000\r\n',
            b'000000:00000\r\n',
            b'000000:000\r\n',
            b'000000:00\r\n',
            b'000000:\r\n',

            b'000000::0000\r\n',
            b'......:0000\r\n',
            b'000000.0000\r\n',
            b'000000:....\r\n',

            b'.000000:0000\r\n',
            b'000000.:0000\r\n',
            b'000000:.0000\r\n',
            b'000000:0000.\r\n',
        ]
        for line in lines:
            with pytest.raises(ValueError, match='syntax error'):
                AvrRecord.parse(line)

    def test_print(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'\xAB\xCD', count=None, checksum=None,
                        before=b'', after=b'', coords=(33, 44), validate=False)
        plain_stream = io.BytesIO()
        record.print(stream=plain_stream, color=False)
        color_stream = io.BytesIO()
        record.print(stream=color_stream, color=True)
        plain_text = plain_stream.getvalue()
        color_text = color_stream.getvalue()
        assert plain_text
        assert color_text
        assert len(color_text) >= len(plain_text)

    def test_print_stdout(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'\xAB\xCD', count=None, checksum=None,
                        before=b'', after=b'', coords=(33, 44), validate=False)
        stream = io.BytesIO()
        stdout = sys.stdout
        try:
            sys.stdout = stream
            record.print(stream=stream, color=False)
        finally:
            sys.stdout = stdout
        text = stream.getvalue()
        assert text

    def test_serialize(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'\xAB\xCD', count=None, checksum=None,
                        before=b'', after=b'', coords=(33, 44), validate=False)
        stream = io.BytesIO()
        record.serialize(stream)
        actual = stream.getvalue()
        expected = record.to_bytestr()
        assert actual == expected

    def test_to_bytestr(self):
        record = AvrRecord.create_data(0x654321, b'\xAB\xCD')
        line = record.to_bytestr()
        assert line == b'654321:ABCD\r\n'

        record = AvrRecord.create_data(0x654321, b'\xAB\xCD')
        line = record.to_bytestr(end=b'\n')
        assert line == b'654321:ABCD\n'

    def test_to_tokens(self):
        record = AvrRecord.create_data(0x654321, b'\xAB\xCD')
        tokens = record.to_tokens(end=b'\n')
        ref = {
            'before': b'',
            'address': b'654321',
            'begin': b':',
            'data': b'ABCD',
            'after': b'',
            'end': b'\n',
        }
        assert tokens == ref

    def test_validate_address(self):
        record = AvrRecord(AvrTag.DATA, data=b'\xAB\xCD', address=-1, validate=False)
        with pytest.raises(ValueError, match='address'):
            record.validate()

        record = AvrRecord(AvrTag.DATA, data=b'\xAB\xCD', address=0)
        record.validate()

        record = AvrRecord(AvrTag.DATA, data=b'\xAB\xCD', address=0xFFFFFF)
        record.validate()

        record = AvrRecord(AvrTag.DATA, data=b'\xAB\xCD', address=0x1000000, validate=False)
        with pytest.raises(ValueError, match='address'):
            record.validate()

    def test_validate_after(self):
        record = AvrRecord(AvrTag.DATA, data=b'\xAB\xCD', after=b' ')
        record.validate()

        record = AvrRecord(AvrTag.DATA, data=b'\xAB\xCD', after=b'?', validate=False)
        with pytest.raises(ValueError, match='junk after is not whitespace'):
            record.validate()

    def test_validate_before(self):
        record = AvrRecord(AvrTag.DATA, data=b'\xAB\xCD', before=b'?', validate=False)
        with pytest.raises(ValueError, match='junk before is not whitespace'):
            record.validate()

    def test_validate_data(self):
        record = AvrRecord(AvrTag.DATA, data=b'\xAB\xCD')
        record.validate()

        record = AvrRecord(AvrTag.DATA, data=b'\xAB', validate=False)
        with pytest.raises(ValueError, match='data size'):
            record.validate()

        record = AvrRecord(AvrTag.DATA, data=b'\xAB\xCD\xEF', validate=False)
        with pytest.raises(ValueError, match='data size'):
            record.validate()

    def test_validate_default(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, data=b'\x00\x00')
        returned = record.validate()
        assert returned is record

    def test_validate_checksum_none(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, data=b'\x00\x00', checksum=None)
        returned = record.validate(checksum=False)
        assert returned is record

    def test_validate_count_none(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, data=b'\x00\x00', count=None, checksum=None)
        returned = record.validate(count=False, checksum=False)
        assert returned is record


class TestAvrFile(BaseTestFile):

    File = AvrFile

    def test___bool___(self):
        File = self.File

        file = File()
        assert bool(file) is False
        file.append(0)
        assert bool(file) is True

        file = File.from_records(File().records)
        assert bool(file) is False

        file = File.from_records(File.from_bytes(b'\x00\x00').records)
        assert bool(file) is True

    def test___eq___false_memory(self):
        File = self.File
        file1 = File.from_bytes(b'ab', offset=(5 * 2))
        file2 = File.from_blocks([[(6 * 2), b'ab']])
        assert file1 is not file2
        assert (file1 == file2) is False
        file3 = File.from_blocks([[(5 * 2), b'xy']])
        assert file1 is not file3
        assert (file1 == file3) is False
        file4 = file1.copy()
        meta_keys = list(file4.META_KEYS) + ['_this_is_an_unknown_meta_key_']
        setattr(file1, 'META_KEYS', meta_keys)
        assert file1 is not file4
        assert (file1 == file4) is False

    def test___eq___false_records(self):
        File = self.File
        Record = File.Record
        file1 = File.from_records([Record.create_data(5, b'ab')])
        file2 = File.from_records([Record.create_data(6, b'ab')])
        assert file1 is not file2
        assert (file1 == file2) is False
        file3 = File.from_records([Record.create_data(5, b'xy')])
        assert file1 is not file3
        assert (file1 == file3) is False

    def test___eq___raises(self):
        File = self.File
        Record = File.Record
        file1 = File.from_bytes(b'ab', offset=(5 * 2))
        file2 = File.from_records([Record.create_data(5, b'ab')])
        assert file1 is not file2
        with pytest.raises(ValueError, match='both memory or both records required'):
            assert (file1 == file2) is True

    def test___eq___true_memory(self):
        File = self.File
        file1 = File.from_bytes(b'ab', offset=(5 * 2))
        file2 = File.from_blocks([[(5 * 2), b'ab']])
        assert file1 is not file2
        assert (file1 == file2) is True
        file1.update_records()
        file1.discard_memory()
        file2.update_records()
        file2.discard_memory()
        assert (file1 == file2) is True

    def test___eq___true_records(self):
        File = self.File
        Record = File.Record
        file1 = File.from_records([Record.create_data(5, b'ab')])
        file2 = File.from_records([Record.create_data(5, b'ab')])
        assert file1 is not file2
        assert (file1 == file2) is True

    def test___ne___false_memory(self):
        File = self.File
        file1 = File.from_bytes(b'ab', offset=(5 * 2))
        file2 = File.from_blocks([[(5 * 2), b'ab']])
        assert file1 is not file2
        assert (file1 != file2) is False

    def test___ne___false_records(self):
        File = self.File
        Record = File.Record
        file1 = File.from_records([Record.create_data(5, b'ab')])
        file2 = File.from_records([Record.create_data(5, b'ab')])
        assert file1 is not file2
        assert (file1 != file2) is False

    def test___ne___raises(self):
        File = self.File
        Record = File.Record
        file1 = File.from_bytes(b'ab', offset=(5 * 2))
        file2 = File.from_records([Record.create_data(5, b'xy')])
        assert file1 is not file2
        with pytest.raises(ValueError, match='both memory or both records required'):
            assert (file1 != file2) is True

    def test___ne___true_memory(self):
        File = self.File
        file1 = File.from_bytes(b'ab', offset=(5 * 2))
        file2 = File.from_blocks([[(6 * 2), b'ab']])
        assert file1 is not file2
        assert (file1 != file2) is True
        file3 = File.from_blocks([[(5 * 2), b'xy']])
        assert file1 is not file3
        assert (file1 != file3) is True
        file4 = file1.copy()
        meta_keys = list(file4.META_KEYS) + ['_this_is_an_unknown_meta_key_']
        setattr(file1, 'META_KEYS', meta_keys)
        assert file1 is not file4
        assert (file1 != file4) is True

    def test___ne___true_records(self):
        File = self.File
        Record = File.Record
        file1 = File.from_records([Record.create_data(5, b'ab')])
        file2 = File.from_records([Record.create_data(6, b'ab')])
        assert file1 is not file2
        assert (file1 != file2) is True
        file3 = File.from_records([Record.create_data(5, b'xy')])
        assert file1 is not file3
        assert (file1 != file3) is True

    def test_apply_records(self):
        File = self.File
        Record = File.Record
        Tag = Record.Tag
        records = [
            Record(Tag._DATA, address=5, data=b'ab'),
            Record(Tag._DATA, address=10, data=b'xy'),
        ]
        file = File.from_records(records)
        file._memory = Memory.from_bytes(b'discarded!')
        assert file._records is records
        returned = file.apply_records()
        assert returned is file
        assert file._memory.to_blocks() == [[(5 * 2), b'ab'], [(10 * 2), b'xy']]
        assert file._records is records

    def test_discard_records(self):
        File = self.File
        file = File.from_bytes(b'abcxyz', offset=(5 * 2))

        file._records = []
        assert file._memory is not None
        returned = file.discard_records()
        assert returned is file
        assert file._memory is not None
        assert file._records is None

        file.update_records()
        assert file._records
        assert file._memory is not None
        returned = file.discard_records()
        assert returned is file
        assert file._memory is not None
        assert file._records is None

        file._memory = None
        returned = file.discard_records()
        assert returned is file
        assert file._records is None
        assert file._memory is not None
        assert not file._memory

    def test_discard_memory(self):
        File = self.File
        file = File.from_bytes(b'abcxyz', offset=(5 * 2))

        file.update_records()
        assert file._memory
        assert file._records
        returned = file.discard_memory()
        assert returned is file
        assert file._memory is None

        file._records = None
        returned = file.discard_memory()
        assert returned is file
        assert file._records is None
        assert file._memory is not None
        assert not file._memory

    def test_from_records(self):
        File = self.File
        Record = File.Record
        records = [
            Record.create_data(123, b'ab'),
            Record.create_data(456, b'xy'),
        ]
        file = File.from_records(records)
        assert file is not None
        assert isinstance(file, File)
        assert file._records is records
        assert file._memory is None
        assert file.maxdatalen == 2

    def test_from_records_maxdatalen(self):
        File = self.File
        Record = File.Record
        records = [
            Record.create_data(123, b'ab'),
            Record.create_data(456, b'xy'),
        ]
        file = File.from_records(records, maxdatalen=2)
        assert file is not None
        assert isinstance(file, File)
        assert file._records is records
        assert file._memory is None
        assert file.maxdatalen == 2

    def test_load_file(self, datapath):
        path = str(datapath / 'basic.rom')
        records = [
            AvrRecord.create_data(0x123456, b'\xAB\xCD'),
            AvrRecord.create_data(0xABCDEF, b'\x12\x34'),
        ]
        file = AvrFile.load(path)
        assert file.records == records

    def test_load_stdin(self):
        buffer = (
            b'123456:ABCD\r\n'
            b'ABCDEF:1234\r\n'
        )
        records = [
            AvrRecord.create_data(0x123456, b'\xAB\xCD'),
            AvrRecord.create_data(0xABCDEF, b'\x12\x34'),
        ]
        stream = io.BytesIO(buffer)
        with replace_stdin(stream):
            file = AvrFile.load(None)
        assert file._records == records

    def test_memory_getter(self):
        File = self.File
        Record = File.Record
        Tag = Record.Tag
        records = [
            Record(Tag._DATA, address=5, data=b'ab'),
            Record(Tag._DATA, address=10, data=b'xy'),
        ]
        file = File.from_records(records)
        file._memory = None
        assert file._records is records
        memory = file.memory
        assert memory is file._memory
        assert memory.to_blocks() == [[(5 * 2), b'ab'], [(10 * 2), b'xy']]
        assert file._records is records
        file._records = None
        memory = file.memory
        assert memory is file._memory
        assert memory.to_blocks() == [[(5 * 2), b'ab'], [(10 * 2), b'xy']]
        assert file._records is None

    def test_parse(self):
        buffer = (
            b'123456:ABCD\r\n'
            b'ABCDEF:1234\r\n'
        )
        records = [
            AvrRecord.create_data(0x123456, b'\xAB\xCD'),
            AvrRecord.create_data(0xABCDEF, b'\x12\x34'),
        ]
        with io.BytesIO(buffer) as stream:
            file = AvrFile.parse(stream)
        assert file._records == records

    def test_parse_empty(self):
        with io.BytesIO(b'') as stream:
            file = AvrFile.parse(stream)
        assert not file._records
        assert file._records == []

    def test_parse_file_basic(self, datapath):
        path = str(datapath / 'basic.rom')
        records = [
            AvrRecord.create_data(0x123456, b'\xAB\xCD'),
            AvrRecord.create_data(0xABCDEF, b'\x12\x34'),
        ]
        with open(path, 'rb') as stream:
            file = AvrFile.parse(stream)
        assert file._records == records

    def test_print(self):
        File = self.File
        file = File.from_bytes(b'ab')
        stream_plain = io.BytesIO()
        returned = file.print(stream=stream_plain, color=False)
        assert returned is file
        buffer_plain = stream_plain.getvalue()
        assert len(buffer_plain) > 0
        stream_color = io.BytesIO()
        returned = file.print(stream=stream_color, color=True)
        assert returned is file
        buffer_color = stream_color.getvalue()
        assert len(buffer_color) > 0
        assert len(buffer_plain) <= len(buffer_color)

    def test_print_stdout(self):
        File = self.File
        file = File.from_bytes(b'ab')
        stream_plain = io.BytesIO()
        with replace_stdout(stream_plain):
            returned = file.print(stream=None, color=False)
            assert returned is file
        buffer_plain = stream_plain.getvalue()
        assert len(buffer_plain) > 0

    def test_records_getter(self):
        File = self.File
        blocks = [[(5 * 2), b'ab'], [(10 * 2), b'xy']]
        memory = Memory.from_blocks(blocks)
        file = File.from_memory(memory)
        file._records = None
        assert file._memory.to_blocks() == blocks
        actual = file.records
        assert actual is file._records
        assert len(actual) >= 2
        assert file._memory is memory
        file._memory = None
        actual = file.records
        assert actual is file._records
        assert len(actual) >= 2
        assert file._memory is None

    def test_save_file(self, tmppath):
        path = str(tmppath / 'test_save_file.rom')
        records = [
            AvrRecord.create_data(0x123456, b'\xAB\xCD'),
            AvrRecord.create_data(0xABCDEF, b'\x12\x34'),
        ]
        expected = (
            b'123456:ABCD\r\n'
            b'ABCDEF:1234\r\n'
        )
        file = AvrFile.from_records(records)
        returned = file.save(path)
        assert returned is file
        with open(path, 'rb') as stream:
            actual = stream.read()
        assert actual == expected

    def test_save_stdout(self):
        records = [
            AvrRecord.create_data(0x123456, b'\xAB\xCD'),
            AvrRecord.create_data(0xABCDEF, b'\x12\x34'),
        ]
        expected = (
            b'123456:ABCD\r\n'
            b'ABCDEF:1234\r\n'
        )
        stream = io.BytesIO()
        file = AvrFile.from_records(records)
        with replace_stdout(stream):
            returned = file.save(None)
        assert returned is file
        actual = stream.getvalue()
        assert actual == expected

    def test_serialize(self):
        File = self.File
        records = [
            AvrRecord.create_data(0x123456, b'\xAB\xCD'),
            AvrRecord.create_data(0xABCDEF, b'\x12\x34'),
        ]
        file = File.from_records(records)
        stream = io.BytesIO()
        returned = file.serialize(stream)
        assert returned is file
        actual = stream.getvalue()
        expected = (
            b'123456:ABCD\r\n'
            b'ABCDEF:1234\r\n'
        )
        assert actual == expected

    def test_update_records(self):
        word_address = 0x654321
        byte_address = word_address * 2
        file = AvrFile().write(byte_address, b'\xAB\xCD\x89\xEF')
        file.update_records()
        records = file._records
        assert len(records) == 2

        record0 = records[0]
        assert record0.tag == AvrTag.DATA
        assert record0.address == word_address
        assert record0.data == b'\xAB\xCD'

        record1 = records[1]
        assert record1.tag == AvrTag.DATA
        assert record1.address == word_address + 1
        assert record1.data == b'\x89\xEF'

    def test_update_records_empty(self):
        file = AvrFile()
        file.update_records()
        records = file._records
        assert not records
        assert records == []

    def test_update_records_raises_maxdatalen(self):
        file = AvrFile()

        file._maxdatalen = 1
        with pytest.raises(ValueError, match='invalid maximum data length'):
            file.update_records()

        file._maxdatalen = 3
        with pytest.raises(ValueError, match='invalid maximum data length'):
            file.update_records()

    def test_update_records_raises_memory(self):
        records = [
            AvrRecord.create_data(0x123456, b'\xAB\xCD'),
            AvrRecord.create_data(0xABCDEF, b'\x12\x34'),
        ]
        file = AvrFile.from_records(records)
        with pytest.raises(ValueError, match='memory instance required'):
            file.update_records()

    def test_update_records_raises_word_alignment(self):
        file = AvrFile.from_bytes(b'ab', offset=1)
        with pytest.raises(ValueError, match='invalid word alignment'):
            file.update_records()

    def test_update_records_raises_word_size(self):
        file = AvrFile.from_bytes(b'a')
        with pytest.raises(ValueError, match='invalid word size'):
            file.update_records()

    def test_validate_records(self):
        records = [
            AvrRecord.create_data(0x123456, b'\xAB\xCD'),
            AvrRecord.create_data(0xABCDEF, b'\x12\x34'),
        ]
        file = AvrFile.from_records(records)

    def test_validate_records_data_order(self):
        records = [
            AvrRecord.create_data(0x123456, b'\xAB\xCD'),
            AvrRecord.create_data(0xABCDEF, b'\x12\x34'),
        ]
        file = AvrFile.from_records(records)
        file.validate_records(data_ordering=True)
        file.validate_records(data_ordering=False)

    def test_validate_records_raises_records(self):
        file = AvrFile()
        with pytest.raises(ValueError, match='records required'):
            file.validate_records()

    def test_validate_records_raises_data_order(self):
        records = [
            AvrRecord.create_data(0xABCDEF, b'\x12\x34'),
            AvrRecord.create_data(0x123456, b'\xAB\xCD'),
        ]
        file = AvrFile.from_records(records)
        with pytest.raises(ValueError, match='unordered data record'):
            file.validate_records(data_ordering=True)
