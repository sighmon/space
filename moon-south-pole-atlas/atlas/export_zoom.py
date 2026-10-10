"""Export the data behind the crater-zoom view on each region card.

Writes, into web/data/:
  sun.json / sun.js     DE421 Sun azimuth and elevation, hourly, for all nine points
                        (window.SUN_DATA). Sun disc centre against a smooth local horizontal.
                        No terrain is involved, so it is the same kind of number for every region.
  zoom.json / zoom.js   a local north-up elevation chip of the real LOLA Site 06 5 m DEM
                        around NR101 (window.ZOOM_DATA), 16-bit heights, base64.
  zoom/<ID>.webp        a crop of the LOLA average-sunlight-visibility map (120 m) around each
                        point, north-up. The same raster as the home backdrop. Not terrain.

Only NR101 has an elevation raster on disk (Site06 ``_surf.tif``). The other tiles in data/raw
are slope, slope error and return-count rasters: they cannot be hillshaded, so no terrain is
drawn for those regions.

    python -m atlas.export_zoom
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import warnings
from datetime import timezone
from pathlib import Path

import numpy as np

from atlas.ephemeris import EPHEMERIS_DETAIL, EPHEMERIS_NAME, moon_centered_vectors_m, utc_hours
from atlas.frame import RADIUS_M, SOLAR_DN_SCALE, illumination_transform, lonlat_to_xy
from atlas.horizon import enu_axes, position_xyz
from atlas.regions import REGIONS
from atlas.timeline import WINDOW_START_DT

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = PACKAGE_ROOT / "data" / "raw"
DEFAULT_OUT = PACKAGE_ROOT / "web" / "data"
HOURS = 336  # 14 Earth days from 2025-01-01T00Z, same window as the NR101 timeline
DEM_NAME = "Site06_final_adj_5mpp_surf.tif"
DEM_REGION_POINT = "NR101"
DEM_N = 256          # chip is DEM_N x DEM_N
DEM_PX_M = 10.0      # metres per chip pixel (2.56 km across); source is 5 m
MAP_N = 256          # backdrop crop size
MAP_SPAN_M = 15_360.0  # 128 source pixels of 120 m
_BANNED = {"score", "safety", "safety_score", "habitability", "habitability_score", "fused_score", "rank", "ranking", "safe"}


def sun_azel(longitude_deg: float, latitude_deg: float, sun_xyz_m: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Azimuth (deg, from north toward east) and elevation (deg) of the Sun's centre. Spherical Moon, no terrain."""
    east, north, up = enu_axes(longitude_deg, latitude_deg)
    observer = position_xyz(longitude_deg, latitude_deg, RADIUS_M)
    delta = sun_xyz_m - observer
    dist = np.linalg.norm(delta, axis=1)
    el = np.degrees(np.arcsin(np.clip(delta @ up / dist, -1, 1)))
    az = np.degrees(np.arctan2(delta @ east, delta @ north)) % 360.0
    return az, el


