#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Verify and summarize a public source/PDB oracle for a private PE target.

The report contains identities, public symbol addresses and aggregate source
references only. It never copies executable bytes, decompilation or snippets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

PUB = re.compile(r"S_PUB32[^`]*`([^`]+)`")
PUB_ADDRESS = re.compile(r"flags\s*=\s*function,\s*addr\s*=\s*([0-9A-Fa-f]{4}):(\d+)")
PDB_GUID = re.compile(r"GUID:\s*\{([^}]+)\}")
PDB_AGE = re.compile(r"Age:\s*(\d+)")


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True).stdout


def pe_identity(raw: bytes) -> tuple[int, int]:
    """Return (image base, .text RVA) from a PE32 image."""
    if len(raw) < 0x40 or raw[:2] != b"MZ":
        raise ValueError("not a DOS/PE image")
    pe = struct.unpack_from("<I", raw, 0x3C)[0]
    if pe + 24 > len(raw) or raw[pe:pe + 4] != b"PE\0\0":
        raise ValueError("invalid PE signature")
    sections = struct.unpack_from("<H", raw, pe + 6)[0]
    optional_size = struct.unpack_from("<H", raw, pe + 20)[0]
    optional = pe + 24
    if optional + optional_size > len(raw) or struct.unpack_from("<H", raw, optional)[0] != 0x10B:
        raise ValueError("source oracle currently requires PE32")
    image_base = struct.unpack_from("<I", raw, optional + 28)[0]
    table = optional + optional_size
    for index in range(sections):
        offset = table + index * 40
        if offset + 40 > len(raw):
            raise ValueError("truncated section table")
        name = raw[offset:offset + 8].split(b"\0", 1)[0]
        if name == b".text":
            return image_base, struct.unpack_from("<I", raw, offset + 12)[0]
    raise ValueError("PE has no .text section")


def parse_public_symbols(text: str) -> tuple[dict[str, tuple[int, int]], str, int]:
    symbols: dict[str, tuple[int, int]] = {}
    pending: str | None = None
    for line in text.splitlines():
        match = PUB.search(line)
        if match:
            pending = match.group(1)
            continue
        address = PUB_ADDRESS.search(line)
        if pending and address:
            symbols[pending] = (int(address.group(1), 16), int(address.group(2)))
            pending = None
    guid = PDB_GUID.search(text)
    age = PDB_AGE.search(text)
    if not guid or not age:
        raise ValueError("PDB identity was not found")
    return symbols, guid.group(1).upper(), int(age.group(1))


def require_commit(repo: Path, commit: str) -> None:
    subprocess.run(["git", "-C", str(repo), "cat-file", "-e", commit + "^{commit}"],
                   check=True, capture_output=True)


def build(config_path: Path, repo: Path, image: Path) -> dict[str, object]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema") != "pw-source-oracle-config/1":
        raise ValueError("unexpected source-oracle config schema")
    oracle = config["win32_oracle_commit"]
    maintained = config["maintained_commit"]
    require_commit(repo, oracle)
    require_commit(repo, maintained)

    raw = image.read_bytes()
    sha1 = hashlib.sha1(raw).hexdigest()
    sha256 = hashlib.sha256(raw).hexdigest()
    if {"sha1": sha1, "sha256": sha256} != config["target"]:
        raise ValueError("private target identity does not match the pinned oracle")
    image_base, text_rva = pe_identity(raw)

    pdb_path = config["pdb"]["path"]
    pdb = git(repo, "show", f"{oracle}:{pdb_path}").decode("utf-8", errors="strict")
    symbols, guid, age = parse_public_symbols(pdb)
    if guid != config["pdb"]["guid"].upper() or age != config["pdb"]["age"]:
        raise ValueError("public PDB identity does not match config")

    mapped: dict[str, str] = {}
    for name, expected in config["symbols"].items():
        if name not in symbols:
            raise ValueError(f"public symbol absent: {name}")
        segment, offset = symbols[name]
        if segment != 1:
            raise ValueError(f"unsupported PDB segment for {name}: {segment}")
        address = f"{image_base + text_rva + offset:08x}"
        if address != expected.lower():
            raise ValueError(f"public symbol address mismatch for {name}")
        mapped[name] = address

    groups: dict[str, object] = {}
    for group_name, group in config["source_groups"].items():
        sources = {
            path: git(repo, "show", f"{oracle}:{path}").decode("utf-8", errors="strict")
            for path in group["files"]
        }
        api_rows = []
        for entry in group["apis"]:
            api = entry if isinstance(entry, str) else entry["api"]
            source_token = entry if isinstance(entry, str) else entry["token"]
            token = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(source_token) +
                               r"(?![A-Za-z0-9_])")
            by_file = {path: len(token.findall(text)) for path, text in sources.items()}
            api_rows.append({"api": api, "occurrences": sum(by_file.values()),
                             "files": sorted(path for path, count in by_file.items() if count)})
        groups[group_name] = {"files": sorted(sources), "api_references": api_rows}

    license_text = git(repo, "show", f"{maintained}:LICENSE").decode("utf-8", errors="strict")
    if "MIT License" not in license_text:
        raise ValueError("expected MIT license was not found")
    return {
        "schema": "pw-source-oracle/1",
        "repository": config["repository"],
        "provenance": {
            "win32_oracle_commit": oracle,
            "maintained_commit": maintained,
            "license": config["license"],
            "pdb_guid": guid,
            "pdb_age": age,
        },
        "target": {"sha1": sha1, "sha256": sha256},
        "pe": {"image_base": f"{image_base:08x}", "text_rva": f"{text_rva:08x}"},
        "public_symbol_addresses": mapped,
        "source_groups": groups,
        "privacy": "identities, public symbols and aggregate public-source references only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = json.dumps(build(args.config, args.reference_dir, args.image),
                        indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
