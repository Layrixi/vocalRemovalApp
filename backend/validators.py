"""
Input validation helpers for API.
Each function returns an error string on failure, or None on success.
"""


import math


def validate_font_file(value) -> str | None:
    if value is not None and not isinstance(value, str):
        return 'font_file must be a string'
    return None


def validate_font_size(value) -> str | None:
    try:
        if int(value) <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return 'font_size must be a positive integer'
    return None


def validate_letter_spacing(value) -> str | None:
    try:
        if not 0 <= int(value) <= 100:
            raise ValueError()
    except (ValueError, TypeError):
        return 'letter_spacing must be an integer in range 0-100'
    return None


def validate_angle(value) -> str | None:
    try:
        parsed = float(value)
    except (ValueError, TypeError):
        return 'angle must be a number'
    if not math.isfinite(parsed):
        return 'angle must be a finite number'
    return None


def validate_outline_width(value) -> str | None:
    try:
        if not 0 <= int(value) <= 4:
            raise ValueError()
    except (ValueError, TypeError):
        return 'outline_width must be an integer in range 0-4'
    return None


def validate_box_padding(value) -> str | None:
    try:
        if not 1 <= int(value) <= 100:
            raise ValueError()
    except (ValueError, TypeError):
        return 'box_padding must be an integer in range 1-100'
    return None


def validate_shadow_offset(value) -> str | None:
    try:
        if not 0 <= int(value) <= 4:
            raise ValueError()
    except (ValueError, TypeError):
        return 'shadow_offset must be an integer in range 0-4'
    return None


def validate_style(style: dict) -> str | None:
    """Returns an error message if the style dict contains invalid values, else None."""
    if not isinstance(style, dict):
        return 'style must be an object'
    
    if 'font_file' in style:
        if err := validate_font_file(style['font_file']):
            return err

    if 'font_size' not in style:
        return 'font_size is required'
    if err := validate_font_size(style['font_size']):
        return err

    if 'letter_spacing' not in style:
        return 'letter_spacing is required'
    if err := validate_letter_spacing(style['letter_spacing']):
        return err

    if 'angle' not in style:
        return 'angle is required'
    if err := validate_angle(style['angle']):
        return err

    if 'outline_width' not in style:
        return 'outline_width is required'
    if err := validate_outline_width(style['outline_width']):
        return err

    if 'box_padding' in style:
        if err := validate_box_padding(style['box_padding']):
            return err

    if 'shadow_offset' in style:
        if err := validate_shadow_offset(style['shadow_offset']):
            return err

    return None
