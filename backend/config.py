import pathlib
import torch
from api_helpers import resolve_font

VIDEO_LEN: float = 0.0
PLAY_RES_X: int = 1920              # fixed play resolution consistent scaling factor. Do not overwrite.
PLAY_RES_Y: int = 1080
VIDEO_W:   int   = 1920             # actual video dimensions, set at runtime after upload
VIDEO_H:   int   = 1080
CHAR_WIDTH_RATIO: float = 0.5
FONTS_DIR : pathlib.Path = pathlib.Path(__file__).parent / "static" / "fonts"
AVAILABLE_FONTS: list[str] = []  # populated after function definitions below
FIRST_FONT: str = ""             # same here
#check if cuda is available
def check_device():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return device

#returns path to the uploaded audio file
def get_audio_path(filename):
    return pathlib.Path(__file__).parent / "uploads" / "audio" / filename

def set_video_duration(seconds: float):
    global VIDEO_LEN
    VIDEO_LEN = seconds

def get_video_duration() -> float:
    return VIDEO_LEN

def set_video_dimensions(w: int, h: int):
    global VIDEO_W, VIDEO_H
    VIDEO_W = w
    VIDEO_H = h

def get_video_dimensions() -> tuple[int, int]:
    return VIDEO_W, VIDEO_H

def get_char_width_ratio() -> float:
    return CHAR_WIDTH_RATIO

def set_available_fonts(fonts_dir: pathlib.Path, relative_only: bool = False) -> list[str]:
    """Returns a list of available fonts in a resolved form."""
    global AVAILABLE_FONTS
    fonts = _scan_font_files(fonts_dir)
    if relative_only:
        AVAILABLE_FONTS = fonts
    else:
        resolved_fonts = []
        for font in fonts:
            resolved_fonts.append(resolve_font(font, fonts_dir))
        AVAILABLE_FONTS = resolved_fonts
    return AVAILABLE_FONTS

def get_available_fonts() -> list[str]:
    """Returns a list of available fonts in a resolved form."""
    return AVAILABLE_FONTS

def _scan_font_files(fonts_dir: pathlib.Path) -> list[str]:
    fonts = sorted(
        f.relative_to(fonts_dir).as_posix()
        for pattern in ('*.ttf', '*.otf')
        for f in fonts_dir.rglob(pattern)
    )
    if not fonts:
        raise ValueError("INTERNAL APP ERROR: No font files found in the fonts directory.")
    return fonts

AVAILABLE_FONTS = set_available_fonts(FONTS_DIR, relative_only=True)
FIRST_FONT = AVAILABLE_FONTS[0]