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

r"""Hexadecimal record management.

The core of this library are *hexadecimal record files*.  Such files are used
to store binary data in text form, where each byte octet is represented in
hexadecimal format.  Over the whole byte addressing range of the memory to
store (typically 32-bit addressing), only the relevant data is kept.

The hexadecimal data text is split into *record lines*, which give the name to
this family of file formats.  Each line should at least be marked with the
*address* of its first byte, so that it is possible to load data from sparse
records.

Usually not only plain data records exist, but also records holding metadata,
such as: a *terminator* record, the *record count*, the *start address* to set
the program counter upon loading an executable, a generic *header string*, and
so on.  Each record line is thus marked with a *tag* to indicate which kind of
data it holds.

Record lines are commonly protected by a *checksum*, so that each line can be
checked for (arguably weak) consistency.
A *count* number is used to measure the record line length some way.

Summarizing, a record line holds the following fields:

* a *tag* to tell which kind of (meta)data is hold;
* some bytes of actual *data*, or tag-specific;
* the *address* of its first data byte, or tag-specific;
* the *count* of record line characters;
* a *checksum* to protect the record line.

This module provides functions and classes to handle hexadecimal record files,
from the record line itself, to high-level procedures.
"""
import enum
import os
from typing import IO
from typing import Any
from typing import Collection
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Type
from typing import Union

import pkg_resources
from click import open_file

from .blocks import BlockIterable
from .blocks import BlockSequence
from .blocks import Memory
from .blocks import merge
from .blocks import union
from .utils import AnyBytes
from .utils import check_empty_args_kwargs
from .utils import do_overlap
from .utils import sum_bytes

RecordIterable = Iterable['Record']
RecordCollection = Collection['Record']
RecordSequence = Sequence['Record']
RecordList = List['Record']


def get_data_records(
    records: RecordIterable,
) -> RecordList:
    r"""Extracts data records.

    Arguments:
        records(list of records):
            Sequence of records.

    Returns:
        list of records: Sequence of data records.

    Example:
        >>> from hexrec.blocks import chop_blocks
        >>> from hexrec.formats.motorola import Record as MotorolaRecord
        >>> data = bytes(range(256))
        >>> blocks = list(chop_blocks(data, 16))
        >>> records = blocks_to_records(blocks, MotorolaRecord)
        >>> all(r.is_data() for r in get_data_records(records))
        True
    """
    data_records = [record for record in records if record.is_data()]
    return data_records


def get_max_data_length(
    data_records: RecordIterable,
) -> Optional[int]:
    r"""Extracts data records.

    Arguments:
        data_records (list of records):
            Sequence of data records.

    Returns:
        int: Maximum data count found; ``0`` by default.

    Example:
        >>> from hexrec.blocks import chop_blocks
        >>> from hexrec.formats.motorola import Record as MotorolaRecord
        >>> data = bytes(range(100))
        >>> blocks = list(chop_blocks(data, 16))
        >>> records = blocks_to_records(blocks, MotorolaRecord)
        >>> get_max_data_length(records))
        16
    """
    length = max(len(record.data or b'') for record in data_records)
    return length


def find_corrupted_records(
    records: RecordIterable,
) -> List[int]:
    r"""Finds corrupted records.

    Arguments:
        records (list of records):
            Sequence of records.

    Returns:
        list of int: Sequence of corrupted record indices.

    Example:
        >>> from hexrec.formats.motorola import Record as MotorolaRecord
        >>> data = bytes(range(256))
        >>> records = list(MotorolaRecord.split(data))
        >>> records[3].checksum ^= 0xFF
        >>> records[5].checksum ^= 0xFF
        >>> records[7].checksum ^= 0xFF
        >>> find_corrupted_records(records)
        [3, 5, 7]
    """
    corrupted = []
    for index, record in enumerate(records):
        try:
            record.check()
        except ValueError:
            corrupted.append(index)
    return corrupted


def records_to_blocks(
    records: RecordIterable,
) -> BlockSequence:
    r"""Converts records to blocks.

    Extracts all the data records, collapses them in the order they compare in
    `records`, and merges the collapsed blocks.
    Returns sequence of non-contiguous blocks, sorted by start address.

    Arguments:
        records (list of records):
            Sequence of records to convert to blocks.

    Returns:
        list of blocks: Blocks holding data from `records`.

    Example:
        >>> from hexrec.blocks import chop_blocks, merge
        >>> from hexrec.formats.motorola import Record as MotorolaRecord
        >>> data = bytes(range(256))
        >>> blocks = list(chop_blocks(data, 16))
        >>> records = blocks_to_records(blocks, MotorolaRecord)
        >>> records_to_blocks(records) == merge(blocks)
        True
    """
    blocks = [(r.address, r.data) for r in get_data_records(records)]
    blocks = merge(union(blocks))
    return blocks


def blocks_to_records(
    blocks: BlockIterable,
    record_type: Type['Record'],
    split_args: Optional[Sequence[Any]] = None,
    split_kwargs: Optional[Mapping[str, Any]] = None,
    build_args: Optional[Sequence[Any]] = None,
    build_kwargs: Optional[Mapping[str, Any]] = None,
) -> RecordList:
    r"""Converts blocks to records.

    Arguments:
        blocks (list of blocks):
            A sequence of non-contiguous blocks, sorted by start address.

        record_type (type):
            Output record type.

        split_args (list):
            Positional arguments for :meth:`Record.split`.

        split_kwargs (dict):
            Keyword arguments for :meth:`Record.split`.

        build_args (list):
            Positional arguments for :meth:`Record.build_standalone`.

        build_kwargs (dict):
            Keyword arguments for :meth:`Record.build_standalone`.

    Returns:
        list of records: Records holding data from `blocks`.

    Example:
        >>> from hexrec.blocks import chop_blocks, merge
        >>> from hexrec.formats.motorola import Record as MotorolaRecord
        >>> data = bytes(range(256))
        >>> blocks = list(chop_blocks(data, 16))
        >>> records = blocks_to_records(blocks, MotorolaRecord)
        >>> records_to_blocks(records) == merge(blocks)
        True
    """
    split_args = split_args or ()
    split_kwargs = dict(split_kwargs or ())
    split_kwargs['standalone'] = False
    data_records = []

    for start, items in blocks:
        split_kwargs['address'] = start
        records = record_type.split(items, *split_args, **split_kwargs)
        data_records.extend(records)

    build_args = build_args or ()
    build_kwargs = dict(build_kwargs or ())
    records = list(record_type.build_standalone(data_records,
                                                *build_args, **build_kwargs))
    return records


