"""Local horizon and disc visibility.

Pure functions of positions and an elevation grid. No file I/O and no ephemeris.
A disc is visible when its center altitude plus angular radius is strictly above
the terrain horizon in that azimuth. The two observer heights are never merged.
"""

from __future__ import annotations

import math

import numpy as np

from atlas.frame import RADIUS_M, xy_to_lonlat, xy_to_lonlat_array

# Nominal solar radius, and the IAU equatorial radius of Earth.
SUN_RADIUS_M = 695_700_000.0
EARTH_EQUATORIAL_RADIUS_M = 6_378_137.0

AZIMUTH_BINS = 720  # 0.5 degree bins, from north toward east
MIN_HORIZONTAL_M = 2.5  # half of a 5 m Site 06 pixel; skips the observer pixel


def disc_above_horizon(center_altitude_rad, angular_radius_rad, horizon_altitude_rad):
    """True where any part of the disc is above the terrain horizon."""
    center = np.asarray(center_altitude_rad, dtype=np.float64)
    radius = np.asarray(angular_radius_rad, dtype=np.float64)
    horizon = np.asarray(horizon_altitude_rad, dtype=np.float64)
    if np.any(radius < 0.0):
        raise ValueError("angular radius must be non-negative")
    visible = center + radius > horizon
    if visible.shape == ():
        return bool(visible)
    return visible


def angular_radius_rad(distance_m, body_radius_m):
    distance = np.asarray(distance_m, dtype=np.float64)
    radius = np.asarray(body_radius_m, dtype=np.float64)
    ratio = radius / distance
    if np.any(ratio >= 1.0) or np.any(distance <= 0.0):
        raise ValueError("body radius must be smaller than the distance to the body")
    return np.arcsin(ratio)


def position_xyz(longitude_deg, latitude_deg, radius_m):
    """MOON_ME cartesian meters. Radius is from the Moon's center."""
    lon = np.radians(np.asarray(longitude_deg, dtype=np.float64))
    lat = np.radians(np.asarray(latitude_deg, dtype=np.float64))
    radius = np.asarray(radius_m, dtype=np.float64)
    cos_lat = np.cos(lat)
    xyz = (
        radius * cos_lat * np.cos(lon),
        radius * cos_lat * np.sin(lon),
        radius * np.sin(lat),
    )
    return np.stack(xyz, axis=-1)


def enu_axes(longitude_deg: float, latitude_deg: float):
    """Local east, north, and up at one surface point. Each vector has shape (3,)."""
    lon = math.radians(longitude_deg)
    lat = math.radians(latitude_deg)
    east = np.array((-math.sin(lon), math.cos(lon), 0.0), dtype=np.float64)
    north = np.array(
        (-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon), math.cos(lat)),
        dtype=np.float64,
    )
    up = np.array((math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)), dtype=np.float64)
    return east, north, up


def bin_center_azimuth(index: int, n_bins: int) -> float:
    return (index + 0.5) * (2.0 * math.pi) / n_bins


def horizontal_direction(east: np.ndarray, north: np.ndarray, azimuth_rad: float) -> np.ndarray:
    """Unit horizontal vector. Azimuth is radians from north toward east."""
    return math.sin(azimuth_rad) * np.asarray(east, dtype=np.float64) + math.cos(azimuth_rad) * np.asarray(north, dtype=np.float64)


def terrain_horizon(
    observer_xyz: np.ndarray,
    target_xyz: np.ndarray,
    east: np.ndarray,
    north: np.ndarray,
    *,
    n_bins: int = AZIMUTH_BINS,
    min_horizontal_m: float = 0.0,
) -> np.ndarray:
    """Maximum terrain elevation angle in each azimuth bin.

    Empty bins stay at -pi/2, which hides nothing above the nadir.
    ``target_xyz`` has shape (N, 3).
    """
    horizon = np.full(n_bins, -0.5 * math.pi, dtype=np.float64)
    targets = np.asarray(target_xyz, dtype=np.float64)
    if targets.size == 0:
        return horizon
    if targets.ndim == 1:
        targets = targets.reshape(1, 3)
    _accumulate(horizon, np.asarray(observer_xyz, dtype=np.float64), east, north, targets, min_horizontal_m)
    return horizon


