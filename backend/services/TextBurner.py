import subprocess
import pathlib
import sys
import tempfile
import json
import textwrap
from dataclasses import dataclass, field
from typing import Optional
import shutil
sys.path.append(str(pathlib.Path(__file__).parent.parent))
from config import set_video_duration, get_video_duration, set_video_dimensions, get_video_dimensions, get_char_width_ratio

"""
Class responsible for applying the text to the video.
It's also responsible for the rendering process.
"""


def _require_ffmpeg():
    if shutil.which("ffmpeg") is None:
        raise EnvironmentError("ffmpeg is not installed or not found in PATH.")
    
#TEMPORARY FOR BUG FIXING, probes the length of the video and stores it in config
def _probe_and_set_duration(video_path: str | pathlib.Path):
    """
    Probe video duration and dimensions using a single ffprobe call and store them in config.
    Used for testing and video processing.
    """
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "format=duration:stream=width,height",
                "-of", "json",
                str(video_path),
            ],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(probe.stdout)
        set_video_duration(float(data["format"]["duration"]))
        stream = data["streams"][0]
        set_video_dimensions(int(stream["width"]), int(stream["height"]))
    except Exception:
        set_video_duration(0.0)
        set_video_dimensions(1920, 1080)
    


@dataclass
class TextStyle:
    """
    All visual properties for a text overlay.
    font_file:
        Path to a .ttf / .otf file.  When omitted ffmpeg uses its built-in font.
    """
 
    # ── Typography
    font_file:    Optional[str] = None         
    font_size:    int           = 64
    font_color:   str           = "#FFFFFFFF"
 
    # ── Background box
    box:          bool          = False
    box_color:    str           = "#000000FF"
    box_padding:  int           = 0      
 
    # ── Drop shadow
    shadow:       bool          = False
    shadow_color: str           = "#000000FF"
    shadow_x:     int           = 0             
    shadow_y:     int           = 0             
 
    # ── Border
    border_width: int           = 4             
    border_color: str           = "#000000FF"
 
    # ── Vertical position
    vertical_position: str      = "center"
 
    # ── Horizontal position
    horizontal_position: str    = "center"
 
    # ── Spacing
    line_spacing: int           = 30      

@dataclass
class TextSegment:
    """One piece of text with its own timing and style."""
    text:       str
    start_time: float                       # seconds; use 0 for "always on"
    end_time:   float                       # seconds
    style:      TextStyle = field(default_factory=TextStyle)

