"""
Generate placeholder PNGs for the README screenshots section.

These stand in for real captures until you run:

    npm i -D puppeteer
    node scripts/capture_screenshots.mjs

No third-party dependency is used — the PNGs are written directly with
`zlib` + `struct`, so this works with a bare Python install.

Usage:
    python scripts/make_placeholder_screenshots.py
"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "docs" / "screenshots"

WIDTH, HEIGHT = 1280, 720

# SOC console palette (matches frontend/src/index.css)
BG = (10, 14, 23)
PANEL = (20, 30, 51)
BORDER = (30, 41, 59)
ACCENT = (56, 189, 248)
MUTED = (100, 116, 139)

# 5x7 bitmap font for the label text
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "11110", "10001", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "11110", "10000", "10000", "10000", "11111"],
    "F": ["11111", "10000", "11110", "10000", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "11111", "10001", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    " ": ["00000"] * 7,
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    "_": ["00000", "00000", "00000", "00000", "00000", "00000", "11111"],
}

PLACEMENTS = [
    ("01-dashboard.png", "SOC DASHBOARD - LIVE ALERTS"),
    ("02-incidents.png", "INCIDENTS - TRIAGE"),
    ("03-ml-anomalies.png", "ML ANOMALIES"),
    ("04-threat-intel.png", "THREAT INTELLIGENCE"),
    ("05-security-logs.png", "SECURITY LOGS"),
    ("06-system-health.png", "SYSTEM HEALTH"),
    ("07-incident-detail.png", "INCIDENT DETAIL - AI INVESTIGATION"),
    ("08-login.png", "LOGIN - JWT AUTH"),
]


def new_canvas(width: int, height: int, color: tuple[int, int, int]) -> bytearray:
    row = bytes(color) * width
    return bytearray(row * height)


def fill_rect(buf, x, y, w, h, color) -> None:
    """Fill a w×h rectangle at (x, y) with a solid colour."""
    if w <= 0 or h <= 0:
        return
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(WIDTH, x + w), min(HEIGHT, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(color) * (x1 - x0)
    for yy in range(y0, y1):
        start = yy * WIDTH * 3 + x0 * 3
        buf[start : start + len(row)] = row


def draw_text(buf, text: str, x: int, y: int, scale: int, color) -> None:
    cursor = x
    for char in text.upper():
        glyph = FONT.get(char, FONT[" "])
        for gy, row_bits in enumerate(glyph):
            for gx, bit in enumerate(row_bits):
                if bit == "1":
                    fill_rect(buf, cursor + gx * scale, y + gy * scale, scale, scale, color)
        cursor += (5 + 1) * scale


def draw_frame(buf) -> None:
    """A simple SOC-console-looking placeholder frame."""
    fill_rect(buf, 0, 0, 1280, 56, PANEL)          # top bar
    fill_rect(buf, 0, 56, 1280, 2, BORDER)
    fill_rect(buf, 0, 0, 320, 56, BG)
    fill_rect(buf, 24, 20, 16, 16, ACCENT)         # "shield" square
    draw_text(buf, "SENTINELAI", 52, 20, 2, (241, 245, 249))
    draw_text(buf, "SOC CORE", 900, 20, 2, MUTED)

    # sidebar
    fill_rect(buf, 0, 58, 220, 662, PANEL)
    for i in range(6):
        fill_rect(buf, 20, 100 + i * 40, 180, 24, (17, 24, 39))

    # metric cards
    for i in range(4):
        x = 250 + i * 250
        fill_rect(buf, x, 90, 230, 110, PANEL)
        fill_rect(buf, x, 90, 230, 3, ACCENT if i < 2 else BORDER)
        fill_rect(buf, x + 20, 120, 120, 26, (30, 41, 59))

    # table rows
    fill_rect(buf, 250, 230, 990, 40, (17, 24, 39))
    for i in range(6):
        fill_rect(buf, 250, 280 + i * 44, 990, 34, PANEL)


def write_png(path: Path, buf: bytearray, width: int, height: int) -> None:
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter type 0
        raw += buf[y * stride : (y + 1) * stride]

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, label in PLACEMENTS:
        buf = new_canvas(WIDTH, HEIGHT, BG)
        draw_frame(buf)
        # placeholder banner
        fill_rect(buf, 250, 560, 990, 90, (17, 24, 39))
        draw_text(buf, "PLACEHOLDER SCREENSHOT", 280, 585, 3, ACCENT)
        draw_text(buf, "RUN CAPTURE_SCREENSHOTS.MJS TO GENERATE", 280, 615, 2, MUTED)
        draw_text(buf, label, 20, 660, 2, MUTED)
        out = OUT_DIR / filename
        write_png(out, buf, WIDTH, HEIGHT)
        print(f"  wrote {out.relative_to(REPO)}")
    print(f"\n{len(PLACEMENTS)} placeholder images in {OUT_DIR.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
