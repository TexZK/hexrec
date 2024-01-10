# -*- coding: utf-8 -*-
import abc
import io
import enum
import sys
from binascii import hexlify
from typing import Mapping
from typing import cast as _cast

import pytest
from bytesparse import Memory
from hexrec import FILE_TYPES
from hexrec.formats.intel import IhexFile
from hexrec.formats.motorola import SrecFile
from hexrec.records import BaseFile
from hexrec.records import BaseRecord
from hexrec.records import BaseTag
from hexrec.records import colorize_tokens
from hexrec.records import guess_type_class
from hexrec.records import guess_type_name
from hexrec.utils import AnyBytes


# ============================================================================

@pytest.mark.skip(reason='TODO')
def test_colorize_tokens():
    ...  # TODO:


# ----------------------------------------------------------------------------

def test_guess_type_name():
    vector = [
        ('ihex', 'example.hex'),
        ('srec', 'example.srec'),
    ]
    for expected, path in vector:
        actual = guess_type_name(path)
        assert actual == expected


def test_guess_type_class():
    vector = [
        (IhexFile, 'example.hex'),
        (SrecFile, 'example.srec'),
    ]
    for expected, path in vector:
        actual = guess_type_class(path)
        assert actual is expected


# ============================================================================

class BaseTestTag:

    Tag = BaseTag
    Tag_FAKE = _cast(BaseTag, -1)

    def test_is_data(self):
        assert self.Tag._DATA.is_data() is True


# ----------------------------------------------------------------------------

