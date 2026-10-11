"""Read the frozen local files and write the figure plus the check statement."""

from __future__ import annotations

import sys
from pathlib import Path

from power.assemble import assemble
from power.figure import render
from power.parse import (
    assign_site,
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


def build_report():
    sites = []
    for name in PAPERS:
        sites.extend(parse_sites((RAW / name).read_bytes(), name))
    interface = (RAW / INTERFACE).read_text(encoding="utf-8", errors="replace")
    sites.extend(parse_rovers(interface, INTERFACE))
    samples = []
    for path in sorted(RAW.glob("mcd62_*.html")):
        if path.name == SEASON:
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


def main() -> None:
    report = build_report()
    render(report, FIGURE)
    sys.stdout.write(report.text)
