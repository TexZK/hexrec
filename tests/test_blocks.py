# -*- coding: utf-8 -*-
import pytest

from hexrec.blocks import *

# ============================================================================


def test_chop_blocks_doctest():
    ans_out = list(chop_blocks('ABCDEFG', 2, start=10))
    ans_ref = [(10, 'AB'), (12, 'CD'), (14, 'EF'), (16, 'G')]
    assert ans_out == ans_ref

    ans_out = list(chop_blocks('ABCDEFG', 4, 3, 10))
    ans_ref = [(13, 'A'), (14, 'BCDE'), (18, 'FG')]
    assert ans_out == ans_ref


# ============================================================================

def test_overlap_doctest():
    assert not overlap((1, 'ABCD'), (5, 'xyz'))
    assert overlap((1, 'ABCD'), (3, 'xyz'))


# ============================================================================

def test_sequence_doctest():
    assert check_sequence([(1, 'ABC'), (6, 'xyz')])
    assert not check_sequence([(1, 'ABC'), (2, 'xyz')])
    assert not check_sequence([(6, 'ABC'), (1, 'xyz')])


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

    ans_ref = []
    ans_out = read(blocks, 5, 6, None)
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

    assert read(blocks, 3, -3) == []
    assert read([], None, None) == []
    assert read([], 3, None) == []
    assert read([], None, 3) == []


# ============================================================================

def test_crop_doctest():
    blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]

    ans_ref = [(3, 'CD'), (6, '$'), (8, 'xy')]
    ans_out = crop(blocks, 3, 10, None)
    assert ans_out == ans_ref

    ans_ref = [(3, 'CD'), (5, '#'), (6, '$'), (7, '#'), (8, 'xy')]
    ans_out = crop(blocks, 3, 10, '#', ''.join)
    assert ans_out == ans_ref

    ans_ref = [(1, 'ABCD'), (6, '$'), (8, 'xy')]
    ans_out = crop(blocks, None, 10, None)
    assert ans_out == ans_ref

    ans_ref = [(3, 'CD'), (6, '$'), (8, 'xyz')]
    ans_out = crop(blocks, 3, None, None)
    assert ans_out == ans_ref

    ans_ref = []
    ans_out = crop(blocks, 5, 6, None)
    assert ans_out == ans_ref


def test_crop():
    blocks = [(1, 'ABCD')]
    ans_ref = [(2, 'BC')]
    ans_out = crop(blocks, 2, 4)
    assert ans_out == ans_ref

    blocks = [(2, 'BC')]
    ans_ref = blocks
    ans_out = crop(blocks, None, None)
    assert ans_out == ans_ref

    assert crop(blocks, 3, -3) == []
    assert crop([], None, None) == []
    assert crop([], 3, None) == []
    assert crop([], None, 3) == []


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

    assert clear(blocks, 3, -3) == blocks
    assert clear([], None, None) == []
    assert clear([], 3, None) == []
    assert clear([], None, 3) == []


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

def test_reserve_doctest():
    blocks = [(0, 'ABCD'), (6, 'xyz')]
    ans_ref = [(0, 'ABCD'), (6, 'xy'), (9, 'z')]
    ans_out = list(blocks)
    ans_out = reserve(ans_out, 10, 1)
    ans_out = reserve(ans_out, 8, 1)
    assert ans_out == ans_ref


def test_reserve():
    blocks = [(0, 'ABCD'), (6, 'xyz')]

    ans_ref = blocks
    ans_out = reserve(blocks, 10, 0)
    assert ans_out == ans_ref

    ans_ref = [(0, 'ABCD'), (7, 'xyz')]
    ans_out = reserve(blocks, 6, 1)
    assert ans_out == ans_ref


# ============================================================================

