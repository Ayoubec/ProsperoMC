#!/usr/bin/env python3
"""Verify published app/core bytes; never confuse deployment with gameplay."""
import ftplib
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
deploy = SourceFileLoader('core_deploy', str(ROOT / 'scripts/deploy-ps5.py')).load_module()
core = SourceFileLoader('core_stage', str(ROOT / 'scripts/stage-runtime-v020-core.py')).load_module()
title = ROOT / 'dist/PPSA99888'
title_names, data_names = core.core_names(title)
title_names += ['eboot.bin', 'launcher/prosperomc-launcher.jar', 'STAGE-REPORT.json']
title_names += [name for name in ('WEBP_LICENSE.txt','WEBP_PATENTS.txt','THIRD_PARTY_NOTICES.md') if (title/name).is_file()]
data_names += ['launcher/prosperomc-launcher.jar', 'STAGE-REPORT.json']
if json.loads((title/'STAGE-REPORT.json').read_text()).get('zipfsBootstrapSha256'):
    title_names.append('launcher/prosperomc-zipfs.jar');data_names.append('launcher/prosperomc-zipfs.jar')
receipt = {'publishedFiles': [], 'consoleGameplayVerified': False}
with ftplib.FTP() as ftp:
    ftp.connect(sys.argv[1], 2121, timeout=30)
    ftp.login()
    for base, local_root, names in ((deploy.TITLE_ROOT, title, title_names),
                                   (deploy.DATA_ROOT, title / 'prosperomc', data_names)):
        manifest = deploy.remote_inventory(ftp, base)
        for name in names:
            local = local_root / name
            sha = deploy.file_digest(local)
            if manifest[name]['sha256'] != sha:
                raise ValueError('Published manifest differs: ' + name)
            remote = base + '/' + name
            ftp.voidcmd('TYPE I')
            deploy.verify_transferred_file(ftp, local, remote, manifest[name], ftp.size(remote))
            if local.read_bytes()[:4] not in (bytes.fromhex('5414f5ee'), bytes.fromhex('4f153d1d')):
                received = bytearray()
                def collect(data):
                    if len(received) + len(data) > local.stat().st_size:
                        raise ValueError('Readback exceeds expected size')
                    received.extend(data)
                ftp.retrbinary('RETR ' + remote, collect)
                if hashlib.sha256(received).hexdigest() != sha:
                    raise ValueError('Published bytes differ: ' + name)
            receipt['publishedFiles'].append({'path': remote, 'sha256': sha})
(ROOT / 'artifacts/console-runtime-core-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('PUBLISHED_APP_AND_CORE_VERIFIED', len(receipt['publishedFiles']))
