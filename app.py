#!/usr/bin/env python3
"""
Простой веб-сервер для передачи видео с USB-камеры
"""

import cv2
from flask import Flask, Response, render_template_string
import time
import os

app = Flask(__name__)

# HTML шаблон для веб-страницы
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>USB Camera Stream</title>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            text-align: center;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        h1 {
            color: #00adb5;
            margin-bottom: 10px;
        }
        .video-container {
            margin: 20px auto;
            background: #0f3460;
            padding: 20px;
            border-radius: 15px;
            display: inline-block;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        img {
            border: 3px solid #00adb5;
            border-radius: 8px;
            max-width: 100%;
            height: auto;
            background: #000;
        }
        .info {
            margin-top: 20px;
            color: #888;
            font-size: 14px;
        }
        .status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            margin-bottom: 15px;
        }
        .status-online {
            background: #00adb5;
            color: #fff;
        }
        .status-offline {
            background: #f05454;
            color: #fff;
        }
        button {
            background-color: #00adb5;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }
        button:hover {
            background-color: #008b93;
            transform: scale(1.02);
        }
        .ip {
            font-family: monospace;
            background: #0f3460;
            padding: 5px 10px;
            border-radius: 5px;
            display: inline-block;
        }
    </style>
</head>
<body>
    <h1>📹 USB Camera Stream</h1>
    <div class="status status-online" id="status">🟢 ONLINE</div>
    <div class="video-container">
        <img src="{{ url_for('video_feed') }}" width="800" id="camera-feed">
    </div>
    <div class="info">
        <p>🌐 Доступ с других устройств: <span class="ip">{{ ip_address }}</span>:5000</p>
        <p>📷 Разрешение: 640x480 | FPS: ~30</p>
        <button onclick="location.reload()">🔄 Обновить страницу</button>
        <button onclick="window.location.href='/reset'">🔄 Перезапустить камеру</button>
    </div>
    <script>
        // Автоматическое обновление статуса
        setInterval(function() {
            var img = document.getElementById('camera-feed');
            var status = document.getElementById('status');
            var timestamp = new Date().getTime();
            img.src = "{{ url_for('video_feed') }}?t=" + timestamp;
        }, 5000);
    </script>
</body>
</html>
'''

# Глобальная переменная для камеры
camera = None
camera_index = None

def find_camera():
    """Автоматический поиск камеры по индексам"""
    global camera_index
    for index in [0, 2, 4, 6, 8, 10, 12, 14, 16]:
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            cap.release()
            camera_index = index
            print(f"✅ Камера найдена на /dev/video{index}")
            return index
    print("❌ Камера не найдена! Проверьте подключение.")
    return None

def get_camera():
    """Инициализация камеры"""
    global camera, camera_index
    
    if camera is None:
        print("📷 Инициализация камеры...")
        if camera_index is None:
            camera_index = find_camera()
        
        if camera_index is not None:
            camera = cv2.VideoCapture(camera_index)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Проверка реального разрешения
            width = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
            print(f"✅ Камера готова: {int(width)}x{int(height)}")
        else:
            print("❌ Нет доступных камер")
    
    return camera

def get_ip():
    """Получение IP-адреса Raspberry Pi"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "192.168.1.53"

def generate_frames():
    """Генератор кадров для видеопотока"""
    while True:
        cap = get_camera()
        
        if cap is None or not cap.isOpened():
            # Если камеры нет, отправляем заглушку
            time.sleep(0.1)
            continue
        
        ret, frame = cap.read()
        if ret:
            # Кодируем кадр в JPEG
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        else:
            time.sleep(0.05)

@app.route('/')
def index():
    """Главная страница"""
    return render_template_string(HTML_TEMPLATE, ip_address=get_ip())

@app.route('/video_feed')
def video_feed():
    """Видеопоток"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/reset')
def reset():
    """Сброс камеры"""
    global camera
    if camera:
        camera.release()
        camera = None
    return index()

@app.teardown_appcontext
def cleanup(exception=None):
    """Очистка при завершении"""
    global camera
    if camera:
        camera.release()
        print("📷 Камера освобождена")

if __name__ == '__main__':
    print("=" * 60)
    print("🎥 USB Camera Web Server")
    print("=" * 60)
    
    # Поиск камеры
    idx = find_camera()
    if idx is not None:
        print(f"📷 Используется камера: /dev/video{idx}")
    else:
        print("⚠️ ВНИМАНИЕ: Камера не обнаружена!")
        print("   Подключите камеру USB и перезапустите сервер")
    
    ip = get_ip()
    print(f"🌐 Локальный доступ: http://localhost:5000")
    print(f"🌐 Сеть доступ: http://{ip}:5000")
    print("=" * 60)
    print("Нажмите CTRL+C для остановки")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
