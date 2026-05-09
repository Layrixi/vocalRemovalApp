import pathlib

def _scan_font_files(fonts_dir: pathlib.Path) -> list[pathlib.Path] | ValueError:
    fonts = sorted(
        f.relative_to(fonts_dir).as_posix()
        for pattern in ('*.ttf', '*.otf')
        for f in fonts_dir.rglob(pattern)
    )
    if not fonts:
        raise ValueError("INTERNAL APP ERROR: No font files found in the fonts directory.")
    return fonts

def resolve_font(relative: str, fonts_dir: pathlib.Path) -> pathlib.Path | ValueError:
    """Resolve a font path received from the frontend to an absolute path inside FONTS_DIR.
    Raises ValueError if the resolved path escapes the fonts directory or if it does not exist. Just a safety net in case someone changed the payload data."""
    resolved = (fonts_dir / pathlib.Path(relative)).resolve()
    if not resolved.is_relative_to(fonts_dir.resolve()):
        raise ValueError(f"Invalid font path: {relative}")
    if not resolved.exists() or not resolved.is_file():
        raise ValueError(f"Font file not found: {relative}")
    return resolved

def get_first_font_file(fonts_dir: pathlib.Path, relative_only: bool = False) -> pathlib.Path | ValueError:
    """Get a list of available font files in the 'fonts_dir' directory and return the 1st one in a sorted order."""
    fonts = _scan_font_files(fonts_dir) 
    if relative_only:
        return fonts[0]
    return resolve_font(fonts[0], fonts_dir)

def get_available_fonts_list(fonts_dir: pathlib.Path, relative_only: bool = False) -> list[str] | list[pathlib.Path] | ValueError:
    """Returns a list of available fonts"""
    fonts = _scan_font_files(fonts_dir)
    if relative_only:
        return fonts
    resolved_Fonts = []
    for font in fonts:
        resolved_Fonts.append(resolve_font(font, fonts_dir))
    return resolved_Fonts

