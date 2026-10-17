"""Verify the exact native atlas and, when required, its fresh server readback."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parent


def check(require_readback=False):
    path = ROOT / 'chiyan-native-motion.webp'
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    with Image.open(path) as source:
        static = source.n_frames == 1
        atlas = source.convert('RGBA')
    before = Image.open(ROOT / 'before.png').convert('RGBA')

    def box(image):
        return image.getchannel('A').point(lambda a: 255 if a > 16 else 0).getbbox()

    def cell(image, row, column):
        return image.crop((column * 192, row * 208, (column + 1) * 192, (row + 1) * 208))

    idle_height = box(cell(atlas, 0, 0))[3] - box(cell(atlas, 0, 0))[1]
    old_rest = box(cell(before, 4, 4))
    rest = box(cell(atlas, 4, 4))
    jump_boxes = [box(cell(atlas, 4, i)) for i in range(5)]
    wave_boxes = [box(cell(atlas, 3, i)) for i in range(4)]
    read = lambda name: json.loads((ROOT / 'qa' / name).read_text(encoding='utf-8'))
    checks = {
        'static_v2_atlas': static and atlas.size == (1536, 2288),
        'untouched_rows_preserved': all(atlas.crop((0, r * 208, 1536, (r + 1) * 208)).tobytes() ==
            before.crop((0, r * 208, 1536, (r + 1) * 208)).tobytes() for r in (0, 1, 2, 5, 6, 7, 8, 9, 10)),
        'unused_cells_preserved': all(cell(atlas, r, i).tobytes() == cell(before, r, i).tobytes()
            for r, count in ((3, 4), (4, 5)) for i in range(count, 8)),
        'both_repaired_rows_changed': all(atlas.crop((0, r * 208, 1536, (r + 1) * 208)).tobytes() !=
            before.crop((0, r * 208, 1536, (r + 1) * 208)).tobytes() for r in (3, 4)),
        'safe_frame_edges': all(b and b[0] > 0 and b[1] > 0 and b[2] < 192 and b[3] < 208 for b in jump_boxes + wave_boxes),
        'wave_feet_share_idle_baseline': all(b[3] == 203 for b in wave_boxes),
        'jump_lands_on_idle_baseline': rest[3] == 203,
        'jump_leaves_ground': 203 - min(b[3] for b in jump_boxes) >= 8,
        'landing_height_at_least_95_percent_of_idle': (rest[3] - rest[1]) / idle_height >= .95,
        'landing_height_improved_at_least_10_pixels': (rest[3] - rest[1]) - (old_rest[3] - old_rest[1]) >= 10,
        'distinct_wave_frames': len({cell(atlas, 3, i).tobytes() for i in range(4)}) == 4,
        'distinct_jump_frames': len({cell(atlas, 4, i).tobytes() for i in range(5)}) == 5,
        'official_preflight_valid': read('official-preflight.json')['valid'],
        'source_review_passed': read('source-review.json')['ok'],
        'frame_review_passed': read('frame-review.json')['ok'],
        'atlas_gate_matches_final_bytes': read('atlas-validation.json')['ok'] and read('atlas-validation.json')['sha256'] == sha,
        'quality_gate_matches_final_bytes': read('pet-quality.json')['ok'] and read('pet-quality.json')['sha256'] == sha,
        'timeline_matches_final_bytes': json.loads((ROOT / 'timeline.json').read_text())['sha256'] == sha,
    }
    for state, count in (('waving', 4), ('jumping', 5), ('idle', 6)):
        with Image.open(ROOT / 'previews' / (state + '.gif')) as preview:
            checks[state + '_preview_frames'] = preview.n_frames == count
            if state == 'idle':
                checks['native_idle_6600ms'] = sum(f.info['duration'] for f in ImageSequence.Iterator(preview)) == 6600
    if require_readback:
        remote = Image.open(ROOT / 'stored-readback.png').convert('RGBA')
        checks['stored_pixels_match_final'] = remote.size == atlas.size and remote.tobytes() == atlas.tobytes()
    report = {'ok': all(checks.values()), 'checks': checks, 'sha256': sha,
              'pet_id': 'pet_6abb898c7228819191b6e896f2538d5d', 'client_modified': False,
              'idle_height': idle_height, 'old_jump_landing_height': old_rest[3] - old_rest[1],
              'new_jump_landing_height': rest[3] - rest[1], 'jump_bounds': jump_boxes,
              'readback_required': require_readback}
    (ROOT / 'qa' / ('self-check-stored.json' if require_readback else 'self-check.json')).write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return report['ok']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-readback', action='store_true')
    args = parser.parse_args()
    raise SystemExit(0 if check(args.require_readback) else 1)
