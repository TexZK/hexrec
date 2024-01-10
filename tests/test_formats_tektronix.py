# -*- coding: utf-8 -*-

import pytest

from hexrec.formats.tektronix import TekExtFile
from hexrec.formats.tektronix import TekExtRecord
from hexrec.formats.tektronix import TekExtTag

from test_records import BaseTestFile
from test_records import BaseTestRecord
from test_records import BaseTestTag


# ============================================================================

class TesTekExtTag(BaseTestTag):

    Tag = TekExtTag

    # TODO: ...


# ----------------------------------------------------------------------------

class TestTekExtRecord(BaseTestRecord):

    Record = TekExtRecord

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

class TestTekExtFile(BaseTestFile):

    File = TekExtFile

    # TODO: ...
