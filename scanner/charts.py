"""Year-and-grade prices from CoinValueChecker chart pages.

The site has no public API. Each series page is a WordPress article whose
value table uses the same columns: Good, Fine, AU, MS, and Proof. This keeps
those figures and leaves the article text behind.
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

SITE = "https://www.coinvaluechecker.com/"
CACHE = Path(__file__).with_name("value_charts.json")

# Series that share a page point at the same slug.
CHARTS = {
    "indian-head": "indian-head-pennies-value-by-year",
    "flying-eagle": "flying-eagle-penny-value",
    "lincoln-wheat": "wheat-pennies-value-by-year",
    "lincoln-memorial": "lincoln-pennies-value-by-year",
    "lincoln-2009": "lincoln-pennies-value-by-year",
    "lincoln-shield": "lincoln-pennies-value-by-year",
    "lincoln-2026": "lincoln-pennies-value-by-year",
    "liberty-nickel": "v-nickel-value",
    "jefferson": "jefferson-nickels-value-by-year",
    "westward": "jefferson-nickels-value-by-year",
    "jefferson-return": "jefferson-nickels-value-by-year",
    "barber-dime": "barber-dime-value-by-year",
    "mercury": "mercury-dime-value-by-year",
    "roosevelt": "roosevelt-dime-value-by-year",
    "liberty-dime-2026": "roosevelt-dime-value-by-year",
    "barber-quarter": "barber-quarter-value-by-year",
    "standing-liberty": "standing-liberty-quarter-value-by-year",
    "washington": "washington-quarter-value-by-year",
    "state-quarter": "state-quarter-value-by-year",
    "atb-quarter": "america-the-beautiful-quarters-checklist",
    "women-quarter": "american-women-quarters-checklist",
    "barber-half": "barber-half-dollar-value-by-year",
    "walking-liberty": "walking-liberty-half-dollar-value-by-year",
    "franklin": "franklin-half-dollar-value-by-year",
    "kennedy": "kennedy-half-dollar-value-by-year",
    "enduring-liberty": "kennedy-half-dollar-value-by-year",
    "trade-dollar": "trade-dollar-value-by-year",
    "morgan": "morgan-dollar-value-by-year",
    "peace": "peace-dollar-value-by-year",
    "ike": "eisenhower-dollar-value-by-year",
    "sba": "susan-b-anthony-dollar-value",
    "sacagawea": "sacagawea-dollar-value-by-year",
    "native-american": "sacagawea-dollar-value-by-year",
    "presidential": "presidential-dollars-value-by-year",
    "innovation": "american-innovation-dollar-value",
}

_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_MONEY = re.compile(r"\$([0-9][0-9,]*(?:\.[0-9]+)?)")
_EXACT = re.compile(r"^(\d{4})(?:-(CC|[PSDWO]))?$")
_START = re.compile(r"^(\d{4})(?:-(CC|[PSDWO]))?\b")


def _cell_text(html: str) -> str:
    text = _TAG.sub(" ", html)
    text = text.replace("&mdash;", "—").replace("&ndash;", "–").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def _money(text: str) -> list[float] | None:
    if not text or "—" in text or text.strip() in {"-", "–"}:
        return None
    numbers = [float(match.replace(",", "")) for match in _MONEY.findall(text)]
    if not numbers:
        return None
    if len(numbers) == 1:
        return [numbers[0], numbers[0]]
    return [numbers[0], numbers[1]]


def _proof(label: str) -> bool:
    upper = label.upper()
    return " PR" in f" {upper}" or upper.endswith(" PR") or "DCAM" in upper or re.search(r"\bCAM\b", upper)


def parse_chart(html: str, source: str) -> dict:
    """Pull Good, Fine, AU, and MS ranges. An exact year row wins over a variety row."""
    years: dict[str, dict] = {}
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
        if not grades["good"] or _proof(label):
            continue
        exact = _EXACT.match(label)
        start = _START.match(label)
        if exact:
            year, mint = exact.group(1), exact.group(2) or ""
            key = f"{year}-{mint}" if mint else year
            years[key] = grades
            if mint and year not in years:
                years[year] = grades
            continue
        if not start:
            continue
        year, mint = start.group(1), start.group(2) or ""
        key = f"{year}-{mint}" if mint else year
        if key not in years:
            years[key] = grades
        if year not in years:
            years[year] = grades
    return {"source": source, "updated": updated, "years": years}


def load() -> dict:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"site": SITE, "charts": {}}


def save(book: dict) -> None:
    CACHE.write_text(json.dumps(book), encoding="utf-8")


def _fetch(slug: str) -> str:
    url = f"https://www.coinvaluechecker.com/{slug}/"
    request = urllib.request.Request(url, headers={"User-Agent": "coin-scanner"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8", "replace")


def refresh() -> dict:
    """Reload every chart page. A page that fails leaves the saved copy in place."""
    current = load()
    charts = dict(current.get("charts") or {})
    parsed: dict[str, dict] = {}
    for series_id, slug in CHARTS.items():
        if slug not in parsed:
            url = f"https://www.coinvaluechecker.com/{slug}/"
            try:
                parsed[slug] = parse_chart(_fetch(slug), url)
            except (OSError, TimeoutError, ValueError):
                parsed[slug] = charts.get(series_id) or {"source": url, "updated": "", "years": {}}
        chart = parsed[slug]
        if len(chart.get("years") or {}) >= 3:
            charts[series_id] = chart
    book = {"site": SITE, "charts": charts}
    if charts:
        save(book)
    return book


def price_for(series_id: str, year: int, mint: str = "", sheldon: str = "", book: dict | None = None) -> dict | None:
    """Pick the chart range that matches the wear band."""
    data = book if book is not None else load()
    chart = (data.get("charts") or {}).get(series_id) or {}
    years = chart.get("years") or {}
    key = str(year)
    if mint and f"{year}-{mint}" in years:
        key = f"{year}-{mint}"
    row = years.get(key)
    if not row or not row.get("good") or not row.get("fine"):
        return None
    good, fine, au = row["good"], row["fine"], row.get("au") or fine
    if sheldon.startswith("XF") and row.get("au"):
        low, high, grade = au[0], au[1], "AU"
    elif sheldon.startswith("F-") and row.get("au"):
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
        "source": chart.get("source") or SITE,
        "updated": chart.get("updated") or "",
    }

