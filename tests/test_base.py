import abc
import io
import os
import sys
from pathlib import Path
from typing import IO
from typing import Any
from typing import Optional
from typing import Union
from typing import cast as _cast

import pytest
from bytesparse import Memory

import hexrec.base as _hr
from hexrec.base import AnyBytes
from hexrec.base import BaseFile
from hexrec.base import BaseRecord
from hexrec.base import BaseTag
from hexrec.base import colorize_tokens
from hexrec.base import convert
from hexrec.base import guess_format_name
from hexrec.base import guess_format_type
from hexrec.base import load
from hexrec.base import merge
from hexrec.formats.ihex import IhexFile
from hexrec.formats.srec import SrecFile


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


@pytest.fixture
def fake_token_color_codes(request):
    backup = _hr.TOKEN_COLOR_CODES
    _hr.TOKEN_COLOR_CODES = {key: (b'[%s]' % key.encode()) for key in backup}
    yield
    _hr.TOKEN_COLOR_CODES = backup


@pytest.fixture
def fake_file_types(request):
    backup = _hr.file_types
    _hr.file_types = dict(backup)

    class FakeFile(SrecFile):
        FILE_EXT = list(SrecFile.FILE_EXT) + ['.hex', '.dat']

    _hr.file_types['_fake_'] = FakeFile
    yield
    _hr.file_types = backup


class replace_stdin:

    def __init__(self, stream: IO):
        self.buffer = stream
        self.original = sys.stdin

    def __enter__(self):
        sys.stdin = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdin = self.original


class replace_stdout:

    def __init__(self, stream: Optional[IO] = None):
        if stream is None:
            stream = io.StringIO()
        self.buffer = stream
        self.original = sys.stdout
        self.write = stream.write

    def __enter__(self):
        sys.stdout = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original

    def assert_normalized(self, expected: Union[str, AnyBytes]):  # pragma: no cover
        if isinstance(self.buffer, io.StringIO):
            actual = ''.join(self.buffer.getvalue().split())
        else:
            actual = _cast(io.BytesIO, self.buffer)
            actual = b''.join(actual.getvalue().split())

        if isinstance(expected, str):
            expected = ''.join(expected.split())
        else:
            expected = b''.join(expected.split())

        assert actual == expected


def test_colorize_tokens_altdata(fake_token_color_codes):

    tokens = {
        '':         b'(empty)',
        '<':        b'(stx)',
        '>':        b'(etx)',
        'address':  b'(address)',
        'addrlen':  b'(addrlen)',
        'after':    b'(after)',
        'before':   b'(before)',
        'begin':    b'(begin)',
        'checksum': b'(checksum)',
        'count':    b'(count)',
        'data':     b'AABBCCD',
        'end':      b'(end)',
        'tag':      b'(tag)',
    }
    expected = {
        '':         b'[](empty)',
        '<':        b'[<](stx)',
        '>':        b'[>](etx)',
        'address':  b'[address](address)',
        'addrlen':  b'[addrlen](addrlen)',
        'after':    b'[after](after)',
        'before':   b'[before](before)',
        'begin':    b'[begin](begin)',
        'checksum': b'[checksum](checksum)',
        'count':    b'[count](count)',
        'data':     b'[data]AA[dataalt]BB[data]CC[dataalt]D',
        'end':      b'[end](end)',
        'tag':      b'[tag](tag)',
    }
    actual = colorize_tokens(tokens, altdata=True)
    assert actual == expected


def test_colorize_tokens_plaindata(fake_token_color_codes):

    tokens = {
        '':         b'(empty)',
        '<':        b'(stx)',
        '>':        b'(etx)',
        'address':  b'(address)',
        'addrlen':  b'(addrlen)',
        'after':    b'(after)',
        'before':   b'(before)',
        'begin':    b'(begin)',
        'checksum': b'(checksum)',
        'count':    b'(count)',
        'data':     b'AABBCCD',
        'end':      b'(end)',
        'tag':      b'(tag)',
    }
    expected = {
        '':         b'[](empty)',
        '<':        b'[<](stx)',
        '>':        b'[>](etx)',
        'address':  b'[address](address)',
        'addrlen':  b'[addrlen](addrlen)',
        'after':    b'[after](after)',
        'before':   b'[before](before)',
        'begin':    b'[begin](begin)',
        'checksum': b'[checksum](checksum)',
        'count':    b'[count](count)',
        'data':     b'[data]AABBCCD',
        'end':      b'[end](end)',
        'tag':      b'[tag](tag)',
    }
    actual = colorize_tokens(tokens, altdata=False)
    assert actual == expected