def merge_records(
    data_records: Sequence[RecordSequence],
    input_types: Optional[Sequence[type]] = None,
    output_type: Optional[Type['Record']] = None,
    split_args: Optional[Sequence[Any]] = None,
    split_kwargs: Optional[Mapping[str, Any]] = None,
    build_args: Optional[Sequence[Any]] = None,
    build_kwargs: Optional[Mapping[str, Any]] = None,
) -> RecordList:
    r"""Merges data records.

    Merges multiple sequences of data records where each sequence overwrites
    overlapping data of the previous sequences.

    Arguments:
        data_records (list of records):
            A vector of *data* record sequences.
            If `input_types` is not ``None``, sequence generators are
            supported for the vector and its nested sequences.

        input_types (list of types):
            Selects the record type for each of the sequences in
            `data_records`.
            ``None`` will choose that of the first element of the (indexable)
            sequence.

        output_type (type):
            Selects the output record type.
            ``None`` will choose that of the first `input_types`.

        split_args (list):
            Positional arguments for :meth:`Record.split`.

        split_kwargs (dict):
            Keyword arguments for :meth:`Record.split`.

        build_args (list):
            Positional arguments for :meth:`Record.build_standalone`.

        build_kwargs (dict):
            Keyword arguments for :meth:`Record.build_standalone`.

    Returns:
        list of records: Merged records.

    Example:
        >>> from hexrec.blocks import chop_blocks, merge
        >>> from hexrec.formats.intel import Record as IntelRecord
        >>> from hexrec.formats.motorola import Record as MotorolaRecord
        >>> data1 = bytes(range(0, 32))
        >>> data2 = bytes(range(96, 128))
        >>> blocks1 = list(chop_blocks(data1, 16, start=0))
        >>> blocks2 = list(chop_blocks(data2, 16, start=96))
        >>> records1 = blocks_to_records(blocks1, MotorolaRecord)
        >>> records2 = blocks_to_records(blocks2, IntelRecord)
        >>> IntelRecord.readdress(records2)
        >>> data_records1 = get_data_records(records1)
        >>> data_records2 = get_data_records(records2)
        >>> merged_records = merge_records([data_records1, data_records2])
        >>> merged_blocks = records_to_blocks(merged_records)
        >>> merged_blocks == merge(blocks1 + blocks2)
        True
    """
    if input_types is None:
        input_types = [type(records[0]) if records else Record
                       for records in data_records]
    else:
        input_types = list(input_types)

    if output_type is None:
        output_type = input_types[0]

    blocks = merge(union(*[[(r.address, r.data) for r in records]
                           for records in data_records]))

    output_records = blocks_to_records(blocks, output_type,
                                       split_args, split_kwargs,
                                       build_args, build_kwargs)
    return output_records


def convert_records(
    records: RecordSequence,
    input_type: Optional[Type['Record']] = None,
    output_type: Optional[Type['Record']] = None,
    split_args: Optional[Sequence[Any]] = None,
    split_kwargs: Optional[Mapping[str, Any]] = None,
    build_args: Optional[Sequence[Any]] = None,
    build_kwargs: Optional[Mapping[str, Any]] = None,
) -> RecordList:
    r"""Converts records to another type.

    Arguments:
        records (list of records):
            A sequence of :class:`Record` elements.
            Sequence generators supported if `input_type` is specified.

        input_type (type):
            Explicit type of `records` elements.
            If ``None``, it is taken from the first element of the (indexable)
            `records` sequence.

        output_type (type):
            Explicit output type.
            If ``None``, it is reassigned as `input_type`.

        split_args (list):
            Positional arguments for :meth:`Record.split`.

        split_kwargs (dict):
            Keyword arguments for :meth:`Record.split`.

        build_args (list):
            Positional arguments for :meth:`Record.build_standalone`.

        build_kwargs (dict):
            Keyword arguments for :meth:`Record.build_standalone`.

    Returns:
        list of records: Converted records.

    Examples:
        >>> from hexrec.formats.intel import Record as IntelRecord
        >>> from hexrec.formats.motorola import Record as MotorolaRecord
        >>> motorola = list(MotorolaRecord.split(bytes(range(256))))
        >>> intel = list(IntelRecord.split(bytes(range(256))))
        >>> converted = convert_records(motorola, output_type=IntelRecord)
        >>> converted == intel
        True

        >>> from hexrec.formats.intel import Record as IntelRecord
        >>> from hexrec.formats.motorola import Record as MotorolaRecord
        >>> motorola = list(MotorolaRecord.split(bytes(range(256))))
        >>> intel = list(IntelRecord.split(bytes(range(256))))
        >>> converted = convert_records(intel, output_type=MotorolaRecord)
        >>> converted == motorola
        True
    """
    if input_type is None:
        input_type = type(records[0])
    if output_type is None:
        output_type = input_type

    data_records = [r for r in records if r.is_data()]
    output_records = merge_records([data_records], [input_type], output_type,
                                   split_args, split_kwargs,
                                   build_args, build_kwargs)
    return output_records


def merge_files(
    input_files: Sequence[str],
    output_file: str,
    input_types: Optional[Sequence[Type['Record']]] = None,
    output_type: Optional[Type['Record']] = None,
    split_args: Optional[Sequence[Any]] = None,
    split_kwargs: Optional[Mapping[str, Any]] = None,
    build_args: Optional[Sequence[Any]] = None,
    build_kwargs: Optional[Mapping[str, Any]] = None,
) -> None:
    r"""Merges record files.

    Merges multiple record files where each file overwrites overlapping data
    of the previous files.

    Warning:
        Only binary data is kept; metadata will be overwritten by the call
        to :meth:`Record.build_standalone`.

    Arguments:
        input_files (list of str):
            A sequence of file paths to merge.

        output_file (str): Path of the output file. It can target an
            input file.

        input_types (list of types):
            Selects the record type for each of the sequences in
            `data_records`.
            ``None`` will guess from file extension.

        output_type (type):
            Selects the output record type.
            ``None`` will guess from file extension.

        split_args (list):
            Positional arguments for :meth:`Record.split`.

        split_kwargs (dict):
            Keyword arguments for :meth:`Record.split`.

        build_args (list):
            Positional arguments for :meth:`Record.build_standalone`.

        build_kwargs (dict):
            Keyword arguments for :meth:`Record.build_standalone`.

    Example:
        >>> merge_files(['merge1.mot', 'merge2.hex'], 'merged.tek')

    """
    if input_types is None:
        input_types: List[Optional[Type['Record']]] = [None] * len(input_files)
    else:
        input_types = list(input_types)

    for level in range(len(input_types)):
        if input_types[level] is None:
            input_types[level] = find_record_type(input_files[level])

    if output_type is None:
        output_type = find_record_type(output_file)

    input_records = []
    for level in range(len(input_types)):
        input_type = input_types[level]
        records = input_type.load_records(input_files[level])
        input_type.readdress(records)
        records = [r for r in records if r.is_data()]
        input_records.append(records)

    output_records = merge_records(input_records, input_types, output_type,
                                   split_args, split_kwargs,
                                   build_args, build_kwargs)
    output_type.save_records(output_file, output_records)


def convert_file(
    input_file: str,
    output_file: str,
    input_type: Optional[Type['Record']] = None,
    output_type: Optional[Type['Record']] = None,
    split_args: Optional[Sequence[Any]] = None,
    split_kwargs: Optional[Mapping[str, Any]] = None,
    build_args: Optional[Sequence[Any]] = None,
    build_kwargs: Optional[Mapping[str, Any]] = None,
) -> None:
    r"""Converts a record file to another record type.

    Warning:
        Only binary data is kept; metadata will be overwritten by the call
        to :meth:`Record.build_standalone`.

    Arguments:
        input_file (str):
            Path of the input file.

        output_file (str):
            Path of the output file.

        input_type (type):
            Explicit input record type.
            If ``None``, it is guessed from the file extension.

        output_type (type):
            Explicit output record type.
            If ``None``, it is guessed from the file extension.

        split_args (list):
            Positional arguments for :meth:`Record.split`.

        split_kwargs (dict):
            Keyword arguments for :meth:`Record.split`.

        build_args (list):
            Positional arguments for :meth:`Record.build_standalone`.

        build_kwargs (dict):
            Keyword arguments for :meth:`Record.build_standalone`.

    Example:
        >>> from hexrec.formats.intel import Record as IntelRecord
        >>> from hexrec.formats.motorola import Record as MotorolaRecord
        >>> motorola = list(MotorolaRecord.split(bytes(range(256))))
        >>> intel = list(IntelRecord.split(bytes(range(256))))
        >>> save_records('bytes.mot', motorola)
        >>> convert_file('bytes.mot', 'bytes.hex')
        >>> load_records('bytes.hex') == intel
        True
    """
    merge_files([input_file], output_file, [input_type], output_type,
                split_args, split_kwargs, build_args, build_kwargs)


