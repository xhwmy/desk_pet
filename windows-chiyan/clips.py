"""Load the built-in atlas and optional complete keyframe action clips."""
import json
from pathlib import Path
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QPixmap
from motion_model import ClipClock
from sprite_model import CELL_HEIGHT, CELL_WIDTH, COLUMNS, FRAME_ROWS, ROWS, cell_rect

IDLE_TIMINGS = (1.68, .66, .66, .84, .84, 1.92)


def load_clips(asset_dir, width, height):
    asset_dir = Path(asset_dir)
    sheet = QPixmap(str(asset_dir / 'spritesheet.png'))
    if sheet.isNull() or sheet.width() != COLUMNS * CELL_WIDTH or sheet.height() != ROWS * CELL_HEIGHT:
        raise RuntimeError('赤焰精灵图丢失或尺寸不正确')

    def scaled(pixmap):
        return pixmap.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

    frames, timings = {}, {}
    for state, (_, count) in FRAME_ROWS.items():
        frames[state] = [scaled(sheet.copy(QRect(*cell_rect(state, i)))) for i in range(count)]
        timings[state] = IDLE_TIMINGS if state == 'idle' else tuple(.16 for _ in range(count))
    looks = [scaled(sheet.copy(QRect((i % 8) * CELL_WIDTH, (9 + i // 8) * CELL_HEIGHT,
                                    CELL_WIDTH, CELL_HEIGHT))) for i in range(16)]
    warnings = []
    manifest_path = asset_dir / 'actions' / 'clips.json'
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            if not isinstance(manifest, dict):
                raise ValueError('Expected an action map')
        except (OSError, ValueError) as error:
            manifest = {}
            warnings.append(f'Action manifest: {error}')
        for name, clip in manifest.items():
            try:
                if name in frames:
                    raise ValueError('Cannot override built-in actions')
                durations = [ms / 1000 for ms in clip['durations_ms']]
                ClipClock(durations)
                paths = clip['frames']
                if len(paths) != len(durations) or len(paths) > 600:
                    raise ValueError('Frame count and duration count must match (maximum 600)')
                loaded = []
                root = manifest_path.parent.resolve()
                for relative in paths:
                    path = (root / relative).resolve()
                    if not path.is_relative_to(root):
                        raise ValueError('Frame path escapes the action directory')
                    frame = QPixmap(str(path))
                    if frame.isNull() or frame.width() != CELL_WIDTH or frame.height() != CELL_HEIGHT:
                        raise ValueError(f'Invalid action frame: {relative}')
                    loaded.append(scaled(frame))
                frames[name], timings[name] = loaded, durations
            except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as error:
                warnings.append(f'{name}: {error}')
    return frames, timings, looks, warnings
