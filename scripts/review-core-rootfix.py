"""Require the locally rebuilt core to preserve all deployed exports/imports."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess

root=Path(__file__).resolve().parents[1]
out=root/'artifacts/wine-core-rootfix'
spec=importlib.util.spec_from_file_location('core_abi',root/'scripts/review-runtime-v020.py')
abi=importlib.util.module_from_spec(spec);spec.loader.exec_module(abi)
tool=root/'.deps/source/ps5-native-app-boilerplate-9c0b994a048521af6fb84c73ded364504fe250e9/build/runtime-shim/ps5-native-tool'
report=json.loads((out/'report.json').read_text())
assert report['wine_commit']=='490f6d5dcbb2a5047345b8af88d114bbcaad69a8'
assert report['prx']['status']=='0'
receipt={'sourceCommit':'644e32e400c555e340d507383398c5d21b39b0b0','modules':{},'consoleVerified':False}
for name in ('ntdll','wineserver'):
    entry=report['prx']['modules'][name]
    assert entry['built'] and all(not entry.get(key) for key in ('unresolved','errors','title_unbound','webkit_unbound','raw_syscalls'))
    old=root/'dist/PPSA99888/win/wine/lib/wine/x86_64-unix'/f'{name}.prx'
    new=out/f'{name}.prx'
    assert hashlib.sha256(new.read_bytes()).hexdigest()==entry['sha256']
    old_elf=out/f'baseline-{name}.elf';new_elf=out/f'review-{name}.elf'
    for source,target in ((old,old_elf),(new,new_elf)):
        subprocess.run([str(tool),'self','--extract','--file',str(source),'--out',str(target)],check=True,stdout=subprocess.DEVNULL)
    old_exports,old_imports=abi.symbols(old_elf);exports,imports=abi.symbols(new_elf)
    missing=old_exports-exports;added=imports-old_imports
    assert not missing,(name,'missing exports',missing)
    assert not added,(name,'unexpected platform imports',added)
    # Ensure the failure reporter was actually compiled into each module.
    assert b'wine-ps5: fd-exhaustion origin=' in new_elf.read_bytes()
    receipt['modules'][name]={'beforeSha256':hashlib.sha256(old.read_bytes()).hexdigest(),
        'sha256':entry['sha256'],'exports':len(exports),'missingExports':sorted(missing),'addedImports':sorted(added)}
(out/'abi-review.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
