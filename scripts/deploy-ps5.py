#!/usr/bin/env python3
"""Upload only this title and its staged data, with completed files published last."""
from __future__ import annotations

import argparse
import ftplib
import hashlib
import io
import json
from pathlib import Path
import posixpath
import socket
import time

TITLE_ID = "PPSA99888"
TITLE_ROOT = f"/data/homebrew/{TITLE_ID}"
DATA_ROOT = "/data/ProsperoMC"
MARKER = "prosperomc-deploy.json"
PROJECT = Path(__file__).resolve().parent.parent


def verify_transferred_file(ftp, local, remote, expected, reported_size):
    with local.open('rb') as file:
        signed = file.read(4) in (bytes.fromhex('5414f5ee'), bytes.fromhex('4f153d1d'))
    if not signed:
        if reported_size != expected['size']:
            raise ValueError(f"FTP size mismatch: {local.name}: {reported_size} != {expected['size']}")
        return
    # PS5 FTP may expose SELF files through the kernel's reconstructed ELF view.
    # Compare all bytes; normalize only the non-loadable SCE version records.
    records_path = PROJECT / 'artifacts/ftp-elf-views.json'
    if not records_path.is_file():
        raise ValueError('Build the signed-file FTP ELF views before deployment')
    record = json.loads(records_path.read_text())[local.resolve().relative_to(PROJECT).as_posix()]
    if record['sourceSha256'] != expected['sha256']:
        raise ValueError('FTP comparison view is stale')
    data = io.BytesIO()
    def collect(chunk):
        if data.tell() + len(chunk) > max(expected['size'], record['elfSize']):
            raise ValueError('Remote signed-file view exceeds expected bounds')
        data.write(chunk)
    ftp.retrbinary('RETR ' + remote, collect)
    raw = data.getvalue()
    if len(raw) == expected['size'] and hashlib.sha256(raw).hexdigest() == expected['sha256']:
        return
    if len(raw) != record['elfSize'] or raw[:4] != b'\x7fELF':
        raise ValueError('Remote signed-file representation does not match the build')
    canonical = bytearray(raw)
    for start, length in record['metadataRanges']:
        canonical[start:start + length] = bytes(length)
    if hashlib.sha256(canonical).hexdigest() != record['canonicalSha256']:
        raise ValueError(f'FTP executable content mismatch: {local.name}')
    print(f'VERIFIED PS5 ELF VIEW: {local.name}', flush=True)


def file_digest(path: Path) -> str:
    for attempt in range(3):
        try:
            before = path.stat()
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1 << 20), b""):
                    digest.update(chunk)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise OSError("Source file changed during hashing")
            return digest.hexdigest()
        except OSError:
            if attempt == 2:
                raise
            time.sleep(0.1 * (attempt + 1))


def validate_package(title: Path, data: Path) -> dict:
    identity = json.loads((title / "sce_sys/param.json").read_text(encoding="utf-8-sig"))
    report = json.loads((title / "STAGE-REPORT.json").read_text())
    if identity.get("titleId") != TITLE_ID or not report.get("structurallyComplete"):
        raise ValueError("Only a validated, structurally complete ProsperoMC title may be uploaded")
    checks = {
        title / "eboot.bin": report.get("ebootSha256"),
        title / "launcher/prosperomc-launcher.jar": report.get("jarSha256"),
        data / "launcher/prosperomc-launcher.jar": report.get("jarSha256"),
        data / "runtimes/java8/bin/java.exe": report.get("javaSha256"),
        data / "prefixes/minecraft/dosdevices/.pw-symlinks": report.get("wineDriveTableSha256"),
        title / "win/wine/lib/wine/x86_64-unix/ntdll.prx": report.get("wine", {}).get("ntdllSha256"),
        title / "win/wine/lib/wine/x86_64-unix/win32u.prx": report.get("wine", {}).get("win32uSha256"),
    }
    if report.get("helper"):
        checks[title / "lapy.elf"] = report["helper"].get("elf_sha256")
    if report.get('zipfsBootstrapSha256'):
        for base in (title,data):
            checks[base/'launcher/prosperomc-zipfs.jar']=report['zipfsBootstrapSha256']
    if report.get("wine", {}).get("vulkanSha256"):
        checks[title / "win/wine/lib/wine/x86_64-unix/libvulkan.prx"] = report['wine']['vulkanSha256']
    if report.get('wine', {}).get('runtimeCore'):
        from importlib.machinery import SourceFileLoader
        core = SourceFileLoader('runtime_core_validate', str(PROJECT / 'scripts/stage-runtime-v020-core.py')).load_module()
        core.core_names(title, data)
    for path, expected in checks.items():
        if not expected or not path.is_file() or file_digest(path) != expected:
            raise ValueError(f"Staged input changed or is missing: {path}")
    if (data / 'prefixes/minecraft/dosdevices/.pw-symlinks').read_bytes() not in (
        b'c:\t../drive_c\nz:\t/\n', b'c:\t../drive_c\np:\t/data/ProsperoMC\nz:\t/\n'):
        raise ValueError('Wine drive mapping table must use exact Unix line endings')
    for file in data.rglob("*"):
        name = file.name.lower()
        if file.is_file() and (name.startswith(("launcher_accounts", "launcher_msa_credentials")) or
            name in {"auth.properties", "auth-pending.json", "launch-plan.json", "launch.profile"}):
            raise ValueError(f"Private/host launch state in staged data: {file}")
    return report


