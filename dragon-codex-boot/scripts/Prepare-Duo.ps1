[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$LeftImage,
    [Parameter(Mandatory=$true)][string]$RightImage,
    [Parameter(Mandatory=$true)][string]$BackgroundImage,
    [string]$AppExecutable,
    [switch]$ResetAssets
)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$outputRoot = Join-Path $repoRoot 'build/DragonCodexBoot'
$node = (Get-Command node -ErrorAction Stop).Source
$explicitExecutable = $PSBoundParameters.ContainsKey('AppExecutable')
$images = [ordered]@{left=$LeftImage;right=$RightImage;background=$BackgroundImage}
foreach ($name in @($images.Keys)) {
    $path = (Resolve-Path -LiteralPath $images[$name]).Path
    if ([IO.Path]::GetExtension($path).ToLowerInvariant() -notin @('.png','.jpg','.jpeg')) { throw 'Scene images must be PNG or JPEG.' }
    & (Join-Path $PSScriptRoot 'Validate-SceneImage.ps1') -ImagePath $path
    if (!$?) { throw ('Image validation failed: ' + $name) }
    $images[$name] = $path
}
if ($explicitExecutable) {
    $AppExecutable = (Resolve-Path -LiteralPath $AppExecutable).Path
    if ([IO.Path]::GetExtension($AppExecutable) -ine '.exe') { throw 'AppExecutable must be an EXE.' }
}
& (Join-Path $PSScriptRoot 'build.ps1')
$configPath = Join-Path $outputRoot 'launcher.json'
$lockPath = Join-Path $outputRoot '.asset-import.lock'
$lock = [IO.File]::Open($lockPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
$stage = Join-Path $outputRoot ('.prepare-' + [Guid]::NewGuid().ToString('N'))
try {
    $original = [IO.File]::ReadAllBytes($configPath)
    $active = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $initialize = !$active.Scene -or $ResetAssets
    if ($initialize) {
        $active = Get-Content -LiteralPath (Join-Path $repoRoot 'config/duo.example.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if (!$AppExecutable) {
            $portable = Join-Path $env:LOCALAPPDATA 'Programs/Codex/ChatGPT.exe'
            if (Test-Path -LiteralPath $portable -PathType Leaf) { $AppExecutable = $portable }
        }
    }
    $changed = [bool]$initialize
    if ($AppExecutable -and ($initialize -or $explicitExecutable)) {
        $active | Add-Member -NotePropertyName AppExecutable -NotePropertyValue $AppExecutable -Force
        $active.ProcessPathContains = Split-Path -Parent $AppExecutable
        $active.ProcessNames = @('ChatGPT','Codex','LaunchCodex')
        $changed = $true
    }
    New-Item -ItemType Directory -Path $stage -Force | Out-Null
    $stageConfig = Join-Path $stage 'launcher.json'
    [IO.File]::WriteAllText($stageConfig, ($active | ConvertTo-Json -Depth 12), (New-Object Text.UTF8Encoding $false))
    $fields = @{ left='LeftCharacter';right='RightCharacter';background='Background' }
    foreach ($name in @($images.Keys)) {
        $current = $active.Scene.($fields[$name])
        $selectedExists = $current -and (Test-Path -LiteralPath (Join-Path $outputRoot $current) -PathType Leaf)
        if ($ResetAssets -or !$selectedExists) {
            & $node (Join-Path $PSScriptRoot 'duo-assets.mjs') import --root $stage --slot $name --file $images[$name]
            if ($LASTEXITCODE -ne 0) { throw ('Asset import failed: ' + $name) }
            $changed = $true
        }
    }
    if ($changed) {
        # Assets are content-addressed. Publish them before committing config.
        $stagedAssets = Join-Path $stage 'assets/duo'
        if (Test-Path -LiteralPath $stagedAssets) {
            $targetAssets = Join-Path $outputRoot 'assets/duo'
            New-Item -ItemType Directory -Path $targetAssets -Force | Out-Null
            foreach ($asset in Get-ChildItem -LiteralPath $stagedAssets -File) {
                $target = Join-Path $targetAssets $asset.Name
                if (Test-Path -LiteralPath $target) {
                    if ((Get-FileHash -LiteralPath $target).Hash -ne (Get-FileHash -LiteralPath $asset.FullName).Hash) { throw 'Selected asset has conflicting content.' }
                } else { Copy-Item -LiteralPath $asset.FullName -Destination $target }
            }
        }
        if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($configPath)) -ne [Convert]::ToBase64String($original)) { throw 'Active config changed during preparation.' }
        $backupRoot = Join-Path $outputRoot ('backups/prepare-' + [Guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
        [IO.File]::Replace($stageConfig, $configPath, (Join-Path $backupRoot 'launcher.json'))
    }
    $preview = '@echo off' + "`r`n" + 'pushd "%~dp0"' + "`r`n" + 'start "" "DragonCodexBoot.exe" --preview' + "`r`n" + 'popd' + "`r`n"
    $launch = '@echo off' + "`r`n" + 'pushd "%~dp0"' + "`r`n" + 'start "" "DragonCodexBoot.exe"' + "`r`n" + 'popd' + "`r`n"
    [IO.File]::WriteAllText((Join-Path $outputRoot 'Preview-Duo.cmd'), $preview, [Text.Encoding]::ASCII)
    [IO.File]::WriteAllText((Join-Path $outputRoot 'Launch-Duo.cmd'), $launch, [Text.Encoding]::ASCII)
    Write-Output ('Prepared: ' + $outputRoot)
    Write-Output 'Preview-Duo.cmd plays offline. Launch-Duo.cmd opens or hands off to the real client.'
    Write-Output 'Current JPGs are provisional reference cards, not regenerated characters.'
} finally {
    $lock.Dispose()
    Remove-Item -LiteralPath $lockPath -Force
    # Verify the exact recursive cleanup target stays inside this package.
    $resolvedStage = [IO.Path]::GetFullPath($stage)
    $allowedPrefix = [IO.Path]::GetFullPath($outputRoot).TrimEnd('\') + '\.prepare-'
    if (!$resolvedStage.StartsWith($allowedPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe staging cleanup path.' }
    if (Test-Path -LiteralPath $resolvedStage) { Remove-Item -LiteralPath $resolvedStage -Recurse -Force }
}
