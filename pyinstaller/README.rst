*******************
PyInstaller scripts
*******************

This folder contains wrapper scripts to generate self-contained executables
with PyInstaller.


Installation
============

Make sure that ``pyinstaller`` is called by a Python environment where
``hexrec`` was successfully installed.

For example, with Anaconda Prompt:

.. code-block:: sh

    $ conda create -n hexrec_pyinstaller python=3
    $ conda activate hexrec_pyinstaller
    $ pip install pyinstaller
    $ cd PATH_TO_HEXREC_SOURCE_ROOT
    $ python setup.py install


Generation
==========

Example command line to create a standalone executable for Windows:

.. code-block:: sh

    $ cd PATH_TO_HEXREC_SOURCE_ROOT
    $ cd pyinstaller
    $ pyinstaller -n hexrec --onefile --distpath=win-x86 hexrec_cli.py

This will generate ``hexrec.exe`` in the ``win-x86`` subfolder.


Disclaimer
==========

All the generated executables files found in the subdirectories of this
repository may be outdated with respect to the actual source code, and are only
provided as-is for example purposes, although they should work properly.
