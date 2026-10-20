"""The black retro terminal: colored plain-text output, blinking cursor and scrollbar."""

from collections.abc import Iterable
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QFrame,
    QPlainTextEdit,
    QScrollBar,
    QStyle,
    QStyleFactory,
    QStyleOptionSlider,
    QWidget,
)

from passgen.generator import SYMBOLS
from passgen.gui import theme
from passgen.gui.controls import state_color
from passgen.session import Line, LineKind
from passgen.strings import TEXTS

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
SCROLL_STYLE_NAME = "Fusion"
ARROW_SIZE_RATIO = 0.32
HANDLE_INSET = 2

LINE_COLORS = {
    LineKind.OUTPUT: theme.TEXT_OUTPUT,
    LineKind.ECHO: theme.TEXT_INPUT,
    LineKind.ERROR: theme.TEXT_ERROR,
    LineKind.PASSWORD: theme.TEXT_PASSWORD,
}


def required_characters() -> str:
    """Return every character the terminal font must be able to draw.

    Returns:
        All characters used by the localized texts, the password alphabet and
        the prompt marker.
    """
    texts = "".join(value for language in TEXTS.values() for value in language.values())
    ascii_printable = "".join(chr(code) for code in range(ord(" "), ord("~") + 1))
    return "".join(sorted(set(texts + ascii_printable + SYMBOLS + theme.PROMPT_MARKER)))


def missing_glyphs(font: QFont, characters: str) -> str:
    """Return the characters that ``font`` cannot render itself.

    Args:
        font: The font to check (without fallback substitution).
        characters: The characters to look for.

    Returns:
        The unsupported characters, in input order.
    """
    metrics = QFontMetrics(font)
    return "".join(char for char in characters if not metrics.inFontUcs4(ord(char)))


def load_terminal_font(pixel_size: int) -> QFont:
    """Load the bundled VT323 font, falling back to the system monospace font.

    The fallback is used if the font file cannot be loaded or if it lacks any
    glyph needed by the interface (for example ``¿``, ``¡``, ``ñ`` or accents).

    Args:
        pixel_size: The desired font size in pixels.

    Returns:
        The font to use for the terminal and controls.
    """
    font_id = QFontDatabase.addApplicationFont(str(ASSETS_DIR / theme.FONT_FILE))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    if families:
        font = QFont(families[0])
        font.setPixelSize(pixel_size)
        if not missing_glyphs(font, required_characters()):
            return font
    fallback = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    fallback.setPixelSize(pixel_size)
    return fallback


def text_format(color: str) -> QTextCharFormat:
    """Return a character format with the given foreground color.

    Args:
        color: A ``#RRGGBB`` color.

    Returns:
        The format.
    """
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    return fmt


class RetroScrollBar(QScrollBar):
    """A vertical scrollbar painted in the light-blue Y2K style with arrow buttons.

    The Fusion style provides the hit-testing geometry (arrows at both ends),
    and this class paints every part itself.

    Args:
        parent: The parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the scrollbar with a fixed width.

        Args:
            parent: The parent widget.
        """
        super().__init__(Qt.Orientation.Vertical, parent)
        self._style = QStyleFactory.create(SCROLL_STYLE_NAME)
        self.setStyle(self._style)
        self.setFixedWidth(theme.SCROLLBAR_WIDTH)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _event: object) -> None:
        """Paint the track, the handle and both arrow buttons.

        Args:
            _event: The paint event (unused).
        """
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.SCROLL_TRACK))
        self._paint_handle(painter, option)
        for control, pointing_up in ((QStyle.SubControl.SC_ScrollBarSubLine, True),
                                     (QStyle.SubControl.SC_ScrollBarAddLine, False)):
            self._paint_arrow_button(painter, option, control, pointing_up)
        painter.setPen(QPen(QColor(theme.NAVY), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5))

    def _subcontrol_rect(self, option: QStyleOptionSlider, control: QStyle.SubControl) -> QRectF:
        """Return the rectangle of a scrollbar part.

        Args:
            option: The scrollbar's style option.
            control: The part to locate.

        Returns:
            The part's rectangle in widget coordinates.
        """
        return QRectF(self.style().subControlRect(
            QStyle.ComplexControl.CC_ScrollBar, option, control, self))

    def _is_active(self, option: QStyleOptionSlider, control: QStyle.SubControl) -> bool:
        """Tell whether a part is currently pressed.

        Args:
            option: The scrollbar's style option.
            control: The part to check.

        Returns:
            ``True`` if the part is being pressed.
        """
        sunken = bool(option.state & QStyle.StateFlag.State_Sunken)
        return sunken and bool(option.activeSubControls & control)

    def _paint_handle(self, painter: QPainter, option: QStyleOptionSlider) -> None:
        """Paint the draggable handle.

        Args:
            painter: The active painter.
            option: The scrollbar's style option.
        """
        rect = self._subcontrol_rect(option, QStyle.SubControl.SC_ScrollBarSlider)
        rect = rect.adjusted(HANDLE_INSET, 0, -HANDLE_INSET, 0)
        hovered = rect.contains(QPointF(self.mapFromGlobal(self.cursor().pos())))
        color = state_color(theme.SCROLL_HANDLE, hovered, self.isSliderDown())
        painter.setPen(QPen(QColor(theme.NAVY), 1))
        painter.setBrush(color)
        painter.drawRoundedRect(rect, HANDLE_INSET, HANDLE_INSET)

    def _paint_arrow_button(self, painter: QPainter, option: QStyleOptionSlider,
                            control: QStyle.SubControl, pointing_up: bool) -> None:
        """Paint one arrow button.

        Args:
            painter: The active painter.
            option: The scrollbar's style option.
            control: Which arrow sub-control to paint.
            pointing_up: Direction of the arrow.
        """
        rect = self._subcontrol_rect(option, control)
        pressed = self._is_active(option, control)
        painter.setPen(QPen(QColor(theme.NAVY), 1))
        painter.setBrush(state_color(theme.SCROLL_BUTTON, False, pressed))
        painter.drawRect(rect.adjusted(0.5, 0.5, -0.5, -0.5))
        half = rect.width() * ARROW_SIZE_RATIO
        center = rect.center()
        direction = -1 if pointing_up else 1
        arrow = QPainterPath(QPointF(center.x() - half, center.y() - direction * half / 2))
        arrow.lineTo(center.x() + half, center.y() - direction * half / 2)
        arrow.lineTo(center.x(), center.y() + direction * half / 2)
        arrow.closeSubpath()
        painter.fillPath(arrow, QColor(theme.SCROLL_ARROW))


