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

import enum
import os
import re
import struct

import six

from .blocks import SparseItems
from .blocks import collapse
from .blocks import merge
from .blocks import sorting
from .utils import chop
from .utils import do_overlap
from .utils import hexlify
from .utils import sum_bytes
from .utils import unhexlify


def get_data_records(records):
    r"""Extracts data records.

    Arguments:
        records(:obj:`list` of :obj:`Record`): Sequence of records.

    Returns:
        :obj:`list` of :obj:`Record`: Sequence of data records.

    Example:
        >>> from hexrec.blocks import chop_blocks
        >>> data = bytes(bytearray(range(256)))
        >>> blocks = list(chop_blocks(data, 16))
        >>> records = blocks_to_records(blocks, MotorolaRecord)
        >>> all(r.is_data() for r in get_data_records(records))
        True
    """
    data_records = [record for record in records if record.is_data()]
    return data_records


def find_corrupted_records(records):
    r"""Finds corrupted records.

    Arguments:
        records(:obj:`list` of :obj:`Record`): Sequence of records.

    Returns:
        :obj:`list` of :obj:`int`: Sequence of corrupted record indices.

    Example:
        >>> data = bytes(bytearray(range(256)))
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


def records_to_blocks(records):
    r"""Converts records to blocks.

    Extracts all the data records, collapses them in the order they compare in
    `records`, and merges the collapsed blocks.

    Arguments:
        records (:obj:`list` of :obj:`Record`): Sequence of records to
            convert to blocks. Sequence generators supported.

    Returns:
        :obj:`list` of block: A sequence of non-contiguous blocks, sorted by
            start address.

    Example:
        >>> from hexrec.blocks import chop_blocks, merge
        >>> data = bytes(bytearray(range(256)))
        >>> blocks = list(chop_blocks(data, 16))
        >>> records = blocks_to_records(blocks, MotorolaRecord)
        >>> records_to_blocks(records) == merge(blocks)
        True
    """
    blocks = [(r.address, r.data) for r in get_data_records(records)]
    blocks = collapse(blocks)
    blocks.sort(key=sorting)
    blocks = merge(blocks)
    return blocks


def blocks_to_records(blocks, record_type,
                      split_args=None, split_kwargs=None):
    r"""Converts blocks to records.

    Arguments:
        blocks (:obj:`list` of block): A sequence of non-contiguous blocks,
            sorted by start address.
        record_type (:class:`Record`): Output record type.
        split_args (list): Positional arguments for :meth:`Record.split`.
        split_kwargs (dict): Keyword arguments for :meth:`Record.split`.

    Returns:
        :obj:`list` of :obj:`Record`: Sequence of blocks split into records.

    Example:
        >>> from hexrec.blocks import chop_blocks, merge
        >>> data = bytes(bytearray(range(256)))
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

    records = list(record_type.build_standalone(data_records))
    return records


