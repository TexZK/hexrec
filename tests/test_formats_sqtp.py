import io
import os
from pathlib import Path
from typing import cast as _cast

import pytest

from hexrec.formats.ihex import IhexFile
from hexrec.formats.ihex import IhexRecord
from hexrec.formats.ihex import IhexTag
from hexrec.formats.sqtp import from_numbers
from hexrec.formats.sqtp import from_strings
from hexrec.formats.sqtp import to_numbers
from hexrec.formats.sqtp import to_strings


@pytest.fixture(scope='module')
def datadir(request):
    dir_path, _ = os.path.splitext(request.module.__file__)
    assert os.path.isdir(str(dir_path))
    return dir_path


@pytest.fixture
def datapath(datadir):
    return Path(str(datadir))


def get_print(file: IhexFile) -> bytes:
    with io.BytesIO() as stream:
        file.print(stream=stream)
        value = stream.getvalue()
        return value


# https://developerhelp.microchip.com/xwiki/bin/view/software-tools/ipe/sqtp-file-format-specification/example/
def test_parse_record_microchip_sqtp():
    lines = [
        b':02000004740086\r\n',
        b':04000000BF7087ED59\r\n',
        b':0400000043BD7F3449\r\n',
        b':00000001FF\r\n',
    ]
    DATA = IhexTag.DATA
    ELA = IhexTag.EXTENDED_LINEAR_ADDRESS
    EOF = IhexTag.END_OF_FILE
    records = [
        IhexRecord(ELA, count=0x02, address=0x0000, checksum=0x86, data=b'\x74\x00'),
        IhexRecord(DATA, count=0x04, address=0x0000, checksum=0x59, data=b'\xBF\x70\x87\xED'),
        IhexRecord(DATA, count=0x04, address=0x0000, checksum=0x49, data=b'\x43\xBD\x7F\x34'),
        IhexRecord(EOF, count=0x00, address=0x0000, checksum=0xFF, data=b''),
    ]
    for line, expected in zip(lines, records):
        actual = IhexRecord.parse(line)
        actual.validate()
        expected = _cast(IhexRecord, expected)
        expected.validate()
        assert actual == expected


# https://developerhelp.microchip.com/xwiki/bin/view/software-tools/ipe/sqtp-file-format-specification/examples/
def test_parse_file_microchip_sqtp(datapath):
    filenames = [
        'auxmem_dsPIC33EP256MU806.hex',
        'bootmem_PIC32MX110F016B.hex',
        'eeprom_PIC12F1840.hex',
        'eeprom_PIC18F1220.hex',
        'progmem_PIC18F1220.hex',
        'progmem_PIC32MX360F512L.hex',
        'userid_PIC12F1501.hex',  # with correct checksums
        'userid_PIC32MX360F512L.hex',
    ]
    for filename in filenames:
        path = str(datapath / filename)
        with open(path, 'rb') as stream:
            file = IhexFile.parse(stream)
        file.validate_records()


