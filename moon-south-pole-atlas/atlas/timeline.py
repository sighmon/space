"""Hourly Sun and Earth disc visibility at NR101. Separate from the static sheet."""

from __future__ import annotations

import argparse
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from atlas.ephemeris import EPHEMERIS_DETAIL, EPHEMERIS_NAME, moon_centered_vectors_m, utc_hours
from atlas.frame import RADIUS_M, lonlat_to_xy
from atlas.horizon import (
    AZIMUTH_BINS,
    EARTH_EQUATORIAL_RADIUS_M,
    MIN_HORIZONTAL_M,
    SUN_RADIUS_M,
    enu_axes,
    horizon_from_elevation,
    position_xyz,
    visibility_mask,
)
from atlas.load import load_bundle, load_elevation
from atlas.sample import EARTH_LABEL, SOLAR_LABEL, query_point, sample_grid
from atlas.timeline_sheet import render_timeline

# Fixed window. January 2025 is lunar south-polar summer, inside the years Wueller et al. examined.
WINDOW_START = "2025-01-01T00:00:00Z"
WINDOW_START_DT = datetime(2025, 1, 1, tzinfo=timezone.utc)
STEP = "1 hour"
STEP_SECONDS = 3600
HEIGHTS_M = (1, 5)
WINDOWS = (
    ("fourteen_earth_days", 14, "14 Earth days"),
    ("thirty_earth_days", 30, "30 Earth days"),
)

_BANNED_KEYS = {"habitability", "habitability_score", "safety", "safety_score", "score", "fused_score"}

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = PACKAGE_ROOT / "data" / "raw"
DEFAULT_KERNELS = DEFAULT_RAW / "kernels"
DEFAULT_PNG = PACKAGE_ROOT / "output" / "nobile-rim-1-timeline-14d.png"

HORIZON_NOTE = (
    "The local horizon is the maximum elevation angle of Site 06 elevation samples in each "
    f"{360.0 / AZIMUTH_BINS:.1f} degree azimuth bin, from the observer's 3D position on the "
    "MOON_ME sphere of radius 1737.4 km. Samples closer than half a 5 m pixel are skipped. "
    "Terrain outside the Site 06 raster is not in the mask. "
    "A disc is visible when its center altitude plus angular radius is strictly above that "
    "terrain horizon. This is not a flat horizon and not a radio link budget. "
    "The 1 m and 5 m series are separate. Visibility during these windows is not the 18.6-year average."
)


def main(argv: list[str] | None = None) -> int:
    warnings.filterwarnings("ignore", message="You will likely lose important projection information")
    parser = argparse.ArgumentParser(description="Sun and Earth disc timelines at one Nobile Rim 1 point.")
    parser.add_argument("--lat", type=float, default=-85.295)
    parser.add_argument("--lon", type=float, default=36.917)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--kernels", type=Path, default=DEFAULT_KERNELS)
    parser.add_argument("--png", type=Path, default=DEFAULT_PNG)
    args = parser.parse_args(argv)
    result = build_timeline(args.lon, args.lat, args.raw, args.kernels)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    if args.png is not None:
        render_timeline(fourteen_day_series(result), timeline_notes(result), args.png)
    return 0


def build_timeline(longitude_deg: float, latitude_deg: float, raw_dir: Path, kernel_dir: Path) -> dict:
    bundle = load_bundle(raw_dir)
    elevation = load_elevation(raw_dir)
    if not elevation.usable:
        raise RuntimeError(elevation.frame_note)
    if elevation.values.shape != bundle.slope.values.shape or elevation.transform != bundle.slope.transform:
        raise RuntimeError(
            "Site 06 elevation georeferencing does not match the slope grid already in use. "
            f"elevation {elevation.values.shape} {elevation.transform}; "
            f"slope {bundle.slope.values.shape} {bundle.slope.transform}"
        )
    easting, northing = lonlat_to_xy(longitude_deg, latitude_deg)
    surface = sample_grid(elevation, easting, northing)
    if surface is None:
        raise RuntimeError("The elevation sample at this point is missing. No horizon was invented from the slope raster.")
    horizons = {
        height: horizon_from_elevation(
            elevation.values,
            elevation.transform,
            observer_x_m=easting,
            observer_y_m=northing,
            surface_elevation_m=surface,
            height_m=height,
            nodata=elevation.nodata,
        )
        for height in HEIGHTS_M
    }
    hours = utc_hours(WINDOW_START_DT, WINDOWS[-1][1] * 24)
    vectors = moon_centered_vectors_m(kernel_dir, hours)
    masks: dict[int, dict[str, np.ndarray]] = {}
    for height in HEIGHTS_M:
        observer = position_xyz(longitude_deg, latitude_deg, RADIUS_M + surface + height)
        east, north, _up = enu_axes(longitude_deg, latitude_deg)
        masks[height] = {
            "sun": visibility_mask(observer, east, north, vectors["sun"], SUN_RADIUS_M, horizons[height]),
            "earth": visibility_mask(observer, east, north, vectors["earth"], EARTH_EQUATORIAL_RADIUS_M, horizons[height]),
        }
    from atlas.sample import cold_shadow_centers

    point = query_point(
        easting,
        northing,
        longitude_deg=longitude_deg,
        latitude_deg=latitude_deg,
        extent=bundle.extent,
        slope=bundle.slope,
        slope_rms=bundle.slope_rms,
        returns=bundle.returns,
        solar=bundle.solar,
        earth=bundle.earth,
        shadow=bundle.shadow,
        temperature=bundle.temperature,
        cold_centers=cold_shadow_centers(bundle.shadow, bundle.temperature),
    )
    series: dict[str, dict[str, list[bool]]] = {}
    for key, days, _label in WINDOWS:
        count = days * 24
        series[key] = {}
        for height in HEIGHTS_M:
            for body in ("sun", "earth"):
                flags = [bool(value) for value in masks[height][body][:count]]
                series[key][f"{body}_{height}m"] = flags
    result = package_timeline(
        series,
        longitude_deg=longitude_deg,
        latitude_deg=latitude_deg,
        easting_m=easting,
        northing_m=northing,
        surface_elevation_m=surface,
        elevation_frame=elevation.frame_note,
        solar_fraction=point["solar_fraction"],
        earth_fraction=point["earth_fraction"],
    )
    short = series["fourteen_earth_days"]
    long = series["thirty_earth_days"]
    for name, flags in short.items():
        if flags != long[name][: len(flags)]:
            raise RuntimeError(f"{name} fourteen-day series is not the start of the thirty-day series")
    return result


