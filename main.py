"""Entry point for running the password generator from a source checkout.

For now it launches the CLI; a desktop GUI will be wired in a later phase.
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"


def _ensure_src_on_path() -> None:
    """Make the ``src`` directory importable when the package is not installed."""
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))


def run() -> int:
    """Run the command-line interface.

    Returns:
        The process exit code returned by the CLI.
    """
    _ensure_src_on_path()
    from passgen.cli import main

    return main()


if __name__ == "__main__":
    sys.exit(run())
