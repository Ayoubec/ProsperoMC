#!/usr/bin/env python3
"""Stage the verified ntdll rebuild without changing other Wine modules."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / 'artifacts/wine-fpfix'
TITLE = ROOT / 'dist/PPSA99888'
PATCH = '0501-ntdll-ps5-signal-fp-state-at-its-measured-offset.patch'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

report = json.loads((BUILD / 'report.json').read_text())
entry = report['prx']['modules']['ntdll']
assert report['wine_commit'] == '490f6d5dcbb2a5047345b8af88d114bbcaad69a8'
assert report['prx']['status'] == '0' and entry['built'], 'ntdll build failed'
for key in ('unresolved', 'errors', 'title_unbound', 'webkit_unbound', 'raw_syscalls'):
    assert not entry.get(key), (key, entry.get(key))
assert set(entry['needed']) == {'libSceLibcInternal.sprx', 'libkernel.sprx'}
# System-library data imports are supported; imports between app PRXs are not.
assert set(entry.get('data_imports', [])) <= {'__isthreaded', '__stderrp', '__stdoutp', 'environ'}
assert digest(BUILD / 'ntdll.prx') == entry['sha256'], 'module differs from build report'
with zipfile.ZipFile(ROOT / '.deps/archives/prospero-win-runtime-8086243.zip') as archive:
    expected = sorted(Path(name).name for name in archive.namelist()
                      if '/wine/patches/' in name and name.endswith('.patch'))
assert report['patches'] == sorted(expected + [PATCH]), 'unexpected Wine patch set'
assert report['sources']['prx_foundation'] == '30597512539e7edfde079cbcaf4a626bc0a948c5'

stage_paths = [TITLE / 'STAGE-REPORT.json', TITLE / 'prosperomc/STAGE-REPORT.json']
stages = [json.loads(path.read_text()) for path in stage_paths]
assert stages[0] == stages[1], 'stage reports disagree'
ntdll = TITLE / 'win/wine/lib/wine/x86_64-unix/ntdll.prx'
win32u = TITLE / 'win/wine/lib/wine/x86_64-unix/win32u.prx'
assert digest(win32u) == '7298fc50097fbe06980a6e2c8482675dcff7fc3c679456bad34945042d2a674d'
backup = BUILD / 'ntdll-v0.1.1-original.prx'
if not backup.exists():
    assert digest(ntdll) == '5d313d0b6afb9408fe0e3ae951e46e40e37aeca07e55a10c5f6f3502a88d33b1'
    shutil.copy2(ntdll, backup)
shutil.copy2(BUILD / 'ntdll.prx', ntdll)
patch = ROOT / 'vendor/prospero-win/wine/patches' / PATCH
patch_dir = TITLE / 'WINE_PATCHES'
patch_dir.mkdir(exist_ok=True)
shutil.copy2(patch, patch_dir / PATCH)
notice = TITLE / 'WINE_SOURCES.txt'
text = notice.read_text()
marker = '\nProsperoMC ntdll floating-point repair:\n'
text = text.split(marker)[0] + marker + (
    '  ntdll.prx alone rebuilt from the above Wine revision and original 72 release patches,\n'
    '  plus upstream 0501 from prospero-win commit b510eb3db8709bb251d3da3c56850e96e057f489.\n'
    '  Patch source included in WINE_PATCHES/; all other Wine modules remain from v0.1.1.\n'
    '  Reproduce with scripts/prepare-wine-fpfix.py then scripts/build-wine-fpfix.sh.\n'
    '  PS5 module tool commit 30597512539e7edfde079cbcaf4a626bc0a948c5.\n')
notice.write_bytes(text.encode())
for path, stage in zip(stage_paths, stages):
    stage['wine']['ntdllSha256'] = entry['sha256']
    stage['wine']['ntdllFix'] = {'patch': PATCH, 'patchSha256': digest(patch),
                               'sourceCommit': 'b510eb3db8709bb251d3da3c56850e96e057f489'}
    path.write_text(json.dumps(stage, indent=2) + '\n')
spec = importlib.util.spec_from_file_location('deploy', ROOT / 'scripts/deploy-ps5.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)
deploy.validate_package(TITLE, TITLE / 'prosperomc')
print('STAGED_NTDLL_ONLY', entry['sha256'])