def test_convert(datapath, tmppath):
    in_path = str(datapath / 'simple.hex')
    out_path = str(tmppath / 'simple.srec')
    ref_path = str(datapath / 'simple.srec')
    in_file, out_file = convert(in_path, out_path)
    assert in_file is not out_file
    assert in_file.memory is not out_file.memory
    blocks = [[0x1234, b'abc'], [0xABCD5678, b'xyz']]
    assert in_file.memory.to_blocks() == blocks
    assert out_file.memory.to_blocks() == blocks
    with open(out_path, 'rb') as out_stream:
        out_content = out_stream.read()
    with open(ref_path, 'rb') as ref_stream:
        ref_content = ref_stream.read()
    assert out_content == ref_content


def test_convert_out_format(datapath, tmppath):
    in_path = str(datapath / 'simple.hex')
    out_path = str(tmppath / 'simple.srec')
    ref_path = str(datapath / 'simple.srec')
    in_file, out_file = convert(in_path, out_path, in_format='ihex', out_format='srec')
    assert in_file is not out_file
    assert in_file.memory is not out_file.memory
    blocks = [[0x1234, b'abc'], [0xABCD5678, b'xyz']]
    assert in_file.memory.to_blocks() == blocks
    assert out_file.memory.to_blocks() == blocks
    with open(out_path, 'rb') as out_stream:
        out_content = out_stream.read()
    with open(ref_path, 'rb') as ref_stream:
        ref_content = ref_stream.read()
    assert out_content == ref_content


def test_guess_format_name():
    vector = [
        ('ihex', 'example.hex'),
        ('srec', 'example.srec'),
    ]
    for expected, path in vector:
        actual = guess_format_name(path)
        assert actual == expected


def test_guess_format_name_hex(fake_file_types, datapath):
    path = str(datapath / 'simple.hex')
    name = guess_format_name(path)
    assert name == 'ihex'


def test_guess_format_name_raw(fake_file_types, datapath):
    path = str(datapath / 'data.dat')
    name = guess_format_name(path)
    assert name == 'raw'


def test_guess_format_name_raises_missing():
    with pytest.raises(ValueError, match='extension not found'):
        guess_format_name('file._some_unexisting_extension_')


def test_guess_format_type():
    vector = [
        (IhexFile, 'example.hex'),
        (SrecFile, 'example.srec'),
    ]
    for expected, path in vector:
        actual = guess_format_type(path)
        assert actual is expected


def test_load(datapath):
    IhexRecord = IhexFile.Record
    in_path = str(datapath / 'simple.hex')
    records = [
        IhexRecord.create_data(0x1234, b'abc'),
        IhexRecord.create_extended_linear_address(0xABCD),
        IhexRecord.create_data(0x5678, b'xyz'),
        IhexRecord.create_start_linear_address(0xABCD5678),
        IhexRecord.create_end_of_file(),
    ]
    in_file = load(in_path)
    assert in_file.records == records


def test_load_in_format(datapath):
    IhexRecord = IhexFile.Record
    in_path = str(datapath / 'simple.hex')
    records = [
        IhexRecord.create_data(0x1234, b'abc'),
        IhexRecord.create_extended_linear_address(0xABCD),
        IhexRecord.create_data(0x5678, b'xyz'),
        IhexRecord.create_start_linear_address(0xABCD5678),
        IhexRecord.create_end_of_file(),
    ]
    in_file = load(in_path, in_format='ihex')
    assert in_file.records == records


def test_load_stream(datapath):
    SrecRecord = SrecFile.Record
    SrecTag = SrecRecord.Tag
    in_path = str(datapath / 'simple.srec')
    records = [
        SrecRecord.create_header(),
        SrecRecord.create_data(0x00001234, b'abc', tag=SrecTag.DATA_32),
        SrecRecord.create_data(0xABCD5678, b'xyz', tag=SrecTag.DATA_32),
        SrecRecord.create_count(2, tag=SrecTag.COUNT_16),
        SrecRecord.create_start(0xABCD5678, tag=SrecTag.START_32),
    ]
    with open(in_path, 'rb') as in_stream:
        in_file = load(in_stream)
    assert in_file.records == records


