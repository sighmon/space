"""Read the frozen local files and write the figure plus the check statement."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from power.assemble import assemble, assemble_sol
from power.figure import render
from power.parse import (
    assign_site,
    diurnal_hours,
    month_span_degrees,
    parse_mcd_html,
    parse_opportunity,
    parse_rovers,
    parse_sites,
    storm_season_sentence,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
FIGURE = ROOT / "output" / "mcd-v62.png"

PAPERS = (
    "head2015_deuteronilus_1033.pdf",
    "gallegos2015_protonilus_1053.pdf",
    "gallegos2015_mesopotamia_1035.pdf",
)
MANUAL = "mcd_user_manual_6.1.pdf"
INTERFACE = "mcd_v62_web_interface.html"
SEASON = "mcd62_storm_season_limit.html"
OPACITY_TAB = "1tau880_5106_20181207a.tab"
OPACITY_LBL = "1tau880_5106_20181207a.lbl"
DESIGN = "mcd_ddd_v6.1.pdf"
NOON_FILE = re.compile(r"^mcd62_(climatology|cold|warm|storm)_ls\d{3}_[a-z]+\.html$")
SOL_FILE = re.compile(r"^mcd62_(cold|warm|storm)_ls(\d{3})_lt(\d{2})_([a-z]+)\.html$")
SLUGS = {
    "Deuteronilus Mensae": "deuteronilus",
    "Protonilus Mensae": "protonilus",
    "Mesopotamia": "mesopotamia",
    "Curiosity": "curiosity",
    "Perseverance": "perseverance",
    "Opportunity": "opportunity",
}


def _sites():
    sites = []
    for name in PAPERS:
        sites.extend(parse_sites((RAW / name).read_bytes(), name))
    interface = (RAW / INTERFACE).read_text(encoding="utf-8", errors="replace")
    sites.extend(parse_rovers(interface, INTERFACE))
    return sites


def build_report():
    sites = _sites()
    samples = []
    for path in sorted(RAW.glob("mcd62_*.html")):
        if not NOON_FILE.match(path.name):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        parsed = parse_mcd_html(text, path.name)
        if parsed is None:
            continue
        samples.append(assign_site(parsed, sites))
    table = (RAW / OPACITY_TAB).read_text(encoding="utf-8", errors="replace")
    label = (RAW / OPACITY_LBL).read_text(encoding="utf-8", errors="replace")
    opportunity = parse_opportunity(table, label, OPACITY_TAB)
    month = month_span_degrees((RAW / MANUAL).read_bytes())
    season = storm_season_sentence((RAW / SEASON).read_text(encoding="utf-8", errors="replace"))
    return assemble(samples, opportunity, month_degrees=month, storm_season=season)


def build_sol(report=None):
    """The twelve stored local times at the site and Ls where the noon dust-storm deficit is deepest."""
    if report is None:
        report = build_report()
    storms = [item for item in report.deficits if item.scenario_key == "storm"]
    deepest = min(storms, key=lambda item: (item.value, item.site, item.ls))
    slug = SLUGS[deepest.site]
    ls = int(deepest.ls)
    hours = diurnal_hours((RAW / DESIGN).read_bytes()) or ()
    sites = _sites()
    samples = []
    for path in sorted(RAW.glob("mcd62_*_lt*_*.html")):
        match = SOL_FILE.match(path.name)
        if match is None or int(match.group(2)) != ls or match.group(4) != slug:
            continue
        parsed = parse_mcd_html(path.read_text(encoding="utf-8", errors="replace"), path.name)
        if parsed is None:
            continue
        samples.append(assign_site(parsed, sites))
    return assemble_sol(samples, hours)


def main() -> None:
    report = build_report()
    sol = build_sol(report)
    render(report, FIGURE, sol)
    sys.stdout.write(report.text)
    if not report.text.endswith("\n"):
        sys.stdout.write("\n")
    sys.stdout.write(sol.text)
