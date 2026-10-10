"""Sun and Earth vectors in the MOON_ME frame from local SPICE kernels.

No network calls. If a kernel file is missing, this raises and does not invent a vector.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from skyfield.api import PlanetaryConstants, load, load_file

EPHEMERIS_NAME = "DE421"
EPHEMERIS_DETAIL = (
    "JPL DE421 planetary ephemeris (de421.bsp), lunar orientation "
    "moon_pa_de421_1900-2050.bpc, and the MOON_ME frame defined by moon_080317.tf. "
    "In that kernel MOON_ME is an identity alias of MOON_ME_DE421. "
    "Directions include light time from the Moon and do not include stellar aberration. "
    "UTC is converted with Skyfield 1.53 builtin leap-second and delta-T tables "
    "(the 2017-01-01 leap second is the last one; the 2025 window contains none). "
    "naif0012.tls is kept with the kernels as the leap-second archive. "
    "No lunar refraction."
)

_KERNEL_FILES = (
    "de421.bsp",
    "moon_pa_de421_1900-2050.bpc",
    "moon_080317.tf",
    "naif0012.tls",
)


def utc_hours(start: datetime, count: int) -> list[datetime]:
    if start.tzinfo is None:
        raise ValueError("start must be timezone-aware UTC")
    return [start + timedelta(hours=hour) for hour in range(count)]


def moon_centered_vectors_m(kernel_dir: Path, when: list[datetime]) -> dict[str, np.ndarray]:
    """Moon-centered Sun and Earth positions in MOON_ME, meters, shape (N, 3)."""
    missing = [name for name in _KERNEL_FILES if not (kernel_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(
            "SPICE kernels are not on disk, so no Sun or Earth vector was computed: " + ", ".join(missing)
        )
    timescale = load.timescale(builtin=True)
    ephemeris = load_file(str(kernel_dir / "de421.bsp"))
    constants = PlanetaryConstants()
    constants.read_text(open(kernel_dir / "moon_080317.tf", "rb"))
    # The binary PCK must stay open; Skyfield reads it when rotating vectors.
    constants.read_binary(open(kernel_dir / "moon_pa_de421_1900-2050.bpc", "rb"))
    alias = np.array(constants.variables["TKFRAME_31001_MATRIX"], dtype=np.float64).reshape(3, 3)
    if not np.array_equal(alias, np.eye(3)):
        raise RuntimeError("moon_080317.tf does not make MOON_ME an identity alias of MOON_ME_DE421")
    if constants.variables.get("FRAME_31001_NAME") != "MOON_ME":
        raise RuntimeError("moon_080317.tf does not name frame 31001 MOON_ME")
    frame = constants.build_frame_named("MOON_ME_DE421")
    times = timescale.from_datetimes(when)
    moon = ephemeris["moon"].at(times)
    vectors = {}
    for key in ("sun", "earth"):
        observed = moon.observe(ephemeris[key]).frame_xyz(frame)
        vectors[key] = np.asarray(observed.km, dtype=np.float64).T * 1000.0
        if vectors[key].shape != (len(when), 3):
            raise RuntimeError(f"{key} vectors have shape {vectors[key].shape}, expected {(len(when), 3)}")
    return vectors
