#!/usr/bin/env python3
"""Read only ProsperoMC diagnostics and produce a deduplicated error census."""
import argparse
import collections
import ftplib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = '/data/ProsperoMC'


def collect(host, port, out):
    out = out.resolve()
    if not out.is_relative_to(ROOT / 'artifacts'):
        raise ValueError('Diagnostics must stay under artifacts')
    out.mkdir(parents=True, exist_ok=True)
    receipt = {'files': [], 'unavailable': [], 'errors': {}}
    with ftplib.FTP() as ftp:
        ftp.connect(host, port, timeout=20)
        ftp.login()

        def listing(relative):
            rows = []
            try:
                ftp.retrlines('LIST ' + DATA + '/' + relative, rows.append)
            except ftplib.error_perm as error:
                receipt['unavailable'].append([relative, str(error)])
                return []
            return [(row[0] == 'd', row.split(maxsplit=8)[-1]) for row in rows
                    if len(row.split(maxsplit=8)) == 9]

        def read(relative):
            data = bytearray()
            def append(chunk):
                if len(data) + len(chunk) > 64 * 1024 * 1024:
                    raise ValueError('Diagnostic exceeds 64 MiB: ' + relative)
                data.extend(chunk)
            try:
                ftp.retrbinary('RETR ' + DATA + '/' + relative, append)
            except ftplib.error_perm as error:
                receipt['unavailable'].append([relative, str(error)])
                return
            path = out / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            receipt['files'].append({'path': relative, 'bytes': len(data)})
            counts = collections.Counter()
            for line in data.decode('utf-8', errors='replace').splitlines():
                if re.search(r'(?i)exception|caused by:|error|failed|fatal|file-inventory|file-probe', line):
                    normalized = re.sub(r'^REC seq=\d+ t=[\d.]+ ', '', line)
                    normalized = re.sub(r'^\[[\d:]+\] ', '', normalized)
                    counts[normalized] += 1
            receipt['errors'][relative] = dict(counts)

        for directory, name in listing('logs'):
            if not directory and re.fullmatch(r'session-\d+\.log', name):
                read('logs/' + name)
        for directory, instance in listing('instances'):
            if not directory or not re.fullmatch(r'[A-Za-z0-9_-]+', instance):
                continue
            base = 'instances/' + instance + '/.minecraft/'
            for folder in ('logs', 'crash-reports'):
                for is_dir, name in listing(base + folder):
                    if not is_dir and (name == 'latest.log' or re.fullmatch(r'crash-[\w.\-]+\.txt', name)):
                        read(base + folder + '/' + name)
        # Public build provenance only; never read private account or launch-plan files.
        read('STAGE-REPORT.json')
    (out / 'error-census.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps({'files': len(receipt['files']), 'unavailable': receipt['unavailable'],
                      'fatal': {name: {line: count for line, count in errors.items()
                                      if re.search(r'Caused by:|^WINESERVER java\.|VK_ERROR|Too many open|file-inventory|file-probe', line)}
                                for name, errors in receipt['errors'].items()}}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True)
    parser.add_argument('--port', type=int, default=2121)
    parser.add_argument('--out', type=Path, default=ROOT / 'artifacts/console-repair-full')
    args = parser.parse_args()
    collect(args.host, args.port, args.out)
