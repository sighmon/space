"""Write the download manifest and the georeferencing record."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import rasterio

from atlas.frame import assess_embedded_crs, illumination_transform
from atlas.load import DIVINER_NAME, SITE06_FILES

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

RASTERS = [
    (
        "Site06_final_adj_5mpp_slp.tif",
        "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site06/Site06_final_adj_5mpp_slp.tif",
        5.0,
    ),
    (
        "Site06_final_adj_5mpp_slperr.tif",
        "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site06/Site06_final_adj_5mpp_slperr.tif",
        5.0,
    ),
    (
        "Site06_final_adj_5mpp_ldec.tif",
        "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site06/Site06_final_adj_5mpp_ldec.tif",
        5.0,
    ),
    (
        "AVGVISIB_75S_120M_201608.JP2",
        "http://imbrium.mit.edu/EXTRAS/ILLUMINATION/JP2/AVGVISIB_75S_120M_201608.JP2",
        120.0,
    ),
    (
        "AVGVISIB_75S_120M_201608_EARTH.JP2",
        "http://imbrium.mit.edu/EXTRAS/ILLUMINATION/JP2/AVGVISIB_75S_120M_201608_EARTH.JP2",
        120.0,
    ),
    (
        "LPSR_75S_120M_201608.JP2",
        "http://imbrium.mit.edu/EXTRAS/ILLUMINATION/JP2/LPSR_75S_120M_201608.JP2",
        120.0,
    ),
    (
        DIVINER_NAME,
        "http://luna1.diviner.ucla.edu/~jpierre/diviner/level4_polar/additional_maps/polar_south_80_summer_max-float.tif",
        240.0,
    ),
]


def write_manifest(path: Path | None = None) -> Path:
    path = path or (ROOT / "data" / "MANIFEST.tsv")
    lines = ["filename\turl\tfetched_utc\tsha256\tbytes"]
    for name, url, _expected in RASTERS:
        file_path = RAW / name
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        fetched = datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        lines.append(f"{name}\t{url}\t{fetched}\t{digest}\t{file_path.stat().st_size}")
    path.write_text("\n".join(lines) + "\n")
    return path


def write_georef(path: Path | None = None) -> Path:
    path = path or (ROOT / "docs" / "georef.md")
    paragraphs = [
        "# Georeferencing check",
        "",
        "Expected frame: south-polar stereographic, true scale at the pole, sphere radius 1737.4 km, "
        "longitude of origin 0, Mean Earth / polar axis of DE421. Map units are meters.",
        "",
        "The reported extent is the LOLA Site 06 raster (Nobile Rim 1). "
        "The USGS candidate-region outline was not applied.",
        "",
    ]
    for name, _url, expected in RASTERS:
        file_path = RAW / name
        with rasterio.open(file_path) as src:
            pixel = (abs(src.transform.a), abs(src.transform.e))
            wkt = src.crs.to_wkt() if src.crs else None
            assessment = assess_embedded_crs(wkt, pixel, expected)
            paragraphs.append(f"## {name}")
            paragraphs.append("")
            paragraphs.append(f"- Usable in the expected frame: {assessment.usable}")
            paragraphs.append(f"- Pixel size: {pixel[0]:.4f} by {pixel[1]:.4f} m (expected {expected:g} m)")
            paragraphs.append(f"- Upper left: ({src.transform.c:.3f}, {src.transform.f:.3f}) m")
            paragraphs.append(f"- CRS name: {src.crs.to_string() if src.crs else 'none'}")
            paragraphs.append(f"- Note: {assessment.note}")
            paragraphs.append("")
    label = illumination_transform()
    with rasterio.open(RAW / "AVGVISIB_75S_120M_201608.JP2") as src:
        dx = src.transform.c - label[2]
        dy = src.transform.f - label[5]
        embedded_corner = (src.transform.c, src.transform.f)
    paragraphs.extend(
        [
            "## Label origin versus embedded illumination grid",
            "",
            "The PDS labels for the 75°S / 120 m grids state polar stereographic, radius 1737.4 km, "
            "Mean Earth/polar axis of DE421, center latitude −90, center longitude 0, and "
            "LINE_PROJECTION_OFFSET = SAMPLE_PROJECTION_OFFSET = 3811.5. "
            "Reading that offset as a 1-based pixel-center coordinate puts the upper-left corner at "
            f"({label[2]:.1f}, {label[5]:.1f}) m.",
            "",
            "The JPEG2000 files carry their own polar-stereographic CRS (radius 1737.4 km, "
            "latitude of origin −90, central meridian 0). "
            f"Their embedded upper-left corner is ({embedded_corner[0]:.1f}, {embedded_corner[1]:.1f}) m, "
            f"which differs by ({dx:.1f}, {dy:.1f}) m. "
            "The CRS name string on those files says `Moon2000_npole` even though the projection "
            "parameters are the south pole. The parameters are what get used. "
            "The embedded grid is sampled. The label origin is not substituted for it.",
            "",
            "Diviner's summer-maximum GeoTIFF measures 240.036 m per pixel against the published 240 m bin. "
            "That difference is inside the frame check, and the temperature is quoted at the measured spacing, "
            "not as a 5 m value.",
            "",
            "Site 06's datum is named `unknown` inside the GeoTIFF. The spheroid radius is 1737400 m and the "
            "projection is polar stereographic with latitude of origin −90. That matches the frame. "
            "The product README at the same archive states the MOON_ME / DE421 axes for these files.",
            "",
        ]
    )
    # Keep the site-file names referenced so a rename of the load table is noticed.
    paragraphs.append("Site 06 files checked: " + ", ".join(SITE06_FILES.values()) + ".")
    paragraphs.append("")
    path.write_text("\n".join(paragraphs))
    return path


if __name__ == "__main__":
    print(write_manifest())
    print(write_georef())
