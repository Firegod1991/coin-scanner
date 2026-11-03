"""Synthetic coins for the sample button and the detector tests."""

from __future__ import annotations

import math

import cv2
import numpy as np


def render_coin(kind: str = "clean", size: tuple[int, int] = (960, 720)) -> np.ndarray:
    """Draw a copper disc. kind is clean, chip, scratch, pit, doubling, green, offcenter, or mixed."""
    width, height = size
    img = np.zeros((height, width, 3), np.uint8)
    img[:] = (34, 38, 36)
    cx, cy = width // 2, height // 2 + 8
    radius = int(min(width, height) * 0.34)
    disc = (46, 96, 176)
    cv2.circle(img, (cx, cy), radius, disc, -1, lineType=cv2.LINE_8)

    yy, xx = np.mgrid[:height, :width]
    shade = (1.0 + 0.10 * ((xx - cx) / radius)).astype(np.float32)
    mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius ** 2
    work = img.astype(np.float32)
    work[mask] *= shade[mask, None]
    img = np.clip(work, 0, 255).astype(np.uint8)

    ink = (22, 48, 96)
    if kind != "doubling":
        cv2.putText(
            img, "LIBERTY", (cx - 78, cy + 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.85, ink, 2, cv2.LINE_8,
        )

    def notch(angle: float, depth: int, width_rad: float) -> None:
        pts = []
        for step in np.linspace(-width_rad, width_rad, 16):
            rr = radius - depth * math.cos(step / width_rad * math.pi / 2)
            pts.append([
                int(cx + rr * math.cos(angle + step)),
                int(cy + rr * math.sin(angle + step)),
            ])
        pts.append([
            int(cx + (radius + 4) * math.cos(angle + width_rad)),
            int(cy + (radius + 4) * math.sin(angle + width_rad)),
        ])
        pts.append([
            int(cx + (radius + 4) * math.cos(angle - width_rad)),
            int(cy + (radius + 4) * math.sin(angle - width_rad)),
        ])
        cv2.fillPoly(img, [np.array(pts, np.int32)], (34, 38, 36), lineType=cv2.LINE_8)

    if kind in ("chip", "mixed"):
        # Straight down in the image is 6 o'clock.
        notch(math.pi / 2, 22, 0.09)

    if kind in ("scratch", "mixed"):
        cv2.line(
            img,
            (cx - int(radius * 0.5), cy + int(radius * 0.28)),
            (cx + int(radius * 0.48), cy + int(radius * 0.18)),
            (18, 28, 48),
            2,
            cv2.LINE_8,
        )

    if kind in ("pit", "mixed"):
        cv2.circle(img, (cx + int(radius * 0.28), cy - int(radius * 0.22)), 8, (16, 24, 40), -1, lineType=cv2.LINE_8)

    if kind in ("doubling", "mixed"):
        origin = (cx - 90, cy - int(radius * 0.22))
        cv2.putText(img, "LIBERTY", origin, cv2.FONT_HERSHEY_SIMPLEX, 0.9, ink, 2, cv2.LINE_8)
        cv2.putText(
            img, "LIBERTY", (origin[0] + 5, origin[1]),
            cv2.FONT_HERSHEY_SIMPLEX, 0.9, ink, 2, cv2.LINE_8,
        )

    if kind in ("green", "mixed"):
        cv2.circle(img, (cx - int(radius * 0.32), cy + int(radius * 0.16)), 16, (40, 170, 55), -1, lineType=cv2.LINE_8)

    if kind == "offcenter":
        ox = cx - int(radius * 0.14)
        oy = cy
        for i in range(72):
            angle = i * 2 * math.pi / 72
            inner = radius * 0.68
            outer = radius * 0.86
            p1 = (int(ox + inner * math.cos(angle)), int(oy + inner * math.sin(angle)))
            p2 = (int(ox + outer * math.cos(angle)), int(oy + outer * math.sin(angle)))
            cv2.line(img, p1, p2, ink, 3, cv2.LINE_8)

    rng = np.random.default_rng(4)
    noise = rng.normal(0, 1.6, img.shape)
    return np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

