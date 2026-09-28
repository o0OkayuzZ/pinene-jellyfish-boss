import bpy, math, os, sys
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(args) != 2:
    raise SystemExit("Usage: blender SOURCE.blend --background --python build_clean_tentacle_rig.py -- OUTPUT.blend PREVIEW.png")
OUT, PREVIEW = map(os.path.abspath, args)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)

for obj in list(bpy.data.objects):
    if obj.name.startswith("JF_"):
        bpy.data.objects.remove(obj, do_unlink=True)

source_tentacles = bpy.data.objects.get("Meshy_Mesh_0")
hood = bpy.data.objects.get("Meshy_Mesh_0.008")
if not source_tentacles or not hood:
    raise RuntimeError("Expected separated source objects were not found")
source_tentacles.hide_render = True
source_tentacles.hide_viewport = True

def make_material(name, color, metallic=0.0, roughness=0.55):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat

pink = make_material("JF_Tentacle_Pink", (0.48, 0.07, 0.34), 0.05, 0.42)
magenta = make_material("JF_Tentacle_Magenta", (0.29, 0.025, 0.24), 0.08, 0.40)
violet = make_material("JF_Tentacle_Violet", (0.095, 0.012, 0.16), 0.14, 0.36)
core_material = make_material("JF_Core", (0.028, 0.012, 0.055), 0.22, 0.30)
arm_data = bpy.data.armatures.new("JF_Rig")
arm = bpy.data.objects.new("JF_Rig", arm_data)
bpy.context.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")

root = arm_data.edit_bones.new("root")
root.head, root.tail = (0, 0, -0.1), (0, 0, 0.1)
bell = arm_data.edit_bones.new("bell")
bell.head, bell.tail = (0, 0, 0.30), (0, 0, 0.78)
bell.parent = root

chains = []
for kind, count in (("outer", 8), ("inner", 8)):
    for i in range(count):
        theta = 2.0 * math.pi * i / count + (math.pi / 8 if kind == "inner" else 0)
        radial = Vector((math.cos(theta), math.sin(theta), 0))
        tangent = Vector((-math.sin(theta), math.cos(theta), 0))
        phase = 0.73 * i + (0.4 if kind == "inner" else 0)
        if kind == "outer":
            r = 0.45 + 0.018 * math.sin(phase * 1.7)
            points = [
                radial * r + Vector((0, 0, 0.39)),
                radial * (r + 0.055) + tangent * (0.08 * math.sin(phase)) + Vector((0, 0, 0.14)),
                radial * (r + 0.035) - tangent * (0.15 * math.cos(phase + 0.3)) + Vector((0, 0, -0.15)),
                radial * (r - 0.045) + tangent * (0.17 * math.sin(phase + 0.8)) + Vector((0, 0, -0.48)),
                radial * (r + 0.075) - tangent * (0.18 * math.cos(phase + 0.5)) + Vector((0, 0, -0.84 - 0.11 * math.sin(phase))),
            ]
            widths = [0.064, 0.054, 0.043, 0.029]
        else:
            r = 0.225 + 0.025 * math.cos(phase * 1.3)
            points = [
                radial * r + Vector((0, 0, 0.36)),
                radial * (r + 0.065) + tangent * (0.085 * math.sin(phase + 0.2)) + Vector((0, 0, 0.10)),
                radial * (r - 0.055) - tangent * (0.13 * math.cos(phase + 0.7)) + Vector((0, 0, -0.19)),
                radial * (r + 0.035) + tangent * (0.14 * math.sin(phase + 1.1)) + Vector((0, 0, -0.50 - 0.11 * math.cos(phase))),
            ]
            widths = [0.072, 0.052, 0.033]
        bone_names = []
        parent = bell
        for j in range(len(points) - 1):
            name = f"tentacle_{kind}_{i + 1:02d}_{j + 1:02d}"
            bone = arm_data.edit_bones.new(name)
            bone.head, bone.tail = points[j], points[j + 1]
            bone.parent = parent
            bone.use_connect = j > 0
            parent = bone
            bone_names.append(name)
        chains.append({"kind": kind, "index": i, "points": points,
                       "widths": widths, "bones": bone_names})

bpy.ops.object.mode_set(mode="OBJECT")
arm.show_in_front = True

