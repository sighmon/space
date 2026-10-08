"""Point query over aligned grids. No file I/O.

Cuts stay separate. Nothing in the result is a fused habitability or safety score.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

BARKER_2021 = "Barker et al. 2021, Planetary and Space Science 203, 105119, doi:10.1016/j.pss.2020.105119"
MAZARICO_2011 = "Mazarico et al. 2011, Icarus 211, 1066-1081, doi:10.1016/j.icarus.2010.10.030"
WILLIAMS_2019 = "Williams et al. 2019, JGR Planets 124, 2505-2521, doi:10.1029/2019JE006028"

SOLAR_LABEL = (
    "18.6-year average fraction of hourly steps when any part of the solar disc is above the horizon. "
    "Long-term average, not the sunlight during a particular mission week."
)
EARTH_LABEL = (
    "18.6-year average fraction of hourly steps when any part of the Earth disc is above the horizon. "
    "Disc visibility, not a radio link budget."
)
TEMPERATURE_LABEL = (
    "Diviner summer-maximum bolometric brightness temperature. "
    "Quoted on Diviner's own pixel, not as a 5 m measurement."
)

CUT_NAMES = (
    "slope_under_5_deg",
    "slope_under_8_deg",
    "average_sunlight_above_0_5",
    "earth_visibility_at_or_above_0_99",
    "earth_visibility_at_or_above_0_30",
    "temperature_below_110_k",
    "below_75_k_and_inside_permanent_shadow",
)


@dataclass
class Grid:
    """One band on its own grid. `values` are raw stored numbers."""

    values: np.ndarray
    transform: tuple[float, float, float, float, float, float]
    nodata: float | None
    scale: float
    offset: float
    resolution_m: float
    usable: bool
    frame_note: str
    citation: str
    value_label: str

    def __post_init__(self) -> None:
        self.values = np.asarray(self.values)
        if self.values.ndim != 2:
            raise ValueError("Grid values must be a 2-D array")


def apply_stored_scale(raw: float, scale: float, offset: float) -> float:
    return float(raw) * float(scale) + float(offset)


def rowcol_of_point(transform: tuple[float, float, float, float, float, float], x: float, y: float) -> tuple[float, float]:
    """Continuous column and row of a map point. Integers are pixel corners."""
    a, b, c, d, e, f = transform
    det = a * e - b * d
    if det == 0.0:
        raise ValueError("transform is singular")
    col = (e * (x - c) - b * (y - f)) / det
    row = (-d * (x - c) + a * (y - f)) / det
    return float(row), float(col)


def pixel_center(transform: tuple[float, float, float, float, float, float], row: int, col: int) -> tuple[float, float]:
    a, b, c, d, e, f = transform
    cc = col + 0.5
    rr = row + 0.5
    return float(a * cc + b * rr + c), float(d * cc + e * rr + f)


def sample_grid(grid: Grid, x: float, y: float) -> float | None:
    """Nearest pixel on this grid, scaled to physical units. None if unusable, outside, or nodata."""
    if not grid.usable:
        return None
    row_f, col_f = rowcol_of_point(grid.transform, x, y)
    row = math.floor(row_f)
    col = math.floor(col_f)
    height, width = grid.values.shape
    if row < 0 or col < 0 or row >= height or col >= width:
        return None
    raw = grid.values[row, col]
    if _is_nodata(raw, grid.nodata):
        return None
    value = apply_stored_scale(float(raw), grid.scale, grid.offset)
    if not math.isfinite(value):
        return None
    return value


def sample_many(grid: Grid, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Nearest-pixel sample of many points. NaN where sample_grid would return None."""
    out = np.empty(xs.shape, dtype=np.float64)
    # Vectorized path for a usable north-up or general affine, matching sample_grid.
    if not grid.usable:
        out[:] = np.nan
        return out
    a, b, c, d, e, f = grid.transform
    det = a * e - b * d
    col_f = (e * (xs - c) - b * (ys - f)) / det
    row_f = (-d * (xs - c) + a * (ys - f)) / det
    rows = np.floor(row_f).astype(np.int64)
    cols = np.floor(col_f).astype(np.int64)
    height, width = grid.values.shape
    inside = (rows >= 0) & (cols >= 0) & (rows < height) & (cols < width)
    out[:] = np.nan
    if not np.any(inside):
        return out
    raw = grid.values[rows[inside], cols[inside]].astype(np.float64)
    if grid.nodata is not None:
        raw = np.where(raw == grid.nodata, np.nan, raw)
    raw = np.where(np.isfinite(raw), raw, np.nan)
    scaled = raw * grid.scale + grid.offset
    out[inside] = scaled
    return out


def cold_shadow_centers(shadow: Grid, temperature: Grid) -> np.ndarray:
    """Centers of shadow pixels whose Diviner sample is below 110 K.

    Returns an (N, 2) array of map coordinates on the shadow grid.
    Temperature is read from the temperature grid at that center and is not
    resampled onto the shadow pixel as if it were the same resolution.
    """
    if not shadow.usable or not temperature.usable:
        return np.zeros((0, 2), dtype=np.float64)
    physical = shadow.values.astype(np.float64) * shadow.scale + shadow.offset
    if shadow.nodata is not None:
        physical = np.where(shadow.values == shadow.nodata, np.nan, physical)
    rows, cols = np.nonzero(np.isfinite(physical) & (physical >= 0.5))
    if rows.size == 0:
        return np.zeros((0, 2), dtype=np.float64)
    xs, ys = _centers(shadow.transform, rows, cols)
    temps = sample_many(temperature, xs, ys)
    keep = np.isfinite(temps) & (temps < 110.0)
    if not np.any(keep):
        return np.zeros((0, 2), dtype=np.float64)
    return np.column_stack([xs[keep], ys[keep]])


