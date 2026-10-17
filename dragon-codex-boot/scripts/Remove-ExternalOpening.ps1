$ErrorActionPreference='Stop'
$repoRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$package=Join-Path $repoRoot 'build/DragonCodexBoot'
$workerEntry=Join-Path $PSScriptRoot 'Start-CustomCodex.ps1'
$workerModule=Join-Path $PSScriptRoot 'skin-worker.mjs'
$ps=Join-Path $env:WINDIR 'System32/WindowsPowerShell/v1.0/powershell.exe'

# Stop only this wallpaper worker while replacing its old opening integration.
Stop-ScheduledTask -TaskName 'CodexSkinStudio' -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object {
    $_.CommandLine -and $_.CommandLine.Contains($workerModule)
} | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
foreach($name in @('BambooDuoApplyOnce','BambooDuoReopenTest')) {
    $task=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if($task -and @($task.Actions | Where-Object {$_.Arguments -and $_.Arguments.Contains($repoRoot)}).Count) {
        Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
    }
}

# Delete deployed opening players and their manual entrypoints, keeping artwork and source.
$deployments=@($package,(Join-Path $repoRoot '.local/Bamboo-Duo-BC'),(Join-Path $repoRoot '.local/Bamboo-Duo-preview'))
$removed=@()
foreach($deployment in $deployments) {
    $resolved=[IO.Path]::GetFullPath($deployment)
    if(!$resolved.StartsWith($repoRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Opening path escaped the project.' }
    $player=Join-Path $resolved 'DragonCodexBoot.exe'
    Get-CimInstance Win32_Process -Filter "Name='DragonCodexBoot.exe'" | Where-Object {$_.ExecutablePath -eq $player} | ForEach-Object {
        Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
    }
    foreach($name in @('DragonCodexBoot.exe','Launch-Duo.cmd','Preview-Duo.cmd')) {
        $path=Join-Path $resolved $name
        if(Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force; $removed+=$path }
    }
}
$gate=[IO.Path]::GetFullPath((Join-Path $package '.startup'))
if(!$gate.StartsWith($repoRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Gate path escaped the project.' }
if(Test-Path -LiteralPath $gate) { Remove-Item -LiteralPath $gate -Recurse -Force }

& (Join-Path $PSScriptRoot 'Install-DuoEntrypoints.ps1') -Repair
$arguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$workerEntry+'" -Worker'
$action=New-ScheduledTaskAction -Execute $ps -Argument $arguments -WorkingDirectory $PSScriptRoot
Set-ScheduledTask -TaskName 'CodexSkinStudio' -Action $action | Out-Null
Start-ScheduledTask -TaskName 'CodexSkinStudio'
[pscustomobject]@{status='external-opening-removed';removed=$removed;internalWallpaper='preserved'} | ConvertTo-Json
