"""Export the September 2017 report as web/data/storm.json and storm.js (stdlib only).

Everything comes from the repository's own build_report (and the same parsers for the K alerts that
the report does not carry). Nothing is modelled, smoothed or filled: a GOES sample that build_report
dropped (missing, -99999 or a non-zero _QUAL_FLAG) is exported as null on the 5-minute grid.
Run from space-weather/:  python3 -m weather.export_web
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from weather import assemble as A
from weather.parse import Alert, Point, parse_alert_pdf
from weather.storm import ALERT_NAMES, GOES_NAME, RAW, ROOT, build_report

WEB_DATA = ROOT / "web" / "data"
MANIFEST = ROOT / "data" / "MANIFEST.tsv"
STEP_S = 300
BANNED_KEYS = ("score", "safe", "rank", "forecast")
MAX_BYTES = 2_000_000
NOAA_SCALES_URL = "https://www.swpc.noaa.gov/noaa-scales-explanation"

MANIFEST_ROLES = {
    "g13_epead_cpflux_5m_20170901_20170930.csv": "GOES-13 EPEAD corrected integral proton flux, 5-minute averages (ZPGT10E, ZPGT100E and a _QUAL_FLAG column per channel)",
    "prf2193.pdf": "NOAA SWPC PRF 2193, Alerts and Warnings Issued (NGDC archive)",
    "prf2194.pdf": "NOAA SWPC PRF 2194, Alerts and Warnings Issued (NGDC archive)",
    "radlab_crater_d1d2_20170904_20170915.csv": "NASA OSDR RadLab, LRO CRaTER-D1D2 absorbed dose rate (uGy/hour), copied as published",
    "radlab_data_api_20240522.html": "Wayback copy of the RadLab data API page, used only to read the dose unit",
}


class BannedKeyError(ValueError):
    pass


def check_keys(node, path="$"):
    """Refuse any key that is, or contains as a word, score / safe / rank / forecast."""
    if isinstance(node, dict):
        for key, value in node.items():
            words = re.split(r"[^a-z0-9]+", re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(key)).lower())
            for banned in BANNED_KEYS:
                if banned in words or str(key).lower() == banned:
                    raise BannedKeyError(f"key {key!r} at {path} is not allowed ({banned})")
            check_keys(value, f"{path}.{key}")
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            check_keys(value, f"{path}[{index}]")


def _iso(moment):
    return None if moment is None else moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def grid_values(points, start, end):
    """Place points on the regular grid; absent slots stay None (never 0)."""
    n = int((end - start).total_seconds()) // STEP_S
    values = [None] * n
    for point in points:
        offset = (point.when - start).total_seconds()
        if offset % STEP_S == 0 and 0 <= offset // STEP_S < n and point.value is not None:
            values[int(offset // STEP_S)] = point.value
    return values


def _runs(flags):
    count, prev = 0, False
    for flag in flags:
        if flag and not prev:
            count += 1
        prev = flag
    return count


def series_stats(values, start, threshold, op):
    """Real counts from the series itself. op is '>=' (all published thresholds here count at-or-above)."""
    above = [i for i, v in enumerate(values) if v is not None and v >= threshold]
    known = [(v, i) for i, v in enumerate(values) if v is not None]
    peak_v, peak_i = max(known) if known else (None, None)
    when = lambda i: None if i is None else _iso(start + timedelta(seconds=i * STEP_S))
    return {
        "threshold": threshold,
        "comparison": op,
        "samples_at_or_above": len(above),
        "minutes_at_or_above": len(above) * STEP_S // 60,
        "hours_at_or_above": round(len(above) * STEP_S / 3600, 2),
        "first_at_or_above": when(above[0]) if above else None,
        "last_at_or_above": when(above[-1]) if above else None,
        "separate_stretches": _runs([v is not None and v >= threshold for v in values]),
        "peak": peak_v,
        "peak_time": when(peak_i),
        "samples_with_value": len(known),
        "samples_without_value": len(values) - len(known),
    }


def goes_quality(start, end):
    """Count rows the parser dropped, by reason, straight from the CSV (flag columns respected)."""
    path = RAW / GOES_NAME
    if not path.exists():
        return None
    lines = path.read_text(encoding="ascii", errors="replace").splitlines()
    head = next(i for i, line in enumerate(lines) if line.startswith("time_tag,ZPGT"))
    out = {}
    for col in ("ZPGT10E", "ZPGT100E"):
        out[col] = {"rows_in_window": 0, "flagged_nonzero": 0, "missing_value": 0}
    for row in csv.DictReader(lines[head:]):
        if not re.match(r"\d{4}-\d{2}-\d{2}", row.get("time_tag") or ""):
            break
        when = datetime.strptime(row["time_tag"].strip(), "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
        if not start <= when < end:
            continue
        for col in out:
            out[col]["rows_in_window"] += 1
            try:
                flagged = float(row.get(col + "_QUAL_FLAG", "")) != 0.0
            except ValueError:
                flagged = True
            try:
                missing = float(row[col]) == -99999.0
            except ValueError:
                missing = True
            out[col]["flagged_nonzero"] += flagged
            out[col]["missing_value"] += missing
    return out


def load_alerts():
    alerts = []
    for name in ALERT_NAMES:
        alerts.extend(parse_alert_pdf((RAW / name).read_bytes(), name))
    return alerts


def _alert_obj(a: Alert, kind):
    return {
        "type": kind,
        "role": a.role or None,
        "channel": a.channel,
        "comparator": a.comparator,
        "value": a.value,
        "unit": a.unit,
        "start": _iso(a.start),
        "end": _iso(a.end),
        "product_id": a.product_id,
        "source_file": a.source_file,
    }


def _grid_warnings(alerts, start, end):
    keep = []
    for a in alerts:
        if a.kind != "geomagnetic" or a.role not in ("warning", "extended warning"):
            continue
        if a.value is None or a.value < A.GRID_THRESHOLD_K or a.start is None or a.end is None:
            continue
        if start <= a.start < end and start <= a.end <= end:
            keep.append(a)
    return sorted(keep, key=lambda a: (a.start, a.end))


def read_manifest():
    rows = []
    with open(MANIFEST, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            rows.append(
                {
                    "filename": row["filename"],
                    "url": row["url"],
                    "fetched_utc": row["fetched_utc"],
                    "sha256": row["sha256"],
                    "bytes": int(row["bytes"]),
                    "what": MANIFEST_ROLES.get(row["filename"], ""),
                }
            )
    return rows


def build_payload(report=None, alerts=None, quality="auto", manifest=None):
    report = report or build_report()
    if quality == "auto":
        quality = goes_quality(report.window_start, report.window_end)
    alerts = alerts if alerts is not None else load_alerts()
    manifest = manifest if manifest is not None else read_manifest()
    start, end = report.window_start, report.window_end
    g10 = grid_values(report.proton_gt10, start, end)
    g100 = grid_values(report.proton_gt100, start, end)
    dose_pts = [p for p in report.dose if p.value is not None]
    dose_t = [int((p.when - start).total_seconds()) for p in dose_pts]
    dose_v = [p.value for p in dose_pts]
    n_slots = len(g10)

    observed = A._observed_grid(alerts, start, end)
    warnings = _grid_warnings(alerts, start, end)
    chosen = report.grid_alert
    grid_alerts = [_alert_obj(a, "grid_issued_alert") for a in observed]
    grid_warn = []
    for a in warnings:
        o = _alert_obj(a, "grid_warning")
        o["longest_in_sentence"] = chosen is not None and (a.start, a.end, a.role, a.product_id) == (chosen.start, chosen.end, chosen.role, chosen.product_id)
        o["hours_valid"] = round((a.end - a.start).total_seconds() / 3600, 2)
        o["observed_k"] = False
        grid_warn.append(o)
    proton = [_alert_obj(a, "proton_alert") for a in report.proton_alerts]

    s10 = series_stats(g10, start, A.POLAR_THRESHOLD_PFU, ">=")
    s100 = series_stats(g100, start, A.CREW_THRESHOLD_PFU, ">=")
    dmin = min(dose_pts, key=lambda p: p.value) if dose_pts else None
    dmax = max(dose_pts, key=lambda p: p.value) if dose_pts else None
    ks = [a.start for a in observed]
    grid_stats = {
        "issued_alerts_k_at_or_above_7": len(observed),
        "first_alert": _iso(min(ks)) if ks else None,
        "last_alert": _iso(max(ks)) if ks else None,
        "highest_k_in_an_alert": max((a.value for a in observed), default=None),
        "warning_valid_from": _iso(chosen.start) if chosen else None,
        "warning_valid_to": _iso(chosen.end) if chosen else None,
        "warning_hours_valid": round((chosen.end - chosen.start).total_seconds() / 3600, 2) if chosen else None,
        "warning_is_observed_k": False,
    }
    dose_stats = {
        "samples": len(dose_pts),
        "min": dmin.value if dmin else None,
        "min_time": _iso(dmin.when) if dmin else None,
        "max": dmax.value if dmax else None,
        "max_time": _iso(dmax.when) if dmax else None,
    }
    first_dose = report.dose[0] if report.dose else None
    f10 = report.proton_gt10[0] if report.proton_gt10 else None
    f100 = report.proton_gt100[0] if report.proton_gt100 else None
    payload = {
        "meta": {
            "storm": report.storm,
            "active_region": report.active_region,
            "window_start": _iso(start),
            "window_end": _iso(end),
            "kind": "past observation of one storm, from archived files",
            "generated_by": "python3 -m weather.export_web (build_report)",
            "latency": "not measured: the files are archives",
            "uncertainty": "none published in these files; no error bars are drawn",
        },
        "series": {
            "t0": _iso(start),
            "step_seconds": STEP_S,
            "slots": n_slots,
            "gt10": {
                "label": ">=10 MeV protons",
                "column": "ZPGT10E",
                "unit": f10.unit if f10 else "",
                "unit_read_as": "pfu",
                "product_id": f10.product_id if f10 else "",
                "source_file": f10.source_file if f10 else "",
                "values": g10,
            },
            "gt100": {
                "label": ">100 MeV protons",
                "column": "ZPGT100E",
                "unit": f100.unit if f100 else "",
                "unit_read_as": "pfu",
                "product_id": f100.product_id if f100 else "",
                "source_file": f100.source_file if f100 else "",
                "values": g100,
            },
            "dose": {
                "label": "CRaTER-D1D2 absorbed dose rate",
                "unit": first_dose.unit if first_dose else "",
                "product_id": first_dose.product_id if first_dose else "",
                "source_file": first_dose.source_file if first_dose else "",
                "where": "measured by CRaTER on the Lunar Reconnaissance Orbiter in lunar orbit, not at flight altitude, in a crew vehicle or on the ground",
                "derived_from_flux": False,
                "t_seconds": dose_t,
                "values": dose_v,
            },
            "downsampling": {
                "applied": False,
                "note": "No downsampling: every 5-minute GOES sample and every CRaTER sample kept by build_report is exported.",
            },
            "quality": {
                "rule": "A GOES sample with a non-zero _QUAL_FLAG for its channel, a -99999 fill value or no value is dropped by weather.parse and exported here as null on the 5-minute grid. Nulls are drawn as gaps, never as 0.",
                "slots_without_value": {"gt10": s10["samples_without_value"], "gt100": s100["samples_without_value"]},
                "csv_rows": quality,
            },
        },
        "alerts": {
            "note": "Times are the event times written in each issued SWPC product (start; end for warnings and summaries). The proton threshold on each item is the pfu written on the alert; it is not a flux. A warning's valid period is not observed K. Geomagnetic alerts and warnings below K 7 are in the PDFs and are not listed here.",
            "proton": proton,
            "grid_issued": grid_alerts,
            "grid_warnings": grid_warn,
        },
        "thresholds": {
            "crew": {
                "label": "NASA SRAG energetic solar particle event",
                "channel": "gt100",
                "value": A.CREW_THRESHOLD_PFU,
                "unit": "pfu",
                "comparison": "above 1 pfu of >100 MeV integral flux (counted here at or above, as the project sentence does)",
                "source": A.CREW_CITATION,
                "url": None,
            },
            "polar": {
                "label": "NOAA S2 solar radiation storm",
                "channel": "gt10",
                "value": A.POLAR_THRESHOLD_PFU,
                "unit": "pfu",
                "comparison": "at or above 100 pfu of >=10 MeV protons",
                "source": A.POLAR_CITATION,
                "url": NOAA_SCALES_URL,
            },
            "grid": {
                "label": "NOAA G3 geomagnetic storm",
                "channel": "K",
                "value": A.GRID_THRESHOLD_K,
                "unit": "Kp",
                "comparison": "Kp = 7",
                "source": A.GRID_CITATION,
                "url": NOAA_SCALES_URL,
            },
            "not_rules": "Published scales and definitions, shown with their source. They are not flight rules, aviation limits or grid limits.",
        },
        "audiences": {
            "crew": {"stats": s100, "dose": dose_stats, "sentence": report.sentences[0]},
            "polar": {"stats": s10, "sentence": report.sentences[1]},
            "grid": {"stats": grid_stats, "sentence": report.sentences[2]},
        },
        "sentences": list(report.sentences),
        "method": report.method,
        "manifest": manifest,
    }
    return payload


def write(payload, out_dir=WEB_DATA):
    check_keys(payload)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    (out_dir / "storm.json").write_text(text + "\n", encoding="utf-8")
    (out_dir / "storm.js").write_text("window.STORM=" + text + ";\n", encoding="utf-8")
    total = sum(p.stat().st_size for p in out_dir.iterdir() if p.is_file())
    if total > MAX_BYTES:
        raise SystemExit(f"web/data is {total} bytes, over {MAX_BYTES}")
    return total


def main() -> None:
    total = write(build_payload())
    sys.stdout.write(f"wrote {WEB_DATA / 'storm.json'} and storm.js ({total} bytes in web/data)\n")


if __name__ == "__main__":
    main()
