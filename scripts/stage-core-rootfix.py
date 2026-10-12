"""Stage only the ABI-reviewed core root-query fix and its exact source patches."""
from pathlib import Path
import hashlib
from importlib.machinery import SourceFileLoader
import json
import shutil

root=Path(__file__).resolve().parents[1]
out=root/'artifacts/wine-core-rootfix';title=root/'dist/PPSA99888'
core=SourceFileLoader('core_rootfix_stage',str(root/'scripts/stage-runtime-v020-core.py')).load_module()
core.core_names(title)
review=json.loads((out/'abi-review.json').read_text())
source=json.loads((out/'source-provenance.json').read_text())
report=json.loads((title/'WINE_CORE_V020_REPORT.json').read_text())
assert source['sourceCommit']==core.SOURCE==review['sourceCommit']
assert source['cwdSha256']==hashlib.sha256((root/'vendor/prospero-win/wine/ps5/pw_wine_cwd.c').read_bytes()).hexdigest()
report['localPatches']={}
for file,expected in ((out/'cwd-volume-root.patch',source['patchSha256']),
                      (root/'artifacts/wine-fd-review/cwd-fd-diagnostic.patch',source['fdDiagnosticPatchSha256'])):
    assert hashlib.sha256(file.read_bytes()).hexdigest()==expected
    target=title/'WINE_PATCHES'/file.name
    shutil.copy2(file,target)
    name=target.relative_to(title).as_posix()
    report['titleFiles'][name]=expected;report['localPatches'][name]=expected
for module,sha in core.LOCAL_MODULES.items():
    verified=review['modules'][module]
    assert verified['sha256']==sha and not verified['missingExports'] and not verified['addedImports']
    name='win/wine/lib/wine/x86_64-unix/'+module+'.prx'
    target=title/name
    backup=out/(module+'-before-rootfix.prx')
    if not backup.exists():shutil.copy2(target,backup)
    assert hashlib.sha256((out/(module+'.prx')).read_bytes()).hexdigest()==sha
    shutil.copy2(out/(module+'.prx'),target)
    report['titleFiles'][name]=sha
notice=title/'WINE_CORE_V020_SOURCES.txt'
text=notice.read_text().split('\nProsperoMC local virtual-drive fix:\n')[0]
text+='\nProsperoMC local virtual-drive fix:\n  Follow directory links ending in a slash; retain ENOTDIR for file links.\n  Includes one-shot EMFILE/ENFILE origin and descriptor telemetry.\n  Source patches: WINE_PATCHES/cwd-volume-root.patch and cwd-fd-diagnostic.patch.\n  Reproduce: scripts/check-drive-root-links.py, prepare-wine-core-rootfix.py, build-wine-core-rootfix.sh, review-core-rootfix.py and stage-core-rootfix.py.\n  Matched v0.2.0 PE companions retained; native OpenGL and Vulkan modules preserved.\n'
notice.write_text(text)
report['titleFiles']['WINE_CORE_V020_SOURCES.txt']=hashlib.sha256(notice.read_bytes()).hexdigest()
report['localRootFix']=True
report['consoleVerified']=False
report['preservedNativeOpenGL']=hashlib.sha256((title/'win/wine/lib/wine/x86_64-unix/win32u.prx').read_bytes()).hexdigest()
(title/'WINE_CORE_V020_REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
for path in (title/'STAGE-REPORT.json',title/'prosperomc/STAGE-REPORT.json'):
    stage=json.loads(path.read_text())
    stage['wine']['ntdllSha256']=core.LOCAL_MODULES['ntdll']
    stage['wine']['runtimeCore'].update(localRootFix=True,fdFailureDiagnostics=True,consoleVerified=False)
    path.write_text(json.dumps(stage,indent=2)+'\n')
core.core_names(title)
print('STAGED_ABI_REVIEWED_V020_ROOT_FIX',core.LOCAL_MODULES)
