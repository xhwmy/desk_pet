import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdtemp, mkdir, writeFile, readFile, rm, cp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const repo = fileURLToPath(new URL('../', import.meta.url));
const exec = promisify(execFile);
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAASSURBVBhXY/h/4PR/BgRgYAAANtgDikoDybcAAAAASUVORK5CYII=', 'base64');
const powershell = join(process.env.WINDIR, 'System32/WindowsPowerShell/v1.0/powershell.exe');
async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), 'prepare-duo-'));
  t.after(() => rm(root, { recursive:true, force:true }));
  for (const dir of ['scripts','config','build/DragonCodexBoot/assets']) await mkdir(join(root,dir),{recursive:true});
  for (const file of ['Prepare-Duo.ps1','duo-assets.mjs','Validate-SceneImage.ps1']) await cp(join(repo,'scripts',file),join(root,'scripts',file));
  // A controlled build step keeps these tests on preparation, not compilation.
  await writeFile(join(root,'scripts/build.ps1'), "Write-Output 'fixture build'\n");
  await cp(join(repo,'config/duo.example.json'),join(root,'config/duo.example.json'));
  const packageRoot = join(root,'build/DragonCodexBoot');
  await writeFile(join(packageRoot,'assets/chosen.png'),png);
  const config = { PlaybackMode:'Video',Video:'chosen.mp4',AppExecutable:powershell,Scene:{Background:'assets/chosen.png',LeftCharacter:'assets/chosen.png',RightCharacter:'assets/chosen.png',DurationSeconds:8},AutoReplaceEntrypoints:false,ProcessNames:['chosen'],ProcessPathContains:'chosen'};
  const configPath = join(packageRoot,'launcher.json');
  await writeFile(configPath,JSON.stringify(config));
  const image = join(root,'reference.png');await writeFile(image,png);
  return {root,packageRoot,configPath,config,image};
}
async function prepare(f,more=[]) {
  return exec(powershell,['-NoProfile','-ExecutionPolicy','Bypass','-File',join(f.root,'scripts/Prepare-Duo.ps1'),'-LeftImage',f.image,'-RightImage',f.image,'-BackgroundImage',f.image,...more],{windowsHide:true,timeout:30000});
}

test('preparation preserves chosen video mode and previous character selections', async t => {
  const f=await fixture(t);const before=await readFile(f.configPath,'utf8');
  await prepare(f);
  assert.equal(await readFile(f.configPath,'utf8'),before);
});

test('an explicit executable update takes effect without resetting chosen art', async t => {
  const f=await fixture(t);
  f.config.PlaybackMode='Scene'; await writeFile(f.configPath,JSON.stringify(f.config));
  const alternative=join(process.env.WINDIR,'System32/notepad.exe');
  await prepare(f,['-AppExecutable',alternative]);
  const actual=JSON.parse(await readFile(f.configPath,'utf8'));
  assert.equal(actual.AppExecutable.toLowerCase(),alternative.toLowerCase());
  assert.deepEqual(actual.Scene,f.config.Scene);
});

test('a failed reset leaves the active configuration byte identical', async t => {
  const f=await fixture(t);const before=await readFile(f.configPath,'utf8');
  // A real 9000x1 PNG decodes successfully, but exceeds the renderer asset limit.
  const script="Add-Type -AssemblyName System.Drawing; $b=New-Object Drawing.Bitmap 9000,1; try { $b.Save($args[0],[Drawing.Imaging.ImageFormat]::Png) } finally { $b.Dispose() }";
  const make=join(f.root,'make-wide.ps1');await writeFile(make,script);
  await exec(powershell,['-NoProfile','-ExecutionPolicy','Bypass','-File',make,f.image],{windowsHide:true});
  await assert.rejects(prepare(f,['-ResetAssets']));
  assert.equal(await readFile(f.configPath,'utf8'),before);
});
