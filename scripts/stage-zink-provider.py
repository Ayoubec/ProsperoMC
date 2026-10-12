#!/usr/bin/env python3
"""Stage only the verified upstream PE64 WGL/Zink provider and its notices."""
import hashlib
import json
from pathlib import Path
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'https://github.com/mpereiraesaa/prospero-win/releases/tag/v0.2.0'
ARCHIVE_SHA = '7585efc624c2f8077c0d579a045ef808129a7b0bc525a9dd9c5c6db0c51626ca'
DLLS = {
    'x86_64-windows/libgallium_wgl.dll': 'eb677b5e00de7dc7c5c7db29562c727285d4ad20b7b2d74215eb39fab7a31779',
    'x86_64-windows/opengl32.dll': '09a0342b9a75056cc90f06ebc2221e9e1f2a676c17a9620b7cca604b327d2636',
}
DRIVER = 'win/wine/lib/wine/x86_64-unix/libvulkan.prx'
DRIVER_SHA = '3e1c58d9cee69609868b197fab0a77be534357cbaf641f0c0485a893300a43d4'
OLD_DRIVER_SHA = 'd2f0a02bc8c2a6d3643c66e9c2929cf520d30a367834d5e8bf44d1ec11a97982'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def provider_names(title):
    report_path = title / 'MESA_ZINK_REPORT.json'
    if not report_path.is_file():
        return []
    report = json.loads(report_path.read_text())
    if report.get('archiveSha256') != ARCHIVE_SHA or report.get('driver') != 'zink':
        raise ValueError('Unverified Zink provider report')
    files = report.get('files', {})
    if files.get(DRIVER) != DRIVER_SHA:
        raise ValueError('Zink requires the matching display-takeover driver')
    for name, expected in DLLS.items():
        if files.get('win/mesa-zink/' + name) != expected:
            raise ValueError('Zink provider DLL pin mismatch')
    for name, expected in files.items():
        p = Path(name)
        if p.is_absolute() or '..' in p.parts or not (
            name == DRIVER or name in ('win/mesa-zink/' + n for n in DLLS)
            or name.startswith('ZINK_LICENSES/') or name == 'ZINK_SOURCES.txt'):
            raise ValueError('Invalid Zink package path')
        local = title / name
        if local.is_symlink() or digest(local.read_bytes()) != expected:
            raise ValueError('Zink provider content mismatch: ' + name)
    return sorted(files) + ['MESA_ZINK_REPORT.json']


def stage():
    archive = ROOT / '.deps/archives/prospero-win-v0.2.0.zip'
    if digest(archive.read_bytes()) != ARCHIVE_SHA:
        raise ValueError('Upstream release archive hash mismatch')
    title = ROOT / 'dist/PPSA99888'
    prefix = 'PPSA99995/'
    selected = {}
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read(prefix + 'mesa-zink-manifest.json'))
        if manifest.get('driver') != 'zink' or manifest.get('mesa_commit') != 'e4607ef697fe3df8d1ebc329bf1917d041843306':
            raise ValueError('Unexpected upstream Mesa source')
        driver = z.read(prefix + DRIVER)
        if digest(driver) != DRIVER_SHA or b'never presented gives the display' not in driver:
            raise ValueError('Matching Vulkan driver or upstream swapchain fix missing')
        current = title / DRIVER
        if digest(current.read_bytes()) not in (OLD_DRIVER_SHA, DRIVER_SHA):
            raise ValueError('Unreviewed existing Vulkan driver; refusing to replace it')
        backup = ROOT / 'artifacts/zink-presentation-review/libvulkan-before-update.prx'
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_bytes(current.read_bytes())
        selected[DRIVER] = driver
        for name, expected in DLLS.items():
            record = manifest['files'][name]
            data = z.read(prefix + 'win/mesa-zink/' + name)
            pe = struct.unpack_from('<I', data, 60)[0]
            if digest(data) != expected or record['sha256'] != expected or data[pe:pe+4] != b'PE\0\0' or struct.unpack_from('<H', data, pe+4)[0] != 0x8664:
                raise ValueError('Invalid PE64 provider: ' + name)
            selected['win/mesa-zink/' + name] = data
        for name, expected in manifest['license_sha256'].items():
            if not name.startswith('LICENSES/') or '..' in Path(name).parts:
                raise ValueError('Unsafe upstream licence path')
            data = z.read(prefix + name)
            if digest(data) != expected:
                raise ValueError('Licence hash mismatch')
            selected['ZINK_' + name] = data
    selected['ZINK_SOURCES.txt'] = (
        'Mesa WGL/Zink PE64 provider from Prospero Win v0.2.0\n' + RELEASE + '\n'
        'Release SHA-256: ' + ARCHIVE_SHA + '\n'
        'Mesa source: https://github.com/mpereiraesaa/PS5_Mesa/tree/' + manifest['mesa_commit'] + '\n'
        'Compiler: llvm-mingw ' + manifest['llvm_mingw'] + '\n'
        'Compiler archive SHA-256: ' + manifest['llvm_mingw_archive_sha256'] + '\n'
        'Provider DLLs and the matching official RADV driver were staged; Wine modules are preserved.\n'
        'RADV source: https://github.com/mpereiraesaa/PS5_Mesa/tree/01d70579b8d410d6a482e36c6f184798ae4c83ad\n'
        'RADV link recipe: https://github.com/mpereiraesaa/PS5_Vulkan/tree/8aee3afb37bcfad06f0c7d263b901040f08ebbd0\n'
        'Swapchain fix: https://github.com/mpereiraesaa/PS5_Mesa/commit/f2ee3891be81f5f36fc1e64ada36e36033bae5e4\n'
        'A hidden context that never presented relinquishes the display to the game window.\n'
        'Console compatibility/performance validation is pending.\n').encode()
    for name, data in selected.items():
        target = title / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    report = {'release': RELEASE, 'archiveSha256': ARCHIVE_SHA, 'driver': 'zink',
              'mesaCommit': manifest['mesa_commit'], 'consoleValidated': False,
              'files': {name: digest(data) for name, data in selected.items()}}
    (title / 'MESA_ZINK_REPORT.json').write_text(json.dumps(report, indent=2) + '\n')
    for name in ('STAGE-REPORT.json', 'prosperomc/STAGE-REPORT.json'):
        path = title / name
        stage_report = json.loads(path.read_text())
        stage_report['wine']['vulkanSha256'] = DRIVER_SHA
        stage_report['wine']['vulkanFix'] = {
            'sourceCommit': '01d70579b8d410d6a482e36c6f184798ae4c83ad',
            'swapchainFixCommit': 'f2ee3891be81f5f36fc1e64ada36e36033bae5e4',
            'consoleVerified': False,
        }
        path.write_text(json.dumps(stage_report, indent=2) + '\n')
    provider_names(title)
    print('STAGED_VERIFIED_ZINK_AND_MATCHING_VULKAN: Wine preserved; console validation pending')


if __name__ == '__main__':
    stage()
