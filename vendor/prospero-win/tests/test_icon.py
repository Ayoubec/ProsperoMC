#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The committed icon must be exactly what its generator produces.

`sce_sys/icon0.png` is a functional requirement: the console installer
copies it into `/user/app/<title>` and aborts the registration if it is
missing, which leaves the title unlaunchable. Keeping it generated and
verified means it is reviewable as code and cannot drift into an opaque
blob.
"""

from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import make_icon  # noqa: E402


def main() -> int:
    committed = (ROOT / "sce_sys" / "icon0.png").read_bytes()
    regenerated = make_icon.render()
    assert committed == regenerated, \
        "sce_sys/icon0.png differs from tools/make_icon.py output"

    # The format the console expects, and the one the laboratory's other
    # titles already use: 512x512, 8-bit RGB.
    assert committed[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    width, height = struct.unpack(">II", committed[16:24])
    assert (width, height) == (512, 512), (width, height)
    assert committed[24] == 8, committed[24]
    assert committed[25] == 2, committed[25]

    # Deterministic: two renders must agree byte for byte, or the pinned
    # digest in the publication audit would drift on every build.
    assert make_icon.render() == regenerated, "icon rendering is not stable"

    digest = hashlib.sha256(committed).hexdigest()
    audit = (ROOT / "tools" / "audit_publication.py").read_text()
    assert digest in audit, \
        f"publication audit does not pin the icon digest {digest}"

    print(f"icon contract passed: {width}x{height} {len(committed)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
