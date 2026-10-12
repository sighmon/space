"""Export the frozen slice for the web page: web/data/mars.json and the script-tag twin web/data/mars.js.

Stdlib only. Every number comes from the project's own parsers (power.parse) reading the files in data/raw/, after each
file's sha256 is checked against data/MANIFEST.tsv. Deficits and opacity come from power.slice.build_report(); the absolute
fluxes and optical depths come from parse_mcd_html. The two are cross-checked before anything is written.
Nothing is interpolated, converted or invented: a scenario with no sample at an Ls is null, never 0.

    python3 -m power.export_web          (from mars-surface-power/)
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

from power.assemble import NO_CONVERSION, NO_POWER
from power.parse import assign_site, parse_mcd_html, parse_rovers, parse_sites, traced_sample
from power.slice import DESIGN, INTERFACE, NOON_FILE, PAPERS, RAW, ROOT, SLUGS, build_report, build_sol

WEB_DATA = ROOT / "web" / "data"
MANIFEST = ROOT / "data" / "MANIFEST.tsv"

LS = tuple(range(0, 360, 30))
# interface key -> (page label, dust code); page order is clear, climatology, dusty, storm
SCENARIOS = (
    ("cold", "Clear", 8),
    ("climatology", "Climatology", 1),
    ("warm", "Dusty", 7),
    ("storm", "Dust storm", 5),
)
# fixed site order, id, display name, kind
SITES = (
    ("deuteronilus", "Deuteronilus Mensae", "candidate"),
    ("protonilus", "Protonilus Mensae", "candidate"),
    ("mesopotamia", "Mesopotamia", "candidate"),
    ("curiosity", "Curiosity", "rover"),
    ("perseverance", "Perseverance", "rover"),
    ("opportunity", "Opportunity", "rover"),
)
CITATIONS = {
    "Deuteronilus Mensae": "Head et al. 2015, Mars Human Landing Site Exploration Zone abstract 1033",
    "Protonilus Mensae": "Gallegos and Newsom 2015, Mars Human Landing Site Exploration Zone abstract 1053",
    "Mesopotamia": "Gallegos and Newsom 2015, Mars Human Landing Site Exploration Zone abstract 1035",
    "Curiosity": "MCD v6.2 web interface rover preset",
    "Perseverance": "MCD v6.2 web interface rover preset",
    "Opportunity": "MCD v6.2 web interface rover preset (also the opacity-check site)",
}
BANNED_WORDS = ("score", "safe", "rank", "forecast")
MAX_BYTES = 1_000_000


def banned_key(key: str) -> bool:
    """True when a key is, or contains as a word, score, safe, rank or forecast (plurals and -ing/-ed forms too)."""
    words = re.split(r"[^a-z0-9]+", re.sub(r"([a-z])([A-Z])", r"\1 \2", str(key)).lower())
    return any(w.startswith(b) for w in words if w for b in BANNED_WORDS)


def guard(node, path="$"):
    if isinstance(node, dict):
        for key, value in node.items():
            if banned_key(key):
                raise ValueError(f"refusing key {key!r} at {path}: score, safe, rank and forecast are not allowed")
            guard(value, f"{path}.{key}")
    elif isinstance(node, (list, tuple)):
        for i, value in enumerate(node):
            guard(value, f"{path}[{i}]")


def read_manifest(raw: Path = RAW, manifest: Path = MANIFEST) -> list[dict]:
    rows = []
    with manifest.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            path = raw / row["filename"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != row["sha256"]:
                raise ValueError(f"{row['filename']}: sha256 {digest} does not match the manifest {row['sha256']}")
            rows.append(row)
    return rows


def _what(name: str) -> str:
    if name.startswith("mcd62_storm_season"):
        return "MCD v6.2 interface response: the dust-storm season limit (out-of-season request rejection)"
    hour = re.match(r"mcd62_([a-z]+)_ls(\d+)_lt(\d+)_([a-z]+)\.html$", name)
    if hour:
        requested = int(hour.group(3))
        clock = f"requested local time {requested} h"
        if requested == 24:
            clock += " (the interface prints this response as local time 0.0 h)"
        return (
            f"MCD v6.2 response, {hour.group(1)} scenario, Ls {int(hour.group(2))}, "
            f"{clock}, {hour.group(4)}"
        )
    if name == DESIGN:
        return "MCD detailed design document v6.1: mean fields every 2 Martian hours from 2 to 24"
    m = re.match(r"mcd62_([a-z]+)_ls(\d+)_([a-z]+)\.html$", name)
    if m:
        return f"MCD v6.2 response, {m.group(1)} scenario, Ls {int(m.group(2))}, {m.group(3)}"
    if name.endswith(".pdf") and "manual" in name:
        return "MCD user manual (version 6.1; says each month covers 30 degrees of Ls)"
    if name.endswith(".pdf"):
        return "Landing-site exploration-zone abstract (site coordinate)"
    if name.endswith(".tab"):
        return "PDS Pancam atmospheric opacity table (880 nm), Opportunity"
    if name.endswith(".lbl"):
        return "PDS label for the Pancam opacity table"
    if name == INTERFACE:
        return "MCD v6.2 web interface page (rover presets)"
    return "Frozen source file"


def build() -> dict:
    manifest = read_manifest()
    digest = {r["filename"]: r["sha256"] for r in manifest}
    url = {r["filename"]: r["url"] for r in manifest}
    report = build_report()

    # sites, exactly as build_report finds them
    found = []
    for name in PAPERS:
        found.extend(parse_sites((RAW / name).read_bytes(), name))
    found.extend(parse_rovers((RAW / INTERFACE).read_text(encoding="utf-8", errors="replace"), INTERFACE))
    by_name = {s.name: s for s in found}
    samples = []
    for path in sorted(RAW.glob("mcd62_*.html")):
        if not NOON_FILE.match(path.name):
            continue
        parsed = parse_mcd_html(path.read_text(encoding="utf-8", errors="replace"), path.name)
        if parsed is None:
            continue
        sample = assign_site(parsed, found)
        if traced_sample(sample):
            samples.append(sample)

    sites = []
    for sid, name, kind in SITES:
        s = by_name[name]
        sites.append({
            "id": sid, "name": name, "kind": kind,
            "lat": s.latitude, "lon": s.longitude,
            "source": CITATIONS[name], "source_file": s.source_file, "source_sha256": digest[s.source_file],
            "source_url": url[s.source_file],
            "coordinate_note": ("exploration-zone candidate coordinate" if kind == "candidate" else "rover preset coordinate"),
        })

    index = {}
    for sample in samples:
        index[(sample.site, sample.key, int(sample.ls))] = sample
    series = {}
    names = {sid: name for sid, name, _ in SITES}
    for sid, name, _ in SITES:
        series[sid] = {}
        for key, _label, _dust in SCENARIOS:
            rows = []
            for ls in LS:
                s = index.get((name, key, ls))
                if s is None:
                    rows.append({"ls": ls, "flux": None, "dod": None, "file": None, "sha256": None})
                else:
                    rows.append({"ls": ls, "flux": s.flux, "dod": s.opacity, "file": s.source_file, "sha256": digest[s.source_file]})
            series[sid][key] = rows

    units = {s.flux_unit for s in samples}
    dod_units = {s.opacity_unit for s in samples}
    if len(units) != 1 or len(dod_units) != 1:
        raise ValueError("mixed units in the frozen responses")
    scenarios = []
    for key, label, dust in SCENARIOS:
        any_s = next(s for s in samples if s.key == key)
        scenarios.append({"key": key, "label": label, "interface_label": any_s.scenario, "dust": dust,
                          "ls_available": [ls for ls in LS if any(index.get((n, key, ls)) for n in names.values())]})

    deficits = [{
        "site": next(i for i, n in names.items() if n == d.site), "scenario": d.scenario_key, "ls": int(d.ls),
        "value": d.value, "unit": d.unit, "dusty_file": d.dusty_file, "baseline_file": d.baseline_file,
        "dusty_sha256": digest[d.dusty_file], "baseline_sha256": digest[d.baseline_file],
    } for d in report.deficits]

    # cross-check: the exported absolute fluxes reproduce the project's deficits
    for d in deficits:
        a = series[d["site"]][d["scenario"]][LS.index(d["ls"])]["flux"]
        b = series[d["site"]]["cold"][LS.index(d["ls"])]["flux"]
        if a is None or b is None or abs((a - b) - d["value"]) > 1e-9:
            raise ValueError(f"deficit mismatch at {d['site']} {d['scenario']} Ls {d['ls']}")
    if len(deficits) != 108:
        raise ValueError(f"expected 108 deficits, found {len(deficits)}")

    sol_report = build_sol(report)
    if sol_report.hours != (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22):
        raise ValueError(f"expected printed local times 0,2,...,22, found {sol_report.hours}")
    if len(sol_report.deficits) != 24:
        raise ValueError(f"expected 24 local-time deficits, found {len(sol_report.deficits)}")
    sol_slug = SLUGS[sol_report.site]
    sol_index = {}
    for item in sol_report.deficits:
        sol_index[(item.scenario_key, int(item.local_time_h))] = item
    sol_rows = []
    for hour in sol_report.hours:
        row = {"hour": hour}
        for key in ("cold", "warm", "storm"):
            # absolute fluxes are on the deficit rows for warm and storm; cold is the baseline of either
            if key == "cold":
                item = sol_index[("warm", hour)]
                row[key] = {"flux": item.baseline_flux, "file": item.baseline_file, "sha256": digest[item.baseline_file]}
            else:
                item = sol_index[(key, hour)]
                row[key] = {"flux": item.dusty_flux, "file": item.dusty_file, "sha256": digest[item.dusty_file]}
                row[key + "_deficit"] = item.value
                if abs((row[key]["flux"] - row["cold"]["flux"]) - item.value) > 1e-9:
                    raise ValueError(f"sol deficit mismatch at local time {hour} {key}")
        sol_rows.append(row)
    noon = next(row for row in sol_rows if row["hour"] == 12)
    seasonal_index = LS.index(int(sol_report.ls))
    for key in ("cold", "warm", "storm"):
        seasonal = series[sol_slug][key][seasonal_index]["flux"]
        if abs(noon[key]["flux"] - seasonal) > 1e-6:
            raise ValueError(f"local noon does not match the seasonal sample for {key}")
    sol = {
        "site": sol_slug,
        "name": sol_report.site,
        "ls": int(sol_report.ls),
        "hours": list(sol_report.hours),
        "why": "This is the site and season where the stored dust-storm minus cold noon flux is deepest.",
        "design_file": DESIGN,
        "design_sha256": digest[DESIGN],
        "flux_unit": sol_report.deficits[0].unit,
        "samples": sol_rows,
        "sentences": list(sol_report.sentences),
        "method": sol_report.method,
    }

    opp = report.opportunity
    opportunity = {
        "unit": opp[0].unit, "product_id_note": "one product per point", "source_file": opp[0].source_file,
        "source_sha256": digest[opp[0].source_file], "label_file": "1tau880_5106_20181207a.lbl",
        "label_sha256": digest["1tau880_5106_20181207a.lbl"],
        "points": [{"sol": p.sol, "ls": p.ls, "value": p.value, "product_id": p.product_id} for p in opp],
        "storm_model_unit": next(iter(dod_units)),
        "note": NO_CONVERSION,
    }

    data = {
        "database": report.version,
        "ls": list(LS),
        "local_time_h": 12, "altitude_m": 0,
        "flux_unit": next(iter(units)), "dod_unit": next(iter(dod_units)),
        "no_power": NO_POWER, "no_conversion": NO_CONVERSION,
        "scenarios": scenarios, "sites": sites, "series": series, "deficits": deficits, "sol": sol,
        "opportunity": opportunity,
        "sentences": list(report.sentences), "method": report.method,
        "manifest": [{"filename": r["filename"], "what": _what(r["filename"]), "url": r["url"],
                      "fetched_utc": r["fetched_utc"], "sha256": r["sha256"], "bytes": int(r["bytes"])} for r in manifest],
        "repo_url": "https://github.com/sighmon/space",
    }
    guard(data)
    return data


def write(data: dict, out: Path = WEB_DATA) -> tuple[Path, Path]:
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    js = "/* generated by power/export_web.py: do not edit. Script-tag twin of mars.json so the page works from file:// */\nwindow.MARS=" + text + ";\n"
    if len(text.encode()) >= MAX_BYTES or len(js.encode()) >= MAX_BYTES:
        raise ValueError("export is larger than 1 MB")
    j, s = out / "mars.json", out / "mars.js"
    j.write_text(text + "\n", encoding="utf-8")
    s.write_text(js, encoding="utf-8")
    return j, s


def main() -> None:
    j, s = write(build())
    sys.stdout.write(f"wrote {j.relative_to(ROOT)} ({j.stat().st_size} bytes) and {s.relative_to(ROOT)} ({s.stat().st_size} bytes)\n")


if __name__ == "__main__":
    main()
