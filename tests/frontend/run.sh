#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
UPSTREAM=vendor/prospero-win/src
if [ ! -f "$UPSTREAM/pw_present.h" ]; then
  UPSTREAM=.deps/source/prospero-win-b510eb3db8709bb251d3da3c56850e96e057f489/src
fi
mkdir -p artifacts/frontend
mkdir -p artifacts/frontend/icons
cp assets/generated/prosperomc-icon.png artifacts/frontend/icons/custom.png
cc -std=c99 -Wall -Wextra -Werror -O2 -I app/native -I "$UPSTREAM" app/native/pm_frontend.c vendor/qrcodegen/qrcodegen.c tests/frontend/navigation.c -o artifacts/frontend/navigation
artifacts/frontend/navigation
cc -std=c99 -Wall -Wextra -Werror -O2 -I app/native -I "$UPSTREAM" app/native/pm_frontend.c app/native/pm_icons.c vendor/qrcodegen/qrcodegen.c app/preview/render.c -lm -o artifacts/frontend/render
for screen in 0 1 2 3 4 5; do
  artifacts/frontend/render "artifacts/frontend/screen-$screen.ppm" "$screen"
done
artifacts/frontend/render artifacts/frontend/empty.ppm 0 --empty
artifacts/frontend/render artifacts/frontend/versions.ppm 2 --versions
artifacts/frontend/render artifacts/frontend/modrinth.ppm 2 --remote
artifacts/frontend/render artifacts/frontend/signin.ppm 5 --signin
artifacts/frontend/render artifacts/frontend/close.ppm 0 --close
artifacts/frontend/render artifacts/frontend/resolution.ppm 4 --resolution
artifacts/frontend/render artifacts/frontend/curseforge.ppm 2 --curse
artifacts/frontend/render artifacts/frontend/content-search.ppm 3 --content-search
artifacts/frontend/render artifacts/frontend/controller-input.ppm 4 --input
