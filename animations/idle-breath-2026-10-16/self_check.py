"""Verify the encoded sprite sheet, previews, and fresh cloud readback."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image,ImageSequence

ROOT=Path(__file__).resolve().parent
QA=ROOT/'qa'
read=lambda name:json.loads((QA/name).read_text(encoding='utf8'))
path=ROOT/'chiyan-native-breath.webp'
sha=hashlib.sha256(path.read_bytes()).hexdigest()
with Image.open(path) as image:
    static=image.n_frames==1
    native=image.convert('RGBA')
before=Image.open(ROOT/'before.png').convert('RGBA')
remote=Image.open(ROOT/'stored-readback.png').convert('RGBA')
cells=[native.crop((192*i,0,192*(i+1),208)) for i in range(6)]
boxes=[c.getchannel('A').point(lambda a:255 if a>16 else 0).getbbox() for c in cells]
masks=[np.asarray(c)[:,:,3]>16 for c in cells]
loop_iou=float((masks[-1]&masks[0]).sum()/(masks[-1]|masks[0]).sum())
checks={
    'static_v2_atlas':static and native.size==(1536,2288),
    'stored_pixels_equal_final':remote.size==native.size and remote.tobytes()==native.tobytes(),
    'non_idle_rows_identical_to_pre_update':native.crop((0,208,1536,2288)).tobytes()==before.crop((0,208,1536,2288)).tobytes(),
    'unused_cells_identical_to_pre_update':native.crop((1152,0,1536,208)).tobytes()==before.crop((1152,0,1536,208)).tobytes(),
    'idle_replaced_with_new_art':native.crop((0,0,1152,208)).tobytes()!=before.crop((0,0,1152,208)).tobytes(),
    'six_distinct_frames':len({c.tobytes() for c in cells})==6,
    'feet_share_baseline_203':all(b and b[3]==203 for b in boxes),
    'safe_frame_edges':all(b and b[0]>0 and b[1]>0 and b[2]<192 and b[3]<208 for b in boxes),
    'loop_endpoint_silhouette_iou_above_90_percent':loop_iou>=.90,
    'official_preflight_passed':read('official-preflight.json')['valid'],
    'source_review_passed':read('source-review.json')['ok'],
    'frame_review_passed':read('frame-review.json')['ok'],
    'timeline_matches_final_bytes':json.loads((ROOT/'timeline.json').read_text(encoding='utf8'))['sha256']==sha,
}
for name in ['atlas-validation','pet-quality']:
    r=read(name+'.json')
    checks[name+'_passes_current_bytes']=r['ok'] and r['sha256']==sha
with Image.open(ROOT/'previews'/'idle.gif') as preview:
    duration=0
    for frame in ImageSequence.Iterator(preview):
        frame.load()
        duration+=frame.info['duration']
    checks['native_preview_six_frames_6600ms']=preview.n_frames==6 and duration==6600 and preview.info.get('loop')==0
sys.path.insert(0,str(ROOT.parents[1]/'animations'/'idle-six'/'vendor'))
import imageio_ffmpeg
decoded=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(ROOT/'previews'/'all-states.mp4'),'-f','null','-'],capture_output=True,text=True)
checks['all_state_mp4_decodes']=decoded.returncode==0
report={'ok':all(checks.values()),'checked_at_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'sha256':sha,'loop_endpoint_silhouette_iou':loop_iou,'idle_bounds':boxes,'pet_id':'pet_6abb898c7228819191b6e896f2538d5d','client_modified':False,'native_mode':'one six-frame coherent idle sequence; no random scheduling'}
(QA/'self-check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['ok'] else 1)
