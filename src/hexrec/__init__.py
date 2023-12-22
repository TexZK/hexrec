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

from .formats.ascii_hex import AsciiHexFile
from .formats.binary import RawFile
from .formats.intel import IhexFile
from .formats.mos import MosFile
from .formats.motorola import SrecFile
from .formats.tektronix import TekExtFile
from .records2 import FILE_TYPES
from .xxd import xxd

if 1:  # TODO: remove all
    from .formats.ascii_hex import Record as AsciiHexRecord
    from .formats.binary import Record as BinaryRecord
    from .formats.intel import Record as IntelRecord
    from .formats.mos import Record as MosRecord
    from .formats.motorola import Record as MotorolaRecord
    from .formats.tektronix import Record as TektronixRecord
    from .records import convert_file
    from .records import find_record_type
    from .records import find_record_type_name
    from .records import load_memory
    from .records import load_records
    from .records import merge_files
    from .records import register_default_record_types
    from .records import save_memory
    from .records import save_records

# Register default record file types
FILE_TYPES.update({
    'asciihex': AsciiHexFile,
    'ihex': IhexFile,
    'mos': MosFile,
    'raw': RawFile,
    'srec': SrecFile,
    'tekext': TekExtFile,
})
