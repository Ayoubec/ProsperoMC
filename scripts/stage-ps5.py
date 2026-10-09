#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Stage the compiled Minecraft-only app and local console data; never deploy it.

Java and Minecraft inputs are private, opt-in build artifacts. The result is
structurally complete only after every mandatory component has been checked;
console validation is a separate, explicitly reported result.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import struct
import sys
import zipfile

PROJECT = Path(__file__).resolve().parent.parent
TITLE_ID = 'PPSA99888'
WINE_COMMIT = '490f6d5dcbb2a5047345b8af88d114bbcaad69a8'
FORBIDDEN = {'accounts.json', 'launcher_accounts.json', 'launcher_profiles.json',
             'usercache.json', 'authentication.json', 'auth.json', 'auth.properties',
             'msa-account.json', 'msa.json', 'request.properties', 'response.properties'}

def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(1 << 20), b''):
            value.update(chunk)
    return value.hexdigest()

def require(path: Path) -> Path:
    if not path.is_file() or not path.stat().st_size:
        raise ValueError(f'Missing or empty input: {path}')
    return path

def machine(path: Path) -> int:
    with require(path).open('rb') as file:
        data = file.read(64)
        if data[:2] != b'MZ' or len(data) != 64:
            raise ValueError(f'Not a Windows executable: {path}')
        file.seek(struct.unpack_from('<I', data, 60)[0])
        if file.read(4) != b'PE\0\0':
            raise ValueError(f'Invalid PE header: {path}')
        return struct.unpack('<H', file.read(2))[0]

def copy_tree(source: Path, target: Path, *, filter_accounts: bool = False) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for entry in sorted(source.iterdir()):
        if entry.name.lower() in FORBIDDEN or entry.name in {'.git', '.wineserver', '.pw-symlinks'}:
            if not filter_accounts and entry.name.lower() in FORBIDDEN:
                raise ValueError(f'Credential/state file is forbidden in package: {entry}')
            continue
        if entry.is_symlink():
            resolved = entry.resolve()
            if entry.name.endswith(':') or resolved.is_dir():
                # PS5 virtual drive mappings are generated below; never copy host links.
                (target / entry.name).mkdir(exist_ok=True) if ':' not in entry.name else None
                continue
            if not resolved.is_relative_to(source.resolve()):
                continue
        if entry.is_dir():
            copy_tree(entry, target / entry.name, filter_accounts=filter_accounts)
        elif entry.is_file():
            shutil.copy2(entry, target / entry.name)

def validate_wine(wine: Path) -> dict:
    unix = wine / 'win/wine/lib/wine/x86_64-unix'
    pe = wine / 'win/wine/lib/wine/x86_64-windows'
    for name in ('ntdll.prx', 'win32u.prx', 'wineserver.prx', 'wineps5.prx', 'libfreetype.prx'):
        require(unix / name)
    for name in ('ntdll.dll', 'kernel32.dll', 'kernelbase.dll', 'opengl32.dll', 'win32u.dll',
                 'ws2_32.dll', 'winhttp.dll', 'crypt32.dll', 'secur32.dll', 'winmm.dll', 'mmdevapi.dll'):
        if machine(pe / name) != 0x8664:
            raise ValueError(f'Expected x64 Wine PE module: {pe / name}')
    require(wine / 'win/wine/share/wine/nls/locale.nls')
    provenance = require(wine / 'SOURCES.txt').read_text(encoding='utf-8')
    if WINE_COMMIT not in provenance or 'OpenGL (in win32u.prx)' not in provenance:
        raise ValueError('Wine release must record the pinned Wine and embedded PS5 OpenGL build')
    # The release records statically linked OpenGL. Require actual EGL exports
    # as well as the source notice so a GDI-only replacement cannot pass.
    graphics = (unix / 'win32u.prx').read_bytes()
    if b'eglGetDisplay' not in graphics or b'eglCreateContext' not in graphics:
        raise ValueError('win32u.prx lacks embedded EGL/OpenGL symbols')
    return {'sourceCommit': WINE_COMMIT, 'ntdllSha256': digest(unix / 'ntdll.prx'),
            'win32uSha256': digest(unix / 'win32u.prx'), 'opengl': 'embedded in win32u.prx'}

