"""Pure assembly: already-parsed records in, aligned series and three sentences out."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from weather.parse import Alert, Point, traced_alert, traced_point

WINDOW_START = datetime.fromisoformat("2017-09-04T00:00:00+00:00")
WINDOW_END = datetime.fromisoformat("2017-09-15T00:00:00+00:00")

# Published thresholds. They are not measurements from the storm files.
CREW_THRESHOLD_PFU = 1.0
CREW_CITATION = (
    "NASA SRAG defines an energetic solar particle event as >100 MeV integral "
    "proton flux above 1 pfu (AES-CHP-SW-002, 31 December 2020)"
)
POLAR_THRESHOLD_PFU = 100.0
POLAR_CITATION = (
    "NOAA's S2 solar radiation storm is 10^2 pfu of >=10 MeV protons; passengers "
    "and crew in high-flying aircraft at high latitudes may be exposed to elevated "
    "radiation risk (NOAA Space Weather Scales)"
)
GRID_THRESHOLD_K = 7.0
GRID_CITATION = (
    "NOAA's G3 geomagnetic storm is Kp = 7; voltage corrections may be required, "
    "and false alarms may be triggered on some protection devices (NOAA Space Weather Scales)"
)

DOSE_NOT_FROM_FLUX = "Dose was not computed from flux."


@dataclass(frozen=True)
class Report:
    storm: str
    window_start: datetime
    window_end: datetime
    active_region: str | None
    proton_alerts: tuple[Alert, ...]
    grid_alert: Alert | None
    proton_gt10: tuple[Point, ...]
    proton_gt100: tuple[Point, ...]
    dose: tuple[Point, ...]
    sentences: tuple[str, str, str]
    method: str
    text: str


def assemble(
    *,
    alerts: list[Alert],
    proton_gt10: list[Point],
    proton_gt100: list[Point],
    dose: list[Point],
    window_start: datetime = WINDOW_START,
    window_end: datetime = WINDOW_END,
    storm: str = "September 2017",
    active_region: str | None = None,
) -> Report:
    kept_alerts = [item for item in alerts if traced_alert(item) and _alert_in_window(item, window_start, window_end)]
    proton_alerts = tuple(sorted((item for item in kept_alerts if item.kind == "proton"), key=_alert_key))
    grid_alert = _grid_alert(kept_alerts, window_start, window_end)
    gt10 = _keep_points(proton_gt10, window_start, window_end)
    gt100 = _keep_points(proton_gt100, window_start, window_end)
    kept_dose = _keep_points(dose, window_start, window_end)
    sentences = (
        _crew_sentence(gt100, window_start, window_end, kept_dose),
        _polar_sentence(gt10, window_start, window_end),
        _grid_sentence(grid_alert, window_start, window_end),
    )
    method = _method(storm, window_start, window_end, active_region, proton_alerts, gt10, gt100, kept_dose)
    text = _text(storm, window_start, window_end, active_region, proton_alerts, gt10, gt100, kept_dose, sentences, method)
    return Report(
        storm=storm,
        window_start=window_start,
        window_end=window_end,
        active_region=active_region,
        proton_alerts=proton_alerts,
        grid_alert=grid_alert,
        proton_gt10=gt10,
        proton_gt100=gt100,
        dose=kept_dose,
        sentences=sentences,
        method=method,
        text=text,
    )


def _keep_points(points: list[Point], start: datetime, end: datetime) -> tuple[Point, ...]:
    kept = [
        point
        for point in points
        if traced_point(point) and start <= point.when < end  # type: ignore[operator]
    ]
    return tuple(sorted(kept, key=lambda point: (point.when, point.product_id, point.source_file)))


def _alert_in_window(alert: Alert, start: datetime, end: datetime) -> bool:
    if alert.start is None or not start <= alert.start < end:
        return False
    return alert.end is None or start <= alert.end <= end


def _alert_key(alert: Alert) -> tuple:
    return (alert.start, alert.end or alert.start, alert.channel, alert.value, alert.product_id, alert.source_file)


def _grid_alert(alerts: list[Alert], start: datetime, end: datetime) -> Alert | None:
    candidates = []
    for alert in alerts:
        if alert.kind != "geomagnetic" or alert.end is None or alert.value is None:
            continue
        if alert.value < GRID_THRESHOLD_K:
            continue
        if not (start <= alert.start < end and start <= alert.end <= end):
            continue
        if alert.end <= alert.start:
            continue
        candidates.append(alert)
    if not candidates:
        return None
    candidates.sort(key=lambda alert: (-(alert.end - alert.start).total_seconds(), alert.start, -alert.value, alert.product_id, alert.source_file))
    return candidates[0]


def _crew_sentence(points: tuple[Point, ...], start: datetime, end: datetime, dose: tuple[Point, ...]) -> str:
    above = [point for point in points if point.value is not None and point.value >= CREW_THRESHOLD_PFU]
    dose_file = dose[0].source_file if dose else "the dose file"
    dose_unit = dose[0].unit if dose else "its own unit"
    dose_product = dose[0].product_id if dose else "the dose product"
    count, first, last = _sample_span(above)
    return (
        f"For a crew beyond low Earth orbit, GOES-13 EPEAD ZPGT100E "
        f"({_file_of(points)}, unit {_unit_of(points, 'p/(cm^2 s sr)')}) "
        f"has {count} at or above 1 pfu inside the storm window {_span(start, end)}, "
        f"earliest {first}, latest {last}. {CREW_CITATION}. "
        f"The dose series is {dose_product} absorbed dose rate copied from {dose_file} "
        f"in {dose_unit}. {DOSE_NOT_FROM_FLUX}"
    )


def _polar_sentence(points: tuple[Point, ...], start: datetime, end: datetime) -> str:
    above = [point for point in points if point.value is not None and point.value >= POLAR_THRESHOLD_PFU]
    count, first, last = _sample_span(above)
    return (
        f"For a polar flight, GOES-13 EPEAD ZPGT10E "
        f"({_file_of(points)}, unit {_unit_of(points, 'p/(cm^2 s sr)')}) "
        f"has {count} at or above 100 pfu inside the storm window {_span(start, end)}, "
        f"earliest {first}, latest {last}. {POLAR_CITATION}."
    )


def _grid_sentence(alert: Alert | None, start: datetime, end: datetime) -> str:
    window = _span(start, end)
    if alert is None or alert.start is None or alert.end is None or alert.value is None:
        return (
            f"For electrical-grid operators, no geomagnetic K alert at or above "
            f"{_k_text(GRID_THRESHOLD_K)} with both ends inside the storm window {window} "
            f"is in the frozen alert files. {GRID_CITATION}."
        )
    duration = _elapsed(alert.start, alert.end)
    comparator = "at or above" if alert.comparator == ">=" else "equal to"
    return (
        f"For electrical-grid operators, {alert.product_id} in {alert.source_file} "
        f"warns that the geomagnetic K-index was {comparator} {_k_text(alert.value)} "
        f"from {_iso(alert.start)} to {_iso(alert.end)} ({duration}), inside the storm window {window}. "
        f"{GRID_CITATION}."
    )


def _sample_span(points: list[Point]) -> tuple[str, str, str]:
    if not points:
        return "0 samples", "n/a", "n/a"
    spacing = _spacing_seconds(points)
    if spacing == 300:
        counted = f"{len(points)} five-minute samples ({len(points) * 5} minutes)"
    elif spacing is None:
        counted = f"{len(points)} samples"
    else:
        counted = f"{len(points)} samples spaced {spacing} seconds apart"
    return counted, _iso(points[0].when), _iso(points[-1].when)


def _spacing_seconds(points: list[Point]) -> int | None:
    if len(points) < 2:
        return None
    gaps = []
    for earlier, later in zip(points, points[1:]):
        if earlier.when is None or later.when is None:
            continue
        gaps.append(int((later.when - earlier.when).total_seconds()))
    if not gaps:
        return None
    gaps.sort()
    return gaps[len(gaps) // 2]


def _file_of(points: tuple[Point, ...]) -> str:
    if not points:
        return "the GOES file"
    return points[0].source_file


def _unit_of(points: tuple[Point, ...], fallback: str) -> str:
    if not points:
        return fallback
    return points[0].unit or fallback


def _method(
    storm: str,
    start: datetime,
    end: datetime,
    active_region: str | None,
    alerts: tuple[Alert, ...],
    gt10: tuple[Point, ...],
    gt100: tuple[Point, ...],
    dose: tuple[Point, ...],
) -> str:
    region = f" NOAA region {active_region}." if active_region else ""
    products = _product_line(alerts, gt10, gt100, dose)
    lines = [
        f"Storm {storm}.{region} Shared time axis {_span(start, end)}.",
        f"Products: {products}.",
        f"Units: proton alerts pfu; ZPGT10E {_unit_of(gt10, 'p/(cm^2 s sr)')}; "
        f"ZPGT100E {_unit_of(gt100, 'p/(cm^2 s sr)')}; dose {_unit_of(dose, 'uGy/hour')}.",
        DOSE_NOT_FROM_FLUX,
        "The alert trace copies the pfu threshold written on each SWPC proton alert. It is not the GOES flux.",
        "A sample without a time, value, unit, product id, and source file is omitted.",
        CREW_CITATION + ".",
        POLAR_CITATION + ".",
        GRID_CITATION + ".",
        "Thresholds are those published figures. This project does not set a flight rule, an aviation limit, or a grid limit.",
    ]
    return "\n".join(lines)


def _product_line(alerts: tuple[Alert, ...], gt10: tuple[Point, ...], gt100: tuple[Point, ...], dose: tuple[Point, ...]) -> str:
    names: list[str] = []
    for alert in alerts:
        label = f"{alert.product_id} ({alert.source_file})"
        if label not in names:
            names.append(label)
    for series in (gt10, gt100, dose):
        if not series:
            continue
        label = f"{series[0].product_id} ({series[0].source_file})"
        if label not in names:
            names.append(label)
    return "; ".join(names) if names else "none"


def _text(
    storm: str,
    start: datetime,
    end: datetime,
    active_region: str | None,
    alerts: tuple[Alert, ...],
    gt10: tuple[Point, ...],
    gt100: tuple[Point, ...],
    dose: tuple[Point, ...],
    sentences: tuple[str, str, str],
    method: str,
) -> str:
    region = active_region or "absent"
    lines = [
        f"storm: {storm}",
        f"window: {_span(start, end)}",
        f"active_region: {region}",
        f"products: {_product_line(alerts, gt10, gt100, dose)}",
        f"units: alert pfu; ZPGT10E {_unit_of(gt10, 'p/(cm^2 s sr)')}; "
        f"ZPGT100E {_unit_of(gt100, 'p/(cm^2 s sr)')}; dose {_unit_of(dose, 'uGy/hour')}",
        DOSE_NOT_FROM_FLUX,
        f"crew: {sentences[0]}",
        f"polar: {sentences[1]}",
        f"grid: {sentences[2]}",
        "method:",
        method,
        "figure: output/september-2017.png",
    ]
    return "\n".join(lines) + "\n"


def _span(start: datetime, end: datetime) -> str:
    return f"{_iso(start)} .. {_iso(end)}"


def _iso(moment: datetime | None) -> str:
    if moment is None:
        return "n/a"
    return moment.astimezone(tz=moment.tzinfo).strftime("%Y-%m-%dT%H:%M:%SZ")


def _k_text(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return str(value)


def _elapsed(start: datetime, end: datetime) -> str:
    seconds = int((end - start).total_seconds())
    if seconds < 0:
        seconds = 0
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if minutes == 0:
        return f"{hours} hours"
    return f"{hours} hours {minutes} minutes"
