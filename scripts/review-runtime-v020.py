#!/usr/bin/env python3
"""Audit release-pinned Wine core ABI without replacing the native GL backend."""
import hashlib
import base64
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA = '7585efc624c2f8077c0d579a045ef808129a7b0bc525a9dd9c5c6db0c51626ca'
CORE = ('ntdll.prx', 'wineserver.prx')
OUT = ROOT / 'artifacts/runtime-v020-review'
TITLE = ROOT / 'dist/PPSA99888'


def symbols(path):
    raw = subprocess.check_output(['llvm-readelf-18', '--dyn-syms', '--wide', str(path)], text=True)
    exports, imports = set(), set()
    for line in raw.splitlines():
        fields = line.split()
        if len(fields) == 8 and fields[0].rstrip(':').isdigit():
            if fields[6] == 'UND':
                imports.add(fields[7])
            elif fields[4] in ('GLOBAL', 'WEAK'):
                exports.add(fields[7])
    return exports, imports


def main():
    archive = ROOT / '.deps/archives/prospero-win-v0.2.0.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == ARCHIVE_SHA
    OUT.mkdir(parents=True, exist_ok=True)
    tool = ROOT / '.deps/source/ps5-native-app-boilerplate-9c0b994a048521af6fb84c73ded364504fe250e9/build/runtime-shim/ps5-native-tool'
    receipt = {'archiveSha256': ARCHIVE_SHA, 'modules': {}, 'consoleVerified': False}
    sdk = ROOT / '.deps/source/ps5-native-app-boilerplate-9c0b994a048521af6fb84c73ded364504fe250e9/.deps/native/ps5-payload-sdk/target/lib'
    names = {}
    salt = bytes.fromhex('518d64a635ded8c1e6b039b1c3e55230')
    for library in sdk.glob('*.so'):
        exports, _ = symbols(library)
        for name in exports:
            nid = base64.b64encode(hashlib.sha1(name.encode() + salt).digest()[:8][::-1]).decode()[:11].replace('/', '-')
            names[nid] = name
    with zipfile.ZipFile(archive) as z:
        for name in CORE:
            old = TITLE / 'win/wine/lib/wine/x86_64-unix' / name
            new = OUT / name
            new.write_bytes(z.read('PPSA99995/win/wine/lib/wine/x86_64-unix/' + name))
            old_elf, new_elf = OUT / ('before-' + name + '.elf'), OUT / (name + '.elf')
            for source, target in ((old, old_elf), (new, new_elf)):
                subprocess.run([str(tool), 'self', '--extract', '--file', str(source), '--out', str(target)], check=True, stdout=subprocess.DEVNULL)
            before_exports, before_imports = symbols(old_elf)
            after_exports, after_imports = symbols(new_elf)
            missing = before_exports - after_exports
            receipt['modules'][name] = {'beforeSha256': hashlib.sha256(old.read_bytes()).hexdigest(),
                'sha256': hashlib.sha256(new.read_bytes()).hexdigest(), 'missingExports': sorted(missing),
                'newImports': sorted(after_imports - before_imports), 'exports': len(after_exports),
                'newExports': sorted(after_exports - before_exports)}
            added = after_imports - before_imports
            receipt['modules'][name]['newImportNames'] = {value: names.get(value.split('#')[0], 'UNKNOWN') for value in sorted(added)}
            if missing or any(value == 'UNKNOWN' for value in receipt['modules'][name]['newImportNames'].values()):
                raise ValueError('Core module ABI or platform imports require review: ' + name)
    (OUT / 'abi-review.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
