"""Render the README demos, the social preview and the app icons from the live GUI code.

Usage::

    python tools/make_assets.py            # everything below
    python tools/make_assets.py --demo     # docs/demo-<lang>.gif
    python tools/make_assets.py --social   # docs/social-preview.png
    python tools/make_assets.py --icons    # src/passgen/gui/assets/icon.*

Runs with the offscreen Qt platform, so no display is needed. Requires the
``gui`` extra plus Pillow (included in the ``build`` extra). The passwords shown
are freshly generated throwaway values.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image  # noqa: E402
from PySide6.QtCore import QPointF, QRectF, QSettings, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtTest import QTest  # noqa: E402

from passgen.gui import theme  # noqa: E402
from passgen.gui.app import create_application  # noqa: E402
from passgen.gui.padlock import render_icon  # noqa: E402
from passgen.gui.terminal import load_terminal_font, missing_glyphs  # noqa: E402
from passgen.gui.window import PadlockWindow  # noqa: E402
from passgen.strings import TEXTS  # noqa: E402

DOCS_DIR = ROOT / "docs"
ASSETS_DIR = ROOT / "src" / "passgen" / "gui" / "assets"
DEMO_LANGUAGES = ("es", "en")
DEMO_LENGTH = "16"
TYPE_DELAY_MS = 220
SHORT_PAUSE_MS = 1600
LONG_PAUSE_MS = 2650
PRESS_FRAME_MS = 300
GIF_COLORS = 255
PALETTE_BUTTONS_BOX = (360, 230, 464, 264)  # round title buttons, window coords
PALETTE_BUTTONS_REPEAT = 4
TRANSPARENT_INDEX = 255
ALPHA_THRESHOLD = 128
PNG_ICON_SIZE = 512
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)

# Social preview: laid out in 1280x640 logical pixels, painted at 2x.
SOCIAL_PATH = DOCS_DIR / "social-preview.png"
SOCIAL_WIDTH = 1280
SOCIAL_HEIGHT = 640
SOCIAL_SUPERSAMPLE = 2
SOCIAL_SAFE_MARGIN = 80
SOCIAL_LANGUAGE = "en"
SOCIAL_MAX_BYTES = 1_000_000
SOCIAL_TITLE_LINES = ("Secure", "Password", "Generator")
SOCIAL_SUBTITLE = "Random, secure passwords on your desktop"
SOCIAL_TEXT_GAP = 56
SOCIAL_TITLE_MAX_PX = 112
SOCIAL_SUBTITLE_PX = 34
SOCIAL_LINE_SPACING = 0.92
SOCIAL_SUBTITLE_GAP = 26
SOCIAL_TITLE_OUTLINE = 6
SOCIAL_CURSOR_WIDTH_RATIO = 0.5
SOCIAL_GRID_STEP = 40
SOCIAL_GRID_ALPHA = 22
SOCIAL_GLOW_ALPHA = 70
SOCIAL_BG_TOP = "#0B1C5C"
SOCIAL_BG_BOTTOM = "#03050B"

Frame = tuple[Image.Image, int]


def to_pillow(image: QImage) -> Image.Image:
    """Convert a Qt image to an RGBA Pillow image.

    Args:
        image: The Qt image (any format).

    Returns:
        A copy of the image as RGBA.
    """
    rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
    data = bytes(rgba.constBits())
    return Image.frombuffer("RGBA", (rgba.width(), rgba.height()), data, "raw", "RGBA",
                            rgba.bytesPerLine(), 1).copy()


class DemoRecorder:
    """Drive a real window through the guided flow and capture frames.

    Args:
        window: The window to drive (already shown).
    """

    def __init__(self, window: PadlockWindow) -> None:
        """Start with no frames.

        Args:
            window: The window to drive.
        """
        self.window = window
        self.frames: list[Frame] = []

    def snap(self, duration_ms: int) -> None:
        """Capture the current window image and how long to show it.

        Args:
            duration_ms: Display time of this frame in the GIF.
        """
        self.frames.append((to_pillow(self.window.grab().toImage()), duration_ms))

    def pause(self, total_ms: int) -> None:
        """Hold the current screen, capturing each cursor blink.

        The event loop runs between frames, so the real blink timer toggles
        the cursor exactly as it does on screen.

        Args:
            total_ms: Approximate total time to hold.
        """
        for _ in range(max(1, total_ms // theme.CURSOR_BLINK_MS)):
            self.snap(theme.CURSOR_BLINK_MS)
            QTest.qWait(theme.CURSOR_BLINK_MS)

    def type_text(self, text: str) -> None:
        """Type ``text`` one key at a time into the input field.

        Args:
            text: The characters to type.
        """
        for char in text:
            QTest.keyClicks(self.window.input, char)
            self.snap(TYPE_DELAY_MS)

    def press_enter(self) -> None:
        """Submit the input field with the Enter key."""
        QTest.keyClick(self.window.input, Qt.Key.Key_Return)

    def click_restart(self) -> None:
        """Show the restart button pressed for a moment, then click it."""
        button = self.window.restart_button
        button.setDown(True)
        self.snap(PRESS_FRAME_MS)
        button.setDown(False)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)


def record_demo(language: str, settings: QSettings) -> list[Frame]:
    """Record the guided flow: length, types, password, another password, then restart.

    Args:
        language: The interface language to show.
        settings: A throwaway settings store.

    Returns:
        The captured frames with their durations.
    """
    window = PadlockWindow(settings=settings, opaque=False)
    window.set_language(language)
    window.show()
    recorder = DemoRecorder(window)
    keys = TEXTS[language]
    recorder.pause(SHORT_PAUSE_MS)
    recorder.type_text(DEMO_LENGTH)
    recorder.press_enter()
    recorder.pause(SHORT_PAUSE_MS)
    recorder.type_text(keys["key_letters"] + keys["key_digits"])
    recorder.press_enter()
    recorder.pause(LONG_PAUSE_MS)
    recorder.press_enter()
    recorder.pause(LONG_PAUSE_MS)
    recorder.click_restart()
    recorder.pause(SHORT_PAUSE_MS)
    window.close()
    return recorder.frames


def build_palette(frames: list[Frame]) -> Image.Image:
    """Build one shared palette from the first and last frames.

    A shared palette keeps colors stable between frames and lets the GIF
    encoder store only the pixels that change.

    Args:
        frames: The captured frames.

    Returns:
        A palette image with ``GIF_COLORS`` colors.
    """
    first, last = frames[0][0].convert("RGB"), frames[-1][0].convert("RGB")
    # The small round buttons (red, blue, yellow) are a tiny share of the
    # pixels; repeating their strip gives them enough palette entries.
    buttons = first.crop(PALETTE_BUTTONS_BOX)
    strip_height = buttons.height * PALETTE_BUTTONS_REPEAT
    sheet = Image.new("RGB", (first.width, first.height * 2 + strip_height))
    sheet.paste(first, (0, 0))
    sheet.paste(last, (0, first.height))
    for row in range(PALETTE_BUTTONS_REPEAT):
        for column in range(first.width // buttons.width):
            sheet.paste(buttons, (column * buttons.width,
                                  first.height * 2 + row * buttons.height))
    return sheet.quantize(colors=GIF_COLORS, method=Image.Quantize.MEDIANCUT)


def to_gif_frame(frame: Image.Image, palette: Image.Image) -> Image.Image:
    """Map an RGBA frame onto the palette with 1-bit transparency.

    Args:
        frame: The RGBA frame.
        palette: The shared palette image.

    Returns:
        A palette-mode frame where transparent pixels use ``TRANSPARENT_INDEX``.
    """
    indexed = frame.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE)
    transparent = frame.getchannel("A").point(lambda alpha: 255 if alpha < ALPHA_THRESHOLD else 0)
    indexed.paste(TRANSPARENT_INDEX, mask=transparent.convert("1"))
    return indexed


def save_gif(frames: list[Frame], target: Path) -> None:
    """Write the frames as an endlessly looping, transparent GIF.

    Args:
        frames: The captured frames with their durations.
        target: The GIF file to write.
    """
    palette = build_palette(frames)
    images = [to_gif_frame(image, palette) for image, _ in frames]
    images[0].save(target, save_all=True, append_images=images[1:],
                   duration=[duration for _, duration in frames], loop=0,
                   transparency=TRANSPARENT_INDEX, disposal=1, optimize=False)


def make_demos() -> None:
    """Write ``docs/demo-<language>.gif`` for each demo language."""
    DOCS_DIR.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        settings = QSettings(str(Path(folder) / "settings.ini"), QSettings.Format.IniFormat)
        for language in DEMO_LANGUAGES:
            target = DOCS_DIR / f"demo-{language}.gif"
            frames = record_demo(language, settings)
            save_gif(frames, target)
            size_kb = target.stat().st_size / 1024
            print(f"wrote {target.relative_to(ROOT)} ({len(frames)} frames, {size_kb:.0f} KB)")


def render_window_pixmap(settings: QSettings, device_ratio: float) -> QPixmap:
    """Render the real window, showing a fresh demo password, at a given pixel ratio.

    Args:
        settings: A throwaway settings store.
        device_ratio: Device pixels per logical pixel for the vector rendering.

    Returns:
        A transparent pixmap of the window with ``device_ratio`` applied.
    """
    window = PadlockWindow(settings=settings, opaque=False)
    window.set_language(SOCIAL_LANGUAGE)
    window.show()
    for answer in (DEMO_LENGTH, ""):
        window.input.setText(answer)
        window.submit_input()
    pixmap = QPixmap(round(window.width() * device_ratio), round(window.height() * device_ratio))
    pixmap.setDevicePixelRatio(device_ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    window.render(pixmap)
    window.close()
    return pixmap


def paint_social_background(painter: QPainter, glow_center: QPointF) -> None:
    """Paint the opaque navy gradient, a faint Y2K grid and a soft golden glow.

    Args:
        painter: A painter in 1280x640 logical coordinates.
        glow_center: Where the glow behind the padlock is centered.
    """
    gradient = QLinearGradient(0, 0, 0, SOCIAL_HEIGHT)
    gradient.setColorAt(0.0, QColor(SOCIAL_BG_TOP))
    gradient.setColorAt(1.0, QColor(SOCIAL_BG_BOTTOM))
    painter.fillRect(QRectF(0, 0, SOCIAL_WIDTH, SOCIAL_HEIGHT), gradient)
    grid = QColor(theme.FRAME_LIGHT)
    grid.setAlpha(SOCIAL_GRID_ALPHA)
    painter.setPen(QPen(grid, 1))
    for x in range(0, SOCIAL_WIDTH + 1, SOCIAL_GRID_STEP):
        painter.drawLine(QPointF(x, 0), QPointF(x, SOCIAL_HEIGHT))
    for y in range(0, SOCIAL_HEIGHT + 1, SOCIAL_GRID_STEP):
        painter.drawLine(QPointF(0, y), QPointF(SOCIAL_WIDTH, y))
    glow = QRadialGradient(glow_center, SOCIAL_HEIGHT / 2)
    warm = QColor(theme.GOLD_MID)
    warm.setAlpha(SOCIAL_GLOW_ALPHA)
    glow.setColorAt(0.0, warm)
    warm.setAlpha(0)
    glow.setColorAt(1.0, warm)
    painter.fillRect(QRectF(0, 0, SOCIAL_WIDTH, SOCIAL_HEIGHT), glow)


def social_font(pixel_size: int) -> QFont:
    """Return the bundled VT323 font, or the system monospace font if glyphs are missing.

    Args:
        pixel_size: The font size in pixels.

    Returns:
        A font that can draw every character of the title and subtitle.
    """
    font = load_terminal_font(pixel_size)
    if missing_glyphs(font, "".join(SOCIAL_TITLE_LINES) + SOCIAL_SUBTITLE):
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPixelSize(pixel_size)
    return font


def fit_title_font(max_width: float) -> QFont:
    """Pick the largest title size (up to the maximum) whose longest line fits.

    Args:
        max_width: The available width in logical pixels.

    Returns:
        The title font.
    """
    font = social_font(SOCIAL_TITLE_MAX_PX)
    widest = max(QFontMetricsF(font).horizontalAdvance(line) for line in SOCIAL_TITLE_LINES)
    if widest > max_width:
        font.setPixelSize(int(SOCIAL_TITLE_MAX_PX * max_width / widest))
    return font


def paint_social_text(painter: QPainter, area: QRectF) -> None:
    """Paint the gold, outlined title and the subtitle with a block cursor, centered vertically.

    Args:
        painter: A painter in 1280x640 logical coordinates.
        area: The safe text area.
    """
    title_font = fit_title_font(area.width())
    subtitle_font = social_font(SOCIAL_SUBTITLE_PX)
    title_metrics, subtitle_metrics = QFontMetricsF(title_font), QFontMetricsF(subtitle_font)
    line_height = title_metrics.height() * SOCIAL_LINE_SPACING
    block_height = (line_height * len(SOCIAL_TITLE_LINES) + SOCIAL_SUBTITLE_GAP
                    + subtitle_metrics.height())
    top = area.center().y() - block_height / 2
    title = QPainterPath()
    for index, line in enumerate(SOCIAL_TITLE_LINES):
        baseline = top + title_metrics.ascent() + index * line_height
        title.addText(QPointF(area.left(), baseline), title_font, line)
    fill = QLinearGradient(0, top, 0, top + line_height * len(SOCIAL_TITLE_LINES))
    fill.setColorAt(0.0, QColor(theme.GOLD_HIGHLIGHT))
    fill.setColorAt(0.4, QColor(theme.GOLD_LIGHT))
    fill.setColorAt(1.0, QColor(theme.GOLD_DARK))
    painter.strokePath(title, QPen(QColor(theme.OUTLINE), SOCIAL_TITLE_OUTLINE,
                                   Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                   Qt.PenJoinStyle.RoundJoin))
    painter.fillPath(title, fill)
    subtitle_top = top + line_height * len(SOCIAL_TITLE_LINES) + SOCIAL_SUBTITLE_GAP
    painter.setFont(subtitle_font)
    painter.setPen(QColor(theme.TEXT_OUTPUT))
    baseline = subtitle_top + subtitle_metrics.ascent()
    painter.drawText(QPointF(area.left(), baseline), SOCIAL_SUBTITLE)
    cursor_left = area.left() + subtitle_metrics.horizontalAdvance(SOCIAL_SUBTITLE + " ")
    cursor = QRectF(cursor_left, subtitle_top, subtitle_metrics.height() * SOCIAL_CURSOR_WIDTH_RATIO,
                    subtitle_metrics.height())
    painter.fillRect(cursor, QColor(theme.CURSOR))


def save_png_under_limit(image: QImage, target: Path) -> None:
    """Save ``image`` as an optimized PNG, quantizing only if it exceeds the size limit.

    Args:
        image: The final 1280x640 image.
        target: The PNG file to write.
    """
    picture = to_pillow(image).convert("RGB")
    picture.save(target, optimize=True)
    if target.stat().st_size > SOCIAL_MAX_BYTES:
        picture.quantize(colors=GIF_COLORS + 1, method=Image.Quantize.MEDIANCUT).save(
            target, optimize=True)


def make_social() -> None:
    """Write ``docs/social-preview.png``: padlock window, title and subtitle, 1280x640."""
    DOCS_DIR.mkdir(exist_ok=True)
    safe = QRectF(SOCIAL_SAFE_MARGIN, SOCIAL_SAFE_MARGIN, SOCIAL_WIDTH - 2 * SOCIAL_SAFE_MARGIN,
                  SOCIAL_HEIGHT - 2 * SOCIAL_SAFE_MARGIN)
    scale = safe.height() / theme.WINDOW_HEIGHT
    with tempfile.TemporaryDirectory() as folder:
        settings = QSettings(str(Path(folder) / "settings.ini"), QSettings.Format.IniFormat)
        window = render_window_pixmap(settings, SOCIAL_SUPERSAMPLE * scale)
    lock = QRectF(safe.left(), safe.top(), theme.WINDOW_WIDTH * scale, safe.height())
    canvas = QImage(SOCIAL_WIDTH * SOCIAL_SUPERSAMPLE, SOCIAL_HEIGHT * SOCIAL_SUPERSAMPLE,
                    QImage.Format.Format_RGB32)
    painter = QPainter(canvas)
    painter.setRenderHints(QPainter.RenderHint.Antialiasing
                           | QPainter.RenderHint.TextAntialiasing
                           | QPainter.RenderHint.SmoothPixmapTransform)
    painter.scale(SOCIAL_SUPERSAMPLE, SOCIAL_SUPERSAMPLE)
    paint_social_background(painter, lock.center())
    # The window was rendered at exactly the canvas's device resolution, so
    # its pixels map 1:1 onto the lock rectangle.
    window.setDevicePixelRatio(1)
    painter.drawPixmap(lock, window, QRectF(window.rect()))
    text_area = safe.adjusted(lock.width() + SOCIAL_TEXT_GAP, 0, 0, 0)
    paint_social_text(painter, text_area)
    painter.end()
    final = canvas.scaled(SOCIAL_WIDTH, SOCIAL_HEIGHT, Qt.AspectRatioMode.IgnoreAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
    save_png_under_limit(final, SOCIAL_PATH)
    size_kb = SOCIAL_PATH.stat().st_size / 1024
    print(f"wrote {SOCIAL_PATH.relative_to(ROOT)} ({SOCIAL_WIDTH}x{SOCIAL_HEIGHT}, {size_kb:.0f} KB)")


def make_icons() -> None:
    """Write ``icon.png`` and a multi-size ``icon.ico`` into the GUI assets."""
    png_path = ASSETS_DIR / "icon.png"
    render_icon(PNG_ICON_SIZE).save(str(png_path))
    print(f"wrote {png_path.relative_to(ROOT)}")
    ico_path = ASSETS_DIR / "icon.ico"
    with Image.open(png_path) as image:
        image.save(ico_path, sizes=[(size, size) for size in ICO_SIZES])
    print(f"wrote {ico_path.relative_to(ROOT)}")


def main() -> int:
    """Parse arguments and generate the requested assets.

    Returns:
        The process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--icons", action="store_true", help="app icons only")
    parser.add_argument("--demo", action="store_true", help="demo GIFs only")
    parser.add_argument("--social", action="store_true", help="social preview image only")
    args = parser.parse_args()
    everything = not (args.icons or args.demo or args.social)
    create_application([sys.argv[0]])
    if everything or args.icons:
        make_icons()
    if everything or args.demo:
        make_demos()
    if everything or args.social:
        make_social()
    return 0


if __name__ == "__main__":
    sys.exit(main())
