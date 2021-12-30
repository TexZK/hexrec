# -*- coding: utf-8 -*-

# Copyright (c) 2013-2020, Andrea Zoppi
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

r"""Utilities for sparse blocks of data.

Blocks are a useful way to describe sparse linear data, for example strings,
chunks of bytes, lists, and so on.
In the case of strings, a string itself is a contiguous block of items
(*i.e.* characters).

The audience of this module are most importantly those who have to manage
sparse blocks of bytes, where a very broad addressing space (*e.g.* 4 GiB)
is used only in some sparse parts (*e.g.* physical memory addressing in a
microcontroller).

This module also provides the :obj:`Memory` class, which is a handy wrapper
around blocks, giving the user the flexibility of most operations of a
:obj:`bytearray` on sparse byte-like chunks.

A `block` is a tuple ``(start, items)`` where `start` is the start address and
`items` is the container of items (e.g. :obj:`bytes`, :obj:`str`,
:obj:`tuple`).  The length of the block is ``len(items)``.

In this module it is common to require *contiguous* blocks, *i.e.* blocks
in which a block ``b`` starts immediately after block ``a``:

+---+---+---+---+---+---+---+---+---+
| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
+===+===+===+===+===+===+===+===+===+
|   |[A | B | C]|   |   |   |   |   |
+---+---+---+---+---+---+---+---+---+
|   |   |   |   |[x | y | z]|   |   |
+---+---+---+---+---+---+---+---+---+

>>> a = (1, 'ABC')
>>> b = (4, 'xyz')

Instead, *overlapping* blocks have at least an addressed cell occupied by
more items:

+---+---+---+---+---+---+---+---+---+
| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
+===+===+===+===+===+===+===+===+===+
|   |[A | B | C]|   |   |   |   |   |
+---+---+---+---+---+---+---+---+---+
|   |   |   |[x | y | z]|   |   |   |
+---+---+---+---+---+---+---+---+---+
|[# | #]|   |   |   |   |   |   |   |
+---+---+---+---+---+---+---+---+---+
|   |   |[!]|   |   |   |   |   |   |
+---+---+---+---+---+---+---+---+---+

>>> a = (1, 'ABC')
>>> b = (3, 'xyz')
>>> c = (0, '##')
>>> d = (2, '!')

Contiguous blocks are *non-overlapping*.

*Spaced* blocks are also non-overlapping:

+---+---+---+---+---+---+---+---+---+
| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
+===+===+===+===+===+===+===+===+===+
|   |[A | B | C]|   |   |   |   |   |
+---+---+---+---+---+---+---+---+---+
|   |   |   |   |   |[x | y | z]|   |
+---+---+---+---+---+---+---+---+---+

>>> a = (1, 'ABC')
>>> b = (5, 'xyz')

This module often deals with *sequences* of blocks, typically :obj:`list`
objects containing blocks:

>>> seq = [(1, 'ABC'), (5, 'xyz')]

Sometimes *sequence generators* are allowed, in that blocks of the sequence
are yielded on-the-fly by a generator, like `seq_gen`:

>>> seq_gen = ((i, chr(i + 0x21) * 3) for i in range(0, 15, 5))
>>> list(seq_gen)
[(0, '!!!'), (5, '&&&'), (10, '+++')]

Other times it is required that sequences are ordered, which means that a
block ``b`` must follow a block ``a`` which end address is lesser than the
`start` of ``b``, like in:

>>> a = (1, 'ABC')
>>> b = (5, 'xyz')
>>> a[0] + len(a[1]) <= b[0]
True

"""
from typing import Callable
from typing import Collection
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union

from deprecated import deprecated

from .utils import AnyBytes
from .utils import chop
from .utils import do_overlap
from .utils import makefill
from .utils import straighten_index
from .utils import straighten_slice

Item = TypeVar('Item')
ItemSequence = Union[Sequence[Item], AnyBytes, Sequence[int], str]
ItemJoiner = Callable[[Iterable[ItemSequence]], ItemSequence]

Block = Tuple[int, ItemSequence]
BlockIterable = Iterable[Block]
BlockCollection = Collection[Block]
BlockSequence = Sequence[Block]
BlockList = List[Block]


def chop_blocks(
    items: ItemSequence,
    window: int,
    align_base: int = 0,
    start: int = 0,
) -> Iterator[Block]:
    r"""Chops a sequence of items into blocks.

    Iterates through the vector grouping its items into windows.

    Arguments:
        items (items):
            Sequence of items to chop.

        window (int):
            Window length.

        align_base (int):
            Offset of the first window.

        start (int):
            Start address.

    Yields:
        items: `items` slices of up to `window` elements.

    Examples:
        +---+---+---+---+---+---+---+---+---+
        | 9 | 10| 11| 12| 13| 14| 15| 16| 17|
        +===+===+===+===+===+===+===+===+===+
        |   |[A | B]|[C | D]|[E | F]|[G]|   |
        +---+---+---+---+---+---+---+---+---+

        >>> list(chop_blocks('ABCDEFG', 2, start=10))
        [(10, 'AB'), (12, 'CD'), (14, 'EF'), (16, 'G')]

        ~~~

        +---+---+---+---+---+---+---+---+---+
        | 12| 13| 14| 15| 16| 17| 18| 19| 20|
        +===+===+===+===+===+===+===+===+===+
        |   |[A]|[B | C | D | E]|[F | G]|   |
        +---+---+---+---+---+---+---+---+---+

        >>> list(chop_blocks('ABCDEFG', 4, 3, 10))
        [(13, 'A'), (14, 'BCDE'), (18, 'FG')]
    """
    offset = start + align_base
    for chunk in chop(items, window, align_base):
        yield offset, chunk
        offset += len(chunk)


def overlap(
    block1: Block,
    block2: Block,
) -> bool:
    r"""Checks if two blocks do overlap.

    Arguments:
        block1 (block):
            A block.

        block2 (block):
            Another block.

    Returns:
        bool: The blocks do overlap.

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

        ~~~

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


def check_sequence(
    blocks: BlockIterable,
) -> bool:
    r"""Checks if a sequence of blocks is valid.

    Checks that the sequence is ordered and non-overlapping.

    Arguments:
        blocks (list of blocks):
            A sequence of blocks.

    Returns:
        bool: Valid sequence.

    Examples:
        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C]|   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |   |   |   |   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+

        >>> check_sequence([(1, 'ABC'), (6, 'xyz')])
        True

        ~~~

        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C]|   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |[x | y | z]|   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+

        >>> check_sequence([(1, 'ABC'), (2, 'xyz')])
        False

        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |   |   |   |   |   |[A | B | C]|   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |[x | y | z]|   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+

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


def sorting(
    block: Block,
) -> int:
    r"""Block sorting key.

    Allows to sort blocks so that blocks with the same start address are kept
    in the same order as per `blocks`.

    Python provides stable sorting functions, so it is sufficient to pass only
    the start address to them.

    Arguments:
        block (block):
            Block under examination.

    Returns:
        int: The start address of the block.

    Example:
        For reference:

        - ``ord('!')`` = 33
        - ``ord('1')`` = 49
        - ``ord('A')`` = 65

        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |   |[A | B | C]|   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |   |   |   |   |   |[>]|   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |[!]|   |   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |[<]|   |   |   |   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |[1 | 1]|   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(2, 'ABC'), (7, '>'), (2, '!'), (0, '<'), (2, '11')]
        >>> blocks.sort(key=sorting)
        >>> blocks
        [(0, '<'), (2, 'ABC'), (2, '!'), (2, '11'), (7, '>')]

        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |[<]|   |   |   |   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |[A | B | C]|   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |[!]|   |   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |[1 | 1]|   |   |   |   |   |   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |   |   |   |   |   |   |[>]|   |   |
        +---+---+---+---+---+---+---+---+---+---+
    """
    return block[0]


