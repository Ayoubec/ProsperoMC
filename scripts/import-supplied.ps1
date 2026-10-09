param(
    [string]$Source = 'C:\Users\Admin\Desktop\minecraft ps5',
    [string]$DataRoot = '',
    [string]$Version = '1.12.2',
    [string]$InstanceId = 'minecraft-1.12.2'
)
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
if (!$DataRoot) { $DataRoot = Join-Path $projectPath 'game-data/prosperomc' }
$javaSource = Join-Path $Source 'java8'
$gameSource = Join-Path $Source '.minecraft'
$launcher = Join-Path $projectPath 'artifacts/launcher/prosperomc-launcher.jar'
foreach ($requiredPath in @((Join-Path $javaSource 'bin/java.exe'), $launcher)) {
    if (!(Test-Path -LiteralPath $requiredPath)) { throw "Missing input: $requiredPath" }
}
if (!(Test-Path -LiteralPath $gameSource -PathType Container)) { throw "Missing .minecraft folder: $gameSource" }
New-Item -ItemType Directory -Force -Path (Join-Path $DataRoot 'runtimes'),(Join-Path $DataRoot 'launcher') | Out-Null
if (!(Test-Path -LiteralPath (Join-Path $DataRoot 'runtimes/java8/bin/java.exe'))) {
    Copy-Item -LiteralPath $javaSource -Destination (Join-Path $DataRoot 'runtimes/java8') -Recurse
}
Copy-Item -LiteralPath $launcher -Destination (Join-Path $DataRoot 'launcher/prosperomc-launcher.jar') -Force
$javaExecutable = Join-Path $DataRoot 'runtimes/java8/bin/java.exe'
$requestPath = Join-Path $projectPath 'artifacts/local-import.properties'
if (Test-Path -LiteralPath (Join-Path $DataRoot "instances/$InstanceId/instance.properties")) {
    @("command=install", "id=$InstanceId") | Set-Content -LiteralPath $requestPath -Encoding utf8
} else {
    @("command=import", "id=$InstanceId", "name=Minecraft $Version", "version=$Version", "source=$gameSource") |
        Set-Content -LiteralPath $requestPath -Encoding utf8
}
& $javaExecutable -jar $launcher --root $DataRoot --request $requestPath
if ($LASTEXITCODE -ne 0) { throw 'Local Minecraft import/install failed; see response.properties' }
Get-Content -LiteralPath (Join-Path $DataRoot 'response.properties')
