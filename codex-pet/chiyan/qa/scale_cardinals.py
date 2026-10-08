from PIL import Image

src = r"D:\deskpet\codex-pet\chiyan\decoded\look-cardinals.png"
dst = r"D:\deskpet\codex-pet\chiyan\decoded\look-cardinals-safe.png"
with Image.open(src).convert("RGBA") as image:
    canvas = Image.new("RGBA", image.size, (0, 0, 0, 0))
    slot_width = image.width / 4
    for index in range(4):
        left = round(index * slot_width)
        right = round((index + 1) * slot_width)
        cell = image.crop((left, 0, right, image.height))
        bbox = cell.getbbox()
        if bbox is None:
            continue
        sprite = cell.crop(bbox)
        scale = 0.72
        sprite = sprite.resize((round(sprite.width * scale), round(sprite.height * scale)), Image.Resampling.LANCZOS)
        x = left + (right - left - sprite.width) // 2
        y = (image.height - sprite.height) // 2
        canvas.alpha_composite(sprite, (x, y))
    canvas.save(dst)
