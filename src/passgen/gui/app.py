"""Desktop application entry point."""

import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication

from passgen.gui import theme
from passgen.gui.padlock import render_icon
from passgen.gui.window import PadlockWindow

ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
BUNDLED_FONT_FAMILY = "VT323"


def application_icon() -> QIcon:
    """Build the window/taskbar icon from the padlock drawing.

    Returns:
        An icon with several pre-rendered sizes.
    """
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(render_icon(size))
    return icon


def create_application(argv: Sequence[str]) -> QApplication:
    """Create (or reuse) the Qt application with HiDPI and identity settings.

    Args:
        argv: Command-line arguments passed to Qt.

    Returns:
        The application instance.
    """
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(list(argv))
    app.setOrganizationName(theme.APP_ORGANIZATION)
    app.setApplicationName(theme.APP_NAME)
    app.setWindowIcon(application_icon())
    return app


def run_gui(argv: Sequence[str] | None = None) -> int:
    """Show the padlock window and run the Qt event loop.

    Args:
        argv: Command-line arguments for Qt; ``None`` uses ``sys.argv``.

    Returns:
        The application's exit code.
    """
    app = create_application(sys.argv if argv is None else argv)
    window = PadlockWindow()
    window.show()
    return app.exec()


def self_test(argv: Sequence[str] | None = None) -> int:
    """Build the window without showing it and verify the bundled assets.

    Used by the release workflow to check that a packaged app actually starts
    (run it with ``QT_QPA_PLATFORM=offscreen`` on headless machines). It uses a
    throwaway settings file so nothing is written to the user's settings.

    Args:
        argv: Command-line arguments for Qt; ``None`` uses ``sys.argv``.

    Returns:
        ``0`` if the window renders with the bundled font, otherwise ``1``.
    """
    create_application(sys.argv if argv is None else argv)
    with tempfile.TemporaryDirectory() as folder:
        settings = QSettings(str(Path(folder) / "settings.ini"), QSettings.Format.IniFormat)
        window = PadlockWindow(settings=settings)
        rendered = not window.grab().isNull()
        bundled_font = window.terminal.font().family() == BUNDLED_FONT_FAMILY
        window.close()
    ok = rendered and bundled_font
    print(f"self-test {'passed' if ok else 'failed'}: rendered={rendered}, "
          f"bundled_font={bundled_font}")
    return 0 if ok else 1


def main() -> int:
    """Console-script entry point for ``passgen-gui``.

    Returns:
        The application's exit code.
    """
    return run_gui()


if __name__ == "__main__":
    sys.exit(main())
