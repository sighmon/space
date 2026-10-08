"""Synthetic rasters for the shipped query, cuts, and sheet renderer."""

from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

import numpy as np

from atlas.frame import assess_embedded_crs, assess_pds_label, illumination_transform, lonlat_to_xy, xy_to_lonlat
from atlas.sample import Grid, apply_stored_scale, query_point, sample_grid
from atlas.sheet import render_sheet

ROOT = Path(__file__).resolve().parents[1]
LABEL = (Path(__file__).resolve().parent / "fixtures" / "avgvisib_75s_excerpt.lbl").read_text()


def _grid(values, transform, resolution, usable=True, note="test frame", scale=1.0, offset=0.0, nodata=None, citation="test", label="test"):
    return Grid(
        values=np.asarray(values, dtype=np.float64),
        transform=transform,
        nodata=nodata,
        scale=scale,
        offset=offset,
        resolution_m=resolution,
        usable=usable,
        frame_note=note,
        citation=citation,
        value_label=label,
    )


class QueryTests(unittest.TestCase):
    def setUp(self):
        # 4 by 4 pixels, 10 m, origin at the upper-left corner of pixel (0, 0).
        self.transform = (10.0, 0.0, 0.0, 0.0, -10.0, 40.0)
        self.slope = _grid(
            [
                [1, 1, 1, 1],
                [1, 6, 1, 1],
                [1, 1, 1, 1],
                [1, 1, 1, 1],
            ],
            self.transform,
            10.0,
        )
        self.slope_rms = _grid(np.full((4, 4), 1.5), self.transform, 10.0)
        self.returns = _grid(
            [
                [4, 4, 4, 4],
                [4, 0, 4, 4],
                [4, 4, 4, 4],
                [4, 4, 4, 4],
            ],
            self.transform,
            10.0,
        )
        # Coarser 20 m sunlight / earth / shadow covering the same 40 m box.
        coarse = (20.0, 0.0, 0.0, 0.0, -20.0, 40.0)
        self.solar = _grid([[0.2, 0.2], [0.2, 0.2]], coarse, 20.0, scale=0.00004, offset=0.0)
        # 0.2 / 0.00004 = 5000 DN stored, so the grid holds DN and the scale produces 0.2.
        self.solar = _grid([[5000, 5000], [5000, 5000]], coarse, 20.0, scale=0.00004, offset=0.0)
        self.earth = _grid([[24750, 24750], [24750, 24750]], coarse, 20.0, scale=0.00004, offset=0.0)
        # Shadow only on the lower-right coarse pixel. Stored as the PDS DN for flag 1 and 0.
        # 1 = (DN * 0.000025) + 0.5 => DN = 20000; 0 => DN = -20000.
        self.shadow = _grid([[-20000, -20000], [-20000, 20000]], coarse, 20.0, scale=0.000025, offset=0.5)
        # Temperature is one 40 m pixel covering the whole box, so it is coarser than shadow.
        self.temperature = _grid([[100.0]], (40.0, 0.0, 0.0, 0.0, -40.0, 40.0), 40.0)

    def test_scale_and_five_fields_and_separate_cuts(self):
        self.assertEqual(apply_stored_scale(25000, 0.00004, 0.0), 1.0)
        # Pixel (1, 1) center is at x=15, y=25.
        x, y = 15.0, 25.0
        result = query_point(
            x,
            y,
            longitude_deg=36.917,
            latitude_deg=-85.295,
            extent="synthetic site",
            slope=self.slope,
            slope_rms=self.slope_rms,
            returns=self.returns,
            solar=self.solar,
            earth=self.earth,
            shadow=self.shadow,
            temperature=self.temperature,
        )
        self.assertEqual(result["slope_deg"], 6.0)
        self.assertEqual(result["slope_rms_deg"], 1.5)
        self.assertAlmostEqual(result["solar_fraction"], 0.2)
        self.assertAlmostEqual(result["earth_fraction"], 0.99)
        self.assertEqual(result["summer_max_temperature_k"], 100.0)
        self.assertEqual(result["temperature_resolution_m"], 40.0)
        self.assertIn("not as a 5 m", result["temperature_label"])
        self.assertIn("not a radio link budget", result["earth_label"])
        self.assertIn("Long-term average", result["solar_label"])
        self.assertFalse(result["permanent_shadow"])
        self.assertEqual(result["lola_return_count"], 0.0)
        self.assertTrue(result["interpolated_gap"])
        cuts = result["cuts"]
        self.assertFalse(cuts["slope_under_5_deg"])
        self.assertTrue(cuts["slope_under_8_deg"])
        self.assertFalse(cuts["average_sunlight_above_0_5"])
        self.assertTrue(cuts["earth_visibility_at_or_above_0_99"])
        self.assertTrue(cuts["earth_visibility_at_or_above_0_30"])
        self.assertTrue(cuts["temperature_below_110_k"])
        self.assertFalse(cuts["below_75_k_and_inside_permanent_shadow"])
        # Nearest cold shadow is the lower-right 20 m pixel, center (30, 10),
        # and the temperature sample there is 100 K, which is below 110 K.
        self.assertAlmostEqual(result["distance_to_cold_shadow_m"], math.hypot(30 - 15, 10 - 25))
        blob = json.dumps(result)
        for banned in ("habitability", "safety_score", "fused_score"):
            self.assertNotIn(banned, blob)
        self.assertNotIn("score", result)
        self.assertNotIn("score", result["cuts"])

    def test_unusable_frame_is_not_sampled(self):
        blocked = _grid([[9.0]], (1.0, 0.0, 0.0, 0.0, -1.0, 1.0), 1.0, usable=False, note="mismatch")
        self.assertIsNone(sample_grid(blocked, 0.5, 0.5))

    def test_no_cold_shadow_in_extent(self):
        warm = _grid([[200.0]], (40.0, 0.0, 0.0, 0.0, -40.0, 40.0), 40.0)
        result = query_point(
            15.0,
            25.0,
            longitude_deg=0.0,
            latitude_deg=-89.0,
            extent="synthetic site",
            slope=self.slope,
            slope_rms=self.slope_rms,
            returns=self.returns,
            solar=self.solar,
            earth=self.earth,
            shadow=self.shadow,
            temperature=warm,
        )
        self.assertIsNone(result["distance_to_cold_shadow_m"])
        self.assertIn("No permanently shadowed pixel", result["cold_shadow_note"])

    def test_projection_roundtrip_and_pole(self):
        self.assertEqual(lonlat_to_xy(0.0, -90.0), (0.0, 0.0))
        lon, lat = 36.917, -85.295
        x, y = lonlat_to_xy(lon, lat)
        back_lon, back_lat = xy_to_lonlat(x, y)
        self.assertAlmostEqual(back_lon, lon, places=6)
        self.assertAlmostEqual(back_lat, lat, places=6)

    def test_label_frame_and_rejected_crs(self):
        assessment = assess_pds_label(LABEL, 120.0)
        self.assertTrue(assessment.usable)
        self.assertIn("DE421", assessment.note)
        bad = assess_embedded_crs(
            'PROJCS["utm",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",0],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1]]',
            (120.0, 120.0),
            120.0,
        )
        self.assertFalse(bad.usable)
        missing = assess_embedded_crs(None, (5.0, 5.0), 5.0)
        self.assertFalse(missing.usable)
        transform = illumination_transform()
        # Pole sits on the corner between the four central pixels, not inside one of them.
        row, col = __import__("atlas.sample", fromlist=["rowcol_of_point"]).rowcol_of_point(transform, 0.0, 0.0)
        self.assertAlmostEqual(col, 3811.0, places=6)
        self.assertAlmostEqual(row, 3811.0, places=6)

    def test_sheet_has_more_than_one_band(self):
        out = Path(__file__).resolve().parents[1] / "output" / "synthetic-sheet.png"
        # Keep this out of the way of the real sheet; the test only needs the file it writes.
        out = Path(__file__).resolve().parent / "_synthetic_sheet.png"
        render_sheet(
            [
                ("sunlight", np.zeros((8, 8)), "sun"),
                ("temperature", np.ones((8, 8)), "temperature"),
            ],
            citations=["Barker et al. 2021", "Mazarico et al. 2011", "Williams et al. 2019"],
            notes=["cuts stay separate"],
            out_path=out,
            panel_px=32,
        )
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 500)
        from PIL import Image

        image = np.asarray(Image.open(out).convert("RGB"))
        colors = np.unique(image.reshape(-1, 3), axis=0)
        self.assertGreater(len(colors), 1)
        out.unlink()


if __name__ == "__main__":
    unittest.main()