def test_from_numbers_doctest():
    # Program Memory - PIC18F1220
    file = from_numbers(range(5), retlw=0x0C)
    actual = get_print(file)
    expected = (
        b':04000000000C000CE4\r\n'
        b':04000000010C000CE3\r\n'
        b':04000000020C000CE2\r\n'
        b':04000000030C000CE1\r\n'
        b':04000000040C000CE0\r\n'
        b':00000001FF\r\n'
    )
    assert actual == expected

    # Program Memory - PIC32MX360F512L
    file = from_numbers(range(5), length=4, start=0x1D000000, wordsize=4)
    actual = get_print(file)
    expected = (
        b':02000004740086\r\n'
        b':0400000000000000FC\r\n'
        b':0400000001000000FB\r\n'
        b':0400000002000000FA\r\n'
        b':0400000003000000F9\r\n'
        b':0400000004000000F8\r\n'
        b':00000001FF\r\n'
    )
    assert actual == expected

    # User ID - PIC12F1501 (with correct checksums)
    numbers = [0xCF7E, 0xC590, 0x110B, 0xF3F2, 0x681C]
    file = from_numbers(numbers, start=0x8000, retlw=0x34)
    actual = get_print(file)
    expected = (
        b':020000040001F9\r\n'
        b':040000007E34CF3447\r\n'
        b':040000009034C5343F\r\n'
        b':040000000B34113478\r\n'
        b':04000000F234F334AF\r\n'
        b':040000001C34683410\r\n'
        b':00000001FF\r\n'
    )
    assert actual == expected
    file = from_numbers(numbers, start=0x8000, retlw=0x34, byteorder='big')
    actual = get_print(file)
    expected = (
        b':020000040001F9\r\n'
        b':04000000CF347E3447\r\n'
        b':04000000C53490343F\r\n'
        b':0400000011340B3478\r\n'
        b':04000000F334F234AF\r\n'
        b':0400000068341C3410\r\n'
        b':00000001FF\r\n'
    )
    assert actual == expected

    # User ID - PIC32MX360F512L
    file = from_numbers(range(5), length=4, start=0x1FC02FF0, wordsize=4)
    actual = get_print(file)
    expected = (
        b':020000047F007B\r\n'
        b':04BFC000000000007D\r\n'
        b':04BFC000010000007C\r\n'
        b':04BFC000020000007B\r\n'
        b':04BFC000030000007A\r\n'
        b':04BFC0000400000079\r\n'
        b':00000001FF\r\n'
    )
    assert actual == expected

    # Auxiliary Memory - dsPIC33EP256MU806
    file = from_numbers(range(5), length=4, start=0x7FC000, wordsize=4)
    actual = get_print(file)
    expected = (
        b':0200000401FFFA\r\n'
        b':0400000000000000FC\r\n'
        b':0400000001000000FB\r\n'
        b':0400000002000000FA\r\n'
        b':0400000003000000F9\r\n'
        b':0400000004000000F8\r\n'
        b':00000001FF\r\n'
    )
    assert actual == expected

    # Boot Memory - PIC32MX110F016B
    numbers = [0xC78E2639, 0xE277B71F, 0x3D7E1E03, 0xE2646FD5, 0xA7C293F9]
    file = from_numbers(numbers, length=4, start=0x1FC00000, wordsize=4)
    actual = get_print(file)
    expected = (
        b':020000047F007B\r\n'
        b':0400000039268EC748\r\n'
        b':040000001FB777E2CD\r\n'
        b':04000000031E7E3D20\r\n'
        b':04000000D56F64E272\r\n'
        b':04000000F993C2A707\r\n'
        b':00000001FF\r\n'
    )
    assert actual == expected
    file = from_numbers(numbers, length=4, start=0x1FC00000, wordsize=4, byteorder='big')
    actual = get_print(file)
    expected = (
        b':020000047F007B\r\n'
        b':04000000C78E263948\r\n'
        b':04000000E277B71FCD\r\n'
        b':040000003D7E1E0320\r\n'
        b':04000000E2646FD572\r\n'
        b':04000000A7C293F907\r\n'
        b':00000001FF\r\n'
    )
    assert actual == expected

    # EEPROM - PIC12F1840
    file = from_numbers(range(5), forcedela=True)
    actual = get_print(file)
    expected = (
        b':020000040000FA\r\n'
        b':020000000000FE\r\n'
        b':020000000100FD\r\n'
        b':020000000200FC\r\n'
        b':020000000300FB\r\n'
        b':020000000400FA\r\n'
        b':00000001FF\r\n'
    )
    assert actual == expected

    # EEPROM - PIC18F1220 (with actual start address 0x00780000)
    file = from_numbers(range(5), start=0x00780000, forcedela=True)
    actual = get_print(file)
    expected = (
        b':0200000400F00A\r\n'
        b':020000000000FE\r\n'
        b':020000000100FD\r\n'
        b':020000000200FC\r\n'
        b':020000000300FB\r\n'
        b':020000000400FA\r\n'
        b':00000001FF\r\n'
    )
    assert actual == expected


