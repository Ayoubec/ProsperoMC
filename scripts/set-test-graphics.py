#!/usr/bin/env python3
"""Set only the installed vanilla 1.12.2's reversible graphics options."""
import argparse
import ftplib
import hashlib
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REMOTE = '/data/ProsperoMC/instances/minecraft-1.12.2/.minecraft/options.txt'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--host', required=True)
parser.add_argument('--framebuffer', choices=('true', 'false'), help='Change only the framebuffer option')
parser.add_argument('--performance', action='store_true', help='Apply a conservative vanilla performance preset')
args = parser.parse_args()
if args.performance and args.framebuffer:
    parser.error('Choose either --performance or --framebuffer')
with ftplib.FTP() as ftp:
    ftp.connect(args.host, 2121, timeout=15)
    ftp.login()
    before = bytearray()
    def collect(chunk):
        if len(before) + len(chunk) > 64 * 1024:
            raise ValueError('Options file exceeds expected limit')
        before.extend(chunk)
    try:
        ftp.retrbinary('RETR ' + REMOTE, collect)
    except ftplib.error_perm as error:
        if not str(error).startswith('550'):
            raise
    out = ROOT / 'artifacts/console-test-graphics'
    out.mkdir(exist_ok=True)
    backup = out / ('options-before-performance-test.txt' if args.performance else
                    'options-before-framebuffer-test.txt' if args.framebuffer else 'options-before.txt')
    if not backup.exists():
        backup.write_bytes(before)
    changes = {'fboEnable': args.framebuffer} if args.framebuffer else {'fboEnable': 'false', 'useVbo': 'false', 'mipmapLevels': '0'}
    if args.performance:
        # Keep the framebuffer path that now renders correctly; use GPU vertex
        # buffers and reduce visible chunks while measuring the first world.
        changes = {'fboEnable': 'true', 'useVbo': 'true', 'renderDistance': '2',
                   'fancyGraphics': 'false', 'ao': '0', 'mipmapLevels': '0',
                   'particles': '2', 'renderClouds': 'false', 'entityShadows': 'false',
                   'enableVsync': 'false', 'maxFps': '60'}
    lines = [line for line in before.decode('utf-8').splitlines()
             if line.split(':', 1)[0] not in changes]
    lines += [key + ':' + value for key, value in changes.items()]
    data = ('\n'.join(lines) + '\n').encode()
    (out / 'options.txt').write_bytes(data)
    pending = REMOTE + '.prosperomc-upload'
    ftp.storbinary('STOR ' + pending, io.BytesIO(data))
    check = bytearray()
    ftp.retrbinary('RETR ' + pending, check.extend)
    if bytes(check) != data:
        raise ValueError('Options readback mismatch')
    ftp.rename(pending, REMOTE)
    print('VANILLA_GRAPHICS_OPTIONS_VERIFIED', hashlib.sha256(data).hexdigest())
