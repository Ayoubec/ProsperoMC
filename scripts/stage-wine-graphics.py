"""Stage verified win32u graphics repair; preserve the working Java runtime."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import argparse

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build', type=Path, default=root / 'artifacts/wine-graphics')
parser.add_argument('--sdk', type=Path, default=root / '.deps/graphics-sdk-1.0.1')
args = parser.parse_args()
build = args.build.resolve()
sdk = args.sdk.resolve()
assert build.is_relative_to(root / 'artifacts') and sdk.is_relative_to(root / '.deps')
title = root / 'dist/PPSA99888'
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
report = json.loads((build / 'report.json').read_text())
entry = report['prx']['modules']['win32u']
assert report['wine_commit'] == '490f6d5dcbb2a5047345b8af88d114bbcaad69a8'
assert report['prx']['status'] == '0' and entry['built']
for key in ('unresolved', 'errors', 'title_unbound', 'webkit_unbound', 'raw_syscalls'):
    assert not entry.get(key), (key, entry.get(key))
assert set(entry.get('data_imports', [])) <= {'__isthreaded', '__stderrp', '__stdinp', '__stdoutp', 'environ'}
assert digest(build / 'win32u.prx') == entry['sha256']
assert digest(title / 'win/wine/lib/wine/x86_64-unix/ntdll.prx') == '1c86a5eab801b5a2246f17543b5b7a938d3825b64e618fa9f58cb2f129906bd8'
provenance = json.loads((sdk / 'provenance.json').read_text())
assert digest(sdk / 'sdk/manifest.sha256') == provenance['sdk_manifest_sha256']
assert report['sources']['ps5_opengl_sdk'] == provenance['sdk_manifest_sha256']
assert 'PASS:' in (root / 'artifacts/graphics-source/capabilities-check.log').read_text()
local_patch = provenance.get('local_patch')
if local_patch:
    patch_source = root / 'artifacts/graphics-batching' / local_patch['file']
    assert patch_source.parent == root / 'artifacts/graphics-batching'
    assert digest(patch_source) == local_patch['sha256']
    assert 'PASS:' in (root / 'artifacts/graphics-batching/policy-check.log').read_text()
    patch_target = title / 'WINE_PATCHES' / local_patch['file']
    patch_target.parent.mkdir(exist_ok=True)
    shutil.copy2(patch_source,patch_target)
module = title / 'win/wine/lib/wine/x86_64-unix/win32u.prx'
backup = build / 'win32u-before-update.prx'
if not backup.exists():
    assert digest(module) in ('7298fc50097fbe06980a6e2c8482675dcff7fc3c679456bad34945042d2a674d',
                              'f606e54c51c71716756a916e90e10a7e87c319596e1a02f1acc6d08a941df207',
                              'b7a7f01628afdb9873bc57fe6188a27813bad6ed4241b1f18fe02b94ab838149')
    shutil.copy2(module, backup)
shutil.copy2(build / 'win32u.prx', module)
notice = title / 'WINE_SOURCES.txt'
wheel = root / 'vendor/prospero-win/wine/patches/0671-win32u-ps5-mouse-wheel.patch'
wheel_built = wheel.name in report['patches']
if wheel_built:
    shutil.copy2(wheel,title / 'WINE_PATCHES' / wheel.name)
additional_patches = {}
for name in ('0672-win32u-ps5-fixed-game-window.patch', '0910-win32u-ps5-worker-desktop-cache.patch'):
    assert name in report['patches'], name
    source = root / 'vendor/prospero-win/wine/patches' / name
    shutil.copy2(source, title / 'WINE_PATCHES' / name)
    additional_patches[name] = digest(source)
text = notice.read_text().replace('all other Wine modules remain from v0.1.1.', 'other Wine modules remain from v0.1.1 except the graphics repair below.')
marker = '\nProsperoMC BGRA texture graphics repair:\n'
text = text.split(marker)[0] + marker + (
    '  win32u.prx rebuilt from the above Wine revision with ' + str(len(report['patches'])) + ' patches.\n'
    '  OpenGL SDK ' + provenance['version'] + ': https://github.com/blackbearreloaded/ps5-opengl\n'
    '  Source commit ' + provenance['runtime_source_commit'] + '\n'
    '  Baseline official source snapshots/SDK verified against the published artifact and manifest.\n'
    '  SDK manifest SHA-256 ' + provenance['sdk_manifest_sha256'] + '\n'
    '  Includes upstream BGRA sampler-capability rejection; Mesa converts uploads to RGBA.\n'
    '  Compiled capability check retains BGRA rendering and RGBA sampling/rendering.\n' +
    ('  CI 738f94c additionally includes upstream legacy varyings, lowered client draw and HUD fixes.\n'
     if provenance['runtime_source_commit'].startswith('738f94c') else '') +
    ('  Local mouse-wheel patch WINE_PATCHES/' + wheel.name + '; SHA-256 ' + digest(wheel) + '\n' if wheel_built else '') +
    ('  Local modification: ' + local_patch['description'] + '.\n'
     '  Source patch WINE_PATCHES/' + local_patch['file'] + '; SHA-256 ' + local_patch['sha256'] + '\n'
     '  Reproduce modified driver with scripts/prepare-graphics-batching.py then scripts/build-graphics-batching.sh.\n'
     if local_patch else '') +
    ''.join('  Additional Wine patch WINE_PATCHES/'+name+'; SHA-256 '+sha+'\n' for name,sha in additional_patches.items()) +
    '  Upstream 0910 from prospero-win 807eed638c268b94f313e6371e2c760fe1cb2b5b.\n'
    '  Reproduce with scripts/prepare-wine-graphics.py then scripts/build-wine-graphics.sh.\n'
    '  ntdll and the launcher executable are unchanged by this graphics update.\n')
notice.write_bytes(text.encode())
for path in (title / 'STAGE-REPORT.json', title / 'prosperomc/STAGE-REPORT.json'):
    stage = json.loads(path.read_text())
    stage['wine']['win32uSha256'] = entry['sha256']
    stage['wine'].pop('graphicsRollback', None)
    stage['wine']['graphicsFix'] = {'sdkVersion': provenance['version'], 'sourceCommit': provenance['runtime_source_commit'],
        'sdkManifestSha256': provenance['sdk_manifest_sha256'], 'consoleVerified': False}
    if 'draw_profile' in provenance:
        stage['wine']['graphicsFix']['drawProfile'] = provenance['draw_profile']
        stage['wine']['graphicsFix']['batchTimings'] = provenance.get('batch_timings',False)
        stage['wine']['graphicsFix']['runtimeConfigSha256'] = provenance['runtime_config_sha256']
        stage['wine']['graphicsFix']['asyncNativePrepare'] = provenance.get('async_native_prepare',False)
        stage['wine']['graphicsFix']['nativePrepareWorkers'] = provenance.get('native_prepare_workers',0)
    if local_patch:
        stage['wine']['graphicsFix']['localPatch'] = local_patch
    if wheel_built:
        stage['wine']['graphicsFix']['wheelPatchSha256'] = digest(wheel)
    stage['wine']['graphicsFix']['additionalPatches'] = additional_patches
    path.write_text(json.dumps(stage, indent=2) + '\n')
spec = importlib.util.spec_from_file_location('deploy', root / 'scripts/deploy-ps5.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)
deploy.validate_package(title, title / 'prosperomc')
print('STAGED_WIN32U_ONLY', entry['sha256'])
