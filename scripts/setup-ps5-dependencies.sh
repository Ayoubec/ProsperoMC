#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Reproducible public toolchain/bootstrap; no proprietary SDK or Git mutation.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
pin=9c0b994a048521af6fb84c73ded364504fe250e9
archive_sha=dad4d99acbd8a7326691bb517c56b542cc2a503b1bded66c616743ecdd751fbc
foundation="$root/.deps/source/ps5-native-app-boilerplate-$pin"
archive="$root/.deps/source/ps5-native-foundation-9c0b.zip"
for command in python3 sha256sum make clang-18 clang++-18; do
    command -v "$command" >/dev/null || { echo "Missing host tool: $command" >&2; exit 2; }
done
mkdir -p "$root/.deps/source"
if [[ ! -f $archive ]]; then
    python3 - "$archive" "$pin" <<'PY'
import pathlib,sys,urllib.request
output=pathlib.Path(sys.argv[1]); temporary=output.with_suffix('.download')
url='https://codeload.github.com/mpereiraesaa/ps5-native-app-boilerplate/zip/'+sys.argv[2]
with urllib.request.urlopen(url,timeout=60) as source,temporary.open('wb') as target:
    while chunk:=source.read(1<<20): target.write(chunk)
temporary.replace(output)
PY
fi
printf '%s  %s\n' "$archive_sha" "$archive" | sha256sum --check --strict
if [[ ! -f $foundation/.prosperomc-archive-sha256 ]]; then
    python3 - "$archive" "$root/.deps/source" <<'PY'
import pathlib,sys,zipfile
target=pathlib.Path(sys.argv[2]).resolve()
with zipfile.ZipFile(sys.argv[1]) as archive:
    for item in archive.infolist():
        if not (target/item.filename).resolve().is_relative_to(target): raise SystemExit('Unsafe foundation archive entry')
    archive.extractall(target)
PY
    printf '%s\n' "$archive_sha" > "$foundation/.prosperomc-archive-sha256"
fi
[[ $(cat "$foundation/.prosperomc-archive-sha256") == "$archive_sha" ]] || { echo 'Foundation provenance stamp mismatch' >&2; exit 2; }
# Its bootstrap pins SDK0.42 digest8cfbc7... and zlib1.3.2 digestbb329a...
bash "$foundation/tools/setup-native-dependencies.sh"
if [[ ! -f $foundation/runtime/libc.prx || ! -x $foundation/build/runtime-shim/ps5-native-tool ]]; then
    bash "$foundation/tools/rebuild-libc.sh"
fi
(cd "$foundation/runtime" && sha256sum --check --strict libc.prx.sha256)
echo "Pinned PS5 foundation ready: $foundation"
