from flask import Flask, render_template, request, jsonify, send_from_directory
import uuid
import pathlib
import json

# text burning
import subprocess
import tempfile

import soundfile as sf
from werkzeug.utils import secure_filename
import sys
sys.path.append(str(pathlib.Path(__file__).parent))
from config import check_device, set_video_duration, get_video_duration, get_video_dimensions, get_char_width_ratio, set_video_dimensions
from services.TextBurner import TextBurner, TextSegment, TextStyle
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

    # probe duration and dimensions and store them in config
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "format=duration:stream=width,height",
                "-of", "json",
                str(save_path),
            ],
            capture_output=True, text=True, check=True,
        )
        probe_data = json.loads(probe.stdout)
        set_video_duration(float(probe_data["format"]["duration"]))
        stream = probe_data["streams"][0]
        set_video_dimensions(int(stream["width"]), int(stream["height"]))
    except Exception:
        set_video_duration(0.0)

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

    # Pass the video directly in the model handler class
    try:
        instrumental = removal_handler.remove_vocals(str(video_path))
    except Exception as e:
        return jsonify({'error': f'Vocal removal failed: {e}'}), 500

    # Save instrumental to a temporary WAV, then mux it into the original video
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp_audio_path = pathlib.Path(tmp.name)
    sf.write(str(tmp_audio_path), instrumental.T, removal_handler.model.samplerate)

    output_filename = f"{video_path.stem}_instrumental.mp4"
    output_path = OUTPUT_DIR / output_filename
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-i", str(tmp_audio_path),
                "-c:v", "copy",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                str(output_path),
            ],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Video muxing failed: {e.stderr}'}), 500
    except FileNotFoundError:
        return jsonify({'error': 'Video muxing failed: ffmpeg is not installed or not available in PATH'}), 500
    finally:
        tmp_audio_path.unlink(missing_ok=True)

    return jsonify({'download_url': f'/api/download/{output_filename}'})


@app.route('/api/download/<filename>')
def download_file(filename):
    safe_name = secure_filename(filename)
    return send_from_directory(str(OUTPUT_DIR), safe_name, as_attachment=True)


# POST { filename, lines: [{text, timestamp}, …] }
# Passes the video to the burn function, which burns the text into the video 
# with user-provided style or default one
# and returns a download link — no re-upload needed.
@app.route('/api/render-video', methods=['POST'])
def render_video():
    data = request.get_json()    
    
    if not data or 'filename' not in data or 'lines' not in data:
        return jsonify({'error': 'filename and lines required'}), 400

    lines = [l for l in data['lines'] if l.get('timestamp') is not None]
    if not lines:
        return jsonify({'error': 'No synced lines to render'}), 400
    

    #video preperation
    safe_name = secure_filename(data['filename'])
    video_path = UPLOAD_VIDEO_DIR / safe_name
    if not video_path.exists() or not video_path.is_file():
        return jsonify({'error': 'Video file not found'}), 404
    #remove vocals from the video and use it on the final video later

    #text preparation
    text_segments = [
        # for every line unpack the text, timestamp and style (if it exists) into a TextSegment dataclass
        TextSegment(
            text=line['text'],
            start_time=float(line['timestamp']),
            end_time=float(lines[i + 1]['timestamp']) if i + 1 < len(lines) else None,
            style=TextStyle(**{k: v for k, v in line.get('style', {}).items() if hasattr(TextStyle, k)}),
        )
        for i, line in enumerate(lines)
    ]
    output_filename = f"{video_path.stem}_karaoke.mp4"
    output_path = OUTPUT_DIR / output_filename
    try:
        renderer = TextBurner(ffmpeg_path="ffmpeg")  # May add adjusting path if ffmpeg is not in system PATH, but it's in the readme so may not as well
        renderer.burn(video_path=video_path, output_path=output_path, lines=text_segments)
    except Exception as e:
        return jsonify({'error': f'Video rendering failed: {e}'}), 500

    return jsonify({'download_url': f'/api/download/{output_filename}'})


@app.route('/api/wrap-config', methods=['GET'])
def get_wrap_config():
    """Return the constants needed to replicate TextBurner._wrap_text on the frontend."""
    style = TextStyle()
    video_w, video_h = get_video_dimensions()
    return jsonify({
        'font_size':        style.font_size,
        'char_width_ratio': get_char_width_ratio(),
        'play_res_x':       video_w,
        'play_res_y':       video_h,
    })


if __name__ == '__main__':
    # debug=false in prod later, change the port adequatly to the pc(if possible)
    # use_reloader=False prevents WinError 10038 (socket inheritance issue on Windows)
    # and avoids loading the heavy ML model twice
    app.run(debug=True, port=5000, use_reloader=False)