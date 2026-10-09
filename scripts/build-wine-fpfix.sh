#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
task_work=/tmp/prosperomc-wine-fpfix
mkdir -p "$task_work/source" "$task_work/host"
if [[ ! -f "$task_work/source/configure" ]]; then
    echo 'Extracting verified pinned Wine source'
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
capture_logs() {
    mkdir -p "$project/artifacts/wine-fpfix"
    for log in "$task_work/ntdll-build.log" "$task_work/ps5/configure.log" \
        "$task_work/ps5/make.log" "$task_work/ps5/prx/ntdll.link.log"; do
        [[ ! -f "$log" ]] || cp "$log" "$project/artifacts/wine-fpfix/"
    done
}
trap capture_logs EXIT

release="$project/.deps/source/prospero-win-8086243da85fae62206a98af322dc746fe5f7a6d"
foundation="$project/.deps/source/ps5-native-app-boilerplate-9c0b994a048521af6fb84c73ded364504fe250e9"
prx_foundation="$project/.deps/source/ps5-native-app-boilerplate-30597512539e7edfde079cbcaf4a626bc0a948c5"
sdk="$foundation/.deps/native/ps5-payload-sdk"
native="$prx_foundation/tooling/native"
tool="$prx_foundation/build/host/ps5-native-tool"
mkdir -p "$(dirname "$tool")"
if [[ ! -x "$tool" ]]; then
    clang++-18 -std=c++20 -O2 -Wall -Wextra -Werror \
        "$native/native_app_builder.cpp" "$native/self_container.cpp" \
        "$native/elf_object.cpp" "$native/sce_module_writer.cpp" \
        /usr/lib/x86_64-linux-gnu/libz.a -o "$tool"
fi
echo MODULE_EXPORT_TOOL_READY
bash "$release/tools/build_prosperomc_ntdll.sh" \
    --source "$task_work/source" --host-tools "$task_work/host" \
    --foundation "$foundation" --sdk "$sdk" --prx-foundation "$prx_foundation" \
    --work "$task_work/ps5" --jobs 8 > "$task_work/ntdll-build.log" 2>&1
echo PATCHED_NTDLL_BUILD_COMPLETE
mkdir -p "$project/artifacts/wine-fpfix"
cp "$task_work/ps5/prx/sce_module/ntdll.prx" "$task_work/ps5/prx/ntdll.elf" \
    "$task_work/ps5/prx/ntdll.shared.elf" "$task_work/ps5/report.json" \
    "$task_work/ps5/prx/ntdll.link.log" "$project/artifacts/wine-fpfix/"
cp "$task_work/ntdll-build.log" "$project/artifacts/wine-fpfix/"
