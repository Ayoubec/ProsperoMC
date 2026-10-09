#!/usr/bin/env python3
"""Read bounded ProsperoMC status files and the two newest native logs."""
import argparse
import ftplib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
DATA = '/data/ProsperoMC'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--host', required=True)
parser.add_argument('--port', type=int, default=2121)
parser.add_argument('--out', type=Path, default=ROOT / 'artifacts/console-fpfix-retest')
parser.add_argument('--sessions', type=int, choices=range(1,9), default=2)
args = parser.parse_args()
out = args.out.resolve()
if not out.is_relative_to(ROOT / 'artifacts'):
    raise ValueError('Diagnostic output must stay inside workspace artifacts')
out.mkdir(parents=True, exist_ok=True)
status = {}
with ftplib.FTP() as ftp:
    ftp.connect(args.host, args.port, timeout=15)
    ftp.login()
    def read(relative):
        data = bytearray()
        is_log = relative.startswith('logs/session-')
        def collect(chunk):
            if not is_log and len(data) + len(chunk) > 512 * 1024:
                raise ValueError('Diagnostic file exceeds limit')
            data.extend(chunk)
            if is_log and len(data) > 512 * 1024:
                del data[:-512 * 1024]
        try:
            offset = 0
            if is_log:
                ftp.voidcmd('TYPE I')
                offset = max(0, (ftp.size(DATA + '/' + relative) or 0) - 512 * 1024)
            ftp.retrbinary('RETR ' + DATA + '/' + relative, collect, rest=offset or None)
        except ftplib.error_perm as error:
            if str(error).startswith('550'):
                return None
            raise
        (out / relative.replace('/', '_')).write_bytes(data)
        return data.decode('utf-8', errors='replace')
    for name in ('backend-ready.properties', 'progress.properties', 'response.properties', 'backend-failed'):
        status[name] = read(name)
    listing = []
    ftp.retrlines('LIST ' + DATA + '/logs', listing.append)
    logs = []
    for line in listing:
        match = re.search(r'\b(session-([0-9]+)\.log)$', line)
        if match:
            logs.append((int(match.group(2)), match.group(1)))
    next_slot = read('logs/next.txt')
    by_slot = dict(logs)
    if next_slot and next_slot.strip().isdigit():
        # Native diagnostics rotate through eight slots; the highest slot is
        # not necessarily the newest session after wraparound.
        next_number = int(next_slot.strip()) % 8
        recent = [by_slot[slot] for slot in ((next_number-n)%8 for n in range(args.sessions,0,-1)) if slot in by_slot]
    else:
        recent = [name for _, name in sorted(logs)[-args.sessions:]]
    for name in recent:
        value = read('logs/' + name)
        status[name] = {'bytes': len(value.encode()) if value else 0,
                        'tail': value.splitlines()[-12:] if value else []}
(out / 'status.json').write_text(json.dumps(status, indent=2))
print(json.dumps(status, indent=2))
