"""
Tests for changes made to backend/services/TextBurner.py in this PR:

- TextStyle new fields: bold, italic, underline, strikeout, letter_spacing, angle
- _style_to_ass_line: default font changed to Arial, new field encodings
- _wrap_text: core wrapping logic (covered by PR diff)
"""
import sys
import pathlib
import pytest

# Ensure the backend directory is on the path so imports resolve correctly.
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from services.TextBurner import TextBurner, TextStyle, TextSegment


# ---------------------------------------------------------------------------
# TextStyle – new fields added in this PR
# ---------------------------------------------------------------------------

class TestTextStyleNewFields:
    """TextStyle dataclass should expose the new fields with correct defaults."""

    def test_bold_default_false(self):
        s = TextStyle()
        assert s.bold is False

    def test_italic_default_false(self):
        s = TextStyle()
        assert s.italic is False

    def test_underline_default_false(self):
        s = TextStyle()
        assert s.underline is False

    def test_strikeout_default_false(self):
        s = TextStyle()
        assert s.strikeout is False

    def test_letter_spacing_default_zero(self):
        s = TextStyle()
        assert s.letter_spacing == 0

    def test_angle_default_zero(self):
        s = TextStyle()
        assert s.angle == 0

    def test_new_fields_settable(self):
        s = TextStyle(bold=True, italic=True, underline=True, strikeout=True,
                      letter_spacing=10, angle=45)
        assert s.bold is True
        assert s.italic is True
        assert s.underline is True
        assert s.strikeout is True
        assert s.letter_spacing == 10
        assert s.angle == 45

    def test_fields_independent(self):
        """Setting one new field must not affect the others."""
        s = TextStyle(bold=True)
        assert s.italic is False
        assert s.underline is False
        assert s.strikeout is False
        assert s.letter_spacing == 0
        assert s.angle == 0


# ---------------------------------------------------------------------------
# TextBurner._style_to_ass_line – field encoding changes in this PR
# ---------------------------------------------------------------------------

def _parse_ass_style_fields(line: str) -> list[str]:
    """Extract the comma-separated field values from a 'Style: …' ASS line."""
    assert line.startswith("Style: ")
    return line[len("Style: "):].split(",")


class TestStyleToAssLineDefaultFont:
    """Default font name must be Arial (changed from Comic Sans MS)."""

    def test_no_font_file_uses_arial(self):
        burner = TextBurner()
        style = TextStyle(font_file=None)
        line = burner._style_to_ass_line(style, "TestStyle")
        fields = _parse_ass_style_fields(line)
        font_name = fields[1]  # index 1 = Fontname
        assert font_name == "Arial"

    def test_explicit_font_file_uses_stem(self, tmp_path):
        """When a font_file is given, use its stem (filename without extension)."""
        burner = TextBurner()
        fake_font = tmp_path / "MyFont.ttf"
        fake_font.write_text("")
        style = TextStyle(font_file=str(fake_font))
        line = burner._style_to_ass_line(style, "TestStyle")
        fields = _parse_ass_style_fields(line)
        assert fields[1] == "MyFont"


class TestStyleToAssLineBoldItalic:
    """Bold and Italic use (0, 1) encoding in ASS."""

    def test_bold_false_encodes_0(self):
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(bold=False), "S")
        fields = _parse_ass_style_fields(line)
        # ASS field order: Name, Fontname, Fontsize, Primary, Secondary, Outline, Back,
        # Bold(7), Italic(8), Underline(9), StrikeOut(10), …
        assert fields[7] == "0"

    def test_bold_true_encodes_1(self):
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(bold=True), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[7] == "1"

    def test_italic_false_encodes_0(self):
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(italic=False), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[8] == "0"

    def test_italic_true_encodes_1(self):
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(italic=True), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[8] == "1"


class TestStyleToAssLineUnderlineStrikeout:
    """Underline and StrikeOut use (0, -1) encoding in ASS (ASS convention)."""

    def test_underline_false_encodes_0(self):
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(underline=False), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[9] == "0"

    def test_underline_true_encodes_minus1(self):
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(underline=True), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[9] == "-1"

    def test_strikeout_false_encodes_0(self):
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(strikeout=False), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[10] == "0"

    def test_strikeout_true_encodes_minus1(self):
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(strikeout=True), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[10] == "-1"


class TestStyleToAssLineLetterSpacing:
    """Letter spacing is passed directly as Spacing (field 13)."""

    def test_default_spacing_is_zero(self):
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[13] == "0"

    def test_nonzero_spacing_preserved(self):
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(letter_spacing=8), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[13] == "8"

    def test_negative_spacing_preserved(self):
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(letter_spacing=-3), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[13] == "-3"