def stage_prefix(source: Path, target: Path, wine: Path) -> dict:
    for name in ('system.reg', 'user.reg', 'userdef.reg'):
        require(source / name)
    if not (source / 'drive_c/windows/system32').is_dir():
        raise ValueError('Wine prefix must be initialized offline; PS5 cannot run wineboot')
    target.mkdir(parents=True, exist_ok=True)
    # A fresh prefix contributes registry/configuration only. All PE modules
    # come from the PS5 Wine release, avoiding stale host DLLs and unrelated apps.
    for name in ('system.reg', 'user.reg', 'userdef.reg', '.update-timestamp', 'prosperomc-prefix.json'):
        if (source / name).is_file():
            shutil.copy2(source / name, target / name)
    for folder in ('Fonts', 'resources/themes'):
        if (source / 'drive_c/windows' / folder).is_dir():
            copy_tree(source / 'drive_c/windows' / folder, target / 'drive_c/windows' / folder)
    winsxs = source / 'drive_c/windows/winsxs'
    pe64 = wine / 'win/wine/lib/wine/x86_64-windows'
    pe32 = wine / 'win/wine/lib/wine/i386-windows'
    if winsxs.is_dir():
        for entry in winsxs.rglob('*'):
            if not entry.is_file() or entry.is_symlink():
                continue
            dest = target / 'drive_c/windows/winsxs' / entry.relative_to(winsxs)
            if entry.suffix.lower() in ('.manifest', '.xml'):
                dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(entry, dest)
            elif entry.suffix.lower() == '.dll':
                architecture = pe64 if entry.relative_to(winsxs).parts[0].startswith('amd64_') else pe32
                replacement = architecture / entry.name
                if replacement.is_file():
                    dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(replacement, dest)
    modules = wine / 'win/wine/lib/wine'
    for architecture, folder in (('x86_64-windows', 'system32'), ('i386-windows', 'syswow64')):
        if (modules / architecture).is_dir():
            copy_tree(modules / architecture, target / 'drive_c/windows' / folder)
    for directory in ('AppData/Local/Temp', 'AppData/LocalLow', 'AppData/Roaming', 'Desktop', 'Documents', 'Saved Games'):
        (target / 'drive_c/users/prospero' / directory).mkdir(parents=True, exist_ok=True)
    dosdevices = target / 'dosdevices'
    dosdevices.mkdir(parents=True, exist_ok=True)
    # The PS5 virtual-link parser includes CR in targets; use exact Unix bytes
    # even when packaging on Windows.
    (dosdevices / '.pw-symlinks').write_bytes(b'c:\t../drive_c\nz:\t/\n')
    registry = target / 'system.reg'
    registry_bytes = registry.read_bytes().replace(b'@="wow64cpu.dll"', b'@="wowprospero.dll"')
    # The packaged resolver supports localhost, not a host PC's copied name.
    registry_bytes = re.sub(rb'(?m)^"(ComputerName|Hostname|NV Hostname)"="[^"\r\n]*"',
                            rb'"\1"="localhost"', registry_bytes)
    registry.write_bytes(registry_bytes)
    user = target / 'user.reg'
    data = user.read_text(encoding='utf-8')
    # A host audio provider cannot be loaded on PS5.
    if '[Software\\\\Wine\\\\Drivers]' in data:
        start = data.index('[Software\\\\Wine\\\\Drivers]')
        end = data.find('\n[', start + 1)
        end = len(data) if end < 0 else end
        section = data[start:end]
        section = '\n'.join(line for line in section.splitlines() if not line.startswith('"Audio"='))
        data = data[:start] + section + '\n"Audio"="ps5"\n' + data[end:]
    else:
        data += '\n[Software\\\\Wine\\\\Drivers]\n"Audio"="ps5"\n'
    user.write_text(data, encoding='utf-8')
    metadata = source / 'prosperomc-prefix.json'
    info = json.loads(metadata.read_text(encoding='utf-8')) if metadata.is_file() else {}
    source_commit = info.get('wineCommit')
    return {'hostWine': info.get('wineVersion', 'unknown'), 'hostWineCommit': source_commit,
            'matchingSource': source_commit == WINE_COMMIT,
            'peModules': 'overlaid from pinned PS5 Wine release',
            'consoleValidated': False}

