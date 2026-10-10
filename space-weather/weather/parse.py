"""Parsers for the frozen NOAA, GOES, and RadLab files. No dose is derived here."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from io import StringIO

from weather.pdftext import pdf_lines

_MISSING = -99999.0
_ISSUE = re.compile(r"^(\d{2}) Sep (\d{4})$")
_RANGE = re.compile(r"(\d{2})/(\d{4})\s*-\s*(?:(\d{2})/)?(\d{4})")
_MOMENT = re.compile(r"(\d{2})/(\d{4})")
_PROTON = re.compile(r"(>=|>)\s*(\d+)\s*pfu", re.IGNORECASE)
_KINDEX = re.compile(r"K\s*(>=|=)\s*(\d)(?!\d)")
_PRF = re.compile(r"SWPC PRF (\d{4})")
_YEAR = re.compile(r"September 2017")


@dataclass(frozen=True)
class Point:
    when: datetime | None
    value: float | None
    unit: str
    product_id: str
    source_file: str


@dataclass(frozen=True)
class Alert:
    kind: str
    start: datetime | None
    end: datetime | None
    value: float | None
    comparator: str
    channel: str
    unit: str
    product_id: str
    source_file: str


def traced_point(point: Point) -> bool:
    return (
        point.when is not None
        and point.value is not None
        and bool(point.unit)
        and bool(point.product_id)
        and bool(point.source_file)
    )


def traced_alert(alert: Alert) -> bool:
    return (
        alert.start is not None
        and alert.value is not None
        and bool(alert.unit)
        and bool(alert.product_id)
        and bool(alert.source_file)
        and bool(alert.channel)
    )


def parse_alert_pdf(data: bytes, source_file: str) -> list[Alert]:
    lines = pdf_lines(data)
    text = "\n".join(lines)
    if _YEAR.search(text) is None:
        return []
    product = _PRF.search(text)
    if product is None:
        return []
    product_id = f"SWPC PRF {product.group(1)}"
    alerts: list[Alert] = []
    block: list[str] = []

    def flush() -> None:
        if block:
            alerts.extend(_alerts_in_block(" ".join(block), product_id, source_file))

    for line in lines:
        if _ISSUE.match(line):
            flush()
            block = [line]
        elif block:
            block.append(line)
    flush()
    return alerts


def _alerts_in_block(block: str, product_id: str, source_file: str) -> list[Alert]:
    start, end = _event_span(block)
    found: list[Alert] = []
    if "Proton" in block and "MeV" in block:
        channel = "100MeV" if "100MeV" in block.replace(" ", "") or "100 MeV" in block else ""
        if not channel and ("10MeV" in block.replace(" ", "") or "10 MeV" in block):
            channel = "10MeV"
        match = _PROTON.search(block.replace(" ", ""))
        if match is None:
            match = _PROTON.search(block)
        if channel and match is not None:
            found.append(
                Alert(
                    kind="proton",
                    start=start,
                    end=end,
                    value=float(match.group(2)),
                    comparator=match.group(1),
                    channel=channel,
                    unit="pfu",
                    product_id=product_id,
                    source_file=source_file,
                )
            )
    kmatch = _KINDEX.search(block)
    if kmatch is not None and "Geomagnetic" in block:
        found.append(
            Alert(
                kind="geomagnetic",
                start=start,
                end=end,
                value=float(kmatch.group(2)),
                comparator=kmatch.group(1),
                channel="K",
                unit="K",
                product_id=product_id,
                source_file=source_file,
            )
        )
    return found


def _event_span(block: str) -> tuple[datetime | None, datetime | None]:
    ranged = _RANGE.search(block)
    if ranged:
        day1 = int(ranged.group(1))
        hhmm1 = ranged.group(2)
        day2 = int(ranged.group(3) or ranged.group(1))
        hhmm2 = ranged.group(4)
        return _stamp(day1, hhmm1), _stamp(day2, hhmm2)
    moment = _MOMENT.search(block)
    if moment:
        return _stamp(int(moment.group(1)), moment.group(2)), None
    return None, None


def _stamp(day: int, hhmm: str) -> datetime | None:
    if len(hhmm) != 4 or not hhmm.isdigit():
        return None
    hour = int(hhmm[:2])
    minute = int(hhmm[2:])
    if hour > 23 or minute > 59 or not 1 <= day <= 30:
        return None
    return datetime(2017, 9, day, hour, minute, tzinfo=timezone.utc)


def active_region(data: bytes) -> str | None:
    text = "\n".join(pdf_lines(data))
    match = re.search(r"Region (\d{4})", text)
    return match.group(1) if match else None


def parse_goes(text: str, source_file: str) -> tuple[list[Point], list[Point]]:
    units = {
        "ZPGT10E": _unit(text, "ZPGT10E"),
        "ZPGT100E": _unit(text, "ZPGT100E"),
    }
    header_at = None
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("time_tag,ZPGT"):
            header_at = index
            break
    if header_at is None:
        return [], []
    reader = csv.DictReader(lines[header_at:])
    gt10: list[Point] = []
    gt100: list[Point] = []
    for row in reader:
        if row is None or "time_tag" not in row or not row["time_tag"]:
            break
        if not re.match(r"\d{4}-\d{2}-\d{2}", row["time_tag"]):
            break
        when = _goes_time(row["time_tag"])
        gt10.append(_goes_point(row, "ZPGT10E", units["ZPGT10E"], when, source_file))
        gt100.append(_goes_point(row, "ZPGT100E", units["ZPGT100E"], when, source_file))
    return gt10, gt100


def _unit(text: str, column: str) -> str:
    match = re.search(rf"{column}:units = \"([^\"]+)\"", text)
    return match.group(1) if match else ""


def _goes_time(value: str) -> datetime | None:
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc)


def _goes_point(row: dict[str, str], column: str, unit: str, when: datetime | None, source_file: str) -> Point:
    raw = row.get(column, "")
    flag = row.get(f"{column}_QUAL_FLAG", "")
    value: float | None
    try:
        value = float(raw)
    except ValueError:
        value = None
    if value is None or value == _MISSING:
        value = None
    try:
        bad_flag = float(flag) != 0.0
    except ValueError:
        bad_flag = True
    if bad_flag:
        value = None
    return Point(
        when=when,
        value=value,
        unit=unit,
        product_id=f"GOES-13 EPEAD {column}",
        source_file=source_file,
    )


def dose_unit(html: str) -> str:
    if "absorbed_dose_rate" in html and "&mu;Gy/hour" in html:
        return "uGy/hour"
    return ""


def parse_dose(text: str, unit: str, source_file: str) -> list[Point]:
    reader = csv.DictReader(StringIO(text))
    points: list[Point] = []
    for row in reader:
        stamp = (row.get("timestamp") or "").strip().strip('"')
        when = _dose_time(stamp)
        raw = (row.get("absorbed_dose_rate") or "").strip()
        try:
            value: float | None = float(raw)
        except ValueError:
            value = None
        product = (row.get("instrument_id") or "").strip().strip('"')
        points.append(
            Point(
                when=when,
                value=value,
                unit=unit,
                product_id=product,
                source_file=source_file,
            )
        )
    return points


def _dose_time(value: str) -> datetime | None:
    for pattern in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(value, pattern).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