def inventory(source: Path, exclude_data: bool = False) -> dict[str, dict]:
    source = source.resolve()
    result = {}
    for file in sorted(source.rglob("*")):
        if file.is_symlink():
            raise ValueError(f"Refusing symlink upload: {file}")
        if not file.is_file() or file.name == MARKER:
            continue
        relative = file.relative_to(source).as_posix()
        if exclude_data and relative.startswith('prosperomc/'):
            continue
        if "\r" in relative or "\n" in relative:
            raise ValueError("Invalid FTP filename")
        result[relative] = {"size": file.stat().st_size, "sha256": file_digest(file)}
    return result


def remote_inventory(ftp: ftplib.FTP, remote: str) -> dict:
    data = io.BytesIO()
    def collect(chunk: bytes) -> None:
        if data.tell() + len(chunk) > 4 << 20:
            raise ValueError("Remote manifest exceeds limit")
        data.write(chunk)
    try:
        ftp.retrbinary(f"RETR {remote}/{MARKER}", collect)
        value = json.loads(data.getvalue())
        return value if isinstance(value, dict) else {}
    except (ftplib.error_perm, json.JSONDecodeError):
        return {}


def ensure_directory(ftp: ftplib.FTP, remote: str) -> None:
    if not (remote == TITLE_ROOT or remote.startswith(TITLE_ROOT + "/") or
            remote == DATA_ROOT or remote.startswith(DATA_ROOT + "/")):
        raise ValueError(f"FTP mutation outside this app: {remote}")
    parts = remote.strip("/").split("/")
    current = ""
    for part in parts:
        current += "/" + part
        try:
            ftp.cwd(current)
        except ftplib.error_perm:
            if current not in (TITLE_ROOT, DATA_ROOT) and not (
                current.startswith(TITLE_ROOT + "/") or current.startswith(DATA_ROOT + "/")
            ):
                raise ValueError(f"Parent directory must already exist: {current}")
            ftp.mkd(current)
    ftp.cwd("/")


def upload_tree(ftp: ftplib.FTP, source: Path, remote: str) -> tuple[int, int]:
    files = inventory(source, exclude_data=(remote == TITLE_ROOT))
    previous = remote_inventory(ftp, remote)
    ensure_directory(ftp, remote)
    directories = {remote}
    uploaded = skipped = 0
    ordered = sorted(files, key=lambda name: (
        name == "sce_sys/param.json", name == "eboot.bin", name
    ))
    for relative in ordered:
        target = remote + "/" + relative
        if previous.get(relative) == files[relative]:
            try:
                ftp.voidcmd("TYPE I")
                if ftp.size(target) == files[relative]["size"]:
                    skipped += 1
                    if skipped % 1000 == 0:
                        print(f"UNCHANGED {remote}: {skipped} files", flush=True)
                    continue
            except ftplib.error_perm:
                pass
        directory = posixpath.dirname(target)
        if directory not in directories:
            ensure_directory(ftp, directory)
            directories.add(directory)
        pending = directory + "/." + posixpath.basename(target) + ".prosperomc-upload"
        with (source / relative).open("rb") as stream:
            ftp.storbinary("STOR " + pending, stream, blocksize=256 * 1024)
        ftp.voidcmd("TYPE I")
        size = ftp.size(pending)
        verify_transferred_file(ftp, source / relative, pending, files[relative], size)
        ftp.rename(pending, target)
        if target.endswith((".bin", ".prx", ".elf")):
            try:
                ftp.sendcmd("SITE CHMOD 777 " + target)
            except ftplib.error_perm:
                pass
        uploaded += 1
        if uploaded % 100 == 0:
            print(f"UPLOAD {remote}: {uploaded} files", flush=True)
    pending_marker = remote + "/." + MARKER + ".prosperomc-upload"
    ftp.storbinary("STOR " + pending_marker,
                   io.BytesIO(json.dumps(files, separators=(",", ":")).encode()))
    ftp.rename(pending_marker, remote + "/" + MARKER)
    return uploaded, skipped


def inspect(ftp: ftplib.FTP) -> None:
    for remote in (TITLE_ROOT, DATA_ROOT):
        try:
            ftp.cwd(remote)
            rows = []
            ftp.retrlines("LIST", rows.append)
            print(json.dumps({"path": remote, "entries": rows}))
        except ftplib.error_perm as error:
            print(json.dumps({"path": remote, "status": str(error)}))
    ftp.cwd("/")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=2121)
    parser.add_argument("--title", type=Path)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if not args.inspect:
        if not args.title or not args.data:
            parser.error("--title and --data are required for upload")
        validate_package(args.title, args.data)
        if args.validate_only:
            title_files, data_files = inventory(args.title, exclude_data=True), inventory(args.data)
            print(f"PACKAGE_HASHES_VALID: {len(title_files)} title files, {len(data_files)} data files")
            return
    with ftplib.FTP() as ftp:
        ftp.connect(args.host, args.port, timeout=30)
        ftp.login()
        if args.inspect:
            inspect(ftp)
            return
        data_result = upload_tree(ftp, args.data, DATA_ROOT)
        title_result = upload_tree(ftp, args.title, TITLE_ROOT)
        print(json.dumps({"uploadedData": data_result[0], "skippedData": data_result[1],
                          "uploadedTitle": title_result[0], "skippedTitle": title_result[1]}))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, ftplib.Error, socket.error) as error:
        raise SystemExit(f"DEPLOY_FAILED: {error}")
