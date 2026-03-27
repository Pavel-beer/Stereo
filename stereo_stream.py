#!/usr/bin/env python3
"""
Простой сервер для стереокамеры - передача видео с двух USB-камер
"""

import cv2
from flask import Flask, Response, render_template_string
import threading
import time

app = Flask(__name__)

# HTML страница с двумя видеопотоками
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Стереокамера</title>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a2e;
            color: #eee;
            text-align: center;
            margin: 0;
            padding: 20px;
        }
        h1 {
            color: #00adb5;
        }
        .cameras {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 20px;
            margin: 20px 0;
        }
        .camera {
            background: #0f3460;
            padding: 15px;
            border-radius: 10px;
        }
        .camera h3 {
            margin-top: 0;
            color: #00adb5;
        }
        img {
            border: 2px solid #00adb5;
            border-radius: 8px;
            max-width: 100%;
            height: auto;
        }
        .info {
            margin-top: 20px;
            color: #888;
        }
        .ip {
            background: #0f3460;
            padding: 5px 10px;
            border-radius: 5px;
            font-family: monospace;
        }
        button {
            background: #00adb5;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            border-radius: 5px;
            cursor: pointer;
        }
        button:hover {
            background: #008b93;
        }
    </style>
</head>
<body>
    <h1>📹 Стереокамера - два видеопотока</h1>
    
    <div class="cameras">
        <div class="camera">
            <h3>📷 Левая камера (CAM 0)</h3>
            <img id="left-cam" src="{{ url_for('video_feed_left') }}" width="500">
        </div>
        <div class="camera">
            <h3>📷 Правая камера (CAM 2)</h3>
            <img id="right-cam" src="{{ url_for('video_feed_right') }}" width="500">
        </div>
    </div>
    
    <div class="info">
        <p>🌐 Доступ: <span class="ip">{{ ip_address }}:5000</span></p>
        <button onclick="location.reload()">🔄 Обновить</button>
        <button onclick="window.location.href='/reset'">📷 Сброс камер</button>
    </div>
    
    <script>
        // Принудительное обновление без кэша
        setInterval(function() {
            let left = document.getElementById('left-cam');
            let right = document.getElementById('right-cam');
            let t = new Date().getTime();
            left.src = "{{ url_for('video_feed_left') }}?t=" + t;
            right.src = "{{ url_for('video_feed_right') }}?t=" + t;
        }, 100);
    </script>
</body>
</html>
'''

# Глобальные переменные
frame_left = None
frame_right = None
lock = threading.Lock()
camera_left = None
camera_right = None
running = True

def init_cameras():
    """Инициализация двух камер"""
    global camera_left, camera_right
    
    print("📷 Поиск камер...")
    
    # Пробуем разные комбинации индексов
    indices_to_try = [(0, 2), (0, 4), (2, 4), (0, 1), (1, 2), (4, 6)]
    
    for left_idx, right_idx in indices_to_try:
        print(f"Пробуем: левая={left_idx}, правая={right_idx}")
        
        cap_left = cv2.VideoCapture(left_idx)
        cap_right = cv2.VideoCapture(right_idx)
        
        if cap_left.isOpened() and cap_right.isOpened():
            camera_left = cap_left
            camera_right = cap_right
            print(f"✅ Камеры найдены: левая=/dev/video{left_idx}, правая=/dev/video{right_idx}")
            return True
        else:
            if cap_left.isOpened():
                cap_left.release()
            if cap_right.isOpened():
                cap_right.release()
    
    # Если не нашли, пробуем по одному индексу
    print("⚠️ Пробуем использовать одну камеру для обоих потоков...")
    for idx in [0, 2, 4, 6, 8]:
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            camera_left = cap
            camera_right = cv2.VideoCapture(idx)
            print(f"✅ Используем одну камеру /dev/video{idx} для обоих потоков")
            return True
    
    print("❌ Камеры не найдены!")
    return False

def capture_thread():
    """Поток для захвата кадров с обеих камер"""
    global frame_left, frame_right, running
    
    while running:
        if camera_left and camera_left.isOpened():
            ret, img = camera_left.read()
            if ret:
                with lock:
                    frame_left = img.copy()
        
        if camera_right and camera_right.isOpened():
            ret, img = camera_right.read()
            if ret:
                with lock:
                    frame_right = img.copy()
        
        time.sleep(0.03)  # ~30 FPS

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

@app.route('/video_feed_left')
def video_feed_left():
    """Видеопоток с левой камеры"""
    def generate():
        while True:
            with lock:
                if frame_left is not None:
                    ret, jpeg = cv2.imencode('.jpg', frame_left, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(0.033)
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed_right')
def video_feed_right():
    """Видеопоток с правой камеры"""
    def generate():
        while True:
            with lock:
                if frame_right is not None:
                    ret, jpeg = cv2.imencode('.jpg', frame_right, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(0.033)
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/reset')
def reset():
    """Сброс камер"""
    global camera_left, camera_right, frame_left, frame_right
    if camera_left:
        camera_left.release()
    if camera_right:
        camera_right.release()
    
    camera_left = None
    camera_right = None
    frame_left = None
    frame_right = None
    
    init_cameras()
    return {'status': 'ok'}

@app.route('/status')
def status():
    """Проверка статуса"""
    with lock:
        has_left = frame_left is not None
        has_right = frame_right is not None
    return {'left': has_left, 'right': has_right}

@app.teardown_appcontext
def cleanup(exception=None):
    """Очистка при завершении"""
    global running, camera_left, camera_right
    running = False
    if camera_left:
        camera_left.release()
    if camera_right:
        camera_right.release()
    print("📷 Камеры освобождены")

if __name__ == '__main__':
    print("=" * 60)
    print("🎥 СТЕРЕОКАМЕРА - Два видеопотока")
    print("=" * 60)
    
    if init_cameras():
        # Запуск потока захвата
        thread = threading.Thread(target=capture_thread)
        thread.daemon = True
        thread.start()
        print("✅ Поток захвата запущен")
    else:
        print("⚠️ Камеры не найдены! Проверьте подключение.")
    
    ip = get_ip()
    print(f"🌐 http://localhost:5000")
    print(f"🌐 http://{ip}:5000")
    print("=" * 60)
    print("Нажмите CTRL+C для остановки")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
