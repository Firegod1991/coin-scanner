"""Regular-issue U.S. coins the scanner can be aimed at.

Diameters are the U.S. Mint specifications where the size stayed fixed.
Series whose diameter changed across the years are marked size_check false
so a modern calibration is not used to scold an early coin.
"""

from __future__ import annotations

import re

_RANGE = re.compile(r"(\d{4})\s*[-–—]\s*(\d{4}|date)")
_ONE_YEAR = re.compile(r"\d{4}")


def _coin(**fields):
    fields.setdefault("size_check", True)
    fields.setdefault("edge", "Reeded")
    fields.setdefault("errors", [])
    return fields


SERIES = [
    _coin(
        id="half-cent", group="Cents", name="Half cent", years="1793–1857",
        diameter_mm=23.5, size_check=False, edge="Plain", metal="copper",
        composition="Copper",
        guide="Early half cents vary in diameter. Use the millimeter readout, and do not expect an exact match.",
        look=[
            "Rim bites and bent edges are the marks a camera can see.",
            "The date and LIBERTY are the places a wide doubled die would show.",
        ],
    ),
    _coin(
        id="large-cent", group="Cents", name="Large cent", years="1793–1857",
        diameter_mm=28.5, size_check=False, edge="Plain", metal="copper",
        composition="Copper",
        guide="Large cents shrank over the series. A size warning is turned off for this entry.",
        look=[
            "Look for rim bites, corrosion, and green spots.",
            "Porous surfaces and dark pits are common and usually environmental.",
        ],
    ),
    _coin(
        id="flying-eagle", group="Cents", name="Flying Eagle cent", years="1856–1858",
        diameter_mm=19.05, edge="Plain", metal="copper", composition="Copper-nickel",
        guide="Same diameter as a modern cent. The eagle and the legend are the doubling check.",
        look=["A wide split on the legend or the eagle is the kind of doubling this camera might show."],
    ),
    _coin(
        id="indian-head", group="Cents", name="Indian Head cent", years="1859–1909",
        diameter_mm=19.05, edge="Plain", metal="copper", composition="Copper-nickel, then bronze",
        guide="Check the headdress tips, the date, and the wreath or shield.",
        look=["Rim bites and green corrosion show up here. Fine die cracks usually do not."],
    ),
    _coin(
        id="lincoln-wheat", group="Cents", name="Lincoln cent, Wheat reverse", years="1909–1958",
        diameter_mm=19.05, edge="Plain", metal="copper", composition="Bronze",
        guide="The teaching doubled die of the series is the 1955 Philadelphia obverse.",
        look=[
            "On a doubled die, LIBERTY, IN GOD WE TRUST, and the date carry a second outline.",
            "Wheat cents are bronze. Green spots are corrosion, not zinc rot.",
        ],
        errors=["1955 doubled die obverse, Philadelphia. The spread on LIBERTY and the motto is wide enough to see."],
    ),
    _coin(
        id="lincoln-memorial", group="Cents", name="Lincoln cent, Memorial reverse", years="1959–2008",
        diameter_mm=19.05, edge="Plain", metal="copper",
        composition="Bronze through mid-1982, then copper-plated zinc",
        guide="Cents dated 1982 and later are copper-plated zinc. Gray blisters are zinc rot.",
        look=[
            "Check the date, LIBERTY, the motto, and Lincoln's ear for a second outline.",
            "A gray bubble under the copper skin is plating failure, common on zinc cents.",
            "The memorial columns are a hard place for a webcam. Use the light test on the date first.",
        ],
        errors=[
            "1969-S doubled die obverse.",
            "1972 doubled die obverse. Several spreads exist. The strong one is obvious on the motto.",
            "1983 doubled die reverse.",
            "1984 doubled ear.",
            "1995 doubled die obverse.",
        ],
    ),
    _coin(
        id="lincoln-2009", group="Cents", name="Lincoln cent, Bicentennial reverses", years="2009",
        diameter_mm=19.05, edge="Plain", metal="copper", composition="Copper-plated zinc",
        guide="Four reverse designs in 2009. The obverse is the doubling check.",
        look=["Birth, formative years, professional life, and presidency reverses. Rim bites read the same on all four."],
    ),
    _coin(
        id="lincoln-shield", group="Cents", name="Lincoln cent, Shield reverse", years="2010–2025",
        diameter_mm=19.05, edge="Plain", metal="copper", composition="Copper-plated zinc",
        guide="Circulation cents stopped in November 2025. This is the cent you still find in change.",
        look=[
            "Shield union and the rim are where bites and plating blisters show.",
            "A doubled die would split LIBERTY, the motto, or the date.",
        ],
    ),
    _coin(
        id="lincoln-2026", group="Cents", name="Lincoln cent, 1776~2026", years="2026",
        diameter_mm=19.05, edge="Plain", metal="copper", composition="Copper-plated zinc",
        guide="Sold in Mint products, not rolled out for commerce. Shield design with the dual date.",
        look=["Read the dual date 1776~2026. A split there is the first place to look."],
    ),
    _coin(
        id="two-cent", group="Cents", name="Two-cent piece", years="1864–1873",
        diameter_mm=23.0, edge="Plain", metal="copper", composition="Bronze",
        guide="IN GOD WE TRUST started here. Check that motto and the date.",
        look=["Rim bites and corrosion are the camera-visible problems."],
    ),
    _coin(
        id="three-silver", group="Cents", name="Three-cent silver", years="1851–1873",
        diameter_mm=14.0, edge="Plain", metal="silver", composition="Silver",
        guide="A small coin. Move the camera in until the disc fills the ring.",
        look=["Any doubling or bite has to be large relative to the coin before this camera can see it."],
    ),
    _coin(
        id="three-nickel", group="Nickels", name="Three-cent nickel", years="1865–1889",
        diameter_mm=17.9, edge="Plain", metal="nickel", composition="Copper-nickel",
        guide="About dime-sized, plain edge, nickel color.",
        look=["Check the rim and the Roman numeral III."],
    ),
    _coin(
        id="shield-nickel", group="Nickels", name="Shield nickel", years="1866–1883",
        diameter_mm=20.5, edge="Plain", metal="nickel", composition="Copper-nickel",
        guide="Rays on the reverse in 1866–1867, then no rays.",
        look=["The shield lines create shadows. Run the light test before calling a split a doubled die."],
    ),
    _coin(
        id="liberty-nickel", group="Nickels", name="Liberty Head nickel", years="1883–1913",
        diameter_mm=21.21, edge="Plain", metal="nickel", composition="Copper-nickel",
        guide="Same size as a modern nickel. The 1913 is a famous rarity. This tool cannot authenticate it.",
        look=["Check the date and LIBERTY. A missing CENT on the 1883 reverse is a type difference, not damage."],
    ),
    _coin(
        id="buffalo", group="Nickels", name="Buffalo nickel", years="1913–1938",
        diameter_mm=21.21, edge="Plain", metal="nickel", composition="Copper-nickel",
        guide="Dates wear off first. A weak date is wear, not a weak camera, when the rest of the coin is also smooth.",
        look=[
            "The 1937-D three-legged buffalo is a missing front leg on the reverse, not a doubled die.",
            "Rim bites are common because the rim is low.",
        ],
        errors=["1937-D three-legged buffalo. Look at the front leg on the reverse."],
    ),
    _coin(
        id="jefferson", group="Nickels", name="Jefferson nickel", years="1938–2003",
        diameter_mm=21.21, edge="Plain", metal="nickel", composition="Copper-nickel. 35% silver in 1942–1945.",
        guide="War nickels, 1942–1945, have a large mint mark over the dome and a silver alloy. They are the same size.",
        look=[
            "Monticello's steps and columns need a loupe. The camera can still catch rim bites and a wide split on LIBERTY or the date.",
            "A large mint mark above Monticello means a silver war nickel.",
        ],
    ),
    _coin(
        id="westward", group="Nickels", name="Westward Journey nickel", years="2004–2005",
        diameter_mm=21.21, edge="Plain", metal="nickel", composition="Copper-nickel",
        guide="Two reverses each year. Peace Medal, Keelboat, Bison, Ocean in View.",
        look=["The bison reverse invites a comparison with the 1937-D leg. That variety is on the Buffalo nickel, not this coin."],
    ),
    _coin(
        id="jefferson-return", group="Nickels", name="Jefferson nickel, modern portrait", years="2006–date",
        diameter_mm=21.21, edge="Plain", metal="nickel", composition="Copper-nickel",
        guide="Includes the 2026 nickel with the dual date 1776~2026 and Schlag's Monticello.",
        look=["The 2026 coin keeps the Jefferson portrait and Monticello. The new detail is the dual date."],
    ),
    _coin(
        id="half-dime", group="Dimes", name="Half dime", years="1794–1873",
        diameter_mm=15.5, size_check=False, metal="silver", composition="Silver",
        guide="Smaller than a dime. Early dates vary in diameter.",
        look=["Fill the ring or the camera will miss everything but a gross bite."],
    ),
    _coin(
        id="early-dime", group="Dimes", name="Early dime", years="1796–1837",
        diameter_mm=18.8, size_check=False, metal="silver", composition="Silver",
        guide="Draped Bust and Capped Bust. Diameter changed. Size check is off.",
        look=["Rim damage and bent coins are the realistic finds."],
    ),
    _coin(
        id="seated-dime", group="Dimes", name="Seated Liberty dime", years="1837–1891",
        diameter_mm=17.9, metal="silver", composition="Silver",
        guide="Modern dime diameter. Stars, legend, or arrows at the date depending on the year.",
        look=["Arrows at the date in 1853–1855 and 1873 are part of the design."],
    ),
    _coin(
        id="barber-dime", group="Dimes", name="Barber dime", years="1892–1916",
        diameter_mm=17.91, metal="silver", composition="Silver",
        guide="Check the date and the wreath. Wear hits the headband first.",
        look=["A smooth headband with a readable rim is wear. A bite is a missing piece of rim."],
    ),
    _coin(
        id="mercury", group="Dimes", name="Mercury dime", years="1916–1945",
        diameter_mm=17.91, metal="silver", composition="Silver",
        guide="The 1942/1 overdate is in the date. It needs a loupe. Bands on the fasces are a strike question, not a defect scan.",
        look=["Full bands are strike quality. This camera will not grade bands.", "Rim bites and bent coins still show."],
        errors=["1942/1 and 1942/1-D overdates. Look at the date with a loupe."],
    ),
    _coin(
        id="roosevelt", group="Dimes", name="Roosevelt dime", years="1946–2025",
        diameter_mm=17.91, metal="clad", composition="Silver through 1964, then copper-nickel clad",
        guide="1964 and earlier are silver. Later dimes show a copper streak on the edge. That streak is the clad sandwich, and it is normal on the edge.",
        look=[
            "A copper streak on the face, not the edge, is worth a look. It can be a lamination.",
            "The torch and the date are the doubling check.",
        ],
    ),
    _coin(
        id="liberty-dime-2026", group="Dimes", name="Emerging Liberty dime", years="2026",
        diameter_mm=17.91, metal="clad", composition="Copper-nickel clad",
        guide="One-year design. Liberty in a cap on the obverse, an eagle on the reverse, dual date 1776~2026.",
        look=["New devices and a new date. Check both for a second outline, then run the light test."],
    ),
    _coin(
        id="twenty-cent", group="Dimes", name="Twenty-cent piece", years="1875–1878",
        diameter_mm=22.0, edge="Plain", metal="silver", composition="Silver",
        guide="Plain edge, between a nickel and a quarter in size. Easy to confuse with a quarter until you see the edge.",
        look=["The plain edge is the identifier. This face-on view cannot see it. Tip the coin if you are unsure."],
    ),
    _coin(
        id="early-quarter", group="Quarters", name="Early quarter", years="1796–1838",
        diameter_mm=24.3, size_check=False, metal="silver", composition="Silver",
        guide="Bust quarters changed diameter. Size check is off.",
        look=["Rim bites, bends, and graffiti-sized scratches are in range. Variety attribution is not."],
    ),
    _coin(
        id="seated-quarter", group="Quarters", name="Seated Liberty quarter", years="1838–1891",
        diameter_mm=24.3, metal="silver", composition="Silver",
        guide="Arrows and rays are design changes for weight, not damage.",
        look=["Arrows at the date in 1853 and 1873, and rays in 1853, belong to the coin."],
    ),
    _coin(
        id="barber-quarter", group="Quarters", name="Barber quarter", years="1892–1916",
        diameter_mm=24.26, metal="silver", composition="Silver",
        guide="Same size as a modern quarter.",
        look=["Check the date, LIBERTY on the headband, and the rim."],
    ),
    _coin(
        id="standing-liberty", group="Quarters", name="Standing Liberty quarter", years="1916–1930",
        diameter_mm=24.26, metal="silver", composition="Silver",
        guide="The 1916 is a rare date. The 1918/7-S overdate is a loupe item.",
        look=["Bare breast in 1916–1917, then chain mail. That is a type change.", "The date wears off. A blank date with a full rim is wear."],
        errors=["1918/7-S overdate in the date."],
    ),
    _coin(
        id="washington", group="Quarters", name="Washington quarter", years="1932–1998",
        diameter_mm=24.26, metal="clad", composition="Silver through 1964, then copper-nickel clad",
        guide="The 1776–1976 bicentennial reverse is the drummer. Silver in 1964 and earlier.",
        look=["Check LIBERTY, the date, and IN GOD WE TRUST.", "A copper line on the face of a clad quarter can be a lamination."],
    ),
    _coin(
        id="state-quarter", group="Quarters", name="State quarter", years="1999–2008",
        diameter_mm=24.26, metal="clad", composition="Copper-nickel clad",
        guide="Fifty reverses, one Washington obverse. Pick this entry for any of them.",
        look=["The obverse is shared. A doubled die hunt starts at LIBERTY, the date, and the motto.", "Extra metal at the rim can be a cud. Missing metal is a bite."],
    ),
    _coin(
        id="territories-quarter", group="Quarters", name="D.C. and U.S. Territories quarter", years="2009",
        diameter_mm=24.26, metal="clad", composition="Copper-nickel clad",
        guide="Six reverses in 2009.",
        look=["Same obverse checks as the state quarters."],
    ),
    _coin(
        id="atb-quarter", group="Quarters", name="America the Beautiful quarter", years="2010–2021",
        diameter_mm=24.26, metal="clad", composition="Copper-nickel clad",
        guide="National park reverses. The obverse is Washington.",
        look=["Fine landscape lines will look soft on a USB 2.0 camera. Judge bites, bends, and wide splits, not the trees."],
    ),
    _coin(
        id="delaware-crossing", group="Quarters", name="Crossing the Delaware quarter", years="2021",
        diameter_mm=24.26, metal="clad", composition="Copper-nickel clad",
        guide="One-year reverse between the park series and the American Women series.",
        look=["Check the dual-side lettering and the rim."],
    ),
    _coin(
        id="women-quarter", group="Quarters", name="American Women quarter", years="2022–2025",
        diameter_mm=24.26, metal="clad", composition="Copper-nickel clad",
        guide="Washington obverse with a new portrait, five reverses a year through 2025.",
        look=["The portrait changed. Compare a split on the new portrait with the light test before you call it a doubled die."],
    ),
    _coin(
        id="semi-quarter", group="Quarters", name="Semiquincentennial quarter", years="2026",
        diameter_mm=24.26, metal="clad", composition="Copper-nickel clad",
        guide="Five reverses: Mayflower Compact, Revolutionary War, Declaration of Independence, U.S. Constitution, Gettysburg Address. Dual date 1776~2026.",
        look=["Any of the five uses this entry. The size and the metal match a modern quarter.", "Check the new devices and the dual date."],
    ),
    _coin(
        id="early-half", group="Half dollars", name="Early half dollar", years="1794–1839",
        diameter_mm=32.5, size_check=False, metal="silver", composition="Silver",
        guide="Flowing Hair, Draped Bust, and Capped Bust. Diameter varied.",
        look=["Lettering on the edge exists on some of these. Tip the coin. This view reads the face."],
    ),
    _coin(
        id="seated-half", group="Half dollars", name="Seated Liberty half dollar", years="1839–1891",
        diameter_mm=30.61, metal="silver", composition="Silver",
        guide="Arrows and rays are design changes.",
        look=["With a coin this large, rim bites and long lines are easy. Doubling still needs the light test."],
    ),
    _coin(
        id="barber-half", group="Half dollars", name="Barber half dollar", years="1892–1915",
        diameter_mm=30.61, metal="silver", composition="Silver",
        guide="Same diameter as a Kennedy half.",
        look=["Check the date, the cap, and the rim."],
    ),
    _coin(
        id="walking-liberty", group="Half dollars", name="Walking Liberty half dollar", years="1916–1947",
        diameter_mm=30.61, metal="silver", composition="Silver",
        guide="The date is on the obverse in the field, and it wears away.",
        look=["A weak date with a weak hand and head is wear.", "The 1946 doubled die reverse is a loupe coin unless the spread is wide."],
    ),
    _coin(
        id="franklin", group="Half dollars", name="Franklin half dollar", years="1948–1963",
        diameter_mm=30.61, metal="silver", composition="Silver",
        guide="Full bell lines are strike quality. This scan does not grade them.",
        look=["Check Franklin's head, the date, and the bell for a wide split.", "Rim bites show clearly at this size."],
    ),
    _coin(
        id="kennedy", group="Half dollars", name="Kennedy half dollar", years="1964–2025",
        diameter_mm=30.61, metal="clad",
        composition="90% silver in 1964, 40% silver in 1965–1970, clad afterward",
        guide="The 1776–1976 reverse is Independence Hall. Later dates were struck mainly for collectors and still match this size.",
        look=[
            "Silver coins tone brown, gold, and blue. That is not damage by itself.",
            "Green is the color to stop on.",
            "A copper line on the face of a clad half can be a lamination.",
        ],
    ),
    _coin(
        id="enduring-liberty", group="Half dollars", name="Enduring Liberty half dollar", years="2026",
        diameter_mm=30.61, metal="clad", composition="Copper-nickel clad",
        guide="One-year coin. Statue of Liberty on the obverse, Liberty passing the torch on the reverse. Sold by the Mint, not general circulation.",
        look=["New high-relief-looking devices throw hard shadows. Move the lamp before you trust a split."],
    ),
    _coin(
        id="early-dollar", group="Dollars", name="Early dollar", years="1794–1804",
        diameter_mm=40.0, size_check=False, metal="silver", composition="Silver",
        guide="Flowing Hair and Draped Bust. These are scarce. The scan only looks for damage you can see.",
        look=["Do not clean it. A camera cannot authenticate an early dollar."],
    ),
    _coin(
        id="seated-dollar", group="Dollars", name="Seated Liberty dollar", years="1840–1873",
        diameter_mm=38.1, metal="silver", composition="Silver",
        guide="Same diameter as a Morgan dollar.",
        look=["Check the rim, the date, and any long scratch across Liberty."],
    ),
    _coin(
        id="trade-dollar", group="Dollars", name="Trade dollar", years="1873–1885",
        diameter_mm=38.1, metal="silver", composition="Silver",
        guide="TRADE DOLLAR on the reverse. Chop marks from commerce in Asia are stamps, not mint errors.",
        look=["A chop is a punch from later commerce. Note it, and do not call it a cud."],
    ),
    _coin(
        id="morgan", group="Dollars", name="Morgan dollar", years="1878–1921",
        diameter_mm=38.1, metal="silver", composition="Silver",
        guide="Large and detailed. Fill the frame. CC mint marks and the 1893-S are attribution, which this camera will not settle.",
        look=[
            "Check the date, LIBERTY on the headband, and the eagle's feathers for a wide split.",
            "Bag marks are small nicks from other coins. A few are normal.",
            "Green spots are the ones to separate from ordinary toning.",
        ],
    ),
    _coin(
        id="peace", group="Dollars", name="Peace dollar", years="1921–1935",
        diameter_mm=38.1, metal="silver", composition="Silver",
        guide="High relief in 1921, then a lower relief. The relief change is the design.",
        look=["The 1921 often shows a soft strike in the center. Soft centers with sharp rims are strike, not blur, when the rim lettering is sharp."],
    ),
    _coin(
        id="ike", group="Dollars", name="Eisenhower dollar", years="1971–1978",
        diameter_mm=38.1, metal="clad", composition="Copper-nickel clad, plus some 40% silver collector strikes",
        guide="The 1776–1976 reverse is the Moon and the Liberty Bell.",
        look=["Clad coins can show a copper line on the face from a lamination.", "Silver collector strikes tone. Green is the warning color."],
    ),
    _coin(
        id="sba", group="Dollars", name="Susan B. Anthony dollar", years="1979–1981 and 1999",
        diameter_mm=26.5, metal="clad", composition="Copper-nickel clad",
        guide="Small dollar with a reeded edge. The 1979 wide rim is a variety people hunt with a loupe.",
        look=["A reeded edge and a copper-nickel color separate it from the later golden dollars."],
    ),
    _coin(
        id="sacagawea", group="Dollars", name="Sacagawea dollar", years="2000–2008",
        diameter_mm=26.49, edge="Plain", metal="brass",
        composition="Manganese brass over copper",
        guide="Golden color, plain edge. The core is copper, so a bright copper spot can be a missing layer.",
        look=["A patch of red copper on the gold surface is a plating or planchet question.", "The edge is plain. Later Native American dollars have lettered edges."],
    ),
    _coin(
        id="native-american", group="Dollars", name="Native American dollar", years="2009–date",
        diameter_mm=26.49, edge="Lettered", metal="brass",
        composition="Manganese brass over copper",
        guide="Sacagawea obverse, a new reverse each year. The edge is lettered.",
        look=["Tip the coin to read the edge. This overlay reads the face.", "Copper showing through the gold is the color check."],
    ),
    _coin(
        id="presidential", group="Dollars", name="Presidential dollar", years="2007–2016",
        diameter_mm=26.49, edge="Lettered", metal="brass",
        composition="Manganese brass over copper",
        guide="Deceased presidents only. The date, mint mark, and motto sit on the edge.",
        look=["A missing edge inscription is a known error class. Tip the coin. The camera does not see the edge in this view.", "Face checks are rim bites and copper showing through."],
        errors=["Missing edge lettering. Roll the coin. Do not judge it from the face."],
    ),
    _coin(
        id="innovation", group="Dollars", name="American Innovation dollar", years="2018–2032",
        diameter_mm=26.49, edge="Lettered", metal="brass",
        composition="Manganese brass over copper",
        guide="Statue of Liberty obverse and a state or territory reverse. Lettered edge.",
        look=["Same body as the other golden dollars. 2026 pieces also carry semiquincentennial marks."],
    ),
    _coin(
        id="semi-dollar-2026", group="Dollars", name="Semiquincentennial dollar", years="2026",
        diameter_mm=26.49, edge="Plain", metal="brass",
        composition="Manganese brass. 8.1 grams. Plain edge. No mint mark.",
        guide="One-year legal-tender dollar. Obverse portrait of President Donald J. Trump. Reverse is the Presidential Seal with 250 on the shield. Dual date 1776~2026.",
        look=[
            "Plain edge, unlike the Native American and Innovation dollars.",
            "A July 4th privy mark was mixed into some rolls and bags. That mark is small. Use a loupe.",
            "Copper showing through the golden color is the planchet check.",
        ],
    ),
    _coin(
        id="gold-dollar", group="Gold", name="Gold dollar", years="1849–1889",
        diameter_mm=14.5, size_check=False, edge="Reeded", metal="gold", composition="Gold",
        guide="Type 1 is about 13 mm. Types 2 and 3 are about 15 mm. Size check is off.",
        look=["Too small for doubling. Look for bends, bites, and holes. A holed coin is damaged."],
    ),
    _coin(
        id="quarter-eagle", group="Gold", name="Quarter eagle", years="1796–1929",
        diameter_mm=18.0, size_check=False, edge="Reeded", metal="gold", composition="Gold. $2.50.",
        guide="Liberty Head and Indian Head are about 18 mm. Earlier coins vary.",
        look=["Incuse devices on the Indian Head quarter eagle look different from raised relief. Shadows inside the incuse lines are normal."],
    ),
    _coin(
        id="three-dollar", group="Gold", name="Three-dollar gold", years="1854–1889",
        diameter_mm=20.5, edge="Reeded", metal="gold", composition="Gold",
        guide="A scarce denomination. The scan looks for damage, not authenticity.",
        look=["Check the rim and look for mounts or solder from jewelry use."],
    ),
    _coin(
        id="half-eagle", group="Gold", name="Half eagle", years="1795–1929",
        diameter_mm=21.6, size_check=False, edge="Reeded", metal="gold", composition="Gold. $5.",
        guide="Early half eagles are larger. Liberty and Indian Head coins are about 21.6 mm.",
        look=["Indian Head half eagles are incuse. Dark lines in the devices are the design."],
    ),
    _coin(
        id="eagle", group="Gold", name="Eagle", years="1795–1933",
        diameter_mm=27.0, size_check=False, edge="Reeded", metal="gold", composition="Gold. $10.",
        guide="Liberty and Indian Head eagles are about 27 mm. Earlier coins vary.",
        look=["Look for rim bites, mounts, and scratches. Variety work needs a loupe and a reference."],
    ),
    _coin(
        id="double-eagle", group="Gold", name="Double eagle", years="1850–1933",
        diameter_mm=34.1, edge="Reeded", metal="gold", composition="Gold. $20.",
        guide="Liberty Head and Saint-Gaudens. Large coins. Fill the frame and use a side light.",
        look=["Saint-Gaudens relief throws deep shadows. Run the light test on any split you see in the date or the rays."],
    ),
]


