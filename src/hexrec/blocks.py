# -*- coding: utf-8 -*-

# Copyright (c) 2013-2018, Andrea Zoppi
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""Utilities for sparse blocks of data.

A `block` is ``(start, items)`` where `start` is the start address and
`items` is the container of items (e.g. :obj:`bytes`, :obj:`str`,
:obj:`tuple`). The length of the block is ``len(items)``.

"""
from .utils import do_overlap
from .utils import makefill
from .utils import straighten_index
from .utils import straighten_slice


def overlap(block1, block2):
    r"""Checks if two blocks do overlap.

    Arguments:
        block1 (block): A block.
        block2 (block): A block.

    Returns:
        :obj:`bool`: The blocks do overlap.

    Examples:
        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |   |   |   |[x | y | z]|   |   |
        +---+---+---+---+---+---+---+---+---+---+

        >>> overlap((1, 'ABCD'), (5, 'xyz'))
        False

        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |   |[x | y | z]|   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+

        >>> overlap((1, 'ABCD'), (3, 'xyz'))
        True
    """
    start1, items1 = block1
    endex1 = start1 + len(items1)
    start2, items2 = block2
    endex2 = start2 + len(items2)
    return do_overlap(start1, endex1, start2, endex2)


def sorting(block):
    r"""Block sorting key.

    Allows to sort blocks so that blocks with the same start address are kept
    in the same order as per `blocks`.

    Python provides stable sorting functions, so it is sufficient to pass only
    the start address to them.

    Arguments:
        block (block): Block under examination.

    Returns:
        :obj:`int`. The start address of the block.

    Example:
        For reference:
        - ``ord('!')`` = 33
        - ``ord('1')`` = 49
        - ``ord('A')`` = 65

        >>> blocks = [(2, 'ABC'), (7, '>'), (2, '!'), (0, '<'), (2, '11')]
        >>> blocks.sort(key=sorting)
        >>> blocks
        [(0, '<'), (2, 'ABC'), (2, '!'), (2, '11'), (7, '>')]
    """
    return block[0]


def locate_at(blocks, address):
    r"""Locates the block enclosing an address.

    Arguments:
        blocks (:obj:`list` of block): A fast indexable sequence of
            non-overlapping blocks, sorted by address.
        address (:obj:`int`): Address of the target item.

    Returns:
        :obj:`int`: Index of the block enclosing the given address, ``None``
            if not found.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11|
        +===+===+===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |[!]|   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+---+---+
        |   | 0 | 0 | 0 | 0 |   | 1 |   | 2 | 2 | 2 |   |
        +---+---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (6, '!'), (8, 'xyz')]
        >>> [locate_at(blocks, i) for i in range(12)]
        [None, 0, 0, 0, 0, None, 1, None, 2, 2, 2, None]
    """
    length = len(blocks)
    if length:
        start, items = blocks[0]
        if address < start:
            return None

        start, items = blocks[length - 1]
        if start + len(items) <= address:
            return None
    else:
        return None

    left = 0
    right = length

    while left <= right:
        center = (left + right) >> 1
        start, items = blocks[center]

        if start + len(items) <= address:
            left = center + 1
        elif address < start:
            right = center - 1
        else:
            return center
    else:
        return None


def locate_start(blocks, address):
    r"""Locates the first block inside of an address range.

    Arguments:
        blocks (:obj:`list` of block): A fast indexable sequence of
            non-overlapping blocks, sorted by address.
        address (:obj:`int`): Inclusive start address of the scanned range.

    Returns:
        :obj:`int`: Index of the first block whose start address is greater
            than or equal to `address`.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11|
        +===+===+===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |[!]|   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 2 | 2 | 2 | 3 |
        +---+---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (6, '!'), (8, 'xyz')]
        >>> [locate_start(blocks, i) for i in range(12)]
        [0, 0, 0, 0, 0, 1, 1, 2, 2, 2, 2, 3]
    """
    length = len(blocks)
    if length:
        start, items = blocks[0]
        if address < start:
            return 0

        start, items = blocks[length - 1]
        if start + len(items) <= address:
            return length
    else:
        return 0

    left = 0
    right = length

    while left <= right:
        center = (left + right) >> 1
        start, items = blocks[center]

        if start + len(items) <= address:
            left = center + 1
        elif address < start:
            right = center - 1
        else:
            return center
    else:
        return left


def locate_endex(blocks, address):
    r"""Locates the first block after an address range.

    Arguments:
        blocks (:obj:`list` of block): A fast indexable sequence of
            non-overlapping blocks, sorted by address.
        address (:obj:`int`): Exclusive end address of the scanned range.

    Returns:
        :obj:`int`: Index of the first block whose end address is lesser
            than or equal to `address`.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11|
        +===+===+===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |[!]|   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 3 | 3 | 3 | 3 |
        +---+---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (6, '!'), (8, 'xyz')]
        >>> [locate_endex(blocks, i) for i in range(12)]
        [0, 1, 1, 1, 1, 1, 2, 2, 3, 3, 3, 3]
    """
    length = len(blocks)
    if length:
        start, items = blocks[0]
        if address < start:
            return 0

        start, items = blocks[length - 1]
        if start + len(items) <= address:
            return length
    else:
        return 0

    left = 0
    right = length

    while left <= right:
        center = (left + right) >> 1
        start, items = blocks[center]

        if start + len(items) <= address:
            left = center + 1
        elif address < start:
            right = center - 1
        else:
            return center + 1
    else:
        return right + 1


def shift(blocks, amount):
    r"""Shifts the address of blocks.

    Arguments:
        blocks (:obj:`list` of block): Sequence of blocks to shift.
        amount (:obj:`int`): Signed amount of address shifting.

    Returns:
        :obj:`list` or block: A new list with shifted blocks.

    Example:
        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |   |[x | y | z]|
        +---+---+---+---+---+---+---+---+---+---+
        |[A | B | C | D]|   |   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (7, 'xyz')]
        >>> shift(blocks, -1)
        [(0, 'ABCD'), (6, 'xyz')]
    """
    return [(start + amount, items) for start, items in blocks]


def select(blocks, start, endex):
    r"""Selects blocks from a range.

    Arguments:
        blocks (:obj:`list` of block): A fast indexable sequence of
            non-overlapping blocks, sorted by address.
        start (:obj:`int`): Inclusive start of the extracted range.
            If ``None``, the global inclusive start address is considered
            (i.e. that of the first block).
        endex (:obj:`int`): Exclusive end of the extracted range.
            If ``None``, the global exclusive end address is considered
            (i.e. that of the last block).

    Returns:
        :obj:`list` of block: A new list of blocks, with the same order of
            `blocks`.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10|
        +===+===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |[!]|   |[x | y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |   |   |[C | D]|   |[!]|   |[x | y]|   |
        +---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (6, '!'), (8, 'xyz')]
        >>> select(blocks, 3, 10)
        [(3, 'CD'), (6, '!'), (8, 'xy')]
    """
    if start is None:
        start, _ = blocks[0]
    range_start = start

    if endex is None:
        start, items = blocks[-1]
        endex = start + len(items)
    range_endex = endex

    index_start = locate_start(blocks, range_start)
    index_endex = locate_endex(blocks, range_endex)

    blocks_inside = []
    append = blocks_inside.append

    for index in range(index_start, index_endex):
        start, items = blocks[index]
        endex = start + len(items)

        if range_start <= start <= endex <= range_endex:
            append((start, items))

        elif start < range_start < range_endex < endex:
            start = range_start - start
            endex = range_endex - endex
            append((range_start, items[start:endex]))

        elif start < range_start < endex <= range_endex:
            append((range_start, items[(range_start - start):]))

        elif range_start <= start < range_endex < endex:
            append((start, items[:(range_endex - endex)]))

        else:
            append((start, items))

    result = blocks_inside
    return result


def clear(blocks, start, endex):
    r"""Clears a range.

    Arguments:
        blocks (:obj:`list` of block): A fast indexable sequence of
            non-overlapping blocks, sorted by address.
        start (:obj:`int`): Inclusive start of the cleared range.
            If ``None``, the global inclusive start address is considered
            (i.e. that of the first block).
        endex (:obj:`int`): Exclusive end of the cleared range.
            If ``None``, the global exclusive end address is considered
            (i.e. that of the last block).

    Returns:
        :obj:`list` of block: A new list of blocks, with the same order of
            `blocks`.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10|
        +===+===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |[!]|   |[x | y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C]|   |   |   |   |   |[y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C]|   |   |   |   |   |[y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A]|   |[C]|   |   |   |   |   |[y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (6, '!'), (8, 'xyz')]
        >>> blocks = clear(blocks, 4, 9)
        >>> blocks = clear(blocks, 2, 2)
        >>> blocks = clear(blocks, 2, 3)
        >>> blocks
        [(1, 'A'), (3, 'C'), (9, 'yz')]
    """
    if start is None:
        start, _ = blocks[0]
    range_start = start

    if endex is None:
        start, items = blocks[-1]
        endex = start + len(items)
    range_endex = endex

    index_start = locate_start(blocks, range_start)
    index_endex = locate_endex(blocks, range_endex)

    blocks_before = blocks[:index_start]
    blocks_after = blocks[index_endex:]
    blocks_inside = []
    append = blocks_inside.append

    for index in range(index_start, index_endex):
        start, items = blocks[index]
        endex = start + len(items)

        if range_start <= start <= endex <= range_endex:
            pass  # fully deleted

        elif start < range_start < range_endex < endex:
            append((start, items[:(range_start - start)]))
            append((range_endex, items[(range_endex - endex):]))

        elif start < range_start < endex <= range_endex:
            append((start, items[:(range_start - start)]))

        elif range_start <= start < range_endex < endex:
            append((range_endex, items[(range_endex - endex):]))

        else:
            append((start, items))

    result = blocks_before + blocks_inside + blocks_after
    return result


def delete(blocks, start, endex):
    r"""Deletes a range.

    Arguments:
        blocks (:obj:`list` of block): A fast indexable sequence of
            non-overlapping blocks, sorted by address.
        start (:obj:`int`): Inclusive start of the deleted range.
            If ``None``, the global inclusive start address is considered
            (i.e. that of the first block).
        endex (:obj:`int`): Exclusive end of the deleted range.
            If ``None``, the global exclusive end address is considered
            (i.e. that of the last block).

    Returns:
        :obj:`list` of block: A new list of blocks, with the same order of
            `blocks`.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10|
        +===+===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |[!]|   |[x | y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C]|[y | z]|   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C]|[y | z]|   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A]|[C]|[y | z]|   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (6, '!'), (8, 'xyz')]
        >>> blocks = delete(blocks, 4, 9)
        >>> blocks = delete(blocks, 2, 2)
        >>> blocks = delete(blocks, 2, 3)
        >>> blocks
        [(1, 'A'), (2, 'C'), (3, 'yz')]
    """
    if start is None:
        start, _ = blocks[0]
    range_start = start

    if endex is None:
        start, items = blocks[-1]
        endex = start + len(items)
    range_endex = endex

    range_length = range_endex - range_start
    if range_length <= 0:
        return list(blocks)

    index_start = locate_start(blocks, range_start)
    index_endex = locate_endex(blocks, range_endex)

    blocks_before = blocks[:index_start]
    blocks_after = blocks[index_endex:]
    blocks_inside = []
    append = blocks_inside.append

    for index in range(index_start, index_endex):
        start, items = blocks[index]
        endex = start + len(items)

        if range_start <= start <= endex <= range_endex:
            pass  # fully deleted

        elif start < range_start < range_endex < endex:
            append((start, items[:(range_start - start)]))
            append((range_start, items[(range_endex - endex):]))

        elif start < range_start < endex <= range_endex:
            append((start, items[:(range_start - start)]))

        elif range_start <= start < range_endex < endex:
            append((range_start, items[(range_endex - endex):]))

        elif range_endex <= start:
            append((start - (range_endex - range_start), items))

        else:
            append((start, items))

    blocks_after = shift(blocks_after, -range_length)
    result = blocks_before + blocks_inside + blocks_after
    return result


def insert(blocks, inserted):
    r"""Inserts a block into a sequence.

    Inserts a block into a sequence, moving existing items after the insertion
    address by the length of the inserted block.

    Arguments:
        blocks (:obj:`list` of block): A fast indexable sequence of
            non-overlapping blocks, sorted by address.
        inserted (block): Block to insert.

    Returns:
        :obj:`list` of block: A new list of non-overlapping blocks, sorted by
            start address.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11|
        +===+===+===+===+===+===+===+===+===+===+===+===+
        |[A | B | C | D]|   |   |[x | y | z]|   |   |   |
        +---+---+---+---+---+---+---+---+---+---+---+---+
        |[A | B | C | D]|   |   |[x | y | z]|   |[!]|   |
        +---+---+---+---+---+---+---+---+---+---+---+---+
        |[A]|[1]|[B | C | D]|   |   |[x | y | z]|   |[!]|
        +---+---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(0, 'ABCD'), (6, 'xyz')]
        >>> blocks = insert(blocks, (10, '!'))
        >>> blocks = insert(blocks, (1, '1'))
        >>> blocks
        [(0, 'A'), (1, '1'), (2, 'BCD'), (7, 'xyz'), (11, '!')]
    """
    inserted_start, inserted_items = inserted
    inserted_length = len(inserted_items)
    inserted_endex = inserted_start + inserted_length

    pivot_index = locate_at(blocks, inserted_start)

    if pivot_index is None:
        pivot_index = locate_endex(blocks, inserted_start)
        blocks_before = blocks[:pivot_index]
        blocks_after = blocks[pivot_index:]
        blocks_inside = [(inserted_start, inserted_items)]

    else:
        blocks_before = blocks[:pivot_index]
        blocks_after = blocks[(pivot_index + 1):]
        pivot_start, pivot_items = blocks[pivot_index]

        if pivot_start == inserted_start:
            blocks_inside = [(inserted_start, inserted_items),
                             (pivot_start + inserted_length, pivot_items)]
        else:
            blocks_inside = [(pivot_start, pivot_items[:inserted_length]),
                             (inserted_start, inserted_items),
                             (inserted_endex, pivot_items[inserted_length:])]

    blocks_after = shift(blocks_after, inserted_length)
    result = blocks_before + blocks_inside + blocks_after
    return result


def write(blocks, written):
    r"""Writes a block onto a sequence.

    Arguments:
        blocks (:obj:`list` of block): A fast indexable sequence of
            non-overlapping blocks, sorted by address.
        written (block): Block to write.

    Returns:
        :obj:`list` of block: A new list of non-overlapping blocks, sorted by
            start address.

    Example:
        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |[!]|   |[x | y]|
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |   |[1 | 2 | 3 | 4 | 5 | 6]|   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |[A | B]|[1 | 2 | 3 | 4 | 5 | 6]|[y]|
        +---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (6, '!'), (8, 'xy')]
        >>> write(blocks, (3, '123456'))
        [(1, 'AB'), (3, '123456'), (9, 'y')]
    """
    start, items = written
    endex = start + len(items)

    result = clear(blocks, start, endex)
    pivot_index = locate_start(result, start)
    result.insert(pivot_index, written)
    return result


def fill(blocks, start=None, endex=None, pattern=b'\0',
         fill_only=False, join=b''.join):
    r"""Fills emptiness between non-touching blocks.

    Arguments:
        blocks (:obj:`list` of block): A fast indexable sequence of
            non-overlapping blocks, sorted by address.
        pattern (items): Pattern of items to fill the emptiness.
        start (:obj:`int`): Inclusive start of the filled range.
            If ``None``, the global inclusive start address is considered
            (i.e. that of the first block).
        endex (:obj:`int`): Exclusive end of the filled range.
            If ``None``, the global exclusive end address is considered
            (i.e. that of the last block).
        fill_only (:obj:`bool`): Returns only the filling blocks.
        join (callable): A function to join a sequence of items.

    Returns:
        :obj:`list` of block: List of the filling blocks, including the
            existing blocks if `fill_only` is ``False``.

    Example:
        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C]|   |   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C]|[# | #]|[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+
        |[# |[A | B | C]| #]|   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C]|   |[# |[x | y | z]| #]|
        +---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABC'), (6, 'xyz')]
        >>> fill(blocks, pattern='123', join=''.join)
        [(1, 'ABC'), (4, '23'), (6, 'xyz')]
        >>> fill(blocks, pattern='123', fill_only=True, join=''.join)
        [(4, '23')]
        >>> fill(blocks, pattern='123', start=0, endex=5, join=''.join)
        [(0, '1'), (1, 'ABC'), (4, '2'), (6, 'xyz')]
        >>> fill(blocks, pattern='123', start=5, endex=10, join=''.join)
        [(1, 'ABC'), (5, '3'), (6, 'xyz'), (9, '1')]
    """
    if start is None and endex is None and not blocks:
        raise ValueError('no blocks')
    if start is None:
        start = blocks[0][0]
    if endex is None:
        block_start, block_items = blocks[-1]
        endex = block_start + len(block_items)
    with_blocks = not fill_only

    pattern_length = len(pattern)
    if pattern_length < 64:
        pattern_length = (64 - 1 + pattern_length) // pattern_length
        pattern = join(pattern for _ in range(pattern_length))
        pattern_length = len(pattern)

    start_index = locate_start(blocks, start)
    endex_index = locate_endex(blocks, endex)
    blocks_before = blocks[:start_index]
    blocks_after = blocks[endex_index:]
    blocks_inside = []
    last_endex = start

    for block in blocks[start_index:endex_index]:
        block_start, block_items = block

        if last_endex < block_start:
            pattern_start = last_endex % pattern_length
            pattern_endex = block_start - last_endex + pattern_start
            items = makefill(pattern, pattern_start, pattern_endex, join=join)
            blocks_inside.append((last_endex, items))

        if with_blocks:
            blocks_inside.append(block)

        last_endex = block_start + len(block_items)

    if last_endex < endex:
        pattern_start = last_endex % pattern_length
        pattern_endex = endex - last_endex + pattern_start
        items = makefill(pattern, pattern_start, pattern_endex, join)
        blocks_inside.append((last_endex, items))

    if with_blocks:
        result = blocks_before + blocks_inside + blocks_after
    else:
        result = blocks_inside
    return result


def merge(blocks, join=''.join):
    r"""Merges touching blocks.

    Arguments:
        blocks (:obj:`list` of block): An sequence of non-overlapping blocks,
            sorted by address. Sequence generators supported.
        join (callable): A function to join a sequence of items.

    Returns:
        :obj:`list` of block: A new list of non-overlapping blocks, sorted by
            address.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11| 12|
        +===+===+===+===+===+===+===+===+===+===+===+===+===+
        |[H | e | l | l | o | ,]|   |   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+
        |   |   |   |   |   |   |[ ]|   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+
        |   |   |   |   |   |   |   |[W | o | r | l | d]|   |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+
        |   |   |   |   |   |   |   |   |   |   |   |   |[!]|
        +---+---+---+---+---+---+---+---+---+---+---+---+---+
        |[H | e | l | l | o | , |   | W | o | r | l | d | !]|
        +---+---+---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(0, 'Hello,'), (6, ' '), (7, 'World'), (12, '!')]
        >>> merge(blocks)
        [(0, 'Hello, World!')]
    """
    result = []
    contiguous_items = []
    contiguous_start = None
    last_endex = None

    for block in blocks:
        start, items = block
        endex = start + len(items)

        if last_endex is None or last_endex == start:
            if not contiguous_items:
                contiguous_start = start
            contiguous_items.append(items)

        else:
            if contiguous_items:
                contiguous_items = join(contiguous_items)
                result.append((contiguous_start, contiguous_items))

            contiguous_items = [items]
            contiguous_start = start

        last_endex = endex

    if contiguous_items:
        contiguous_items = join(contiguous_items)
        result.append((contiguous_start, contiguous_items))

    return result


def collapse(blocks):
    r"""Collapses blocks of items.

    Given a sequence of blocks, they are modified so that a previous block
    does not overlap with the following ones.

    Arguments:
        blocks (:obj:`list` of block): A sequence of blocks.
            Sequence generators supported.

    Returns:
        :obj:`list` of block: A new list of non-overlapping blocks.

    Example:
        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |[0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9]|
        +---+---+---+---+---+---+---+---+---+---+
        |[A | B | C | D]|   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |   |[E | F]|   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |[!]|   |   |   |   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |   |   |   |   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+
        |[!]|[B | C]|[E | F]|[5]|[x | y | z]|[9]|
        +---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [
        ...     (0, '0123456789'),
        ...     (0, 'ABCD'),
        ...     (3, 'EF'),
        ...     (0, '!'),
        ...     (6, 'xyz'),
        ... ]
        >>> collapse(blocks)
        [(5, '5'), (1, 'BC'), (3, 'EF'), (0, '!'), (9, '9'), (6, 'xyz')]
    """
    result = []

    for block in blocks:
        start1, items1 = block
        if items1:
            endex1 = start1 + len(items1)

            for i in range(len(result)):
                start2, items2 = result[i]
                if items2:
                    endex2 = start2 + len(items2)

                    if start1 <= start2 <= endex2 <= endex1:
                        result[i] = (start2, None)

                    elif start2 < start1 < endex2 <= endex1:
                        result[i] = (start2, items2[:(start1 - start2)])

                    elif start1 <= start2 < endex1 < endex2:
                        result[i] = (endex1, items2[(endex1 - start2):])

                    elif start2 < start1 <= endex1 < endex2:
                        result[i] = (start2, items2[:(start1 - start2)])
                        result.append((endex1, items2[(endex1 - start2):]))

            result.append(block)

    return result


class SparseItems(object):  # TODO
    r"""Sparse item blocks manager.

    This is an helper class to emulate a virtual space with sparse blocks of
    items, for example a virtual memory of :class:`str` blocks.
    """
    def __init__(self, items=None, start=0, automerge=True,
                 items_type=str, items_join=''.join):

        if items is not None:
            items = [items_type(it) for it in items]
            blocks = [(start, items)]
        else:
            blocks = []

        self.blocks = blocks
        self.automerge = automerge
        self.items_type = items_type
        self.items_join = items_join

    def __bool__(self):
        return bool(self.blocks)

    def __eq__(self, other):
        r"""Equality comparison.

        Arguments:
            other (:obj:`SparseItems`, or :obj:`list` of items, or items):
                Data to compare with `self`.
                If it is an instance of `SparseItems`, all of its blocks must
                match.
                If it is a :obj:`list`, it is expected that it contains the
                same blocks as `self`.
                Otherwise, it must match the first stored block, considered
                equal if also starts at 0.

        Returns:
            :obj:`bool`: `self` is equal to `other`.
        """
        if isinstance(other, SparseItems):
            return self.blocks == other.blocks

        elif isinstance(other, list):
            return self.blocks == other

        else:
            if len(self.blocks) != 1:
                return False

            start, items = next(iter(self.blocks))
            return start == 0 and items == other

    def __iter__(self):
        r"""Item iterator."""
        for _, items in self.blocks:
            for item in items:
                yield item

    def __reversed__(self):
        r"""Reverse iterator."""
        for _, items in reversed(self.blocks):
            for item in reversed(items):
                yield item

    def __add__(self, value):
        r"""Concatenates items.

        Arguments:
            value (:obj:`SparseItems` or items): Items to append at the
                current virtual space end (i.e. at :attr:`endex`).

        Returns:
            :obj:`SparseItems`: A new space with the items concatenated.
        """
        result = type(self)()
        result.blocks = list(self.blocks)
        result += value
        return result

    def __iadd__(self, value):
        r"""Concatenates items.

        Arguments:
            value (:obj:`SparseItems` or items): Items to append at the
                current virtual space end (i.e. at :attr:`endex`).

        Returns:
            :obj:`SparseItems`: `self`.
        """
        blocks = self.blocks

        if isinstance(value, SparseItems):
            if value is self:
                value.blocks = list(blocks)  # guard extend() over iter()

            offset = self.endex - value.start
            blocks.extend((start + offset, items)
                          for start, items in value.blocks)
        else:
            if blocks:
                start, items = blocks[-1]
                blocks[-1] = (start, items + value)
            else:
                blocks.append((0, value))

        if self.automerge:
            blocks = merge(blocks)

        self.blocks = blocks
        return self

    def __mul__(self, times):
        r"""Repeats the items.

        Repeats the stored items by `times`. Each repeated sequence is
        appended at the current virtual space end (i.e. :attr:`endex`).

        Arguments:
            times (:obj:`int`): Times to repeat the sequence of items.

        Returns:
            :obj:`SparseItems`: A new space with the items repeated.
        """
        result = type(self)()
        result.blocks = list(self.blocks)
        result *= times
        return result

    def __imul__(self, times):
        r"""Repeats the items.

        Repeats the stored items by `times`. Each repeated sequence is
        appended at the current virtual space end (i.e. :attr:`endex`).

        Arguments:
            times (:obj:`int`): Times to repeat the sequence of items.

        Returns:
            :obj:`SparseItems`: `self`.
        """
        blocks = self.blocks
        repeated = []
        offset = 0
        length = len(self)

        for _ in range(times):
            repeated.extend((start + offset, items)
                            for start, items in blocks)
            offset += length

        if self.automerge:
            repeated = merge(repeated)

        self.blocks = repeated
        return self

    def __len__(self):
        r"""Actual length.

        Returns:
            :obj:`int`: The actual length of the stored items, i.e.
                (:attr:`endex` - :attr:`start`).
        """
        return self.endex - self.start

    def index(self, value, start=None, endex=None):
        r"""Index of an item.

        Arguments:
            value (item): Value to find.
            start (:obj:`int`): Inclusive start of the searched range.
                If ``None``, the global inclusive start address is considered
                (i.e. :attr:`start`).
            endex (:obj:`int`): Exclusive end of the searched range.
                If ``None``, the global exclusive end address is considered
                (i.e. :attr:`endex`).

        Returns:
            :obj:`int`: The index of the first item equal to `value`.
        """
        for address, items in self.blocks:
            items_start = None if start is None else start - address
            items_endex = None if endex is None else endex - address
            try:
                offset = items.index(value, items_start, items_endex)
            except ValueError:
                continue
            return address + offset
        else:
            raise ValueError('item not found')

    def count(self, value):
        r"""Counts items.

        Arguments:
            value (item): Reference value to count.

        Returns:
            :obj:`int`: The number of items equal to `value`.
        """
        return sum(1 for item in self if item == value)

    def __getitem__(self, key):
        r"""Extracts contiguous data.

        Arguments:
            key (:obj:`slice` or :obj:`int`): Selection range or address.

        Returns:
            items: Items from the given range.

        Note:
            This method is not optimized for a :class:`slice` with its `step`
            different from either ``None`` or 1.
        """
        if isinstance(key, slice):
            start, stop, step = key.start, key.stop, key.step
            length = self.endex
            start, stop, step = straighten_slice(start, stop, step, length)
            blocks = self.blocks

            if step is None:
                for address, items in blocks:
                    if start <= address <= address + len(items) <= stop:
                        return items[(start - address):(stop - address)]
                else:
                    raise ValueError('contiguous slice not found')
            else:
                raise NotImplementedError('TODO')  # TODO

        else:
            for address, items in blocks:
                if address <= key <= address + len(items):
                    return items[key - address]
            else:
                raise IndexError('item index out of range')

    def __setitem__(self, key, value):
        r"""Writes data.

        Arguments:
            key (:obj:`slice` or :obj:`int`): Selection range or address.
            value (items): Items to write at the selection address.

        Note:
            This method is not optimized for a :class:`slice` with its `step`
            different from either ``None`` or 1.
        """
        blocks = self.blocks

        if isinstance(key, slice):
            start, stop, step = key.start, key.stop, key.step
            length = self.endex
            start, stop, step = straighten_slice(start, stop, step, length)

            if start + len(value) < stop:
                blocks = delete(blocks, start + len(value), stop)

            if step is None or step == 1:
                blocks = write(blocks, (start, value))
            else:
                for address, item in zip(range(start, stop, step), value):
                    blocks = write(blocks, (address, item))

        else:
            key = key.__index__()
            if key < 0:
                key %= self.endex
            blocks = write(blocks, value)

        if self.automerge:
            blocks = merge(blocks)
        self.blocks = blocks

    def __delitem__(self, key):
        r"""Deletes data.

        Arguments:
            key (:obj:`slice` or :obj:`int`): Deletion range or address.

        Note:
            This method is not optimized for a :class:`slice` with its `step`
            different from either ``None`` or 1.
        """
        blocks = self.blocks

        if isinstance(key, slice):
            start, stop, step = key.start, key.stop, key.step
            length = self.endex
            start, stop, step = straighten_slice(start, stop, step, length)

            if step is None or step == 1:
                blocks = delete(blocks, start, stop)
            else:
                for address in range(start, stop, step):
                    blocks = delete(blocks, address, address + 1)

        else:
            key = key.__index__()
            if key < 0:
                key %= self.endex
            blocks = delete(blocks, key, key + 1)

        if self.automerge:
            blocks = merge(blocks)
        self.blocks = blocks

    @property
    def start(self):
        r"""Inclusive start address.

        Returns:
            :obj:`int`: The inclusive start address, or 0.
        """
        blocks = self.blocks

        if blocks:
            start, _ = blocks[0]
            return start
        else:
            return 0

    @property
    def endex(self):
        r"""Exclusive end address.

        Returns:
            :obj:`int`: The eclusive end address, or 0.
        """
        blocks = self.blocks

        if blocks:
            start, items = blocks[-1]
            return start + len(items)
        else:
            return 0

    def shift(self, amount):
        r"""Shifts the items.

        Arguments:
            amount (:obj:`int`): Signed amount of address shifting.

        See Also:
            :func:`shift`
        """
        blocks = self.blocks
        blocks = shift(blocks, amount)
        self.blocks = blocks

    def select(self, start, endex):
        r"""Selects items from a range.

        Arguments:
            start (:obj:`int`): Inclusive start of the extracted range.
                If ``None``, the global inclusive start address is considered
                (i.e. :attr:`start`).
            endex (:obj:`int`): Exclusive end of the extracted range.
                If ``None``, the global exclusive end address is considered
                (i.e. :attr:`endex`).

        Returns:
            items: Items from the selected range.

        See Also:
            :func:`select`
        """
        return self[start:endex]

    def clear(self, start, endex):
        r"""Clears a range.

        Arguments:
            start (:obj:`int`): Inclusive start of the extracted range.
                If ``None``, the global inclusive start address is considered
                (i.e. :attr:`start`).
            endex (:obj:`int`): Exclusive end of the extracted range.
                If ``None``, the global exclusive end address is considered
                (i.e. :attr:`endex`).

        See Also:
            :func:`clear`
        """
        blocks = self.blocks
        blocks = clear(blocks, start, endex)

        if self.automerge:
            blocks = merge(blocks)

        self.blocks = blocks

    def delete(self, start, endex):
        r"""Deletes a range.

        Arguments:
            start (:obj:`int`): Inclusive start of the extracted range.
                If ``None``, the global inclusive start address is considered
                (i.e. :attr:`start`).
            endex (:obj:`int`): Exclusive end of the extracted range.
                If ``None``, the global exclusive end address is considered
                (i.e. :attr:`endex`).

        See Also:
            :func:`delete`
        """
        del self[start:endex]

    def insert(self, block):
        r"""Inserts a block.

        Inserts a block, moving existing items after the insertion address by
        the length of the inserted block.

        Arguments:
            block (block): Block to insert.

        See Also:
            :func:`insert`
        """
        blocks = self.blocks
        blocks = insert(blocks, block)

        if self.automerge:
            blocks = merge(blocks)

        self.blocks = blocks

    def write(self, block):
        r"""Writes a block.

        Arguments:
            block (block): Block to write.

        See Also:
            :func:`write`
        """
        blocks = self.blocks
        blocks = write(blocks, block)

        if self.automerge:
            blocks = merge(blocks)

        self.blocks = blocks

    def fill(self, start=None, endex=None, pattern=b'\0',
             fill_only=False, join=b''.join):
        r"""Fills emptiness between non-touching blocks.

        Arguments:
            pattern (items): Pattern of items to fill the emptiness.
            start (:obj:`int`): Inclusive start of the filled range.
                If ``None``, the global inclusive start address is considered
                (i.e. that of the first block).
            endex (:obj:`int`): Exclusive end of the filled range.
                If ``None``, the global exclusive end address is considered
                (i.e. that of the last block).
            fill_only (:obj:`bool`): Returns only the filling blocks.
            join (callable): A function to join a sequence of items.

        See Also:
            :func:`fill`
        """

        blocks = self.blocks
        blocks = fill(blocks, start, endex, pattern, fill_only, join)

        if self.automerge:
            blocks = merge(blocks)

        self.blocks = blocks

    def merge(self):
        r"""Merges touching blocks.

        See Also:
            :func:`merge`
        """
        blocks = self.blocks
        blocks = merge(blocks)
        self.blocks = blocks
