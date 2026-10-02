"""Package actual runtime-geometry renders as a looping 12 fps motion preview."""
import os
import sys
from pathlib import Path
from PIL import Image

if len(sys.argv) != 3:
    raise SystemExit("Usage: python package_motion_preview.py FRAMES_DIR OUTPUT.gif")
folder, out = Path(sys.argv[1]), Path(sys.argv[2])
paths = sorted(folder.glob("frame_*.png"))
assert len(paths) == 144, f"Expected 144 frames, got {len(paths)}"
frames = [Image.open(path).convert("RGB").resize((400,400),Image.Resampling.LANCZOS) for path in paths]
out.parent.mkdir(parents=True,exist_ok=True)
palette_sheet = Image.new("RGB",(frames[0].width*8,frames[0].height))
for i in range(8):
    palette_sheet.paste(frames[i*18],(i*frames[0].width,0))
palette = palette_sheet.quantize(colors=96)
frames = [frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
# GIF delays are centiseconds: 80,80,90 ms approximate the 12 fps render.
durations = [80 if i%3 != 2 else 90 for i in range(len(frames))]
frames[0].save(out,save_all=True,append_images=frames[1:],duration=durations,
               loop=0,disposal=1,optimize=True)
with Image.open(out) as check:
    assert check.n_frames == 144 and check.size == (400,400)
    duration = 0
    for i in range(check.n_frames):
        check.seek(i)
        duration += check.info["duration"]
    assert duration == 12000
print("MOTION_PREVIEW",str(out.resolve()),"frames=144 seconds=12",os.path.getsize(out))
