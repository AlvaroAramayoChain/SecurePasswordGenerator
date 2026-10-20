"""Secure random password generator.

Public API::

    from passgen import generate_password

    password = generate_password(16, use_symbols=False)
"""

from passgen.exceptions import (
    InvalidLengthError,
    InvalidLengthTypeError,
    NoCharacterSetSelectedError,
    PasswordGeneratorError,
)
from passgen.generator import (
    DEFAULT_LENGTH,
    MAX_LENGTH,
    MIN_LENGTH,
    SYMBOLS,
    generate_password,
)

__version__ = "1.0.0"

__all__ = [
    "DEFAULT_LENGTH",
    "MAX_LENGTH",
    "MIN_LENGTH",
    "SYMBOLS",
    "InvalidLengthError",
    "InvalidLengthTypeError",
    "NoCharacterSetSelectedError",
    "PasswordGeneratorError",
    "generate_password",
    "__version__",
]
