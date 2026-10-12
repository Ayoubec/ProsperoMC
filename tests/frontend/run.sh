#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
UPSTREAM=vendor/prospero-win/src
if [ ! -f "$UPSTREAM/pw_present.h" ]; then
  UPSTREAM=.deps/source/prospero-win-b510eb3db8709bb251d3da3c56850e96e057f489/src
fi
mkdir -p artifacts/frontend
mkdir -p artifacts/frontend/icons
python3 scripts/build-webp-host.py
cp assets/generated/prosperomc-icon.png artifacts/frontend/icons/custom.png
cp tests/fixtures/icon.webp artifacts/frontend/icons/fo.webp
cc -std=c99 -Wall -Wextra -Werror -O2 -I app/native -I "$UPSTREAM" app/native/pm_frontend.c vendor/qrcodegen/qrcodegen.c tests/frontend/navigation.c -o artifacts/frontend/navigation
artifacts/frontend/navigation
cc -std=c99 -Wall -Wextra -Werror -O2 -I app/native -I "$UPSTREAM" tests/frontend/rounded-spans.c vendor/qrcodegen/qrcodegen.c -o artifacts/frontend/rounded-spans
artifacts/frontend/rounded-spans
cc -std=c99 -Wall -Wextra -Werror -O2 -I app/native -I "$UPSTREAM" -I .deps/native/libwebp/libwebp-1.6.0 app/native/pm_frontend.c app/native/pm_icons.c vendor/qrcodegen/qrcodegen.c app/preview/render.c build/tests/webp/libwebpdecoder.a -lm -o artifacts/frontend/render
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
artifacts/frontend/render artifacts/frontend/restored-modrinth.ppm 2 --restored-modrinth
artifacts/frontend/render artifacts/frontend/restored-curseforge.ppm 2 --restored-curse
artifacts/frontend/render artifacts/frontend/content-resources.ppm 3 --resources
artifacts/frontend/render artifacts/frontend/content-shaders.ppm 3 --shaders
artifacts/frontend/render artifacts/frontend/theme-amethyst.ppm 4 --theme
artifacts/frontend/render artifacts/frontend/motion.ppm 0 --motion
artifacts/frontend/render artifacts/frontend/home-fo.ppm 0 --fo
artifacts/frontend/render artifacts/frontend/rename.ppm 1 --rename
for palette in grass ocean diamond amethyst redstone gold; do
  artifacts/frontend/render "artifacts/frontend/settings-$palette.ppm" 4 "--palette=$palette"
done
