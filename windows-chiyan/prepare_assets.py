"""Copy existing approved artwork; never regenerate or rescale individual poses."""
import argparse
import json
from pathlib import Path
import shutil


def prepare(source_root, destination):
    source_root, destination = Path(source_root), Path(destination)
    shutil.copyfile(source_root / 'animations/idle-breath-2026-10-16/chiyan-native-breath.png',
                    destination / 'spritesheet.png')
    manifest = {}
    for action in ('hair', 'collar', 'sleep', 'stretch', 'typing', 'peek'):
        target = destination / 'actions' / action
        target.mkdir(parents=True, exist_ok=True)
        source = source_root / 'animations/idle-six' / action / 'clean'
        for i in range(6):
            shutil.copyfile(source / f'{i:02}.png', target / f'{i:02}.png')
        sequence = list(enumerate([300, 320, 500, 800, 350, 400]))
        if action == 'sleep':
            sequence = [(0, 300), (1, 450), (2, 900), (3, 2600), (2, 450), (4, 450), (5, 400)]
        elif action == 'typing':
            sequence = [(0, 300), (1, 400), (2, 450), (3, 450), (2, 450),
                        (3, 450), (2, 450), (3, 450), (4, 400), (5, 400)]
        manifest[action] = {'frames': [f'{action}/{i:02}.png' for i, _ in sequence],
                            'durations_ms': [duration for _, duration in sequence]}
    (destination / 'actions/clips.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    prepare(args.source_root, Path(__file__).resolve().parent / 'assets')