def test_load_none(datapath):
    SrecRecord = SrecFile.Record
    SrecTag = SrecRecord.Tag
    in_path = str(datapath / 'simple.srec')
    records = [
        SrecRecord.create_header(),
        SrecRecord.create_data(0x00001234, b'abc', tag=SrecTag.DATA_32),
        SrecRecord.create_data(0xABCD5678, b'xyz', tag=SrecTag.DATA_32),
        SrecRecord.create_count(2, tag=SrecTag.COUNT_16),
        SrecRecord.create_start(0xABCD5678, tag=SrecTag.START_32),
    ]
    with open(in_path, 'rb') as in_stream:
        with replace_stdin(in_stream):
            in_file = load(None)
    assert in_file.records == records


def test_load_wrong_extension(datapath):
    vector = [
        (IhexFile, 'simple_hex.srec'),
        (SrecFile, 'simple_srec.hex'),
    ]
    for expected, path in vector:
        in_path = str(datapath / path)
        in_file = load(in_path)
        assert type(in_file) is expected


def test_load_cannot_guess_file(datapath):
    with pytest.raises(Exception):
        in_path = str(datapath / 'missing.file')
        load(in_path)


def test_load_cannot_guess_stream():
    in_stream = io.BufferedWriter(io.BytesIO(b''))
    assert not in_stream.readable()
    with pytest.raises(Exception):
        load(in_stream)


def test_merge(datapath, tmppath):
    in_paths = [
        str(datapath / 'data.dat'),
        str(datapath / 'simple.hex'),
    ]
    out_path = str(tmppath / 'merged.xtek')
    ref_path = str(datapath / 'merged.xtek')
    in_files, out_file = merge(in_paths, out_path)
    out_blocks = [
        [0, b'first\nsecond\n'],
        [0x1234, b'abc'],
        [0xABCD5678, b'xyz'],
    ]
    assert out_file.memory.to_blocks() == out_blocks
    for in_file in in_files:
        assert in_file is not out_file
        assert in_file.memory is not out_file.memory
        assert in_file.memory != out_file.memory
    with open(out_path, 'rb') as out_stream:
        out_content = out_stream.read()
    with open(ref_path, 'rb') as ref_stream:
        ref_content = ref_stream.read()
    assert out_content == ref_content


def test_merge_formats(datapath, tmppath):
    in_paths = [
        str(datapath / 'data.dat'),
        str(datapath / 'simple.hex'),
    ]
    out_path = str(tmppath / 'merged.xtek')
    ref_path = str(datapath / 'merged.xtek')
    in_formats = ['raw', 'ihex']
    out_format = 'xtek'
    in_files, out_file = merge(in_paths, out_path,
                               in_formats=in_formats,
                               out_format=out_format)
    out_blocks = [
        [0, b'first\nsecond\n'],
        [0x1234, b'abc'],
        [0xABCD5678, b'xyz'],
    ]
    assert out_file.memory.to_blocks() == out_blocks
    for in_file in in_files:
        assert in_file is not out_file
        assert in_file.memory is not out_file.memory
        assert in_file.memory != out_file.memory
    with open(out_path, 'rb') as out_stream:
        out_content = out_stream.read()
    with open(ref_path, 'rb') as ref_stream:
        ref_content = ref_stream.read()
    assert out_content == ref_content


def test_merge_out_ellipsis(datapath):
    in_paths = [
        str(datapath / 'data.dat'),
        str(datapath / 'simple.hex'),
    ]
    in_formats = ['raw', 'ihex']
    out_format = 'xtek'
    in_files, out_file = merge(in_paths,
                               in_formats=in_formats,
                               out_format=out_format)
    out_blocks = [
        [0, b'first\nsecond\n'],
        [0x1234, b'abc'],
        [0xABCD5678, b'xyz'],
    ]
    assert out_file.memory.to_blocks() == out_blocks
    for in_file in in_files:
        assert in_file is not out_file
        assert in_file.memory is not out_file.memory
        assert in_file.memory != out_file.memory


