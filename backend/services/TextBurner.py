import subprocess
import pathlib
import sys
import tempfile
import json
from dataclasses import dataclass, field
from typing import Optional
import shutil
from fontTools import ttLib
sys.path.append(str(pathlib.Path(__file__).parent.parent))
from config import VIDEO_W,PLAY_RES_X, PLAY_RES_Y, set_video_duration, get_video_duration, set_video_dimensions, get_video_dimensions, get_char_width_ratio

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
    # consider more optional properties
    # ── Typography
    font_file:    Optional[str] = None  # path to .ttf/.otf font file; if None, ffmpeg's default font is used         
    font_size:    int           = 64
    font_color:   str           = "#FFFFFFFF"
    bold:         bool          = False
    italic:       bool          = False
    underline:    bool          = False
    strikeout:    bool          = False
    letter_spacing: int           = 0
    angle:        int           = 0
    scale_x:      int           = 100
    scale_y:      int           = 100
    
    # ── Background box
    box:          bool          = False
    box_color:    str           = "#000000FF"
    box_padding:  int           = 1     
 
    # ── Drop shadow
    shadow:       bool          = False
    shadow_color: str           = "#000000FF"
    shadow_offset: int          = 0                        
 
    # ── Border
    outline_width: int           = 1             
    outline_color: str           = "#000000FF"
 
    # ── Vertical position
    vertical_position: str      = "center"
 
    # ── Horizontal position
    horizontal_position: str    = "center"

    # ── Encoding (ASS encoding value; 1 = OS default, most cases UTF-8)
    encoding:           int           = 1
 

@dataclass
class TextSegment:
    """One piece of text with its own timing and style."""
    text:       str
    start_time: float                       # seconds; use 0 for "always on"
    end_time:   float                       # seconds
    style:      TextStyle = field(default_factory=TextStyle)

