$ErrorActionPreference='Stop'
$log=Join-Path $PSScriptRoot '../build/DragonCodexBoot/logs/native-reopen-test.json'
try {
 . (Join-Path $PSScriptRoot 'StoreClient.ps1')
 $store=Get-AppxPackage -Name OpenAI.Codex | Select-Object -First 1
 $app=Join-Path $store.InstallLocation 'app/ChatGPT.exe'
 $old=@(Get-CimInstance Win32_Process -Filter "Name='ChatGPT.exe'" | Where-Object {$_.ExecutablePath -eq $app -and $_.CommandLine -notmatch '--type='})
 @{status='reopening-native-entry';at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content $log -Encoding UTF8
 foreach($item in $old) { $null=(Get-Process -Id $item.ProcessId -ErrorAction SilentlyContinue).CloseMainWindow() }
 Start-Sleep -Seconds 3
 Get-CimInstance Win32_Process -Filter "Name='ChatGPT.exe'" | Where-Object {$_.ExecutablePath -eq $app} | ForEach-Object {Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue}
 Start-Sleep -Seconds 1
 $nativePid=Start-StoreClient -Aumid ($store.PackageFamilyName+'!App') -Normal
 $node=(Get-Command node).Source
 $deadline=[DateTime]::UtcNow.AddSeconds(100)
 do {
  Start-Sleep -Seconds 2
  $result=& $node (Join-Path $PSScriptRoot 'Inspect-Skin.mjs')
  if($LASTEXITCODE -ne 0) {continue}
  $live=$result | ConvertFrom-Json
  if($live.status -eq 'active' -and $live.surfaceAdapter) {
   $current=@(Get-CimInstance Win32_Process -Filter "Name='ChatGPT.exe'" | Where-Object {$_.ExecutablePath -eq $app -and $_.CommandLine -notmatch '--type='})
   @{status='passed';nativeLaunchPid=$nativePid;currentPid=$current.ProcessId;oldPid=$old.ProcessId;themeId=$live.themeId;surfaceAdapter=$live.surfaceAdapter;at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content $log -Encoding UTF8
   exit 0
  }
 }while([DateTime]::UtcNow -lt $deadline)
 throw 'Native reopen did not restore the visible wallpaper within 100 seconds.'
}catch{
 @{status='failed';error=$_.Exception.Message;stack=$_.ScriptStackTrace;at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content $log -Encoding UTF8
 exit 1
}
