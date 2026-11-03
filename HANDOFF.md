# Coin Scanner

Goal: live USB-camera overlay that screens U.S. coins for rim bites, lines, pits, color, off-center design, and split edges, with a two-light doubled-die check.

Status: detector tests pass (13). Server and overlay are in this folder. Run with `run.bat`.

Next: the USB2.0 UVC PC Camera is DirectShow index 2 and works at the driver's 640x480 picture. Do not set resolution, MJPEG, or buffer size, and do not list devices with ffmpeg. That combination turned the picture black and it stays black until the camera is unplugged and plugged back in. After that, press Reconnect.

