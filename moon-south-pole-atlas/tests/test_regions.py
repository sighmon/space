"""Synthetic grids for the nine-region comparison. No rasters and no network."""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from atlas.compare import CAVEATS, RegionSpec, WUELLER_2026, package_comparison, region_record
from atlas.compare_sheet import render_comparison, row_mark_center
from atlas.regions import REGIONS
from atlas.sample import EARTH_LABEL, SOLAR_LABEL, TEMPERATURE_LABEL, Grid

OUT = Path(__file__).resolve().parent / "_synthetic_regions.png"


def _grid(values, transform, resolution, usable=True, note="test frame"):
    return Grid(
        values=np.asarray(values, dtype=np.float64),
        transform=transform,
        nodata=None,
        scale=1.0,
        offset=0.0,
        resolution_m=resolution,
        usable=usable,
        frame_note=note,
        citation="test",
        value_label="test",
    )


def _spec(region: str, point_id: str, source: str, folder: str | None = "synthetic") -> RegionSpec:
    return RegionSpec(
        region=region,
        point_id=point_id,
        longitude_deg=10.0,
        latitude_deg=-85.0,
        point_citation=WUELLER_2026,
        slope_folder=folder,
        slope_source=source,
    )


class RegionComparisonTests(unittest.TestCase):
    def setUp(self):
        # One pixel covering the origin. Slope at 5 m, sun and Earth at 120 m, temperature at 240 m.
        self.slope = _grid([[3.0]], (5.0, 0.0, 0.0, 0.0, -5.0, 5.0), 5.0, note="slope test map")
        self.slope_rms = _grid([[1.0]], (5.0, 0.0, 0.0, 0.0, -5.0, 5.0), 5.0, note="slope rms test map")
        self.returns = _grid([[4.0]], (5.0, 0.0, 0.0, 0.0, -5.0, 5.0), 5.0, note="return test map")
        self.solar = _grid([[0.6]], (120.0, 0.0, 0.0, 0.0, -120.0, 120.0), 120.0, note="sun test map")
        self.earth = _grid([[0.4]], (120.0, 0.0, 0.0, 0.0, -120.0, 120.0), 120.0, note="earth test map")
        self.shadow = _grid([[0.0]], (120.0, 0.0, 0.0, 0.0, -120.0, 120.0), 120.0, note="shadow test map")
        self.temperature = _grid([[200.0]], (240.0, 0.0, 0.0, 0.0, -240.0, 240.0), 240.0, note="temperature test map")

    def _record(self, spec: RegionSpec, **overrides):
        layers = {
            "slope": self.slope,
            "slope_rms": self.slope_rms,
            "returns": self.returns,
            "solar": self.solar,
            "earth": self.earth,
            "shadow": self.shadow,
            "temperature": self.temperature,
        }
        layers.update(overrides)
        return region_record(spec, 1.0, 1.0, **layers)

    def test_nine_records_keep_fields_cuts_and_pixel_labels(self):
        names = [
            "Peak near Cabeus B",
            "Haworth",
            "Malapert Massif",
            "Mons Mouton Plateau",
            "Mons Mouton",
            "Nobile Rim 1",
            "Nobile Rim 2",
            "de Gerlache Rim 2",
            "Slater Plain",
        ]
        records = []
        for index, name in enumerate(names):
            if index == 0:
                records.append(
                    self._record(
                        _spec(name, f"P{index}", "no product-78 file", folder=None),
                        slope=None,
                        slope_rms=None,
                        returns=None,
                    )
                )
            else:
                records.append(self._record(_spec(name, f"P{index}", "synthetic 5 m tile")))
        comparison = package_comparison(records)
        self.assertEqual([row["region"] for row in comparison["regions"]], names)
        self.assertEqual(len(comparison["caveats"]), 4)
        for phrase in CAVEATS:
            self.assertIn(phrase, comparison["caveats"])
        self.assertIn("18.6-year", comparison["timeline_note"])
        self.assertIn("hourly", comparison["timeline_note"])
        missing = comparison["regions"][0]
        self.assertIsNone(missing["slope_deg"])
        self.assertIsNone(missing["slope_rms_deg"])
        self.assertIsNone(missing["lola_return_count"])
        self.assertIsNone(missing["interpolated_gap"])
        self.assertIsNone(missing["slope_pixel_label"])
        self.assertIsNone(missing["cuts"]["slope_under_5_deg"])
        self.assertIsNot(missing["cuts"]["slope_under_5_deg"], False)
        present = comparison["regions"][1]
        for key in (
            "slope_deg",
            "slope_rms_deg",
            "solar_fraction",
            "earth_fraction",
            "summer_max_temperature_k",
            "permanent_shadow",
            "lola_return_count",
        ):
            self.assertIn(key, present)
        self.assertEqual(present["slope_pixel_label"], "5.0000 m")
        self.assertEqual(present["solar_pixel_label"], "120.0000 m")
        self.assertEqual(present["earth_pixel_label"], "120.0000 m")
        self.assertEqual(present["temperature_pixel_label"], "240.0000 m")
        self.assertNotEqual(present["slope_pixel_label"], present["solar_pixel_label"])
        self.assertNotEqual(present["solar_pixel_label"], present["temperature_pixel_label"])
        self.assertEqual(present["slope_dem_label"], "5.0000 m LOLA site DEM")
        self.assertNotIn("not the 5 m site DEM", present["slope_dem_label"])
        self.assertIn("18.6-year", present["solar_label"])
        self.assertIn("Long-term average", present["solar_label"])
        self.assertEqual(present["solar_label"], SOLAR_LABEL)
        self.assertIn("not a radio link budget", present["earth_label"])
        self.assertEqual(present["earth_label"], EARTH_LABEL)
        self.assertIn("not as a 5 m", present["temperature_label"])
        self.assertEqual(present["temperature_label"], TEMPERATURE_LABEL)
        self.assertEqual(present["slope_map"], "slope test map")
        self.assertEqual(present["temperature_map"], "temperature test map")
        self.assertFalse(present["permanent_shadow"])
        self.assertIs(present["cuts"]["slope_under_5_deg"], True)
        self.assertIs(present["cuts"]["average_sunlight_above_0_5"], True)
        self.assertIs(present["cuts"]["earth_visibility_at_or_above_0_99"], False)
        self.assertIn("distance_to_cold_shadow_m", present)
        self.assertIsNone(present["distance_to_cold_shadow_m"])  # no cold-shadow centers were passed
        for banned in ("habitability", "safety", "score", "fused_score", "rank", "ranking"):
            self.assertNotIn(banned, comparison)
            self.assertNotIn(banned, present)
            self.assertNotIn(banned, present["cuts"])

    def test_coarser_slope_is_not_called_a_5m_site_dem(self):
        coarse = _grid([[2.0]], (20.0, 0.0, 0.0, 0.0, -20.0, 20.0), 20.0, note="20 m mosaic")
        record = self._record(
            _spec("Example", "EX1", "20 m mosaic, not a site DEM"),
            slope=coarse,
            slope_rms=coarse,
            returns=coarse,
        )
        self.assertEqual(record["slope_pixel_label"], "20.0000 m")
        self.assertIn("not the 5 m site DEM", record["slope_dem_label"])
        self.assertNotIn("5 m LOLA site DEM", record["slope_dem_label"])

    def test_missing_shadow_is_not_false(self):
        record = self._record(_spec("Example", "EX1", "synthetic"), shadow=None, temperature=None)
        self.assertIsNone(record["permanent_shadow"])
        self.assertIsNone(record["summer_max_temperature_k"])
        self.assertIsNone(record["cuts"]["temperature_below_110_k"])
        self.assertIsNone(record["cuts"]["below_75_k_and_inside_permanent_shadow"])
        self.assertIsNot(record["permanent_shadow"], False)

    def test_ranking_key_is_refused(self):
        records = [self._record(_spec(f"Region {i}", f"P{i}", "synthetic")) for i in range(9)]
        records[3]["ranking"] = 1
        with self.assertRaises(RuntimeError):
            package_comparison(records)

    def test_catalog_names_one_published_point_and_missing_files(self):
        self.assertEqual(
            [spec.point_id for spec in REGIONS],
            ["PCB01", "HW01", "MMA01", "MMP01", "MMO01", "NR101", "NR201", "dGR101", "SP01"],
        )
        self.assertEqual(
            [spec.region for spec in REGIONS],
            [
                "Peak near Cabeus B",
                "Haworth",
                "Malapert Massif",
                "Mons Mouton Plateau",
                "Mons Mouton",
                "Nobile Rim 1",
                "Nobile Rim 2",
                "de Gerlache Rim 2",
                "Slater Plain",
            ],
        )
        nr101 = next(spec for spec in REGIONS if spec.point_id == "NR101")
        self.assertEqual(nr101.longitude_deg, 36.917)
        self.assertEqual(nr101.latitude_deg, -85.295)
        self.assertEqual(nr101.slope_folder, "Site06")
        for spec in REGIONS:
            self.assertIn("10.1029/2025JE009434", spec.point_citation)
        missing = {spec.point_id: spec for spec in REGIONS if spec.slope_folder is None}
        self.assertEqual(set(missing), {"PCB01", "MMP01", "SP01"})
        for spec in missing.values():
            self.assertIn("missing", spec.slope_source)
            self.assertIn("20 m mosaic is not used", spec.slope_source)
        self.assertIn("Site 20", missing["MMP01"].slope_source)
        self.assertIn("does not contain MMP01", missing["MMP01"].slope_source)
        mouton = next(spec for spec in REGIONS if spec.point_id == "MMO01")
        self.assertEqual(mouton.slope_folder, "Site20")
        self.assertIn("not a Mons Mouton Plateau DEM", mouton.slope_source)
        gerlache = next(spec for spec in REGIONS if spec.point_id == "dGR101")
        self.assertEqual(gerlache.slope_folder, "SL2")
        self.assertIn("not Site 11", gerlache.slope_source)

    def test_renderer_shows_more_than_one_region_and_the_caveats(self):
        records = [
            self._record(_spec("Haworth", "HW01", "synthetic haworth")),
            self._record(_spec("Slater Plain", "SP01", "no product-78 file", folder=None), slope=None, slope_rms=None, returns=None),
        ]
        comparison = {
            "frame": "South-polar stereographic test frame.",
            "extent": "USGS region polygons were not applied.",
            "timeline_note": "18.6-year averages, not the NR101 hourly timeline.",
            "caveats": list(CAVEATS),
            "sources": [
                {"layer": "slope", "citation": "Barker et al. 2021", "pixel": "5 m or missing"},
            ],
            "regions": records,
        }
        render_comparison(comparison, OUT)
        self.assertGreater(OUT.stat().st_size, 500)
        image = Image.open(OUT)
        self.assertGreater(image.size[1], 100)
        first = image.getpixel(row_mark_center(0))
        second = image.getpixel(row_mark_center(1))
        self.assertNotEqual(first, second)
        self.assertNotEqual(first, (16, 18, 22))
        note = image.text["method"]
        for phrase in CAVEATS:
            self.assertIn(phrase, note)
        self.assertIn("Haworth", note)
        self.assertIn("Slater Plain", note)
        image.close()
        OUT.unlink()


if __name__ == "__main__":
    unittest.main()
