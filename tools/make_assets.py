"""Render the README demo animations and the application icons from the live GUI code.

Usage::

    python tools/make_assets.py          # demo GIFs and icons
    python tools/make_assets.py demo     # docs/demo-<lang>.gif only
    python tools/make_assets.py icons    # src/passgen/gui/assets/icon.* only

Runs with the offscreen Qt platform, so no display is needed. Requires the
``gui`` extra plus Pillow (included in the ``build`` extra). The passwords shown
in the demo are freshly generated throwaway values.
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
from PySide6.QtCore import QSettings, Qt  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from passgen.gui import theme  # noqa: E402
from passgen.gui.app import create_application  # noqa: E402
from passgen.gui.padlock import render_icon  # noqa: E402
from passgen.gui.window import PadlockWindow  # noqa: E402
from passgen.strings import TEXTS  # noqa: E402

DOCS_DIR = ROOT / "docs"
ASSETS_DIR = ROOT / "src" / "passgen" / "gui" / "assets"
DEMO_LANGUAGES = ("es", "en")
DEMO_LENGTH = "16"
TYPE_DELAY_MS = 220
SHORT_PAUSE_MS = 1600
LONG_PAUSE_MS = 2650
GIF_COLORS = 255
TRANSPARENT_INDEX = 255
ALPHA_THRESHOLD = 128
PNG_ICON_SIZE = 512
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)

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


def record_demo(language: str, settings: QSettings) -> list[Frame]:
    """Record the guided flow: length, types, password, then another password.

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
    sheet = Image.new("RGB", (first.width, first.height * 2))
    sheet.paste(first, (0, 0))
    sheet.paste(last, (0, first.height))
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
    parser.add_argument("what", nargs="?", choices=("all", "demo", "icons"), default="all")
    args = parser.parse_args()
    create_application([sys.argv[0]])
    if args.what in ("all", "icons"):
        make_icons()
    if args.what in ("all", "demo"):
        make_demos()
    return 0


if __name__ == "__main__":
    sys.exit(main())
