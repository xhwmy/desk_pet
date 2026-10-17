import { pathToFileURL } from 'node:url';
import { join } from 'node:path';
import { homedir } from 'node:os';
import { writeFile } from 'node:fs/promises';
const runtime=await import(pathToFileURL(join(homedir(),'.codex/skills/codex-skin-studio/scripts/apply.mjs')));
const status=await runtime.commandStatus(9341);
let surfaceAdapter=false;
if(status.status==='active') {
 const target=await runtime.selectMainTarget(await runtime.targets(9341));
 const session=new runtime.Session(target.webSocketDebuggerUrl);
 try{await session.open();surfaceAdapter=await session.evaluate("Boolean(document.getElementById('bamboo-duo-windows-surfaces')?.isConnected)");}finally{session.close();}
}
console.log(JSON.stringify({status:status.status,themeId:status.state?.themeId,surfaceAdapter,renderers:status.renderers?.map(({installed,connected,themeId,heroLoaded,cssRules,rootBackground})=>({installed,connected,themeId,heroLoaded,cssRules,rootBackground}))},null,2));
if(process.argv[2]) {
 const target=await runtime.selectMainTarget(await runtime.targets(9341));
 const session=new runtime.Session(target.webSocketDebuggerUrl);
 try {
  await session.open();
  const screenshot=await session.send('Page.captureScreenshot',{format:'png'});
  await writeFile(process.argv[2],Buffer.from(screenshot.data,'base64'));
  console.log(JSON.stringify({screenshot:process.argv[2]}));
 } finally {session.close();}
}
