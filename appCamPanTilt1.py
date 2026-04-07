#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, Response
from camera_dual_usb import DualUSBCamera
import RPi.GPIO as GPIO
from angleServoCtrl import setServoAngle   # предполагается, что этот файл у вас есть

app = Flask(__name__)

# Углы сервоприводов
panServoAngle = 90
tiltServoAngle = 90
panPin = 27
tiltPin = 17

# Настройка GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(panPin, GPIO.OUT)
GPIO.setup(tiltPin, GPIO.OUT)
GPIO.setwarnings(False)

# Инициализация стереокамеры: левое видео - /dev/video0, правое - /dev/video1
camera = DualUSBCamera(left_id=0, right_id=1, width=320, height=240, hstack=True)

@app.route('/')
def index():
    templateData = {
        'panServoAngle': panServoAngle,
        'tiltServoAngle': tiltServoAngle
    }
    return render_template('index.html', **templateData)

def gen():
    while True:
        frame = camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            time.sleep(0.05)

@app.route('/video_feed')
def video_feed():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/<servo>/<angle>")
def move(servo, angle):
    global panServoAngle, tiltServoAngle
    angle_val = int(angle)
    if servo == 'pan':
        panServoAngle = angle_val
        setServoAngle(panPin, panServoAngle)
    elif servo == 'tilt':
        tiltServoAngle = angle_val
        setServoAngle(tiltPin, tiltServoAngle)
    templateData = {
        'panServoAngle': panServoAngle,
        'tiltServoAngle': tiltServoAngle
    }
    return render_template('index.html', **templateData)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False, threaded=True)
