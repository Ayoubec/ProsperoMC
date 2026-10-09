#!/usr/bin/env python3
"""Publish only ProsperoMC executable/JAR repairs and their stage reports."""
import argparse
import ftplib
import hashlib
import importlib.util
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('deploy', Path(__file__).with_name('deploy-ps5.py'))
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


def publish(ftp, base, source, names, skip_unchanged=False):
    manifest = deploy.remote_inventory(ftp, base)
    if not manifest:
        raise ValueError('A complete existing ProsperoMC deployment is required')
    for name in names:
        local = source / name
        record = {'size': local.stat().st_size, 'sha256': deploy.file_digest(local)}
        target = base + '/' + name
        if skip_unchanged and manifest.get(name) == record:
            try:
                ftp.voidcmd('TYPE I')
                deploy.verify_transferred_file(ftp,local,target,record,ftp.size(target))
                print('UNCHANGED', target, flush=True)
                continue
            except ftplib.error_perm:
                pass
        pending = str(Path(target).parent).replace('\\','/') + '/.' + Path(name).name + '.prosperomc-upload'
        with local.open('rb') as stream:
            ftp.storbinary('STOR ' + pending, stream, blocksize=256 * 1024)
        ftp.voidcmd('TYPE I')
        deploy.verify_transferred_file(ftp, local, pending, record, ftp.size(pending))
        if local.read_bytes()[:4] not in (bytes.fromhex('5414f5ee'), bytes.fromhex('4f153d1d')):
            received = bytearray()
            def collect(chunk):
                if len(received) + len(chunk) > record['size']:
                    raise ValueError('Patch readback exceeds the expected file size')
                received.extend(chunk)
            ftp.retrbinary('RETR ' + pending, collect)
            if hashlib.sha256(received).hexdigest() != record['sha256']:
                raise ValueError('Patch readback hash mismatch')
        ftp.rename(pending, target)
        manifest[name] = record
        print('PATCHED', base + '/' + name, flush=True)
    pending = base + '/.' + deploy.MARKER + '.prosperomc-upload'
    ftp.storbinary('STOR ' + pending, io.BytesIO(json.dumps(manifest, separators=(',', ':')).encode()))
    ftp.rename(pending, base + '/' + deploy.MARKER)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True)
    parser.add_argument('--port', type=int, default=2121)
    parser.add_argument('--wine-fpfix', action='store_true', help='Publish only the verified ntdll repair and source notices')
    parser.add_argument('--launcher-only', action='store_true', help='Publish only the changed launcher JAR and reports')
    parser.add_argument('--graphics-only', action='store_true', help='Publish only the verified win32u graphics module and reports')
    parser.add_argument('--native-only', action='store_true', help='Publish only the native launcher executable and reports')
    parser.add_argument('--app-update', action='store_true', help='Update app binaries/reports, preserving console game data and settings')
    args = parser.parse_args()
    title = ROOT / 'dist/PPSA99888'
    data = title / 'prosperomc'
    deploy.validate_package(title, data)
    with ftplib.FTP() as ftp:
        ftp.connect(args.host, args.port, timeout=30)
        ftp.login()
        if 'eboot.bin' not in deploy.remote_inventory(ftp, deploy.TITLE_ROOT):
            raise ValueError('Existing title executable is missing from deployment manifest')
        if args.app_update:
            names = ['launcher/prosperomc-launcher.jar','win/wine/lib/wine/x86_64-unix/ntdll.prx',
                     'win/wine/lib/wine/x86_64-unix/win32u.prx','WINE_SOURCES.txt','STAGE-REPORT.json','eboot.bin',
                     'sce_sys/icon0.png','sce_sys/pic0.dds','sce_sys/pic1.dds']
            names += [p.relative_to(title).as_posix() for p in sorted((title / 'WINE_PATCHES').glob('*.patch'))]
            deploy.ensure_directory(ftp,deploy.TITLE_ROOT+'/WINE_PATCHES')
            publish(ftp,deploy.DATA_ROOT,data,['launcher/prosperomc-launcher.jar','STAGE-REPORT.json'],True)
            publish(ftp,deploy.TITLE_ROOT,title,names,True)
        elif args.native_only:
            publish(ftp, deploy.TITLE_ROOT, title, ['eboot.bin', 'STAGE-REPORT.json'])
            publish(ftp, deploy.DATA_ROOT, data, ['STAGE-REPORT.json'])
        elif args.graphics_only:
            graphics = json.loads((title / 'STAGE-REPORT.json').read_text()).get('wine', {}).get('graphicsFix')
            if not graphics:
                raise ValueError('Stage the verified graphics module before uploading it')
            names = ['win/wine/lib/wine/x86_64-unix/win32u.prx','WINE_SOURCES.txt','STAGE-REPORT.json']
            patch = graphics.get('localPatch')
            if patch:
                if Path(patch['file']).name != patch['file'] or not patch['file'].endswith('.patch'):
                    raise ValueError('Invalid graphics source patch name')
                name = 'WINE_PATCHES/'+patch['file']
                if deploy.file_digest(title / name) != patch['sha256']:
                    raise ValueError('Graphics source patch hash mismatch')
                deploy.ensure_directory(ftp,deploy.TITLE_ROOT+'/WINE_PATCHES')
                names.insert(0,name)
            publish(ftp, deploy.TITLE_ROOT, title, names)
            publish(ftp, deploy.DATA_ROOT, data, ['STAGE-REPORT.json'])
        elif args.wine_fpfix:
            if not json.loads((title / 'STAGE-REPORT.json').read_text()).get('wine', {}).get('ntdllFix'):
                raise ValueError('Stage the verified ntdll repair before uploading it')
            patch = 'WINE_PATCHES/0501-ntdll-ps5-signal-fp-state-at-its-measured-offset.patch'
            deploy.ensure_directory(ftp, deploy.TITLE_ROOT + '/WINE_PATCHES')
            publish(ftp, deploy.TITLE_ROOT, title, ['win/wine/lib/wine/x86_64-unix/ntdll.prx',
                    patch, 'WINE_SOURCES.txt', 'STAGE-REPORT.json'])
            publish(ftp, deploy.DATA_ROOT, data, ['STAGE-REPORT.json'])
        elif args.launcher_only:
            publish(ftp, deploy.DATA_ROOT, data, ['launcher/prosperomc-launcher.jar', 'STAGE-REPORT.json'])
            publish(ftp, deploy.TITLE_ROOT, title, ['launcher/prosperomc-launcher.jar', 'STAGE-REPORT.json'])
        else:
            publish(ftp, deploy.DATA_ROOT, data, ['prefixes/minecraft/dosdevices/.pw-symlinks', 'launcher/prosperomc-launcher.jar', 'STAGE-REPORT.json'])
            publish(ftp, deploy.TITLE_ROOT, title, ['launcher/prosperomc-launcher.jar', 'eboot.bin', 'STAGE-REPORT.json'])
        # A newly verified executable must get one fresh backend start.
        for transient in ('backend-failed', 'runtime-notice.properties'):
            try:
                ftp.sendcmd('DELE ' + deploy.DATA_ROOT + '/' + transient)
            except ftplib.error_perm as error:
                if not str(error).startswith('550'):
                    raise
    print('PS5_EXECUTABLE_PATCH_COMPLETE')
