"""The shipped assembly, on a small series and on the parsed frozen slice."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from power.assemble import NO_CONVERSION, NO_POWER, assemble, assemble_sol
from power.figure import read_method, render
from power.parse import OpacityPoint, Sample, diurnal_hours, parse_mcd_html, parse_opportunity, traced_opacity
from power.slice import DESIGN, OPACITY_LBL, OPACITY_TAB, RAW, build_report, build_sol


def _sample(**overrides) -> Sample:
    fields = dict(
        version="MCD_v6.2",
        scenario="warm scenario (dusty, maximum solar)",
        key="warm",
        ls=180.0,
        latitude=-1.95,
        longitude=354.47,
        site="Opportunity",
        local_time_h=12.0,
        altitude_m=0.0,
        flux=200.0,
        flux_unit="W/m2",
        opacity=1.0,
        opacity_unit="Monthly mean dust column visible optical depth above surface",
        source_file="mcd62_warm_ls180_opportunity.html",
    )
    fields.update(overrides)
    return Sample(**fields)


class AssemblyTests(unittest.TestCase):
    def test_deficit_is_stored_subtraction_and_untraced_values_drop(self):
        cold = _sample(
            scenario="cold scenario (low dust, minimum solar)",
            key="cold",
            flux=416.92514,
            opacity=0.0958612,
            source_file="mcd62_cold_ls180_opportunity.html",
        )
        warm = _sample(flux=250.5, opacity=1.2)
        storm = _sample(
            scenario="dust storm average solar scenario",
            key="storm",
            flux=174.24506,
            opacity=4.7392387,
            source_file="mcd62_storm_ls180_opportunity.html",
        )
        untraced = _sample(flux=99999.0, site="", source_file="", flux_unit="")
        changed = _sample(flux=250.5, opacity=9.5)
        opportunity = [
            OpacityPoint(187.9, 5105.610, 2.259, "PANCAM_R8_880NM atmospheric opacity", "1tau880_5106_20181207a.tab", "id-a"),
            OpacityPoint(180.0, 5100.0, 99999.0, "", "", ""),
        ]
        report = assemble(
            [storm, untraced, warm, cold],
            opportunity,
            month_degrees=30,
            storm_season="180 < Ls < 360",
        )
        same = assemble([changed, cold], opportunity, month_degrees=30, storm_season="180 < Ls < 360")
        warm_deficit = [item for item in report.deficits if item.scenario_key == "warm"]
        storm_deficit = [item for item in report.deficits if item.scenario_key == "storm"]
        self.assertEqual([item.value for item in warm_deficit], [250.5 - 416.92514])
        self.assertEqual([item.value for item in storm_deficit], [174.24506 - 416.92514])
        self.assertEqual(warm_deficit[0].unit, "W/m2")
        self.assertEqual([item.value for item in same.deficits], [item.value for item in warm_deficit])
        self.assertNotIn("99999", report.text)
        self.assertIn(NO_POWER, report.text)
        self.assertIn("negative on 1 of 1 shared seasonal samples", report.text)
        self.assertIn("Each database month covers 30 degrees of Ls.", report.text)
        self.assertIn("2.259", report.text)
        self.assertIn(NO_CONVERSION, report.text)
        self.assertIn("PANCAM_R8_880NM atmospheric opacity", report.text)
        self.assertIn("Monthly mean dust column visible optical depth above surface", report.text)
        self.assertEqual(report.opportunity[0].value, 2.259)
        self.assertEqual(report.storm_opacity[0].value, 4.7392387)

    def test_frozen_slice_matches_the_files(self):
        report = build_report()
        self.assertEqual(report.version, "MCD_v6.2")
        self.assertIn(NO_POWER, report.text)
        self.assertIn("cold scenario (low dust, minimum solar)", report.text)
        self.assertIn("warm scenario (dusty, maximum solar)", report.text)
        self.assertIn("dust storm average solar scenario", report.text)
        self.assertIn("climatology average solar scenario", report.text)
        for site in (
            "Deuteronilus Mensae",
            "Protonilus Mensae",
            "Mesopotamia",
            "Curiosity",
            "Perseverance",
            "Opportunity",
        ):
            self.assertIn(site, report.text)
        self.assertIn("shared seasonal samples", report.text)
        self.assertIn("180 < Ls < 360", report.text)
        self.assertIn(NO_CONVERSION, report.text)
        self.assertTrue(report.deficits)
        item = report.deficits[0]
        dusty = parse_mcd_html((RAW / item.dusty_file).read_text(encoding="utf-8"), item.dusty_file)
        baseline = parse_mcd_html((RAW / item.baseline_file).read_text(encoding="utf-8"), item.baseline_file)
        self.assertIsNotNone(dusty)
        self.assertIsNotNone(baseline)
        self.assertEqual(item.value, dusty.flux - baseline.flux)
        self.assertEqual(item.unit, dusty.flux_unit)
        self.assertEqual(item.unit, "W/m2")
        copied = parse_opportunity(
            (RAW / OPACITY_TAB).read_text(encoding="utf-8", errors="replace"),
            (RAW / OPACITY_LBL).read_text(encoding="utf-8", errors="replace"),
            OPACITY_TAB,
        )
        traced = [point for point in copied if traced_opacity(point)]
        self.assertEqual(
            [(point.sol, point.ls, point.value, point.product_id) for point in report.opportunity],
            [(point.sol, point.ls, point.value, point.product_id) for point in traced],
        )
        self.assertTrue(report.opportunity)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "figure.png"
            render(report, path)
            self.assertEqual(read_method(path), report.method)


class SolTests(unittest.TestCase):
    def test_printed_midnight_is_kept_and_untraced_hours_drop(self):
        hours = tuple(range(2, 26, 2))

        def at(key, hour, flux, source):
            scenario = {
                "cold": "cold scenario (low dust, minimum solar)",
                "warm": "warm scenario (dusty, maximum solar)",
                "storm": "dust storm average solar scenario",
            }[key]
            return _sample(
                scenario=scenario,
                key=key,
                ls=270.0,
                latitude=-35.352,
                longitude=94.02,
                site="Mesopotamia",
                local_time_h=float(hour),
                flux=flux,
                source_file=source,
            )

        sol = assemble_sol(
            [
                at("cold", 12, 10.0, "mcd62_cold_ls270_lt12_mesopotamia.html"),
                at("warm", 12, 4.0, "mcd62_warm_ls270_lt12_mesopotamia.html"),
                at("cold", 0, 0.0, "mcd62_cold_ls270_lt24_mesopotamia.html"),
                at("warm", 0, 0.0, "mcd62_warm_ls270_lt24_mesopotamia.html"),
                at("cold", 0, 5.0, "mcd62_cold_ls270_lt00_mesopotamia.html"),
                at("warm", 3, 99999.0, "mcd62_warm_ls270_lt03_mesopotamia.html"),
                _sample(flux=99999.0, site="", source_file="", flux_unit="", local_time_h=12.0),
            ],
            hours,
        )
        warm = [item for item in sol.deficits if item.scenario_key == "warm"]
        self.assertEqual(sol.hours, (0, 12))
        self.assertEqual([item.value for item in warm], [0.0, 4.0 - 10.0])
        self.assertNotIn("99999", sol.text)
        self.assertNotIn("lt00", sol.text)
        self.assertNotIn("lt03", sol.text)
        self.assertIn(NO_POWER, sol.text)
        self.assertIn("printed by the interface as local time 0.0", sol.text)
        self.assertIn("negative on 1 of 2 stored local-time samples", sol.text)
        self.assertIn("local true solar time at the site", sol.method)
        self.assertIn("Mars Universal Time", sol.method)
        self.assertIn("linear interpolation between stored Martian hours", sol.method)
        self.assertIn("How long the deficit lasts is a count of these stored local-time samples.", sol.method)

    def test_frozen_sol_matches_the_seasonal_noon(self):
        report = build_report()
        sol = build_sol(report)
        self.assertEqual(sol.site, "Mesopotamia")
        self.assertEqual(int(sol.ls), 270)
        self.assertEqual(sol.hours, (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22))
        self.assertEqual(len(sol.deficits), 24)
        self.assertEqual(len(report.deficits), 108)
        self.assertIn(NO_POWER, sol.text)
        self.assertIn("negative on 7 of 12 stored local-time samples", sol.text)
        for label in ("cold", "warm", "dust-storm"):
            self.assertIn(
                f"{label} incident flux is above zero on 7 of 12 stored local-time samples.",
                sol.text,
            )
        noon_storm = next(item for item in sol.deficits if item.scenario_key == "storm" and item.local_time_h == 12)
        seasonal = next(
            item for item in report.deficits
            if item.site == "Mesopotamia" and item.scenario_key == "storm" and int(item.ls) == 270
        )
        self.assertEqual(noon_storm.value, seasonal.value)
        self.assertAlmostEqual(noon_storm.value, -537.81713, places=4)
        for key in ("cold", "warm", "storm"):
            name = f"mcd62_{key}_ls270_mesopotamia.html"
            parsed = parse_mcd_html((RAW / name).read_text(encoding="utf-8"), name)
            self.assertIsNotNone(parsed)
            if key == "cold":
                self.assertEqual(noon_storm.baseline_flux, parsed.flux)
                self.assertEqual(noon_storm.baseline_file, "mcd62_cold_ls270_lt12_mesopotamia.html")
            else:
                item = next(d for d in sol.deficits if d.scenario_key == key and d.local_time_h == 12)
                self.assertEqual(item.dusty_flux, parsed.flux)
                self.assertEqual(item.value, item.dusty_flux - item.baseline_flux)
                self.assertEqual(item.baseline_file, noon_storm.baseline_file)
        for item in sol.deficits:
            self.assertEqual(item.value, item.dusty_flux - item.baseline_flux)
            self.assertNotIn("99999", item.dusty_file)
        self.assertEqual(diurnal_hours((RAW / DESIGN).read_bytes()), tuple(range(2, 26, 2)))
        self.assertIsNone(diurnal_hours(b"no stored clock in this file"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "figure.png"
            render(report, path, sol)
            traced = read_method(path)
            self.assertIn(report.method, traced)
            self.assertIn(sol.method, traced)
            render(report, path)
            self.assertEqual(read_method(path), report.method)


if __name__ == "__main__":
    unittest.main()
