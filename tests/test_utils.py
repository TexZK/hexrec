# -*- coding: utf-8 -*-
import pytest
import six

from hexrec.utils import *

HEXBYTES = bytes(bytearray(range(16)))

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
    for value_in, value_out in six.iteritems(PARSE_INT_PASS):
        assert parse_int(value_in) == value_out


def test_parse_int_fail():
    for value_in, raised_exception in six.iteritems(PARSE_INT_FAIL):
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
    bytes_in = HEXBYTES

    sep = ''
    ans_ref = sep.join('{:08b}'.format(b) for b in six.iterbytes(bytes_in))
    assert bitlify(bytes_in, sep=sep) == ans_ref

    sep = '.'
    ans_ref = sep.join('{:08b}'.format(b) for b in six.iterbytes(bytes_in))
    assert bitlify(bytes_in, sep=sep) == ans_ref

# ============================================================================

def test_unbitlify_doctest():
    ans_out = unbitlify('010010000110100100100001')
    ans_ref = b'Hi!'
    assert ans_out == ans_ref


def test_unbitlify():
    bytes_ref = HEXBYTES

    str_in = ' '.join('{:08b}'.format(b) for b in six.iterbytes(bytes_ref))
    assert unbitlify(str_in) == bytes_ref

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
    ans_ref = sep.join('{:02x}'.format(b) for b in six.iterbytes(bytes_in))
    ans_out = hexlify(bytes_in, sep=sep, upper=False)
    assert ans_out == ans_ref

    ans_ref = ans_ref[:16] + '\n' + ans_ref[16:]
    ans_out = hexlify(bytes_in, sep=sep, upper=False, width=16)
    assert ans_out == ans_ref

    ans_ref = sep.join('{:02X}'.format(b) for b in six.iterbytes(bytes_in))
    ans_out = hexlify(bytes_in, sep=sep, upper=True)
    assert ans_out == ans_ref

    sep = '.'
    ans_ref = sep.join('{:02X}'.format(b) for b in six.iterbytes(bytes_in))
    ans_out = hexlify(bytes_in, sep=sep, upper=True)
    assert ans_out == ans_ref

# ============================================================================

def test_unhexlify_doctest():
    ans_out = unhexlify('48656C6C 6F2C2057 6F726C64 21')
    ans_ref = b'Hello, World!'
    assert ans_out == ans_ref


def test_unhexlify():
    bytes_ref = HEXBYTES

    str_in = ' '.join('{:02x}'.format(b) for b in six.iterbytes(bytes_ref))
    assert unhexlify(str_in) == bytes_ref

    str_in = ' '.join('{:02X}'.format(b) for b in six.iterbytes(bytes_ref))
    assert unhexlify(str_in) == bytes_ref

# ============================================================================

def test_hexlify_lists():
    bytes_in = HEXBYTES

    ans_ref = [['{:02x}'.format(b) for b in six.iterbytes(bytes_in)]]
    ans_out = hexlify_lists(bytes_in, upper=False)
    assert ans_out == ans_ref

    ans_ref = ['{:02x}'.format(b) for b in six.iterbytes(bytes_in)]
    ans_ref = [ans_ref[:8], ans_ref[8:]]
    ans_out = hexlify_lists(bytes_in, upper=False, width=16)
    assert ans_out == ans_ref

    ans_ref = [['{:02X}'.format(b) for b in six.iterbytes(bytes_in)]]
    ans_out = hexlify_lists(bytes_in, upper=True)
    assert ans_out == ans_ref

# ============================================================================

def test_humanize_ascii_doctest():
    bytes_in = b'\x89PNG\r\n\x1a\n'
    ans_out = humanize_ascii(bytes_in)
    ans_ref = '.PNG....'
    assert ans_out == ans_ref

# ============================================================================

def test_humanize_ebcdic_doctest():
    bytes_in = bytearray(range(0xC0, 0xD0))
    ans_out = humanize_ebcdic(bytes_in)
    ans_ref = '{ABCDEFGHI......'
    assert ans_out == ans_ref

# ============================================================================

def test_sum_bytes_doctest():
    assert sum_bytes(bytes(bytearray(range(16)))) == 120
    assert sum_bytes(range(16)) == 120

# ============================================================================

def test_do_overlap_doctest():
    assert do_overlap(0, 4, 4, 8) == False
    assert do_overlap(0, 4, 2, 6) == True
    assert do_overlap(4, 0, 2, 6) == True
    assert do_overlap(8, 4, 4, 0) == False

# ============================================================================

def test_straighten_index_doctest():
    assert straighten_index(3, 7) == 3
    assert straighten_index(-3, 7) == 4
    assert straighten_index(9, 7) == 9
    assert straighten_index(-8, 7) == 6
    assert straighten_index(None, 3) is None
    assert straighten_index(3, None) == 0

# ============================================================================

def test_straighten_slice_doctest():
    assert straighten_slice(3, 5, 1, 7) == (3, 5, 1)
    assert straighten_slice(-3, 5, 1, 7) == (4, 5, 1)
    assert straighten_slice(3, -5, 1, 7) == (3, 2, 1)
    assert straighten_slice(-3, -5, 1, 7) == (4, 2, 1)
    assert straighten_slice(None, 5, 1, 7) == (0, 5, 1)
    assert straighten_slice(3, None, 1, 7) == (3, 7, 1)
    assert straighten_slice(3, 5, None, 7) == (3, 5, None)
    assert straighten_slice(3, 5, 1, None) == (0, 0, 1)

# ============================================================================

def test_wrap_index_doctest():
    assert wrap_index(3, 7) == 3
    assert wrap_index(-3, 7) == 4
    assert wrap_index(9, 7) == 2
    assert wrap_index(-8, 7) == 6
    assert wrap_index(None, 3) == 0
    assert wrap_index(3, None) == 0

# ============================================================================

def test_wrap_slice_doctest():
    assert wrap_slice(3, 5, 1, 7) == (3, 5, 1)
    assert wrap_slice(-3, 5, 1, 7) == (4, 5, 1)
    assert wrap_slice(3, -5, 1, 7) == (3, 2, 1)
    assert wrap_slice(-3, -5, 1, 7) == (4, 2, 1)
    assert wrap_slice(None, 5, 1, 7) == (0, 5, 1)
    assert wrap_slice(3, None, 1, 7) == (3, 7, 1)
    assert wrap_slice(3, 5, None, 7) == (3, 5, 1)
    assert wrap_slice(3, 5, 1, None) == (0, 0, 1)

# ============================================================================

def test_makefill_doctest():
    assert makefill(b'0123456789ABCDEF', 0, 8) == b'01234567'
    assert makefill(b'0123456789ABCDEF', 8, 16) == b'89ABCDEF'

    ans_out = makefill(b'0123456789ABCDEF', 4, 44)
    ans_ref = b'456789ABCDEF0123456789ABCDEF0123456789AB'
    assert ans_out == ans_ref


def test_makefill():
    with pytest.raises(ValueError):
        makefill(b'', 0, 8)

    with pytest.raises(ValueError):
        makefill(b'0123456789ABCDEF', 8, 0)

    with pytest.raises(ValueError):
        makefill(b'0123456789ABCDEF', -1, 8)

    with pytest.raises(ValueError):
        makefill(b'0123456789ABCDEF', 0, -8)
