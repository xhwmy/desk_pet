"""Restore approved calm idle frames without changing the installed task rows.

Fetch the current pet to ../idle-timing-review/before-update.png first.
This script builds and validates locally; it never uploads or patches Codex.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'calm'
OUT.mkdir(exist_ok=True)
CODEX_DIR = Path(os.environ.get('CODEX_HOME', Path.home()/'.codex'))
candidates = list((CODEX_DIR/'plugins'/'cache').glob('*/work-pets/*/skills/create-pet/scripts'))
SCRIPTS = Path(os.environ['WORK_PETS_SCRIPTS']) if 'WORK_PETS_SCRIPTS' in os.environ else max(candidates, key=lambda p:p.stat().st_mtime)
sys.path.insert(0, str(SCRIPTS))
import compose_atlas
import render_animation_previews as previews


def run(script, *args):
    result = subprocess.run([sys.executable, str(SCRIPTS/script), *map(str,args)], capture_output=True, text=True)
    (OUT/(script+'.log')).write_text(result.stdout+result.stderr, encoding='utf8')
    if result.returncode:
        raise RuntimeError(result.stdout+result.stderr)
    print(script, 'passed', flush=True)


def background(cell):
    bg = Image.new('RGBA', cell.size, '#e5e7ed')
    bg.alpha_composite(cell)
    return bg.convert('RGB')


before = Image.open(ROOT.parent/'idle-timing-review'/'before-update.png').convert('RGBA')
original = Image.open(ROOT/'original.webp').convert('RGBA')
assert before.size == original.size == (1536,2288)
atlas = before.copy()
atlas.paste(original.crop((0,0,1152,208)), (0,0))
dest = OUT/'chiyan-native-calm.webp'
compose_atlas.save_outputs(atlas, OUT/'chiyan-native-calm.png', dest)
encoded = Image.open(dest).convert('RGBA')
assert encoded.crop((0,208,1536,2288)).tobytes() == before.crop((0,208,1536,2288)).tobytes()
assert encoded.crop((1152,0,1536,208)).tobytes() == before.crop((1152,0,1536,208)).tobytes()

frames_root = OUT/'frames'
state_frames = {}
for row, (state, durations) in enumerate(previews.ROW_DURATIONS.items()):
    folder = frames_root/state
    folder.mkdir(parents=True, exist_ok=True)
    cells = [encoded.crop((i*192,row*208,(i+1)*192,(row+1)*208)) for i in range(len(durations))]
    for i, cell in enumerate(cells):
        cell.save(folder/f'{i:02}.png')
    state_frames[state] = cells
run('inspect_frames.py', '--frames-root', frames_root, '--json-out', OUT/'frame-review.json')
run('validate_atlas.py', dest, '--require-v2', '--chroma-key', '#00FFFF', '--json-out', OUT/'atlas-validation.json')
run('make_contact_sheet.py', dest, '--output', OUT/'contact.png')
run('make_direction_qa_sheet.py', dest, '--output', OUT/'directions.png')
run('measure_direction_continuity.py', dest, '--json-out', OUT/'continuity.json')
run('validate_pet_quality.py', dest, '--atlas-validation', OUT/'atlas-validation.json', '--chroma-report', ROOT/'qa'/'chroma.json', '--frame-review', OUT/'frame-review.json', '--direction-semantics', ROOT.parents[1]/'codex-pet'/'chiyan'/'qa'/'direction-semantics.json', '--continuity', OUT/'continuity.json', '--json-out', OUT/'pet-quality.json')
run('render_animation_previews.py', '--frames-root', frames_root, '--output-dir', OUT/'previews')
durations = [1680,660,660,840,840,1920]
previews.save_preview([background(f) for f in state_frames['idle']], durations, OUT/'previews'/'idle.gif')
previews.save_preview([background(state_frames['idle'][0]), *[background(f) for f in state_frames['jumping']], background(state_frames['idle'][0])], [1000,*previews.ROW_DURATIONS['jumping'],1000], OUT/'previews'/'idle-jump-idle.gif')
looks = [encoded.crop((i%8*192,(9+i//8)*208,(i%8+1)*192,(10+i//8)*208)) for i in range(16)]
previews.save_preview([background(f) for f in looks], [180]*16, OUT/'previews'/'look-loop.gif')
stills = Image.new('RGB',(1152,232),'#e5e7ed')
draw = ImageDraw.Draw(stills)
for i, cell in enumerate(state_frames['idle']):
    stills.paste(background(cell),(i*192,24))
    draw.text((i*192+5,5),f'{sum(durations[:i])/1000:.2f}s',fill='black')
stills.save(OUT/'idle-stills.png')
all_frames, all_durations = [], []
for state, cells in state_frames.items():
    all_frames.extend(background(c) for c in cells)
    all_durations.extend(durations if state == 'idle' else previews.ROW_DURATIONS[state])
previews.save_preview(all_frames, all_durations, OUT/'previews'/'all-states.gif')
sys.path.insert(0,str(ROOT/'vendor'))
import imageio_ffmpeg
writer = imageio_ffmpeg.write_frames(str(OUT/'previews'/'all-states.mp4'), (192,208), fps=20, codec='libx264', pix_fmt_in='rgb24', pix_fmt_out='yuv420p', macro_block_size=1)
writer.send(None)
for frame, duration in zip(all_frames,all_durations):
    for _ in range(max(1,round(duration/50))):
        writer.send(frame.tobytes())
writer.close()
report = {'mode':'calm continuous native idle; no random action scheduler', 'source':'original.webp first six idle cells', 'durations_ms':durations,'cycle_ms':sum(durations), 'task_rows_preserved':True, 'look_rows_preserved':True, 'unused_cells_preserved':True, 'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(), 'bytes':dest.stat().st_size, 'client_modified':False}
(OUT/'timeline.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report,indent=2))
