"""Vector drawing of the glossy Y2K padlock (shape, gradients, keyhole).

The same functions build the window silhouette, paint the window background,
draw the small title-bar icon and render the application icon files.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QPixmap,
)

from passgen.gui import theme

FULL_CIRCLE_DEGREES = 360
HALF_CIRCLE_DEGREES = 180
QUARTER_CIRCLE_DEGREES = 90
ICON_PADDING_RATIO = 0.04
ICON_KEYHOLE_SCALE = 3.2
GLOSS_INSET_RATIO = 1.6
GLOSS_SIDE_LENGTH = 70
GLOSS_TOP_GAP = 24
# Pixel-art sparkle: a small plus sign, offsets in sparkle-size units.
SPARKLE_OFFSETS = ((1.0, 0.0), (0.0, 1.0), (1.0, 1.0), (2.0, 1.0), (1.0, 2.0))
SHACKLE_GLOSS_START_DEGREES = 168
SHACKLE_GLOSS_SPAN_DEGREES = -70
SHACKLE_GLOSS_DEPTH = 0.3
SHACKLE_GLOSS_WIDTH = 0.14
KEYHOLE_HIGHLIGHT_OFFSET = 2.0
# Slightly wider than one pixel so neighbouring rings overlap without gaps.
RING_PEN_WIDTH = 1.6


def _shackle_u(radius: float) -> QPainterPath:
    """Build a filled "U" (arch plus straight legs) of the given radius.

    Args:
        radius: Distance from the arch center to the U's edge.

    Returns:
        The closed path of the U.
    """
    center_y = theme.SHACKLE_TOP + theme.SHACKLE_OUTER_RADIUS
    arch = QRectF(theme.CENTER_X - radius, center_y - radius, 2 * radius, 2 * radius)
    path = QPainterPath(QPointF(theme.CENTER_X - radius, theme.SHACKLE_LEG_BOTTOM))
    path.lineTo(theme.CENTER_X - radius, center_y)
    path.arcTo(arch, HALF_CIRCLE_DEGREES, -HALF_CIRCLE_DEGREES)
    path.lineTo(theme.CENTER_X + radius, theme.SHACKLE_LEG_BOTTOM)
    path.closeSubpath()
    return path


def shackle_path() -> QPainterPath:
    """Return the shackle as a ring-shaped path with an open center.

    Returns:
        The shackle path.
    """
    inner_radius = theme.SHACKLE_OUTER_RADIUS - theme.SHACKLE_THICKNESS
    return _shackle_u(theme.SHACKLE_OUTER_RADIUS).subtracted(_shackle_u(inner_radius))


def _bump_path() -> QPainterPath:
    """Return the raised hump on top of the body that holds the keyhole.

    Returns:
        A closed path whose base overlaps the body's top edge.
    """
    top = theme.BODY.y - theme.BUMP_HEIGHT
    base = theme.BODY.y + theme.BODY_RADIUS / 2
    base_left = theme.CENTER_X - theme.BUMP_BASE_HALF_WIDTH
    base_right = theme.CENTER_X + theme.BUMP_BASE_HALF_WIDTH
    top_left = theme.CENTER_X - theme.BUMP_TOP_HALF_WIDTH
    top_right = theme.CENTER_X + theme.BUMP_TOP_HALF_WIDTH
    path = QPainterPath(QPointF(base_left, base))
    path.lineTo(base_left, theme.BODY.y)
    path.cubicTo(top_left - theme.BUMP_HEIGHT / 2, theme.BODY.y,
                 top_left - theme.BUMP_HEIGHT / 2, top, top_left, top)
    path.lineTo(top_right, top)
    path.cubicTo(top_right + theme.BUMP_HEIGHT / 2, top,
                 top_right + theme.BUMP_HEIGHT / 2, theme.BODY.y, base_right, theme.BODY.y)
    path.lineTo(base_right, base)
    path.closeSubpath()
    return path


def body_path() -> QPainterPath:
    """Return the padlock body: a rounded rectangle plus the keyhole hump.

    Returns:
        The body path.
    """
    body = QPainterPath()
    box = theme.BODY
    body.addRoundedRect(QRectF(box.x, box.y, box.width, box.height),
                        theme.BODY_RADIUS, theme.BODY_RADIUS)
    return body.united(_bump_path()).simplified()


def silhouette_path() -> QPainterPath:
    """Return the full padlock outline (shackle plus body).

    Returns:
        The union of the shackle and body paths.
    """
    return shackle_path().united(body_path()).simplified()


def keyhole_path() -> QPainterPath:
    """Return the keyhole: a circle on top of a flared stem.

    Returns:
        The keyhole path.
    """
    path = QPainterPath()
    path.addEllipse(QPointF(theme.CENTER_X, theme.KEYHOLE_CENTER_Y),
                    theme.KEYHOLE_RADIUS, theme.KEYHOLE_RADIUS)
    stem = QPainterPath(QPointF(theme.CENTER_X - theme.KEYHOLE_STEM_TOP_HALF_WIDTH,
                                theme.KEYHOLE_CENTER_Y))
    stem.lineTo(theme.CENTER_X + theme.KEYHOLE_STEM_TOP_HALF_WIDTH, theme.KEYHOLE_CENTER_Y)
    stem.lineTo(theme.CENTER_X + theme.KEYHOLE_STEM_BOTTOM_HALF_WIDTH, theme.KEYHOLE_STEM_BOTTOM)
    stem.lineTo(theme.CENTER_X - theme.KEYHOLE_STEM_BOTTOM_HALF_WIDTH, theme.KEYHOLE_STEM_BOTTOM)
    stem.closeSubpath()
    return path.united(stem).simplified()


def inset_path(path: QPainterPath, distance: float) -> QPainterPath:
    """Shrink a closed path by ``distance`` on every side.

    Args:
        path: The closed path to shrink.
        distance: How far to move the edge inwards.

    Returns:
        The inset path.
    """
    return path.subtracted(_stroke(path, 2 * distance)).simplified()


def outset_path(path: QPainterPath, distance: float) -> QPainterPath:
    """Grow a closed path by ``distance`` on every side.

    Args:
        path: The closed path to grow.
        distance: How far to move the edge outwards.

    Returns:
        The grown path.
    """
    return path.united(_stroke(path, 2 * distance)).simplified()


def _stroke(path: QPainterPath, width: float) -> QPainterPath:
    """Return the area covered by stroking ``path`` with a round pen.

    Args:
        path: The path to stroke.
        width: The pen width.

    Returns:
        The stroke outline as a fillable path.
    """
    stroker = QPainterPathStroker()
    stroker.setWidth(width)
    stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
    return stroker.createStroke(path)


def _vertical_gradient(top: float, bottom: float, stops: tuple[tuple[float, str], ...]
                       ) -> QLinearGradient:
    """Create a top-to-bottom linear gradient.

    Args:
        top: The y coordinate where the gradient starts.
        bottom: The y coordinate where it ends.
        stops: ``(position, color)`` pairs with positions in ``[0, 1]``.

    Returns:
        The configured gradient.
    """
    gradient = QLinearGradient(0, top, 0, bottom)
    for position, color in stops:
        gradient.setColorAt(position, QColor(color))
    return gradient


def _horizontal_gradient(left: float, right: float, stops: tuple[tuple[float, str], ...]
                         ) -> QLinearGradient:
    """Create a left-to-right linear gradient.

    Args:
        left: The x coordinate where the gradient starts.
        right: The x coordinate where it ends.
        stops: ``(position, color)`` pairs with positions in ``[0, 1]``.

    Returns:
        The configured gradient.
    """
    gradient = QLinearGradient(left, 0, right, 0)
    for position, color in stops:
        gradient.setColorAt(position, QColor(color))
    return gradient


TUBE_STOPS = (
    (0.0, theme.GOLD_SHADOW),
    (0.18, theme.GOLD_DARK),
    (0.38, theme.GOLD_HIGHLIGHT),
    (0.55, theme.GOLD_LIGHT),
    (0.82, theme.GOLD_MID),
    (1.0, theme.GOLD_SHADOW),
)
BODY_STOPS = (
    (0.0, theme.GOLD_LIGHT),
    (0.45, theme.GOLD_MID),
    (1.0, theme.GOLD_DARK),
)
BEVEL_STOPS = (
    (0.0, theme.GOLD_HIGHLIGHT),
    (0.5, theme.GOLD_LIGHT),
    (1.0, theme.GOLD_SHADOW),
)


def _paint_shackle(painter: QPainter) -> None:
    """Paint the shackle as a cylindrical golden tube.

    The arch uses a radial-looking ring of strokes; the legs use horizontal
    gradients so each leg reads as a round bar.

    Args:
        painter: An active painter in window coordinates.
    """
    shackle = shackle_path()
    outer = theme.SHACKLE_OUTER_RADIUS
    center_y = theme.SHACKLE_TOP + outer
    painter.save()
    painter.setClipPath(shackle)
    # Concentric one-pixel rings approximate a radial tube gradient on the arch.
    steps = int(theme.SHACKLE_THICKNESS)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for step in range(steps + 1):
        painter.setPen(QPen(_color_at(TUBE_STOPS, step / steps), RING_PEN_WIDTH))
        painter.drawEllipse(QPointF(theme.CENTER_X, center_y), outer - step, outer - step)
    for left in (theme.CENTER_X - outer, theme.CENTER_X + outer - theme.SHACKLE_THICKNESS):
        leg = QRectF(left, center_y, theme.SHACKLE_THICKNESS,
                     theme.SHACKLE_LEG_BOTTOM - center_y)
        stops = TUBE_STOPS if left < theme.CENTER_X else _mirror(TUBE_STOPS)
        painter.fillRect(leg, _horizontal_gradient(leg.left(), leg.right(), stops))
    painter.restore()
    _paint_shackle_gloss(painter, center_y)


def _mirror(stops: tuple[tuple[float, str], ...]) -> tuple[tuple[float, str], ...]:
    """Reverse gradient stops so the highlight faces the other side.

    Args:
        stops: ``(position, color)`` pairs.

    Returns:
        The mirrored stops.
    """
    return tuple((1.0 - position, color) for position, color in reversed(stops))


def _color_at(stops: tuple[tuple[float, str], ...], position: float) -> QColor:
    """Interpolate a color along gradient stops.

    Args:
        stops: Sorted ``(position, color)`` pairs.
        position: A value in ``[0, 1]``.

    Returns:
        The interpolated color.
    """
    for (start, start_color), (end, end_color) in zip(stops, stops[1:]):
        if start <= position <= end:
            ratio = (position - start) / (end - start) if end > start else 0.0
            first, second = QColor(start_color), QColor(end_color)
            return QColor.fromRgbF(
                first.redF() + (second.redF() - first.redF()) * ratio,
                first.greenF() + (second.greenF() - first.greenF()) * ratio,
                first.blueF() + (second.blueF() - first.blueF()) * ratio,
            )
    return QColor(stops[-1][1])


def _paint_shackle_gloss(painter: QPainter, center_y: float) -> None:
    """Add a white specular streak along the upper-left of the shackle.

    Args:
        painter: An active painter in window coordinates.
        center_y: The y coordinate of the arch center.
    """
    radius = theme.SHACKLE_OUTER_RADIUS - theme.SHACKLE_THICKNESS * SHACKLE_GLOSS_DEPTH
    arch = QRectF(theme.CENTER_X - radius, center_y - radius, 2 * radius, 2 * radius)
    streak = QPainterPath()
    streak.arcMoveTo(arch, SHACKLE_GLOSS_START_DEGREES)
    streak.arcTo(arch, SHACKLE_GLOSS_START_DEGREES, SHACKLE_GLOSS_SPAN_DEGREES)
    gloss = QColor(theme.GLOSS)
    gloss.setAlpha(theme.GLOSS_ALPHA)
    pen = QPen(gloss, theme.SHACKLE_THICKNESS * SHACKLE_GLOSS_WIDTH, Qt.PenStyle.SolidLine,
               Qt.PenCapStyle.RoundCap)
    painter.strokePath(streak, pen)


def _paint_body(painter: QPainter) -> None:
    """Paint the body with a bevelled edge, inner line and gloss.

    Args:
        painter: An active painter in window coordinates.
    """
    body = body_path()
    top = theme.BODY.y - theme.BUMP_HEIGHT
    painter.fillPath(body, _vertical_gradient(top, theme.BODY.bottom, BEVEL_STOPS))
    inner = inset_path(body, theme.BEVEL_WIDTH)
    painter.fillPath(inner, _vertical_gradient(top, theme.BODY.bottom, BODY_STOPS))
    painter.strokePath(inner, QPen(QColor(theme.GOLD_DARK), theme.INNER_LINE_WIDTH))
    _paint_body_gloss(painter)


def _paint_body_gloss(painter: QPainter) -> None:
    """Add glossy highlights and pixel sparkles to the body's upper-left.

    Args:
        painter: An active painter in window coordinates.
    """
    gloss = QColor(theme.GLOSS)
    gloss.setAlpha(theme.GLOSS_ALPHA)
    box = theme.BODY
    # Sit just inside the bevel so the white reads against the yellow face.
    inset = theme.BEVEL_WIDTH * GLOSS_INSET_RATIO
    radius = theme.BODY_RADIUS - inset
    corner = QRectF(box.x + inset, box.y + inset, 2 * radius, 2 * radius)
    streak = QPainterPath(QPointF(box.x + inset, box.y + theme.BODY_RADIUS + GLOSS_SIDE_LENGTH))
    streak.lineTo(box.x + inset, box.y + theme.BODY_RADIUS)
    streak.arcTo(corner, HALF_CIRCLE_DEGREES, -QUARTER_CIRCLE_DEGREES)
    streak.lineTo(theme.CENTER_X - theme.BUMP_BASE_HALF_WIDTH - GLOSS_TOP_GAP, box.y + inset)
    pen = QPen(gloss, theme.GLOSS_WIDTH, Qt.PenStyle.SolidLine,
               Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.strokePath(streak, pen)
    size = theme.SPARKLE_SIZE
    origin = QPointF(box.x + inset + 2 * size, box.y + inset + 2 * size)
    for dx, dy in SPARKLE_OFFSETS:
        painter.fillRect(QRectF(origin.x() + dx * size, origin.y() + dy * size, size, size), gloss)


def _paint_keyhole(painter: QPainter) -> None:
    """Paint the keyhole with a carved highlight underneath.

    Args:
        painter: An active painter in window coordinates.
    """
    keyhole = keyhole_path()
    painter.save()
    painter.translate(0, KEYHOLE_HIGHLIGHT_OFFSET)
    painter.fillPath(keyhole, QColor(theme.GOLD_HIGHLIGHT))
    painter.restore()
    painter.fillPath(keyhole, QColor(theme.KEYHOLE))


def paint_padlock(painter: QPainter) -> None:
    """Paint the complete padlock (outline, shackle, body, keyhole).

    Args:
        painter: An active painter in window coordinates.
    """
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    outline = QPen(QColor(theme.OUTLINE), theme.OUTLINE_WIDTH, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.strokePath(shackle_path(), outline)
    painter.strokePath(body_path(), outline)
    _paint_shackle(painter)
    _paint_body(painter)
    _paint_keyhole(painter)


def silhouette_bounds() -> QRectF:
    """Return the bounding box of the padlock including its outline.

    Returns:
        The bounds in window coordinates.
    """
    half_outline = theme.OUTLINE_WIDTH / 2
    return silhouette_path().boundingRect().adjusted(
        -half_outline, -half_outline, half_outline, half_outline
    )


def paint_padlock_in(painter: QPainter, target: QRectF, large_keyhole: bool = False) -> None:
    """Paint the padlock scaled to fit, centered, inside ``target``.

    Args:
        painter: An active painter.
        target: The rectangle to fit the padlock into.
        large_keyhole: Add a big keyhole in the body center, which keeps the
            design recognizable at small icon sizes.
    """
    bounds = silhouette_bounds()
    scale = min(target.width() / bounds.width(), target.height() / bounds.height())
    painter.save()
    painter.translate(target.center())
    painter.scale(scale, scale)
    painter.translate(-bounds.center())
    paint_padlock(painter)
    if large_keyhole:
        _paint_large_keyhole(painter)
    painter.restore()


def _paint_large_keyhole(painter: QPainter) -> None:
    """Paint an enlarged copy of the keyhole in the middle of the body.

    Args:
        painter: An active painter in window coordinates.
    """
    keyhole_mid_y = (theme.KEYHOLE_CENTER_Y + theme.KEYHOLE_STEM_BOTTOM) / 2
    body_mid_y = theme.BODY.y + theme.BODY.height / 2
    painter.save()
    painter.translate(theme.CENTER_X, body_mid_y)
    painter.scale(ICON_KEYHOLE_SCALE, ICON_KEYHOLE_SCALE)
    painter.translate(-theme.CENTER_X, -keyhole_mid_y)
    _paint_keyhole(painter)
    painter.restore()


def render_icon(size: int) -> QPixmap:
    """Render the padlock as a square, transparent application icon.

    Args:
        size: The icon edge length in pixels.

    Returns:
        A ``size`` x ``size`` pixmap.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    padding = size * ICON_PADDING_RATIO
    painter = QPainter(pixmap)
    paint_padlock_in(painter, QRectF(padding, padding, size - 2 * padding, size - 2 * padding),
                     large_keyhole=True)
    painter.end()
    return pixmap


def solid_brush(color: str) -> QBrush:
    """Return a solid brush for a hex color.

    Args:
        color: A ``#RRGGBB`` color string.

    Returns:
        The brush.
    """
    return QBrush(QColor(color))
