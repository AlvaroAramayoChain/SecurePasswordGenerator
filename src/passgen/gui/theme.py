"""Colors, sizes and geometry of the padlock window.

Every visual value used by the GUI lives here as a named constant, so the
design can be tuned in one place. Coordinates are logical pixels inside the
fixed-size window; Qt scales them automatically on HiDPI screens.
"""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class Box:
    """An immutable axis-aligned rectangle in logical pixels.

    Attributes:
        x: Left edge.
        y: Top edge.
        width: Horizontal size.
        height: Vertical size.
    """

    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        """The x coordinate of the right edge."""
        return self.x + self.width

    @property
    def bottom(self) -> float:
        """The y coordinate of the bottom edge."""
        return self.y + self.height


# --- Window -----------------------------------------------------------------
WINDOW_WIDTH: Final[int] = 520
WINDOW_HEIGHT: Final[int] = 620
APP_ORGANIZATION: Final[str] = "SecurePasswordGenerator"
APP_NAME: Final[str] = "SecurePasswordGenerator"
SETTINGS_LANGUAGE_KEY: Final[str] = "language"
OPAQUE_ENV_VAR: Final[str] = "PASSGEN_OPAQUE"
FALLBACK_BACKGROUND: Final[str] = "#1E1E1E"

# --- Padlock geometry -------------------------------------------------------
CENTER_X: Final[float] = WINDOW_WIDTH / 2
SHACKLE_TOP: Final[float] = 22
SHACKLE_OUTER_RADIUS: Final[float] = 145
SHACKLE_THICKNESS: Final[float] = 50
SHACKLE_LEG_BOTTOM: Final[float] = 260

BODY: Final[Box] = Box(10, 212, 500, 396)
BODY_RADIUS: Final[float] = 72

BUMP_BASE_HALF_WIDTH: Final[float] = 92
BUMP_TOP_HALF_WIDTH: Final[float] = 44
BUMP_HEIGHT: Final[float] = 44

KEYHOLE_CENTER_Y: Final[float] = 199
KEYHOLE_RADIUS: Final[float] = 13
KEYHOLE_STEM_TOP_HALF_WIDTH: Final[float] = 6
KEYHOLE_STEM_BOTTOM_HALF_WIDTH: Final[float] = 13
KEYHOLE_STEM_BOTTOM: Final[float] = 238

OUTLINE_WIDTH: Final[float] = 7
BEVEL_WIDTH: Final[float] = 11
INNER_LINE_WIDTH: Final[float] = 1.5
MASK_MARGIN: Final[float] = OUTLINE_WIDTH
GLOSS_ALPHA: Final[int] = 190
GLOSS_WIDTH: Final[float] = 4
SPARKLE_SIZE: Final[float] = 3

# --- Title buttons and language toggle --------------------------------------
ROUND_BUTTON_RADIUS: Final[int] = 13
ROUND_BUTTON_CENTER_Y: Final[int] = 247
ROUND_BUTTON_CENTERS_X: Final[tuple[int, int, int]] = (382, 414, 446)
ROUND_BUTTON_OUTLINE: Final[float] = 2.5
ROUND_BUTTON_GLYPH_WIDTH: Final[float] = 3.0
ROUND_BUTTON_GLYPH_SCALE: Final[float] = 0.42

LANGUAGE_TOGGLE: Final[Box] = Box(296, 236, 62, 22)
LANGUAGE_TOGGLE_FONT_PX: Final[int] = 16

# --- Console (blue retro window) --------------------------------------------
CONSOLE: Final[Box] = Box(30, 270, 460, 306)
CONSOLE_RADIUS: Final[float] = 14
CONSOLE_OUTLINE: Final[float] = 3
CONSOLE_BORDER: Final[int] = 7
TITLE_BAR_HEIGHT: Final[int] = 36
TITLE_ICON_SIZE: Final[int] = 22
TITLE_PADDING: Final[int] = 12
TITLE_FONT_PX: Final[int] = 22
INPUT_ROW_HEIGHT: Final[int] = 42
ROW_GAP: Final[int] = 7
RUN_BUTTON_WIDTH: Final[int] = 118
SCROLLBAR_WIDTH: Final[int] = 18
PANEL_RADIUS: Final[float] = 6

# --- Terminal ---------------------------------------------------------------
TERMINAL_FONT_PX: Final[int] = 21
TERMINAL_MARGIN: Final[int] = 8
PROMPT_MARKER: Final[str] = ">>> "
CURSOR_BLINK_MS: Final[int] = 530
MAX_INPUT_CHARS: Final[int] = 40
FONT_FILE: Final[str] = "VT323-Regular.ttf"

# --- Interaction ------------------------------------------------------------
HOVER_LIGHTEN: Final[int] = 118
PRESS_DARKEN: Final[int] = 125
PRESS_OFFSET: Final[float] = 1.0

# --- Colors: padlock --------------------------------------------------------
OUTLINE: Final[str] = "#2A1900"
GOLD_HIGHLIGHT: Final[str] = "#FFF8B8"
GOLD_LIGHT: Final[str] = "#FFE640"
GOLD_MID: Final[str] = "#FFD200"
GOLD_DARK: Final[str] = "#F0A800"
GOLD_SHADOW: Final[str] = "#B86F00"
GLOSS: Final[str] = "#FFFFFF"
KEYHOLE: Final[str] = "#0A0A0A"

# --- Colors: console --------------------------------------------------------
NAVY: Final[str] = "#061452"
FRAME_BLUE: Final[str] = "#1442C8"
FRAME_LIGHT: Final[str] = "#4C82FF"
TITLE_TOP: Final[str] = "#3F7DFF"
TITLE_BOTTOM: Final[str] = "#1240C4"
TITLE_TEXT: Final[str] = "#F4F7FF"
TERMINAL_BG: Final[str] = "#04060C"
TEXT_OUTPUT: Final[str] = "#A8D8FF"
TEXT_INPUT: Final[str] = "#46E86A"
TEXT_ERROR: Final[str] = "#FF7B72"
TEXT_PASSWORD: Final[str] = "#FFFFFF"
CURSOR: Final[str] = "#3D8BFF"
SELECTION_BG: Final[str] = "#2A5BD7"
PLACEHOLDER: Final[str] = "#5F8BD6"

# --- Colors: scrollbar ------------------------------------------------------
SCROLL_TRACK: Final[str] = "#9DB9F2"
SCROLL_HANDLE: Final[str] = "#5C8DF2"
SCROLL_BUTTON: Final[str] = "#E8EEFF"
SCROLL_ARROW: Final[str] = "#0A1C66"

# --- Colors: buttons --------------------------------------------------------
MINIMIZE_COLOR: Final[str] = "#2F7FFF"
RESTART_COLOR: Final[str] = "#F7BE16"
CLOSE_COLOR: Final[str] = "#EC3A2E"
GLYPH_LIGHT: Final[str] = "#FFFFFF"
GLYPH_DARK: Final[str] = "#3A2400"
RUN_TOP: Final[str] = "#1A3FB8"
RUN_BOTTOM: Final[str] = "#0A2580"
RUN_TRIANGLE: Final[str] = "#3FE03F"
RUN_TEXT: Final[str] = "#F4F7FF"
TOGGLE_BG: Final[str] = "#0A1F6B"
TOGGLE_ACTIVE: Final[str] = "#3D8BFF"
TOGGLE_TEXT: Final[str] = "#9DB9F2"
TOGGLE_ACTIVE_TEXT: Final[str] = "#FFFFFF"
