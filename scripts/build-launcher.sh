#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
jdk=${JDK_HOME:-}
out=${1:-"$repo/artifacts/launcher"}
mkdir -p "$out/classes"
find "$repo/launcher/src" -name '*.java' > "$out/sources.txt"
if [ -n "$jdk" ]; then javac="$jdk/bin/javac"; jar="$jdk/bin/jar"; else javac=javac; jar=jar; fi
"$javac" --release 8 -encoding UTF-8 -d "$out/classes" @"$out/sources.txt"
"$jar" "-J-Djava.io.tmpdir=$out" --create --file "$out/prosperomc-launcher.jar" --main-class org.prosperomc.Main -C "$out/classes" .
"$jar" "-J-Djava.io.tmpdir=$out" --update --file "$out/prosperomc-launcher.jar" -C "$repo/launcher/resources" .
echo "$out/prosperomc-launcher.jar"
