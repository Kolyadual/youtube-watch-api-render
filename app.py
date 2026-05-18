import os
import sys
import subprocess
import tempfile
import shutil
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

COOKIE_FILE = '/etc/secrets/cookies.txt' if os.path.exists('/etc/secrets/cookies.txt') else None

def get_stream_url(youtube_url, quality='best[height<=720]'):
    """Извлекает прямую ссылку на видео (поток) без скачивания"""
    cmd = [
        sys.executable, '-m', 'yt_dlp',
        '-f', quality,
        '-g',  # <-- магия: вывести URL потока
        '--no-playlist',
        '--add-header', 'User-Agent:Mozilla/5.0 ...',
        youtube_url
    ]
    if COOKIE_FILE:
        cmd += ['--cookies', COOKIE_FILE]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise Exception(result.stderr)
    return result.stdout.strip()

@app.route('/stream-url', methods=['POST'])
def stream_url():
    """Отдаёт плееру прямую ссылку на поток"""
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'No URL'}), 400
    try:
        stream_link = get_stream_url(url)
        return jsonify({'stream_url': stream_link})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/proxy-video')
def proxy_video():
    """Проксирует видеофайл напрямую (если нужен именно файл)"""
    # ... (уже было, можно оставить)
    pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
