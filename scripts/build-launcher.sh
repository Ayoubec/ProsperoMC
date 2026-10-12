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
printf 'Premain-Class: org.prosperomc.ZipFsAgent\nCan-Retransform-Classes: true\n\n' > "$out/agent-manifest.mf"
"$jar" "-J-Djava.io.tmpdir=$out" --create --file "$out/prosperomc-launcher.jar" --manifest "$out/agent-manifest.mf" --main-class org.prosperomc.Main -C "$classes" .
"$jar" "-J-Djava.io.tmpdir=$out" --update --file "$out/prosperomc-launcher.jar" -C "$repo/launcher/resources" .
mkdir -p "$out/bootstrap-classes"
find "$repo/launcher/bootstrap" -name '*.java' > "$out/bootstrap-sources.txt"
"$javac" --release 8 -encoding UTF-8 -d "$out/bootstrap-classes" @"$out/bootstrap-sources.txt"
"$jar" "-J-Djava.io.tmpdir=$out" --create --file "$out/prosperomc-zipfs.jar" -C "$out/bootstrap-classes" .
echo "$out/prosperomc-launcher.jar"
