"""Point-query entry point. Reads local rasters and prints one JSON object."""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

from atlas.frame import lonlat_to_xy
from atlas.load import load_bundle
from atlas.sample import cold_shadow_centers, query_point
from atlas.sheet import default_citations, render_sheet

# Wueller et al. 2026 representative site NR101, inside the Nobile Rim 1 cluster.
DEFAULT_LON = 36.917
DEFAULT_LAT = -85.295

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = PACKAGE_ROOT / "data" / "raw"
DEFAULT_SHEET = PACKAGE_ROOT / "output" / "nobile-rim-1-sheet.png"


def main(argv: list[str] | None = None) -> int:
    warnings.filterwarnings("ignore", message="You will likely lose important projection information")
    parser = argparse.ArgumentParser(description="Query the Nobile Rim 1 static sheet.")
    parser.add_argument("--lat", type=float, default=DEFAULT_LAT, help="Planetocentric latitude, degrees.")
    parser.add_argument("--lon", type=float, default=DEFAULT_LON, help="Planetocentric east longitude, degrees.")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--sheet", type=Path, default=None, help="Also write the static PNG to this path.")
    args = parser.parse_args(argv)
    bundle = load_bundle(args.raw)
    x, y = lonlat_to_xy(args.lon, args.lat)
    centers = cold_shadow_centers(bundle.shadow, bundle.temperature)
    result = query_point(
        x,
        y,
        longitude_deg=args.lon,
        latitude_deg=args.lat,
        extent=bundle.extent,
        slope=bundle.slope,
        slope_rms=bundle.slope_rms,
        returns=bundle.returns,
        solar=bundle.solar,
        earth=bundle.earth,
        shadow=bundle.shadow,
        temperature=bundle.temperature,
        cold_centers=centers,
    )
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False)
    print(text)
    if args.sheet is not None:
        write_sheet(bundle, result, args.sheet)
    return 0


def write_sheet(bundle, result: dict, out_path: Path) -> Path:
    panels = [
        ("slope", _physical(bundle.slope), "Slope (deg), Barker et al. 2021"),
        ("slope_rms", _physical(bundle.slope_rms), "Slope uncertainty (deg RMS)"),
        ("returns", _physical(bundle.returns), "LOLA return count"),
        ("sunlight", _physical(bundle.solar), "Avg sunlight (fraction), Mazarico et al. 2011"),
        ("earth", _physical(bundle.earth), "Earth disc visibility, Mazarico et al. 2011"),
        ("shadow", _physical(bundle.shadow), "Permanent shadow"),
        ("temperature", _physical(bundle.temperature), "Summer max T (K), Williams et al. 2019"),
    ]
    cuts = result["cuts"]
    notes = [
        f"Point lon {result['longitude_deg']} lat {result['latitude_deg']}",
        f"slope {result['slope_deg']} deg, rms {result['slope_rms_deg']}",
        f"sun {result['solar_fraction']}, earth {result['earth_fraction']}",
        f"summer max {result['summer_max_temperature_k']} K at {result['temperature_resolution_m']} m",
        f"permanent shadow {result['permanent_shadow']}, LOLA returns {result['lola_return_count']}, gap {result['interpolated_gap']}",
        "Cuts: " + ", ".join(f"{key}={cuts[key]}" for key in cuts),
        f"distance to shadowed ground below 110 K: {result['distance_to_cold_shadow_m']}",
        result["extent"],
        result["cold_shadow_note"],
        bundle.solar.frame_note,
    ]
    return render_sheet(panels, citations=default_citations(), notes=notes, out_path=out_path)


def _physical(grid) -> "object":
    import numpy as np

    values = grid.values.astype(np.float64) * grid.scale + grid.offset
    if grid.nodata is not None:
        values = np.where(grid.values == grid.nodata, np.nan, values)
    values = np.where(np.isfinite(values), values, np.nan)
    return values


if __name__ == "__main__":
    raise SystemExit(main())
