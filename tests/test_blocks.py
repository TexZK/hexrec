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

def test_chop_blocks_doctest():
    ans_out = list(chop_blocks('ABCDEFG', 2, start=10))
    ans_ref = [(10, 'AB'), (12, 'CD'), (14, 'EF'), (16, 'G')]
    assert ans_out == ans_ref

    ans_out = list(chop_blocks('ABCDEFG', 4, 3, 10))
    ans_ref= [(13, 'A'), (14, 'BCDE'), (18, 'FG')]
    assert ans_out == ans_ref

# ============================================================================

def test_overlap_doctest():
    assert overlap((1, 'ABCD'), (5, 'xyz')) == False
    assert overlap((1, 'ABCD'), (3, 'xyz')) == True

# ============================================================================

def test_sequence_doctest():
    assert check_sequence([(1, 'ABC'), (6, 'xyz')]) == True
    assert check_sequence([(1, 'ABC'), (2, 'xyz')]) == False
    assert check_sequence([(6, 'ABC'), (1, 'xyz')]) == False

# ============================================================================

def test_sorting_doctest():
    blocks = [(2, 'ABC'), (7, '>'), (2, '$'), (0, '<'), (2, '11')]
    ans_ref = [(0, '<'), (2, 'ABC'), (2, '$'), (2, '11'), (7, '>')]
    ans_out = list(blocks)
    ans_out.sort(key=sorting)
    assert ans_out == ans_ref

# ============================================================================

def test_locate_at_doctest():
    blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
    ans_ref = [None, 0, 0, 0, 0, None, 1, None, 2, 2, 2, None]
    ans_out = [locate_at(blocks, i) for i in range(12)]
    assert ans_out == ans_ref


def test_locate_at():
    assert locate_at((), 1) is None

# ============================================================================

def test_locate_start_doctest():
    blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
    ans_ref = [0, 0, 0, 0, 0, 1, 1, 2, 2, 2, 2, 3]
    ans_out = [locate_start(blocks, i) for i in range(12)]
    assert ans_out == ans_ref


def test_locate_start():
    assert locate_start((), 1) == 0

# ============================================================================

def test_locate_endex_doctest():
    blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
    ans_ref = [0, 1, 1, 1, 1, 1, 2, 2, 3, 3, 3, 3]
    ans_out = [locate_endex(blocks, i) for i in range(12)]
    assert ans_out == ans_ref


def test_locate_endex():
    assert locate_endex((), 1) == 0

# ============================================================================

def test_shift_doctest():
    blocks = [(1, 'ABCD'), (7, 'xyz')]
    ans_ref = [(0, 'ABCD'), (6, 'xyz')]
    ans_out = shift(blocks, -1)
    assert ans_out == ans_ref

# ============================================================================

def test_read_doctest():
    blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]

    ans_ref = [(3, 'CD'), (6, '$'), (8, 'xy')]
    ans_out = read(blocks, 3, 10, None)
    assert ans_out == ans_ref

    ans_ref = [(3, 'CD'), (5, '#'), (6, '$'), (7, '#'), (8, 'xy')]
    ans_out = read(blocks, 3, 10, '#', ''.join)
    assert ans_out == ans_ref

    ans_ref = [(1, 'ABCD'), (6, '$'), (8, 'xy')]
    ans_out = read(blocks, None, 10, None)
    assert ans_out == ans_ref

    ans_ref = [(3, 'CD'), (6, '$'), (8, 'xyz')]
    ans_out = read(blocks, 3, None, None)
    assert ans_out == ans_ref


def test_read():
    blocks = [(1, 'ABCD')]
    ans_ref = [(2, 'BC')]
    ans_out = read(blocks, 2, 4)
    assert ans_out == ans_ref

    blocks = [(2, 'BC')]
    ans_ref = blocks
    ans_out = read(blocks, None, None)
    assert ans_out == ans_ref

# ============================================================================