def merge_records(data_records, input_types=None, output_type=None,
                  split_args=None, split_kwargs=None):
    r"""Merges data records.

    Merges multiple sequences of data records where each sequence overwrites
    overlapping data of the previous sequences.

    Arguments:
        data_records: A vector of *data* record sequences. If `input_types` is
            not ``None``, sequence generators are supported for the vector and
            its nested sequences.
        input_types: Selects the record type for each of the sequences
            in `data_records`. ``None`` will choose that of the first
            element of the (indexable) sequence.
        output_type: Selects the output record type. ``None`` will choose that
            of the first `input_types`.
        split_args (list): Positional arguments for :meth:`Record.split`.
        split_kwargs (dict): Keyword arguments for :meth:`Record.split`.

    Returns:
        :obj:`list` of :obj:`Record`: A sequence of merged records.

    Example:
        >>> from hexrec.blocks import chop_blocks, merge
        >>> data1 = bytes(bytearray(range(0, 32)))
        >>> data2 = bytes(bytearray(range(96, 128)))
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

    blocks = []
    for records in data_records:
        blocks.extend((r.address, r.data) for r in records)

    blocks = collapse(blocks)
    blocks.sort(key=sorting)
    blocks = merge(blocks)

    output_records = blocks_to_records(blocks, output_type,
                                       split_args, split_kwargs)
    return output_records


def convert_records(records, input_type=None, output_type=None,
                    split_args=None, split_kwargs=None):
    r"""Converts records to another type.

    Arguments:
        records (list): A sequence of :class:`Record` elements.
            Sequence generators supported if `input_type` is specified.
        input_type (:class:`Record`): explicit type of `records` elements.
            If ``None``, it is taken from the first element of the (indexable)
            `records` sequence.
        output_type (:class:`Record`): explicit output type. If ``None``, it
            is reassigned as `input_type`.
        split_args (list): Positional arguments for :meth:`Record.split`.
        split_kwargs (dict): Keyword arguments for :meth:`Record.split`.

    Returns:
        :obj:`list` of :obj:`Record`: A sequence of merged records.

    Examples:
        >>> motorola = list(MotorolaRecord.split(bytes(range(256))))
        >>> intel = list(IntelRecord.split(bytes(range(256))))
        >>> converted = convert_records(motorola, output_type=IntelRecord)
        >>> converted == intel
        True

        >>> motorola = list(MotorolaRecord.split(bytes(range(256))))
        >>> intel = list(IntelRecord.split(bytes(range(256))))
        >>> converted = convert_records(intel, output_type=MotorolaRecord)
        >>> converted == motorola
        True
    """
    records = list(records)

    if input_type is None:
        input_type = type(records[0])
    if output_type is None:
        output_type = input_type

    records = [r for r in records if r.is_data()]
    output_records = merge_records([records], [input_type], output_type,
                                   split_args, split_kwargs)
    return output_records


def merge_files(input_files, output_file, input_types=None, output_type=None,
                split_args=None, split_kwargs=None):
    r"""Merges record files.

    Merges multiple record files where each file overwrites overlapping data
    of the previous files.

    Arguments:
        input_files (list): A sequence of file paths to merge.
        output_file (:obj:`str`): Path of the output file. It can target an
            input file.
        input_types: Selects the record type for each of the sequences
            in `data_records`. ``None`` will guess from file extension.
        output_type: Selects the output record type. ``None`` will guess from
            file extension.
        split_args (list): Positional arguments for :meth:`Record.split`.
        split_kwargs (dict): Keyword arguments for :meth:`Record.split`.

    Example:
        >>> merge_files(['merge1.mot', 'merge2.hex'], 'merged.tek')

    """
    if input_types is None:
        input_types = [None] * len(input_files)
    else:
        input_types = list(input_types)

    for level in range(len(input_types)):
        if input_types[level] is None:
            type_name = find_record_type(input_files[level])
            input_types[level] = RECORD_TYPES[type_name]

    if output_type is None:
        type_name = find_record_type(output_file)
        output_type = RECORD_TYPES[type_name]

    input_records = []
    for level in range(len(input_types)):
        input_type = input_types[level]
        records = input_type.load(input_files[level])
        input_type.readdress(records)
        records = [r for r in records if r.is_data()]
        input_records.append(records)

    output_records = merge_records(input_records, input_types, output_type,
                                   split_args, split_kwargs)
    output_type.save(output_file, output_records)


def convert_file(input_file, output_file, input_type=None, output_type=None,
                 split_args=None, split_kwargs=None):
    r"""Converts a record file to another record type.

    Arguments:
        input_file (:obj:`str`): Path of the input file.
        output_file (:obj:`str`): Path of the output file.
        input_type (:class:`Record`): Explicit input record type.
            If ``None``, it is guessed from the file extension.
        output_type (:class:`Record`): Explicit output record type.
            If ``None``, it is guessed from the file extension.
        split_args (list): Positional arguments for :meth:`Record.split`.
        split_kwargs (dict): Keyword arguments for :meth:`Record.split`.

    Example:
        >>> motorola = list(MotorolaRecord.split(bytes(range(256))))
        >>> intel = list(IntelRecord.split(bytes(range(256))))
        >>> save_records('bytes.mot', motorola)
        >>> convert_file('bytes.mot', 'bytes.hex')
        >>> load_records('bytes.hex') == intel
        True
    """
    merge_files([input_file], output_file, [input_type], output_type,
                split_args, split_kwargs)


def load_records(path, record_type=None):
    r"""Loads records from a record file.

    Arguments:
        path (:obj:`str`): Path of the input file.
        record_type (:class:`Record`): Explicit record type.
            If ``None``, it is guessed from the file extension.

    Example:
        >>> records = list(MotorolaRecord.split(bytes(range(256))))
        >>> save_records('bytes.mot', records)
        >>> load_records('bytes.mot') == records
        True
    """
    if record_type is None:
        type_name = find_record_type(path)
        record_type = RECORD_TYPES[type_name]
    records = record_type.load(path)
    return records


def save_records(path, records, output_type=None,
                 split_args=None, split_kwargs=None):
    r"""Saves records to a record file.

    Arguments:
        path (:obj:`str`): Path of the output file.
        records (list): Sequence of records to save.
        output_type (:class:`Record`): Output record type.
            If ``None``, it is guessed from the file extension.
        split_args (list): Positional arguments for :meth:`Record.split`.
        split_kwargs (dict): Keyword arguments for :meth:`Record.split`.

    Example:
        >>> records = list(IntelRecord.split(bytes(range(256))))
        >>> save_records('bytes.hex', records)
        >>> load_records('bytes.hex') == records
        True
    """
    if output_type is None:
        type_name = find_record_type(path)
        output_type = RECORD_TYPES[type_name]

    if records:
        if not all(isinstance(r, output_type) for r in records):
            records = convert_records(records, output_type=output_type,
                                      split_args=split_args,
                                      split_kwargs=split_kwargs)
    else:
        records = ()

    output_type.save(path, records)


def load_blocks(path, record_type=None):
    r"""Loads blocks from a record file.

    Arguments:
        path (:obj:`str`): Path of the input file.
        record_type (:class:`Record`): Explicit record type.
            If ``None``, it is guessed from the file extension.

    Returns:
        :obj:`list` of block: Sequence of non-overlapping blocks, sorted by
            start address.

    Example:
        >>> blocks = [(offset, bytes(bytearray(range(offset, offset + 16))))
        ...           for offset in range(0, 256, 16)]
        >>> save_blocks('bytes.mot', blocks)
        >>> load_blocks('bytes.mot') == blocks
        True
    """
    if record_type is None:
        type_name = find_record_type(path)
        record_type = RECORD_TYPES[type_name]

    records = record_type.load(path)
    blocks = records_to_blocks(records)
    return blocks


def save_blocks(path, blocks, record_type=None,
                split_args=None, split_kwargs=None):
    r"""Saves blocks to a record file.

    Arguments:
        path (:obj:`str`): Path of the output file.
        records (:obj:`list` of block): Sequence of non-overlapping blocks,
            sorted by start address.
        record_type (:class:`Record`): Explicit record type.
            If ``None``, it is guessed from the file extension.
        split_args (list): Positional arguments for :meth:`Record.split`.
        split_kwargs (dict): Keyword arguments for :meth:`Record.split`.

    Example:
        >>> blocks = [(offset, bytes(bytearray(range(offset, offset + 16))))
        ...           for offset in range(0, 256, 16)]
        >>> save_blocks('bytes.hex', blocks)
        >>> load_blocks('bytes.hex') == blocks
        True
    """
    if record_type is None:
        type_name = find_record_type(path)
        record_type = RECORD_TYPES[type_name]

    records = blocks_to_records(blocks, record_type, split_args, split_kwargs)
    record_type.save(path, records)


def load_memory(path, record_type=None):
    r"""Loads a virtual memory from a file.

    Arguments:
        path (:obj:`str`): Path of the input file.
        record_type (:class:`Record`): Explicit record type.
            If ``None``, it is guessed from the file extension.

    Returns:
        :obj:`SparseItems`: A virtual memory.

    Example:
        >>> blocks = [(offset, bytes(bytearray(range(offset, offset + 16))))
        ...           for offset in range(0, 256, 16)]
        >>> sparse_items = SparseItems(blocks=blocks)
        >>> save_memory('bytes.mot', sparse_items)
        >>> load_memory('bytes.mot') == sparse_items
        True
    """
    blocks = load_blocks(path, record_type)
    sparse_items = SparseItems(blocks=blocks)
    return sparse_items


def save_memory(path, sparse_items, record_type=None,
                split_args=None, split_kwargs=None):
    r"""Saves a virtual memory to a record file.

    Arguments:
        path (:obj:`str`): Path of the output file.
        sparse_items (:obj:`SparseItems`): A virtual memory.
        record_type (:class:`Record`): Explicit record type.
            If ``None``, it is guessed from the file extension.
        split_args (list): Positional arguments for :meth:`Record.split`.
        split_kwargs (dict): Keyword arguments for :meth:`Record.split`.

    Example:
        >>> blocks = [(offset, bytes(bytearray(range(offset, offset + 16))))
        ...           for offset in range(0, 256, 16)]
        >>> sparse_items = SparseItems(blocks=blocks)
        >>> save_memory('bytes.hex', sparse_items)
        >>> load_memory('bytes.hex') == sparse_items
        True
    """
    save_blocks(path, sparse_items.blocks, record_type,
                split_args, split_kwargs)


class Record(object):
    r"""Abstract record type.

    A record is the basic structure of a record file.

    This is an abstract class, so it provides basic generic methods shared by
    most of the :class:`Record` implementations.
    Please refer to the actual subclass for more details.

    Attributes:
        address (:obj:`int`): Tells where its `data` starts in the memory
            addressing space, or an address with a special meaning.
        tag (:obj:`int`): Defines the logical meaning of the `address` and
            `data` fields.
        data (:obj:`bytes`): Byte data as required by the `tag`.
        count (:obj:`int`): Counts its fields as required by the
            :class:`Record` subclass implementation.
        checksum (:obj:`int`): Computes the checksum as required by most
            :class:`Record` implementations.

    Arguments:
        address (:obj:`int`): Record `address` field.
        tag (:obj:`int`): Record `tag` field.
        data (:obj:`bytes`): Record `data` field.
        checksum (:obj:`int` or ``None`` or ``Ellipsis``): Record
            `checksum` field. ``Ellipsis`` makes the constructor compute
            its actual value automatically. ``None`` assigns ``None``.

    Examples:
        >>> BinaryRecord(0x1234, 0, b'Hello, World!')
        ... #doctest: +NORMALIZE_WHITESPACE
        BinaryRecord(address=0x00001234, tag=0, count=13,
                     data=b'Hello, World!', checksum=0x69)

        >>> MotorolaRecord(0x1234, MotorolaTag.DATA_16, b'Hello, World!')
        ... #doctest: +NORMALIZE_WHITESPACE
        MotorolaRecord(address=0x00001234, tag=<MotorolaTag.DATA_16: 1>,
                       count=16, data=b'Hello, World!', checksum=0x40)

        >>> IntelRecord(0x1234, IntelTag.DATA, b'Hello, World!')
        ... #doctest: +NORMALIZE_WHITESPACE
        IntelRecord(address=0x00001234, tag=<IntelTag.DATA: 0>, count=13,
                    data=b'Hello, World!', checksum=0x44)
    """
    def __init__(self, address, tag, data, checksum=Ellipsis):
        self.address = address
        self.tag = tag
        self.data = data
        self.checksum = None
        self.update_count()
        if checksum is Ellipsis:
            self.update_checksum()
        else:
            self.checksum = checksum

    def __repr__(self):
        fmt = ('{0}('
               'address=0x{1.address:08X}, '
               'tag={1.tag!r}, '
               'count={1.count:d}, '
               'data={1.data!r}, '
               'checksum=0x{2:02X}'
               ')')
        checksum = self._get_checksum() or 0
        return fmt.format(type(self).__name__, self, checksum)

    def __str__(self):
        r"""Converts to text string.

        Returns:
            :obj:`str`: A printable text representation of the record, usually
                the same found in the saved record file as per its
                :class:`Record` subclass requirements.

        Examples:
            >>> str(BinaryRecord(0x1234, 0, b'Hello, World!'))
            '48656C6C6F2C20576F726C6421'

            >>> str(MotorolaRecord(0x1234, MotorolaTag.DATA_16,
            ...                    b'Hello, World!'))
            'S110123448656C6C6F2C20576F726C642140'

            >>> str(IntelRecord(0x1234, IntelTag.DATA, b'Hello, World!'))
            ':0D12340048656C6C6F2C20576F726C642144'
        """
        return repr(self)

    def __eq__(self, other):
        r"""Equality comparison.

        Returns:
            :obj:`bool`: The `address`, `tag`, and `data` fields are equal.

        Examples:
            >>> record1 = BinaryRecord.build_data(0, b'Hello, World!')
            >>> record2 = BinaryRecord.build_data(0, b'Hello, World!')
            >>> record1 == record2
            True

            >>> record1 = BinaryRecord.build_data(0, b'Hello, World!')
            >>> record2 = BinaryRecord.build_data(1, b'Hello, World!')
            >>> record1 == record2
            False

            >>> record1 = BinaryRecord.build_data(0, b'Hello, World!')
            >>> record2 = BinaryRecord.build_data(0, b'hello, world!')
            >>> record1 == record2
            False

            >>> record1 = MotorolaRecord.build_header(b'Hello, World!')
            >>> record2 = MotorolaRecord.build_data(0, b'hello, world!')
            >>> record1 == record2
            False
        """
        return (self.address == other.address and
                self.tag == other.tag and
                self.data == other.data)

    def __hash__(self):
        r"""Computes the hash value.

        Returns:
            :obj:`int`: Hash of the :class:`Record` fields. Useful to make
                the record hashable although it is a mutable class.

        Warning:
            Be careful with hashable mutable objects!

        Examples:
            >>> hash(BinaryRecord(0x1234, 0, b'Hello, World!'))
            ... #doctest: +SKIP
            7668968047460943252

            >>> hash(MotorolaRecord(0x1234, MotorolaTag.DATA_16,
            ...                             b'Hello, World!'))
            ... #doctest: +SKIP
            7668968047460943265

            >>> hash(IntelRecord(0x1234, IntelTag.DATA,
            ...                          b'Hello, World!'))
            ... #doctest: +SKIP
            7668968047460943289
        """
        return (hash(int(self.address) or 0) ^
                hash(int(self.tag) or 0) ^
                hash(bytes(self.data) or b'') ^
                hash(int(self.count) or 0) ^
                hash(int(self.checksum) or 0))

    def __lt__(self, other):
        r"""Less-than comparison.

        Returns:
            :obj:`bool`: `address` less than `other`'s.

        Examples:
            >>> record1 = BinaryRecord(0x1234, 0, b'')
            >>> record2 = BinaryRecord(0x4321, 0, b'')
            >>> record1 < record2
            True

            >>> record1 = BinaryRecord(0x4321, 0, b'')
            >>> record2 = BinaryRecord(0x1234, 0, b'')
            >>> record1 < record2
            False
        """
        return self.address < other.address

    def is_data(self):
        r"""Tells if it is a data record.

        Returns:
            :obj:`bool`: The record contains plain binary data, i.e. it is
                not a *special* record.

        Note:
            This method must be overridden.

        Examples:
            >>> BinaryRecord(0, 0, b'Hello, World!').is_data()
            True

            >>> MotorolaRecord(0, MotorolaTag.DATA_16,
            ...                b'Hello, World!').is_data()
            True

            >>> MotorolaRecord(0, MotorolaTag.HEADER,
            ...                b'Hello, World!').is_data()
            False

            >>> IntelRecord(0, IntelTag.DATA, b'Hello, World!').is_data()
            True

            >>> IntelRecord(0, IntelTag.END_OF_FILE, b'').is_data()
            False
        """
        return self.TAG_TYPE.is_data(self.tag)

    def compute_count(self):
        r"""Computes the count.

        Returns:
            :obj:`bool`: Computed `count` field value based on the current
                record fields.

        Examples:
            >>> record = BinaryRecord(0, 0, b'Hello, World!')
            >>> str(record)
            '48656C6C6F2C20576F726C6421'
            >>> record.compute_count()
            13

            >>> record = MotorolaRecord(0, MotorolaTag.DATA_16,
            ...                         b'Hello, World!')
            >>> str(record)
            'S110000048656C6C6F2C20576F726C642186'
            >>> record.compute_count()
            16

            >>> record = IntelRecord(0, IntelTag.DATA, b'Hello, World!')
            >>> str(record)
            ':0D00000048656C6C6F2C20576F726C64218A'
            >>> record.compute_count()
            13
        """
        return len(self.data)

    def update_count(self):
        r"""Updates the `count` field via :meth:`compute_count`."""
        self.count = self.compute_count()

    def compute_checksum(self):
        r"""Computes the checksum.

        Returns:
            :obj:`int`: Computed `checksum` field value based on the current
                record fields.

        Examples:
            >>> record = BinaryRecord(0, 0, b'Hello, World!')
            >>> str(record)
            '48656C6C6F2C20576F726C6421'
            >>> hex(record.compute_checksum())
            '0x69'

            >>> record = MotorolaRecord(0, MotorolaTag.DATA_16,
            ...                         b'Hello, World!')
            >>> str(record)
            'S110000048656C6C6F2C20576F726C642186'
            >>> hex(record.compute_checksum())
            '0x86'

            >>> record = IntelRecord(0, IntelTag.DATA, b'Hello, World!')
            >>> str(record)
            ':0D00000048656C6C6F2C20576F726C64218A'
            >>> hex(record.compute_checksum())
            '0x8a'
        """
        return sum_bytes(self.data) & 0xFF

    def update_checksum(self):
        r"""Updates the `checksum` field via :meth:`compute_count`."""
        self.checksum = self.compute_checksum()

    def _get_checksum(self):
        r""":obj:`int`: The `checksum` field itself if not ``None``, the
            value computed by :meth:`compute_count` otherwise.
        """
        if self.checksum is None:
            return self.compute_checksum()
        else:
            return self.checksum

    def check(self):
        r"""Performs consistency checks.

        Raises:
            :obj:`ValueError`: a field is inconsistent.
        """
        if not 0 <= self.address:
            raise ValueError('address overflow')

        if not 0x00 <= self.tag <= 0xFF:
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

    def overlaps(self, other):
        r"""Checks if overlapping occurs.

        Returns:
            :obj:`bool`: This record and another have overlapping `data`,
                when both `address` fields are not ``None``.

        Examples:
            >>> record1 = BinaryRecord(0, 0, b'abc')
            >>> record2 = BinaryRecord(1, 0, b'def')
            >>> record1.overlaps(record2)
            True

            >>> record1 = BinaryRecord(0, 0, b'abc')
            >>> record2 = BinaryRecord(3, 0, b'def')
            >>> record1.overlaps(record2)
            False
        """
        if self.address is None or other.address is None:
            return False
        else:
            return do_overlap(self.address,
                              self.address + len(self.data),
                              other.address,
                              other.address + len(other.data))

    @classmethod
    def parse(cls, line, *args, **kwargs):
        r"""Parses a record from a text line.

        Arguments:
            line (:obj:`str`): Text line to parse.
            args (:obj:`tuple`): Further positional arguments for overriding.
            kwargs (:obj:`dict`): Further keyword arguments for overriding.

        Note:
            This method must be overridden.
        """
        raise NotImplementedError('method must be overriden')

    @classmethod
    def split(cls, data, *args, **kwargs):
        r"""Splits a chunk of data into records.

        Arguments:
            data (:obj:`bytes`): Byte data to split.
            args (:obj:`tuple`): Further positional arguments for overriding.
            kwargs (:obj:`dict`): Further keyword arguments for overriding.

        Note:
            This method must be overridden.
        """
        raise NotImplementedError('method must be overriden')

    @classmethod
    def build_standalone(cls, data_records, *args, **kwargs):
        r"""Makes a sequence of data records standalone.

        Arguments:
            data_records (:obj:`list` of :class:`Record`): A sequence of data
                records.
            args (:obj:`tuple`): Further positional arguments for overriding.
            kwargs (:obj:`dict`): Further keyword arguments for overriding.

        Yields:
            :obj:`Record`: Records for a standalone record file.
        """
        for record in data_records:
            yield record

    @classmethod
    def check_sequence(cls, records):
        r"""Consistency check of a sequence of records.

        Raises:
            ValueError: a field is inconsistent.
        """
        last = None
        record_endex = 0

        for record in records:
            record.check()

            if record.is_data():
                if last is not None and record.overlaps(last):
                    raise ValueError('overlapping records')

                if record.address < record_endex:
                    raise ValueError('unsorted records')

                last = record

            record_endex = record.address + len(record.data)

    @classmethod
    def readdress(cls, records):
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
            records (list): Sequence of records to be converted to *flat*
                addressing, in-place. Sequence generators supported.
        """
        pass

    @classmethod
    def load(cls, path):
        r"""Loads records from a file.

        Each line of the input text file is parsed via :meth:`parse`, and
        collected into the returned list.

        Arguments:
            path (:obj:`str`): Path of the record file to load.

        Returns:
            :obj:`list`: Sequence of parsed records.
        """
        with open(path, 'rt') as stream:
            records = [cls.parse(line) for line in stream]
        return records

    @classmethod
    def save(cls, path, records):
        r"""Saves records to a file.

        Each record of the `records` sequence is converted into text via
        :func:`str`, and stored into the output text file.

        Arguments:
            path (:obj:`str`): Path of the record file to save.
            records (list): Sequence of records to store. Sequence generators
                supported.
        """
        with open(path, 'wt') as stream:
            for record in records:
                stream.write(str(record))
                stream.write('\n')
            stream.flush()


