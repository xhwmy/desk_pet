$ErrorActionPreference='Stop'
$repoRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
& (Join-Path $PSScriptRoot 'build.ps1')
$outputRoot=Join-Path $repoRoot 'build/DragonCodexBoot'
$exe=Join-Path $outputRoot 'DragonCodexBoot.exe'
$process=Start-Process -FilePath $exe -ArgumentList '--self-test' -WindowStyle Hidden -Wait -PassThru
if ($process.ExitCode -ne 0) { throw 'Launcher self-test failed. See build/DragonCodexBoot/self-test-error.txt.' }
$framework=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
$argsList=@('/nologo','/target:exe','/platform:x64',('/out:'+(Join-Path $outputRoot 'GeometryTests.exe')),('/reference:'+$exe),'/reference:System.Web.Extensions.dll',('/reference:'+(Join-Path $framework 'WPF/PresentationFramework.dll')),('/reference:'+(Join-Path $framework 'WPF/WindowsBase.dll')),(Join-Path $repoRoot 'tests/GeometryTests.cs'))
& (Join-Path $framework 'csc.exe') @argsList
if ($LASTEXITCODE -ne 0) { throw 'Test harness compilation failed.' }
& (Join-Path $outputRoot 'GeometryTests.exe') (Join-Path $repoRoot 'config/launcher.example.json')
if ($LASTEXITCODE -ne 0) { throw 'Geometry or configuration tests failed.' }
& (Join-Path $repoRoot 'tests/EntrypointTests.ps1')
$sceneArgs=@('/nologo','/target:exe','/platform:x64',('/out:'+(Join-Path $outputRoot 'SceneTests.exe')),('/reference:'+$exe),'/reference:System.Web.Extensions.dll','/reference:System.Xaml.dll')
foreach ($name in @('WindowsBase.dll','PresentationCore.dll','PresentationFramework.dll')) { $sceneArgs += '/reference:' + (Join-Path $framework ('WPF/' + $name)) }
$sceneArgs += Join-Path $repoRoot 'tests/SceneTests.cs'
& (Join-Path $framework 'csc.exe') @sceneArgs
if ($LASTEXITCODE -ne 0) { throw 'Scene harness compilation failed.' }
& (Join-Path $outputRoot 'SceneTests.exe') (Join-Path $repoRoot 'config/duo.example.json')
if ($LASTEXITCODE -ne 0) { throw 'Scene tests failed.' }
& node --test (Join-Path $repoRoot 'tests/duo-assets.test.mjs') (Join-Path $repoRoot 'tests/prepare-duo.test.mjs') (Join-Path $repoRoot 'tests/custom-entrypoints.test.mjs') (Join-Path $repoRoot 'tests/skin-worker.test.mjs')
if ($LASTEXITCODE -ne 0) { throw 'Asset import or preparation tests failed.' }
Get-Content -LiteralPath (Join-Path $outputRoot 'qa/self-test.json') -Raw