def distance_to_cold_shadow(x: float, y: float, centers: np.ndarray) -> float | None:
    if centers.size == 0:
        return None
    dist = np.hypot(centers[:, 0] - x, centers[:, 1] - y)
    return float(dist.min())


def cuts_for(
    slope_deg: float | None,
    solar_fraction: float | None,
    earth_fraction: float | None,
    temperature_k: float | None,
    permanent_shadow: bool | None,
) -> dict[str, bool | None]:
    """Published screening cuts. Each flag is independent. None means the input was missing."""
    return {
        "slope_under_5_deg": None if slope_deg is None else slope_deg < 5.0,
        "slope_under_8_deg": None if slope_deg is None else slope_deg < 8.0,
        "average_sunlight_above_0_5": None if solar_fraction is None else solar_fraction > 0.5,
        "earth_visibility_at_or_above_0_99": None if earth_fraction is None else earth_fraction >= 0.99,
        "earth_visibility_at_or_above_0_30": None if earth_fraction is None else earth_fraction >= 0.30,
        "temperature_below_110_k": None if temperature_k is None else temperature_k < 110.0,
        "below_75_k_and_inside_permanent_shadow": (
            None
            if temperature_k is None or permanent_shadow is None
            else bool(temperature_k < 75.0 and permanent_shadow)
        ),
    }


def query_point(
    x: float,
    y: float,
    *,
    longitude_deg: float,
    latitude_deg: float,
    extent: str,
    slope: Grid,
    slope_rms: Grid,
    returns: Grid,
    solar: Grid,
    earth: Grid,
    shadow: Grid,
    temperature: Grid,
    cold_centers: np.ndarray | None = None,
) -> dict:
    slope_deg = sample_grid(slope, x, y)
    slope_rms_deg = sample_grid(slope_rms, x, y)
    count = sample_grid(returns, x, y)
    solar_fraction = sample_grid(solar, x, y)
    earth_fraction = sample_grid(earth, x, y)
    shadow_value = sample_grid(shadow, x, y)
    temperature_k = sample_grid(temperature, x, y)
    permanent_shadow = None if shadow_value is None else bool(shadow_value >= 0.5)
    interpolated_gap = None if count is None else bool(count <= 0.0)
    if cold_centers is None:
        cold_centers = cold_shadow_centers(shadow, temperature)
    distance = distance_to_cold_shadow(x, y, cold_centers)
    if distance is None:
        cold_note = "No permanently shadowed pixel below 110 K exists in the loaded extent."
    else:
        cold_note = (
            "Distance in map meters from this point to the nearest permanent-shadow pixel "
            "whose Diviner summer-maximum sample is below 110 K. The temperature sample "
            "stays on the Diviner pixel; it is not a 5 m ice measurement."
        )
    result = {
        "longitude_deg": longitude_deg,
        "latitude_deg": latitude_deg,
        "easting_m": x,
        "northing_m": y,
        "extent": extent,
        "slope_deg": slope_deg,
        "slope_rms_deg": slope_rms_deg,
        "slope_citation": BARKER_2021,
        "slope_frame": slope.frame_note,
        "solar_fraction": solar_fraction,
        "solar_label": SOLAR_LABEL,
        "solar_citation": MAZARICO_2011,
        "solar_frame": solar.frame_note,
        "earth_fraction": earth_fraction,
        "earth_label": EARTH_LABEL,
        "earth_citation": MAZARICO_2011,
        "earth_frame": earth.frame_note,
        "summer_max_temperature_k": temperature_k,
        "temperature_label": TEMPERATURE_LABEL,
        "temperature_resolution_m": temperature.resolution_m,
        "temperature_citation": WILLIAMS_2019,
        "temperature_frame": temperature.frame_note,
        "permanent_shadow": permanent_shadow,
        "permanent_shadow_citation": MAZARICO_2011,
        "permanent_shadow_frame": shadow.frame_note,
        "lola_return_count": count,
        "interpolated_gap": interpolated_gap,
        "return_count_citation": BARKER_2021,
        "return_count_frame": returns.frame_note,
        "cuts": cuts_for(slope_deg, solar_fraction, earth_fraction, temperature_k, permanent_shadow),
        "distance_to_cold_shadow_m": distance,
        "cold_shadow_note": cold_note,
    }
    _reject_fused_score(result)
    return result


def _reject_fused_score(result: dict) -> None:
    banned = {"habitability", "habitability_score", "safety", "safety_score", "score", "fused_score"}
    found = banned.intersection(result)
    if found:
        raise RuntimeError(f"fused score leaked into the query: {sorted(found)}")


def _is_nodata(raw: object, nodata: float | None) -> bool:
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return True
    if not math.isfinite(value):
        return True
    if nodata is None:
        return False
    return value == float(nodata)


def _centers(transform: tuple[float, float, float, float, float, float], rows: np.ndarray, cols: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a, b, c, d, e, f = transform
    cc = cols.astype(np.float64) + 0.5
    rr = rows.astype(np.float64) + 0.5
    xs = a * cc + b * rr + c
    ys = d * cc + e * rr + f
    return xs, ys
