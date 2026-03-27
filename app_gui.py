#!/usr/bin/env python3
"""
Веб-сервер с графическим интерфейсом для USB-камеры
Оптимизированная версия с правильным потоковым видео
"""

import cv2
from flask import Flask, Response, render_template_string
import time
import threading

app = Flask(__name__)

# HTML шаблон с графическим интерфейсом
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>USB Camera Control Panel</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        h1 {
            text-align: center;
            color: #00adb5;
            margin-bottom: 20px;
        }
        
        .camera-panel {
            background: #0f3460;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .video-container {
            text-align: center;
        }
        
        .video-container img {
            max-width: 100%;
            border-radius: 10px;
            border: 3px solid #00adb5;
            background: #000;
        }
        
        .controls {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .control-group {
            background: #1a1a2e;
            border-radius: 10px;
            padding: 15px;
        }
        
        .control-group h3 {
            color: #00adb5;
            margin-bottom: 15px;
            text-align: center;
        }
        
        .button-group {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: center;
        }
        
        button {
            background: #00adb5;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        button:hover {
            background: #008b93;
            transform: scale(1.05);
        }
        
        .info-panel {
            background: #1a1a2e;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }
        
        .status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .status.online {
            background: #4caf50;
            color: white;
        }
        
        .ip-address {
            background: #0f3460;
            padding: 5px 10px;
            border-radius: 5px;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📹 USB Camera Live Stream</h1>
        
        <div class="camera-panel">
            <div class="video-container">
                <img id="camera-feed" src="{{ url_for('video_feed') }}" alt="Camera Feed">
            </div>
            
            <div class="info-panel">
                <p>📷 Статус: <span id="status" class="status online">ОНЛАЙН</span></p>
                <p>🌐 IP-адрес: <span class="ip-address">{{ ip_address }}:5000</span></p>
            </div>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <h3>🔄 Управление</h3>
                <div class="button-group">
                    <button onclick="location.reload()">🔄 Обновить</button>
                    <button onclick="resetCamera()">📷 Сброс</button>
                </div>
            </div>
        </div>
        
        <div class="info-panel">
            <p>💡 Полноэкранный режим: <a href="/video_only" target="_blank" style="color: #00adb5;">/video_only</a></p>
        </div>
    </div>
    
    <script>
        function resetCamera() {
            fetch('/reset')
                .then(response => response.json())
                .then(data => {
                    console.log('Camera reset');
                });
        }
        
        function checkStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    let statusEl = document.getElementById('status');
                    if (data.camera_working) {
                        statusEl.className = 'status online';
                        statusEl.textContent = 'ОНЛАЙН';
                    } else {
                        statusEl.className = 'status offline';
                        statusEl.textContent = 'ОФЛАЙН';
                    }
                });
        }
        
        setInterval(checkStatus, 5000);
    </script>
</body>
</html>
'''

# Глобальные переменные
frame = None
lock = threading.Lock()
camera = None

def init_camera():
    """Инициализация камеры"""
    global camera
    
    print("📷 Подключение к камере...")
    camera = cv2.VideoCapture(0)
    
    if not camera.isOpened():
        print("❌ Ошибка: не удалось открыть камеру")
        return False
    
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    w = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"✅ Камера готова: {w}x{h}")
    
    return True

def capture_thread():
    """Поток для захвата кадров"""
    global frame, camera
    
    while True:
        if camera and camera.isOpened():
            ret, img = camera.read()
            if ret:
                with lock:
                    frame = img.copy()
        time.sleep(0.03)  # ~30 fps

def get_ip():
    """Получение IP-адреса"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "192.168.1.53"

@app.route('/')
def index():
    """Главная страница"""
    return render_template_string(HTML_TEMPLATE, ip_address=get_ip())

@app.route('/video_feed')
def video_feed():
    """Видеопоток MJPEG"""
    def generate():
        while True:
            with lock:
                if frame is not None:
                    ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            # Контроль частоты кадров - не чаще 30 FPS
            time.sleep(0.033)
    
    return Response(generate(), 
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_only')
def video_only():
    """Страница только с видео"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Video Stream</title>
        <style>
            body { margin: 0; background: black; }
            img { width: 100%; height: 100vh; object-fit: contain; }
        </style>
    </head>
    <body>
        <img src="/video_feed">
    </body>
    </html>
    '''

@app.route('/reset')
def reset():
    """Сброс камеры"""
    global camera, frame
    if camera:
        camera.release()
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        with lock:
            frame = None
    return {'status': 'ok'}

@app.route('/status')
def status():
    """Проверка статуса"""
    with lock:
        has_frame = frame is not None
    return {'camera_working': has_frame}

@app.teardown_appcontext
def cleanup(exception=None):
    """Очистка при завершении"""
    global camera
    if camera:
        camera.release()
    print("📷 Камера освобождена")

if __name__ == '__main__':
    print("=" * 60)
    print("🎥 USB Camera Web Server - Live Stream")
    print("=" * 60)
    
    if init_camera():
        thread = threading.Thread(target=capture_thread)
        thread.daemon = True
        thread.start()
        print("✅ Поток захвата запущен")
    
    ip = get_ip()
    print(f"🌐 http://localhost:5000")
    print(f"🌐 http://{ip}:5000")
    print("=" * 60)
    print("Нажмите CTRL+C для остановки")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
