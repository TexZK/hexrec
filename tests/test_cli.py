# -*- coding: utf-8 -*-
from click.testing import CliRunner

from hexrec.__init__ import __version__ as _version
from hexrec.cli import main

# ============================================================================

def _run_help(command):
    runner = CliRunner()
    result = runner.invoke(main, [command, '--help'])
    assert result.exit_code == 0
    assert result.output.strip().startswith('Usage:')

# ============================================================================

def test_clear_help():
    _run_help('clear')

# ============================================================================

def test_convert_help():
    _run_help('convert')

# ============================================================================

def test_cut_help():
    _run_help('cut')

# ============================================================================

def test_delete_help():
    _run_help('delete')

# ============================================================================

def test_fill_help():
    _run_help('fill')

# ============================================================================

def test_flood_help():
    _run_help('flood')

# ============================================================================

def test_merge_help():
    _run_help('merge')

# ============================================================================

def test_reverse_help():
    _run_help('reverse')

# ============================================================================

def test_shift_help():
    _run_help('shift')

# ============================================================================

def test_xxd_help():
    _run_help('xxd')

# ----------------------------------------------------------------------------

def test_xxd_version():
    runner = CliRunner()
    result = runner.invoke(main, 'xxd -v'.split())

    assert result.exit_code == 0
    assert result.output.strip() == str(_version)

# ----------------------------------------------------------------------------

def test_xxd_empty():
    runner = CliRunner()
    result = runner.invoke(main, 'xxd - -'.split())

    assert result.exit_code == 0
    assert result.output == ''

# ----------------------------------------------------------------------------

def test_xxd_parse_int_pass():
    runner = CliRunner()
    result = runner.invoke(main, 'xxd -c 0x10 - -'.split())

    assert result.exit_code == 0
    assert result.output == ''

# ----------------------------------------------------------------------------

def test_xxd_parse_int_fail():
    runner = CliRunner()
    result = runner.invoke(main, 'xxd -c ? - -'.split())

    assert result.exit_code == 2
    assert '? is not a valid integer' in result.output
