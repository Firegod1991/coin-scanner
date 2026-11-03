const NS = "http://www.w3.org/2000/svg";

const feed = document.getElementById("feed");
const svg = document.getElementById("reticle");
const coinButton = document.getElementById("coin-button");
const drawer = document.getElementById("drawer");
const search = document.getElementById("search");
const list = document.getElementById("list");
const findingsEl = document.getElementById("findings");
const guideEl = document.getElementById("guide");
const sizeEl = document.getElementById("size");
const focusEl = document.getElementById("focus");
const cameraEl = document.getElementById("camera");
const lightEl = document.getElementById("light-result");

let catalog = [];
let indianBook = { years: {}, updated: "", source: "" };
let valueBook = { charts: {} };
let state = {};
let cameraKey = "";
let defectBook = { note: "", series: {} };
let phase = "absent";
let steady = 0;
let sides = { first: null, second: null, away: false };

function startFeed() {
  feed.src = `/api/stream?t=${Date.now()}`;
}
startFeed();
feed.addEventListener("error", () => {
  setTimeout(startFeed, 800);
});

function post(url, body) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  }).then((response) => response.json());
}

function seriesById(id) {
  return catalog.find((item) => item.id === id) || null;
}

function fillSeries() {
  const query = search.value.trim().toLowerCase();
  list.replaceChildren();
  fillSaved();
  let group = "";
  catalog.forEach((series) => {
    const haystack = `${series.name} ${series.years} ${series.group} ${(series.errors || []).join(" ")}`.toLowerCase();
    if (query && !haystack.includes(query)) return;
    if (series.group !== group) {
      group = series.group;
      const label = document.createElement("div");
      label.className = "group";
      label.textContent = group;
      list.appendChild(label);
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = "series" + (series.id === state.series_id ? " current" : "");
    button.textContent = series.name;
    const years = document.createElement("small");
    years.textContent = series.years;
    button.appendChild(years);
    button.addEventListener("click", () => {
      post("/api/series", { id: series.id });
      drawer.hidden = true;
    });
    list.appendChild(button);
  });
}

function placeOverlay() {
  const width = state.frame_w || 1280;
  const height = state.frame_h || 720;
  const scale = Math.min(window.innerWidth / width, window.innerHeight / height);
  const boxW = width * scale;
  const boxH = height * scale;
  svg.style.left = `${(window.innerWidth - boxW) / 2}px`;
  svg.style.top = `${(window.innerHeight - boxH) / 2}px`;
  svg.style.width = `${boxW}px`;
  svg.style.height = `${boxH}px`;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
}

function el(name, attrs) {
  const node = document.createElementNS(NS, name);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
  return node;
}

const market = { silver: null, gold: null, copper: null, updated: null };

const LIVE = {
  "barber-dime": ["silver", 0.07234],
  mercury: ["silver", 0.07234],
  "barber-quarter": ["silver", 0.18084],
  "standing-liberty": ["silver", 0.18084],
  "barber-half": ["silver", 0.36169],
  "walking-liberty": ["silver", 0.36169],
  franklin: ["silver", 0.36169],
  morgan: ["silver", 0.77344],
  peace: ["silver", 0.77344],
  "gold-dollar": ["gold", 0.04837, 1.6],
  "quarter-eagle": ["gold", 0.12094, 1.35],
  "half-eagle": ["gold", 0.24187, 1.3],
  eagle: ["gold", 0.48375, 1.2],
  "double-eagle": ["gold", 0.9675, 1.12],
};

function dollars(amount) {
  if (amount < 1) return `${Math.round(amount * 100)}¢`;
  if (amount >= 100) return `$${Math.round(amount).toLocaleString("en-US")}`;
  if (amount >= 20) return `$${Math.round(amount)}`;
  return `$${amount.toFixed(2)}`;
}

function moneyRange(low, high) {
  const left = dollars(low);
  const right = dollars(high);
  return left === right ? left : `${left}–${right}`;
}

function silverBand(ounces) {
  if (!market.silver) return "live silver loading";
  const melt = ounces * market.silver;
  return moneyRange(melt, melt * 1.25);
}

function goldBand(ounces, high = 1.15) {
  if (!market.gold) return "live gold loading";
  const melt = ounces * market.gold;
  return moneyRange(melt, melt * high);
}

function copperCentBand() {
  if (!market.copper) return "live copper loading";
  const melt = 2.9545 / 453.592 * market.copper;
  return moneyRange(melt * 0.9, Math.max(melt * 1.5, 0.02));
}

function livePrice(id, fallback) {
  const row = LIVE[id];
  if (!row) return fallback;
  if (row[0] === "silver") return silverBand(row[1]);
  return goldBand(row[1], row[2] || 1.15);
}

function quoteSuffix(kind) {
  if (kind === "silver" && market.silver) return ` · live silver $${market.silver.toFixed(2)}/oz`;
  if (kind === "gold" && market.gold) return ` · live gold $${Math.round(market.gold).toLocaleString("en-US")}/oz`;
  if (kind === "copper" && market.copper) return ` · live copper $${market.copper.toFixed(2)}/lb`;
  return "";
}

const FACE = {
  "lincoln-2009": ["A 2009 cent spends at one cent.", "1¢"],
  "lincoln-shield": ["A shield cent spends at one cent.", "1¢"],
  "lincoln-2026": ["The 2026 cent spends at one cent.", "1¢"],
  westward: ["A Westward Journey nickel spends at five cents.", "5¢"],
  "jefferson-return": ["A modern Jefferson nickel spends at five cents. The 2026 dual date does not change that.", "5¢"],
  "liberty-dime-2026": ["The 2026 dime spends at ten cents.", "10¢"],
  "state-quarter": ["A state quarter spends at 25 cents.", "25¢"],
  "territories-quarter": ["A 2009 territory quarter spends at 25 cents.", "25¢"],
  "atb-quarter": ["An America the Beautiful quarter spends at 25 cents.", "25¢"],
  "delaware-crossing": ["The 2021 Crossing the Delaware quarter spends at 25 cents.", "25¢"],
  "women-quarter": ["An American Women quarter, including Anna May Wong, spends at 25 cents.", "25¢"],
  "semi-quarter": ["A 2026 quarter spends at 25 cents.", "25¢"],
  "enduring-liberty": ["The 2026 half dollar spends at 50 cents.", "50¢"],
  sba: ["A Susan B. Anthony dollar spends at one dollar.", "$1"],
  sacagawea: ["A Sacagawea dollar spends at one dollar.", "$1"],
  "native-american": ["A Native American dollar spends at one dollar.", "$1"],
  presidential: ["A presidential dollar spends at one dollar. A missing edge inscription is the exception, and this view cannot see the edge.", "$1"],
  innovation: ["An American Innovation dollar spends at one dollar.", "$1"],
  "semi-dollar-2026": ["The 2026 dollar spends at one dollar.", "$1"],
  ike: ["A clad Eisenhower dollar spends near one dollar. A 40% silver Ike from a Mint pack is about $16–$22 in metal.", "$1–$2"],
};

const PREMIUM = {
  "half-cent": ["A worn half cent still sells well above half a cent.", "$40–$120"],
  "large-cent": ["A common worn large cent sells above one cent. Early dates are more.", "$15–$50"],
  "flying-eagle": ["Flying Eagle cents sell above one cent.", "$25–$80"],
  "indian-head": ["A common Indian Head cent sells above one cent.", "$1–$4"],
  "lincoln-wheat": ["A common wheat cent is worth more than one cent. A 1909-S VDB or a 1955 doubled die is far more.", "10¢–30¢"],
  "two-cent": ["Two-cent pieces sell above two cents.", "$12–$30"],
  "three-silver": ["Three-cent silver sells well above melt. The coin is small and scarce.", "$25–$70"],
  "three-nickel": ["Three-cent nickels sell above three cents.", "$12–$28"],
  "shield-nickel": ["Shield nickels sell above five cents.", "$20–$50"],
  "liberty-nickel": ["A common Liberty nickel sells above five cents. The 1913 is a famous rarity and is not priced here.", "$2–$8"],
  buffalo: ["A Buffalo nickel with a readable date sells above five cents.", "$1–$4"],
  "half-dime": ["Half dimes are silver and sell well above five cents.", "$30–$90"],
  "early-dime": ["Early dimes are silver. Common worn ones vary a lot by type.", "$40–$150"],
  "seated-dime": ["Seated dimes are 90% silver, and common dates sell above the metal.", "$15–$40"],
  "barber-dime": ["Barber dimes are 90% silver. The price follows the live silver quote.", null],
  mercury: ["Mercury dimes are 90% silver. The price follows the live silver quote.", null],
  "twenty-cent": ["Twenty-cent pieces are scarce silver.", "$100–$250"],
  "early-quarter": ["Early quarters are silver. Type and date move the price a lot.", "$80–$250"],
  "seated-quarter": ["Seated quarters are 90% silver, and common dates sell above the metal.", "$25–$70"],
  "barber-quarter": ["Barber quarters are 90% silver. The price follows the live silver quote.", null],
  "standing-liberty": ["Standing Liberty quarters are 90% silver. The 1916 is much more than this range.", null],
  "early-half": ["Early half dollars are silver. Common worn ones still vary widely.", "$100–$400"],
  "seated-half": ["Seated half dollars are 90% silver.", "$40–$100"],
  "barber-half": ["Barber half dollars are 90% silver. The price follows the live silver quote.", null],
  "walking-liberty": ["Walking Liberty halves are 90% silver. The price follows the live silver quote.", null],
  franklin: ["Franklin halves are 90% silver. The price follows the live silver quote.", null],
  "early-dollar": ["Early dollars are rare silver. This is not an appraisal.", "$1,500 and up"],
  "seated-dollar": ["Seated dollars are 90% silver and scarce.", "$250–$600"],
  "trade-dollar": ["Trade dollars are silver and sell well above a common Morgan.", "$150–$400"],
  morgan: ["A common Morgan dollar is 90% silver. A rare date is more. The price follows the live silver quote.", null],
  peace: ["A common Peace dollar is 90% silver. The price follows the live silver quote.", null],
  "gold-dollar": ["A gold dollar's metal is far above one dollar. This does not say the coin is genuine.", null],
  "quarter-eagle": ["A quarter eagle is gold, worth far more than $2.50.", null],
  "three-dollar": ["A three-dollar gold piece is scarce. The metal is the floor, not the usual price.", "$900–$1,800"],
  "half-eagle": ["A half eagle is gold, worth far more than five dollars.", null],
  eagle: ["An eagle is gold, worth far more than ten dollars.", null],
  "double-eagle": ["A common double eagle is gold, worth far more than twenty dollars.", null],
};

function heldMint() {
  const live = (state.read && state.read.mint) || "";
  if (live) return live;
  const saved = [sides.second, sides.first].find((side) => side && side.mint);
  return (saved && saved.mint) || "";
}

function trackSides() {
  if (phase === "absent") {
    if (sides.first) sides.away = true;
    return;
  }
  if (phase !== "done") return;
  const snap = {
    year: (state.read && state.read.year) || coinYear(),
    mint: (state.read && state.read.mint) || "",
  };
  if (!sides.first) {
    sides.first = snap;
    return;
  }
  if (snap.year && sides.first.year && snap.year !== sides.first.year) {
    sides = { first: snap, second: null, away: false };
    return;
  }
  if (sides.away && !sides.second) {
    sides.second = snap;
    sides.away = false;
  } else if (snap.mint && sides.first && !sides.first.mint) {
    sides.first.mint = snap.mint;
  }
}

function fillSaved() {
  let vault = {};
  try {
    vault = JSON.parse(localStorage.getItem("coin-vault") || "{}");
  } catch (error) {
    vault = {};
  }
  const keys = Object.keys(vault);
  if (!keys.length) return;
  const label = document.createElement("div");
  label.className = "group";
  label.textContent = "Saved";
  list.appendChild(label);
  keys.slice(-8).reverse().forEach((key) => {
    const [id, year, mint] = key.split("|");
    const series = seriesById(id);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "series";
    button.textContent = `${year || ""}${mint ? `-${mint}` : ""} ${series ? series.name : "Coin"}`.trim();
    const price = document.createElement("small");
    price.textContent = vault[key].price || "";
    button.appendChild(price);
    list.appendChild(button);
  });
}

function faceOf(series) {
  const faces = {
    Cents: 0.01,
    Nickels: 0.05,
    Dimes: 0.1,
    Quarters: 0.25,
    "Half dollars": 0.5,
    Dollars: 1,
  };
  return faces[series && series.group] ?? 0;
}

function chartQuote(series, year, mint, sheldon) {
  const chart = series && (valueBook.charts || {})[series.id];
  const years = (chart && chart.years) || (series && series.id === "indian-head" ? indianBook.years : null);
  if (!years) return null;
  const marked = mint && years[`${year}-${mint}`] ? `${year}-${mint}` : String(year);
  const row = years[marked];
  if (!row || !row.good || !row.fine) return null;
  let low = row.good[0];
  let high = row.fine[1];
  if (String(sheldon).startsWith("XF") && row.au) {
    low = row.au[0];
    high = row.au[1];
  } else if (String(sheldon).startsWith("F-") && row.au) {
    low = row.fine[0];
    high = row.au[0];
  }
  low = Math.min(low, high);
  high = Math.max(low, high);
  return {
    price: moneyRange(low, high),
    above: high > faceOf(series) + 0.001 || series.group === "Gold",
    updated: (chart && chart.updated) || indianBook.updated || "",
  };
}

function coinYear() {
  const raw = (document.getElementById("year").value || "").trim();
  if (!/^\d{4}$/.test(raw)) return null;
  return Number(raw);
}

function green(detail, price, uses) {
  return { tone: "green", title: "Above face", detail, price, uses: uses || "" };
}

function red(detail, price) {
  return { tone: "red", title: "Face value", detail, price };
}

function wait(title, detail, price) {
  return { tone: "wait", title, detail, price: price || "" };
}

function shownSeries() {
  const suggested = state.read && state.read.series_id;
  if (suggested) {
    const match = seriesById(suggested);
    if (match) return match;
  }
  return seriesById(state.series_id);
}

function worth(series) {
  if (isSteelCent()) {
    const year = (state.read && state.read.year) || coinYear();
    if (year === 1944) {
      return green("A gray 1944 cent is the rare steel wrong-planchet. A magnet should grab it. This camera cannot authenticate it.", "Far above face");
    }
    return green("1943 steel cent. It should look gray and stick to a magnet. A copper-colored 1943 is the rare bronze cent.", "20¢–$1");
  }
  const light = state.light && state.light.verdict;
  if (light && light.verdict === "die") {
    return green("The light test kept a split. That can be worth more than face. The price stays unknown until the variety is confirmed.", "Unpriced");
  }
  if (state.read && state.read.year && state.read.year_fits === false) {
    const names = (state.read.choices || []).slice(0, 4);
    const list = names.length ? ` This year also fits ${names.join(", ")}.` : "";
    return wait("Several types", `The date is ${state.read.year}.${list}`);
  }
  if (!series) return wait("Pick a coin", "Choose the series. The color is the metal and the type, not a grade.");
  const year = (state.read && state.read.year) || coinYear();
  const mint = heldMint();
  const sheldon = (state.condition && state.condition.sheldon) || "";
  const quoted = year ? chartQuote(series, year, mint, sheldon) : null;
  if (quoted) {
    const updated = quoted.updated ? `, updated ${quoted.updated}` : "";
    const detail = `CoinValueChecker chart${updated}.`;
    return quoted.above ? green(detail, quoted.price) : red(detail, quoted.price);
  }
  if (PREMIUM[series.id]) {
    const row = PREMIUM[series.id];
    const uses = LIVE[series.id] ? LIVE[series.id][0] : "";
    return green(row[0], livePrice(series.id, row[1]), uses);
  }
  if (FACE[series.id]) return red(FACE[series.id][0], FACE[series.id][1]);

  if (series.id === "lincoln-memorial") {
    if (!year) return wait("Enter the year", "1959 through 1981 are copper and worth more than one cent. 1983 and later spend at one cent. 1982 can be either.");
    if (year >= 1959 && year <= 1981) return green("Copper cents are worth more than one cent in metal. Do not melt them. The figure follows the live copper quote.", copperCentBand(), "copper");
    if (year === 1982) return wait("Weigh the 1982", "Some 1982 cents are copper and some are zinc. Copper weighs about 3.11 grams and is about 4¢–8¢. Zinc weighs about 2.50 grams and spends at 1¢.", "4¢–8¢ or 1¢");
    if (year >= 1983) return red("Zinc cents from 1983 on spend at one cent.", "1¢");
  }
  if (series.id === "jefferson") {
    if (!year) return wait("Enter the year", "1943, 1944, and 1945 are 35% silver. Most other Jefferson nickels spend at five cents.");
    if (year >= 1943 && year <= 1945) return green("War nickels are 35% silver. The price follows the live silver quote.", silverBand(0.05626), "silver");
    if (year === 1942) return wait("Check the mint mark", "A large P, D, or S over the dome is 35% silver, about $3–$4. No mark over the dome is a normal nickel.", "5¢ or $3–$4");
    return red("This Jefferson nickel spends at five cents. A scarce mint mark can be more, and this camera does not read mint marks.", "5¢");
  }
  if (series.id === "roosevelt") {
    if (!year) return wait("Enter the year", "1964 and earlier are 90% silver. 1965 and later spend at ten cents.");
    if (year <= 1964) return green("A dime from 1964 or earlier is 90% silver. The price follows the live silver quote.", silverBand(0.07234), "silver");
    return red("A dime from 1965 on spends at ten cents.", "10¢");
  }
  if (series.id === "washington") {
    if (!year) return wait("Enter the year", "1964 and earlier are 90% silver. 1965 and later spend at 25 cents.");
    if (year <= 1964) return green("A quarter from 1964 or earlier is 90% silver. The price follows the live silver quote.", silverBand(0.18084), "silver");
    return red("A quarter from 1965 on spends at 25 cents. A pocket 1776–1976 quarter is clad.", "25¢");
  }
  if (series.id === "kennedy") {
    if (!year) return wait("Enter the year", "1964 is 90% silver. 1965 through 1970 are 40% silver. 1971 and later spend at 50 cents.");
    if (year === 1964) return green("A 1964 half dollar is 90% silver. The price follows the live silver quote.", silverBand(0.36169), "silver");
    if (year >= 1965 && year <= 1970) return green("A 1965–1970 half dollar is 40% silver. The price follows the live silver quote.", silverBand(0.1479), "silver");
    return red("A half dollar from 1971 on spends at 50 cents, unless it is a silver collector piece from a Mint pack.", "50¢");
  }
  return wait("Enter the year", "Type the date on the coin.");
}

function ringColor() {
  if (phase === "light") return "#f0c14a";
  if (phase !== "done") return "#e0c17a";
  const call = worth(shownSeries());
  if (call.tone === "green") return "#b6f27a";
  if (call.tone === "red") return "#ff3b30";
  return "#e0c17a";
}

const CENT_SERIES = new Set([
  "flying-eagle", "indian-head", "lincoln-wheat", "lincoln-memorial",
  "lincoln-2009", "lincoln-shield", "lincoln-2026",
]);

function isCent(series) {
  return Boolean(series && CENT_SERIES.has(series.id));
}

function isSteelCent() {
  if (state.surface !== "steel") return false;
  const year = (state.read && state.read.year) || coinYear();
  if (year && year !== 1943 && year !== 1944) return false;
  return isCent(shownSeries());
}

function lightProblem() {
  const findings = state.findings || [];
  if (isSteelCent()) return findings.some((item) => item.kind === "focus");
  return findings.some((item) => item.kind === "glare" || item.kind === "focus" || item.kind === "tilt");
}

function updatePhase() {
  if (state.camera_error || !state.locked) {
    phase = "absent";
    steady = 0;
    return;
  }
  if (lightProblem()) {
    phase = "light";
    steady = 0;
    return;
  }
  steady += 1;
  phase = steady < 4 ? "scan" : "done";
}

function statusText() {
  if (state.camera_error) return "Camera off";
  if (phase === "absent") return sides.first && !sides.second ? "Flip the coin" : "Align the coin in the ring";
  if (phase === "light") {
    const findings = state.findings || [];
    if (findings.some((item) => item.kind === "glare")) return "Too bright";
    if (findings.some((item) => item.kind === "focus")) return "Too soft";
    return "Straighten the camera";
  }
  return "Scanning";
}

function drawArc(cx, cy, radius, a0, a1, color) {
  const startX = cx + radius * Math.cos(a0);
  const startY = cy + radius * Math.sin(a0);
  const endX = cx + radius * Math.cos(a1);
  const endY = cy + radius * Math.sin(a1);
  const large = a1 - a0 > Math.PI ? 1 : 0;
  svg.appendChild(el("path", {
    d: `M ${startX} ${startY} A ${radius} ${radius} 0 ${large} 1 ${endX} ${endY}`,
    fill: "none",
    stroke: color,
    "stroke-width": Math.max(3, radius * 0.02),
    "stroke-linecap": "round",
  }));
}

function draw() {
  placeOverlay();
  svg.replaceChildren();
  const width = state.frame_w || 1280;
  const height = state.frame_h || 720;
  const color = ringColor();
  let cx = width / 2;
  let cy = height / 2;
  let radius = Math.min(width, height) * 0.34;
  if (state.locked && state.circle) {
    cx = state.circle.cx;
    cy = state.circle.cy;
    radius = state.circle.r;
  }
  svg.classList.toggle("scanning", phase === "scan");
  svg.appendChild(el("circle", {
    cx, cy, r: radius,
    fill: "none",
    stroke: color,
    "stroke-width": phase === "done" ? 8 : 3,
    "stroke-dasharray": phase === "done" ? "none" : "10 8",
  }));
}

function renderFindings() {
  const findings = state.findings || [];
  findingsEl.replaceChildren();
  if (!findings.length) {
    const note = document.createElement("p");
    note.className = "hint";
    note.textContent = state.hint || "Put a coin under the camera.";
    findingsEl.appendChild(note);
    return;
  }
  findings.forEach((item) => {
    const block = document.createElement("article");
    block.className = "finding";
    const title = document.createElement("h3");
    const tag = document.createElement("span");
    tag.className = `tag ${item.severity}`;
    tag.textContent = item.severity === "check" ? "Look" : item.severity === "watch" ? "Maybe" : "Note";
    title.appendChild(tag);
    title.appendChild(document.createTextNode(item.title));
    if (item.clock) {
      const clock = document.createElement("span");
      clock.textContent = item.clock;
      title.appendChild(clock);
    }
    const detail = document.createElement("p");
    detail.textContent = item.detail;
    block.append(title, detail);
    findingsEl.appendChild(block);
  });
}

function renderKnown() {
  const box = document.getElementById("known");
  if (!box) return;
  const series = seriesById(state.series_id);
  const year = coinYear();
  box.replaceChildren();
  const title = document.createElement("h2");
  title.textContent = year ? `Known defects, ${year}` : "Known defects";
  box.appendChild(title);
  const note = document.createElement("p");
  note.className = "hint";
  note.textContent = defectBook.note || "Type the year. The list is the published major defects for that date.";
  box.appendChild(note);
  if (!series) return;
  const byYear = (defectBook.series && defectBook.series[series.id]) || {};
  const lines = year ? (byYear[String(year)] || []) : [];
  if (year && !lines.length) {
    const empty = document.createElement("p");
    empty.textContent = `No major published defect is listed for ${series.name} in ${year}. Ordinary clips, off-center strikes, and die cracks can still show up. A webcam will not sort minor doubled dies.`;
    box.appendChild(empty);
    return;
  }
  if (!year) {
    const years = Object.keys(byYear).sort();
    if (!years.length) {
      const empty = document.createElement("p");
      empty.textContent = "No dated major defect is on file for this series. Check the year on the coin.";
      box.appendChild(empty);
      return;
    }
    const hint = document.createElement("p");
    hint.textContent = `Years with a listed defect: ${years.join(", ")}.`;
    box.appendChild(hint);
    return;
  }
  const list = document.createElement("ul");
  lines.forEach((line) => {
    const item = document.createElement("li");
    item.textContent = line;
    list.appendChild(item);
  });
  box.appendChild(list);
}

function renderGuide() {
  const series = seriesById(state.series_id);
  if (!series) {
    guideEl.textContent = "Pick the coin you are holding. Space freezes the picture.";
    coinButton.textContent = "Choose a coin";
    return;
  }
  coinButton.textContent = series.name;
  const call = worth(series);
  const lines = [call.detail, series.guide];
  (series.look || []).slice(0, 1).forEach((line) => lines.push(line));
  if (series.errors && series.errors.length) lines.push(series.errors[0]);
  guideEl.textContent = lines.join(" ");
}

function renderSize() {
  if (!state.locked) {
    sizeEl.textContent = "No coin locked";
    return;
  }
  if (state.diameter_mm) {
    const expected = state.expected_mm ? ` / ${Number(state.expected_mm).toFixed(2)} mm` : "";
    sizeEl.textContent = `${state.diameter_mm.toFixed(1)} mm${expected}`;
    return;
  }
  sizeEl.textContent = `${Math.round(state.diameter_px || 0)} px across`;
}

function renderFocus() {
  focusEl.replaceChildren();
  const ticks = 8;
  const filled = Math.round((state.focus || 0) * ticks);
  for (let i = 0; i < ticks; i += 1) {
    const tick = document.createElement("i");
    if (i < filled) {
      tick.className = filled < 3 ? "low" : filled < 5 ? "mid" : "on";
    }
    focusEl.appendChild(tick);
  }
}

function renderLight() {
  const light = state.light || {};
  const shotA = document.getElementById("shot-a");
  const shotB = document.getElementById("shot-b");
  shotA.textContent = light.a ? "Shot A kept" : "Shot A";
  shotB.textContent = light.b ? "Shot B kept" : "Shot B";
  if (light.verdict) {
    lightEl.textContent = `${light.verdict.title}. ${light.verdict.detail}`;
  } else if (light.a && !light.b) {
    lightEl.textContent = "Shot A is in. Move the lamp, leave the coin, then take shot B.";
  } else {
    lightEl.textContent = "No light test yet.";
  }
}

function renderCameras() {
  const cameras = state.cameras || [];
  const key = cameras.map((camera) => `${camera.index}:${camera.name}`).join("|");
  if (key === cameraKey) {
    if (state.camera_index !== null && cameraEl.value !== String(state.camera_index)) {
      cameraEl.value = String(state.camera_index);
    }
    return;
  }
  cameraKey = key;
  cameraEl.replaceChildren();
  cameras.forEach((camera) => {
    const option = document.createElement("option");
    option.value = String(camera.index);
    option.textContent = camera.name || `Camera ${camera.index}`;
    cameraEl.appendChild(option);
  });
  if (state.camera_index !== null && state.camera_index !== undefined) {
    cameraEl.value = String(state.camera_index);
  } else {
    const usb = [...cameraEl.options].find((option) => option.textContent.includes("USB2.0 UVC PC Camera"));
    if (usb) cameraEl.value = usb.value;
  }
}

function gradeLine() {
  const cond = state.condition || {};
  const color = { RD: "Red", RB: "Red-brown", BN: "Brown" }[cond.color] || "";
  if (!cond.sheldon) return "Too soft or too bright to grade.";
  return `${cond.sheldon}${color ? `, ${color} copper` : ""}. Wide band, not a certified grade.`;
}

function errorLine() {
  const findings = (state.findings || []).filter((item) => item.severity === "check" || item.severity === "watch");
  const seen = findings.slice(0, 3).map((item) => (item.clock ? `${item.title}, ${item.clock}` : item.title));
  const series = shownSeries();
  const year = (state.read && state.read.year) || coinYear();
  const lines = series && year && state.read && state.read.year_fits !== false && defectBook.series && defectBook.series[series.id]
    ? defectBook.series[series.id][String(year)]
    : null;
  const parts = [];
  if (seen.length) parts.push(seen.join(". "));
  if (lines && lines.length) parts.push(lines[0]);
  if (!parts.length) return "No chip, off-center strike, or green in this view.";
  return parts.join(". ");
}

function marketLine(series, price) {
  const year = (state.read && state.read.year) || coinYear();
  if (!series || !year || !price) return "Waiting for a date and a chart price.";
  const key = `${series.id}|${year}|${(state.read && state.read.mint) || ""}`;
  let vault = {};
  try {
    vault = JSON.parse(localStorage.getItem("coin-vault") || "{}");
  } catch (error) {
    vault = {};
  }
  const saved = vault[key];
  if (!saved) {
    vault[key] = { price, at: Date.now() };
    localStorage.setItem("coin-vault", JSON.stringify(vault));
    return "Saved. First check for this coin.";
  }
  if (saved.price === price) {
    return sides.second ? "Both sides saved. Price matches the last check." : "One side saved. Flip the coin for the other side.";
  }
  return `Saved earlier at ${saved.price}. Now ${price}.`;
}

function renderValue() {
  const badge = document.getElementById("value-badge");
  const price = document.getElementById("value-price");
  const series = shownSeries();
  const call = worth(series);
  badge.className = call.tone;
  badge.textContent = call.title;
  price.textContent = call.price ? `Possible price: ${call.price}${quoteSuffix(call.uses)}` : "";
  price.hidden = !call.price;
  const coin = document.getElementById("report-coin");
  const grade = document.getElementById("report-grade");
  const value = document.getElementById("report-value");
  const errors = document.getElementById("report-errors");
  const market = document.getElementById("report-market");
  if (coin) coin.textContent = identity();
  if (grade) grade.textContent = gradeLine();
  if (value) value.textContent = call.price ? `${call.price}. ${call.detail || ""}`.trim() : (call.detail || "No chart price for this coin.");
  if (errors) errors.textContent = errorLine();
  if (market) market.textContent = marketLine(series, call.price || "");
  const psa = document.getElementById("psa-line");
  if (psa) psa.textContent = psaLine();
}

function psaLine() {
  const base = "PSA coins are graded 1–10, with no half points.";
  if (state.camera_error || !state.locked) return `${base} They look at scratches, dents, rust, and centering.`;
  const findings = state.findings || [];
  if (findings.some((item) => item.kind === "glare" || item.kind === "focus")) {
    return `${base} Eye appeal decides the grade, and this picture is too bright or soft.`;
  }
  const kinds = new Set(findings.map((item) => item.kind));
  if (kinds.has("bite") || kinds.has("bump") || kinds.has("line") || kinds.has("pit")) {
    return `${base} A scratch or dent keeps it off a 10.`;
  }
  if (kinds.has("color")) return `${base} Rust or green on the surface keeps it off a 10.`;
  if (kinds.has("off_center")) return `${base} Centering is off, and PSA counts that.`;
  return `${base} Nothing in this view counts as a scratch, dent, or rust.`;
}

function applyRead() {
  const box = document.getElementById("year");
  const read = state.read || {};
  const steelYear = isSteelCent() && !(read.year) ? 1943 : null;
  const year = read.year || steelYear;
  if (!box || !year || document.activeElement === box) return;
  const next = String(year);
  if (!box.value || box.dataset.auto === "1") {
    box.value = next;
    box.dataset.auto = "1";
    sessionStorage.setItem("coin-year", next);
  }
}

function identity() {
  const read = state.read || {};
  const series = shownSeries();
  if (isSteelCent()) {
    const year = read.year || 1943;
    if (read.mint) return `${year} ${read.mint} · ${read.mint_name} steel cent.`;
    return `${year} steel cent.`;
  }
  if (!read.year) return "Flip the coin. The date is on the other side.";
  if (read.year_fits === false) return `${read.year}. Several coins use this year.`;
  const mintLetter = heldMint();
  const mint = mintLetter ? ` ${mintLetter}` : "";
  if (series) return `${read.year}${mint}. ${series.name}.`;
  return `${read.year}${mint}.`;
}

function shortNote() {
  if (state.camera_error) return "Camera is off. Press Reconnect.";
  const who = identity();
  const findings = (state.findings || []).filter((item) => item.severity === "check" || item.severity === "watch");
  const seen = findings.slice(0, 4).map((item) => (item.clock ? `${item.title}, ${item.clock}` : item.title));
  if (findings.length > 4) seen.push(`${findings.length - 4} more`);
  const series = shownSeries();
  const year = (state.read && state.read.year) || coinYear();
  const lines = series && year && state.read && state.read.year_fits !== false && defectBook.series && defectBook.series[series.id]
    ? defectBook.series[series.id][String(year)]
    : null;
  const parts = [];
  const cond = state.condition || {};
  const colorName = { RD: "Red", RB: "Red-brown", BN: "Brown" }[cond.color] || "";
  if (colorName || cond.wear) {
    const colorBit = colorName ? `${colorName} copper. ` : "";
    const wearBit = cond.wear ? `Wear looks like ${cond.wear}, about ${cond.sheldon}. Wide band, not a certified grade.` : "";
    parts.push(`${colorBit}${wearBit}`.trim());
  }
  if (seen.length) parts.push(`${seen.join(". ")}.`);
  if (lines && lines.length) parts.push(lines[0]);
  if (!parts.length) {
    parts.push("No chip, scratch, pit, split, or green shows in this view. A clip, cud, or off-center strike can happen in any year. Fine doubled dies are beyond this camera.");
  }
  return `${who} ${parts.join(" ")}`;
}

function takeMarket() {
  const incoming = state.market;
  if (!incoming || !incoming.ok) return;
  market.silver = incoming.silver;
  market.gold = incoming.gold;
  market.copper = incoming.copper;
  market.updated = incoming.updated;
}

function render() {
  takeMarket();
  updatePhase();
  trackSides();
  document.body.className = `phase-${phase}`;
  const status = document.getElementById("status");
  const wrap = document.getElementById("value-wrap");
  if (status) {
    status.hidden = phase === "done";
    status.textContent = statusText();
  }
  if (wrap) wrap.hidden = phase !== "done";
  draw();
  applyRead();
  if (phase === "done") renderValue();
  renderCameras();
  const series = shownSeries();
  if (series) coinButton.textContent = series.name;
  if (!drawer.hidden) fillSeries();
}

async function poll() {
  try {
    state = await fetch("/api/state").then((response) => response.json());
    render();
  } catch (error) {
    const note = document.getElementById("value-note");
    if (note) note.textContent = "Scanner stopped. Open Coin Scanner again.";
  }
  setTimeout(poll, 350);
}

coinButton.addEventListener("click", () => {
  drawer.hidden = !drawer.hidden;
  if (!drawer.hidden) {
    search.focus();
    fillSeries();
  }
});
search.addEventListener("input", fillSeries);
cameraEl.addEventListener("change", () => {
  post("/api/open", { index: Number(cameraEl.value) }).then(() => startFeed());
});
document.getElementById("reconnect").addEventListener("click", () => {
  const index = cameraEl.value === "" ? 2 : Number(cameraEl.value);
  post("/api/open", { index }).then(() => startFeed());
});
document.getElementById("quit").addEventListener("click", async () => {
  await post("/api/shutdown");
  document.body.innerHTML = "<p style='padding:24px'>Coin Scanner is closed. You can shut this tab.</p>";
});
window.addEventListener("resize", () => draw());
const yearEl = document.getElementById("year");
// A saved date belongs to the previous coin. Do not price a new coin from it
// while OCR is still looking for the current date.
sessionStorage.removeItem("coin-year");
yearEl.value = "";
yearEl.dataset.auto = "1";
yearEl.addEventListener("input", () => {
  yearEl.value = yearEl.value.replace(/\D/g, "").slice(0, 4);
  yearEl.dataset.auto = "0";
  sessionStorage.setItem("coin-year", yearEl.value);
  render();
});

window.addEventListener("keydown", (event) => {
  if (event.target === search || event.target === yearEl) {
    if (event.key === "Escape") drawer.hidden = true;
    return;
  }
  if (event.key === "Escape") drawer.hidden = true;
});

Promise.all([
  fetch("/api/catalog").then((response) => response.json()),
  fetch("/defects.json").then((response) => response.json()),
  fetch("/api/values").then((response) => response.json()).catch(() => ({ charts: {} })),
])
  .then(([rows, book, values]) => {
    catalog = rows;
    defectBook = book;
    valueBook = values || { charts: {} };
    indianBook = (valueBook.charts && valueBook.charts["indian-head"]) || { years: {} };
  })
  .then(() => poll());