class TestStyleToAssLineAngle:
    """Angle field (14) is (360 - style.angle) % 360 to match CSS rotation direction."""

    def test_angle_zero_stays_zero(self):
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(angle=0), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[14] == "0"

    def test_angle_90_becomes_270(self):
        """90 degrees CSS → (360 - 90) % 360 = 270 in ASS."""
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(angle=90), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[14] == "270"

    def test_angle_180_becomes_180(self):
        """180 degrees CSS → (360 - 180) % 360 = 180 in ASS."""
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(angle=180), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[14] == "180"

    def test_angle_270_becomes_90(self):
        """270 degrees CSS → (360 - 270) % 360 = 90 in ASS."""
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(angle=270), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[14] == "90"

    def test_angle_360_becomes_0(self):
        """360 degrees CSS → (360 - 360) % 360 = 0 in ASS."""
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(angle=360), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[14] == "0"

    def test_angle_45_becomes_315(self):
        """45 degrees CSS → (360 - 45) % 360 = 315 in ASS."""
        burner = TextBurner()
        line = burner._style_to_ass_line(TextStyle(angle=45), "S")
        fields = _parse_ass_style_fields(line)
        assert fields[14] == "315"


# ---------------------------------------------------------------------------
# TextBurner._wrap_text – covered by the PR diff (comments only changed but
# logic remains; test the observable behaviour)
# ---------------------------------------------------------------------------

class TestWrapText:
    """_wrap_text should split long lines using \\N (ASS hard break)."""

    # Default CHAR_WIDTH_RATIO=0.5, play_res_x=1920, font_size=64
    # => chars_per_line = max(1, int(1920 / (64 * 0.5))) = max(1, 60) = 60

    def test_short_text_no_wrap(self):
        burner = TextBurner()
        result = burner._wrap_text("Hello", font_size=64, play_res_x=1920)
        assert result == "Hello"
        assert "\\N" not in result

    def test_single_word_fits_on_one_line(self):
        burner = TextBurner()
        result = burner._wrap_text("Word", font_size=64, play_res_x=1920)
        assert "\\N" not in result

    def test_long_text_wraps_with_ass_break(self):
        """A sentence that exceeds chars_per_line must be broken with \\N."""
        burner = TextBurner()
        # 60 chars per line with font_size=64, play_res_x=1920
        # Build a string that is definitely longer than 60 chars
        long_text = "word " * 20  # 100 chars
        result = burner._wrap_text(long_text.strip(), font_size=64, play_res_x=1920)
        assert "\\N" in result

    def test_wrapped_lines_each_fit_within_limit(self):
        """Each line produced by _wrap_text must not exceed chars_per_line."""
        burner = TextBurner()
        text = "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa quebec romeo sierra tango"
        result = burner._wrap_text(text, font_size=64, play_res_x=1920)
        chars_per_line = max(1, int(1920 / (64 * 0.5)))
        for segment in result.split("\\N"):
            assert len(segment) <= chars_per_line, (
                f"Segment '{segment}' ({len(segment)} chars) exceeds limit {chars_per_line}"
            )

    def test_overlong_single_word_gets_split(self):
        """A word longer than chars_per_line must be split across lines."""
        burner = TextBurner()
        # chars_per_line = int(1920 / (64 * 0.5)) = 60
        long_word = "a" * 150  # 150 chars – must be split
        result = burner._wrap_text(long_word, font_size=64, play_res_x=1920)
        assert "\\N" in result
        for segment in result.split("\\N"):
            assert len(segment) <= 60

    def test_empty_string_returns_empty(self):
        burner = TextBurner()
        result = burner._wrap_text("", font_size=64, play_res_x=1920)
        assert result == ""

    def test_whitespace_only_returns_empty(self):
        """Whitespace-only input should produce no output lines."""
        burner = TextBurner()
        result = burner._wrap_text("   ", font_size=64, play_res_x=1920)
        # split() on whitespace → empty word list → no lines → joined is ""
        assert result == ""

    def test_small_play_res_x_wraps_aggressively(self):
        """Reducing play_res_x reduces chars_per_line and causes more wrapping."""
        burner = TextBurner()
        text = "one two three four five"
        result_wide = burner._wrap_text(text, font_size=64, play_res_x=1920)
        result_narrow = burner._wrap_text(text, font_size=64, play_res_x=320)
        # The narrow version must wrap more (more \\N separators)
        assert result_narrow.count("\\N") >= result_wide.count("\\N")

    def test_large_font_size_wraps_more(self):
        """Larger font_size reduces chars_per_line, causing more line breaks."""
        burner = TextBurner()
        text = "the quick brown fox jumps over the lazy dog and runs away"
        result_small_font = burner._wrap_text(text, font_size=32, play_res_x=1920)
        result_large_font = burner._wrap_text(text, font_size=128, play_res_x=1920)
        assert result_large_font.count("\\N") >= result_small_font.count("\\N")

    def test_newline_chars_preserved_only_as_ass_break(self):
        """The function joins output with \\N (two chars), not a real newline."""
        burner = TextBurner()
        text = "word " * 20
        result = burner._wrap_text(text.strip(), font_size=64, play_res_x=1920)
        # \\N in Python source = literal backslash + N, not a real newline
        assert "\n" not in result

    def test_minimum_chars_per_line_is_one(self):
        """Even with extreme settings, chars_per_line must be at least 1."""
        burner = TextBurner()
        # Tiny play_res_x with huge font → would give 0 without the max(1, …)
        result = burner._wrap_text("hello", font_size=10000, play_res_x=1)
        # Should not raise and should produce some output
        assert result != ""