def test_clear_doctest():
    blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
    ans_ref = [(1, 'A'), (3, 'C'), (9, 'yz')]
    ans_out = list(blocks)
    ans_out = clear(ans_out, 4, 9)
    ans_out = clear(ans_out, 2, 2)
    ans_out = clear(ans_out, 2, 3)
    assert ans_out == ans_ref


def test_clear():
    blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
    ans_ref = []
    ans_out = clear(blocks, None, None)
    assert ans_out == ans_ref

# ============================================================================

def test_delete_doctest():
    blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
    ans_ref = [(1, 'A'), (2, 'C'), (3, 'yz')]
    ans_out = list(blocks)
    ans_out = delete(ans_out, 4, 9)
    ans_out = delete(ans_out, 2, 2)
    ans_out = delete(ans_out, 2, 3)
    assert ans_out == ans_ref


def test_delete():
    blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
    ans_ref = []
    ans_out = delete(blocks, None, None)
    assert ans_out == ans_ref

# ============================================================================

def test_insert_doctest():
    blocks = [(0, 'ABCD'), (6, 'xyz')]
    ans_ref = [(0, 'A'), (1, '1'), (2, 'BCD'), (7, 'xyz'), (11, '$')]
    ans_out = list(blocks)
    ans_out = insert(ans_out, (10, '$'))
    ans_out = insert(ans_out, (1, '1'))
    assert ans_out == ans_ref


def test_insert():
    blocks = [(0, 'ABCD'), (6, 'xyz')]

    ans_ref = blocks
    ans_out = insert(blocks, (10, ''))
    assert ans_out == ans_ref

    ans_ref = [(0, 'ABCD'), (6, '$'), (7, 'xyz')]
    ans_out = insert(blocks, (6, '$'))
    assert ans_out == ans_ref

# ============================================================================

def test_write_doctest():
    blocks = [(1, 'ABCD'), (6, '$'), (8, 'xy')]
    ans_ref = [(1, 'AB'), (3, '123456'), (9, 'y')]
    ans_out = write(blocks, (3, '123456'))
    assert ans_out == ans_ref


def test_write():
    blocks = [(1, 'ABCD'), (6, '$'), (8, 'xy')]
    ans_ref = blocks
    ans_out = write(blocks, (3, ''))
    assert ans_out == ans_ref

# ============================================================================

def test_fill_doctest():
    blocks = [(1, 'ABC'), (6, 'xyz')]

    ans_ref = [(1, 'ABC'), (4, '23'), (6, 'xyz')]
    ans_out = fill(blocks, pattern='123', join=''.join)
    assert ans_out == ans_ref

    ans_ref = [(4, '23')]
    ans_out = fill(blocks, pattern='123', fill_only=True, join=''.join)
    assert ans_out == ans_ref

    ans_ref = [(0, '1'), (1, 'ABC'), (4, '2'), (6, 'xyz')]
    ans_out = fill(blocks, pattern='123', start=0, endex=5, join=''.join)
    assert ans_out == ans_ref

    ans_ref = [(1, 'ABC'), (5, '3'), (6, 'xyz'), (9, '1')]
    ans_out = fill(blocks, pattern='123', start=5, endex=10, join=''.join)
    assert ans_out == ans_ref


def test_fill():
    with pytest.raises(ValueError): fill([])

    blocks = [(1, 'ABC'), (6, 'xyz')]

    ans_ref = blocks
    ans_out = fill(blocks, start=5, endex=5, join=''.join)
    assert ans_out == ans_ref

    ans_ref = [(1, 'ABC'), (4, '##'), (6, 'xyz')]
    ans_out = fill(blocks, pattern=('#' * 64), join=''.join)
    assert ans_out == ans_ref

# ============================================================================

def test_merge_doctest():
    blocks = [(0, 'Hello,'), (6, ' '), (7, 'World'), (12, '!')]
    ans_ref = [(0, 'Hello, World!')]
    ans_out = merge(blocks, join=''.join)
    assert ans_out == ans_ref


