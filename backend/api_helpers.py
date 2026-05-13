import pathlib
import logging
from fontTools import ttLib

def resolve_font(relative: str, fonts_dir: pathlib.Path) -> pathlib.Path:
    """Resolve a font path received from the frontend to an absolute path inside FONTS_DIR.
    Raises ValueError if the resolved path escapes the fonts directory or if it does not exist. Just a safety net in case someone changed the payload data."""
    resolved = (fonts_dir / pathlib.Path(relative)).resolve()
    if not resolved.is_relative_to(fonts_dir.resolve()):
        raise ValueError(f"Invalid font path: {relative}")
    if not resolved.exists() or not resolved.is_file():
        raise ValueError(f"Font file not found: {relative}")
    return resolved

def get_libass_scale_factor(font_path: pathlib.Path) -> float:
    """Calculate the scale factor libass uses based on the font's metadata."""
    try:
        font = ttLib.TTFont(font_path)
        hhea = font['hhea']
        hori_height = hhea.ascent - hhea.descent
        #reading os2 for old fonts may result in KeyError, so it will log a warning and fallback to 0.8
        os2 = font['OS/2']
        os2_height = os2.usWinAscent + os2.usWinDescent
        if hori_height and os2_height:
            return hori_height / os2_height
    except Exception as e:
        logging.debug("Error reading font %s: %s", font_path, e)
        return 0.8  # fallback to old scaling magic number that libass used.

