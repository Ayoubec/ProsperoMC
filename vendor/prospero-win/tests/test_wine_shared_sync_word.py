#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Exercise the actual event/semaphore atomic header, without starting Wine."""
from pathlib import Path
import os
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "wine/patches/0885-server-ps5-shared-sync-word.patch"


def main():
    parts = PATCH.read_text().split("diff --git ")[1:]
    part, = [p for p in parts if p.splitlines()[0].endswith(
        " b/include/wine/ps5_sync_word.h")]
    header = "\n".join(line[1:] for line in part.splitlines()
                       if line.startswith("+") and not line.startswith("+++")) + "\n"
    with tempfile.TemporaryDirectory(prefix="pw-shared-sync-word-") as temp:
        folder = Path(temp)
        (folder / "ps5_sync_word.h").write_text(header)
        command = shlex.split(os.environ.get("CC", "cc"))
        command += shlex.split(os.environ.get("CFLAGS", "-O2 -g -Wall -Wextra -Werror"))
        command += ["-std=gnu11", "-pthread", "-I", str(folder),
                    str(ROOT / "tests/fixtures/wine_shared_sync_word.c"),
                    "-o", str(folder / "test")]
        subprocess.run(command, check=True)
        subprocess.run([str(folder / "test")], check=True, timeout=60)


if __name__ == "__main__":
    main()
