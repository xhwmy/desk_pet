import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { join, resolve } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { homedir } from 'node:os';

export function createStoreCallbacks({hasApp,hasTheme,launch}) {
 return {
  startupFn: async()=>{
   if(!await hasTheme()) return {status:'idle'};
   if(await hasApp()) return {status:'already-running'};
   await launch(false);return {status:'launched'};
  },
  recoveryFn: async({state})=>{
   if(!state?.themeId || !await hasApp()) return {status:'idle'};
   await launch(true);return {status:'restarted'};
  }
 };
}

if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const skill=join(homedir(),'.codex/skills/codex-skin-studio/scripts/persist.mjs');
  const {persistenceWorker}=await import(pathToFileURL(skill));
  const {runtime,applySurfaceAdapter,evaluateWithAdapter}=await import('./client-surface-adapter.mjs');
  const exec=promisify(execFile);
  const ps=join(process.env.WINDIR,'System32/WindowsPowerShell/v1.0/powershell.exe');
  const entry=fileURLToPath(new URL('./Start-CustomCodex.ps1',import.meta.url));
  const callbacks=createStoreCallbacks({
   hasTheme:async()=>Boolean((await runtime.readState())?.themeId),
   hasApp:async()=>(await runtime.processIds('ChatGPT.exe')).length>0,
   launch:async restart=>{
    const args=['-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File',entry,'-LaunchOnly',...(restart?['-Restart']:[])];
    const env={...process.env,PSModulePath:[join(process.env.ProgramFiles,'WindowsPowerShell/Modules'),join(process.env.WINDIR,'System32/WindowsPowerShell/v1.0/Modules')].join(';')};
    await exec(ps,args,{windowsHide:true,timeout:90000,env});
   }
  });
  // Retain the supported worker's locking and CSS recovery, adapting Store activation and current surface tokens.
  await persistenceWorker({...callbacks,evaluateListFn:evaluateWithAdapter,
   injectionVerifiedFn:(value,id,assets)=>runtime.injectionVerified(value,id,assets)&&value.surfaceAdapter===true,
   injectThemeFn:async(list,saved)=>{const result=await runtime.injectTheme(list,saved);await applySurfaceAdapter(list);return result;}
  });
}