def load_records(
    path: str,
    record_type: Optional[Type['Record']] = None,
) -> RecordList:
    r"""Loads records from a record file.

    Arguments:
        path (str):
            Path of the input file.

        record_type (type):
            Explicit record type.
            If ``None``, it is guessed from the file extension.

    Example:
        >>> from hexrec.formats.motorola import Record as MotorolaRecord
        >>> records = list(MotorolaRecord.split(bytes(range(256))))
        >>> save_records('bytes.mot', records)
        >>> load_records('bytes.mot') == records
        True
    """
    if record_type is None:
        record_type = find_record_type(path)

    records = record_type.load_records(path)
    return records


def save_records(
    path: str,
    records: RecordSequence,
    output_type: Optional[Type['Record']] = None,
    split_args: Optional[Sequence[Any]] = None,
    split_kwargs: Optional[Mapping[str, Any]] = None,
) -> None:
    r"""Saves records to a record file.

    Arguments:
        path (str):
            Path of the output file.

        records (list of records):
            Sequence of records to save.

        output_type (type):
            Output record type.
            If ``None``, it is guessed from the file extension.

        split_args (list):
            Positional arguments for :meth:`Record.split`.

        split_kwargs (dict):
            Keyword arguments for :meth:`Record.split`.

    Example:
        >>> from hexrec.formats.intel import Record as IntelRecord
        >>> records = list(IntelRecord.split(bytes(range(256))))
        >>> save_records('bytes.hex', records)
        >>> load_records('bytes.hex') == records
        True
    """
    if output_type is None:
        output_type = find_record_type(path)

    if records:
        if not all(isinstance(r, output_type) for r in records):
            records = convert_records(records, output_type=output_type,
                                      split_args=split_args,
                                      split_kwargs=split_kwargs)
    else:
        records = ()

    output_type.save_records(path, records)


def load_blocks(
    path: str,
    record_type: Optional[Type['Record']] = None,
):
    r"""Loads blocks from a record file.

    Arguments:
        path (str):
            Path of the input file.

        record_type (type):
            Explicit record type.
            If ``None``, it is guessed from the file extension.

    Returns:
        list of blocks: Blocks loaded from `path`.

    Example:
        >>> blocks = [(n, bytes(range(n, n + 16))) for n in range(0, 256, 16)]
        >>> save_blocks('bytes.mot', blocks)
        >>> load_blocks('bytes.mot') == blocks
        True
    """
    if record_type is None:
        record_type = find_record_type(path)

    blocks = record_type.load_blocks(path)
    return blocks


def save_blocks(
    path: str,
    blocks: BlockSequence,
    record_type: Optional[Type['Record']] = None,
    split_args: Optional[Sequence[Any]] = None,
    split_kwargs: Optional[Mapping[str, Any]] = None,
    build_args: Optional[Sequence[Any]] = None,
    build_kwargs: Optional[Mapping[str, Any]] = None,
) -> None:
    r"""Saves blocks to a record file.

    Arguments:
        path (str):
            Path of the output file.

        blocks (list of blocks):
            Sequence of blocks to save.

        record_type (type):
            Explicit record type.
            If ``None``, it is guessed from the file extension.

        split_args (list):
            Positional arguments for :meth:`Record.split`.

        split_kwargs (dict):
            Keyword arguments for :meth:`Record.split`.

        build_args (list):
            Positional arguments for :meth:`Record.build_standalone`.

        build_kwargs (dict):
            Keyword arguments for :meth:`Record.build_standalone`.

    Example:
        >>> blocks = [(n, bytes(range(n, n + 16))) for n in range(0, 256, 16)]
        >>> save_blocks('bytes.hex', blocks)
        >>> load_blocks('bytes.hex') == blocks
        True
    """
    if record_type is None:
        record_type = find_record_type(path)

    record_type.save_blocks(path, blocks,
                            split_args=split_args,
                            split_kwargs=split_kwargs,
                            build_args=build_args,
                            build_kwargs=build_kwargs)


def load_memory(
    path: str,
    record_type: Optional[Type['Record']] = None,
) -> Memory:
    r"""Loads a virtual memory from a file.

    Arguments:
        path (str):
            Path of the input file.

        record_type (type):
            Explicit record type.
            If ``None``, it is guessed from the file extension.

    Returns:
        :obj:`Memory`: Virtual memory holding data from `path`.

    Example:
        >>> blocks = [(n, bytes(range(n, n + 16))) for n in range(0, 256, 16)]
        >>> memory = Memory(blocks=blocks)
        >>> save_memory('bytes.mot', memory)
        >>> load_memory('bytes.mot') == memory
        True
    """
    if record_type is None:
        record_type = find_record_type(path)

    memory = record_type.load_memory(path)
    return memory


def save_memory(
    path: str,
    memory: Memory,
    record_type: Optional[Type['Record']] = None,
    split_args: Optional[Sequence[Any]] = None,
    split_kwargs: Optional[Mapping[str, Any]] = None,
) -> None:
    r"""Saves a virtual memory to a record file.

    Arguments:
        path (str):
            Path of the output file.

        memory (:obj:`Memory`):
            A virtual memory.

        record_type (type):
            Explicit record type.
            If ``None``, it is guessed from the file extension.

        split_args (list):
            Positional arguments for :meth:`Record.split`.

        split_kwargs (dict):
            Keyword arguments for :meth:`Record.split`.

    Example:
        >>> blocks = [(n, bytes(range(n, n + 16))) for n in range(0, 256, 16)]
        >>> memory = Memory(blocks=blocks)
        >>> save_memory('bytes.hex', memory)
        >>> load_memory('bytes.hex') == memory
        True
    """
    if record_type is None:
        record_type = find_record_type(path)

    record_type.save_memory(path, memory,
                            split_args=split_args,
                            split_kwargs=split_kwargs)


def save_chunk(
    path: str,
    chunk: AnyBytes,
    address: int = 0,
    record_type: Optional[Type['Record']] = None,
    split_args: Optional[Sequence[Any]] = None,
    split_kwargs: Optional[Mapping[str, Any]] = None,
) -> None:
    r"""Saves a data chunk to a record file.

    Arguments:
        path (str):
            Path of the output file.

        chunk (bytes):
            A chunk of data.

        address (int):
            Address of the data chunk.

        record_type (type):
            Explicit record type.
            If ``None``, it is guessed from the file extension.

        split_args (list):
            Positional arguments for :meth:`Record.split`.

        split_kwargs (dict):
            Keyword arguments for :meth:`Record.split`.

    Example:
        >>> data = bytes(range(256))
        >>> save_chunk('bytes.mot', data, 0x12345678)
        >>> load_blocks('bytes.mot') == [(0x12345678, data)]
        True
    """
    save_blocks(path, [(address, chunk)],
                record_type=record_type,
                split_args=split_args,
                split_kwargs=split_kwargs)