class BaseTestTag:

    Tag = BaseTag
    Tag_FAKE = _cast(BaseTag, -1)

    @abc.abstractmethod
    def test_is_data(self):
        ...

    @abc.abstractmethod
    def test_is_file_termination(self):
        ...


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
                   before=b'b', after=b'a', coords=(33, 44), validate=False),
            Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                   before=b'?', after=b'a', coords=(33, 44), validate=False),
            Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                   before=b'b', after=b'?', coords=(33, 44), validate=False),
            Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                   before=b'b', after=b'a', coords=(55, 44), validate=False),
            Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                   before=b'b', after=b'a', coords=(33, 66), validate=False),
        ]
        record1 = records[0]
        for record2 in records:
            assert record2 == record1

    def test___init___basic(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'b', after=b'a', coords=(33, 44), validate=False)
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
                        before=b'b', after=b'a', coords=(33, 44), validate=False)
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
                        before=b'b', after=b'a', coords=(33, 44), validate=False)
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
                        before=b'b', after=b'a', coords=(33, 44), validate=False)
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
                        before=b'b', after=b'a', coords=(33, 44), validate=False)
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
                   before=b'b', after=b'a', coords=(33, 44), validate=False),
            Record(Tag._DATA, address=0x4321, data=b'xyz', count=3, checksum=0xA5,
                   before=b'b', after=b'a', coords=(33, 44), validate=False),
            Record(Tag._DATA, address=0x1234, data=b'abc', count=3, checksum=0xA5,
                   before=b'b', after=b'a', coords=(33, 44), validate=False),
            Record(Tag._DATA, address=0x1234, data=b'xyz', count=4, checksum=0xA5,
                   before=b'b', after=b'a', coords=(33, 44), validate=False),
            Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0x5A,
                   before=b'b', after=b'a', coords=(33, 44), validate=False),
        ]
        record1 = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                         before=b'b', after=b'a', coords=(33, 44), validate=False)
        for record2 in records:
            assert record2 != record1

    def test___ne___meta_keys(self):
        Tag = self.Record.Tag
        Record = self.Record
        record1 = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                         before=b'b', after=b'a', coords=(33, 44), validate=False)
        record2 = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                         before=b'b', after=b'a', coords=(33, 44), validate=False)
        delattr(record1, 'data')
        assert record2 != record1

    def test___repr___type(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'', after=b'', coords=(33, 44), validate=False)
        text = repr(record)
        assert isinstance(text, str)
        assert text

    def test___str___type(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'', after=b'', coords=(33, 44), validate=False)
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
                         before=b'b', after=b'a', coords=(33, 44), validate=False)
        record2 = record1.copy(validate=False)
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
                        before=b'b', after=b'a', coords=(33, 44), validate=False)
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
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
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
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=3, checksum=0xA5,
                        before=b'', after=b'', coords=(33, 44), validate=False)
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
                        before=b'b', after=b'a', coords=(33, 44), validate=False)
        assert record.checksum is None
        returned = record.update_checksum()
        assert returned is record
        assert record.checksum == record.compute_checksum()

    def test_update_count(self):
        Tag = self.Record.Tag
        Record = self.Record
        record = Record(Tag._DATA, address=0x1234, data=b'xyz', count=None, checksum=0xA5,
                        before=b'b', after=b'a', coords=(33, 44), validate=False)
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
            Record(Tag._DATA, address=-1, count=0, checksum=0, validate=False),

            Record(Tag._DATA, address=0, count=0, checksum=-1, validate=False),
            Record(Tag._DATA, address=0, count=0, checksum=42, validate=False),

            Record(Tag._DATA, address=0, count=-1, checksum=0, validate=False),
            Record(Tag._DATA, address=0, count=42, checksum=0, validate=False),
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


