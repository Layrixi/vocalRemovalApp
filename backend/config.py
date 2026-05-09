import pathlib
import torch

VIDEO_LEN: float = 0.0
PLAY_RES_X: int = 1920              # fixed play resolution consistent scaling factor. Do not overwrite.
PLAY_RES_Y: int = 1080
VIDEO_W:   int   = 1920             # actual video dimensions, set at runtime after upload
VIDEO_H:   int   = 1080
CHAR_WIDTH_RATIO: float = 0.5
FONTS_DIR : pathlib.Path = pathlib.Path(__file__).parent / "static" / "fonts"

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