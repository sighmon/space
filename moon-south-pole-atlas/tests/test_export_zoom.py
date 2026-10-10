import json
import math
import unittest
from pathlib import Path

import numpy as np

from atlas.export_zoom import (DEM_N, DEM_SOURCES, HOURS, _BANNED, _check, decode_heights, encode_heights,
                               local_axes_in_grid, north_up_offsets, read_dem, sun_azel, terrain_strips)
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

    def test_every_region_has_a_labelled_dem_and_a_map_crop(self):
        self.assertEqual(sorted(self.zoom["dem"]), sorted(r.point_id for r in REGIONS))
        for pid, rec in self.zoom["dem"].items():
            spec = DEM_SOURCES[pid]
            self.assertEqual(rec["source_pixel_m"], spec["source_pixel_m"], pid)
            self.assertEqual(rec["file"], spec["file"], pid)
            self.assertAlmostEqual(rec["extent_m"], rec["n"] * rec["pixel_m"])
            self.assertGreaterEqual(rec["pixel_m"], rec["source_pixel_m"], pid)  # never finer than the source
            self.assertIn(str(int(rec["source_pixel_m"])) + " m", rec["source_short"])
            h = decode_heights(rec, rec["n"])
            self.assertAlmostEqual(float(h.max() - h.min()), rec["relief_m"], delta=2 * rec["step_m"] + 1e-6)
            self.assertGreater(rec["relief_m"], 50.0, pid)  # real relief, not a flat fill
        for r in REGIONS:
            self.assertTrue((WEB.parent / self.zoom["map"]["crops"][r.point_id]["file"]).is_file(), r.point_id)
        # 5 m for seven regions (six site DEMs + the 87-90S mosaic for Slater Plain); 20 m polar DEM windows for the other two
        self.assertEqual(sorted(p for p, d in self.zoom["dem"].items() if d["source_pixel_m"] == 20.0), ["MMP01", "PCB01"])

    def test_strips_for_every_region_but_nr101(self):
        self.assertEqual(sorted(self.zoom["strips"]), sorted(r.point_id for r in REGIONS if r.point_id != "NR101"))
        for pid, st in self.zoom["strips"].items():
            for key in ("sun_1m", "sun_5m", "earth_1m", "earth_5m"):
                self.assertEqual(len(st[key]), HOURS, (pid, key))
                self.assertTrue(set(st[key]) <= {"0", "1"})
            self.assertIn("m elevation", st["source"])
            self.assertGreater(st["reach_m"], 3000.0)
        home = self.sun["home"]
        self.assertEqual(len(home["longitude_deg_x10"]), HOURS)
        self.assertTrue(all(abs(v) < 120 for v in home["elevation_deg_x10"]))

    @unittest.skipUnless(all((ROOT / "data" / "raw" / s["file"]).is_file() for s in DEM_SOURCES.values()), "DEM rasters not on disk")
    def test_chip_centre_matches_raster_at_the_point(self):
        for r in REGIONS:
            spec, rec = DEM_SOURCES[r.point_id], self.zoom["dem"][r.point_id]
            arr, t = read_dem(ROOT / "data" / "raw", spec["file"])
            x, y = lonlat_to_xy(r.longitude_deg, r.latitude_deg)
            col, row = (x - t.c) / t.a - 0.5, (y - t.f) / t.e - 0.5
            c0, r0 = int(col), int(row)
            local = arr[r0 - 3:r0 + 5, c0 - 3:c0 + 5]  # a few source pixels around the point
            h = decode_heights(rec, rec["n"])[rec["n"] // 2 - 1:rec["n"] // 2 + 1, rec["n"] // 2 - 1:rec["n"] // 2 + 1]
            self.assertGreaterEqual(float(h.min()), float(local.min()) - 1.0, r.point_id)
            self.assertLessEqual(float(h.max()), float(local.max()) + 1.0, r.point_id)

    @unittest.skipUnless((KERNELS / "de421.bsp").is_file() and (ROOT / "data" / "raw" / DEM_SOURCES["SP01"]["file"]).is_file(), "kernels or SP01 DEM not on disk")
    def test_sp01_strips_recompute_identically(self):
        from datetime import datetime, timezone

        from atlas.ephemeris import moon_centered_vectors_m, utc_hours

        hours = utc_hours(datetime(2025, 1, 1, tzinfo=timezone.utc), HOURS)
        v = moon_centered_vectors_m(KERNELS, hours)
        r = next(x for x in REGIONS if x.point_id == "SP01")
        again = terrain_strips(ROOT / "data" / "raw", "SP01", r.longitude_deg, r.latitude_deg, v["sun"], v["earth"])
        for key in ("sun_1m", "sun_5m", "earth_1m", "earth_5m"):
            self.assertEqual(again[key], self.zoom["strips"]["SP01"][key], key)
        # the Sun strip at the pole map-angle export matches the same vectors
        lon = np.degrees(np.arctan2(v["sun"][:, 1], v["sun"][:, 0])) % 360
        got = np.array(self.sun["home"]["longitude_deg_x10"]) / 10
        d = (got - lon + 180) % 360 - 180
        self.assertLess(float(np.abs(d).max()), 0.06)

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
