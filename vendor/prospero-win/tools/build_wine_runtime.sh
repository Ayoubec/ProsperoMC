#!/bin/sh
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Stage a reproducible i386 Wine PE runtime from the pinned revision.
#
# The build is out-of-tree and refuses a dirty or wrong checkout, because the
# whole point of the exercise is that the PE modules other modules bind
# against are the ones this manifest describes. Generated modules are
# build artifacts: they are never committed.
#
# Reproducibility comes from three documented things and nothing else:
#   * the exact Wine commit below;
#   * a normalised environment (LC_ALL=C, TZ=UTC, SOURCE_DATE_EPOCH);
#   * a fixed module set, so two runs stage the same file names.
# A later rebuild of the same commit with the same toolchain produces
# byte-identical PE files, whose hashes are recorded in the manifest.
#
# Usage:
#   tools/build_wine_runtime.sh [--check-reproducible] [--jobs N]
#       [--out DIR] [--build-root DIR] [--source DIR]
#
# Environment:
#   PROSPERO_WINE_SOURCE   existing checkout (default <build-root>/source)
#   PROSPERO_WINE_BUILD    build directory  (default <build-root>/build)
#   PROSPERO_WINE_OUT      staged runtime   (default .deps/wine-runtime)
#   PROSPERO_WINE_GIT      clone URL used when --source does not exist
set -eu

WINE_COMMIT=490f6d5dcbb2a5047345b8af88d114bbcaad69a8
WINE_URL=${PROSPERO_WINE_GIT:-https://github.com/wine-mirror/wine.git}
MODULES="ntdll kernelbase kernel32"
LIBRARY=lib/i386-windows
# The distribution's data files, staged beside the modules and folded into the
# manifest's digest: every NLS data file the pinned revision tracks (its nls/
# directory), which is what the runtime's own locale code reads - locale.nls
# for the locale tables (RtlGetLocaleFileMappingAddress, dlls/ntdll/locale.c:613,
# and kernelbase's init_locale, dlls/kernelbase/locale.c:438), the sort keys,
# the case map, the normalization tables and one file per codepage the guest
# asks about (dlls/ntdll/unix/env.c:93 get_nls_file_path). Wine tracks them
# all as source files, so staging them is a copy and not a second build, and a
# distribution that carries them is what an installed prefix has: measured, the
# run asked for c_437.nls and crashed on the unset table pointer that a refused
# codepage request left behind.
DATA_SUFFIX=".nls"
CONFIGURE_ARGS="--enable-archs=i386,x86_64 --disable-tests"

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
default_root="$root/.deps/wine"
build_root=${PROSPERO_WINE_ROOT:-$default_root}
source_dir=${PROSPERO_WINE_SOURCE:-$build_root/source}
build_dir=${PROSPERO_WINE_BUILD:-$build_root/build}
out_dir=${PROSPERO_WINE_OUT:-$root/.deps/wine-runtime}
manifest=$out_dir/wine-runtime-manifest.json
jobs=${PROSPERO_WINE_JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}
check_reproducible=0

while [ $# -gt 0 ]; do
    case "$1" in
        --check-reproducible) check_reproducible=1 ;;
        --jobs) jobs=$2; shift ;;
        --out) out_dir=$2; manifest=$out_dir/wine-runtime-manifest.json; shift ;;
        --build-root)
            build_root=$2
            source_dir=${PROSPERO_WINE_SOURCE:-$build_root/source}
            build_dir=${PROSPERO_WINE_BUILD:-$build_root/build}
            shift ;;
        --source) source_dir=$2; shift ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
    shift
done

# A toolchain that ignores SOURCE_DATE_EPOCH would silently produce a new
# runtime identity per build, so it is pinned here rather than inherited.
LC_ALL=C
TZ=UTC
SOURCE_DATE_EPOCH=1000000000
export LC_ALL TZ SOURCE_DATE_EPOCH

fail() { echo "build_wine_runtime: $*" >&2; exit 1; }

case "$out_dir" in ""|"/") fail "refusing an empty or root out directory" ;; esac
case "$build_root" in ""|"/") fail "refusing an empty or root build root" ;; esac

