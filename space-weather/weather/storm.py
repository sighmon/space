"""Read the frozen local files and write the figure plus the three sentences."""

from __future__ import annotations

import sys
from pathlib import Path

from weather.assemble import WINDOW_END, WINDOW_START, assemble
from weather.figure import render
from weather.parse import active_region, dose_unit, parse_alert_pdf, parse_dose, parse_goes

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
FIGURE = ROOT / "output" / "september-2017.png"

GOES_NAME = "g13_epead_cpflux_5m_20170901_20170930.csv"
ALERT_NAMES = ("prf2193.pdf", "prf2194.pdf")
DOSE_NAME = "radlab_crater_d1d2_20170904_20170915.csv"
UNIT_NAME = "radlab_data_api_20240522.html"


def build_report():
    alerts = []
    region = None
    for name in ALERT_NAMES:
        data = (RAW / name).read_bytes()
        alerts.extend(parse_alert_pdf(data, name))
        if region is None:
            region = active_region(data)
    goes_text = (RAW / GOES_NAME).read_text(encoding="ascii", errors="replace")
    proton_gt10, proton_gt100 = parse_goes(goes_text, GOES_NAME)
    unit = dose_unit((RAW / UNIT_NAME).read_text(encoding="utf-8", errors="replace"))
    dose = parse_dose((RAW / DOSE_NAME).read_text(encoding="utf-8"), unit, DOSE_NAME)
    return assemble(
        alerts=alerts,
        proton_gt10=proton_gt10,
        proton_gt100=proton_gt100,
        dose=dose,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        storm="September 2017",
        active_region=region,
    )


def main() -> None:
    report = build_report()
    render(report, FIGURE)
    sys.stdout.write(report.text)