hood_world = hood.matrix_world.copy()
hood.parent = arm
hood.parent_type = "BONE"
hood.parent_bone = "bell"
hood.matrix_parent_inverse = (arm.matrix_world @ arm.pose.bones["bell"].matrix).inverted()
hood.matrix_world = hood_world

bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0.13))
core = bpy.context.object
core.name = "JF_Core"
core.dimensions = (0.43, 0.43, 0.52)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
core_bevel = core.modifiers.new("Core rounding", "BEVEL")
core_bevel.width, core_bevel.segments = 0.09, 4
core.data.materials.append(core_material)
core_world = core.matrix_world.copy()
core.parent, core.parent_type, core.parent_bone = arm, "BONE", "bell"
core.matrix_parent_inverse = (arm.matrix_world @ arm.pose.bones["bell"].matrix).inverted()
core.matrix_world = core_world

def add_segment(name, start, end, width, bone_name, material):
    direction = end - start
    length = direction.length
    midpoint = (start + end) * 0.5
    bpy.ops.mesh.primitive_cube_add(location=midpoint)
    obj = bpy.context.object
    obj.name = "JF_" + name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    obj.dimensions = (width, width * 0.86, length * 1.12)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new("Soft pixel edge", "BEVEL")
    bevel.width = min(width * 0.22, 0.012)
    bevel.segments = 2
    obj.data.materials.append(material)
    world = obj.matrix_world.copy()
    obj.parent = arm
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_parent_inverse = (arm.matrix_world @ arm.pose.bones[bone_name].matrix).inverted()
    obj.matrix_world = world
    return obj

for chain in chains:
    for j, bone_name in enumerate(chain["bones"]):
        material = violet if j == 0 else (pink if j == len(chain["bones"]) - 1 else magenta)
        add_segment(f"{chain['kind']}_{chain['index'] + 1:02d}_{j + 1:02d}",
                    chain["points"][j], chain["points"][j + 1],
                    chain["widths"][j], bone_name, material)

scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, 81
action = bpy.data.actions.new("jellyfish_idle_individual_tentacles")
arm.animation_data_create()
arm.animation_data.action = action
for frame in (1, 21, 41, 61, 81):
    t = 2.0 * math.pi * (frame - 1) / 80.0
    for chain in chains:
        base_phase = chain["index"] * 0.79 + (0.55 if chain["kind"] == "inner" else 0)
        for j, bone_name in enumerate(chain["bones"]):
            pose = arm.pose.bones[bone_name]
            pose.rotation_mode = "XYZ"
            amp = (0.075 + 0.045 * j) if chain["kind"] == "outer" else (0.10 + 0.055 * j)
            pose.rotation_euler = (
                amp * math.sin(t + base_phase + j * 0.65),
                amp * 0.8 * math.cos(t * 0.87 + base_phase + j * 0.4),
                amp * 0.35 * math.sin(t * 0.63 + base_phase),
            )
            pose.keyframe_insert(data_path="rotation_euler", frame=frame)
    bell_pose = arm.pose.bones["bell"]
    pulse = 1.0 + 0.025 * math.sin(t)
    bell_pose.scale = (pulse, pulse, 1.0 - 0.018 * math.sin(t))
    bell_pose.keyframe_insert(data_path="scale", frame=frame)

target = Vector((0, 0, -0.02))
cam_data = bpy.data.cameras.new("JF_Camera")
cam = bpy.data.objects.new("JF_Camera", cam_data)
bpy.context.collection.objects.link(cam)
cam.location = (2.15, -3.15, 1.15)
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 58
scene.camera = cam
for name, loc, energy, color, size in [
    ("JF_Key", (2.4, -2.2, 2.7), 1150, (0.68, 0.92, 1.0), 2.2),
    ("JF_Fill", (-2.0, -0.3, 1.1), 850, (1.0, 0.25, 0.62), 1.8),
]:
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.color, data.size = energy, color, size
    lamp = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(lamp)
    lamp.location = loc
    lamp.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 700
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = PREVIEW
if scene.world is None:
    scene.world = bpy.data.worlds.new("World")
scene.world.color = (0.009, 0.012, 0.022)
scene.frame_set(21)
bpy.ops.render.render(write_still=True)
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print(f"SAVED {OUT}")
print(f"PREVIEW {PREVIEW}")
print(f"RIG tentacles={len(chains)} tentacle_bones={sum(len(c['bones']) for c in chains)}")