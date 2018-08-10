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
from .utils import chop
from .utils import do_overlap
from .utils import makefill
from .utils import straighten_index
from .utils import straighten_slice


def chop_blocks(items, window, align_base=0, start=0):
    r"""Chops a sequence of items into blocks.

    Iterates through the vector grouping its items into windows.

    Arguments:
        items (items): Sequence of items to chop.
        window (:obj:`int`): Window length.
        align_base (:obj:`int`): Offset of the first window.
        start (:obj:`int`): Start address.

    Yields:
        list: `items` slices of up to `window` elements.

    Examples:
        >>> list(chop_blocks('ABCDEFG', 2, start=10))
        [(10, 'AB'), (12, 'CD'), (14, 'EF'), (16, 'G')]

        >>> list(chop_blocks('ABCDEFG', 4, 3, 10))
        [(13, 'A'), (14, 'BCDE'), (18, 'FG')]
    """
    offset = start + align_base
    for chunk in chop(items, window, align_base):
        yield (offset, chunk)
        offset += len(chunk)


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


def check_sequence(blocks):
    r"""Checks if a sequence of blocks is valid.

    Returns:
        :obj:`bool`: The sequence is made of non-overlapping blocks, sorted
            by start address.

    Examples:
        >>> check_sequence([(1, 'ABC'), (6, 'xyz')])
        True

        >>> check_sequence([(1, 'ABC'), (2, 'xyz')])
        False

        >>> check_sequence([(6, 'ABC'), (1, 'xyz')])
        False
    """
    last_endex = None
    for start, items in blocks:
        if last_endex is not None and start < last_endex:
            return False
        last_endex = start + len(items)
    else:
        return True


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
        |   |[A | B | C | D]|   |[$]|   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+---+---+
        |   | 0 | 0 | 0 | 0 |   | 1 |   | 2 | 2 | 2 |   |
        +---+---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
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
        |   |[A | B | C | D]|   |[$]|   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 2 | 2 | 2 | 3 |
        +---+---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
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
        |   |[A | B | C | D]|   |[$]|   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 3 | 3 | 3 | 3 |
        +---+---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
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


def find(blocks, value, start=None, endex=None):
    r"""Finds the address of a substring.

    Arguments:
        blocks (:obj:`list` of block): A fast indexable sequence of
            non-overlapping blocks, sorted by address.
        value (:obj:`list` of items): Substring to find.
        start (:obj:`int`): Inclusive start of the searched range.
            If ``None``, the global inclusive start address is considered.
        endex (:obj:`int`): Exclusive end of the searched range.
            If ``None``, the global exclusive end address is considered.

    Returns:
        :obj:`int`: The address of the first substring equal to `value`.

    Raises:
        ValueError: Item not found

    Example:
        >>> blocks = [(1, 'ABCD'), (7, 'xyz')]
        >>> find(blocks, 'yz')
        8
        >>> find(blocks, '$', -1, 15)  #doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: item not found
    """
    for address, items in blocks:
        items_start = None if start is None else start - address
        items_endex = None if endex is None else endex - address
        try:
            offset = items.index(value, items_start, items_endex)
        except ValueError:
            pass
        else:
            return address + offset
    else:
        raise ValueError('item not found')


