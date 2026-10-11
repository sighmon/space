"""Pure assembly: parsed samples in, deficit series and the check statement out."""

from __future__ import annotations

from dataclasses import dataclass

from power.parse import OpacityPoint, Sample, traced_opacity, traced_sample

NO_POWER = "No power system was sized."
NO_CONVERSION = "No conversion factor was applied."


@dataclass(frozen=True)
class Deficit:
    site: str
    scenario_key: str
    scenario: str
    baseline: str
    ls: float
    value: float
    unit: str
    dusty_file: str
    baseline_file: str


@dataclass(frozen=True)
class StoredOpacity:
    site: str
    scenario_key: str
    scenario: str
    ls: float
    value: float
    unit: str
    source_file: str


@dataclass(frozen=True)
class Report:
    version: str
    sites: tuple[str, ...]
    deficits: tuple[Deficit, ...]
    storm_opacity: tuple[StoredOpacity, ...]
    opportunity: tuple[OpacityPoint, ...]
    sentences: tuple[str, ...]
    method: str
    text: str


def assemble(
    samples: list[Sample],
    opportunity: list[OpacityPoint],
    *,
    month_degrees: int | None = None,
    storm_season: str = "",
) -> Report:
    kept = [sample for sample in samples if traced_sample(sample)]
    kept.sort(key=lambda sample: (sample.site, sample.key, sample.ls, sample.source_file))
    version = kept[0].version if kept else ""
    sites = tuple(dict.fromkeys(sample.site for sample in kept))
    deficits = _deficits(kept)
    storm_opacity = _storm_opacity(kept)
    copied = tuple(point for point in opportunity if traced_opacity(point))
    sentences = _sentences(kept, deficits, storm_opacity, copied, month_degrees, storm_season)
    method = _method(kept, deficits, storm_opacity, copied, month_degrees, storm_season)
    text = _text(version, sites, kept, sentences, method)
    return Report(
        version=version,
        sites=sites,
        deficits=deficits,
        storm_opacity=storm_opacity,
        opportunity=copied,
        sentences=sentences,
        method=method,
        text=text,
    )


def _deficits(samples: list[Sample]) -> tuple[Deficit, ...]:
    by_key: dict[tuple[str, str, float], Sample] = {}
    for sample in samples:
        by_key[(sample.site, sample.key, sample.ls)] = sample
    found: list[Deficit] = []
    for sample in samples:
        if sample.key not in ("warm", "storm"):
            continue
        baseline = by_key.get((sample.site, "cold", sample.ls))
        if baseline is None or baseline.flux is None or sample.flux is None:
            continue
        if baseline.flux_unit != sample.flux_unit or not sample.flux_unit:
            continue
        found.append(
            Deficit(
                site=sample.site,
                scenario_key=sample.key,
                scenario=sample.scenario,
                baseline=baseline.scenario,
                ls=sample.ls,
                value=sample.flux - baseline.flux,
                unit=sample.flux_unit,
                dusty_file=sample.source_file,
                baseline_file=baseline.source_file,
            )
        )
    found.sort(key=lambda item: (item.site, item.scenario_key, item.ls, item.dusty_file))
    return tuple(found)


def _storm_opacity(samples: list[Sample]) -> tuple[StoredOpacity, ...]:
    found: list[StoredOpacity] = []
    for sample in samples:
        if sample.key != "storm" or sample.opacity is None or not sample.opacity_unit:
            continue
        found.append(
            StoredOpacity(
                site=sample.site,
                scenario_key=sample.key,
                scenario=sample.scenario,
                ls=sample.ls,
                value=sample.opacity,
                unit=sample.opacity_unit,
                source_file=sample.source_file,
            )
        )
    found.sort(key=lambda item: (item.site, item.ls, item.source_file))
    return tuple(found)


def _sentences(
    samples: list[Sample],
    deficits: tuple[Deficit, ...],
    storm_opacity: tuple[StoredOpacity, ...],
    opportunity: tuple[OpacityPoint, ...],
    month_degrees: int | None,
    storm_season: str,
) -> tuple[str, ...]:
    lines: list[str] = []
    sites = dict.fromkeys(item.site for item in deficits)
    for site in sites:
        for key in ("warm", "storm"):
            series = [item for item in deficits if item.site == site and item.scenario_key == key]
            if series:
                lines.append(_deficit_sentence(series, month_degrees))
    opacity_sites = dict.fromkeys(item.site for item in storm_opacity)
    for site in opacity_sites:
        series = [item for item in storm_opacity if item.site == site]
        lines.append(_opacity_sentence(series))
    lines.append(_opportunity_sentence(samples, opportunity, storm_season))
    lines.append(NO_POWER)
    return tuple(lines)


