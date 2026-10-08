from pathlib import Path
import importlib.util
import json
from PIL import Image

script = Path(r"C:\Users\windows\.codex\skills\hatch-pet\scripts\assemble_extended_atlas.py")
spec = importlib.util.spec_from_file_location("atlas", script)
atlas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atlas)
root = Path(r"D:\deskpet\codex-pet\chiyan")
base = Image.open(root / "final/spritesheet.webp").convert("RGBA")
neutral = atlas.base_neutral_cell(base)
target = atlas.cell_geometry(neutral)
scale = json.loads((root / "qa/look-row-9-registration.json").read_text())["scale"]
for file in [
    root / "decoded/look-row-10-failed.png",
    Path(r"C:\Users\windows\.codex\generated_images\01a0e803-c0bf-77a3-b2d2-c52bf86080e3\exec-a0ee3d16-59a9-4ad8-bfa3-d32c88cba323.png"),
    root / "decoded/look-row-10.png",
]:
    cells = atlas.extract_row_strip_cells(file, (0, 255, 255), 96)
    print(file)
    print('neutral', target.height, round(target.lower_center_x, 1), target.bottom, 'scale', round(scale, 4))
    for i, cell in enumerate(cells):
        geo = atlas.cell_geometry(cell)
        box = cell.getbbox()
        norm = atlas.normalize_cell_to_geometry(cell, target, scale)
        a = norm.getchannel("A")
        w, h = a.size
        edges = [sum(a.crop(b).histogram()[1:]) for b in [(0, 0, w, 2), (0, h-2, w, h), (0, 0, 2, h), (w-2, 0, w, h)]]
        print(atlas.LOOK_DIRECTION_LABELS[i+8], 'source', cell.size, box, 'height', geo.height, 'lowerx', round(geo.lower_center_x,1), 'norm', norm.getbbox(), 'edges', edges)
