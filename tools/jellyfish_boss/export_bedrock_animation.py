import json
import math
import os
import sys

args = sys.argv[1:]
if len(args) != 1:
    raise SystemExit(
        "Usage: python export_bedrock_animation.py OUTPUT.animation.json"
    )

OUT = os.path.abspath(args[0])
DURATION = 4.0
KEY_TIMES = (0.0, 1.0, 2.0, 3.0, 4.0)

def clean_number(value):
    value = round(float(value), 3)
    return 0.0 if abs(value) < 0.0005 else value

def clean_vector(values):
    return [clean_number(value) for value in values]

def rotation_keys(kind, index, joint):
    theta = 2.0 * math.pi * index / 8.0
    if kind == "inner":
        theta += math.pi / 8.0
    phase = 0.79 * index + (0.55 if kind == "inner" else 0.0)
    amplitude = (
        4.3 + 2.6 * joint
        if kind == "outer"
        else 5.7 + 3.15 * joint
    )
    keys = {}
    for key_time in KEY_TIMES:
        cycle = 2.0 * math.pi * key_time / DURATION
        primary = amplitude * math.sin(
            cycle + phase + joint * 0.65
        )
        secondary = amplitude * 0.72 * math.cos(
            cycle + phase + joint * 0.40
        )
        twist = amplitude * 0.22 * math.sin(
            2.0 * cycle + phase * 1.37 + joint * 0.40
        )
        rotation_x = (
            primary * math.cos(theta)
            + secondary * math.sin(theta)
        )
        rotation_z = (
            primary * math.sin(theta)
            - secondary * math.cos(theta)
        )
        keys[f"{key_time:.2f}"] = clean_vector(
            (rotation_x, twist, rotation_z)
        )
    assert keys["0.00"] == keys["4.00"]
    return keys

bones = {}
for kind, count, joints in (
    ("outer", 8, 4),
    ("inner", 8, 3),
):
    for index in range(count):
        for joint in range(joints):
            name = (
                f"tentacle_{kind}_{index + 1:02d}_"
                f"{joint + 1:02d}"
            )
            bones[name] = {
                "rotation": rotation_keys(
                    kind, index, joint
                )
            }

bones["bell"] = {
    "scale": {
        "0.00": [1.0, 1.0, 1.0],
        "1.00": [1.025, 0.982, 1.025],
        "2.00": [1.0, 1.0, 1.0],
        "3.00": [0.975, 1.018, 0.975],
        "4.00": [1.0, 1.0, 1.0],
    }
}

payload = {
    "format_version": "1.8.0",
    "animations": {
        "animation.pinene.jellyfish_boss.idle": {
            "loop": True,
            "animation_length": DURATION,
            "bones": bones,
        }
    },
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=2)
    handle.write("\n")

print(f"EXPORTED {OUT}")
print(
    "ANIMATION "
    f"bones={len(bones)} "
    f"tentacle_bones={len(bones) - 1} "
    f"duration={DURATION:.1f}s"
)
