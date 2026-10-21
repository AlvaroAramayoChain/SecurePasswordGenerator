"""Shared pytest fixtures, including a cleanly torn-down Qt application."""

import gc
import os
from collections.abc import Iterator

import pytest


def _teardown_qt(app: object) -> None:
    """Stop timers, delete every top-level widget and flush pending Qt events.

    Leaving live widgets and running timers until interpreter shutdown makes
    Qt objects die in an arbitrary order; this releases them deterministically
    while the application still exists.

    Args:
        app: The ``QApplication`` instance created for the test session.
    """
    from PySide6.QtCore import QCoreApplication, QEvent, QTimer
    from PySide6.QtWidgets import QApplication

    for widget in QApplication.topLevelWidgets():
        for timer in widget.findChildren(QTimer):
            timer.stop()
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    gc.collect()


@pytest.fixture(scope="session")
def qapp() -> Iterator[object]:
    """Create one offscreen ``QApplication`` for the whole test session.

    Skips the requesting test if PySide6 is not installed.

    Yields:
        The application instance; it is torn down after the last test.
    """
    pytest.importorskip("PySide6", reason="GUI extra not installed")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from passgen.gui.app import create_application

    app = create_application(["pytest"])
    yield app
    _teardown_qt(app)
