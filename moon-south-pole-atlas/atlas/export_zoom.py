"""Export the data behind the crater-zoom view on each region card.

Writes, into web/data/:
  sun.json / sun.js     DE421 Sun azimuth and elevation, hourly, for all nine points
                        (window.SUN_DATA). Sun disc centre against a smooth local horizontal.
                        No terrain is involved, so it is the same kind of number for every region.
  zoom.json / zoom.js   a local north-up elevation chip (window.ZOOM_DATA), 16-bit heights, base64,
                        for every region that has a real LOLA elevation raster on disk (see DEM_SOURCES):
                        5 m product-78 site DEMs (``*_surf.tif``) where a tile contains the point, and
                        a window of the 5 m 87-90S mosaic (product 81) for Slater Plain, and windows of the 20 m LOLA polar DEM (LDEM_80S_20MPP_ADJ) for the rest. Also the
                        terrain-aware hourly Sun/Earth visibility strips for each of those regions.
  zoom/<ID>.webp        a crop of the LOLA average-sunlight-visibility map (120 m) around each
                        point, north-up. The same raster as the home backdrop. Not terrain.

Slope, slope-error and return-count tiles in data/raw cannot be hillshaded and are not used here.
A region with no elevation raster would keep only the static sunlight crop; at present all nine
regions have one (the three without a 5 m site tile use the 20 m polar DEM).

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
DEM_N = 256          # chip is DEM_N x DEM_N
STRIP_HEIGHTS_M = (1, 5)
# point id -> elevation raster on disk. ``pixel_m`` is the chip pixel: 10 m for the 5 m site DEMs
# (2x2 box mean of bilinear samples), the native 20 m for the polar-DEM windows (no upsampling).
DEM_SOURCES = {
    "NR101": dict(file="Site06_final_adj_5mpp_surf.tif", source_pixel_m=5.0, pixel_m=10.0, product="LOLA product 78 Site 06",
                  url="https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site06/Site06_final_adj_5mpp_surf.tif"),
    "HW01": dict(file="Haworth_final_adj_5mpp_surf.tif", source_pixel_m=5.0, pixel_m=10.0, product="LOLA product 78 Haworth",
                 url="https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Haworth/Haworth_final_adj_5mpp_surf.tif"),
    "MMA01": dict(file="Site23_final_adj_5mpp_surf.tif", source_pixel_m=5.0, pixel_m=10.0, product="LOLA product 78 Site 23",
                  url="https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site23/Site23_final_adj_5mpp_surf.tif"),
    "MMO01": dict(file="Site20_final_adj_5mpp_surf.tif", source_pixel_m=5.0, pixel_m=10.0, product="LOLA product 78 Site 20 (Leibnitz beta)",
                  url="https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site20/Site20_final_adj_5mpp_surf.tif"),
    "NR201": dict(file="DM2_final_adj_5mpp_surf.tif", source_pixel_m=5.0, pixel_m=10.0, product="LOLA product 78 DM2",
                  url="https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/DM2/DM2_final_adj_5mpp_surf.tif"),
    "dGR101": dict(file="SL2_final_adj_5mpp_surf.tif", source_pixel_m=5.0, pixel_m=10.0, product="LOLA product 78 SL2",
                   url="https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/SL2/SL2_final_adj_5mpp_surf.tif"),
    "PCB01": dict(file="LDEM_80S_20MPP_ADJ_win30km_PCB01.tif", source_pixel_m=20.0, pixel_m=20.0, product="LOLA product 90 polar DEM, 30 km window",
                  url="https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_20MPP_ADJ.TIF"),
    "MMP01": dict(file="LDEM_80S_20MPP_ADJ_win30km_MMP01.tif", source_pixel_m=20.0, pixel_m=20.0, product="LOLA product 90 polar DEM, 30 km window",
                  url="https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_20MPP_ADJ.TIF"),
    "SP01": dict(file="ldem_87s_5mpp_win20km_SP01.tif", source_pixel_m=5.0, pixel_m=10.0,
                 product="LOLA product 81 87-90S 5 m mosaic (interpolation fill-in), 20 km window",
                 url="https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/87S/ldem_87s_5mpp.tif"),
}
CITATION = {5.0: "Barker et al. 2021, Planetary and Space Science 203, 105119",
            20.0: "Barker et al. 2023, Planetary Science Journal, 10.3847/PSJ/acf3e1"}
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


def read_dem(raw: Path, name: str):
    import rasterio

    with rasterio.open(raw / name) as src:
        arr = src.read(1).astype(np.float64)
        t = src.transform
        nodata = src.nodata
    if not np.isfinite(arr).all() or (nodata is not None and np.isfinite(nodata) and (arr == nodata).any()):
        raise RuntimeError(f"{name} contains nodata; refusing to fill it")
    return arr, t


def dem_chip(raw: Path, point_id: str, lon: float, lat: float) -> dict:
    spec = DEM_SOURCES[point_id]
    arr, t = read_dem(raw, spec["file"])
    px = spec["pixel_m"]
    sub = 2 if px > spec["source_pixel_m"] else 1
    (ex, ey), (nx, ny) = local_axes_in_grid(lon, lat)
    x0, y0 = lonlat_to_xy(lon, lat)
    E, N = north_up_offsets(DEM_N, px, sub=sub)
    x = x0 + E * ex + N * nx
    y = y0 + E * ey + N * ny
    col = (x - t.c) / t.a - 0.5
    row = (y - t.f) / t.e - 0.5
    h = _bilinear(arr, col, row)
    if sub > 1:
        h = h.reshape(DEM_N, sub, DEM_N, sub).mean(axis=(1, 3))  # 2x2 box = anti-aliased chip pixel
    rec = encode_heights(h)
    q = rec.pop("_q")
    res = spec["source_pixel_m"]
    how = f"resampled to {px:g} m by 2x2 box mean" if sub > 1 else "native pixel spacing, bilinear at the chip grid, not upsampled"
    rec.update({
        "n": DEM_N, "pixel_m": px, "extent_m": DEM_N * px, "source_pixel_m": res,
        "orientation": "north up, east right, local frame at the point (grid convergence removed)",
        "source": f"{spec['product']} elevation, {spec['file']} ({CITATION[res]}), {how}",
        "source_short": f"{spec['product']}, {res:g} m elevation",
        "citation": CITATION[res], "file": spec["file"], "url": spec["url"],
        "point_id": point_id, "longitude_deg": lon, "latitude_deg": lat,
        "relief_m": float(h.max() - h.min()),
    })
    return rec


def terrain_strips(raw: Path, point_id: str, lon: float, lat: float, sun_xyz, earth_xyz) -> dict:
    """Hourly terrain-aware Sun and Earth disc visibility (the repo's own horizon code), 1 m and 5 m eye height.

    Same method as atlas.timeline for NR101: horizon = highest terrain elevation angle per 0.5 degree azimuth
    bin from the observer's 3D position, disc visible when centre altitude + angular radius clears it.
    Terrain outside the raster is not in the mask (the 20 m windows reach 15 km from the point).
    """
    from atlas.horizon import (EARTH_EQUATORIAL_RADIUS_M, SUN_RADIUS_M, horizon_from_elevation,
                               visibility_mask)

    spec = DEM_SOURCES[point_id]
    arr, t = read_dem(raw, spec["file"])
    x0, y0 = lonlat_to_xy(lon, lat)
    col = int(math.floor((x0 - t.c) / t.a)); row = int(math.floor((y0 - t.f) / t.e))
    if not (0 <= row < arr.shape[0] and 0 <= col < arr.shape[1]):
        raise RuntimeError(f"{point_id} is outside {spec['file']}")
    surface = float(arr[row, col])
    transform = (t.a, t.b, t.c, t.d, t.e, t.f)
    east, north, _up = enu_axes(lon, lat)
    out = {}
    for h in STRIP_HEIGHTS_M:
        hor = horizon_from_elevation(arr, transform, observer_x_m=x0, observer_y_m=y0, surface_elevation_m=surface,
                                     height_m=h, min_horizontal_m=spec["source_pixel_m"] / 2.0)
        obs = position_xyz(lon, lat, RADIUS_M + surface + h)
        for body, xyz, rad in (("sun", sun_xyz, SUN_RADIUS_M), ("earth", earth_xyz, EARTH_EQUATORIAL_RADIUS_M)):
            m = visibility_mask(obs, east, north, xyz, rad, hor)
            out[f"{body}_{h}m"] = "".join("1" if v else "0" for v in m)
    out["surface_elevation_m"] = surface
    out["source_pixel_m"] = spec["source_pixel_m"]
    out["reach_m"] = float(min(row, col, arr.shape[0] - 1 - row, arr.shape[1] - 1 - col) * spec["source_pixel_m"])
    return out


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
    # Sun as seen from the pole, for the home map: longitude of the Sun's direction (map angle) and elevation at 90S.
    sx, sy = sun[:, 0], sun[:, 1]
    home_lon = np.degrees(np.arctan2(sy, sx)) % 360.0
    _az, home_el = sun_azel(0.0, -90.0, sun)
    sun_data["home"] = {
        "definition": "Longitude of the Sun's direction in MOON_ME (the angle the home map draws the light from) and the Sun's centre elevation at the pole, hours as in points. Tenths of a degree.",
        "longitude_deg_x10": [int(round(v * 10)) % 3600 for v in home_lon],
        "elevation_deg_x10": [int(round(v * 10)) for v in home_el],
    }
    vec = moon_centered_vectors_m(kernels, hours)
    dems, strips = {}, {}
    for r in REGIONS:
        if r.point_id not in DEM_SOURCES or not (raw / DEM_SOURCES[r.point_id]["file"]).is_file():
            continue
        dems[r.point_id] = dem_chip(raw, r.point_id, r.longitude_deg, r.latitude_deg)
        if r.point_id != "NR101":  # NR101 keeps its published nr101.json timeline (atlas.timeline, 14 and 30 days)
            ts = terrain_strips(raw, r.point_id, r.longitude_deg, r.latitude_deg, vec["sun"], vec["earth"])
            ts["source"] = dems[r.point_id]["source_short"]
            strips[r.point_id] = ts
    maps = write_map_crops(raw, out)
    zoom = {
        "provenance": "Generated by atlas/export_zoom.py.",
        "dem": dems,
        "strips": strips,
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
