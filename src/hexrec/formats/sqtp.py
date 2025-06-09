# Copyright (c) 2013-2025, Andrea Zoppi
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

r"""Microchip Serial Quick Time Programming format.

See Also:
    `<https://developerhelp.microchip.com/xwiki/bin/view/software-tools/ipe/sqtp-file-format-specification/>`_
"""

from typing import Any
from typing import Iterable
from typing import Optional
from typing import Sequence
from typing import cast as _cast

from ..base import AnyBytes
from .ihex import IhexFile
from .ihex import IhexRecord


def from_numbers(
    numbers: Iterable[int],
    length: int = 2,
    start: int = 0,
    retlw: Optional[int] = None,
    wordsize: int = 2,
    byteorder: str = 'little',
    forcedela: bool = False,
) -> IhexFile:
    r"""Creates a file from numbers.

    Given a sequence of numbers, it creates an *Intel HEX* file with the
    special record sequence and addressing of *Microchip SQTP*.

    Args:
        numbers (list of int):
            Sequence of serial numbers.

        length (int):
            Serial number byte size.

        start (int):
            Start word address of a serial number within the target memory.

        retlw (int):
            If ``None``, this has no effect.
            If a byte integer is given, it must be the equivalent of the
            ``RETLW`` *opcode* of the target processor.
            The ``RETLW`` byte is put after each byte of the serial number.

        wordsize (int):
            Memory word size (2 or 4 bytes).

        byteorder (str):
            By default, *Microchip SQTP* uses ``little`` endian.
            Provide ``big`` for the alternative integer byte order.

        forcedela (bool):
            Forces *Extended Linear Address* generation.

    Returns:
        :class:`IhexFile`: *Microchip SQTP* file as special *Intel HEX* format.

    Examples:
        `<https://developerhelp.microchip.com/xwiki/bin/view/software-tools/ipe/sqtp-file-format-specification/examples/>`_.

        >>> from hexrec.formats.sqtp import from_numbers

        >>> # Program Memory - PIC18F1220
        >>> file = from_numbers(range(5), retlw=0x0C)
        >>> _ = file.print()
        :04000000000C000CE4
        :04000000010C000CE3
        :04000000020C000CE2
        :04000000030C000CE1
        :04000000040C000CE0
        :00000001FF

        >>> # Program Memory - PIC32MX360F512L
        >>> file = from_numbers(range(5), length=4, start=0x1D000000, wordsize=4)
        >>> _ = file.print()
        :02000004740086
        :0400000000000000FC
        :0400000001000000FB
        :0400000002000000FA
        :0400000003000000F9
        :0400000004000000F8
        :00000001FF

        >>> # User ID - PIC12F1501 (with correct checksums)
        >>> numbers = [0xCF7E, 0xC590, 0x110B, 0xF3F2, 0x681C]
        >>> file = from_numbers(numbers, start=0x8000, retlw=0x34)
        >>> _ = file.print()
        :020000040001F9
        :040000007E34CF3447
        :040000009034C5343F
        :040000000B34113478
        :04000000F234F334AF
        :040000001C34683410
        :00000001FF
        >>> file = from_numbers(numbers, start=0x8000, retlw=0x34, byteorder='big')
        >>> _ = file.print()
        :020000040001F9
        :04000000CF347E3447
        :04000000C53490343F
        :0400000011340B3478
        :04000000F334F234AF
        :0400000068341C3410
        :00000001FF

        >>> # User ID - PIC32MX360F512L
        >>> file = from_numbers(range(5), length=4, start=0x1FC02FF0, wordsize=4)
        >>> _ = file.print()
        :020000047F007B
        :04BFC000000000007D
        :04BFC000010000007C
        :04BFC000020000007B
        :04BFC000030000007A
        :04BFC0000400000079
        :00000001FF

        >>> # Auxiliary Memory - dsPIC33EP256MU806
        >>> file = from_numbers(range(5), length=4, start=0x7FC000, wordsize=4)
        >>> _ = file.print()
        :0200000401FFFA
        :0400000000000000FC
        :0400000001000000FB
        :0400000002000000FA
        :0400000003000000F9
        :0400000004000000F8
        :00000001FF

        >>> # Boot Memory - PIC32MX110F016B
        >>> numbers = [0xC78E2639, 0xE277B71F, 0x3D7E1E03, 0xE2646FD5, 0xA7C293F9]
        >>> file = from_numbers(numbers, length=4, start=0x1FC00000, wordsize=4)
        >>> _ = file.print()
        :020000047F007B
        :0400000039268EC748
        :040000001FB777E2CD
        :04000000031E7E3D20
        :04000000D56F64E272
        :04000000F993C2A707
        :00000001FF
        >>> file = from_numbers(numbers, length=4, start=0x1FC00000, wordsize=4, byteorder='big')
        >>> _ = file.print()
        :020000047F007B
        :04000000C78E263948
        :04000000E277B71FCD
        :040000003D7E1E0320
        :04000000E2646FD572
        :04000000A7C293F907
        :00000001FF

        >>> # EEPROM - PIC12F1840
        >>> file = from_numbers(range(5), forcedela=True)
        >>> _ = file.print()
        :020000040000FA
        :020000000000FE
        :020000000100FD
        :020000000200FC
        :020000000300FB
        :020000000400FA
        :00000001FF

        >>> # EEPROM - PIC18F1220 (with actual start address 0x00780000)
        >>> file = from_numbers(range(5), start=0x00780000, forcedela=True)
        >>> _ = file.print()
        :0200000400F00A
        :020000000000FE
        :020000000100FD
        :020000000200FC
        :020000000300FB
        :020000000400FA
        :00000001FF
    """

    byteorder = _cast(Any, byteorder)
    strings = [
        int(number).to_bytes(length, byteorder)
        for number in numbers
    ]
    file = from_strings(
        strings,
        start=start,
        retlw=retlw,
        wordsize=wordsize,
        forcedela=forcedela,
    )
    return file


