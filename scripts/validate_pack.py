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
assert components["minecraft:scale"]["value"] == 1.0
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
    "geometry.pinene.jellyfish_boss.shell_far",
    "geometry.pinene.jellyfish_boss.tissue_far",
}
assert {item["description"]["identifier"] for item in geometries} == expected_ids

cubes = [
    cube
    for item in geometries
    for bone in item["bones"]
    for cube in bone.get("cubes", [])
]
open_ended = [cube for cube in cubes if isinstance(cube.get("uv"), dict) and len(cube['uv']) < 6]
rendered_triangles = sum(
    len(cube["uv"]) * 2 if isinstance(cube.get("uv"), dict) else 12
    for cube in cubes
)
near_geometries = [g for g in geometries if not g['description']['identifier'].endswith('_far')]
far_geometries = [g for g in geometries if g['description']['identifier'].endswith('_far')]
def counts(items):
    active = [c for g in items for b in g['bones'] for c in b.get('cubes',[])]
    return len(active),sum(len(c['uv'])*2 for c in active)
assert counts(near_geometries) == (622,3656)
assert counts(far_geometries) == (206,1224)
assert sum(len(g['bones']) for g in near_geometries) == 116
assert len(client['minecraft:client_entity']['description']['render_controllers']) == 2
controllers = load(RP/'render_controllers/jellyfish_boss.render_controllers.json')
assert len(controllers['render_controllers']) == 2
lod = load(RP/'animation_controllers/jellyfish_boss.lod.json')
assert set(lod['animation_controllers']['controller.animation.pinene.jellyfish_boss.lod']['states']) == {'near','far'}
for g in geometries:
    names = {b['name'] for b in g['bones']}
    assert all(b.get('parent') is None or b['parent'] in names for b in g['bones'])
    assert len(names) == len(g['bones'])
    assert g['description']['visible_bounds_width'] == 16
    assert g['description']['visible_bounds_height'] == 22
for cube in cubes:
    assert all(v > 0 for v in cube['size'])
    for face in cube['uv'].values():
        for start,length in zip(face['uv'],face['uv_size']):
            assert -0.001 <= min(start,start+length)
            assert max(start,start+length) <= 512.001

animation = load(RP / "animations/jellyfish_boss.animation.json")
idle = animation["animations"]["animation.pinene.jellyfish_boss.idle"]
assert len(idle["bones"]) == 112
assert idle['animation_length'] == 6.0
assert animation['animations']['animation.pinene.jellyfish_boss.pulse']['bones'].keys() == {'bell'}
assert animation['animations']['animation.pinene.jellyfish_boss.distant']['bones'].keys() == {'bell'}
assert len({name.rsplit('_',1)[0] for name in idle['bones'] if name.startswith('tentacle_')}) == 16
near_names = {b['name'] for g in near_geometries for b in g['bones']}
assert set(idle['bones']) <= near_names
for name, count in (('outer',8),('inner',6)):
    for index in range(1,9):
        assert all(f'tentacle_{name}_{index:02d}_{joint:02d}' in idle['bones']
                   for joint in range(1,count+1))
for item in animation['animations'].values():
    for bone in item['bones'].values():
        for channel in bone.values():
            pairs = sorted((float(t),v) for t,v in channel.items())
            assert len(pairs) >= 33
            assert pairs[0][0] == 0 and pairs[-1][0] == item['animation_length']
            assert pairs[0][1] == pairs[-1][1]
            assert all(b-a <= .125001 for (a,_),(b,_) in zip(pairs,pairs[1:]))
assert lod['animation_controllers']['controller.animation.pinene.jellyfish_boss.lod']['states']['near']['animations'] == ['idle','pulse']
assert bp_manifest['header']['version'] == rp_manifest['header']['version'] == [0,1,5]
rig = load(ROOT/'docs/bosses/jellyfish/rig-plan.json')
assert rig['skeleton']['tentacle_bone_count'] == len(idle['bones']) == 112
assert rig['skeleton']['total_bone_count'] == len(near_names) == 114
assert rig['idle_animation']['duration_seconds'] == idle['animation_length']

texture_root = RP / "textures/entity/pinene"
for role in ("shell", "tissue"):
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

print("VALID", f"near={counts(near_geometries)}", f"far={counts(far_geometries)}",
      f"open_ended={len(open_ended)}", "animated_bones=113",
      "used_textures=7", "spawn_egg=ok", "physical_scale=1", "baked_visual_scale=9.5")