def test_insert_doctest():
    blocks = [(0, 'ABCD'), (6, 'xyz')]
    ans_ref = [(0, 'ABCD'), (6, 'xy'), (8, '1'), (9, 'z'), (11, '$')]
    ans_out = list(blocks)
    ans_out = insert(ans_out, (10, '$'))
    ans_out = insert(ans_out, (8, '1'))
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

    ans_ref = [(1, '12312312')]
    ans_out = fill(blocks, pattern='123', join=''.join)
    assert ans_out == ans_ref

    ans_ref = [(0, '12312'), (6, 'xyz')]
    ans_out = fill(blocks, pattern='123', start=0, endex=5, join=''.join)
    assert ans_out == ans_ref

    ans_ref = [(1, 'ABC'), (5, '12312')]
    ans_out = fill(blocks, pattern='123', start=5, endex=10, join=''.join)
    assert ans_out == ans_ref


def test_fill():
    with pytest.raises(ValueError):
        fill([])

    blocks = [(1, 'ABC'), (6, 'xyz')]

    ans_ref = blocks
    ans_out = fill(blocks, start=5, endex=5, join=''.join)
    assert ans_out == ans_ref

    ans_ref = [(1, '########')]
    ans_out = fill(blocks, pattern=('#' * 64), join=''.join)
    assert ans_out == ans_ref


# ============================================================================

def test_flood_doctest():
    blocks = [(1, 'ABC'), (6, 'xyz')]

    ans_ref = [(1, 'ABC'), (4, '12'), (6, 'xyz')]
    ans_out = flood(blocks, pattern='123', join=''.join)
    assert ans_out == ans_ref

    ans_ref = [(4, '12')]
    ans_out = flood(blocks, pattern='123', flood_only=True, join=''.join)
    assert ans_out == ans_ref

    ans_ref = [(0, '1'), (1, 'ABC'), (4, '2'), (6, 'xyz')]
    ans_out = flood(blocks, 0, 5, '123', join=''.join)
    assert ans_out == ans_ref

    ans_ref = [(1, 'ABC'), (5, '1'), (6, 'xyz'), (9, '2')]
    ans_out = flood(blocks, 5, 10, '123', join=''.join)
    assert ans_out == ans_ref


def test_flood():
    with pytest.raises(ValueError):
        flood([])

    blocks = [(1, 'ABC'), (6, 'xyz')]

    ans_ref = blocks
    ans_out = flood(blocks, start=5, endex=5, join=''.join)
    assert ans_out == ans_ref

    ans_ref = [(1, 'ABC'), (4, '##'), (6, 'xyz')]
    ans_out = flood(blocks, pattern=('#' * 64), join=''.join)
    assert ans_out == ans_ref


# ============================================================================

def test_merge_doctest():
    blocks = [(0, 'Hello,'), (6, ' '), (7, 'World'), (12, '!')]
    ans_ref = [(0, 'Hello, World!')]
    ans_out = merge(blocks, join=''.join)
    assert ans_out == ans_ref


def test_merge():
    blocks = [(0, 'Hello,'), (6, ''), (7, 'World'), (12, '!'), (15, '$')]
    ans_ref = [(0, 'Hello,'), (7, 'World!'), (15, '$')]
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
        (0, 'xyz'),
    ]
    ans_ref = [(0, None), (3, 'D'), (1, None), (0, 'xyz')]
    ans_out = collapse(blocks)
    assert ans_out == ans_ref

    blocks = [
        (0, 'ABCD'),
        (3, 'EF'),
        (0, '$'),
        (6, 'xyz'),
    ]
    ans_ref = [(1, 'BC'), (3, 'EF'), (0, '$'), (6, 'xyz')]
    ans_out = collapse(blocks)
    assert ans_out == ans_ref


# ============================================================================

def test_union_doctest():
    blocks1 = [
        (0, '0123456789'),
        (0, 'ABCD'),
    ]
    blocks2 = [
        (3, 'EF'),
        (0, '$'),
        (6, 'xyz'),
    ]
    ans_ref = [(0, '$'), (1, 'BC'), (3, 'EF'), (5, '5'), (6, 'xyz'), (9, '9')]
    ans_out = union(blocks1, blocks2, join=''.join)
    assert ans_out == ans_ref


# ============================================================================

