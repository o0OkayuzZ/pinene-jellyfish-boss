import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


SIZE = 512


def noise_image(seed, coarse, blur=0.0):
    rng = random.Random(seed)
    data = [rng.randrange(256) for _ in range(coarse * coarse)]
    image = Image.new("L", (coarse, coarse))
    image.putdata(data)
    image = image.resize((SIZE, SIZE), Image.Resampling.BICUBIC)
    if blur:
        image = image.filter(ImageFilter.GaussianBlur(blur))
    return image


def clamp(value):
    return max(0, min(255, int(round(value))))


def color_texture(role, coarse, fine):
    out = Image.new("RGBA", (SIZE, SIZE))
    dst = out.load()
    cpx = coarse.load()
    fpx = fine.load()
    for y in range(SIZE):
        v = y / (SIZE - 1)
        for x in range(SIZE):
            u = x / (SIZE - 1)
            n = cpx[x, y] / 255.0
            f = fpx[x, y] / 255.0
            wave = 0.5 + 0.5 * math.sin(
                math.tau * (u * 3.0 + 0.18 * math.sin(v * math.tau * 2.0))
            )
            if role == "shell":
                burgundy = max(0.0, wave - 0.70) * (0.35 + 0.65 * (1.0 - v))
                wet = max(0.0, f - 0.68)
                dst[x, y] = (
                    clamp(1 + 11 * n + 34 * burgundy + 6 * wet),
                    clamp(3 + 17 * n + 4 * wet),
                    clamp(7 + 25 * n + 26 * burgundy + 10 * wet),
                    clamp(203 + 31 * n),
                )
            elif role == "tissue":
                vein = 0.5 + 0.5 * math.sin(math.tau * (u * 5.0 - v * 2.3) + n * 4.0)
                hot = max(0.0, f - 0.52) * vein
                dst[x, y] = (
                    clamp(20 + 92 * n + 92 * hot),
                    clamp(2 + 8 * n + 10 * hot),
                    clamp(18 + 62 * n + 78 * hot),
                    255,
                )
            else:
                pulse = 0.70 + 0.30 * math.sin(math.tau * (u * 2.0 + v * 1.2) + n)
                dst[x, y] = (
                    clamp(8 + 45 * f),
                    clamp(178 + 72 * n * pulse),
                    clamp(212 + 43 * f),
                    clamp(220 + 35 * n),
                )
    return out


def mers_texture(role, coarse, fine):
    out = Image.new("RGBA", (SIZE, SIZE))
    dst = out.load()
    cpx = coarse.load()
    fpx = fine.load()
    for y in range(SIZE):
        for x in range(SIZE):
            n = cpx[x, y] / 255.0
            f = fpx[x, y] / 255.0
            if role == "shell":
                dst[x, y] = (0, clamp(2 + 10 * max(0.0, f - 0.72)), clamp(42 + 34 * n), clamp(168 + 58 * f))
            elif role == "tissue":
                dst[x, y] = (0, clamp(15 + 55 * max(0.0, f - 0.48)), clamp(62 + 42 * n), clamp(88 + 76 * f))
            else:
                dst[x, y] = (0, 255, clamp(44 + 24 * n), clamp(44 + 42 * f))
    return out


def normal_texture(height, strength):
    src = height.load()
    out = Image.new("RGBA", (SIZE, SIZE), (128, 128, 255, 255))
    dst = out.load()
    for y in range(SIZE):
        ym = max(0, y - 1)
        yp = min(SIZE - 1, y + 1)
        for x in range(SIZE):
            xm = max(0, x - 1)
            xp = min(SIZE - 1, x + 1)
            dx = (src[xp, y] - src[xm, y]) * strength
            dy = (src[x, yp] - src[x, ym]) * strength
            nx, ny, nz = -dx, -dy, 255.0
            length = math.sqrt(nx * nx + ny * ny + nz * nz)
            dst[x, y] = (
                clamp(128 + 127 * nx / length),
                clamp(128 + 127 * ny / length),
                clamp(128 + 127 * nz / length),
                255,
            )
    return out


def write_texture_set(folder, role):
    stem = f"jellyfish_boss_{role}"
    payload = {
        "format_version": "1.21.30",
        "minecraft:texture_set": {
            "color": stem,
            "normal": f"{stem}_normal",
            "metalness_emissive_roughness_subsurface": f"{stem}_mers",
        },
    }
    path = folder / f"{stem}.texture_set.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def contact_sheet(textures, output):
    tile = 220
    margin = 24
    label_h = 26
    canvas = Image.new("RGB", (margin * 2 + tile * 3, margin * 2 + (tile + label_h) * 3), (12, 13, 18))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    columns = ("COLOR", "NORMAL", "MERS (A=SSS)")
    roles = ("shell", "tissue", "glow")
    for col, title in enumerate(columns):
        draw.text((margin + col * tile + 5, 5), title, fill=(225, 232, 240), font=font)
    for row, role in enumerate(roles):
        y = margin + row * (tile + label_h)
        draw.text((5, y + 5), role.upper(), fill=(120, 225, 240), font=font)
        for col, kind in enumerate(("color", "normal", "mers")):
            image = textures[(role, kind)].convert("RGB").resize((tile, tile), Image.Resampling.LANCZOS)
            canvas.paste(image, (margin + col * tile, y))
        draw.text((margin, y + tile + 5), f"{role}: 512x512", fill=(170, 176, 190), font=font)
    canvas.save(output)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python build_jellyfish_textures.py OUTPUT_DIR")
    folder = Path(sys.argv[1]).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    textures = {}
    role_settings = {
        "shell": (17, 41, 0.55),
        "tissue": (29, 53, 0.78),
        "glow": (71, 89, 0.20),
    }
    for role, (coarse_seed, fine_seed, strength) in role_settings.items():
        coarse = noise_image(coarse_seed, 34, 1.2)
        fine = noise_image(fine_seed, 112, 0.35)
        color = color_texture(role, coarse, fine)
        mers = mers_texture(role, coarse, fine)
        normal = normal_texture(fine if role != "shell" else coarse, strength)
        stem = f"jellyfish_boss_{role}"
        color.save(folder / f"{stem}.png", optimize=True)
        mers.save(folder / f"{stem}_mers.png", optimize=True)
        normal.save(folder / f"{stem}_normal.png", optimize=True)
        write_texture_set(folder, role)
        textures[(role, "color")] = color
        textures[(role, "mers")] = mers
        textures[(role, "normal")] = normal
    contact_sheet(textures, folder.parent.parent.parent / "jellyfish_boss_v15_texture_preview.png")
    print(f"TEXTURES {folder}")
    print("FILES color=3 mers=3 normal=3 texture_sets=3")


if __name__ == "__main__":
    main()
