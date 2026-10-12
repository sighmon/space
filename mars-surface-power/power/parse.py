"""Parsers for the frozen MCD responses, landing-site papers, and Pancam table."""

from __future__ import annotations

import re
from dataclasses import dataclass

from power.pdftext import pdf_lines

_MCD = re.compile(
    r"MCD_v([0-9.]+) with ([^.]+)\. Ls ([0-9.]+)deg\."
)
_LAT = re.compile(r"Latitude ([+-]?[0-9.]+)N")
_LON = re.compile(r"Longitude ([+-]?[0-9.]+)E")
_LT = re.compile(r"Local time ([0-9.]+)h")
_ALT = re.compile(r"Altitude ([0-9.]+) m ALS")
_FLUX = re.compile(
    r"Incident solar flux on horizontal surface \(([^)]+)\) \.+ ([+-]?[0-9.]+(?:[eE][+-]?[0-9]+)?)"
)
_DOD = re.compile(
    r"(Monthly mean dust column visible optical depth above surface) \.+ "
    r"([+-]?[0-9.]+(?:[eE][+-]?[0-9]+)?)"
)
_PAIR = re.compile(r"\(([0-9]+(?:\.[0-9]+)?)E,([0-9]+(?:\.[0-9]+)?)([NS])\)")
_NORTH = re.compile(r"\(([0-9]+(?:\.[0-9]+)?)[^0-9A-Za-z]*N,([0-9]+(?:\.[0-9]+)?)[^0-9A-Za-z]*E\)")
_ROVER = re.compile(
    r"spacecraft\.value === '([A-Za-z0-9]+)'\)[\s\S]{0,240}?MapValues\(([+-]?[0-9.]+),([+-]?[0-9.]+)\)"
)
_MONTH = re.compile(r"Eachmonthcovers30")
_STORM_SEASON = re.compile(r"180 < Ls < 360")
_ROVERS = ("Curiosity", "Perseverance", "Opportunity")


@dataclass(frozen=True)
class Site:
    name: str
    latitude: float
    longitude: float
    source_file: str


@dataclass(frozen=True)
class Sample:
    version: str
    scenario: str
    key: str
    ls: float
    latitude: float
    longitude: float
    site: str
    local_time_h: float | None
    altitude_m: float | None
    flux: float | None
    flux_unit: str
    opacity: float | None
    opacity_unit: str
    source_file: str


@dataclass(frozen=True)
class OpacityPoint:
    ls: float | None
    sol: float | None
    value: float | None
    unit: str
    source_file: str
    product_id: str


def traced_sample(sample: Sample) -> bool:
    return bool(
        sample.version
        and sample.scenario
        and sample.key
        and sample.site
        and sample.flux is not None
        and sample.flux_unit
        and sample.source_file
    )


def traced_opacity(point: OpacityPoint) -> bool:
    return (
        point.ls is not None
        and point.sol is not None
        and point.value is not None
        and point.value != -1.0
        and bool(point.unit)
        and bool(point.source_file)
        and bool(point.product_id)
    )


def scenario_key(phrase: str) -> str:
    text = phrase.lower()
    if "dust storm" in text:
        return "storm"
    if "cold scenario" in text:
        return "cold"
    if "warm scenario" in text:
        return "warm"
    if "climatology" in text:
        return "climatology"
    return ""


def parse_mcd_html(text: str, source_file: str) -> Sample | None:
    header = _MCD.search(text)
    lat = _LAT.search(text)
    lon = _LON.search(text)
    flux = _FLUX.search(text)
    dod = _DOD.search(text)
    if header is None or lat is None or lon is None or flux is None or dod is None:
        return None
    local = _LT.search(text)
    altitude = _ALT.search(text)
    phrase = header.group(2).strip()
    return Sample(
        version=f"MCD_v{header.group(1)}",
        scenario=phrase,
        key=scenario_key(phrase),
        ls=float(header.group(3)),
        latitude=float(lat.group(1)),
        longitude=float(lon.group(1)),
        site="",
        local_time_h=float(local.group(1)) if local else None,
        altitude_m=float(altitude.group(1)) if altitude else None,
        flux=float(flux.group(2)),
        flux_unit=flux.group(1),
        opacity=float(dod.group(2)),
        opacity_unit=dod.group(1),
        source_file=source_file,
    )