def locate_at(
    blocks: BlockSequence,
    address: int,
) -> Optional[int]:
    r"""Locates the block enclosing an address.

    Returns the index of the block enclosing the given address.

    Arguments:
        blocks (list of blocks):
            Sequence of non-overlapping blocks, sorted by address.

        address (int):
            Address of the target item.

    Returns:
        int: Block index if found, ``None`` otherwise.

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


def locate_start(
    blocks: BlockSequence,
    address: int,
) -> int:
    r"""Locates the first block inside of an address range.

    Returns the index of the first block whose start address is greater than
    or equal to `address`.

    Arguments:
        blocks (list of blocks):
            Sequence of non-overlapping blocks, sorted by address.

        address (int):
            Inclusive start address of the scanned range.

    Returns:
        int: First block index since `address`.

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


def locate_endex(
    blocks: BlockSequence,
    address: int,
) -> int:
    r"""Locates the first block after an address range.

    Returns the index of the first block whose end address is lesser than or
    equal to `address`.

    Arguments:
        blocks (list of blocks):
            Sequence of non-overlapping blocks, sorted by address.

        address (int):
            Exclusive end address of the scanned range.

    Returns:
        int: First block index after `address`.

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


def shift(
    blocks: BlockSequence,
    amount: int,
) -> BlockList:
    r"""Shifts the address of blocks.

    Arguments:
        blocks (list of blocks):
            Sequence of blocks to shift.

        amount (int):
            Signed amount of address shifting.

    Returns:
        list of blocks: A new list with shifted blocks.

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


def find(
    blocks: BlockSequence,
    value: ItemSequence,
    start: int = None,
    endex: int = None,
) -> int:
    r"""Finds the address of a substring.

    Arguments:
        blocks (list of blocks):
            Sequence of non-overlapping blocks, sorted by address.

        value (items):
            Substring to find.

        start (int):
            Inclusive start of the searched range.
            If ``None``, the global inclusive start address is considered.

        endex (int):
            Exclusive end of the searched range.
            If ``None``, the global exclusive end address is considered.

    Returns:
        int: The address of the first substring equal to `value`.

    Raises:
        :obj:`ValueError` Item not found

    Example:
        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |   |[x | y | z]|
        +---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (7, 'xyz')]
        >>> find(blocks, 'yz')
        8
        >>> find(blocks, '$', -1, 15)  #doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        :obj:`ValueError` item not found
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


@deprecated
def read(
    blocks: BlockSequence,
    start: Optional[int],
    endex: Optional[int],
    pattern: Optional[ItemSequence] = b'\0',
    join: ItemJoiner = b''.join,
) -> BlockList:
    r"""Selects blocks from a range.

    Arguments:
        blocks (list of blocks):
            Sequence of non-overlapping blocks, sorted by address.

        start (int):
            Inclusive start of the extracted range.
            If ``None``, the global inclusive start address is considered
            (i.e. that of the first block).

        endex (int):
            Exclusive end of the extracted range.
            If ``None``, the global exclusive end address is considered
            (i.e. that of the last block).

        pattern (items):
            Pattern of items to fill the emptiness, if not null.

        join (callable):
            A function to join a sequence of items, if `pattern` is not null.

    Returns:
        list of blocks: A new list of blocks as per `blocks`.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10|
        +===+===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |[$]|   |[x | y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |   |   |[C | D]|   |[$]|   |[x | y]|   |
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |   |   |[C | D]|[#]|[$]|[#]|[x | y]|   |
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C | D]|   |[$]|   |[x | y]|   |
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |   |   |[C | D]|   |[$]|   |[x | y | z]|
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
        >>> read(blocks, 5, 6, None)
        []
    """
    return crop(blocks, start, endex, pattern, join)


def crop(
    blocks: BlockSequence,
    start: Optional[int],
    endex: Optional[int],
    pattern: Optional[ItemSequence] = b'\0',
    join: ItemJoiner = b''.join,
) -> BlockList:
    r"""Selects blocks from a range.

    Arguments:
        blocks (list of blocks):
            Sequence of non-overlapping blocks, sorted by address.

        start (int):
            Inclusive start of the extracted range.
            If ``None``, the global inclusive start address is considered
            (i.e. that of the first block).

        endex (int):
            Exclusive end of the extracted range.
            If ``None``, the global exclusive end address is considered
            (i.e. that of the last block).

        pattern (items):
            Pattern of items to fill the emptiness, if not null.

        join (callable):
            A function to join a sequence of items, if `pattern` is not null.

    Returns:
        list of blocks: A new list of blocks as per `blocks`.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10|
        +===+===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C | D]|   |[$]|   |[x | y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |   |   |[C | D]|   |[$]|   |[x | y]|   |
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |   |   |[C | D]|[#]|[$]|[#]|[x | y]|   |
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C | D]|   |[$]|   |[x | y]|   |
        +---+---+---+---+---+---+---+---+---+---+---+
        |   |   |   |[C | D]|   |[$]|   |[x | y | z]|
        +---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
        >>> crop(blocks, 3, 10, None)
        [(3, 'CD'), (6, '$'), (8, 'xy')]
        >>> crop(blocks, 3, 10, '#', ''.join)
        [(3, 'CD'), (5, '#'), (6, '$'), (7, '#'), (8, 'xy')]
        >>> crop(blocks, None, 10, None)
        [(1, 'ABCD'), (6, '$'), (8, 'xy')]
        >>> crop(blocks, 3, None, None)
        [(3, 'CD'), (6, '$'), (8, 'xyz')]
        >>> crop(blocks, 5, 6, None)
        []
    """
    if start is None:
        if not blocks:
            return []
        start, _ = blocks[0]
    range_start = start

    if endex is None:
        if not blocks:
            return []
        start, items = blocks[-1]
        endex = start + len(items)
    range_endex = endex

    if endex <= start:
        return []

    index_start = locate_start(blocks, range_start)
    index_endex = locate_endex(blocks, range_endex)

    if pattern and index_start + 1 < index_endex:
        blocks = flood(blocks, start, endex, pattern, False, join)
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

#        else:  # range_endex <= start
#            pass  # fully outside

    result = blocks_inside
    return result


def clear(
    blocks: BlockSequence,
    start: Optional[int],
    endex: Optional[int],
) -> BlockList:
    r"""Clears a range.

    Arguments:
        blocks (list of blocks):
            Sequence of non-overlapping blocks, sorted by address.

        start (int):
            Inclusive start of the cleared range.
            If ``None``, the global inclusive start address is considered
            (i.e. that of the first block).

        endex (int):
            Exclusive end of the cleared range.
            If ``None``, the global exclusive end address is considered
            (i.e. that of the last block).

    Returns:
        list of blocks: A new list of blocks as per `blocks`.

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
        if not blocks:
            return []
        start, _ = blocks[0]
    range_start = start

    if endex is None:
        if not blocks:
            return []
        start, items = blocks[-1]
        endex = start + len(items)
    range_endex = endex

    if endex <= start:
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
            append((range_endex, items[(range_endex - endex):]))

        elif start < range_start < endex <= range_endex:
            append((start, items[:(range_start - start)]))

        elif range_start <= start < range_endex < endex:
            append((range_endex, items[(range_endex - endex):]))

        else:  # range_endex <= start
            append((start, items))

    result = []
    result.extend(blocks_before)
    result.extend(blocks_inside)
    result.extend(blocks_after)
    return result


def delete(
    blocks: BlockSequence,
    start: Optional[int],
    endex: Optional[int],
) -> BlockList:
    r"""Deletes a range.

    Arguments:
        blocks (list of blocks):
            Sequence of non-overlapping blocks, sorted by address.

        start (int):
            Inclusive start of the deleted range.
            If ``None``, the global inclusive start address is considered
            (i.e. that of the first block).

        endex (int):
            Exclusive end of the deleted range.
            If ``None``, the global exclusive end address is considered
            (i.e. that of the last block).

    Returns:
        list of blocks: A new list of blocks as per `blocks`.

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

        else:  # range_endex <= start
            append((start - range_length, items))

    blocks_after = shift(blocks_after, -range_length)
    result = []
    result.extend(blocks_before)
    result.extend(blocks_inside)
    result.extend(blocks_after)
    return result


def reserve(
    blocks: BlockSequence,
    address: int,
    length: int,
) -> BlockList:
    r"""Inserts some reserved space into a sequence.

    Inserts reserved space into a sequence, moving existing items after the
    insertion address by the reserved length.

    Arguments:
        blocks (list of blocks):
            Sequence of non-overlapping blocks, sorted by address.

        address (int):
            Start address of the reserved space.

        length (int):
            Reserved space to insert.

    Returns:
        list of blocks: Non-overlapping blocks, sorted by start address.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11|
        +===+===+===+===+===+===+===+===+===+===+===+===+
        |[A | B | C | D]|   |   |[x | y | z]|   |   |   |
        +---+---+---+---+---+---+---+---+---+---+---+---+
        |[A | B | C | D]|   |   |[x | y]|   [z]|   |[$]|
        +---+---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(0, 'ABCD'), (6, 'xyz')]
        >>> blocks = reserve(blocks, 10, 1)
        >>> blocks = reserve(blocks, 8, 1)
        >>> blocks
        [(0, 'ABCD'), (6, 'xy'), (9, 'z')]
    """
    inserted_start = address
    inserted_length = length
    inserted_endex = inserted_start + inserted_length

    if length <= 0:
        return list(blocks)

    pivot_index = locate_at(blocks, inserted_start)

    if pivot_index is None:
        pivot_index = locate_endex(blocks, inserted_start)
        blocks_before = blocks[:pivot_index]
        blocks_after = blocks[pivot_index:]
        blocks_inside = []

    else:
        blocks_before = blocks[:pivot_index]
        blocks_after = blocks[(pivot_index + 1):]
        pivot_start, pivot_items = blocks[pivot_index]

        if pivot_start == inserted_start:
            blocks_inside = [(pivot_start + inserted_length, pivot_items)]
        else:
            offset = inserted_start - pivot_start
            blocks_inside = [(pivot_start, pivot_items[:offset]),
                             (inserted_endex, pivot_items[offset:])]

    blocks_after = shift(blocks_after, inserted_length)
    result = []
    result.extend(blocks_before)
    result.extend(blocks_inside)
    result.extend(blocks_after)
    return result


def insert(
    blocks: BlockSequence,
    inserted: Block,
) -> BlockList:
    r"""Inserts a block into a sequence.

    Inserts a block into a sequence, moving existing items after the insertion
    address by the length of the inserted block.

    Arguments:
        blocks (list of blocks):
            Sequence of non-overlapping blocks, sorted by address.

        inserted (block):
            Block to insert.

    Returns:
        list of blocks: Non-overlapping blocks, sorted by start address.

    Example:
        +---+---+---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11|
        +===+===+===+===+===+===+===+===+===+===+===+===+
        |[A | B | C | D]|   |   |[x | y | z]|   |   |   |
        +---+---+---+---+---+---+---+---+---+---+---+---+
        |[A | B | C | D]|   |   |[x | y | z]|   |[$]|   |
        +---+---+---+---+---+---+---+---+---+---+---+---+
        |[A | B | C | D]|   |   |[x | y]|[1]|[z]|   |[$]|
        +---+---+---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(0, 'ABCD'), (6, 'xyz')]
        >>> blocks = insert(blocks, (10, '$'))
        >>> blocks = insert(blocks, (8, '1'))
        >>> blocks
        [(0, 'ABCD'), (6, 'xy'), (8, '1'), (9, 'z'), (11, '$')]
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
            offset = inserted_start - pivot_start
            blocks_inside = [(pivot_start, pivot_items[:offset]),
                             (inserted_start, inserted_items),
                             (inserted_endex, pivot_items[offset:])]

    blocks_after = shift(blocks_after, inserted_length)
    result = []
    result.extend(blocks_before)
    result.extend(blocks_inside)
    result.extend(blocks_after)
    return result


