import json
import unittest
from pathlib import Path

import numpy as np

from atlas.compare import WUELLER_2026, RegionSpec, package_comparison, region_record
from atlas.export_web import _BANNED, _REGION_KEYS, _check, trim_comparison
from atlas.regions import REGIONS
from atlas.sample import Grid

WEB = Path(__file__).resolve().parents[1] / "web"


def _grid(value, res):
    return Grid(values=np.array([[value]], dtype=np.float64), transform=(res, 0.0, 0.0, 0.0, -res, res),
                nodata=None, scale=1.0, offset=0.0, resolution_m=res, usable=True, frame_note="t",
                citation="t", value_label="t")


def _synthetic_comparison():
    records = []
    for i in range(9):
        spec = RegionSpec(f"R{i}", f"P{i}", 1.0, -85.0, WUELLER_2026, None if i % 3 == 0 else "f", "src")
        has_slope = spec.slope_folder is not None
        records.append(region_record(
            spec, 1.0, 1.0,
            slope=_grid(3.0, 5.0) if has_slope else None, slope_rms=_grid(1.0, 5.0) if has_slope else None,
            returns=_grid(2.0, 5.0) if has_slope else None, solar=_grid(0.6, 120.0), earth=_grid(0.4, 120.0),
            shadow=_grid(0.0, 120.0), temperature=_grid(200.0, 240.0),
            cold_centers=np.array([[301.0, 401.0]]),
        ))
    return package_comparison(records)


class ExportGuardTest(unittest.TestCase):
    def test_rejects_combined_score_keys(self):
        for key in sorted(_BANNED):
            with self.assertRaises(RuntimeError, msg=key):
                _check({"a": {key: 1}})

    def test_rejects_nested_in_lists(self):
        with self.assertRaises(RuntimeError):
            _check({"regions": [{"rank": 1}]})

    def test_accepts_plain_values(self):
        _check({"query": {"slope_deg": 2.9}, "series": ["0101"]})


class RegionsExportTest(unittest.TestCase):
    def test_trim_keeps_nine_rows_nulls_and_distance(self):
        out = trim_comparison(_synthetic_comparison())
        self.assertEqual(len(out["regions"]), 9)
        for row in out["regions"]:
            self.assertEqual(set(row), set(_REGION_KEYS))
        missing = [r for r in out["regions"] if r["slope_deg"] is None]
        self.assertEqual(len(missing), 3)
        for row in missing:
            self.assertIsNone(row["lola_return_count"])
            self.assertIsNotNone(row["solar_fraction"])  # other layers survive a missing slope tile
        self.assertAlmostEqual(out["regions"][0]["distance_to_cold_shadow_m"], 500.0)
        json.dumps(out, allow_nan=False)

    def test_distance_is_none_without_centers(self):
        spec = RegionSpec("R", "P", 1.0, -85.0, WUELLER_2026, None, "src")
        rec = region_record(spec, 1.0, 1.0, slope=None, slope_rms=None, returns=None, solar=_grid(0.6, 120.0),
                            earth=_grid(0.4, 120.0), shadow=_grid(0.0, 120.0), temperature=_grid(200.0, 240.0))
        self.assertIsNone(rec["distance_to_cold_shadow_m"])


class CommittedWebDataTest(unittest.TestCase):
    """The committed web/data files, read as the page reads them. Skipped if not generated."""

    def setUp(self):
        path = WEB / "data" / "regions.json"
        if not path.is_file():
            self.skipTest("web/data/regions.json not generated")
        self.data = json.loads(path.read_text())

    def test_nine_regions_match_atlas_regions_and_page(self):
        points = [r["point_id"] for r in self.data["regions"]]
        self.assertEqual(points, [spec.point_id for spec in REGIONS])
        html = (WEB / "index.html").read_text()
        for point in points:
            self.assertIn(f"site:'{point}'", html)

    def test_no_verdict_keys_and_consistent_measures(self):
        _check(self.data)
        for row in self.data["regions"]:
            for key in ("solar_fraction", "earth_fraction"):
                self.assertTrue(0.0 <= row[key] <= 1.0, (row["point_id"], key))
            self.assertIn("18.6-year", row["solar_label"])
            self.assertIn("18.6-year", row["earth_label"])
            if row["slope_deg"] is None:
                self.assertIsNone(row["slope_rms_deg"])
                self.assertIsNone(row["lola_return_count"])

    def test_nr101_row_matches_nr101_export(self):
        nr = json.loads((WEB / "data" / "nr101.json").read_text())["query"]
        row = next(r for r in self.data["regions"] if r["point_id"] == "NR101")
        for key in ("slope_deg", "solar_fraction", "earth_fraction", "summer_max_temperature_k",
                    "distance_to_cold_shadow_m"):
            self.assertAlmostEqual(row[key], nr[key], places=6)

    def test_play_button_is_fixed_size_and_never_transformed(self):
        import re

        html = (WEB / "index.html").read_text()
        rule = re.search(r"\.play\{[^}]*\}", html).group(0)
        self.assertIn("width:38px", rule)
        self.assertIn("height:38px", rule)
        self.assertIn("flex:none", rule)
        for m in re.finditer(r"\.play[^{,]*(?::active|:hover|:focus[^{,]*)?\{([^}]*)\}", html):
            self.assertNotIn("scale", m.group(1))
            self.assertNotIn("translate", m.group(1))
            self.assertNotRegex(m.group(1), r"transform:(?!none)")
        self.assertRegex(html, r"\.rate\{[^}]*width:\d+px")  # label width cannot change with Playing/Paused

    def test_home_and_card_share_one_play_state(self):
        html = (WEB / "index.html").read_text()
        self.assertEqual(html.count('class="play js-play"'), 2)  # home control and card control
        self.assertIn('id="homectl"', html)
        self.assertIn("matchMedia('(prefers-reduced-motion: reduce)')", html)
        self.assertIn("setPlaying(!(REDUCED||qs.has('paused')))", html)
        self.assertIn("window.SUN_DATA", html)
        self.assertEqual(html.count("function setPlaying("), 1)

    def test_page_labels_every_zoom_source_and_no_nr101_only_claims(self):
        html = (WEB / "index.html").read_text()
        for needle in ("source_short", "source_pixel_m", "Real terrain ·", "LDEM_80S_20MPP_ADJ"):
            self.assertIn(needle, html)
        for stale in ("NR101 only", "only Site 06 (Nobile Rim 1) has been downloaded"):
            self.assertNotIn(stale, html)

    def test_page_has_no_example_data_generator(self):
        html = (WEB / "index.html").read_text()
        for needle in ("horizonFn", "EXNOTE", "14-day means", "placeholder generated"):
            self.assertNotIn(needle, html)


if __name__ == "__main__":
    unittest.main()
