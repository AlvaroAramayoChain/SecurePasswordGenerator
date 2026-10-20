"""Render README screenshots and application icons from the live GUI code.

Usage::

    python tools/make_assets.py              # screenshots and icons
    python tools/make_assets.py screenshots  # docs/screenshot-<lang>.png only
    python tools/make_assets.py icons        # src/passgen/gui/assets/icon.* only

Runs with the offscreen Qt platform, so no display is needed. Requires the
``gui`` extra; ``.ico`` generation also requires Pillow (``build`` extra).
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402

from passgen.gui.app import create_application  # noqa: E402
from passgen.gui.padlock import render_icon  # noqa: E402
from passgen.gui.window import PadlockWindow  # noqa: E402
from passgen.strings import SUPPORTED_LANGUAGES  # noqa: E402

DOCS_DIR = ROOT / "docs"
ASSETS_DIR = ROOT / "src" / "passgen" / "gui" / "assets"
SCREENSHOT_LENGTH = "16"
PNG_ICON_SIZE = 512
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def render_screenshot(language: str, settings: QSettings, target: Path) -> None:
    """Run a short demo flow in ``language`` and save the window image.

    Args:
        language: The interface language to show.
        settings: A throwaway settings store.
        target: The PNG file to write.
    """
    window = PadlockWindow(settings=settings, opaque=False)
    window.set_language(language)
    for answer in (SCREENSHOT_LENGTH, ""):
        window.input.setText(answer)
        window.submit_input()
    window.show()
    window.grab().save(str(target))
    window.close()


def make_screenshots() -> None:
    """Write ``docs/screenshot-<language>.png`` for every supported language."""
    DOCS_DIR.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        settings = QSettings(str(Path(folder) / "settings.ini"), QSettings.Format.IniFormat)
        for language in SUPPORTED_LANGUAGES:
            target = DOCS_DIR / f"screenshot-{language}.png"
            render_screenshot(language, settings, target)
            print(f"wrote {target.relative_to(ROOT)}")


def make_icons() -> None:
    """Write ``icon.png`` and a multi-size ``icon.ico`` into the GUI assets."""
    png_path = ASSETS_DIR / "icon.png"
    render_icon(PNG_ICON_SIZE).save(str(png_path))
    print(f"wrote {png_path.relative_to(ROOT)}")
    try:
        from PIL import Image
    except ImportError:
        print("Pillow is not installed; skipping icon.ico (pip install pillow)")
        return
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
    parser.add_argument("what", nargs="?", choices=("all", "screenshots", "icons"),
                        default="all")
    args = parser.parse_args()
    create_application([sys.argv[0]])
    if args.what in ("all", "icons"):
        make_icons()
    if args.what in ("all", "screenshots"):
        make_screenshots()
    return 0


if __name__ == "__main__":
    sys.exit(main())
