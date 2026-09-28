import json
import os
import sys
from pathlib import Path

from PIL import Image

args = sys.argv[1:]
if len(args) not in (1, 2):
    raise SystemExit(
        "Usage: python validate_bedrock_staging.py GENERATED_DIR [REVISION]"
    )

root = Path(os.path.abspath(args[0]))
revision = args[1] if len(args) == 2 else "v12"
prefix = f"jellyfish_boss_{revision}"

def load(name):
    with (root / name).open(encoding="utf-8") as handle:
        return json.load(handle)

geo = load(f"{prefix}.geo.json")
animation = load(f"{prefix}.animation.json")
entity = load(f"{prefix}.entity.json")
controllers = load(
    f"{prefix}.render_controllers.json"
)
geometries = {
    item["description"]["identifier"]: item
    for item in geo["minecraft:geometry"]
}
expected_geometry_ids = {
    "geometry.pinene.jellyfish_boss.shell",
    "geometry.pinene.jellyfish_boss.tissue",
    "geometry.pinene.jellyfish_boss.glow",
}
assert set(geometries) == expected_geometry_ids

cube_counts = {}
all_cubes = []
for identifier, geometry in geometries.items():
    bones = geometry["bones"]
    names = {bone["name"] for bone in bones}
    assert len(bones) == 58
    assert len(names) == len(bones)
    assert not any("poly_mesh" in bone for bone in bones)
    assert not any(
        bone.get("parent") not in names
        for bone in bones if bone.get("parent")
    )
    cubes = [
        cube
        for bone in bones
        for cube in bone.get("cubes", [])
    ]
    assert cubes
    assert all(
        len(cube["origin"]) == 3
        and len(cube["size"]) == 3
        and min(cube["size"]) > 0
        for cube in cubes
    )
    cube_counts[identifier] = len(cubes)
    all_cubes.extend(cubes)

expected_counts = {
    "v06": {
        "geometry.pinene.jellyfish_boss.shell": 176,
        "geometry.pinene.jellyfish_boss.tissue": 188,
        "geometry.pinene.jellyfish_boss.glow": 34,
    },
    "v12": {
        "geometry.pinene.jellyfish_boss.shell": 240,
        "geometry.pinene.jellyfish_boss.tissue": 217,
        "geometry.pinene.jellyfish_boss.glow": 54,
    },
    "v13": {
        "geometry.pinene.jellyfish_boss.shell": 448,
        "geometry.pinene.jellyfish_boss.tissue": 265,
        "geometry.pinene.jellyfish_boss.glow": 88,
    },
    "v14": {
        "geometry.pinene.jellyfish_boss.shell": 480,
        "geometry.pinene.jellyfish_boss.tissue": 265,
        "geometry.pinene.jellyfish_boss.glow": 88,
    },
    "v15": {
        "geometry.pinene.jellyfish_boss.shell": 704,
        "geometry.pinene.jellyfish_boss.tissue": 313,
        "geometry.pinene.jellyfish_boss.glow": 119,
    },
}
if revision in expected_counts:
    assert cube_counts == expected_counts[revision]

per_face_cubes = [cube for cube in all_cubes if isinstance(cube["uv"], dict)]
for cube in per_face_cubes:
    assert set(cube["uv"]) == {"north", "south", "east", "west"}
rendered_triangles = 2 * sum(
    len(cube["uv"]) if isinstance(cube["uv"], dict) else 6
    for cube in all_cubes
)
expected_triangles = {
    "v06": 4776,
    "v12": 6132,
    "v13": 9612,
    "v14": 9996,
    "v15": 9176,
}
if revision in expected_triangles:
    assert rendered_triangles == expected_triangles[revision]
if revision == "v15":
    assert len(per_face_cubes) == 1114
    for cube in per_face_cubes:
        for face in cube["uv"].values():
            assert face["uv_size"] == [12, 44]
            u, v = face["uv"]
            assert 0 <= u <= 500 and 0 <= v <= 468
            assert u + 12 <= 512 and v + 44 <= 512

    texture_root = root / "textures" / "entity" / "pinene"
    for role in ("shell", "tissue", "glow"):
        stem = f"jellyfish_boss_{role}"
        paths = {
            "color": texture_root / f"{stem}.png",
            "normal": texture_root / f"{stem}_normal.png",
            "mers": texture_root / f"{stem}_mers.png",
        }
        for path in paths.values():
            with Image.open(path) as image:
                assert image.size == (512, 512)
                assert image.mode == "RGBA"
        with Image.open(paths["mers"]) as mers:
            red, green, blue, alpha = mers.getextrema()
            assert red == (0, 0)
            assert blue[0] > 0 and alpha[1] > 0
            if role == "glow":
                assert green == (255, 255)
        texture_set = load(
            f"textures/entity/pinene/{stem}.texture_set.json"
        )
        assert texture_set["format_version"] == "1.21.30"
        layers = texture_set["minecraft:texture_set"]
        assert layers == {
            "color": stem,
            "normal": f"{stem}_normal",
            "metalness_emissive_roughness_subsurface": f"{stem}_mers",
        }
animations = animation["animations"]
animation_id = "animation.pinene.jellyfish_boss.idle"
assert set(animations) == {animation_id}
idle = animations[animation_id]
assert idle["loop"] is True
assert idle["animation_length"] == 4.0
assert len(idle["bones"]) == 57

geometry_bones = {
    bone["name"]
    for bone in next(iter(geometries.values()))["bones"]
}
assert set(idle["bones"]).issubset(geometry_bones)
for channels in idle["bones"].values():
    for keyframes in channels.values():
        if isinstance(keyframes, dict):
            assert keyframes["0.00"] == keyframes["4.00"]

description = entity["minecraft:client_entity"]["description"]
assert set(description["geometry"].values()) == set(geometries)
assert animation_id in description["animations"].values()
controller_map = controllers["render_controllers"]
assert set(description["render_controllers"]) == set(controller_map)
assert {
    definition["geometry"]
    for definition in controller_map.values()
} == {
    "geometry.shell",
    "geometry.tissue",
    "geometry.glow",
}

print(
    "VALID "
    f"revision={revision} "
    f"geometries={len(geometries)} "
    f"bones={len(geometry_bones)} "
    f"cubes={sum(cube_counts.values())} "
    f"rendered_triangles={rendered_triangles} "
    f"open_ended_cubes={len(per_face_cubes)} "
    f"animated_bones={len(idle['bones'])} "
    f"controllers={len(controller_map)}"
)
