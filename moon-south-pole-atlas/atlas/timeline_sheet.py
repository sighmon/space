"""Draw the fourteen-day Sun and Earth timeline. Four series, no fused score."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

LINE_PX = 18
LABEL_PX = 150
SAMPLE_PX = 2
TRACK_PX = 28
GAP_PX = 8
MARGIN_PX = 12

TRACKS = (
    ("sun_1m", "Sun 1 m", (240, 196, 40)),
    ("sun_5m", "Sun 5 m", (230, 92, 28)),
    ("earth_1m", "Earth 1 m", (55, 128, 220)),
    ("earth_5m", "Earth 5 m", (36, 188, 176)),
)


def render_timeline(series: dict[str, list[bool]], notes: list[str], out_path: str | Path) -> Path:
    """Write a PNG. ``series`` keys are the four track names. Notes are drawn above the tracks."""
    missing = [name for name, _label, _hue in TRACKS if name not in series]
    if missing:
        raise ValueError("timeline is missing series: " + ", ".join(missing))
    lengths = {len(series[name]) for name, _label, _hue in TRACKS}
    if lengths != {len(series["sun_1m"])} or len(series["sun_1m"]) < 2:
        raise ValueError("the four series must share one length of at least 2")
    wrapped = note_lines(notes)
    header = _header_height(len(wrapped))
    sample_count = len(series["sun_1m"])
    width = MARGIN_PX + LABEL_PX + sample_count * SAMPLE_PX + MARGIN_PX
    height = header + len(TRACKS) * (TRACK_PX + GAP_PX) + 36
    canvas = Image.new("RGB", (width, height), (16, 18, 22))
    draw = ImageDraw.Draw(canvas)
    font = _font()
    for index, line in enumerate(wrapped):
        draw.text((MARGIN_PX, 8 + index * LINE_PX), line, fill=(230, 228, 220), font=font)
    for track_index, (name, label, hue) in enumerate(TRACKS):
        top = header + track_index * (TRACK_PX + GAP_PX)
        draw.text((MARGIN_PX, top + 6), label, fill=hue, font=font)
        flags = series[name]
        for sample_index, flag in enumerate(flags):
            color = hue if flag else (hue[0] // 7, hue[1] // 7, hue[2] // 7)
            x0 = MARGIN_PX + LABEL_PX + sample_index * SAMPLE_PX
            draw.rectangle((x0, top, x0 + SAMPLE_PX - 1, top + TRACK_PX - 1), fill=color)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
    return path


def note_lines(notes: list[str], width: int = 96) -> list[str]:
    lines: list[str] = []
    for note in notes:
        lines.extend(_wrap(note, width))
    return lines


def sample_origin(track_index: int, sample_index: int, wrapped_line_count: int) -> tuple[int, int]:
    """Pixel inside one sample of one track. Shared by the renderer layout and tests."""
    header = _header_height(wrapped_line_count)
    y = header + track_index * (TRACK_PX + GAP_PX) + TRACK_PX // 2
    x = MARGIN_PX + LABEL_PX + sample_index * SAMPLE_PX + SAMPLE_PX // 2
    return x, y


def _header_height(line_count: int) -> int:
    return 8 + line_count * LINE_PX + 10


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = current + " " + word
        if len(trial) > width:
            lines.append(current)
            current = word
        else:
            current = trial
    lines.append(current)
    return lines


def _font():
    try:
        return ImageFont.load_default(size=15)
    except TypeError:
        return ImageFont.load_default()


def series_colors(image: np.ndarray, wrapped_line_count: int) -> list[tuple[int, int, int]]:
    """Color at the first sample of each track, for tests of the shipped renderer."""
    colors = []
    for track_index in range(len(TRACKS)):
        x, y = sample_origin(track_index, 0, wrapped_line_count)
        pixel = image[y, x]
        colors.append((int(pixel[0]), int(pixel[1]), int(pixel[2])))
    return colors