class TextBurner:
    """Burns subtitle text onto a video using FFmpeg's subtitles filter."""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """
        Parameters
        ----------
        ffmpeg_path : path/name of the ffmpeg executable
        """
        self.ffmpeg_path = ffmpeg_path
        
    #API

    def burn(
        self,
        video_path: str | pathlib.Path,
        output_path: str | pathlib.Path,
        lines: list[TextSegment],
        video_codec: str = "libx264",
        audio_codec: str = "copy",
        quality: int = 23, 
        verbose: bool = False,
        timeout: int = 300,
    ):
        """
        Burn subtitles into video and write the result.

        Parameters
        ----------
        video_path  : input video file
        output_path : where to save the rendered video (mp4)
        lines       : list of TextSegment objects defining the text, timing, and style of each subtitle line
        video_codec : ffmpeg video codec to use (default: libx264)
        audio_codec : ffmpeg audio codec to use (default: copy)
        quality     : ffmpeg CRF quality level (lower is better quality, default: 23)
        verbose     : if True, print ffmpeg command and output; debug purposes
        timeout     : ffmpeg subprocess timeout in seconds

        Returns
        -------
        pathlib.Path to the output file
        """

        _require_ffmpeg()

        video_path  = pathlib.Path(video_path)
        output_path = pathlib.Path(output_path)

        if not lines:
            raise ValueError("No lines with a timestamp provided.")

        try:
            with tempfile.TemporaryDirectory(prefix="karaoke_textburner_") as temp_dir:
                temp_dir_path = pathlib.Path(temp_dir)

                ass_file = temp_dir_path / "subtitles.ass"
                width, height = get_video_dimensions()
                ass_file.write_text(
                    self._build_ass_content(lines, width, height), encoding="utf-8"
                )

                filter_str = f"subtitles='{self._escape_ass_path(ass_file)}'"

                self._run_ffmpeg([
                    self.ffmpeg_path, '-y',
                    '-i', str(video_path),
                    '-vf', filter_str,
                    '-c:v', video_codec,
                    '-crf', str(quality),
                    '-c:a', audio_codec,
                    str(output_path),
                ], verbose=verbose)
                print(f"Video saved to: {output_path}")
        except RuntimeError as e:
            return RuntimeError(f"Failed to burn subtitles: {e}")
            
        return output_path

    # Private helpers

    def _run_ffmpeg(self, cmd: list[str], verbose: bool):
        if verbose:
            print("Running:", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=not verbose, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")

    def _escape_ass_path(self, path: pathlib.Path) -> str:
        """Escape a path for use in an FFmpeg subtitles filter option (Windows-safe)."""
        return path.as_posix().replace(':', '\\:')

    def _seconds_to_ass_time(self, seconds: float) -> str:
        """Convert seconds to ASS timestamp format H:MM:SS.cs"""
        h  = int(seconds // 3600)
        m  = int((seconds % 3600) // 60)
        s  = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


    def _wrap_text(self, text: str, font_size: int, play_res_x: int) -> str:
        """Pre-wrap text using \\N (ASS hard break) so long words don't overflow the frame."""
        usable_px    = play_res_x * 0.8          # leave 10% margin on each side, hardcpded, may leave hoice to th user later
        chars_per_line = max(1, int(usable_px / (font_size * get_char_width_ratio())))
        wrapped_lines = []
        for word in text.split():
            while len(word) > chars_per_line:
                wrapped_lines.append(word[:chars_per_line])
                word = word[chars_per_line:]
            wrapped_lines.append(word) if word else None
        return "\\N".join(textwrap.wrap(" ".join(wrapped_lines), width=chars_per_line))

    _ALIGNMENT_MAP: dict = {
        ("center", "center"): 5,
        ("left",   "center"): 4,
        ("right",  "center"): 6,
        ("center", "top"):    8,
        ("left",   "top"):    7,
        ("right",  "top"):    9,
        ("center", "bottom"): 2,
        ("left",   "bottom"): 1,
        ("right",  "bottom"): 3,
    }

    def _color_to_ass(self, color_str: str) -> str:
        """Convert a CSS hex color (#RRGGBB or #RRGGBBAA) to ASS &HAABBGGRR format.
        CSS alpha: 00 = transparent, FF = opaque.
        ASS alpha: 00 = opaque,      FF = transparent  (inverted).
        """
        #if for future
        if color_str.startswith("#"):
            hex_str = color_str.lstrip("#")
            r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
            alpha = 0
            if len(hex_str) == 8:
                css_alpha = int(hex_str[6:8], 16)
                alpha = 255 - css_alpha   # invert: CSS FF opaque → ASS 00 opaque
        else:
            r, g, b, alpha = 255, 255, 255, 0
        return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"

    def _position_to_alignment(self, h_pos: str, v_pos: str) -> int:
        """Map horizontal/vertical position names to an ASS alignment value (1-9)."""
        return self._ALIGNMENT_MAP.get((h_pos, v_pos), 5)

    def _style_to_ass_line(self, style: TextStyle, style_name: str) -> str:
        """Convert a TextStyle to a single ASS [V4+ Styles] line.
           ASS field goes as: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, TertiaryColour, BackColour, 
           Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, 
           Outline, Shadow, Alignment, MarginL, MarginR, MarginV, AlphaLevel, Encoding
        """
        primary_color  = self._color_to_ass(style.font_color)
        secondary_color = "&H000000FF"
        
        if style.box:
            border_style  = 3
            outline       = style.box_padding
            shadow        = 0
            outline_color = "&H00000000"
            back_color    = self._color_to_ass(style.box_color)
        elif style.shadow or style.border_width > 0:
            border_style  = 1
            outline       = style.border_width
            shadow        = max(style.shadow_x, style.shadow_y) if style.shadow else 0
            outline_color = self._color_to_ass(style.border_color) if style.border_width > 0 else "&H00000000"
            back_color    = self._color_to_ass(style.shadow_color) if style.shadow else "&H00000000"
        else:
            border_style  = 0
            outline       = 0
            shadow        = 0
            outline_color = "&H00000000"
            back_color    = "&H00000000"

        alignment = self._position_to_alignment(style.horizontal_position, style.vertical_position)
        font_name = pathlib.Path(style.font_file).stem if style.font_file else "Comic Sans MS"

        fields = [
            style_name, font_name, str(style.font_size),
            primary_color, secondary_color, outline_color, back_color,
            "0", "0", "0", "0",   # Bold, Italic, Underline, StrikeOut
            "100", "100",          # ScaleX, ScaleY
            "0",                   # Spacing (letter spacing; line_spacing has no direct ASS equivalent)
            "0",                   # Angle
            str(border_style), str(outline), str(shadow),
            str(alignment),
            "10", "10", "10",      # MarginL, MarginR, MarginV
            "1",                   # Encoding
        ]
        return "Style: " + ",".join(fields)

    def _build_ass_content(self, lines: list[TextSegment], width: int, height: int) -> str:
        """Generate an ASS subtitle file with one style entry per unique TextStyle."""
        unique_styles: list[TextStyle] = []
        style_indices: list[int] = []
        for line in lines:
            try:
                idx = unique_styles.index(line.style)
            except ValueError:
                idx = len(unique_styles)
                unique_styles.append(line.style)
            style_indices.append(idx)

        style_lines = "\n".join(
            self._style_to_ass_line(s, f"Style{i}")
            for i, s in enumerate(unique_styles)
        )

        header = (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            "WrapStyle: 2\n"
            "ScaledBorderAndShadow: yes\n"
            f"PlayResX: {width}\n"
            f"PlayResY: {height}\n"
            "\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
            "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"{style_lines}\n"
            "\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )

        events = []
        for line, style_idx in zip(lines, style_indices):
            start = self._seconds_to_ass_time(line.start_time)
            end   = self._seconds_to_ass_time(
                line.end_time if line.end_time is not None else (get_video_duration() or 99999)
            )
            text = self._wrap_text(line.text, line.style.font_size, width)
            events.append(f"Dialogue: 0,{start},{end},Style{style_idx},,0,0,0,,{text}")
        return header + "\n".join(events) + "\n"
        
# testing main, to be removed later
if __name__ == "__main__":

    VIDEO_DIR  = pathlib.Path(__file__).parent.parent / "uploads" / "video"
    OUTPUT_DIR  = pathlib.Path(__file__).parent.parent / "uploads" / "output"
    vid = "chronos tester.mp4"
    video_path = VIDEO_DIR / vid
    burner = TextBurner()

    LINES = [
        TextSegment(text="Hello world",        start_time=0.0, end_time=1.0),
        TextSegment(text="TextBurner works",   start_time=1.0, end_time=2.0),
        TextSegment(text="Subtitles on video", start_time=2.0, end_time=3.0),
        TextSegment(text="Done",               start_time=3.0, end_time=4.0),
    ]
    LINES2 = [
        TextSegment(text='Sudden ringing, I slowly get upb bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', start_time=0.0,       end_time=4.519145),
        TextSegment(text='And turn off the noise, already fed up',                                                            start_time=4.519145,   end_time=5.561934),
        TextSegment(text='And turn off the noise, already fed',                                                               start_time=5.561934,   end_time=6.772827),
        TextSegment(text="Reminding me that tomorrow's hopeless",                                                             start_time=6.772827,   end_time=7.849959),
        TextSegment(text="I'm slowly rotting inside a jail cell",                                                             start_time=7.849959,   end_time=None),
    ]

    out = OUTPUT_DIR / f"{video_path.stem}_burned.mp4"
    _probe_and_set_duration(video_path)
    video_duration = get_video_duration()
    print(f"Video duration: {video_duration} seconds")
    print(f"--- Burning subtitles → {out} ---")
    try:
        out = burner.burn(video_path=video_path, output_path=out, lines=LINES2,verbose=True)
    except RuntimeError as e:
        print(e)
    

    print("Done")