def test_from_strings_doctest():
    strings = [b'abcdefghijklm', b'nopqrstuvwxyz', b'ABCDEFGHIJKLM', b'NOPQRSTUVWXYZ']

    file = from_strings(strings, forcedela=True)
    actual = get_print(file)
    expected = (
        b':020000040000FA\r\n'
        b':0D0000006162636465666768696A6B6C6DB8\r\n'
        b':0D0000006E6F707172737475767778797A0F\r\n'
        b':0D0000004142434445464748494A4B4C4D58\r\n'
        b':0D0000004E4F505152535455565758595AAF\r\n'
        b':00000001FF\r\n'
    )
    assert actual == expected

    file = from_strings(strings, start=0x1FC02FF0, wordsize=4)
    actual = get_print(file)
    expected = (
        b':020000047F007B\r\n'
        b':0DBFC0006162636465666768696A6B6C6D39\r\n'
        b':0DBFC0006E6F707172737475767778797A90\r\n'
        b':0DBFC0004142434445464748494A4B4C4DD9\r\n'
        b':0DBFC0004E4F505152535455565758595A30\r\n'
        b':00000001FF\r\n'
    )
    assert actual == expected

    file = from_strings(strings, start=0x8000, retlw=0x34)
    actual = get_print(file)
    expected = (
        b':020000040001F9\r\n'
        b':1A0000006134623463346434653466346734683469346A346B346C346D3407\r\n'
        b':1A0000006E346F3470347134723473347434753476347734783479347A345E\r\n'
        b':1A0000004134423443344434453446344734483449344A344B344C344D34A7\r\n'
        b':1A0000004E344F3450345134523453345434553456345734583459345A34FE\r\n'
        b':00000001FF\r\n'
    )
    assert actual == expected


def test_from_strings_raises_wordsize():
    for wordsize in [0, 1, 3, 5, 6, 7, 8]:
        with pytest.raises(ValueError, match='invalid word size'):
            from_strings([], wordsize=wordsize)


def test_from_strings_raises_length_invalid():
    for wordsize in [2, 4]:
        lengths = list(range(wordsize)) + [257]
        for length in lengths:
            string = b'x' * length
            with pytest.raises(ValueError, match='invalid string length'):
                from_strings([string], wordsize=wordsize)


def test_from_strings_raises_length_inconsistent():
    with pytest.raises(ValueError, match='inconsistent string length'):
        from_strings([b'abcd', b'xyz'])


def test_from_strings_raises_start_overflow():
    for start in [-1, 0x100000000]:
        with pytest.raises(ValueError, match='start address overflow'):
            from_strings([], start=start)


def test_from_strings_raises_start_misaligned():
    for wordsize in [2, 4]:
        for offset in [-1, +1]:
            start = wordsize + offset
            with pytest.raises(ValueError, match='misaligned start address'):
                from_strings([], start=start, wordsize=wordsize)


