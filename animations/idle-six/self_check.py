"""Check the built artifacts and a freshly downloaded native sprite sheet.

Run build_loops.py and build_native.py first. This script is read-only except
for its JSON report; it never uploads or changes the selected desktop pet.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parent
FINAL = ROOT / 'final'
checks = {}

def read(path):
    return json.loads(path.read_text(encoding='utf8'))

native_path = FINAL / 'chiyan-native-six-poses.webp'
animated_path = FINAL / 'chiyan-six-idles.webp'
native = Image.open(native_path).convert('RGBA')
remote = Image.open(FINAL / 'native-stored-readback.png').convert('RGBA')
checks['native_dimensions'] = native.size == (1536,2288)
checks['installed_pixels_equal_native_artifact'] = native.tobytes() == remote.tobytes()
checks['native_timeline_hash_matches'] = read(FINAL/'native-timeline.json')['sha256'] == hashlib.sha256(native_path.read_bytes()).hexdigest()
cells = [native.crop((i*192,0,(i+1)*192,208)) for i in range(6)]
checks['six_distinct_native_poses'] = len({c.tobytes() for c in cells}) == 6
actions = ['hair','collar','sleep','stretch','typing','peek']
indices = [2,2,3,3,3,2]
checks['all_six_actions_in_native_slots'] = all(c.tobytes() == Image.open(ROOT/a/'clean'/f'{i:02}.png').convert('RGBA').tobytes() for c,a,i in zip(cells,actions,indices))
checks['all_six_source_reviews_pass'] = all(read(ROOT/a/'review.json')['ok'] for a in actions)
for folder in [ROOT/'qa',ROOT/'qa'/'native']:
    for name in ['atlas-validation','pet-quality']:
        report = read(folder/(name+'.json'))
        path = animated_path if folder.name == 'qa' else native_path
        checks[f'{folder.name}_{name}_passes_current_bytes'] = report['ok'] and report['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
checks['official_native_preflight_passes'] = read(ROOT/'qa'/'native'/'official-preflight.json')['valid']
original = Image.open(ROOT/'original.webp').convert('RGBA')
checks['sixteen_look_directions_preserved'] = native.crop((0,1872,1536,2288)).tobytes() == original.crop((0,1872,1536,2288)).tobytes()
with Image.open(animated_path) as animation:
    checks['full_animation_has_48_frames_and_loops_forever'] = animation.n_frames == 48 and animation.info.get('loop') == 0
    baseline = native.crop((0,208,1536,2288)).tobytes()
    duration = 0
    stable = True
    for frame in ImageSequence.Iterator(animation):
        frame.load()
        duration += frame.info['duration']
        stable = stable and frame.convert('RGBA').crop((0,208,1536,2288)).tobytes() == baseline
    checks['full_animation_duration_28430ms'] = duration == 28430
    checks['all_task_rows_stable_across_entire_animation'] = stable
with Image.open(FINAL/'native-six-poses.gif') as preview:
    count = preview.n_frames
    duration = 0
    for frame in ImageSequence.Iterator(preview):
        frame.load()
        duration += frame.info['duration']
    checks['native_preview_has_six_poses_and_6600ms_cycle'] = count == 6 and duration == 6600
checks['all_state_video_and_gif_exist'] = all((ROOT/'qa'/'previews'/('all-states.'+suffix)).stat().st_size > 1000 for suffix in ['gif','mp4'])
report = {'ok':all(checks.values()),'checked_at_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'native_sha256':hashlib.sha256(native_path.read_bytes()).hexdigest(),'full_animation_sha256':hashlib.sha256(animated_path.read_bytes()).hexdigest(),'native_mode':'six key poses; complete continuous animation remains a preview artifact'}
(ROOT/'qa'/'self-check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['ok'] else 1)
