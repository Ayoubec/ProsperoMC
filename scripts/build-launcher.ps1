param([string]$Jdk = "", [string]$Output = "")
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
if (!$Jdk) { $Jdk = Join-Path $repo ".deps/host-jdk/jdk-21.0.8+9" }
if (!$Output) { $Output = Join-Path $repo "artifacts/launcher" }
$javac = Join-Path $Jdk "bin/javac.exe"
$jar = Join-Path $Jdk "bin/jar.exe"
if (!(Test-Path -LiteralPath $javac)) { throw "JDK javac missing: $javac" }
$classes = Join-Path $Output "plain-classes"
New-Item -ItemType Directory -Force -Path $classes | Out-Null
$sources = @(Get-ChildItem -LiteralPath (Join-Path $repo "launcher/src") -Recurse -Filter "*.java" | ForEach-Object { $_.FullName })
& $javac --release 8 -encoding UTF-8 -d $classes @sources
if ($LASTEXITCODE -ne 0) { throw "Java compilation failed" }
$modernSources = @(Get-ChildItem -LiteralPath (Join-Path $repo "launcher/src18") -Recurse -Filter "*.java" | ForEach-Object { $_.FullName })
& $javac --release 18 -encoding UTF-8 -cp $classes -d $classes @modernSources
if ($LASTEXITCODE -ne 0) { throw "Modern DNS provider compilation failed" }
$archive = Join-Path $Output "prosperomc-launcher.jar"
$manifest = Join-Path $Output "agent-manifest.mf"
Set-Content -LiteralPath $manifest -Value "Premain-Class: org.prosperomc.ZipFsAgent`nCan-Retransform-Classes: true`n" -Encoding ascii
& $jar "-J-Djava.io.tmpdir=$Output" --create --file $archive --manifest $manifest --main-class org.prosperomc.Main -C $classes .
if ($LASTEXITCODE -ne 0) { throw "JAR creation failed" }
& $jar "-J-Djava.io.tmpdir=$Output" --update --file $archive -C (Join-Path $repo "launcher/resources") .
if ($LASTEXITCODE -ne 0) { throw "Launcher resource staging failed" }
$bootstrapClasses = Join-Path $Output "bootstrap-classes"
New-Item -ItemType Directory -Force -Path $bootstrapClasses | Out-Null
$bootstrapSources = @(Get-ChildItem -LiteralPath (Join-Path $repo "launcher/bootstrap") -Recurse -Filter "*.java" | ForEach-Object { $_.FullName })
& $javac --release 8 -encoding UTF-8 -d $bootstrapClasses @bootstrapSources
if ($LASTEXITCODE -ne 0) { throw "ZIP channel compilation failed" }
& $jar "-J-Djava.io.tmpdir=$Output" --create --file (Join-Path $Output "prosperomc-zipfs.jar") -C $bootstrapClasses .
if ($LASTEXITCODE -ne 0) { throw "ZIP channel JAR creation failed" }
Write-Output $archive
