# -*- coding: utf-8 -*-

from hexrec.utils import do_overlap


def overlap(block1, block2):
    r"""Checks if two blocks do overlap.

    Arguments:
        block1 (block): A block.
        block2 (block): Another block.

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

        >>> overlap((1, b'ABCD'), (5, b'xyz'))
        False

        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |   |[x | y | z]|   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+

        >>> overlap((1, b'ABCD'), (3, b'xyz'))
        True

    """
    start1, items1 = block1
    endex1 = start1 + len(items1)
    start2, items2 = block2
    endex2 = start2 + len(items2)
    return do_overlap(start1, endex1, start2, endex2)


def shift(blocks, amount):
    r"""Shifts the address of blocks.

    Arguments:
        blocks (:obj:`list` of block): Sequence of blocks to shift.
        amount (:obj:`int`): Signed amount of address shifting.

    Returns:
        :obj:`list`: A new list with shifted blocks.

    Example:
        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |   |[x | y | z]|
        +---+---+---+---+---+---+---+---+---+---+
        |[A | B | C | D]|   |   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, b'ABCD'), (7, b'xyz')]
        >>> shift(blocks, -1)
        [(0, b'ABCD'), (6, b'xyz')]
    """
    return [(start + amount, items) for start, items in blocks]


def clear(blocks, start, endex):
    r"""Deletes all the items within the specified range.

    Arguments:
        blocks (:obj:`list` of block): A sequence of blocks. Sequence
            generators supported.

    Returns:
        :obj:`list` of block: A new list of blocks.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10|
        +===+===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |[!]|   |[x | y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C]|(  |   |   |   |  )|[y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C]|   |   |   |   |   |[y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A]|   |[C]|   |   |   |   |   |[y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, b'ABCD'), (6, b'!'), (8, b'xyz')]
        >>> blocks = clear(blocks, 4, 9)
        >>> blocks = clear(blocks, 2, 2)
        >>> blocks = clear(blocks, 2, 3)
        >>> blocks
        [(1, b'A'), (3, b'C'), (9, b'yz')]
    """
    range_start = start
    range_endex = endex
    result = []
    append = result.append

    for block in blocks:
        start, items = block
        endex = start + len(items)

        if range_start <= start <= endex <= range_endex:
            pass  # fully deleted

        elif start < range_start < range_endex < endex:
            append((start, items[:(range_start - start)]))
            append((range_endex, items[-(endex - range_endex):]))

        elif start < range_start < endex <= range_endex:
            append((start, items[:(range_start - start)]))

        elif range_start <= start < range_endex < endex:
            append((range_endex, items[-(endex - range_endex):]))

        else:
            append(block)

    return result


def delete(blocks, start, endex):
    r"""Deletes the specified range.

    Arguments:
        blocks (:obj:`list` of block): A sequence of blocks. Sequence
            generators supported.

    Returns:
        :obj:`list` of block: A new list of blocks.

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

        >>> blocks = [(1, b'ABCD'), (6, b'!'), (8, b'xyz')]
        >>> blocks = delete(blocks, 4, 9)
        >>> blocks = delete(blocks, 2, 2)
        >>> blocks = delete(blocks, 2, 3)
        >>> blocks
        [(1, b'A'), (2, b'C'), (3, b'yz')]
    """
    range_start = start
    range_endex = endex
    result = []
    append = result.append

    for block in blocks:
        start, items = block
        endex = start + len(items)

        if range_start <= start <= endex <= range_endex:
            pass  # fully deleted

        elif start < range_start < range_endex < endex:
            append((start, items[:(range_start - start)]))
            append((range_start, items[-(endex - range_endex):]))

        elif start < range_start < endex <= range_endex:
            append((start, items[:(range_start - start)]))

        elif range_start <= start < range_endex < endex:
            append((range_start, items[-(endex - range_endex):]))

        elif range_endex <= start:
            append((start - (range_endex - range_start), items))

        else:
            append(block)

    return result


