"""Command-line interface for the password generator.

If ``--length`` is omitted, the user is asked for it interactively. All user
interaction lives here; the backend in :mod:`passgen.generator` stays UI-free.
"""

import argparse
import sys
from collections.abc import Sequence

from passgen.exceptions import PasswordGeneratorError
from passgen.generator import MAX_LENGTH, MIN_LENGTH, generate_password

EXIT_SUCCESS = 0
EXIT_INVALID_INPUT = 2
EXIT_INTERRUPTED = 130

LENGTH_PROMPT = f"Password length ({MIN_LENGTH}-{MAX_LENGTH}): "


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI.

    Returns:
        A configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="passgen",
        description="Generate a cryptographically secure random password.",
        epilog="Example: passgen --length 20 --no-symbols",
    )
    parser.add_argument(
        "-l",
        "--length",
        type=parse_length,
        help=f"password length ({MIN_LENGTH}-{MAX_LENGTH}); "
        "asked interactively if omitted",
    )
    parser.add_argument(
        "--no-letters", action="store_true", help="exclude letters (A-Z, a-z)"
    )
    parser.add_argument("--no-digits", action="store_true", help="exclude digits (0-9)")
    parser.add_argument(
        "--no-symbols", action="store_true", help="exclude special characters"
    )
    return parser


def parse_length(text: str) -> int:
    """Convert user-provided text into an integer length.

    Range checks are left to the backend so the rules live in one place.

    Args:
        text: The raw text typed by the user.

    Returns:
        The parsed integer.

    Raises:
        argparse.ArgumentTypeError: If ``text`` is not a whole number. When
            raised while parsing ``--length``, argparse turns it into a clean
            usage error.
    """
    try:
        return int(text.strip())
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"'{text}' is not a whole number. Please enter a number such as 16."
        ) from None


def prompt_for_length() -> int:
    """Ask the user for the password length on standard input.

    Returns:
        The length entered by the user.

    Raises:
        argparse.ArgumentTypeError: If the input is not a whole number.
        EOFError: If standard input is closed.
    """
    return parse_length(input(LENGTH_PROMPT))


def print_error(message: str) -> None:
    """Print a friendly error message to standard error.

    Args:
        message: The message to show.
    """
    print(f"Error: {message}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Command-line arguments without the program name. ``None`` uses
            ``sys.argv[1:]``.

    Returns:
        The process exit code.
    """
    args = build_parser().parse_args(argv)
    try:
        length = args.length if args.length is not None else prompt_for_length()
        password = generate_password(
            length,
            use_letters=not args.no_letters,
            use_digits=not args.no_digits,
            use_symbols=not args.no_symbols,
        )
    except (argparse.ArgumentTypeError, PasswordGeneratorError) as error:
        print_error(str(error))
        return EXIT_INVALID_INPUT
    except (KeyboardInterrupt, EOFError):
        print_error("Cancelled by user.")
        return EXIT_INTERRUPTED
    print(password)
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
