"""South-polar stereographic frame used by the LOLA products.

True scale at the pole, sphere radius 1737.4 km, longitude of origin 0,
Mean Earth / polar axis of DE421. Map units are meters.
"""

from __future__ import annotations

from dataclasses import dataclass

from pyproj import CRS, Transformer

RADIUS_M = 1_737_400.0
RADIUS_TOLERANCE_M = 1.0
LAT0 = -90.0
LON0 = 0.0

# PDS label of the 75°S / 120 m illumination grids (pixel registration).
ILLUM_SIZE = 7624
ILLUM_SCALE_M = 120.0
ILLUM_OFFSET_PIX = 3811.5  # 1-based sample and line of the pole

SOLAR_DN_SCALE = 0.00004
SOLAR_DN_OFFSET = 0.0
EARTH_DN_SCALE = 0.00004
EARTH_DN_OFFSET = 0.0
# PERMANENT_SHADOW = DN * 0.000025 + 0.5, so ±20000 maps to 1 and 0.
PSR_DN_SCALE = 0.000025
PSR_DN_OFFSET = 0.5

MOON_XY = CRS.from_proj4(
    f"+proj=stere +lat_0={LAT0} +lat_ts={LAT0} +lon_0={LON0} "
    f"+R={RADIUS_M} +units=m +no_defs +type=crs"
)
MOON_LONLAT = CRS.from_proj4(f"+proj=longlat +R={RADIUS_M} +no_defs +type=crs")
_TO_XY = Transformer.from_crs(MOON_LONLAT, MOON_XY, always_xy=True)
_TO_LONLAT = Transformer.from_crs(MOON_XY, MOON_LONLAT, always_xy=True)


def lonlat_to_xy(longitude_deg: float, latitude_deg: float) -> tuple[float, float]:
    x, y = _TO_XY.transform(longitude_deg, latitude_deg)
    return float(x), float(y)


def xy_to_lonlat(x_m: float, y_m: float) -> tuple[float, float]:
    lon, lat = _TO_LONLAT.transform(x_m, y_m)
    return float(lon), float(lat)


def illumination_transform() -> tuple[float, float, float, float, float, float]:
    """Rasterio-style affine for the 75°S illumination grids.

    (a, b, c, d, e, f) maps the upper-left corner of a pixel:
    x = a * col + b * row + c, y = d * col + e * row + f.
    Derived from the PDS offsets, which place the pole on the boundary
    between the four central pixels of the even-sized grid.
    """
    scale = ILLUM_SCALE_M
    # Upper-left corner of pixel (0, 0). Pole is at sample/line 3811.5 (1-based).
    c = (0.5 - ILLUM_OFFSET_PIX) * scale
    f = (ILLUM_OFFSET_PIX - 0.5) * scale
    return (scale, 0.0, c, 0.0, -scale, f)


@dataclass(frozen=True)
class FrameAssessment:
    usable: bool
    agrees: bool
    source: str
    note: str


