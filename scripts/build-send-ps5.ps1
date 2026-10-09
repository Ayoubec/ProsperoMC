param(
    [ValidateSet('build','send','build-send','help')][string]$Action = 'help',
    [string]$HostAddress = '192.168.1.111',
    [ValidateRange(1,65535)][int]$Port = 2121,
    [string]$Python = '',
    [string]$Distribution = 'Ubuntu'
)
$ErrorActionPreference = 'Stop'
$projectPath = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ($Action -eq 'help') {
    Write-Host 'ProsperoMC.cmd build                         Build Java + native app'
    Write-Host 'ProsperoMC.cmd send                          Send current app update'
    Write-Host 'ProsperoMC.cmd build-send                    Build then send'
    Write-Host 'ProsperoMC.cmd build-send 192.168.1.111 2121   Set FTP address/port'
    Write-Host 'Close Minecraft and ProsperoMC before sending. Start PS5 FTP.'
    Write-Host 'Updates preserve console worlds, settings, mods, Java and the Wine prefix.'
    Write-Host 'The build retains staged Wine/OpenGL modules; engine source rebuilds use the documented graphics scripts.'
    exit 0
}
if (!$Python) {
    $candidates = @(
        (Join-Path $projectPath '.deps/python/python.exe'),
        (Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
    )
    $Python = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (!$Python) {
        $command = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notmatch 'WindowsApps') { $Python = $command.Source }
    }
    if (!$Python) { throw 'Python 3 is required. Run this script with -Python C:\path\python.exe.' }
}
Push-Location -LiteralPath $projectPath
try {
    if ($Action -in @('build','build-send')) {
        Write-Host 'Building Java launcher...'
        & (Join-Path $PSScriptRoot 'build-launcher.ps1')
        Write-Host 'Building native PS5 app...'
        & (Join-Path $PSScriptRoot 'build-ps5.ps1') -Distribution $Distribution
        & $Python (Join-Path $PSScriptRoot 'stage-app-update.py')
        if ($LASTEXITCODE -ne 0) { throw 'App update staging failed.' }
        # The PS5 FTP server exposes signed executables as ELF. Regenerate the
        # executable comparison view for this exact build before publishing.
        $wslProject = '/mnt/' + $projectPath.Substring(0,1).ToLowerInvariant() + $projectPath.Substring(2).Replace('\','/')
        $nativeTool = $wslProject + '/.deps/source/ps5-native-app-boilerplate-9c0b994a048521af6fb84c73ded364504fe250e9/build/runtime-shim/ps5-native-tool'
        & wsl -d $Distribution -- python3 ($wslProject + '/scripts/build-ftp-views.py') --tool $nativeTool --title ($wslProject + '/dist/PPSA99888') --file ($wslProject + '/dist/PPSA99888/eboot.bin')
        if ($LASTEXITCODE -ne 0) { throw 'Executable FTP verification preparation failed.' }
        Write-Host 'Build ready: dist\PPSA99888'
    }
    if ($Action -in @('send','build-send')) {
        Write-Host "Sending app update to ${HostAddress}:$Port. Minecraft and ProsperoMC must be closed."
        & $Python (Join-Path $PSScriptRoot 'deploy-ps5-patch.py') --host $HostAddress --port $Port --app-update
        if ($LASTEXITCODE -ne 0) { throw 'PS5 update failed; see the error above.' }
        Write-Host 'Verified app update complete. Reopen ProsperoMC from your loader.'
    }
} finally { Pop-Location }