def test_merge():
    blocks = [(0, 'Hello,'), (7, 'World')]
    ans_ref = blocks
    ans_out = merge(blocks, join=''.join)
    assert ans_out == ans_ref

# ============================================================================

def test_collapse_doctest():
    blocks = [
        (0, '0123456789'),
        (0, 'ABCD'),
        (3, 'EF'),
        (0, '$'),
        (6, 'xyz'),
    ]
    ans_ref = [(5, '5'), (1, 'BC'), (3, 'EF'), (0, '$'), (9, '9'), (6, 'xyz')]
    ans_out = collapse(blocks)
    assert ans_out == ans_ref


def test_collapse():
    blocks = [
        (0, ''),
        (0, 'ABCD'),
        (3, ''),
        (1, '$'),
    ]
    ans_ref = [(0, 'A'), (2, 'CD'), (1, '$')]
    ans_out = collapse(blocks)
    assert ans_out == ans_ref

# ============================================================================

class TestSparseItems(object):  # TODO

    def test___init__(self):
        obj = SparseItems(items_type=str, items_join=''.join)
        assert obj.blocks == []
        assert obj.items_type == str
        assert obj.items_join == ''.join
        assert obj.autofill is None
        assert obj.automerge == True

        with pytest.raises(ValueError):
            SparseItems(items='ABC', blocks=[(0, 'abc')],
                        items_type=str, items_join=''.join)

        obj = SparseItems(items='ABC', start=1,
                          items_type=str, items_join=''.join)
        assert obj.blocks == [(1, 'ABC')]

        obj = SparseItems(blocks=[(1, 'ABC')], automerge=False,
                          items_type=str, items_join=''.join)
        assert obj.blocks == [(1, 'ABC')]

    def test___str__(self):
        obj = SparseItems(items_type=str, items_join=''.join)
        obj.blocks = [(1, 'ABC'), (7, 'xyz')]
        ans_out = str(obj)
        ans_ref= 'ABCxyz'
        assert ans_out == ans_ref

    def test___bool__(self):
        obj = SparseItems(items_type=str, items_join=''.join)
        assert bool(obj) == False

        obj.blocks = [(1, 'ABC')]
        assert bool(obj) == True

    def test___eq__(self):
        obj1 = SparseItems(items_type=str, items_join=''.join)
        obj1.blocks = [(1, 'ABC'), (7, 'xyz')]
        obj2 = SparseItems()
        obj2.blocks = [(1, 'ABC'), (7, 'xyz')]
        assert obj1 == obj2

        blocks2 = [(1, 'ABC'), (7, 'xyz')]
        assert obj1 == blocks2

        obj1 = SparseItems(items_type=str, items_join=''.join)
        obj1.blocks = [(0, 'ABC')]
        assert obj1 == 'ABC'

        obj1 = SparseItems(items_type=str, items_join=''.join)
        obj1.blocks = [(0, 'ABC'), (7, 'xyz')]
        assert (obj1 == 'ABC') == False

    def test___iter__(self):
        obj = SparseItems(items_type=str, items_join=''.join)
        obj.blocks = [(1, 'ABC'), (7, 'xyz')]
        ans_out = list(obj)
        ans_ref = list('ABCxyz')
        assert ans_out == ans_ref

    def test___reversed__(self):
        obj = SparseItems(items_type=str, items_join=''.join)
        obj.blocks = [(1, 'ABC'), (7, 'xyz')]
        ans_out = list(reversed(obj))
        ans_ref = list(reversed('ABCxyz'))
        assert ans_out == ans_ref

    def test___in__(self):
        obj = SparseItems(items_type=str, items_join=''.join)
        obj.blocks = [(1, 'ABC'), (7, 'xyz')]
        assert 'B' in obj

    def test___add__(self):
        obj1 = SparseItems(items_type=str, items_join=''.join)
        obj1.blocks = [(1, 'ABC'), (5, '$')]

        obj2 = obj1 + obj1
        assert obj2.blocks == [(1, 'ABC'), (5, '$'), (7, 'ABC'), (11, '$')]

        obj2 = obj1 + 'xyz'
        assert obj2.blocks == [(1, 'ABC'), (5, '$xyz')]

    def test___iadd__(self):
        obj = SparseItems(items_type=str, items_join=''.join, automerge=False)
        obj += 'ABC'
        assert obj.blocks == [(0, 'ABC')]

        obj = SparseItems(items_type=str, items_join=''.join)
        obj += [(1, 'ABC'), (5, '$')]
        assert obj.blocks == [(1, 'ABC'), (5, '$')]

        obj = SparseItems(items_type=str, items_join=''.join)
        obj.blocks = [(1, 'ABC'), (5, '$')]
        obj += obj
        assert obj.blocks == [(1, 'ABC'), (5, '$'), (7, 'ABC'), (11, '$')]

        obj = SparseItems(items_type=str, items_join=''.join)
        obj.blocks = [(1, 'ABC'), (5, '$')]
        obj += 'xyz'
        assert obj.blocks == [(1, 'ABC'), (5, '$xyz')]

    def test__mul__(self):
        obj1 = SparseItems(items_type=str, items_join=''.join)
        obj1.blocks = [(1, 'ABC'), (5, '$')]
        obj2 = obj1 * 3
        ans_out = obj2.blocks
        ans_ref = [(1, 'ABC'), (5, '$ABC'), (10, '$ABC'), (15, '$')]
        assert ans_out == ans_ref

    def test___imul__(self):
        obj = SparseItems(items_type=str, items_join=''.join)
        obj.blocks = [(1, 'ABC'), (5, '$')]
        obj *= 3
        ans_out = obj.blocks
        ans_ref = [(1, 'ABC'), (5, '$ABC'), (10, '$ABC'), (15, '$')]
        assert ans_out == ans_ref

        obj = SparseItems(items_type=str, items_join=''.join, automerge=False)
        obj.blocks = [(1, 'ABC'), (5, '$')]
        obj *= 3
        ans_out = obj.blocks
        ans_ref = [(1, 'ABC'), (5, '$'),
                   (6, 'ABC'), (10, '$'),
                   (11, 'ABC'), (15, '$')]
        assert ans_out == ans_ref

    def test_index(self):
        obj = SparseItems(items_type=str, items_join=''.join)
        obj.blocks = [(1, 'ABC'), (7, 'xyz'), (11, 'ABC')]
        assert obj.index('B') == 2
        assert obj.index('y') == 8
        with pytest.raises(ValueError): obj.index('$')

    def test___contains___doctest(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        memory.blocks = [(1, 'ABC'), (5, '123'), (9, 'xyz')]
        assert ('23' in memory) == True
        assert ('y' in memory) == True
        assert ('$' in memory) == False

    def test_count_doctest(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        memory.blocks = [(1, 'ABC'), (7, 'Bat'), (12, 'tab')]
        assert memory.count('a') == 2

    def test_count(self):
        obj = SparseItems(items_type=str, items_join=''.join)
        obj.blocks = [(1, 'ABC'), (7, 'xyz'), (11, 'ABC')]
        assert obj.count('B') == 2
        assert obj.count('y') == 1
        assert obj.count('$') == 0

    def test___getitem___doctest(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        assert memory[9] == 'y'
        assert memory[-2] == 'y'
        assert memory[:3] == 'AB'
        assert memory[-2:] == 'yz'
        with pytest.raises(ValueError): memory[3:10]

        assert memory[3:10:'.'] == 'CD.$.xy'

        assert memory[memory.endex] == ''

    def test___getitem__(self):
        memory = SparseItems(items_type=str, items_join=''.join, autofill='.')
        memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        assert memory[3:10] == 'CD.$.xy'

    def test___setitem___doctest(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        memory.blocks = [(5, 'ABC'), (9, 'xyz')]
        memory[7:10] = None
        assert memory.blocks == [(5, 'AB'), (10, 'yz')]
        memory[7] = 'C'
        memory[-3] = 'x'
        assert memory.blocks == [(5, 'ABC'), (9, 'xyz')]

        memory = SparseItems(items_type=str, items_join=''.join,
                             automerge=False)
        memory.blocks = [(5, 'ABC'), (9, 'xyz')]
        memory[0:4] = '$'
        ans_out = memory.blocks
        ans_ref = [(0, '$'), (2, 'ABC'), (6, 'xyz')]
        assert ans_out == ans_ref

        memory[4:7] = '45678'
        ans_out = memory.blocks
        ans_ref = [(0, '$'), (2, 'AB'), (4, '456'), (7, '78'), (9, 'yz')]
        assert ans_out == ans_ref

        memory[6:8] = '<>'
        ans_out = memory.blocks
        ans_ref = [(0, '$'), (2, 'AB'), (4, '45'), (6, '<>'), (8, '8'),
                   (9, 'yz')]
        assert ans_out == ans_ref

    def test___setitem__(self):
        memory = SparseItems(items='ABC', items_type=str, items_join=''.join)
        memory[1] = None
        assert memory.blocks == [(0, 'A'), (2, 'C')]
        with pytest.raises(ValueError): memory[0] = 'xyz'

    def test___delitem___doctest(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        del memory[4:9]
        assert memory.blocks == [(1, 'ABCyz')]

        memory = SparseItems(items_type=str, items_join=''.join,
                             automerge=False)
        memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        del memory[4:9]
        assert memory.blocks == [(1, 'ABC'), (4, 'yz')]

        memory = SparseItems(items_type=str, items_join=''.join)
        memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        del memory[-2]
        assert memory.blocks == [(1, 'ABCD'), (6, '$'), (8, 'xz')]
        del memory[3]
        assert memory.blocks == [(1, 'ABD'), (5, '$'), (7, 'xz')]

    def test_append_doctest(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        memory.append('$')
        assert memory.blocks == [(0, '$')]

        memory = SparseItems(items_type=list, items_join=''.join)
        memory.append(3)
        assert memory.blocks == [(0, 3)]

    def test_extend(self):
        obj = SparseItems(items_type=str, items_join=''.join, automerge=False)
        obj.extend('ABC')
        assert obj.blocks == [(0, 'ABC')]

    def test_shift(self):
        obj = SparseItems(items_type=str, items_join=''.join)
        obj.blocks = [(1, 'ABC'), (7, 'xyz')]
        obj.shift(3)
        assert obj.blocks == [(4, 'ABC'), (10, 'xyz')]

    def test_find_doctest(self):
        blocks = [(1, 'ABCD'), (7, 'xyz')]
        assert find(blocks, 'yz', -1, 15) == 8
        with pytest.raises(ValueError): find(blocks, '$')

    def test__read(self):
        obj = SparseItems(items_type=str, items_join=''.join)
        obj.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        assert obj.read(3, 10, '.') == 'CD.$.xy'

    def test_clear_doctest(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        memory.blocks = [(5, 'ABC'), (9, 'xyz')]
        memory.clear(memory.index('B'), memory.index('y'))
        assert memory.blocks == [(5, 'A'), (10, 'yz')]

    def test_clear(self):
        obj = SparseItems(items_type=str, items_join=''.join, automerge=False)
        obj.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        obj.clear(3, 10)
        assert obj.blocks == [(1, 'AB'), (10, 'z')]

    def test_delete_doctest(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        memory.blocks = [(5, 'ABC'), (9, 'xyz')]
        memory.delete(memory.index('B'), memory.index('y'))
        assert memory.blocks == [(5, 'Ayz')]

    def test_delete(self):
        obj = SparseItems(items_type=str, items_join=''.join)
        obj.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        obj.delete(3, 10)
        assert obj.blocks == [(1, 'ABz')]

    def test_pop_doctest(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        memory.blocks = [(5, 'ABC'), (9, 'xyz')]
        assert memory.pop(6) == 'B'
        assert memory.blocks == [(5, 'AC'), (8, 'xyz')]
        assert memory.pop(-2) == 'y'
        assert memory.blocks == [(5, 'AC'), (8, 'xz')]
        assert memory.pop() == 'z'
        assert memory.blocks == [(5, 'AC'), (8, 'x')]
        assert memory.pop(7) == ''
        assert memory.blocks == [(5, 'ACx')]

    def test_pop(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        with pytest.raises(IndexError): memory.pop()

    def test_remove_doctest(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        memory.blocks = [(1, 'ABC'), (5, '123'), (9, 'xyz')]
        memory.remove('23')
        assert memory.blocks == [(1, 'ABC'), (5, '1'), (7, 'xyz')]
        memory.remove('y')
        assert memory.blocks == [(1, 'ABC'), (5, '1'), (7, 'xz')]
        with pytest.raises(ValueError): memory.remove('$')

    def test_insert_doctest(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        memory.blocks = [(1, 'ABC'), (6, 'xyz')]
        memory.insert(5, '123')
        assert memory.blocks == [(1, 'ABC'), (5, '123'), (9, 'xyz')]

    def test_insert(self):
        obj = SparseItems(items_type=str, items_join=''.join)
        obj.blocks = [(1, 'ABCD'), (7, 'xyz')]
        obj.insert(7, '$')
        assert obj.blocks == [(1, 'ABCD'), (7, '$xyz')]

        obj = SparseItems(items_type=str, items_join=''.join, automerge=False)
        obj.blocks = [(1, 'ABCD'), (7, 'xyz')]
        obj.insert(6, '$')
        assert obj.blocks == [(1, 'ABCD'), (6, '$'), (8, 'xyz')]

    def test_write_doctest(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        memory.blocks = [(1, 'ABC'), (6, 'xyz')]
        memory.write(5, '123')
        assert memory.blocks == [(1, 'ABC'), (5, '123z')]

    def test_write(self):
        obj = SparseItems(items_type=str, items_join=''.join)
        obj.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xy')]
        obj.write(3, '123456')
        assert obj.blocks == [(1, 'AB123456y')]

        obj = SparseItems(items_type=str, items_join=''.join, automerge=False)
        obj.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xy')]
        obj.write(3, '123456')
        ans_out = obj.blocks
        ans_ref = [(1, 'AB'), (3, '123456'), (9, 'y')]
        assert ans_out == ans_ref

    def test_fill_doctest(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        memory.blocks = [(1, 'ABC'), (6, 'xyz')]
        memory.fill(pattern='123')
        assert memory.blocks == [(1, 'ABC23xyz')]

        memory = SparseItems(items_type=str, items_join=''.join,
                             autofill='123')
        memory.blocks = [(1, 'ABC'), (6, 'xyz')]
        memory.fill()
        assert memory.blocks == [(1, 'ABC23xyz')]

    def test_fill(self):
        obj = SparseItems(items_type=str, items_join=''.join)
        obj.blocks = [(1, 'ABC'), (6, 'xyz')]
        obj.fill(pattern='123')
        ans_out = obj.blocks
        ans_ref = [(1, 'ABC23xyz')]
        assert ans_out == ans_ref

        obj = SparseItems(items_type=str, items_join=''.join, automerge=False)
        obj.blocks = [(1, 'ABC'), (6, 'xyz')]
        obj.fill(pattern='123')
        ans_out = obj.blocks
        ans_ref = [(1, 'ABC'), (4, '23'), (6, 'xyz')]
        assert ans_out == ans_ref

    def test_merge_doctest(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        memory.blocks = [(1, 'ABC'), (4, 'xyz')]
        memory.merge()
        ans_out = memory.blocks
        ans_ref = [(1, 'ABCxyz')]
        assert ans_out == ans_ref

    def test_reverse_doctest(self):
        memory = SparseItems(items_type=str, items_join=''.join)
        memory.blocks = [(1, 'ABC'), (5, '$'), (9, 'xyz')]
        memory.reverse()
        assert memory.blocks == [(0, 'zyx'), (6, '$'), (8, 'CBA')]