def _deficit_sentence(series: list[Deficit], month_degrees: int | None) -> str:
    lead = series[0]
    below = [item for item in series if item.value < 0]
    deepest = min(series, key=lambda item: (item.value, item.ls))
    below_list = ", ".join(_ls(item.ls) for item in below) if below else "none"
    month = ""
    if month_degrees is not None:
        month = f" Each database month covers {month_degrees} degrees of Ls."
    values = "; ".join(
        f"Ls {_ls(item.ls)} {_num(item.value)} {item.unit} ({item.dusty_file} minus {item.baseline_file})"
        for item in series
    )
    return (
        f"At {lead.site}, {lead.scenario} minus {lead.baseline} incident solar flux "
        f"is {_num(deepest.value)} {lead.unit} at its deepest, Ls {_ls(deepest.ls)} "
        f"({deepest.dusty_file} minus {deepest.baseline_file}). "
        f"The difference is negative on {len(below)} of {len(series)} shared seasonal samples "
        f"({below_list}). Samples: {values}.{month}"
    )


def _opacity_sentence(series: list[StoredOpacity]) -> str:
    lead = series[0]
    values = "; ".join(
        f"Ls {_ls(item.ls)} {_num(item.value)} {item.unit} ({item.source_file})"
        for item in series
    )
    return f"At {lead.site}, {lead.scenario} optical depth is {values}."


def _opportunity_sentence(
    samples: list[Sample],
    opportunity: tuple[OpacityPoint, ...],
    storm_season: str,
) -> str:
    if not opportunity:
        return "Opportunity's opacity record has no traced values in the frozen file."
    ordered = sorted(opportunity, key=lambda point: (point.sol, point.product_id))
    peak = max(ordered, key=lambda point: (point.value, -(point.sol or 0)))
    first, last = ordered[0], ordered[-1]
    storm = [
        sample for sample in samples
        if sample.site == "Opportunity" and sample.key == "storm" and sample.opacity is not None and sample.opacity_unit
    ]
    storm.sort(key=lambda sample: sample.ls)
    if storm:
        listed = ", ".join(f"Ls {_ls(sample.ls)} {_num(sample.opacity)} {sample.opacity_unit} ({sample.source_file})" for sample in storm)
        storm_text = f"The dust-storm responses at Opportunity are {listed}."
    else:
        storm_text = "No traced dust-storm opacity at Opportunity is in the frozen responses."
    season = f" The web interface limits that scenario to {storm_season}." if storm_season else ""
    same = storm and storm[0].opacity_unit == peak.unit
    comparison = (
        "The units match, so the copied opacity and the dust-storm opacity are the same unit."
        if same
        else f"The record unit is {peak.unit} and the scenario unit is {storm[0].opacity_unit if storm else 'absent'}. {NO_CONVERSION}"
    )
    return (
        f"Opportunity {peak.unit} copied from {peak.source_file} "
        f"covers sol {_num(first.sol)} Ls {_ls(first.ls)} through sol {_num(last.sol)} Ls {_ls(last.ls)}, "
        f"{len(ordered)} samples. The maximum is {_num(peak.value)} at sol {_num(peak.sol)} "
        f"Ls {_ls(peak.ls)} ({peak.product_id}). {storm_text}{season} {comparison}"
    )


