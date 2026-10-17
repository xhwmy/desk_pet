import { createHash, randomUUID } from 'node:crypto';
import { mkdir, open, readFile, rename, rm, stat, writeFile } from 'node:fs/promises';
import { dirname, extname, isAbsolute, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const exec = promisify(execFile);

const fields = { background: 'Background', left: 'LeftCharacter', right: 'RightCharacter' };

function imageDimensions(bytes, extension) {
  if (extension === '.png') {
    if (bytes.length < 33 || !bytes.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10])) || bytes.toString('ascii',12,16) !== 'IHDR') throw new Error('Invalid PNG image');
    return [bytes.readUInt32BE(16), bytes.readUInt32BE(20)];
  }
  if (extension === '.jpg' || extension === '.jpeg') {
    if (bytes[0] !== 255 || bytes[1] !== 216) throw new Error('Invalid JPEG image');
    let i = 2;
    while (i + 3 < bytes.length) {
      if (bytes[i++] !== 255) break;
      while (bytes[i] === 255) i++;
      const marker = bytes[i++];
      if (marker === 217 || marker === 218) break;
      if (marker === 1 || (marker >= 208 && marker <= 215)) continue;
      const length = bytes.readUInt16BE(i);
      if (length < 2 || i + length > bytes.length) break;
      if ([192,193,194,195,197,198,199,201,202,203,205,206,207].includes(marker) && length >= 7) return [bytes.readUInt16BE(i+5), bytes.readUInt16BE(i+3)];
      i += length;
    }
    throw new Error('Invalid JPEG image dimensions');
  }
  throw new Error('Image must be PNG or JPEG (WPF scene assets do not use WebP)');
}

function localAsset(root, name) {
  if (typeof name !== 'string' || !name) return null;
  const path = resolve(root, name);
  const rel = relative(root, path);
  if (isAbsolute(rel) || rel === '..' || rel.startsWith('..\\') || rel.startsWith('../')) throw new Error('Asset path must stay inside the package');
  return path;
}

async function readOptional(path) {
  try { return await readFile(path); } catch (e) { if (e.code === 'ENOENT') return null; throw e; }
}

export async function importAsset({ root, file, slot }) {
  if (!Object.hasOwn(fields, slot) && !['video', 'wallpaper'].includes(slot)) throw new Error('Unsupported asset slot');
  if (!root || !file) throw new Error('Both root and file are required');
  root = resolve(root); file = resolve(file);
  const details = await stat(file);
  const maxBytes = slot === 'video' ? 512 * 1024 * 1024 : 32 * 1024 * 1024;
  if (!details.isFile() || details.size < 1 || details.size > maxBytes) throw new Error('Asset file is empty or too large');
  const bytes = await readFile(file);
  const extension = extname(file).toLowerCase();
  if (slot === 'video') {
    if (extension !== '.mp4' || bytes.length < 24 || bytes.toString('ascii', 4, 8) !== 'ftyp') throw new Error('Expected an MP4 file with an ftyp header');
  } else {
    const [width, height] = imageDimensions(bytes, extension);
    if (!width || !height || width > 8192 || height > 8192 || width * height > 32000000) throw new Error('Image dimensions exceed the 32 megapixel limit');
    const decoder = fileURLToPath(new URL('./Validate-SceneImage.ps1', import.meta.url));
    const powershell = join(process.env.WINDIR || 'C:/Windows', 'System32/WindowsPowerShell/v1.0/powershell.exe');
    try { await exec(powershell, ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', decoder, '-ImagePath', file], { windowsHide: true, timeout: 20000 }); }
    catch { throw new Error('Image decode failed; use a complete PNG or JPEG image'); }
  }
  const lockPath = join(root, '.asset-import.lock');
  let lock;
  try { lock = await open(lockPath, 'wx'); }
  catch (e) { if (e.code === 'EEXIST') throw new Error('An asset import is already in progress'); throw e; }
  let staging;
  try {
    const configPath = slot === 'wallpaper' ? join(root, 'wallpaper', 'selection.json') : join(root, 'launcher.json');
    const original = await readOptional(configPath);
    if (!original && slot !== 'wallpaper') throw new Error('launcher.json is required; prepare the duo package first');
    const config = original ? JSON.parse(original.toString('utf8').replace(/^\uFEFF/, '')) : {};
    if (Object.hasOwn(fields, slot) && !config.Scene) throw new Error('Scene configuration is required');
    const previous = slot === 'wallpaper' ? config.file : slot === 'video' ? config.Video : config.Scene[fields[slot]];
    const oldPath = localAsset(root, previous);
    const oldBytes = oldPath ? await readOptional(oldPath) : null;
    const hash = createHash('sha256').update(bytes).digest('hex');
    const assetName = `${slot}-${hash.slice(0, 16)}${extension}`;
    const assetRelative = `${slot === 'wallpaper' ? 'wallpaper' : 'assets/duo'}/${assetName}`;
    const destination = join(root, assetRelative);
    const backupDir = join(root, 'backups', `${Date.now()}-${randomUUID()}`);
    if (original || oldBytes) {
      await mkdir(backupDir, { recursive: true });
      if (original) await writeFile(join(backupDir, slot === 'wallpaper' ? 'selection.json' : 'launcher.json'), original);
      if (oldBytes) await writeFile(join(backupDir, `previous-asset${extname(oldPath)}`), oldBytes);
    }
    await mkdir(dirname(destination), { recursive: true });
    const existing = await readOptional(destination);
    if (existing && !existing.equals(bytes)) throw new Error('Asset hash collision or modified destination');
    if (!existing) await writeFile(destination, bytes, { flag: 'wx' });
    if (slot === 'wallpaper') Object.assign(config, { file: assetRelative, sha256: hash, applied: false });
    else if (slot === 'video') Object.assign(config, { Video: assetRelative, PlaybackMode: 'Video' });
    else { config.Scene[fields[slot]] = assetRelative; config.PlaybackMode = 'Scene'; }
    staging = `${configPath}.${randomUUID()}.tmp`;
    await writeFile(staging, `${JSON.stringify(config, null, 2)}\n`, { flag: 'wx' });
    await rename(staging, configPath);
    staging = null;
    return { status: 'imported', slot, destination, backupDir, sha256: hash,
      ...(slot === 'video' ? { note: 'Check HoldAt, TransitionStart, TransitionEnd and ScreenFrames for this MP4. Header validation does not verify codec support.' } : {}) };
  } finally {
    if (staging) await rm(staging, { force: true });
    await lock.close();
    await rm(lockPath, { force: true });
  }
}

async function main() {
  const args = process.argv.slice(2);
  if (args.shift() !== 'import') throw new Error('Usage: node duo-assets.mjs import --root PACKAGE --slot background|left|right|video|wallpaper --file FILE');
  const options = {};
  while (args.length) {
    const key = args.shift(), value = args.shift();
    if (!['--root','--slot','--file'].includes(key) || !value || value.startsWith('--')) throw new Error('Invalid command arguments');
    options[key.slice(2)] = value;
  }
  console.log(JSON.stringify(await importAsset(options), null, 2));
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main().catch(e => { console.error(e.message); process.exitCode = 1; });
