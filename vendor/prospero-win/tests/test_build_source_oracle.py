#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
import hashlib
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_source_oracle import build, parse_public_symbols, pe_identity


pdb = """Age: 2
GUID: {1c24fd97-10ea-cc4f-8960-a06f3babe841}
  10 | S_PUB32 [size = 28] `_WinMain@16`
       flags = function, addr = 0001:29498
  20 | S_PUB32 [size = 28] `_data`
       flags = none, addr = 0002:4
"""
symbols, guid, age = parse_public_symbols(pdb)
assert symbols == {"_WinMain@16": (1, 29498)}
assert guid == "1C24FD97-10EA-CC4F-8960-A06F3BABE841" and age == 2

raw = bytearray(0x200)
raw[:2] = b"MZ"
struct.pack_into("<I", raw, 0x3C, 0x80)
raw[0x80:0x84] = b"PE\0\0"
struct.pack_into("<HH", raw, 0x86, 1, 0xE0)
struct.pack_into("<H", raw, 0x80 + 20, 0xE0)
struct.pack_into("<H", raw, 0x98, 0x10B)
struct.pack_into("<I", raw, 0x98 + 28, 0x01000000)
raw[0x178:0x180] = b".text\0\0\0"
struct.pack_into("<I", raw, 0x178 + 12, 0x1000)
assert pe_identity(bytes(raw)) == (0x01000000, 0x1000)

with tempfile.TemporaryDirectory(prefix="pw-oracle-") as directory:
    repo = Path(directory) / "reference";repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    (repo / "Doc").mkdir();(repo / "Doc/.pdb dump.txt").write_text(pdb)
    (repo / "source.cpp").write_text("void f(){ Foo(); Foo(); }\n")
    (repo / "LICENSE").write_text("MIT License\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "oracle"], check=True)
    oracle = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                            capture_output=True, text=True).stdout.strip()
    (repo / "source.cpp").write_text("void f(){ Foo(); Foo(); }\n// maintained\n")
    subprocess.run(["git", "-C", str(repo), "commit", "-qam", "maintained"], check=True)
    maintained = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                                capture_output=True, text=True).stdout.strip()
    image = Path(directory) / "target.exe";image.write_bytes(raw)
    config = {
        "schema": "pw-source-oracle-config/1", "repository": "https://example.invalid/ref",
        "license": "MIT", "win32_oracle_commit": oracle, "maintained_commit": maintained,
        "target": {"sha1": hashlib.sha1(raw).hexdigest(),
                   "sha256": hashlib.sha256(raw).hexdigest()},
        "pdb": {"path": "Doc/.pdb dump.txt", "guid": guid, "age": age},
        "symbols": {"_WinMain@16": "0100833a"},
        "source_groups": {"startup": {"files": ["source.cpp"], "apis": ["Foo"]}},
    }
    config_path = Path(directory) / "config.json";config_path.write_text(json.dumps(config))
    report = build(config_path, repo, image)
    assert report["public_symbol_addresses"]["_WinMain@16"] == "0100833a"
    assert report["source_groups"]["startup"]["api_references"][0]["occurrences"] == 2
    config["target"]["sha1"] = "0" * 40;config_path.write_text(json.dumps(config))
    try:
        build(config_path, repo, image)
    except ValueError as error:
        assert "identity" in str(error)
    else:
        raise AssertionError("mismatched target identity accepted")

for broken in (b"", b"MZ" + bytes(100)):
    try:
        pe_identity(broken)
    except ValueError:
        pass
    else:
        raise AssertionError("malformed PE accepted")

print("source oracle parser passed: PDB identity, public symbols and PE32 mapping")
