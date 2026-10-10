"""Assemble nine region records from point samples. No file I/O and no drawing.

Each record keeps the five Nobile Rim 1 fields and the separate cuts.
A missing grid stays missing. Nothing here is a fused or ranking score.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from atlas.sample import (
    BARKER_2021,
    EARTH_LABEL,
    MAZARICO_2011,
    SOLAR_LABEL,
    TEMPERATURE_LABEL,
    WILLIAMS_2019,
    Grid,
    _reject_fused_score,
    cuts_for,
    distance_to_cold_shadow,
    sample_grid,
)

WUELLER_2026 = (
    "Wueller et al. 2026, JGR Planets, doi:10.1029/2025JE009434, Table A1. "
    "First listed candidate landing site of each October 2024 region. Not a ranking."
)

FRAME_NOTE = (
    "South-polar stereographic, true scale at the pole, radius 1737400 m, "
    "longitude of origin 0, latitude of origin and true scale −90°, MOON_ME / DE421, meters. "
    "Longitude is east-positive. Latitude is planetocentric and negative south."
)

EXTENT_NOTE = (
    "USGS region polygons were not applied. Each number is the nearest pixel of the named map "
    "at one published point. Sunlight, Earth-disc visibility, and permanent shadow are the "
    "75°S / 120 m grids. Summer-maximum temperature is the Diviner grid on its own pixel, "
    "not a 5 m measurement. Slope, slope RMS, and the LOLA return count come from the "
    "product-78 tile named on that row, and only when the point falls inside it. "
    "The 20 m mosaic is not used as a 5 m site DEM."
)

TIMELINE_NOTE = (
    "Sunlight and Earth fractions in this comparison are 18.6-year averages. "
    "They are not the NR101 hourly Sun and Earth disc timeline, which remains a separate product for that one point."
)

# The four sentences a reader has to be able to find on the comparison.
CAVEATS = (
    "Cuts are not flight rules.",
    "Earth visibility is not a radio link budget.",
    "Ice is not a volume.",
    "There is no single score.",
)

_BANNED_KEYS = {
    "habitability",
    "habitability_score",
    "safety",
    "safety_score",
    "score",
    "fused_score",
    "rank",
    "ranking",
}


@dataclass(frozen=True)
class RegionSpec:
    """One published point and the slope product that contains it, if any."""

    region: str
    point_id: str
    longitude_deg: float
    latitude_deg: float
    point_citation: str
    slope_folder: str | None
    slope_source: str


def pixel_label(resolution_m: float | None) -> str | None:
    if resolution_m is None or not math.isfinite(resolution_m):
        return None
    return f"{float(resolution_m):.4f} m"


def slope_dem_label(resolution_m: float | None) -> str | None:
    """Name the pixel size that was actually sampled. A coarser grid is not the 5 m site DEM."""
    if resolution_m is None or not math.isfinite(resolution_m):
        return None
    if abs(resolution_m - 5.0) <= max(0.05, 0.01 * 5.0):
        return f"{resolution_m:.4f} m LOLA site DEM"
    return f"{resolution_m:.4f} m grid; not the 5 m site DEM"


def region_record(
    spec: RegionSpec,
    x: float,
    y: float,
    *,
    slope: Grid | None,
    slope_rms: Grid | None,
    returns: Grid | None,
    solar: Grid | None,
    earth: Grid | None,
    shadow: Grid | None,
    temperature: Grid | None,
    cold_centers: np.ndarray | None = None,
) -> dict:
    """One region. None grids and nodata samples stay None, including the cuts that need them."""
    slope_deg = _sample(slope, x, y)
    slope_rms_deg = _sample(slope_rms, x, y)
    count = _sample(returns, x, y)
    solar_fraction = _sample(solar, x, y)
    earth_fraction = _sample(earth, x, y)
    shadow_value = _sample(shadow, x, y)
    temperature_k = _sample(temperature, x, y)
    permanent_shadow = None if shadow_value is None else bool(shadow_value >= 0.5)
    interpolated_gap = None if count is None else bool(count <= 0.0)
    slope_resolution = _resolution(slope)
    cold_distance = None if cold_centers is None else distance_to_cold_shadow(x, y, cold_centers)
    record = {
        "region": spec.region,
        "point_id": spec.point_id,
        "longitude_deg": spec.longitude_deg,
        "latitude_deg": spec.latitude_deg,
        "point_citation": spec.point_citation,
        "easting_m": x,
        "northing_m": y,
        "slope_deg": slope_deg,
        "slope_rms_deg": slope_rms_deg,
        "slope_resolution_m": slope_resolution,
        "slope_pixel_label": pixel_label(slope_resolution),
        "slope_dem_label": slope_dem_label(slope_resolution),
        "slope_map": _map_note(slope),
        "slope_source": spec.slope_source,
        "slope_citation": None if slope is None or not slope.usable else BARKER_2021,
        "solar_fraction": solar_fraction,
        "solar_resolution_m": _resolution(solar),
        "solar_pixel_label": pixel_label(_resolution(solar)),
        "solar_map": _map_note(solar),
        "solar_label": SOLAR_LABEL,
        "solar_citation": None if solar is None or not solar.usable else MAZARICO_2011,
        "earth_fraction": earth_fraction,
        "earth_resolution_m": _resolution(earth),
        "earth_pixel_label": pixel_label(_resolution(earth)),
        "earth_map": _map_note(earth),
        "earth_label": EARTH_LABEL,
        "earth_citation": None if earth is None or not earth.usable else MAZARICO_2011,
        "summer_max_temperature_k": temperature_k,
        "temperature_resolution_m": _resolution(temperature),
        "temperature_pixel_label": pixel_label(_resolution(temperature)),
        "temperature_map": _map_note(temperature),
        "temperature_label": TEMPERATURE_LABEL,
        "temperature_citation": None if temperature is None or not temperature.usable else WILLIAMS_2019,
        "permanent_shadow": permanent_shadow,
        "permanent_shadow_resolution_m": _resolution(shadow),
        "permanent_shadow_pixel_label": pixel_label(_resolution(shadow)),
        "permanent_shadow_map": _map_note(shadow),
        "permanent_shadow_citation": None if shadow is None or not shadow.usable else MAZARICO_2011,
        "distance_to_cold_shadow_m": cold_distance,
        "lola_return_count": count,
        "interpolated_gap": interpolated_gap,
        "return_resolution_m": _resolution(returns),
        "return_pixel_label": pixel_label(_resolution(returns)),
        "return_map": _map_note(returns),
        "return_citation": None if returns is None or not returns.usable else BARKER_2021,
        "cuts": cuts_for(slope_deg, solar_fraction, earth_fraction, temperature_k, permanent_shadow),
    }
    _reject_ranking(record)
    return record


def package_comparison(records: list[dict]) -> dict:
    """Nine separate records, in the order given. Refuses a fused or ranking key."""
    if len(records) != 9:
        raise ValueError(f"the comparison has {len(records)} records; the October 2024 list has nine")
    names = [record["region"] for record in records]
    if len(set(names)) != 9:
        raise ValueError("region names are not nine separate rows")
    points = [record["point_id"] for record in records]
    if len(set(points)) != 9:
        raise ValueError("point ids are not nine separate rows")
    return _document(records)


def method_lines(comparison: dict) -> list[str]:
    """Frame, sources, nine coordinates, and the four caveats. Shared by the figure and the JSON."""
    lines = [
        "Method",
        comparison["frame"],
        comparison["extent"],
        comparison["timeline_note"],
        "Sources:",
    ]
    for source in comparison["sources"]:
        lines.append(f"{source['layer']}: {source['citation']} ({source['pixel']})")
    lines.append("Points, one per region, not a ranking:")
    for record in comparison["regions"]:
        lines.append(
            f"{record['region']} {record['point_id']}: "
            f"lon {record['longitude_deg']}°, lat {record['latitude_deg']}°."
        )
    lines.append("Caveats:")
    lines.extend(comparison["caveats"])
    return lines


def _document(records: list[dict]) -> dict:
    document = {
        "frame": FRAME_NOTE,
        "extent": EXTENT_NOTE,
        "timeline_note": TIMELINE_NOTE,
        "caveats": list(CAVEATS),
        "sources": [
            {
                "layer": "slope, slope RMS, and LOLA return count",
                "citation": BARKER_2021,
                "pixel": "5 m where a product-78 tile contains the point; otherwise missing",
            },
            {
                "layer": "sunlight, Earth disc, and permanent shadow",
                "citation": MAZARICO_2011,
                "pixel": "120 m on the 75°S grids",
            },
            {
                "layer": "summer maximum temperature",
                "citation": WILLIAMS_2019,
                "pixel": "Diviner's own pixel, about 240 m, not 5 m",
            },
            {
                "layer": "point coordinates",
                "citation": WUELLER_2026,
                "pixel": "one named point, not a region polygon",
            },
        ],
        "regions": records,
    }
    _reject_ranking(document)
    for record in records:
        _reject_ranking(record)
        _reject_ranking(record["cuts"])
    return document


def _reject_ranking(result: dict) -> None:
    _reject_fused_score(result)
    found = _BANNED_KEYS.intersection(result)
    if found:
        raise RuntimeError(f"fused or ranking key leaked into the comparison: {sorted(found)}")


def _sample(grid: Grid | None, x: float, y: float) -> float | None:
    if grid is None:
        return None
    return sample_grid(grid, x, y)


def _resolution(grid: Grid | None) -> float | None:
    if grid is None or not grid.usable:
        return None
    if not math.isfinite(grid.resolution_m):
        return None
    return float(grid.resolution_m)


def _map_note(grid: Grid | None) -> str | None:
    if grid is None or not grid.usable:
        return None
    return grid.frame_note
