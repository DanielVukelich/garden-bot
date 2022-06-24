from asyncio import AbstractEventLoop, Event, Lock
import os
import cv2
import asyncio
from typing import List, Optional
from quart import Response

camera_daemon_exists: bool = False
camera_daemon_init_lock: Lock = Lock()

class WebCamHandler():

    def __init__(self, event_loop: AbstractEventLoop):
        self.__list_video_devices()
        self._camera = None
        self._need_camera_connect = Event()
        self._need_camera_connect.set()
        self._camera_connect_complete = Event()
        self._error_img = open('static/no_camera.jpeg', 'rb').read()

    def __list_video_devices(self) -> List[int]:
        device_ids = []
        # Search for devices in /dev/video<int>
        for file in os.listdir('/dev/'):
            if file.startswith('video'):
                device_id = file[5:]
                device_ids.append(int(device_id))
        device_ids.sort()
        return device_ids

    def __try_connect_camera(self) -> Optional[str]:
        self._camera = None
        for i in self.__list_video_devices():
            camera = cv2.VideoCapture(i)
            if camera.isOpened():
                status, _ = camera.read()
                if not status:
                    continue
                self._camera = camera
                return '/dev/video' + str(i)
        return None

    async def start_camera_daemon(self):
        global camera_daemon_exists
        global camera_daemon_init_lock

        if camera_daemon_exists:
            return
        async with camera_daemon_init_lock:
            asyncio.create_task(self.__reconnect_camera_loop(10))
            camera_daemon_exists = True


    async def __reconnect_camera_loop(self, timeout:float):
        while(True):
            await self._need_camera_connect.wait()
            print('Camera daemon: Attempting to connect to camera.')
            connected_device = self.__try_connect_camera()
            if connected_device is None:
                print('Camera daemon: Could not reconnect to camera.  Try again in ' + str(timeout) + ' seconds.')
                await asyncio.sleep(timeout)
            else:
                print('Camera daemon: Connected to ' + connected_device + '.  Waiting for next disconnect event')
                self._need_camera_connect.clear()
                self._camera_connect_complete.set()


    async def __get_frames(self):
        yield self.__generate_error_img()
        while(True):
            # ~60fps
            await asyncio.sleep(0.016)

            if self._camera is None:
                print('Camera handler: Waiting to connect to camera...')
                yield self.__generate_error_img()
                self._need_camera_connect.set()
                self._camera_connect_complete.clear()
                await self._camera_connect_complete.wait()
                self._camera_connect_complete.clear()
                print('Camera handler: Camera is reconnected.')
                continue

            status, frame = self._camera.read()
            if not status:
                print('Camera handler: Failed to read frame.  Camera may be unplugged.')
                yield self.__generate_error_img()
                self._camera.release()
                self._camera = None
                continue

            _, buffer = cv2.imencode('.jpeg', frame)
            yield self.__generate_response_bytes(buffer)

    def __generate_response_bytes(self, buffer):
        return (b'--frame\r\n' +
                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    def __generate_error_img(self):
        return (b'--frame\r\n' +
                b'Content-Type: image/jpeg\r\n\r\n' + self._error_img + b'\r\n')

    async def get(self):
        await self.start_camera_daemon()
        return Response(self.__get_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
