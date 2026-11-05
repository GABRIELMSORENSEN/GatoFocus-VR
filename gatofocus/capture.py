import ctypes
from ctypes import wintypes
import os
import threading
import time
from pathlib import Path
import numpy as np
import cv2
import psutil


class NoFrame(RuntimeError):
    """A temporarily unavailable frame; keep the capture session alive."""


class DesktopCapture:
    def __init__(self, fps=6):
        self.fps = fps
        self.opened = False
        self.control = None
        self.image = None
        self.timestamp = 0.
        self.lock = threading.Lock()
        self.hwnd = 0
        self.pid = 0

    def open(self):
        from windows_capture import WindowsCapture
        user = ctypes.windll.user32
        targets = {p.info["pid"] for p in psutil.process_iter(["name", "pid"])
                   if (p.info["name"] or "").lower() == "vrchat.exe"}
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def visit(hwnd, _):
            pid = ctypes.c_ulong()
            user.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), ctypes.byref(pid))
            if pid.value in targets and user.IsWindowVisible(ctypes.c_void_p(hwnd)):
                title = ctypes.create_unicode_buffer(512)
                user.GetWindowTextW(ctypes.c_void_p(hwnd), title, 512)
                if title.value == "VRChat":
                    self.hwnd, self.pid = hwnd, pid.value
            return True
        user.EnumWindows(callback_type(visit), None)
        if not self.hwnd:
            raise RuntimeError("Abra o VRChat no modo PC (Desktop).")
        self.capture = WindowsCapture(window_hwnd=self.hwnd, cursor_capture=False,
                                      draw_border=True, minimum_update_interval=round(1000 / self.fps))
        @self.capture.event
        def on_frame_arrived(frame, capture_control):
            if frame.width < 32 or frame.height < 32:
                return
            # Bound inference/preview memory; do not retain native frame buffers.
            pixels = frame.frame_buffer[:, :, :3]
            bounds, client, origin = wintypes.RECT(), wintypes.RECT(), wintypes.POINT()
            handle = ctypes.c_void_p(self.hwnd)
            hr = ctypes.windll.dwmapi.DwmGetWindowAttribute(handle, 9, ctypes.byref(bounds), ctypes.sizeof(bounds))
            if hr == 0 and user.GetClientRect(handle, ctypes.byref(client)) and user.ClientToScreen(handle, ctypes.byref(origin)):
                sx = frame.width / max(1, bounds.right - bounds.left)
                sy = frame.height / max(1, bounds.bottom - bounds.top)
                x = max(0, round((origin.x - bounds.left) * sx))
                y = max(0, round((origin.y - bounds.top) * sy))
                crop = pixels[y:min(frame.height, y+round(client.bottom*sy)),
                              x:min(frame.width, x+round(client.right*sx))]
                if crop.shape[0] > 32 and crop.shape[1] > 32:
                    pixels = crop
            h, w = pixels.shape[:2]
            ratio = min(1., 640 / max(w, h))
            image = cv2.resize(pixels, (max(1, int(w * ratio)), max(1, int(h * ratio))))
            with self.lock:
                self.image, self.timestamp = image, time.monotonic()
        @self.capture.event
        def on_closed():
            self.opened = False
            self.image = None
        self.control = self.capture.start_free_threaded()
        self.opened = True

    def grab(self):
        if not self.opened:
            self.close()
            self.open()
        if ctypes.windll.user32.IsIconic(ctypes.c_void_p(self.hwnd)):
            raise NoFrame("Restaure a janela do VRChat. O GatoFocus pode ficar minimizado.")
        with self.lock:
            if self.image is None or time.monotonic() - self.timestamp > 1.5:
                raise NoFrame("Aguardando um quadro novo da janela do VRChat.")
            image = self.image.copy()
        # Desktop view has configurable FOV. 60 degrees vertical is the initial calibration.
        tangent = np.tan(np.radians(60 / 2))
        horizontal = tangent * image.shape[1] / image.shape[0]
        return image, np.array([-horizontal, horizontal, -tangent, tangent]), np.eye(3), self.pid

    def close(self):
        if self.control:
            try:
                self.control.stop()
            except RuntimeError:
                pass
        self.control = None
        self.opened = False
        self.image = None
        self.timestamp = 0.
        self.hwnd = 0


class SteamCapture:
    def __init__(self, root):
        runtime = Path(root) / "runtime"
        self.dll_dir = os.add_dll_directory(str(runtime))
        self.dll = ctypes.CDLL(str(runtime / "gatofocus_capture.dll"))
        self.dll.gf_error.restype = ctypes.c_char_p
        self.dll.gf_grab.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p,
                                    ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
        self.buffer = np.empty((416, 416, 4), np.uint8)
        self.projection = np.zeros(4, np.float32)
        self.rotation = np.zeros((3, 3), np.float32)
        self.pid = ctypes.c_uint()
        self.opened = False

    def error(self):
        return self.dll.gf_error().decode("utf-8", errors="replace")

    def open(self):
        self.opened = bool(self.dll.gf_open())
        if not self.opened:
            raise RuntimeError(self.error())

    def grab(self):
        if not self.opened:
            self.open()
        ok = self.dll.gf_grab(self.buffer.ctypes.data, self.buffer.nbytes,
                              self.projection.ctypes.data, self.rotation.ctypes.data,
                              ctypes.byref(self.pid))
        if not ok:
            raise RuntimeError(self.error())
        return self.buffer[:, :, :3].copy(), self.projection.copy(), self.rotation.copy(), self.pid.value

    def close(self):
        self.dll.gf_close()
        self.opened = False
