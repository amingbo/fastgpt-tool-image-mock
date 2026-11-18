"""Dependency-free PNG writer with a blocky 5x7 font.

The mock service must render a readable marker image without pulling in Pillow,
so the deployment stays a single small Python image.
"""
from __future__ import annotations

import struct
import zlib

FONT: dict[str, tuple[str, ...]] = {
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}

GLYPH_HEIGHT = 7
GLYPH_WIDTH = 5


def _png_bytes(width: int, height: int, pixels: list[bytearray]) -> bytes:
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        raw.extend(row)

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def render_marker_png(code: str, *, scale: int = 18, margin: int = 24) -> bytes:
    """Render an uppercase marker code as a black-on-white PNG."""
    text = "".join(ch for ch in code.upper() if ch in FONT) or "0"
    scale = max(4, min(int(scale), 40))
    margin = max(0, min(int(margin), 120))

    glyph_pixel_w = GLYPH_WIDTH * scale
    glyph_pixel_h = GLYPH_HEIGHT * scale
    gap = scale * 2
    text_w = len(text) * glyph_pixel_w + (len(text) - 1) * gap
    width = text_w + margin * 2
    height = glyph_pixel_h + margin * 2

    pixels = [bytearray(b"\xff" * (width * 3)) for _ in range(height)]
    for index, ch in enumerate(text):
        origin_x = margin + index * (glyph_pixel_w + gap)
        for row_index, row in enumerate(FONT[ch]):
            for col_index, bit in enumerate(row):
                if bit != "1":
                    continue
                for dy in range(scale):
                    y = margin + row_index * scale + dy
                    line = pixels[y]
                    for dx in range(scale):
                        x = origin_x + col_index * scale + dx
                        offset = x * 3
                        line[offset : offset + 3] = b"\x00\x00\x00"
    return _png_bytes(width, height, pixels)


def render_marker_svg(code: str) -> bytes:
    text = "".join(ch for ch in code.upper() if ch in FONT) or "0"
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="240" viewBox="0 0 640 240">'
        '<rect width="640" height="240" fill="#ffffff"/>'
        f'<text x="320" y="160" font-family="monospace" font-size="160" font-weight="700" '
        f'text-anchor="middle" fill="#000000">{text}</text>'
        "</svg>"
    )
    return svg.encode("utf-8")
