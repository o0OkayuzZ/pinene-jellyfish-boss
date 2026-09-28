import bpy
import json
import math
import os
import sys
from mathutils import Matrix, Quaternion, Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(args) != 1:
    raise SystemExit(
        "Usage: blender MODEL.blend --background --python "
        "export_bedrock_geometry.py -- OUTPUT.geo.json"
    )

OUT = os.path.abspath(args[0])
SCALE = 16.0
Y_OFFSET = 16.0
COORDINATE_CONVERSION = Matrix((
    (1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0),
    (0.0, -1.0, 0.0),
))
COORDINATE_CONVERSION_INV = COORDINATE_CONVERSION.transposed()

def clean_number(value):
    value = round(float(value), 4)
    return 0.0 if abs(value) < 0.00005 else value

def clean_vector(values):
    return [clean_number(value) for value in values]

def convert_position(values):
    position = COORDINATE_CONVERSION @ Vector(values)
    position *= SCALE
    position.y += Y_OFFSET
    return position

def convert_dimensions(values):
    dimensions = Vector(values)
    return Vector((
        dimensions.x * SCALE,
        dimensions.z * SCALE,
        dimensions.y * SCALE,
    ))

def convert_rotation(values):
    quaternion = Quaternion(tuple(values))
    blender_rotation = quaternion.to_matrix()
    bedrock_rotation = (
        COORDINATE_CONVERSION
        @ blender_rotation
        @ COORDINATE_CONVERSION_INV
    )
    euler = bedrock_rotation.to_euler("XYZ")
    return Vector(tuple(math.degrees(value) for value in euler))

def cube_from_object(obj):
    center = convert_position(obj["jf_center"])
    dimensions = convert_dimensions(obj["jf_dimensions"])
    rotation = convert_rotation(obj["jf_quaternion"])
    origin = center - dimensions * 0.5
    cube = {
        "origin": clean_vector(origin),
        "size": clean_vector(dimensions),
        "uv": [0, 0],
    }
    if max(abs(value) for value in rotation) > 0.0001:
        cube["pivot"] = clean_vector(center)
        cube["rotation"] = clean_vector(rotation)
    return cube

arm = bpy.data.objects.get("JF_Rig")
if arm is None or arm.type != "ARMATURE":
    raise RuntimeError("JF_Rig armature was not found")

export_objects = sorted(
    (
        obj for obj in bpy.data.objects
        if obj.get("jf_export_cube") and obj.type == "MESH"
    ),
    key=lambda obj: obj.name,
)
if not export_objects:
    raise RuntimeError("No tagged jellyfish cubes were found")

def material_role(obj):
    return str(obj.get("jf_material_role", ""))

TISSUE_ROLES = {
    "JF_Inner_Core",
    "JF_Gel_Pink",
    "JF_Gel_Magenta",
    "JF_Gel_Violet",
    "JF_Gel_Frill",
}
glow_objects = [
    obj for obj in export_objects
    if material_role(obj).startswith("JF_Cyan_Glow")
]
tissue_objects = [
    obj for obj in export_objects
    if material_role(obj) in TISSUE_ROLES
]
shell_objects = [
    obj for obj in export_objects
    if obj not in glow_objects and obj not in tissue_objects
]
assert len(shell_objects) + len(tissue_objects) + len(glow_objects) == len(export_objects)

def make_bones(objects):
    cubes_by_bone = {}
    for obj in objects:
        cubes_by_bone.setdefault(str(obj["jf_bone"]), []).append(
            cube_from_object(obj)
        )
    bones = []
    for bone in arm.data.bones:
        entry = {
            "name": bone.name,
            "pivot": clean_vector(convert_position(bone.head_local)),
        }
        if bone.parent is not None:
            entry["parent"] = bone.parent.name
        cubes = cubes_by_bone.get(bone.name)
        if cubes:
            entry["cubes"] = cubes
        bones.append(entry)
    return bones

def make_geometry(identifier, objects):
    return {
        "description": {
            "identifier": identifier,
            "texture_width": 512,
            "texture_height": 512,
            "visible_bounds_width": 4.0,
            "visible_bounds_height": 4.0,
            "visible_bounds_offset": [0.0, 1.0, 0.0],
        },
        "bones": make_bones(objects),
    }

geometries = [
    make_geometry("geometry.pinene.jellyfish_boss.shell", shell_objects),
    make_geometry("geometry.pinene.jellyfish_boss.tissue", tissue_objects),
]
if glow_objects:
    geometries.append(
        make_geometry("geometry.pinene.jellyfish_boss.glow", glow_objects)
    )

payload = {
    "format_version": "1.12.0",
    "minecraft:geometry": geometries,
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=2)
    handle.write("\n")

print(f"EXPORTED {OUT}")
print(
    "GEOMETRY "
    f"bones={len(arm.data.bones)} "
    f"shell_cubes={len(shell_objects)} "
    f"tissue_cubes={len(tissue_objects)} "
    f"glow_cubes={len(glow_objects)} "
    f"total_cubes={len(export_objects)}"
)
