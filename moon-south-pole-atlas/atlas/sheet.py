"""Draw the static sheet. Each layer keeps its own panel and its own citation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from atlas.sample import (
    BARKER_2021,
    EARTH_LABEL,
    MAZARICO_2011,
    SOLAR_LABEL,
    TEMPERATURE_LABEL,
    WILLIAMS_2019,
)

# Distinct hues so a two-panel synthetic sheet cannot collapse to one color.
PANEL_HUES: dict[str, tuple[int, int, int]] = {
    "slope": (220, 220, 210),
    "slope_rms": (180, 140, 90),
    "returns": (170, 130, 210),
    "sunlight": (230, 190, 40),
    "earth": (70, 130, 210),
    "shadow": (40, 160, 120),
    "temperature": (210, 80, 60),
}


def render_sheet(
    panels: list[tuple[str, np.ndarray, str]],
    *,
    citations: list[str],
    notes: list[str],
    out_path: str | Path,
    panel_px: int = 280,
) -> Path:
    """Write a PNG. `panels` are (name, 2-d array, caption). Names select the hue."""
    if len(panels) < 1:
        raise ValueError("render_sheet needs at least one panel")
    thumbnails = []
    for name, values, caption in panels:
        hue = PANEL_HUES.get(name, (200, 200, 200))
        thumbnails.append((caption, _thumbnail(np.asarray(values, dtype=np.float64), hue, panel_px)))

    text_lines = list(notes) + [""] + list(citations)
    text_block = _text_image(text_lines, width=panel_px * 2)

    cols = 3 if len(thumbnails) > 2 else len(thumbnails)
    rows = math_ceil(len(thumbnails) / cols)
    caption_h = 36
    grid_w = cols * panel_px
    grid_h = rows * (panel_px + caption_h)
    canvas = Image.new("RGB", (max(grid_w, text_block.width), grid_h + text_block.height), (16, 18, 22))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, (caption, image) in enumerate(thumbnails):
        r, c = divmod(index, cols)
        x = c * panel_px
        y = r * (panel_px + caption_h)
        canvas.paste(image, (x, y + caption_h))
        draw.text((x + 6, y + 8), caption[:80], fill=(235, 235, 230), font=font)
    canvas.paste(text_block, (0, grid_h))
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
    return path


def default_citations() -> list[str]:
    return [
        "Slope, slope uncertainty, LOLA return count: " + BARKER_2021,
        "Average sunlight, Earth disc visibility, permanent shadow: " + MAZARICO_2011,
        "Summer maximum temperature: " + WILLIAMS_2019,
        "Sunlight label: " + SOLAR_LABEL,
        "Earth label: " + EARTH_LABEL,
        "Temperature label: " + TEMPERATURE_LABEL,
        "Cuts are drawn separately. This sheet has no combined habitability or safety score.",
    ]


def _thumbnail(values: np.ndarray, hue: tuple[int, int, int], panel_px: int) -> Image.Image:
    small = _downsample(values, panel_px)
    image = _colorize(small, hue)
    if image.shape[0] != panel_px or image.shape[1] != panel_px:
        pil = Image.fromarray(image, mode="RGB")
        pil = pil.resize((panel_px, panel_px), Image.Resampling.NEAREST)
        return pil
    return Image.fromarray(image, mode="RGB")


def _downsample(values: np.ndarray, panel_px: int) -> np.ndarray:
    if values.ndim != 2 or values.size == 0:
        raise ValueError("panel values must be a non-empty 2-d array")
    stride = max(1, int(math_ceil(max(values.shape) / panel_px)))
    return values[::stride, ::stride]


def _colorize(values: np.ndarray, hue: tuple[int, int, int]) -> np.ndarray:
    finite = np.isfinite(values)
    image = np.zeros(values.shape + (3,), dtype=np.uint8)
    image[..., :] = (28, 28, 32)
    if not np.any(finite):
        # Still the requested hue, so an empty-looking panel is distinguishable.
        image[..., 0] = hue[0] // 5
        image[..., 1] = hue[1] // 5
        image[..., 2] = hue[2] // 5
        return image
    data = values[finite]
    lo = float(np.percentile(data, 2))
    hi = float(np.percentile(data, 98))
    if hi <= lo:
        lo = float(np.min(data))
        hi = float(np.max(data))
    if hi == lo:
        norm = np.zeros(values.shape, dtype=np.float64)
        norm[finite] = 0.75
    else:
        norm = np.zeros(values.shape, dtype=np.float64)
        norm[finite] = (values[finite] - lo) / (hi - lo)
    for channel, level in enumerate(hue):
        image[..., channel] = np.where(finite, np.clip(norm * level, 0, 255).astype(np.uint8), image[..., channel])
    return image


def _text_image(lines: list[str], width: int) -> Image.Image:
    font = ImageFont.load_default()
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(_wrap(line, 96) or [""])
    line_h = 14
    image = Image.new("RGB", (width, max(line_h, line_h * len(wrapped) + 12)), (16, 18, 22))
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(wrapped):
        draw.text((8, 6 + i * line_h), line, fill=(210, 214, 220), font=font)
    return image


def _wrap(line: str, limit: int) -> list[str]:
    if len(line) <= limit:
        return [line]
    words = line.split()
    rows: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if len(trial) <= limit:
            current = trial
        else:
            if current:
                rows.append(current)
            current = word
    if current:
        rows.append(current)
    return rows


def math_ceil(value: float) -> int:
    import math
    return int(math.ceil(value))