def from_strings(
    strings: Sequence[AnyBytes],
    start: int = 0,
    retlw: Optional[int] = None,
    wordsize: int = 2,
    forcedela: bool = False,
) -> IhexFile:
    r"""Creates a file from byte strings.

    Given a sequence of byte strings, it creates an *Intel HEX* file with the
    special record sequence and addressing of *Microchip SQTP*.

    All the `strings` must be the same length, between the minimum word size
    of the processor (minimum 2) and 256.

    Args:
        strings (list of bytes):
            Sequence of byte strings.

        start (int):
            Start word address of a byte string within the target memory.

        retlw (int):
            If ``None``, this has no effect.
            If a byte integer is given, it must be the equivalent of the
            ``RETLW`` *opcode* of the target processor.
            The ``RETLW`` byte is put after each byte of the byte string.

        wordsize (int):
            Memory word size (2 or 4 bytes).

        forcedela (bool):
            Forces *Extended Linear Address* generation.

    Returns:
        :class:`IhexFile`: *Microchip SQTP* file as special *Intel HEX* format.

    Examples:
        >>> from hexrec.formats.sqtp import from_strings
        >>> strings = [b'abcdefghijklm', b'nopqrstuvwxyz', b'ABCDEFGHIJKLM', b'NOPQRSTUVWXYZ']

        >>> file = from_strings(strings, forcedela=True)
        >>> _ = file.print()
        :020000040000FA
        :0D0000006162636465666768696A6B6C6DB8
        :0D0000006E6F707172737475767778797A0F
        :0D0000004142434445464748494A4B4C4D58
        :0D0000004E4F505152535455565758595AAF
        :00000001FF

        >>> file = from_strings(strings, start=0x1FC02FF0, wordsize=4)
        >>> _ = file.print()
        :020000047F007B
        :0DBFC0006162636465666768696A6B6C6D39
        :0DBFC0006E6F707172737475767778797A90
        :0DBFC0004142434445464748494A4B4C4DD9
        :0DBFC0004E4F505152535455565758595A30
        :00000001FF

        >>> file = from_strings(strings, start=0x8000, retlw=0x34)
        >>> _ = file.print()
        :020000040001F9
        :1A0000006134623463346434653466346734683469346A346B346C346D3407
        :1A0000006E346F3470347134723473347434753476347734783479347A345E
        :1A0000004134423443344434453446344734483449344A344B344C344D34A7
        :1A0000004E344F3450345134523453345434553456345734583459345A34FE
        :00000001FF
    """

    wordsize = wordsize.__index__()
    if wordsize != 2 and wordsize != 4:
        raise ValueError('invalid word size')
    length = max((len(s) for s in strings), default=wordsize)
    if not wordsize <= length <= 256:
        raise ValueError('invalid string length')
    if any(len(s) != length for s in strings):
        raise ValueError('inconsistent string length')
    start = start.__index__()
    if not 0 <= start <= 0x3FFFFFFF:
        raise ValueError('start address overflow')
    if start % wordsize:
        raise ValueError('misaligned start address')

    retlw_bytes = bytes([retlw or 0]) * (length * 2)
    records = []

    address = start * wordsize
    extension = address >> 16
    address &= 0xFFFF

    if extension or forcedela:
        record = IhexRecord.create_extended_linear_address(extension)
        records.append(record)

    for string in strings:
        if retlw is None:
            data = string
        else:
            data = bytearray(retlw_bytes)
            data[::2] = string

        record = IhexRecord.create_data(address, data)
        records.append(record)

    record = IhexRecord.create_end_of_file()
    records.append(record)

    file = IhexFile.from_records(records)
    return file