class BaseTestFile:

    File = BaseFile

    def test___add__(self):
        File = self.File
        file = File.from_bytes(b'abc', offset=5)
        assert file._memory.to_blocks() == [[5, b'abc']]
        result = file + b'xyz'
        assert result is not file
        assert file._memory.to_blocks() == [[5, b'abc']]
        assert result._memory.to_blocks() == [[5, b'abcxyz']]

    def test___bool___(self):
        File = self.File

        file = File()
        assert bool(file) is False
        file.append(0)
        assert bool(file) is True

        file = File.from_records(File().records)
        assert bool(file) is False

        file = File.from_records(File.from_bytes(b'\0').records)
        assert bool(file) is True

    def test___delitem__(self):
        File = self.File
        file = File.from_bytes(b'abcxyz', offset=5)
        assert file._memory.to_blocks() == [[5, b'abcxyz']]
        del file[6]
        assert file._memory.to_blocks() == [[5, b'acxyz']]
        del file[6::2]
        assert file._memory.to_blocks() == [[5, b'axz']]
        del file[:]
        assert file._memory.to_blocks() == []

    def test___getitem__(self):
        File = self.File

        file = File.from_bytes(b'abcxyz', offset=5)
        assert file[6] == ord('b')
        assert file[1] is None
        assert file[7:9] == b'cx'
        assert file[6::2] == b'bxz'

        blocks = [[5, b'abc'], [10, b'xyz']]
        file = File.from_blocks(blocks)
        assert file[::b'.'] == b'abc..xyz'
        with pytest.raises(ValueError, match='non-contiguous'):
            assert file[::]

    def test___eq___false_memory(self):
        File = self.File
        file1 = File.from_bytes(b'abc', offset=5)
        file2 = File.from_blocks([[6, b'abc']])
        assert file1 is not file2
        assert (file1 == file2) is False
        file3 = File.from_blocks([[5, b'xyz']])
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
        file1 = File.from_records([Record.create_data(5, b'abc')])
        file2 = File.from_records([Record.create_data(6, b'abc')])
        assert file1 is not file2
        assert (file1 == file2) is False
        file3 = File.from_records([Record.create_data(5, b'xyz')])
        assert file1 is not file3
        assert (file1 == file3) is False

    def test___eq___raises(self):
        File = self.File
        Record = File.Record
        file1 = File.from_bytes(b'abc', offset=5)
        file2 = File.from_records([Record.create_data(5, b'abc')])
        assert file1 is not file2
        with pytest.raises(ValueError, match='both memory or both records required'):
            assert (file1 == file2) is True

    def test___eq___true_memory(self):
        File = self.File
        file1 = File.from_bytes(b'abc', offset=5)
        file2 = File.from_blocks([[5, b'abc']])
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
        file1 = File.from_records([Record.create_data(5, b'abc')])
        file2 = File.from_records([Record.create_data(5, b'abc')])
        assert file1 is not file2
        assert (file1 == file2) is True

    def test___iadd__(self):
        File = self.File
        file = File.from_bytes(b'abc', offset=5)
        assert file._memory.to_blocks() == [[5, b'abc']]
        original = file
        file += b'xyz'
        assert file is original
        assert file._memory.to_blocks() == [[5, b'abcxyz']]

    def test___ior___(self):
        File = self.File
        file1 = File.from_bytes(b'abc', offset=5)
        file2 = File.from_blocks([[10, b'xyz']])
        original = file1
        file1 |= file2
        assert file1 is original
        assert file1 is not file2
        assert file1 != file2
        assert file1._memory.to_blocks() == [[5, b'abc'], [10, b'xyz']]

    def test___ne___false_memory(self):
        File = self.File
        file1 = File.from_bytes(b'abc', offset=5)
        file2 = File.from_blocks([[5, b'abc']])
        assert file1 is not file2
        assert (file1 != file2) is False

    def test___ne___false_records(self):
        File = self.File
        Record = File.Record
        file1 = File.from_records([Record.create_data(5, b'abc')])
        file2 = File.from_records([Record.create_data(5, b'abc')])
        assert file1 is not file2
        assert (file1 != file2) is False

    def test___ne___raises(self):
        File = self.File
        Record = File.Record
        file1 = File.from_bytes(b'abc', offset=5)
        file2 = File.from_records([Record.create_data(5, b'xyz')])
        assert file1 is not file2
        with pytest.raises(ValueError, match='both memory or both records required'):
            assert (file1 != file2) is True

    def test___ne___true_memory(self):
        File = self.File
        file1 = File.from_bytes(b'abc', offset=5)
        file2 = File.from_blocks([[6, b'abc']])
        assert file1 is not file2
        assert (file1 != file2) is True
        file3 = File.from_blocks([[5, b'xyz']])
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
        file1 = File.from_records([Record.create_data(5, b'abc')])
        file2 = File.from_records([Record.create_data(6, b'abc')])
        assert file1 is not file2
        assert (file1 != file2) is True
        file3 = File.from_records([Record.create_data(5, b'xyz')])
        assert file1 is not file3
        assert (file1 != file3) is True

    def test___or__(self):
        File = self.File
        file1 = File.from_bytes(b'abc', offset=5)
        file2 = File.from_blocks([[10, b'xyz']])
        result = file1 | file2
        assert result is not file1
        assert result is not file2
        assert result != file1
        assert result != file2
        assert result._memory.to_blocks() == [[5, b'abc'], [10, b'xyz']]

    def test___setitem__(self):
        File = self.File
        file = File.from_bytes(b'abcxyz', offset=5)
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

    def test_align(self):
        File = self.File
        file = File.from_blocks([[123, b'abc'], [134, b'xyz']])
        returned = file.align(4, pattern=b'.')
        assert returned is file
        assert file._memory.to_blocks() == [[120, b'...abc..'], [132, b'..xyz...']]
        assert file._records is None

    def test_append(self):
        File = self.File
        file = File.from_bytes(b'abc', offset=5)
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
        file = File.from_bytes(b'abcxyz', offset=5)
        returned = file.clear(start=7, endex=9)
        assert returned is file
        assert file._memory.to_blocks() == [[5, b'ab'], [9, b'yz']]
        assert file._records is None

    def test_convert_meta(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
        maxdatalen = max(1, File.DEFAULT_DATALEN - 1)
        original = File.from_blocks(blocks, maxdatalen=maxdatalen)
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
        original = File.from_blocks(blocks, maxdatalen=maxdatalen)
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
        original = File.from_blocks(blocks, maxdatalen=maxdatalen)
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
        original = File.from_blocks(blocks, maxdatalen=maxdatalen)
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
        original = File.from_blocks(blocks, maxdatalen=maxdatalen)
        copied = original.copy(start=6, endex=12, meta=True)
        assert copied is not original
        assert copied != original
        assert copied._records is None
        assert copied._memory is not original._memory
        assert copied._memory.to_blocks() == [[6, b'bc'], [10, b'xy']]
        assert copied.get_meta() == original.get_meta()

    def test_crop(self):
        File = self.File
        file = File.from_bytes(b'abcxyz', offset=5)
        returned = file.crop(start=7, endex=9)
        assert returned is file
        assert file._memory.to_blocks() == [[7, b'cx']]
        assert file._records is None

    def test_cut_meta(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
        maxdatalen = max(1, File.DEFAULT_DATALEN - 1)
        original = File.from_blocks(blocks, maxdatalen=maxdatalen)
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
        original = File.from_blocks(blocks, maxdatalen=maxdatalen)
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
        original = File.from_blocks(blocks, maxdatalen=maxdatalen)
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
        file = File.from_bytes(b'abcxyz', offset=5)
        returned = file.delete(start=7, endex=9)
        assert returned is file
        assert file._memory.to_blocks() == [[5, b'abyz']]
        assert file._records is None

    def test_discard_records(self):
        File = self.File
        file = File.from_bytes(b'abcxyz', offset=5)

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
        file = File.from_bytes(b'abcxyz', offset=5)

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

    def test_extend(self):
        File = self.File
        file = File.from_bytes(b'abc', offset=5)
        returned = file.extend(b'xyz')
        assert returned is file
        assert file._memory.to_blocks() == [[5, b'abcxyz']]
        assert file._records is None

    def test_extend_file(self):
        File = self.File
        file = File.from_bytes(b'abc', offset=5)
        more = File.from_bytes(b'xyz')
        returned = file.extend(more)
        assert returned is file
        assert file._memory.to_blocks() == [[5, b'abcxyz']]
        assert file._records is None

    def test_fill(self):
        File = self.File
        file = File.from_bytes(b'abcxyz', offset=5)
        returned = file.fill(start=7, endex=9, pattern=b'.')
        assert returned is file
        assert file._memory.to_blocks() == [[5, b'ab..yz']]
        assert file._records is None

    def test_find(self):
        File = self.File
        file = File.from_blocks([[5, b'abc'], [10, b'xyz']])
        assert file.find(b'bc') == 6
        assert file.find(b'y') == 11
        assert file.find(ord('y')) == 11
        assert file.find(b'?') < 0

    def test_flood(self):
        File = self.File
        file = File.from_blocks([[5, b'ab'], [9, b'yz']])
        returned = file.flood(pattern=b'.')
        assert returned is file
        assert file._memory.to_blocks() == [[5, b'ab..yz']]
        assert file._records is None

    def test_from_blocks(self):
        File = self.File
        blocks = [
            [123, b'abc'],
            [456, b'xyz'],
        ]
        file = File.from_blocks(blocks)
        assert file._memory.to_blocks() == blocks

    def test_from_bytes(self):
        File = self.File
        file = File.from_bytes(b'abc', offset=5)
        assert file is not None
        assert isinstance(file, BaseFile)
        assert file._memory.to_blocks() == [[5, b'abc']]

    def test_from_memory(self):
        File = self.File
        blocks = [
            [123, b'abc'],
            [456, b'xyz'],
        ]
        memory = Memory.from_blocks(blocks)
        file = File.from_memory(memory, maxdatalen=9)
        assert file is not None
        assert isinstance(file, BaseFile)
        assert file._records is None
        assert file._memory is memory
        assert file._maxdatalen == 9

    def test_from_memory_raises_invalid_meta(self):
        File = self.File
        with pytest.raises(KeyError, match='invalid meta'):
            File.from_memory(maxdatalen=9, _this_is_an_unknown_meta_key_=...)

    def test_from_records(self):
        File = self.File
        Record = File.Record
        records = [
            Record.create_data(123, b'abc'),
            Record.create_data(456, b'xyz'),
        ]
        file = File.from_records(records)
        assert file is not None
        assert isinstance(file, BaseFile)
        assert file._records is records
        assert file._memory is None
        assert file.maxdatalen == 3

    def test_from_records_maxdatalen(self):
        File = self.File
        Record = File.Record
        records = [
            Record.create_data(123, b'abc'),
            Record.create_data(456, b'xyz'),
        ]
        file = File.from_records(records, maxdatalen=7)
        assert file is not None
        assert isinstance(file, BaseFile)
        assert file._records is records
        assert file._memory is None
        assert file.maxdatalen == 7

    def test_from_records_raises_maxdatalen(self):
        File = self.File
        with pytest.raises(ValueError, match='invalid maximum data length'):
            File.from_records([], maxdatalen=0)

    def test_get_address_max(self):
        File = self.File
        file = File()
        assert file.get_address_max() == -1
        file = File.from_blocks([[5, b'abc'], [10, b'xyz']])
        assert file.get_address_max() == 12

    def test_get_address_min(self):
        File = self.File
        file = File()
        assert file.get_address_min() == 0
        file = File.from_blocks([[5, b'abc'], [10, b'xyz']])
        assert file.get_address_min() == 5

    def test_get_holes(self):
        File = self.File
        blocks = [
            [5, b'abc'],
            [10, b'xyz'],
            [20, b'?'],
        ]
        expected = [
            (8, 10),
            (13, 20),
        ]
        file = File.from_blocks(blocks)
        actual = file.get_holes()
        assert actual == expected

    def test_get_spans(self):
        File = self.File
        blocks = [
            [5, b'abc'],
            [10, b'xyz'],
            [20, b'?'],
        ]
        expected = [
            (5, 8),
            (10, 13),
            (20, 21),
        ]
        file = File.from_blocks(blocks)
        actual = file.get_spans()
        assert actual == expected

    def test_get_meta(self):
        File = self.File
        file = File.from_memory(maxdatalen=9)
        meta = file.get_meta()
        assert meta
        assert meta['maxdatalen'] == 9

    def test_index(self):
        File = self.File
        file = File.from_blocks([[5, b'abc'], [10, b'xyz']])
        assert file.index(b'bc') == 6
        assert file.index(b'y') == 11
        assert file.index(ord('y')) == 11
        with pytest.raises(ValueError, match='not found'):
            file.index(b'?')

    @abc.abstractmethod
    def test_load_file(self, datapath):
        ...

    @abc.abstractmethod
    def test_load_stdin(self):
        ...

    def test_maxdatalen_getter(self):
        File = self.File
        file = File.from_memory(maxdatalen=9)
        assert file._maxdatalen == 9
        assert file.maxdatalen == 9

    def test_maxdatalen_setter(self):
        File = self.File
        file = File.from_memory(maxdatalen=9)
        assert file._maxdatalen == 9
        file.maxdatalen = 7
        assert file._maxdatalen == 7

    def test_maxdatalen_setter_raises(self):
        File = self.File
        with pytest.raises(ValueError, match='invalid maximum data length'):
            File.from_memory(maxdatalen=-1)

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
        file1 = File.from_bytes(b'abc', offset=5)
        file2 = File.from_blocks([[10, b'xyz']])
        merged = File()
        result = merged.merge(file1, file2)
        assert result is merged
        assert result is not file1
        assert result is not file2
        assert result != file1
        assert result != file2
        assert result._memory.to_blocks() == [[5, b'abc'], [10, b'xyz']]

    @abc.abstractmethod
    def test_parse(self):
        ...

    def test_print(self):
        File = self.File
        file = File.from_bytes(b'abc')
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
        file = File.from_bytes(b'abc')
        stream_plain = io.BytesIO()
        with replace_stdout(stream_plain):
            returned = file.print(stream=None, color=False)
            assert returned is file
        buffer_plain = stream_plain.getvalue()
        assert len(buffer_plain) > 0

    def test_read(self):
        File = self.File

        file = File.from_bytes(b'abcxyz', offset=5)
        assert file.read(start=7, endex=9) == b'cx'
        assert file.read(start=2, endex=14) == b'\0\0\0abcxyz\0\0\0'
        assert file.read(start=2, endex=14, fill=b'.') == b'...abcxyz...'

        blocks = [[5, b'abc'], [10, b'xyz']]
        file = File.from_blocks(blocks)
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

    @abc.abstractmethod
    def test_save_file(self, tmppath):
        ...

    @abc.abstractmethod
    def test_save_stdout(self):
        ...

    def test_set_meta(self):
        File = self.File
        file = File.from_memory(maxdatalen=9)
        assert file._maxdatalen == 9
        returned = file.set_meta(dict(maxdatalen=7))
        assert returned is file
        assert file._maxdatalen == 7

    def test_set_meta_raises_strict(self):
        File = self.File
        file = File()
        assert not hasattr(file, 'this_is_an_unknown_meta_')
        with pytest.raises(KeyError, match='unknown meta'):
            file.set_meta(dict(this_is_an_unknown_meta_='something'), strict=True)

    def test_set_meta_strict(self):
        File = self.File
        file = File()
        assert not hasattr(file, 'this_is_an_unknown_meta_')
        returned = file.set_meta(dict(this_is_an_unknown_meta_='something'), strict=False)
        assert returned is file
        file = _cast(Any, file)
        assert file.this_is_an_unknown_meta_ == 'something'

    def test_serialize(self):
        File = self.File
        file = File.from_bytes(b'abc')
        file.update_records()
        stream = io.BytesIO()
        returned = file.serialize(stream)
        assert returned is file
        actual = stream.getvalue()
        expected = b''.join(r.to_bytestr() for r in file._records)
        assert actual == expected

    def test_shift(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
        file = File.from_blocks(blocks)
        assert file._memory.to_blocks() == blocks
        file.shift(+1)
        assert file._memory.to_blocks() == [[6, b'abc'], [11, b'xyz']]
        file.shift(-1)
        assert file._memory.to_blocks() == blocks

    def test_split(self):
        File = self.File
        file = File.from_bytes(b'abcxyz?!', offset=5)
        parts = file.split(8, 11)
        assert len(parts) == 3
        assert parts[0]._memory.to_blocks() == [[5, b'abc']]
        assert parts[1]._memory.to_blocks() == [[8, b'xyz']]
        assert parts[2]._memory.to_blocks() == [[11, b'?!']]

    def test_split_meta(self):
        File = self.File
        file = File.from_bytes(b'abcxyz?!', offset=5, maxdatalen=7)
        parts = file.split(8, 11)
        assert len(parts) == 3
        assert parts[0]._memory.to_blocks() == [[5, b'abc']]
        assert parts[1]._memory.to_blocks() == [[8, b'xyz']]
        assert parts[2]._memory.to_blocks() == [[11, b'?!']]
        for part in parts:
            assert part._maxdatalen == 7

    def test_split_unsorted(self):
        File = self.File
        file = File.from_bytes(b'abcxyz?!', offset=5)
        parts = file.split(11, 8)
        assert len(parts) == 3
        assert parts[0]._memory.to_blocks() == [[5, b'abc']]
        assert parts[1]._memory.to_blocks() == [[8, b'xyz']]
        assert parts[2]._memory.to_blocks() == [[11, b'?!']]

    @abc.abstractmethod
    def test_update_records(self):
        ...

    @abc.abstractmethod
    def test_validate_records(self):
        ...

    def test_view(self):
        File = self.File
        file = File.from_bytes(b'abcxyz', offset=5)
        with file.view() as view:
            assert isinstance(view, memoryview)
            assert view == b'abcxyz'
        with file.view(start=7, endex=9) as view:
            assert isinstance(view, memoryview)
            assert view == b'cx'

    def test_view_raises(self):
        File = self.File
        blocks = [[5, b'abc'], [10, b'xyz']]
        file = File.from_blocks(blocks)
        with pytest.raises(ValueError, match='non-contiguous'):
            file.view()

    def test_write(self):
        File = self.File
        file = File.from_bytes(b'abc', offset=5)
        assert file._memory.to_blocks() == [[5, b'abc']]
        file.write(10, b'xyz')
        assert file._memory.to_blocks() == [[5, b'abc'], [10, b'xyz']]

    def test_write_file(self):
        File = self.File
        file = File.from_bytes(b'abc', offset=5)
        assert file._memory.to_blocks() == [[5, b'abc']]
        more = File.from_bytes(b'xyz', offset=10)
        file.write(0, more)
        assert file._memory.to_blocks() == [[5, b'abc'], [10, b'xyz']]
