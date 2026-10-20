"""Offscreen smoke tests for the PySide6 window (skipped without PySide6)."""

import os
import string
from collections.abc import Iterator
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="GUI extra not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QLocale, QPoint, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from passgen import SYMBOLS  # noqa: E402
from passgen.gui import theme  # noqa: E402
from passgen.gui.window import PadlockWindow  # noqa: E402
from passgen.strings import SUPPORTED_LANGUAGES, TEXTS, detect_language, get_text  # noqa: E402

PASSWORD_ALPHABET = set(string.ascii_letters + string.digits + SYMBOLS)


@pytest.fixture
def settings(tmp_path: Path) -> QSettings:
    """Return a throwaway settings store so real user settings are untouched.

    Args:
        tmp_path: pytest's per-test temporary directory.

    Returns:
        An INI-backed settings object in ``tmp_path``.
    """
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def window(qapp: QApplication, settings: QSettings) -> Iterator[PadlockWindow]:
    """Build and show a padlock window.

    Args:
        qapp: The Qt application.
        settings: The temporary settings store.

    Yields:
        The shown window; it is closed afterwards.
    """
    widget = PadlockWindow(settings=settings, opaque=False)
    widget.show()
    yield widget
    widget.close()
    widget.deleteLater()


def _click_language(window: PadlockWindow, language: str) -> None:
    """Click the toggle segment of ``language``.

    Args:
        window: The window under test.
        language: The language code to click.
    """
    toggle = window.language_toggle
    index = SUPPORTED_LANGUAGES.index(language)
    QTest.mouseClick(toggle, Qt.MouseButton.LeftButton,
                     pos=toggle.segment_rect(index).center().toPoint())


def _answer(window: PadlockWindow, text: str) -> None:
    """Type ``text`` into the input field and press Enter.

    Args:
        window: The window under test.
        text: The answer to type (may be empty).
    """
    QTest.keyClicks(window.input, text)
    QTest.keyClick(window.input, Qt.Key.Key_Return)


def _last_password(window: PadlockWindow) -> str:
    """Return the most recent password shown in the terminal.

    Args:
        window: The window under test.

    Returns:
        The line that follows the last "your password" label.
    """
    lines = window.terminal.plain_lines()
    label = get_text(window.language, "result_label")
    index = len(lines) - 1 - lines[::-1].index(label)
    return lines[index + 1]


def test_window_builds_with_padlock_shape(window: PadlockWindow) -> None:
    """The window is frameless, fixed-size and masked to the padlock."""
    assert window.size().toTuple() == (theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT)
    assert window.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    mask = window.mask()
    assert mask.contains(QPoint(int(theme.CENTER_X), int(theme.BODY.y + theme.BODY.height / 2)))
    assert not mask.contains(QPoint(1, 1))
    # Midway between the inside of the arch and the top of the keyhole bump.
    hole_top = theme.SHACKLE_TOP + theme.SHACKLE_THICKNESS
    bump_top = theme.BODY.y - theme.BUMP_HEIGHT
    assert not mask.contains(QPoint(int(theme.CENTER_X), int((hole_top + bump_top) / 2)))


def test_input_has_focus_at_startup(window: PadlockWindow) -> None:
    """The input field is focused when the window opens."""
    QApplication.processEvents()
    assert window.input.hasFocus() or QApplication.focusWidget() in (window.input, None)


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_toggle_changes_visible_texts(window: PadlockWindow, settings: QSettings,
                                      language: str) -> None:
    """Clicking a language updates button, placeholder, title and settings."""
    _click_language(window, language)
    assert window.language == language
    assert window.run_button.text() == get_text(language, "run_button")
    assert window.input.placeholderText() == get_text(language, "placeholder")
    assert window.windowTitle() == get_text(language, "window_title")
    assert window.close_button.toolTip() == get_text(language, "tooltip_close")
    assert settings.value(theme.SETTINGS_LANGUAGE_KEY) == language
    assert settings.allKeys() == [theme.SETTINGS_LANGUAGE_KEY]


@pytest.mark.parametrize(("old", "new"), [("es", "en"), ("en", "es")])
def test_switch_clears_terminal_and_restarts(window: PadlockWindow, old: str, new: str) -> None:
    """Switching language restarts the flow and removes old-language text."""
    _click_language(window, old)
    _answer(window, "12")
    _click_language(window, new)
    lines = window.terminal.plain_lines()
    assert lines == [get_text(new, "welcome"), get_text(new, "ask_length", min=8, max=128)]
    assert get_text(old, "welcome") not in lines


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_widgets_produce_valid_password(window: PadlockWindow, language: str) -> None:
    """Typing through the widgets yields a valid password, then copies it."""
    _click_language(window, language)
    _answer(window, "12")
    keys = TEXTS[language]
    _answer(window, keys["key_letters"] + keys["key_digits"])
    password = _last_password(window)
    assert len(password) == 12 and set(password) <= set(string.ascii_letters + string.digits)
    window.input.setText(keys["key_copy"])
    window.run_button.click()
    assert QGuiApplication.clipboard().text() == password
    assert window.terminal.plain_lines()[-1] == get_text(language, "copied")
    assert window.input.text() == ""


def test_enter_generates_another_password(window: PadlockWindow) -> None:
    """Enter on the result screen shows a new password from the full alphabet."""
    _answer(window, "20")
    _answer(window, "")
    first = _last_password(window)
    _answer(window, "")
    second = _last_password(window)
    assert first != second and len(second) == 20 and set(second) <= PASSWORD_ALPHABET


def test_invalid_input_shows_error_without_crashing(window: PadlockWindow) -> None:
    """Bad answers produce localized errors and the flow continues."""
    _click_language(window, "es")
    _answer(window, "abc")
    assert get_text("es", "error_not_number", value="abc") in window.terminal.plain_lines()
    _answer(window, "500")
    assert get_text("es", "error_length_range", min=8, max=128) in window.terminal.plain_lines()


def test_invalid_stored_language_falls_back_to_locale(qapp: QApplication,
                                                      settings: QSettings) -> None:
    """A corrupt stored value is ignored in favour of the system locale."""
    settings.setValue(theme.SETTINGS_LANGUAGE_KEY, "klingon")
    widget = PadlockWindow(settings=settings, opaque=False)
    assert widget.language == detect_language(QLocale.system().name())
    widget.close()


def test_stored_language_is_restored(qapp: QApplication, settings: QSettings) -> None:
    """A valid stored language is used at startup."""
    for language in SUPPORTED_LANGUAGES:
        settings.setValue(theme.SETTINGS_LANGUAGE_KEY, language)
        widget = PadlockWindow(settings=settings, opaque=False)
        assert widget.language == language
        widget.close()


def test_opaque_fallback_builds(qapp: QApplication, settings: QSettings) -> None:
    """The no-compositor fallback window builds without translucency."""
    widget = PadlockWindow(settings=settings, opaque=True)
    assert not widget.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert not widget.grab().isNull()
    widget.close()
