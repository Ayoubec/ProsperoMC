#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
task_work=/tmp/prosperomc-wine-graphics
output=${PROSPEROMC_GRAPHICS_OUTPUT:-"$project/artifacts/wine-graphics"}
graphics_prefix=${PROSPEROMC_GRAPHICS_SDK:-"$project/.deps/graphics-sdk-1.0.1/sdk"}
mkdir -p "$task_work/source" "$task_work/host" "$output"
capture_logs() {
    for log in "$task_work/graphics-build.log" "$task_work/ps5/configure.log" \
        "$task_work/ps5/make.log" "$task_work/ps5/prx/win32u.link.log"; do
        [[ ! -f "$log" ]] || cp "$log" "$output/"
    done
}
trap capture_logs EXIT
if [[ ! -f "$task_work/source/configure" ]]; then
    tar -xzf "$project/.deps/archives/wine-490f6d5.tar.gz" -C "$task_work/source" --strip-components=1
fi
cd "$task_work/host"
if [[ ! -f Makefile ]]; then
    "$task_work/source/configure" --enable-win64 --disable-tests --without-x \
        --without-wayland --without-freetype --without-opengl --without-gnutls \
        --without-alsa --without-pulse > configure.log 2>&1
fi
make -j8 tools/winebuild/winebuild tools/widl/widl tools/makedep > host-tools.log 2>&1
echo HOST_WINE_TOOLS_READY
release="$project/.deps/source/prospero-win-8086243da85fae62206a98af322dc746fe5f7a6d"
foundation="$project/.deps/source/ps5-native-app-boilerplate-9c0b994a048521af6fb84c73ded364504fe250e9"
prx_foundation="$project/.deps/source/ps5-native-app-boilerplate-30597512539e7edfde079cbcaf4a626bc0a948c5"
sdk="$task_work/sdk"
# Local build inputs avoid repeated cross-filesystem header/tool lookups.
if [[ ! -f "$sdk/bin/prospero-clang" ]]; then
    cp -a "$foundation/.deps/native/ps5-payload-sdk" "$sdk"
fi
mkdir -p "$task_work/graphics-sdk"
cp -a "$graphics_prefix/." "$task_work/graphics-sdk/"
export PROSPEROMC_NTDLL_IMPORT="$project/artifacts/wine-fpfix/ntdll.shared.elf"
if [[ -f "$project/.deps/archives/freetype-2.13.3.tar.xz" ]]; then
    export PROSPERO_FREETYPE_TARBALL="$project/.deps/archives/freetype-2.13.3.tar.xz"
fi
export PROSPEROMC_OPENGL_REVISION=${PROSPEROMC_OPENGL_REVISION:-db752da4c89380af228497b5b6852163a4e61069}
bash "$release/tools/build_prosperomc_graphics.sh" \
    --source "$task_work/source" --host-tools "$task_work/host" \
    --foundation "$foundation" --sdk "$sdk" --prx-foundation "$prx_foundation" \
    --ps5-opengl-sdk "$task_work/graphics-sdk" \
    --work "$task_work/ps5" --jobs 8 > "$task_work/graphics-build.log" 2>&1
echo WIN32U_GRAPHICS_BUILD_COMPLETE
cp "$task_work/ps5/prx/sce_module/win32u.prx" "$task_work/ps5/prx/win32u.elf" \
    "$task_work/ps5/prx/win32u.shared.elf" "$task_work/ps5/report.json" "$output/"
