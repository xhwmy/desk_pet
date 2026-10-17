import { readFile, writeFile } from 'node:fs/promises';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { homedir } from 'node:os';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
export const runtime=await import(pathToFileURL(join(homedir(),'.codex/skills/codex-skin-studio/scripts/apply.mjs')));
export const adapterId='bamboo-duo-windows-surfaces';
export async function applySurfaceAdapter(list) {
 const target=await runtime.selectMainTarget(list);
 if(!target) throw new Error('Main Codex surface was not found.');
 const css=await readFile(new URL('./client-surfaces.css',import.meta.url),'utf8');
 const session=new runtime.Session(target.webSocketDebuggerUrl);
 try {
  await session.open();
  const result=await session.evaluate(`(async()=>{let s=document.getElementById(${JSON.stringify(adapterId)});if(!s){s=document.createElement('style');s.id=${JSON.stringify(adapterId)};document.head.appendChild(s)}s.textContent=${JSON.stringify(css)};let caption=document.getElementById('bamboo-duo-caption-contrast');if(!caption){caption=document.createElement('div');caption.id='bamboo-duo-caption-contrast';caption.className=caption.id;caption.setAttribute('aria-hidden','true');document.body.appendChild(caption)}await Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,600))]);await Promise.race([new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))),new Promise(r=>setTimeout(r,250))]);const panel=document.querySelector('main[class*="_MainContentSurface_"]');return {adapterInstalled:s.isConnected,mainBackground:panel?getComputedStyle(panel).backgroundImage:null}})()`);
  const exec=promisify(execFile);
  const env={...process.env,PSModulePath:[join(process.env.ProgramFiles,'WindowsPowerShell/Modules'),join(process.env.WINDIR,'System32/WindowsPowerShell/v1.0/Modules')].join(';')};
  const frame=await exec(join(process.env.WINDIR,'System32/WindowsPowerShell/v1.0/powershell.exe'),['-NoProfile','-ExecutionPolicy','Bypass','-File',fileURLToPath(new URL('./Restore-WindowControls.ps1',import.meta.url))],{windowsHide:true,timeout:15000,env});
  const packageRoot=fileURLToPath(new URL('../build/DragonCodexBoot/',import.meta.url));
  await writeFile(join(packageRoot,'logs/window-controls.log'),frame.stdout);
  return {...result,windowControls:true};
 }finally{session.close()}
}
export async function evaluateWithAdapter(list,expression) {
 const values=await runtime.evaluateAll(list,expression);
 if(expression!==runtime.STATUS_EXPRESSION) return values;
 const flags=await runtime.evaluateAll(list,`Boolean(document.getElementById(${JSON.stringify(adapterId)})?.isConnected)`);
 return values.map((value,index)=>({...value,surfaceAdapter:flags[index]}));
}
if(process.argv[1] && pathToFileURL(process.argv[1]).href===import.meta.url) {
 console.log(JSON.stringify(await applySurfaceAdapter(await runtime.targets(9341))));
}
