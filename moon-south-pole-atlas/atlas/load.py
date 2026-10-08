"""Read the local rasters into Grid objects. Sampling stays in atlas.sample."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds

from atlas.frame import (
    EARTH_DN_OFFSET,
    EARTH_DN_SCALE,
    ILLUM_SCALE_M,
    PSR_DN_OFFSET,
    PSR_DN_SCALE,
    SOLAR_DN_OFFSET,
    SOLAR_DN_SCALE,
    assess_embedded_crs,
    assess_pds_label,
    illumination_transform,
)
from atlas.sample import (
    BARKER_2021,
    EARTH_LABEL,
    MAZARICO_2011,
    SOLAR_LABEL,
    TEMPERATURE_LABEL,
    WILLIAMS_2019,
    Grid,
)

MARGIN_M = 40_000.0
SITE06_FILES = {
    "slope": "Site06_final_adj_5mpp_slp.tif",
    "slope_rms": "Site06_final_adj_5mpp_slperr.tif",
    "returns": "Site06_final_adj_5mpp_ldec.tif",
}
ILLUM_FILES = {
    "solar": ("AVGVISIB_75S_120M_201608.JP2", "AVGVISIB_75S_120M_201608.LBL", SOLAR_DN_SCALE, SOLAR_DN_OFFSET, SOLAR_LABEL),
    "earth": (
        "AVGVISIB_75S_120M_201608_EARTH.JP2",
        "AVGVISIB_75S_120M_201608_EARTH.LBL",
        EARTH_DN_SCALE,
        EARTH_DN_OFFSET,
        EARTH_LABEL,
    ),
    "shadow": ("LPSR_75S_120M_201608.JP2", "LPSR_75S_120M_201608.LBL", PSR_DN_SCALE, PSR_DN_OFFSET, "Permanent shadow flag, 1 inside, 0 outside."),
}
DIVINER_NAME = "polar_south_80_summer_max-float.tif"

EXTENT = (
    "LOLA Site 06 raster (Nobile Rim 1). The USGS candidate-region outline was not applied. "
    "Sunlight, Earth visibility, permanent shadow, and Diviner temperature were read on their "
    f"native grids inside the Site 06 bounding box expanded by {MARGIN_M / 1000:.0f} km."
)


@dataclass
class Bundle:
    slope: Grid
    slope_rms: Grid
    returns: Grid
    solar: Grid
    earth: Grid
    shadow: Grid
    temperature: Grid
    extent: str
    site_bounds: tuple[float, float, float, float]


def load_bundle(raw_dir: Path) -> Bundle:
    slope = _load_site(raw_dir / SITE06_FILES["slope"], "slope", "degrees", 5.0)
    slope_rms = _load_site(raw_dir / SITE06_FILES["slope_rms"], "slope RMS", "degrees", 5.0)
    returns = _load_site(raw_dir / SITE06_FILES["returns"], "LOLA return count", "count", 5.0)
    bounds = _bounds(slope)
    left, bottom, right, top = bounds
    window_bounds = (left - MARGIN_M, bottom - MARGIN_M, right + MARGIN_M, top + MARGIN_M)
    solar = _load_illumination(raw_dir, "solar", window_bounds)
    earth = _load_illumination(raw_dir, "earth", window_bounds)
    shadow = _load_illumination(raw_dir, "shadow", window_bounds)
    temperature = _load_diviner(raw_dir / DIVINER_NAME, window_bounds)
    return Bundle(
        slope=slope,
        slope_rms=slope_rms,
        returns=returns,
        solar=solar,
        earth=earth,
        shadow=shadow,
        temperature=temperature,
        extent=EXTENT,
        site_bounds=bounds,
    )


def _load_site(path: Path, name: str, unit: str, expected_pixel_m: float) -> Grid:
    with rasterio.open(path) as src:
        values = src.read(1)
        transform = _affine(src.transform)
        crs_wkt = src.crs.to_wkt() if src.crs else None
        nodata = None if src.nodata is None else float(src.nodata)
        pixel = (abs(src.transform.a), abs(src.transform.e))
    assessment = assess_embedded_crs(crs_wkt, pixel, expected_pixel_m)
    if not assessment.usable:
        # Product README at the same archive states the frame. Accept only when
        # the pixel size matches and the CRS is simply absent or local.
        if _pixel_ok(pixel, expected_pixel_m) and _crs_is_unstated(crs_wkt):
            assessment = _documented_site_frame(pixel, path.name)
        else:
            assessment = assessment
    return Grid(
        values=values,
        transform=transform,
        nodata=nodata,
        scale=1.0,
        offset=0.0,
        resolution_m=float(pixel[0]),
        usable=assessment.usable,
        frame_note=f"{name}: {assessment.note}",
        citation=BARKER_2021,
        value_label=unit,
    )


def _documented_site_frame(pixel: tuple[float, float], filename: str):
    from atlas.frame import FrameAssessment

    return FrameAssessment(
        usable=True,
        agrees=True,
        source="product-readme",
        note=(
            f"{filename} has no embedded IAU/DE421 CRS. The LOLA 5 m/pixel product README "
            "states south-polar stereographic X/Y meters in the MOON_ME frame of DE421, "
            f"GMT pixel registration. Measured pixel size is {pixel[0]:.4f} by {pixel[1]:.4f} m, "
            "which matches 5 m. Sampled in that documented frame; the missing embedded CRS is recorded here."
        ),
    )


def _load_illumination(raw_dir: Path, key: str, bounds: tuple[float, float, float, float]) -> Grid:
    filename, label_name, dn_scale, dn_offset, value_label = ILLUM_FILES[key]
    path = raw_dir / filename
    label_path = raw_dir / label_name
    label_text = label_path.read_text() if label_path.exists() else ""
    label_assessment = assess_pds_label(label_text, ILLUM_SCALE_M) if label_text else None
    with rasterio.open(path) as src:
        embedded = assess_embedded_crs(
            src.crs.to_wkt() if src.crs else None,
            (abs(src.transform.a), abs(src.transform.e)),
            ILLUM_SCALE_M,
        )
        if embedded.usable:
            transform = _affine(src.transform)
            assessment_note = embedded.note + _label_origin_note(transform)
            usable = True
            full_transform = transform
            height, width = src.height, src.width
        elif label_assessment is not None and label_assessment.usable and src.width == 7624 and src.height == 7624:
            full_transform = illumination_transform()
            transform = full_transform
            assessment_note = label_assessment.note + " Embedded CRS was absent or not the frame, so the PDS label grid is used."
            usable = True
            height, width = src.height, src.width
        else:
            full_transform = _affine(src.transform)
            transform = full_transform
            assessment_note = embedded.note
            if label_assessment is not None:
                assessment_note += " " + label_assessment.note
            usable = False
            height, width = src.height, src.width
        if usable:
            window = _window_for(full_transform, height, width, bounds)
            values = src.read(1, window=window)
            transform = _window_transform(full_transform, window)
        else:
            values = np.zeros((1, 1), dtype=np.float32)
    scale, offset, scale_note = _visibility_scale(values, dn_scale, dn_offset, key)
    citation = MAZARICO_2011
    return Grid(
        values=values,
        transform=transform,
        nodata=None,
        scale=scale,
        offset=offset,
        resolution_m=ILLUM_SCALE_M if usable else float("nan"),
        usable=usable,
        frame_note=f"{key}: {assessment_note} {scale_note}",
        citation=citation,
        value_label=value_label,
    )


def _load_diviner(path: Path, bounds: tuple[float, float, float, float]) -> Grid:
    with rasterio.open(path) as src:
        pixel = (abs(src.transform.a), abs(src.transform.e))
        # Diviner's published bin is 240 m. Accept a measured size near that.
        expected = 240.0 if _pixel_ok(pixel, 240.0) else pixel[0]
        embedded = assess_embedded_crs(src.crs.to_wkt() if src.crs else None, pixel, expected if expected else 240.0)
        if embedded.usable:
            full_transform = _affine(src.transform)
            usable = True
            note = embedded.note
        elif _pixel_ok(pixel, 240.0) and _crs_is_unstated(src.crs.to_wkt() if src.crs else None):
            full_transform = _affine(src.transform)
            usable = True
            note = (
                "Diviner summer-maximum GeoTIFF has no embedded IAU CRS. "
                f"Measured pixel size is {pixel[0]:.4f} by {pixel[1]:.4f} m, matching the 240 m "
                "Williams et al. 2019 polar stereographic bin. The archive readme states x,y "
                "distances from the pole on the 1737.4 km sphere. Sampled on that documented "
                "grid; the missing embedded CRS is recorded here and the value is not called a 5 m measurement."
            )
        else:
            full_transform = _affine(src.transform)
            usable = False
            note = embedded.note + (
                f" Measured pixel size {pixel[0]:.4f} by {pixel[1]:.4f} m."
            )
        if usable:
            window = _window_for(full_transform, src.height, src.width, bounds)
            values = src.read(1, window=window)
            transform = _window_transform(full_transform, window)
            nodata = None if src.nodata is None else float(src.nodata)
        else:
            values = np.zeros((1, 1), dtype=np.float32)
            transform = full_transform
            nodata = None
        resolution = float(pixel[0])
    return Grid(
        values=values,
        transform=transform,
        nodata=nodata,
        scale=1.0,
        offset=0.0,
        resolution_m=resolution,
        usable=usable,
        frame_note=f"temperature: {note}",
        citation=WILLIAMS_2019,
        value_label=TEMPERATURE_LABEL,
    )


def _label_origin_note(embedded: tuple[float, float, float, float, float, float]) -> str:
    """The PDS offset and the embedded JPEG2000 origin differ by one pixel. Say so."""
    label = illumination_transform()
    dx = embedded[2] - label[2]
    dy = embedded[5] - label[5]
    if abs(dx) <= 1.0 and abs(dy) <= 1.0:
        return " PDS label origin matches the embedded grid."
    return (
        f" The PDS label offset 3811.5 places the upper-left corner at "
        f"({label[2]:.1f}, {label[5]:.1f}) m. The embedded grid places it at "
        f"({embedded[2]:.1f}, {embedded[5]:.1f}) m, a difference of ({dx:.1f}, {dy:.1f}) m. "
        "That is one 120 m pixel. The embedded grid is the one sampled; the label origin is not substituted for it."
    )


def _visibility_scale(values: np.ndarray, dn_scale: float, dn_offset: float, key: str) -> tuple[float, float, str]:
    if values.size == 0 or not np.issubdtype(values.dtype, np.integer):
        return 1.0, 0.0, "Stored values are floating point; PDS DN scale was not applied."
    # Integer JPEG2000 / IMG samples are digital numbers.
    return dn_scale, dn_offset, f"Applied PDS DN scale {dn_scale} and offset {dn_offset} for {key}."


def _window_for(transform: tuple[float, float, float, float, float, float], height: int, width: int, bounds: tuple[float, float, float, float]) -> Window:
    from rasterio.transform import Affine

    affine = Affine(*transform)
    window = from_bounds(*bounds, transform=affine)
    window = window.intersection(Window(0, 0, width, height))
    # Rounding outward keeps every pixel that touches the box.
    row_off = max(0, int(np.floor(window.row_off)))
    col_off = max(0, int(np.floor(window.col_off)))
    row_end = min(height, int(np.ceil(window.row_off + window.height)))
    col_end = min(width, int(np.ceil(window.col_off + window.width)))
    if row_end <= row_off or col_end <= col_off:
        raise ValueError(f"window does not intersect the raster: {bounds}")
    return Window(col_off, row_off, col_end - col_off, row_end - row_off)


def _window_transform(transform: tuple[float, float, float, float, float, float], window: Window) -> tuple[float, float, float, float, float, float]:
    a, b, c, d, e, f = transform
    col0 = float(window.col_off)
    row0 = float(window.row_off)
    return (a, b, a * col0 + b * row0 + c, d, e, d * col0 + e * row0 + f)


def _bounds(grid: Grid) -> tuple[float, float, float, float]:
    height, width = grid.values.shape
    a, b, c, d, e, f = grid.transform
    corners = []
    for row, col in ((0, 0), (0, width), (height, 0), (height, width)):
        corners.append((a * col + b * row + c, d * col + e * row + f))
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    return min(xs), min(ys), max(xs), max(ys)


def _affine(transform) -> tuple[float, float, float, float, float, float]:
    return (transform.a, transform.b, transform.c, transform.d, transform.e, transform.f)


def _pixel_ok(pixel: tuple[float, float], expected: float) -> bool:
    tol = max(0.05, 0.02 * expected)
    return abs(pixel[0] - expected) <= tol and abs(pixel[1] - expected) <= tol


def _crs_is_unstated(crs_wkt: str | None) -> bool:
    if not crs_wkt:
        return True
    text = crs_wkt.lower()
    if "engineering" in text or "local_cs" in text or "unknown" in text:
        return True
    return False
