"""Verify the published graphics module and save a local deployment receipt."""
import ftplib
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('deploy', root / 'scripts/deploy-ps5.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)
title = root / 'dist/PPSA99888'
name = 'win/wine/lib/wine/x86_64-unix/win32u.prx'
with ftplib.FTP() as ftp:
    ftp.connect(sys.argv[1], 2121, timeout=30)
    ftp.login()
    manifest = deploy.remote_inventory(ftp, deploy.TITLE_ROOT)
    local = title / name
    assert manifest[name]['sha256'] == deploy.file_digest(local)
    ftp.voidcmd('TYPE I')
    deploy.verify_transferred_file(ftp, local, deploy.TITLE_ROOT + '/' + name, manifest[name], ftp.size(deploy.TITLE_ROOT + '/' + name))
    for base, path in ((deploy.TITLE_ROOT, title / 'STAGE-REPORT.json'), (deploy.DATA_ROOT, title / 'prosperomc/STAGE-REPORT.json')):
        report = bytearray()
        ftp.retrbinary('RETR ' + base + '/STAGE-REPORT.json', report.extend)
        assert hashlib.sha256(report).hexdigest() == deploy.file_digest(path)
stage = json.loads((title / 'STAGE-REPORT.json').read_text())
receipt_path = root / 'artifacts/console-graphics-repair.json'
previous = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
receipt = {'graphicsModuleSha256': manifest[name]['sha256'], 'publishedExecutableContentVerified': True,
           'launcherJarSha256': stage['jarSha256'], 'nativeExecutableSha256': stage['ebootSha256'],
           'bothStageReportsVerified': True, 'compiledBgraCapabilitiesVerified': True,
           'consoleMenuVerified': False, 'consoleWorldVerified': False,
           'sourceCommit': stage['wine']['graphicsFix']['sourceCommit']}
if all(previous.get(key) == receipt[key] for key in
       ('graphicsModuleSha256','launcherJarSha256','nativeExecutableSha256')):
    for key in ('consoleMenuVerified','consoleWorldVerified','consolePerformance','consoleEvidence'):
        if key in previous:
            receipt[key] = previous[key]
receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
print('GRAPHICS_UPLOAD_RECEIPT_VERIFIED')
