"""Extend an existing v2 pet with an animated-WebP idle timeline.

All artwork comes from imagegen. Bundled pet tools own extraction, cleanup,
composition and acceptance. This adapter only registers generated rows to the
existing neutral, copies unchanged cells, and encodes the temporal dimension.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import io
import struct
import os
from PIL import Image, ImageDraw, ImageSequence

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
CODEX_DIR = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex'))
candidates = list((CODEX_DIR / 'plugins' / 'cache').glob('*/work-pets/*/skills/create-pet/scripts'))
SCRIPTS = Path(os.environ['WORK_PETS_SCRIPTS']) if 'WORK_PETS_SCRIPTS' in os.environ else max(candidates, key=lambda p:p.stat().st_mtime) if candidates else None
if SCRIPTS is None or not (SCRIPTS / 'validate_pet_quality.py').is_file():
    raise SystemExit('Install the work-pets plugin or set WORK_PETS_SCRIPTS to its create-pet/scripts directory.')
sys.path.insert(0, str(SCRIPTS))
import compose_atlas
import render_animation_previews as previews
import extract_strip_frames as extractor

ACTIONS = ['hair', 'collar', 'sleep', 'stretch', 'typing', 'peek']
QA = ROOT / 'qa'
FINAL = ROOT / 'final'
for p in (QA, FINAL):
    p.mkdir(exist_ok=True)

def run(script, *args):
    result = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True)
    (QA / (script.removesuffix('.py') + '-last.log')).write_text(result.stdout + result.stderr, encoding='utf8')
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    print(script, 'passed', flush=True)

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')

def background(frame):
    out = Image.new('RGBA', frame.size, '#e5e7ed')
    out.alpha_composite(frame)
    return out.convert('RGB')

original = Image.open(ROOT / 'original.webp').convert('RGBA')
neutral = original.crop((1152, 0, 1344, 208))
nb = neutral.getbbox()
# The older installed jump row fitted every pose separately, flattening its
# vertical movement. Restore shared registration from its approved source
# geometry while reusing the already cleaned original artwork.
jump_source = Image.open(REPO / 'codex-pet' / 'chiyan' / 'decoded' / 'jumping.png').convert('RGBA')
jump_groups = extractor.component_frame_groups(jump_source,5)
assert jump_groups and len(jump_groups)==5
jump_boxes = [extractor.component_bounds(g) for g in jump_groups]
jump_top = min(b[1] for b in jump_boxes)
jump_bottom = max(b[3] for b in jump_boxes)
jump_scale = min(198/(jump_bottom-jump_top),182/max(b[2]-b[0] for b in jump_boxes))
for col,b in enumerate(jump_boxes):
    old = original.crop((col*192,832,(col+1)*192,1040))
    cropped = old.crop(old.getbbox())
    sized = cropped.resize((round((b[2]-b[0])*jump_scale),round((b[3]-b[1])*jump_scale)),Image.Resampling.LANCZOS)
    restored = Image.new('RGBA',(192,208))
    restored.alpha_composite(sized,((192-sized.width)//2,203-round((jump_bottom-b[1])*jump_scale)))
    original.paste(compose_atlas.clear_transparent_rgb(restored),(col*192,832))
dump(QA/'jump-registration-restored.json',{'source':'approved original jumping.png','source_bounds':jump_boxes,'shared_scale':jump_scale,'method':'restore source geometry using cleaned original cells'})
allframes = {}
registration = {}
for action in ACTIONS:
    work = ROOT / action
    source = work / 'decoded' / 'idle.png'
    keyed = extractor.remove_chroma_background(Image.open(source), (0,255,255), 84)
    components = extractor.connected_components(keyed)
    largest = max(c['area'] for c in components)
    if sum(c['area'] >= largest * .2 for c in components) < 6:
        # Detect the sparse cyan valleys between the six visual subjects, then
        # add gutters without dropping source pixels. The bundled component
        # extractor still determines complete pose groups and shared fitting.
        import numpy as np
        ink = (np.asarray(keyed)[:,:,3] > 16).sum(axis=0)
        cuts = [0]
        for i in range(1,6):
            center = round(keyed.width*i/6)
            radius = round(keyed.width/6*.13)
            cut = min(range(center-radius,center+radius),key=lambda x:ink[x])
            assert ink[cut] <= keyed.height*.04, 'substantial source overlap; regenerate row'
            cuts.append(cut)
        cuts.append(keyed.width)
        spaced = Image.new('RGBA',(keyed.width+7*40,keyed.height))
        x=40
        for left,right in zip(cuts,cuts[1:]):
            spaced.paste(keyed.crop((left,0,right,keyed.height)),(x,0))
            x += right-left+40
        source.rename(work / 'decoded' / 'source-touching-tips.png')
        spaced.save(source)
        dump(work/'segmentation.json',{'method':'sparse-alpha-column valleys and added gutters','cuts':cuts,'boundary_ink_pixels':[int(ink[x]) for x in cuts[1:-1]],'source_pixels_removed':0})
    run('extract_strip_frames.py', '--decoded-dir', work / 'decoded', '--output-dir', work / 'frames', '--states', 'idle', '--chroma-key', '#00FFFF', '--method', 'components')
    run('inspect_frames.py', '--frames-root', work / 'frames', '--states', 'idle', '--require-components', '--json-out', work / 'review.json')
    frames = [Image.open(p).convert('RGBA') for p in sorted((work / 'frames' / 'idle').glob('*.png'))]
    if action == 'hair':
        # The source's fourth pose changes hands. Replay the approved lift pose
        # in reverse cadence rather than introducing that inconsistent pose.
        frames = [frames[i] for i in (0,1,2,1,4,0)]
    standing = sum(f.getbbox()[3] - f.getbbox()[1] for f in (frames[0], frames[-1])) / 2
    scale = min((nb[3]-nb[1])/standing, 198/max(f.getbbox()[3]-f.getbbox()[1] for f in frames), 182/max(f.getbbox()[2]-f.getbbox()[0] for f in frames))
    # A single uniform scale and baseline translation per entire generated row.
    baseline = round(sum(f.getbbox()[3] for f in frames)/len(frames))
    registered = []
    for f in frames:
        sized = f.resize((round(192*scale), round(208*scale)), Image.Resampling.LANCZOS)
        cell = Image.new('RGBA', (192,208))
        cell.alpha_composite(sized, ((192-sized.width)//2, nb[3]-round(baseline*scale)))
        registered.append(compose_atlas.clear_transparent_rgb(cell))
    allframes[action] = registered
    registration[action] = {'uniform_scale': scale, 'source_baseline': baseline, 'target_baseline': nb[3]}

# One cleanup pass on newly generated art, leaving all original cells untouched.
packed = Image.new('RGBA', (192*6,208*6))
for row, action in enumerate(ACTIONS):
    for col, f in enumerate(allframes[action]):
        packed.alpha_composite(f, (192*col,208*row))
packed.save(QA / 'new-art-before-cleanup.png')
run('despill_chroma_edges.py', QA / 'new-art-before-cleanup.png', '--output', QA / 'new-art-clean.png', '--chroma-key', '#00FFFF', '--json-out', QA / 'chroma.json')
packed = Image.open(QA / 'new-art-clean.png').convert('RGBA')
for row, action in enumerate(ACTIONS):
    allframes[action] = [packed.crop((192*c,208*row,192*(c+1),208*(row+1))) for c in range(6)]
    out = ROOT / action / 'clean'
    out.mkdir(exist_ok=True)
    for c, f in enumerate(allframes[action]):
        f.save(out / f'{c:02}.png')
dump(QA / 'registration.json', registration)

# Original standard cells are assembled by the bundled compositor. Preserve
# both look rows byte for byte in every frame. Neutral is used in the timeline;
# unused column 6 stays transparent under the bundled v2 atlas contract.
baseframes = QA / 'frames'
for state, row, count in compose_atlas.ROW_SPECS:
    folder = baseframes / state
    folder.mkdir(parents=True, exist_ok=True)
    for col in range(count):
        cell = neutral if row == 0 else original.crop((192*col,208*row,192*(col+1),208*(row+1)))
        cell.save(folder / f'{col:02}.png')
base = compose_atlas.compose_from_frames(baseframes)
template = Image.new('RGBA', original.size)
template.paste(base,(0,0))
template.paste(original.crop((0,1872,1536,2288)), (0,1872))

timeline = [(neutral, 1400, 'neutral')]
timings = [300,320,500,800,350,400]
for action in ACTIONS:
    sequence = list(enumerate(timings))
    if action == 'sleep':
        sequence = [(0,300),(1,450),(2,900),(3,2600),(2,450),(4,450),(5,400)]
    elif action == 'typing':
        sequence = [(0,300),(1,400),(2,450),(3,450),(2,450),(3,450),(2,450),(3,450),(4,400),(5,400)]
    for index, duration in sequence:
        timeline.append((allframes[action][index],duration,action))
    timeline.append((neutral,1100,'neutral'))
atlases=[]
for cell, duration, action in timeline:
    atlas=template.copy()
    for col in range(6):
        atlas.paste(cell,(192*col,0))
    atlases.append(compose_atlas.clear_transparent_rgb(atlas))
dest=FINAL / 'chiyan-six-idles.webp'
# Pillow's animation encoder discards exact=True and colors transparent RGB.
# Mux exact lossless static frame payloads instead. Subsequent rectangles only
# replace the idle row, so original artwork is stored once and remains exact.
def chunk(tag, payload):
    return tag + struct.pack('<I',len(payload)) + payload + (b'\0' if len(payload)%2 else b'')
def u24(number):
    return int(number).to_bytes(3,'little')
body=chunk(b'VP8X',bytes([0x12,0,0,0])+u24(1535)+u24(2287))
body+=chunk(b'ANIM',struct.pack('<IH',0,0))
for index,(atlas,(_,duration,_)) in enumerate(zip(atlases,timeline)):
    frame=atlas if index==0 else atlas.crop((0,0,1152,208))
    stream=io.BytesIO()
    frame.save(stream,format='WEBP',lossless=True,quality=100,method=4,exact=True)
    raw=stream.getvalue()
    payload=b''
    offset=12
    while offset<len(raw):
        tag=raw[offset:offset+4]
        size=struct.unpack_from('<I',raw,offset+4)[0]
        if tag in (b'VP8L',b'VP8 ',b'ALPH'):
            payload+=raw[offset:offset+8+size+(size%2)]
        offset+=8+size+(size%2)
    header=u24(0)+u24(0)+u24(frame.width-1)+u24(frame.height-1)+u24(duration)+bytes([2])
    body+=chunk(b'ANMF',header+payload)
dest.write_bytes(b'RIFF'+struct.pack('<I',len(body)+4)+b'WEBP'+body)
assert dest.stat().st_size <= 20*1024*1024
dump(FINAL / 'timeline.json', {'loop':0,'duration_ms':sum(d for _,d,_ in timeline),'actions':ACTIONS,'source_frames':len(timeline),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'timeline':[{'action':a,'duration_ms':d} for _,d,a in timeline]})

# Preview and verify the final encoded bytes, including every temporal frame.
decoded=[]
durations=[]
with Image.open(dest) as encoded:
    assert encoded.n_frames > 6
    for image in ImageSequence.Iterator(encoded):
        rgba=image.convert('RGBA')
        assert rgba.crop((0,208,1536,2288)).tobytes() == original.crop((0,208,1536,2288)).tobytes()
        decoded.append(rgba.crop((0,0,192,208)))
        durations.append(image.info['duration'])
for index, cell in enumerate(decoded):
    box=cell.getchannel('A').point(lambda v:255 if v>16 else 0).getbbox()
    assert box and box[0]>0 and box[1]>0 and box[2]<192 and box[3]<208, (index,box)
run('inspect_frames.py','--frames-root',baseframes,'--json-out',QA/'review.json')
run('render_animation_previews.py','--frames-root',baseframes,'--output-dir',QA/'previews')
previews.save_preview([background(f) for f in decoded],durations,QA/'previews'/'idle.gif')
previews.save_preview([background(f) for f in decoded],durations,FINAL/'six-idles.gif')
for action in ACTIONS:
    frames=[background(f) for f,d,a in timeline if a==action]
    ds=[d for f,d,a in timeline if a==action]
    previews.save_preview(frames,ds,QA/'previews'/f'{action}.gif')
allstate=list(decoded)
alldurations=list(durations)
for state in previews.ROW_DURATIONS:
    if state!='idle':
        allstate.extend(previews.load_frames(baseframes,state,len(previews.ROW_DURATIONS[state])))
        alldurations.extend(previews.ROW_DURATIONS[state])
previews.save_preview([background(f) for f in allstate],alldurations,QA/'previews'/'all-states.gif')
jump=previews.load_frames(baseframes,'jumping',5)
previews.save_preview([background(neutral),*[background(f) for f in jump],background(neutral)],[1000,*previews.ROW_DURATIONS['jumping'],1000],QA/'previews'/'idle-jump-idle.gif')
looks=[original.crop((192*(i%8),208*(9+i//8),192*(i%8+1),208*(10+i//8))) for i in range(16)]
previews.save_preview([background(f) for f in looks],[180]*16,QA/'previews'/'look-loop.gif')
contact=Image.new('RGB',(1152,6*232),'#e5e7ed')
draw=ImageDraw.Draw(contact)
for row,action in enumerate(ACTIONS):
    draw.text((5,232*row+4),action,fill='black')
    for col,f in enumerate(allframes[action]):
        contact.paste(background(f),(192*col,232*row+24))
contact.save(FINAL/'six-idles-contact.png')
sys.path.insert(0,str(ROOT/'vendor'))
import imageio_ffmpeg
writer=imageio_ffmpeg.write_frames(str(QA/'previews'/'all-states.mp4'), (192,208), fps=20, codec='libx264', pix_fmt_in='rgb24', pix_fmt_out='yuv420p', macro_block_size=1)
writer.send(None)
for frame,duration in zip(allstate,alldurations):
    data=background(frame).tobytes()
    for _ in range(max(1,round(duration/50))):
        writer.send(data)
writer.close()
run('validate_atlas.py',dest,'--require-v2','--chroma-key','#00FFFF','--json-out',QA/'atlas-validation.json')
run('make_contact_sheet.py',dest,'--output',QA/'contact.png')
run('make_direction_qa_sheet.py',dest,'--output',QA/'directions.png')
run('measure_direction_continuity.py',dest,'--json-out',QA/'continuity.json')
run('validate_pet_quality.py',dest,'--atlas-validation',QA/'atlas-validation.json','--chroma-report',QA/'chroma.json','--frame-review',QA/'review.json','--direction-semantics',REPO/'codex-pet'/'chiyan'/'qa'/'direction-semantics.json','--continuity',QA/'continuity.json','--json-out',QA/'pet-quality.json')
dump(QA/'temporal-validation.json',{'frames':len(decoded),'unchanged_rows_preserved':True,'jump_registration_restored':True,'cell_bounds_passed':True,'decoded_duration_ms':sum(durations)})
print('FINAL',dest,'bytes',dest.stat().st_size,'frames',len(decoded),'duration',sum(durations),flush=True)
