********
Overview
********

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |gh_actions|
        | |codecov|
    * - package
      - | |version| |wheel|
        | |supported-versions|
        | |supported-implementations|

.. |docs| image:: https://app.readthedocs.org/projects/hexrec/badge/?style=flat
    :target: https://app.readthedocs.org/projects/hexrec
    :alt: Documentation Status

.. |gh_actions| image:: https://github.com/TexZK/hexrec/workflows/CI/badge.svg
    :alt: GitHub Actions Status
    :target: https://github.com/TexZK/hexrec

.. |codecov| image:: https://codecov.io/gh/TexZK/hexrec/branch/main/graphs/badge.svg?branch=main
    :alt: Coverage Status
    :target: https://app.codecov.io/github/TexZK/hexrec

.. |version| image:: https://img.shields.io/pypi/v/hexrec.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/hexrec/

.. |wheel| image:: https://img.shields.io/pypi/wheel/hexrec.svg
    :alt: PyPI Wheel
    :target: https://pypi.org/project/hexrec/

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/hexrec.svg
    :alt: Supported versions
    :target: https://pypi.org/project/hexrec/

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/hexrec.svg
    :alt: Supported implementations
    :target: https://pypi.org/project/hexrec/

.. end-badges


Library to handle hexadecimal record files

* Free software: BSD 2-Clause License


Introduction
============

The purpose of this library is to provide simple but useful methods to load,
edit, and save hexadecimal record files.

In the field of embedded systems, hexadecimal record files are the most common
way to share binary data to be written to the target non-volatile memory, such
as a EEPROM or microcontroller code flash.
Such binary data can contain compiled executable code, configuration data,
volatile memory dumps, etc.

The most common file formats for hexadecimal record files are *Intel HEX*
(.hex) and *Motorola S-record* (.srec).
Other common formats for binary data exchange for embedded systems include the
*Executable and Linkable Format* (.elf), hex dumps (by *hexdump* or *xxd*),
and raw binary files (.bin).

A good thing about hexadecimal record files is that they are almost *de-facto*,
so every time a supplier has to give away its binary data it is either in HEX
or SREC, although ELF is arguably the most common for debuggable executables.

A bad thing is that their support in embedded software toolsets is sometimes
flawed or only one of the formats is supported, while the supplier provides its
binary data in the other format.

Another feature is that binary data is split into text record lines (thus their
name) protected by some kind of checksum. This is good for data exchange and
line-by-line writing to the target memory (in the old days), but this makes
in-place editing by humans rather tedious as data should be split, and the
checksum and other metadata have to be updated.

All of the above led to the development of this library, which allows to,
for example:

* convert between hexadecimal record formats;
* merge/patch multiple hexadecimal record files of different formats;
* access every single record of a hexadecimal record file;
* build records through handy methods;
* edit sparse data in a virtual memory behaving like a ``bytearray``;
* extract or update only some parts of the binary data.


Documentation
=============

For the full documentation, please refer to:

https://hexrec.readthedocs.io/en/latest/


Architecture
============

Within the ``hexrec`` package itself are the symbols of the most commonly used
classes and functions.

As the core of this library are record files, the ``hexrec.base`` is the
first module a user should look up.
It provides high-level functions to deal with record files, as well as classes
holding record data.

The ``hexrec.base`` allows to load ``bytesparse`` virtual memories, which
are as easy to use as the native ``bytearray``, but with sparse data blocks.

The ``hexrec.utils`` module provides some miscellaneous utility stuff.

``hexrec.xxd`` is an emulation of the ``xxd`` command line utility delivered
by ``vim``.

The package can also be run as a command line tool, by running the ``hexrec``
package itself (``python -m hexrec``), providing some record file  utilities.

The codebase is written in a simple fashion, to be easily readable and
maintainable, following some naive pythonic *K.I.S.S.* approach by choice.


Examples
========

To have a glimpse of the features provided by this library, some simple but
common examples are shown in the following.


Convert format
--------------

It happens that some software tool only supports some hexadecimal record file
formats, or the format given to you is not handled properly, or simply you
prefer a format against another (*e.g.* SREC has *linear* addressing, while HEX
is in a *segment:offset* fashion).

In this example, a HEX file is converted to SREC.

.. code-block:: python3

    from hexrec import convert

    convert('data.hex', 'data.srec')

This can also be done by running `hexrec` as a command line tool:

.. code-block:: sh

    $ hexrec convert data.hex data.srec

Alternatively, by executing the package itself:

.. code-block:: sh

    $ python -m hexrec convert data.hex data.srec


Merge files
-----------

It is very common that the board factory prefers to receive a single file to
program the microcontroller, because a single file is simpler to manage for
them, and might be faster for their workers or machine, where every second
counts.

This example shows how to merge a bootloader, an executable, and some
configuration data into a single file, in the order they are listed.

.. code-block:: python3

    from hexrec import merge

    in_paths = ['bootloader.hex', 'executable.mot', 'configuration.xtek']
    out_path = 'merged.srec'
    merge(in_paths, out_path)

Alternatively, these files can be merged via manual load:

.. code-block:: python3

    from hexrec import load, SrecFile

    in_paths = ['bootloader.hex', 'executable.mot', 'configuration.xtek']
    in_files = [load(path) for path in in_paths]
    out_file = SrecFile().merge(*in_files)
    out_file.save('merged.srec')

