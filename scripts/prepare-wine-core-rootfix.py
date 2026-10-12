"""Adapt the pinned v0.2.0 recipe to build only the core with a proven CWD fix."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess

root=Path(__file__).resolve().parents[1]
release=root/'.deps/source/prospero-win-644e32e400c555e340d507383398c5d21b39b0b0'
out=root/'artifacts/wine-core-rootfix';out.mkdir(parents=True,exist_ok=True)
archive=root/'.deps/archives/wine-490f6d5.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='c40c03637f90ede4fe60ffc4162473870038dc2324cd1d67d186ad72212a70d5'
original=(release/'wine/ps5/pw_wine_cwd.c').read_bytes()
backup=out/'pw_wine_cwd-original.c'
if not backup.exists():backup.write_bytes(original)
assert hashlib.sha256(backup.read_bytes()).hexdigest()=='b7dfab538e459da54c90156b7171de28216a544270a2d9af72e6d7e4533ee730'
modified=(root/'vendor/prospero-win/wine/ps5/pw_wine_cwd.c').read_bytes()
patch=''.join(difflib.unified_diff(backup.read_text().splitlines(True),modified.decode().splitlines(True),
    fromfile='a/wine/ps5/pw_wine_cwd.c',tofile='b/wine/ps5/pw_wine_cwd.c'))
(out/'cwd-volume-root.patch').write_text(patch)
shutil.copy2(root/'vendor/prospero-win/wine/ps5/pw_wine_cwd.c',release/'wine/ps5/pw_wine_cwd.c')
subprocess.run(['python3',str(root/'scripts/prepare-wine-fd-report.py'),'--recipe-root',str(release)],check=True)
text=(release/'tools/build_wine_ps5.sh').read_text()
start=text.index('TARGETS="');end=text.index('\n# Everything optional',start)
text=text[:start]+'TARGETS="dlls/ntdll/ntdll.so server/wineserver"\nPE_MODULES=""\n'+text[end:]
old='[ "$(git -C "$source_dir" rev-parse HEAD 2>/dev/null)" = "$WINE_COMMIT" ] ||\n    fail "$source_dir is not the pinned Wine revision $WINE_COMMIT"'
assert text.count(old)==1
text=text.replace(old,'# Exact source archive verified by prepare-wine-core-rootfix.py.\n[ -f "$source_dir/configure" ] || fail "missing pinned Wine source"')
start=text.index('if [ ! -d "$tree/.git" ]; then');end=text.index('\n# Stage Vulkan batching',start)
text=text[:start]+'''if [ ! -f "$tree/.prosperomc-patched" ]; then
    mkdir -p "$tree"
    cp -a "$source_dir/." "$tree/"
    for patch in $ordered; do
        git -C "$tree" apply "$patches/$patch" || fail "patch does not apply: $patch"
    done
    printf '%s\\n' "$ordered" > "$tree/.prosperomc-patched"
fi
'''+text[end:]
start=text.index('for step in "dlls/ntdll/ntdll.so|');end=text.index('; do\n    target=',start)
text=text[:start]+'for step in "dlls/ntdll/ntdll.so|$heap $dmem" "server/wineserver|$heap"'+text[end:]
start=text.index('rm -rf "$work/pe"');end=text.index('\n# The PRX link.',start)
text=text[:start]+'# PE ntdll companions remain the verified matching v0.2.0 release binaries.\n'+text[end:]
old='elif ! git -C "$prx_foundation" merge-base --is-ancestor "$MODULE_EXPORTS_COMMIT" HEAD 2>/dev/null; then'
assert text.count(old)==1
text=text.replace(old,'elif ! grep -q \'has_flag(args, "--module")\' "$prx_foundation/tooling/native/native_app_builder.cpp"; then')
start=text.index('    link_prx win32u dlls/win32u/win32u.so');end=text.index('    # The WoW64 CPU backend',start)
pair=text[start:end];pair=pair[pair.index('    # ntdll loads'):]
tail=text.index('\nif PW_SOURCE_PRX_FOUNDATION=',end)
text=text[:start]+pair+'fi\n'+text[tail:]
start=text.index('for name in ("ntdll", "win32u", "wineserver",');end=text.index(':\n    module =',start)
text=text[:start]+'for name in ("ntdll", "wineserver") if not prx_status.startswith("skipped") else ()'+text[end:]
text=text.replace('source_prx_foundation=$(git -C "$prx_foundation" rev-parse HEAD 2>/dev/null || true)','source_prx_foundation=$MODULE_EXPORTS_COMMIT')
(release/'tools/build_prosperomc_core_rootfix.sh').write_text(text)
(out/'source-provenance.json').write_text(json.dumps({'sourceCommit':release.name.removeprefix('prospero-win-'),
    'wineArchiveSha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
    'patchSha256':hashlib.sha256(patch.encode()).hexdigest(),'cwdSha256':hashlib.sha256(modified).hexdigest(),
    'recipeSha256':hashlib.sha256(text.encode()).hexdigest(),
    'fdDiagnosticPatchSha256':hashlib.sha256((root/'artifacts/wine-fd-review/cwd-fd-diagnostic.patch').read_bytes()).hexdigest()},indent=2))
print('PREPARED_PINNED_V020_CORE_ROOT_FIX')