def to_numbers(
    file: IhexFile,
    retlw: bool = False,
    byteorder: str = 'little',
) -> Sequence[int]:
    r"""Extracts numbers from a file.

    Given a *Microchip SQTP* file (as special *Intel HEX* format), it extracts
    numbers from *data* records.

    Warnings:
        This algorithm ignores addressing. It just takes *data* records and
        converts them into numbers.
        Please provide valid *Microchip SQTP* files only.

    Args:
        file (:class:`IhexFile`):
            *Microchip SQTP* file as special *Intel HEX* format.

        retlw (bool):
            The ``RETLW`` byte is put after each byte of the byte string.
            If true, it ignores the ``RETLW`` bytes.

        byteorder (str):
            By default, *Microchip SQTP* uses ``little`` endian.
            Provide ``big`` for the alternative integer byte order.

    Returns:
        list of int: Sequence of serial numbers.

    Examples:
        `<https://developerhelp.microchip.com/xwiki/bin/view/software-tools/ipe/sqtp-file-format-specification/examples/>`_.

        >>> from hexrec import IhexFile
        >>> from hexrec.formats.sqtp import to_numbers

        >>> # Program Memory - PIC18F1220
        >>> file = IhexFile.parse(b'''
        ...     :04000000000C000CE4
        ...     :04000000010C000CE3
        ...     :04000000020C000CE2
        ...     :04000000030C000CE1
        ...     :04000000040C000CE0
        ...     :00000001FF
        ... ''')
        >>> to_numbers(file, retlw=True)
        [0, 1, 2, 3, 4]

        >>> # Program Memory - PIC32MX360F512L
        >>> file = IhexFile.parse(b'''
        ...     :02000004740086
        ...     :0400000000000000FC
        ...     :0400000001000000FB
        ...     :0400000002000000FA
        ...     :0400000003000000F9
        ...     :0400000004000000F8
        ...     :00000001FF
        ... ''')
        >>> to_numbers(file)
        [0, 1, 2, 3, 4]

        >>> # User ID - PIC12F1501 (with correct checksums)
        >>> file = IhexFile.parse(b'''
        ...     :020000040001F9
        ...     :040000007E34CF3447
        ...     :040000009034C5343F
        ...     :040000000B34113478
        ...     :04000000F234F334AF
        ...     :040000001C34683410
        ...     :00000001FF
        ... ''')
        >>> to_numbers(file, retlw=True)
        [53118, 50576, 4363, 62450, 26652]
        >>> to_numbers(file, retlw=True, byteorder='big')
        [32463, 37061, 2833, 62195, 7272]

        >>> # User ID - PIC32MX360F512L
        >>> file = IhexFile.parse(b'''
        ...     :020000047F007B
        ...     :04BFC000000000007D
        ...     :04BFC000010000007C
        ...     :04BFC000020000007B
        ...     :04BFC000030000007A
        ...     :04BFC0000400000079
        ...     :00000001FF
        ... ''')
        >>> to_numbers(file)
        [0, 1, 2, 3, 4]

        >>> # Auxiliary Memory - dsPIC33EP256MU806
        >>> file = IhexFile.parse(b'''
        ...     :0200000401FFFA
        ...     :0400000000000000FC
        ...     :0400000001000000FB
        ...     :0400000002000000FA
        ...     :0400000003000000F9
        ...     :0400000004000000F8
        ...     :00000001FF
        ... ''')
        >>> to_numbers(file)
        [0, 1, 2, 3, 4]

        >>> # Boot Memory - PIC32MX110F016B
        >>> file = IhexFile.parse(b'''
        ...     :020000047F007B
        ...     :0400000039268EC748
        ...     :040000001FB777E2CD
        ...     :04000000031E7E3D20
        ...     :04000000D56F64E272
        ...     :04000000F993C2A707
        ...     :00000001FF
        ... ''')
        >>> to_numbers(file)
        [3347981881, 3799496479, 1031675395, 3798233045, 2814546937]
        >>> to_numbers(file, byteorder='big')
        [958828231, 532117474, 52330045, 3580847330, 4187210407]

        >>> # EEPROM - PIC12F1840
        >>> file = IhexFile.parse(b'''
        ...     :020000040000FA
        ...     :020000000000FE
        ...     :020000000100FD
        ...     :020000000200FC
        ...     :020000000300FB
        ...     :020000000400FA
        ...     :00000001FF
        ... ''')
        >>> to_numbers(file)
        [0, 1, 2, 3, 4]

        >>> # EEPROM - PIC18F1220 (with actual start address 0x00780000)
        >>> file = IhexFile.parse(b'''
        ...     :0200000400F00A
        ...     :020000000000FE
        ...     :020000000100FD
        ...     :020000000200FC
        ...     :020000000300FB
        ...     :020000000400FA
        ...     :00000001FF
        ... ''')
        >>> to_numbers(file)
        [0, 1, 2, 3, 4]
    """

    byteorder = _cast(Any, byteorder)
    numbers = [
        int.from_bytes(string, byteorder)
        for string in to_strings(file, retlw=retlw)
    ]
    return numbers


