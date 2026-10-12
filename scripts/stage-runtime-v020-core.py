#!/usr/bin/env python3
"""Stage the audited v0.2.0 Wine core pair and its matching PE ntdlls."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA = '7585efc624c2f8077c0d579a045ef808129a7b0bc525a9dd9c5c6db0c51626ca'
SOURCE = '644e32e400c555e340d507383398c5d21b39b0b0'
MODULES = {'ntdll': 'abf33f754840af9076e14e39d3800f029647ca95ad13d6d162fb511b4f71d56b',
           'wineserver': '07a7eb0dbd9c7a0d6edcbc1e001325436f670ea639c3755fd540003d5a6167a2'}
LOCAL_MODULES = {'ntdll': '3a34f7e07ee6f3c3be845075bda2c6e765a05598b555b86721e230ab98af7192',
                 'wineserver': 'fd15c41cf92b05aace6095b5026c43f9737c076fabe788736c1df9d86e926add'}
LOCAL_PATCHES = {'WINE_PATCHES/cwd-volume-root.patch': '0de6118e027f55776811adf914df7073c35aadf1ca3d7d693432c9a3a87103b2',
                 'WINE_PATCHES/cwd-fd-diagnostic.patch': 'c3bb4e1a87f638f5b8ddda011a8acfe7373026f79ef098c250b815aa41a45e47'}
TITLE_FILES = ['win/wine/lib/wine/x86_64-unix/' + name + '.prx' for name in MODULES]
TITLE_FILES += ['win/wine/lib/wine/' + arch + '/ntdll.dll' for arch in ('x86_64-windows', 'i386-windows')]
PE_PREFIX = {'x86_64-windows': 'system32', 'i386-windows': 'syswow64'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def core_names(title, data_root=None):
    report = title / 'WINE_CORE_V020_REPORT.json'
    if not report.is_file():
        return [], []
    data = json.loads(report.read_text())
    if data.get('archiveSha256') != ARCHIVE_SHA or data.get('sourceCommit') != SOURCE:
        raise ValueError('Unverified Wine core report')
    expected = set(TITLE_FILES + ['WINE_CORE_V020_SOURCES.txt', 'WINE_CORE_V020_LICENSE.txt'])
    modules = MODULES
    if data.get('localRootFix'):
        if data.get('localPatches') != LOCAL_PATCHES:
            raise ValueError('Unverified local Wine core source patches')
        modules = LOCAL_MODULES
        expected.update(LOCAL_PATCHES)
    if set(data['titleFiles']) != expected:
        raise ValueError('Wine core files outside the selected core update')
    for name, sha in data['titleFiles'].items():
        if digest(title / name) != sha:
            raise ValueError('Wine core hash mismatch: ' + name)
    for module, sha in modules.items():
        if data['titleFiles']['win/wine/lib/wine/x86_64-unix/' + module + '.prx'] != sha:
            raise ValueError('Wine core module pin mismatch')
    allowed = {'prefixes/minecraft/drive_c/windows/' + folder + '/ntdll.dll' for folder in PE_PREFIX.values()}
    if set(data['dataFiles']) != allowed:
        raise ValueError('Wine core data files outside selected PE companions')
    for name, sha in data['dataFiles'].items():
        if digest((data_root if data_root is not None else title / 'prosperomc') / name) != sha:
            raise ValueError('Wine core PE companion mismatch')
    return sorted(expected) + ['WINE_CORE_V020_REPORT.json'], sorted(allowed)


def stage():
    archive = ROOT / '.deps/archives/prospero-win-v0.2.0.zip'
    if digest(archive) != ARCHIVE_SHA:
        raise ValueError('Release archive hash mismatch')
    review = json.loads((ROOT / 'artifacts/runtime-v020-review/abi-review.json').read_text())
    if review['archiveSha256'] != ARCHIVE_SHA:
        raise ValueError('ABI review does not match release')
    for name, sha in MODULES.items():
        module = review['modules'][name + '.prx']
        if module['sha256'] != sha or module['missingExports'] or 'UNKNOWN' in module['newImportNames'].values():
            raise ValueError('Incomplete ABI review')
    title = ROOT / 'dist/PPSA99888'
    records = {'archiveSha256': ARCHIVE_SHA, 'sourceCommit': SOURCE, 'consoleVerified': False,
               'titleFiles': {}, 'dataFiles': {}, 'preservedNativeOpenGL': digest(title / 'win/wine/lib/wine/x86_64-unix/win32u.prx')}
    backup = ROOT / 'artifacts/runtime-v020-review/before-update'
    def save(base, name, content, category):
        target = base / name
        previous = backup / category / name
        if target.exists() and not previous.exists():
            previous.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, previous)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        records[category][name] = hashlib.sha256(content).hexdigest()
    with zipfile.ZipFile(archive) as z:
        for name in TITLE_FILES:
            save(title, name, z.read('PPSA99995/' + name), 'titleFiles')
        for arch, folder in PE_PREFIX.items():
            name = 'prefixes/minecraft/drive_c/windows/' + folder + '/ntdll.dll'
            save(title / 'prosperomc', name, z.read('PPSA99995/win/wine/lib/wine/' + arch + '/ntdll.dll'), 'dataFiles')
        notice = z.read('PPSA99995/SOURCES.txt') + (
            '\nProsperoMC updates ntdll.prx, wineserver.prx and matching PE ntdll.dll only.\n'
            'Native OpenGL win32u, other Wine modules and all user data are retained.\n'
            'Reproduce: scripts/review-runtime-v020.py then scripts/stage-runtime-v020-core.py.\n'
            'The original GPL/LGPL Wine patch sources are at the pinned public source revision above.\n'
            'Host ABI checks passed; console execution is pending.\n').encode()
        save(title, 'WINE_CORE_V020_SOURCES.txt', notice, 'titleFiles')
        save(title, 'WINE_CORE_V020_LICENSE.txt', (ROOT / 'vendor/prospero-win/LICENSE').read_bytes(), 'titleFiles')
    (title / 'WINE_CORE_V020_REPORT.json').write_text(json.dumps(records, indent=2) + '\n')
    for path in (title / 'STAGE-REPORT.json', title / 'prosperomc/STAGE-REPORT.json'):
        report = json.loads(path.read_text())
        report['wine']['ntdllSha256'] = MODULES['ntdll']
        report['wine']['runtimeCore'] = {'version': 'v0.2.0', 'sourceCommit': SOURCE, 'archiveSha256': ARCHIVE_SHA,
                                      'consoleVerified': False, 'nativeOpenGLPreserved': True}
        path.write_text(json.dumps(report, indent=2) + '\n')
    core_names(title)
    print('STAGED_AUDITED_V020_CORE: native OpenGL preserved; console validation pending')


if __name__ == '__main__':
    stage()
