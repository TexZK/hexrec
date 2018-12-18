"""
Run PyInstaller against this script file to build a standalone executable.
Make sure that hexrec is installed into the Python environment before.
"""
from hexrec.__main__ import main as _main

_main('__main__')