def _method(
    samples: list[Sample],
    deficits: tuple[Deficit, ...],
    storm_opacity: tuple[StoredOpacity, ...],
    opportunity: tuple[OpacityPoint, ...],
    month_degrees: int | None,
    storm_season: str,
) -> str:
    version = samples[0].version if samples else "absent"
    scenarios = []
    for sample in samples:
        if sample.scenario not in scenarios:
            scenarios.append(sample.scenario)
    sites = []
    for sample in samples:
        label = f"{sample.site} ({_num(sample.latitude)} N, {_num(sample.longitude)} E)"
        if label not in sites:
            sites.append(label)
    local = sorted({sample.local_time_h for sample in samples if sample.local_time_h is not None})
    altitude = sorted({sample.altitude_m for sample in samples if sample.altitude_m is not None})
    month = (
        f"The user manual says each month covers {month_degrees} degrees of Ls."
        if month_degrees is not None
        else "The month spacing was not found in the frozen manual."
    )
    season = (
        f"The frozen interface page limits the dust-storm scenario to {storm_season}."
        if storm_season
        else "No dust-storm season limit was found in the frozen interface page."
    )
    if storm_season and any(sample.key == "storm" and sample.ls == 180 for sample in samples):
        season += " Saved responses at Ls 180 are included because the interface returned them."
    unit = deficits[0].unit if deficits else "absent"
    opp = opportunity[0].unit if opportunity else "absent"
    lines = [
        f"{version}. Scenarios: {'; '.join(scenarios) if scenarios else 'none'}.",
        f"Sites: {'; '.join(sites) if sites else 'none'}.",
        f"Local time {', '.join(_num(value) + ' h' for value in local) or 'absent'}. "
        f"Altitude {', '.join(_num(value) + ' m ALS' for value in altitude) or 'absent'}.",
        f"Sunlight deficit is stored dusty flux minus stored cold flux, in {unit}. {NO_POWER}",
        "Climatology samples are frozen and named. The deficit panels are warm minus cold and dust storm minus cold.",
        month,
        season,
        "A sample without a version, scenario, site, Ls, flux, unit, and source file is omitted.",
        f"Opportunity opacity is copied in {opp}. {NO_CONVERSION}",
        "Plotted warm minus cold: " + _deficit_trace(deficits, "warm"),
        "Plotted dust storm minus cold: " + _deficit_trace(deficits, "storm"),
        "Plotted dust-storm optical depth: " + _opacity_trace(storm_opacity),
        "Plotted Opportunity opacity: " + _opportunity_trace(opportunity),
    ]
    return "\n".join(lines)


def _deficit_trace(deficits: tuple[Deficit, ...], key: str) -> str:
    series = [item for item in deficits if item.scenario_key == key]
    if not series:
        return "none"
    return "; ".join(
        f"{item.site} Ls {_ls(item.ls)} {_num(item.value)} {item.unit} ({item.dusty_file} minus {item.baseline_file})"
        for item in series
    )


def _opacity_trace(storm_opacity: tuple[StoredOpacity, ...]) -> str:
    if not storm_opacity:
        return "none"
    return "; ".join(
        f"{item.site} Ls {_ls(item.ls)} {_num(item.value)} {item.unit} ({item.source_file})"
        for item in storm_opacity
    )


def _opportunity_trace(opportunity: tuple[OpacityPoint, ...]) -> str:
    if not opportunity:
        return "none"
    ordered = sorted(opportunity, key=lambda point: (point.sol or 0, point.product_id))
    return "; ".join(
        f"sol {_num(point.sol)} Ls {_ls(point.ls)} {_num(point.value)} {point.unit} ({point.product_id}, {point.source_file})"
        for point in ordered
    )


def _text(
    version: str,
    sites: tuple[str, ...],
    samples: list[Sample],
    sentences: tuple[str, ...],
    method: str,
) -> str:
    scenarios = []
    units = []
    for sample in samples:
        if sample.scenario not in scenarios:
            scenarios.append(sample.scenario)
        if sample.flux_unit and sample.flux_unit not in units:
            units.append(sample.flux_unit)
        if sample.opacity_unit and sample.opacity_unit not in units:
            units.append(sample.opacity_unit)
    lines = [
        f"database: {version or 'absent'}",
        f"scenarios: {'; '.join(scenarios) if scenarios else 'none'}",
        f"sites: {'; '.join(sites) if sites else 'none'}",
        f"units: {'; '.join(units) if units else 'none'}",
        NO_POWER,
        *[f"check: {sentence}" for sentence in sentences],
        "method:",
        method,
        "figure: output/mcd-v62.png",
    ]
    return "\n".join(lines) + "\n"


def _ls(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return _num(value)


def _num(value: float | None) -> str:
    if value is None:
        return "absent"
    return f"{value:.6g}"
