"""Screen a close-up frame for coin defects a USB camera can actually see.

A single frame can show a rim bite, a long line, a pit, odd color, and
parallel split edges. Split edges become a doubled-die suspect only when a
second photo, with the lamp moved and the coin unmoved, keeps the same split.
"""

from __future__ import annotations

import math

import cv2
import numpy as np


def clock_label(cx: float, cy: float, x: float, y: float) -> str:
    """Clock position. Image y grows downward, so the angle runs clockwise from 3 o'clock."""
    angle = math.atan2(y - cy, x - cx)
    hours = (3.0 + angle / (2.0 * math.pi) * 12.0) % 12.0
    hour = int(hours)
    minute = int(round((hours - hour) * 60.0))
    if minute == 60:
        hour += 1
        minute = 0
    hour %= 12
    if hour == 0:
        hour = 12
    return f"{hour}:{minute:02d}"


def _contours(binary: np.ndarray):
    found = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(found) == 3:
        return found[1]
    return found[0]


def _disc_mask(shape, cx, cy, radius, shrink=1.0) -> np.ndarray:
    mask = np.zeros(shape[:2], np.uint8)
    cv2.circle(mask, (int(round(cx)), int(round(cy))), max(1, int(round(radius * shrink))), 255, -1)
    return mask


def find_coin(gray: np.ndarray):
    """Return (cx, cy, r) for the coin, or None."""
    height, width = gray.shape
    blur = cv2.GaussianBlur(gray, (9, 9), 2)
    grad_x = cv2.Sobel(blur, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(blur, cv2.CV_32F, 0, 1, ksize=3)
    grad = cv2.magnitude(grad_x, grad_y)
    min_r = int(min(height, width) * 0.12)
    max_r = int(min(height, width) * 0.48)
    best = None
    best_score = -1.0
    for param2 in (60, 42, 28):
        circles = cv2.HoughCircles(
            blur,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=min(height, width) // 2,
            param1=120,
            param2=param2,
            minRadius=min_r,
            maxRadius=max_r,
        )
        if circles is None:
            continue
        for raw in circles[0]:
            cx, cy, radius = (float(raw[0]), float(raw[1]), float(raw[2]))
            if cx < 8 or cy < 8 or cx > width - 8 or cy > height - 8:
                continue
            if _visible_fraction(width, height, cx, cy, radius) < 0.42:
                continue
            if not _edge_contrast(gray, cx, cy, radius):
                continue
            # The real rim is a strong edge. A clipped coin with that rim beats a weaker circle that happens to fit the frame.
            visible = _visible_fraction(width, height, cx, cy, radius)
            strength = _rim_strength(grad, width, height, cx, cy, radius)
            score = strength * visible
            if score > best_score:
                best_score = score
                best = (cx, cy, radius)
    return best


def _rim_strength(grad: np.ndarray, width: int, height: int, cx: float, cy: float, radius: float) -> float:
    values = []
    for index in range(36):
        angle = index * 2 * math.pi / 36
        x = int(round(cx + radius * math.cos(angle)))
        y = int(round(cy + radius * math.sin(angle)))
        if 1 <= x < width - 1 and 1 <= y < height - 1:
            values.append(float(grad[y, x]))
    if len(values) < 8:
        return 0.0
    return float(np.mean(values))


def _visible_fraction(width: int, height: int, cx: float, cy: float, radius: float) -> float:
    hits = 0
    steps = 36
    for index in range(steps):
        angle = index * 2 * math.pi / steps
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        if 1 <= x < width - 1 and 1 <= y < height - 1:
            hits += 1
    return hits / steps


def _edge_contrast(gray: np.ndarray, cx: float, cy: float, radius: float) -> bool:
    height, width = gray.shape
    angles = np.linspace(0, 2 * math.pi, 24, endpoint=False)
    inside = []
    outside = []
    for angle in angles:
        ix = int(round(cx + radius * 0.55 * math.cos(angle)))
        iy = int(round(cy + radius * 0.55 * math.sin(angle)))
        ox = int(round(cx + radius * 1.12 * math.cos(angle)))
        oy = int(round(cy + radius * 1.12 * math.sin(angle)))
        if 0 <= ix < width and 0 <= iy < height:
            inside.append(float(gray[iy, ix]))
        if 0 <= ox < width and 0 <= oy < height:
            outside.append(float(gray[oy, ox]))
    if len(inside) < 8 or len(outside) < 8:
        return False
    return abs(float(np.mean(inside)) - float(np.mean(outside))) >= 12.0


def _circular_median(values: np.ndarray, radius: int = 2) -> np.ndarray:
    pad = np.r_[values[-radius:], values, values[:radius]]
    windows = np.lib.stride_tricks.sliding_window_view(pad, radius * 2 + 1)
    return np.median(windows, axis=1)


def rim_profile(gray: np.ndarray, cx: float, cy: float, radius: float, samples: int = 360):
    """Measured outer radius at each angle, plus a mask of angles that stay on the image."""
    height, width = gray.shape
    angles = np.linspace(0, 2 * math.pi, samples, endpoint=False)
    # Search past the Hough radius. The circle often sits on the beads, and the planchet edge is farther out.
    fracs = np.linspace(0.86, 1.18, 40)
    cosine = np.cos(angles)[:, None]
    sine = np.sin(angles)[:, None]
    xs = np.rint(cx + (fracs[None, :] * radius) * cosine).astype(np.int32)
    ys = np.rint(cy + (fracs[None, :] * radius) * sine).astype(np.int32)
    valid = (xs >= 1) & (xs < width - 1) & (ys >= 1) & (ys < height - 1)
    sample = gray[np.clip(ys, 0, height - 1), np.clip(xs, 0, width - 1)].astype(np.float32)
    gradient = np.abs(np.diff(sample, axis=1))
    # The planchet edge is the outermost strong step. Beads and letters are inside it.
    peak = np.maximum(gradient.max(axis=1, keepdims=True), 1.0)
    strong = gradient >= np.maximum(10.0, 0.42 * peak)
    has = strong.any(axis=1)
    outermost = strong.shape[1] - 1 - np.argmax(strong[:, ::-1], axis=1)
    index = np.where(has, outermost, np.argmax(gradient, axis=1))
    measured = fracs[index] * radius
    on_image = valid.mean(axis=1) > 0.8
    return measured, angles, on_image


def _groups(mask: np.ndarray) -> list[tuple[int, int, int]]:
    """Return (start, end, length) groups on a circular boolean mask. Ends are inclusive."""
    count = len(mask)
    if count == 0 or not np.any(mask):
        return []
    if np.all(mask):
        return [(0, count - 1, count)]
    gap = int(np.argmax(~mask))
    rolled = np.roll(mask, -gap)
    groups = []
    start = None
    for index, bit in enumerate(rolled):
        if bit and start is None:
            start = index
        elif not bit and start is not None:
            groups.append((start, index - 1))
            start = None
    if start is not None:
        groups.append((start, len(rolled) - 1))
    mapped = []
    for start, end in groups:
        length = end - start + 1
        mapped.append(((start + gap) % count, (end + gap) % count, length))
    return mapped


def _focus_and_glare(gray: np.ndarray, hsv: np.ndarray, cx, cy, radius):
    mask = _disc_mask(gray.shape, cx, cy, radius, 0.82) > 0
    if not np.any(mask):
        return 0.0, 0.0, 0.0
    variance = float(cv2.Laplacian(gray, cv2.CV_32F)[mask].var())
    # A sharp coin under a desk lamp lands in the hundreds. A blur falls under ~30.
    focus = float(np.clip((math.log(variance + 1.0) - math.log(20.0)) / (math.log(500.0) - math.log(20.0)), 0.0, 1.0))
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    glare = float(np.mean((val >= 248) & (sat <= 35) & mask))
    return focus, variance, glare


def _split_edges(gray: np.ndarray, cx, cy, radius, px_per_mm: float | None):
    empty = {"rate": 0.0, "consistency": 0.0, "angle_deg": None, "count": 0, "edges": 0}
    height, width = gray.shape
    blur = cv2.GaussianBlur(gray, (0, 0), 1.1)
    gx = cv2.Sobel(blur, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blur, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    ang = np.arctan2(gy, gx)
    yy, xx = np.ogrid[:height, :width]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    annulus = (dist > radius * 0.10) & (dist < radius * 0.90)
    if int(annulus.sum()) < 50:
        return empty
    # Lettering is a small share of the field, so a low percentile is just the flat metal.
    peak = float(np.percentile(mag[annulus], 99.6))
    if peak < 28.0:
        return empty
    threshold = max(16.0, peak * 0.42)
    edges = annulus & (mag >= threshold)
    ys, xs = np.nonzero(edges)
    if len(xs) < 160:
        return empty
    if len(xs) > 2800:
        step = int(math.ceil(len(xs) / 2800))
        xs = xs[::step]
        ys = ys[::step]
    strength = mag[ys, xs] + 1e-6
    normal_x = gx[ys, xs] / strength
    normal_y = gy[ys, xs] / strength
    base = ang[ys, xs]
    if px_per_mm and px_per_mm > 1.0:
        start = max(3, int(round(0.10 * px_per_mm)))
        stop = max(start + 2, int(round(0.45 * px_per_mm)))
    else:
        start, stop = 4, 9
    pending = np.ones(len(xs), dtype=bool)
    twin_distance = np.zeros(len(xs), dtype=np.float32)
    shift_x = np.zeros(len(xs), dtype=np.float32)
    shift_y = np.zeros(len(xs), dtype=np.float32)
    # Search both ways. A doubled outline sits on one side of a stroke, and that side
    # is with the gradient for one edge and against it for the edge facing the other way.
    for sign in (1.0, -1.0):
        for distance in range(start, stop + 1):
            if not np.any(pending):
                break
            step_x = sign * normal_x * distance
            step_y = sign * normal_y * distance
            x2 = np.clip(np.rint(xs + step_x).astype(np.int32), 0, width - 1)
            y2 = np.clip(np.rint(ys + step_y).astype(np.int32), 0, height - 1)
            mid = max(1, distance // 2)
            xm = np.clip(np.rint(xs + sign * normal_x * mid).astype(np.int32), 0, width - 1)
            ym = np.clip(np.rint(ys + sign * normal_y * mid).astype(np.int32), 0, height - 1)
            delta = np.abs(base - ang[y2, x2])
            delta = np.minimum(delta, 2 * np.pi - delta)
            radius2 = np.sqrt((x2 - cx) ** 2 + (y2 - cy) ** 2)
            weaker = np.minimum(strength, mag[y2, x2])
            same_way = (
                (mag[y2, x2] >= threshold * 0.50)
                & (delta < 0.55)
                & (radius2 < radius * 0.95)
                & (mag[ym, xm] < 0.82 * weaker)
            )
            hit = pending & same_way
            twin_distance[hit] = distance
            shift_x[hit] = step_x[hit]
            shift_y[hit] = step_y[hit]
            pending[hit] = False
    twins = twin_distance > 0
    count = int(np.count_nonzero(twins))
    rate = float(count / max(len(xs), 1))
    result = {"rate": rate, "consistency": 0.0, "angle_deg": None, "count": count, "edges": int(len(xs))}
    if count < 30:
        return result
    # Doubling is an axis: the ghost lies to one side of some edges and the other side of the rest.
    offset_angle = np.arctan2(shift_y[twins], shift_x[twins])
    doubled = offset_angle * 2.0
    mean_cos = float(np.mean(np.cos(doubled)))
    mean_sin = float(np.mean(np.sin(doubled)))
    result["consistency"] = float(math.hypot(mean_cos, mean_sin))
    result["angle_deg"] = float(math.degrees(0.5 * math.atan2(mean_sin, mean_cos)))
    return result


def _off_center(gray: np.ndarray, cx, cy, radius):
    """Rim-width variation. Returns (score, clock or None). Portrait coins stay quiet because the outer legend is centered."""
    height, width = gray.shape
    count = 72
    angles = np.linspace(0, 2 * math.pi, count, endpoint=False)
    steps = np.linspace(0.58, 0.96, 28)
    texture = np.zeros((count, len(steps) - 4), np.float32)
    for index, angle in enumerate(angles):
        xs = np.clip(np.rint(cx + steps * radius * math.cos(angle)).astype(int), 0, width - 1)
        ys = np.clip(np.rint(cy + steps * radius * math.sin(angle)).astype(int), 0, height - 1)
        column = gray[ys, xs].astype(np.float32)
        texture[index] = np.array([column[i:i + 5].std() for i in range(len(column) - 4)])
    if float(np.percentile(texture, 95)) < 7.0:
        return 0.0, None
    threshold = max(5.0, float(np.percentile(texture, 90)) * 0.45)
    raw = np.full(count, np.nan, np.float32)
    for index in range(count):
        hits = np.where(texture[index] >= threshold)[0]
        if len(hits) == 0:
            continue
        outer = float(steps[min(len(steps) - 1, int(hits[-1]) + 2)])
        raw[index] = max(0.0, 0.96 - outer)
    good = np.isfinite(raw)
    if int(good.sum()) < count * 0.35:
        return 0.0, None
    known = np.flatnonzero(good)
    extended_index = np.r_[known - count, known, known + count]
    extended_value = np.r_[raw[good], raw[good], raw[good]]
    widths = np.interp(np.arange(count), extended_index, extended_value).astype(np.float32)
    widths = _circular_median(widths, 2)
    design = np.stack([np.ones(count), np.cos(angles), np.sin(angles)], axis=1)
    coef, *_ = np.linalg.lstsq(design, widths, rcond=None)
    prediction = design @ coef
    residual = float(np.mean((widths - prediction) ** 2))
    amplitude = float(math.hypot(coef[1], coef[2]))
    mean_width = float(abs(coef[0])) + 1e-6
    if amplitude * amplitude < residual * 3.0:
        return 0.0, None
    score = amplitude / mean_width
    narrow = int(np.argmin(widths))
    x = cx + radius * math.cos(float(angles[narrow]))
    y = cy + radius * math.sin(float(angles[narrow]))
    return float(score), clock_label(cx, cy, x, y)


def _color_findings(hsv, cx, cy, radius, metal: str):
    mask = _disc_mask(hsv.shape, cx, cy, radius, 0.78) > 0
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    findings = []
    markers = []
    green = mask & (hue >= 35) & (hue <= 95) & (sat >= 50) & (val >= 40)
    fraction = float(green.sum()) / max(int(mask.sum()), 1)
    if int(green.sum()) >= 100 and fraction >= 0.004:
        ys, xs = np.nonzero(green)
        mx, my = float(xs.mean()), float(ys.mean())
        findings.append({
            "kind": "color",
            "severity": "check",
            "title": "Green spot",
            "clock": clock_label(cx, cy, mx, my),
            "detail": "Green on the surface. On copper that is corrosion. On other coins it can be PVC damage. Do not rub it.",
        })
        markers.append({"kind": "color", "x": mx, "y": my})
    if metal in ("clad", "silver", "nickel"):
        copper = mask & (sat >= 70) & (val >= 60) & ((hue <= 15) | (hue >= 170))
        copper_fraction = float(copper.sum()) / max(int(mask.sum()), 1)
        if copper_fraction >= 0.02:
            ys, xs = np.nonzero(copper)
            mx, my = float(xs.mean()), float(ys.mean())
            findings.append({
                "kind": "lamination",
                "severity": "watch",
                "title": "Copper-colored spot",
                "clock": clock_label(cx, cy, mx, my),
                "detail": "A silver-colored coin with a copper patch. It can be a lamination, or a reflection of a nearby copper coin. Move the cloth and scan again.",
            })
            markers.append({"kind": "lamination", "x": mx, "y": my})
    return findings, markers


def _line_and_pits(gray, cx, cy, radius):
    mask = _disc_mask(gray.shape, cx, cy, radius, 0.84)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    dark = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
    light = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
    feature = cv2.max(dark, light)
    feature = cv2.bitwise_and(feature, feature, mask=mask)
    values = feature[mask > 0]
    findings = []
    markers = []
    lines = []
    if values.size > 20:
        cutoff = max(22.0, float(np.percentile(values, 99.3)))
        binary = np.where(feature >= cutoff, 255, 0).astype(np.uint8)
        found = cv2.HoughLinesP(
            binary, 1, np.pi / 180, threshold=28,
            minLineLength=max(18, int(radius * 0.42)),
            maxLineGap=10,
        )
        if found is not None:
            rows = np.asarray(found).reshape(-1, 4)
            ranked = sorted(
                (tuple(int(v) for v in row) for row in rows),
                key=lambda row: math.hypot(row[2] - row[0], row[3] - row[1]),
                reverse=True,
            )
            for x1, y1, x2, y2 in ranked[:3]:
                length = math.hypot(float(x2 - x1), float(y2 - y1))
                if length < radius * 0.42 or not _line_is_hairline(binary, x1, y1, x2, y2):
                    continue
                lines.append((int(x1), int(y1), int(x2), int(y2)))
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                findings.append({
                    "kind": "line",
                    "severity": "check",
                    "title": "Long line",
                    "clock": clock_label(cx, cy, mx, my),
                    "detail": f"A straight mark about {length / radius:.0%} of the coin's width. It can be a scratch or a die crack. The camera cannot tell which.",
                })
                markers.append({"kind": "line", "x": float(mx), "y": float(my), "x2": float(x2), "y2": float(y2), "x1": float(x1), "y1": float(y1)})
                break

    pit_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))
    pits = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, pit_kernel)
    pits = cv2.bitwise_and(pits, pits, mask=mask)
    pit_values = pits[mask > 0]
    pit_markers = []
    if pit_values.size > 20:
        cutoff = max(28.0, float(np.percentile(pit_values, 99.6)))
        binary = np.where(pits >= cutoff, 255, 0).astype(np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        for contour in _contours(binary):
            area = float(cv2.contourArea(contour))
            peri = float(cv2.arcLength(contour, True))
            if peri <= 1:
                continue
            circular = 4 * math.pi * area / (peri * peri)
            min_area = math.pi * (radius * 0.018) ** 2
            max_area = math.pi * (radius * 0.07) ** 2
            if circular < 0.55 or not (min_area <= area <= max_area):
                continue
            moment = cv2.moments(contour)
            if moment["m00"] == 0:
                continue
            mx = moment["m10"] / moment["m00"]
            my = moment["m01"] / moment["m00"]
            if any(math.hypot(mx - line[0], my - line[1]) < 12 or _point_near_segment(mx, my, line) for line in lines):
                continue
            pit_markers.append((mx, my, area))
    if pit_markers:
        pit_markers.sort(key=lambda item: item[2], reverse=True)
        shown = pit_markers[:6]
        severity = "check" if len(shown) >= 3 or shown[0][2] > math.pi * (radius * 0.04) ** 2 else "watch"
        title = "Round pit" if len(shown) == 1 else f"{len(shown)} round pits"
        findings.append({
            "kind": "pit",
            "severity": severity,
            "title": title,
            "clock": clock_label(cx, cy, shown[0][0], shown[0][1]),
            "detail": "A round dark spot inside the rim. It can be a bag mark, a corrosion pit, or debris. Brush nothing. Tip the light and see if it stays.",
        })
        for mx, my, _area in shown:
            markers.append({"kind": "pit", "x": float(mx), "y": float(my)})
    return findings, markers


def _line_is_hairline(binary: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> bool:
    """A scratch is a thin continuous mark. A word is tall, so its sides stay lit."""
    height, width = binary.shape
    length = int(math.hypot(x2 - x1, y2 - y1))
    if length < 8:
        return False
    xs = np.linspace(x1, x2, length)
    ys = np.linspace(y1, y2, length)
    core_x = np.clip(np.rint(xs).astype(int), 0, width - 1)
    core_y = np.clip(np.rint(ys).astype(int), 0, height - 1)
    if float(np.mean(binary[core_y, core_x] > 0)) < 0.55:
        return False
    px, py = -(y2 - y1) / length, (x2 - x1) / length
    side_hits = []
    for offset in (8, -8):
        sx = np.clip(np.rint(xs + px * offset).astype(int), 0, width - 1)
        sy = np.clip(np.rint(ys + py * offset).astype(int), 0, height - 1)
        side_hits.append(float(np.mean(binary[sy, sx] > 0)))
    return max(side_hits) < 0.28


def _point_near_segment(px, py, line, pad=8.0) -> bool:
    x1, y1, x2, y2 = line
    vx, vy = x2 - x1, y2 - y1
    length = math.hypot(vx, vy) + 1e-6
    t = max(0.0, min(1.0, ((px - x1) * vx + (py - y1) * vy) / (length * length)))
    qx, qy = x1 + t * vx, y1 + t * vy
    return math.hypot(px - qx, py - qy) <= pad


def _rim_findings(measured, angles, on_image, cx, cy, radius):
    # The frame edge is not a bite. Ignore a few samples next to any angle that left the picture.
    invalid = ~on_image
    if np.any(invalid):
        padded = np.r_[invalid[-3:], invalid, invalid[:3]]
        invalid = np.array([padded[i:i + 7].any() for i in range(len(invalid))])
        on_image = ~invalid
    smooth = _circular_median(measured, 2)
    center = float(np.median(smooth[on_image])) if np.any(on_image) else float(np.median(smooth))
    dent = center - smooth
    dent = np.where(on_image, dent, 0.0)
    mad = float(np.median(np.abs(dent[on_image]))) + 1e-3 if np.any(on_image) else 1.0
    # A beaded rim wobbles a few pixels. A bite has to be a clear chunk of the planchet edge.
    threshold = max(radius * 0.045, 8.0, mad * 6.0)
    bite_mask = (dent > threshold) & on_image
    bump_mask = ((-dent) > threshold) & on_image
    findings = []
    markers = []
    count = len(smooth)

    def describe(mask, inward: bool):
        for start, end, length in _groups(mask):
            if length < 2 or length > count * 0.45:
                continue
            if start <= end:
                indexes = np.arange(start, end + 1)
            else:
                indexes = np.r_[np.arange(start, count), np.arange(0, end + 1)]
            deepest = int(indexes[np.argmax(dent[indexes] if inward else -dent[indexes])])
            depth = float(dent[deepest] if inward else -dent[deepest])
            span = length / count * 360.0
            angle = float(angles[deepest])
            x = cx + center * math.cos(angle)
            y = cy + center * math.sin(angle)
            clock = clock_label(cx, cy, x, y)
            depth_frac = depth / radius
            if inward and span >= 18 and depth_frac >= 0.03:
                findings.append({
                    "kind": "bite",
                    "severity": "check",
                    "title": "Large rim bite",
                    "clock": clock,
                    "depth_frac": depth_frac,
                    "detail": f"A wide piece of rim is missing around {clock}, about {depth_frac:.0%} of the radius. It can be damage or a broken planchet.",
                })
            elif inward:
                findings.append({
                    "kind": "bite",
                    "severity": "check" if depth_frac >= 0.02 else "watch",
                    "title": "Rim bite",
                    "clock": clock,
                    "depth_frac": depth_frac,
                    "detail": f"Missing metal at {clock}. The camera cannot tell a mint-made chip from a later knock.",
                })
            else:
                findings.append({
                    "kind": "bump",
                    "severity": "watch",
                    "title": "Raised rim spot",
                    "clock": clock,
                    "depth_frac": depth_frac,
                    "detail": f"The rim sticks out at {clock}. It can be lint, a cud, or a die-crack lip. Do not scrub the coin. Look again after you blow the dust off.",
                })
            markers.append({"kind": "bite" if inward else "bump", "x": float(x), "y": float(y)})

    describe(bite_mask, True)
    describe(bump_mask, False)
    # Sparkline of the dent as a fraction of radius, 120 steps.
    picked = np.linspace(0, count, 120, endpoint=False).astype(int) % count
    rim = [round(float(dent[i] / radius), 4) for i in picked]
    return findings, markers, rim


def _tilt(measured, on_image) -> float:
    usable = measured[on_image] if np.any(on_image) else measured
    if len(usable) < 8:
        return 1.0
    low = float(np.percentile(usable, 8))
    high = float(np.percentile(usable, 92))
    if low <= 1:
        return 1.0
    return high / low


def surface_metal(hsv: np.ndarray, cx: float, cy: float, radius: float) -> str:
    """Tell a gray steel cent from a copper cent. Silver coins are gray too, so the caller checks the series."""
    mask = _disc_mask(hsv.shape, cx, cy, radius, 0.72) > 0
    hue = hsv[:, :, 0][mask]
    sat = hsv[:, :, 1][mask]
    val = hsv[:, :, 2][mask]
    usable = (val > 45) & (val < 250)
    if int(usable.sum()) < 40:
        return "unknown"
    hue = hue[usable]
    sat = sat[usable]
    val = val[usable]
    copper = ((hue <= 18) | (hue >= 170)) & (sat >= 40)
    copper_share = float(copper.mean())
    if copper_share >= 0.28:
        return "copper"
    # A real steel cent is bright zinc-gray. A dark, toned copper cent is not.
    bright = float(np.percentile(val, 70))
    if float(np.median(sat)) <= 35 and bright >= 165 and copper_share < 0.12:
        return "steel"
    return "unknown"


def _copper_color(hsv: np.ndarray, cx: float, cy: float, radius: float) -> str:
    """Red, red-brown, or brown for a copper coin. Empty when the metal is not copper."""
    mask = _disc_mask(hsv.shape, cx, cy, radius, 0.62) > 0
    if int(mask.sum()) < 40:
        return ""
    hue = hsv[:, :, 0][mask]
    sat = hsv[:, :, 1][mask]
    val = hsv[:, :, 2][mask]
    copper = ((hue <= 18) | (hue >= 170)) & (sat >= 35) & (val > 40) & (val < 250)
    if float(copper.mean()) < 0.25:
        return ""
    median_value = float(np.median(val[copper]))
    median_sat = float(np.median(sat[copper]))
    if median_value >= 145 and median_sat >= 80:
        return "RD"
    if median_value >= 100 and median_sat >= 50:
        return "RB"
    return "BN"


def _wear(gray: np.ndarray, cx: float, cy: float, radius: float, focus: float, glare: float) -> dict:
    """A wide Sheldon band from how much design is left. Not a certified grade."""
    empty = {"wear": "", "sheldon": ""}
    if focus < 0.22 or glare >= 0.10:
        return empty
    height, width = gray.shape
    yy, xx = np.ogrid[:height, :width]
    inner = (xx - cx) ** 2 + (yy - cy) ** 2 <= (radius * 0.78) ** 2
    if int(inner.sum()) < 80:
        return empty
    blur = cv2.GaussianBlur(gray, (0, 0), 1.2)
    gx = cv2.Sobel(blur, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blur, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(gx, gy)
    edges = (magnitude > 28) & inner
    if int(edges.sum()) < 40:
        design = 0.0
    else:
        design = float(magnitude[edges].mean())
    if design >= 65:
        return {"wear": "Extremely Fine to About Uncirculated", "sheldon": "XF-40 to AU-50"}
    if design >= 42:
        return {"wear": "Fine to Very Fine", "sheldon": "F-12 to VF-30"}
    return {"wear": "Good to Fine", "sheldon": "G-4 to F-12"}


def analyze(bgr: np.ndarray, spec: dict, px_per_mm: float | None = None) -> dict:
    height, width = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    base = {
        "locked": False,
        "frame_w": width,
        "frame_h": height,
        "circle": None,
        "focus": 0.0,
        "glare": 0.0,
        "tilt": 1.0,
        "diameter_px": None,
        "diameter_mm": None,
        "expected_mm": spec.get("diameter_mm"),
        "rim": [],
        "markers": [],
        "findings": [],
        "doubling": {"rate": 0.0, "consistency": 0.0, "angle_deg": None, "count": 0, "edges": 0},
        "hint": "No coin yet. Set it on a dark cloth, fill the ring, and light it from one side.",
        "surface": "unknown",
    }
    found = find_coin(gray)
    if found is None:
        return base
    cx, cy, radius = found
    visible = _visible_fraction(width, height, cx, cy, radius)
    clipped = visible < 0.90
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    surface = surface_metal(hsv, cx, cy, radius)
    focus, _raw, glare = _focus_and_glare(gray, hsv, cx, cy, radius)
    measured, angles, on_image = rim_profile(gray, cx, cy, radius)
    rim_findings, rim_markers, rim = _rim_findings(measured, angles, on_image, cx, cy, radius)
    tilt = _tilt(measured, on_image)
    findings = []
    markers = list(rim_markers)
    soft = focus < 0.22
    if soft:
        findings.append({
            "kind": "focus",
            "severity": "info",
            "title": "Soft focus",
            "clock": None,
            "detail": "The picture is soft. Move the lens ring, or move the camera, until the focus bar climbs. Small marks are not trustworthy yet.",
        })
    if glare >= 0.06:
        findings.append({
            "kind": "glare",
            "severity": "info",
            "title": "Glare",
            "clock": None,
            "detail": "A hot spot is blowing out the surface. Tip the lamp down and toward the side so the coin goes satin, not mirror.",
        })
    if tilt >= 1.12:
        findings.append({
            "kind": "tilt",
            "severity": "info",
            "title": "Camera is tilted",
            "clock": None,
            "detail": "The coin is an oval in the picture. Square the camera to the coin or the rim reading will lie.",
        })
    if clipped:
        findings.append({
            "kind": "framing",
            "severity": "info",
            "title": "Coin is cut off",
            "clock": None,
            "detail": "Part of the disc is outside the picture. Move the camera back until the ring closes around the whole coin.",
        })
    if radius < min(height, width) * 0.22:
        findings.append({
            "kind": "framing",
            "severity": "info",
            "title": "Move closer",
            "clock": None,
            "detail": "The coin is small in the frame. A USB 2.0 camera only has a chance at doubling and small bites when the coin fills the ring.",
        })

    if clipped:
        # A coin running off the picture will look bitten. Wait until the whole disc is in frame.
        rim_findings, rim_markers, rim = [], [], []
        markers = []
    washed = glare >= 0.10
    if washed:
        rim_findings, rim_markers, rim = [], [], rim
        markers = [marker for marker in markers if marker.get("kind") not in ("bite", "bump")]
    findings.extend(rim_findings)
    if not soft and not clipped and not washed:
        line_findings, line_markers = _line_and_pits(gray, cx, cy, radius)
        findings.extend(line_findings)
        markers.extend(line_markers)
        split = _split_edges(gray, cx, cy, radius, px_per_mm)
        consistent = split["consistency"] >= 0.40 and split["count"] >= 70 and split["rate"] >= 0.07
        obvious = split["rate"] >= 0.18 and split["consistency"] >= 0.34 and split["count"] >= 40
        if consistent or obvious:
            findings.append({
                "kind": "split",
                "severity": "watch",
                "title": "Parallel split edges",
                "clock": None,
                "detail": "Some edges have a twin just beside them. A shadow does this too. Keep the coin still, move the lamp about a quarter turn, and take light shot B.",
            })
    else:
        split = {"rate": 0.0, "consistency": 0.0, "angle_deg": None, "count": 0, "edges": 0}

    if glare < 0.12 and not clipped:
        color_findings, color_markers = _color_findings(hsv, cx, cy, radius, spec.get("metal", "clad"))
        findings.extend(color_findings)
        markers.extend(color_markers)

    score, off_clock = _off_center(gray, cx, cy, radius)
    if score >= 0.28 and off_clock and not soft and not clipped:
        findings.append({
            "kind": "off_center",
            "severity": "watch",
            "title": "Design sits off center",
            "clock": off_clock,
            "detail": f"The devices sit toward {off_clock}. Confirm it by eye. A coin that is tipped in the light can fake this.",
        })

    diameter_px = float(radius * 2.0)
    diameter_mm = None
    if px_per_mm and px_per_mm > 0 and not clipped:
        diameter_mm = diameter_px / px_per_mm
        expected = float(spec.get("diameter_mm") or 0)
        if spec.get("size_check", True) and expected > 0:
            delta = (diameter_mm - expected) / expected
            if abs(delta) > 0.08:
                findings.append({
                    "kind": "size",
                    "severity": "check",
                    "title": "Size does not match",
                    "clock": None,
                    "detail": f"This reads about {diameter_mm:.1f} mm. The selected coin is {expected:.2f} mm. Pick the type you are holding, or calibrate again on a coin you know.",
                })

    order = {"check": 0, "watch": 1, "info": 2}
    findings.sort(key=lambda item: order.get(item["severity"], 9))
    findings = findings[:10]
    serious = [item for item in findings if item["severity"] in ("check", "watch")]
    if not serious:
        hint = "Nothing stands out at this resolution. Flip the coin and scan the other side."
    elif any(item["kind"] == "split" for item in findings):
        hint = "Split edges are on the screen. Take the two-light test before you call it a doubled die."
    else:
        hint = "Marks are on the screen. Each one is a place to look, not a grade."

    return {
        "locked": True,
        "frame_w": width,
        "frame_h": height,
        "circle": {"cx": cx, "cy": cy, "r": radius},
        "focus": focus,
        "glare": glare,
        "tilt": tilt,
        "diameter_px": diameter_px,
        "diameter_mm": diameter_mm,
        "expected_mm": spec.get("diameter_mm"),
        "rim": rim,
        "markers": markers[:12],
        "findings": findings,
        "doubling": {
            "rate": float(split["rate"]),
            "consistency": float(split["consistency"]),
            "angle_deg": split["angle_deg"],
            "count": int(split["count"]),
            "edges": int(split["edges"]),
        },
        "off_center_score": score,
        "hint": hint,
        "surface": surface,
        "condition": {
            "color": _copper_color(hsv, cx, cy, radius),
            **_wear(gray, cx, cy, radius, focus, glare),
        },
    }


def light_verdict(shot_a: dict | None, shot_b: dict | None) -> dict | None:
    """Compare two doubling signatures taken with the coin held still and the lamp moved."""
    if not shot_a or not shot_b:
        return None
    angle_a = shot_a.get("angle_deg")
    angle_b = shot_b.get("angle_deg")
    rate_a = float(shot_a.get("rate") or 0)
    rate_b = float(shot_b.get("rate") or 0)
    if angle_a is None or angle_b is None or rate_a < 0.06 or rate_b < 0.06:
        return {
            "verdict": "weak",
            "title": "Light test is too weak",
            "detail": "One of the shots does not have a clear split. Get the coin sharp, light it from the side, and shoot A and B again.",
        }
    # The split is an axis, so 10° and 190° are the same direction.
    delta = abs(float(angle_a) - float(angle_b)) % 180.0
    delta = min(delta, 180.0 - delta)
    if delta >= 50.0:
        return {
            "verdict": "relief",
            "title": "Shadow, not a doubled die",
            "detail": f"The split moved {delta:.0f}° when the lamp moved. That is relief shadow. A doubled die stays put.",
        }
    if delta <= 25.0 and float(shot_a.get("consistency") or 0) > 0.4 and float(shot_b.get("consistency") or 0) > 0.4:
        return {
            "verdict": "die",
            "title": "Doubled-die suspect",
            "detail": f"The split stayed within {delta:.0f}° after the lamp moved. Worth a loupe on the letters and the date. This is a screen, not an authentication.",
        }
    return {
        "verdict": "unsure",
        "title": "Light test is inconclusive",
        "detail": f"The split moved {delta:.0f}°. Shoot it again with a bigger lamp move, and do not rotate the coin.",
    }

