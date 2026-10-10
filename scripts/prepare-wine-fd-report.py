#!/usr/bin/env python3
"""Record or mirror the failure-only CWD helper into a verified Wine recipe root.

This prepares source only: it does not build, stage, upload, or replace a PRX.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor/prospero-win"
BASE_CWD_SHA256 = "f77b35033f91a59d3bf0ee12e699d3b041e2077a364a56a8e009f585c0c1bb80"
WINE_ARCHIVE_SHA256 = "c40c03637f90ede4fe60ffc4162473870038dc2324cd1d67d186ad72212a70d5"
UNITS = ("wine/ps5/pw_wine_cwd_libc.c", "wine/ps5/pw_wine_fd_report.h")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(path):
    return path.read_bytes().replace(b"\r\n", b"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe-root", type=Path, help="Optional pinned ProsperoWin source recipe root to mirror into")
    args = parser.parse_args()
    archive = ROOT / ".deps/archives/wine-490f6d5.tar.gz"
    if digest(archive) != WINE_ARCHIVE_SHA256:
        raise ValueError("Pinned Wine source archive hash does not match")
    baseline = ROOT / ".deps/source/prospero-win-8086243da85fae62206a98af322dc746fe5f7a6d/wine/ps5/pw_wine_cwd_libc.c"
    if hashlib.sha256(normalized(baseline)).hexdigest() != BASE_CWD_SHA256:
        raise ValueError("CWD shim baseline no longer matches the verified upstream snapshot")
    changed = VENDOR / UNITS[0]
    helper = VENDOR / UNITS[1]
    patch = "".join(difflib.unified_diff(normalized(baseline).decode().splitlines(True),
                                      normalized(changed).decode().splitlines(True),
                                      fromfile="a/" + UNITS[0], tofile="b/" + UNITS[0]))
    patch += "".join(difflib.unified_diff([], normalized(helper).decode().splitlines(True),
                                        fromfile="/dev/null", tofile="b/" + UNITS[1]))
    output = ROOT / "artifacts/wine-fd-review"
    output.mkdir(parents=True, exist_ok=True)
    patch_path = output / "cwd-fd-diagnostic.patch"
    patch_path.write_text(patch, encoding="utf-8", newline="\n")
    mirrored = None
    if args.recipe_root:
        target = args.recipe_root.resolve()
        if target == VENDOR.resolve() or not (target / "tools/build_wine_ps5.sh").is_file():
            raise ValueError("Mirror target must be a separate existing ProsperoWin recipe root")
        previous = target / UNITS[0]
        old_digest = hashlib.sha256(normalized(previous)).hexdigest()
        new_digest = hashlib.sha256(normalized(changed)).hexdigest()
        if old_digest not in (BASE_CWD_SHA256, new_digest):
            raise ValueError("Mirror target has other CWD changes; refusing to overwrite them")
        for unit in UNITS:
            shutil.copy2(VENDOR / unit, target / unit)
        mirrored = str(target)
    provenance = {
        "schema": "prosperomc-wine-fd-probe/1", "diagnosticOnly": True,
        "built": False, "deployed": False, "mirrorRoot": mirrored,
        "wineCommit": "490f6d5dcbb2a5047345b8af88d114bbcaad69a8",
        "wineArchiveSha256": WINE_ARCHIVE_SHA256,
        "upstreamCwdNormalizedSha256": BASE_CWD_SHA256,
        "sourceSha256": {unit: digest(VENDOR / unit) for unit in UNITS},
        "patchSha256": digest(patch_path),
        "compileRecipe": "vendor/prospero-win/tools/build_wine_ps5.sh",
        "compileRecipeSha256": digest(VENDOR / "tools/build_wine_ps5.sh"),
        "compileUnit": "pw_wine_cwd_libc.c already includes the helper header; no new link object or ABI export",
        "affectedPrx": ["ntdll.prx", "wineserver.prx"],
        "test": "python3 tests/runtime/test_wine_fd_report.py",
    }
    capture = ROOT / "artifacts/console-ui-revamp-retest/STAGE-REPORT.json"
    if capture.is_file():
        snapshot = json.loads(capture.read_text())
        provenance["preUpdateConsoleCapture"] = {
            "file": str(capture.relative_to(ROOT)), "sha256": digest(capture),
            "wine": snapshot.get("wine"),
            "note": "Historical captured manifest; not a claim about the subsequently deployed title",
        }
    (output / "fd-probe-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print("Wine FD probe source prepared; no runtime module built or deployed")


if __name__ == "__main__":
    main()
