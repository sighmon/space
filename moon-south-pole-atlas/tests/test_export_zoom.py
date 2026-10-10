import json
import math
import unittest
from pathlib import Path

import numpy as np

from atlas.export_zoom import (DEM_N, HOURS, _BANNED, _check, decode_heights, encode_heights,
                               local_axes_in_grid, north_up_offsets, sun_azel)
from atlas.frame import RADIUS_M, lonlat_to_xy
from atlas.horizon import enu_axes, position_xyz
from atlas.regions import REGIONS

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "data"
KERNELS = ROOT / "data" / "raw" / "kernels"


class SunAzElTest(unittest.TestCase):
    def test_cardinal_directions(self):
        lon, lat = 36.917, -85.295
        east, north, up = enu_axes(lon, lat)
        obs = position_xyz(lon, lat, RADIUS_M)
        d = 1.496e11
        for vec, az, el in ((north, 0, 0), (east, 90, 0), (-north, 180, 0), (-east, 270, 0), (up, None, 90)):
            a, e = sun_azel(lon, lat, (obs + vec * d)[None, :])
            self.assertAlmostEqual(float(e[0]), el, delta=0.01)
            if az is not None:
                self.assertAlmostEqual(float(a[0]), az, delta=0.01)


class ChipFrameTest(unittest.TestCase):
    def test_north_is_radially_outward_and_axes_are_orthogonal(self):
        for r in REGIONS:
            (ex, ey), (nx, ny) = local_axes_in_grid(r.longitude_deg, r.latitude_deg)
            x, y = lonlat_to_xy(r.longitude_deg, r.latitude_deg)
            rad = (x / math.hypot(x, y), y / math.hypot(x, y))
            self.assertGreater(nx * rad[0] + ny * rad[1], 0.999 * math.hypot(nx, ny))  # north points away from the south pole
            self.assertLess(abs(ex * nx + ey * ny) / (math.hypot(ex, ey) * math.hypot(nx, ny)), 0.01)
            self.assertAlmostEqual(math.hypot(nx, ny), 1.0, delta=0.01)  # polar stereographic scale near 1 within 5 deg of the pole

    def test_offsets_run_north_to_south(self):
        e, n = north_up_offsets(4, 10.0)
        self.assertGreater(n[0, 0], n[-1, 0])
        self.assertLess(e[0, 0], e[0, -1])

    def test_height_roundtrip(self):
        h = np.random.default_rng(1).uniform(6300, 6800, (DEM_N, DEM_N))
        rec = encode_heights(h)
        rec.pop("_q")
        back = decode_heights(rec, DEM_N)
        self.assertLess(float(np.abs(back - h).max()), rec["step_m"])
        self.assertLess(rec["step_m"], 0.01)


class ExportGuardTest(unittest.TestCase):
    def test_banned_keys_rejected(self):
        for key in sorted(_BANNED):
            with self.assertRaises(ValueError, msg=key):
                _check({"a": [{key: 1}]})


@unittest.skipUnless((WEB / "sun.json").is_file() and (WEB / "zoom.json").is_file(), "run python -m atlas.export_zoom first")
class ExportedDataTest(unittest.TestCase):
    def setUp(self):
        self.sun = json.loads((WEB / "sun.json").read_text())
        self.zoom = json.loads((WEB / "zoom.json").read_text())

    def test_nine_points_full_series(self):
        self.assertEqual(sorted(self.sun["points"]), sorted(r.point_id for r in REGIONS))
        self.assertEqual(self.sun["ephemeris"], "DE421")
        for pid, p in self.sun["points"].items():
            self.assertEqual(len(p["azimuth_deg_x10"]), HOURS, pid)
            self.assertEqual(len(p["elevation_deg_x10"]), HOURS, pid)
            self.assertTrue(all(0 <= v < 3600 for v in p["azimuth_deg_x10"]))
            self.assertTrue(all(abs(v) < 120 for v in p["elevation_deg_x10"]), pid)  # within 12 deg of horizontal near the pole

    def test_no_verdict_keys_anywhere(self):
        _check(self.sun)
        _check(self.zoom)

    def test_dem_only_for_nr101_and_map_crop_for_all(self):
        self.assertEqual(list(self.zoom["dem"]), ["NR101"])
        rec = self.zoom["dem"]["NR101"]
        h = decode_heights(rec, rec["n"])
        self.assertAlmostEqual(float(h.max() - h.min()), rec["relief_m"], delta=2 * rec["step_m"] + 1e-6)
        for r in REGIONS:
            self.assertTrue((WEB.parent / self.zoom["map"]["crops"][r.point_id]["file"]).is_file(), r.point_id)

    @unittest.skipUnless((KERNELS / "de421.bsp").is_file(), "kernels not on disk")
    def test_nr101_matches_recomputed_ephemeris(self):
        from datetime import datetime, timezone

        from atlas.ephemeris import moon_centered_vectors_m, utc_hours

        hours = utc_hours(datetime(2025, 1, 1, tzinfo=timezone.utc), HOURS)
        sun = moon_centered_vectors_m(KERNELS, hours)["sun"]
        r = next(x for x in REGIONS if x.point_id == "NR101")
        az, el = sun_azel(r.longitude_deg, r.latitude_deg, sun)
        p = self.sun["points"]["NR101"]
        self.assertLess(float(np.abs(np.array(p["elevation_deg_x10"]) / 10 - el).max()), 0.06)
        d = (np.array(p["azimuth_deg_x10"]) / 10 - az + 180) % 360 - 180
        self.assertLess(float(np.abs(d).max()), 0.06)


if __name__ == "__main__":
    unittest.main()