class WrapValues:
    """Values used for text wrapping, extracted from a TextStyle or a style dict."""

    def __init__(self, style):
        if isinstance(style, TextStyle):
            self.font_size      = style.font_size
            self.font_file      = style.font_file
            self.bold           = style.bold
            self.italic         = style.italic
            self.letter_spacing = style.letter_spacing
            self.angle          = style.angle
        else:  # dict from API
            _d = TextStyle()
            self.font_size      = int(style['font_size'])
            self.font_file      = style.get('font_file', _d.font_file)
            self.bold           = bool(style.get('bold', _d.bold))
            self.italic         = bool(style.get('italic', _d.italic))
            self.letter_spacing = int(style['letter_spacing'])
            self.angle          = int(style['angle'])

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
                # Use a fixed 1080p reference space so that all style values stay independent of actual video resolution.
                ass_file.write_text(
                    self._build_ass_content(lines, PLAY_RES_X, PLAY_RES_Y), encoding="utf-8"
                )

                # Copy any custom font files into the temp dir so libass can find them
                unique_fonts = [
                    pathlib.Path(line.style.font_file)
                    for line in lines
                    if line.style.font_file
                ]
                for font_path in unique_fonts:
                    if font_path.is_file():
                        # Prefix with parent folder name to avoid collisions when two fonts from different subdirectories share the same filename.
                        dest_name = f"{font_path.parent.name}_{font_path.name}"
                        shutil.copy2(font_path, temp_dir_path / dest_name)

                escaped_ass  = self._escape_ass_path(ass_file)
                escaped_fonts = self._escape_ass_path(temp_dir_path)
                filter_str = f"subtitles='{escaped_ass}':fontsdir='{escaped_fonts}'"

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

    def _get_proper_font_name(self, font_file: str) -> str:
        """Read the internal full name (nameID 4) from a font file so libass can match it.
        Falls back to the file stem if the name table can't be read."""
        try:
            with ttLib.TTFont(font_file) as tt:
                for record in tt['name'].names:
                    if record.nameID == 4 and record.platformID == 3:
                        return record.toUnicode()
                # fallback: first nameID 4 record regardless of platform
                for record in tt['name'].names:
                    if record.nameID == 4:
                        return record.toUnicode()
        except Exception:
            pass
        return pathlib.Path(font_file).stem

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


    def wrap_text(self, text: str, wrap_values: WrapValues, play_res_x: int) -> str:
        """Pre-wrap text using \\N (ASS hard break) so long words don't overflow the frame."""
        usable_px      = play_res_x*0.8 # 10% marginX on each side
        char_width_factor = 1.0
        """Checked manually if there is any difference between both of them applied, there's none so we can scale it like that"""
        if wrap_values.bold or wrap_values.italic:
            char_width_factor *= 1.1
        char_width = wrap_values.font_size * get_char_width_ratio() * char_width_factor + wrap_values.letter_spacing
        chars_per_line = max(1, int(usable_px / char_width))

        # split over long words first
        words = []
        for word in text.split():
            while len(word) > chars_per_line:
                words.append(word[:chars_per_line])
                word = word[chars_per_line:]
            if word:
                words.append(word)

        lines = []
        current = ""
        for word in words:
            if not current:
                current = word
            elif len(current) + 1 + len(word) <= chars_per_line:
                current += " " + word
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)

        return "\\N".join(lines)

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


    def _style_to_ass_line(self, style: TextStyle, style_name: str, height: int = 1080, mode: str = "no_box") -> str:
        """Convert a TextStyle to a single ASS [V4+ Styles] line.
           ASS field goes as: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, TertiaryColour, BackColour, 
           Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, 
           Outline, Shadow, Alignment, MarginL, MarginR, MarginV, AlphaLevel, Encoding

           mode:
                 "box_only"     — bottom layer of a combined box+border render
                 "no_box"       — top layer: transparent fill so only the outline ring is visible
        """
        primary_color = self._color_to_ass(style.font_color)
        secondary_color = "&H000000FF"

        #render a transparent text so the bounding box is drawn
        if mode =="box_only":
            primary_color = "&HFF" + primary_color[4:]
            border_style  = 3
            outline       = max(style.box_padding, 1)  
            shadow        = 0
            # set both for libass build compability
            outline_color = self._color_to_ass(style.box_color)
            back_color    = self._color_to_ass(style.box_color)
        else:
            border_style  = 1
            outline       = style.outline_width
            outline_color = self._color_to_ass(style.outline_color)
            shadow        = style.shadow_offset if style.shadow else 0
            back_color    = self._color_to_ass(style.shadow_color) if style.shadow else "&HFF000000"

        alignment = self._position_to_alignment(style.horizontal_position, style.vertical_position)
        font_name = self._get_proper_font_name(style.font_file) if style.font_file else "Arial"
        
        fields = [
            style_name, font_name, str(style.font_size),
            primary_color, secondary_color, outline_color, back_color,
            #apply hardcoded later
            str(int(style.bold)), str(int(style.italic)), str(-int(style.underline)), str(-int(style.strikeout)), #bold (0,1), italic(0,1), underline(0,-1),strikeout(0,-1) 
            str(style.scale_x), str(style.scale_y),  # ScaleX, ScaleY
            str(style.letter_spacing),                   # Letter Spacing
            str((360-style.angle) % 360),       # Angle, -360- to match frontend view
            str(border_style), str(outline), str(shadow),
            str(alignment),
            "10", "10", str(int(height * 0.14)) if style.vertical_position in ("top", "bottom") else "0",  # MarginL, MarginR, MarginV
            str(style.encoding),   # Encoding
        ]
        return "Style: " + ",".join(fields)

    def _build_ass_content(self, lines: list[TextSegment], playResX: int, playResY: int) -> str:
        """Generate an ASS subtitle file with one style entry per unique TextStyle.
        When a style has both box and outline, two layered styles/events are emitted.
        """
        unique_styles: list[TextStyle] = []
        style_indices: list[int] = []
        for line in lines:
            try:
                idx = unique_styles.index(line.style)
            except ValueError:
                idx = len(unique_styles)
                unique_styles.append(line.style)
            style_indices.append(idx)

        style_lines_list = []
        # if box checked draw empty box as 1st layer, then text with outline+shadow taken into considerate as second layer
        # else simply draw the text
        for i, s in enumerate(unique_styles):
            if s.box:
                # Two styles: box layer (bottom) + outline layer (top)
                style_lines_list.append(self._style_to_ass_line(s, f"Style{i}b", playResY, mode="box_only"))
                style_lines_list.append(self._style_to_ass_line(s, f"Style{i}o", playResY, mode="no_box"))
            else:
                style_lines_list.append(self._style_to_ass_line(s, f"Style{i}", playResY, mode="no_box"))
        style_lines = "\n".join(style_lines_list)

        header = (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            "WrapStyle: 2\n"
            "ScaledBorderAndShadow: yes\n"
            f"PlayResX: {playResX}\n"
            f"PlayResY: {playResY}\n"
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
            text = self.wrap_text(line.text, WrapValues(line.style), playResX)
            if line.style.box:
                # Layer 0: box underneath, Layer 1: outline on top
                events.append(f"Dialogue: 0,{start},{end},Style{style_idx}b,,0,0,0,,{text}")
                events.append(f"Dialogue: 1,{start},{end},Style{style_idx}o,,0,0,0,,{text}")
            else:
                events.append(f"Dialogue: 0,{start},{end},Style{style_idx},,0,0,0,,{text}")
        return header + "\n".join(events) + "\n"
        
# testing main, to be removed later
if __name__ == "__main__":

    VIDEO_DIR  = pathlib.Path(__file__).parent.parent / "uploads" / "video"
    OUTPUT_DIR  = pathlib.Path(__file__).parent.parent / "uploads" / "output"
    vid = "karabin cut.mp4"
    video_path = VIDEO_DIR / vid
    burner = TextBurner()
    out = OUTPUT_DIR / f"{video_path.stem}_burned.mp4"
    linesRaw = [
        {'text': 'aaa', 'timestamp': 0.36786, 'style': {'font_file': 'Abril_Fatface/AbrilFatface-Regular.ttf', 'font_size': 64, 'font_color': '#FFFFFFFF', 'box': False, 'box_color': '#000000FF', 'box_padding': 1, 'shadow': False, 'shadow_color': '#000000FF', 'shadow_offset': 1, 'outline_width': 1, 'outline_color': '#000000FF', 'vertical_position': 'center', 'horizontal_position': 'center', 'bold': False, 'italic': False, 'underline': False, 'strikeout': False, 'letter_spacing': 0, 'angle': 0, 'scale_x': 100, 'scale_y': 100, 'encoding': 1}, 'wrappedText': ['aaa']},
        {'text': 'aaaaa', 'timestamp': 1.170463, 'style': {'font_file': 'Cabin/Cabin-Regular.ttf', 'font_size': 64, 'font_color': '#ffffffFF', 'box': False, 'box_color': '#000000FF', 'box_padding': 1, 'shadow': False, 'shadow_color': '#000000FF', 'shadow_offset': 1, 'outline_width': 1, 'outline_color': '#000000FF', 'vertical_position': 'center', 'horizontal_position': 'center', 'bold': False, 'italic': False, 'underline': False, 'strikeout': False, 'letter_spacing': 0, 'angle': 0, 'scale_x': 100, 'scale_y': 100, 'encoding': 1}, 'wrappedText': ['aaaaa']},
        {'text': 'aaa', 'timestamp': 2.307484, 'style': {'font_file': 'Montserrat/Montserrat-Regular.ttf', 'font_size': 64, 'font_color': '#ffffffFF', 'box': False, 'box_color': '#000000FF', 'box_padding': 1, 'shadow': False, 'shadow_color': '#000000FF', 'shadow_offset': 1, 'outline_width': 1, 'outline_color': '#000000FF', 'vertical_position': 'center', 'horizontal_position': 'center', 'bold': False, 'italic': False, 'underline': False, 'strikeout': False, 'letter_spacing': 0, 'angle': 0, 'scale_x': 100, 'scale_y': 100, 'encoding': 1}, 'wrappedText': ['aaa']},
        {'text': 'bbbbbb', 'timestamp': 3.076645,'style': {'font_file': 'Roboto/Roboto-Regular.ttf', 'font_size': 64, 'font_color': '#ffffffFF', 'box': False, 'box_color': '#000000FF', 'box_padding': 1, 'shadow': False, 'shadow_color': '#000000FF', 'shadow_offset': 1, 'outline_width': 1, 'outline_color': '#000000FF', 'vertical_position': 'center', 'horizontal_position': 'center', 'bold': False, 'italic': False, 'underline': False, 'strikeout': False, 'letter_spacing': 0, 'angle': 0, 'scale_x': 100, 'scale_y': 100, 'encoding': 1} , 'wrappedText': ['bbbbbb']},
    ]
    linesTextSegments = [
        TextSegment(text='aaa', start_time=0.36786, end_time=1.170463, style=TextStyle(font_file='D:\\vocalRemovalApp\\backend\\static\\fonts\\Abril_Fatface\\AbrilFatface-Regular.ttf', font_size=64, font_color='#FFFFFFFF', bold=False, italic=False, underline=False, strikeout=False, letter_spacing=0, angle=0, scale_x=100, scale_y=100, box=False, box_color='#000000FF', box_padding=1, shadow=False, shadow_color='#000000FF', shadow_offset=1, outline_width=1, outline_color='#000000FF', vertical_position='center', horizontal_position='center', encoding=1)),
        TextSegment(text='aaaaa', start_time=1.170463, end_time=2.307484, style=TextStyle(font_file='D:\\vocalRemovalApp\\backend\\static\\fonts\\Cabin\\Cabin-Regular.ttf', font_size=64, font_color='#ffffffFF', bold=False, italic=False, underline=False, strikeout=False, letter_spacing=0, angle=0, scale_x=100, scale_y=100, box=False, box_color='#000000FF', box_padding=1, shadow=False, shadow_color='#000000FF', shadow_offset=1, outline_width=1, outline_color='#000000FF', vertical_position='center', horizontal_position='center', encoding=1)),
        TextSegment(text='aaa', start_time=2.307484, end_time=3.076645, style=TextStyle(font_file='D:\\vocalRemovalApp\\backend\\static\\fonts\\Montserrat\\Montserrat-Regular.ttf', font_size=64, font_color='#ffffffFF', bold=False, italic=False, underline=False, strikeout=False, letter_spacing=0, angle=0, scale_x=100, scale_y=100, box=False, box_color='#000000FF', box_padding=1, shadow=False, shadow_color='#000000FF', shadow_offset=1, outline_width=1, outline_color='#000000FF', vertical_position='center', horizontal_position='center', encoding=1)),
        TextSegment(text='bbbbbb', start_time=3.076645, end_time=None, style=TextStyle(font_file='D:\\vocalRemovalApp\\backend\\static\\fonts\\Roboto\\Roboto-Regular.ttf', font_size=64, font_color='#ffffffFF', bold=False, italic=False, underline=False, strikeout=False, letter_spacing=0, angle=0, scale_x=100, scale_y=100, box=False, box_color='#000000FF', box_padding=1, shadow=False, shadow_color='#000000FF', shadow_offset=1, outline_width=1, outline_color='#000000FF', vertical_position='center', horizontal_position='center', encoding=1))
    ]
    
    _probe_and_set_duration(video_path)
    video_duration = get_video_duration()
    print(f"Video duration: {video_duration} seconds")
    print(f"--- Burning subtitles → {out} ---")
    try:
        out = burner.burn(video_path=video_path, output_path=out, lines=linesRaw, verbose=True)
    except RuntimeError as e:
        print(e)
    

    print("Done")
