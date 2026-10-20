"""Tests for the password generator backend."""

import itertools
import string

import pytest

from passgen import (
    MAX_LENGTH,
    MIN_LENGTH,
    SYMBOLS,
    InvalidLengthError,
    InvalidLengthTypeError,
    NoCharacterSetSelectedError,
    PasswordGeneratorError,
    generate_password,
)

CATEGORY_CHARS = {
    "uppercase": set(string.ascii_uppercase),
    "lowercase": set(string.ascii_lowercase),
    "digits": set(string.digits),
    "symbols": set(SYMBOLS),
}

# Every non-empty combination of (use_letters, use_digits, use_symbols).
VALID_FLAG_COMBINATIONS = [
    flags for flags in itertools.product([True, False], repeat=3) if any(flags)
]

# Enough repetitions to make a flaky "lucky" pass very unlikely.
REPETITIONS = 200


def _expected_categories(
    use_letters: bool, use_digits: bool, use_symbols: bool
) -> set[str]:
    """Return the category names that the given flags enable.

    Args:
        use_letters: Whether letters are enabled.
        use_digits: Whether digits are enabled.
        use_symbols: Whether symbols are enabled.

    Returns:
        The names of the enabled categories, as keys of ``CATEGORY_CHARS``.
    """
    enabled = set()
    if use_letters:
        enabled |= {"uppercase", "lowercase"}
    if use_digits:
        enabled.add("digits")
    if use_symbols:
        enabled.add("symbols")
    return enabled


@pytest.mark.parametrize("length", [MIN_LENGTH, 16, 64, MAX_LENGTH])
def test_password_has_requested_length(length: int) -> None:
    """The password has exactly the requested number of characters."""
    assert len(generate_password(length)) == length


@pytest.mark.parametrize("flags", VALID_FLAG_COMBINATIONS)
def test_every_selected_category_is_present(flags: tuple[bool, bool, bool]) -> None:
    """Each enabled category appears at least once, even at minimum length."""
    expected = _expected_categories(*flags)
    for _ in range(REPETITIONS):
        password = set(generate_password(MIN_LENGTH, *flags))
        for name in expected:
            assert password & CATEGORY_CHARS[name], f"missing {name}"


@pytest.mark.parametrize("flags", VALID_FLAG_COMBINATIONS)
def test_excluded_categories_are_absent(flags: tuple[bool, bool, bool]) -> None:
    """Disabled categories never contribute any character."""
    excluded = set(CATEGORY_CHARS) - _expected_categories(*flags)
    for _ in range(REPETITIONS):
        password = set(generate_password(MAX_LENGTH, *flags))
        for name in excluded:
            assert not password & CATEGORY_CHARS[name], f"unexpected {name}"


@pytest.mark.parametrize("length", [MIN_LENGTH - 1, 0, -5])
def test_length_below_minimum_raises(length: int) -> None:
    """Lengths below the minimum raise InvalidLengthError."""
    with pytest.raises(InvalidLengthError, match=str(MIN_LENGTH)):
        generate_password(length)


@pytest.mark.parametrize("length", [MAX_LENGTH + 1, 10_000])
def test_length_above_maximum_raises(length: int) -> None:
    """Lengths above the maximum raise InvalidLengthError."""
    with pytest.raises(InvalidLengthError, match=str(MAX_LENGTH)):
        generate_password(length)


@pytest.mark.parametrize("length", ["16", 16.0, None, True, [16]])
def test_non_integer_length_raises(length: object) -> None:
    """Non-integer lengths (including bool) raise InvalidLengthTypeError."""
    with pytest.raises(InvalidLengthTypeError, match="integer"):
        generate_password(length)  # type: ignore[arg-type]


def test_length_type_error_is_catchable_as_builtin_and_base() -> None:
    """The type error can be caught as TypeError and as the package base class."""
    with pytest.raises(TypeError):
        generate_password("16")  # type: ignore[arg-type]
    with pytest.raises(PasswordGeneratorError):
        generate_password("16")  # type: ignore[arg-type]


def test_no_categories_selected_raises() -> None:
    """Disabling every category raises NoCharacterSetSelectedError."""
    with pytest.raises(NoCharacterSetSelectedError):
        generate_password(16, use_letters=False, use_digits=False, use_symbols=False)


def test_consecutive_passwords_differ() -> None:
    """Two consecutive generations produce different passwords."""
    assert generate_password(32) != generate_password(32)


def test_invalid_length_error_exposes_details() -> None:
    """InvalidLengthError keeps the rejected value and bounds for callers (e.g. a GUI)."""
    with pytest.raises(InvalidLengthError) as excinfo:
        generate_password(MAX_LENGTH + 1)
    error = excinfo.value
    assert (error.length, error.min_length, error.max_length) == (
        MAX_LENGTH + 1,
        MIN_LENGTH,
        MAX_LENGTH,
    )
