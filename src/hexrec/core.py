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

from .utils import chop
from .utils import do_overlap
from .utils import hexlify
from .utils import merge_blocks
from .utils import unhexlify


def merge_records(sorted_data_records, input_types=None, output_type=None,
                  split_args=None, split_kwargs=None):

    if input_types is None:
        input_types = [type(records[0]) if records else Record
                       for records in sorted_data_records]
    else:
        input_types = list(input_types)

    if output_type is None:
        output_type = input_types[0]

    input_blocks = []
    for level in range(len(input_types)):
        records = sorted_data_records[level]
        input_type = input_types[level]
        input_blocks.extend((p[0].address, level, input_type.flatten(p))
                            for p in input_type.partition(records))

    input_blocks.sort()
    merged_blocks = merge_blocks(input_blocks)

    args = split_args or ()
    kwargs = split_kwargs or {}
    output_records = []
    for start, _, chunk in merged_blocks:
        records = output_type.split(chunk, *args, start=start, **kwargs)
        output_records.extend(records)

    return output_records


def convert_records(records, input_type=None, output_type=None,
                    split_args=None, split_kwargs=None):
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
    merge_files([input_file], output_file, [input_type], output_type,
                split_args, split_kwargs)


def load_file(path, record_type=None):
    if record_type is None:
        type_name = find_record_type(path)
        record_type = RECORD_TYPES[type_name]
    records = record_type.load(path)
    return records


def save_file(path, records, record_type=None,
              split_args=None, split_kwargs=None):

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


SIZE_GUARD = 64 << 20  # 64 MiB bound


def _size_guard(start, endex):
    fill_length = endex - start
    if not 0 <= fill_length <= SIZE_GUARD:
        fmt = 'Trying to fill {} bytes, which is likely too much'
        raise ResourceWarning(fmt.format(fill_length))


class Record(object):

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
        return repr(self)

    def __eq__(self, other):
        return (self.address == other.address and
                self.tag == other.tag and
                self.data == other.data)

    def __hash__(self):
        return (hash(self.address or 0) ^
                hash(self.tag or 0) ^
                hash(self.data or b'') ^
                hash(self.count or 0) ^
                hash(self.checksum or 0))

    def __lt__(self, other):
        return self.address < other.address

    def __copy__(self):
        cls = type(self)
        copied = cls(self.address, self.tag, self.data, self.checksum)
        copied.__dict__.update(self.__dict__)
        return copied

    def is_data(self):
        raise NotImplementedError()
        return False

    def compute_count(self):
        raise NotImplementedError()
        return 0

    def update_count(self):
        self.count = self.compute_count()

    def compute_checksum(self):
        raise NotImplementedError()
        return 0

    def update_checksum(self):
        self.checksum = self.compute_checksum()

    def _get_checksum(self):
        if self.checksum is None:
            return self.compute_checksum()
        else:
            return self.checksum

    def check(self):
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
        if self.address is None or other.address is None:
            return False
        else:
            return do_overlap(self.address,
                              self.address + len(self.data),
                              other.address,
                              other.address + len(other.data))

    @classmethod
    def parse(cls, line, *args, **kwargs):
        raise NotImplementedError()

    @classmethod
    def split(cls, data, *args, **kwargs):
        raise NotImplementedError()

    @classmethod
    def check_sequence(cls, records):
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
        pass

    @classmethod
    def flatten(cls, sorted_data_records, start=None, endex=None, align=1,
                fill=b'\xFF', size_guard=Ellipsis):

        if not sorted_data_records:
            return b''

        if start is None:
            start = sorted_data_records[0].address
        if endex is None:
            endex = (sorted_data_records[-1].address +
                     len(sorted_data_records[-1].data))
        if start > endex:
            raise ValueError('address overflow')
        start -= start % align
        endex += -endex % align

        if size_guard is Ellipsis:
            size_guard = _size_guard
        if size_guard is not None:
            size_guard(start, endex)

        data = bytearray().ljust(endex - start, fill)

        for record in sorted_data_records:
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
        with open(path, 'rt') as stream:
            records = [cls.parse(line) for line in stream]
        return records

    @classmethod
    def save(cls, path, records):
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

    def compute_count(self):
        count = len(self.data)
        return count

    def compute_checksum(self):
        checksum = sum(self.data) & 0xFF
        return checksum

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
    'motorola'  : MotorolaRecord,
    'intel'     : IntelRecord,
    'tektronix' : TektronixRecord,
    'binary'    : BinaryRecord,
}


def find_record_type(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    for name, record_type in RECORD_TYPES.items():
        if ext in record_type.EXTENSIONS:
            return name
    else:
        raise KeyError('unsupported extension')
