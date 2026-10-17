[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Image,
    [string]$PackageRoot,
    [string]$SkillRoot = (Join-Path $env:USERPROFILE '.codex/skills/codex-skin-studio'),
    [string]$FfmpegDirectory,
    [string]$NodeModuleDirectory,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (!$PackageRoot) {
    if (Test-Path -LiteralPath (Join-Path $repoRoot 'DragonCodexBoot.exe')) { $PackageRoot = $repoRoot }
    else { $PackageRoot = Join-Path $repoRoot 'build/DragonCodexBoot' }
}
$PackageRoot = (Resolve-Path -LiteralPath $PackageRoot).Path
$Image = (Resolve-Path -LiteralPath $Image).Path
$creator = Join-Path $SkillRoot 'scripts/create-theme.mjs'
if (!(Test-Path -LiteralPath $creator -PathType Leaf)) { throw 'Codex Skin Studio is required to prepare a client wallpaper.' }
$node = (Get-Command node -ErrorAction Stop).Source
if (!$NodeModuleDirectory) {
    $bundledModules = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
    if (Test-Path -LiteralPath (Join-Path $bundledModules 'sharp')) { $NodeModuleDirectory = $bundledModules }
}
if ($NodeModuleDirectory) { $env:NODE_PATH = (Resolve-Path -LiteralPath $NodeModuleDirectory).Path }
if ($FfmpegDirectory) { $env:Path = (Resolve-Path -LiteralPath $FfmpegDirectory).Path + [IO.Path]::PathSeparator + $env:Path }
$portable = Join-Path $env:LOCALAPPDATA 'Programs/Codex'
if (Test-Path -LiteralPath (Join-Path $portable 'ChatGPT.exe')) { $env:Path = $portable + [IO.Path]::PathSeparator + $env:Path }
# Creation is local only; applying is a separate explicit operation.
$themeDir = Join-Path $PackageRoot ('wallpaper/themes/duo-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,6))
& $node $creator --id 'bamboo-duo' --name 'Bamboo Duo' --out $themeDir --hero $Image --accent '#D59CB8' --secondary '#93BCAC' --surface '#1E3332' --text '#F4F1ED' --brand 'Bamboo Duo' --brand-style mystic
if ($LASTEXITCODE -ne 0) { throw 'Wallpaper creation failed; see the creator diagnostics above. WebP encoding requires sharp or ffmpeg.' }
& $node (Join-Path $PSScriptRoot 'duo-assets.mjs') import --root $PackageRoot --slot wallpaper --file $Image
if ($LASTEXITCODE -ne 0) { throw 'Wallpaper was created, but selecting its source image failed.' }
Write-Output ('Theme prepared locally: ' + $themeDir)
if ($Apply) {
    # This supported external runner can restart the client and install persistence.
    # Do not pass -Apply during normal art iteration or preview.
    $runner = Join-Path $SkillRoot 'scripts/windows/apply.ps1'
    & $runner -ThemeDir $themeDir -Persist
    if (!$?) { throw 'Wallpaper application failed. The prepared theme remains available.' }
} else {
    Write-Output 'The client has not been changed. Select final art before applying the theme.'
}
