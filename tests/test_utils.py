# -*- coding: utf-8 -*-
from typing import Type

import pytest

from hexrec.utils import *

HEXBYTES = bytes(range(16))


# ============================================================================

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


# ============================================================================

def test_check_empty_args_kwargs():
    check_empty_args_kwargs([], {})
    check_empty_args_kwargs(None, {})
    check_empty_args_kwargs([], None)
    check_empty_args_kwargs(None, None)

    with pytest.raises(ValueError, match='unexpected positional argument'):
        check_empty_args_kwargs([Ellipsis], {})

    with pytest.raises(ValueError, match='unexpected keyword argument'):
        check_empty_args_kwargs([], {'_': Ellipsis})


# ============================================================================

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


# ============================================================================

def test_chop_doctest():
    assert list(chop('ABCDEFG', 2)) == ['AB', 'CD', 'EF', 'G']
    assert ':'.join(chop('ABCDEFG', 2)) == 'AB:CD:EF:G'
    assert list(chop('ABCDEFG', 4, 3)) == ['A', 'BCDE', 'FG']


def test_chop():
    with pytest.raises(ValueError):
        next(chop('ABDEFG', -1))


# ============================================================================

def test_columnize_doctest():
    ans_out = columnize('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 6, sep=' ', window=3)
    ans_ref = 'ABC DEF\nGHI JKL\nMNO PQR\nSTU VWX\nYZ'
    assert ans_out == ans_ref


# ============================================================================

def test_hexlify_doctest():
    ans_out = hexlify(b'Hello, World!', sep='.')
    ans_ref = '48.65.6C.6C.6F.2C.20.57.6F.72.6C.64.21'
    assert ans_out == ans_ref

    ans_out = hexlify(b'Hello, World!', 6, ' ')
    ans_ref = '48 65 6C\n6C 6F 2C\n20 57 6F\n72 6C 64\n21'
    assert ans_out == ans_ref


def test_hexlify():
    bytes_in = HEXBYTES

    sep = ''
    ans_ref = sep.join('{:02x}'.format(b) for b in bytes_in)
    ans_out = hexlify(bytes_in, sep=sep, upper=False)
    assert ans_out == ans_ref

    ans_ref = ans_ref[:16] + '\n' + ans_ref[16:]
    ans_out = hexlify(bytes_in, sep=sep, upper=False, width=16)
    assert ans_out == ans_ref

    ans_ref = sep.join('{:02X}'.format(b) for b in bytes_in)
    ans_out = hexlify(bytes_in, sep=sep, upper=True)
    assert ans_out == ans_ref

    sep = '.'
    ans_ref = sep.join('{:02X}'.format(b) for b in bytes_in)
    ans_out = hexlify(bytes_in, sep=sep, upper=True)
    assert ans_out == ans_ref


# ============================================================================

def test_unhexlify_doctest():
    ans_out = unhexlify('48656C6C 6F2C2057 6F726C64 21')
    ans_ref = b'Hello, World!'
    assert ans_out == ans_ref


def test_unhexlify():
    bytes_ref = HEXBYTES

    str_in = ' '.join('{:02x}'.format(b) for b in bytes_ref)
    assert unhexlify(str_in) == bytes_ref

    str_in = ' '.join('{:02X}'.format(b) for b in bytes_ref)
    assert unhexlify(str_in) == bytes_ref