def local_axes_in_grid(longitude_deg: float, latitude_deg: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """Grid (map x, y) displacement per true metre toward local east and local north.

    Includes grid convergence and the projection scale, so a north-up chip really is north-up.
    """
    step = 500.0
    x0, y0 = lonlat_to_xy(longitude_deg, latitude_deg)
    dlat = math.degrees(step / RADIUS_M)
    dlon = math.degrees(step / (RADIUS_M * math.cos(math.radians(latitude_deg))))
    xn, yn = lonlat_to_xy(longitude_deg, latitude_deg + dlat)
    xe, ye = lonlat_to_xy(longitude_deg + dlon, latitude_deg)
    return ((xe - x0) / step, (ye - y0) / step), ((xn - x0) / step, (yn - y0) / step)


def _bilinear(arr: np.ndarray, col: np.ndarray, row: np.ndarray) -> np.ndarray:
    c0 = np.floor(col).astype(int)
    r0 = np.floor(row).astype(int)
    if c0.min() < 0 or r0.min() < 0 or c0.max() > arr.shape[1] - 2 or r0.max() > arr.shape[0] - 2:
        raise RuntimeError("chip reaches outside the source raster; nothing was extrapolated")
    fx, fy = col - c0, row - r0
    return (arr[r0, c0] * (1 - fx) * (1 - fy) + arr[r0, c0 + 1] * fx * (1 - fy)
            + arr[r0 + 1, c0] * (1 - fx) * fy + arr[r0 + 1, c0 + 1] * fx * fy)


def north_up_offsets(n: int, px_m: float, sub: int = 1):
    """East and north offsets in metres of each output pixel centre (rows run north to south)."""
    k = (np.arange(n * sub) + 0.5) / sub - n / 2
    e = k * px_m
    nn = -k * px_m
    return np.meshgrid(e, nn)


def encode_heights(h: np.ndarray) -> dict:
    lo, hi = float(h.min()), float(h.max())
    step = (hi - lo) / 65535.0 or 1.0
    q = np.rint((h - lo) / step).astype("<u2")
    return {"min_m": lo, "step_m": step, "u16le_b64": base64.b64encode(q.tobytes()).decode("ascii"), "_q": q}


def decode_heights(rec: dict, n: int) -> np.ndarray:
    q = np.frombuffer(base64.b64decode(rec["u16le_b64"]), dtype="<u2").reshape(n, n)
    return rec["min_m"] + q.astype(np.float64) * rec["step_m"]


def dem_chip(raw: Path, lon: float, lat: float) -> dict:
    import rasterio

    with rasterio.open(raw / DEM_NAME) as src:
        arr = src.read(1).astype(np.float64)
        t = src.transform
        nodata = src.nodata
    if not np.isfinite(arr).all() or (nodata is not None and np.isfinite(nodata) and (arr == nodata).any()):
        raise RuntimeError("DEM contains nodata; refusing to fill it")
    (ex, ey), (nx, ny) = local_axes_in_grid(lon, lat)
    x0, y0 = lonlat_to_xy(lon, lat)
    E, N = north_up_offsets(DEM_N, DEM_PX_M, sub=2)
    x = x0 + E * ex + N * nx
    y = y0 + E * ey + N * ny
    col = (x - t.c) / t.a - 0.5
    row = (y - t.f) / t.e - 0.5
    h = _bilinear(arr, col, row)
    h = h.reshape(DEM_N, 2, DEM_N, 2).mean(axis=(1, 3))  # 2x2 box = anti-aliased 10 m pixel
    rec = encode_heights(h)
    q = rec.pop("_q")
    rec.update({
        "n": DEM_N, "pixel_m": DEM_PX_M, "extent_m": DEM_N * DEM_PX_M,
        "orientation": "north up, east right, local frame at the point (grid convergence removed)",
        "source": "LOLA product 78 Site 06 5 m elevation, Site06_final_adj_5mpp_surf.tif (Barker et al. 2021), resampled to 10 m by 2x2 box mean",
        "point_id": DEM_REGION_POINT, "longitude_deg": lon, "latitude_deg": lat,
        "relief_m": float(h.max() - h.min()),
    })
    return rec


def map_crop(src_values: np.ndarray, lon: float, lat: float):
    a, _, c, _, e, f = illumination_transform()
    (ex, ey), (nx, ny) = local_axes_in_grid(lon, lat)
    x0, y0 = lonlat_to_xy(lon, lat)
    E, N = north_up_offsets(MAP_N, MAP_SPAN_M / MAP_N)
    x = x0 + E * ex + N * nx
    y = y0 + E * ey + N * ny
    return _bilinear(src_values, (x - c) / a - 0.5, (y - f) / e - 0.5)


def write_map_crops(raw: Path, out: Path) -> dict:
    import rasterio
    from PIL import Image

    with rasterio.open(raw / "AVGVISIB_75S_120M_201608.JP2") as src:
        v = src.read(1).astype(np.float32) * SOLAR_DN_SCALE
    d = out / "zoom"
    d.mkdir(parents=True, exist_ok=True)
    info = {}
    for r in REGIONS:
        s = map_crop(v, r.longitude_deg, r.latitude_deg)
        t = np.clip(s / 0.9, 0, 1) ** 0.8  # same tone curve as the home backdrop
        g = np.clip(t * 0.92 + 0.02, 0, 1)
        rgb = np.stack([g * 226 + 3, g * 231 + 4, g * 238 + 6], axis=-1)
        Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(d / f"{r.point_id}.webp", "WEBP", quality=82, method=6)
        info[r.point_id] = {"file": f"data/zoom/{r.point_id}.webp", "span_m": MAP_SPAN_M, "source_pixel_m": 120.0,
                            "fraction_min": float(np.clip(s, 0, 1).min()), "fraction_max": float(np.clip(s, 0, 1).max())}
    return info


def build(raw: Path, kernels: Path, out: Path) -> None:
    warnings.filterwarnings("ignore", message="You will likely lose important projection information")
    hours = utc_hours(WINDOW_START_DT, HOURS)
    sun = moon_centered_vectors_m(kernels, hours)["sun"]
    points = {}
    for r in REGIONS:
        az, el = sun_azel(r.longitude_deg, r.latitude_deg, sun)
        points[r.point_id] = {
            "region": r.region, "longitude_deg": r.longitude_deg, "latitude_deg": r.latitude_deg,
            "azimuth_deg_x10": [int(round(v * 10)) % 3600 for v in az],
            "elevation_deg_x10": [int(round(v * 10)) for v in el],
        }
    sun_data = {
        "provenance": "Generated by atlas/export_zoom.py with the repository's DE421 code (atlas.ephemeris).",
        "ephemeris": EPHEMERIS_NAME, "ephemeris_detail": EPHEMERIS_DETAIL,
        "start": hours[0].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "step_seconds": 3600, "hours": HOURS,
        "definition": "Azimuth in degrees from local north toward east and elevation in degrees of the Sun's disc centre above a smooth local horizontal (spherical Moon, radius 1737.4 km, MOON_ME frame, point-source centre, no terrain, no refraction). Stored in tenths of a degree.",
        "points": points,
    }
    dem = dem_chip(raw, points[DEM_REGION_POINT]["longitude_deg"], points[DEM_REGION_POINT]["latitude_deg"])
    maps = write_map_crops(raw, out)
    zoom = {
        "provenance": "Generated by atlas/export_zoom.py.",
        "dem": {DEM_REGION_POINT: dem},
        "map": {"label": "LOLA average sunlight visibility (Mazarico et al. 2011, AVGVISIB_75S_120M_201608), 120 m pixels, north up. A long-term average, not terrain and not a particular time.", "crops": maps},
    }
    for name, glob, data in (("sun", "SUN_DATA", sun_data), ("zoom", "ZOOM_DATA", zoom)):
        _check(data)
        text = json.dumps(data, sort_keys=True, allow_nan=False, separators=(",", ":"))
        (out / f"{name}.json").write_text(text + "\n")
        (out / f"{name}.js").write_text(f"window.{glob} = " + text + ";\n")
        print(f"wrote {out / name}.json and .js ({len(text) / 1e3:.0f} kB)")


def _check(value) -> None:
    if isinstance(value, dict):
        for k, child in value.items():
            if str(k).lower() in _BANNED:
                raise ValueError(f"banned key in export: {k}")
            _check(child)
    elif isinstance(value, list) and value and not isinstance(value[0], (int, float)):
        for child in value:
            _check(child)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Export the crater-zoom data for web/.")
    p.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    p.add_argument("--kernels", type=Path, default=DEFAULT_RAW / "kernels")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = p.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    build(a.raw, a.kernels, a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
