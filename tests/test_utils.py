from typing import Type

import pytest

from hexrec.utils import *

HEXBYTES = bytes(range(16))


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
