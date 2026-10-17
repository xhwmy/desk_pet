import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, readdir, rm } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

// These exercise real file replacement: invalid imports must leave the active
// configuration untouched, and valid replacements must retain the previous art.
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAASSURBVBhXY/h/4PR/BgRgYAAANtgDikoDybcAAAAASUVORK5CYII=', 'base64');
async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), 'duo-assets-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(join(root, 'assets'), { recursive: true });
  await writeFile(join(root, 'assets', 'old.png'), png);
  const config = { PlaybackMode: 'Scene', Scene: { Background: 'assets/old.png', LeftCharacter: 'assets/old.png', RightCharacter: 'assets/old.png', DurationSeconds: 8 }, HoldAt: 4.8, TransitionStart: 6, TransitionEnd: 7.6 };
  await writeFile(join(root, 'launcher.json'), JSON.stringify(config));
  return { root, config };
}
async function importer() { return (await import('../scripts/duo-assets.mjs')).importAsset; }

test('invalid PNG rejects without changing config or creating an asset backup', async t => {
  const { root } = await fixture(t);
  const file = join(root, 'broken.png');
  await writeFile(file, 'not an image');
  const before = await readFile(join(root, 'launcher.json'), 'utf8');
  const importAsset = await importer();
  await assert.rejects(importAsset({ root, file, slot: 'left' }), /PNG|image/i);
  assert.equal(await readFile(join(root, 'launcher.json'), 'utf8'), before);
  assert.equal((await readdir(root)).includes('backups'), false);
});

test('PNG header without pixel data cannot replace a working scene', async t => {
  const { root } = await fixture(t);
  const file = join(root, 'truncated.png');
  await writeFile(file, png.subarray(0,33));
  const before = await readFile(join(root, 'launcher.json'), 'utf8');
  const importAsset = await importer();
  await assert.rejects(importAsset({ root, file, slot: 'left' }), /decode|image|PNG/i);
  assert.equal(await readFile(join(root, 'launcher.json'), 'utf8'), before);
  assert.equal((await readdir(root)).includes('backups'), false);
});

test('a replacement in a Unicode path updates only its slot and backs up previous art', async t => {
  const { root, config } = await fixture(t);
  const dir = join(root, '\u56fe\u7247 with spaces');
  await mkdir(dir);
  const file = join(dir, '\u89d2\u8272.png');
  await writeFile(file, png);
  const importAsset = await importer();
  const result = await importAsset({ root, file, slot: 'left' });
  const actual = JSON.parse(await readFile(join(root, 'launcher.json'), 'utf8'));
  assert.notEqual(actual.Scene.LeftCharacter, config.Scene.LeftCharacter);
  assert.equal(actual.Scene.RightCharacter, config.Scene.RightCharacter);
  assert.equal(actual.PlaybackMode, 'Scene');
  assert.deepEqual(await readFile(join(root, actual.Scene.LeftCharacter)), png);
  assert.deepEqual(await readFile(join(result.backupDir, 'previous-asset.png')), png);
  assert.deepEqual(JSON.parse(await readFile(join(result.backupDir, 'launcher.json'), 'utf8')), config);
});

test('wallpaper selection never changes startup config', async t => {
  const { root } = await fixture(t);
  const file = join(root, 'new.png');
  await writeFile(file, png);
  const before = await readFile(join(root, 'launcher.json'), 'utf8');
  const importAsset = await importer();
  const result = await importAsset({ root, file, slot: 'wallpaper' });
  assert.equal(await readFile(join(root, 'launcher.json'), 'utf8'), before);
  const selection = JSON.parse(await readFile(join(root, 'wallpaper', 'selection.json'), 'utf8'));
  assert.equal(selection.applied, false);
  assert.deepEqual(await readFile(result.destination), png);
});

test('unsupported slots and mismatched extensions reject before mutation', async t => {
  const { root } = await fixture(t);
  const file = join(root, 'not-jpeg.jpg');
  await writeFile(file, png);
  const importAsset = await importer();
  await assert.rejects(importAsset({ root, file, slot: '../../escape' }), /slot/i);
  await assert.rejects(importAsset({ root, file, slot: 'right' }), /JPEG|image/i);
});

test('video import switches modes but refuses a fake MP4', async t => {
  const { root } = await fixture(t);
  const file = join(root, 'fake.mp4');
  await writeFile(file, 'not a video');
  const importAsset = await importer();
  await assert.rejects(importAsset({ root, file, slot: 'video' }), /MP4/i);
});

test('a real MP4 selects video mode and later character replacement returns to scene mode', async t => {
  const { root, config } = await fixture(t);
  const importAsset = await importer();
  const video = fileURLToPath(new URL('../media/startup.mp4', import.meta.url));
  const imported = await importAsset({root, file:video, slot:'video'});
  let active = JSON.parse(await readFile(join(root,'launcher.json'),'utf8'));
  assert.equal(active.PlaybackMode,'Video');
  assert.deepEqual(active.Scene,config.Scene);
  assert.equal((await readFile(imported.destination)).toString('ascii',4,8),'ftyp');
  assert.match(imported.note,/Check HoldAt/);
  const image=join(root,'new.png');await writeFile(image,png);
  await importAsset({root,file:image,slot:'right'});
  active=JSON.parse(await readFile(join(root,'launcher.json'),'utf8'));
  assert.equal(active.PlaybackMode,'Scene');
  assert.equal(active.Video.replaceAll('\\','/'),imported.destination.slice(root.length+1).replaceAll('\\','/'));
});

test('an in-progress import is not overwritten by another import', async t => {
  const { root } = await fixture(t);
  await writeFile(join(root, '.asset-import.lock'), 'another import');
  const file = join(root, 'new.png');
  await writeFile(file, png);
  const importAsset = await importer();
  await assert.rejects(importAsset({ root, file, slot: 'left' }), /import.*progress/i);
  assert.equal(await readFile(join(root, '.asset-import.lock'), 'utf8'), 'another import');
});
