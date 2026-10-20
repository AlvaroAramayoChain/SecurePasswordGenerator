"""Desktop application entry point."""

import sys
from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication

from passgen.gui import theme
from passgen.gui.padlock import render_icon
from passgen.gui.window import PadlockWindow

ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


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


def main() -> int:
    """Console-script entry point for ``passgen-gui``.

    Returns:
        The application's exit code.
    """
    return run_gui()


if __name__ == "__main__":
    sys.exit(main())
