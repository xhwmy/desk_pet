"""Repair only the waving/jumping rows using generated strips and official tools."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
QA = ROOT / 'qa'
QA.mkdir(exist_ok=True)
cache = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'plugins/cache'
candidates = list(cache.glob('*/work-pets/*/skills/create-pet/scripts'))
SCRIPTS = Path(os.environ['WORK_PETS_SCRIPTS']) if os.environ.get('WORK_PETS_SCRIPTS') else max(candidates, key=lambda p: p.stat().st_mtime)
sys.path.insert(0, str(SCRIPTS))
import compose_atlas
import render_animation_previews as previews


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def run(script, *args):
    result = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True)
    (QA / (script + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    print(script, 'passed', flush=True)


def bounds(image):
    return image.getchannel('A').point(lambda a: 255 if a > 16 else 0).getbbox()


def background(image):
    bg = Image.new('RGBA', image.size, '#e5e7ed')
    bg.alpha_composite(image)
    return bg.convert('RGB')


before = Image.open(ROOT / 'before.png').convert('RGBA')
run('extract_strip_frames.py', '--decoded-dir', ROOT / 'decoded', '--output-dir', ROOT / 'extracted',
    '--states', 'waving,jumping', '--chroma-key', '#00FFFF', '--method', 'components')
run('inspect_frames.py', '--frames-root', ROOT / 'extracted', '--states', 'waving,jumping',
    '--require-components', '--json-out', QA / 'source-review.json')
atlas = before.copy()
registration = {}
for state, row, count in [('waving', 3, 4), ('jumping', 4, 5)]:
    frames = [Image.open(ROOT / 'extracted' / state / f'{i:02}.png').convert('RGBA') for i in range(count)]
    boxes = [bounds(frame) for frame in frames]
    # A single transform per whole row. Preserve the original airborne offsets;
    # only the shared ground is registered, never pin every foot to the floor.
    ground = max(box[3] for box in boxes)
    scale = min(1.03, 201 / (ground - min(box[1] for box in boxes))) if state == 'jumping' else 1.0
    scaled_size = (round(192 * scale), round(208 * scale))
    shift = (round((192 - scaled_size[0]) / 2), 203 - round(ground * scale))
    packed = Image.new('RGBA', (count * 192, 208))
    for i, frame in enumerate(frames):
        sized = frame.resize(scaled_size, Image.Resampling.LANCZOS) if scale != 1 else frame
        cell = Image.new('RGBA', (192, 208))
        cell.alpha_composite(sized, shift)
        packed.paste(cell, (i * 192, 0))
    raw, clean = QA / f'{state}-raw.png', QA / f'{state}-clean.png'
    packed.save(raw)
    run('despill_chroma_edges.py', raw, '--output', clean, '--chroma-key', '#00FFFF',
        '--json-out', QA / f'{state}-chroma.json')
    atlas.paste(Image.open(clean).convert('RGBA'), (0, row * 208))
    registration[state] = {'shared_scale': scale, 'translation': shift, 'source_bounds': boxes}

dump(QA / 'registration.json', registration)
# Combine the two actual cleanup reports for the final quality gate.
reports = [json.loads((QA / f'{state}-chroma.json').read_text(encoding='utf-8')) for state in ('waving', 'jumping')]
chroma = {'ok': all(report['ok'] for report in reports),
          'alpha_preserved': all(report['alpha_preserved'] for report in reports),
          'algorithm': 'edge-local-chroma-spill-suppression',
          'changed_pixels': sum(report['changed_pixels'] for report in reports),
          'row_reports': reports}
dump(QA / 'chroma.json', chroma)
destination = ROOT / 'chiyan-native-motion.webp'
compose_atlas.save_outputs(atlas, ROOT / 'chiyan-native-motion.png', destination)
encoded = Image.open(destination).convert('RGBA')
for row in (0, 1, 2, 5, 6, 7, 8, 9, 10):
    assert encoded.crop((0, row * 208, 1536, (row + 1) * 208)).tobytes() == before.crop((0, row * 208, 1536, (row + 1) * 208)).tobytes()

frames_root = QA / 'frames'
state_frames = {}
for row, (state, timings) in enumerate(previews.ROW_DURATIONS.items()):
    folder = frames_root / state
    folder.mkdir(parents=True, exist_ok=True)
    frames = [encoded.crop((192 * i, row * 208, 192 * (i + 1), (row + 1) * 208)) for i in range(len(timings))]
    for i, frame in enumerate(frames):
        frame.save(folder / f'{i:02}.png')
    state_frames[state] = frames
run('inspect_frames.py', '--frames-root', frames_root, '--json-out', QA / 'frame-review.json')
run('validate_atlas.py', destination, '--require-v2', '--chroma-key', '#00FFFF', '--json-out', QA / 'atlas-validation.json')
run('make_contact_sheet.py', destination, '--output', QA / 'contact.png')
run('make_direction_qa_sheet.py', destination, '--output', QA / 'directions.png')
run('measure_direction_continuity.py', destination, '--json-out', QA / 'continuity.json')
run('validate_pet_quality.py', destination, '--atlas-validation', QA / 'atlas-validation.json',
    '--chroma-report', QA / 'chroma.json', '--frame-review', QA / 'frame-review.json',
    '--direction-semantics', REPO / 'codex-pet/chiyan/qa/direction-semantics.json',
    '--continuity', QA / 'continuity.json', '--json-out', QA / 'pet-quality.json')
run('render_animation_previews.py', '--frames-root', frames_root, '--output-dir', ROOT / 'previews')
# Match the installed client's slower idle cadence; task rows use official timings.
durations = dict(previews.ROW_DURATIONS)
durations['idle'] = [1680, 660, 660, 840, 840, 1920]
out = ROOT / 'previews'
previews.save_preview([background(f) for f in state_frames['idle']], durations['idle'], out / 'idle.gif')
previews.save_preview([background(state_frames['idle'][0]), *[background(f) for f in state_frames['jumping']], background(state_frames['idle'][0])],
                      [1000, *durations['jumping'], 1000], out / 'idle-jump-idle.gif')
looks = [encoded.crop((i % 8 * 192, (9 + i // 8) * 208, (i % 8 + 1) * 192, (10 + i // 8) * 208)) for i in range(16)]
previews.save_preview([background(f) for f in looks], [180] * 16, out / 'look-loop.gif')
all_frames, all_durations = [], []
for state, frames in state_frames.items():
    all_frames.extend(background(f) for f in frames)
    all_durations.extend(durations[state])
previews.save_preview(all_frames, all_durations, out / 'all-states.gif')
try:
    import imageio_ffmpeg
except ModuleNotFoundError:
    sys.path.insert(0, str(REPO / 'animations/idle-six/vendor'))
    import imageio_ffmpeg
writer = imageio_ffmpeg.write_frames(str(out / 'all-states.mp4'), (192, 208), fps=20, codec='libx264',
    pix_fmt_in='rgb24', pix_fmt_out='yuv420p', macro_block_size=1)
writer.send(None)
for frame, duration in zip(all_frames, all_durations):
    for _ in range(max(1, round(duration / 50))):
        writer.send(frame.tobytes())
writer.close()
stills = Image.new('RGB', (6 * 192, 232), '#e5e7ed')
draw = ImageDraw.Draw(stills)
for i, frame in enumerate([state_frames['idle'][0], *state_frames['jumping']]):
    stills.paste(background(frame), (192 * i, 24))
    draw.text((192 * i + 5, 5), ['Idle', 'Anticipation', 'Push', 'Apex', 'Descent', 'Rest'][i], fill='black')
stills.save(ROOT / 'jump-stills.png')
dump(ROOT / 'timeline.json', {'changed_rows': ['waving', 'jumping'], 'native_idle_preserved': True,
    'look_rows_preserved': True, 'client_modified': False, 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
    'bytes': destination.stat().st_size, 'timings_ms': durations})
print(destination)
