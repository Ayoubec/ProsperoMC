#!/usr/bin/env python3
"""Real descriptor exhaustion, first-origin reporting and concurrent one-shot."""
from pathlib import Path
import os
import re
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CWD = ROOT / "vendor/prospero-win/wine/ps5"


def main():
    wraps = sorted(set(re.findall(r"__wrap_([a-z_]+)", (CWD / "pw_wine_cwd_libc.c").read_text())))
    with tempfile.TemporaryDirectory(prefix="prosperomc-fd-build-") as temporary:
        executable = Path(temporary) / "test-wine-fd-report"
        command = shlex.split(os.environ.get("HOST_CC", "clang-18"))
        command += ["-std=gnu11", "-O2", "-Wall", "-Wextra", "-Werror", "-pthread", f"-I{CWD}"]
        command += [f"-Wl,--wrap={name}" for name in wraps]
        command += [str(ROOT / "tests/runtime/test_wine_fd_report.c"), str(CWD / "pw_wine_cwd.c"),
                    str(CWD / "pw_wine_cwd_libc.c"), "-o", str(executable)]
        subprocess.run(command, check=True)
        for operation in ("open", "openat", "fopen", "opendir", "directory-scan", "concurrent"):
            result = subprocess.run([str(executable), operation], text=True, capture_output=True, check=True)
            report = result.stderr
            origin = "open" if operation == "concurrent" else operation
            assert report.count("fd-exhaustion origin=") == 1, report
            assert f"origin={origin} " in report and "(EMFILE)" in report, report
            assert report.count("fd-exhaustion census ") == 1, report
            match = re.search(r"census live=(\d+).*tracked-module=(\d+) stale-module=(\d+) archives=(\d+).*regions=(\d+) "
                              r"unique-inodes-lower-bound=(\d+) .*soft=(\d+)", report)
            assert match, report
            live, tracked, stale, archives, regions, unique, soft = map(int, match.groups())
            assert live == soft == 64 and tracked > 40 and stale == 1 and archives > 40, report
            assert regions == 1 and unique < live and unique >= 2, report
            print(f"Wine FD failure fixture passed: {operation}, live={live}, unique-inodes-lower-bound={unique}")


if __name__ == "__main__":
    main()
