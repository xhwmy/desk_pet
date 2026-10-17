"""Frame mapping for the exact v2 sprite sheet used by Codex pet 赤焰."""

import math

CELL_WIDTH = 192
CELL_HEIGHT = 208
COLUMNS = 8
ROWS = 11
FRAME_ROWS = {
    'idle': (0, 6),
    'running-right': (1, 8),
    'running-left': (2, 8),
    'waving': (3, 4),
    'jumping': (4, 5),
    'failed': (5, 8),
    'waiting': (6, 6),
    'running': (7, 6),
    'review': (8, 6),
}


def cell_rect(state, frame):
    row, count = FRAME_ROWS[state]
    column = frame % count
    return (column * CELL_WIDTH, row * CELL_HEIGHT, CELL_WIDTH, CELL_HEIGHT)


def look_frame(dx, dy):
    """Return the row and column for a 16-way look direction."""
    degrees = math.degrees(math.atan2(dx, -dy)) % 360
    index = round(degrees / 22.5) % 16
    return (9 + index // COLUMNS, index % COLUMNS)


def step_toward(current, target, speed):
    dx, dy = target[0] - current[0], target[1] - current[1]
    distance = math.hypot(dx, dy)
    if distance <= speed:
        return target
    def component(delta):
        if not delta:
            return 0
        amount = max(1, round(abs(delta) / distance * speed))
        return int(math.copysign(min(abs(delta), amount), delta))
    return current[0] + component(dx), current[1] + component(dy)
