import os
import sys
import subprocess
import tempfile
import shutil
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

COOKIE_SECRET_PATH = '/etc/secrets/cookies.txt'
TMP_COOKIE_PATH = '/tmp/cookies.txt'

def prepare_cookies():
    """Копирует cookies из Secret File в /tmp, чтобы yt-dlp мог писать."""
    if os.path.exists(COOKIE_SECRET_PATH):
        shutil.copyfile(COOKIE_SECRET_PATH, TMP_COOKIE_PATH)
        return TMP_COOKIE_PATH
    return None

def get_stream_url(youtube_url, quality='best[height<=720]'):
    cookies = prepare_cookies()
    cmd = [
        sys.executable, '-m', 'yt_dlp',
        '-f', quality,
        '-g',
        '--no-playlist',
        '--add-header', 'User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        '--add-header', 'Accept-Language:en-US,en;q=0.9',
        youtube_url
    ]
    if cookies:
        cmd += ['--cookies', cookies]
    # Указываем Node.js для плагина yt-dlp-ejs
    os.environ['NODE_PATH'] = '/usr/lib/node_modules'
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise Exception(result.stderr.strip())
    return result.stdout.strip()

@app.route('/stream-url', methods=['POST'])
def stream_url():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'No URL'}), 400
    try:
        stream_link = get_stream_url(url)
        return jsonify({'stream_url': stream_link})
    except Exception as e:
        return jsonify({'error': str(e)[-300:]}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
