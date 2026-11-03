"""Local overlay. The page and the camera stay on this machine."""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import cv2

from scanner.camera import Camera, directshow_names
from scanner.catalog import by_id, candidates, contains_year, public_catalog, suggest_series
from scanner.detect import analyze, light_verdict
from scanner.charts import load as value_charts
from scanner.charts import refresh as refresh_charts
from scanner.readcoin import read_coin
from scanner.samples import render_coin

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
SETTINGS = ROOT / "calibration.json"


def _load_settings() -> dict:
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_settings(data: dict) -> None:
    SETTINGS.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _spot(symbol: str) -> tuple[float, str]:
    request = urllib.request.Request(
        f"https://api.gold-api.com/price/{symbol}",
        headers={"User-Agent": "coin-scanner"},
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return float(payload["price"]), str(payload.get("updatedAt") or "")


class Market:
    """Live gold, silver, and copper. The overlay prices from this, not from a saved quote."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.data = {"ok": False, "silver": None, "gold": None, "copper": None, "updated": None}

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self.data)

    def refresh(self) -> None:
        gold, gold_time = _spot("XAU")
        silver, silver_time = _spot("XAG")
        copper, _copper_time = _spot("HG")
        with self._lock:
            self.data = {
                "ok": True,
                "gold": gold,
                "silver": silver,
                "copper": copper,
                "updated": silver_time or gold_time,
            }

    def loop(self, stop: threading.Event) -> None:
        while not stop.is_set():
            try:
                self.refresh()
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                pass
            stop.wait(45)


MARKET = Market()


class Engine:
    def __init__(self):
        self.cam = Camera()
        self.settings = _load_settings()
        self.series_id = self.settings.get("series_id") or "lincoln-shield"
        self.px_per_mm = self.settings.get("px_per_mm")
        self.shot_a = None
        self.shot_b = None
        self.frozen = False
        self.freeze_frame = None
        self.demo = None
        self.names = []
        self._read = {"year": None, "mint": "", "mint_name": "", "series_id": "", "year_fits": True, "choices": []}
        self._read_pending = {"year": None, "mint": ""}
        self._read_hits = 0
        self._reading = False
        self._last_ocr = 0.0
        self.state = {
            "locked": False,
            "hint": "Looking for the USB camera.",
            "findings": [],
            "markers": [],
            "rim": [],
            "frame_w": 1280,
            "frame_h": 720,
            "focus": 0,
            "glare": 0,
        }
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="coin-analyze", daemon=True)

    def start(self) -> None:
        self._thread.start()
        threading.Thread(target=self._boot_camera, name="coin-boot", daemon=True).start()
        threading.Thread(target=MARKET.loop, args=(self.stop,), name="coin-prices", daemon=True).start()

    def _boot_camera(self) -> None:
        # Listing DirectShow devices with ffmpeg leaves this USB camera black, so names
        # are filled in after a picture is up, from the last known order only as labels.
        self.names = [
            "EMEET PIXY",
            "Galaxy A54 5G (Windows Virtual Camera)",
            "USB2.0 UVC PC Camera",
            "Streamfog VirtualCam",
            "EMEET STUDIO CAMERA",
            "OBS Virtual Camera",
        ]
        if self.names:
            self.cam.devices = [
                {"index": index, "name": name, "width": 0, "height": 0, "mean": 0}
                for index, name in enumerate(self.names)
                if index != 1  # Do not wake the Galaxy phone virtual camera.
            ]
        else:
            self.cam.probe()
            for device in self.cam.devices:
                device["name"] = f"Camera {device['index']}"
        prefer = self.settings.get("camera_index")
        if prefer is None:
            for device in self.cam.devices:
                if device.get("name") == "USB2.0 UVC PC Camera":
                    prefer = device["index"]
                    break
        if prefer is None and self.cam.devices:
            prefer = self.cam.devices[0]["index"]
        if prefer is None:
            return
        width = int(self.settings.get("width") or 1280)
        height = int(self.settings.get("height") or 720)
        # The camera index can change when Windows reconnects a virtual or USB
        # camera. Try the saved device first, then the known USB slot and the
        # remaining DirectShow slots so startup can recover by itself.
        choices = []
        for candidate in (prefer, 2, 0, 3, 4, 5):
            if candidate is not None and int(candidate) not in choices:
                choices.append(int(candidate))
        opened = {"ok": False}
        for candidate in choices:
            opened = self.cam.open(candidate, width, height)
            if opened.get("ok"):
                break
        if opened.get("ok"):
            for device in self.cam.devices:
                if device["index"] == opened["index"]:
                    device["width"] = opened["width"]
                    device["height"] = opened["height"]

    def _maybe_read(self, frame, result) -> None:
        if not result.get("locked") or not result.get("circle"):
            self._read = {"year": None, "mint": "", "mint_name": "", "series_id": "", "year_fits": True, "choices": []}
            self._read_hits = 0
            return
        if self._reading:
            return
        if result.get("glare", 1) >= 0.1 and result.get("surface") != "steel":
            return
        if time.time() - self._last_ocr < 2.5:
            return
        self._reading = True
        self._last_ocr = time.time()
        snapshot = frame.copy()
        circle = dict(result["circle"])
        threading.Thread(
            target=self._read_worker,
            args=(snapshot, circle, result.get("surface") or "", result.get("diameter_mm")),
            name="coin-ocr",
            daemon=True,
        ).start()

    def _read_worker(self, frame, circle, surface: str = "", diameter_mm=None) -> None:
        try:
            found = read_coin(frame, circle)
            year = found.get("year")
            mint = found.get("mint") or ""
            if year and year == self._read_pending.get("year") and mint == self._read_pending.get("mint"):
                self._read_hits += 1
            else:
                self._read_pending = {"year": year, "mint": mint}
                self._read_hits = 1 if year else 0
            if year and self._read_hits >= 2:
                measured = float(diameter_mm) if diameter_mm else None
                suggestion = suggest_series(int(year), self.series_id, surface, measured) or ""
                if suggestion:
                    self.series_id = suggestion
                fits = contains_year(by_id(self.series_id), int(year))
                names = []
                if not fits:
                    names = [item["name"] for item in candidates(int(year), surface, measured)[:6]]
                self._read = {
                    "year": year,
                    "mint": mint,
                    "mint_name": found.get("mint_name") or "",
                    "series_id": suggestion,
                    "year_fits": fits,
                    "choices": names,
                }
        finally:
            self._reading = False

    def frame(self):
        if self.demo is not None:
            return self.demo.copy()
        if self.frozen and self.freeze_frame is not None:
            return self.freeze_frame.copy()
        return self.cam.latest()

    def _analyze(self, frame):
        spec = by_id(self.series_id)
        height, width = frame.shape[:2]
        scale = 1.0
        work = frame
        if width > 1100:
            scale = 1100 / width
            work = cv2.resize(frame, (1100, max(1, int(round(height * scale)))), interpolation=cv2.INTER_AREA)
        ppm = self.px_per_mm * scale if self.px_per_mm else None
        result = analyze(work, spec, ppm)
        if scale != 1.0:
            inverse = 1.0 / scale
            if result["circle"]:
                circle = result["circle"]
                result["circle"] = {
                    "cx": circle["cx"] * inverse,
                    "cy": circle["cy"] * inverse,
                    "r": circle["r"] * inverse,
                }
            if result["diameter_px"]:
                result["diameter_px"] *= inverse
            for marker in result["markers"]:
                for key in ("x", "y", "x1", "y1", "x2", "y2"):
                    if key in marker:
                        marker[key] *= inverse
            result["frame_w"] = width
            result["frame_h"] = height
        return result

    def _loop(self) -> None:
        while not self.stop.is_set():
            frame = self.frame()
            if frame is None:
                with self.lock:
                    self.state["hint"] = self.cam.error or "Waiting for a picture from the camera."
                    self.state["series_id"] = self.series_id
                self.stop.wait(0.2)
                continue
            result = self._analyze(frame)
            self._maybe_read(frame, result)
            result["read"] = dict(self._read)
            result["series_id"] = self.series_id
            result["frozen"] = self.frozen
            result["demo"] = self.demo is not None
            result["calibrated"] = bool(self.px_per_mm)
            result["px_per_mm"] = self.px_per_mm
            result["light"] = {
                "a": self.shot_a is not None,
                "b": self.shot_b is not None,
                "verdict": light_verdict(self.shot_a, self.shot_b),
            }
            with self.lock:
                self.state = result
            self.stop.wait(0.15 if self.frozen or self.demo is not None else 0.28)

    def snapshot_state(self) -> dict:
        with self.lock:
            state = dict(self.state)
            state["cameras"] = self.cam.devices
            state["camera_index"] = self.cam.index
            state["camera_error"] = self.cam.error
            state["known_names"] = self.names
            state["market"] = MARKET.snapshot()
            return state

    def set_series(self, series_id: str) -> None:
        self.series_id = series_id
        self.settings["series_id"] = series_id
        _save_settings(self.settings)

    def freeze(self, on: bool) -> None:
        if on:
            frame = self.cam.latest() if self.demo is None else self.demo.copy()
            self.freeze_frame = frame
            self.frozen = frame is not None
        else:
            self.frozen = False
            self.freeze_frame = None

    def use_demo(self, on: bool, kind: str = "mixed") -> None:
        self.demo = render_coin(kind) if on else None
        if on:
            self.frozen = False

    def calibrate(self) -> dict:
        with self.lock:
            state = dict(self.state)
        circle = state.get("circle")
        if not circle:
            return {"ok": False, "error": "Lock a coin in the ring before calibrating."}
        spec = by_id(self.series_id)
        diameter = float(circle["r"]) * 2.0
        if diameter <= 1 or not spec.get("diameter_mm"):
            return {"ok": False, "error": "This series has no fixed diameter to calibrate from."}
        self.px_per_mm = diameter / float(spec["diameter_mm"])
        self.settings["px_per_mm"] = self.px_per_mm
        self.settings["series_id"] = self.series_id
        self.settings["camera_index"] = self.cam.index
        _save_settings(self.settings)
        return {"ok": True, "px_per_mm": self.px_per_mm}

    def light(self, shot: str) -> dict:
        if shot == "clear":
            self.shot_a = None
            self.shot_b = None
            return {"ok": True}
        with self.lock:
            doubling = dict(self.state.get("doubling") or {})
        if shot == "a":
            self.shot_a = doubling
        elif shot == "b":
            self.shot_b = doubling
        return {"ok": True}


ENGINE = Engine()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def _json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/state":
            self._json(ENGINE.snapshot_state())
            return
        if path == "/api/catalog":
            self._json(public_catalog())
            return
        if path == "/api/indian-head":
            book = value_charts()
            self._json((book.get("charts") or {}).get("indian-head") or {"years": {}})
            return
        if path == "/api/values":
            self._json(value_charts())
            return
        if path == "/api/stream":
            self._stream()
            return
        self._file(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._read_json()
        if path == "/api/series":
            ENGINE.set_series(str(body.get("id") or "lincoln-shield"))
            self._json({"ok": True})
            return
        if path == "/api/open":
            ENGINE.use_demo(False)
            opened = ENGINE.cam.open(
                int(body.get("index") or 0),
                int(body.get("width") or 1280),
                int(body.get("height") or 720),
            )
            if opened.get("ok"):
                ENGINE.settings["camera_index"] = opened["index"]
                ENGINE.settings["width"] = opened["width"]
                ENGINE.settings["height"] = opened["height"]
                _save_settings(ENGINE.settings)
            self._json(opened)
            return
        if path == "/api/control":
            ENGINE.cam.set_control(str(body.get("name") or ""), float(body.get("value") or 0))
            self._json({"ok": True})
            return
        if path == "/api/freeze":
            ENGINE.freeze(bool(body.get("on")))
            self._json({"ok": True, "frozen": ENGINE.frozen})
            return
        if path == "/api/demo":
            ENGINE.use_demo(bool(body.get("on", True)), str(body.get("kind") or "mixed"))
            self._json({"ok": True})
            return
        if path == "/api/calibrate":
            self._json(ENGINE.calibrate())
            return
        if path == "/api/light":
            self._json(ENGINE.light(str(body.get("shot") or "a")))
            return
        if path == "/api/shutdown":
            self._json({"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            ENGINE.stop.set()
            return
        self._json({"ok": False, "error": "Unknown request"}, 404)

    def _file(self, path: str) -> None:
        name = "index.html" if path in ("", "/") else path.lstrip("/")
        if name not in ("index.html", "app.js", "style.css", "defects.json"):
            self.send_error(404)
            return
        file_path = WEB / name
        if not file_path.is_file():
            self.send_error(404)
            return
        data = file_path.read_bytes()
        kind = {
            "index.html": "text/html; charset=utf-8",
            "app.js": "text/javascript; charset=utf-8",
            "style.css": "text/css; charset=utf-8",
            "defects.json": "application/json",
        }[name]
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _stream(self) -> None:
        self.send_response(200)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        try:
            while not ENGINE.stop.is_set():
                frame = ENGINE.frame()
                if frame is None:
                    time.sleep(0.05)
                    continue
                ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
                if not ok:
                    continue
                payload = encoded.tobytes()
                self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ")
                self.wfile.write(str(len(payload)).encode("ascii"))
                self.wfile.write(b"\r\n\r\n")
                self.wfile.write(payload)
                self.wfile.write(b"\r\n")
                time.sleep(0.05)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
            return


def _warm_charts() -> None:
    try:
        refresh_charts()
    except (OSError, TimeoutError, json.JSONDecodeError, ValueError):
        return


def serve(port: int = 8765) -> None:
    threading.Thread(target=_warm_charts, name="value-charts", daemon=True).start()
    ENGINE.start()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    print(f"Coin Scanner is at http://127.0.0.1:{port}")
    print("Close this window to quit.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        ENGINE.stop.set()
        ENGINE.cam.close()
        server.server_close()

