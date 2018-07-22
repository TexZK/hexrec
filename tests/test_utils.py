# -*- coding: utf-8 -*-
import pytest

from hexrec.utils import *

# ============================================================================

PARSE_INT_PASS = {
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
    '0b101100111000': 0b101100111000,

    '01234567': 0o1234567,
    '0o1234567': 0o1234567,
    '0O1234567': 0o1234567,

    '1k': 1 << 10,
    '1m': 1 << 20,

    b'123': 123,
    123: 123,
    135.7: 135,
}

PARSE_INT_FAIL = {
    Ellipsis: TypeError,
    'x': ValueError,
    '0b1h': ValueError,
    '0o1h': ValueError,
    (1,): TypeError,
}


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

# ============================================================================

def test_columnize_doctest():
    ans_out = columnize('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 6, sep=' ', window=3)
    ans_ref = 'ABC DEF\nGHI JKL\nMNO PQR\nSTU VWX\nYZ'
    assert ans_out == ans_ref

# ============================================================================

def test_columnize_lists_doctest():
    ans_out = columnize_lists('ABCDEFG', 5, window=2)
    ans_ref = [['AB', 'CD', 'E'], ['FG']]
    assert ans_out == ans_ref

# ============================================================================

def test_bitlify_doctest():
    ans_out = bitlify(b'ABCDEFG', 8*3, sep=' ')
    ans_ref = '01000001 01000010 01000011\n01000100 01000101 01000110\n01000111'
    assert ans_out == ans_ref


def test_bitlify():
    bytes_in = bytes(range(16))

    sep = ''
    str_out = sep.join('{:08b}'.format(b) for b in bytes_in)
    assert bitlify(bytes_in, sep=sep) == str_out

    sep = '.'
    str_out = sep.join('{:08b}'.format(b) for b in bytes_in)
    assert bitlify(bytes_in, sep=sep) == str_out

# ============================================================================

def test_unbitlify_doctest():
    ans_out = unbitlify('010010000110100100100001')
    ans_ref = b'Hi!'
    assert ans_out == ans_ref


def test_unbitlify():
    bytes_out = bytes(range(16))

    str_in = ' '.join('{:08b}'.format(b) for b in bytes_out)
    assert unbitlify(str_in) == bytes_out

# ============================================================================

def test_hexlify_doctest():
    ans_out = hexlify(b'Hello, World!', sep='.')
    ans_ref = '48.65.6C.6C.6F.2C.20.57.6F.72.6C.64.21'
    assert ans_out == ans_ref


def test_hexlify():
    bytes_in = bytes(range(16))

    sep = ''
    str_out = sep.join('{:02x}'.format(b) for b in bytes_in)
    assert hexlify(bytes_in, sep=sep, upper=False) == str_out

    str_out = sep.join('{:02X}'.format(b) for b in bytes_in)
    assert hexlify(bytes_in, sep=sep, upper=True) == str_out

    sep = '.'
    str_out = sep.join('{:02X}'.format(b) for b in bytes_in)
    assert hexlify(bytes_in, sep=sep, upper=True) == str_out

# ============================================================================

def test_unhexlify_doctest():
    ans_out = unhexlify('48656C6C 6F2C2057 6F726C64 21')
    ans_ref = b'Hello, World!'
    assert ans_out == ans_ref


def test_unhexlify():
    bytes_out = bytes(range(16))

    str_in = ' '.join('{:02x}'.format(b) for b in bytes_out)
    assert unhexlify(str_in) == bytes_out

    str_in = ' '.join('{:02X}'.format(b) for b in bytes_out)
    assert unhexlify(str_in) == bytes_out

# ============================================================================

def test_hexlify_lists_doctest():
    pass  # TODO

# ============================================================================

def test_humanize_ascii_doctest():
    ans_out = humanize_ascii(b'\x89PNG\r\n\x1a\n')
    ans_ref = '.PNG....'
    assert ans_out == ans_ref

# ============================================================================

def test_humanize_ebcdic_doctest():
    pass  # TODO

# ============================================================================

def test_bytes_to_c_array_doctest():
    pass  # TODO

# ============================================================================

def test_do_overlap_doctest():
    assert do_overlap(0, 4, 4, 8) == False
    assert do_overlap(0, 4, 2, 6) == True
    assert do_overlap(4, 0, 2, 6) == True
    assert do_overlap(8, 4, 4, 0) == False

# ============================================================================

def test_straighten_slice_doctest():
    assert straighten_slice(3, 5, 1, 7) == (3, 5, 1)
    assert straighten_slice(-3, 5, 1, 7) == (4, 5, 1)
    assert straighten_slice(3, -5, 1, 7) == (3, 2, 1)
    assert straighten_slice(-3, -5, 1, 7) == (4, 2, 1)
