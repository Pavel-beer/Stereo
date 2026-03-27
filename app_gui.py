#!/usr/bin/env python3
"""
Веб-сервер с графическим интерфейсом для USB-камеры
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
            font-size: 2em;
        }
        
        .camera-panel {
            background: #0f3460;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .video-container {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .video-container img {
            max-width: 100%;
            border-radius: 10px;
            border: 3px solid #00adb5;
            background: #000;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
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
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        button:hover {
            background: #008b93;
            transform: scale(1.05);
        }
        
        button.primary {
            background: #4caf50;
        }
        
        button.primary:hover {
            background: #45a049;
        }
        
        button.danger {
            background: #f44336;
        }
        
        button.danger:hover {
            background: #da190b;
        }
        
        .info-panel {
            background: #1a1a2e;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }
        
        .info-panel p {
            margin: 5px 0;
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
        
        .status.offline {
            background: #f44336;
            color: white;
        }
        
        .ip-address {
            background: #0f3460;
            padding: 5px 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 14px;
        }
        
        .slider-container {
            text-align: center;
            margin-top: 10px;
        }
        
        input[type="range"] {
            width: 100%;
            margin: 10px 0;
        }
        
        .angle-value {
            font-size: 18px;
            font-weight: bold;
            color: #00adb5;
        }
        
        @media (max-width: 768px) {
            .controls {
                grid-template-columns: 1fr;
            }
            .button-group button {
                padding: 8px 12px;
                font-size: 12px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📹 USB Camera Control Panel</h1>
        
        <div class="camera-panel">
            <div class="video-container">
                <img id="camera-feed" src="{{ url_for('video_feed') }}" alt="Camera Feed">
            </div>
            
            <div class="info-panel">
                <p>📷 Статус: <span id="status" class="status online">ОНЛАЙН</span></p>
                <p>🌐 IP-адрес: <span class="ip-address">{{ ip_address }}:5000</span></p>
                <p>📱 Доступно с любого устройства в сети</p>
            </div>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <h3>🔄 Управление камерой</h3>
                <div class="button-group">
                    <button onclick="location.reload()">🔄 Обновить</button>
                    <button onclick="resetCamera()">📷 Сброс камеры</button>
                    <button onclick="toggleMirror()">🪞 Зеркало</button>
                </div>
            </div>
            
            <div class="control-group">
                <h3>🎨 Настройки изображения</h3>
                <div class="button-group">
                    <button onclick="setBrightness('up')">🔆 Яркость +</button>
                    <button onclick="setBrightness('down')">🔅 Яркость -</button>
                    <button onclick="setContrast('up')">🎨 Контраст +</button>
                    <button onclick="setContrast('down')">🎨 Контраст -</button>
                </div>
            </div>
        </div>
        
        <div class="info-panel">
            <p>💡 <strong>Совет:</strong> Для полноэкранного режима используйте <a href="/video_only" target="_blank" style="color: #00adb5;">/video_only</a></p>
            <p>🖱️ Нажмите F11 для полноэкранного режима браузера</p>
        </div>
    </div>
    
    <script>
        let mirrorEnabled = false;
        
        function updateFeed() {
            let img = document.getElementById('camera-feed');
            let timestamp = new Date().getTime();
            let url = "{{ url_for('video_feed') }}?t=" + timestamp;
            if (mirrorEnabled) {
                url += "&mirror=1";
            }
            img.src = url;
            setTimeout(updateFeed, 50);
        }
        
        function resetCamera() {
            fetch('/reset')
                .then(response => response.json())
                .then(data => {
                    console.log('Camera reset:', data);
                });
        }
        
        function toggleMirror() {
            mirrorEnabled = !mirrorEnabled;
            updateFeed();
        }
        
        function setBrightness(direction) {
            fetch('/brightness/' + direction)
                .then(response => response.json())
                .then(data => {
                    console.log('Brightness:', data);
                });
        }
        
        function setContrast(direction) {
            fetch('/contrast/' + direction)
                .then(response => response.json())
                .then(data => {
                    console.log('Contrast:', data);
                });
        }
        
        // Проверка статуса камеры
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
        
        // Запуск обновления
        updateFeed();
        setInterval(checkStatus, 5000);
    </script>
</body>
</html>
'''

# Глобальные переменные
frame = None
lock = threading.Lock()
running = True
camera = None
mirror = False
brightness = 0
contrast = 0

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
    """Поток для непрерывного захвата кадров"""
    global frame, running, camera, mirror
    
    while running:
        if camera and camera.isOpened():
            ret, img = camera.read()
            if ret:
                if mirror:
                    img = cv2.flip(img, 1)
                with lock:
                    frame = img.copy()
        time.sleep(0.03)

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
        global frame
        while True:
            with lock:
                if frame is not None:
                    ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n'
                               b'Cache-Control: no-cache\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(0.03)
    
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
            body { margin: 0; background: black; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
            img { max-width: 100%; max-height: 100vh; }
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

@app.route('/brightness/<direction>')
def set_brightness(direction):
    """Настройка яркости"""
    global brightness, camera
    if direction == 'up':
        brightness += 10
    else:
        brightness -= 10
    brightness = max(-100, min(100, brightness))
    if camera:
        camera.set(cv2.CAP_PROP_BRIGHTNESS, brightness)
    return {'brightness': brightness}

@app.route('/contrast/<direction>')
def set_contrast(direction):
    """Настройка контраста"""
    global contrast, camera
    if direction == 'up':
        contrast += 10
    else:
        contrast -= 10
    contrast = max(-100, min(100, contrast))
    if camera:
        camera.set(cv2.CAP_PROP_CONTRAST, contrast)
    return {'contrast': contrast}

@app.route('/status')
def status():
    """Проверка статуса"""
    with lock:
        has_frame = frame is not None
    return {'camera_working': has_frame}

@app.teardown_appcontext
def cleanup(exception=None):
    """Очистка при завершении"""
    global running, camera
    running = False
    if camera:
        camera.release()
    print("📷 Камера освобождена")

if __name__ == '__main__':
    print("=" * 60)
    print("🎥 USB Camera Web Server - GUI Version")
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
