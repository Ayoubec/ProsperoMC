#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
task_work=/tmp/prosperomc-wine-core020
out="$project/artifacts/wine-core-rootfix"
mkdir -p "$task_work/source" "$task_work/host" "$out"
capture() {
    for log in "$task_work/core-build.log" "$task_work/ps5/configure.log" "$task_work/ps5/make.log" "$task_work/ps5/prx/ntdll.link.log" "$task_work/ps5/prx/wineserver.link.log"; do
        [[ ! -f "$log" ]] || cp "$log" "$out/"
    done
}
trap capture EXIT
if [[ ! -f "$task_work/source/configure" ]]; then
    tar -xzf "$project/.deps/archives/wine-490f6d5.tar.gz" -C "$task_work/source" --strip-components=1
fi
cd "$task_work/host"
if [[ ! -f Makefile ]]; then
    "$task_work/source/configure" --enable-win64 --disable-tests --without-x --without-wayland --without-freetype --without-opengl --without-gnutls --without-alsa --without-pulse > configure.log 2>&1
fi
make -j4 tools/winebuild/winebuild tools/widl/widl tools/makedep > host-tools.log 2>&1
echo CORE_HOST_TOOLS_READY
release="$project/.deps/source/prospero-win-644e32e400c555e340d507383398c5d21b39b0b0"
foundation="$project/.deps/source/ps5-native-app-boilerplate-9c0b994a048521af6fb84c73ded364504fe250e9"
prx_foundation="$project/.deps/source/ps5-native-app-boilerplate-30597512539e7edfde079cbcaf4a626bc0a948c5"
sdk="$task_work/sdk"
[[ -d "$sdk" ]] || cp -a "$foundation/.deps/native/ps5-payload-sdk" "$sdk"
export PROSPERO_FREETYPE_TARBALL="$project/.deps/archives/freetype-2.13.3.tar.xz"
bash "$release/tools/build_prosperomc_core_rootfix.sh" --source "$task_work/source" --host-tools "$task_work/host" --foundation "$foundation" --sdk "$sdk" --prx-foundation "$prx_foundation" --work "$task_work/ps5" --jobs 4 > "$task_work/core-build.log" 2>&1
for name in ntdll wineserver; do
    cp "$task_work/ps5/prx/sce_module/$name.prx" "$task_work/ps5/prx/$name.elf" "$task_work/ps5/prx/$name.shared.elf" "$out/"
done
cp "$task_work/ps5/report.json" "$out/"
echo V020_CORE_ROOT_FIX_BUILD_COMPLETE
