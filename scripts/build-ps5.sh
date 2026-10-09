#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
pin=9c0b994a048521af6fb84c73ded364504fe250e9
foundation=${PS5_NATIVE_FOUNDATION:-$root/.deps/source/ps5-native-app-boilerplate-$pin}
sdk=${PS5_PAYLOAD_SDK:-$foundation/.deps/native/ps5-payload-sdk}
vendor="$root/vendor/prospero-win"
build="$root/build/ps5"
dist="$root/dist/PPSA99888"
native="$foundation/tooling/native"
tool="$foundation/build/runtime-shim/ps5-native-tool"
layout="$native/ps5-pie-high.ld"
if [[ ! -f $tool || ! -f $sdk/bin/prospero-lld || ! -f $foundation/runtime/libc.prx ]]; then
    [[ -z ${PS5_NATIVE_FOUNDATION:-} && -z ${PS5_PAYLOAD_SDK:-} ]] || {
        echo 'Custom foundation/SDK inputs are incomplete; prepare them or use the default pinned bootstrap' >&2; exit 2; }
    bash "$root/scripts/setup-ps5-dependencies.sh"
fi
for file in "$sdk/bin/prospero-lld" "$foundation/tooling/prospero-clang18" "$tool" "$layout" "$foundation/runtime/libc.prx"; do
    [[ -f $file ]] || { echo "Missing pinned build input: $file" >&2; exit 2; }
done
mkdir -p "$build/obj" "$build/import-stubs" "$dist/sce_sys" "$dist/sce_module"
cc=(env PS5_PAYLOAD_SDK="$sdk" sh "$foundation/tooling/prospero-clang18")
common=(-O2 -Wall -Wextra -Werror -ffunction-sections -fdata-sections
    -I"$vendor/include" -I"$vendor/src" -I"$vendor/native" -I"$vendor/native/ps5log" -I"$root/app/native"
    -DPW_BUILD_ID=\"prosperomc-b510eb3\" -DPW_WINE64_SCRIPT=0 -DPW_WINE64_SECONDS=0)
sources=(native/wine64_main.c native/pm_bridge.c native/pw_diagnostics.c native/pw_audio_ps5.c native/pw_pad_ps5.c
    native/pw_hid_ps5.c native/pw_agc_ps5.c native/pw_agc_submit_lifecycle.c native/pw_videoout_ps5.c
    native/pw_data_mount.c native/pw_lapy_elevation.c native/pw_wine_display.c native/pw_wine_prefix.c
    src/pw_result.c src/pw_wine_start.c src/pw_wine_launch.c src/pw_game_profile.c src/pw_prefix_temp.c
    src/pw_app_profile.c src/pw_present.c src/pw_pad.c src/pw_hid.c src/pw_spinner.c src/pw_tsc_calibrate.c
    wine/ps5/pw_wine_prx.c)
objects=()
for source in "${sources[@]}"; do
    object="$build/obj/${source//\//_}.o"
    "${cc[@]}" -std=c11 "${common[@]}" -c "$vendor/$source" -o "$object"
    objects+=("$object")
done
"${cc[@]}" -std=c11 "${common[@]}" -c "$root/app/native/pm_frontend.c" -o "$build/obj/pm_frontend.o"
objects+=("$build/obj/pm_frontend.o")
"${cc[@]}" -std=c11 "${common[@]}" -include "$vendor/native/ps5log/ps5log_ps5_net.h" -c "$vendor/native/ps5log/ps5log.c" -o "$build/obj/ps5log.o"
"${cc[@]}" -std=c11 "${common[@]}" -c "$vendor/native/ps5log/ps5log_ps5_net.c" -o "$build/obj/ps5log_ps5_net.o"
objects+=("$build/obj/ps5log.o" "$build/obj/ps5log_ps5_net.o")
"${cc[@]}" -std=c++20 -O2 -Wall -Wextra -Werror -fno-exceptions -fno-rtti -ffunction-sections -fdata-sections -c "$native/app_crt.cpp" -o "$build/obj/app_crt.o"
for name in libSceAgc libSceAgcDriver; do
    "${cc[@]}" -std=c11 -O2 -fPIC -c "$vendor/native/stubs/$name.c" -o "$build/obj/$name.o"
    "$sdk/bin/prospero-lld" --shared -soname "$name.prx" -o "$build/import-stubs/$name.so" "$build/obj/$name.o"
done
"$sdk/bin/prospero-lld" -T "$layout" --eh-frame-hdr -e _start -o "$build/llvm-pie.elf" "$build/obj/app_crt.o" "${objects[@]}" \
    --as-needed "$sdk"/target/lib/*.so "$build/import-stubs/libSceAgc.so" "$build/import-stubs/libSceAgcDriver.so"
"$tool" link --in "$build/llvm-pie.elf" --out "$build/eboot.elf" --stub-dir "$sdk/target/lib" --module-sdk 0x02000009 \
    --stub "$build/import-stubs/libSceAgc.so" --stub "$build/import-stubs/libSceAgcDriver.so" --companion-sdk 0x08050001 --file-name eboot.elf
"$tool" self --sign --in "$build/eboot.elf" --out "$dist/eboot.bin" --magic 0x1D3D154F
cp "$vendor/sce_sys/param.json" "$dist/sce_sys/param.json"
cp "$root/sce_sys/icon0.png" "$dist/sce_sys/icon0.png"
cp "$root/sce_sys/pic0.dds" "$root/sce_sys/pic1.dds" "$dist/sce_sys/"
cp "$root/sce_sys/snd0.at9" "$dist/sce_sys/"
cp "$foundation/runtime/libc.prx" "$dist/sce_module/libc.prx"
chmod 755 "$dist/eboot.bin" "$dist/sce_module/libc.prx"
readelf=${LLVM_READELF:-$(command -v llvm-readelf-18 || command -v llvm-readelf)}
"$readelf" --dyn-syms "$build/llvm-pie.elf" | awk '$7 == "UND" { print $8 }' | sort -u > "$build/DYNAMIC_IMPORTS.txt"
if grep -qx strcasestr "$build/DYNAMIC_IMPORTS.txt"; then echo 'Unusable platform import: strcasestr' >&2; exit 2; fi
sha256sum "$build/eboot.elf" "$dist/eboot.bin" | tee "$build/native-sha256.txt"
echo "Native title compiled. Stage and validate Wine, Java and launcher separately before deployment."