require_clean_source() {
    [ -d "$source_dir/.git" ] || fail "not a Wine git checkout: $source_dir"
    head=$(git -C "$source_dir" rev-parse HEAD)
    [ "$head" = "$WINE_COMMIT" ] || \
        fail "Wine checkout is $head, expected $WINE_COMMIT"
    if [ -n "$(git -C "$source_dir" status --porcelain)" ]; then
        fail "Wine checkout is dirty: $source_dir"
    fi
    [ -x "$source_dir/configure" ] || fail "Wine checkout has no configure"
}

if [ ! -d "$source_dir/.git" ]; then
    echo "cloning Wine into $source_dir"
    mkdir -p "$build_root"
    git clone --filter=blob:none --no-checkout "$WINE_URL" "$source_dir"
fi
if ! git -C "$source_dir" cat-file -e "$WINE_COMMIT^{commit}" 2>/dev/null; then
    git -C "$source_dir" fetch --quiet origin "$WINE_COMMIT"
fi
git -C "$source_dir" checkout --quiet "$WINE_COMMIT"
require_clean_source

build_modules() {
    if [ ! -f "$build_dir/Makefile" ]; then
        mkdir -p "$build_dir"
        (cd "$build_dir" && "$source_dir/configure" $CONFIGURE_ARGS) \
            > "$build_root/configure.log" 2>&1 || \
            fail "configure failed; see $build_root/configure.log"
    fi
    for module in $MODULES; do
        target="dlls/$module/i386-windows/$module.dll"
        (cd "$build_dir" && make -B -j"$jobs" "$target") \
            > "$build_root/make-$module.log" 2>&1 || \
            fail "building $target failed; see $build_root/make-$module.log"
    done
}

stage() {
    destination=$1
    rm -rf "$destination/$LIBRARY"
    mkdir -p "$destination/$LIBRARY"
    for module in $MODULES; do
        built="$build_dir/dlls/$module/i386-windows/$module.dll"
        [ -f "$built" ] || fail "missing built module: $built"
        cp "$built" "$destination/$LIBRARY/$module.dll"
    done
    [ -d "$source_dir/nls" ] || fail "missing NLS data: $source_dir/nls"
    mkdir -p "$destination/nls"
    for data in "$source_dir"/nls/*"$DATA_SUFFIX"; do
        [ -f "$data" ] || fail "no NLS data files in $source_dir/nls"
        cp "$data" "$destination/nls/"
    done
}

build_modules

if [ "$check_reproducible" = 1 ]; then
    stage "$build_root/stage-a"
    build_modules
    stage "$build_root/stage-b"
    for module in $MODULES; do
        if ! cmp -s "$build_root/stage-a/$LIBRARY/$module.dll" \
                    "$build_root/stage-b/$LIBRARY/$module.dll"; then
            fail "$module.dll differs between two forced rebuilds in one pinned build tree"
        fi
    done
    for data in "$build_root"/stage-a/nls/*"$DATA_SUFFIX"; do
        name=$(basename "$data")
        if ! cmp -s "$data" "$build_root/stage-b/nls/$name"; then
            fail "$name differs between two staged distributions"
        fi
    done
    echo "reproducible: two forced rebuilds in one pinned build tree produced identical modules"
fi

stage "$out_dir"
data_args=""
for data in "$out_dir"/nls/*"$DATA_SUFFIX"; do
    data_args="$data_args --data nls/$(basename "$data")"
done
python3 "$root/tools/validate_wine_runtime.py" write \
    --distribution "$out_dir" \
    --wine-source "$source_dir" \
    --wine-commit "$WINE_COMMIT" \
    --wine-url "$WINE_URL" \
    --library "$LIBRARY" \
    $data_args \
    --configure "$CONFIGURE_ARGS" \
    --out "$manifest" --force
python3 "$root/tools/validate_wine_runtime.py" check \
    --manifest "$manifest" --distribution "$out_dir" \
    --expect-commit "$WINE_COMMIT"
echo "staged i386 Wine runtime: $out_dir"
