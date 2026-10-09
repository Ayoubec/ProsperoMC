#!/usr/bin/env bash
# The Minecraft-specific native title is built from the root wrapper.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)
exec bash "$root/scripts/build-ps5.sh" "$@"
