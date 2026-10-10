"""Export the home-screen backdrop image (web/data/backdrop.webp).

The backdrop is the LOLA/Mazarico et al. 2011 average-sunlight-visibility
raster (AVGVISIB_75S_120M_201608, 120 m) resampled from south-polar
stereographic to the azimuthal-equidistant layout used by web/index.html
(radius proportional to colatitude, longitude 0 straight up, covering
+/-EXT degrees of colatitude). Tone only: it is not a hillshade, not an
elevation model and carries no values. Marker positions come from the same
latitude/longitude, so they line up with the real terrain.

    python -m atlas.export_backdrop [--size 2048]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

from atlas.frame import RADIUS_M, SOLAR_DN_SCALE, illumination_transform

EXT = 8.5  # degrees of colatitude from the pole to the image edge; keep equal to EXT in web/index.html
RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "AVGVISIB_75S_120M_201608.JP2"
OUT = Path(__file__).resolve().parents[1] / "web" / "data" / "backdrop.webp"


def render(size: int) -> Image.Image:
    with rasterio.open(RAW) as src:
        v = src.read(1).astype(np.float32) * SOLAR_DN_SCALE
    a, _, c, _, e, f = illumination_transform()
    ax = (np.arange(size, dtype=np.float64) + 0.5 - size / 2) / (size / 2)
    X, Y = np.meshgrid(ax, ax)
    rr = np.hypot(X, Y)
    colat = rr * np.radians(EXT)
    rho = 2 * RADIUS_M * np.tan(colat / 2)
    sx, sy = X / np.maximum(rr, 1e-12), -Y / np.maximum(rr, 1e-12)  # sin(lon), cos(lon); lon 0 is up
    x, y = rho * sx, rho * sy
    col = (x - c) / a - 0.5
    row = (y - f) / e - 0.5
    # bilinear sample (downsampling 120 m -> ~255 m/px at 2048; average 2x2 first to avoid aliasing)
    k = max(1, int(round((2 * RADIUS_M * np.tan(np.radians(EXT) / 2) * 2 / size) / abs(a))))
    if k > 1:
        n = (v.shape[0] // k) * k
        v = v[:n, :n].reshape(n // k, k, n // k, k).mean(axis=(1, 3))
        col = (col + 0.5) / k - 0.5
        row = (row + 0.5) / k - 0.5
    c0 = np.clip(np.floor(col).astype(int), 0, v.shape[1] - 2)
    r0 = np.clip(np.floor(row).astype(int), 0, v.shape[0] - 2)
    fx, fy = np.clip(col - c0, 0, 1), np.clip(row - r0, 0, 1)
    s = (v[r0, c0] * (1 - fx) * (1 - fy) + v[r0, c0 + 1] * fx * (1 - fy)
         + v[r0 + 1, c0] * (1 - fx) * fy + v[r0 + 1, c0 + 1] * fx * fy)
    # tone: gentle curve so shadowed ground stays dark but legible, lit ridges stay below white
    t = np.clip(s / 0.9, 0, 1) ** 0.8
    fade = np.clip(1 - rr ** 4, 0, 1)
    g = (t * 0.92 + 0.02) * fade
    rgb = np.stack([g * 226 + 3, g * 231 + 4, g * 238 + 6], axis=-1)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--size", type=int, default=2048)
    p.add_argument("--quality", type=int, default=80)
    args = p.parse_args()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    render(args.size).save(OUT, "WEBP", quality=args.quality, method=6)
    print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
