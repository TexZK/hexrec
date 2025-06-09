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

__version__ = '0.4.3'

from .base import convert
from .base import file_types
from .base import guess_format_name
from .base import guess_format_type
from .base import load
from .base import merge
from .formats.asciihex import AsciiHexFile
from .formats.avr import AvrFile
from .formats.ihex import IhexFile
from .formats.mos import MosFile
from .formats.raw import RawFile
from .formats.srec import SrecFile
from .formats.titxt import TiTxtFile
from .formats.xtek import XtekFile
from .hexdump import hexdump_core
from .xxd import xxd_core


def _register_default_file_types():

    defaults = {
        # The most common formats come first
        'ihex': IhexFile,
        'srec': SrecFile,

        # Least common
        'asciihex': AsciiHexFile,
        'titxt': TiTxtFile,
        'xtek': XtekFile,
        'mos': MosFile,
        'avr': AvrFile,

        # Raw file parses anything, keep as last
        'raw': RawFile
    }

    for key, value in defaults.items():
        file_types.setdefault(key, value)


# Automatically register default file types on module load
_register_default_file_types()
