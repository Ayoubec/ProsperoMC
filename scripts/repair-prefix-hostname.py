#!/usr/bin/env python3
"""Normalize only this app's Wine computer name while the app is closed."""
import argparse
import ftplib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('patch', ROOT / 'scripts/deploy-ps5-patch.py')
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--host', required=True)
args = parser.parse_args()
title = ROOT / 'dist/PPSA99888'
data = title / 'prosperomc'
name = 'prefixes/minecraft/system.reg'
with ftplib.FTP() as ftp:
    ftp.connect(args.host, 2121, timeout=15)
    ftp.login()
    raw = bytearray()
    def collect(chunk):
        if len(raw) + len(chunk) > 16 * 1024 * 1024:
            raise ValueError('Registry exceeds expected limit')
        raw.extend(chunk)
    ftp.retrbinary('RETR ' + patch.deploy.DATA_ROOT + '/' + name, collect)
    backup = ROOT / 'artifacts/console-prefix-hostname'
    backup.mkdir(exist_ok=True)
    (backup / 'system-before.reg').write_bytes(raw)
    fixed, count = re.subn(rb'(?m)^"(ComputerName|Hostname|NV Hostname)"="[^"\r\n]*"',
                          rb'"\1"="localhost"', bytes(raw))
    if not count:
        raise ValueError('Wine computer-name registry values were not found')
    (data / name).write_bytes(fixed)
    for source in (title, data):
        report = json.loads((source / 'STAGE-REPORT.json').read_text())
        report['prefix']['computerName'] = 'localhost'
        (source / 'STAGE-REPORT.json').write_text(json.dumps(report, indent=2) + '\n')
    patch.deploy.validate_package(title, data)
    patch.publish(ftp, patch.deploy.DATA_ROOT, data, [name, 'STAGE-REPORT.json'])
    patch.publish(ftp, patch.deploy.TITLE_ROOT, title, ['STAGE-REPORT.json'])
    print('WINE_HOSTNAME_LOCALHOST', count)
