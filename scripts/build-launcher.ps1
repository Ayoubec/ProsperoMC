param([string]$Jdk = "", [string]$Output = "")
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
if (!$Jdk) { $Jdk = Join-Path $repo ".deps/host-jdk/jdk-21.0.8+9" }
if (!$Output) { $Output = Join-Path $repo "artifacts/launcher" }
$javac = Join-Path $Jdk "bin/javac.exe"
$jar = Join-Path $Jdk "bin/jar.exe"
if (!(Test-Path -LiteralPath $javac)) { throw "JDK javac missing: $javac" }
$classes = Join-Path $Output "classes"
New-Item -ItemType Directory -Force -Path $classes | Out-Null
$sources = @(Get-ChildItem -LiteralPath (Join-Path $repo "launcher/src") -Recurse -Filter "*.java" | ForEach-Object { $_.FullName })
& $javac --release 8 -encoding UTF-8 -d $classes @sources
if ($LASTEXITCODE -ne 0) { throw "Java compilation failed" }
$modern = Join-Path $classes "META-INF/versions/18"
New-Item -ItemType Directory -Force -Path $modern | Out-Null
$modernSources = @(Get-ChildItem -LiteralPath (Join-Path $repo "launcher/src18") -Recurse -Filter "*.java" | ForEach-Object { $_.FullName })
& $javac --release 18 -encoding UTF-8 -cp $classes -d $modern @modernSources
if ($LASTEXITCODE -ne 0) { throw "Modern DNS provider compilation failed" }
$archive = Join-Path $Output "prosperomc-launcher.jar"
& $jar "-J-Djava.io.tmpdir=$Output" --create --file $archive --main-class org.prosperomc.Main -C $classes .
if ($LASTEXITCODE -ne 0) { throw "JAR creation failed" }
& $jar "-J-Djava.io.tmpdir=$Output" --update --file $archive -C (Join-Path $repo "launcher/resources") .
if ($LASTEXITCODE -ne 0) { throw "Launcher resource staging failed" }
& $jar "-J-Djava.io.tmpdir=$Output" --update --file $archive --manifest (Join-Path $repo "launcher/multi-release.mf")
if ($LASTEXITCODE -ne 0) { throw "Multi-release manifest staging failed" }
Write-Output $archive