@enum.unique
class BinaryTag(enum.IntEnum):
    """Binary record tag."""

    DATA = 0
    """Data record."""

    @classmethod
    def is_data(cls, value):
        r""":obj:`bool`: `value` is a data record tag."""
        return True


class BinaryRecord(Record):

    EXTENSIONS = ('.bin', '.dat', '.raw')

    def __init__(self, address, tag, data, checksum=Ellipsis):
        super(BinaryRecord, self).__init__(address, 0, data, checksum)

    def __str__(self):
        text = hexlify(self.data)
        return text

    def is_data(self):
        return True

    @classmethod
    def build_data(cls, address, data):
        r"""Builds a data record.

        Example:
            >>> BinaryRecord.build_data(0x1234, b'Hello, World!')
            ... #doctest: +NORMALIZE_WHITESPACE
            BinaryRecord(address=0x00001234, tag=0, count=13,
                         data=b'Hello, World!', checksum=0x69)
        """
        record = cls(address, 0, data)
        return record

    @classmethod
    def parse(cls, line):
        r"""Parses a binary record line.

        Warning:
            Since it parses raw hex data, it is not possible to set address
            to a value different than ``0``.

        Example:
            >>> line = '48656C6C 6F2C2057 6F726C64 21'
            >>> BinaryRecord.parse(line)
            ... #doctest: +NORMALIZE_WHITESPACE
            BinaryRecord(address=0x00000000, tag=0, count=13,
                         data=b'Hello, World!', checksum=0x69)
        """
        line = str(line).strip()
        data = unhexlify(line)
        record = cls.build_data(0, data)
        return record

    @classmethod
    def split(cls, data, address=0, columns=None, align=True,
              standalone=True):
        r"""Splits a chunk of data into records.

        Arguments:
            data (:obj:`bytes`): Byte data to split.
            address (:obj:`int`): Start address of the first data record being
                split.
            columns (:obj:`int`): Maximum number of columns per data record.
                If ``None``, the whole `data` is put into a single record.
            align (:obj:`int`): Byte Alignment of record start addresses.
            standalone (:obj:`bool`): Generates a sequence of records that can
                be saved as a standlone record file.

        Yields:
            :obj:`MotorolaRecord`: Data split into records.

        Raises:
            ValueError: Address or size overflow.
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')

        if columns is None:
            yield cls.build_data(address, data)
        else:
            align_base = (address % columns) if align else 0
            for chunk in chop(data, columns, align_base):
                yield cls.build_data(address, chunk)
                address += len(chunk)

    @classmethod
    def load(cls, path, *args, **kwargs):
        with open(path, 'rb') as stream:
            chunk = stream.read()
        records = cls.split(chunk, *args, **kwargs)
        return records

    @classmethod
    def save(cls, path, records, *args, **kwargs):
        with open(path, 'wb') as stream:
            for record in records:
                stream.write(record.data)
            stream.flush()


@enum.unique
class MotorolaTag(enum.IntEnum):
    """Motorola S-record tag."""

    HEADER = 0
    """Header string. Optional."""

    DATA_16 = 1
    """16-bit address data record."""

    DATA_24 = 2
    """24-bit address data record."""

    DATA_32 = 3
    """32-bit address data record."""

    _RESERVED = 4
    """Reserved tag."""

    COUNT_16 = 5
    """16-bit record count. Optional."""

    COUNT_24 = 6
    """24-bit record count. Optional."""

    START_32 = 7
    """32-bit start address. Terminates :attr:`DATA_32`."""

    START_24 = 8
    """24-bit start address. Terminates :attr:`DATA_24`."""

    START_16 = 9
    """16-bit start address. Terminates :attr:`DATA_16`."""

    @classmethod
    def is_data(cls, value):
        r""":obj:`bool`: `value` is a data record tag."""
        return value in (cls.DATA_16, cls.DATA_24, cls.DATA_32)


class MotorolaRecord(Record):
    r"""Motorola S-record.

    See:
        `<https://en.wikipedia.org/wiki/SREC_(file_format)>`_
    """

    TAG_TYPE = MotorolaTag
    """Associated Python class for tags."""

    TAG_TO_ADDRESS_LENGTH = (2, 2, 3, 4, None, None, None, 4, 3, 2)
    """Maps a tag to its address byte length, if available."""

    MATCHING_TAG = (None, None, None, None, None, None, None, 3, 2, 1)
    """Maps the terminator tag to its mathing data tag."""

    REGEX = re.compile(r'^S[0-9]([0-9A-Fa-f]{2}){4,140}$')
    """Regular expression for parsing a record text line."""

    EXTENSIONS = ('.mot', '.s19', '.s28', '.s37', '.srec', '.exo')
    """Automatically supported file extensions."""

    def __init__(self, address, tag, data, checksum=Ellipsis):
        super(MotorolaRecord, self).__init__(address, self.TAG_TYPE(tag),
                                             data, checksum)

    def __str__(self):
        self.check()
        tag_text = 'S{:d}'.format(self.tag)

        address_length = self.TAG_TO_ADDRESS_LENGTH[self.tag]
        if address_length is None:
            address_text = ''
            count_text = '{:02X}'.format(len(self.data) + 1)
        else:
            count_text = '{:02X}'.format(address_length + len(self.data) + 1)
            offset = 2 * (4 - address_length)
            address_text = '{:08X}'.format(self.address)[offset:]

        data_text = hexlify(self.data)

        checksum_text = '{:02X}'.format(self._get_checksum())

        text = ''.join((tag_text,
                        count_text,
                        address_text,
                        data_text,
                        checksum_text))
        return text

    def compute_count(self):
        tag = int(self.tag)
        address_length = self.TAG_TO_ADDRESS_LENGTH[tag] or 0
        return address_length + len(self.data) + 1

    def compute_checksum(self):
        checksum = sum_bytes(struct.pack('BL', self.count, self.address))
        checksum += sum_bytes(self.data)
        checksum = (checksum & 0xFF) ^ 0xFF
        return checksum

    def check(self):
        super(MotorolaRecord, self).check()

        tag = int(self.TAG_TYPE(self.tag))

        if tag in (0, 4, 5, 6) and self.address:
            raise ValueError('address error')

        if self.count != self.compute_count():
            raise ValueError('count error')

    @classmethod
    def fit_data_tag(cls, endex):
        r"""Fits a data tag by address.

        Depending on the value of `endex`, get the data tag with the smallest
        supported address.

        Arguments:
            endex (:obj:`int`): Exclusive end address of the data.

        Returns:
            :obj:`MotorolaTag`: Fitting data tag.

        Raises:
            ValueError: Address overflow.

        Examples:
            >>> MotorolaRecord.fit_data_tag(0x00000000)
            <MotorolaTag.DATA_16: 1>

            >>> MotorolaRecord.fit_data_tag(0x0000FFFF)
            <MotorolaTag.DATA_16: 1>

            >>> MotorolaRecord.fit_data_tag(0x00010000)
            <MotorolaTag.DATA_16: 1>

            >>> MotorolaRecord.fit_data_tag(0x00FFFFFF)
            <MotorolaTag.DATA_24: 2>

            >>> MotorolaRecord.fit_data_tag(0x01000000)
            <MotorolaTag.DATA_24: 2>

            >>> MotorolaRecord.fit_data_tag(0xFFFFFFFF)
            <MotorolaTag.DATA_32: 3>
        """

        if not 0 <= endex < (1 << 32):
            raise ValueError('address overflow')

        elif endex <= (1 << 16):
            return cls.TAG_TYPE.DATA_16

        elif endex <= (1 << 24):
            return cls.TAG_TYPE.DATA_24

        else:
            return cls.TAG_TYPE.DATA_32

    @classmethod
    def fit_count_tag(cls, record_count):
        r"""Fits the record count tag.

        Arguments:
            record_count (:obj:`int`): Record count.

        Returns:
            :obj:`MotorolaTag`: Fitting record count tag.

        Raises:
            ValueError: Count overflow.

        Examples:
            >>> MotorolaRecord.fit_count_tag(0x0000000)
            <MotorolaTag.COUNT_16: 5>

            >>> MotorolaRecord.fit_count_tag(0x00FFFF)
            <MotorolaTag.COUNT_16: 5>

            >>> MotorolaRecord.fit_count_tag(0x010000)
            <MotorolaTag.COUNT_24: 6>

            >>> MotorolaRecord.fit_count_tag(0xFFFFFF)
            <MotorolaTag.COUNT_24: 6>
        """

        if not 0 <= record_count < (1 << 24):
            raise ValueError('count overflow')

        elif record_count < (1 << 16):
            return cls.TAG_TYPE.COUNT_16

        elif record_count < (1 << 24):
            return cls.TAG_TYPE.COUNT_24

    @classmethod
    def build_header(cls, data):
        r"""Builds a header record.

        Arguments:
            data (:obj:`bytes`): Header string data.

        Returns:
            :obj:`MotorolaRecord`: Header record.

        Example:
            >>> str(MotorolaRecord.build_header(b'Hello, World!'))
            'S010000048656C6C6F2C20576F726C642186'
        """
        return cls(0, 0, data)

    @classmethod
    def build_data(cls, address, data, tag=None):
        r"""Builds a data record.

        Arguments:
            address (:obj:`int`): Record start address.
            data (:obj:`bytes`): Some program data.
            tag (:obj:`MotorolaTag`): Data tag record.
                If ``None``, automatically selects the fitting one.

        Returns:
            :obj:`MotorolaRecord`: Data record.

        Raises:
            ValueError: Tag error.

        Examples:
            >>> str(MotorolaRecord.build_data(0x1234, b'Hello, World!'))
            'S110123448656C6C6F2C20576F726C642140'

            >>> str(MotorolaRecord.build_data(0x1234, b'Hello, World!',
            ...                               tag=MotorolaTag.DATA_16))
            'S110123448656C6C6F2C20576F726C642140'

            >>> str(MotorolaRecord.build_data(0x123456, b'Hello, World!',
            ...                               tag=MotorolaTag.DATA_24))
            'S21112345648656C6C6F2C20576F726C6421E9'

            >>> str(MotorolaRecord.build_data(0x12345678, b'Hello, World!',
            ...                               tag=MotorolaTag.DATA_32))
            'S3121234567848656C6C6F2C20576F726C642170'
        """
        if tag is None:
            tag = cls.fit_data_tag(address + len(data))

        if tag not in (1, 2, 3):
            raise ValueError('tag error')

        record = cls(address, tag, data)
        return record

    @classmethod
    def build_terminator(cls, start, last_data_tag=MotorolaTag.DATA_16):
        r"""Builds a terminator record.

        Arguments:
            start (:obj:`int`): Program start address.
            last_data_tag (:obj:`MotorolaTag`): Last data record tag to match.

        Returns:
            :obj:`MotorolaRecord`: Terminator record.

        Examples:
            >>> str(MotorolaRecord.build_terminator(0x1234))
            'S9031234B6'

            >>> str(MotorolaRecord.build_terminator(0x1234,
            ...                                     MotorolaTag.DATA_16))
            'S9031234B6'

            >>> str(MotorolaRecord.build_terminator(0x123456,
            ...                                     MotorolaTag.DATA_24))
            'S8041234565F'

            >>> str(MotorolaRecord.build_terminator(0x12345678,
            ...                                     MotorolaTag.DATA_32))
            'S70512345678E6'
        """
        tag_index = cls.MATCHING_TAG.index(int(last_data_tag))
        terminator_record = cls(start, tag_index, b'')
        return terminator_record

    @classmethod
    def build_count(cls, record_count):
        r"""Builds a count record.

        Arguments:
            count (:obj:`int`): Record count.

        Returns:
            :obj:`MotorolaRecord`: Count record.

        Raises:
            ValueError: Count error.

        Examples:
             >>> str(MotorolaRecord.build_count(0x1234))
             'S5031234B6'

             >>> str(MotorolaRecord.build_count(0x123456))
             'S6041234565F'
        """
        tag = cls.fit_count_tag(record_count)
        count_data = struct.pack('>L', record_count)
        count_record = cls(0, tag, count_data[(7 - tag):])
        return count_record

    @classmethod
    def parse(cls, line):
        line = str(line).strip()
        match = cls.REGEX.match(line)
        if not match:
            raise ValueError('regex error')

        tag = int(line[1:2])
        count = int(line[2:4], 16)
        assert 2 * count == len(line) - (2 + 2)
        address_length = cls.TAG_TO_ADDRESS_LENGTH[tag] or 0
        address = int('0' + line[4:(4 + 2 * address_length)], 16)
        data = unhexlify(line[(4 + 2 * address_length):-2])
        checksum = int(line[-2:], 16)

        record = cls(address, tag, data, checksum)
        return record

    @classmethod
    def build_standalone(cls, data_records, start=None, tag=None,
                         header_data=None):
        r"""Makes a sequence of data records standalone.

        Arguments:
            data_records (:obj:`list` of :class:`Record`): A sequence of data
                records.
            start (:obj:`int`): Program start address.
                If ``None``, it is assigned the minimum data record address.
            tag (:obj:`MotorolaTag`): Data tag record.
                If ``None``, automatically selects the fitting one.
            header_data (:obj:`bytes`): Header string data.

        Yields:
            :obj:`Record`: Records for a standalone record file.
        """
        address = 0
        count = 0
        if tag is None:
            tag = max(record.tag for record in data_records)

        if header_data is not None:
            yield cls.build_header(header_data)
            count += 1

        for record in data_records:
            yield record
            count += 1
            address = max(address, record.address + len(record.data))
            tag = max(tag, record.tag)

        yield cls.build_count(count)

        if start is None:
            start = min(record.address for record in data_records)
        yield cls.build_terminator(start, tag)

    @classmethod
    def check_sequence(cls, records):
        Record.check_sequence(records)

        record = records[0]
        last = record
        if record.tag != 0:
            raise ValueError('missing header')

        record = records[1]
        tag = record.tag
        if tag not in (1, 2, 3):
            raise ValueError('tag error')

        for i in range(2, len(records)):
            record = records[i]
            if record.tag == tag:
                if record.overlaps(last):
                    raise ValueError('overlapping records')
                last = record
            else:
                if record.tag in (5, 6):
                    if record.tag == 5:
                        expected_count = struct.unpack('>H', record.data)[0]
                    elif record.tag == 6:
                        u, hl = struct.unpack('>BH', record.data)
                        expected_count = (u << 16) | hl

                    if expected_count != i:
                        raise ValueError('record count error')
                else:
                    break

        matching_tag = cls.MATCHING_TAG[record.tag]
        if tag != matching_tag:
            raise ValueError('matching tag error')

        if i != len(records) - 1:
            raise ValueError('record count error')

    @classmethod
    def split(cls, data, address=0, columns=16, align=True,
              standalone=True, start=None, tag=None, header_data=None):
        r"""Splits a chunk of data into records.

        Arguments:
            data (:obj:`bytes`): Byte data to split.
            address (:obj:`int`): Start address of the first data record being
                split.
            columns (:obj:`int`): Maximum number of columns per data record.
                If ``None``, the whole `data` is put into a single record.
                Maximum of 128 columns.
            align (:obj:`bool`): Aligns record addresses to the column length.
            standalone (:obj:`bool`): Generates a sequence of records that can
                be saved as a standlone record file.
            start (:obj:`int`): Program start address.
                If ``None``, it is assigned the minimum data record address.
            tag (:obj:`MotorolaTag`): Data tag record.
                If ``None``, automatically selects the fitting one.
            header_data (:obj:`bytes`): Header string data.

        Yields:
            :obj:`MotorolaRecord`: Data split into records.

        Raises:
            ValueError: Address, size, or column overflow.
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        if not 0 < columns < 128:
            raise ValueError('column overflow')

        if start is None:
            start = address
        if tag is None:
            tag = cls.fit_data_tag(address + len(data))
        count = 0

        if standalone and header_data is not None:
            yield cls.build_header(header_data)

        skip = (address % columns) if align else 0
        for chunk in chop(data, columns, skip):
            yield cls.build_data(address, chunk, tag)
            count += 1
            address += len(chunk)

        if standalone:
            yield cls.build_count(count)
            yield cls.build_terminator(start, tag)

    @classmethod
    def fix_tags(cls, records):
        r"""Fix record tags.

        Updates record tags to reflect modified size and count.
        All the checksums are updated too.
        Operates in-place.

        Arguments:
            records (:obj:`list` of :obj:`MotorolaRecord`): A sequence of
                records. Must be in-ine mutable.
        """
        max_address = max(record.address + len(record.data)
                          for record in records)
        tag = cls.TAG_TYPE(cls.fit_data_tag(max_address))
        COUNT_16 = cls.TAG_TYPE.COUNT_16
        start_tags = (cls.TAG_TYPE.START_16,
                      cls.TAG_TYPE.START_24,
                      cls.TAG_TYPE.START_32)
        start_ids = []

        for index, record in enumerate(records):
            if record.tag == COUNT_16:
                count = struct.unpack('>L', record.data.rjust(4, b'\0'))[0]
                if count >= (1 << 16):
                    record.tag = cls.TAG_TYPE.COUNT_24
                    record.data = struct.pack('>L', count)[1:]
                    record.update_count()
                    record.update_checksum()

            elif record.is_data():
                record.tag = tag
                record.update_checksum()

            elif record.tag in start_tags:
                start_ids.append(index)

        max_tag = int(max(record.tag for record in get_data_records(records)))
        start_tag = cls.TAG_TYPE(cls.MATCHING_TAG.index(max_tag))
        for index in start_ids:
            records[index].tag = start_tag