def assess_embedded_crs(crs_wkt: str | None, pixel_size_m: tuple[float, float], expected_pixel_m: float) -> FrameAssessment:
    """Decide whether an embedded CRS is the south-polar DE421 frame.

    A missing CRS is not treated as that frame. A present CRS is usable only
    when it is polar stereographic, true at the south pole, on a sphere of
    1737.4 km, and the pixel size matches the product.
    """
    px = abs(pixel_size_m[0])
    py = abs(pixel_size_m[1])
    size_ok = (
        abs(px - expected_pixel_m) <= max(0.05, 0.01 * expected_pixel_m)
        and abs(py - expected_pixel_m) <= max(0.05, 0.01 * expected_pixel_m)
    )
    if not crs_wkt:
        return FrameAssessment(
            usable=False,
            agrees=False,
            source="none",
            note=(
                "No embedded CRS. Not treated as south-polar stereographic "
                "1737.4 km MOON_ME/DE421."
            ),
        )
    try:
        crs = CRS.from_wkt(crs_wkt)
    except Exception:
        crs = None
    if crs is None:
        try:
            crs = CRS.from_user_input(crs_wkt)
        except Exception as exc:
            return FrameAssessment(
                usable=False,
                agrees=False,
                source="embedded",
                note=f"Embedded CRS could not be parsed ({exc}). Not used.",
            )
    proj = (crs.to_proj4() or "").lower()
    radius = _radius_m(crs)
    lat0 = _proj_param(proj, "lat_0")
    lon0 = _proj_param(proj, "lon_0")
    lat_ts = _proj_param(proj, "lat_ts")
    is_stere = "stere" in proj
    radius_ok = radius is not None and abs(radius - RADIUS_M) <= RADIUS_TOLERANCE_M
    pole_ok = lat0 is not None and abs(lat0 - LAT0) < 1e-6
    lon_ok = lon0 is None or abs(lon0 - LON0) < 1e-6
    # lat_ts=-90 is the true-scale parallel. Absent is accepted; a different parallel is not.
    ts_ok = lat_ts is None or abs(lat_ts - LAT0) <= 1e-3
    agrees = bool(is_stere and radius_ok and pole_ok and lon_ok and ts_ok and size_ok)
    parts = [
        f"proj4={proj.strip()}",
        f"radius_m={radius}",
        f"pixel_m=({px:.4f}, {py:.4f})",
        f"expected_pixel_m={expected_pixel_m}",
    ]
    if agrees:
        note = "Embedded CRS matches south-polar stereographic, 1737.4 km, lon0=0. " + "; ".join(parts)
    else:
        note = (
            "Embedded CRS does not match south-polar stereographic 1737.4 km "
            "MOON_ME/DE421, so this grid is not sampled as that frame. "
            + "; ".join(parts)
        )
    return FrameAssessment(usable=agrees, agrees=agrees, source="embedded", note=note)


def assess_pds_label(label_text: str, expected_scale_m: float) -> FrameAssessment:
    """A PDS label is usable only when it states this frame in its own words."""
    text = " ".join(label_text.split())
    loose_missing = []
    if "POLAR STEREOGRAPHIC" not in text:
        loose_missing.append("POLAR STEREOGRAPHIC")
    if "1737.4" not in text:
        loose_missing.append("1737.4 km radius")
    if "MEAN EARTH/POLAR AXIS OF DE421" not in text:
        loose_missing.append("MOON_ME/DE421")
    if "CENTER_LATITUDE" not in text or "-90" not in text:
        loose_missing.append("center latitude -90")
    if "CENTER_LONGITUDE" not in text:
        loose_missing.append("center longitude")
    scale_token = f"{expected_scale_m:.0f}" if expected_scale_m >= 1 else str(expected_scale_m)
    if f"MAP_SCALE                    = {scale_token}" not in label_text and scale_token not in text:
        loose_missing.append(f"map scale {expected_scale_m} m")
    if loose_missing:
        return FrameAssessment(
            usable=False,
            agrees=False,
            source="pds-label",
            note="PDS label does not state the expected frame: " + ", ".join(loose_missing),
        )
    return FrameAssessment(
        usable=True,
        agrees=True,
        source="pds-label",
        note=(
            "No embedded CRS on the raster. The PDS label states polar stereographic, "
            "radius 1737.4 km, Mean Earth/polar axis of DE421, center latitude -90, "
            f"center longitude 0, map scale {expected_scale_m:.0f} m/pixel. "
            "The grid is sampled in that frame because the label says so."
        ),
    )


def _radius_m(crs: CRS) -> float | None:
    proj = crs.to_proj4() or ""
    radius = _proj_param(proj.lower(), "r")
    if radius is not None:
        return radius
    try:
        ell = crs.ellipsoid
    except Exception:
        return None
    if ell is None:
        return None
    a = getattr(ell, "semi_major_metre", None)
    return float(a) if a is not None else None


def _proj_param(proj4: str, name: str) -> float | None:
    token = f"+{name}="
    if token not in proj4:
        return None
    raw = proj4.split(token, 1)[1].split()[0]
    try:
        return float(raw)
    except ValueError:
        return None