class TerminalView(QPlainTextEdit):
    """Read-only colored text output ending with a blinking ``>>>`` prompt line.

    The last block of the document is always the prompt: the marker, a live
    mirror of what the user is typing, and a block cursor.

    Args:
        font: The monospace font to use.
        parent: The parent widget.
    """

    def __init__(self, font: QFont, parent: QWidget | None = None) -> None:
        """Create the terminal and start the cursor blink timer.

        Args:
            font: The monospace font to use.
            parent: The parent widget.
        """
        super().__init__(parent)
        self._prompt_text = ""
        self._cursor_visible = True
        self._configure(font)
        self._blink = QTimer(self)
        self._blink.setInterval(theme.CURSOR_BLINK_MS)
        self._blink.timeout.connect(self._toggle_cursor)
        self._blink.start()
        self._render_prompt()

    def _configure(self, font: QFont) -> None:
        """Apply font, colors, scrollbar and read-only behaviour.

        Args:
            font: The monospace font to use.
        """
        self.setFont(font)
        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollBar(RetroScrollBar(self))
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.document().setDocumentMargin(theme.TERMINAL_MARGIN)
        self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        self.setStyleSheet(
            f"QPlainTextEdit {{ background: {theme.TERMINAL_BG}; color: {theme.TEXT_OUTPUT};"
            f" selection-background-color: {theme.SELECTION_BG}; border: none; }}"
        )

    def plain_lines(self) -> list[str]:
        """Return the visible text, one string per line, without the prompt.

        Returns:
            The output lines.
        """
        return self.toPlainText().split("\n")[:-1]

    def clear_output(self) -> None:
        """Remove every line and reset the prompt."""
        self.clear()
        self._prompt_text = ""
        self._render_prompt()

    def append_lines(self, lines: Iterable[Line]) -> None:
        """Insert lines above the prompt and scroll to the bottom.

        Args:
            lines: The lines to show, in order.
        """
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        for line in lines:
            if line.kind is LineKind.ECHO:
                cursor.insertText(theme.PROMPT_MARKER, text_format(theme.TEXT_INPUT))
            cursor.insertText(line.text, text_format(LINE_COLORS[line.kind]))
            cursor.insertBlock()
        self.scroll_to_bottom()

    def set_prompt_text(self, text: str) -> None:
        """Mirror the user's in-progress input on the prompt line.

        Args:
            text: The current content of the input field.
        """
        self._prompt_text = text
        self._cursor_visible = True
        self._render_prompt()
        self.scroll_to_bottom()

    def scroll_to_bottom(self) -> None:
        """Scroll so the prompt line is visible."""
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _toggle_cursor(self) -> None:
        """Blink the block cursor."""
        self._cursor_visible = not self._cursor_visible
        self._render_prompt()

    def _render_prompt(self) -> None:
        """Redraw the last block: marker, mirrored input and block cursor."""
        bar = self.verticalScrollBar()
        position = bar.value()
        at_bottom = position >= bar.maximum()
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock,
                            QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(theme.PROMPT_MARKER + self._prompt_text, text_format(theme.TEXT_INPUT))
        block_cursor = text_format(theme.TEXT_INPUT)
        if self._cursor_visible:
            block_cursor.setBackground(QColor(theme.CURSOR))
        cursor.insertText(" ", block_cursor)
        bar.setValue(bar.maximum() if at_bottom else position)