@enum.unique
class IntelTag(enum.IntEnum):
    """Intel HEX tag."""

    DATA = 0
    """Binary data."""

    END_OF_FILE = 1
    """End of file."""

    EXTENDED_SEGMENT_ADDRESS = 2
    """Extended segment address."""

    START_SEGMENT_ADDRESS = 3
    """Start segment address."""

    EXTENDED_LINEAR_ADDRESS = 4
    """Extended linear address."""

    START_LINEAR_ADDRESS = 5
    """Start linear address."""

    @classmethod
    def is_data(cls, value):
        r""":obj:`bool`: `value` is a data record tag."""
        return value == cls.DATA


class IntelRecord(Record):
    r"""Intel HEX record.

    See:
        `<https://en.wikipedia.org/wiki/Intel_HEX>`_
    """

    TAG_TYPE = IntelTag
    """Associated Python class for tags."""

    REGEX = re.compile(r'^:(?P<count>[0-9A-Fa-f]{2})'
                       r'(?P<offset>[0-9A-Fa-f]{4})'
                       r'(?P<tag>[0-9A-Fa-f]{2})'
                       r'(?P<data>([0-9A-Fa-f]{2}){,255})'
                       r'(?P<checksum>[0-9A-Fa-f]{2})$')
    """Regular expression for parsing a record text line."""

    EXTENSIONS = ('.hex', '.ihex', '.mcs')
    """Automatically supported file extensions."""

    def __init__(self, address, tag, data, checksum=Ellipsis):
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        super(IntelRecord, self).__init__(address, self.TAG_TYPE(tag),
                                          data, checksum)

    def __str__(self):
        self.check()
        offset = (self.address or 0) & 0xFFFF
        data = self.data or b''
        data_hex = hexlify(data)
        checksum = self._get_checksum()
        fmt = ':{:02X}{:04X}{:02X}{}{:02X}'
        text = fmt.format(len(data), offset, self.tag, data_hex, checksum)
        return text

    def compute_count(self):
        return len(self.data)

    def compute_checksum(self):
        offset = (self.address or 0) & 0xFFFF

        checksum = (self.count +
                    sum_bytes(struct.pack('H', offset)) +
                    self.tag +
                    sum_bytes(self.data))

        checksum = (0x100 - int(checksum & 0xFF)) & 0xFF
        return checksum

    def check(self):
        super(IntelRecord, self).check()

        if self.count != self.compute_count():
            raise ValueError('count error')

        self.TAG_TYPE(self.tag)
        # TODO: check values

    @classmethod
    def build_data(cls, address, data):
        r"""Builds a data record.

        Arguments:
            address (:obj:`int`): Record start address.
            data (:obj:`bytes`): Some program data.

        Returns:
            :obj:`IntelRecord`: Data record.

        Example:
            >>> str(IntelRecord.build_data(0x1234, b'Hello, World!'))
            ':0D12340048656C6C6F2C20576F726C642144'
        """
        record = cls(address, cls.TAG_TYPE.DATA, data)
        return record

    @classmethod
    def build_extended_segment_address(cls, address):
        r"""Builds an extended segment address record.

        Arguments:
            address (:obj:`int`): Extended segment address.
                The 20 least significant bits are ignored.

        Returns:
            :obj:`IntelRecord`: Extended segment address record.

        Example:
            >>> str(IntelRecord.build_extended_segment_address(0x12345678))
            ':020000020123D8'
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        segment = address >> (16 + 4)
        tag = cls.TAG_TYPE.EXTENDED_SEGMENT_ADDRESS
        record = cls(0, tag, struct.pack('>H', segment))
        return record

    @classmethod
    def build_start_segment_address(cls, address):
        r"""Builds an start segment address record.

        Arguments:
            address (:obj:`int`): Start segment address.

        Returns:
            :obj:`IntelRecord`: Start segment address record.

        Raises:
            ValueError: Address overflow.

        Example:
            >>> str(IntelRecord.build_start_segment_address(0x12345678))
            ':0400000312345678E5'
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')

        tag = cls.TAG_TYPE.START_SEGMENT_ADDRESS
        record = cls(0, tag, struct.pack('>L', address))
        return record

    @classmethod
    def build_end_of_file(cls):
        r"""Builds an end-of-file record.

        Returns:
            :obj:`IntelRecord`: End-of-file record.

        Example:
            >>> str(IntelRecord.build_end_of_file())
            ':00000001FF'
        """
        tag = cls.TAG_TYPE.END_OF_FILE
        return cls(0, tag, b'')

    @classmethod
    def build_extended_linear_address(cls, address):
        r"""Builds an extended linear address record.

        Arguments:
            address (:obj:`int`): Extended linear address.
            The 16 least significant bits are ignored.

        Returns:
            :obj:`IntelRecord`: Extended linear address record.

        Raises:
            ValueError: Address overflow.

        Example:
            >>> str(IntelRecord.build_extended_linear_address(0x12345678))
            ':020000041234B4'
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')

        segment = address >> 16
        tag = cls.TAG_TYPE.EXTENDED_LINEAR_ADDRESS
        record = cls(0, tag, struct.pack('>H', segment))
        return record

    @classmethod
    def build_start_linear_address(cls, address):
        r"""Builds an start linear address record.

        Arguments:
            address (:obj:`int`): Start linear address.

        Returns:
            :obj:`IntelRecord`: Start linear address record.

        Raises:
            ValueError: Address overflow.

        Example:
            >>> str(IntelRecord.build_start_linear_address(0x12345678))
            ':0400000512345678E3'
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')

        tag = cls.TAG_TYPE.START_LINEAR_ADDRESS
        record = cls(0, tag, struct.pack('>L', address))
        return record

    @classmethod
    def parse(cls, line):
        line = str(line).strip()
        match = cls.REGEX.match(line)
        if not match:
            raise ValueError('regex error')
        groups = match.groupdict()

        offset = int(groups['offset'], 16)
        tag = cls.TAG_TYPE(int(groups['tag'], 16))
        count = int(groups['count'], 16)
        data = unhexlify(groups['data'] or '')
        checksum = int(groups['checksum'], 16)

        if count != len(data):
            raise ValueError('count error')
        record = cls(offset, tag, data, checksum)
        return record

    @classmethod
    def split(cls, data, address=0, columns=16, align=True,
              standalone=True, start=None):
        r"""Splits a chunk of data into records.

        Arguments:
            data (:obj:`bytes`): Byte data to split.
            address (:obj:`int`): Start address of the first data record being
                split.
            columns (:obj:`int`): Maximum number of columns per data record.
                If ``None``, the whole `data` is put into a single record.
                Maximum of 255 columns.
            align (:obj:`bool`): Aligns record addresses to the column length.
            standalone (:obj:`bool`): Generates a sequence of records that can
                be saved as a standlone record file.
            start (:obj:`int`): Program start address.
                If ``None``, it is assigned the minimum data record address.

        Yields:
            :obj:`IntelRecord`: Data split into records.

        Raises:
            ValueError: Address, size, or column overflow.
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        if not 0 < columns < 255:
            raise ValueError('column overflow')

        if start is None:
            start = address
        align_base = (address % columns) if align else 0
        address_old = 0

        for chunk in chop(data, columns, align_base):
            length = len(chunk)
            endex = address + length
            overflow = endex & 0xFFFF

            if overflow and (address ^ endex) & 0xFFFF0000:
                pivot = length - overflow

                yield cls.build_data(address, chunk[:pivot])
                address += pivot

                yield cls.build_extended_linear_address(address)

                yield cls.build_data(address, chunk[pivot:])
                address_old = address
                address += overflow

            else:
                if (address ^ address_old) & 0xFFFF0000:
                    yield cls.build_extended_linear_address(address)

                yield cls.build_data(address, chunk)
                address_old = address
                address += length

        if standalone:
            for record in cls.terminate(start):
                yield record

    @classmethod
    def build_standalone(cls, data_records, start=None):
        r"""Makes a sequence of data records standalone.

        Arguments:
            data_records (:obj:`list` of :class:`Record`): A sequence of data
                records.
            start (:obj:`int`): Program start address.
                If ``None``, it is assigned the minimum data record address.

        Yields:
            :obj:`Record`: Records for a standalone record file.
        """
        for record in data_records:
            yield record

        if start is None:
            start = min(record.address for record in data_records)
        for record in cls.terminate(start):
                yield record

    @classmethod
    def terminate(cls, start):
        r"""Builds a record termination sequence.

        The termination sequence is made of:

            # An extended linear address record at zero.
            # A start linear address record at `start`.
            # An end-of-file record.

        Arguments:
            start (:obj:`int`): Program start address.

        Returns:
            :obj:`list` of :obj:`IntelRecord`: Termination sequence.

        Example:
            >>> list(map(str, IntelRecord.terminate(0x12345678)))
            [':020000040000FA', ':0400000512345678E3', ':00000001FF']
        """
        return [cls.build_extended_linear_address(0),
                cls.build_start_linear_address(start),
                cls.build_end_of_file()]

    @classmethod
    def readdress(cls, records):
        r"""Converts to flat addressing.

        *Intel HEX*, stores records by *segment/offset* addressing.
        As this library adopts *flat* addressing instead, all the record
        addresses should be converted to *flat* addressing after loading.
        This procedure readdresses a sequence of records in-place.

        Warning:
            Only the `address` field is modified. All the other fields hold
            their previous value.

        Arguments:
            records (list): Sequence of records to be converted to *flat*
                addressing, in-place. Sequence generators supported.

        Example:
            >>> records = [
            ...     IntelRecord.build_extended_linear_address(0x76540000),
            ...     IntelRecord.build_data(0x00003210, b'Hello, World!'),
            ... ]
            >>> records  #doctest: +NORMALIZE_WHITESPACE
            [IntelRecord(address=0x00000000,
                         tag=<IntelTag.EXTENDED_LINEAR_ADDRESS: 4>, count=2,
                         data=b'vT', checksum=0x30),
             IntelRecord(address=0x00003210, tag=<IntelTag.DATA: 0>, count=13,
                         data=b'Hello, World!', checksum=0x48)]
            >>> IntelRecord.readdress(records)
            >>> records  #doctest: +NORMALIZE_WHITESPACE
            [IntelRecord(address=0x76540000,
                         tag=<IntelTag.EXTENDED_LINEAR_ADDRESS: 4>, count=2,
                         data=b'vT', checksum=0x30),
             IntelRecord(address=0x76543210, tag=<IntelTag.DATA: 0>, count=13,
                         data=b'Hello, World!', checksum=0x48)]
        """
        ESA = cls.TAG_TYPE.EXTENDED_SEGMENT_ADDRESS
        ELA = cls.TAG_TYPE.EXTENDED_LINEAR_ADDRESS
        base = 0

        for record in records:
            tag = record.tag
            if tag == ESA:
                base = struct.unpack('>H', record.data)[0] << 4
                address = base
            elif tag == ELA:
                base = struct.unpack('>H', record.data)[0] << 16
                address = base
            else:
                address = base + record.address

            record.address = address


@enum.unique
class TektronixTag(enum.IntEnum):
    DATA = 6
    TERMINATOR = 8

    @classmethod
    def is_data(cls, value):
        r""":obj:`bool`: `value` is a data record tag."""
        return value == cls.DATA


class TektronixRecord(Record):
    r"""Tektronix extended HEX record.

    See:
        `<https://en.wikipedia.org/wiki/Tektronix_extended_HEX>`_

    """

    TAG_TYPE = TektronixTag
    """Associated Python class for tags."""

    REGEX = re.compile(r'^%(?P<count>[0-9A-Fa-f]{2})'
                       r'(?P<tag>[68])'
                       r'(?P<checksum>[0-9A-Fa-f]{2})'
                       r'8(?P<address>[0-9A-Fa-f]{8})'
                       r'(?P<data>([0-9A-Fa-f]{2}){,255})$')
    """Regular expression for parsing a record text line."""

    EXTENSIONS = ('.tek',)
    """Automatically supported file extensions."""

    def __init__(self, address, tag, data, checksum=Ellipsis):
        super(TektronixRecord, self).__init__(address, self.TAG_TYPE(tag),
                                              data, checksum)

    def __str__(self):
        self.check()
        checksum = self._get_checksum()
        fmt = '%{0.count:02X}{0.tag:01X}{1:02X}8{0.address:08X}'
        text = fmt.format(self, checksum)
        text += hexlify(self.data)
        return text

    def compute_count(self):
        count = 9 + (len(self.data) * 2)
        return count

    def compute_checksum(self):
        fmt = '{0.count:02X}{0.tag:01X}8{0.address:08X}'
        text = fmt.format(self)
        text += hexlify(self.data)
        checksum = sum_bytes(int(c, 16) for c in text) & 0xFF
        return checksum

    def check(self):
        super(TektronixRecord, self).check()
        tag = self.TAG_TYPE(self.tag)

        if tag == self.TAG_TYPE.TERMINATOR and self.data:
            raise ValueError('invalid data')

        if self.count != self.compute_count():
            raise ValueError('count error')

    @classmethod
    def parse(cls, line):
        line = str(line).strip()
        match = cls.REGEX.match(line)
        if not match:
            raise ValueError('regex error')
        groups = match.groupdict()

        address = int(groups['address'], 16)
        tag = cls.TAG_TYPE(int(groups['tag'], 16))
        count = int(groups['count'], 16)
        data = unhexlify(groups['data'] or '')
        checksum = int(groups['checksum'], 16)

        assert count == 9 + (len(data) * 2)
        record = cls(address, tag, data, checksum)
        return record

    @classmethod
    def build_data(cls, address, data):
        r"""Builds a data record.

        Arguments:
            address (:obj:`int`): Record start address.
            data (:obj:`bytes`): Some program data.

        Returns:
            :obj:`TektronixRecord`: Data record.

        Example:
            >>> str(TektronixRecord.build_data(0x12345678, b'Hello, World!'))
            '%236E081234567848656C6C6F2C20576F726C6421'
        """
        record = cls(address, cls.TAG_TYPE.DATA, data)
        return record

    @classmethod
    def build_terminator(cls, start):
        r"""Builds a terminator record.

        Arguments:
            start (:obj:`int`): Program start address.

        Returns:
            :obj:`TektronixRecord`: Terminator record.

        Example:
            >>> str(TektronixRecord.build_terminator(0x12345678))
            '%0983D812345678'
        """
        record = cls(start, cls.TAG_TYPE.TERMINATOR, b'')
        return record

    @classmethod
    def split(cls, data, address=0, columns=16, align=True,
              standalone=True, start=None):
        r"""Splits a chunk of data into records.

        Arguments:
            data (:obj:`bytes`): Byte data to split.
            address (:obj:`int`): Start address of the first data record being
                split.
            columns (:obj:`int`): Maximum number of columns per data record.
                If ``None``, the whole `data` is put into a single record.
                Maximum of 128 columns.
            align (:obj:`bool`): Aligns record addresses to the column length.
            standalone (:obj:`bool`): Generates a sequence of records that can
                be saved as a standlone record file.
            start (:obj:`int`): Program start address.
                If ``None``, it is assigned the minimum data record address.

        Yields:
            :obj:`TektronixRecord`: Data split into records.

        Raises:
            ValueError: Address, size, or column overflow.
        """
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        if not 0 < columns < 128:
            raise ValueError('column overflow')

        align_base = (address % columns) if align else 0
        offset = address
        for chunk in chop(data, columns, align_base):
            yield cls.build_data(offset, chunk)
            offset += len(chunk)

        if standalone:
            yield cls.build_terminator(address if start is None else start)

    @classmethod
    def build_standalone(cls, data_records, start=None):
        r"""Makes a sequence of data records standalone.

        Arguments:
            data_records (:obj:`list` of :class:`Record`): A sequence of data
                records.
            start (:obj:`int`): Program start address.
                If ``None``, it is assigned the minimum data record address.

        Yields:
            :obj:`Record`: Records for a standalone record file.
        """
        for record in data_records:
            yield record

        if start is None:
            start = min(record.address for record in data_records)
        yield cls.build_terminator(start)

    @classmethod
    def check_sequence(cls, records):
        Record.check_sequence(records)

        if len(records) < 1:
            raise ValueError('missing terminator')

        for i in range(len(records) - 1):
            record = records[i]
            record.check()
            if record.tag != cls.TAG_TYPE.DATA:
                raise ValueError('tag error')

        record = records[-1]
        record.check()
        if record.tag != cls.TAG_TYPE.TERMINATOR:
            raise ValueError('missing terminator')
        if record.data:
            raise ValueError('data error')


RECORD_TYPES = {
    'motorola': MotorolaRecord,
    'intel': IntelRecord,
    'tektronix': TektronixRecord,
    'binary': BinaryRecord,
}


def find_record_type(file_path):
    r"""Finds the record type.

    Check if the extension of `file_path` is in a record type mapped by
    ``RECORD_TYPES``, and returns its mapped name.

    Arguments:
        file_path (:obj:`str`): File path to get the file extension from.

    Returns:
        :obj:`str`: Key of ``RECORD_TYPES``.

    Raises:
        KeyError: Unsupported extension.
    """
    ext = os.path.splitext(file_path)[1].lower()
    for name, record_type in six.iteritems(RECORD_TYPES):
        if ext in record_type.EXTENSIONS:
            return name
    else:
        raise KeyError('unsupported extension: ' + ext)
