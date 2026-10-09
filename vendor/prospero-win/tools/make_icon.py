#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Generate the title icon deterministically.

The console's installer copies `sce_sys/icon0.png` into `/user/app/<title>`
and aborts the whole registration if it is missing, so the icon is a
functional requirement rather than decoration. It is generated rather than
committed as an opaque blob: the output is byte-reproducible, the design is
reviewable as code, and `tests/test_icon.py` regenerates it to prove the
committed file still matches.

512x512, 8-bit RGB, matching the format the laboratory's other titles use.
"""

from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path

SIZE = 512
BACKGROUND = (0x12, 0x16, 0x1d)
FRAME = (0x2b, 0x33, 0x42)
LEFT = (0x4f, 0x8e, 0xf7)      # the Win32 side
RIGHT = (0xc9, 0xd4, 0xe6)     # the native side


def chunk(tag: bytes, payload: bytes) -> bytes:
    return (struct.pack(">I", len(payload)) + tag + payload +
            struct.pack(">I", zlib.crc32(tag + payload) & 0xffffffff))


def inside_rounded_square(x: int, y: int, margin: int, radius: int) -> bool:
    low = margin
    high = SIZE - 1 - margin
    if x < low or x > high or y < low or y > high:
        return False
    for corner_x, corner_y in ((low + radius, low + radius),
                               (high - radius, low + radius),
                               (low + radius, high - radius),
                               (high - radius, high - radius)):
        if ((x < low + radius or x > high - radius) and
                (y < low + radius or y > high - radius)):
            dx = x - corner_x
            dy = y - corner_y
            if dx * dx + dy * dy > radius * radius:
                return False
    return True


def pixel(x: int, y: int) -> tuple[int, int, int]:
    """A framed panel split diagonally: mapped code on one side, native on
    the other. Deliberately geometric, so it stays legible when the console
    scales it down and carries no third-party mark."""
    if not inside_rounded_square(x, y, 28, 72):
        return BACKGROUND
    if not inside_rounded_square(x, y, 44, 58):
        return FRAME
    # A diagonal band separates the two halves.
    band = x + y - SIZE
    if -14 <= band <= 14:
        return FRAME
    return LEFT if band < 0 else RIGHT


def render() -> bytes:
    rows = bytearray()
    for y in range(SIZE):
        rows.append(0)                       # filter type: none
        for x in range(SIZE):
            rows.extend(pixel(x, y))
    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
            chunk(b"IDAT", zlib.compress(bytes(rows), 9)) +
            chunk(b"IEND", b""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).resolve().parents[1] /
                        "sce_sys" / "icon0.png")
    arguments = parser.parse_args()
    data = render()
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_bytes(data)
    print(f"{arguments.out} {len(data)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
