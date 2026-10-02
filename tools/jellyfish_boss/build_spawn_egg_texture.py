from math import pi, sin
from pathlib import Path
from random import Random

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "resource_pack/textures/items/jellyfish_boss_spawn_egg.png"
SCALE = 4
SIZE = 32
W = SIZE * SCALE
rng = Random(15015)

mask = Image.new("L", (W, W), 0)
pixels = mask.load()
for y in range(8, 120):
    t = (y - 8) / 112
    half = (sin(pi * t) ** 0.72) * (38 + 13 * t)
    for x in range(W):
        if abs(x - 64) <= half:
            pixels[x, y] = 255

base = Image.new("RGBA", (W, W), (0, 0, 0, 0))
base_pixels = base.load()
for y in range(W):
    for x in range(W):
        if pixels[x, y]:
            edge = abs(x - 64) / 52
            light = max(0, 1 - edge)
            base_pixels[x, y] = (
                int(4 + 8 * light),
                int(13 + 25 * light),
                int(25 + 39 * light),
                255,
            )

pattern = Image.new("RGBA", (W, W), (0, 0, 0, 0))
draw = ImageDraw.Draw(pattern)
for _ in range(34):
    x = rng.randint(25, 103)
    y = rng.randint(25, 111)
    r = rng.randint(3, 10)
    color = rng.choice([
        (42, 222, 236, rng.randint(90, 185)),
        (210, 38, 167, rng.randint(65, 150)),
        (64, 100, 160, rng.randint(45, 110)),
    ])
    draw.ellipse((x-r, y-r, x+r, y+r), fill=color)
pattern = pattern.filter(ImageFilter.GaussianBlur(2.2))
pattern.putalpha(Image.composite(pattern.getchannel("A"), Image.new("L", (W, W), 0), mask))
base = Image.alpha_composite(base, pattern)

shine = Image.new("RGBA", (W, W), (0, 0, 0, 0))
sdraw = ImageDraw.Draw(shine)
sdraw.ellipse((37, 20, 57, 65), fill=(150, 245, 255, 105))
sdraw.arc((18, 8, 109, 122), 115, 245, fill=(64, 231, 244, 220), width=4)
sdraw.arc((22, 12, 105, 120), 285, 65, fill=(235, 50, 186, 180), width=3)
shine.putalpha(Image.composite(shine.getchannel("A"), Image.new("L", (W, W), 0), mask))
base = Image.alpha_composite(base, shine)

outline = Image.new("RGBA", (W, W), (0, 0, 0, 0))
odraw = ImageDraw.Draw(outline)
odraw.bitmap((0, 0), mask.filter(ImageFilter.FIND_EDGES), fill=(2, 5, 12, 220))
base = Image.alpha_composite(base, outline)
base = base.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
base.save(OUTPUT)
print(f"WROTE {OUTPUT}")