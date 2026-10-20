"""Entry point for running the password generator from a source checkout.

``python main.py`` opens the desktop GUI; ``python main.py --cli [options]``
runs the command-line interface (all remaining options go to the CLI).
"""

import sys
from collections.abc import Sequence
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
CLI_FLAG = "--cli"
EXIT_MISSING_GUI = 1
MISSING_GUI_MESSAGE = (
    "The desktop GUI needs PySide6. Install it with:\n"
    '    pip install -e ".[gui]"\n'
    "or run the command-line version with:\n"
    "    python main.py --cli"
)


def _ensure_src_on_path() -> None:
    """Make the ``src`` directory importable when the package is not installed."""
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))


def run_cli(argv: Sequence[str]) -> int:
    """Run the command-line interface.

    Args:
        argv: Arguments for the CLI, without the program name.

    Returns:
        The CLI's exit code.
    """
    from passgen.cli import main

    return main(list(argv))


def run_gui() -> int:
    """Run the desktop GUI, explaining how to install it if PySide6 is missing.

    Returns:
        The GUI's exit code, or ``EXIT_MISSING_GUI``.
    """
    try:
        from passgen.gui import run_gui as start_gui
    except ImportError:
        print(MISSING_GUI_MESSAGE, file=sys.stderr)
        return EXIT_MISSING_GUI
    return start_gui()


def run(argv: Sequence[str] | None = None) -> int:
    """Dispatch to the CLI (``--cli``) or the GUI (default).

    Args:
        argv: Arguments without the program name; ``None`` uses ``sys.argv``.

    Returns:
        The process exit code.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    _ensure_src_on_path()
    if CLI_FLAG in args:
        args.remove(CLI_FLAG)
        return run_cli(args)
    return run_gui()


if __name__ == "__main__":
    sys.exit(run())
