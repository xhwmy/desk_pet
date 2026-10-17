[CmdletBinding()]
param([switch]$Inspect, [switch]$Worker, [switch]$Restart, [switch]$LaunchOnly)
$ErrorActionPreference = 'Stop'
$package = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../build/DragonCodexBoot'))
$logDir = Join-Path $package 'logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
if (!$Inspect -and !$Worker) { @{status='starting';pid=$PID;at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $logDir 'custom-start.json') }
trap {
    @{status='failed';error=$_.Exception.Message;detail=$_.ToString();stack=$_.ScriptStackTrace;at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $logDir 'custom-start.json') -Encoding UTF8
    break
}
$skill = Join-Path $env:USERPROFILE '.codex/skills/codex-skin-studio'
$node = (Get-Command node -ErrorAction Stop).Source
$windowsPowerShell = Join-Path $env:WINDIR 'System32/WindowsPowerShell/v1.0/powershell.exe'
. (Join-Path $PSScriptRoot 'StoreClient.ps1')
# Resolve the Store package on every launch so application updates are supported.
$store = Get-AppxPackage -Name OpenAI.Codex | Select-Object -First 1
if (!$store) { throw 'The installed Codex Store package was not found.' }
$app = Join-Path $store.InstallLocation 'app/ChatGPT.exe'
if (!(Test-Path -LiteralPath $app -PathType Leaf)) { throw 'Codex executable was not found.' }
$env:Path = (Split-Path -Parent $app) + ';' + $env:Path
$theme = (Get-Content (Join-Path $package 'wallpaper/active-theme.json') -Raw | ConvertFrom-Json).themeDir
if (!(Test-Path -LiteralPath (Join-Path $theme 'theme.json'))) { throw 'Selected wallpaper theme is missing.' }
$running = @(Get-StoreClientProcesses | Where-Object {
    $_.CommandLine -notmatch '--type='
})
function Test-Cdp {
    try { $null = Invoke-RestMethod 'http://127.0.0.1:9341/json/version' -TimeoutSec 1; return $true } catch { return $false }
}
if ($Inspect) {
    [pscustomobject]@{Application=$app;Theme=$theme;Running=($running.Count -gt 0);Cdp=(Test-Cdp);Package=$package} | ConvertTo-Json
    return
}
if ($Worker) {
    & $node (Join-Path $PSScriptRoot 'skin-worker.mjs') *> (Join-Path $logDir 'skin-worker.log')
    exit $LASTEXITCODE
}
$created = $false
$mutex = New-Object Threading.Mutex($true, 'Local\BambooDuoEntry', [ref]$created)
if (!$created) { $mutex.Dispose(); return }
try {
    if ($Restart -and $running.Count) {
        @{status='restarting';pid=$PID;at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $logDir 'custom-start.json')
        # Restart only this Store application's UI, preserving unrelated Codex CLI processes.
        foreach($item in $running) { $null=(Get-Process -Id $item.ProcessId -ErrorAction SilentlyContinue).CloseMainWindow() }
        Start-Sleep -Seconds 3
        $remaining=@(Get-StoreClientProcesses)
        foreach($item in $remaining) { Stop-Process -Id $item.ProcessId -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 1
        $store = Get-AppxPackage -Name OpenAI.Codex | Select-Object -First 1
        if(!$store) { throw 'Codex package registration is unavailable after restart.' }
        $app = Join-Path $store.InstallLocation 'app/ChatGPT.exe'
        $env:Path = (Split-Path -Parent $app) + ';' + $env:Path
        $running=@()
    }
    $cdp = Test-Cdp
    if ($running.Count -gt 0 -and !$cdp) {
        # Keep the user's current session alive. The next cold launch applies the wallpaper.
        @{status='deferred';reason='Existing session has no CDP; no restart requested';at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $logDir 'custom-start.json')
        return
    }
    if (!$running.Count) {
        @{status='launching-with-wallpaper-interface';pid=$PID;at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $logDir 'custom-start.json')
        # Launch the real client directly; only its internal wallpaper is customized.
        $null=Start-StoreClient -Aumid ($store.PackageFamilyName+'!App')
    }
    $ready = $false
    for ($index=0; $index -lt 80; $index++) {
        if (Test-Cdp) { $ready=$true; break }
        Start-Sleep -Milliseconds 250
    }
    if (!$ready) { throw 'Codex did not open its loopback wallpaper interface. The client was left running.' }
    if ($LaunchOnly) { Write-Output '{"status":"launched"}'; return }
    # A CDP page can exist before the main application shell mounts.
    $mainReady=$false
    for($attempt=0;$attempt -lt 80;$attempt++) {
        & $node (Join-Path $PSScriptRoot 'Wait-SkinSurface.mjs') 2>$null
        if($LASTEXITCODE -eq 0) { $mainReady=$true; break }
        Start-Sleep -Milliseconds 500
    }
    if(!$mainReady) { throw 'Codex opened its wallpaper interface but the main surface was not ready.' }
    # The supported runner reuses CDP here and therefore never closes this session.
    $previousPreference=$ErrorActionPreference
    $ErrorActionPreference='Continue'
    & $windowsPowerShell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $skill 'scripts/windows/apply.ps1') -ThemeDir $theme -Persist *> (Join-Path $logDir 'wallpaper-apply.log')
    $applyExitCode=$LASTEXITCODE
    $ErrorActionPreference=$previousPreference
    if ($applyExitCode -ne 0) { throw 'Wallpaper application failed; see wallpaper-apply.log.' }
    & $node (Join-Path $PSScriptRoot 'client-surface-adapter.mjs')
    if($LASTEXITCODE -ne 0) { throw 'Client surface adaptation failed.' }
    # Preserve the standard persistence worker, but discover the current Store path at logon.
    $arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $PSCommandPath + '" -Worker'
    $action = New-ScheduledTaskAction -Execute $windowsPowerShell -Argument $arguments -WorkingDirectory $PSScriptRoot
    Set-ScheduledTask -TaskName 'CodexSkinStudio' -Action $action | Out-Null
    Start-ScheduledTask -TaskName 'CodexSkinStudio'
    $status = & $node (Join-Path $PSScriptRoot 'Inspect-Skin.mjs')
    $status | Set-Content (Join-Path $logDir 'wallpaper-status.json')
    if (($status | ConvertFrom-Json).status -ne 'active') { throw 'Wallpaper was not verified active.' }
    $selectionPath = Join-Path $package 'wallpaper/selection.json'
    $selection = Get-Content $selectionPath -Raw | ConvertFrom-Json
    $selection.applied=$true
    $selection | ConvertTo-Json | Set-Content $selectionPath
    @{status='active';themeId='bamboo-duo';at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $logDir 'custom-start.json')
} catch {
    @{status='failed';error=$_.Exception.Message;detail=$_.ToString();stack=$_.ScriptStackTrace;at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $logDir 'custom-start.json') -Encoding UTF8
    throw
} finally {
    if(!$LaunchOnly) {
        # Keep recovery alive even if a client update invalidates this launch attempt.
        try {
            $workerArguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$PSCommandPath+'" -Worker'
            $workerAction=New-ScheduledTaskAction -Execute $windowsPowerShell -Argument $workerArguments -WorkingDirectory $PSScriptRoot
            Set-ScheduledTask -TaskName 'CodexSkinStudio' -Action $workerAction | Out-Null
            Start-ScheduledTask -TaskName 'CodexSkinStudio'
        }catch{ Write-Warning ('Wallpaper recovery task could not start: '+$_.Exception.Message) }
    }
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
