"""Adapt the release-matched recipe to relink only win32u with fixed GL SDK."""
from pathlib import Path
root = Path(__file__).resolve().parent.parent
release = root / '.deps/source/prospero-win-8086243da85fae62206a98af322dc746fe5f7a6d'
# The existing adapter supplies archive verification and exactly 73 Wine patches.
exec((root / 'scripts/prepare-wine-fpfix.py').read_text(), {'__file__': str(root / 'scripts/prepare-wine-fpfix.py')})
extra_patches = ('0671-win32u-ps5-mouse-wheel.patch', '0672-win32u-ps5-fixed-game-window.patch',
                 '0910-win32u-ps5-worker-desktop-cache.patch')
for name in extra_patches:
    (release / 'wine/patches' / name).write_bytes(
        (root / 'vendor/prospero-win/wine/patches' / name).read_bytes())
text = (release / 'tools/build_prosperomc_ntdll.sh').read_text()
text = text.replace('-le 899', '-le 999').replace('outside 0100-0899', 'outside 0100-0999')
text = text.replace('\n# The PS5 OpenGL SDK', '''
for extra_patch in 0671-win32u-ps5-mouse-wheel.patch 0672-win32u-ps5-fixed-game-window.patch 0910-win32u-ps5-worker-desktop-cache.patch; do
    if ! grep -qx "$extra_patch" "$tree/.prosperomc-patched"; then
        git -C "$tree" apply "$patches/$extra_patch" || fail "extra patch does not apply: $extra_patch"
        echo "$extra_patch" >> "$tree/.prosperomc-patched"
    fi
done
# The PS5 OpenGL SDK''', 1)
text = text.replace('TARGETS="dlls/ntdll/ntdll.so"', 'TARGETS="dlls/win32u/win32u.so"')
text = text.replace('for step in "dlls/ntdll/ntdll.so|$heap $dmem";', 'for step in "dlls/win32u/win32u.so|";')
start = text.index('    link_prx ntdll dlls/ntdll/ntdll.so')
end = text.index('\nif PW_SOURCE_PRX_FOUNDATION=', start)
text = text[:start] + '''    cp "$PROSPEROMC_NTDLL_IMPORT" "$prx/ntdll.shared.elf"
    "$sdk/bin/prospero-clang" -std=c11 -O2 -Wall -Wextra -Werror -fPIC \\
        -c "$root/wine/ps5/pw_opengl_libc.c" -o "$prx/obj/pw_opengl_libc.o"
    (cd "$prx/obj" && "$sdk/bin/llvm-ar" x "$sdk/target/lib/libc.a" emutls.o)
    link_prx win32u dlls/win32u/win32u.so \\
        "$prx/obj/win32u_desc.o $prx/obj/pw_opengl_libc.o $prx/obj/emutls.o" \\
        "$prx/ntdll.shared.elf"
fi
''' + text[end:]
text = text.replace('for name in ("ntdll",) if', 'for name in ("win32u",) if')
text = text.replace('source_ps5_opengl=$(git -C "$ps5opengl_sdk" rev-parse HEAD 2>/dev/null || true)',
                    'source_ps5_opengl=$PROSPEROMC_OPENGL_REVISION')
(release / 'tools/build_prosperomc_graphics.sh').write_bytes(text.encode())
print('PREPARED_WIN32U_ONLY_GRAPHICS_RECIPE')
