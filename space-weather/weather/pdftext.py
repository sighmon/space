"""Pull literal strings out of a PDF's FlateDecode streams."""

from __future__ import annotations

import re
import zlib


def pdf_lines(data: bytes) -> list[str]:
    parts: list[bytes] = []
    for match in re.finditer(rb"stream\r?\n", data):
        start = match.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        raw = data[start:end]
        if raw.endswith(b"\r\n"):
            raw = raw[:-2]
        elif raw.endswith(b"\n"):
            raw = raw[:-1]
        try:
            parts.append(zlib.decompress(raw))
        except zlib.error:
            continue
    lines: list[str] = []
    for blob in parts:
        for piece in _strings(blob):
            text = piece.strip()
            if text:
                lines.append(text)
    return lines


def _strings(blob: bytes) -> list[str]:
    found: list[str] = []
    index = 0
    while True:
        start = blob.find(b"(", index)
        if start < 0:
            break
        chars: list[str] = []
        cursor = start + 1
        while cursor < len(blob):
            byte = blob[cursor]
            if byte == 0x5C:
                cursor += 1
                if cursor >= len(blob):
                    break
                escaped = blob[cursor]
                if escaped in b"01234567":
                    digits = [escaped]
                    cursor += 1
                    while cursor < len(blob) and len(digits) < 3 and blob[cursor] in b"01234567":
                        digits.append(blob[cursor])
                        cursor += 1
                    chars.append(chr(int(bytes(digits), 8)))
                    continue
                mapping = {ord("n"): "\n", ord("r"): "\n", ord("t"): "\t", ord("b"): "\b", ord("f"): "\f"}
                chars.append(mapping.get(escaped, chr(escaped)))
                cursor += 1
                continue
            if byte == 0x29:
                break
            chars.append(chr(byte))
            cursor += 1
        found.append("".join(chars))
        index = cursor + 1
    return found