class BaseTestRecord:

    Record = BaseRecord

    def test___bytes__(self):
        Record = self.Record
        record = Record(self.Record.Tag._DATA)
        assert bytes(record) == record.to_bytestr()

    def test___eq__(self):
        Tag = self.Record.Tag
        Record = self.Record
        records = [
            Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                   before=b'b', after=b'a', coords=(33, 44)),
            Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                   before=b'?', after=b'a', coords=(33, 44)),
            Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                   before=b'b', after=b'?', coords=(33, 44)),
            Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                   before=b'b', after=b'a', coords=(55, 44)),
            Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                   before=b'b', after=b'a', coords=(33, 66)),
        ]
        record1 = records[0]
        for record2 in records:
            assert record2 == record1

    def test___init___basic(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'b', after=b'a', coords=(33, 44))
        assert record.address == 0x1234
        assert record.after == b'a'
        assert record.before == b'b'
        assert record.checksum == 0xA5
        assert record.coords == (33, 44)
        assert record.count == 3
        assert record.data == b'xyz'
        assert record.tag == Tag._DATA

    def test___init___checksum_ellipsis(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=..., checksum=...,
                        before=b'b', after=b'a', coords=(33, 44))
        assert record.address == 0x1234
        assert record.after == b'a'
        assert record.before == b'b'
        assert record.checksum == record.compute_checksum()
        assert record.coords == (33, 44)
        assert record.count == record.compute_count()
        assert record.data == b'xyz'
        assert record.tag == Tag._DATA

    def test___init___checksum_none(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=..., checksum=None,
                        before=b'b', after=b'a', coords=(33, 44))
        assert record.address == 0x1234
        assert record.after == b'a'
        assert record.before == b'b'
        assert record.checksum is None
        assert record.coords == (33, 44)
        assert record.count == record.compute_count()
        assert record.data == b'xyz'
        assert record.tag == Tag._DATA

    def test___init___count_ellipsis(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=..., checksum=0xA5,
                        before=b'b', after=b'a', coords=(33, 44))
        assert record.address == 0x1234
        assert record.after == b'a'
        assert record.before == b'b'
        assert record.checksum == 0xA5
        assert record.coords == (33, 44)
        assert record.count == record.compute_count()
        assert record.data == b'xyz'
        assert record.tag == Tag._DATA

    def test___init___count_none(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=None, checksum=0xA5,
                        before=b'b', after=b'a', coords=(33, 44))
        assert record.address == 0x1234
        assert record.after == b'a'
        assert record.before == b'b'
        assert record.checksum == 0xA5
        assert record.coords == (33, 44)
        assert record.count is None
        assert record.data == b'xyz'
        assert record.tag == Tag._DATA

    def test___init___default(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA)
        assert record.address == 0
        assert record.after == b''
        assert record.before == b''
        assert record.checksum == record.compute_checksum()
        assert record.coords == (-1, -1)
        assert record.count == record.compute_count()
        assert record.data == b''
        assert record.tag == Tag._DATA

    def test___ne__(self):
        Tag = self.Record.Tag
        Record = self.Record
        Tag_FAKE = _cast(Tag, -1)
        records = [
            Record(Tag_FAKE, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                   before=b'b', after=b'a', coords=(33, 44)),
            Record(Tag._DATA, address=0x4321, data=b'xyz', count=3, checksum=0xA5,
                   before=b'b', after=b'a', coords=(33, 44)),
            Record(Tag._DATA, address=0x1234, data=b'abc', count=3, checksum=0xA5,
                   before=b'b', after=b'a', coords=(33, 44)),
            Record(Tag._DATA, address=0x1234, data=b'xyz', count=4, checksum=0xA5,
                   before=b'b', after=b'a', coords=(33, 44)),
            Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0x5A,
                   before=b'b', after=b'a', coords=(33, 44)),
        ]
        record1 = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                         before=b'b', after=b'a', coords=(33, 44))
        for record2 in records:
            assert record2 != record1

    def test___repr___type(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'', after=b'', coords=(33, 44))
        text = repr(record)
        assert isinstance(text, str)
        assert text

    def test___str___type(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'', after=b'', coords=(33, 44))
        text = str(record)
        assert isinstance(text, str)
        assert text

    @abc.abstractmethod
    def test_compute_checksum(self):
        ...

    @abc.abstractmethod
    def test_compute_count(self):
        ...

    def test_copy(self):
        Tag = self.Record.Tag
        Record = self.Record
        record1 = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                         before=b'b', after=b'a', coords=(33, 44))
        record2 = record1.copy()
        assert record1 is not record2
        assert record1 == record2

    @abc.abstractmethod
    def test_create_data(self):
        ...

    def test_data_to_int(self):
        Tag = self.Record.Tag
        Record = self.Record
        vector = [
            (0x00000000, Record(Tag._DATA, data=b'')),
            (0x00000000, Record(Tag._DATA, data=b'\x00')),
            (0x00000000, Record(Tag._DATA, data=b'\x00\x00\x00\x00')),
            (0x000000FF, Record(Tag._DATA, data=b'\xFF')),
            (0xFFFFFFFF, Record(Tag._DATA, data=b'\xFF\xFF\xFF\xFF')),
            (0x12345678, Record(Tag._DATA, data=b'\x12\x34\x56\x78')),
            (0x00ABCDEF, Record(Tag._DATA, data=b'\xAB\xCD\xEF')),
        ]
        for expected, record in vector:
            actual = record.data_to_int()
            assert actual == expected

    def test_data_to_int_big_signed(self):
        Tag = self.Record.Tag
        Record = self.Record
        vector = [
            (+0x00000000, Record(Tag._DATA, data=b'')),
            (+0x00000000, Record(Tag._DATA, data=b'\x00')),
            (+0x00000000, Record(Tag._DATA, data=b'\x00\x00\x00\x00')),
            (-0x00000001, Record(Tag._DATA, data=b'\xFF')),
            (-0x00000001, Record(Tag._DATA, data=b'\xFF\xFF\xFF\xFF')),
            (+0x12345678, Record(Tag._DATA, data=b'\x12\x34\x56\x78')),
            (-0x00543211, Record(Tag._DATA, data=b'\xAB\xCD\xEF')),
        ]
        for expected, record in vector:
            actual = record.data_to_int(byteorder='big', signed=True)
            assert actual == expected

    def test_data_to_int_big_unsigned(self):
        Tag = self.Record.Tag
        Record = self.Record
        vector = [
            (0x00000000, Record(Tag._DATA, data=b'')),
            (0x00000000, Record(Tag._DATA, data=b'\x00')),
            (0x00000000, Record(Tag._DATA, data=b'\x00\x00\x00\x00')),
            (0x000000FF, Record(Tag._DATA, data=b'\xFF')),
            (0xFFFFFFFF, Record(Tag._DATA, data=b'\xFF\xFF\xFF\xFF')),
            (0x12345678, Record(Tag._DATA, data=b'\x12\x34\x56\x78')),
            (0x00ABCDEF, Record(Tag._DATA, data=b'\xAB\xCD\xEF')),
        ]
        for expected, record in vector:
            actual = record.data_to_int(byteorder='big', signed=False)
            assert actual == expected

    def test_data_to_int_little_signed(self):
        Tag = self.Record.Tag
        Record = self.Record
        vector = [
            (+0x00000000, Record(Tag._DATA, data=b'')),
            (+0x00000000, Record(Tag._DATA, data=b'\x00')),
            (+0x00000000, Record(Tag._DATA, data=b'\x00\x00\x00\x00')),
            (-0x00000001, Record(Tag._DATA, data=b'\xFF')),
            (-0x00000001, Record(Tag._DATA, data=b'\xFF\xFF\xFF\xFF')),
            (+0x78563412, Record(Tag._DATA, data=b'\x12\x34\x56\x78')),
            (-0x00103255, Record(Tag._DATA, data=b'\xAB\xCD\xEF')),
        ]
        for expected, record in vector:
            actual = record.data_to_int(byteorder='little', signed=True)
            assert actual == expected

    def test_data_to_int_little_unsigned(self):
        Tag = self.Record.Tag
        Record = self.Record
        vector = [
            (0x00000000, Record(Tag._DATA, data=b'')),
            (0x00000000, Record(Tag._DATA, data=b'\x00')),
            (0x00000000, Record(Tag._DATA, data=b'\x00\x00\x00\x00')),
            (0x000000FF, Record(Tag._DATA, data=b'\xFF')),
            (0xFFFFFFFF, Record(Tag._DATA, data=b'\xFF\xFF\xFF\xFF')),
            (0x78563412, Record(Tag._DATA, data=b'\x12\x34\x56\x78')),
            (0x00EFCDAB, Record(Tag._DATA, data=b'\xAB\xCD\xEF')),
        ]
        for expected, record in vector:
            actual = record.data_to_int(byteorder='little', signed=False)
            assert actual == expected

    def test_get_meta(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'b', after=b'a', coords=(33, 44))
        actual = record.get_meta()
        expected = {
            'address': 0x1234,
            'after': b'a',
            'before': b'b',
            'checksum': 0xA5,
            'coords': (33, 44),
            'count': 3,
            'data': b'xyz',
            'tag': Tag._DATA,
        }
        assert actual == expected

    @abc.abstractmethod
    def test_parse(self):
        ...

    def test_print(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'', after=b'', coords=(33, 44))
        plain_stream = io.StringIO()
        record.print(stream=plain_stream, color=False)
        color_stream = io.StringIO()
        record.print(stream=color_stream, color=True)
        plain_text = plain_stream.getvalue()
        color_text = color_stream.getvalue()
        assert plain_text
        assert color_text
        assert len(color_text) >= len(plain_text)

    def test_print_stdout(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'', after=b'', coords=(33, 44))
        stream = io.StringIO()
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
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'', after=b'', coords=(33, 44))
        stream = io.BytesIO()
        record.serialize(stream)
        actual = stream.getvalue()
        expected = record.to_bytestr()
        assert actual == expected

    @abc.abstractmethod
    def test_to_bytestr(self):
        ...

    @abc.abstractmethod
    def test_to_tokens(self):
        ...

    def test_update_checksum(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=None,
                        before=b'b', after=b'a', coords=(33, 44))
        assert record.checksum is None
        returned = record.update_checksum()
        assert returned is record
        assert record.checksum == record.compute_checksum()

    def test_update_count(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=None, checksum=0xA5,
                        before=b'b', after=b'a', coords=(33, 44))
        assert record.count is None
        returned = record.update_count()
        assert returned is record
        assert record.count == record.compute_count()

    def test_validate_default(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA)
        returned = record.validate()
        assert returned is record

    def test_validate_checksum_none(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, checksum=None)
        returned = record.validate(checksum=False)
        assert returned is record

    def test_validate_count_none(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, count=None, checksum=None)
        returned = record.validate(count=False, checksum=False)
        assert returned is record

    def test_validate_raises_basic(self):
        Tag = self.Record.Tag
        Record = self.Record
        records = [
            Record(Tag._DATA, address=-1, count=0, checksum=0),

            Record(Tag._DATA, address=0, count=0, checksum=-1),
            Record(Tag._DATA, address=0, count=0, checksum=42),

            Record(Tag._DATA, address=0, count=-1, checksum=0),
            Record(Tag._DATA, address=0, count=42, checksum=0),
        ]
        matches = [
            'address overflow',

            'checksum overflow',
            'wrong checksum',

            'count overflow',
            'wrong count',
        ]
        for record, match in zip(records, matches):
            record.compute_checksum = lambda: 0  # override
            record.compute_count = lambda: 0  # override

            with pytest.raises(ValueError, match=match):
                record.validate()


