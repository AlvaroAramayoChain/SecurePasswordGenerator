"""Tests for the command-line interface."""

import string

import pytest

from passgen import MAX_LENGTH, MIN_LENGTH, SYMBOLS
from passgen.cli import EXIT_INTERRUPTED, EXIT_INVALID_INPUT, EXIT_SUCCESS, main


def _raise_eof(_prompt: str) -> str:
    """Stand-in for ``input`` that simulates a closed standard input.

    Args:
        _prompt: The prompt text, ignored.

    Raises:
        EOFError: Always.
    """
    raise EOFError


def test_length_flag_prints_password(capsys: pytest.CaptureFixture[str]) -> None:
    """``--length`` generates a password of that length without prompting."""
    assert main(["--length", "20"]) == EXIT_SUCCESS
    assert len(capsys.readouterr().out.strip()) == 20


def test_no_symbols_flag_excludes_symbols(capsys: pytest.CaptureFixture[str]) -> None:
    """``--no-symbols`` produces a password without special characters."""
    assert main(["-l", "64", "--no-symbols"]) == EXIT_SUCCESS
    assert not set(capsys.readouterr().out.strip()) & set(SYMBOLS)


def test_prompts_for_length_when_flag_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without ``--length`` the CLI asks for it with ``input()``."""
    monkeypatch.setattr("builtins.input", lambda _prompt: "12")
    assert main(["--no-letters", "--no-symbols"]) == EXIT_SUCCESS
    password = capsys.readouterr().out.strip()
    assert len(password) == 12 and set(password) <= set(string.digits)


def test_non_numeric_input_shows_friendly_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Non-numeric interactive input yields a readable error, not a traceback."""
    monkeypatch.setattr("builtins.input", lambda _prompt: "abc")
    assert main([]) == EXIT_INVALID_INPUT
    assert "not a whole number" in capsys.readouterr().err


def test_out_of_range_length_shows_friendly_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An out-of-range length reports the allowed bounds."""
    assert main(["--length", str(MIN_LENGTH - 1)]) == EXIT_INVALID_INPUT
    assert f"between {MIN_LENGTH} and {MAX_LENGTH}" in capsys.readouterr().err


def test_all_categories_disabled_shows_friendly_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Disabling every category reports a clear error."""
    code = main(["-l", "16", "--no-letters", "--no-digits", "--no-symbols"])
    assert code == EXIT_INVALID_INPUT
    assert "At least one character set" in capsys.readouterr().err


def test_invalid_length_flag_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    """A non-numeric ``--length`` value is rejected by argparse with exit code 2."""
    with pytest.raises(SystemExit) as excinfo:
        main(["--length", "ten"])
    assert excinfo.value.code == EXIT_INVALID_INPUT
    assert "not a whole number" in capsys.readouterr().err


def test_closed_stdin_exits_gracefully(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Closed standard input (EOF) exits cleanly with the interrupted code."""
    monkeypatch.setattr("builtins.input", _raise_eof)
    assert main([]) == EXIT_INTERRUPTED
    assert "Cancelled" in capsys.readouterr().err
