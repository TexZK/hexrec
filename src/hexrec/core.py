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

from hexrec.utils import chop
from hexrec.utils import do_overlap
from hexrec.utils import hexlify
from hexrec.utils import merge_blocks
from hexrec.utils import unhexlify


def merge_records(data_records, input_types=None, output_type=None,
                  split_args=None, split_kwargs=None):
    """Merges data records.

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
        list: A sequence of merged records.
    """
    if input_types is None:
        input_types = [type(records[0]) if records else Record
                       for records in data_records]
    else:
        input_types = list(input_types)

    if output_type is None:
        output_type = input_types[0]

    input_blocks = []
    zipped = zip(range(len(input_types)), data_records, input_types)
    for level, records, input_type in zipped:
        input_blocks.extend((p[0].address, -level, input_type.flatten(p))
                            for p in input_type.partition(records))

    input_blocks.sort()
    merged_blocks = merge_blocks((start, chunk)
                                 for (start, _, chunk) in input_blocks)

    args = split_args or ()
    kwargs = split_kwargs or {}
    output_records = []
    for (start, chunk) in merged_blocks:
        records = output_type.split(chunk, *args, start=start, **kwargs)
        output_records.extend(records)

    return output_records


def convert_records(records, input_type=None, output_type=None,
                    split_args=None, split_kwargs=None):
    """Converts records to another type.

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
        list: A sequence of merged records.

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

    records = [record for record in records if record.is_data()]
    records.sort()

    output_records = merge_records([records], [input_type], output_type,
                                   split_args, split_kwargs)
    return output_records


def merge_files(input_files, output_file, input_types=None, output_type=None,
                split_args=None, split_kwargs=None):
    """Merges record files.

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
        >>> merge_files(['original.hex', 'patch.mot'], 'patched.tek')
        ... # doctest +SKIP

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
        records = [record for record in records if record.is_data()]
        records.sort()
        input_records.append(records)

    output_records = merge_records(input_records, input_types, output_type,
                                   split_args, split_kwargs)
    output_type.save(output_file, output_records)


def convert_file(input_file, output_file, input_type=None, output_type=None,
                 split_args=None, split_kwargs=None):
    """Converts a record file to another record type.

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
        >>> save_file('bytes.mot', motorola)
        >>> convert_file('bytes.mot', 'bytes.hex')
        >>> load_file('bytes.hex') == intel
        True
    """
    merge_files([input_file], output_file, [input_type], output_type,
                split_args, split_kwargs)


def load_file(path, record_type=None):
    """Loads records from a file.

    Arguments:
        path (:obj:`str`): Path of the input file.
        record_type (:class:`Record`): Explicit record type.
            If ``None``, it is guessed from the file extension.

    Example:
        >>> records = list(MotorolaRecord.split(bytes(range(256))))
        >>> save_file('bytes.mot', records)
        >>> load_file('bytes.mot') == records
        True
    """
    if record_type is None:
        type_name = find_record_type(path)
        record_type = RECORD_TYPES[type_name]
    records = record_type.load(path)
    return records


def save_file(path, records, record_type=None,
              split_args=None, split_kwargs=None):
    """Saves records to a file.

    Arguments:
        path (:obj:`str`): Path of the output file.
        records (list): Sequence of records to save.
        record_type (:class:`Record`): Explicit record type.
            If ``None``, it is guessed from the file extension.
        split_args (list): Positional arguments for :meth:`Record.split`.
        split_kwargs (dict): Keyword arguments for :meth:`Record.split`.

    Example:
        >>> records = list(MotorolaRecord.split(bytes(range(256))))
        >>> save_file('bytes.mot', records)
        >>> load_file('bytes.mot') == records
        True
    """
    if record_type is None:
        type_name = find_record_type(path)
        record_type = RECORD_TYPES[type_name]

    if records:
        if not all(isinstance(record, record_type) for record in records):
            records = convert_records(records, output_type=record_type,
                                      split_args=split_args,
                                      split_kwargs=split_kwargs)
    else:
        records = ()

    record_type.save(path, records)