def parse_sites(pdf: bytes, source_file: str) -> list[Site]:
    text = _compact(pdf)
    name = _paper_name(text)
    if not name:
        return []
    found: list[Site] = []
    if name == "Deuteronilus Mensae":
        match = _NORTH.search(text)
        if match:
            found.append(Site(name, float(match.group(1)), float(match.group(2)), source_file))
        return found
    for match in _PAIR.finditer(text):
        latitude = float(match.group(2))
        if match.group(3) == "S":
            latitude = -latitude
        found.append(Site(name, latitude, float(match.group(1)), source_file))
        break
    return found


def parse_rovers(html: str, source_file: str) -> list[Site]:
    sites: list[Site] = []
    for match in _ROVER.finditer(html):
        name = match.group(1)
        if name not in _ROVERS:
            continue
        longitude = float(match.group(2))
        latitude = float(match.group(3))
        sites.append(Site(name, latitude, longitude, source_file))
    return sites


def month_span_degrees(pdf: bytes) -> int | None:
    if _MONTH.search(_compact(pdf)):
        return 30
    return None


def diurnal_hours(pdf: bytes) -> tuple[int, ...] | None:
    """The design document's stored clock: every 2 hours from 2 to 24.

    Both phrases have to be in the file. A missing phrase does not become a guessed clock.
    """
    text = _compact(pdf)
    if "every2martianhours" not in text or "from2to24hours" not in text:
        return None
    return tuple(range(2, 26, 2))


def _compact(pdf: bytes) -> str:
    return re.sub(r"\s+", "", " ".join(pdf_lines(pdf)))


def storm_season_sentence(html: str) -> str:
    if _STORM_SEASON.search(html):
        return "180 < Ls < 360"
    return ""


def assign_site(sample: Sample, sites: list[Site]) -> Sample:
    name = ""
    for site in sites:
        if abs(site.latitude - sample.latitude) < 1e-3 and abs(site.longitude - sample.longitude) < 1e-3:
            if name and name != site.name:
                return sample
            name = site.name
    if not name:
        return sample
    return Sample(
        version=sample.version,
        scenario=sample.scenario,
        key=sample.key,
        ls=sample.ls,
        latitude=sample.latitude,
        longitude=sample.longitude,
        site=name,
        local_time_h=sample.local_time_h,
        altitude_m=sample.altitude_m,
        flux=sample.flux,
        flux_unit=sample.flux_unit,
        opacity=sample.opacity,
        opacity_unit=sample.opacity_unit,
        source_file=sample.source_file,
    )


def parse_opportunity(table: str, label: str, source_file: str) -> list[OpacityPoint]:
    if "2018-06-05" not in label or "PANCAM_R8_880NM" not in label:
        return []
    if "ATMOSPHERIC_OPACITY" not in label or "Measured atmospheric opacity" not in label:
        return []
    unit = "PANCAM_R8_880NM atmospheric opacity"
    rows: list[tuple[float, float, float, str]] = []
    for line in table.splitlines():
        if not line.startswith('"'):
            continue
        parts = [part.strip().strip('"') for part in line.split(",")]
        if len(parts) < 7:
            continue
        try:
            ls = float(parts[1])
            sol = float(parts[3])
            value = float(parts[6])
        except ValueError:
            continue
        rows.append((sol, ls, value, parts[0]))
    if not rows:
        return []
    last = max(row[0] for row in rows)
    window = last - 40.0
    points: list[OpacityPoint] = []
    for sol, ls, value, product in rows:
        if sol < window:
            continue
        points.append(
            OpacityPoint(
                ls=ls,
                sol=sol,
                value=None if value == -1.0 else value,
                unit=unit,
                source_file=source_file,
                product_id=product,
            )
        )
    points.sort(key=lambda point: (point.sol or 0, point.product_id))
    return points


def _paper_name(text: str) -> str:
    if "DeuteronilusMensae" in text and "DichotomyBoundary" in text:
        return "Deuteronilus Mensae"
    if "ProtonilusMensae" in text:
        return "Protonilus Mensae"
    if "Mesopotamia" in text:
        return "Mesopotamia"
    return ""
