from typing import Any
from typing import Mapping
from typing import Type

import pytest
from bytesparse import Memory

from hexrec.utils import SparseMemoryIO
from hexrec.utils import chop
from hexrec.utils import hexlify
from hexrec.utils import parse_int
from hexrec.utils import unhexlify

PARSE_INT_PASS: Mapping[Any, int] = {
    None: None,

    '123': 123,
    ' 123 ': 123,
    '\t123\t': 123,
    '+123': 123,
    '-123': -123,
    ' +123 ': 123,
    ' -123 ': -123,
    ' + 123 ': 123,
    ' - 123 ': -123,

    '0xDEADBEEF': 0xDEADBEEF,
    '0XDEADBEEF': 0xDEADBEEF,
    'DEADBEEFh': 0xDEADBEEF,
    'DEADBEEFH': 0xDEADBEEF,

    '0b101100111000': 0b101100111000,

    '01234567': 0o1234567,
    '0o1234567': 0o1234567,
    '0O1234567': 0o1234567,

    '1k': 2**10,
    '1M': 2**20,
    '1 G': 2**30,

    '1KiB': 2**10,
    '1 mib': 2**20,
    '1GiB': 2**30,

    '1 KB': 10**3,
    '1MB': 10**6,
    '1gb': 10**9,

    b'456': 456,
    123: 123,
    135.7: 135,
}

PARSE_INT_FAIL: Mapping[Any, Type[BaseException]] = {
    Ellipsis: TypeError,
    'x': ValueError,
    '0b1h': ValueError,
    '0o1h': ValueError,
    (1,): TypeError,
}


def test_chop():
    with pytest.raises(ValueError):
        next(chop(b'ABDEFG', -1))


def test_chop_doctest():
    assert list(chop(b'ABCDEFG', 2)) == [b'AB', b'CD', b'EF', b'G']
    assert b':'.join(chop(b'ABCDEFG', 2)) == b'AB:CD:EF:G'
    assert list(chop(b'ABCDEFG', 4, 3)) == [b'A', b'BCDE', b'FG']


def test_hexlify_doctest():
    ans_out = hexlify(b'\xAA\xBB\xCC')
    ans_ref = b'AABBCC'
    assert ans_out == ans_ref

    ans_out = hexlify(b'\xAA\xBB\xCC', sep=b' ')
    ans_ref = b'AA BB CC'
    assert ans_out == ans_ref

    ans_out = hexlify(b'\xAA\xBB\xCC', sep=b'-')
    ans_ref = b'AA-BB-CC'
    assert ans_out == ans_ref

    ans_out = hexlify(b'\xAA\xBB\xCC', upper=False)
    ans_ref = b'aabbcc'
    assert ans_out == ans_ref


def test_parse_int_doctest():
    assert parse_int('-0xABk') == -175104
    assert parse_int(None) is None
    assert parse_int(123) == 123
    assert parse_int(135.7) == 135


def test_parse_int_fail():
    for value_in, raised_exception in PARSE_INT_FAIL.items():
        with pytest.raises(raised_exception):
            parse_int(value_in)


def test_parse_int_pass():
    for value_in, value_out in PARSE_INT_PASS.items():
        assert parse_int(value_in) == value_out


def test_unhexlify_doctest():
    ans_out = unhexlify(b'AABBCC')
    ans_ref = b'\xaa\xbb\xcc'
    assert ans_out == ans_ref

    ans_out = unhexlify(b'AA BB CC', delete=...)
    ans_ref = b'\xaa\xbb\xcc'
    assert ans_out == ans_ref

    ans_out = unhexlify(b'AA-BB-CC', delete=...)
    ans_ref = b'\xaa\xbb\xcc'
    assert ans_out == ans_ref

    ans_out = unhexlify(b'AA/BB/CC', delete=b'/')
    ans_ref = b'\xaa\xbb\xcc'
    assert ans_out == ans_ref


class TestSparseMemoryIO:

    def test_read_after(self):
        stream = SparseMemoryIO(Memory.from_bytes(b'\xAA\xBB\xCC'))
        actual = stream.read(5)
        assert actual == [0xAA, 0xBB, 0xCC, 0x102, 0x102]

    def test_read_before(self):
        stream = SparseMemoryIO(Memory.from_bytes(b'\xAA\xBB\xCC', offset=2))
        actual = stream.read()
        assert actual == [0x101, 0x101, 0xAA, 0xBB, 0xCC]

    def test_read_contiguous(self):
        stream = SparseMemoryIO(Memory.from_bytes(b'abc'))
        actual = stream.read()
        assert actual == b'abc'

    def test_read_empty(self):
        stream = SparseMemoryIO(Memory())
        actual = stream.read()
        assert actual == b''

    def test_read_hole(self):
        blocks = [[0, b'\xAA\xBB\xCC'], [5, b'\xEE\xFF']]
        stream = SparseMemoryIO(Memory.from_blocks(blocks))
        actual = stream.read()
        assert actual == [0xAA, 0xBB, 0xCC, 0x100, 0x100, 0xEE, 0xFF]

    def test_read_raises_asmemview(self):
        stream = SparseMemoryIO(Memory())
        with pytest.raises(ValueError, match='memory view not supported'):
            stream.read(asmemview=True)

    def test_write_bytes(self):
        memory = Memory()
        stream = SparseMemoryIO(memory)
        stream.write(b'abc')
        assert memory.to_blocks() == [[0, b'abc']]

    def test_write_empty(self):
        memory = Memory()
        stream = SparseMemoryIO(memory)
        stream.write([])
        assert memory.to_blocks() == []

    def test_write_hole(self):
        memory = Memory()
        stream = SparseMemoryIO(memory)
        stream.write([0xAA, 0xBB, 0xCC, 0x100, 0x100, 0xEE, 0xFF])
        expected = [[0, b'\xAA\xBB\xCC'], [5, b'\xEE\xFF']]
        assert memory.to_blocks() == expected
