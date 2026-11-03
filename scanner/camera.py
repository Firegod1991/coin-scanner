"""DirectShow capture for a USB UVC camera. MJPEG keeps a USB 2.0 link usable."""

from __future__ import annotations

import subprocess
import threading
import time

import cv2


def directshow_names() -> list[str]:
    """Video capture names in DirectShow order. That order matches OpenCV's index on Windows."""
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    names = []
    for line in (proc.stderr or "").splitlines():
        if "(video)" not in line or '"' not in line:
            continue
        names.append(line.split('"', 2)[1])
    return names


class Camera:
    def __init__(self):
        self.cap = None
        self.thread = None
        self.running = False
        self.lock = threading.Lock()
        self.frame = None
        self.index = None
        self.width = 0
        self.height = 0
        self.error = ""
        self.devices = []

    def probe(self, limit: int = 6) -> list[dict]:
        found = []
        for index in range(limit):
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap.release()
                continue
            ok, frame = cap.read()
            if not ok or frame is None:
                cap.release()
                continue
            height, width = frame.shape[:2]
            found.append({
                "index": index,
                "width": int(width),
                "height": int(height),
                "mean": round(float(frame.mean()), 1),
            })
            cap.release()
            time.sleep(0.05)
        self.devices = found
        return found

    def open(self, index: int, width: int = 1280, height: int = 720) -> dict:
        self.close()
        index = int(index)
        cap = None
        # DirectShow can report a stale handle for a short time after the
        # previous capture is released. Retry with a fresh handle so the UI
        # does not need a second manual reconnect.
        for attempt in range(3):
            cap = self._open_live(index, int(width), int(height))
            if cap is not None:
                break
            if attempt < 2:
                time.sleep(0.25)
        if cap is None:
            self.index = index
            self.error = (
                "The USB camera did not send a picture. Unplug it, plug it back in, "
                "and press Reconnect."
            )
            return {"ok": False, "error": self.error}
        ok, frame = cap.read()
        if not ok or frame is None:
            cap.release()
            self.index = index
            self.error = f"Camera {index} opened and then sent no picture."
            return {"ok": False, "error": self.error}
        self.cap = cap
        self.index = int(index)
        self.height, self.width = frame.shape[:2]
        with self.lock:
            self.frame = frame
            self.error = ""
        self.running = True
        self.thread = threading.Thread(target=self._loop, name="coin-camera", daemon=True)
        self.thread.start()
        return {"ok": True, "index": self.index, "width": self.width, "height": self.height}

    def _open_live(self, index: int, width: int, height: int):
        """Open whatever picture the driver offers.

        Asking this USB 2.0 camera for 720p or MJPEG returns a black frame.
        Leaving the size alone returns a real 640x480 picture, which is what we keep.
        """
        del width, height
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            return None
        # Do not set buffer size, resolution, or MJPEG. Those calls turn this
        # USB 2.0 camera black. Show the picture even if the first frames are dark.
        frame = self._pull(cap, 15)
        if not self._alive(frame):
            cap.release()
            return None
        return cap

    @staticmethod
    def _pull(cap, count: int = 8):
        frame = None
        for _ in range(count):
            ok, got = cap.read()
            if ok and got is not None:
                frame = got
        return frame

    @staticmethod
    def _alive(frame) -> bool:
        if frame is None:
            return False
        return float(frame.mean()) > 12.0 and float(frame.std()) > 8.0

    def set_control(self, name: str, value: float) -> None:
        if self.cap is None:
            return
        prop = {
            "brightness": cv2.CAP_PROP_BRIGHTNESS,
            "focus": cv2.CAP_PROP_FOCUS,
        }.get(name)
        if prop is None:
            return
        if name == "focus":
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        self.cap.set(prop, float(value))

    def _loop(self) -> None:
        while self.running and self.cap is not None:
            ok, frame = self.cap.read()
            if not ok or frame is None:
                self.error = "The camera stopped sending frames."
                time.sleep(0.08)
                continue
            with self.lock:
                self.frame = frame
                self.error = ""

    def latest(self):
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def close(self) -> None:
        self.running = False
        thread = self.thread
        cap = self.cap
        self.thread = None
        self.cap = None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=0.6)
        if cap is not None:
            cap.release()

