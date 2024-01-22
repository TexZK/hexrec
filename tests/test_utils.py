# -*- coding: utf-8 -*-
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

    '1k': 1 << 10,
    '1m': 1 << 20,

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


def test_parse_int_doctest():
    assert parse_int('-0xABk') == -175104
    assert parse_int(None) is None
    assert parse_int(123) == 123
    assert parse_int(135.7) == 135


def test_parse_int_pass():
    for value_in, value_out in PARSE_INT_PASS.items():
        assert parse_int(value_in) == value_out


def test_parse_int_fail():
    for value_in, raised_exception in PARSE_INT_FAIL.items():
        with pytest.raises(raised_exception):
            parse_int(value_in)


def test_hexlify():
    bytes_in = HEXBYTES

    ans_ref = b''.join((b'%02x' % b) for b in bytes_in)
    ans_out = hexlify(bytes_in, upper=False)
    assert ans_out == ans_ref

    ans_ref = b''.join((b'%02X' % b) for b in bytes_in)
    ans_out = hexlify(bytes_in, upper=True)
    assert ans_out == ans_ref


def test_unhexlify():
    bytes_ref = HEXBYTES

    bytes_in = b' '.join((b'%02x' % b) for b in bytes_ref)
    assert unhexlify(bytes_in) == bytes_ref

    bytes_in = b' '.join((b'%02X' % b) for b in bytes_ref)
    assert unhexlify(bytes_in) == bytes_ref

    ans_out = unhexlify(b'48656C6C 6F2C2057 6F726C64 21')
    ans_ref = b'Hello, World!'
    assert ans_out == ans_ref
