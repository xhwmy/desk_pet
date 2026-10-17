import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const repo=fileURLToPath(new URL('../',import.meta.url));
const ps=join(process.env.WINDIR,'System32/WindowsPowerShell/v1.0/powershell.exe');
test('Store process discovery includes both sides of an application update and excludes other applications',()=>{
  const helper=join(repo,'scripts/StoreClient.ps1').replaceAll("'","''");
  const command=`$ErrorActionPreference='Stop'; . '${helper}'; function Get-CimInstance { @(
    [pscustomobject]@{ProcessId=1;ExecutablePath='C:\\Program Files\\WindowsApps\\OpenAI.Codex_26.1007_x64__id\\app\\ChatGPT.exe'},
    [pscustomobject]@{ProcessId=2;ExecutablePath='C:\\Program Files\\WindowsApps\\OpenAI.Codex_26.1013_x64__id\\app\\ChatGPT.exe'},
    [pscustomobject]@{ProcessId=3;ExecutablePath='C:\\Other\\ChatGPT.exe'},
    [pscustomobject]@{ProcessId=4;ExecutablePath='C:\\Program Files\\WindowsApps\\Another.App_x64__id\\app\\ChatGPT.exe'}
  ) }; $ids=@(Get-StoreClientProcesses | ForEach-Object {$_.ProcessId}); if(($ids -join ',') -ne '1,2') {throw 'Update process discovery failed'}; 'update-processes-ok'`;
  const output=execFileSync(ps,['-NoProfile','-ExecutionPolicy','Bypass','-Command',command],{encoding:'utf8',windowsHide:true});
  assert.match(output,/update-processes-ok/);
});
test('repair recreates a missing owned shortcut and retains its original backup', async t=>{
  const root=await mkdtemp(join(tmpdir(),'duo-entry-'));
  t.after(()=>rm(root,{recursive:true,force:true}));
  const file=join(root,'test.ps1');
  const installer=join(repo,'scripts/Install-DuoEntrypoints.ps1').replaceAll("'","''");
  await writeFile(file,`
$ErrorActionPreference='Stop'
$linkPaths=@((Join-Path $PSScriptRoot 'Codex.lnk'),(Join-Path $PSScriptRoot 'ChatGPT.lnk'))
$stateRoot=Join-Path $PSScriptRoot 'state'
$shell=New-Object -ComObject WScript.Shell
foreach($linkPath in $linkPaths) {
$link=$shell.CreateShortcut($linkPath)
$link.TargetPath=Join-Path $env:WINDIR 'explorer.exe'
$link.Arguments='shell:AppsFolder\\OpenAI.Codex_2p2nqsd0c76g0!App'
$link.Save()
}
& '${installer}' -ShortcutPaths $linkPaths -StateRoot $stateRoot
$before=Get-Content (Join-Path $stateRoot 'shortcuts.json') -Raw | ConvertFrom-Json
Remove-Item -LiteralPath $linkPaths[0]
& '${installer}' -Repair -ShortcutPaths $linkPaths -StateRoot $stateRoot
& '${installer}' -Verify -StateRoot $stateRoot
$after=Get-Content (Join-Path $stateRoot 'shortcuts.json') -Raw | ConvertFrom-Json
for($index=0;$index -lt $before.Count;$index++) {
if($before[$index].backup -ne $after[$index].backup) {throw 'Original backup changed'}
if((Get-FileHash $after[$index].backup).Hash -ne $before[$index].sha256) {throw 'Original backup bytes changed'}
}
Write-Output 'repair-ok'
`);
  const env={...process.env,PSModulePath:[join(process.env.ProgramFiles,'WindowsPowerShell/Modules'),join(process.env.WINDIR,'System32/WindowsPowerShell/v1.0/Modules')].join(';')};
  const output=execFileSync(ps,['-NoProfile','-ExecutionPolicy','Bypass','-File',file],{encoding:'utf8',windowsHide:true,env});
  assert.match(output,/repair-ok/);
});
