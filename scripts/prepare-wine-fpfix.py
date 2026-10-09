#!/usr/bin/env python3
"""Adapt the verified release recipe to rebuild only ntdll from archive sources."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parent.parent
release = ROOT / '.deps/source/prospero-win-8086243da85fae62206a98af322dc746fe5f7a6d'
latest = ROOT / '.deps/source/prospero-win-b510eb3db8709bb251d3da3c56850e96e057f489'
for name, expected in {
    'wine-490f6d5.tar.gz': 'c40c03637f90ede4fe60ffc4162473870038dc2324cd1d67d186ad72212a70d5',
    'prx-foundation-3059751.zip': '9afcf7314e52af65b2a84848e396b908a0e74c3d4bc179fc6d18560e96a94ac0',
    'prospero-win-runtime-8086243.zip': '9bc865efd9c4f6e5d159c61b64838c25e49682fff55fcd845e800305f688f5b4',
}.items():
    assert hashlib.sha256((ROOT / '.deps/archives' / name).read_bytes()).hexdigest() == expected, name
patch = '0501-ntdll-ps5-signal-fp-state-at-its-measured-offset.patch'
patch_bytes = (latest / 'wine/patches' / patch).read_bytes()
assert hashlib.sha256(patch_bytes).hexdigest() == '24b8a254c01dd65cec187b08b44e830663b677a21410fb5ea5476924f4ea9a19'
(release / 'wine/patches' / patch).write_bytes(patch_bytes)
text = (release / 'tools/build_wine_ps5.sh').read_text()

def replace(old, new):
    global text
    assert text.count(old) == 1, old[:100]
    text = text.replace(old, new)

start = text.index('TARGETS="')
end = text.index('\n# Everything optional', start)
text = text[:start] + 'TARGETS="dlls/ntdll/ntdll.so"\nPE_MODULES=""\n' + text[end:]
replace('[ "$(git -C "$source_dir" rev-parse HEAD 2>/dev/null)" = "$WINE_COMMIT" ] ||\n    fail "$source_dir is not the pinned Wine revision $WINE_COMMIT"',
        '# Source archive SHA-256 and pinned revision verified by prepare-wine-fpfix.py.\n[ -f "$source_dir/configure" ] || fail "missing verified Wine source"')
start = text.index('if [ ! -d "$tree/.git" ]; then')
end = text.index('\n# The PS5 OpenGL SDK', start)
text = text[:start] + '''if [ ! -f "$tree/.prosperomc-patched" ]; then
    mkdir -p "$tree"
    cp -a "$source_dir/." "$tree/"
    for patch in $ordered; do
        git -C "$tree" apply "$patches/$patch" || fail "patch does not apply: $patch"
        echo "applied $patch"
    done
    printf '%s\\n' "$ordered" > "$tree/.prosperomc-patched"
fi
''' + text[end:]
start = text.index('for step in "dlls/ntdll/ntdll.so|')
end = text.index('; do\n    target=', start)
text = text[:start] + 'for step in "dlls/ntdll/ntdll.so|$heap $dmem"' + text[end:]
replace('elif ! git -C "$prx_foundation" merge-base --is-ancestor "$MODULE_EXPORTS_COMMIT" HEAD 2>/dev/null; then',
        'elif ! grep -q \'has_flag(args, "--module")\' "$prx_foundation/tooling/native/native_app_builder.cpp"; then')
replace('source_prx_foundation=$(git -C "$prx_foundation" rev-parse HEAD 2>/dev/null || true)',
        'source_prx_foundation=$MODULE_EXPORTS_COMMIT')
start = text.index('    if [ -n "$ps5opengl_sdk" ]; then', text.index('    link_prx ntdll dlls/ntdll/ntdll.so'))
end = text.index('\nif PW_SOURCE_PRX_FOUNDATION=', start)
text = text[:start] + 'fi\n' + text[end:]
start = text.index('for name in ("ntdll", "win32u", "wineserver",')
end = text.index(':\n    module =', start)
text = text[:start] + 'for name in ("ntdll",) if not prx_status.startswith("skipped") else ()' + text[end:]
(release / 'tools/build_prosperomc_ntdll.sh').write_bytes(text.encode())
print('PREPARED_PINNED_NTDLL_RECIPE_WITH_0501')
