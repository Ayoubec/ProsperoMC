param([string]$Distribution = 'Ubuntu')
$ErrorActionPreference = 'Stop'
$projectPath = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$wslPath = '/mnt/' + $projectPath.Substring(0,1).ToLowerInvariant() + $projectPath.Substring(2).Replace('\','/')
& wsl -d $Distribution -- bash ($wslPath + '/scripts/build-ps5.sh')
if ($LASTEXITCODE -ne 0) { throw "PS5 native build failed ($LASTEXITCODE)" }
