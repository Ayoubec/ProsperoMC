#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
UPSTREAM=vendor/prospero-win/src
if [ ! -f "$UPSTREAM/pw_present.h" ]; then
  UPSTREAM=.deps/source/prospero-win-b510eb3db8709bb251d3da3c56850e96e057f489/src
fi
mkdir -p artifacts/frontend
cc -std=c99 -Wall -Wextra -Werror -O2 -I app/native -I "$UPSTREAM" app/native/pm_frontend.c vendor/qrcodegen/qrcodegen.c tests/frontend/navigation.c -o artifacts/frontend/navigation
artifacts/frontend/navigation
cc -std=c99 -Wall -Wextra -Werror -O2 -I app/native -I "$UPSTREAM" app/native/pm_frontend.c vendor/qrcodegen/qrcodegen.c app/preview/render.c -o artifacts/frontend/render
for screen in 0 1 2 3 4 5; do
  artifacts/frontend/render "artifacts/frontend/screen-$screen.ppm" "$screen"
done
artifacts/frontend/render artifacts/frontend/empty.ppm 0 --empty