class TestMemory:

    def test___init__(self):
        obj = Memory(items_type=str)
        assert obj.blocks == []
        assert obj.items_type == str
        assert obj.items_join == ''.join
        assert obj.autofill is None
        assert obj.automerge

        with pytest.raises(ValueError):
            Memory(items='ABC', blocks=[(0, 'abc')], items_type=str)

        obj = Memory(items='ABC', start=1, items_type=str)
        assert obj.blocks == [(1, 'ABC')]

        obj = Memory(blocks=[(1, 'ABC')], automerge=False, items_type=str)
        assert obj.blocks == [(1, 'ABC')]

    def test___str__doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (7, 'xyz')]
        ans_out = str(memory)
        ans_ref = 'ABCxyz'
        assert ans_out == ans_ref

    def test___bool__(self):
        obj = Memory(items_type=str)
        assert not bool(obj)

        obj.blocks = [(1, 'ABC')]
        assert bool(obj)

    def test___eq__(self):
        obj1 = Memory(items_type=str)
        obj1.blocks = [(1, 'ABC'), (7, 'xyz')]
        obj2 = Memory()
        obj2.blocks = [(1, 'ABC'), (7, 'xyz')]
        assert obj1 == obj2

        blocks2 = [(1, 'ABC'), (7, 'xyz')]
        assert obj1 == blocks2

        obj1 = Memory(items_type=str)
        obj1.blocks = [(0, 'ABC')]
        assert obj1 == 'ABC'

        obj1 = Memory(items_type=str)
        obj1.blocks = [(0, 'ABC'), (7, 'xyz')]
        assert obj1 != 'ABC'

    def test___iter__(self):
        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABC'), (7, 'xyz')]
        ans_out = list(obj)
        ans_ref = list('ABCxyz')
        assert ans_out == ans_ref

    def test___reversed__(self):
        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABC'), (7, 'xyz')]
        ans_out = list(reversed(obj))
        ans_ref = list(reversed('ABCxyz'))
        assert ans_out == ans_ref

    def test___in__(self):
        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABC'), (7, 'xyz')]
        assert 'B' in obj

    def test___add__(self):
        obj1 = Memory(items_type=str)
        obj1.blocks = [(1, 'ABC'), (5, '$')]

        obj2 = obj1 + obj1
        assert obj2.blocks == [(1, 'ABC'), (5, '$'), (7, 'ABC'), (11, '$')]

        obj2 = obj1 + 'xyz'
        assert obj2.blocks == [(1, 'ABC'), (5, '$xyz')]

    def test___iadd__(self):
        obj = Memory(items_type=str, automerge=False)
        obj += 'ABC'
        assert obj.blocks == [(0, 'ABC')]

        obj = Memory(items_type=str)
        obj += [(1, 'ABC'), (5, '$')]
        assert obj.blocks == [(1, 'ABC'), (5, '$')]

        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABC'), (5, '$')]
        obj += obj
        assert obj.blocks == [(1, 'ABC'), (5, '$'), (7, 'ABC'), (11, '$')]

        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABC'), (5, '$')]
        obj += 'xyz'
        assert obj.blocks == [(1, 'ABC'), (5, '$xyz')]

        obj = Memory(items_type=list, items_join=''.join,
                     automerge=False)
        obj += []
        assert obj.blocks == []

    def test__mul__(self):
        obj1 = Memory(items_type=str)
        obj1.blocks = [(1, 'ABC'), (5, '$')]
        obj2 = obj1 * 3
        ans_out = obj2.blocks
        ans_ref = [(1, 'ABC'), (5, '$ABC'), (10, '$ABC'), (15, '$')]
        assert ans_out == ans_ref

    def test___imul__(self):
        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABC'), (5, '$')]
        obj *= 3
        ans_out = obj.blocks
        ans_ref = [(1, 'ABC'), (5, '$ABC'), (10, '$ABC'), (15, '$')]
        assert ans_out == ans_ref

        obj = Memory(items_type=str, automerge=False)
        obj.blocks = [(1, 'ABC'), (5, '$')]
        obj *= 3
        ans_out = obj.blocks
        ans_ref = [(1, 'ABC'), (5, '$'),
                   (6, 'ABC'), (10, '$'),
                   (11, 'ABC'), (15, '$')]
        assert ans_out == ans_ref

    def test_index(self):
        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABC'), (7, 'xyz'), (11, 'ABC')]
        assert obj.index('B') == 2
        assert obj.index('y') == 8
        with pytest.raises(ValueError):
            obj.index('$')

    def test___contains___doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (5, '123'), (9, 'xyz')]
        assert '23' in memory
        assert 'y' in memory
        assert '$' not in memory

    def test_count_doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (5, 'Bat'), (9, 'tab')]
        assert memory.count('a') == 2

    def test_count(self):
        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABC'), (7, 'xyz'), (11, 'ABC')]
        assert obj.count('B') == 2
        assert obj.count('y') == 1
        assert obj.count('$') == 0

    def test___getitem___doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        assert memory[9] == 'y'
        assert memory[-2] == 'y'
        assert memory[:3] == 'AB'
        assert memory[-2:] == 'yz'
        with pytest.raises(ValueError):
            _ = memory[3:10]

        assert memory[3:10:'.'] == 'CD.$.xy'

        assert memory[memory.endex] == ''

        assert memory[3:10:3] == 'C$y'
        with pytest.raises(ValueError):
            _ = memory[3:10:2]

    def test___getitem__(self):
        memory = Memory(items_type=str, autofill='.')
        memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        assert memory[3:10] == 'CD.$.xy'

    def test___setitem___doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(5, 'ABC'), (9, 'xyz')]
        memory[7:10] = None
        assert memory.blocks == [(5, 'AB'), (10, 'yz')]
        memory[7] = 'C'
        memory[-3] = 'x'
        assert memory.blocks == [(5, 'ABC'), (9, 'xyz')]
        memory[6:12:3] = None
        assert memory.blocks == [(5, 'A'), (7, 'C'), (10, 'yz')]
        memory[6:12:3] = '123'
        assert memory.blocks == [(5, 'A1C'), (9, '2yz')]

        memory = Memory(items_type=str, automerge=False)
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
        memory = Memory(items='ABC', items_type=str)
        memory[1] = None
        assert memory.blocks == [(0, 'A'), (2, 'C')]
        with pytest.raises(ValueError):
            memory[0] = 'xyz'

    def test___delitem___doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        del memory[4:9]
        assert memory.blocks == [(1, 'ABCyz')]

        memory = Memory(items_type=str, automerge=False)
        memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        del memory[4:9]
        assert memory.blocks == [(1, 'ABC'), (4, 'yz')]

        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        del memory[-2]
        assert memory.blocks == [(1, 'ABCD'), (6, '$'), (8, 'xz')]
        del memory[3]
        assert memory.blocks == [(1, 'ABD'), (5, '$'), (7, 'xz')]
        del memory[2:10:3]
        assert memory.blocks == [(1, 'AD'), (5, 'x')]

    def test___delitem__(self):
        pass

    def test_append_doctest(self):
        memory = Memory(items_type=str)
        memory.append('$')
        assert memory.blocks == [(0, '$')]

        memory = Memory(items_type=list, items_join=''.join)
        memory.append([3])
        assert memory.blocks == [(0, [3])]

    def test_append(self):
        memory = Memory(items_type=str)
        memory.append('A')
        memory.append('BC')
        assert memory.blocks == [(0, 'ABC')]

    def test_extend(self):
        obj = Memory(items_type=str, automerge=False)
        obj.extend('ABC')
        assert obj.blocks == [(0, 'ABC')]

    def test_contiguous_doctest(self):
        memory = Memory()
        assert memory.contiguous

        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (4, 'xyz')]
        assert memory.contiguous

        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (5, 'xyz')]
        assert not memory.contiguous

    def test_start_doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (5, 'xyz')]
        assert memory.start == 1

    def test_start(self):
        memory = Memory(items_type=str)
        assert memory.start == 0

    def test_endex_doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (5, 'xyz')]
        assert memory.endex == 8

    def test_span_doctest(self):
        memory = Memory()
        assert memory.span == (0 ,0)

        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (5, 'xyz')]
        assert memory.span == (1, 8)

    def test_endex(self):
        memory = Memory(items_type=str)
        assert memory.endex == 0

    def test_shift(self):
        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABC'), (7, 'xyz')]
        obj.shift(3)
        assert obj.blocks == [(4, 'ABC'), (10, 'xyz')]

    def test_find_doctest(self):
        blocks = [(1, 'ABCD'), (7, 'xyz')]
        assert find(blocks, 'yz', -1, 15) == 8
        with pytest.raises(ValueError):
            find(blocks, '$')

    def test_read(self):
        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        assert obj.read(3, 10, '.') == 'CD.$.xy'

    def test_extract(self):
        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        assert obj.extract(3, 10, '.') == 'CD.$.xy'

    def test_cut_doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(5, 'ABC'), (9, 'xyz')]
        memory.cut(memory.index('B'), memory.index('y'))
        assert memory.blocks == [(6, 'BC'), (9, 'x')]

    def test_cut(self):
        obj = Memory(items_type=str, automerge=False)
        obj.blocks = [(5, 'ABC'), (9, 'xyz')]
        obj.cut(6, 10)
        assert obj.blocks == [(6, 'BC'), (9, 'x')]

    def test_crop_doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(5, 'ABC'), (9, 'xyz')]
        memory.crop(memory.index('B'), memory.index('y'))
        assert memory.blocks == [(6, 'BC'), (9, 'x')]

    def test_crop(self):
        obj = Memory(items_type=str, automerge=False)
        obj.blocks = [(5, 'ABC'), (9, 'xyz')]
        obj.crop(6, 10)
        assert obj.blocks == [(6, 'BC'), (9, 'x')]

    def test_clear_doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(5, 'ABC'), (9, 'xyz')]
        memory.clear(memory.index('B'), memory.index('y'))
        assert memory.blocks == [(5, 'A'), (10, 'yz')]

    def test_clear(self):
        obj = Memory(items_type=str, automerge=False)
        obj.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        obj.clear(3, 10)
        assert obj.blocks == [(1, 'AB'), (10, 'z')]

    def test_delete_doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(5, 'ABC'), (9, 'xyz')]
        memory.delete(memory.index('B'), memory.index('y'))
        assert memory.blocks == [(5, 'Ayz')]

    def test_delete(self):
        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        obj.delete(3, 10)
        assert obj.blocks == [(1, 'ABz')]

    def test_pop_doctest(self):
        memory = Memory(items_type=str)
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
        memory = Memory(items_type=str)
        with pytest.raises(IndexError):
            memory.pop()

        memory = Memory(items_type=str, automerge=False)
        memory.blocks = [(5, 'ABC'), (9, 'xyz')]
        assert memory.pop(6) == 'B'

    def test_remove_doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (5, '123'), (9, 'xyz')]
        memory.remove('23')
        assert memory.blocks == [(1, 'ABC'), (5, '1'), (7, 'xyz')]
        memory.remove('y')
        assert memory.blocks == [(1, 'ABC'), (5, '1'), (7, 'xz')]
        with pytest.raises(ValueError):
            memory.remove('$')

    def test_remove(self):
        memory = Memory(items_type=str, automerge=False)
        memory.blocks = [(1, 'ABC'), (5, '123'), (9, 'xyz')]
        memory.remove('23')
        assert memory.blocks == [(1, 'ABC'), (5, '1'), (7, 'xyz')]

    def test_reserve_doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (6, 'xyz')]
        memory.reserve(5, 3)
        assert memory.blocks == [(1, 'ABC'), (9, 'xyz')]

    def test_reserve(self):
        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABCD'), (7, 'xyz')]
        obj.reserve(7, 1)
        assert obj.blocks == [(1, 'ABCD'), (8, 'xyz')]

        obj = Memory(items_type=str, automerge=False)
        obj.blocks = [(1, 'ABCD'), (7, 'xyz')]
        obj.reserve(6, 1)
        assert obj.blocks == [(1, 'ABCD'), (8, 'xyz')]

    def test_insert_doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (6, 'xyz')]
        memory.insert(5, '123')
        assert memory.blocks == [(1, 'ABC'), (5, '123'), (9, 'xyz')]

    def test_insert(self):
        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABCD'), (7, 'xyz')]
        obj.insert(7, '$')
        assert obj.blocks == [(1, 'ABCD'), (7, '$xyz')]

        obj = Memory(items_type=str, automerge=False)
        obj.blocks = [(1, 'ABCD'), (7, 'xyz')]
        obj.insert(6, '$')
        assert obj.blocks == [(1, 'ABCD'), (6, '$'), (8, 'xyz')]

    def test_write_doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (6, 'xyz')]
        memory.write(5, '123')
        assert memory.blocks == [(1, 'ABC'), (5, '123z')]

    def test_write(self):
        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xy')]
        obj.write(3, '123456')
        assert obj.blocks == [(1, 'AB123456y')]

        obj = Memory(items_type=str, automerge=False)
        obj.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xy')]
        obj.write(3, '123456')
        ans_out = obj.blocks
        ans_ref = [(1, 'AB'), (3, '123456'), (9, 'y')]
        assert ans_out == ans_ref

    def test_fill_doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (6, 'xyz')]
        memory.fill(pattern='123')
        assert memory.blocks == [(1, '12312312')]

        memory = Memory(items_type=str, autofill='123')
        memory.blocks = [(1, 'ABC'), (6, 'xyz')]
        memory.fill()
        assert memory.blocks == [(1, '12312312')]

        memory = Memory(items_type=str, autofill='123')
        memory.blocks = [(1, 'ABC'), (6, 'xyz')]
        memory.fill(3, 7)
        assert memory.blocks == [(1, 'AB1231yz')]

    def test_fill(self):
        memory = Memory(items_type=str, automerge=False)
        memory.blocks = [(1, 'ABC'), (6, 'xyz')]
        memory.fill(pattern='123')
        assert memory.blocks == [(1, '12312312')]

    def test_flood_doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (6, 'xyz')]
        memory.flood(pattern='123')
        assert memory.blocks == [(1, 'ABC12xyz')]

        memory = Memory(items_type=str, autofill='123')
        memory.blocks = [(1, 'ABC'), (6, 'xyz')]
        memory.flood()
        assert memory.blocks == [(1, 'ABC12xyz')]

    def test_flood(self):
        obj = Memory(items_type=str)
        obj.blocks = [(1, 'ABC'), (6, 'xyz')]
        obj.flood(pattern='123')
        ans_out = obj.blocks
        ans_ref = [(1, 'ABC12xyz')]
        assert ans_out == ans_ref

        obj = Memory(items_type=str, automerge=False)
        obj.blocks = [(1, 'ABC'), (6, 'xyz')]
        obj.flood(pattern='123')
        ans_out = obj.blocks
        ans_ref = [(1, 'ABC'), (4, '12'), (6, 'xyz')]
        assert ans_out == ans_ref

    def test_merge_doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (4, 'xyz')]
        memory.merge()
        ans_out = memory.blocks
        ans_ref = [(1, 'ABCxyz')]
        assert ans_out == ans_ref

    def test_reverse_doctest(self):
        memory = Memory(items_type=str)
        memory.blocks = [(1, 'ABC'), (5, '$'), (7, 'xyz')]
        memory.reverse()
        assert memory.blocks == [(0, 'zyx'), (4, '$'), (6, 'CBA')]

    def test_reverse(self):
        memory = Memory(items_type=str, automerge=False)
        memory.blocks = [(1, 'ABC'), (5, '$'), (7, 'xyz')]
        memory.reverse()
        assert memory.blocks == [(0, 'zyx'), (4, '$'), (6, 'CBA')]
