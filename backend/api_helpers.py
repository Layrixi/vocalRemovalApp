import pathlib

def resolve_font(relative: str, fonts_dir: pathlib.Path) -> pathlib.Path:
    """Resolve a font path received from the frontend to an absolute path inside FONTS_DIR.
    Raises ValueError if the resolved path escapes the fonts directory or if it does not exist. Just a safety net in case someone changed the payload data."""
    resolved = (fonts_dir / pathlib.Path(relative)).resolve()
    if not resolved.is_relative_to(fonts_dir.resolve()):
        raise ValueError(f"Invalid font path: {relative}")
    if not resolved.exists() or not resolved.is_file():
        raise ValueError(f"Font file not found: {relative}")
    return resolved