def write(
    blocks: BlockSequence,
    written: Block,
) -> BlockList:
    r"""Writes a block onto a sequence.

    Arguments:
        blocks (list of blocks):
            Sequence of non-overlapping blocks, sorted by address.

        written (block):
            Block to write.

    Returns:
        list of blocks: Non-overlapping blocks, sorted by start address.

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


def fill(
    blocks: BlockSequence,
    start: Optional[int] = None,
    endex: Optional[int] = None,
    pattern: ItemSequence = b'\0',
    join: ItemJoiner = b''.join,
) -> BlockList:
    r"""Overwrites a range with a pattern.

    Arguments:
        blocks (list of blocks):
            Sequence of non-overlapping blocks, sorted by address.

        pattern (items):
            Pattern of items to fill the emptiness.

        start (int):
            Inclusive start of the filled range.
            If ``None``, the global inclusive start address is considered
            (i.e. that of the first block).

        endex (int):
            Exclusive end of the filled range.
            If ``None``, the global exclusive end address is considered
            (i.e. that of the last block).

        join (callable):
            A function to join a sequence of items.

    Returns:
        list of blocks: Sequence of blocks.

    Examples:
        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C]|   |   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |[1 | 2 | 3 | 1 | 2 | 3 | 1 | 2]|   |
        +---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABC'), (6, 'xyz')]
        >>> fill(blocks, pattern='123', join=''.join)
        [(1, '12312312')]

        ~~~

        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C]|   |   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+
        |[1 | 2 | 3 | 1 | 2]|   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABC'), (6, 'xyz')]
        >>> fill(blocks, 0, 5, '123', join=''.join)
        [(0, '12312'), (6, 'xyz')]

        ~~~

        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C]|   |   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C]|   |[1 | 2 | 3 | 1 | 2]|
        +---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABC'), (6, 'xyz')]
        >>> fill(blocks, 5, 10, '123', join=''.join)
        [(1, 'ABC'), (5, '12312')]
    """
    if start is None and endex is None and not blocks:
        raise ValueError('no blocks')
    if start is None:
        start = blocks[0][0]
    if endex is None:
        block_start, block_items = blocks[-1]
        endex = block_start + len(block_items)

    if start == endex:
        return list(blocks)

    items = makefill(pattern, 0, max(0, endex - start), join)
    result = write(blocks, (start, items))
    return result


def flood(
    blocks: BlockSequence,
    start: Optional[int] = None,
    endex: Optional[int] = None,
    pattern: ItemSequence = b'\0',
    flood_only: bool = False,
    join: ItemJoiner = b''.join,
) -> BlockList:
    r"""Fills emptiness between non-touching blocks.

    Returns a List of the filling blocks, including the existing blocks if
    `flood_only` is ``False``.

    Arguments:
        blocks (list of blocks):
            Sequence of non-overlapping blocks, sorted by address.

        pattern (items):
            Pattern of items to fill the emptiness.

        start (int):
            Inclusive start of the filled range.
            If ``None``, the global inclusive start address is considered
            (i.e. that of the first block).

        endex (int):
            Exclusive end of the filled range.
            If ``None``, the global exclusive end address is considered
            (i.e. that of the last block).

        flood_only (bool):
            Returns only the filling blocks.

        join (callable):
            A function to join a sequence of items.

    Returns:
        list of blocks: Filling blocks.

    Example:
        +---+---+---+---+---+---+---+---+---+---+
        | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
        +===+===+===+===+===+===+===+===+===+===+
        |   |[A | B | C]|   |   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C]|[1 | 2]|[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+
        |[1]|[A | B | C]|[2]|   |[x | y | z]|   |
        +---+---+---+---+---+---+---+---+---+---+
        |   |[A | B | C]|   |[1]|[x | y | z]|[2]|
        +---+---+---+---+---+---+---+---+---+---+

        >>> blocks = [(1, 'ABC'), (6, 'xyz')]
        >>> flood(blocks, pattern='123', join=''.join)
        [(1, 'ABC'), (4, '12'), (6, 'xyz')]
        >>> flood(blocks, pattern='123', fill_only=True, join=''.join)
        [(4, '23')]
        >>> flood(blocks, 0, 5, '123', join=''.join)
        [(0, '1'), (1, 'ABC'), (4, '2'), (6, 'xyz')]
        >>> flood(blocks, 5, 10, '123', join=''.join)
        [(1, 'ABC'), (5, '1'), (6, 'xyz'), (9, '2')]
    """
    if start is None and endex is None and not blocks:
        raise ValueError('no blocks')
    if start is None:
        start = blocks[0][0]
    if endex is None:
        block_start, block_items = blocks[-1]
        endex = block_start + len(block_items)
    with_blocks = not flood_only

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
            pattern_start = (last_endex - start) % pattern_length
            pattern_endex = pattern_start + block_start - last_endex
            items = makefill(pattern, pattern_start, pattern_endex, join=join)
            blocks_inside.append((last_endex, items))

        if with_blocks:
            blocks_inside.append(block)

        last_endex = block_start + len(block_items)

    if last_endex < endex:
        pattern_start = (last_endex - start) % pattern_length
        pattern_endex = pattern_start + endex - last_endex
        items = makefill(pattern, pattern_start, pattern_endex, join)
        blocks_inside.append((last_endex, items))

    if with_blocks:
        result = []
        result.extend(blocks_before)
        result.extend(blocks_inside)
        result.extend(blocks_after)
    else:
        result = blocks_inside
    return result


def merge(
    blocks: BlockIterable,
    join: Optional[ItemJoiner] = None,
) -> BlockList:
    r"""Merges touching blocks.

    Arguments:
        blocks (list of blocks):
            Sequence of non-overlapping blocks, sorted by address.

        join (callable):
            A function to join a sequence of items.
            If ``None``, defaults to ``bytes().join``.

    Returns:
        list of blocks: Non-overlapping blocks, sorted by address.

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
    if join is None:
        join = b''.join
    result = []
    contiguous_items = []
    contiguous_start = None
    last_endex = None

    for block in blocks:
        start, items = block
        if items:
            endex = start + len(items)

            if last_endex is None or last_endex == start:
                if not contiguous_items:
                    contiguous_start = start
                contiguous_items.append(items)

            else:
                contiguous_items = join(contiguous_items)
                result.append((contiguous_start, contiguous_items))

                contiguous_items = [items]
                contiguous_start = start

            last_endex = endex

    if contiguous_items:
        contiguous_items = join(contiguous_items)
        result.append((contiguous_start, contiguous_items))

    return result


def collapse(
    blocks: BlockIterable,
) -> BlockList:
    r"""Collapses blocks of items.

    Given a sequence of blocks, they are modified so that a previous block
    does not overlap with the following ones.

    Arguments:
        blocks (list of blocks):
            A sequence of blocks. No address ordering required.

    Returns:
        list of blocks: A new list of non-overlapping blocks.

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
    append = result.append
    last_endex = None

    for block in blocks:
        start1, items1 = block
        if items1:
            endex1 = start1 + len(items1)

            if last_endex is None or last_endex <= start1:
                last_endex = endex1

            else:
                for i in range(len(result)):
                    start2, items2 = result[i]
                    endex2 = start2 + len(items2)

                    if start1 <= start2 <= endex2 <= endex1:
                        result[i] = (start2, None)

                    elif start2 < start1 < endex2 <= endex1:
                        result[i] = (start2, items2[:(start1 - start2)])

                    elif start1 <= start2 < endex1 < endex2:
                        result[i] = (endex1, items2[(endex1 - start2):])

                    elif start2 < start1 <= endex1 < endex2:
                        result[i] = (start2, items2[:(start1 - start2)])
                        append((endex1, items2[(endex1 - start2):]))

                    if last_endex < endex2:
                        last_endex = endex2

            append(block)

    return result


def union(
    *blocks_list: BlockIterable,
    join: Optional[ItemJoiner] = None,
) -> BlockList:
    r"""Performs the union of multiple block lists.

    Given some sequences of blocks, their blocks are overwritten to the result
    block list, in the order such sequences are.

    Arguments:
        blocks_list (list of blocks):
            Multiple sequences of blocks.

        join (callable):
            A function to join a sequence of items.
            If ``None``, defaults to ``bytes().join``.

    Returns:
        list of blocks: A new list of non-overlapping blocks.

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

        >>> blocks1 = [
        ...     (0, '0123456789'),
        ...     (0, 'ABCD'),
        ... ]
        >>> blocks2 = [
        ...     (3, 'EF'),
        ...     (0, '$'),
        ...     (6, 'xyz'),
        ... ]
        >>> union(blocks1, blocks2, join=''.join)
        [(0, '$'), (1, 'BC'), (3, 'EF'), (5, '5'), (6, 'xyz'), (9, '9')]
    """
    result = []

    for blocks in blocks_list:
        result.extend(merge(blocks, join=join))

    result = collapse(result)
    result.sort(key=sorting)

    return result


class Memory:
    r"""Virtual memory.

    This class is a handy wrapper around `blocks`, so that it can behave mostly
    like a :obj:`bytearray`, but on sparse chunks of data.
    Please look at examples of each method to get a glimpse of the features of
    this class.

    Attributes:
        blocks (list of blocks):
            A sequence of non-overlapping blocks, sorted by address.

        items_type (type):
            Type of the items stored into blocks.
            Defaults to :obj:`bytes` if ``None``.

        items_join (callable):
            A function to join a sequence of items.
            Defaults to ``items_type().join`` if ``None``.

        autofill (items):
            Pattern of items for automatic flood, or ``None``.

        automerge (bool):
            Automatically merges touching blocks after operations that can
            alter attribute :attr:`blocks`.

    Arguments:
        items (items):
            An iterable to build the initial items block, by passing it to
            `items_type` as a constructor.

        start (int):
            Start address of the initial block, built if `items` is not
            ``None``.

        blocks (list of blocks):
            A sequence of non-overlapping blocks, sorted by address.
            The :attr:`blocks` attribute is assigned a shallow copy.

        items_type (type):
            see attribute :attr:`items_type`.

        items_join (callable):
            see attribute :attr:`items_join`.

        autofill (items):
            see attribute :attr:`autofill`.

        automerge (bool):
            see attribute :attr:`automerge`.

    Raises:
        :obj:`ValueError`: Both `items` and `blocks` are not ``None``.

    Examples:
        >>> memory = Memory()
        >>> memory.blocks
        []

        >>> memory = Memory('Hello, World!', 5)
        >>> memory.blocks
        [(5, 'Hello, World!')]
    """
    def __init__(
        self: 'Memory',
        items: Optional[ItemSequence] = None,
        start: int = 0,
        blocks: Optional[BlockList] = None,
        items_type: Optional[Type[Item]] = None,
        items_join: Optional[ItemJoiner] = None,
        autofill: Optional[ItemSequence] = None,
        automerge: bool = True,
    ) -> None:
        # Invalidate attributes to make type hinting happier
        self.blocks: BlockList = []
        self.items_type: Type[Item] = items_type
        self.items_join: ItemJoiner = items_join
        self.autofill: Optional[ItemSequence] = autofill
        self.automerge: bool = automerge

        if items_type is None:
            items_type: Type[Item] = bytes

        if items_join is None:
            items_join: ItemJoiner = items_type().join

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

        self.blocks: BlockList = blocks
        self.items_type: Type[Item] = items_type
        self.items_join: ItemJoiner = items_join
        self.autofill: Optional[ItemSequence] = autofill
        self.automerge: bool = automerge

    def __str__(
        self: 'Memory',
    ) -> str:
        r"""String representation.

        Applies :func:`str` to all the items from :attr:`blocks`.
        Emptiness around blocks is ignored.

        Returns:
            str: String representation.

        Example:
            +---+---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10|
            +===+===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |   |   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(1, 'ABC'), (7, 'xyz')]
            >>> str(memory)
            'ABCxyz'
        """
        return ''.join(str(items) for _, items in self.blocks)

    def __bool__(
        self: 'Memory',
    ) -> bool:
        r"""Has any items.

        Returns:
            bool: Has any items.

        Examples:
            >>> memory = Memory()
            >>> bool(memory)
            False

            >>> memory = Memory('Hello, World!', 5)
            >>> bool(memory)
            True
        """
        return bool(self.blocks)

    def __eq__(
        self: 'Memory',
        other: Union['Memory', Sequence[ItemSequence], ItemSequence],
    ) -> bool:
        r"""Equality comparison.

        Arguments:
            other (Memory):
                Data to compare with `self`.
                If it is an instance of `Memory`, all of its blocks must
                match.
                If it is a :obj:`list`, it is expected that it contains the
                same blocks as `self`.
                Otherwise, it must match the first stored block, considered
                equal if also starts at 0.

        Returns:
            bool: `self` is equal to `other`.

        Examples:
            >>> items = 'Hello, World!'
            >>> memory = Memory(items)
            >>> memory == items
            True
            >>> memory.shift(1)
            >>> memory == items
            False

            >>> items = 'Hello, World!'
            >>> memory = Memory(items)
            >>> blocks = [(0, items)]
            >>> memory == blocks
            True
            >>> memory == list(items)
            False
            >>> memory.shift(1)
            >>> memory == blocks
            False
        """
        if isinstance(other, Memory):
            return self.blocks == other.blocks

        elif isinstance(other, list):
            return self.blocks == other

        else:
            if len(self.blocks) != 1:
                return False

            start, items = next(iter(self.blocks))
            return start == 0 and items == other

    def __iter__(
        self: 'Memory',
    ) -> Iterator[Item]:
        r"""Iterates over all the items.

        Yields:
            items: All the single items collected from all the :attr:`blocks`.
            Emptiness around blocks is ignored.

        Example:
            +---+---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10|
            +===+===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |   |   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory()
            >>> memory.blocks = [(1, 'ABC'), (7, 'xyz')]
            >>> list(memory)
            ['A', 'B', 'C', 'x', 'y', 'z']
        """
        for _, items in self.blocks:
            yield from items

    def __reversed__(
        self: 'Memory',
    ) -> Iterator[Item]:
        r"""Iterates over all the items, in reverse.

        Yields:
            items: All the single items collected from all the :attr:`blocks`,
            in reverse order. Emptiness around blocks is ignored.

        Example:
            +---+---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10|
            +===+===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |   |   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory()
            >>> memory.blocks = [(1, 'ABC'), (7, 'xyz')]
            >>> list(reversed(memory))
            ['z', 'y', 'x', 'C', 'B', 'A']
        """
        for _, items in reversed(self.blocks):
            yield from reversed(items)

    def __add__(
        self: 'Memory',
        value: Union['Memory', ItemSequence, BlockSequence],
    ) -> 'Memory':
        r"""Concatenates items.

        Arguments:
            value (items):
                Items to append at the end of the current virtual space.
                If instance of :class:`list`, it is interpreted as a sequence
                of non-overlapping blocks, sorted by start address.

        Returns:
            A new memory with the items concatenated.
        """
        cls = type(self)
        result = cls(automerge=self.automerge,
                     items_type=self.items_type,
                     items_join=self.items_join)
        result.blocks = list(self.blocks)
        result += value
        return result

    def __iadd__(
        self: 'Memory',
        value: Union['Memory', ItemSequence, BlockSequence],
    ) -> 'Memory':
        r"""Concatenates items.

        Arguments:
            value (items):
                Items to append at the end of the current virtual space.
                If instance of :class:`list`, it is interpreted as a sequence
                of non-overlapping blocks, sorted by start address.

        Returns:
            :obj:`Memory` - `self`.
        """
        blocks = self.blocks

        if isinstance(value, type(self)):
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

    def __mul__(
        self: 'Memory',
        times: int,
    ) -> 'Memory':
        r"""Repeats the items.

        Repeats the stored items by `times`. Each repeated sequence is
        appended at the current virtual space end (i.e. :attr:`endex`).

        Arguments:
            times (int):
                Times to repeat the sequence of items.

        Returns:
            :obj:`Memory`: A new space with the items repeated.
        """
        cls = type(self)
        result = cls(automerge=self.automerge,
                     items_type=self.items_type,
                     items_join=self.items_join)
        result.blocks = list(self.blocks)
        result *= times
        return result

    def __imul__(
        self: 'Memory',
        times: int,
    ) -> 'Memory':
        r"""Repeats the items.

        Repeats the stored items by `times`. Each repeated sequence is
        appended at the current virtual space end (i.e. :attr:`endex`).

        Arguments:
            times (int):
                Times to repeat the sequence of items.

        Returns:
            :obj:`Memory`: `self`.
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

    def __len__(
        self: 'Memory',
    ) -> int:
        r"""Actual length.

        Computes the actual length of the stored items, i.e.
        (:attr:`endex` - :attr:`start`).

        Returns:
            int: Length of the stored items.
        """
        return self.endex - self.start

    def index(
        self: 'Memory',
        value: Item,
        start: Optional[int] = None,
        endex: Optional[int] = None,
    ) -> int:
        r"""Index of an item.

        Arguments:
            value (items):
                Value to find.

            start (int):
                Inclusive start of the searched range.
                If ``None``, the global inclusive start address is considered
                (i.e. :attr:`start`).

            endex (int):
                Exclusive end of the searched range.
                If ``None``, the global exclusive end address is considered
                (i.e. :attr:`endex`).

        Returns:
            int: The index of the first item equal to `value`.

        Raises:
            :obj:`ValueError` Item not found
        """
        length = self.endex
        start = straighten_index(start, length)
        endex = straighten_index(endex, length)
        address = find(self.blocks, value, start, endex)
        return address

    def __contains__(
        self: 'Memory',
        value: Item,
    ) -> bool:
        r"""Checks if some value is contained.

        Arguments:
            value (items):
                Value to find.

        Returns:
            bool: Values is contained.

        Example:
            +---+---+---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11|
            +===+===+===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |[1 | 2 | 3]|   |[x | y | z]|
            +---+---+---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
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

    def count(
        self: 'Memory',
        value: Item,
    ) -> int:
        r"""Counts items.

        Arguments:
            value (items):
                Reference value to count.

        Returns:
            int: The number of items equal to `value`.

        Example:
            +---+---+---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11|
            +===+===+===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |[B | a | t]|   |[t | a | b]|
            +---+---+---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(1, 'ABC'), (5, 'Bat'), (9, 'tab')]
            >>> memory.count('a')
            2
        """
        return sum(items.count(value) for _, items in self.blocks)

    def __getitem__(
        self: 'Memory',
        key: Union[slice, int],
    ) -> ItemSequence:
        r"""Reads data.

        Arguments:
            key (slice or int):
                Selection range or address.
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

        See Also:
            :meth:`Memory.read`

        Example:
            +---+---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10|
            +===+===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C | D]|   |[$]|   |[x | y | z]|
            +---+---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
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
            >>> memory[3:10:3]
            'C$y'
            >>> memory[3:10:2]
            Traceback (most recent call last):
                ...
            ValueError: contiguous slice not found
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
                blocks = crop(blocks, start, endex, step,
                              join=self.items_join)
                blocks = flood(blocks, start, endex, step,
                               join=self.items_join)
                items = self.items_join(items for _, items in blocks)
                return items

            else:
                if step is None or step == 1:
                    for address, items in blocks:
                        if address <= start <= endex <= address + len(items):
                            return items[(start - address):(endex - address)]
                    else:
                        raise ValueError('contiguous slice not found')
                else:
                    items = []
                    for address in range(start, endex, step):
                        index = locate_at(blocks, address)
                        if index is None:
                            raise ValueError('contiguous slice not found')
                        block = blocks[index]
                        items.append(block[1][address - block[0]])
                    items = self.items_join(items)
                    return items
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
                return items[key]

    def __setitem__(
        self: 'Memory',
        key: Union[slice, int],
        value: Optional[ItemSequence],
    ) -> None:
        r"""Writes data.

        Arguments:
            key (slice or int):
                Selection range or address.

            value (items):
                Items to write at the selection address.
                If `value` is null, the range is cleared.

        Note:
            Setting a single item requires `value` to be of :attr:`items_type`
            with unitary length.

        Note:
            This method is not optimized for a :class:`slice` where its `step`
            is an :obj:`int` different from 1.

        See Also:
            :meth:`Memory.write`
            :meth:`Memory.clear`

        Examples:
            +---+---+---+---+---+---+---+---+---+
            | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11| 12|
            +===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+
            |   |[A]|   |   |   |   |[y | z]|   |
            +---+---+---+---+---+---+---+---+---+
            |   |[A | B | C]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+
            |   |[A]|   |[C]|   |   | y | z]|   |
            +---+---+---+---+---+---+---+---+---+
            |   |[A | 1 | C]|   |[2 | y | z]|   |
            +---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(5, 'ABC'), (9, 'xyz')]
            >>> memory[7:10] = None
            >>> memory.blocks
            [(5, 'AB'), (10, 'yz')]
            >>> memory[7] = 'C'
            >>> memory[-3] = 'x'
            >>> memory.blocks == [(5, 'ABC'), (9, 'xyz')]
            True
            >>> memory[6:12:3] = None
            >>> memory.blocks
            [(5, 'A'), (7, 'C'), (10, 'yz')]
            >>> memory[6:12:3] = '123'
            >>> memory.blocks
            [(5, 'A1C'), (9, '2yz')]

            ~~~

            +---+---+---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11|
            +===+===+===+===+===+===+===+===+===+===+===+===+
            |   |   |   |   |   |[A | B | C]|   |[x | y | z]|
            +---+---+---+---+---+---+---+---+---+---+---+---+
            |[$]|   |[A | B | C]|   |[x | y | z]|   |   |   |
            +---+---+---+---+---+---+---+---+---+---+---+---+
            |[$]|   |[A | B]|[4 | 5 | 6]|[7 | 8]|[y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+---+---+
            |[$]|   |[A | B]|[4 | 5]|[< | >]|[8]|[y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str, automerge=False)
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
                    count = min((endex - start) // step, len(value))
                    for index in range(count):
                        items = value[index:(index + 1)]
                        blocks = write(blocks, (start, items))
                        start += step
            else:
                if step is None or step == 1:
                    blocks = clear(blocks, start, endex)
                else:
                    for address in range(start, endex, step):
                        blocks = clear(blocks, address, address + 1)
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

    def __delitem__(
        self: 'Memory',
        key: Union[slice, int],
    ) -> None:
        r"""Deletes data.

        Arguments:
            key (slice or int):
                Deletion range or address.

        Note:
            This method is not optimized for a :class:`slice` with its `step`
            different from either ``None`` or 1.

        See Also:
            :meth:`Memory.delete`

        Examples:
            +---+---+---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11|
            +===+===+===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C | D]|   |[$]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+---+---+
            |   |[A | B | C | y | z]|   |   |   |   |   |   |
            +---+---+---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
            >>> del memory[4:9]
            >>> memory.blocks
            [(1, 'ABCyz')]

            ~~~

            +---+---+---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11|
            +===+===+===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C | D]|   |[$]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+---+---+
            |   |[A | B | C]|[y | z]|   |   |   |   |   |   |
            +---+---+---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str, automerge=False)
            >>> memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
            >>> del memory[4:9]
            >>> memory.blocks
            [(1, 'ABC'), (4, 'yz')]

            ~~~

            +---+---+---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11|
            +===+===+===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C | D]|   |[$]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+---+---+
            |   |[A | B | C | D]|   |[$]|   |[x | z]|   |   |
            +---+---+---+---+---+---+---+---+---+---+---+---+
            |   |[A | B | D]|   |[$]|   |[x | z]|   |   |   |
            +---+---+---+---+---+---+---+---+---+---+---+---+
            |   |[A | D]|   |   |[x]|   |   |   |   |   |   |
            +---+---+---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(1, 'ABCD'), (6, '$'), (8, 'xyz')]
            >>> del memory[-2]
            >>> memory.blocks
            [(1, 'ABCD'), (6, '$'), (8, 'xz')]
            >>> del memory[3]
            >>> memory.blocks
            [(1, 'ABD'), (5, '$'), (7, 'xz')]
            >>> del memory[2:10:3]
            >>> memory.blocks
            [(1, 'AD'), (5, 'x')]
        """
        blocks = self.blocks

        if isinstance(key, slice):
            start, endex, step = key.start, key.stop, key.step
            length = self.endex
            start, endex, step = straighten_slice(start, endex, step, length)

            if step is None or step == 1:
                blocks = delete(blocks, start, endex)
            else:
                for address in reversed(range(start, endex, step)):
                    blocks = delete(blocks, address, address + 1)
        else:
            key = key.__index__()
            if key < 0:
                key %= self.endex
            blocks = delete(blocks, key, key + 1)

        if self.automerge:
            blocks = merge(blocks, join=self.items_join)

        self.blocks = blocks

    def append(
        self: 'Memory',
        value: ItemSequence,
    ) -> None:
        r"""Appends some items.

        Arguments:
            value (items):
                Items to append.

        Note:
            Appending a single item requires `value` to be of
            :attr:`items_type` with unitary length.

        Examples:
            >>> memory = Memory(items_type=str)
            >>> memory.append('$')
            >>> memory.blocks
            [(0, '$')]

            ~~~

            >>> memory = Memory(items_type=list)
            >>> memory.append([3])
            >>> memory.blocks
            [(0, [3])]
        """
        blocks = self.blocks
        if blocks:
            start, items = blocks[-1]
            items = items + value
            blocks[-1] = (start, items)
        else:
            blocks = [(0, value)]
        self.blocks = blocks

    def extend(
        self: 'Memory',
        items: ItemSequence,
    ) -> None:
        r"""Concatenates items.

        Equivalent to ``self += items``.

        Arguments:
            items (items):
                Items to append at the end of the current virtual space.
                If instance of :class:`list`, it is interpreted as a sequence
                of non-overlapping blocks, sorted by start address.
        """
        self.__iadd__(items)

    @property
    def contiguous(self: 'Memory') -> bool:
        r"""Contains contiguous data.

        The memory is considered to have contiguous data if there is no empty
        space between blocks.

        Returns:
            bool: Contiguous data.

        Examples:
            >>> Memory().contiguous
            True

            ~~~

            +---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
            +===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|[x | y | z]|   |   |
            +---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(1, 'ABC'), (4, 'xyz')]
            >>> memory.contiguous
            True

            ~~~

            +---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
            +===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+

            >>> memory.blocks = [(1, 'ABC'), (5, 'xyz')]
            >>> memory.contiguous
            False
        """
        blocks = self.blocks

        if blocks:
            endex = blocks[0][0]

            for start, items in blocks:
                if endex != start:
                    return False
                endex = start + len(items)

        return True

    @property
    def start(self: 'Memory') -> int:
        r"""Inclusive start address.

        This property holds the inclusive start address of the virtual space.
        By default, it is the current minimum inclusive start address of
        :attr:`blocks`.

        Returns:
            int: The inclusive start address, or 0.

        Examples:
            >>> Memory().start
            0

            ~~~

            +---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
            +===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(1, 'ABC'), (5, 'xyz')]
            >>> memory.start
            1
        """
        blocks = self.blocks

        if blocks:
            start, _ = blocks[0]
            return start
        else:
            return 0

    @property
    def endex(self: 'Memory') -> int:
        r"""Exclusive end address.

        This property holds the exclusive end address of the virtual space.
        By default, it is the current minimum exclusive end address of
        :attr:`blocks`.

        Returns:
            int: The exclusive end address, or 0.

        Examples:
            >>> Memory().endex
            0

            ~~~

            +---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
            +===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(1, 'ABC'), (5, 'xyz')]
            >>> memory.endex
            8
        """
        blocks = self.blocks

        if blocks:
            start, items = blocks[-1]
            return start + len(items)
        else:
            return 0

    @property
    def span(self: 'Memory') -> Tuple[int, int]:
        r"""Memory address span.

        Returns:
            tuple: A :obj:`tuple` holding :attr:`start` and :attr:`endex`.

        Examples:
            >>> Memory().span
            (0, 0)

            ~~~

            +---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
            +===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(1, 'ABC'), (5, 'xyz')]
            >>> memory.span
            (1, 8)
        """
        blocks = self.blocks

        if blocks:
            first = blocks[0][0]
            start, items = blocks[-1]
            return first, start + len(items)
        else:
            return 0, 0

    def shift(
        self: 'Memory',
        amount: int,
    ) -> None:
        r"""Shifts the items.

        Arguments:
            amount (int):
                Signed amount of address shifting.

        See Also:
            :func:`shift`

        Example:
            +---+---+---+---+---+---+---+---+---+---+---+
            | 1 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11| 12|
            +===+===+===+===+===+===+===+===+===+===+===+
            |   |   |   |[A | B | C]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+---+
            |   |[A | B | C]|   |[x | y | z]|   |   |   |
            +---+---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(blocks=[(5, 'ABC'), (9, 'xyz')])
            >>> memory.shift(-2)
            >>> memory.blocks
            [(3, 'ABC'), (7, 'xyz')]
        """
        blocks = self.blocks
        blocks = shift(blocks, amount)
        self.blocks = blocks

    @deprecated(reason='Use extract() instead')
    def read(
        self: 'Memory',
        start: Optional[int],
        endex: Optional[int],
        pattern: Optional[ItemSequence] = None,
    ) -> ItemSequence:
        r"""Selects items from a range.

        Equivalent to ``self[start:endex:pattern]``.

        Arguments:
            start (int):
                Inclusive start of the extracted range.
                If ``None``, the global inclusive start address is considered
                (i.e. :attr:`start`).

            endex (int):
                Exclusive end of the extracted range.
                If ``None``, the global exclusive end address is considered
                (i.e. :attr:`endex`).

            pattern (items):
                Pattern of items to fill the emptiness.
                If ``None``, the :attr:`autofill` attribute is used.

        Returns:
            items: Items from the selected range.
        """
        return self.extract(start, endex, pattern)

    def extract(
        self: 'Memory',
        start: Optional[int],
        endex: Optional[int],
        pattern: Optional[ItemSequence] = None,
    ) -> ItemSequence:
        r"""Selects items from a range.

        Equivalent to ``self[start:endex:pattern]``.

        Arguments:
            start (int):
                Inclusive start of the extracted range.
                If ``None``, the global inclusive start address is considered
                (i.e. :attr:`start`).

            endex (int):
                Exclusive end of the extracted range.
                If ``None``, the global exclusive end address is considered
                (i.e. :attr:`endex`).

            pattern (items):
                Pattern of items to fill the emptiness.
                If ``None``, the :attr:`autofill` attribute is used.

        Returns:
            items: Items from the selected range.
        """
        return self[start:endex:pattern]

    @deprecated(reason='Use crop() instead')
    def cut(
        self: 'Memory',
        start: Optional[int],
        endex: Optional[int],
        pattern: Optional[ItemSequence] = None,
    ) -> None:
        r"""Keeps data within a range.

        Arguments:
            start (int):
                Inclusive start of the selected range.
                If ``None``, the global inclusive start address is considered
                (i.e. :attr:`start`).

            endex (int):
                Exclusive end of the selected range.
                If ``None``, the global exclusive end address is considered
                (i.e. :attr:`endex`).

            pattern (items):
                Pattern of items to fill the emptiness.
                If ``None``, the :attr:`autofill` attribute is used.

        See Also:
            :func:`read`

        Example:
            +---+---+---+---+---+---+---+---+---+
            | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11| 12|
            +===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+
            |   |   |[B | C]|   |[x]|   |   |   |
            +---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(5, 'ABC'), (9, 'xyz')]
            >>> memory.cut(6, 10)
            >>> memory.blocks
            [(6, 'BC'), (9, 'x')]
        """
        self.crop(start, endex, pattern)

    def crop(
        self: 'Memory',
        start: Optional[int],
        endex: Optional[int],
        pattern: Optional[ItemSequence] = None,
    ) -> None:
        r"""Keeps data within a range.

        Arguments:
            start (int):
                Inclusive start of the selected range.
                If ``None``, the global inclusive start address is considered
                (i.e. :attr:`start`).

            endex (int):
                Exclusive end of the selected range.
                If ``None``, the global exclusive end address is considered
                (i.e. :attr:`endex`).

            pattern (items):
                Pattern of items to fill the emptiness.
                If ``None``, the :attr:`autofill` attribute is used.

        See Also:
            :func:`read`

        Example:
            +---+---+---+---+---+---+---+---+---+
            | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11| 12|
            +===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+
            |   |   |[B | C]|   |[x]|   |   |   |
            +---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(5, 'ABC'), (9, 'xyz')]
            >>> memory.crop(6, 10)
            >>> memory.blocks
            [(6, 'BC'), (9, 'x')]
        """
        blocks = self.blocks
        blocks = crop(blocks, start, endex, pattern, self.items_join)

        if self.automerge:
            blocks = merge(blocks, join=self.items_join)

        self.blocks = blocks

    def clear(
        self: 'Memory',
        start: Optional[int] = None,
        endex: Optional[int] = None,
    ) -> None:
        r"""Clears a range.

        Arguments:
            start (int):
                Inclusive start of the extracted range.
                If ``None``, the global inclusive start address is considered
                (i.e. :attr:`start`).

            endex (int):
                Exclusive end of the extracted range.
                If ``None``, the global exclusive end address is considered
                (i.e. :attr:`endex`).

        See Also:
            :func:`clear`

        Example:
            +---+---+---+---+---+---+---+---+---+
            | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11| 12|
            +===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+
            |   |[A]|   |   |   |   |[y | z]|   |
            +---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
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

    def delete(
        self: 'Memory',
        start: Optional[int] = None,
        endex: Optional[int] = None,
    ) -> None:
        r"""Deletes a range.

        Arguments:
            start (int):
                Inclusive start of the extracted range.
                If ``None``, the global inclusive start address is considered
                (i.e. :attr:`start`).

            endex (int):
                Exclusive end of the extracted range.
                If ``None``, the global exclusive end address is considered
                (i.e. :attr:`endex`).

        See Also:
            :func:`delete`

        Example:
            +---+---+---+---+---+---+---+---+---+---+
            | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11| 12| 13|
            +===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+
            |   |[A | y | z]|   |   |   |   |   |   |
            +---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(5, 'ABC'), (9, 'xyz')]
            >>> memory.delete(6, 10)
            >>> memory.blocks
            [(5, 'Ayz')]
        """
        del self[start:endex]

    def pop(
        self: 'Memory',
        address: Optional[int] = None,
    ) -> Item:
        r"""Retrieves an item and deletes it.

        Arguments:
            address (int):
                Address of the item to remove; ``None`` means the last one.

        Returns:
            item: The item at `address` if existing, null otherwise.

        Raises:
            :obj:`IndexError`: Pop from empty blocks.

        Example:
            +---+---+---+---+---+---+---+---+---+
            | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11| 12|
            +===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+
            |   |[A | C]|   |[x | y | z]|   |   |
            +---+---+---+---+---+---+---+---+---+
            |   |[A | C]|   |[x | z]|   |   |   |
            +---+---+---+---+---+---+---+---+---+
            |   |[A | C]|   |[x]|   |   |   |   |
            +---+---+---+---+---+---+---+---+---+
            |   |[A | C]|[x]|   |   |   |   |   |
            +---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
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

    def remove(
        self: 'Memory',
        value: ItemSequence,
    ) -> None:
        r"""Removes some data.

        Finds the first occurrence of `value` and deletes it.

        Arguments:
            value (items):
                Sequence of items to remove.

        Raises:
            :obj:`ValueError`: Item not found.

        Example:
            +---+---+---+---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11| 12|
            +===+===+===+===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |[1 | 2 | 3]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+---+---+---+
            |   |[A | B | C]|   |[1]|   |[x | y | z]|   |   |   |
            +---+---+---+---+---+---+---+---+---+---+---+---+---+
            |   |[A | B | C]|   |[1]|   |[x | z]|   |   |   |   |
            +---+---+---+---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
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
            :obj:`ValueError` item not found
        """
        blocks = self.blocks
        address = find(blocks, value)
        blocks = delete(blocks, address, address + len(value))

        if self.automerge:
            blocks = merge(blocks, join=self.items_join)

        self.blocks = blocks

    def reserve(
        self: 'Memory',
        address: int,
        length: int,
    ) -> None:
        r"""Inserts reserved space.

        Inserts reserved space, moving existing items after the insertion
        address by the length of the inserted block.

        Arguments:
            address (int):
                Address of the reserved space to insert.

            length (int):
                Length of the reserved space.

        See Also:
            :func:`reserve`

        Example:
            +---+---+---+---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11| 12|
            +===+===+===+===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |   |[x | y | z]|   |   |   |   |
            +---+---+---+---+---+---+---+---+---+---+---+---+---+
            |   |[A | B | C]|   |[1 | 2 | 3]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(1, 'ABC'), (6, 'xyz')]
            >>> memory.reserve(5, 3)
            >>> memory.blocks
            [(1, 'ABC'), (9, 'xyz')]
        """
        blocks = self.blocks
        blocks = reserve(blocks, address, length)

        if self.automerge:
            blocks = merge(blocks, join=self.items_join)

        self.blocks = blocks

    def insert(
        self: 'Memory',
        address: int,
        items: ItemSequence,
    ) -> None:
        r"""Inserts data.

        Inserts a block, moving existing items after the insertion address by
        the length of the inserted block.

        Arguments:
            address (int):
                Address of the block to insert.

            items (items):
                Items of the block to insert.

        See Also:
            :func:`insert`

        Example:
            +---+---+---+---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 11| 12|
            +===+===+===+===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |   |[x | y | z]|   |   |   |   |
            +---+---+---+---+---+---+---+---+---+---+---+---+---+
            |   |[A | B | C]|   |[1 | 2 | 3]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
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

    def write(
        self: 'Memory',
        address: int,
        items: ItemSequence,
    ) -> None:
        r"""Writes data.

        Arguments:
            address (int):
                Address of the block to write.

            items (items):
                Items of the block to write.

        See Also:
            :func:`write`

        Example:
            +---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
            +===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+
            |   |[A | B | C]|   |[1 | 2 | 3 | z]|   |
            +---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
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

    def fill(
        self: 'Memory',
        start: Optional[int] = None,
        endex: Optional[int] = None,
        pattern: Optional[ItemSequence] = None,
    ) -> None:
        r"""Overwrites a range with a pattern.

        Arguments:
            start (int):
                Inclusive start of the filled range.
                If ``None``, the global inclusive start address is considered
                (i.e. that of the first block).

            endex (int):
                Exclusive end of the filled range.
                If ``None``, the global exclusive end address is considered
                (i.e. that of the last block).

            pattern (items):
                Pattern of items to fill the range.
                If ``None``, the :attr:`autofill` attribute is used.

        See Also:
            :func:`fill`

        Examples:
            +---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
            +===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+
            |   |[1 | 2 | 3 | 1 | 2 | 3 | 1 | 2]|   |
            +---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(1, 'ABC'), (6, 'xyz')]
            >>> memory.fill(pattern='123')
            >>> memory.blocks
            [(1, '12312312')]

            ~~~

            +---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
            +===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+
            |   |[1 | 2 | 3 | 1 | 2 | 3 | 1 | 2]|   |
            +---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str, autofill='123')
            >>> memory.blocks = [(1, 'ABC'), (6, 'xyz')]
            >>> memory.fill()
            >>> memory.blocks
            [(1, '12312312')]

            ~~~

            +---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
            +===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+
            |   |[A | B | 1 | 2 | 3 | 1 | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str, autofill='123')
            >>> memory.blocks = [(1, 'ABC'), (6, 'xyz')]
            >>> memory.fill(3, 7)
            >>> memory.blocks
            [(1, 'AB1231yz')]
        """
        blocks = self.blocks
        if pattern is None:
            pattern = self.autofill
        blocks = fill(blocks, start, endex, pattern, self.items_join)

        if self.automerge:
            blocks = merge(blocks, join=self.items_join)

        self.blocks = blocks

    def flood(
        self: 'Memory',
        start: Optional[int] = None,
        endex: Optional[int] = None,
        pattern: Optional[ItemSequence] = None,
    ) -> None:
        r"""Fills emptiness between non-touching blocks.

        Arguments:
            start (int):
                Inclusive start of the filled range.
                If ``None``, the global inclusive start address is considered
                (i.e. that of the first block).

            endex (int):
                Exclusive end of the filled range.
                If ``None``, the global exclusive end address is considered
                (i.e. that of the last block).

            pattern (items):
                Pattern of items to fill the emptiness.
                If ``None``, the :attr:`autofill` attribute is used.

        See Also:
            :func:`flood`

        Examples:
            +---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
            +===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+
            |   |[A | B | C | 1 | 2 | x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(1, 'ABC'), (6, 'xyz')]
            >>> memory.flood(pattern='123')
            >>> memory.blocks
            [(1, 'ABC12xyz')]

            ~~~

            +---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
            +===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+
            |   |[A | B | C | 1 | 2 | x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str, autofill='123')
            >>> memory.blocks = [(1, 'ABC'), (6, 'xyz')]
            >>> memory.flood()
            >>> memory.blocks
            [(1, 'ABC12xyz')]
        """
        blocks = self.blocks
        if pattern is None:
            pattern = self.autofill
        blocks = flood(blocks, start, endex, pattern, join=self.items_join)

        if self.automerge:
            blocks = merge(blocks, join=self.items_join)

        self.blocks = blocks

    def merge(
        self: 'Memory',
    ) -> None:
        r"""Merges touching blocks.

        See Also:
            :func:`merge`

        Example:
            +---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
            +===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |   |   |   |
            +---+---+---+---+---+---+---+---+
            |   |   |   |   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+
            |   |[A | B | C | x | y | z]|   |
            +---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(1, 'ABC'), (4, 'xyz')]
            >>> memory.merge()
            >>> memory.blocks
            [(1, 'ABCxyz')]
        """
        blocks = self.blocks
        blocks = merge(blocks, join=self.items_join)
        self.blocks = blocks

    def reverse(
        self: 'Memory',
    ) -> None:
        r"""Reverses data in-place.

        Example:
            +---+---+---+---+---+---+---+---+---+---+---+
            | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10|
            +===+===+===+===+===+===+===+===+===+===+===+
            |   |[A | B | C]|   |[$]|   |[x | y | z]|   |
            +---+---+---+---+---+---+---+---+---+---+---+
            |[z | y | x]|   |[$]|   |[C | B | A]|   |   |
            +---+---+---+---+---+---+---+---+---+---+---+

            >>> memory = Memory(items_type=str)
            >>> memory.blocks = [(1, 'ABC'), (5, '$'), (7, 'xyz')]
            >>> memory.reverse()
            >>> memory.blocks
            [(0, 'zyx'), (4, '$'), (6, 'CBA')]
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
