********
Overview
********

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis| |appveyor| |requires|
        | |codecov|
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|

.. |docs| image:: https://readthedocs.org/projects/hexrec/badge/?style=flat
    :target: https://readthedocs.org/projects/hexrec
    :alt: Documentation Status

.. |travis| image:: https://api.travis-ci.org/TexZK/hexrec.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/TexZK/hexrec

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/TexZK/hexrec?branch=master&svg=true
    :alt: AppVeyor Build Status
    :target: https://ci.appveyor.com/project/TexZK/hexrec

.. |requires| image:: https://requires.io/github/TexZK/hexrec/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/TexZK/hexrec/requirements/?branch=master

.. |codecov| image:: https://codecov.io/gh/TexZK/hexrec/branch/master/graphs/badge.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/TexZK/hexrec

.. |version| image:: https://img.shields.io/pypi/v/hexrec.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/hexrec/

.. |commits-since| image:: https://img.shields.io/github/commits-since/TexZK/hexrec/v0.2.0.svg
    :alt: Commits since latest release
    :target: https://github.com/TexZK/hexrec/compare/v0.2.0...master

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
Other common formats for binary data exhange for embedded systems include the
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

https://hexrec.readthedocs.io/


Architecture
============

As the core of this library are record files, the ``hexrec.records`` is the
first module a user should look up.
It provides high-level functions to deal with record files, as well as classes
holding record data.

However, the ``hexrec.records`` module is actually an user-friendly interface
over ``hexrec.blocks``, which manages sparse blocks of data.
It also provides the handy wrapper class ``hexrec.blocks.Memory`` to work
with sparse byte chunks with an API akin to ``bytearray``.

The ``hexrec.utils`` module provides some miscellaneous utility stuff.

``hexrec.xxd`` is an emulation of the ``xxd`` command line utility delivered
by ``vim``.

The package can also be run as a command line tool, by running the ``hexrec``
package itself (``python -m hexrec``), providing some record file  utilities.
You can also create your own standalone executable, or download a precompiled
one from the ``pyinstaller`` folder.

The codebase is written in a simple fashion, to be easily readable and
maintainable, following some naive pythonic *K.I.S.S.* approach by choice.

This is mainly a library to create and manage sparse blocks of binary data,
not made to edit binary data chunks directly.
Please consider faster native pythonic ways to create and edit your binary
data chunks (``bytes``, ``bytearray``, ``struct``, ...).
Algorithms can be very slow if misused (this is Python anyway), but they are
fast enough for the vast majority of operations made on the memory of a
microcontroller-based embedded system.


+------------------------------------------------------+
|                      hexrec.cli                      |
+--------------+---------------------------------------+
|  hexrec.xxd  |                                       |
+--------------+----------------------+----------------+
|              | hexrec.blocks.Memory | hexrec.records |
| hexrec.utils +----------------------+----------------+
|              |            hexrec.blocks              |
+--------------+---------------------------------------+


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

>>> import hexrec.records as hr
>>> hr.convert_file('data.hex', 'data.srec')

This can also be done by running the `hexrec` package as a command line tool:

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

>>> import hexrec.records as hr
>>> input_files = [u'bootloader.hex', 'executable.mot', 'configuration.s19']
>>> hr.merge_files(input_files, 'merged.srec')

This can also be done by running the `hexrec` package as a command line tool:

.. code-block:: sh

    $ python -m hexrec merge bootloader.hex executable.mot configuration.s19 merged.srec


Dataset generator
-----------------

Let us suppose we are early in the development of the embedded system and we
need to test the current executable with some data stored in EEPROM.
We lack the software tool to generate such data, and even worse we need to test
100 configurations.
For the sake of simplicity, the data structure consists of 4096 random values
(0 to 1) of ``float`` type, stored in little-endian at the address
``0xDA7A0000``.

>>> import struct, random
>>> import hexrec.records as hr
>>> for index in range(100):
>>>     values = [random.random() for _ in range(4096)]
>>>     data = struct.pack('<4096f', *values)
>>>     hr.save_chunk(f'dataset_{index:02d}.mot', data, 0xDA7A0000)


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

>>> import binascii, struct
>>> import hexrec.records as hr
>>> import hexrec.blocks as hb
>>> blocks = hr.load_blocks('data_original.hex')
>>> data = hb.read(blocks, 0x1000, 0x3FFC)
>>> crc = binascii.crc32(data) & 0xFFFFFFFF  # remove sign
>>> blocks = hb.write(blocks, 0x3FFC, struct.pack('>L', crc))
>>> hr.save_blocks('data_crc.srec', blocks)

The same example as above, this time using ``hexrec.blocks.Memory`` as
a virtual memory behaving almost like ``bytearray``.

>>> import binascii, struct
>>> import hexrec.records as hr
>>> memory = hr.load_memory('data.srec')
>>> crc = binascii.crc32(memory[0x1000:0x3FFC]) & 0xFFFFFFFF
>>> memory.write(0x3FFC, struct.pack('>L', crc))
>>> hr.save_memory('data_crc.srec', memory)


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

>>> import hexrec.records as hr
>>> memory = hr.load_memory('app_original.hex')
>>> data = memory[0x8000:0x20000:b'\xFF']
>>> hr.save_chunk('app_trimmed.srec', data, 0x8000)

This can also be done by running the `hexrec` package as a command line tool:

.. code-block:: sh

    $ python -m hexrec cut -s 0x8000 -e 0x20000 -v 0xFF app_original.hex app_trimmed.srec

By contrast, we need to fill the application range within the bootloader image
with ``0xFF``, so that no existing application will be available again.
Also, we need to preserve the address range ``0x3F800``-``0x3FFFF`` because it
already contains some important data.

>>> import hexrec.records as hr
>>> memory = hr.load_memory('boot_original.hex')
>>> memory.fill(0x8000, 0x20000, b'\xFF')
>>> memory.clear(0x3F800, 0x40000)
>>> hr.save_memory('boot_fixed.srec', memory)

With the command line interface, it can be done via a two-pass processing,
first to fill the application range, then to clear the reserved range.
Please note that the first command is chained to the second one via standard
output/input buffering (the virtual ``-`` file path, in ``intel`` format as
per ``boot_original.hex``).

.. code-block:: sh

    $ python -m hexrec fill -s 0x8000 -e 0x20000 -v 0xFF boot_original.hex - | \
      python -m hexrec clear -s 0x3F800 -e 0x40000 -i intel - boot_fixed.srec

(newline continuation is backslash ``\`` for a *Unix-like* shell, caret ``^``
for a *DOS* prompt).


Installation
============

From PIP (might not be the latest version found on *github*):

.. code-block:: sh

    $ pip install hexrec

From source:

.. code-block:: sh

    $ python setup.py install


Development
===========

To run the all the tests:

.. code-block:: sh

    $ tox --skip-missing-interpreters


Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - .. code-block:: sh

            $ set PYTEST_ADDOPTS=--cov-append
            $ tox

    - - Other
      - .. code-block:: sh

            $ PYTEST_ADDOPTS=--cov-append tox