class Tag(enum.IntEnum):
    """Abstract record tag."""

    @classmethod
    def is_data(
        cls: Type['Tag'],
        value: Optional[Union[int, 'Tag']],
    ) -> bool:
        r"""bool: `value` is a data record tag."""
        del cls, value
        return True  # by default, all records are data records


class Record:
    r"""Abstract record type.

    A record is the basic structure of a record file.

    This is an abstract class, so it provides basic generic methods shared by
    most of the :class:`Record` implementations.
    Please refer to the actual subclass for more details.

    Attributes:
        address (int):
            Tells where its `data` starts in the memory addressing space,
            or an address with a special meaning.

        tag (int):
            Defines the logical meaning of the `address` and `data` fields.

        data (bytes):
            Byte data as required by the `tag`.

        count (int):
            Counts its fields as required by the :class:`Record` subclass
            implementation.

        checksum (int):
            Computes the checksum as required by most :class:`Record`
            implementations.

    Arguments:
        address (int):
            Record `address` field.

        tag (int):
            Record `tag` field.

        data (bytes):
            Record `data` field.

        checksum (int):
            Record `checksum` field.
            ``Ellipsis`` makes the constructor compute its actual value
            automatically.
            ``None`` assigns ``None``.

    Examples:
        >>> from hexrec.formats.binary import Record as BinaryRecord
        >>> BinaryRecord(0x1234, None, b'Hello, World!')
        ... #doctest: +NORMALIZE_WHITESPACE
        Record(address=0x00001234, tag=None, count=13,
               data=b'Hello, World!', checksum=0x69)

        >>> from hexrec.formats.motorola import Record as MotorolaRecord
        >>> from hexrec.formats.motorola import Tag as MotorolaTag
        >>> MotorolaRecord(0x1234, MotorolaTag.DATA_16, b'Hello, World!')
        ... #doctest: +NORMALIZE_WHITESPACE
        Record(address=0x00001234, tag=<MotorolaTag.DATA_16: 1>,
               count=16, data=b'Hello, World!', checksum=0x40)

        >>> from hexrec.formats.intel import Record as IntelRecord
        >>> from hexrec.formats.intel import Tag as IntelTag
        >>> IntelRecord(0x1234, IntelTag.DATA, b'Hello, World!')
        ... #doctest: +NORMALIZE_WHITESPACE
        Record(address=0x00001234, tag=<IntelTag.DATA: 0>, count=13,
               data=b'Hello, World!', checksum=0x44)
    """
    def __init__(
        self: 'Record',
        address: int,
        tag: Optional[Union[Tag, int]],
        data: AnyBytes,
        checksum: Optional[Union[int, type(Ellipsis)]] = Ellipsis,
    ) -> None:
        self.address: int = address
        self.tag: Optional[Union[Tag, int]] = tag
        self.data: AnyBytes = data
        self.checksum: Optional[Union[int, type(Ellipsis)]] = None
        self.count: int = -1  # invalidate

        self.update_count()
        if checksum is Ellipsis:
            self.update_checksum()
        else:
            self.checksum = checksum

    __slots__ = ('tag', 'count', 'address', 'data', 'checksum')

    TAG_TYPE: Optional[Type[Tag]] = Tag
    r"""Associated Python class for tags."""

    LINE_SEP: Union[bytes, str] = '\n'
    r"""Separator between record lines.

    If subclass of :obj:`bytes`, it is considered as a binary file.
    """

    EXTENSIONS: Sequence[str] = ()
    r"""File extensions typically mapped to this record type."""

    def __repr__(
        self: 'Record',
    ) -> str:
        text = (f'{type(self).__name__}('
                f'address=0x{self.address:08X}, '
                f'tag={self.tag!r}, '
                f'count={self.count:d}, '
                f'data={self.data!r}, '
                f'checksum=0x{(self._get_checksum() or 0):02X}'
                f')')
        return text

    def __str__(
        self: 'Record',
    ) -> str:
        r"""Converts to text string.

        Builds a printable text representation of the record, usually the same
        found in the saved record file as per its :class:`Record` subclass
        requirements.

        Returns:
            str: A printable text representation of the record.

        Examples:
            >>> from hexrec.formats.binary import Record as BinaryRecord
            >>> str(BinaryRecord(0x1234, None, b'Hello, World!'))
            '48656C6C6F2C20576F726C6421'

            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> from hexrec.formats.motorola import Tag as MotorolaTag
            >>> str(MotorolaRecord(0x1234, MotorolaTag.DATA_16,
            ...                    b'Hello, World!'))
            'S110123448656C6C6F2C20576F726C642140'

            >>> from hexrec.formats.intel import Record as IntelRecord
            >>> from hexrec.formats.intel import Tag as IntelTag
            >>> str(IntelRecord(0x1234, IntelTag.DATA, b'Hello, World!'))
            ':0D12340048656C6C6F2C20576F726C642144'
        """
        return repr(self)

    def __eq__(
        self: 'Record',
        other: 'Record',
    ) -> bool:
        r"""Equality comparison.

        Returns:
            bool: The `address`, `tag`, and `data` fields are equal.

        Examples:
            >>> from hexrec.formats.binary import Record as BinaryRecord
            >>> record1 = BinaryRecord.build_data(0, b'Hello, World!')
            >>> record2 = BinaryRecord.build_data(0, b'Hello, World!')
            >>> record1 == record2
            True

            >>> from hexrec.formats.binary import Record as BinaryRecord
            >>> record1 = BinaryRecord.build_data(0, b'Hello, World!')
            >>> record2 = BinaryRecord.build_data(1, b'Hello, World!')
            >>> record1 == record2
            False

            >>> from hexrec.formats.binary import Record as BinaryRecord
            >>> record1 = BinaryRecord.build_data(0, b'Hello, World!')
            >>> record2 = BinaryRecord.build_data(0, b'hello, world!')
            >>> record1 == record2
            False

            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> record1 = MotorolaRecord.build_header(b'Hello, World!')
            >>> record2 = MotorolaRecord.build_data(0, b'hello, world!')
            >>> record1 == record2
            False
        """
        return (self.address == other.address and
                self.tag == other.tag and
                self.data == other.data)

    def __hash__(
        self: 'Record',
    ) -> int:
        r"""Computes the hash value.

        Computes the hash of the :class:`Record` fields.
        Useful to make the record hashable although it is a mutable class.

        Returns:
            int: Hash of the :class:`Record` fields.

        Warning:
            Be careful with hashable mutable objects!

        Examples:
            >>> from hexrec.formats.binary import Record as BinaryRecord
            >>> hash(BinaryRecord(0x1234, None, b'Hello, World!'))
            ... #doctest: +SKIP
            7668968047460943252

            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> from hexrec.formats.motorola import Tag as MotorolaTag
            >>> hash(MotorolaRecord(0x1234, MotorolaTag.DATA_16,
            ...                             b'Hello, World!'))
            ... #doctest: +SKIP
            7668968047460943265

            >>> from hexrec.formats.intel import Record as IntelRecord
            >>> from hexrec.formats.intel import Tag as IntelTag
            >>> hash(IntelRecord(0x1234, IntelTag.DATA, b'Hello, World!'))
            ... #doctest: +SKIP
            7668968047460943289
        """
        return (hash(int(self.address or 0)) ^
                hash(int(self.tag or 0)) ^
                hash(bytes(self.data or b'')) ^
                hash(int(self.count or 0)) ^
                hash(int(self.checksum or 0)))

    def __lt__(
        self: 'Record',
        other: 'Record',
    ) -> bool:
        r"""Less-than comparison.

        Returns:
            bool: `address` less than `other`'s.

        Examples:
            >>> from hexrec.formats.binary import Record as BinaryRecord
            >>> record1 = BinaryRecord(0x1234, None, b'')
            >>> record2 = BinaryRecord(0x4321, None, b'')
            >>> record1 < record2
            True

            >>> from hexrec.formats.binary import Record as BinaryRecord
            >>> record1 = BinaryRecord(0x4321, None, b'')
            >>> record2 = BinaryRecord(0x1234, None, b'')
            >>> record1 < record2
            False
        """
        return self.address < other.address

    def is_data(
        self: 'Record',
    ) -> bool:
        r"""Tells if it is a data record.

        Tells whether the record contains plain binary data, i.e. it is not a
        *special* record.

        Returns:
            bool: The record contains plain binary data.

        Examples:
            >>> from hexrec.formats.binary import Record as BinaryRecord
            >>> BinaryRecord(0, None, b'Hello, World!').is_data()
            True

            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> from hexrec.formats.motorola import Tag as MotorolaTag
            >>> MotorolaRecord(0, MotorolaTag.DATA_16,
            ...                b'Hello, World!').is_data()
            True

            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> from hexrec.formats.motorola import Tag as MotorolaTag
            >>> MotorolaRecord(0, MotorolaTag.HEADER,
            ...                b'Hello, World!').is_data()
            False

            >>> from hexrec.formats.intel import Record as IntelRecord
            >>> from hexrec.formats.intel import Tag as IntelTag
            >>> IntelRecord(0, IntelTag.DATA, b'Hello, World!').is_data()
            True

            >>> from hexrec.formats.intel import Record as IntelRecord
            >>> from hexrec.formats.intel import Tag as IntelTag
            >>> IntelRecord(0, IntelTag.END_OF_FILE, b'').is_data()
            False
        """
        return self.TAG_TYPE.is_data(self.tag)

    def compute_count(
        self: 'Record',
    ) -> Optional[int]:
        r"""Computes the count.

        Returns:
            bool: `count` field value based on the current fields.

        Examples:
            >>> from hexrec.formats.binary import Record as BinaryRecord
            >>> record = BinaryRecord(0, None, b'Hello, World!')
            >>> str(record)
            '48656C6C6F2C20576F726C6421'
            >>> record.compute_count()
            13

            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> from hexrec.formats.motorola import Tag as MotorolaTag
            >>> record = MotorolaRecord(0, MotorolaTag.DATA_16,
            ...                         b'Hello, World!')
            >>> str(record)
            'S110000048656C6C6F2C20576F726C642186'
            >>> record.compute_count()
            16

            >>> from hexrec.formats.intel import Record as IntelRecord
            >>> from hexrec.formats.intel import Tag as IntelTag
            >>> record = IntelRecord(0, IntelTag.DATA, b'Hello, World!')
            >>> str(record)
            ':0D00000048656C6C6F2C20576F726C64218A'
            >>> record.compute_count()
            13
        """
        return len(self.data or b'')

    def update_count(
        self: 'Record',
    ) -> None:
        r"""Updates the `count` field via :meth:`compute_count`."""
        self.count = self.compute_count()

    def compute_checksum(
        self: 'Record',
    ) -> Optional[int]:
        r"""Computes the checksum.

        Returns:
            int: `checksum` field value based on the current fields.

        Examples:
            >>> from hexrec.formats.binary import Record as BinaryRecord
            >>> record = BinaryRecord(0, None, b'Hello, World!')
            >>> str(record)
            '48656C6C6F2C20576F726C6421'
            >>> hex(record.compute_checksum())
            '0x69'

            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> from hexrec.formats.motorola import Tag as MotorolaTag
            >>> record = MotorolaRecord(0, MotorolaTag.DATA_16,
            ...                         b'Hello, World!')
            >>> str(record)
            'S110000048656C6C6F2C20576F726C642186'
            >>> hex(record.compute_checksum())
            '0x86'

            >>> from hexrec.formats.intel import Record as IntelRecord
            >>> from hexrec.formats.intel import Tag as IntelTag
            >>> record = IntelRecord(0, IntelTag.DATA, b'Hello, World!')
            >>> str(record)
            ':0D00000048656C6C6F2C20576F726C64218A'
            >>> hex(record.compute_checksum())
            '0x8a'
        """
        return sum_bytes(self.data or b'') & 0xFF

    def update_checksum(
        self: 'Record',
    ) -> None:
        r"""Updates the `checksum` field via :meth:`compute_count`."""
        self.checksum = self.compute_checksum()

    def _get_checksum(
        self: 'Record',
    ) -> Optional[int]:
        r"""int: The `checksum` field itself if not ``None``, the
            value computed by :meth:`compute_count` otherwise.
        """
        if self.checksum is None:
            return self.compute_checksum()
        else:
            return self.checksum

    def check(
        self: 'Record',
    ) -> None:
        r"""Performs consistency checks.

        Raises:
            :obj:`ValueError`: a field is inconsistent.
        """
        if not 0 <= self.address:
            raise ValueError('address overflow')

        if self.tag is not None and not 0x00 <= self.tag <= 0xFF:
            raise ValueError('tag overflow')

        if not 0x00 <= self.count <= 0xFF:
            raise ValueError('count overflow')

        if self.data is None:
            raise ValueError('no data')

        if self.checksum is not None:
            if not 0x00 <= self.checksum <= 0xFF:
                raise ValueError('checksum overflow')

            if self.checksum != self.compute_checksum():
                raise ValueError('checksum error')

    def overlaps(
        self: 'Record',
        other: 'Record',
    ) -> bool:
        r"""Checks if overlapping occurs.

        This record and another have overlapping `data`, when both `address`
        fields are not ``None``.

        Arguments:
            other (record):
                Record to compare with `self`.

        Returns:
            bool: Overlapping.

        Examples:
            >>> from hexrec.formats.binary import Record as BinaryRecord
            >>> record1 = BinaryRecord(0, None, b'abc')
            >>> record2 = BinaryRecord(1, None, b'def')
            >>> record1.overlaps(record2)
            True

            >>> from hexrec.formats.binary import Record as BinaryRecord
            >>> record1 = BinaryRecord(0, None, b'abc')
            >>> record2 = BinaryRecord(3, None, b'def')
            >>> record1.overlaps(record2)
            False
        """
        if self.address is None or other.address is None:
            return False
        else:
            return do_overlap(self.address,
                              self.address + len(self.data or b''),
                              other.address,
                              other.address + len(other.data or b''))

    @classmethod
    def _open_input(
        cls: Type['Record'],
        path: str,
    ) -> IO:
        r"""Opens a file for input.

        Arguments:
            path (str):
                File path.

        Returns:
            stream: An input stream handle.
        """
        if isinstance(cls.LINE_SEP, (bytes, bytearray)):
            mode = 'rb'
        else:
            mode = 'rt'
        return open_file(path, mode)

    @classmethod
    def _open_output(
        cls: Type['Record'],
        path: str,
    ) -> IO:
        r"""Opens a file for output.

        Arguments:
            path (str):
                File path.

        Returns:
            stream: An output stream handle.
        """
        if isinstance(cls.LINE_SEP, (bytes, bytearray)):
            mode = 'wb'
        else:
            mode = 'wt'
        return open_file(path, mode)

    @classmethod
    def parse_record(
        cls: Type['Record'],
        line: str,
        *args: Any,
        **kwargs: Any,
    ) -> 'Record':
        r"""Parses a record from a text line.

        Arguments:
            line (str):
                Record line to parse.

            args (tuple):
                Further positional arguments for overriding.

            kwargs (dict):
                Further keyword arguments for overriding.

        Returns:
            record: Parsed record.

        Note:
            This method must be overridden.
        """
        raise NotImplementedError('method must be overriden')

    def marshal(
        self: 'Record',
        *args: Any,
        **kwargs: Any,
    ) -> Union[bytes, bytearray, str]:
        r"""Marshals a record for output.

        Arguments:
            args (tuple):
                Further positional arguments for overriding.

            kwargs (dict):
                Further keyword arguments for overriding.

        Returns:
            bytes or str: Data for output, according to the file type.
        """
        check_empty_args_kwargs(args, kwargs)

        return str(self)

    @classmethod
    def unmarshal(
        cls: Type['Record'],
        data: Union[AnyBytes, str],
        *args: Any,
        **kwargs: Any,
    ) -> 'Record':
        r"""Unmarshals a record from input.

        Arguments:
            data (bytes or str):
                Input data, according to the file type.

            args (tuple):
                Further positional arguments for overriding.

            kwargs (dict):
                Further keyword arguments for overriding.

        Returns:
            record: Unmarshaled record.
        """
        check_empty_args_kwargs(args, kwargs)

        return cls.parse_record(data, *args, **kwargs)

    @classmethod
    def get_metadata(
        cls: 'Record',
        records: RecordSequence,
    ) -> Mapping[str, Any]:
        r"""Retrieves metadata from records.

        Metadata is specific of each record type.
        The most common metadata are:

        * `columns`: maximum data columns per line.
        * `start`: program execution start address.
        * `count`: some count of record lines.
        * `header`: some header data.

        When no such information is found, its keyword is either skipped or
        its value is ``None``.

        Arguments:
            records (list of records):
                Records to scan for metadata.

        Returns:
            dict: Collected metadata.
        """
        columns = 0

        for record in records:
            if record.is_data():
                columns = max(columns, len(record.data or b''))

        metadata = {
            'columns': columns,
        }
        return metadata

    @classmethod
    def split(
        cls: Type['Record'],
        data: AnyBytes,
        *args: Any,
        **kwargs: Any,
    ) -> Iterator['Record']:
        r"""Splits a chunk of data into records.

        Arguments:
            data (bytes):
                Byte data to split.

            args (tuple):
                Further positional arguments for overriding.

            kwargs (dict):
                Further keyword arguments for overriding.

        Returns:
            list: List of records.

        Note:
            This method must be overridden.
        """
        check_empty_args_kwargs(args, kwargs)
        yield from ()

    @classmethod
    def build_standalone(
        cls: Type['Record'],
        data_records: RecordSequence,
        *args: Any,
        **kwargs: Any,
    ) -> Iterator['Record']:
        r"""Makes a sequence of data records standalone.

        Arguments:
            data_records (list of records):
                Sequence of data records.

            args (tuple):
                Further positional arguments for overriding.

            kwargs (dict):
                Further keyword arguments for overriding.

        Yields:
            record: Records for a standalone record file.
        """
        check_empty_args_kwargs(args, kwargs)

        yield from data_records

    @classmethod
    def check_sequence(
        cls: Type['Record'],
        records: RecordSequence,
    ) -> None:
        r"""Consistency check of a sequence of records.

        Arguments:
            records (list of records):
                Sequence of records.

        Raises:
            :obj:`ValueError`: A field is inconsistent.
        """
        last = None
        record_endex = 0

        for record in records:
            record.check()

            if record.is_data():
                if last is not None:
                    if record.overlaps(last):
                        raise ValueError('overlapping records')

                    if record.address < record_endex:
                        raise ValueError('unsorted records')

                last = record

            record_endex = record.address + len(record.data)

    @classmethod
    def readdress(
        cls: Type['Record'],
        records: RecordSequence,
    ) -> None:
        r"""Converts to flat addressing.

        Some record types, notably the *Intel HEX*, store records by some
        *segment/offset* addressing flavor.
        As this library adopts *flat* addressing instead, all the record
        addresses should be converted to *flat* addressing after loading.
        This procedure readdresses a sequence of records in-place.

        Warning:
            Only the `address` field is modified. All the other fields hold
            their previous value.

        Arguments:
            records (list):
                Sequence of records to be converted to *flat* addressing,
                in-place.
        """
        pass

    @classmethod
    def read_blocks(
        cls: Type['Record'],
        stream: IO,
    ) -> BlockSequence:
        r"""Reads blocks from a stream.

        Read blocks from the input stream into the returned sequence.

        Arguments:
            stream (stream):
                Input stream of the blocks to read.

        Returns:
            list of blocks: Sequence of parsed blocks.

        Example:
            >>> import io
            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> blocks = [(0, b'abc'), (16, b'def')]
            >>> stream = io.StringIO()
            >>> MotorolaRecord.write_blocks(stream, blocks)
            >>> _ = stream.seek(0, io.SEEK_SET)
            >>> MotorolaRecord.read_blocks(stream)
            [(0, b'abc'), (16, b'def')]
        """
        records = cls.read_records(stream)
        cls.readdress(records)
        blocks = records_to_blocks(records)
        return blocks

    @classmethod
    def write_blocks(
        cls: Type['Record'],
        stream: IO,
        blocks: BlockSequence,
        split_args: Optional[Sequence[Any]] = None,
        split_kwargs: Optional[Mapping[str, Any]] = None,
        build_args: Optional[Sequence[Any]] = None,
        build_kwargs: Optional[Mapping[str, Any]] = None,
    ) -> None:
        r"""Writes blocks to a stream.

        Each block of the `blocks` sequence is converted into a record via
        :meth:`build_data` and written to the output stream.

        Arguments:
            stream (stream):
                Output stream of the records to write.

            blocks (list of blocks):
                Sequence of records to store.

            split_args (list):
                Positional arguments for :meth:`Record.split`.

            split_kwargs (dict):
                Keyword arguments for :meth:`Record.split`.

            build_args (list):
                Positional arguments for :meth:`Record.build_standalone`.

            build_kwargs (dict):
                Keyword arguments for :meth:`Record.build_standalone`.

        Example:
            >>> import io
            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> blocks = [(0, b'abc'), (16, b'def')]
            >>> stream = io.StringIO()
            >>> MotorolaRecord.write_blocks(stream, blocks)
            >>> stream.getvalue()
            'S0030000FC\nS1060000616263D3\nS1060010646566BA\nS5030002FA\nS9030000FC\n'
        """
        records = blocks_to_records(blocks, cls,
                                    split_args=split_args,
                                    split_kwargs=split_kwargs,
                                    build_args=build_args,
                                    build_kwargs=build_kwargs)
        cls.write_records(stream, records)

    @classmethod
    def load_blocks(
        cls: Type['Record'], path: str,
    ) -> BlockSequence:
        r"""Loads blocks from a file.

        Each line of the input file is parsed via :meth:`parse_block`,
        and collected into the returned sequence.

        Arguments:
            path (str):
                Path of the record file to load.

        Returns:
            list of records: Sequence of parsed records.

        Example:
            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> with open('load_blocks.mot', 'wt') as f:
            ...     f.write('S0030000FC\n')
            ...     f.write('S1060000616263D3\n')
            ...     f.write('S1060010646566BA\n')
            ...     f.write('S5030002FA\n')
            ...     f.write('S9030000FC\n')
            >>> MotorolaRecord.load_blocks('load_blocks.mot')
            [(0, b'abc'), (16, b'def')]
        """
        with cls._open_input(path) as stream:
            blocks = cls.read_blocks(stream)
        return blocks

    @classmethod
    def save_blocks(
        cls: Type['Record'],
        path: str,
        blocks: BlockSequence,
        split_args: Optional[Sequence[Any]] = None,
        split_kwargs: Optional[Mapping[str, Any]] = None,
        build_args: Optional[Sequence[Any]] = None,
        build_kwargs: Optional[Mapping[str, Any]] = None,
    ) -> None:
        r"""Saves blocks to a file.

        Each block of the `blocks` sequence is converted into a record via
        :meth:`build_data` and written to the output file.

        Arguments:
            path (str):
                Path of the record file to save.

            blocks (list of blocks):
                Sequence of blocks to store.

            split_args (list):
                Positional arguments for :meth:`Record.split`.

            split_kwargs (dict):
                Keyword arguments for :meth:`Record.split`.

            build_args (list):
                Positional arguments for :meth:`Record.build_standalone`.

            build_kwargs (dict):
                Keyword arguments for :meth:`Record.build_standalone`.

        Example:
            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> blocks = [(0, b'abc'), (16, b'def')]
            >>> MotorolaRecord.save_blocks('save_blocks.mot', blocks)
            >>> with open('save_blocks.mot', 'rt') as f: text = f.read()
            >>> text
            'S0030000FC\nS1060000616263D3\nS1060010646566BA\nS5030002FA\nS9030000FC\n'
        """
        with cls._open_output(path) as stream:
            cls.write_blocks(stream, blocks,
                             split_args=split_args, split_kwargs=split_kwargs,
                             build_args=build_args, build_kwargs=build_kwargs)
            stream.flush()

    @classmethod
    def read_memory(
        cls: Type['Record'],
        stream: IO,
    ) -> Memory:
        r"""Reads a virtual memory from a stream.

        Read blocks from the input stream into the returned sequence.

        Arguments:
            stream (stream):
                Input stream of the blocks to read.

        Returns:
            :obj:`Memory`: Loaded virtual memory.

        Example:
            >>> import io
            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> blocks = [(0, b'abc'), (16, b'def')]
            >>> stream = io.StringIO()
            >>> MotorolaRecord.write_blocks(stream, blocks)
            >>> _ = stream.seek(0, io.SEEK_SET)
            >>> memory = MotorolaRecord.read_memory(stream)
            >>> memory.blocks
            [(0, b'abc'), (16, b'def')]
        """
        blocks = cls.read_blocks(stream)
        memory = Memory()
        memory.blocks = blocks  # avoid useless constructor operations
        return memory

    @classmethod
    def write_memory(
        cls: Type['Record'],
        stream: IO,
        memory: Memory,
        split_args: Optional[Sequence[Any]] = None,
        split_kwargs: Optional[Mapping[str, Any]] = None,
        build_args: Optional[Sequence[Any]] = None,
        build_kwargs: Optional[Mapping[str, Any]] = None,
    ) -> None:
        r"""Writes a virtual memory to a stream.

        Arguments:
            stream (stream):
                Output stream of the records to write.

            memory (:obj:`Memory`):
                Virtual memory to save.

            split_args (list):
                Positional arguments for :meth:`Record.split`.

            split_kwargs (dict):
                Keyword arguments for :meth:`Record.split`.

            build_args (list):
                Positional arguments for :meth:`Record.build_standalone`.

            build_kwargs (dict):
                Keyword arguments for :meth:`Record.build_standalone`.

        Example:
            >>> import io
            >>> from hexrec.blocks import Memory
            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> memory = Memory(blocks=[(0, b'abc'), (16, b'def')])
            >>> stream = io.StringIO()
            >>> MotorolaRecord.write_memory(stream, memory)
            >>> stream.getvalue()
            'S0030000FC\nS1060000616263D3\nS1060010646566BA\nS5030002FA\nS9030000FC\n'
        """
        cls.write_blocks(stream, memory.blocks,
                         split_args=split_args, split_kwargs=split_kwargs,
                         build_args=build_args, build_kwargs=build_kwargs)

    @classmethod
    def load_memory(
        cls: Type['Record'],
        path: str,
    ) -> Memory:
        r"""Loads a virtual memory from a file.

        Arguments:
            path (str):
                Path of the record file to load.

        Returns:
            :obj:`Memory`: Loaded virtual memory.

        Example:
            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> with open('load_blocks.mot', 'wt') as f:
            ...     f.write('S0030000FC\n')
            ...     f.write('S1060000616263D3\n')
            ...     f.write('S1060010646566BA\n')
            ...     f.write('S5030002FA\n')
            ...     f.write('S9030000FC\n')
            >>> memory = MotorolaRecord.load_memory('load_blocks.mot')
            >>> memory.blocks
            [(0, b'abc'), (16, b'def')]
        """
        with cls._open_input(path) as stream:
            memory = cls.read_memory(stream)
        return memory

    @classmethod
    def save_memory(
        cls: Type['Record'],
        path: str,
        memory: Memory,
        split_args: Optional[Sequence[Any]] = None,
        split_kwargs: Optional[Mapping[str, Any]] = None,
        build_args: Optional[Sequence[Any]] = None,
        build_kwargs: Optional[Mapping[str, Any]] = None,
    ) -> None:
        r"""Saves a virtual memory to a file.

        Arguments:
            path (str):
                Path of the record file to save.

            memory (:obj:`Memory`):
                Virtual memory to store.

            split_args (list):
                Positional arguments for :meth:`Record.split`.

            split_kwargs (dict):
                Keyword arguments for :meth:`Record.split`.

            build_args (list):
                Positional arguments for :meth:`Record.build_standalone`.

            build_kwargs (dict):
                Keyword arguments for :meth:`Record.build_standalone`.

        Example:
            >>> from hexrec.blocks import Memory
            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> memory = Memory(blocks=[(0, b'abc'), (16, b'def')])
            >>> MotorolaRecord.save_memory('save_memory.mot', memory)
            >>> with open('save_memory.mot', 'rt') as f: text = f.read()
            >>> text
            'S0030000FC\nS1060000616263D3\nS1060010646566BA\nS5030002FA\nS9030000FC\n'
        """
        with cls._open_output(path) as stream:
            cls.write_memory(stream, memory,
                             split_args=split_args, split_kwargs=split_kwargs,
                             build_args=build_args, build_kwargs=build_kwargs)
            stream.flush()

    @classmethod
    def read_records(
        cls: Type['Record'],
        stream: IO,
    ) -> RecordList:
        r"""Reads records from a stream.

        For text files, each line of the input file is parsed via
        :meth:`parse`, and collected into the returned sequence.

        For binary files, everything to the end of the stream is parsed as a
        single record.

        Arguments:
            stream (stream):
                Input stream of the records to read.

        Returns:
            list of records: Sequence of parsed records.

        Example:
            >>> import io
            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> blocks = [(0, b'abc'), (16, b'def')]
            >>> stream = io.StringIO()
            >>> MotorolaRecord.write_blocks(stream, blocks)
            >>> _ = stream.seek(0, io.SEEK_SET)
            >>> records = MotorolaRecord.read_records(stream)
            >>> records  #doctest: +NORMALIZE_WHITESPACE
            [Record(address=0x00000000, tag=<Tag.HEADER: 0>, count=3,
                    data=b'', checksum=0xFC),
             Record(address=0x00000000, tag=<Tag.DATA_16: 1>, count=6,
                    data=b'abc', checksum=0xD3),
             Record(address=0x00000010, tag=<Tag.DATA_16: 1>, count=6,
                    data=b'def', checksum=0xBA),
             Record(address=0x00000000, tag=<Tag.COUNT_16: 5>, count=3,
                    data=b'\x00\x02', checksum=0xFA),
             Record(address=0x00000000, tag=<Tag.START_16: 9>, count=3,
                    data=b'', checksum=0xFC)]
        """
        if isinstance(cls.LINE_SEP, (bytes, bytearray)):
            records = [cls.unmarshal(stream.read())]
        else:
            records = [cls.unmarshal(line) for line in stream]
        return records

    @classmethod
    def write_records(
        cls: Type['Record'],
        stream: IO,
        records: RecordSequence,
    ) -> None:
        r"""Saves records to a stream.

        Each record of the `records` sequence is stored into the output file.

        Arguments:
            stream (stream):
                Output stream of the records to write.

            records (list of records):
                Sequence of records to store.

        Example:
            >>> import io
            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> from hexrec.records import blocks_to_records
            >>> blocks = [(0, b'abc'), (16, b'def')]
            >>> records = blocks_to_records(blocks, MotorolaRecord)
            >>> stream = io.StringIO()
            >>> MotorolaRecord.write_records(stream, records)
            >>> stream.getvalue()
            'S0030000FC\nS1060000616263D3\nS1060010646566BA\nS5030002FA\nS9030000FC\n'
        """
        for record in records:
            stream.write(record.marshal())
            stream.write(cls.LINE_SEP)

    @classmethod
    def load_records(
        cls: Type['Record'],
        path: str,
    ) -> RecordList:
        r"""Loads records from a file.

        Each line of the input file is parsed via :meth:`parse`, and
        collected into the returned sequence.

        Arguments:
            path (str):
                Path of the record file to load.

        Returns:
            list of records: Sequence of parsed records.

        Example:
            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> with open('load_records.mot', 'wt') as f:
            ...     f.write('S0030000FC\n')
            ...     f.write('S1060000616263D3\n')
            ...     f.write('S1060010646566BA\n')
            ...     f.write('S5030002FA\n')
            ...     f.write('S9030000FC\n')
            >>> records = MotorolaRecord.load_records('load_records.mot')
            >>> records  #doctest: +NORMALIZE_WHITESPACE
            [Record(address=0x00000000, tag=<Tag.HEADER: 0>, count=3,
                    data=b'', checksum=0xFC),
             Record(address=0x00000000, tag=<Tag.DATA_16: 1>, count=6,
                    data=b'abc', checksum=0xD3),
             Record(address=0x00000010, tag=<Tag.DATA_16: 1>, count=6,
                    data=b'def', checksum=0xBA),
             Record(address=0x00000000, tag=<Tag.COUNT_16: 5>, count=3,
                    data=b'\x00\x02', checksum=0xFA),
             Record(address=0x00000000, tag=<Tag.START_16: 9>, count=3,
                    data=b'', checksum=0xFC)]
        """
        with cls._open_input(path) as stream:
            records = cls.read_records(stream)
        return records

    @classmethod
    def save_records(
        cls: Type['Record'],
        path: str,
        records: RecordSequence,
    ):
        r"""Saves records to a file.

        Each record of the `records` sequence is converted into text via
        :func:`str`, and stored into the output text file.

        Arguments:
            path (str):
                Path of the record file to save.

            records (list):
                Sequence of records to store.

        Example:
            >>> from hexrec.formats.motorola import Record as MotorolaRecord
            >>> from hexrec.records import blocks_to_records
            >>> blocks = [(0, b'abc'), (16, b'def')]
            >>> records = blocks_to_records(blocks, MotorolaRecord)
            >>> MotorolaRecord.save_records('save_records.mot', records)
            >>> with open('save_records.mot', 'rt') as f: text = f.read()
            >>> text
            'S0030000FC\nS1060000616263D3\nS1060010646566BA\nS5030002FA\nS9030000FC\n'
        """
        with cls._open_output(path) as stream:
            cls.write_records(stream, records)
            stream.flush()


