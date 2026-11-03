"""Desktop window for the coin scanner. The page stays on this PC."""

from __future__ import annotations

import os
import socket
import subprocess
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from scanner.server import serve

PORT = 8765
ROOT = Path(__file__).resolve().parent.parent


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _scanner_up(port: int) -> bool:
    if not _port_open(port):
        return False
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=1.5) as response:
            return response.status == 200
    except OSError:
        return False


def _browser() -> str | None:
    candidates = [
        os.environ.get("PROGRAMFILES(X86)", ""),
        os.environ.get("PROGRAMFILES", ""),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    names = [
        r"Microsoft\Edge\Application\msedge.exe",
        r"Google\Chrome\Application\chrome.exe",
    ]
    for root in candidates:
        if not root:
            continue
        for name in names:
            path = Path(root) / name
            if path.is_file():
                return str(path)
    return None


def open_window(port: int = PORT) -> None:
    """Open a standalone app window. A normal browser tab is the fallback."""
    url = f"http://127.0.0.1:{port}"
    browser = _browser()
    if browser is None:
        webbrowser.open(url)
        return
    profile = Path(os.environ.get("LOCALAPPDATA", str(ROOT))) / "CoinScanner" / "window"
    profile.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [
            browser,
            f"--app={url}",
            "--new-window",
            "--window-size=1440,900",
            f"--user-data-dir={profile}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    if _scanner_up(PORT):
        open_window(PORT)
        return

    def _open() -> None:
        for _ in range(40):
            if _scanner_up(PORT):
                open_window(PORT)
                return
            time.sleep(0.25)

    threading.Thread(target=_open, name="coin-window", daemon=True).start()
    print(f"Coin Scanner desktop window: http://127.0.0.1:{PORT}")
    print("Use Quit in the window to stop it.")
    serve(PORT)


if __name__ == "__main__":
    main()

