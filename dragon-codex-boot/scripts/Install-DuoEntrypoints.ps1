[CmdletBinding()]
param([switch]$Verify, [switch]$Repair, [string[]]$ShortcutPaths, [string]$StateRoot)
$ErrorActionPreference='Stop'
$entry=Join-Path $PSScriptRoot 'Start-CustomCodex.ps1'
$ps=Join-Path $env:WINDIR 'System32/WindowsPowerShell/v1.0/powershell.exe'
$clientIcon=Join-Path $env:WINDIR 'explorer.exe'
try {
    $store=Get-AppxPackage -Name OpenAI.Codex -ErrorAction Stop | Select-Object -First 1
    if($store) { $clientIcon=Join-Path $store.InstallLocation 'app/ChatGPT.exe' }
}catch{}
$shortcutArguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$entry+'"'
if (!$StateRoot) { $StateRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../build/DragonCodexBoot/.integration/duo')) }
$stateFile=Join-Path $stateRoot 'shortcuts.json'
$shell=New-Object -ComObject WScript.Shell
if ($Verify) {
    $state=Get-Content $stateFile -Raw | ConvertFrom-Json
    foreach($item in $state) {
        $link=$shell.CreateShortcut($item.path)
        if(!(Test-Path -LiteralPath $item.path) -or $link.TargetPath -ne $ps -or $link.Arguments -ne $shortcutArguments) { throw ('Shortcut differs: '+$item.path) }
    }
    [pscustomobject]@{status='verified';count=@($state).Count;entry=$entry} | ConvertTo-Json
    return
}
if(Test-Path $stateFile) {
    if (!$Repair) { throw 'Shortcuts already installed; use -Verify or -Repair.' }
    $records=Get-Content $stateFile -Raw | ConvertFrom-Json
    foreach($record in $records) {
        if((Get-FileHash -LiteralPath $record.backup).Hash -ne $record.sha256) { throw 'Original shortcut backup differs.' }
        $link=$shell.CreateShortcut($record.path)
        if((Test-Path -LiteralPath $record.path) -and !(($link.TargetPath -eq $ps -and $link.Arguments -eq $shortcutArguments) -or $link.Arguments -match 'OpenAI\.Codex_2p2nqsd0c76g0!App')) { throw ('Changed shortcut preserved: '+$record.path) }
        $link.TargetPath=$ps; $link.Arguments=$shortcutArguments; $link.WorkingDirectory=$PSScriptRoot; $link.WindowStyle=7
        $link.IconLocation=$clientIcon+',0'
        $link.Description='Codex with internal Bamboo Duo wallpaper'
        $link.Save()
    }
    & $PSCommandPath -Verify -StateRoot $StateRoot
    return
}
New-Item -ItemType Directory -Path $stateRoot -Force | Out-Null
$paths=@((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Codex.lnk'))
$programs=[Environment]::GetFolderPath('Programs')
foreach($name in @('Codex.lnk','ChatGPT.lnk')) {
    $path=Join-Path $programs $name
    if(Test-Path -LiteralPath $path) { $paths+=$path }
}
$taskbar=Join-Path $env:APPDATA 'Microsoft/Internet Explorer/Quick Launch/User Pinned/TaskBar'
foreach($file in @(Get-ChildItem -LiteralPath $taskbar -Filter '*.lnk' -ErrorAction SilentlyContinue)) {
    $link=$shell.CreateShortcut($file.FullName)
    if($link.Arguments -match 'OpenAI\.Codex_2p2nqsd0c76g0!App' -or $link.TargetPath -match 'WindowsApps\\OpenAI\.Codex_.*\\ChatGPT.exe$') { $paths+=$file.FullName }
}
if($ShortcutPaths) { $paths=$ShortcutPaths }
$records=@()
foreach($path in $paths | Select-Object -Unique) {
    if(!(Test-Path -LiteralPath $path)) { continue }
    $link=$shell.CreateShortcut($path)
    if($link.Arguments -notmatch 'OpenAI\.Codex_2p2nqsd0c76g0!App' -and $link.TargetPath -notmatch 'WindowsApps\\OpenAI\.Codex_.*\\ChatGPT.exe$') { throw ('Unrecognized shortcut preserved: '+$path) }
    $backup=Join-Path $stateRoot ([Guid]::NewGuid().ToString('N')+'.lnk')
    Copy-Item -LiteralPath $path -Destination $backup
    $records+=@{path=$path;backup=$backup;sha256=(Get-FileHash $backup).Hash}
}
# Save the original shortcuts before the first mutation.
$records | ConvertTo-Json -Depth 4 | Set-Content $stateFile
foreach($record in $records) {
    $link=$shell.CreateShortcut($record.path)
    $link.TargetPath=$ps
    $link.Arguments=$shortcutArguments
    $link.WorkingDirectory=$PSScriptRoot
    $link.WindowStyle=7
    $link.IconLocation=$clientIcon+',0'
    $link.Description='Codex with internal Bamboo Duo wallpaper'
    $link.Save()
}
& $PSCommandPath -Verify -StateRoot $StateRoot
