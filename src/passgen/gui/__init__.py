"""PySide6 desktop interface for the password generator.

Requires the optional ``gui`` extra: ``pip install -e ".[gui]"``.
"""

from passgen.gui.app import run_gui, self_test
from passgen.strings import SUPPORTED_LANGUAGES, get_text

__all__ = ["SUPPORTED_LANGUAGES", "get_text", "run_gui", "self_test"]
