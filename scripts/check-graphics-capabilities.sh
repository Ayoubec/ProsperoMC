#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
task_check=/tmp/prosperomc-graphics-capabilities
mkdir -p "$task_check"
cd "$task_check"
graphics_prefix=${PROSPEROMC_GRAPHICS_SDK:-"$project/.deps/graphics-sdk-1.0.1/sdk"}
llvm-ar-18 x "$graphics_prefix/lib/libps5_opengl_core33.a" ps5_screen.o
objcopy --globalize-symbol=ps5_is_format_supported ps5_screen.o
cat > check.c <<'C'
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
extern bool ps5_is_format_supported(void *, unsigned, unsigned, unsigned, unsigned, unsigned);
/* Only MSAA cases use this Mesa helper; these checks use one sample. */
void *util_format_description(unsigned format) { (void)format; assert(!"unexpected MSAA format helper"); return NULL; }
int main(void) {
    /* Verified against Mesa 26.2.0's generated enum and p_defines.h. */
    const unsigned bgra=105, rgba=84, texture2d=2, sample=8, render=2;
    assert(!ps5_is_format_supported(NULL,bgra,texture2d,1,1,sample));
    assert(!ps5_is_format_supported(NULL,bgra,texture2d,1,1,sample|render));
    assert(ps5_is_format_supported(NULL,bgra,texture2d,1,1,render));
    assert(ps5_is_format_supported(NULL,rgba,texture2d,1,1,sample));
    assert(ps5_is_format_supported(NULL,rgba,texture2d,1,1,sample|render));
    puts("PASS: compiled SDK rejects unsupported BGRA sampling, retains BGRA rendering and RGBA sampling/rendering");
}
C
gcc -O2 -ffunction-sections -fdata-sections -Wl,--gc-sections check.c ps5_screen.o -o check
./check | tee "$project/artifacts/graphics-source/capabilities-check.log"
