#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Emit and validate a staged i386 Wine PE runtime distribution.

The distribution is a directory of PE modules built from one pinned Wine
revision. This tool hashes exactly the bytes a second developer would map and
records them in a manifest whose aggregate digest is reproducible from the
module list alone, so a partial or substituted runtime cannot pass as the
audited one.

`write` refuses to overwrite an existing manifest: a published runtime
identity is evidence, not a scratch file.

Usage:
    validate_wine_runtime.py write --distribution DIR --wine-source DIR
        --wine-commit SHA --configure "..." --out FILE
    validate_wine_runtime.py check --manifest FILE --distribution DIR
        [--expect-commit SHA]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

SCHEMA = "prospero-win-wine-runtime-manifest/1"
ARCHITECTURE = "i386"
PE_MACHINE_I386 = 0x014C
PE_MAGIC_PE32 = 0x010B
SUBSYSTEM_NAMES = {
    1: "native",
    2: "windows-gui",
    3: "windows-console",
    9: "windows-ce",
    10: "efi-application",
}
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}\.dll$")


class Failure(SystemExit):
    def __init__(self, message: str) -> None:
        super().__init__(f"wine runtime manifest: {message}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def distribution_digest(modules: list[dict], data: list[dict]) -> str:
    """Aggregate identity over the whole distribution, order-independent.

    The line format is part of the contract: a validator that recomputes it
    from the manifest must agree with one that recomputes it from disk. The
    modules come first and the data files after them, each block sorted by
    name, so adding a data file to a distribution changes its identity - which
    is the point: the NLS data is part of what this runtime *is*, and a
    distribution that carries it is not the distribution that did not.
    """
    lines = [
        f"{module['name']}\t{module['size']}\t{module['sha256']}\n"
        for module in sorted(modules, key=lambda entry: entry["name"])
    ]
    lines += [
        f"data\t{entry['name']}\t{entry['size']}\t{entry['sha256']}\n"
        for entry in sorted(data, key=lambda entry: entry["name"])
    ]
    return sha256_bytes("".join(lines).encode("utf-8"))


def scan_data(distribution: Path, spec: str) -> dict:
    """One data file of the distribution, named by its staged relative path."""
    if "=" in spec:
        name, _, relative = spec.partition("=")
    else:
        name = relative = spec
    if not name or "/" not in relative and relative.startswith("/"):
        raise Failure(f"data specification is not a relative path: {spec}")
    path = (distribution / relative).resolve()
    if distribution not in path.parents:
        raise Failure(f"data file escapes the distribution: {spec}")
    if not path.is_file():
        raise Failure(f"missing data file: {relative}")
    return {
        "name": name,
        "path": relative,
        "size": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def pe_identity(path: Path) -> dict:
    """Machine, PE magic and subsystem, read from the mapped file bytes."""
    raw = path.read_bytes()
    if len(raw) < 0x40 or raw[:2] != b"MZ":
        raise Failure(f"{path.name} is not a PE image (missing MZ)")
    nt_offset = struct.unpack_from("<I", raw, 0x3C)[0]
    if nt_offset + 0x40 > len(raw) or raw[nt_offset:nt_offset + 4] != b"PE\0\0":
        raise Failure(f"{path.name} is not a PE image (missing PE signature)")
    coff = nt_offset + 4
    machine = struct.unpack_from("<H", raw, coff)[0]
    optional_bytes = struct.unpack_from("<H", raw, coff + 16)[0]
    optional = coff + 20
    if optional + 0x46 > len(raw) or optional_bytes < 0x46:
        raise Failure(f"{path.name} has a truncated optional header")
    magic = struct.unpack_from("<H", raw, optional)[0]
    subsystem = struct.unpack_from("<H", raw, optional + 0x44)[0]
    return {
        "machine": machine,
        "magic": magic,
        "subsystem": subsystem,
    }


def canonical_model(modules: list[dict]) -> list[dict]:
    """Validate one module list and return it sorted by canonical name."""
    seen: set[str] = set()
    names: list[str] = []
    for entry in modules:
        if not isinstance(entry, dict):
            raise Failure("module entry is not an object")
        for field in ("name", "path", "size", "sha256", "pe_machine"):
            if field not in entry:
                raise Failure(f"module entry lacks {field}")
        name = entry["name"]
        if not isinstance(name, str) or not NAME_RE.match(name):
            raise Failure(
                f"module name is not a canonical lowercase .dll name: {name!r}")
        if ".." in name or "/" in name or "\\" in name:
            raise Failure(f"module name escapes the distribution: {name!r}")
        if name in seen:
            raise Failure(f"duplicate module name: {name}")
        seen.add(name)
        names.append(name)
    ordered = sorted(modules, key=lambda entry: entry["name"])
    return ordered


def distribution_dir(distribution: Path, name: str) -> Path:
    """Relative, traversal-free module path inside the distribution."""
    if not isinstance(name, str) or not name:
        raise Failure("module path is empty")
    if name.startswith(("/", "\\")) or ":" in name:
        raise Failure(f"module path is absolute: {name!r}")
    parts = Path(name).parts
    if any(part in ("..", "") for part in parts):
        raise Failure(f"module path traverses out of the distribution: {name!r}")
    return distribution / name


def scan_distribution(distribution: Path, library: str) -> list[dict]:
    root = distribution / library
    if not root.is_dir():
        raise Failure(f"distribution has no {library}/ directory: {distribution}")
    modules: list[dict] = []
    for path in sorted(root.iterdir()):
        if not path.is_file():
            raise Failure(f"unexpected non-file entry: {path.name}")
        name = path.name
        if not NAME_RE.match(name):
            raise Failure(f"module is not a canonical lowercase .dll name: {name}")
        identity = pe_identity(path)
        modules.append({
            "name": name,
            "path": f"{library}/{name}",
            "size": path.stat().st_size,
            "sha256": file_sha256(path),
            "pe_machine": identity["machine"],
            "pe_magic": identity["magic"],
            "subsystem": SUBSYSTEM_NAMES.get(identity["subsystem"],
                                             str(identity["subsystem"])),
        })
    if not modules:
        raise Failure(f"distribution {root} contains no modules")
    return canonical_model(modules)


def tool_versions() -> dict:
    versions: dict[str, str] = {"python": sys.version.split()[0]}
    for key, command in (
        ("cc", [os.environ.get("CC", "cc"), "--version"]),
        ("clang", ["clang", "--version"]),
        ("i686-w64-mingw32-gcc", ["i686-w64-mingw32-gcc", "--version"]),
        ("ld", ["ld", "--version"]),
    ):
        executable = shutil.which(command[0])
        if executable is None:
            versions[key] = "absent"
            continue
        try:
            completed = subprocess.run(command, check=False, capture_output=True,
                                       text=True)
        except OSError:
            versions[key] = "absent"
            continue
        first = completed.stdout.splitlines()[:1]
        versions[key] = first[0].strip() if first else "unknown"
    return versions


def wine_version(source: Path) -> str:
    """Wine's own version string, from configure or the VERSION file."""
    version = source / "VERSION"
    if version.exists():
        text = version.read_text(encoding="utf-8").strip()
        if text:
            return text
    configure = source / "configure"
    if configure.exists():
        completed = subprocess.run([str(configure), "--version"], check=False,
                                   capture_output=True, text=True)
        for line in completed.stdout.splitlines():
            if line.strip().lower().startswith("wine version"):
                return line.strip()
    raise Failure("cannot determine the Wine version")


def wine_head(source: Path) -> tuple[str, bool]:
    completed = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                               check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise Failure("Wine source is not a git checkout")
    status = subprocess.run(["git", "-C", str(source), "status", "--porcelain"],
                            check=False, capture_output=True, text=True)
    return completed.stdout.strip(), status.stdout.strip() == ""


def command_write(arguments: argparse.Namespace) -> int:
    out = Path(arguments.out)
    if out.exists() and not arguments.force:
        raise Failure(f"refusing to overwrite {out}")
    distribution = Path(arguments.distribution).resolve()
    source = Path(arguments.wine_source).resolve()
    commit, clean = wine_head(source)
    if not clean:
        raise Failure("Wine source checkout is dirty")
    if arguments.wine_commit and commit != arguments.wine_commit:
        raise Failure(f"Wine checkout is {commit}, not {arguments.wine_commit}")
    modules = scan_distribution(distribution, arguments.library)
    for module in modules:
        if module["pe_machine"] != PE_MACHINE_I386:
            raise Failure(f"{module['name']} is not an i386 PE image")
        if module["pe_magic"] != PE_MAGIC_PE32:
            raise Failure(f"{module['name']} is not PE32")
    data = [scan_data(distribution, spec) for spec in (arguments.data or [])]
    manifest = {
        "schema": SCHEMA,
        "wine": {
            "commit": commit,
            "version": wine_version(source),
            "source_url": arguments.wine_url,
            "clean": True,
        },
        "target": {
            "architecture": ARCHITECTURE,
            "pe_magic": "pe32",
            "subsystem": modules[0]["subsystem"],
            "library": arguments.library,
        },
        "build": {
            "configure": arguments.configure,
            "environment": {
                "LC_ALL": os.environ.get("LC_ALL", ""),
                "TZ": os.environ.get("TZ", ""),
                "SOURCE_DATE_EPOCH": os.environ.get("SOURCE_DATE_EPOCH", ""),
            },
            "tools": tool_versions(),
        },
        "modules": modules,
        "data": data,
        "distribution_sha256": distribution_digest(modules, data),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"wine runtime manifest written: {out} "
          f"modules={len(modules)} digest={manifest['distribution_sha256']}")
    return 0


def command_check(arguments: argparse.Namespace) -> int:
    manifest_path = Path(arguments.manifest)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise Failure(f"cannot read {manifest_path}: {error}") from error
    if manifest.get("schema") != SCHEMA:
        raise Failure(f"unknown schema version: {manifest.get('schema')!r}")
    wine = manifest.get("wine")
    target = manifest.get("target")
    if not isinstance(wine, dict) or not isinstance(target, dict):
        raise Failure("manifest lacks the wine or target section")
    if target.get("architecture") != ARCHITECTURE:
        raise Failure(f"unexpected architecture: {target.get('architecture')!r}")
    if arguments.expect_commit and wine.get("commit") != arguments.expect_commit:
        raise Failure(f"manifest pins Wine {wine.get('commit')}, "
                      f"expected {arguments.expect_commit}")
    modules = manifest.get("modules")
    if not isinstance(modules, list) or not modules:
        raise Failure("manifest lists no modules")
    ordered = canonical_model(modules)
    distribution = Path(arguments.distribution).resolve()
    library = target.get("library", "lib/i386-windows")
    for module in ordered:
        path = distribution_dir(distribution, module["path"])
        if not path.is_file():
            raise Failure(f"module file is missing: {module['path']}")
        size = path.stat().st_size
        if size != module["size"]:
            raise Failure(f"{module['name']} size drift: "
                          f"{size} != {module['size']}")
        identity = pe_identity(path)
        if identity["machine"] != module["pe_machine"]:
            raise Failure(f"{module['name']} machine drift: "
                          f"{identity['machine']:#x} != "
                          f"{module['pe_machine']:#x}")
        if identity["machine"] != PE_MACHINE_I386:
            raise Failure(f"{module['name']} is not an i386 PE image")
        if identity["magic"] != PE_MAGIC_PE32:
            raise Failure(f"{module['name']} is not PE32")
        digest = file_sha256(path)
        if digest != module["sha256"]:
            raise Failure(f"{module['name']} hash drift: "
                          f"{digest} != {module['sha256']}")
        if module["path"] != f"{library}/{module['name']}":
            raise Failure(f"{module['name']} path is not inside {library}/")
    declared_data = manifest.get("data", [])
    if not isinstance(declared_data, list):
        raise Failure("the manifest's data list is not a list")
    for entry in declared_data:
        path = distribution_dir(distribution, entry["path"])
        if not path.is_file():
            raise Failure(f"data file is missing: {entry['path']}")
        size = path.stat().st_size
        if size != entry["size"]:
            raise Failure(f"{entry['name']} size drift: {size} != {entry['size']}")
        digest = file_sha256(path)
        if digest != entry["sha256"]:
            raise Failure(f"{entry['name']} hash drift: "
                          f"{digest} != {entry['sha256']}")
    if distribution_digest(ordered, declared_data) != manifest.get(
            "distribution_sha256"):
        raise Failure("distribution digest does not match the manifest's files")
    print(f"wine runtime manifest check passed: {len(ordered)} modules, "
          f"{len(declared_data)} data file(s), "
          f"wine={wine.get('commit', '?')[:12]}, "
          f"digest={manifest['distribution_sha256']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write", help="hash a staged distribution")
    write.add_argument("--distribution", required=True)
    write.add_argument("--wine-source", required=True)
    write.add_argument("--wine-commit", default="")
    write.add_argument("--wine-url", default="https://github.com/wine-mirror/wine.git")
    write.add_argument("--library", default="lib/i386-windows")
    write.add_argument(
        "--data", action="append", default=[],
        help="a data file of the distribution, as [name=]relative/path; "
             "recorded in the manifest and folded into the distribution hash")
    write.add_argument("--configure", default="")
    write.add_argument("--out", required=True)
    write.add_argument("--force", action="store_true")
    write.set_defaults(handler=command_write)
    check = sub.add_parser("check", help="validate a manifest against a staged tree")
    check.add_argument("--manifest", required=True)
    check.add_argument("--distribution", required=True)
    check.add_argument("--expect-commit", default="")
    check.set_defaults(handler=command_check)
    arguments = parser.parse_args(argv)
    return arguments.handler(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
