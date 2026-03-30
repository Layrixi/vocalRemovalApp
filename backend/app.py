from flask import Flask, render_template, request, jsonify, send_from_directory
import uuid
import pathlib

# text burning
import subprocess
import tempfile

import soundfile as sf
from werkzeug.utils import secure_filename
import sys
sys.path.append(str(pathlib.Path(__file__).parent))
from config import check_device
from services.VocalRemovalModelHandler import vocalRemovalModelHandler

UPLOAD_VIDEO_DIR = pathlib.Path(__file__).parent / "uploads" / "video"
UPLOAD_AUDIO_DIR = pathlib.Path(__file__).parent / "uploads" / "audio"
OUTPUT_DIR       = pathlib.Path(__file__).parent / "uploads" / "output"

app = Flask(__name__)

# Load model once at startup so it stays in memory between requests
device = check_device()
removal_handler = vocalRemovalModelHandler(device=device)


@app.route('/')
def index():
    return render_template('index.html')

# using secure_filename is not necessary here since it's only used for local needs,
# but it may stay to prevent any issues with special characters in file names. 
# To be changed later if needed.


# API endpoint to handle video uploads
@app.route('/api/upload-video', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'Empty filename'}), 400
    safe_name = secure_filename(f.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    save_path = UPLOAD_VIDEO_DIR / unique_name
    f.save(str(save_path))
    return jsonify({'filename': unique_name})

# gets the file name from the frontend, checks if it exists,
# passes it directly to the model (librosa handles demuxing internally),
# saves the instrumental and returns a download link to the frontend
@app.route('/api/remove-vocals', methods=['POST'])
def remove_vocals_route():
    # get the file
    data = request.get_json()
    if not data or 'filename' not in data:
        return jsonify({'error': 'No filename provided'}), 400

    safe_name = secure_filename(data['filename'])
    video_path = UPLOAD_VIDEO_DIR / safe_name
    if not video_path.exists() or not video_path.is_file():
        return jsonify({'error': 'File not found'}), 404

    # Pass the video directly in the model handler class — librosa handles demuxing internally
    try:
        instrumental = removal_handler.remove_vocals(str(video_path))
    except Exception as e:
        return jsonify({'error': f'Vocal removal failed: {e}'}), 500

    output_filename = f"{video_path.stem}_instrumental.wav"
    output_path = OUTPUT_DIR / output_filename
    sf.write(str(output_path), instrumental.T, removal_handler.model.samplerate)

    return jsonify({'download_url': f'/api/download/{output_filename}'})


@app.route('/api/download/<filename>')
def download_file(filename):
    safe_name = secure_filename(filename)
    return send_from_directory(str(OUTPUT_DIR), safe_name, as_attachment=True)


#helpers

def _srt_time(secs: float) -> str:
    """Convert seconds (float) to SRT timestamp HH:MM:SS,mmm."""
    h  = int(secs // 3600)
    m  = int((secs % 3600) // 60)
    s  = int(secs % 60)
    ms = int(round((secs % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _build_srt(lines: list) -> str:
    """Build an SRT string from a list of {text, timestamp} dicts."""
    sorted_lines = sorted(lines, key=lambda x: float(x['timestamp']))
    entries = []
    for i, line in enumerate(sorted_lines):
        start = _srt_time(float(line['timestamp']))
        if i + 1 < len(sorted_lines):
            end = _srt_time(max(float(line['timestamp']) + 0.1,
                               float(sorted_lines[i + 1]['timestamp']) - 0.1))
        else:
            end = _srt_time(float(line['timestamp']) + 3.0)
        entries.append(f"{i + 1}\n{start} --> {end}\n{line['text'].upper()}\n")
    return "\n".join(entries)


# POST { filename, lines: [{text, timestamp}, …] }
# Builds SRT from lines, burns it into the video via FFmpeg,
# and returns a download link — no re-upload needed.
@app.route('/api/render-video', methods=['POST'])
def render_video():
    data = request.get_json()
    if not data or 'filename' not in data or 'lines' not in data:
        return jsonify({'error': 'filename and lines required'}), 400

    lines = [l for l in data['lines'] if l.get('timestamp') is not None]
    if not lines:
        return jsonify({'error': 'No synced lines to render'}), 400

    safe_name = secure_filename(data['filename'])
    video_path = UPLOAD_VIDEO_DIR / safe_name
    if not video_path.exists() or not video_path.is_file():
        return jsonify({'error': 'Video file not found'}), 404

    srt_content = _build_srt(lines)
    output_filename = f"{video_path.stem}_subtitled.mp4"
    output_path = OUTPUT_DIR / output_filename

    # Write SRT to a temp file in the same directory as the video.
    srt_path = UPLOAD_VIDEO_DIR / f"{video_path.stem}.srt"
    srt_path.write_text(srt_content, encoding='utf-8')

    try:
        # Forward slashes work on Windows with FFmpeg; escape colons for the
        # subtitles filter's own path parser.
        srt_ffmpeg = str(srt_path).replace('\\', '/').replace(':', '\\:')
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', (
                f"subtitles='{srt_ffmpeg}':force_style="
                "'Alignment=5,Fontname=Syne,Fontsize=22,Bold=1,"
                "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                "Outline=3,BorderStyle=3,BackColour=&H73000000,Shadow=0'"
            ),
            '-c:a', 'copy',
            str(output_path),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            return jsonify({'error': f'FFmpeg failed: {result.stderr[-500:]}'}), 500
    finally:
        srt_path.unlink(missing_ok=True)

    return jsonify({'download_url': f'/api/download/{output_filename}'})


if __name__ == '__main__':
    # debug=false in prod later, change the port adequatly to the pc(if possible)
    # use_reloader=False prevents WinError 10038 (socket inheritance issue on Windows)
    # and avoids loading the heavy ML model twice
    app.run(debug=True, port=5000, use_reloader=False)