def by_id(series_id: str) -> dict:
    for series in SERIES:
        if series["id"] == series_id:
            return series
    return SERIES[0]


def public_catalog() -> list[dict]:
    return SERIES


def year_spans(text: str) -> list[tuple[int, int]]:
    """Inclusive year ranges from a catalog label such as '1859–1909' or '2006–date'."""
    spans = []
    covered = []
    for match in _RANGE.finditer(text or ""):
        start = int(match.group(1))
        end_text = match.group(2)
        end = 2026 if end_text == "date" else int(end_text)
        if end < start:
            start, end = end, start
        spans.append((start, end))
        covered.append(match.span())
    for match in _ONE_YEAR.finditer(text or ""):
        if any(begin <= match.start() < stop for begin, stop in covered):
            continue
        year = int(match.group())
        spans.append((year, year))
    return spans


def contains_year(series: dict, year: int) -> bool:
    return any(start <= year <= end for start, end in year_spans(series.get("years") or ""))


def _size_ok(series: dict, diameter_mm: float | None) -> bool:
    if not diameter_mm:
        return True
    expected = float(series.get("diameter_mm") or 0)
    if expected <= 0:
        return True
    tolerance = 0.10 if series.get("size_check", True) else 0.18
    return abs(float(diameter_mm) - expected) / expected <= tolerance