def read(blocks, start, endex, pattern=b'\0', join=b''.join):
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
        pattern (items): Pattern of items to fill the emptiness, if not null.
        join (callable): A function to join a sequence of items, if `pattern`
            is not null.

    Returns:
        :obj:`list` of block: A new list of blocks, with the same order of
            `blocks`.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10|
        +===+===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |[$]|   |[x | y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |   |   |[C | D]|   |[$]|   |[x | y]|   |
        +---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        >>> read(blocks, 3, 10, None)
        [(3, 'CD'), (6, '$'), (8, 'xy')]
        >>> read(blocks, 3, 10, '#', ''.join)
        [(3, 'CD'), (5, '#'), (6, '$'), (7, '#'), (8, 'xy')]
        >>> read(blocks, None, 10, None)
        [(1, 'ABCD'), (6, '$'), (8, 'xy')]
        >>> read(blocks, 3, None, None)
        [(3, 'CD'), (6, '$'), (8, 'xyz')]
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

    if pattern and index_start + 1 < index_endex:
        blocks = fill(blocks, start, endex, pattern, False, join)
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
        |   |[A | B | C | D]|   |[$]|   |[x | y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C]|   |   |   |   |   |[y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C]|   |   |   |   |   |[y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A]|   |[C]|   |   |   |   |   |[y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
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
        |   |[A | B | C | D]|   |[$]|   |[x | y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C]|[y | z]|   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C]|[y | z]|   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A]|[C]|[y | z]|   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
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
        |[A | B | C | D]|   |   |[x | y | z]|   |[$]|   |
        +---+---+---+---+---+---+---+---+---+---+---+---+
        |[A]|[1]|[B | C | D]|   |   |[x | y | z]|   |[$]|
        +---+---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(0, 'ABCD'), (6, 'xyz')]
        >>> blocks = insert(blocks, (10, '$'))
        >>> blocks = insert(blocks, (1, '1'))
        >>> blocks
        [(0, 'A'), (1, '1'), (2, 'BCD'), (7, 'xyz'), (11, '$')]
    """
    inserted_start, inserted_items = inserted
    inserted_length = len(inserted_items)
    inserted_endex = inserted_start + inserted_length

    if not inserted_items:
        return list(blocks)

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
        |   |[A | B | C | D]|   |[$]|   |[x | y]|
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |   |[1 | 2 | 3 | 4 | 5 | 6]|   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |[A | B]|[1 | 2 | 3 | 4 | 5 | 6]|[y]|
        +---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (6, '$'), (8, 'xy')]
        >>> write(blocks, (3, '123456'))
        [(1, 'AB'), (3, '123456'), (9, 'y')]
    """
    start, items = written
    endex = start + len(items)

    if not items:
        return list(blocks)

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

    if start == endex:
        return list(blocks)

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


