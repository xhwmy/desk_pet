"""Native fallback: six key poses in the six supported idle slots."""
from pathlib import Path
import sys,subprocess,json,hashlib,os
from PIL import Image
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
CODEX_DIR=Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))
candidates=list((CODEX_DIR/'plugins'/'cache').glob('*/work-pets/*/skills/create-pet/scripts'))
SCRIPTS=Path(os.environ['WORK_PETS_SCRIPTS']) if 'WORK_PETS_SCRIPTS' in os.environ else max(candidates,key=lambda p:p.stat().st_mtime) if candidates else None
if SCRIPTS is None or not (SCRIPTS/'validate_pet_quality.py').is_file():
    raise SystemExit('Install the work-pets plugin or set WORK_PETS_SCRIPTS to its create-pet/scripts directory.')
sys.path.insert(0,str(SCRIPTS))
import compose_atlas,render_animation_previews
qa=ROOT/'qa'/'native'
qa.mkdir(exist_ok=True)
actions=['hair','collar','sleep','stretch','typing','peek']
indices=[2,2,3,3,3,2]
durations=[1680,660,660,840,840,1920]
atlas=Image.open(ROOT/'final'/'chiyan-six-idles.webp').convert('RGBA')
frames=[]
for col,(action,index) in enumerate(zip(actions,indices)):
    cell=Image.open(ROOT/action/'clean'/f'{index:02}.png').convert('RGBA')
    atlas.paste(cell,(192*col,0))
    frames.append(cell)
dest=ROOT/'final'/'chiyan-native-six-poses.webp'
compose_atlas.save_outputs(atlas,ROOT/'final'/'chiyan-native-six-poses.png',dest)
def run(script,*args):
    r=subprocess.run([sys.executable,str(SCRIPTS/script),*map(str,args)],capture_output=True,text=True)
    (qa/(script+'.log')).write_text(r.stdout+r.stderr,encoding='utf8')
    assert r.returncode==0,r.stdout+r.stderr
    print(script,'passed',flush=True)
run('validate_atlas.py',dest,'--require-v2','--chroma-key','#00FFFF','--json-out',qa/'atlas-validation.json')
run('make_contact_sheet.py',dest,'--output',qa/'contact.png')
run('measure_direction_continuity.py',dest,'--json-out',qa/'continuity.json')
run('validate_pet_quality.py',dest,'--atlas-validation',qa/'atlas-validation.json','--chroma-report',ROOT/'qa'/'chroma.json','--frame-review',ROOT/'qa'/'review.json','--direction-semantics',REPO/'codex-pet'/'chiyan'/'qa'/'direction-semantics.json','--continuity',qa/'continuity.json','--json-out',qa/'pet-quality.json')
backgrounds=[]
for cell in frames:
    bg=Image.new('RGBA',(192,208),'#e5e7ed')
    bg.alpha_composite(cell)
    backgrounds.append(bg.convert('RGB'))
render_animation_previews.save_preview(backgrounds,durations,ROOT/'final'/'native-six-poses.gif')
(ROOT/'final'/'native-timeline.json').write_text(json.dumps({'mode':'six native key poses, not full action strips','actions':actions,'frame_indices':indices,'durations_ms':durations,'duration_ms':sum(durations),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size},indent=2),encoding='utf8')
print(dest,dest.stat().st_size)
