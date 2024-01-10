# -*- coding: utf-8 -*-
import pytest

from hexrec.formats.ascii_hex import AsciiHexFile
from hexrec.formats.ascii_hex import AsciiHexRecord
from hexrec.formats.ascii_hex import AsciiHexTag

from test_records import BaseTestFile
from test_records import BaseTestRecord
from test_records import BaseTestTag


# ============================================================================

class TesAsciiHexTag(BaseTestTag):

    Tag = AsciiHexTag

    # TODO: ...


# ----------------------------------------------------------------------------

class TesAsciiHexRecord(BaseTestRecord):

    Record = AsciiHexRecord

    @pytest.mark.skip(reason='TODO')  # TODO:
    def test_compute_checksum(self):
        ...  # TODO:

    @pytest.mark.skip(reason='TODO')  # TODO:
    def test_compute_count(self):
        ...  # TODO:

    @pytest.mark.skip(reason='TODO')  # TODO:
    def test_parse(self):
        ...  # TODO:

    @pytest.mark.skip(reason='TODO')  # TODO:
    def test_to_bytestr(self):
        ...  # TODO:

    @pytest.mark.skip(reason='TODO')  # TODO:
    def test_to_tokens(self):
        ...  # TODO:

    # TODO: ...


# ----------------------------------------------------------------------------

class TestAsciiHexFile(BaseTestFile):

    File = AsciiHexFile

    # TODO: ...
