# -*- coding: utf-8 -*-
import pytest

from hexrec.blocks import *

TEST_STRING = ' [] [] [.] | [...]  [.][.]|[.]|| '

# ============================================================================

def build_blocks(string):
    blocks = []
    offset = 0
    start = None

    for c in string:
        if c in ' ':
            pass

        elif c == '|':
            blocks.append((offset, c))

        elif c == '[':
            start = offset

        elif c == ']':
            blocks.append((start, string[start:(offset + 1)]))

        offset += 1

    return blocks


@pytest.fixture(scope='module')
def blocks():
    return build_blocks(TEST_STRING)


def test_build_blocks(blocks):
    ans_ref = [
        (1, '[]'),
        (4, '[]'),
        (7, '[.]'),
        (11, '|'),
        (13, '[...]'),
        (20, '[.]'),
        (23, '[.]'),
        (26, '|'),
        (27, '[.]'),
        (30, '|'),
        (31, '|')
    ]
    assert blocks == ans_ref

# ============================================================================

def test_overlap_doctest():
    assert overlap((1, 'ABCD'), (5, 'xyz')) == False
    assert overlap((1, 'ABCD'), (3, 'xyz')) == True

# ============================================================================

def test_sorting_doctest():
    blocks = [(2, 'ABC'), (7, '>'), (2, '!'), (0, '<'), (2, '11')]
    ans_ref = [(0, '<'), (2, 'ABC'), (2, '!'), (2, '11'), (7, '>')]
    ans_out = list(blocks)
    ans_out.sort(key=sorting)
    assert ans_out == ans_ref

# ============================================================================

def test_locate_at_doctest():
    blocks = [(1, 'ABCD'), (6, '!'), (8, 'xyz')]
    ans_ref = [None, 0, 0, 0, 0, None, 1, None, 2, 2, 2, None]
    ans_out = [locate_at(blocks, i) for i in range(12)]
    assert ans_out == ans_ref

# ============================================================================

def test_locate_start_doctest():
    blocks = [(1, 'ABCD'), (6, '!'), (8, 'xyz')]
    ans_ref = [0, 0, 0, 0, 0, 1, 1, 2, 2, 2, 2, 3]
    ans_out = [locate_start(blocks, i) for i in range(12)]
    assert ans_out == ans_ref

# ============================================================================

def test_locate_endex_doctest():
    blocks = [(1, 'ABCD'), (6, '!'), (8, 'xyz')]
    ans_ref = [0, 1, 1, 1, 1, 1, 2, 2, 3, 3, 3, 3]
    ans_out = [locate_endex(blocks, i) for i in range(12)]
    assert ans_out == ans_ref

# ============================================================================

def test_shift_doctest():
    blocks = [(1, 'ABCD'), (7, 'xyz')]
    ans_ref = [(0, 'ABCD'), (6, 'xyz')]
    ans_out = shift(blocks, -1)
    assert ans_out == ans_ref

# ============================================================================

def test_select_doctest():
    blocks = [(1, 'ABCD'), (6, '!'), (8, 'xyz')]
    ans_ref = [(3, 'CD'), (6, '!'), (8, 'xy')]
    ans_out = select(blocks, 3, 10)
    assert ans_out == ans_ref

# ============================================================================

def test_clear_doctest():
    blocks = [(1, 'ABCD'), (6, '!'), (8, 'xyz')]
    ans_ref = [(1, 'A'), (3, 'C'), (9, 'yz')]
    ans_out = list(blocks)
    ans_out = clear(ans_out, 4, 9)
    ans_out = clear(ans_out, 2, 2)
    ans_out = clear(ans_out, 2, 3)
    assert ans_out == ans_ref

# ============================================================================

def test_delete_doctest():
    blocks = [(1, 'ABCD'), (6, '!'), (8, 'xyz')]
    ans_ref = [(1, 'A'), (2, 'C'), (3, 'yz')]
    ans_out = list(blocks)
    ans_out = delete(ans_out, 4, 9)
    ans_out = delete(ans_out, 2, 2)
    ans_out = delete(ans_out, 2, 3)
    assert ans_out == ans_ref

