#!/usr/bin/env python3
"""Create a checked, minimal Minecraft payload for the selected installed instances."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def allowed(rules) -> bool:
    if rules is None:
        return True
    result = False
    for rule in rules:
        os = rule.get("os", {})
        matches = os.get("name", "windows") == "windows"
        if os.get("arch"):
            matches &= bool(re.fullmatch(os["arch"], "amd64") or re.fullmatch(os["arch"], "x86_64"))
        if os.get("version"):
            matches &= bool(re.fullmatch(os["version"], "10.0"))
        matches &= not any(value is True for value in rule.get("features", {}).values())
        if matches:
            result = rule.get("action") == "allow"
    return result


def maven(name: str) -> str:
    pieces = name.split(":")
    if len(pieces) not in (3, 4):
        raise ValueError("Invalid Maven coordinate")
    group, artifact, version = pieces[:3]
    classifier = "-" + pieces[3] if len(pieces) == 4 else ""
    return f"{group.replace('.', '/')}/{artifact}/{version}/{artifact}-{version}{classifier}.jar"


def properties(path: Path) -> dict:
    return dict(line.split("=", 1) for line in path.read_text(encoding="utf-8-sig").splitlines()
                if "=" in line and not line.startswith("#"))


def private(name: str) -> bool:
    name = name.lower()
    return (name.startswith(("launcher_accounts", "launcher_msa_credentials", "launcher_profiles")) or
            name in {"accounts.json", "account.json", "auth.properties", "auth-pending.json",
                     "launch-plan.json", "launch.profile", "usercache.json"} or name.endswith(".log"))


def select(source: Path, output: Path, instances: list[str]) -> dict:
    source, output = source.resolve(), output.resolve()
    workspace = Path(__file__).resolve().parent.parent
    if not output.is_relative_to(workspace) or output == workspace or output == source:
        raise ValueError("Payload output must be a separate directory inside this workspace")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Choose an empty output directory to avoid stale payload files")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {}

    def copy(relative: str, sha1: str = "", size: int = -1) -> Path:
        normalized = relative.replace("\\", "/")
        path = source / normalized
        if path.is_symlink() or not path.resolve().is_relative_to(source):
            raise ValueError("Unsafe payload source")
        if not path.is_file():
            raise ValueError(f"Missing installed file: {relative}")
        content = path.read_bytes()
        if size >= 0 and len(content) != size:
            raise ValueError(f"Size mismatch: {relative}")
        if sha1 and hashlib.sha1(content).hexdigest() != sha1.lower():
            raise ValueError(f"SHA1 mismatch: {relative}")
        target = output / normalized
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        manifest[normalized] = {"size": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        return target

    for instance in instances:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", instance) or instance in (".", ".."):
            raise ValueError("Invalid instance ID")
        folder = source / "instances" / instance
        config = properties(folder / "instance.properties")
        if config.get("installed") != "true":
            raise ValueError(f"Instance not installed: {instance}")
        meta = json.loads((folder / "installed.json").read_text())
        client = meta.get("downloads", {}).get("client", {})
        copy(meta["_clientPath"], client.get("sha1", ""), client.get("size", -1))
        version = config["version"]
        metadata = source / f"versions/{version}/{version}.json"
        if metadata.is_file():
            copy(str(metadata.relative_to(source)))
        for library in meta.get("libraries", []):
            if not allowed(library.get("rules")):
                continue
            downloads = library.get("downloads", {})
            artifact = downloads.get("artifact")
            if artifact:
                relative = artifact.get("path") or maven(library["name"])
                copy("libraries/" + relative, artifact.get("sha1", ""), artifact.get("size", -1))
            elif "downloads" not in library:
                copy("libraries/" + maven(library["name"]))
            classifier = library.get("natives", {}).get("windows", "").replace("${arch}", "64")
            if classifier:
                native = downloads.get("classifiers", {}).get(classifier, {})
                relative = native.get("path") or maven(library["name"] + ":" + classifier)
                copy("libraries/" + relative, native.get("sha1", ""), native.get("size", -1))
        index = meta.get("assetIndex")
        if index:
            relative = f"assets/indexes/{index['id']}.json"
            path = copy(relative, index.get("sha1", ""), index.get("size", -1))
            for asset in json.loads(path.read_text())["objects"].values():
                digest = asset["hash"]
                if not re.fullmatch("[0-9a-f]{40}", digest):
                    raise ValueError("Invalid asset hash")
                relative = f"assets/objects/{digest[:2]}/{digest}"
                if relative not in manifest:
                    copy(relative, digest, asset.get("size", -1))
            virtual = source / "assets/virtual" / index["id"]
            if virtual.is_dir():
                for path in virtual.rglob("*"):
                    if path.is_file():
                        copy(str(path.relative_to(source)))
        logging = meta.get("logging", {}).get("client", {}).get("file")
        if logging:
            copy("assets/log_configs/" + logging["id"], logging.get("sha1", ""), logging.get("size", -1))
        for path in folder.rglob("*"):
            if path.is_symlink():
                raise ValueError("Symlink in instance payload")
            if path.is_file() and not private(path.name):
                copy(str(path.relative_to(source)))
    for relative in ("cache/version_manifest_v2.json", "launcher-view.properties"):
        if (source / relative).is_file():
            copy(relative)
    report = {"schema": "prosperomc-payload/1", "instances": instances,
              "files": len(manifest), "bytes": sum(item["size"] for item in manifest.values()),
              "checks": "source metadata SHA1/size and per-file SHA256", "entries": manifest}
    (output / "PAYLOAD-REPORT.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != "entries"}))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--instance", action="append", required=True)
    args = parser.parse_args()
    select(args.source, args.out, args.instance)
