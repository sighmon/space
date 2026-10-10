"""Synthetic horizon, disc visibility, and the fourteen-day timeline renderer."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from atlas.frame import RADIUS_M, lonlat_to_xy, xy_to_lonlat, xy_to_lonlat_array
from atlas.horizon import (
    EARTH_EQUATORIAL_RADIUS_M,
    SUN_RADIUS_M,
    angular_radius_rad,
    bin_center_azimuth,
    disc_above_horizon,
    enu_axes,
    horizon_from_elevation,
    horizontal_direction,
    position_xyz,
    terrain_horizon,
    topocentric,
    visibility_mask,
)
from atlas.sample import EARTH_LABEL, SOLAR_LABEL
from atlas.timeline import package_timeline
from atlas.timeline_sheet import note_lines, render_timeline, sample_origin, series_colors


class HorizonTests(unittest.TestCase):
    def test_array_inverse_matches_the_project_frame(self):
        for longitude, latitude in ((0.0, -90.0), (36.917, -85.295), (90.0, -80.0), (-45.0, -86.0)):
            x, y = lonlat_to_xy(longitude, latitude)
            lon, lat = xy_to_lonlat_array(x, y)
            expected_lon, expected_lat = xy_to_lonlat(x, y)
            self.assertAlmostEqual(float(lon), expected_lon, places=9)
            self.assertAlmostEqual(float(lat), expected_lat, places=9)

    def test_curvature_puts_a_distant_surface_point_below_the_horizontal(self):
        observer = position_xyz(0.0, -85.0, RADIUS_M + 1.0)
        east, north, _up = enu_axes(0.0, -85.0)
        target = position_xyz(0.0, -83.0, RADIUS_M)
        altitude, _azimuth, _distance = topocentric(observer, east, north, target)
        self.assertLess(altitude, 0.0)

    def test_terrain_hides_a_disc_whose_center_is_above_a_flat_horizon(self):
        longitude, latitude = 36.917, -85.295
        observer = position_xyz(longitude, latitude, RADIUS_M + 1.0)
        east, north, up = enu_axes(longitude, latitude)
        ridge = observer + north * 1000.0 + up * 250.0
        horizon = terrain_horizon(observer, ridge, east, north, n_bins=360, min_horizontal_m=0.0)
        body = observer + north * 1.0e8 + up * 1.0e6
        altitude, azimuth, distance = topocentric(observer, east, north, body)
        angular = float(angular_radius_rad(distance, 1.0e5))
        self.assertGreater(altitude, 0.0)
        bin_index = int(azimuth * 360 / (2.0 * np.pi))
        self.assertGreater(horizon[bin_index], altitude + angular)
        self.assertFalse(disc_above_horizon(altitude, angular, horizon[bin_index]))
        self.assertTrue(disc_above_horizon(altitude, angular, 0.0))
        hidden = visibility_mask(observer, east, north, body, 1.0e5, horizon)
        self.assertFalse(bool(hidden[0]))

    def test_one_meter_and_five_meter_horizons_disagree(self):
        longitude, latitude = 36.917, -85.295
        x, y = lonlat_to_xy(longitude, latitude)
        transform = (5.0, 0.0, x - 12.5, 0.0, -5.0, y + 12.5)
        elevation = np.zeros((5, 5), dtype=np.float64)
        elevation[2, 3] = 3.0
        horizon_1m = horizon_from_elevation(
            elevation, transform, observer_x_m=x, observer_y_m=y, surface_elevation_m=0.0, height_m=1.0, n_bins=360
        )
        horizon_5m = horizon_from_elevation(
            elevation, transform, observer_x_m=x, observer_y_m=y, surface_elevation_m=0.0, height_m=5.0, n_bins=360
        )
        ridge_bin = int(np.argmax(horizon_1m))
        self.assertGreater(horizon_1m[ridge_bin], 0.0)
        self.assertLess(horizon_5m[ridge_bin], 0.0)
        east, north, up = enu_axes(longitude, latitude)
        direction = horizontal_direction(east, north, bin_center_azimuth(ridge_bin, horizon_1m.size))
        eye = position_xyz(longitude, latitude, RADIUS_M + 1.0)
        body = eye + direction * 1.0e8 + up * 2.0e5
        sun_1m = visibility_mask(eye, east, north, body, 1.0e3, horizon_1m)
        eye_5 = position_xyz(longitude, latitude, RADIUS_M + 5.0)
        sun_5m = visibility_mask(eye_5, east, north, body, 1.0e3, horizon_5m)
        self.assertFalse(bool(sun_1m[0]))
        self.assertTrue(bool(sun_5m[0]))
        earth = body + east * 1.0e6
        earth_1m = visibility_mask(eye, east, north, earth, EARTH_EQUATORIAL_RADIUS_M, horizon_1m)
        self.assertTrue(bool(sun_1m[0]) is False)
        self.assertIsInstance(bool(earth_1m[0]), bool)

    def test_sun_and_earth_stay_separate_and_unscored(self):
        count_14 = 14 * 24
        count_30 = 30 * 24
        sun_1m = [True, False] * (count_30 // 2)
        sun_5m = [False] * count_30
        sun_5m[0] = True
        earth_1m = [False, True] * (count_30 // 2)
        earth_5m = [True] * count_30
        series = {}
        for key, days in (("fourteen_earth_days", 14), ("thirty_earth_days", 30)):
            count = days * 24
            series[key] = {
                "sun_1m": sun_1m[:count],
                "sun_5m": sun_5m[:count],
                "earth_1m": earth_1m[:count],
                "earth_5m": earth_5m[:count],
            }
        result = package_timeline(
            series,
            longitude_deg=36.917,
            latitude_deg=-85.295,
            easting_m=1.0,
            northing_m=2.0,
            surface_elevation_m=3.0,
            elevation_frame="synthetic",
            solar_fraction=0.25,
            earth_fraction=0.5,
        )
        self.assertNotIn("score", result)
        self.assertNotIn("habitability", result)
        self.assertNotIn("safety", result)
        window = result["windows"]["fourteen_earth_days"]
        self.assertEqual(set(window), {"sun_1m", "sun_5m", "earth_1m", "earth_5m"})
        self.assertEqual(window["sun_1m"]["observer_height_m"], 1)
        self.assertEqual(window["sun_5m"]["observer_height_m"], 5)
        self.assertEqual(window["sun_1m"]["visible"], sun_1m[:count_14])
        self.assertNotEqual(window["sun_1m"]["visible"], window["sun_5m"]["visible"])
        self.assertNotEqual(window["sun_1m"]["visible"], window["earth_1m"]["visible"])
        self.assertEqual(window["earth_1m"]["body"], "earth")
        self.assertEqual(window["sun_1m"]["ephemeris"], "DE421")
        self.assertEqual(window["sun_1m"]["start"], "2025-01-01T00:00:00Z")
        self.assertEqual(window["sun_1m"]["step"], "1 hour")
        self.assertEqual(window["sun_1m"]["duration"], "14 Earth days")
        self.assertEqual(result["windows"]["thirty_earth_days"]["earth_5m"]["duration"], "30 Earth days")
        self.assertEqual(len(result["windows"]["thirty_earth_days"]["sun_1m"]["visible"]), count_30)
        averages = result["long_term_averages"]
        self.assertEqual(averages["kind"], "18.6-year average")
        self.assertIn("Long-term average", averages["solar_label"])
        self.assertEqual(averages["solar_label"], SOLAR_LABEL)
        self.assertEqual(averages["earth_label"], EARTH_LABEL)
        self.assertNotEqual(averages["solar_fraction"], averages["earth_fraction"])
        self.assertEqual(window["sun_1m"]["body_radius_m"], SUN_RADIUS_M)
        self.assertIn("equatorial", window["earth_1m"]["body_radius_name"])

    def test_renderer_draws_distinguishable_series(self):
        series = {
            "sun_1m": [True, False, True, False],
            "sun_5m": [False, False, True, True],
            "earth_1m": [True, True, False, False],
            "earth_5m": [False, True, False, True],
        }
        notes = [
            "Ephemeris DE421.",
            "The 18.6-year averages are not this window.",
            "Earth disc visibility is not a radio link budget. No combined score.",
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = render_timeline(series, notes, Path(directory) / "timeline.png")
            self.assertGreater(path.stat().st_size, 500)
            image = np.asarray(Image.open(path))
        self.assertGreater(len(np.unique(image.reshape(-1, 3), axis=0)), 1)
        wrapped = len(note_lines(notes))
        colors = series_colors(image, wrapped)
        self.assertEqual(len(set(colors)), 4)
        sun_1m = image[sample_origin(0, 0, wrapped)[1], sample_origin(0, 0, wrapped)[0]]
        sun_5m = image[sample_origin(1, 0, wrapped)[1], sample_origin(1, 0, wrapped)[0]]
        self.assertFalse(np.array_equal(sun_1m, sun_5m))
        self.assertGreater(int(sun_1m.max()), int(sun_5m.max()))


if __name__ == "__main__":
    unittest.main()
