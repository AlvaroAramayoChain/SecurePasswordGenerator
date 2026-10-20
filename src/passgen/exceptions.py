"""Custom exceptions raised by the password generator.

All exceptions derive from :class:`PasswordGeneratorError`, so callers such as
a CLI or a GUI can catch every generator error with a single ``except`` clause.
"""


class PasswordGeneratorError(Exception):
    """Base class for every error raised by the ``passgen`` package."""


class InvalidLengthError(PasswordGeneratorError, ValueError):
    """Raised when the requested password length is outside the allowed range.

    Args:
        length: The rejected length value.
        min_length: The smallest accepted length.
        max_length: The largest accepted length.
    """

    def __init__(self, length: object, min_length: int, max_length: int) -> None:
        """Store the rejected value and the allowed bounds, then build the message.

        Args:
            length: The rejected length value.
            min_length: The smallest accepted length.
            max_length: The largest accepted length.
        """
        self.length = length
        self.min_length = min_length
        self.max_length = max_length
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        """Return the human-readable error message.

        Returns:
            A sentence describing the rejected length and the allowed range.
        """
        return (
            f"Password length must be between {self.min_length} and "
            f"{self.max_length} characters, got {self.length}."
        )


class InvalidLengthTypeError(InvalidLengthError, TypeError):
    """Raised when the requested password length is not an integer.

    It subclasses :class:`InvalidLengthError`, so catching that class also
    catches type problems, and :class:`TypeError` for idiomatic handling.
    """

    def _build_message(self) -> str:
        """Return the human-readable error message.

        Returns:
            A sentence describing the expected and the received type.
        """
        return (
            "Password length must be an integer, "
            f"got {type(self.length).__name__} ({self.length!r})."
        )


class NoCharacterSetSelectedError(PasswordGeneratorError, ValueError):
    """Raised when letters, digits and symbols are all disabled."""

    def __init__(self) -> None:
        """Build the error with a fixed, descriptive message."""
        super().__init__(
            "At least one character set (letters, digits or symbols) "
            "must be enabled."
        )
