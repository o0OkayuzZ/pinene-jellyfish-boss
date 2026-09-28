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

def set_input(bsdf, name, value):
    socket = bsdf.inputs.get(name)
    if socket is not None:
        socket.default_value = value

def make_material(name, color, metallic=0.0, roughness=0.55, alpha=1.0,
                  transmission=0.0, emission=None, emission_strength=0.0,
                  subsurface=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (*color, alpha)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    set_input(bsdf, "Base Color", (*color, 1.0))
    set_input(bsdf, "Metallic", metallic)
    set_input(bsdf, "Roughness", roughness)
    set_input(bsdf, "IOR", 1.34)
    set_input(bsdf, "Alpha", alpha)
    set_input(bsdf, "Transmission Weight", transmission)
    set_input(bsdf, "Subsurface Weight", subsurface)
    set_input(bsdf, "Coat Weight", 0.28 if alpha < 1.0 else 0.08)
    set_input(bsdf, "Coat Roughness", 0.10)
    if emission is not None:
        set_input(bsdf, "Emission Color", (*emission, 1.0))
        set_input(bsdf, "Emission Strength", emission_strength)
    if alpha < 1.0:
        mat.surface_render_method = "BLENDED"
        mat.blend_method = "BLEND"
        mat.show_transparent_back = True
        mat.use_transparent_shadow = True
        mat.use_screen_refraction = True
    return mat

def add_mottled_color(mat, scale, phase):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    geometry = nodes.new("ShaderNodeNewGeometry")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 4.5
    noise.inputs["Roughness"].default_value = 0.72
    noise.inputs["Distortion"].default_value = 0.30 + phase
    ramp = nodes.new("ShaderNodeValToRGB")
    color_ramp = ramp.color_ramp
    color_ramp.elements[0].position = 0.22
    color_ramp.elements[0].color = (0.018, 0.002, 0.045, 1.0)
    color_ramp.elements[1].position = 0.84
    color_ramp.elements[1].color = (0.015, 0.13, 0.16, 1.0)
    for position, color in [
        (0.50, (0.16, 0.004, 0.14, 1.0)),
        (0.66, (0.66, 0.018, 0.38, 1.0)),
        (0.75, (0.035, 0.70, 0.78, 1.0)),
        (0.79, (0.010, 0.22, 0.28, 1.0)),
    ]:
        item = color_ramp.elements.new(position)
        item.color = color
    links.new(geometry.outputs["Position"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

# Bedrock target: alphablend gel body, opaque inner mass, emissive-alpha markings.
pink = make_material("JF_Gel_Pink", (0.52, 0.035, 0.30), 0.0, 0.20, 0.66,
                     0.28, (1.0, 0.035, 0.42), 0.32, 0.10)
magenta = make_material("JF_Gel_Magenta", (0.25, 0.010, 0.20), 0.0, 0.18, 0.72,
                        0.24, (0.48, 0.008, 0.27), 0.18, 0.12)
violet = make_material("JF_Gel_Violet", (0.045, 0.008, 0.11), 0.0, 0.16, 0.78,
                       0.18, (0.03, 0.16, 0.22), 0.12, 0.12)
core_material = make_material("JF_Inner_Core", (0.012, 0.006, 0.028), 0.0, 0.34, 0.94,
                              0.0, (0.01, 0.16, 0.20), 0.20)
cyan_glow = make_material("JF_Cyan_Glow", (0.005, 0.20, 0.26), 0.0, 0.20, 0.62,
                          0.08, (0.01, 0.58, 0.72), 0.70, 0.08)
add_mottled_color(violet, 7.5, 0.05)
add_mottled_color(magenta, 8.5, 0.10)
add_mottled_color(pink, 9.5, 0.15)

# Keep the source texture, but turn the bell into a dense translucent gel shell.
for slot_index, source_mat in enumerate(list(hood.data.materials)):
    if source_mat is None:
        continue
    shell_mat = source_mat.copy()
    shell_mat.name = f"JF_Gel_Shell_{slot_index:02d}"
    shell_mat.use_nodes = True
    shell_bsdf = shell_mat.node_tree.nodes.get("Principled BSDF")
    if shell_bsdf is not None:
        set_input(shell_bsdf, "Metallic", 0.0)
        set_input(shell_bsdf, "Roughness", 0.16)
        set_input(shell_bsdf, "IOR", 1.34)
        set_input(shell_bsdf, "Alpha", 0.58)
        set_input(shell_bsdf, "Transmission Weight", 0.48)
        set_input(shell_bsdf, "Subsurface Weight", 0.24)
        set_input(shell_bsdf, "Coat Weight", 0.32)
        set_input(shell_bsdf, "Coat Roughness", 0.08)
    shell_mat.diffuse_color = (*shell_mat.diffuse_color[:3], 0.58)
    shell_mat.surface_render_method = "BLENDED"
    shell_mat.blend_method = "BLEND"
    shell_mat.show_transparent_back = True
    shell_mat.use_transparent_shadow = True
    shell_mat.use_screen_refraction = True
    hood.data.materials[slot_index] = shell_mat
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

def add_body_lobe(name, location, dimensions, rotation, material, bevel_width):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = "JF_" + name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new("Gel rounding", "BEVEL")
    bevel.width, bevel.segments = bevel_width, 3
    obj.data.materials.append(material)
    world = obj.matrix_world.copy()
    obj.parent, obj.parent_type, obj.parent_bone = arm, "BONE", "bell"
    obj.matrix_parent_inverse = (arm.matrix_world @ arm.pose.bones["bell"].matrix).inverted()
    obj.matrix_world = world
    return obj

# Irregular inner tissue remains readable through the translucent shell without
# turning the boss into a single obvious cube.
add_body_lobe("Core_Center", (0.00, 0.00, 0.11), (0.22, 0.19, 0.50),
              (0.04, -0.08, 0.18), core_material, 0.055)
add_body_lobe("Core_Left", (-0.13, -0.01, 0.07), (0.13, 0.11, 0.41),
              (-0.18, 0.22, -0.42), magenta, 0.038)
add_body_lobe("Core_Right", (0.13, 0.025, 0.09), (0.12, 0.10, 0.43),
              (0.16, -0.24, 0.48), violet, 0.036)
add_body_lobe("Core_Back", (0.015, 0.11, 0.13), (0.14, 0.10, 0.36),
              (0.22, 0.10, -0.16), core_material, 0.038)
add_body_lobe("Lumen", (0.00, -0.035, 0.17), (0.075, 0.065, 0.24),
              (0.05, 0.10, 0.22), cyan_glow, 0.025)

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

# Three overlapping tapered cubes per bone give a continuous, curved silhouette
# while keeping the 58-bone runtime rig unchanged.
for chain in chains:
    for j, bone_name in enumerate(chain["bones"]):
        material = violet if j == 0 else (pink if j == len(chain["bones"]) - 1 else magenta)
        start, end = chain["points"][j], chain["points"][j + 1]
        axis = end - start
        side = Vector((-axis.y, axis.x, 0.0))
        if side.length < 0.0001:
            side = Vector((1.0, 0.0, 0.0))
        side.normalize()
        bend_sign = 1.0 if ((chain["index"] + j) % 2 == 0) else -1.0
        bend = chain["widths"][j] * (0.85 if chain["kind"] == "inner" else 0.62) * bend_sign
        points = []
        for k in range(4):
            u = k / 3.0
            point = start.lerp(end, u)
            point += side * (math.sin(math.pi * u) * bend)
            points.append(point)
        for k in range(3):
            u = (k + 0.5) / 3.0
            terminal_taper = 0.78 if j == len(chain["bones"]) - 1 else 0.90
            width = chain["widths"][j] * (1.0 - (1.0 - terminal_taper) * u)
            add_segment(
                f"{chain['kind']}_{chain['index'] + 1:02d}_{j + 1:02d}_{k + 1:02d}",
                points[k], points[k + 1], width, bone_name, material
            )

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

glow_data = bpy.data.lights.new("JF_Internal_Cyan", "POINT")
glow_data.energy = 38
glow_data.color = (0.02, 0.72, 1.0)
glow_data.shadow_soft_size = 0.42
glow_lamp = bpy.data.objects.new("JF_Internal_Cyan", glow_data)
bpy.context.collection.objects.link(glow_lamp)
glow_lamp.location = (0, 0, 0.18)

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