*******************
PyInstaller scripts
*******************

This folder contains a wrapper script to generate self-containd executables
with PyInstaller.


Installation
============

Make sure that ``pyinstaller`` is called by a Python environment where
``hexrec`` was successfully installed.

For example, with Anaconda Prompt:

.. code-block:: sh

    $ conda create -n hexrec_pyinstaller python=3 pyinstaller
    $ conda activate hexrec_pyinstaller
    $ cd PATH_TO_HEXREC_SOURCE_ROOT\pyinstaller
    $ python setup.py install


Generation
==========

Example command line to create a standalone executable for Windows:

.. code-block:: sh

    $ pyinstaller -n hexrec --onefile --distpath=win-x86 hexrec_cli.py

This will generate ``hexrec.exe`` in the ``win-x86`` subfolder.