def merge(blocks, join=b''.join):
    r"""Merges touching blocks.

    Arguments:
        blocks (:obj:`list` of block): A sequence of non-overlapping blocks,
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
        |[$]|   |   |   |   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |   |   |   |   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+
        |[$]|[B | C]|[E | F]|[5]|[x | y | z]|[9]|
        +---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [
        ...     (0, '0123456789'),
        ...     (0, 'ABCD'),
        ...     (3, 'EF'),
        ...     (0, '$'),
        ...     (6, 'xyz'),
        ... ]
        >>> collapse(blocks)
        [(5, '5'), (1, 'BC'), (3, 'EF'), (0, '$'), (9, '9'), (6, 'xyz')]
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


class SparseItems(object):
    r"""Sparse item blocks manager.

    This is an helper class to emulate a virtual space with sparse blocks of
    items, for example a virtual memory of :class:`str` blocks.

    Attributes:
        blocks (:obj:`list` of block): A sequence of non-overlapping blocks,
            sorted by address.
        items_type (class): Type of the items stored into blocks.
        items_join (callable): A function to join a sequence of items.
        autofill (items): Pattern for automatic fill, or ``None``.
        automerge (:obj:`bool`): Automatically merges touching blocks after
            operations that can alter attribute :attr:`blocks`.

    Arguments:
        items (iterable): An iterable to build the initial items block, by
            passing it to `items_type` as a constructor.
        start (:obj:`int`): Start address of the initial block, built if
            `items` is not ``None``.
        blocks (:obj:`list` of block): A sequence of non-overlapping blocks,
            sorted by address. The :attr:`blocks` attribute is assigned a
            shallow copy.
        items_type (class): see attribute :attr:`items_type`.
        items_join (callable): see attribute :attr:`items_join`.
        autofill (items): Pattern for automatic fill, or ``None``.
        automerge (:obj:`bool`): see attribute :attr:`automerge`.

    Raises:
        ValueError: Both `items` and `blocks` are not ``None``.

    Examples:
        >>> memory = SparseItems()
        >>> memory.blocks
        []

        >>> memory = SparseItems('Hello, World!', 5)
        >>> memory.blocks
        [(5, 'Hello, World!')]

    """
    def __init__(self, items=None, start=0, blocks=None,
                 items_type=bytes, items_join=b''.join,
                 autofill=None, automerge=True):

        if items is not None and blocks is not None:
            raise ValueError('cannot construct from both items and blocks')

        if items:
            items = items_type(items)
            blocks = [(start, items)]

        elif blocks:
            blocks = list(blocks)

        else:
            blocks = []

        if automerge:
            blocks = merge(blocks, items_join)

        self.blocks = blocks
        self.items_type = items_type
        self.items_join = items_join
        self.autofill = autofill
        self.automerge = automerge

    def __str__(self):
        r"""String representation.

        Returns:
            :obj:`str`: The :func:`str` applied to all the items from
                :attr:`blocks`. Emptiness around blocks is ignored.

        Examples:
        """
        return ''.join(str(items) for _, items in self.blocks)

    def __bool__(self):
        r"""Has any items.

        Returns:
            :obj:`bool`: Has any items.

        Examples:
            >>> memory = SparseItems()
            >>> bool(memory)
            False

            >>> memory = SparseItems('Hello, World!', 5)
            >>> bool(memory)
            True
        """
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

        Examples:
            >>> items = 'Hello, World!'
            >>> memory = SparseItems(items)
            >>> memory == items
            True
            >>> memory.shift(1)
            >>> memory == items
            False

            >>> items = 'Hello, World!'
            >>> memory = SparseItems(items)
            >>> blocks = [(0, items)]
            >>> memory == blocks
            True
            >>> memory == list(items)
            False
            >>> memory.shift(1)
            >>> memory == blocks
            False
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
        r"""Iterates over all the items.

        Yields:
            item: All the single items collected from all the :attr:`blocks`.
                Emptiness around blocks is ignored.

        Example:
            >>> memory = SparseItems()
            >>> memory.blocks = [(1, 'ABC'), (7, 'xyz')]
            >>> list(memory)
            ['A', 'B', 'C', 'x', 'y', 'z']
        """
        for _, items in self.blocks:
            for item in items:
                yield item

    def __reversed__(self):
        r"""Iterates over all the items, in reverse.

        Yields:
            item: All the single items collected from all the :attr:`blocks`,
                in reverse order. Emptiness around blocks is ignored.

        Example:
            >>> memory = SparseItems()
            >>> memory.blocks = [(1, 'ABC'), (7, 'xyz')]
            >>> list(reversed(memory))
            ['z', 'y', 'x', 'C', 'B', 'A']
        """
        for _, items in reversed(self.blocks):
            for item in reversed(items):
                yield item

    def __add__(self, value):
        r"""Concatenates items.

        Arguments:
            value (:obj:`SparseItems` or items or :obj:`list` of block):
                Items to append at the end of the current virtual space.
                If instance of :class:`list`, it is interpreted as a sequence
                of non-overlapping blocks, sorted by start address.

        Returns:
            :obj:`SparseItems`: A new space with the items concatenated.
        """
        cls = type(self)
        result = cls(automerge=self.automerge,
                     items_type=self.items_type,
                     items_join=self.items_join)
        result.blocks = list(self.blocks)
        result += value
        return result

    def __iadd__(self, value):
        r"""Concatenates items.

        Arguments:
            value (:obj:`SparseItems` or items or :obj:`list` of block):
                Items to append at the end of the current virtual space.
                If instance of :class:`list`, it is interpreted as a sequence
                of non-overlapping blocks, sorted by start address.

        Returns:
            :obj:`SpraseItems`: `self`.
        """
        blocks = self.blocks

        if isinstance(value, SparseItems):
            if value is self:
                value.blocks = list(blocks)  # guard extend() over iter()

            offset = self.endex
            blocks.extend((start + offset, items)
                          for start, items in value.blocks)

        elif isinstance(value, list):
            if value:
                offset = self.endex
                blocks.extend((start + offset, items)
                              for start, items in value)

        else:
            if blocks:
                start, items = blocks[-1]
                blocks[-1] = (start, items + value)
            else:
                blocks.append((0, value))

        if self.automerge:
            blocks = merge(blocks, join=self.items_join)

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
        cls = type(self)
        result = cls(automerge=self.automerge,
                     items_type=self.items_type,
                     items_join=self.items_join)
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
            :obj:`SpraseItems`: `self`.
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
            repeated = merge(repeated, join=self.items_join)

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

        Raises:
            ValueError: Item not found
        """
        length = self.endex
        start = straighten_index(start, length)
        endex = straighten_index(endex, length)
        address = find(self.blocks, value, start, endex)
        return address

    def __contains__(self, value):
        r"""Checks if some value is contained.

        Arguments:
            value (item): Value to find.

        Returns:
            :obj:`bool`: Values is contained.

        Example:
            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.blocks = [(1, 'ABC'), (5, '123'), (9, 'xyz')]
            >>> '23' in memory
            True
            >>> 'y' in memory
            True
            >>> '$' in memory
            False
        """
        try:
            find(self.blocks, value)
        except ValueError:
            return False
        else:
            return True

    def count(self, value):
        r"""Counts items.

        Arguments:
            value (item): Reference value to count.

        Returns:
            :obj:`int`: The number of items equal to `value`.

        Example:
            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.blocks = [(1, 'ABC'), (7, 'Bat'), (12, 'tab')]
            >>> memory.count('a')
            2
        """
        return sum(items.count(value) for _, items in self.blocks)

    def __getitem__(self, key):
        r"""Reads data.

        Arguments:
            key (:obj:`slice` or :obj:`int`): Selection range or address.
                If it is a :obj:`slice` with `step` instance of
                :attr:`items_type`, then it is interpreted as the fill
                pattern.

        Returns:
            items: Items from the given range.

        Note:
            Retrieving an absolute address (`key` is :obj:`int`) actually
            returns an :attr:`items_type` with unitary length.

        Note:
            This method is not optimized for a :class:`slice` where its `step`
            is an :obj:`int` different from 1.

        Example:
            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
            >>> memory[9]
            'y'
            >>> memory[-2]
            'y'
            >>> memory[:3]
            'AB'
            >>> memory[-2:]
            'yz'
            >>> memory[3:10]
            Traceback (most recent call last):
                ...
            ValueError: contiguous slice not found
            >>> memory[3:10:'.']
            'CD.$.xy'
            >>> memory[memory.endex]
            ''
        """
        blocks = self.blocks

        if isinstance(key, slice):
            start, endex, step = key.start, key.stop, key.step
            length = self.endex
            if start is None:
                start = self.start
            if endex is None:
                endex = self.endex
            start, endex, step = straighten_slice(start, endex, step, length)

            if not step and self.autofill:
                step = self.autofill

            if isinstance(step, self.items_type):
                blocks = read(blocks, start, endex, step, self.items_join)
                blocks = fill(blocks, pattern=step, join=self.items_join)
                items = self.items_join(items for _, items in blocks)
                return items

            else:
                if step is None:
                    for address, items in blocks:
                        if address <= start <= endex <= address + len(items):
                            return items[(start - address):(endex - address)]
                    else:
                        raise ValueError('contiguous slice not found')
                else:
                    raise NotImplementedError((start, endex, step))  # TODO
        else:
            key = key.__index__()
            if key < 0:
                key %= self.endex

            index = locate_at(blocks, key)
            if index is None:
                return self.items_type()
            else:
                address, items = blocks[index]
                key -= address
                return items[key:(key + 1)]

    def __setitem__(self, key, value):
        r"""Writes data.

        Arguments:
            key (:obj:`slice` or :obj:`int`): Selection range or address.
            value (items): Items to write at the selection address.
                If `value` is null, the range is cleared.

        Note:
            Setting a single item requires `value` to be of :attr:`items_type`
            with unitary length.

        Note:
            This method is not optimized for a :class:`slice` where its `step`
            is an :obj:`int` different from 1.

        Examples:
            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.blocks = [(5, 'ABC'), (9, 'xyz')]
            >>> memory[7:10] = None
            >>> memory.blocks
            [(5, 'A'), (10, 'yz')]
            >>> memory[7] = 'C'
            >>> memory[-3] = 'x'
            >>> memory.blocks == blocks
            True

            >>> memory = SparseItems(items_type=str, items_join=''.join,
            ...                      automerge=False)
            >>> memory.blocks = [(5, 'ABC'), (9, 'xyz')]
            >>> memory[0:4] = '$'
            >>> memory.blocks
            [(0, '$'), (2, 'ABC'), (6, 'xyz')]
            >>> memory[4:7] = '45678'
            >>> memory.blocks
            [(0, '$'), (2, 'AB'), (4, '456'), (7, '78'), (9, 'yz')]
            >>> memory[6:8] = '<>'
            >>> memory.blocks
            [(0, '$'), (2, 'AB'), (4, '45'), (6, '<>'), (8, '8'), (9, 'yz')]
        """
        blocks = self.blocks

        if isinstance(key, slice):
            start, endex, step = key.start, key.stop, key.step
            length = self.endex
            start, endex, step = straighten_slice(start, endex, step, length)

            if value:
                if step is None or step == 1:
                    length = len(value)

                    if length < endex - start:
                        blocks = delete(blocks, start + length, endex)
                        blocks = write(blocks, (start, value))

                    elif endex - start < length:
                        split = endex - start
                        blocks = write(blocks, (start, value[:split]))
                        blocks = insert(blocks, (endex, value[split:]))

                    else:
                        blocks = write(blocks, (start, value))
                else:
                    raise NotImplementedError((start, endex, step))  # TODO
            else:
                blocks = clear(blocks, start, endex)
        else:
            key = key.__index__()
            if key < 0:
                key %= self.endex

            if value:
                if len(value) != 1:
                    raise ValueError('not a single item')
                blocks = write(blocks, (key, value))
            else:
                blocks = clear(blocks, key, key + 1)

        if self.automerge:
            blocks = merge(blocks, join=self.items_join)

        self.blocks = blocks

    def __delitem__(self, key):
        r"""Deletes data.

        Arguments:
            key (:obj:`slice` or :obj:`int`): Deletion range or address.

        Note:
            This method is not optimized for a :class:`slice` with its `step`
            different from either ``None`` or 1.

        Examples:
            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
            >>> del memory[4:9]
            >>> memory.blocks
            [(1, 'ABCyz')]

            >>> memory = SparseItems(items_type=str, items_join=''.join,
            ...                      automerge=False)
            >>> memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
            >>> del memory[4:9]
            >>> memory.blocks
            [(1, 'ABC'), (4, 'yz')]

            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
            >>> del memory[-2]
            >>> memory.blocks
            [(1, 'ABCD'), (6, '$'), (8, 'xz')]
            >>> del memory[3]
            >>> memory.blocks
            [(1, 'ABD'), (5, '$'), (7, 'xz')]
        """
        blocks = self.blocks

        if isinstance(key, slice):
            start, endex, step = key.start, key.stop, key.step
            length = self.endex
            start, endex, step = straighten_slice(start, endex, step, length)

            if step is None or step == 1:
                blocks = delete(blocks, start, endex)
            else:
                raise NotImplementedError((start, endex, step))  # TODO
        else:
            key = key.__index__()
            if key < 0:
                key %= self.endex
            blocks = delete(blocks, key, key + 1)

        if self.automerge:
            blocks = merge(blocks, join=self.items_join)

        self.blocks = blocks

    def append(self, value):
        r"""Appends some items.

        Arguments:
            value (items): Items to append.

        Note:
            Appending a single item requires `value` to be of
            :attr:`items_type` with unitary length.

        Examples:
            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.append('$')
            >>> memory.blocks
            [(0, '$')]

            >>> memory = SparseItems(items_type=list, items_join=''.join)
            >>> memory.append(3)
            >>> memory.blocks
            [(0, 3)]
        """
        blocks = self.blocks
        if blocks:
            start, items = blocks[-1]
            items = items + value
            blocks[-1] = (start, items)
        else:
            blocks = [(0, value)]
        self.blocks = blocks

    def extend(self, items):
        r"""Concatenates items.

        Equivalent to ``self += items``.

        Arguments:
            value (:obj:`SparseItems` or items or :obj:`list` of block):
                Items to append at the end of the current virtual space.
                If instance of :class:`list`, it is interpreted as a sequence
                of non-overlapping blocks, sorted by start address.
        """
        self += items

    @property
    def start(self):
        r"""Inclusive start address.

        This property holds the inclusive start address of the virtual space.
        By default, it is the current minimum inclusive start address of
        :attr:`blocks`.

        Returns:
            :obj:`int`: The inclusive start address, or 0.

        Examples:
            >>> SparseItems().start
            0

            >>> SparseItems(blocks=[(5, 'ABC'), (9, 'xyz')]).start
            5
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

        This property holds the exclusive end address of the virtual space.
        By default, it is the current minimum exclusive end address of
        :attr:`blocks`.

        Returns:
            :obj:`int`: The eclusive end address, or 0.

        Examples:
            >>> SparseItems().endex
            0

            >>> SparseItems(blocks=[(5, 'ABC'), (9, 'xyz')]).endex
            12
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

        Example:
            >>> memory = SparseItems(blocks=[(5, 'ABC'), (9, 'xyz')])
            >>> memory.shift(-2)
            >>> memory.blocks
            [(3, 'ABC'), (7, 'xyz')]
        """
        blocks = self.blocks
        blocks = shift(blocks, amount)
        self.blocks = blocks

    def read(self, start, endex, pattern=None):
        r"""Selects items from a range.

        Arguments:
            start (:obj:`int`): Inclusive start of the extracted range.
                If ``None``, the global inclusive start address is considered
                (i.e. :attr:`start`).
            endex (:obj:`int`): Exclusive end of the extracted range.
                If ``None``, the global exclusive end address is considered
                (i.e. :attr:`endex`).
            pattern (items): Pattern of items to fill the emptiness.
                If ``None``, the :attr:`autofill` attribute is used.

        Returns:
            items: Items from the selected range.

        See Also:
            :func:`select`
        """
        return self[start:endex:pattern]

    def clear(self, start=None, endex=None):
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

        Example:
            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.blocks = [(5, 'ABC'), (9, 'xyz')]
            >>> memory.clear(6, 10)
            >>> memory.blocks
            [(5, 'A'), (10, 'yz')]
        """
        blocks = self.blocks
        blocks = clear(blocks, start, endex)

        if self.automerge:
            blocks = merge(blocks, join=self.items_join)

        self.blocks = blocks

    def delete(self, start=None, endex=None):
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

        Example:
            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.blocks = [(5, 'ABC'), (9, 'xyz')]
            >>> memory.delete(6, 10)
            >>> memory.blocks
            [(5, 'Ayz')]
        """
        del self[start:endex]

    def pop(self, address=None):
        r"""Retrieves an item and deletes it.

        Arguments:
            address (:obj:`int`): Address of the item to remove; ``None``
                means the last one.

        Returns:
            items: The item at `address` if existing, null otherwise.

        Raises:
            IndexError: Pop from empty blocks.

        Example:
            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.blocks = [(5, 'ABC'), (9, 'xyz')]
            >>> memory.pop(6)
            'B'
            >>> memory.blocks
            [(5, 'AC'), (8, 'xyz')]
            >>> memory.pop(-2)
            'y'
            >>> memory.blocks
            [(5, 'AC'), (8, 'xz')]
            >>> memory.pop()
            'z'
            >>> memory.blocks
            [(5, 'AC'), (8, 'x')]
            >>> memory.pop(7)
            ''
            >>> memory.blocks
            [(5, 'AC'), (7, 'x')]
        """
        blocks = self.blocks
        if not blocks:
            raise IndexError('pop from empty blocks')

        endex = self.endex
        if address is None:
            address = endex - 1
        else:
            address = address.__index__()

        if address < 0:
            address %= endex
        index = locate_at(blocks, address)

        if index is None:
            value = self.items_type()
        else:
            start, items = blocks[index]
            value = items[address - start]

        blocks = delete(blocks, address, address + 1)

        if self.automerge:
            blocks = merge(blocks, join=self.items_join)

        self.blocks = blocks
        return value

    def remove(self, value):
        r"""Removes some data.

        Finds the first occurrence of `value` and deletes it.

        Arguments:
            value (items): Sequence of items to remove.

        Raises:
            ValueError: Item not found.

        Example:
            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.blocks = [(1, 'ABC'), (5, '123'), (9, 'xyz')]
            >>> memory.remove('23')
            >>> memory.blocks
            [(1, 'ABC'), (5, '1'), (7, 'xyz')]
            >>> memory.remove('y')
            >>> memory.blocks
            [(1, 'ABC'), (5, '1'), (7, 'xz')]
            >>> memory.remove('$')  #doctest: +ELLIPSIS
            Traceback (most recent call last):
                ...
            ValueError: item not found
        """
        blocks = self.blocks
        address = find(blocks, value)
        blocks = delete(blocks, address, address + len(value))

        if self.automerge:
            blocks = merge(blocks, join=self.items_join)

        self.blocks = blocks

    def insert(self, address, items):
        r"""Inserts data.

        Inserts a block, moving existing items after the insertion address by
        the length of the inserted block.

        Arguments:
            address (:obj:`int`): Address of the block to insert.
            items (items): Items of the block to insert.

        See Also:
            :func:`insert`

        Example:
            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.blocks = [(1, 'ABC'), (6, 'xyz')]
            >>> memory.insert(5, '123')
            >>> memory.blocks
            [(1, 'ABC'), (5, '123'), (9, 'xyz')]
        """
        blocks = self.blocks
        blocks = insert(blocks, (address, items))

        if self.automerge:
            blocks = merge(blocks, join=self.items_join)

        self.blocks = blocks

    def write(self, address, items):
        r"""Writes data.

        Arguments:
            address (:obj:`int`): Address of the block to write.
            items (items): Items of the block to write.

        See Also:
            :func:`write`

        Example:
            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.blocks = [(1, 'ABC'), (6, 'xyz')]
            >>> memory.write(5, '123')
            >>> memory.blocks
            [(1, 'ABC'), (5, '123z')]
        """
        blocks = self.blocks
        blocks = write(blocks, (address, items))

        if self.automerge:
            blocks = merge(blocks, join=self.items_join)

        self.blocks = blocks

    def fill(self, start=None, endex=None, pattern=None):
        r"""Fills emptiness between non-touching blocks.

        Arguments:
            pattern (items): Pattern of items to fill the emptiness.
                If ``None``, the :attr:`autofill` attribute is used.
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

        Example:
            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.blocks = [(1, 'ABC'), (6, 'xyz')]
            >>> memory.fill(pattern='123')
            >>> memory.blocks
            [(1, 'ABC23xyz')]

            >>> memory = SparseItems(items_type=str, items_join=''.join,
            ...                      autofill='123')
            >>> memory.blocks = [(1, 'ABC'), (6, 'xyz')]
            >>> memory.fill()
            >>> memory.blocks
            [(1, 'ABC23xyz')]
        """
        blocks = self.blocks
        if pattern is None:
            pattern = self.autofill
        blocks = fill(blocks, start, endex, pattern, join=self.items_join)

        if self.automerge:
            blocks = merge(blocks, join=self.items_join)

        self.blocks = blocks

    def merge(self):
        r"""Merges touching blocks.

        See Also:
            :func:`merge`

        Example:
            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.blocks = [(1, 'ABC'), (4, 'xyz')]
            >>> memory.merge()
            >>> memory.blocks
            [(1, 'ABCxyz')]
        """
        blocks = self.blocks
        blocks = merge(blocks, join=self.items_join)
        self.blocks = blocks

    def reverse(self):
        r"""Reverses data in-place.

        Example:
            >>> memory = SparseItems(items_type=str, items_join=''.join)
            >>> memory.blocks = [(1, 'ABC'), (5, '$'), (9, 'xyz')]
            >>> memory.reverse()
            >>> memory.blocks
            [(0, 'zyx'), (6, '$'), (8, 'CBA')]
        """
        blocks = self.blocks
        endex = self.endex
        result = []

        for block in reversed(blocks):
            block_start, block_items = block
            block_endex = block_start + len(block_items)
            reversed_items = block_items[::-1]
            reversed_start = endex - block_endex
            result.append((reversed_start, reversed_items))

        if self.automerge:
            result = merge(result, join=self.items_join)

        self.blocks = result
