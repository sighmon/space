"""Draw the nine-region comparison. Separate from the Nobile Rim 1 sheet."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

from atlas.compare import method_lines

# Saturated marks, one per row, so two regions cannot collapse to one color.
ROW_MARKS: tuple[tuple[int, int, int], ...] = (
    (220, 70, 55),
    (40, 150, 220),
    (240, 180, 40),
    (80, 190, 120),
    (180, 90, 200),
    (240, 120, 50),
    (80, 210, 200),
    (230, 80, 140),
    (160, 190, 70),
)

BACKGROUND = (16, 18, 22)
HEADER_H = 52
ROW_H = 92
SWATCH_X = 16
SWATCH_Y = 18
SWATCH = 22
TEXT_X = 52
WIDTH = 1280


def row_mark_center(index: int) -> tuple[int, int]:
    """Pixel at the center of the row's color mark. Tests read this pixel."""
    return (SWATCH_X + SWATCH // 2, HEADER_H + index * ROW_H + SWATCH_Y + SWATCH // 2)


def render_comparison(comparison: dict, out_path: str | Path) -> Path:
    """Write a PNG with one row per region and the method note, including the four caveats."""
    records = comparison["regions"]
    if len(records) < 1:
        raise ValueError("render_comparison needs at least one region")
    lines = method_lines(comparison)
    font = _font(15)
    small = _font(13)
    wrapped = []
    for line in lines:
        wrapped.extend(_wrap(line, 148) or [""])
    line_h = 18
    note_h = 16 + line_h * len(wrapped)
    height = HEADER_H + ROW_H * len(records) + note_h
    canvas = Image.new("RGB", (WIDTH, height), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 16), "Artemis III regions, five fields each. Not a ranking.", fill=(235, 235, 230), font=font)
    for index, record in enumerate(records):
        y = HEADER_H + index * ROW_H
        color = ROW_MARKS[index % len(ROW_MARKS)]
        draw.rectangle((SWATCH_X, y + SWATCH_Y, SWATCH_X + SWATCH, y + SWATCH_Y + SWATCH), fill=color)
        draw.text((TEXT_X, y + 6), _title(record), fill=(235, 235, 230), font=font)
        draw.text((TEXT_X, y + 28), _numbers(record), fill=(210, 214, 220), font=small)
        for extra, source_line in enumerate(_wrap(record["slope_source"], 155)[:2]):
            draw.text((TEXT_X, y + 48 + extra * 16), source_line, fill=(150, 156, 166), font=small)
    note_top = HEADER_H + ROW_H * len(records)
    for i, line in enumerate(wrapped):
        draw.text((16, note_top + 8 + i * line_h), line, fill=(210, 214, 220), font=small)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = PngInfo()
    meta.add_text("method", "\n".join(lines))
    canvas.save(path, pnginfo=meta)
    return path


def _title(record: dict) -> str:
    return (
        f"{record['region']}  {record['point_id']}  "
        f"lon {record['longitude_deg']}°  lat {record['latitude_deg']}°"
    )


def _numbers(record: dict) -> str:
    slope = _num(record["slope_deg"])
    rms = _num(record["slope_rms_deg"])
    sun = _num(record["solar_fraction"])
    earth = _num(record["earth_fraction"])
    temp = _num(record["summer_max_temperature_k"])
    shadow = "missing" if record["permanent_shadow"] is None else ("yes" if record["permanent_shadow"] else "no")
    count = _num(record["lola_return_count"])
    if record["interpolated_gap"] is True:
        count = f"{count} (interpolated gap)"
    return (
        f"slope {slope}° ± {rms}° ({_px(record['slope_pixel_label'])})   "
        f"sun {sun} ({_px(record['solar_pixel_label'])}, 18.6-year)   "
        f"earth {earth} ({_px(record['earth_pixel_label'])}, 18.6-year)   "
        f"T {temp} K ({_px(record['temperature_pixel_label'])})   "
        f"shadow {shadow}   returns {count}"
    )


def _num(value: object) -> str:
    if value is None:
        return "missing"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _px(label: str | None) -> str:
    return "missing pixel" if label is None else label


def _font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ):
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


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
