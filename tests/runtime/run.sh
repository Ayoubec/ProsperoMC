#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
mkdir -p "$root/build/tests"
cc=${HOST_CC:-clang-18}
"$cc" -std=c11 -O2 -Wall -Wextra -Werror -I"$root/vendor/prospero-win/src" -I"$root/vendor/prospero-win/native" -I"$root/vendor/prospero-win/include" -I"$root/app/native" \
    "$root/tests/runtime/test_bridge.c" "$root/vendor/prospero-win/native/pm_bridge.c" \
    "$root/vendor/prospero-win/src/pw_wine_launch.c" "$root/vendor/prospero-win/src/pw_app_profile.c" "$root/vendor/prospero-win/src/pw_game_profile.c" \
    -o "$root/build/tests/runtime-bridge"
"$root/build/tests/runtime-bridge"
"$cc" -std=c11 -O2 -Wall -Wextra -Werror -I"$root/vendor/prospero-win/native" \
    "$root/tests/runtime/test_file_limit.c" -o "$root/build/tests/runtime-file-limit"
"$root/build/tests/runtime-file-limit"
python3 "$root/tests/runtime/test_icons.py"
python3 "$root/tests/runtime/test_launcher_output.py"
python3 "$root/tests/runtime/test_wine_fd_report.py"
python3 "$root/tests/runtime/test_stage.py"
