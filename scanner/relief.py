"""Read a raised date when ordinary text recognition sees nothing.

The date on a worn cent is a groove, not printed type. This looks for four
digit-shaped dark strokes in a row and returns a year only when every digit
is identified. A miss stays empty. It does not guess.
"""

from __future__ import annotations

import cv2
import numpy as np

_DIGITS = "0123456789"


def _render_digit(char: str, height: int = 160):
    width = int(round(height * 0.62))
    image = np.zeros((height, width), np.uint8)
    thick = max(6, height // 9)
    color = 255
    margin = 8
    if char == "0":
        cv2.ellipse(image, (width // 2, height // 2), (width // 2 - margin, height // 2 - margin), 0, 0, 360, color, thick)
    elif char == "1":
        cv2.line(image, (width // 2, margin), (width // 2, height - margin), color, thick + 2)
        cv2.line(image, (width // 2, margin), (int(width * 0.28), int(height * 0.22)), color, thick)
        cv2.line(image, (int(width * 0.28), height - margin), (int(width * 0.72), height - margin), color, thick)
    elif char == "2":
        cv2.ellipse(image, (width // 2, int(height * 0.30)), (width // 2 - margin, int(height * 0.22)), 0, 180, 430, color, thick)
        cv2.line(image, (width - margin, int(height * 0.42)), (margin, height - margin - 4), color, thick)
        cv2.line(image, (margin, height - margin), (width - margin, height - margin), color, thick)
    elif char == "3":
        cv2.ellipse(image, (int(width * 0.48), int(height * 0.28)), (int(width * 0.40), int(height * 0.20)), 0, -80, 230, color, thick)
        cv2.ellipse(image, (int(width * 0.48), int(height * 0.72)), (int(width * 0.40), int(height * 0.22)), 0, -70, 240, color, thick)
    elif char == "4":
        cv2.line(image, (int(width * 0.68), margin), (int(width * 0.12), int(height * 0.55)), color, thick)
        cv2.line(image, (int(width * 0.08), int(height * 0.55)), (width - margin, int(height * 0.55)), color, thick)
        cv2.line(image, (int(width * 0.68), margin), (int(width * 0.68), height - margin), color, thick + 1)
    elif char == "5":
        cv2.line(image, (width - margin, margin), (margin, margin), color, thick)
        cv2.line(image, (margin, margin), (margin, int(height * 0.48)), color, thick)
        cv2.ellipse(image, (width // 2, int(height * 0.70)), (width // 2 - margin, int(height * 0.24)), 0, -30, 250, color, thick)
    elif char == "6":
        cv2.ellipse(image, (width // 2, int(height * 0.62)), (int(width * 0.36), int(height * 0.30)), 0, 0, 360, color, thick)
        cv2.ellipse(image, (width // 2, int(height * 0.40)), (int(width * 0.36), int(height * 0.38)), 0, 200, 360, color, thick)
    elif char == "7":
        cv2.line(image, (margin, margin), (width - margin, margin), color, thick)
        cv2.line(image, (width - margin, margin), (int(width * 0.30), height - margin), color, thick)
    elif char == "8":
        cv2.ellipse(image, (width // 2, int(height * 0.30)), (int(width * 0.34), int(height * 0.22)), 0, 0, 360, color, thick)
        cv2.ellipse(image, (width // 2, int(height * 0.70)), (int(width * 0.38), int(height * 0.26)), 0, 0, 360, color, thick)
    elif char == "9":
        cv2.ellipse(image, (width // 2, int(height * 0.38)), (int(width * 0.36), int(height * 0.28)), 0, 0, 360, color, thick)
        cv2.ellipse(image, (width // 2, int(height * 0.62)), (int(width * 0.36), int(height * 0.38)), 0, 0, 160, color, thick)
    return image


def _grid(glyph):
    ys, xs = np.where(glyph > 0)
    if len(xs) == 0:
        return None
    crop = glyph[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    height, width = crop.shape
    out = np.zeros((8, 4), np.float32)
    for row in range(8):
        y0 = int(row * height / 8)
        y1 = max(y0 + 1, int((row + 1) * height / 8))
        for col in range(4):
            x0 = int(col * width / 4)
            x1 = max(x0 + 1, int((col + 1) * width / 4))
            out[row, col] = float((crop[y0:y1, x0:x1] > 0).mean())
    return out


_TEMPLATES = {char: _grid(_render_digit(char)) for char in _DIGITS}


def _holes(glyph):
    height, width = glyph.shape
    filled = cv2.bitwise_not(glyph)
    mask = np.zeros((height + 2, width + 2), np.uint8)
    for x in range(0, width, max(1, width // 40)):
        if filled[0, x]:
            cv2.floodFill(filled, mask, (int(x), 0), 0)
        if filled[height - 1, x]:
            cv2.floodFill(filled, mask, (int(x), int(height - 1)), 0)
    for y in range(0, height, max(1, height // 40)):
        if filled[y, 0]:
            cv2.floodFill(filled, mask, (0, int(y)), 0)
        if filled[y, width - 1]:
            cv2.floodFill(filled, mask, (int(width - 1), int(y)), 0)
    count, _, stats, cent = cv2.connectedComponentsWithStats((filled > 0).astype(np.uint8), 8)
    found = []
    area = height * width
    for index in range(1, count):
        pixels = int(stats[index, cv2.CC_STAT_AREA])
        if pixels < max(24, int(0.012 * area)) or pixels > int(0.40 * area):
            continue
        found.append(float(cent[index][1]) / height)
    return found


def _parts(glyph):
    count, _, stats, cent = cv2.connectedComponentsWithStats((glyph > 0).astype(np.uint8), 8)
    height, width = glyph.shape
    found = []
    floor = max(40, int(0.015 * height * width))
    for index in range(1, count):
        pixels = int(stats[index, cv2.CC_STAT_AREA])
        if pixels < floor:
            continue
        x, y, box_w, box_h = [int(value) for value in stats[index, :4]]
        found.append({
            "a": pixels,
            "y": y / height,
            "b": (y + box_h) / height,
            "cx": float(cent[index][0]) / width,
            "cy": float(cent[index][1]) / height,
        })
    return found


def _from_grid(crop):
    grid = _grid(crop)
    if grid is None:
        return None
    ranked = sorted((float(np.abs(grid - template).mean()), char) for char, template in _TEMPLATES.items())
    best, second = ranked[0], ranked[1]
    if best[0] < 0.08 and second[0] - best[0] > 0.05:
        return best[1]
    return None


def _classify(glyph):
    ys, xs = np.where(glyph > 0)
    if len(xs) < 30:
        return None
    crop = glyph[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    height, width = crop.shape
    if height < 16 or width < 4:
        return None
    printed = _from_grid(crop)
    if printed:
        return printed
    aspect = width / float(height)
    holes = _holes(crop)
    if aspect < 0.48 and not holes:
        return "1"
    if len(holes) >= 2:
        centers = sorted(holes)
        if centers[0] < 0.48 < centers[-1]:
            return "8"
    grid = _grid(crop)
    open_lower = float(grid[5:, :2].mean()) if grid is not None else 1.0
    mid_bar = float(grid[3:5].mean()) if grid is not None else 0.0
    # A 4 leaves the lower left empty and crosses the middle. An upper hole is not a 9 by itself.
    if open_lower < 0.08 and mid_bar > 0.45:
        return "4"
    if len(holes) == 1:
        center_y = holes[0]
        if center_y < 0.42 and open_lower > 0.2:
            return "9"
        if center_y > 0.58:
            return "6"
        if 0.42 <= center_y <= 0.58:
            return "0"
    parts = _parts(crop)
    left = [part for part in parts if part["cx"] < 0.40]
    right = [part for part in parts if part["cx"] > 0.50]
    left_upper = any(part["cy"] < 0.48 for part in left)
    left_lower = any(part["cy"] > 0.58 for part in left)
    left_bridge = any(part["y"] < 0.35 and part["b"] > 0.72 for part in left)
    right_upper = any(part["cy"] < 0.48 or part["y"] < 0.30 for part in right)
    right_lower = any(part["cy"] > 0.58 or part["b"] > 0.75 for part in right)
    # An 8 can keep a connected right side and still show two separate left bowls.
    if left_upper and left_lower and right_upper and right_lower and not left_bridge:
        return "8"
    lower_left = [part for part in parts if part["cy"] > 0.62 and part["cx"] < 0.42]
    lower_right = [part for part in parts if part["cy"] > 0.58 and part["cx"] > 0.55]
    upper = [part for part in parts if part["cy"] < 0.42 and part["b"] < 0.78]
    tall = [part for part in parts if (part["b"] - part["y"]) > 0.82]
    if upper and lower_right and lower_left and not tall:
        return "8"
    if len(parts) >= 2 and not tall:
        upper_left = [part for part in parts if part["cy"] < 0.40 and part["cx"] < 0.55]
        if upper_left and lower_right and not lower_left:
            return "6"
    left_side = [part for part in parts if part["cx"] < 0.30]
    if tall and left_side and max(part["a"] for part in left_side) > tall[0]["a"] * 0.25:
        return "9"
    return None


def _date_mask(gray):
    work = gray
    if gray.shape[1] < 700:
        work = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    work = cv2.bilateralFilter(work, 9, 60, 60)
    clahe = cv2.createCLAHE(3.0, (8, 8)).apply(work)
    background = cv2.GaussianBlur(clahe, (0, 0), 28)
    normal = cv2.GaussianBlur(cv2.divide(clahe, background, scale=160), (0, 0), 1.6)
    low, high = np.percentile(normal, (2, 98))
    stretch = np.clip((normal.astype(np.float32) - low) / max(float(high - low), 1.0) * 255, 0, 255).astype(np.uint8)
    smooth = cv2.GaussianBlur(stretch, (0, 0), 2.8)
    level = float(np.percentile(smooth, 12))
    mask = (smooth <= level).astype(np.uint8) * 255
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    clean = np.zeros_like(mask)
    for index in range(1, count):
        if int(stats[index, cv2.CC_STAT_AREA]) >= 120 and int(stats[index, cv2.CC_STAT_HEIGHT]) >= 36:
            clean[labels == index] = 255
    return clean


def _slots(mask):
    height, width = mask.shape
    row = (mask > 0).sum(axis=1)
    if int(row.max()) < 8:
        return []
    window = max(40, int(height * 0.62))
    if window >= height:
        y0, y1 = 0, height
    else:
        scored = np.convolve(row.astype(np.float32), np.ones(window, np.float32), mode="valid")
        y0 = int(np.argmax(scored))
        y1 = y0 + window
    band = mask[y0:y1]
    column = (band > 0).sum(axis=0).astype(np.float32)
    column = cv2.GaussianBlur(column.reshape(1, -1), (1, 0), 9).ravel()
    positive = column[column > 0]
    threshold = max(8.0, float(np.percentile(positive, 35)) * 0.45) if positive.size else 8.0
    active = column > threshold
    spans = []
    start = None
    for index, flag in enumerate(active):
        if flag and start is None:
            start = index
        if not flag and start is not None:
            if index - start > 16:
                spans.append([start, index])
            start = None
    if start is not None and width - start > 16:
        spans.append([start, width])
    merged = []
    for left, right in spans:
        gap = max(16, int((right - left) * 0.2))
        if merged and left - merged[-1][1] < gap:
            merged[-1][1] = right
        else:
            merged.append([left, right])
    glyphs = []
    for left, right in merged:
        crop = band[:, left:right]
        ys = np.where(crop.any(axis=1))[0]
        xs = np.where(crop.any(axis=0))[0]
        if len(ys) < 2:
            continue
        glyphs.append(crop[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1])
    if len(glyphs) < 4:
        return glyphs
    heights = np.array([glyph.shape[0] for glyph in glyphs])
    typical = float(np.median(heights))
    return [glyph for glyph in glyphs if typical * 0.62 <= glyph.shape[0] <= typical * 1.45 and glyph.shape[0] > 28]


def read_relief_year(image) -> int | None:
    """Return a four-digit year, or None when the date is not readable."""
    if image is None or getattr(image, "size", 0) == 0:
        return None
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if gray.shape[0] < 24 or gray.shape[1] < 48:
        return None
    glyphs = _slots(_date_mask(gray))
    labels = [_classify(glyph) for glyph in glyphs]
    found = []
    for index in range(0, max(0, len(labels) - 3)):
        chunk = labels[index:index + 4]
        heights = [glyphs[index + offset].shape[0] for offset in range(4)]
        if any(item is None for item in chunk):
            continue
        if max(heights) > min(heights) * 1.45:
            continue
        if chunk[0] not in ("1", "2"):
            continue
        year = int("".join(chunk))
        if 1792 <= year <= 2026:
            found.append(year)
    unique = set(found)
    if len(unique) == 1:
        return found[0]
    return None


def relief_year_from_circle(frame, circle: dict | None) -> int | None:
    """Look along the bottom of a coin, where a cent date sits, including a small tilt."""
    if frame is None or not circle:
        return None
    height, width = frame.shape[:2]
    cx = float(circle["cx"])
    cy = float(circle["cy"])
    radius = float(circle["r"])
    if radius < 20:
        return None
    side = int(radius * 2.3)
    x0 = max(0, int(cx) - side // 2)
    y0 = max(0, int(cy) - side // 2)
    x1 = min(width, int(cx) + side // 2)
    y1 = min(height, int(cy) + side // 2)
    square = frame[y0:y1, x0:x1]
    if square.size == 0:
        return None
    gray = square if square.ndim == 2 else cv2.cvtColor(square, cv2.COLOR_BGR2GRAY)
    for angle in (0, 180, -12, 12, -24, 24, -36, 36, -48, 48):
        turned = gray
        if angle:
            center = (gray.shape[1] / 2.0, gray.shape[0] / 2.0)
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            turned = cv2.warpAffine(
                gray, matrix, (gray.shape[1], gray.shape[0]),
                flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
            )
        band_h, band_w = turned.shape
        bands = [turned[int(band_h * 0.52):int(band_h * 0.97), int(band_w * 0.08):int(band_w * 0.92)]]
        if band_h < band_w * 0.85:
            bands.insert(0, turned)
        else:
            bands.append(turned[int(band_h * 0.38):int(band_h * 0.98), int(band_w * 0.06):int(band_w * 0.94)])
        for band in bands:
            if band.shape[0] < 24 or band.shape[1] < 48:
                continue
            year = read_relief_year(band)
            if year:
                return year
    return None


def sample_date(text: str):
    """Gray picture of a drawn date, used to check the reader does not invent a year."""
    glyphs = [255 - _render_digit(char, 90) for char in text]
    height = 150
    width = sum(glyph.shape[1] for glyph in glyphs) + 30 * (len(glyphs) + 1)
    canvas = np.full((height, width), 148, np.uint8)
    noise = np.random.default_rng(3).normal(0, 7, canvas.shape)
    canvas = np.clip(canvas.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    x = 20
    for glyph in glyphs:
        ink = glyph < 128
        y = 24
        canvas[y:y + glyph.shape[0], x:x + glyph.shape[1]][ink] = 20
        x += glyph.shape[1] + 30
    return canvas

