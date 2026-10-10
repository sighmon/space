"""Nine October 2024 regions at one published point each.

`python -m atlas.regions` prints the comparison. Raster reads stay in this module.
The assembly itself is atlas.compare, which tests call without these files.
"""

from __future__ import annotations

import argparse
import json
import math
import warnings
from dataclasses import replace
from pathlib import Path

from atlas.compare import FRAME_NOTE, WUELLER_2026, RegionSpec, package_comparison, region_record
from atlas.frame import lonlat_to_xy
from atlas.load import _load_diviner, _load_illumination, _load_site
from atlas.sample import cold_shadow_centers, rowcol_of_point

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = PACKAGE_ROOT / "data" / "raw"
DEFAULT_PNG = PACKAGE_ROOT / "output" / "nine-regions.png"

# Cap-wide illumination and Diviner are windowed to the nine points plus this pad.
# The pad is the same 40 km margin the Nobile Rim 1 sheet uses, so the search for the
# nearest cold permanent-shadow pixel reaches at least 40 km past any of the nine points.
CAP_PAD_M = 40_000.0

# NASA's 28 October 2024 order. One Wueller Table A1 point each, the *01 row.
REGIONS: tuple[RegionSpec, ...] = (
    RegionSpec(
        region="Peak near Cabeus B",
        point_id="PCB01",
        longitude_deg=-69.9830,
        latitude_deg=-83.7630,
        point_citation=WUELLER_2026,
        slope_folder=None,
        slope_source=(
            "Product 78 does not publish a 5 m site DEM for Peak near Cabeus B. "
            "Slope, slope RMS, and LOLA return count are missing. "
            "The 20 m mosaic is not used in their place."
        ),
    ),
    RegionSpec(
        region="Haworth",
        point_id="HW01",
        longitude_deg=-20.5140,
        latitude_deg=-86.7680,
        point_citation=WUELLER_2026,
        slope_folder="Haworth",
        slope_source=(
            "LOLA product 78 Haworth, 5 m site DEM (Barker et al. 2021). "
            "HW01 is sampled on this tile."
        ),
    ),
    RegionSpec(
        region="Malapert Massif",
        point_id="MMA01",
        longitude_deg=-0.9440,
        latitude_deg=-85.9420,
        point_citation=WUELLER_2026,
        slope_folder="Site23",
        slope_source=(
            "LOLA product 78 Site 23, 5 m site DEM (Barker et al. 2021). "
            "MMA01 falls inside this tile. Wueller's table names the massif Mons Malapert."
        ),
    ),
    RegionSpec(
        region="Mons Mouton Plateau",
        point_id="MMP01",
        longitude_deg=26.7100,
        latitude_deg=-85.1110,
        point_citation=WUELLER_2026,
        slope_folder=None,
        slope_source=(
            "Product 78 has no 5 m folder for Mons Mouton Plateau. "
            "Site 20 (Leibnitz beta) does not contain MMP01, so that tile is not used. "
            "Slope, slope RMS, and LOLA return count are missing. "
            "The 20 m mosaic is not used in their place."
        ),
    ),
    RegionSpec(
        region="Mons Mouton",
        point_id="MMO01",
        longitude_deg=31.8510,
        latitude_deg=-85.4160,
        point_citation=WUELLER_2026,
        slope_folder="Site20",
        slope_source=(
            "LOLA product 78 Site 20, the Leibnitz beta plateau, 5 m site DEM (Barker et al. 2021). "
            "MMO01 falls inside this tile. This tile is not a Mons Mouton Plateau DEM."
        ),
    ),
    RegionSpec(
        region="Nobile Rim 1",
        point_id="NR101",
        longitude_deg=36.917,
        latitude_deg=-85.295,
        point_citation=WUELLER_2026,
        slope_folder="Site06",
        slope_source=(
            "LOLA product 78 Site 06, 5 m site DEM (Barker et al. 2021). "
            "NR101, the same point as the existing Nobile Rim 1 sheet."
        ),
    ),
    RegionSpec(
        region="Nobile Rim 2",
        point_id="NR201",
        longitude_deg=56.4810,
        latitude_deg=-84.0540,
        point_citation=WUELLER_2026,
        slope_folder="DM2",
        slope_source=(
            "LOLA product 78 folder DM2, 5 m site DEM (Barker et al. 2021). "
            "NR201 falls inside this tile. A different published point near 60.7°E is not used."
        ),
    ),
    RegionSpec(
        region="de Gerlache Rim 2",
        point_id="dGR101",
        longitude_deg=-68.0150,
        latitude_deg=-88.5130,
        point_citation=WUELLER_2026,
        slope_folder="SL2",
        slope_source=(
            "LOLA product 78 folder SL2, 5 m site DEM (Barker et al. 2021). "
            "dGR101 falls inside this tile. This is not Site 11, the 2022 de Gerlache rim product."
        ),
    ),
    RegionSpec(
        region="Slater Plain",
        point_id="SP01",
        longitude_deg=124.5210,
        latitude_deg=-87.4780,
        point_citation=WUELLER_2026,
        slope_folder=None,
        slope_source=(
            "Product 78 does not publish a 5 m site DEM for Slater Plain. "
            "Slope, slope RMS, and LOLA return count are missing. "
            "The 20 m mosaic is not used in their place."
        ),
    ),
)


