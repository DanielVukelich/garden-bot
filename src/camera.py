from asyncio import Event, Lock
from datetime import datetime, timedelta
import os
import cv2
import asyncio
from typing import Any, List, Tuple
from quart import Response, request

class WebCamHandler():

    def __init__(self):
        self.camera_id = -1
        self.camera = None
        self.camera_set_lock = Lock()
        for id in self.__list_video_devices():
            status, camera = self.__try_connect_camera(id)
            if status:
                self.camera_id = id
                self.camera = camera
        self._error_img = open('static/no_camera.jpeg', 'rb').read()
        self.camera_reconnected = Event()
        self.retry_wait_sec = 10
        if self.camera_id == -1:
            print('Camera handler could not identify any usable camera')

    def __list_video_devices(self) -> List[int]:
        device_ids = []
        # Search for devices in /dev/video<int>
        for file in os.listdir('/dev/'):
            if file.startswith('video'):
                device_id = file[5:]
                device_ids.append(int(device_id))
        device_ids.sort()
        return device_ids

    def __try_connect_camera(self, device_id: int) -> Tuple[bool, Any]:
        if device_id < 0:
            return (False, None)
        camera = cv2.VideoCapture(device_id)
        if camera.isOpened():
            status, _ = camera.read()
            if status:
                return (True, camera)
        return (False, None)

    async def __reconnect_camera(self):
        # If we never acquired a camera during init, don't try reconnecting
        if self.camera_id == -1:
            return

        # If camera is None, then another task is already trying to reconnect.
        # Make the caller wait until reconnection is complete
        if self.camera is None:
            return self.camera_reconnected.wait()

        async with self.camera_set_lock:
            if self.camera is None:
                return self.camera_reconnected.wait()
            self.camera_reconnected.clear()
            self.camera.release()
            self.camera = None
            reconnected_yet = False
            new_camera = None
            while not reconnected_yet:
                reconnected_yet, new_camera = self.__try_connect_camera(self.camera_id)
                await asyncio.sleep(self.retry_wait_sec)
            self.camera = new_camera
            self.camera_reconnected.set()

    async def __get_frames(self, ms_of_frames_to_get: int):
        if self.camera_id == -1:
            yield self.__generate_error_img()
            return

        loop_end = datetime.utcnow() + timedelta(milliseconds=ms_of_frames_to_get)

        while(datetime.utcnow() < loop_end):
            # ~60fps
            await asyncio.sleep(0.016)

            if self.camera is None:
                print('Camera handler: Waiting for camera reconnect')
                yield self.__generate_error_img()
                await self.__reconnect_camera()

            status, frame = self.camera.read()
            if not status:
                print('Camera handler: Failed to read frame.  Camera may be unplugged.')
                yield self.__generate_error_img()
                await self.__reconnect_camera()
                continue

            _, buffer = cv2.imencode('.jpeg', frame)
            yield self.__generate_response_bytes(buffer)

    def __generate_response(self, buffer: bytes):
        return (b'--frame\r\n' +
                b'Content-Type: image/jpeg\r\n' +
                b'Cache-Control: no-cache\r\n' +
                b'Content-Length: ' + bytes(str(len(buffer)), 'ascii') + b'\r\n\r\n' + buffer + b'\r\n')

    def __generate_response_bytes(self, buffer):
        content = buffer.tobytes()
        return self.__generate_response(content)

    def __generate_error_img(self):
        return self.__generate_response(self._error_img)

    async def get(self):
        ms = int(request.args['ms'])
        return Response(self.__get_frames(ms), mimetype='multipart/x-mixed-replace; boundary=frame')
