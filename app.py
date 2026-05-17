import os
import sys
import subprocess
import tempfile
import shutil
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

COOKIE_PATHS = [
    '/etc/secrets/cookies.txt',
    'cookies.txt'
]

def find_and_prepare_cookies():
    # ... (эта функция остаётся без изменений) ...
    for src_path in COOKIE_PATHS:
        if os.path.exists(src_path):
            if src_path != '/etc/secrets/cookies.txt' or os.access(src_path, os.W_OK):
                return src_path
            fd, tmp_path = tempfile.mkstemp(suffix='.txt', prefix='cookies_')
            with os.fdopen(fd, 'w') as f_out:
                with open(src_path, 'r') as f_in:
                    shutil.copyfileobj(f_in, f_out)
            return tmp_path
    return None

def stream_video(url, cookies_path):
    """Запускает yt-dlp и отдаёт видео потоком (без сохранения на диск)."""
    command = [
        sys.executable, '-m', 'yt_dlp',
        '-o', '-',  # Вывод в stdout
        '-f', 'best[height<=720]',
        '--no-playlist',
        '--add-header', 'User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        '--cookies', cookies_path,
        url
    ]

    # Указываем путь к Node.js для плагина yt-dlp-ejs
    os.environ['NODE_PATH'] = '/usr/lib/node_modules'

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process

@app.route('/stream', methods=['POST'])
def stream():
    """Стриминг видео напрямую в браузер."""
    data = request.get_json()
    url = data.get('url') if data else None
    if not url:
        return jsonify({'error': 'URL не указан'}), 400

    cookies_path = find_and_prepare_cookies()
    if not cookies_path:
        return jsonify({'error': 'Файл cookies.txt не найден.'}), 500

    process = stream_video(url, cookies_path)
    return Response(process.stdout, mimetype='video/mp4')

@app.route('/download', methods=['POST'])
def download_video():
    data = request.get_json()
    url = data.get('url') if data else None
    if not url:
        return jsonify({'error': 'URL не указан'}), 400

    cookies_path = find_and_prepare_cookies()
    if not cookies_path:
        return jsonify({'error': 'Файл cookies.txt не найден.'}), 500

    temp_dir = tempfile.mkdtemp(prefix='ytdl_')
    output_template = os.path.join(temp_dir, '%(title)s.%(ext)s')

    command = [
        sys.executable, '-m', 'yt_dlp',
        '-o', output_template,
        '-f', 'best[height<=720]',
        '--no-playlist',
        '--merge-output-format', 'mp4',
        '--add-header', 'User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        '--cookies', cookies_path,
        url
    ]

    os.environ['NODE_PATH'] = '/usr/lib/node_modules'

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or 'Неизвестная ошибка'
            shutil.rmtree(temp_dir, ignore_errors=True)
            return jsonify({'error': f'Ошибка при скачивании: {error_msg[-300:]}'}), 500

        files = os.listdir(temp_dir)
        video_files = [f for f in files if f.endswith(('.mp4', '.mkv', '.webm'))]

        if not video_files:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return jsonify({'error': 'Файл не найден после скачивания'}), 500

        filepath = os.path.join(temp_dir, video_files[0])

        response = send_file(
            filepath,
            as_attachment=True,
            download_name=video_files[0],
            mimetype='video/mp4'
        )

        @response.call_on_close
        def cleanup():
            shutil.rmtree(temp_dir, ignore_errors=True)
            if cookies_path.startswith(tempfile.gettempdir()):
                try:
                    os.unlink(cookies_path)
                except:
                    pass

        return response

    except subprocess.TimeoutExpired:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({'error': 'Таймаут (5 минут). Видео слишком большое.'}), 504
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({'error': f'Внутренняя ошибка: {str(e)}'}), 500

@app.route('/')
def index():
    return jsonify({'status': 'ok', 'message': 'API with streaming and download'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