def candidates(year: int, surface: str | None = None, diameter_mm: float | None = None) -> list[dict]:
    """Series that can carry this year after metal and size evidence.

    Copper color drops silver and nickel types. A measured diameter drops
    coins of a different size. Unknown color or an uncalibrated camera
    leaves those filters off.
    """
    rows = [item for item in SERIES if contains_year(item, year)]
    if diameter_mm:
        sized = [item for item in rows if _size_ok(item, diameter_mm)]
        if sized:
            rows = sized
    if surface == "copper":
        copper = [item for item in rows if item.get("metal") in ("copper", "brass")]
        if copper:
            rows = copper
    return rows


def suggest_series(
    year: int,
    current_id: str,
    surface: str | None = None,
    diameter_mm: float | None = None,
) -> str | None:
    """Switch series only when the evidence points at one coin.

    The selected series stays when the year still fits it. 1909 stays unset
    when both an Indian Head cent and a Lincoln cent are possible.
    """
    current = by_id(current_id)
    if contains_year(current, year) and _size_ok(current, diameter_mm):
        if surface != "copper" or current.get("metal") in ("copper", "brass"):
            return None
    matches = candidates(year, surface, diameter_mm)
    if len(matches) == 1:
        return matches[0]["id"]
    same_group = [item["id"] for item in matches if item["group"] == current["group"]]
    if len(same_group) == 1:
        return same_group[0]
    return None

