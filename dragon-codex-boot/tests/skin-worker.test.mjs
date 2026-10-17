import test from 'node:test';
import assert from 'node:assert/strict';
import { createStoreCallbacks } from '../scripts/skin-worker.mjs';
test('wallpaper startup leaves an already running client in place',async()=>{
  let launches=0;
  const callbacks=createStoreCallbacks({hasApp:async()=>true,hasTheme:async()=>true,launch:async()=>launches++});
  assert.equal((await callbacks.startupFn()).status,'already-running');
  assert.equal(launches,0);
});
test('wallpaper startup stays idle when no theme is selected',async()=>{
  let launches=0;
  const callbacks=createStoreCallbacks({hasApp:async()=>false,hasTheme:async()=>false,launch:async()=>launches++});
  assert.equal((await callbacks.startupFn()).status,'idle');
  assert.equal(launches,0);
});
test('Store recovery uses registered activation and never relaunches an intentionally closed app',async()=>{
  const calls=[];let running=true;
  const callbacks=createStoreCallbacks({hasApp:async()=>running,hasTheme:async()=>true,launch:async restart=>calls.push(restart)});
  assert.equal((await callbacks.recoveryFn({state:{themeId:'bamboo-duo'}})).status,'restarted');
  running=false;
  assert.equal((await callbacks.recoveryFn({state:{themeId:'bamboo-duo'}})).status,'idle');
  assert.deepEqual(calls,[true]);
});