def stage(args: argparse.Namespace) -> dict:
    output, data = args.out.resolve(), args.data_out.resolve()
    if not output.is_relative_to(PROJECT) or not data.is_relative_to(PROJECT):
        raise ValueError('Stage output directories must stay inside this workspace')
    if output == PROJECT or data == PROJECT or output == data:
        raise ValueError('Unsafe stage directory')
    # A failed restage cannot leave an old report approving modified bytes.
    for report in (output / 'STAGE-REPORT.json', data / 'STAGE-REPORT.json'):
        if report.is_file():
            report.unlink()
    require(output / 'eboot.bin')
    require(output / 'sce_module/libc.prx')
    require(output / 'sce_sys/icon0.png')
    identity = json.loads(require(output / 'sce_sys/param.json').read_text(encoding='utf-8-sig'))
    if identity.get('titleId') != TITLE_ID:
        raise ValueError(f'Native title identity must be {TITLE_ID}')
    wine_info = validate_wine(args.wine)
    require(args.java / 'bin/java.exe')
    if machine(args.java / 'bin/java.exe') != 0x8664 or machine(args.java / 'bin/server/jvm.dll') != 0x8664:
        raise ValueError('Windows x64 Java 8 runtime required')
    release = require(args.java / 'release').read_text(encoding='utf-8')
    if 'JAVA_VERSION="1.8.' not in release:
        raise ValueError('Headless launcher bootstrap requires Java 8')
    with zipfile.ZipFile(require(args.launcher)) as jar:
        if 'org/prosperomc/Main.class' not in jar.namelist():
            raise ValueError('JAR does not contain the ProsperoMC launcher')
    copy_tree(args.wine / 'win', output / 'win')
    for name in ('LICENSE', 'THIRD_PARTY.md', 'SOURCES.txt'):
        shutil.copy2(require(args.wine / name), output / ('WINE_' + name))
    copy_tree(args.wine / 'LICENSES', output / 'LICENSES/Wine-runtime')
    shutil.copy2(require(PROJECT / 'LICENSE'), output / 'LICENSE')
    if (PROJECT / 'THIRD_PARTY_NOTICES.md').is_file():
        shutil.copy2(PROJECT / 'THIRD_PARTY_NOTICES.md', output / 'THIRD_PARTY_NOTICES.md')
    font_license = PROJECT / 'app/native/Montserrat-OFL.txt'
    if font_license.is_file():
        (output / 'LICENSES').mkdir(parents=True, exist_ok=True)
        shutil.copy2(font_license, output / 'LICENSES/Montserrat-OFL.txt')
    vendor = PROJECT / 'vendor/prospero-win'
    for name in ('LICENSE', 'NOTICE.md', 'LICENSING.md', 'PROSPEROMC-ADAPTATIONS.md'):
        shutil.copy2(require(vendor / name), output / ('PROSPERO-WIN-' + name))
    (output / 'APP-SOURCES.txt').write_text(
        'ProsperoMC: source in the accompanying repository.\n'
        'Wine native title base: https://github.com/mpereiraesaa/prospero-win commit b510eb3db8709bb251d3da3c56850e96e057f489\n'
        'Native foundation: https://github.com/mpereiraesaa/ps5-native-app-boilerplate commit 9c0b994a048521af6fb84c73ded364504fe250e9\n'
        'Embedded font: Montserrat, SIL Open Font License 1.1 (LICENSES/Montserrat-OFL.txt).\n'
        'Wine/runtime module exact sources: WINE_SOURCES.txt.\n', encoding='utf-8')
    (output / 'launcher').mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.launcher, output / 'launcher/prosperomc-launcher.jar')
    copy_tree(args.java, data / 'runtimes/java8')
    (data / 'launcher').mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.launcher, data / 'launcher/prosperomc-launcher.jar')
    prefix = stage_prefix(args.prefix, data / 'prefixes/minecraft', args.wine)
    (data / 'profiles').mkdir(parents=True, exist_ok=True)
    (data / 'imports').mkdir(parents=True, exist_ok=True)
    if args.game_root:
        # Only installed Minecraft content and public download metadata survive.
        # Profiles/plans contain host paths; auth/account stores never enter a title.
        for name in ('libraries', 'assets', 'versions', 'instances', 'cache'):
            source = args.game_root / name
            if source.is_dir() and source.resolve() != (data / name).resolve():
                copy_tree(source, data / name, filter_accounts=True)
        snapshot = args.game_root / 'launcher-view.properties'
        if snapshot.is_file() and snapshot.resolve() != (data / snapshot.name).resolve():
            lines = snapshot.read_text(encoding='utf-8').splitlines()
            allowed = ('instance.', 'version.', 'mod.', 'settings.memoryMb', 'settings.accountMode')
            clean = [line for line in lines if line.split('=', 1)[0].startswith(allowed)]
            clean += ['status=Ready', 'detail=Select your Minecraft instance or choose a version.']
            (data / snapshot.name).write_text('\n'.join(clean) + '\n', encoding='utf-8')
    # The native settings screen can report the packaged bootstrap immediately;
    # additional runtimes are detected from the actual console filesystem.
    snapshot = data / 'launcher-view.properties'
    lines = snapshot.read_text(encoding='utf-8').splitlines() if snapshot.is_file() else ['status=Ready']
    lines = [line for line in lines if not line.startswith('java.') and not line.startswith('settings.java')]
    java_version = next(line.split('=', 1)[1].strip('"') for line in release.splitlines() if line.startswith('JAVA_VERSION='))
    lines += ['java.count=1', 'java.0.major=8', 'java.0.version=' + java_version,
              'java.0.path=Z:\\data\\ProsperoMC\\runtimes\\java8\\bin\\java.exe',
              'java.0.valid=true', 'java.0.detail=Bundled Windows x64 Java 8']
    snapshot.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    if args.instance:
        require(args.instance / 'instance.cfg')
        target = data / 'instances' / args.instance.name
        copy_tree(args.instance, target, filter_accounts=True)
    if bool(args.helper) != bool(args.helper_manifest):
        raise ValueError('--helper and --helper-manifest must be supplied together')
    helper_info = None
    if args.helper:
        helper_info = json.loads(require(args.helper_manifest).read_text(encoding='utf-8'))
        protocol = PROJECT / 'vendor/prospero-win/native/lapy_elevation_protocol.h'
        if helper_info.get('target_title') != TITLE_ID or helper_info.get('elf_sha256') != digest(require(args.helper)) or helper_info.get('protocol_sha256') != digest(protocol):
            raise ValueError('Lapy helper manifest title, ELF or protocol mismatch')
        if helper_info.get('mode') != 'elf-helper' or 'root_layout_probe_retry' not in helper_info.get('features', []):
            raise ValueError('Lapy helper lacks required protocol safety features')
        if args.helper.read_bytes()[:4] != b'\x7fELF':
            raise ValueError('Lapy helper is not an ELF')
        shutil.copy2(args.helper, output / 'lapy.elf')
        shutil.copy2(args.helper_manifest, output / 'lapy-manifest.json')
    elif (output / 'lapy.elf').exists():
        raise ValueError('Unvalidated pre-existing helper in output; provide its matching manifest')
    report = {'schema': 'prosperomc-stage/1', 'titleId': TITLE_ID,
              'structurallyComplete': True, 'consoleValidated': False,
              'readyToPlay': False, 'wine': wine_info, 'prefix': prefix,
              'javaSha256': digest(args.java / 'bin/java.exe'), 'jarSha256': digest(args.launcher),
              'ebootSha256': digest(output / 'eboot.bin'),
              'wineDriveTableSha256': digest(data / 'prefixes/minecraft/dosdevices/.pw-symlinks'),
              'dataRoot': '/data/ProsperoMC',
              'sandboxFallback': None, 'helper': helper_info,
              'limitations': ['Requires homebrew-enabled PS5 and actual Java/LWJGL console validation']}
    if not prefix['matchingSource']:
        report['limitations'].append('Offline prefix host Wine differs from runtime Wine; PE modules were overlaid but registry compatibility remains unvalidated')
    if not helper_info:
        report['limitations'].append('/data must already be granted; package uses sandbox fallback otherwise')
    for directory in (output, data):
        for item in directory.rglob('*'):
            if item.is_file() and item.name.lower() in FORBIDDEN:
                raise ValueError(f'Forbidden credential/state file: {item}')
            if item.is_file() and item.suffix in {'.prx', '.bin', '.elf'}:
                item.chmod(0o755)
    (output / 'STAGE-REPORT.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (data / 'STAGE-REPORT.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('wine', 'java', 'launcher', 'prefix'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--out', type=Path, default=PROJECT / 'dist/PPSA99888')
    parser.add_argument('--data-out', type=Path, default=PROJECT / 'dist/PPSA99888/prosperomc')
    parser.add_argument('--instance', type=Path)
    parser.add_argument('--game-root', type=Path, help='Verified local backend data root; only Minecraft content and public cache are copied')
    parser.add_argument('--helper', type=Path)
    parser.add_argument('--helper-manifest', type=Path)
    try:
        print(json.dumps(stage(parser.parse_args()), indent=2))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f'Staging refused: {error}', file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