# ============================================================================

def test_insert_doctest():
    blocks = [(0, 'ABCD'), (6, 'xyz')]
    ans_ref = [(0, 'A'), (1, '1'), (2, 'BCD'), (7, 'xyz'), (11, '!')]
    ans_out = list(blocks)
    ans_out = insert(ans_out, (10, '!'))
    ans_out = insert(ans_out, (1, '1'))
    assert ans_out == ans_ref

# ============================================================================

def test_write_doctest():
    blocks = [(1, 'ABCD'), (6, '!'), (8, 'xy')]
    ans_ref = [(1, 'AB'), (3, '123456'), (9, 'y')]
    ans_out = write(blocks, (3, '123456'))
    assert ans_out == ans_ref

# ============================================================================

def test_merge_doctest():
    blocks = [(0, 'Hello,'), (6, ' '), (7, 'World'), (12, '!')]
    ans_ref = [(0, 'Hello, World!')]
    ans_out = merge(blocks)
    assert ans_out == ans_ref

# ============================================================================

def test_collapse():
    blocks = [
        (0, '0123456789'),
        (0, 'ABCD'),
        (3, 'EF'),
        (0, '!'),
        (6, 'xyz'),
    ]
    ans_ref = [(5, '5'), (1, 'BC'), (3, 'EF'), (0, '!'), (9, '9'), (6, 'xyz')]
    ans_out = collapse(blocks)
    assert ans_out == ans_ref

# ============================================================================

class TestSparseItems(object):  # TODO

    def test__init__(self):
        obj = SparseItems()
        assert obj.blocks == []
        assert obj.automerge == True
        assert obj.items_type == str
        assert obj.items_join == ''.join

    def test__bool__(self):
        obj = SparseItems()
        assert bool(obj) == False

        obj.blocks = [(1, 'ABC')]
        assert bool(obj) == True

    def test__eq__(self):
        obj1 = SparseItems()
        obj1.blocks = [(1, 'ABC'), (5, '!')]
        obj2 = SparseItems()
        obj2.blocks = [(1, 'ABC'), (5, '!')]
        assert obj1 == obj2

        blocks2 = [(1, 'ABC'), (5, '!')]
        assert obj1 == blocks2

        obj1 = SparseItems()
        obj1.blocks = [(0, 'ABC')]
        assert obj1 == 'ABC'

    def test__iter__(self):
        obj = SparseItems()
        obj.blocks = [(1, 'ABC'), (5, '!')]
        ans_out = list(obj)
        ans_ref = list('ABC!')
        assert ans_out == ans_ref

    def test__reversed__(self):
        obj = SparseItems()
        obj.blocks = [(1, 'ABC'), (5, '!')]
        ans_out = list(reversed(obj))
        ans_ref = list(reversed('ABC!'))
        assert ans_out == ans_ref

    def test__in__(self):
        obj = SparseItems()
        obj.blocks = [(1, 'ABC'), (5, '!')]
        assert 'B' in obj

    def test__add__(self):
        obj1 = SparseItems()
        obj1.blocks = [(1, 'ABC'), (5, '!')]

        obj2 = obj1 + obj1
        assert obj2.blocks == [(1, 'ABC'), (5, '!ABC'), (10, '!')]

        obj2 = obj1 + 'xyz'
        assert obj2.blocks == [(1, 'ABC'), (5, '!xyz')]

    def test__iadd__(self):
        obj = SparseItems()
        obj.blocks = [(1, 'ABC'), (5, '!')]
        obj += obj
        assert obj.blocks == [(1, 'ABC'), (5, '!ABC'), (10, '!')]

        obj = SparseItems()
        obj.blocks = [(1, 'ABC'), (5, '!')]
        obj += 'xyz'
        assert obj.blocks == [(1, 'ABC'), (5, '!xyz')]
