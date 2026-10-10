#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
jdk=${JDK_HOME:-}
out=${1:-"$repo/artifacts/launcher"}
classes="$out/plain-classes"
mkdir -p "$classes"
find "$repo/launcher/src" -name '*.java' > "$out/sources.txt"
if [ -n "$jdk" ]; then javac="$jdk/bin/javac"; jar="$jdk/bin/jar"; else javac=javac; jar=jar; fi
"$javac" --release 8 -encoding UTF-8 -d "$classes" @"$out/sources.txt"
find "$repo/launcher/src18" -name '*.java' > "$out/modern-sources.txt"
"$javac" --release 18 -encoding UTF-8 -cp "$classes" -d "$classes" @"$out/modern-sources.txt"
"$jar" "-J-Djava.io.tmpdir=$out" --create --file "$out/prosperomc-launcher.jar" --main-class org.prosperomc.Main -C "$classes" .
"$jar" "-J-Djava.io.tmpdir=$out" --update --file "$out/prosperomc-launcher.jar" -C "$repo/launcher/resources" .
echo "$out/prosperomc-launcher.jar"
