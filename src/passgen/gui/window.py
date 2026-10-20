"""The frameless, padlock-shaped main window and its ES | EN language toggle."""

import os

from PySide6.QtCore import QLocale, QPointF, QRect, QRectF, QSettings, Qt, Signal
from PySide6.QtGui import (
    QBitmap,
    QColor,
    QFont,
    QGuiApplication,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QLineEdit, QWidget

from passgen.gui import theme
from passgen.gui.controls import RoundButton, RoundButtonKind, RunButton, state_color
from passgen.gui.padlock import outset_path, paint_padlock, paint_padlock_in, silhouette_path
from passgen.gui.terminal import TerminalView, load_terminal_font
from passgen.session import Session, StepResult
from passgen.strings import SUPPORTED_LANGUAGES, get_text, resolve_language

TOGGLE_SEPARATOR = "|"


class LanguageToggle(QWidget):
    """A pill showing every language code (e.g. "ES | EN"), active one highlighted.

    Clicking a segment emits :attr:`language_selected` with that language code.

    Args:
        font: The font for the labels.
        parent: The parent widget.
    """

    language_selected = Signal(str)

    def __init__(self, font: QFont, parent: QWidget | None = None) -> None:
        """Create the toggle with no language active yet.

        Args:
            font: The font for the labels.
            parent: The parent widget.
        """
        super().__init__(parent)
        self._languages = SUPPORTED_LANGUAGES
        self._active = self._languages[0]
        self._hovered: int | None = None
        self._pressed: int | None = None
        self.setFont(font)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def active_language(self) -> str:
        """The highlighted language code."""
        return self._active

    def set_active_language(self, language: str) -> None:
        """Highlight ``language`` without emitting a signal.

        Args:
            language: A supported language code.
        """
        self._active = language
        self.update()

    def segment_rect(self, index: int) -> QRectF:
        """Return the clickable rectangle of one language segment.

        Args:
            index: The segment index.

        Returns:
            The segment rectangle in widget coordinates.
        """
        width = self.width() / len(self._languages)
        return QRectF(index * width, 0, width, self.height())

    def _segment_at(self, point: QPointF) -> int | None:
        """Return the segment index under ``point``, if any.

        Args:
            point: A position in widget coordinates.

        Returns:
            The segment index, or ``None`` outside the widget.
        """
        for index in range(len(self._languages)):
            if self.segment_rect(index).contains(point):
                return index
        return None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Track the hovered segment.

        Args:
            event: The mouse event.
        """
        self._hovered = self._segment_at(event.position())
        self.update()

    def leaveEvent(self, _event: object) -> None:
        """Clear the hover state.

        Args:
            _event: The leave event (unused).
        """
        self._hovered = None
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Remember the pressed segment.

        Args:
            event: The mouse event.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = self._segment_at(event.position())
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Select the segment if the press and release happened on it.

        Args:
            event: The mouse event.
        """
        released = self._segment_at(event.position())
        pressed, self._pressed = self._pressed, None
        self.update()
        if pressed is not None and pressed == released:
            self.language_selected.emit(self._languages[pressed])

    def paintEvent(self, _event: object) -> None:
        """Draw the pill, the highlighted segment, the labels and separators.

        Args:
            _event: The paint event (unused).
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pill = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        radius = pill.height() / 2
        painter.setPen(QPen(QColor(theme.NAVY), theme.ROUND_BUTTON_OUTLINE))
        painter.setBrush(QColor(theme.TOGGLE_BG))
        painter.drawRoundedRect(pill, radius, radius)
        for index, language in enumerate(self._languages):
            self._paint_segment(painter, index, language, radius)
        self._paint_separators(painter)

    def _paint_segment(self, painter: QPainter, index: int, language: str,
                       radius: float) -> None:
        """Draw one segment's highlight and label.

        Args:
            painter: The active painter.
            index: The segment index.
            language: The segment's language code.
            radius: The pill corner radius.
        """
        rect = self.segment_rect(index).adjusted(3, 3, -3, -3)
        active = language == self._active
        hovered, pressed = index == self._hovered, index == self._pressed
        if active or hovered or pressed:
            base = theme.TOGGLE_ACTIVE if active else theme.TOGGLE_BG
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(state_color(base, hovered, pressed))
            painter.drawRoundedRect(rect, radius, radius)
        painter.setPen(QColor(theme.TOGGLE_ACTIVE_TEXT if active else theme.TOGGLE_TEXT))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, language.upper())

    def _paint_separators(self, painter: QPainter) -> None:
        """Draw the "|" between segments.

        Args:
            painter: The active painter.
        """
        painter.setPen(QColor(theme.TOGGLE_TEXT))
        for index in range(1, len(self._languages)):
            left = self.segment_rect(index).left()
            painter.drawText(QRectF(left - self.height() / 2, 0, self.height(), self.height()),
                             Qt.AlignmentFlag.AlignCenter, TOGGLE_SEPARATOR)


def console_inner_rect() -> QRect:
    """Return the area inside the console frame, below the title bar.

    Returns:
        The rectangle that holds the terminal and the input row.
    """
    box = theme.CONSOLE
    return QRect(int(box.x) + theme.CONSOLE_BORDER,
                 int(box.y) + theme.TITLE_BAR_HEIGHT,
                 int(box.width) - 2 * theme.CONSOLE_BORDER,
                 int(box.height) - theme.TITLE_BAR_HEIGHT - theme.CONSOLE_BORDER)


def terminal_rect() -> QRect:
    """Return the terminal's geometry (including its scrollbar).

    Returns:
        The terminal rectangle.
    """
    inner = console_inner_rect()
    return inner.adjusted(0, 0, 0, -(theme.INPUT_ROW_HEIGHT + theme.ROW_GAP))


def input_rect() -> QRect:
    """Return the input field's geometry.

    Returns:
        The input field rectangle.
    """
    inner = console_inner_rect()
    top = inner.bottom() - theme.INPUT_ROW_HEIGHT + 1
    width = inner.width() - theme.RUN_BUTTON_WIDTH - theme.ROW_GAP
    return QRect(inner.left(), top, width, theme.INPUT_ROW_HEIGHT)


def run_button_rect() -> QRect:
    """Return the Run button's geometry.

    Returns:
        The Run button rectangle.
    """
    field = input_rect()
    return QRect(field.right() + 1 + theme.ROW_GAP, field.top(),
                 theme.RUN_BUTTON_WIDTH, theme.INPUT_ROW_HEIGHT)


def input_stylesheet() -> str:
    """Return the Qt stylesheet of the command input field.

    Returns:
        The stylesheet text.
    """
    return (
        f"QLineEdit {{ background: {theme.TERMINAL_BG}; color: {theme.TEXT_INPUT};"
        f" border: {theme.CONSOLE_OUTLINE}px solid {theme.NAVY};"
        f" border-radius: {theme.PANEL_RADIUS}px; padding: 0 {theme.TERMINAL_MARGIN}px;"
        f" selection-background-color: {theme.SELECTION_BG}; }}"
        f" QLineEdit:focus {{ border-color: {theme.FRAME_LIGHT}; }}"
    )


class PadlockWindow(QWidget):
    """The application window: a glossy padlock hosting the password console.

    Args:
        settings: Where to persist the language code. ``None`` uses the
            application's default ``QSettings``.
        opaque: Paint a solid backdrop instead of relying on translucency.
            ``None`` reads the ``PASSGEN_OPAQUE`` environment variable.
    """

    def __init__(self, settings: QSettings | None = None, opaque: bool | None = None) -> None:
        """Build the window, restore the language and start the guided flow.

        Args:
            settings: Where to persist the language code.
            opaque: Whether to paint a solid backdrop.
        """
        super().__init__()
        self._settings = settings if settings is not None else QSettings()
        self._opaque = opaque if opaque is not None else os.environ.get(theme.OPAQUE_ENV_VAR) == "1"
        self._configure_window()
        self._font = load_terminal_font(theme.TERMINAL_FONT_PX)
        self._build_children()
        self._connect_signals()
        stored = self._settings.value(theme.SETTINGS_LANGUAGE_KEY)
        language = resolve_language(stored, QLocale.system().name())
        self._session = Session(language)
        self._apply_language(language, persist=False)

    # --- Construction -------------------------------------------------------

    def _configure_window(self) -> None:
        """Set the frameless, translucent, fixed-size window attributes."""
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowMinimizeButtonHint)
        if not self._opaque:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT)
        self.setMask(self._shape_mask())

    def _shape_mask(self) -> QBitmap:
        """Build the input/clip mask from the padlock silhouette.

        The mask is grown by the outline width so its hard edge falls on fully
        transparent pixels: antialiased edges stay smooth, while clicks on the
        empty areas (including inside the shackle) go to the windows below.

        Returns:
            A monochrome bitmap of the window size.
        """
        bitmap = QBitmap(theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT)
        bitmap.fill(Qt.GlobalColor.color0)
        painter = QPainter(bitmap)
        painter.fillPath(outset_path(silhouette_path(), theme.MASK_MARGIN),
                         Qt.GlobalColor.color1)
        painter.end()
        return bitmap

    def _build_children(self) -> None:
        """Create the title buttons, language toggle, terminal and input row."""
        self.minimize_button = RoundButton(RoundButtonKind.MINIMIZE, self)
        self.maximize_button = RoundButton(RoundButtonKind.MAXIMIZE, self)
        self.close_button = RoundButton(RoundButtonKind.CLOSE, self)
        buttons = (self.minimize_button, self.maximize_button, self.close_button)
        for button, center_x in zip(buttons, theme.ROUND_BUTTON_CENTERS_X):
            button.move(center_x - button.width() // 2,
                        theme.ROUND_BUTTON_CENTER_Y - button.height() // 2)
        toggle_font = QFont(self._font)
        toggle_font.setPixelSize(theme.LANGUAGE_TOGGLE_FONT_PX)
        self.language_toggle = LanguageToggle(toggle_font, self)
        box = theme.LANGUAGE_TOGGLE
        self.language_toggle.setGeometry(int(box.x), int(box.y), int(box.width), int(box.height))
        self.terminal = TerminalView(self._font, self)
        self.terminal.setGeometry(terminal_rect())
        self.input = QLineEdit(self)
        self.input.setFont(self._font)
        self.input.setMaxLength(theme.MAX_INPUT_CHARS)
        self.input.setGeometry(input_rect())
        self.input.setStyleSheet(input_stylesheet())
        self.run_button = RunButton(self._font, self)
        self.run_button.setGeometry(run_button_rect())

    def _connect_signals(self) -> None:
        """Wire buttons, the input field and the language toggle."""
        self.minimize_button.clicked.connect(self.showMinimized)
        self.close_button.clicked.connect(self.close)
        self.run_button.clicked.connect(self.submit_input)
        self.input.returnPressed.connect(self.submit_input)
        self.input.textChanged.connect(self.terminal.set_prompt_text)
        self.language_toggle.language_selected.connect(self.set_language)

    # --- Behaviour ----------------------------------------------------------

    @property
    def language(self) -> str:
        """The current interface language code."""
        return self._session.language

    def set_language(self, language: str) -> None:
        """Switch the interface language, persist it and restart the flow.

        Args:
            language: A supported language code.
        """
        self._apply_language(language, persist=True)

    def submit_input(self) -> None:
        """Send the input field's text to the session and show the response."""
        text = self.input.text()
        self.input.clear()
        self._show(self._session.submit(text))
        self.input.setFocus()

    def _apply_language(self, language: str, persist: bool) -> None:
        """Update every visible text and restart the guided flow.

        Args:
            language: A supported language code.
            persist: Whether to save the code in the settings.
        """
        if persist:
            self._settings.setValue(theme.SETTINGS_LANGUAGE_KEY, language)
        result = self._session.switch_language(language)
        self.setWindowTitle(get_text(language, "window_title"))
        self.input.setPlaceholderText(get_text(language, "placeholder"))
        self.run_button.setText(get_text(language, "run_button"))
        self.run_button.setToolTip(get_text(language, "tooltip_run"))
        self.minimize_button.setToolTip(get_text(language, "tooltip_minimize"))
        self.maximize_button.setToolTip(get_text(language, "tooltip_maximize"))
        self.close_button.setToolTip(get_text(language, "tooltip_close"))
        self.language_toggle.setToolTip(get_text(language, "tooltip_language"))
        self.language_toggle.set_active_language(language)
        self.input.clear()
        self.terminal.clear_output()
        self._show(result)
        self.update()
        self.input.setFocus()

    def _show(self, result: StepResult) -> None:
        """Display a session step and perform its clipboard request.

        Args:
            result: The step returned by the session.
        """
        self.terminal.append_lines(result.lines)
        if result.copy_text is not None:
            QGuiApplication.clipboard().setText(result.copy_text)

    # --- Events -------------------------------------------------------------

    def showEvent(self, event: object) -> None:
        """Focus the input field whenever the window is shown.

        Args:
            event: The show event.
        """
        super().showEvent(event)
        self.input.setFocus()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start a system move when the padlock itself is dragged.

        Child widgets handle their own clicks, so this only fires on the
        padlock body, the shackle and the console title bar.

        Args:
            event: The mouse event.
        """
        handle = self.windowHandle()
        if event.button() == Qt.MouseButton.LeftButton and handle is not None:
            handle.startSystemMove()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, _event: object) -> None:
        """Paint the padlock and the console frame behind the child widgets.

        Args:
            _event: The paint event (unused).
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._opaque:
            painter.fillRect(self.rect(), QColor(theme.FALLBACK_BACKGROUND))
        paint_padlock(painter)
        self._paint_console(painter)

    def _paint_console(self, painter: QPainter) -> None:
        """Paint the blue retro window: frame, title bar, icon and title.

        Args:
            painter: The active painter.
        """
        box = theme.CONSOLE
        frame = QRectF(box.x, box.y, box.width, box.height)
        painter.setPen(QPen(QColor(theme.NAVY), theme.CONSOLE_OUTLINE))
        painter.setBrush(QColor(theme.FRAME_BLUE))
        painter.drawRoundedRect(frame, theme.CONSOLE_RADIUS, theme.CONSOLE_RADIUS)
        title = QRectF(box.x + theme.CONSOLE_OUTLINE, box.y + theme.CONSOLE_OUTLINE,
                       box.width - 2 * theme.CONSOLE_OUTLINE,
                       theme.TITLE_BAR_HEIGHT - theme.CONSOLE_OUTLINE)
        gradient = QLinearGradient(title.topLeft(), title.bottomLeft())
        gradient.setColorAt(0.0, QColor(theme.TITLE_TOP))
        gradient.setColorAt(1.0, QColor(theme.TITLE_BOTTOM))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        radius = theme.CONSOLE_RADIUS - theme.CONSOLE_OUTLINE
        painter.drawRoundedRect(title, radius, radius)
        painter.fillRect(title.adjusted(0, radius, 0, 0), gradient)
        painter.setPen(QPen(QColor(theme.FRAME_LIGHT), 1))
        painter.drawLine(QPointF(title.left() + radius, title.top() + 1),
                         QPointF(title.right() - radius, title.top() + 1))
        self._paint_title(painter, title)
        self._paint_panel_bevels(painter)

    def _paint_title(self, painter: QPainter, title: QRectF) -> None:
        """Draw the lock icon and the "Password Console" title.

        Args:
            painter: The active painter.
            title: The title bar rectangle.
        """
        icon = QRectF(title.left() + theme.TITLE_PADDING,
                      title.center().y() - theme.TITLE_ICON_SIZE / 2,
                      theme.TITLE_ICON_SIZE, theme.TITLE_ICON_SIZE)
        paint_padlock_in(painter, icon)
        font = QFont(self._font)
        font.setPixelSize(theme.TITLE_FONT_PX)
        painter.setFont(font)
        painter.setPen(QColor(theme.TITLE_TEXT))
        text_rect = title.adjusted(icon.right() - title.left() + theme.TITLE_PADDING, 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter,
                         get_text(self.language, "console_title"))

    def _paint_panel_bevels(self, painter: QPainter) -> None:
        """Draw dark outlines around the terminal so it looks inset.

        Args:
            painter: The active painter.
        """
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(theme.NAVY), theme.CONSOLE_OUTLINE))
        outline = QRectF(terminal_rect()).adjusted(-1.5, -1.5, 1.5, 1.5)
        painter.drawRect(outline)