# ----------------------------------------------------------------------------

class BaseTestFile:

    File = BaseFile

    def test___add__(self):
        File = self.File
        file = File.from_memory(Memory.from_bytes(b'abc', offset=5))
        assert file._memory.to_blocks() == [[5, b'abc']]
        result = file + b'xyz'
        assert result is not file
        assert file._memory.to_blocks() == [[5, b'abc']]
        assert result._memory.to_blocks() == [[5, b'abcxyz']]

    def test___delitem__(self):
        File = self.File
        file = File.from_memory(Memory.from_bytes(b'abcxyz', offset=5))
        assert file._memory.to_blocks() == [[5, b'abcxyz']]
        del file[6]
        assert file._memory.to_blocks() == [[5, b'acxyz']]
        del file[6::2]
        assert file._memory.to_blocks() == [[5, b'axz']]
        del file[:]
        assert file._memory.to_blocks() == []

    def test___getitem__(self):
        File = self.File

        file = File.from_memory(Memory.from_bytes(b'abcxyz', offset=5))
        assert file[6] == ord('b')
        assert file[1] is None
        assert file[7:9] == b'cx'
        assert file[6::2] == b'bxz'

        blocks = [[5, b'abc'], [10, b'xyz']]
        file = File.from_memory(Memory.from_blocks(blocks))
        assert file[::b'.'] == b'abc..xyz'
        with pytest.raises(ValueError, match='non-contiguous'):
            assert file[::]

    def test___eq__(self):
        File = self.File
        file1 = File.from_memory(Memory.from_bytes(b'abc', offset=5))
        file2 = File.from_memory(Memory.from_blocks([[5, b'abc']]))
        assert file1 is not file2
        assert file1 == file2

    def test___iadd__(self):
        File = self.File
        file = File.from_memory(Memory.from_bytes(b'abc', offset=5))
        assert file._memory.to_blocks() == [[5, b'abc']]
        original = file
        file += b'xyz'
        assert file is original
        assert file._memory.to_blocks() == [[5, b'abcxyz']]

    def test___ior___(self):
        File = self.File
        file1 = File.from_memory(Memory.from_bytes(b'abc', offset=5))
        file2 = File.from_memory(Memory.from_blocks([[10, b'xyz']]))
        original = file1
        file1 |= file2
        assert file1 is original
        assert file1 is not file2
        assert file1 != file2
        assert file1._memory.to_blocks() == [[5, b'abc'], [10, b'xyz']]

    def test___neq__(self):
        File = self.File

        file1 = File.from_memory(Memory.from_bytes(b'abc', offset=5))
        file2 = File.from_memory(Memory.from_blocks([[6, b'abc']]))
        assert file1 is not file2
        assert file1 != file2

        file1 = File.from_memory(Memory.from_bytes(b'abc', offset=5))
        file2 = File.from_memory(Memory.from_blocks([[5, b'xyz']]))
        assert file1 is not file2
        assert file1 != file2

    def test___or__(self):
        File = self.File
        file1 = File.from_memory(Memory.from_bytes(b'abc', offset=5))
        file2 = File.from_memory(Memory.from_blocks([[10, b'xyz']]))
        result = file1 | file2
        assert result is not file1
        assert result is not file2
        assert result != file1
        assert result != file2
        assert result._memory.to_blocks() == [[5, b'abc'], [10, b'xyz']]

    def test___setitem__(self):
        File = self.File
        file = File.from_memory(Memory.from_bytes(b'abcxyz', offset=5))
        assert file._memory.to_blocks() == [[5, b'abcxyz']]
        file[6] = b'?'
        assert file._memory.to_blocks() == [[5, b'a?cxyz']]
        file[5::2] = b'...'
        assert file._memory.to_blocks() == [[5, b'.?.x.z']]
        file[0:] = b'123'
        assert file._memory.to_blocks() == [[0, b'123']]

    def test__is_line_empty(self):
        File = self.File
        assert File._is_line_empty(b'') is True
        assert File._is_line_empty(b' \t\v\r\n') is True

    def test_append(self):
        File = self.File
        file = File.from_memory(Memory.from_bytes(b'abc', offset=5))
        assert file._memory.to_blocks() == [[5, b'abc']]
        returned = file.append(b'.')
        assert returned is file
        assert file._memory.to_blocks() == [[5, b'abc.']]
        assert file._records is None
        file.append(ord('?'))
        assert file._memory.to_blocks() == [[5, b'abc.?']]

    def test_apply_records(self):
        File = self.File
        Record = File.Record
        Tag = Record.Tag
        records = [
            Record(Tag._DATA, address=5, data=b'abc'),
            Record(Tag._DATA, address=10, data=b'xyz'),
        ]
        file = File.from_records(records)
        file._memory = Memory.from_bytes(b'discarded')
        assert file._records is records
        returned = file.apply_records()
        assert returned is file
        assert file._memory.to_blocks() == [[5, b'abc'], [10, b'xyz']]
        assert file._records is records

    def test_clear(self):
        File = self.File
        file = File.from_memory(Memory.from_bytes(b'abcxyz', offset=5))
        file._records = []
        assert file._memory.to_blocks() == [[5, b'abcxyz']]
        returned = file.clear(start=7, endex=9)
        assert returned is file
        assert file._memory.to_blocks() == [[5, b'ab'], [9, b'yz']]
        assert file._records is None

    def test_convert_meta(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
        maxdatalen = max(1, File.DEFAULT_DATALEN - 1)
        memory = Memory.from_blocks(blocks)
        original = File.from_memory(memory, maxdatalen=maxdatalen)
        converted = File.convert(original, meta=True)
        assert converted is not original
        assert converted == original
        assert converted._memory is not original._memory
        assert converted.memory == original.memory
        assert converted.get_meta() == original.get_meta()

    def test_convert_no_meta(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
        maxdatalen = max(1, File.DEFAULT_DATALEN - 1)
        memory = Memory.from_blocks(blocks)
        original = File.from_memory(memory, maxdatalen=maxdatalen)
        converted = File.convert(original, meta=False)
        assert converted is not original
        assert converted != original
        assert converted._memory is not original._memory
        assert converted.memory == original.memory
        converted_meta = converted.get_meta()
        assert converted_meta != original.get_meta()
        assert converted_meta['maxdatalen'] == File.DEFAULT_DATALEN

    def test_copy_meta(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
        maxdatalen = max(1, File.DEFAULT_DATALEN - 1)
        memory = Memory.from_blocks(blocks)
        original = File.from_memory(memory, maxdatalen=maxdatalen)
        copied = original.copy(meta=True)
        assert copied is not original
        assert copied == original
        assert copied._records is None
        assert copied._memory is not original._memory
        assert copied._memory == original._memory
        assert copied.get_meta() == original.get_meta()

    def test_copy_no_meta(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
        maxdatalen = max(1, File.DEFAULT_DATALEN - 1)
        memory = Memory.from_blocks(blocks)
        original = File.from_memory(memory, maxdatalen=maxdatalen)
        copied = original.copy(meta=False)
        assert copied is not original
        assert copied != original
        assert copied._records is None
        assert copied._memory is not original._memory
        assert copied._memory == original._memory
        copied_meta = copied.get_meta()
        assert copied_meta != original.get_meta()
        assert copied_meta['maxdatalen'] == File.DEFAULT_DATALEN

    def test_copy_slice(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
        maxdatalen = max(1, File.DEFAULT_DATALEN - 1)
        memory = Memory.from_blocks(blocks)
        original = File.from_memory(memory, maxdatalen=maxdatalen)
        copied = original.copy(start=6, endex=12, meta=True)
        assert copied is not original
        assert copied != original
        assert copied._records is None
        assert copied._memory is not original._memory
        assert copied._memory.to_blocks() == [[6, b'bc'], [10, b'xy']]
        assert copied.get_meta() == original.get_meta()

    def test_crop(self):
        File = self.File
        file = File.from_memory(Memory.from_bytes(b'abcxyz', offset=5))
        file._records = []
        assert file._memory.to_blocks() == [[5, b'abcxyz']]
        returned = file.crop(start=7, endex=9)
        assert returned is file
        assert file._memory.to_blocks() == [[7, b'cx']]
        assert file._records is None

    def test_cut_meta(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
        maxdatalen = max(1, File.DEFAULT_DATALEN - 1)
        memory = Memory.from_blocks(blocks)
        original = File.from_memory(memory, maxdatalen=maxdatalen)
        outer = original.copy()
        inner = outer.cut(meta=True)
        assert inner is not original
        assert inner == original
        assert inner._records is None
        assert inner._memory is not original._memory
        assert inner._memory == original._memory
        assert inner.get_meta() == original.get_meta()
        assert outer is not original
        assert outer != original
        assert outer._records is None
        assert outer._memory is not original._memory
        assert outer._memory.to_blocks() == []
        assert outer.get_meta() == original.get_meta()

    def test_cut_no_meta(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
        maxdatalen = max(1, File.DEFAULT_DATALEN - 1)
        memory = Memory.from_blocks(blocks)
        original = File.from_memory(memory, maxdatalen=maxdatalen)
        outer = original.copy()
        inner = outer.cut(meta=False)
        assert inner is not original
        assert inner != original
        assert inner._records is None
        assert inner._memory is not original._memory
        assert inner._memory == original._memory
        inner_meta = inner.get_meta()
        assert inner_meta != original.get_meta()
        assert inner_meta['maxdatalen'] == File.DEFAULT_DATALEN
        assert outer is not original
        assert outer != original
        assert outer._records is None
        assert outer._memory is not original._memory
        assert outer._memory.to_blocks() == []
        assert outer.get_meta() == original.get_meta()

    def test_cut_slice(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
        maxdatalen = max(1, File.DEFAULT_DATALEN - 1)
        memory = Memory.from_blocks(blocks)
        original = File.from_memory(memory, maxdatalen=maxdatalen)
        outer = original.copy()
        inner = outer.cut(start=6, endex=12, meta=True)
        assert inner is not original
        assert inner != original
        assert inner._records is None
        assert inner._memory is not original._memory
        assert inner._memory.to_blocks() == [[6, b'bc'], [10, b'xy']]
        assert inner.get_meta() == original.get_meta()
        assert outer is not original
        assert outer != original
        assert outer._records is None
        assert outer._memory is not original._memory
        assert outer._memory.to_blocks() == [[5, b'a'], [12, b'z']]
        assert outer.get_meta() == original.get_meta()

    def test_delete(self):
        File = self.File
        file = File.from_memory(Memory.from_bytes(b'abcxyz', offset=5))
        file._records = []
        assert file._memory.to_blocks() == [[5, b'abcxyz']]
        returned = file.delete(start=7, endex=9)
        assert returned is file
        assert file._memory.to_blocks() == [[5, b'abyz']]
        assert file._records is None

    def test_discard_records(self):
        File = self.File
        file = File.from_memory(Memory.from_bytes(b'abcxyz', offset=5))
        file._records = []
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

    @pytest.mark.skip(reason='TODO')
    def test_discard_records_views(self):
        raise NotImplementedError('TODO')  # TODO:

    def test_discard_memory(self):
        File = self.File
        file = File.from_memory(Memory.from_bytes(b'abcxyz', offset=5))
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

    @pytest.mark.skip(reason='TODO')
    def test_extend(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_fill(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_find(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_flood(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_from_records(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_from_memory(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_get_address_max(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_get_address_min(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_get_holes(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_get_spans(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_get_meta(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_index(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_load(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_maxdatalen_getter(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_maxdatalen_setter(self):
        raise NotImplementedError('TODO')  # TODO:

    def test_memory_getter(self):
        File = self.File
        Record = File.Record
        Tag = Record.Tag
        records = [
            Record(Tag._DATA, address=5, data=b'abc'),
            Record(Tag._DATA, address=10, data=b'xyz'),
        ]
        file = File.from_records(records)
        file._memory = None
        assert file._records is records
        memory = file.memory
        assert memory is file._memory
        assert memory.to_blocks() == [[5, b'abc'], [10, b'xyz']]
        assert file._records is records
        file._records = None
        memory = file.memory
        assert memory is file._memory
        assert memory.to_blocks() == [[5, b'abc'], [10, b'xyz']]
        assert file._records is None

    def test_memory_getter_raises(self):
        File = self.File
        file = File()
        file._records = None
        file._memory = None
        with pytest.raises(ValueError, match='records required'):
            assert file.memory

    def test_merge(self):
        File = self.File
        file1 = File.from_memory(Memory.from_bytes(b'abc', offset=5))
        file2 = File.from_memory(Memory.from_blocks([[10, b'xyz']]))
        result = File.merge(file1, file2)
        assert result is not file1
        assert result is not file2
        assert result != file1
        assert result != file2
        assert result._memory.to_blocks() == [[5, b'abc'], [10, b'xyz']]

    def test_merge_empty(self):
        File = self.File
        result = File.merge()
        assert result._memory.to_blocks() == []

    @abc.abstractmethod
    def test_parse(self):
        ...

    @pytest.mark.skip(reason='TODO')
    def test_print(self):
        raise NotImplementedError('TODO')  # TODO:

    def test_read(self):
        File = self.File

        file = File.from_memory(Memory.from_bytes(b'abcxyz', offset=5))
        assert file.read(start=7, endex=9) == b'cx'
        assert file.read(start=2, endex=14) == b'\0\0\0abcxyz\0\0\0'
        assert file.read(start=2, endex=14, fill=b'.') == b'...abcxyz...'

        blocks = [[5, b'abc'], [10, b'xyz']]
        file = File.from_memory(Memory.from_blocks(blocks))
        assert file.read(fill=b'.') == b'abc..xyz'
        assert file.read() == b'abc\0\0xyz'

    def test_records_getter(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
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

    def test_reverse(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
        expected = [[5, b'zyx'], [10, b'cba']]
        memory = Memory.from_blocks(blocks)
        file = File.from_memory(memory)
        assert file._memory.to_blocks() == blocks
        returned = file.reverse()
        assert returned is file
        actual = file._memory.to_blocks()
        assert actual == expected

    @pytest.mark.skip(reason='TODO')
    def test_save(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_set_meta(self):
        raise NotImplementedError('TODO')  # TODO:

    @pytest.mark.skip(reason='TODO')
    def test_serialize(self):
        raise NotImplementedError('TODO')  # TODO:

    def test_shift(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
        memory = Memory.from_blocks(blocks)
        file = File.from_memory(memory)
        assert file._memory.to_blocks() == blocks
        file.shift(+1)
        assert file._memory.to_blocks() == [[6, b'abc'], [11, b'xyz']]
        file.shift(-1)
        assert file._memory.to_blocks() == blocks

    @pytest.mark.skip(reason='TODO')
    def test_split(self):
        raise NotImplementedError('TODO')  # TODO:

    @abc.abstractmethod
    def test_update_records(self):
        ...

    @abc.abstractmethod
    def test_validate_records(self):
        ...

    def test_view(self):
        File = self.File
        file = File.from_memory(Memory.from_bytes(b'abcxyz', offset=5))
        with file.view() as view:
            assert isinstance(view, memoryview)
            assert view == b'abcxyz'
        with file.view(start=7, endex=9) as view:
            assert isinstance(view, memoryview)
            assert view == b'cx'

    def test_view_raises(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
        memory = Memory.from_blocks(blocks)
        file = File.from_memory(memory)
        with pytest.raises(ValueError, match='non-contiguous'):
            file.view()

    def test_write(self):
        File = self.File
        file = File.from_memory(Memory.from_bytes(b'abc', offset=5))
        assert file._memory.to_blocks() == [[5, b'abc']]
        file.write(10, b'xyz')
        assert file._memory.to_blocks() == [[5, b'abc'], [10, b'xyz']]


# ============================================================================

class FakeTag(BaseTag, enum.IntEnum):

    DATA = 0
    FAKE = -1

    _DATA = DATA


# ----------------------------------------------------------------------------

class FakeRecord(BaseRecord):

    Tag = FakeTag

    def compute_checksum(self) -> int:
        total = 0
        for key in self.EQUALITY_KEYS:
            if key != 'checksum':
                value = getattr(self, key)
                try:
                    value = value.__index__()
                except:
                    value = sum(value)
                total ^= value
        return total

    def compute_count(self) -> int:
        return len(self.data)

    @classmethod
    def create_data(cls, address: int, data: AnyBytes) -> 'BaseRecord':
        return cls(FakeTag.DATA, address=address, data=data)

    def parse(cls, line: AnyBytes, address: int = 0) -> 'FakeRecord':
        return FakeRecord(FakeTag.DATA, address=address, data=line)

    def to_bytestr(self) -> bytes:
        return b''.join(self.to_tokens().values())

    def to_tokens(self) -> Mapping[str, bytes]:
        return {
            'tag': b'%X' % self.tag,
            'address': b'%08X' % self.address,
            'data': hexlify(self.data).upper(),
        }


# ----------------------------------------------------------------------------

class FakeFile(BaseFile):

    Record = FakeRecord

    def update_records(self) -> 'FakeFile':

        if self._memory is None:
            raise ValueError('memory instance required')

        records = []

        for address, view in self._memory.blocks():
            with view:
                data = bytes(view)
                record = FakeRecord(FakeTag.DATA, address=address, data=data)
                records.append(record)

        self.discard_records()
        self._records = records
        return self

    def validate_records(self) -> 'FakeFile':

        if self._records is None:
            raise ValueError('records required')

        for record in self._records:
            record.validate()

        return self


# ============================================================================

class TestFakeTag(BaseTestTag):

    Tag = FakeTag


# ----------------------------------------------------------------------------

class TestFakeRecord(BaseTestRecord):

    Tag = FakeTag
    Record = FakeRecord

    def test_compute_checksum(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'b', after=b'a', coords=(33, 44))
        checksum = record.compute_checksum()
        assert checksum == 4956

    def test_compute_count(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'b', after=b'a', coords=(33, 44))
        count = record.compute_count()
        assert count == 3

    def test_to_bytestr(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'a', after=b'b', coords=(33, 44))
        actual = record.to_bytestr()
        expected = b'00000123478797A'
        assert actual == expected

    def test_to_tokens(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'a', after=b'b', coords=(33, 44))
        actual = record.to_tokens()
        expected = {
            'tag': b'0',
            'address': b'00001234',
            'data': b'78797A',
        }
        assert actual == expected


# ----------------------------------------------------------------------------

class TestFakeFile(BaseTestFile):

    File = FakeFile