def package_timeline(
    series: dict[str, dict[str, list[bool]]],
    *,
    longitude_deg: float,
    latitude_deg: float,
    easting_m: float,
    northing_m: float,
    surface_elevation_m: float,
    elevation_frame: str,
    solar_fraction: float,
    earth_fraction: float,
) -> dict:
    """Assemble series metadata. ``series`` maps a window name to sun/earth height lists."""
    windows = {}
    for key, days, label in WINDOWS:
        block = series[key]
        packaged = {}
        for height in HEIGHTS_M:
            for body, radius_m, radius_name in (
                ("sun", SUN_RADIUS_M, "nominal solar radius 695700 km"),
                ("earth", EARTH_EQUATORIAL_RADIUS_M, "IAU equatorial radius 6378.137 km"),
            ):
                name = f"{body}_{height}m"
                flags = [bool(value) for value in block[name]]
                if len(flags) != days * 24:
                    raise RuntimeError(f"{name} in {key} has {len(flags)} samples, expected {days * 24}")
                packaged[name] = {
                    "body": body,
                    "observer_height_m": height,
                    "start": WINDOW_START,
                    "duration": label,
                    "duration_days": days,
                    "step": STEP,
                    "step_seconds": STEP_SECONDS,
                    "ephemeris": EPHEMERIS_NAME,
                    "body_radius_m": radius_m,
                    "body_radius_name": radius_name,
                    "visible": flags,
                }
        windows[key] = packaged
    result = {
        "name": "NR101",
        "longitude_deg": longitude_deg,
        "latitude_deg": latitude_deg,
        "easting_m": easting_m,
        "northing_m": northing_m,
        "surface_elevation_m": surface_elevation_m,
        "elevation_frame": elevation_frame,
        "ephemeris": EPHEMERIS_NAME,
        "ephemeris_detail": EPHEMERIS_DETAIL,
        "horizon_note": HORIZON_NOTE,
        "azimuth_bin_deg": 360.0 / AZIMUTH_BINS,
        "azimuth_bins": AZIMUTH_BINS,
        "min_horizontal_m": MIN_HORIZONTAL_M,
        "long_term_averages": {
            "kind": "18.6-year average",
            "distinct_from": "fourteen_earth_days and thirty_earth_days",
            "solar_fraction": solar_fraction,
            "solar_label": SOLAR_LABEL,
            "earth_fraction": earth_fraction,
            "earth_label": EARTH_LABEL,
        },
        "windows": windows,
    }
    _reject_fused_keys(result)
    return result


def fourteen_day_series(result: dict) -> dict[str, list[bool]]:
    window = result["windows"]["fourteen_earth_days"]
    return {name: record["visible"] for name, record in window.items()}


def timeline_notes(result: dict) -> list[str]:
    averages = result["long_term_averages"]
    return [
        f"Nobile Rim 1, Wueller NR101, lon {result['longitude_deg']} lat {result['latitude_deg']}.",
        f"Fourteen Earth days from {WINDOW_START}, step {STEP}. Ephemeris {result['ephemeris']}.",
        "Sun 1 m, Sun 5 m, Earth 1 m, and Earth 5 m are separate series. Bright means the disc is above the terrain horizon.",
        (
            "The 18.6-year averages are not this window: "
            f"sunlight {averages['solar_fraction']:.5f}, Earth disc {averages['earth_fraction']:.5f}. "
            + averages["solar_label"]
        ),
        averages["earth_label"] + " No combined habitability or safety score.",
        result["horizon_note"],
    ]


def _reject_fused_keys(value) -> None:
    if isinstance(value, dict):
        found = _BANNED_KEYS.intersection(value)
        if found:
            raise RuntimeError(f"fused score leaked into the timeline: {sorted(found)}")
        for child in value.values():
            _reject_fused_keys(child)
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                _reject_fused_keys(child)


if __name__ == "__main__":
    raise SystemExit(main())
