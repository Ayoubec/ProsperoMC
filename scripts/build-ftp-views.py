#!/usr/bin/env python3
"""Build verified ELF comparison views for our own unsigned homebrew SELF files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess


def canonical_elf(raw, ranges):
    data = bytearray(raw)
    for start, length in ranges:
        if start < 0 or length < 0 or start + length > len(data):
            raise ValueError('Invalid ELF metadata range')
        data[start:start + length] = bytes(length)
    return hashlib.sha256(data).hexdigest()


def metadata_ranges(raw):
    if raw[:4] != b'\x7fELF' or raw[4:6] != b'\x02\x01':
        raise ValueError('Expected little-endian ELF64')
    offset = struct.unpack_from('<Q', raw, 32)[0]
    stride, count = struct.unpack_from('<HH', raw, 54)
    if stride != 56 or offset + count * stride > len(raw):
        raise ValueError('Invalid ELF program table')
    loads, ranges = [], []
    for i in range(count):
        at = offset + i * stride
        kind = struct.unpack_from('<I', raw, at)[0]
        start = struct.unpack_from('<Q', raw, at + 8)[0]
        length = struct.unpack_from('<Q', raw, at + 32)[0]
        if kind == 1:
            loads.append((start, start + length))
        if kind == 0x6fffff01:
            if length > 4096 or start + length > len(raw):
                raise ValueError('Invalid SCE version-record region')
            ranges.append((start, length))
    for start, length in ranges:
        if any(start < end and start + length > begin for begin, end in loads):
            raise ValueError('Version metadata overlaps executable/loadable content')
    return ranges


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool', type=Path, required=True)
    parser.add_argument('--title', type=Path, default=Path('dist/PPSA99888'))
    parser.add_argument('--file', type=Path, help='Refresh only this signed file, preserving unchanged comparison records')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    out = root / 'artifacts/ftp-elf-views'
    out.mkdir(parents=True, exist_ok=True)
    records_path = root / 'artifacts/ftp-elf-views.json'
    records = json.loads(records_path.read_text()) if args.file else {}
    candidates = []
    if args.file:
        if not args.file.resolve().is_relative_to(args.title.resolve()):
            raise ValueError('Comparison input must be inside the staged title')
        candidates.append(args.file)
    else:
        for directory, folders, files in os.walk(args.title):
            if Path(directory) == args.title:
                folders[:] = [name for name in folders if name != 'prosperomc']
            candidates.extend(Path(directory) / name for name in files
                              if Path(name).suffix.lower() in ('.bin', '.prx', '.sprx', '.self', '.elf'))
    for source in sorted(candidates):
        if not source.is_file():
            continue
        if source.relative_to(args.title).parts[0] == 'prosperomc':
            continue
        with source.open('rb') as stream:
            magic = stream.read(4)
        if magic not in (bytes.fromhex('5414f5ee'), bytes.fromhex('4f153d1d')):
            continue
        relative = source.resolve().relative_to(root).as_posix()
        target = out / (relative.replace('/', '_') + '.elf')
        subprocess.run([str(args.tool), 'self', '--extract', '--file', str(source), '--out', str(target)],
                       check=True, stdout=subprocess.DEVNULL)
        elf = target.read_bytes()
        ranges = metadata_ranges(elf)
        records[relative] = {'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                             'elfSize': len(elf), 'elfSha256': hashlib.sha256(elf).hexdigest(),
                             'metadataRanges': ranges, 'canonicalSha256': canonical_elf(elf, ranges)}
    pending = records_path.with_suffix('.tmp')
    pending.write_text(json.dumps(records, indent=2))
    pending.replace(records_path)
    print('FTP_ELF_COMPARISON_VIEWS', len(records))
