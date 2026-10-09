#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Initialize a fresh Wine prefix on Linux. For a release-matched prefix set
# PM_HOST_WINE to the host build of Wine commit 490f6d... and PM_WINE_COMMIT.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
out=${1:-$root/.deps/prefix-template}
wine=${PM_HOST_WINE:-wine}
wine_path=$(command -v "$wine")
server=${PM_HOST_WINESERVER:-"$(dirname -- "$wine_path")/wineserver"}
if [[ ! -x $server && -z ${PM_HOST_WINE:-} && -x /usr/lib/x86_64-linux-gnu/wine/wineserver ]]; then
    server=/usr/lib/x86_64-linux-gnu/wine/wineserver
fi
[[ -x $server ]] || { echo "Matching host wineserver missing: $server; set PM_HOST_WINESERVER" >&2; exit 2; }
prefix=$(mktemp -d /tmp/prosperomc-wine-prefix.XXXXXX)
trap 'rm -rf -- "$prefix"' EXIT
version=$("$wine" --version)
WINEPREFIX="$prefix" WINEARCH=win64 WINEDLLOVERRIDES=mshtml,mscoree=d WINEDEBUG=-all USER=prospero "$wine" wineboot --init
# wineboot returns while services still hold the registry in memory. Close only
# this freshly-created prefix's server, then wait for registry flush completion.
WINEPREFIX="$prefix" "$server" -k
WINEPREFIX="$prefix" "$server" -w
for registry in system.reg user.reg userdef.reg; do
    [[ -s $prefix/$registry ]] || { echo "Wine prefix registry not flushed: $registry" >&2; exit 2; }
done
mkdir -p "$out"
python3 - "$prefix" "$out" "$version" "${PM_WINE_COMMIT:-}" <<'PY'
import json, os, pathlib, shutil, sys
source, output = map(pathlib.Path, sys.argv[1:3])
for name in ('system.reg', 'user.reg', 'userdef.reg'):
    if not (source / name).is_file() or not (source / name).stat().st_size:
        raise SystemExit('Prefix registry is missing: ' + name)
if output.name != 'prefix-template' or output.exists() and any(output.iterdir()):
    raise SystemExit('Output must be an empty prefix-template directory')
for directory, dirs, files in os.walk(source, followlinks=False):
    base = pathlib.Path(directory)
    target = output / base.relative_to(source)
    target.mkdir(parents=True, exist_ok=True)
    for name in dirs[:]:
        if base == source / 'drive_c' and name not in ('windows', 'users'):
            dirs.remove(name)
            continue
        if base == source / 'drive_c/windows' and name.lower() in ('system32', 'syswow64'):
            (target / name).mkdir(exist_ok=True)
            dirs.remove(name)
            continue
        if (base / name).is_symlink():
            dirs.remove(name)
            if ':' not in name:
                (target / name).mkdir(exist_ok=True)
    for name in files:
        candidate = base / name
        if not candidate.is_symlink():
            shutil.copy2(candidate, target / name)
(output / 'prosperomc-prefix.json').write_text(json.dumps({'wineVersion': sys.argv[3], 'wineCommit': sys.argv[4] or None, 'fresh': True, 'consoleValidated': False}, indent=2) + '\n')
PY
echo "Initialized offline prefix: $out ($version). Console compatibility still requires validation."
