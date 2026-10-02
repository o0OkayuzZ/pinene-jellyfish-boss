import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BP = ROOT / "behavior_pack"
RP = ROOT / "resource_pack"

def load(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)

for path in sorted(BP.rglob("*.json")) + sorted(RP.rglob("*.json")):
    load(path)

bp_manifest = load(BP / "manifest.json")
rp_manifest = load(RP / "manifest.json")
assert rp_manifest["capabilities"] == ["pbr"]
assert rp_manifest["header"]["min_engine_version"] >= [1, 21, 120]
assert bp_manifest["dependencies"][0]["uuid"] == rp_manifest["header"]["uuid"]

behavior = load(BP / "entities/jellyfish_boss.behavior.json")
client = load(RP / "entity/jellyfish_boss.entity.json")
identifier = "pinene:jellyfish_boss"
assert behavior["minecraft:entity"]["description"]["identifier"] == identifier
assert client["minecraft:client_entity"]["description"]["identifier"] == identifier
assert "spawn_egg" not in client["minecraft:client_entity"]["description"]
components = behavior["minecraft:entity"]["components"]
assert components["minecraft:scale"]["value"] == 9.5
assert components["minecraft:collision_box"] == {"width": 10.5, "height": 8.0}

spawn_egg = load(BP / "items/jellyfish_boss_spawn_egg.item.json")
egg_description = spawn_egg["minecraft:item"]["description"]
assert egg_description["identifier"] == "pinene:jellyfish_boss_spawn_egg"
assert egg_description["menu_category"] == {
    "category": "items",
    "is_hidden_in_commands": False,
}
egg_components = spawn_egg["minecraft:item"]["components"]
assert egg_components["minecraft:entity_placer"]["entity"] == identifier
assert egg_components["minecraft:icon"] == "pinene_jellyfish_boss_spawn_egg"
item_atlas = load(RP / "textures/item_texture.json")
assert "pinene_jellyfish_boss_spawn_egg" in item_atlas["texture_data"]

geometry = load(RP / "models/entity/jellyfish_boss.geo.json")
geometries = geometry["minecraft:geometry"]
expected_ids = {
    "geometry.pinene.jellyfish_boss.shell",
    "geometry.pinene.jellyfish_boss.tissue",
    "geometry.pinene.jellyfish_boss.glow",
}
assert {item["description"]["identifier"] for item in geometries} == expected_ids

cubes = [
    cube
    for item in geometries
    for bone in item["bones"]
    for cube in bone.get("cubes", [])
]
open_ended = [cube for cube in cubes if isinstance(cube.get("uv"), dict)]
rendered_triangles = sum(
    len(cube["uv"]) * 2 if isinstance(cube.get("uv"), dict) else 12
    for cube in cubes
)
assert len(cubes) == 1136
assert len(open_ended) == 1114
assert rendered_triangles == 9176

animation = load(RP / "animations/jellyfish_boss.animation.json")
idle = animation["animations"]["animation.pinene.jellyfish_boss.idle"]
assert len(idle["bones"]) == 57

texture_root = RP / "textures/entity/pinene"
for role in ("shell", "tissue", "glow"):
    stem = f"jellyfish_boss_{role}"
    for suffix in ("", "_normal", "_mers"):
        path = texture_root / f"{stem}{suffix}.png"
        with path.open("rb") as handle:
            assert handle.read(8) == b"\x89PNG\r\n\x1a\n"
            length = struct.unpack(">I", handle.read(4))[0]
            assert handle.read(4) == b"IHDR" and length == 13
            width, height = struct.unpack(">II", handle.read(8))
            assert (width, height) == (512, 512)
    texture_set = load(texture_root / f"{stem}.texture_set.json")
    assert texture_set["format_version"] == "1.21.30"

egg_icon = RP / "textures/items/jellyfish_boss_spawn_egg.png"
with egg_icon.open("rb") as handle:
    assert handle.read(8) == b"\x89PNG\r\n\x1a\n"
    length = struct.unpack(">I", handle.read(4))[0]
    assert handle.read(4) == b"IHDR" and length == 13
    assert struct.unpack(">II", handle.read(8)) == (32, 32)

print("VALID", f"cubes={len(cubes)}", f"triangles={rendered_triangles}",
      f"open_ended={len(open_ended)}", f"animated_bones={len(idle['bones'])}",
      "textures=10", "spawn_egg=ok", "scale=9.5")