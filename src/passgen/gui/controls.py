"""Custom-painted buttons: the round title buttons and the green Run button."""

import math
from enum import Enum, auto

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QEnterEvent,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QAbstractButton, QWidget

from passgen.gui import theme

GLOSS_HEIGHT_RATIO = 0.55
GLOSS_WIDTH_RATIO = 0.7
GLOSS_ALPHA = 150
TRIANGLE_SIZE_RATIO = 0.42
CONTENT_SPACING = 8
# Restart glyph: a clockwise arc with a gap at the top-right; the arrowhead
# sits at the top and points right, like a classic "refresh" icon.
RESTART_ARC_START = 15.0
RESTART_ARC_SPAN = -295.0
RESTART_HEAD_RATIO = 0.7
QT_ANGLE_UNITS = 16  # QPainter.drawArc takes angles in 1/16 of a degree.


def state_color(base: str, hovered: bool, pressed: bool) -> QColor:
    """Return ``base`` adjusted for the hover/pressed state.

    Args:
        base: The normal ``#RRGGBB`` color.
        hovered: Whether the pointer is over the control.
        pressed: Whether the control is held down.

    Returns:
        A darker color when pressed, lighter when hovered, else ``base``.
    """
    color = QColor(base)
    if pressed:
        return color.darker(theme.PRESS_DARKEN)
    if hovered:
        return color.lighter(theme.HOVER_LIGHTEN)
    return color


class HoverButton(QAbstractButton):
    """Base class for painted buttons that repaint on hover changes.

    Args:
        parent: The parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the button with a pointing-hand cursor and no focus.

        Args:
            parent: The parent widget.
        """
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def enterEvent(self, event: QEnterEvent) -> None:
        """Repaint when the pointer enters.

        Args:
            event: The enter event.
        """
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: object) -> None:
        """Repaint when the pointer leaves.

        Args:
            event: The leave event.
        """
        self.update()
        super().leaveEvent(event)

    def is_hovered(self) -> bool:
        """Tell whether the pointer is over the button.

        Returns:
            ``True`` while hovered.
        """
        return self.underMouse()


class RoundButtonKind(Enum):
    """The three title buttons and their glyphs."""

    MINIMIZE = auto()
    RESTART = auto()
    CLOSE = auto()


ROUND_BUTTON_COLORS = {
    RoundButtonKind.MINIMIZE: (theme.MINIMIZE_COLOR, theme.GLYPH_LIGHT),
    RoundButtonKind.RESTART: (theme.RESTART_COLOR, theme.GLYPH_DARK),
    RoundButtonKind.CLOSE: (theme.CLOSE_COLOR, theme.GLYPH_LIGHT),
}


