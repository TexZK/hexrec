# Copyright (c) 2013-2024, Andrea Zoppi
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

__version__ = '0.4.dev0'

from .formats.asciihex import AsciiHexFile
from .formats.ihex import IhexFile
from .formats.mos import MosFile
from .formats.raw import RawFile
from .formats.srec import SrecFile
from .formats.xtek import XtekFile
from .records import FILE_TYPES
from .xxd import xxd


def _register_default_file_types():
    # TODO: __doc__

    defaults = {
        # Most common come first
        'ihex': IhexFile,
        'srec': SrecFile,

        # Least common
        'asciihex': AsciiHexFile,
        'xtek': XtekFile,
        'mos': MosFile,

        # Raw file parses anything, keep last
        'raw': RawFile
    }

    for key, value in defaults.items():
        FILE_TYPES.setdefault(key, value)


# Automatically register default file types on module load
_register_default_file_types()