def insert(blocks, inserted):
    r"""Inserts a block into a sequence.

    Inserts a block into a sequence, moving existing items after the insertion
    address by the length of the inserted block.

    Arguments:
        blocks (:obj:`list` of block): An indexable sequence of
            non-overlapping blocks, sorted by address.
        inserted (block): Block to insert.

    Returns:
        :obj:`list` of block: A new list of blocks.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11| 12| 13| 14|
        +===+===+===+===+===+===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |   |   |[x | y | z]|   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C | D]|   |   |   |[x | y | z]|   |[1 | 3]|   |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
        |   |[A]|[2]|[B | C | D]|   |   |   |[x | y | z]|   |[1 | 3]|
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, b'ABCD'), (8, b'xyz')]
        >>> blocks = insert(blocks, (12, b'13'))
        >>> blocks = insert(blocks, (2, b'2'))
        >>> blocks
        [(1, b'A'), (2, b'2'), (3, b'BCD'), (9, b'xyz'), (13, b'13')]
    """
    inserted_start, inserted_items = inserted
    inserted_length = len(inserted_items)
    inserted_endex = inserted_start + inserted_length

    for pivot in range(len(blocks)):
        pivot_start, pivot_items = blocks[pivot]
        pivot_endex = pivot_start + len(pivot_items)

        if inserted_start <= pivot_start:
            before, after = blocks[:pivot], blocks[pivot:]

            after = [(start + inserted_length, items)
                     for start, items in after]

            result = before + [inserted] + after
            break

        elif pivot_start < inserted_start < pivot_endex:
            before, after = blocks[:pivot], blocks[(pivot + 1):]
            splitting = inserted_start - pivot_start

            patch = [(pivot_start, pivot_items[:splitting]),
                     (inserted_start, inserted_items),
                     (inserted_endex, pivot_items[splitting:])]

            after = [(start + inserted_length, items)
                     for start, items in after]

            result = before + patch + after
            break
    else:
        result = list(blocks)
        result.append(inserted)

    return result


def write(blocks, written):
    r"""Writes a block onto a sequence.

    Arguments:
        blocks (:obj:`list` of block): A sequence of non-overlapping blocks.
        written (block): Block to write.

    Returns:
        :obj:`list` of block: A new list of non-overlapping blocks.

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

        >>> blocks = [(1, b'ABCD'), (6, b'!'), (8, b'xy')]
        >>> write(blocks, (3, b'123456'))
        [(1, b'AB'), (9, b'y'), (3, b'123456')]
    """
    start, items = written
    endex = start + len(items)

    result = delete(blocks, start, endex)
    result.append(written)
    return result


def merge(blocks, invalid_start=-1, join=b''.join):
    r"""Merges a sequence of blocks.

    Touching blocks are merged into a single block.

    Arguments:
        blocks (:obj:`list` of block): An sequence of non-overlapping blocks,
            sorted by address. Sequence generators supported.
        invalid_start (:obj:`int`): An invalid start index, lesser than
            all the addresses within `blocks`.
        join (callable): A function to join a sequence of items.

    Returns:
        :obj:`list` of block: A new list of non-overlapping blocks, sorted by
            address.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11| 12| 13|
        +===+===+===+===+===+===+===+===+===+===+===+===+===+===+
        |   |[H | e | l | l | o | ,]|   |   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+
        |   |   |   |   |   |   |   |[ ]|   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+
        |   |   |   |   |   |   |   |   |[W | o | r | l | d]|   |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+
        |   |   |   |   |   |   |   |   |   |   |   |   |   |[!]|
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+
        |   |[H | e | l | l | o | ,]|[ ]|[W | o | r | l | d]|[!]|
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, b'Hello,'), (7, b' '), (8, b'World'), (13, b'!')]
        >>> merge(blocks)
        [(1, b'Hello, World!')]
    """
    result = []
    contiguous_items = []
    contiguous_start = None

    last_endex = invalid_start

    for block in blocks:
        start, items = block
        endex = start + len(items)

        if last_endex == start or not result:
            if not contiguous_items:
                contiguous_start = start
            contiguous_items.append(items)

        else:
            if contiguous_items:
                contiguous_items = join(contiguous_items)
                result.append((contiguous_start, contiguous_items))

            contiguous_items = []
            contiguous_start = None

        last_endex = endex

    if contiguous_items:
        contiguous_items = join(contiguous_items)
        result.append((contiguous_start, contiguous_items))

    return result


def collapse(blocks):
    r"""Collapses blocks of items.

    Given a sequence of blocks, they are modified so that a previous block
    does not overlap with the following ones.

    A block is ``(start, items)`` where `start` is the start address and
    `items` is the container of items (e.g. a :obj:`bytes` object).
    The length of the block is ``len(items)``.

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

        >>> collapse([
        ...     (0, '0123456789'),
        ...     (0, 'ABCD'),
        ...     (3, 'EF'),
        ...     (0, '!'),
        ...     (6, 'xyz'),
        ... ])
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


class SparseBlocks(object):  # TODO

    def __init__(self, blocks=None):
        self.blocks = [] if blocks is None else blocks

    def shift(self, amount):
        self.blocks = shift(self.blocks, amount)

    def delete(self, start, endex):
        self.blocks = delete(self.block, start, endex)

    def insert(self, block):
        self.blocks = insert(self.blocks, block)

    def write(self, block):
        self.blocks = write(self.blocks, block)

    def merge(self):
        self.blocks = merge(self.blocks)

    def collapse(self):
        self.blocks = collapse(self.blocks)