RECORD_TYPES: Mapping[str, Type[Record]] = {}
r"""Registered record types."""


# Workaround to always regsister official record types.
# Using a function to avoid namespace cluttering.
def __register_default_record_types():
    global RECORD_TYPES

    from hexrec.formats.ascii_hex import Record
    RECORD_TYPES['ascii_hex'] = Record

    from hexrec.formats.binary import Record
    RECORD_TYPES['binary'] = Record

    from hexrec.formats.intel import Record
    RECORD_TYPES['intel'] = Record

    from hexrec.formats.mos import Record
    RECORD_TYPES['mos'] = Record

    from hexrec.formats.motorola import Record
    RECORD_TYPES['motorola'] = Record

    from hexrec.formats.tektronix import Record
    RECORD_TYPES['tektronix'] = Record


__register_default_record_types()
RECORD_TYPES.update(
    (entry_point.name, entry_point.load())
    for entry_point in pkg_resources.iter_entry_points('hexrec_types')
)


def find_record_type_name(
    file_path: str,
) -> str:
    r"""Finds the record type name.

    Checks if the extension of `file_path` is a know record type, and returns
    its mapped name.

    Arguments:
        file_path (str):
            File path to get the file extension from.

    Returns:
        str: Record type name.

    Raises:
        :obj:`KeyError`: Unsupported extension.

    Example:
        >>> from hexrec.records import find_record_type_name
        >>> find_record_type_name('dummy.mot')
        'motorola'
    """
    ext = os.path.splitext(file_path)[1].lower()
    for name, record_type in RECORD_TYPES.items():
        extensions = record_type.EXTENSIONS
        if extensions and ext in extensions:
            return name
    else:
        raise KeyError('unsupported extension: ' + ext)


def find_record_type(
    file_path: str,
) -> Type[Record]:
    r"""Finds the record type class.

    Checks if the extension of `file_path` is a know record type, and returns
    its mapped type class.

    Arguments:
        file_path (str):
            File path to get the file extension from.

    Returns:
        str: Record type class.

    Raises:
        :obj:`KeyError`: Unsupported extension.

    Example:
        >>> from hexrec.records import find_record_type_name
        >>> find_record_type('dummy.mot').__name__
        'MotorolaRecord'
    """
    type_name = find_record_type_name(file_path)
    record_type = RECORD_TYPES[type_name]
    return record_type
