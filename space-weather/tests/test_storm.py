"""The shipped assembly, on a small series and on the frozen September 2017 files."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from weather.assemble import DOSE_NOT_FROM_FLUX, WINDOW_END, WINDOW_START, assemble
from weather.figure import read_method, render
from weather.parse import Alert, Point, dose_unit, parse_alert_pdf, parse_dose, parse_goes, traced_point
from weather.storm import ALERT_NAMES, DOSE_NAME, GOES_NAME, RAW, UNIT_NAME, build_report

OUT = Path(__file__).resolve().parent / "_storm_figure.png"


def _utc(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


class AssemblyTests(unittest.TestCase):
    def test_synthetic_series_keep_dose_and_drop_untraced_values(self):
        start = _utc(2020, 1, 1, 0)
        end = start + timedelta(hours=6)

        def at(minutes, value, product, unit, source):
            return Point(start + timedelta(minutes=minutes), value, unit, product, source)

        alerts = [
            Alert("proton", start + timedelta(minutes=10), None, 10.0, ">=", "10MeV", "pfu", "SWPC PRF 0001", "alert.pdf"),
            Alert("geomagnetic", start + timedelta(hours=1), start + timedelta(hours=3), 7.0, ">=", "K", "K", "SWPC PRF 0001", "alert.pdf"),
        ]
        gt10 = [
            at(0, 50.0, "GOES-13 EPEAD ZPGT10E", "p/(cm^2 s sr)", "goes.csv"),
            at(5, 150.0, "GOES-13 EPEAD ZPGT10E", "p/(cm^2 s sr)", "goes.csv"),
            at(10, 150.0, "GOES-13 EPEAD ZPGT10E", "p/(cm^2 s sr)", "goes.csv"),
        ]
        gt100 = [
            at(0, 0.2, "GOES-13 EPEAD ZPGT100E", "p/(cm^2 s sr)", "goes.csv"),
            at(5, 2.0, "GOES-13 EPEAD ZPGT100E", "p/(cm^2 s sr)", "goes.csv"),
            at(10, 2.0, "GOES-13 EPEAD ZPGT100E", "p/(cm^2 s sr)", "goes.csv"),
        ]
        dose = [
            at(0, 11.5, "CRaTER-D1D2", "uGy/hour", "dose.csv"),
            at(60, 12.5, "CRaTER-D1D2", "uGy/hour", "dose.csv"),
            Point(start + timedelta(minutes=30), 99999.0, "uGy/hour", "", "dose.csv"),
        ]
        report = assemble(
            alerts=alerts,
            proton_gt10=gt10,
            proton_gt100=gt100,
            dose=dose,
            window_start=start,
            window_end=end,
            storm="synthetic",
            active_region=None,
        )
        self.assertEqual([point.value for point in report.dose], [11.5, 12.5])
        self.assertNotIn("99999", report.text)
        self.assertEqual(report.window_start, start)
        self.assertEqual(report.window_end, end)
        for series in (report.proton_gt10, report.proton_gt100, report.dose):
            for point in series:
                self.assertGreaterEqual(point.when, start)
                self.assertLess(point.when, end)
        self.assertEqual(len(report.sentences), 3)
        self.assertIn("1 pfu", report.sentences[0])
        self.assertIn("100 pfu", report.sentences[1])
        self.assertIn("Kp = 7", report.sentences[2])
        self.assertIn("2 hours", report.sentences[2])
        self.assertIn(DOSE_NOT_FROM_FLUX, report.text)
        self.assertIn(report.method, report.text)
        zeroed = assemble(
            alerts=alerts,
            proton_gt10=[Point(point.when, 0.0, point.unit, point.product_id, point.source_file) for point in gt10],
            proton_gt100=[Point(point.when, 0.0, point.unit, point.product_id, point.source_file) for point in gt100],
            dose=dose,
            window_start=start,
            window_end=end,
            storm="synthetic",
        )
        self.assertEqual(zeroed.dose, report.dose)

    def test_frozen_storm_uses_the_shipped_parsers(self):
        report = build_report()
        alerts = []
        for name in ALERT_NAMES:
            alerts.extend(parse_alert_pdf((RAW / name).read_bytes(), name))
        goes = (RAW / GOES_NAME).read_text(encoding="ascii", errors="replace")
        gt10, gt100 = parse_goes(goes, GOES_NAME)
        unit = dose_unit((RAW / UNIT_NAME).read_text(encoding="utf-8", errors="replace"))
        dose = parse_dose((RAW / DOSE_NAME).read_text(encoding="utf-8"), unit, DOSE_NAME)
        self.assertEqual(unit, "uGy/hour")
        kept_dose = tuple(
            point
            for point in sorted(dose, key=lambda item: (item.when, item.product_id, item.source_file))
            if traced_point(point) and WINDOW_START <= point.when < WINDOW_END
        )
        self.assertEqual(report.dose, kept_dose)
        self.assertGreater(len(report.dose), 0)
        self.assertGreater(len(report.proton_gt10), 0)
        self.assertGreater(len(report.proton_gt100), 0)
        zeroed = assemble(
            alerts=alerts,
            proton_gt10=[Point(point.when, 0.0, point.unit, point.product_id, point.source_file) for point in gt10],
            proton_gt100=[Point(point.when, 0.0, point.unit, point.product_id, point.source_file) for point in gt100],
            dose=dose,
            window_start=WINDOW_START,
            window_end=WINDOW_END,
            storm="September 2017",
            active_region=report.active_region,
        )
        self.assertEqual([point.value for point in zeroed.dose], [point.value for point in report.dose])
        self.assertEqual(report.storm, "September 2017")
        self.assertEqual(report.active_region, "2673")
        self.assertEqual(report.window_start, WINDOW_START)
        self.assertEqual(report.window_end, WINDOW_END)
        self.assertIn("SWPC PRF 2193", report.text)
        self.assertIn("SWPC PRF 2194", report.text)
        self.assertIn("ZPGT10E", report.text)
        self.assertIn("ZPGT100E", report.text)
        self.assertIn("CRaTER-D1D2", report.text)
        self.assertIn("p/(cm^2 s sr)", report.text)
        self.assertIn("uGy/hour", report.text)
        self.assertIn(DOSE_NOT_FROM_FLUX, report.text)
        for sentence in report.sentences:
            self.assertIn("2017-09-04T00:00:00Z .. 2017-09-15T00:00:00Z", sentence)
        self.assertIn("1 pfu", report.sentences[0])
        self.assertIn("100 pfu", report.sentences[1])
        self.assertIn("Kp = 7", report.sentences[2])
        self.assertIn("2017-09-07T23:00:00Z", report.sentences[2])
        self.assertIn("2017-09-08T21:00:00Z", report.sentences[2])
        self.assertLess(report.sentences[2].index("2017-09-07T23:00:00Z"), report.sentences[2].index("2017-09-08T21:00:00Z"))
        joined = "\n".join(report.sentences)
        self.assertNotIn("99999", joined)
        render(report, OUT)
        try:
            self.assertEqual(read_method(OUT), report.method)
            self.assertIn(DOSE_NOT_FROM_FLUX, read_method(OUT))
            first = OUT.read_bytes()
            render(report, OUT)
            self.assertEqual(OUT.read_bytes(), first)
        finally:
            OUT.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