def test_to_numbers():
    # Program Memory - PIC18F1220
    file = IhexFile.parse(b'''
        :04000000000C000CE4
        :04000000010C000CE3
        :04000000020C000CE2
        :04000000030C000CE1
        :04000000040C000CE0
        :00000001FF
    ''')
    actual = to_numbers(file, retlw=True)
    expected = [0, 1, 2, 3, 4]
    assert actual == expected

    # Program Memory - PIC32MX360F512L
    file = IhexFile.parse(b'''
        :02000004740086
        :0400000000000000FC
        :0400000001000000FB
        :0400000002000000FA
        :0400000003000000F9
        :0400000004000000F8
        :00000001FF
    ''')
    actual = to_numbers(file)
    expected = [0, 1, 2, 3, 4]
    assert actual == expected

    # User ID - PIC12F1501 (with correct checksums)
    file = IhexFile.parse(b'''
        :020000040001F9
        :040000007E34CF3447
        :040000009034C5343F
        :040000000B34113478
        :04000000F234F334AF
        :040000001C34683410
        :00000001FF
    ''')
    actual = to_numbers(file, retlw=True)
    expected = [53118, 50576, 4363, 62450, 26652]
    assert actual == expected
    actual = to_numbers(file, retlw=True, byteorder='big')
    expected = [32463, 37061, 2833, 62195, 7272]
    assert actual == expected

    # User ID - PIC32MX360F512L
    file = IhexFile.parse(b'''
        :020000047F007B
        :04BFC000000000007D
        :04BFC000010000007C
        :04BFC000020000007B
        :04BFC000030000007A
        :04BFC0000400000079
        :00000001FF
    ''')
    actual = to_numbers(file)
    expected = [0, 1, 2, 3, 4]
    assert actual == expected

    # Auxiliary Memory - dsPIC33EP256MU806
    file = IhexFile.parse(b'''
        :0200000401FFFA
        :0400000000000000FC
        :0400000001000000FB
        :0400000002000000FA
        :0400000003000000F9
        :0400000004000000F8
        :00000001FF
    ''')
    actual = to_numbers(file)
    expected = [0, 1, 2, 3, 4]
    assert actual == expected

    # Boot Memory - PIC32MX110F016B
    file = IhexFile.parse(b'''
        :020000047F007B
        :0400000039268EC748
        :040000001FB777E2CD
        :04000000031E7E3D20
        :04000000D56F64E272
        :04000000F993C2A707
        :00000001FF
    ''')
    actual = to_numbers(file)
    expected = [3347981881, 3799496479, 1031675395, 3798233045, 2814546937]
    assert actual == expected
    actual = to_numbers(file, byteorder='big')
    expected = [958828231, 532117474, 52330045, 3580847330, 4187210407]
    assert actual == expected

    # EEPROM - PIC12F1840
    file = IhexFile.parse(b'''
        :020000040000FA
        :020000000000FE
        :020000000100FD
        :020000000200FC
        :020000000300FB
        :020000000400FA
        :00000001FF
    ''')
    actual = to_numbers(file)
    expected = [0, 1, 2, 3, 4]
    assert actual == expected

    # EEPROM - PIC18F1220 (with actual start address 0x00780000)
    file = IhexFile.parse(b'''
        :0200000400F00A
        :020000000000FE
        :020000000100FD
        :020000000200FC
        :020000000300FB
        :020000000400FA
        :00000001FF
    ''')
    actual = to_numbers(file)
    expected = [0, 1, 2, 3, 4]
    assert actual == expected


def test_to_strings_doctest():
    file = IhexFile.parse(b'''
        :020000040000FA
        :0D0000006162636465666768696A6B6C6DB8
        :0D0000006E6F707172737475767778797A0F
        :0D0000004142434445464748494A4B4C4D58
        :0D0000004E4F505152535455565758595AAF
        :00000001FF
    ''')
    actual = to_strings(file)
    expected = [b'abcdefghijklm', b'nopqrstuvwxyz', b'ABCDEFGHIJKLM', b'NOPQRSTUVWXYZ']
    assert actual == expected

    file = IhexFile.parse(b'''
        :020000047F007B
        :0DBFC0006162636465666768696A6B6C6D39
        :0DBFC0006E6F707172737475767778797A90
        :0DBFC0004142434445464748494A4B4C4DD9
        :0DBFC0004E4F505152535455565758595A30
        :00000001FF
    ''')
    actual = to_strings(file)
    expected = [b'abcdefghijklm', b'nopqrstuvwxyz', b'ABCDEFGHIJKLM', b'NOPQRSTUVWXYZ']
    assert actual == expected

    file = IhexFile.parse(b'''
        :020000040001F9
        :1A0000006134623463346434653466346734683469346A346B346C346D3407
        :1A0000006E346F3470347134723473347434753476347734783479347A345E
        :1A0000004134423443344434453446344734483449344A344B344C344D34A7
        :1A0000004E344F3450345134523453345434553456345734583459345A34FE
        :00000001FF
    ''')
    actual = to_strings(file, retlw=True)
    expected = [b'abcdefghijklm', b'nopqrstuvwxyz', b'ABCDEFGHIJKLM', b'NOPQRSTUVWXYZ']
    assert actual == expected
