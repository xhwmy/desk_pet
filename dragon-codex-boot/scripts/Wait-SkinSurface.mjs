import {runtime} from './client-surface-adapter.mjs';
try {
 const selected=await runtime.selectMainTarget(await runtime.targets(9341),undefined,{allowTransient:true});
 process.exitCode=selected?0:1;
}catch{process.exitCode=1;}
