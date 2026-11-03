"""Read a year and mint mark from a coin that is already in the picture.

Uses the Windows OCR engine. A 640x480 camera often cannot see the mint
letter, and the date is only on one side, so a miss is reported instead of guessed.
"""

from __future__ import annotations

import re

import cv2

from scanner.relief import relief_year_from_circle

MINTS = {
    "P": "Philadelphia",
    "D": "Denver",
    "S": "San Francisco",
    "W": "West Point",
    "O": "New Orleans",
    "CC": "Carson City",
}

_YEAR = re.compile(r"(?:17|18|19|20)\d{2}")


def parse_words(words: list[tuple[str, dict]]) -> dict:
    """Pick a strike year and a nearby mint letter from OCR words."""
    years = []
    mints = []
    for text, box in words:
        cleaned = re.sub(r"[^A-Z0-9]", "", (text or "").upper())
        for match in _YEAR.findall(cleaned):
            year = int(match)
            if 1792 <= year <= 2026:
                years.append((year, box or {}))
        if cleaned in MINTS:
            mints.append((cleaned, box or {}))
    if not years:
        return {"year": None, "mint": "", "mint_name": ""}
    # A dual date reads 1776 and 2026. The coin was struck in the later year.
    year = max(item[0] for item in years)
    year_box = next(box for found, box in years if found == year)
    mint = _nearest_mint(year_box, mints)
    return {"year": year, "mint": mint, "mint_name": MINTS.get(mint, "")}


def _nearest_mint(year_box: dict, mints: list[tuple[str, dict]]) -> str:
    if not mints:
        return ""
    center_x = float(year_box.get("x") or 0) + float(year_box.get("width") or 0) / 2
    center_y = float(year_box.get("y") or 0) + float(year_box.get("height") or 0) / 2
    limit = max(float(year_box.get("height") or 24) * 5, 48)
    best = ""
    best_distance = limit
    for letter, box in mints:
        mint_x = float(box.get("x") or 0) + float(box.get("width") or 0) / 2
        mint_y = float(box.get("y") or 0) + float(box.get("height") or 0) / 2
        distance = abs(mint_x - center_x) + abs(mint_y - center_y)
        if distance < best_distance:
            best = letter
            best_distance = distance
    return best


def _words_from_result(result: dict) -> list[tuple[str, dict]]:
    found = []
    for line in result.get("lines") or []:
        for word in line.get("words") or []:
            found.append((word.get("text") or "", word.get("bounding_rect") or {}))
    return found


def _crop(frame, circle: dict):
    height, width = frame.shape[:2]
    cx, cy, radius = float(circle["cx"]), float(circle["cy"]), float(circle["r"])
    pad = int(radius * 1.08)
    x0 = max(0, int(cx) - pad)
    y0 = max(0, int(cy) - pad)
    x1 = min(width, int(cx) + pad)
    y1 = min(height, int(cy) + pad)
    crop = frame[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    return cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)


def _prepared(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(3.0, (8, 8)).apply(gray)
    yield cv2.cvtColor(clahe, cv2.COLOR_GRAY2BGR)
    # Steel cents are gray on gray. A strong local contrast lift is what makes the date readable.
    blur = cv2.GaussianBlur(clahe, (0, 0), 2.5)
    sharp = cv2.addWeighted(clahe, 2.4, blur, -1.4, 8)
    yield cv2.cvtColor(sharp, cv2.COLOR_GRAY2BGR)
    yield cv2.cvtColor(cv2.bitwise_not(sharp), cv2.COLOR_GRAY2BGR)


def read_coin(frame, circle: dict | None) -> dict:
    """Return year, mint letter, and mint name. Empty when the date is not on this side."""
    empty = {"year": None, "mint": "", "mint_name": ""}
    if frame is None or not circle:
        return empty
    crop = _crop(frame, circle)
    if crop is None:
        return empty
    try:
        import winocr
    except ImportError:
        return empty
    pictures = [crop, cv2.rotate(crop, cv2.ROTATE_180)]
    for picture in pictures:
        height, width = picture.shape[:2]
        # The date is normally on the lower rim. Reading a focused band keeps
        # the portrait and lettering from overwhelming Windows OCR. The upper
        # band covers an upside-down coin after the 180-degree pass above.
        regions = [
            picture,
            picture[int(height * 0.42):int(height * 0.98), int(width * 0.05):int(width * 0.95)],
            picture[int(height * 0.55):int(height * 0.99), int(width * 0.02):int(width * 0.98)],
        ]
        for region in regions:
            if region.size == 0:
                continue
            for view in _prepared(region):
                try:
                    raw = winocr.recognize_cv2_sync(view, "en")
                except (AssertionError, OSError, RuntimeError):
                    return empty
                parsed = parse_words(_words_from_result(raw))
                if parsed["year"]:
                    return parsed
    try:
        year = relief_year_from_circle(frame, circle)
    except (cv2.error, ValueError):
        year = None
    if year:
        return {"year": year, "mint": "", "mint_name": ""}
    return empty