SIZE_GUARD = 64 << 20  # 64 MiB
"""Default :meth:`Record.flatten` size limit"""


def _size_guard(start, endex):
    fill_length = endex - start
    if not 0 <= fill_length <= SIZE_GUARD:
        fmt = 'Trying to fill {} bytes, which is likely too much'
        raise ResourceWarning(fmt.format(fill_length))


class Record(object):
    """Abstract record type.

    A record is the basic structure of a record file.

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

    This is an abstract class, so it provides basic generic methods shared by
    most of the :class:`Record` implementations.
    Please refer to the actual subclass for more details.
    """

    def __init__(self, address, tag, data, checksum=Ellipsis):
        """Constructor.

        Arguments:
            address (:obj:`int`): Record `address` field.
            tag (:obj:`int`): Record `tag` field.
            data (:obj:`bytes`): Record `data` field.
            checksum (:obj:`int` or ``None`` or ``Ellipsis``): Record
                `checksum` field. ``Ellipsis`` makes the constructor compute
                its actual value automatically. ``None`` assigns ``None``.

        Examples:
            >>> BinaryRecord(0x1234, 0, b'Hello, World!')
            ... # doctest: +NORMALIZE_WHITESPACE
            BinaryRecord(address=0x00001234, tag=0, count=13,
                         data=b'Hello, World!', checksum=0x69)

            >>> MotorolaRecord(0x1234, MotorolaTag.DATA_16, b'Hello, World!')
            ... # doctest: +NORMALIZE_WHITESPACE
            MotorolaRecord(address=0x00001234, tag=<MotorolaTag.DATA_16: 1>,
                           count=16, data=b'Hello, World!', checksum=0x40)

            >>> IntelRecord(0x1234, IntelTag.DATA, b'Hello, World!')
            ... # doctest: +NORMALIZE_WHITESPACE
            IntelRecord(address=0x00001234, tag=<IntelTag.DATA: 0>, count=13,
                        data=b'Hello, World!', checksum=0x44)
        """
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
        """Converts to text string.

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
        """Equality comparison.

        Returns:
            :obj:`bool`: The `address`, `tag`, and `data` fields are equal.
        """
        return (self.address == other.address and
                self.tag == other.tag and
                self.data == other.data)

    def __hash__(self):
        """Computes the hash value.

        Returns:
            :obj:`int`: Hash of the :class:`Record` fields. Useful to make
                the record hashable although it is a mutable class.

        Warning:
            Be careful with hashable mutable objects!

        Examples:
            >>> hash(BinaryRecord(0x1234, 0, b'Hello, World!'))
            ... # doctest: +SKIP
            -1396369420761005263

            >>> hash(MotorolaRecord(0x1234, MotorolaTag.DATA_16,
            ...                     b'Hello, World!'))
            ... # doctest: +SKIP
            -1396369420761005308

            >>> hash(IntelRecord(0x1234, IntelTag.DATA, b'Hello, World!'))
            ... # doctest: +SKIP
            -1396369420761005284
        """
        return (hash(self.address or 0) ^
                hash(self.tag or 0) ^
                hash(self.data or b'') ^
                hash(self.count or 0) ^
                hash(self.checksum or 0))

    def __lt__(self, other):
        """Less-than comparison.

        Returns:
            :obj:`bool`: `address` less than `other`'s.

        Examples:
            >>> BinaryRecord(0x1234, 0, b'') < BinaryRecord(0x4321, 0, b'')
            True

            >>> BinaryRecord(0x4321, 0, b'') < BinaryRecord(0x1234, 0, b'')
            False
        """
        return self.address < other.address

    def __copy__(self):
        cls = type(self)
        copied = cls(self.address, self.tag, self.data, self.checksum)
        copied.__dict__.update(self.__dict__)
        return copied

    def is_data(self):
        """Tells if it is a data record.

        Returns:
            :obj:`bool`: The record contains plain binary data, *i.e.* it is
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
        raise NotImplementedError()

    def compute_count(self):
        """Computes the count.

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
        """Updates the `count` field via :meth:`compute_count`."""
        self.count = self.compute_count()

    def compute_checksum(self):
        """Computes the checksum.

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
        return sum(self.data) & 0xFF

    def update_checksum(self):
        """Updates the `checksum` field via :meth:`compute_count`."""
        self.checksum = self.compute_checksum()

    def _get_checksum(self):
        """:obj:`int`: The `checksum` field itself if not ``None``, the
            value computed by :meth:`compute_count` otherwise.
        """
        if self.checksum is None:
            return self.compute_checksum()
        else:
            return self.checksum

    def check(self):
        """Performs consistency checks.

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
        """Checks if overlapping occurs.

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
        """Parses a record from a text line.

        Arguments:
            line (:obj:`str`): Text line to parse.
            args (:obj:`tuple`): Further positional arguments for overriding.
            kwargs (:obj:`dict`): Further keyword arguments for overriding.

        Note:
            This method must be overridden.
        """
        raise NotImplementedError()

    @classmethod
    def split(cls, data, *args, **kwargs):
        """Splits a chunk of data into records.

        Arguments:
            data (:obj:`bytes`): Byte data to split.
            args (:obj:`tuple`): Further positional arguments for overriding.
            kwargs (:obj:`dict`): Further keyword arguments for overriding.

        Note:
            This method must be overridden.
        """
        raise NotImplementedError()

    @classmethod
    def check_sequence(cls, records):
        """Consistency check of a sequence of records.

        Raises:
            :obj:`ValueError`: a field is inconsistent.
        """
        last = None
        record_endex = 0

        for record in records:
            record.check()

            if record.is_data():
                if record.address < record_endex:
                    raise ValueError('unsorted records')
                if last is not None and record.overlaps(last):
                    raise ValueError('overlapping records')
                last = record

            record_endex = record.address + len(record.data)

    @classmethod
    def readdress(cls, records):
        """Converts to flat addressing.

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
    def flatten(cls, data_records, start=None, endex=None, align=1,
                fill=b'xFF', size_guard=Ellipsis):
        """Flattens records to a single chunk.

        Note:
            In case of overlapping data records, it is best to sort them by
            address before calling this function, in order to have predictable
            overwriting of the overlapping regions.

        Arguments:
            data_records (list): Sequence of data records to flatten.
                Sequence generators supported if both `start` and `endex`
                are not ``None``.
            start (:obj:`int`): Inclusive start address of the memory window
                to flatten. If ``None``, it is the minimum record `address`.
            endex (:obj:`int`): Exclusive end address of the memory window to
                flatten. If ``None``, it is the maximum record exclusive end
                address (`address` plus `data` length).
            align (:obj:`int`): Address alignment of the flattened bytes.
                The flattened range (i.e. `start`:`endex`) is expanded so that
                the resulting boundaries are aligned to it.
            fill (:obj:`bytes`): The flattened chunk is filled with this value
                before writing record data on it.
            size_guard (callable): An optional function to prevent the
                creation of a huge flattened chunk. ``None`` ignores such
                check; ``Ellipsis`` applied the default guard (limited to
                ``SIZE_GUARD``).

        Returns:
            :obj:`bytearray`: The flattened data records.
        """
        if not data_records:
            return b''

        if start is None:
            start = min(record.address for record in data_records)
        if endex is None:
            endex = max(record.address + len(record.data)
                        for record in data_records)
        if start > endex:
            raise ValueError('address overflow')
        start -= start % align
        endex += -endex % align

        if size_guard is Ellipsis:
            size_guard = _size_guard
        if size_guard is not None:
            size_guard(start, endex)

        data = bytearray().ljust(endex - start, fill)

        for record in data_records:
            address = record.address
            offset = address + len(record.data)

            if address < endex and offset > start:
                if address >= start and offset <= endex:
                    data[(address - start):(offset - start)] = record.data
                else:
                    os = max(address, start)
                    oex = min(offset, endex)
                    chunk = record.data[(os - address):(oex - address)]
                    data[(os - start):(oex - start)] = chunk

        return data

    @classmethod
    def partition(cls, sorted_data_records, invalid_start=-1):
        """Groups contiguous data records.

        Arguments:
            sorted_data_records (list): Sequence of sorted data records.
                Sequence generators supported.
            invalid_start (:obj:`int`): An address lesser than any other
                record address in `sorted_data_records`.

        Yields:
            :obj:`list`: Sequence of contiguous data records.
        """
        partition = None
        last = BinaryRecord(-1, None, b'', checksum=None)

        for record in sorted_data_records:
            if record.address > last.address + len(last.data):
                if partition:
                    yield partition
                partition = [record]
            else:
                partition.append(record)
            last = record
        if partition:
            yield partition

    @classmethod
    def load(cls, path):
        """Loads records from a file.

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
        """Saves records to a file.

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


class BinaryRecord(Record):

    EXTENSIONS = ('.bin', '.dat', '.raw')

    def __init__(self, address, tag, data, checksum=Ellipsis):
        super().__init__(address, 0, data, checksum)

    def __str__(self):
        text = hexlify(self.data)
        return text

    def is_data(self):
        return True

    @classmethod
    def build_data(cls, address, data):
        record = cls(address, 0, data)
        return record

    @classmethod
    def parse(cls, line):
        line = str(line).strip()
        data = unhexlify(line)
        record = cls.build_data(0, data)
        return record

    @classmethod
    def split(cls, data, address=0, columns=None, align=True):
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')

        if columns is None:
            yield cls.build_data(address, data)
        else:
            align_base = address if align else None
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
        chunk = cls.flatten(records, *args, **kwargs)
        with open(path, 'wb') as stream:
            stream.write(chunk)
            stream.flush()


@enum.unique
class MotorolaTag(enum.IntEnum):
    HEADER = 0  # Header
    DATA_16 = 1  # 16-bit address data record
    DATA_24 = 2  # 24-bit address data record
    DATA_32 = 3  # 32-bit address data record
    _RESERVED = 4  # (reserved)
    COUNT_16 = 5  # 16-bit records count (optional)
    COUNT_24 = 6  # 24-bit records count (optional)
    START_32 = 7  # 32-bit start address (terminates DATA_32)
    START_24 = 8  # 24-bit start address (terminates DATA_24)
    START_16 = 9  # 16-bit start address (terminates DATA_16)

    @classmethod
    def is_data(cls, value):
        return value in (cls.DATA_16, cls.DATA_24, cls.DATA_32)


class MotorolaRecord(Record):

    TAG_TYPE = MotorolaTag
    TAG_TO_ADDRESS_LENGTH = (2, 2, 3, 4, None, None, None, 4, 3, 2)
    MATCHING_TAG = (None, None, None, None, None, None, None, 3, 2, 1)

    REGEX = re.compile(r'^S[0-9]([0-9A-Fa-f]{2}){4,140}$')

    EXTENSIONS = ('.mot', '.s19', '.s28', '.s37', '.srec', '.exo')

    def __init__(self, address, tag, data, checksum=Ellipsis):
        super().__init__(address, self.TAG_TYPE(tag), data, checksum)

    def __str__(self):
        self.check()
        tag_text = 'S{:d}'.format(self.tag)

        address_length = self.TAG_TO_ADDRESS_LENGTH[self.tag]
        if address_length is None:
            address_text = ''
            count_text = '{:02X}'.format(len(self.data) + 1)
        else:
            count_text = '{:02X}'.format(address_length + len(self.data) + 1)
            address_text = hexlify(self.address.to_bytes(address_length, 'big'))

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
        checksum = sum(struct.pack('BL', self.count, self.address))
        checksum += sum(self.data)
        checksum = (checksum & 0xFF) ^ 0xFF
        return checksum

    def check(self):
        super().check()

        tag = int(self.TAG_TYPE(self.tag))
        if not 0 <= tag <= 9:
            raise RuntimeError('tag error')

        if tag in (0, 4, 5, 6) and self.address:
            raise RuntimeError('address error')

        if self.count != self.compute_count():
            raise RuntimeError('count error')

    def is_data(self):
        return int(self.tag) in (1, 2, 3)

    @classmethod
    def fit_data_tag(cls, address, data, start=None):
        if start is None:
            start = address
        endex = address + len(data)
        if endex < (1 << 16):
            tag = 1
        elif endex < (1 << 24):
            tag = 2
        else:
            tag = 3
        return tag

    @classmethod
    def build_header(cls, data):
        return cls(0, 0, data)

    @classmethod
    def build_data(cls, address, data, tag=None):
        if tag is None:
            tag = cls.fit_data_tag(address, data)

        if tag not in (1, 2, 3):
            raise ValueError('tag error')

        record = cls(address, tag, data)
        return record

    @classmethod
    def build_terminator(cls, start, last_tag=1):
        tag_index = cls.MATCHING_TAG.index(int(last_tag))
        terminator_record = cls(start, tag_index, b'')
        return terminator_record

    @classmethod
    def build_count(cls, address, count):
        count_record = cls(0, 5, struct.pack('>H', count))
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

        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        if columns > 128:
            raise ValueError('too many columns')

        if start is None:
            start = address
        if tag is None:
            tag = cls.fit_data_tag((address + len(data)), data, start)
        count = 0

        if standalone and header_data is not None:
            yield cls.build_header(header_data)

        skip = address if align else None
        for chunk in chop(data, columns, skip):
            yield cls.build_data(address, chunk, tag)
            count += 1
            address += len(chunk)

        if standalone:
            yield cls.build_count(address, count)
            yield cls.build_terminator(start, tag)


@enum.unique
class IntelTag(enum.IntEnum):
    DATA = 0
    END_OF_FILE = 1
    EXTENDED_SEGMENT_ADDRESS = 2
    START_SEGMENT_ADDRESS = 3
    EXTENDED_LINEAR_ADDRESS = 4
    START_LINEAR_ADDRESS = 5

    @classmethod
    def is_data(cls, value):
        return value == cls.DATA


class IntelRecord(Record):

    TAG_TYPE = IntelTag

    REGEX = re.compile(r'^:(?P<count>[0-9A-Fa-f]{2})'
                       r'(?P<offset>[0-9A-Fa-f]{4})'
                       r'(?P<tag>[0-9A-Fa-f]{2})'
                       r'(?P<data>([0-9A-Fa-f]{2}){,255})'
                       r'(?P<checksum>[0-9A-Fa-f]{2})$')

    EXTENSIONS = ('.hex', '.ihex', '.mcs')

    def __init__(self, address, tag, data, checksum=Ellipsis):
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        super().__init__(address, self.TAG_TYPE(tag), data, checksum)

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
                    sum(struct.pack('H', offset)) +
                    self.tag +
                    sum(self.data))

        checksum = (0x100 - int(checksum & 0xFF)) & 0xFF
        return checksum

    def check(self):
        super().check()

        if self.count != self.compute_count():
            raise RuntimeError('count error')

        self.TAG_TYPE(self.tag)
        # TODO: check values

    def is_data(self):
        return self.tag == self.TAG_TYPE.DATA

    @classmethod
    def build_data(cls, address, data):
        record = cls(address, cls.TAG_TYPE.DATA, data)
        return record

    @classmethod
    def build_extended_segment_address(cls, address):
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        segment = address >> 4
        tag = cls.TAG_TYPE.EXTENDED_SEGMENT_ADDRESS
        record = cls(0, tag, struct.pack('>H', segment))
        return record

    @classmethod
    def build_start_segment_address(cls, address):
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        tag = cls.TAG_TYPE.START_SEGMENT_ADDRESS
        record = cls(0, tag, struct.pack('>L', address))
        return record

    @classmethod
    def build_end_of_file(cls):
        tag = cls.TAG_TYPE.END_OF_FILE
        return cls(0, tag, b'')

    @classmethod
    def build_extended_linear_address(cls, address):
        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        segment = address >> 16
        tag = cls.TAG_TYPE.EXTENDED_LINEAR_ADDRESS
        record = cls(0, tag, struct.pack('>H', segment))
        return record

    @classmethod
    def build_start_linear_address(cls, address):
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

        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        if columns > 255:
            raise ValueError('too many columns')

        if start is None:
            start = address
        align_base = address if align else None
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
    def terminate(cls, start):
        return [cls.build_extended_linear_address(0),
                cls.build_start_linear_address(start),
                cls.build_end_of_file()]

    @classmethod
    def readdress(cls, records):
        """Converts to flat addressing.

        *Intel HEX*, stores records by *segment/offset* addressing.
        As this library adopts *flat* addressing instead, all the record
        addresses should be converted to *flat* addressing after loading.
        This procedure readdresses a sequence of records in-place.

        Warning:
            Only the `address` field is modified. ALl the other fields hold
            their previous value.

        Arguments:
            records (list): Sequence of records to be converted to *flat*
                addressing, in-place. Sequence generators supported.

        Example:
            >>> records = [
            ...     IntelRecord.build_extended_linear_address(0x76540000),
            ...     IntelRecord.build_data(0x00003210, b'Hello, World!'),
            ... ]
            >>> records  # doctest: +NORMALIZE_WHITESPACE
            [IntelRecord(address=0x00000000,
                         tag=<IntelTag.EXTENDED_LINEAR_ADDRESS: 4>, count=2,
                         data=b'vT', checksum=0x30),
             IntelRecord(address=0x00003210, tag=<IntelTag.DATA: 0>, count=13,
                         data=b'Hello, World!', checksum=0x48)]
            >>> IntelRecord.readdress(records)
            >>> records  # doctest: +NORMALIZE_WHITESPACE
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
        return value == cls.DATA


