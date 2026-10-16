"""Verify the calm replacement against freshly downloaded cloud bytes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'calm'
native_path = OUT/'chiyan-native-calm.webp'
native = Image.open(native_path).convert('RGBA')
remote = Image.open(OUT/'stored-readback.png').convert('RGBA')
before = Image.open(ROOT.parent/'idle-timing-review'/'before-update.png').convert('RGBA')
original = Image.open(ROOT/'original.webp').convert('RGBA')
sha = hashlib.sha256(native_path.read_bytes()).hexdigest()
read = lambda name: json.loads((OUT/name).read_text(encoding='utf8'))
checks = {
    'v2_dimensions':native.size == (1536,2288),
    'stored_pixels_equal_final_atlas':native.tobytes() == remote.tobytes(),
    'idle_matches_approved_coherent_sequence':native.crop((0,0,1152,208)).tobytes() == original.crop((0,0,1152,208)).tobytes(),
    'all_non_idle_rows_unchanged':native.crop((0,208,1536,2288)).tobytes() == before.crop((0,208,1536,2288)).tobytes(),
    'unused_idle_cells_unchanged':native.crop((1152,0,1536,208)).tobytes() == before.crop((1152,0,1536,208)).tobytes(),
    'timeline_matches_current_bytes':read('timeline.json')['sha256'] == sha,
    'official_preflight_passed':read('official-preflight.json')['valid'],
}
for name in ['atlas-validation','pet-quality']:
    report = read(name+'.json')
    checks[name+'_passes_exact_bytes'] = report['ok'] and report['sha256'] == sha
cells = [native.crop((i*192,0,(i+1)*192,208)) for i in range(6)]
boxes = [c.getchannel('A').point(lambda a:255 if a>16 else 0).getbbox() for c in cells]
checks['steady_idle_ground_contact'] = max(b[3] for b in boxes)-min(b[3] for b in boxes) <= 1
checks['idle_includes_blink_variation'] = len({c.tobytes() for c in cells}) >= 4
with Image.open(OUT/'previews'/'idle.gif') as preview:
    duration = 0
    for frame in ImageSequence.Iterator(preview):
        frame.load()
        duration += frame.info['duration']
    checks['preview_matches_native_6600ms_cycle'] = duration == 6600 and preview.info.get('loop') == 0
checks['all_state_video_exists'] = (OUT/'previews'/'all-states.mp4').stat().st_size > 1000
report = {'ok':all(checks.values()), 'checked_at_utc':datetime.now(timezone.utc).isoformat(), 'checks':checks, 'sha256':sha, 'pet_id':'pet_6abb898c7228819191b6e896f2538d5d', 'native_mode':'calm continuous idle; 30-second random actions unsupported', 'client_modified':False}
(OUT/'self-check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['ok'] else 1)