def slope_raster_records() -> list[tuple[str, str, float]]:
    """Product-78 files the comparison opens, other than Site 06, which the manifest already lists.

    Regions with no folder contribute nothing. A file that is not on this list is not hashed.
    """
    rows: list[tuple[str, str, float]] = []
    for spec in REGIONS:
        folder = spec.slope_folder
        if folder is None or folder == "Site06":
            continue
        for suffix in ("slp", "slperr", "ldec"):
            name = f"{folder}_final_adj_5mpp_{suffix}.tif"
            url = f"https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/{folder}/{name}"
            rows.append((name, url, 5.0))
    return rows


def build_comparison(raw_dir: Path) -> dict:
    """Sample the nine points. Illumination and Diviner use one window around those points."""
    coordinates = [lonlat_to_xy(spec.longitude_deg, spec.latitude_deg) for spec in REGIONS]
    xs = [item[0] for item in coordinates]
    ys = [item[1] for item in coordinates]
    bounds = (
        min(xs) - CAP_PAD_M,
        min(ys) - CAP_PAD_M,
        max(xs) + CAP_PAD_M,
        max(ys) + CAP_PAD_M,
    )
    solar = _load_illumination(raw_dir, "solar", bounds)
    earth = _load_illumination(raw_dir, "earth", bounds)
    shadow = _load_illumination(raw_dir, "shadow", bounds)
    temperature = _load_diviner(raw_dir / "polar_south_80_summer_max-float.tif", bounds)
    cold_centers = cold_shadow_centers(shadow, temperature)
    records = []
    for spec, (x, y) in zip(REGIONS, coordinates, strict=True):
        slope, slope_rms, returns, source = _slope_for(raw_dir, spec, x, y)
        record = region_record(
            replace(spec, slope_source=source),
            x,
            y,
            slope=slope,
            slope_rms=slope_rms,
            returns=returns,
            solar=solar,
            earth=earth,
            shadow=shadow,
            temperature=temperature,
            cold_centers=cold_centers,
        )
        records.append(record)
        del slope, slope_rms, returns
    document = package_comparison(records)
    document["extent"] = (
        f"{document['extent']} Cap-wide layers were read inside "
        f"({bounds[0]:.1f}, {bounds[1]:.1f}) to ({bounds[2]:.1f}, {bounds[3]:.1f}) m, "
        f"the nine points expanded by {CAP_PAD_M:.0f} m. "
        "The distance to cold permanent shadow is searched inside that window only."
    )
    document["frame"] = FRAME_NOTE
    return document


def main(argv: list[str] | None = None) -> int:
    warnings.filterwarnings("ignore", message="You will likely lose important projection information")
    parser = argparse.ArgumentParser(description="Five-field comparison of the nine Artemis III regions.")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--png", type=Path, default=None, help="Also write the static comparison to this path.")
    args = parser.parse_args(argv)
    comparison = build_comparison(args.raw)
    print(json.dumps(comparison, indent=2, sort_keys=True, allow_nan=False))
    if args.png is not None:
        from atlas.compare_sheet import render_comparison

        render_comparison(comparison, args.png)
    return 0


def _slope_for(raw_dir: Path, spec: RegionSpec, x: float, y: float):
    """Load a product-78 trio only when the published point is inside a usable 5 m tile."""
    if spec.slope_folder is None:
        return None, None, None, spec.slope_source
    names = {
        "slope": f"{spec.slope_folder}_final_adj_5mpp_slp.tif",
        "slope_rms": f"{spec.slope_folder}_final_adj_5mpp_slperr.tif",
        "returns": f"{spec.slope_folder}_final_adj_5mpp_ldec.tif",
    }
    paths = {key: raw_dir / name for key, name in names.items()}
    absent = [path.name for path in paths.values() if not path.is_file()]
    if absent:
        return None, None, None, (
            f"Product 78 files for {spec.slope_folder} are not on disk ({', '.join(absent)}). "
            "Slope, slope RMS, and LOLA return count are missing."
        )
    slope = _load_site(paths["slope"], "slope", "degrees", 5.0)
    slope_rms = _load_site(paths["slope_rms"], "slope RMS", "degrees", 5.0)
    returns = _load_site(paths["returns"], "LOLA return count", "count", 5.0)
    grids = (slope, slope_rms, returns)
    if not all(grid.usable for grid in grids):
        notes = " ".join(grid.frame_note for grid in grids if not grid.usable)
        return None, None, None, (
            f"The {spec.slope_folder} GeoTIFF failed the south-polar frame check. "
            f"Slope, slope RMS, and LOLA return count are missing. {notes}"
        )
    if not all(_covers(grid, x, y) for grid in grids):
        return None, None, None, (
            f"The published point is outside the {spec.slope_folder} 5 m tile. "
            "Slope, slope RMS, and LOLA return count are missing. "
            "A coarser mosaic is not substituted."
        )
    if abs(slope.resolution_m - 5.0) > max(0.05, 0.01 * 5.0):
        return slope, slope_rms, returns, (
            f"{spec.slope_folder} grid at {slope.resolution_m:.4f} m per pixel. Not the 5 m site DEM."
        )
    return slope, slope_rms, returns, spec.slope_source


def _covers(grid, x: float, y: float) -> bool:
    row_f, col_f = rowcol_of_point(grid.transform, x, y)
    row = math.floor(row_f)
    col = math.floor(col_f)
    height, width = grid.values.shape
    return 0 <= row < height and 0 <= col < width


if __name__ == "__main__":
    raise SystemExit(main())
