"""Cryptographically secure password generation.

This module contains no user-interface code: it only builds passwords and
raises exceptions, so it can be reused by a CLI, a GUI or any other caller.
"""

import secrets
import string
from typing import Final

from passgen.exceptions import (
    InvalidLengthError,
    InvalidLengthTypeError,
    NoCharacterSetSelectedError,
)

MIN_LENGTH: Final[int] = 8
MAX_LENGTH: Final[int] = 128
DEFAULT_LENGTH: Final[int] = 16

UPPERCASE: Final[str] = string.ascii_uppercase
LOWERCASE: Final[str] = string.ascii_lowercase
DIGITS: Final[str] = string.digits
SYMBOLS: Final[str] = "!@#$%^&*()-_=+[]{};:,.<>?"


def generate_password(
    length: int = DEFAULT_LENGTH,
    use_letters: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    """Generate a cryptographically secure random password.

    The password is guaranteed to contain at least one character from every
    selected category. Enabling letters selects two categories: uppercase and
    lowercase.

    Args:
        length: Number of characters, between ``MIN_LENGTH`` and ``MAX_LENGTH``.
        use_letters: Include uppercase and lowercase ASCII letters.
        use_digits: Include the digits 0-9.
        use_symbols: Include the special characters in ``SYMBOLS``.

    Returns:
        The generated password.

    Raises:
        InvalidLengthTypeError: If ``length`` is not an integer.
        InvalidLengthError: If ``length`` is outside the allowed range.
        NoCharacterSetSelectedError: If every category is disabled.
    """
    _validate_length(length)
    categories = _select_categories(use_letters, use_digits, use_symbols)

    # Each selected category contributes one secrets.choice() pick, so every
    # category is guaranteed to appear. The remaining characters come from the
    # combined pool, also via secrets.choice(), so they stay uniform and
    # independent. Finally, a CSPRNG-backed shuffle moves the guaranteed
    # characters to unpredictable positions; without it they would always sit
    # at the start of the password and leak structure to an attacker.
    characters = _pick_one_from_each(categories)
    characters += _pick_from_pool("".join(categories), length - len(characters))
    _secure_shuffle(characters)
    return "".join(characters)


def _validate_length(length: object) -> None:
    """Check that ``length`` is an integer within the allowed range.

    Args:
        length: The value to validate.

    Raises:
        InvalidLengthTypeError: If ``length`` is not an ``int`` (``bool`` is
            rejected too, even though it subclasses ``int``).
        InvalidLengthError: If ``length`` is below ``MIN_LENGTH`` or above
            ``MAX_LENGTH``.
    """
    if isinstance(length, bool) or not isinstance(length, int):
        raise InvalidLengthTypeError(length, MIN_LENGTH, MAX_LENGTH)
    if not MIN_LENGTH <= length <= MAX_LENGTH:
        raise InvalidLengthError(length, MIN_LENGTH, MAX_LENGTH)


def _select_categories(
    use_letters: bool, use_digits: bool, use_symbols: bool
) -> tuple[str, ...]:
    """Return the character categories enabled by the given flags.

    Args:
        use_letters: Enable the uppercase and lowercase categories.
        use_digits: Enable the digits category.
        use_symbols: Enable the symbols category.

    Returns:
        A tuple with one string of characters per enabled category.

    Raises:
        NoCharacterSetSelectedError: If no category is enabled.
    """
    categories: list[str] = []
    if use_letters:
        categories += [UPPERCASE, LOWERCASE]
    if use_digits:
        categories.append(DIGITS)
    if use_symbols:
        categories.append(SYMBOLS)
    if not categories:
        raise NoCharacterSetSelectedError()
    return tuple(categories)


def _pick_one_from_each(categories: tuple[str, ...]) -> list[str]:
    """Pick one secure random character from every category.

    Args:
        categories: The character categories to draw from.

    Returns:
        A list with exactly one character per category, in category order.
    """
    return [secrets.choice(category) for category in categories]


def _pick_from_pool(pool: str, count: int) -> list[str]:
    """Pick ``count`` secure random characters from ``pool``.

    Args:
        pool: The characters to draw from.
        count: How many characters to draw.

    Returns:
        A list of ``count`` characters, drawn independently and uniformly.
    """
    return [secrets.choice(pool) for _ in range(count)]


def _secure_shuffle(characters: list[str]) -> None:
    """Shuffle ``characters`` in place using the operating system's CSPRNG.

    Args:
        characters: The list to shuffle. It is modified in place.
    """
    secrets.SystemRandom().shuffle(characters)