def horizon_from_elevation(
    elevation_m: np.ndarray,
    transform: tuple[float, float, float, float, float, float],
    *,
    observer_x_m: float,
    observer_y_m: float,
    surface_elevation_m: float,
    height_m: float,
    nodata: float | None = None,
    n_bins: int = AZIMUTH_BINS,
    min_horizontal_m: float = MIN_HORIZONTAL_M,
) -> np.ndarray:
    """Horizon from a Site 06-style elevation grid already in memory.

    Observer height is meters above ``surface_elevation_m``, along the local
    radius. Curvature is the 3D MOON_ME position of each pixel, not a flat map.
    """
    values = np.asarray(elevation_m, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("elevation grid must be 2-D")
    nrows, ncols = values.shape
    a, b, c, d, e, f = transform
    longitude, latitude = xy_to_lonlat(observer_x_m, observer_y_m)
    observer = position_xyz(longitude, latitude, RADIUS_M + surface_elevation_m + height_m)
    east, north, _up = enu_axes(longitude, latitude)
    horizon = np.full(n_bins, -0.5 * math.pi, dtype=np.float64)
    columns = np.arange(ncols, dtype=np.float64)
    finite_nodata = nodata is not None and math.isfinite(float(nodata))
    for row0 in range(0, nrows, 500):
        row1 = min(nrows, row0 + 500)
        rows = np.arange(row0, row1, dtype=np.float64)
        rr, cc = np.meshgrid(rows, columns, indexing="ij")
        xs = a * (cc + 0.5) + b * (rr + 0.5) + c
        ys = d * (cc + 0.5) + e * (rr + 0.5) + f
        elev = values[row0:row1]
        valid = np.isfinite(elev)
        if finite_nodata:
            valid &= elev != float(nodata)
        if not np.any(valid):
            continue
        lons, lats = xy_to_lonlat_array(xs[valid], ys[valid])
        targets = position_xyz(lons, lats, RADIUS_M + elev[valid])
        _accumulate(horizon, observer, east, north, targets, min_horizontal_m)
    return horizon


def topocentric(observer_xyz, east, north, body_xyz) -> tuple[float, float, float]:
    """Altitude (rad), azimuth (rad from north toward east), and distance (m)."""
    delta = np.asarray(body_xyz, dtype=np.float64) - np.asarray(observer_xyz, dtype=np.float64)
    distance = float(np.linalg.norm(delta))
    altitude, azimuth = _alt_az(np.asarray(observer_xyz, dtype=np.float64), east, north, delta, distance)
    return float(altitude), float(azimuth), distance


def visibility_mask(observer_xyz, east, north, body_xyz, body_radius_m, horizon) -> np.ndarray:
    """Whether the disc clears the terrain horizon at each body position. Shape (N,)."""
    observer = np.asarray(observer_xyz, dtype=np.float64)
    bodies = np.asarray(body_xyz, dtype=np.float64)
    if bodies.ndim == 1:
        bodies = bodies.reshape(1, 3)
    delta = bodies - observer
    distance = np.linalg.norm(delta, axis=1)
    up = observer / np.linalg.norm(observer)
    sin_alt = np.clip((delta @ up) / distance, -1.0, 1.0)
    altitude = np.arcsin(sin_alt)
    azimuth = np.mod(np.arctan2(delta @ east, delta @ north), 2.0 * math.pi)
    n_bins = len(horizon)
    index = np.minimum((azimuth * n_bins / (2.0 * math.pi)).astype(np.int64), n_bins - 1)
    radius = angular_radius_rad(distance, body_radius_m)
    visible = disc_above_horizon(altitude, radius, np.asarray(horizon, dtype=np.float64)[index])
    return np.asarray(visible, dtype=bool)


def _accumulate(horizon, observer, east, north, targets, min_horizontal_m: float) -> None:
    delta = targets - observer
    horizontal = np.sqrt((delta @ east) ** 2 + (delta @ north) ** 2)
    keep = horizontal > min_horizontal_m
    if not np.any(keep):
        return
    delta = delta[keep]
    distance = np.linalg.norm(delta, axis=1)
    up = observer / np.linalg.norm(observer)
    sin_alt = np.clip((delta @ up) / distance, -1.0, 1.0)
    altitude = np.arcsin(sin_alt)
    azimuth = np.mod(np.arctan2(delta @ east, delta @ north), 2.0 * math.pi)
    n_bins = horizon.shape[0]
    index = np.minimum((azimuth * n_bins / (2.0 * math.pi)).astype(np.int64), n_bins - 1)
    np.maximum.at(horizon, index, altitude)


def _alt_az(observer, east, north, delta, distance: float) -> tuple[float, float]:
    up = observer / np.linalg.norm(observer)
    altitude = math.asin(float(np.clip(np.dot(delta, up) / distance, -1.0, 1.0)))
    azimuth = math.atan2(float(np.dot(delta, east)), float(np.dot(delta, north))) % (2.0 * math.pi)
    return altitude, azimuth
