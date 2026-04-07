#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  camera_dual_usb.py
#  Захват с двух видеоустройств (например, /dev/video0 и /dev/video1) одной стереокамеры
#

import cv2
import time
import threading

class DualUSBCamera:
    def __init__(self, left_id=0, right_id=1, width=320, height=240, hstack=True):
        self.left_id = left_id
        self.right_id = right_id
        self.width = width
        self.height = height
        self.hstack = hstack

        self.left_frame = None
        self.right_frame = None
        self.combined_frame = None
        
        self.thread = None
        self.running = False
        self.last_access = 0

    def initialize(self):
        if self.thread is None:
            self.running = True
            self.thread = threading.Thread(target=self._capture_loop)
            self.thread.start()
            while self.combined_frame is None:
                time.sleep(0.01)

    def get_frame(self):
        self.last_access = time.time()
        self.initialize()
        if self.combined_frame is not None:
            ret, jpeg = cv2.imencode('.jpg', self.combined_frame)
            if ret:
                return jpeg.tobytes()
        return None

    def _capture_loop(self):
        cap_left = cv2.VideoCapture(self.left_id)
        cap_right = cv2.VideoCapture(self.right_id)

        if not cap_left.isOpened():
            print(f"Ошибка: не удалось открыть левое устройство /dev/video{self.left_id}")
            self.running = False
            self.thread = None
            return
        if not cap_right.isOpened():
            print(f"Ошибка: не удалось открыть правое устройство /dev/video{self.right_id}")
            self.running = False
            self.thread = None
            return

        # Установка разрешения
        cap_left.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap_left.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap_right.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap_right.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        # Включение MJPEG (если поддерживается)
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        cap_left.set(cv2.CAP_PROP_FOURCC, fourcc)
        cap_right.set(cv2.CAP_PROP_FOURCC, fourcc)

        time.sleep(2.0)  # прогрев

        while self.running:
            ret_left, frame_left = cap_left.read()
            ret_right, frame_right = cap_right.read()

            if ret_left and ret_right:
                # Приведение к единому размеру
                if frame_left.shape[:2] != (self.height, self.width):
                    frame_left = cv2.resize(frame_left, (self.width, self.height))
                if frame_right.shape[:2] != (self.height, self.width):
                    frame_right = cv2.resize(frame_right, (self.width, self.height))

                self.left_frame = frame_left
                self.right_frame = frame_right

                if self.hstack:
                    self.combined_frame = cv2.hconcat([frame_left, frame_right])
                else:
                    self.combined_frame = cv2.vconcat([frame_left, frame_right])
            else:
                time.sleep(0.01)

            if time.time() - self.last_access > 10:
                break

        cap_left.release()
        cap_right.release()
        self.thread = None
