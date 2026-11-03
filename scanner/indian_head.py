"""Indian Head cent prices from the CoinValueChecker year chart.

The site does not publish an API. This reads the public value tables and
serves the figures for the scanner. The article text is not stored.
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

SOURCE = "https://www.coinvaluechecker.com/indian-head-pennies-value-by-year/"
CACHE = Path(__file__).with_name("indian_head_values.json")

_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_MONEY = re.compile(r"\$([0-9][0-9,]*(?:\.[0-9]+)?)")
_YEAR = re.compile(r"^(\d{4})(?:-([SD]))?$")


def _cell_text(html: str) -> str:
    text = _TAG.sub(" ", html)
    text = text.replace("&mdash;", "—").replace("&ndash;", "–").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def _money(text: str) -> list[float] | None:
    if not text or "—" in text or text.strip() in {"-", "–"}:
        return None
    numbers = []
    for match in _MONEY.findall(text):
        numbers.append(float(match.replace(",", "")))
    if not numbers:
        return None
    if len(numbers) == 1:
        return [numbers[0], numbers[0]]
    return [numbers[0], numbers[1]]


def parse_chart(html: str) -> dict:
    """Pull GOOD, FINE, AU, and MS ranges from the published tables."""
    years: dict[str, dict] = {}
    varieties: list[dict] = []
    updated = ""
    stamp = re.search(r"Updated:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", html)
    if stamp:
        updated = stamp.group(1)
    for row_html in _ROW.findall(html):
        cells = [_cell_text(cell) for cell in _CELL.findall(row_html)]
        if len(cells) < 5 or not cells[0][:4].isdigit():
            continue
        label = cells[0]
        grades = {
            "good": _money(cells[1]),
            "fine": _money(cells[2]),
            "au": _money(cells[3]),
            "ms": _money(cells[4]),
        }
        if " PR" in f" {label}" or label.endswith(" PR"):
            varieties.append({"label": label, **grades})
            continue
        plain = _YEAR.match(label)
        if plain:
            years[label] = grades
        else:
            varieties.append({"label": label, **grades})
            # A plain year row is preferred. Use the first business row only when
            # the chart has no row that is just the year.
            year = label[:4]
            if year.isdigit() and year not in years and grades["good"]:
                years[year] = grades
    return {"source": SOURCE, "updated": updated, "years": years, "varieties": varieties}


def load() -> dict:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"source": SOURCE, "updated": "", "years": {}, "varieties": []}


def save(book: dict) -> None:
    CACHE.write_text(json.dumps(book, indent=2), encoding="utf-8")


def refresh() -> dict:
    """Reload the chart from the site. The saved file is used when the site is down."""
    request = urllib.request.Request(SOURCE, headers={"User-Agent": "coin-scanner"})
    with urllib.request.urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", "replace")
    book = parse_chart(html)
    if len(book["years"]) >= 40:
        save(book)
    return book


def price_for(year: int, mint: str = "", sheldon: str = "", book: dict | None = None) -> dict | None:
    """Pick the chart range that matches the wear band. Mint S is used only for 1908 and 1909."""
    if book is None:
        from scanner.charts import price_for as chart_price
        quoted = chart_price("indian-head", int(year), mint, sheldon)
        if quoted:
            return quoted
    data = book if book is not None else load()
    years = data.get("years") or {}
    key = str(year)
    if mint in {"S", "D"} and f"{year}-{mint}" in years:
        key = f"{year}-{mint}"
    row = years.get(key)
    if not row or not row.get("good") or not row.get("fine"):
        return None
    good, fine, au = row["good"], row["fine"], row["au"] or fine
    if sheldon.startswith("XF") and row.get("au"):
        low, high, grade = au[0], au[1], "AU"
    elif sheldon.startswith("F-"):
        low, high, grade = fine[0], au[0], "F to VF"
    else:
        low, high, grade = good[0], fine[1], "G to F"
    if high < low:
        low, high = high, low
    return {
        "key": key,
        "low": low,
        "high": high,
        "grade": grade,
        "source": data.get("source") or SOURCE,
        "updated": data.get("updated") or "",
    }