This can also be accomplished by running the `hexrec` package itself as a
command line tool:

.. code-block:: sh

    $ hexrec merge bootloader.hex executable.mot configuration.xtek merged.srec


Dataset generator
-----------------

Let us suppose we are early in the development of the embedded system and we
need to test the current executable with some data stored in EEPROM.
We lack the software tool to generate such data, and even worse we need to test
100 configurations.
For the sake of simplicity, the data structure consists of 4096 random values
(0 to 1) of ``float`` type, stored in little-endian at the address
``0xDA7A0000``.

.. code-block:: python3

    import struct, random
    from hexrec import SrecFile

    for index in range(100):
        values = [random.random() for _ in range(4096)]
        data = struct.pack('<4096f', *values)
        file = SrecFile.from_bytes(data, offset=0xDA7A0000)
        file.save(f'dataset_{index:02d}.mot')


Write a CRC
-----------

Usually, the executable or the configuration data of an embedded system are
protected by a CRC, so that their integrity can be self-checked.

Let us suppose that for some reason the compiler does not calculate such CRC
the expected way, and we prefer to do it with a script.

This example shows how to load a HEX file, compute a CRC32 from the address
``0x1000`` to ``0x3FFB`` (``0x3FFC`` exclusive), and write the calculated CRC
to ``0x3FFC`` in big-endian as a SREC file.
The rest of the data is left untouched.

.. code-block:: python3

    import binascii, struct
    from hexrec import load

    file = load('checkme.srec')

    with file.view(0x1000, 0x3FFC) as view:
        crc = binascii.crc32(view) & 0xFFFFFFFF  # remove sign

    file.write(0x3FFC, struct.pack('>L', crc))
    file.save('checkme_crc.srec')


Trim for bootloader
-------------------

When using a bootloader, it is very important that the application being
written does not overlap with the bootloader.  Sometimes the compiler still
generates stuff like a default interrupt table which should reside in the
bootloader, and we need to get rid of it, as well as everything outside the
address range allocated for the application itself.

This example shows how to trim the application executable record file to the
allocated address range ``0x8000``-``0x1FFFF``.  Being written to a flash
memory, unused memory byte cells default to ``0xFF``.

.. code-block:: python3

    from hexrec import load, SrecFile

    in_file = load('application.mot')
    data = in_file.read(0x8000, 0x1FFFF+1, fill=0xFF)

    out_file = SrecFile.from_bytes(data, offset=0x8000)
    out_file.save('app_trimmed.mot')

This can also be done by running the `hexrec` package as a command line tool:

.. code-block:: sh

    $ hexrec crop -s 0x8000 -e 0x20000 -v 0xFF app_original.hex app_trimmed.srec

By contrast, we need to fill the application range within the bootloader image
with ``0xFF``, so that no existing application will be available again.
Also, we need to preserve the address range ``0x3F800``-``0x3FFFF`` because it
already contains some important data.

.. code-block:: python3

    from hexrec import load

    file = load('bootloader.hex')
    file.fill(0x8000, 0x1FFFF+1, 0xFF)
    file.clear(0x3F800, 0x3FFFF+1)
    file.save('boot_fixed.hex')

With the command line interface, it can be done via a two-pass processing,
first to fill the application range, then to clear the reserved range.
Please note that the first command is chained to the second one via standard
output/input buffering (the virtual ``-`` file path, in ``ihex`` format as
per ``boot_original.hex``).

.. code-block:: sh

    $ hexrec fill -s 0x8000 -e 0x20000 -v 0xFF boot_original.hex - | \
      hexrec clear -s 0x3F800 -e 0x40000 -i ihex - boot_fixed.srec

(newline continuation is backslash ``\`` for a *Unix-like* shell, caret ``^``
for a *DOS* prompt).


Export ELF sections
-------------------

The following example shows how to export *sections* stored within an
*Executable and Linkable File* (*ELF*), compiled for a microcontroller.
As per the previous example, only data within the range ``0x8000``-``0x1FFFF``
are kept, with the rest of the memory filled with the ``0xFF`` value.

.. code-block:: python3

    from hexrec import SrecFile
    from bytesparse import Memory
    from elftools.elf.elffile import ELFFile  # "pyelftools" package

    with open('appelf.elf', 'rb') as elf_stream:
        elf_file = ELFFile(elf_stream)

        memory = Memory(start=0x8000, endex=0x1FFFF+1)  # bounds set
        memory.fill(pattern=0xFF)  # between bounds

        for section in elf_file.iter_sections():
            if (section.header.sh_flags & 3) == 3:  # SHF_WRITE | SHF_ALLOC
                address = section.header.sh_addr
                data = section.data()
                memory.write(address, data)

    out_file = SrecFile.from_memory(memory, header=b'Source: appelf.elf\0')
    out_file.save('appelf.srec')


Installation
============

From PyPI (might not be the latest version found on *github*):

.. code-block:: sh

    $ pip install hexrec

From the source code root directory:

.. code-block:: sh

    $ pip install .


Development
===========

To run the all the tests:

.. code-block:: sh

    $ pip install tox
    $ tox
