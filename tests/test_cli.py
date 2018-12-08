# -*- coding: utf-8 -*-
from click.testing import CliRunner

from hexrec.__init__ import __version__ as _version
from hexrec.cli import main

# ============================================================================

def test_xxd_version():
    runner = CliRunner()
    result = runner.invoke(main, 'xxd -v'.split())

    assert result.exit_code == 0
    assert result.output.strip() == str(_version)

# ============================================================================

def test_xxd_empty():
    runner = CliRunner()
    result = runner.invoke(main, 'xxd - -'.split())

    assert result.exit_code == 0
    assert result.output == ''

# ============================================================================

def test_xxd_parse_int_pass():
    runner = CliRunner()
    result = runner.invoke(main, 'xxd -c 0x10 - -'.split())

    assert result.exit_code == 0
    assert result.output == ''


def test_xxd_parse_int_fail():
    runner = CliRunner()
    result = runner.invoke(main, 'xxd -c ? - -'.split())

    assert result.exit_code == 2
    assert '? is not a valid integer' in result.output
