"""Draw the deficit series. The method note is stored in the PNG."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from power.assemble import NO_POWER, Report
from power.font8x8 import FONT

WIDTH = 1180
MARGIN_L = 72
MARGIN_R = 16
PANEL_H = 150
PANEL_GAP = 22
COLORS = (
    (20, 70, 160),
    (170, 70, 20),
    (16, 110, 70),
    (120, 40, 140),
    (40, 40, 40),
    (180, 140, 20),
)


def render(report: Report, path: Path) -> None:
    lines = _wrap(report.method, 70)
    height = 36 + 4 * PANEL_H + 3 * PANEL_GAP + 12 + len(lines) * 16 + 12
    canvas = Canvas(WIDTH, height)
    canvas.fill((248, 246, 240))
    canvas.text(12, 8, f"{report.version or 'MCD'}  {NO_POWER}", (20, 22, 28), 1)
    sites = list(dict.fromkeys(item.site for item in report.deficits))
    top = 28
    _deficit_panel(canvas, top, report, sites, "warm", "warm minus cold (W/m2)")
    top += PANEL_H + PANEL_GAP
    _deficit_panel(canvas, top, report, sites, "storm", "dust storm minus cold (W/m2)")
    top += PANEL_H + PANEL_GAP
    _opacity_panel(
        canvas,
        top,
        [(point.ls, point.value) for point in report.opportunity if point.ls is not None and point.value is not None],
        "Opportunity PANCAM_R8_880NM atmospheric opacity",
        (120, 40, 140),
    )
    top += PANEL_H + PANEL_GAP
    _storm_opacity(canvas, top, report)
    y = top + PANEL_H + 8
    for line in lines:
        canvas.text(12, y, line, (20, 22, 28), 2)
        y += 16
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canvas.png(report.method))


def _storm_opacity(canvas, top, report: Report) -> None:
    sites = list(dict.fromkeys(item.site for item in report.storm_opacity))
    series = {
        site: [(item.ls, item.value) for item in report.storm_opacity if item.site == site]
        for site in sites
    }
    values = [value for points in series.values() for _, value in points]
    unit = report.storm_opacity[0].unit if report.storm_opacity else "absent"
    _xy_panel(canvas, top, f"dust storm {unit}", values, series, sites)


def _deficit_panel(canvas, top, report, sites, key, label) -> None:
    series = {
        site: [(item.ls, item.value) for item in report.deficits if item.site == site and item.scenario_key == key]
        for site in sites
    }
    points = [value for values in series.values() for _, value in values]
    _xy_panel(canvas, top, label, points, series, sites)


def _opacity_panel(canvas, top, samples, label, color) -> None:
    values = [value for _, value in samples]
    _line_panel(canvas, top, label, samples, values, color)


def _xy_panel(canvas, top, label, values, series, sites) -> None:
    x0, x1, y0, y1 = MARGIN_L, WIDTH - MARGIN_R, top + 16, top + PANEL_H - 6
    canvas.rect(x0, y0, x1, y1, (255, 255, 255))
    canvas.rect_border(x0, y0, x1, y1, (40, 42, 48))
    canvas.text(x0, top, label, (20, 22, 28), 1)
    if not values:
        canvas.text(x0 + 8, y0 + 8, "no traced samples", (90, 90, 90), 1)
        return
    low, high = min(values), max(values)
    if high == low:
        high = low + 1
    if low < 0 < high:
        zero = y1 - int((0 - low) / (high - low) * (y1 - y0))
        canvas.hline(x0, x1, zero, (180, 180, 180))
    for index, site in enumerate(sites):
        color = COLORS[index % len(COLORS)]
        previous = None
        for ls, value in series[site]:
            point = _map(ls, value, x0, x1, y0, y1, low, high)
            if previous is None:
                canvas.marker(point[0], point[1], color)
            else:
                canvas.line(previous[0], previous[1], point[0], point[1], color)
            previous = point
        canvas.text(x0 + 8 + index * 180, y0 + 4, site[:16], color, 1)
    canvas.text(4, y1 - 8, f"{low:.4g}", (60, 60, 60), 1)
    canvas.text(4, y0, f"{high:.4g}", (60, 60, 60), 1)


def _line_panel(canvas, top, label, samples, values, color) -> None:
    x0, x1, y0, y1 = MARGIN_L, WIDTH - MARGIN_R, top + 16, top + PANEL_H - 6
    canvas.rect(x0, y0, x1, y1, (255, 255, 255))
    canvas.rect_border(x0, y0, x1, y1, (40, 42, 48))
    canvas.text(x0, top, label, (20, 22, 28), 1)
    if not values:
        canvas.text(x0 + 8, y0 + 8, "no traced samples", (90, 90, 90), 1)
        return
    low, high = min(values), max(values)
    if high == low:
        high = low + 1
    previous = None
    for ls, value in samples:
        point = _map(ls, value, x0, x1, y0, y1, low, high)
        if previous is None:
            canvas.marker(point[0], point[1], color)
        else:
            canvas.line(previous[0], previous[1], point[0], point[1], color)
        previous = point
    canvas.text(4, y1 - 8, f"{low:.4g}", (60, 60, 60), 1)
    canvas.text(4, y0, f"{high:.4g}", (60, 60, 60), 1)


def _map(ls, value, x0, x1, y0, y1, low, high):
    x = x0 + int((ls / 360.0) * (x1 - x0))
    y = y1 - int((value - low) / (high - low) * (y1 - y0))
    return x, y


def _wrap(text: str, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines():
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            trial = current + " " + word
            if len(trial) <= width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def read_method(path: Path) -> str:
    data = path.read_bytes()
    cursor = 8
    while cursor + 8 <= len(data):
        length = struct.unpack(">I", data[cursor:cursor + 4])[0]
        tag = data[cursor + 4:cursor + 8]
        chunk = data[cursor + 8:cursor + 8 + length]
        if tag == b"tEXt" and chunk.startswith(b"method\x00"):
            return chunk.split(b"\x00", 1)[1].decode("latin1")
        cursor += 12 + length
    return ""


class Canvas:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.pixels = bytearray([248, 246, 240]) * (width * height)

    def fill(self, color):
        self.pixels = bytearray(bytes(color) * (self.width * self.height))

    def set(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            index = (y * self.width + x) * 3
            self.pixels[index:index + 3] = bytes(color)

    def rect(self, x0, y0, x1, y1, color):
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.set(x, y, color)

    def rect_border(self, x0, y0, x1, y1, color):
        self.hline(x0, x1, y0, color)
        self.hline(x0, x1, y1 - 1, color)
        self.vline(x0, y0, y1, color)
        self.vline(x1 - 1, y0, y1, color)

    def hline(self, x0, x1, y, color):
        for x in range(min(x0, x1), max(x0, x1)):
            self.set(x, y, color)

    def vline(self, x, y0, y1, color):
        for y in range(min(y0, y1), max(y0, y1)):
            self.set(x, y, color)

    def line(self, x0, y0, x1, y1, color):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for step in range(steps + 1):
            x = x0 + (x1 - x0) * step // steps
            y = y0 + (y1 - y0) * step // steps
            self.set(x, y, color)

    def marker(self, x, y, color):
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                self.set(x + dx, y + dy, color)

    def text(self, x, y, text, color, scale):
        cursor = x
        for character in text:
            glyph = FONT[ord(character)] if 0 <= ord(character) < 128 else FONT[32]
            for row, bits in enumerate(glyph):
                for col in range(8):
                    if bits & (1 << col):
                        for sy in range(scale):
                            for sx in range(scale):
                                self.set(cursor + col * scale + sx, y + row * scale + sy, color)
            cursor += 8 * scale

    def png(self, method: str) -> bytes:
        raw = bytearray()
        row_bytes = self.width * 3
        for y in range(self.height):
            raw.append(0)
            start = y * row_bytes
            raw.extend(self.pixels[start:start + row_bytes])
        ihdr = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        text = b"method\x00" + method.encode("latin1", errors="replace")
        return b"".join([
            b"\x89PNG\r\n\x1a\n",
            _chunk(b"IHDR", ihdr),
            _chunk(b"tEXt", text),
            _chunk(b"IDAT", zlib.compress(bytes(raw), 9)),
            _chunk(b"IEND", b""),
        ])


def _chunk(tag: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