def to_strings(
    file: IhexFile,
    retlw: bool = False,
) -> Sequence[AnyBytes]:
    r"""Extracts byte strings from a file.

    Given a *Microchip SQTP* file (as special *Intel HEX* format), it extracts
    byte strings from *data* records.

    Warnings:
        This algorithm ignores addressing. It just takes *data* records.
        Please provide valid *Microchip SQTP* files only.

    Args:
        file (:class:`IhexFile`):
            *Microchip SQTP* file as special *Intel HEX* format.

        retlw (bool):
            The ``RETLW`` byte is put after each byte of the byte string.
            If true, it ignores the ``RETLW`` bytes.

    Returns:
        list of int: Sequence of byte strings.

    Examples:
        >>> from hexrec import IhexFile
        >>> from hexrec.formats.sqtp import to_strings

        >>> file = IhexFile.parse(b'''
        ...     :020000040000FA
        ...     :0D0000006162636465666768696A6B6C6DB8
        ...     :0D0000006E6F707172737475767778797A0F
        ...     :0D0000004142434445464748494A4B4C4D58
        ...     :0D0000004E4F505152535455565758595AAF
        ...     :00000001FF
        ... ''')
        >>> to_strings(file)
        [b'abcdefghijklm', b'nopqrstuvwxyz', b'ABCDEFGHIJKLM', b'NOPQRSTUVWXYZ']

        >>> file = IhexFile.parse(b'''
        ...     :020000047F007B
        ...     :0DBFC0006162636465666768696A6B6C6D39
        ...     :0DBFC0006E6F707172737475767778797A90
        ...     :0DBFC0004142434445464748494A4B4C4DD9
        ...     :0DBFC0004E4F505152535455565758595A30
        ...     :00000001FF
        ... ''')
        >>> to_strings(file)
        [b'abcdefghijklm', b'nopqrstuvwxyz', b'ABCDEFGHIJKLM', b'NOPQRSTUVWXYZ']

        >>> file = IhexFile.parse(b'''
        ...     :020000040001F9
        ...     :1A0000006134623463346434653466346734683469346A346B346C346D3407
        ...     :1A0000006E346F3470347134723473347434753476347734783479347A345E
        ...     :1A0000004134423443344434453446344734483449344A344B344C344D34A7
        ...     :1A0000004E344F3450345134523453345434553456345734583459345A34FE
        ...     :00000001FF
        ... ''')
        >>> to_strings(file, retlw=True)
        [b'abcdefghijklm', b'nopqrstuvwxyz', b'ABCDEFGHIJKLM', b'NOPQRSTUVWXYZ']
    """

    strings = [
        record.data
        for record in file.records
        if record.tag.is_data()
    ]
    if retlw:
        strings = [string[::2] for string in strings]
    return strings
