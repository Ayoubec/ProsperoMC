param([switch]$Native, [string]$Jdk = '')
$ErrorActionPreference = 'Stop'
$launcherBuild = Join-Path $PSScriptRoot 'scripts/build-launcher.ps1'
if ($Jdk) { & $launcherBuild -Jdk $Jdk } else { & $launcherBuild }
if ($Native) { & (Join-Path $PSScriptRoot 'scripts/build-ps5.ps1') }
