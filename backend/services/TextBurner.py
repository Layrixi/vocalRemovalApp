import subprocess
import pathlib
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Optional
import shutil
sys.path.append(str(pathlib.Path(__file__).parent.parent))
from config import set_video_duration, get_video_duration

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
    Probe video duration using ffprobe and store it in config.
    Used for testing and video processing.
    """
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            capture_output=True, text=True, check=True,
        )
        set_video_duration(float(probe.stdout.strip()))
    except Exception:
        set_video_duration(0.0)
    
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
    font_color:   str           = "white"
 
    # ── Background box
    box:          bool          = True
    box_color:    str           = "black@0.7"
    box_padding:  int           = 10            
 
    # ── Drop shadow
    shadow:       bool          = False
    shadow_color: str           = "black@0.6"
    shadow_x:     int           = 3             
    shadow_y:     int           = 3             
 
    # ── Border
    border_width: int           = 0             
    border_color: str           = "black"
 
    # ── Vertical position
    vertical_position: str      = "center"
 
    # ── Horizontal position
    horizontal_position: str    = "center"
 
    # ── Spacing
    line_spacing: int           = 10            

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
            #write text to a ttemporary file (special characters with ffmpeg issue) and build the filter arguments for ffmpeg
            with tempfile.TemporaryDirectory(prefix="karaoke_textburner_") as temp_dir:
                temp_dir_path = pathlib.Path(temp_dir)

                filter_lines = ",".join(
                    self._build_drawtext_filter(
                        style=line.style,
                        start_time=line.start_time,
                        end_time=line.end_time,
                        text_file=self._write_text_file(temp_dir_path, index, line.text),
                    )
                    for index, line in enumerate(lines)
                )

                self._run_ffmpeg([
                    self.ffmpeg_path, '-y',
                    '-i', str(video_path),
                    '-vf', filter_lines,
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
   
    def _escape(self, text: str) -> str:
        """Saves ffmpeg from breaking by misinterpreting special characters in the subtitle text."""
        return (
            text
            .replace("\\", "\\\\")
            .replace("'",  "\\'")
            .replace(":",  "\\:")
            .replace(",",  "\\,")
            .replace("%",  "\\%")
        )

    def _write_text_file(self, temp_dir: pathlib.Path, index: int, text: str) -> pathlib.Path:
        text_file = temp_dir / f"line_{index}.txt"
        text_file.write_text(text, encoding="utf-8")
        return text_file

    def _escape_path(self, path: str | pathlib.Path) -> str:
        return self._escape(pathlib.Path(path).as_posix())

    def _run_ffmpeg(self, cmd: list[str], verbose: bool):
        if verbose:
            print("Running:", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=not verbose, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")
    
   

    #to implement later,basically rgb hex etc. to ASS
    def _position_expr(self, dimension: str, text_dimension: str, position: str = "center") -> str:
        """
        Translate a named position into an ffmpeg expression. Returns either center
        dimension      : "w" (width) or "h" (height)
        text_dimension : "tw" or "th"
        position       : "center" or treats as a raw pixel value / expression
        """
        if position == "center":
            return f"({dimension} - {text_dimension})/2"
        else:
            # treat as a raw pixel value / expression
            return position
    def _build_drawtext_filter(self, style: TextStyle, start_time: Optional[float] = None,
                            end_time: Optional[float] = None, text: Optional[str] = None,
                            text_file: Optional[str | pathlib.Path] = None) -> str:
        """Build a single drawtext filter fragment."""
    
        x = self._position_expr("w", "tw", style.horizontal_position)
        y = self._position_expr("h", "th", style.vertical_position)
    
        if text_file is not None:
            text_part = f"textfile='{self._escape_path(text_file)}'"
        elif text is not None:
            text_part = f"text='{self._escape(text)}'"
        else:
            raise ValueError("Either text or text_file must be provided.")

        parts = [
            text_part,
            f"fontsize='{style.font_size}'",
            f"fontcolor='{style.font_color}'",
            f"x='{x}'",
            f"y='{y}'",
            f"line_spacing='{style.line_spacing}'",
        ]
    
        if style.font_file:
            parts.append(f"fontfile='{style.font_file}'")
    
        if style.box:
            parts += [
                f"box='1'",
                f"boxcolor='{style.box_color}'",
                f"boxborderw='{style.box_padding}'",
            ]
    
        if style.shadow:
            parts += [
                f"shadowcolor='{style.shadow_color}'",
                f"shadowx='{style.shadow_x}'",
                f"shadowy='{style.shadow_y}'",
            ]
    
        if style.border_width > 0:
            parts += [
                f"borderw='{style.border_width}'",
                f"bordercolor='{style.border_color}'",
            ]
    
        # May generate a bug, if video is less than 99999 seconds and start time is not provided it may expand the video length    
        # to test later
        if start_time is not None:
            effective_end = end_time if end_time is not None else (get_video_duration() or 99999)
            parts.append(f"enable='between(t\\,{start_time}\\,{effective_end})'")
    
        return "drawtext=" + ":".join(parts)
        
# testing main, to be removed later
if __name__ == "__main__":

    VIDEO_DIR  = pathlib.Path(__file__).parent.parent / "uploads" / "video"
    OUTPUT_DIR  = pathlib.Path(__file__).parent.parent / "uploads" / "output"
    vid = "chronos tester.mp4"
    video_path = VIDEO_DIR / vid
    burner = TextBurner()

    #didnt define style, it will take default, in the final app it will be taken from the frontend, to be changed later
    LINES = [
        TextSegment(text="Hello world",        start_time=0.0, end_time=1.0),
        TextSegment(text="TextBurner works",   start_time=1.0, end_time=2.0),
        TextSegment(text="Subtitles on video", start_time=2.0, end_time=3.0),
        TextSegment(text="Done",               start_time=3.0, end_time=4.0),
    ]
    LINES2 = [
        TextSegment(text='Sudden ringing, I slowly get up', start_time=0.0, end_time=4.519145, style=TextStyle(font_file=None, font_size=64, font_color='white', box=True, box_color='black@0.7', box_padding=10, shadow=False, shadow_color='black@0.6', shadow_x=3, shadow_y=3, border_width=0, border_color='black', vertical_position='center', horizontal_position='center', line_spacing=10)),
        TextSegment(text='And turn off the noise, already fed up', start_time=4.519145, end_time=5.561934, style=TextStyle(font_file=None, font_size=64, font_color='white', box=True, box_color='black@0.7', box_padding=10, shadow=False, shadow_color='black@0.6', shadow_x=3, shadow_y=3, border_width=0, border_color='black', vertical_position='center', horizontal_position='center', line_spacing=10)), 
        TextSegment(text='And turn off the noise, already fed', start_time=5.561934, end_time=6.772827, style=TextStyle(font_file=None, font_size=64, font_color='white', box=True, box_color='black@0.7', box_padding=10, shadow=False, shadow_color='black@0.6', shadow_x=3, shadow_y=3, border_width=0, border_color='black', vertical_position='center', horizontal_position='center', line_spacing=10)), 
        TextSegment(text="Reminding me that tomorrow's hopeless", start_time=6.772827, end_time=7.849959, style=TextStyle(font_file=None, font_size=64, font_color='white', box=True, box_color='black@0.7', box_padding=10, shadow=False, shadow_color='black@0.6', shadow_x=3, shadow_y=3, border_width=0, border_color='black', vertical_position='center', horizontal_position='center', line_spacing=10)), 
        TextSegment(text="I'm slowly rotting inside a jail cell", start_time=7.849959, end_time=None, style=TextStyle(font_file=None, font_size=64, font_color='white', box=True, box_color='black@0.7', box_padding=10, shadow=False, shadow_color='black@0.6', shadow_x=3, shadow_y=3, border_width=0, border_color='black', vertical_position='center', horizontal_position='center', line_spacing=10))]

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
