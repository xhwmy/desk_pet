"""Build a new coherent idle from ImageGen artwork; preserve other pet states."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
QA = ROOT/'qa'
QA.mkdir(exist_ok=True)
CODEX_DIR = Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))
candidates = list((CODEX_DIR/'plugins'/'cache').glob('*/work-pets/*/skills/create-pet/scripts'))
SCRIPTS = Path(os.environ['WORK_PETS_SCRIPTS']) if 'WORK_PETS_SCRIPTS' in os.environ else max(candidates,key=lambda p:p.stat().st_mtime) if candidates else None
if SCRIPTS is None:
    raise SystemExit('Install work-pets or set WORK_PETS_SCRIPTS.')
sys.path.insert(0,str(SCRIPTS))
import compose_atlas
import render_animation_previews as previews


def dump(path, data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def run(script,*args):
    result = subprocess.run([sys.executable,str(SCRIPTS/script),*map(str,args)],capture_output=True,text=True)
    (QA/(script+'.log')).write_text(result.stdout+result.stderr,encoding='utf8')
    if result.returncode:
        raise RuntimeError(result.stdout+result.stderr)
    print(script,'passed',flush=True)


def bbox(cell):
    return cell.getchannel('A').point(lambda a:255 if a>16 else 0).getbbox()


def background(cell):
    bg = Image.new('RGBA',cell.size,'#e5e7ed')
    bg.alpha_composite(cell)
    return bg.convert('RGB')


before = Image.open(ROOT/'before.png').convert('RGBA')
run('extract_strip_frames.py','--decoded-dir',ROOT/'decoded','--output-dir',ROOT/'extracted','--states','idle','--chroma-key','#00FFFF','--method','components')
run('inspect_frames.py','--frames-root',ROOT/'extracted','--states','idle','--require-components','--json-out',QA/'source-review.json')
source = [Image.open(ROOT/'extracted'/'idle'/f'{i:02}.png').convert('RGBA') for i in range(6)]
baseline = bbox(before.crop((0,0,192,208)))[3]
# The extractor uses one shared row scale. Correct only subpixel rounding of
# the planted feet (one or two pixels); never fit individual poses to height.
cells, shifts = [], []
for cell in source:
    shift = baseline-bbox(cell)[3]
    assert abs(shift)<=2
    target = Image.new('RGBA',(192,208))
    target.alpha_composite(cell,(0,shift))
    cells.append(target)
    shifts.append(shift)
packed = Image.new('RGBA',(1152,208))
for i,cell in enumerate(cells):
    packed.paste(cell,(192*i,0))
packed.save(QA/'idle-before-despill.png')
run('despill_chroma_edges.py',QA/'idle-before-despill.png','--output',QA/'idle-clean.png','--chroma-key','#00FFFF','--json-out',QA/'chroma.json')
clean = Image.open(QA/'idle-clean.png').convert('RGBA')
atlas = before.copy()
atlas.paste(clean,(0,0))
dest = ROOT/'chiyan-native-breath.webp'
compose_atlas.save_outputs(atlas,ROOT/'chiyan-native-breath.png',dest)
encoded = Image.open(dest).convert('RGBA')
assert encoded.crop((0,208,1536,2288)).tobytes() == before.crop((0,208,1536,2288)).tobytes()
assert encoded.crop((1152,0,1536,208)).tobytes() == before.crop((1152,0,1536,208)).tobytes()

frames_root = QA/'frames'
state_frames = {}
for row,(state,ds) in enumerate(previews.ROW_DURATIONS.items()):
    folder = frames_root/state
    folder.mkdir(parents=True,exist_ok=True)
    cells = [encoded.crop((i*192,row*208,(i+1)*192,(row+1)*208)) for i in range(len(ds))]
    for i,cell in enumerate(cells):
        cell.save(folder/f'{i:02}.png')
    state_frames[state]=cells
run('inspect_frames.py','--frames-root',frames_root,'--json-out',QA/'frame-review.json')
run('validate_atlas.py',dest,'--require-v2','--chroma-key','#00FFFF','--json-out',QA/'atlas-validation.json')
run('make_contact_sheet.py',dest,'--output',QA/'contact.png')
run('make_direction_qa_sheet.py',dest,'--output',QA/'directions.png')
run('measure_direction_continuity.py',dest,'--json-out',QA/'continuity.json')
run('validate_pet_quality.py',dest,'--atlas-validation',QA/'atlas-validation.json','--chroma-report',QA/'chroma.json','--frame-review',QA/'frame-review.json','--direction-semantics',REPO/'codex-pet'/'chiyan'/'qa'/'direction-semantics.json','--continuity',QA/'continuity.json','--json-out',QA/'pet-quality.json')
run('render_animation_previews.py','--frames-root',frames_root,'--output-dir',ROOT/'previews')
durations = [1680,660,660,840,840,1920]
previews.save_preview([background(f) for f in state_frames['idle']],durations,ROOT/'previews'/'idle.gif')
previews.save_preview([background(state_frames['idle'][0]),*[background(f) for f in state_frames['jumping']],background(state_frames['idle'][0])],[1000,*previews.ROW_DURATIONS['jumping'],1000],ROOT/'previews'/'idle-jump-idle.gif')
looks=[encoded.crop((i%8*192,(9+i//8)*208,(i%8+1)*192,(10+i//8)*208)) for i in range(16)]
previews.save_preview([background(f) for f in looks],[180]*16,ROOT/'previews'/'look-loop.gif')
stills=Image.new('RGB',(1152,232),'#e5e7ed')
draw=ImageDraw.Draw(stills)
for i,cell in enumerate(state_frames['idle']):
    stills.paste(background(cell),(i*192,24))
    draw.text((i*192+5,5),f'{sum(durations[:i])/1000:.2f}s',fill='black')
stills.save(ROOT/'idle-stills.png')
all_frames, all_durations = [], []
for state,cells in state_frames.items():
    all_frames.extend(background(c) for c in cells)
    all_durations.extend(durations if state=='idle' else previews.ROW_DURATIONS[state])
previews.save_preview(all_frames,all_durations,ROOT/'previews'/'all-states.gif')
sys.path.insert(0,str(REPO/'animations'/'idle-six'/'vendor'))
import imageio_ffmpeg
writer=imageio_ffmpeg.write_frames(str(ROOT/'previews'/'all-states.mp4'),(192,208),fps=20,codec='libx264',pix_fmt_in='rgb24',pix_fmt_out='yuv420p',macro_block_size=1)
writer.send(None)
for frame,duration in zip(all_frames,all_durations):
    for _ in range(max(1,round(duration/50))):
        writer.send(frame.tobytes())
writer.close()
dump(ROOT/'timeline.json',{'mode':'coherent gentle breathing, hair sway and blink; one native idle sequence','durations_ms':durations,'cycle_ms':sum(durations),'ground_baseline':baseline,'source_translation_y':shifts,'task_and_look_rows_preserved':True,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size,'client_modified':False})
print(dest,flush=True)