class TektronixRecord(Record):

    TAG_TYPE = TektronixTag

    REGEX = re.compile(r'^%(?P<count>[0-9A-Fa-f]{2})'
                       r'(?P<tag>[68])'
                       r'(?P<checksum>[0-9A-Fa-f]{2})'
                       r'8(?P<address>[0-9A-Fa-f]{8})'
                       r'(?P<data>([0-9A-Fa-f]{2}){,255})$')

    EXTENSIONS = ('.tek',)

    def __init__(self, address, tag, data, checksum=Ellipsis):
        super().__init__(address, self.TAG_TYPE(tag), data, checksum)

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
        checksum = sum(int(c, 16) for c in text) & 0xFF
        return checksum

    def check(self):
        super().check()
        tag = self.TAG_TYPE(self.tag)
        if tag == 8 and self.data:
            raise RuntimeError('invalid data')
        if self.count != self.compute_count():
            raise RuntimeError('count error')

    def is_data(self):
        return self.tag == self.TAG_TYPE.DATA

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

    @classmethod
    def build_data(cls, address, data):
        record = cls(address, cls.TAG_TYPE.DATA, data)
        return record

    @classmethod
    def build_terminator(cls, start):
        record = cls(start, cls.TAG_TYPE.TERMINATOR, b'')
        return record

    @classmethod
    def split(cls, data, address=0, columns=16, align=True,
              standalone=True, start=None):

        if not 0 <= address < (1 << 32):
            raise ValueError('address overflow')
        if not 0 <= address + len(data) <= (1 << 32):
            raise ValueError('size overflow')
        if columns > 128:
            raise ValueError('too many columns')

        align_base = address if align else None
        for chunk in chop(data, columns, align_base):
            yield cls.build_data(address, chunk)
            address += len(chunk)

        if standalone:
            yield cls.build_terminator(address if start is None else start)


RECORD_TYPES = {
    'motorola': MotorolaRecord,
    'intel': IntelRecord,
    'tektronix': TektronixRecord,
    'binary': BinaryRecord,
}


def find_record_type(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    for name, record_type in RECORD_TYPES.items():
        if ext in record_type.EXTENSIONS:
            return name
    else:
        raise KeyError('unsupported extension')
