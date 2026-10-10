"""Draw the three series on one time axis. The method note is stored in the PNG."""

from __future__ import annotations

import struct
import zlib
from datetime import datetime
from pathlib import Path

from weather.assemble import DOSE_NOT_FROM_FLUX, POLAR_THRESHOLD_PFU, Report
from weather.font8x8 import FONT

WIDTH = 1180
MARGIN_L = 78
MARGIN_R = 24
PANEL_H = 168
PANEL_GAP = 28
HEADER_H = 28
TEXT_SCALE = 2


def render(report: Report, path: Path) -> None:
    lines = _wrap(report.method, 68)
    height = HEADER_H + 3 * PANEL_H + 2 * PANEL_GAP + 16 + len(lines) * 8 * TEXT_SCALE + 16
    canvas = Canvas(WIDTH, height)
    canvas.fill((248, 246, 240))
    title = f"{report.storm}  {_iso(report.window_start)} .. {_iso(report.window_end)}"
    canvas.text(16, 8, title, (20, 22, 28), 1)
    top = HEADER_H
    _panel(
        canvas,
        top,
        report,
        "SWPC proton-alert threshold (pfu)",
        [(alert.start, alert.value) for alert in report.proton_alerts if alert.start and alert.value],
        (20, 70, 160),
        log=True,
        markers=True,
    )
    top += PANEL_H + PANEL_GAP
    _panel(
        canvas,
        top,
        report,
        "GOES-13 ZPGT10E (p/(cm^2 s sr))",
        [(point.when, point.value) for point in report.proton_gt10 if point.when and point.value and point.value > 0],
        (170, 70, 20),
        log=True,
        rule=POLAR_THRESHOLD_PFU,
        rule_label="NOAA S2 100 pfu",
    )
    top += PANEL_H + PANEL_GAP
    _panel(
        canvas,
        top,
        report,
        "RadLab CRaTER-D1D2 absorbed dose rate (uGy/hour)",
        [(point.when, point.value) for point in report.dose if point.when and point.value and point.value > 0],
        (16, 110, 70),
        log=True,
    )
    canvas.text(16, top + PANEL_H + 8, DOSE_NOT_FROM_FLUX, (120, 30, 30), 1)
    y = top + PANEL_H + 24
    for line in lines:
        canvas.text(16, y, line, (20, 22, 28), TEXT_SCALE)
        y += 8 * TEXT_SCALE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canvas.png(report.method))


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


def _panel(canvas, top, report, label, samples, color, log, markers=False, rule=None, rule_label=""):
    x0 = MARGIN_L
    x1 = WIDTH - MARGIN_R
    y0 = top + 18
    y1 = top + PANEL_H - 8
    canvas.rect(x0, y0, x1, y1, (255, 255, 255))
    canvas.rect_border(x0, y0, x1, y1, (40, 42, 48))
    canvas.text(x0, top, label, (20, 22, 28), 1)
    values = [value for _, value in samples if value and value > 0]
    if rule:
        values.append(rule)
    if not values:
        canvas.text(x0 + 8, y0 + 8, "no traced samples in the window", (90, 90, 90), 1)
        return
    low = min(values)
    high = max(values)
    if log:
        low = max(low, 1e-4)
        high = max(high, low * 1.01)
        lo, hi = _log(low), _log(high)
    else:
        lo, hi = low, high
        if hi == lo:
            hi = lo + 1
    start = report.window_start.timestamp()
    end = report.window_end.timestamp()
    span = max(end - start, 1.0)

    def xy(when: datetime, value: float) -> tuple[int, int]:
        frac = (when.timestamp() - start) / span
        mapped = (_log(value) - lo) / (hi - lo) if log else (value - lo) / (hi - lo)
        return x0 + int(frac * (x1 - x0)), y1 - int(mapped * (y1 - y0))

    if rule and rule > 0:
        y = xy(report.window_start, rule)[1]
        canvas.hline(x0, x1, y, (170, 50, 40))
        if rule_label:
            canvas.text(x0 + 4, max(y0, y - 10), rule_label, (170, 50, 40), 1)
    previous = None
    for when, value in samples:
        if when is None or value is None or value <= 0:
            previous = None
            continue
        point = xy(when, value)
        if markers or previous is None:
            canvas.marker(point[0], point[1], color)
        else:
            canvas.line(previous[0], previous[1], point[0], point[1], color)
        if not markers:
            previous = point
    canvas.text(4, y1 - 8, _tick(low), (60, 60, 60), 1)
    canvas.text(4, y0, _tick(high), (60, 60, 60), 1)


def _log(value: float) -> float:
    import math
    return math.log10(value)


def _tick(value: float) -> str:
    if value >= 100:
        return f"{value:.0f}"
    if value >= 1:
        return f"{value:.1f}"
    return f"{value:.3f}"


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


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


class Canvas:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.pixels = bytearray([248, 246, 240]) * (width * height)

    def fill(self, color: tuple[int, int, int]) -> None:
        pixel = bytes(color)
        self.pixels = bytearray(pixel * (self.width * self.height))

    def set(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            index = (y * self.width + x) * 3
            self.pixels[index:index + 3] = bytes(color)

    def rect(self, x0, y0, x1, y1, color) -> None:
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.set(x, y, color)

    def rect_border(self, x0, y0, x1, y1, color) -> None:
        self.hline(x0, x1, y0, color)
        self.hline(x0, x1, y1 - 1, color)
        self.vline(x0, y0, y1, color)
        self.vline(x1 - 1, y0, y1, color)

    def hline(self, x0, x1, y, color) -> None:
        for x in range(min(x0, x1), max(x0, x1)):
            self.set(x, y, color)

    def vline(self, x, y0, y1, color) -> None:
        for y in range(min(y0, y1), max(y0, y1)):
            self.set(x, y, color)

    def line(self, x0, y0, x1, y1, color) -> None:
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for step in range(steps + 1):
            x = x0 + (x1 - x0) * step // steps
            y = y0 + (y1 - y0) * step // steps
            self.set(x, y, color)

    def marker(self, x, y, color) -> None:
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                self.set(x + dx, y + dy, color)

    def text(self, x, y, text, color, scale) -> None:
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
        method_bytes = method.encode("latin1", errors="replace")
        text = b"method\x00" + method_bytes
        return b"".join([
            b"\x89PNG\r\n\x1a\n",
            _chunk(b"IHDR", ihdr),
            _chunk(b"tEXt", text),
            _chunk(b"IDAT", zlib.compress(bytes(raw), 9)),
            _chunk(b"IEND", b""),
        ])


def _chunk(tag: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