class RoundButton(HoverButton):
    """A glossy round title button (minimize, restart or close).

    Args:
        kind: Which button to draw.
        parent: The parent widget.
    """

    def __init__(self, kind: RoundButtonKind, parent: QWidget | None = None) -> None:
        """Create a round button of the given kind.

        Args:
            kind: Which button to draw.
            parent: The parent widget.
        """
        super().__init__(parent)
        self.kind = kind
        diameter = 2 * theme.ROUND_BUTTON_RADIUS + 2 * int(theme.ROUND_BUTTON_OUTLINE)
        self.setFixedSize(diameter, diameter)

    def sizeHint(self) -> QSize:
        """Return the fixed button size.

        Returns:
            The button's size.
        """
        return self.size()

    def paintEvent(self, _event: object) -> None:
        """Draw the outlined, glossy disc and its glyph.

        Args:
            _event: The paint event (unused).
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2)
        if self.isDown():
            center += QPointF(0, theme.PRESS_OFFSET)
        radius = theme.ROUND_BUTTON_RADIUS
        base, glyph = ROUND_BUTTON_COLORS[self.kind]
        fill = state_color(base, self.is_hovered(), self.isDown())
        gradient = QRadialGradient(center - QPointF(0, radius / 2), radius * 1.4)
        gradient.setColorAt(0.0, fill.lighter(theme.HOVER_LIGHTEN))
        gradient.setColorAt(1.0, fill.darker(theme.PRESS_DARKEN))
        painter.setPen(QPen(QColor(theme.NAVY), theme.ROUND_BUTTON_OUTLINE))
        painter.setBrush(gradient)
        painter.drawEllipse(center, radius, radius)
        _paint_gloss(painter, center, radius)
        self._paint_glyph(painter, center, radius * theme.ROUND_BUTTON_GLYPH_SCALE, glyph)

    def _paint_glyph(self, painter: QPainter, center: QPointF, half: float, color: str) -> None:
        """Draw the minimize bar, restart arrow or close cross.

        Args:
            painter: The active painter.
            center: The button center.
            half: Half the glyph's extent.
            color: The glyph color.
        """
        pen = QPen(QColor(color), theme.ROUND_BUTTON_GLYPH_WIDTH, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.kind is RoundButtonKind.MINIMIZE:
            painter.drawLine(center + QPointF(-half, 0), center + QPointF(half, 0))
        elif self.kind is RoundButtonKind.RESTART:
            _paint_restart_arrow(painter, center, half, QColor(color))
        else:
            painter.drawLine(center + QPointF(-half, -half), center + QPointF(half, half))
            painter.drawLine(center + QPointF(-half, half), center + QPointF(half, -half))


def _paint_restart_arrow(painter: QPainter, center: QPointF, radius: float, color: QColor) -> None:
    """Draw a circular arrow: an open arc ending in a filled arrowhead.

    Uses the painter's current pen for the arc. Angles follow Qt's convention
    (degrees, counter-clockwise from 3 o'clock).

    Args:
        painter: The active painter.
        center: The button center.
        radius: The arc radius.
        color: The arrowhead fill color.
    """
    arc = QRectF(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius)
    painter.drawArc(arc, int(RESTART_ARC_START * QT_ANGLE_UNITS),
                    int(RESTART_ARC_SPAN * QT_ANGLE_UNITS))
    end = math.radians(RESTART_ARC_START + RESTART_ARC_SPAN)
    tip_base = center + QPointF(radius * math.cos(end), -radius * math.sin(end))
    # Unit vectors (screen coordinates) along the sweep direction and outward.
    sweep = math.copysign(1.0, RESTART_ARC_SPAN)
    tangent = QPointF(-math.sin(end), -math.cos(end)) * sweep
    outward = QPointF(math.cos(end), -math.sin(end))
    head = radius * RESTART_HEAD_RATIO
    arrowhead = QPainterPath(tip_base + tangent * head)
    arrowhead.lineTo(tip_base + outward * head)
    arrowhead.lineTo(tip_base - outward * head)
    arrowhead.closeSubpath()
    painter.save()
    painter.setPen(QPen(color, theme.ROUND_BUTTON_GLYPH_WIDTH / 2, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(color)
    painter.drawPath(arrowhead)
    painter.restore()


def _paint_gloss(painter: QPainter, center: QPointF, radius: float) -> None:
    """Draw a soft white highlight on the upper half of a disc.

    Args:
        painter: The active painter.
        center: The disc center.
        radius: The disc radius.
    """
    gloss = QColor(theme.GLOSS)
    gloss.setAlpha(GLOSS_ALPHA)
    width = 2 * radius * GLOSS_WIDTH_RATIO
    height = radius * GLOSS_HEIGHT_RATIO
    rect = QRectF(center.x() - width / 2, center.y() - radius * 0.85, width, height)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gloss)
    painter.drawEllipse(rect)


class RunButton(HoverButton):
    """The dark-blue "Run" button with a green play triangle.

    Args:
        font: The font for the label.
        parent: The parent widget.
    """

    def __init__(self, font: QFont, parent: QWidget | None = None) -> None:
        """Create the button.

        Args:
            font: The font for the label.
            parent: The parent widget.
        """
        super().__init__(parent)
        self.setFont(font)

    def paintEvent(self, _event: object) -> None:
        """Draw the bevelled panel, the play triangle and the label.

        Args:
            _event: The paint event (unused).
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        hovered, pressed = self.is_hovered(), self.isDown()
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        offset = theme.PRESS_OFFSET if pressed else 0.0
        self._paint_panel(painter, rect, hovered, pressed)
        triangle_size = rect.height() * TRIANGLE_SIZE_RATIO
        text_width = painter.fontMetrics().horizontalAdvance(self.text())
        content = triangle_size + CONTENT_SPACING + text_width
        left = rect.center().x() - content / 2
        middle = rect.center().y() + offset
        painter.setPen(QPen(QColor(theme.NAVY), 1))
        painter.setBrush(state_color(theme.RUN_TRIANGLE, hovered, pressed))
        triangle = QPainterPath(QPointF(left, middle - triangle_size / 2))
        triangle.lineTo(left + triangle_size, middle)
        triangle.lineTo(left, middle + triangle_size / 2)
        triangle.closeSubpath()
        painter.drawPath(triangle)
        painter.setPen(QColor(theme.RUN_TEXT))
        text_rect = QRectF(left + triangle_size + CONTENT_SPACING, rect.top() + offset,
                           text_width + 1, rect.height())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, self.text())

    def _paint_panel(self, painter: QPainter, rect: QRectF, hovered: bool, pressed: bool) -> None:
        """Draw the button's rounded, bevelled background.

        Args:
            painter: The active painter.
            rect: The button rectangle.
            hovered: Whether the pointer is over the button.
            pressed: Whether the button is held down.
        """
        top = state_color(theme.RUN_TOP, hovered, pressed)
        bottom = state_color(theme.RUN_BOTTOM, hovered, pressed)
        if pressed:
            top, bottom = bottom, top
        painter.setPen(QPen(QColor(theme.NAVY), theme.CONSOLE_OUTLINE))
        painter.setBrush(_vertical(rect, top, bottom))
        painter.drawRoundedRect(rect, theme.PANEL_RADIUS, theme.PANEL_RADIUS)
        painter.setPen(QPen(QColor(theme.FRAME_LIGHT), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        inner = rect.adjusted(theme.CONSOLE_OUTLINE, theme.CONSOLE_OUTLINE,
                              -theme.CONSOLE_OUTLINE, -theme.CONSOLE_OUTLINE)
        painter.drawRoundedRect(inner, theme.PANEL_RADIUS / 2, theme.PANEL_RADIUS / 2)


def _vertical(rect: QRectF, top: QColor, bottom: QColor) -> QLinearGradient:
    """Create a vertical gradient spanning ``rect``.

    Args:
        rect: The area the gradient covers.
        top: The color at the top edge.
        bottom: The color at the bottom edge.

    Returns:
        The gradient.
    """
    gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    gradient.setColorAt(0.0, top)
    gradient.setColorAt(1.0, bottom)
    return gradient
