# isort: skip_file
import os
from pathlib import Path

import pytest
from test_base import replace_stdout


@pytest.fixture
def tmppath(tmpdir):
    return Path(str(tmpdir))


@pytest.fixture(scope='module')
def datadir(request):
    dir_path, _ = os.path.splitext(request.module.__file__)
    assert os.path.isdir(str(dir_path))
    return dir_path


@pytest.fixture
def datapath(datadir):
    return Path(str(datadir))


def _read(path) -> bytes:
    with open(str(path), 'rb') as stream:
        return stream.read()


def test_colorize_tokens():
    from hexrec.base import colorize_tokens
    from hexrec import IhexFile
    from pprint import pprint

    record = IhexFile.Record.create_end_of_file()
    tokens = record.to_tokens()

    with replace_stdout() as stdout:
        pprint(tokens)
        stdout.assert_normalized(r"""
        {'address': b'0000',
         'after': b'',
         'before': b'',
         'begin': b':',
         'checksum': b'FF',
         'count': b'00',
         'data': b'',
         'end': b'\r\n',
         'tag': b'01'}
        """)

    colorized = colorize_tokens(tokens)
    with replace_stdout() as stdout:
        pprint(colorized)
        stdout.assert_normalized(r"""
        {'<': b'\x1b[0m',
         '>': b'\x1b[0m',
         'address': b'\x1b[31m0000',
         'begin': b'\x1b[33m:',
         'checksum': b'\x1b[35mFF',
         'count': b'\x1b[34m00',
         'end': b'\x1b[0m\r\n',
         'tag': b'\x1b[32m01'}
        """)


def test_convert(datapath, tmppath):
    from hexrec import convert

    convert(str(datapath / 'data.hex'),
            str(tmppath / 'data.srec'))

    ans_out = _read(tmppath / 'data.srec')
    ans_ref = _read(datapath / 'data.srec')
    assert ans_out == ans_ref


def test_merge_files(datapath, tmppath):
    from hexrec import merge

    in_paths = ['bootloader.hex', 'executable.mot', 'configuration.xtek']
    in_paths = [str(datapath / in_path) for in_path in in_paths]
    out_path = str(tmppath / 'merged_files.srec')
    merge(in_paths, out_path)

    ans_out = _read(tmppath / 'merged_files.srec')
    ans_ref = _read(datapath / 'merged.srec')
    assert ans_out == ans_ref


def test_merge_manual(datapath, tmppath):
    from hexrec import load, SrecFile

    in_paths = ['bootloader.hex', 'executable.mot', 'configuration.xtek']
    in_files = [load(str(datapath / path)) for path in in_paths]
    out_file = SrecFile().merge(*in_files)
    out_file.save(str(tmppath / 'merged_manual.srec'))

    ans_out = _read(tmppath / 'merged_manual.srec')
    ans_ref = _read(datapath / 'merged.srec')
    assert ans_out == ans_ref


def test_dataset_generator(datapath, tmppath):
    import struct
    from hexrec import SrecFile

    for index in range(1):
        out_path = str(tmppath / f'dataset_{index:02d}.mot')
        ref_path = str(datapath / f'dataset_{index:02d}.mot')

        values = [i for i in range(4096)]
        data = struct.pack('<4096f', *values)
        file = SrecFile.from_bytes(data, offset=0xDA7A0000)
        file.save(out_path)

        ans_out = _read(out_path)
        ans_ref = _read(ref_path)
        assert ans_out == ans_ref


def test_write_crc(datapath, tmppath):
    import binascii, struct
    from hexrec import load

    in_path = str(datapath / 'checkme.srec')
    out_path = str(tmppath / 'checkme_crc.srec')
    ref_path = str(datapath / 'checkme_crc.srec')

    file = load(in_path)

    with file.view(0x1000, 0x3FFC) as view:
        crc = binascii.crc32(view) & 0xFFFFFFFF  # remove sign

    file.write(0x3FFC, struct.pack('>L', crc))
    file.save(out_path)

    ans_out = _read(out_path)
    ans_ref = _read(ref_path)
    assert ans_out == ans_ref


def test_trim_app(datapath, tmppath):
    from hexrec import load, SrecFile

    in_path = str(datapath / 'application.mot')
    out_path = str(tmppath / 'app_trimmed.mot')
    ref_path = str(datapath / 'app_trimmed.mot')

    in_file = load(in_path)
    data = in_file.read(0x8000, 0x1FFFF+1, fill=0xFF)

    out_file = SrecFile.from_bytes(data, offset=0x8000)
    out_file.save(out_path)

    ans_out = _read(out_path)
    ans_ref = _read(ref_path)
    assert ans_out == ans_ref


def test_trim_boot(datapath, tmppath):
    from hexrec import load

    in_path = str(datapath / 'bootloader.hex')
    out_path = str(tmppath / 'boot_fixed.hex')
    ref_path = str(datapath / 'boot_fixed.hex')

    file = load(in_path)
    file.fill(0x8000, 0x1FFFF+1, 0xFF)
    file.clear(0x3F800, 0x3FFFF+1)
    file.save(out_path)

    ans_out = _read(out_path)
    ans_ref = _read(ref_path)
    assert ans_out == ans_ref


def test_export_elf(datapath, tmppath):
    from hexrec import SrecFile
    from bytesparse import Memory
    from elftools.elf.elffile import ELFFile  # "pyelftools" package

    in_path = str(datapath / 'appelf.elf')
    out_path = str(tmppath / 'appelf.srec')
    ref_path = str(datapath / 'appelf.srec')

    with open(in_path, 'rb') as elf_stream:
        elf_file = ELFFile(elf_stream)

        memory = Memory(start=0x8000, endex=0x1FFFF+1)  # bounds set
        memory.fill(pattern=0xFF)  # between bounds

        for section in elf_file.iter_sections():
            if (section.header.sh_flags & 3) == 3:  # SHF_WRITE | SHF_ALLOC
                address = section.header.sh_addr
                data = section.data()
                memory.write(address, data)

    out_file = SrecFile.from_memory(memory, header=b'Source: appelf.elf\0')
    out_file.save(out_path)

    ans_out = _read(out_path)
    ans_ref = _read(ref_path)
    assert ans_out == ans_ref
