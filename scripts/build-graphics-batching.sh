#!/usr/bin/env bash
# Compile only the changed PS5 draw driver, reusing verified CI SDK libraries.
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
work=/tmp/prosperomc-graphics-performance
out="$project/artifacts/graphics-batching"
mkdir -p "$work" "$out"
capture() {
    find "$work" -maxdepth 1 -name '*.log' -exec cp {} "$out/" \;
    # Preserve configured headers across WSL shutdown, including failed builds.
    [[ ! -f "$work/mesa-build/build.ninja" ]] || \
        tar -czf "$out/build-state.tar.gz" -C "$work" source mesa-build sdk tools prospero.ini
}
trap capture EXIT
if [[ ! -f "$work/mesa-build/build.ninja" && -f "$out/build-state.tar.gz" ]]; then
    tar -xzf "$out/build-state.tar.gz" -C "$work"
fi
export LLVM_CONFIG=/usr/bin/llvm-config-18
[[ -x "$work/tools/bin/python" ]] || python3 -m venv "$work/tools"
"$work/tools/bin/python" -m pip install --no-cache-dir --disable-pip-version-check meson==1.8.3 Mako==1.3.10 PyYAML==6.0.2 packaging==25.0 > "$work/tools.log" 2>&1
export PATH="$work/tools/bin:$PATH"
python "$project/scripts/compile-graphics-batching.py" "$work" > "$work/driver-build.log" 2>&1
echo SMOOTH_QUAD_DRIVER_BUILD_COMPLETE
# The unchanged Wine build recipe links this modified SDK into win32u only.
PROSPEROMC_GRAPHICS_OUTPUT="$project/artifacts/wine-graphics-batching" \
PROSPEROMC_GRAPHICS_SDK="$project/.deps/graphics-sdk-batching/sdk" \
PROSPEROMC_OPENGL_REVISION=738f94cbdf6ff1de0376dc1cd4ce1229fd640730 \
bash "$project/scripts/build-wine-graphics.sh"
