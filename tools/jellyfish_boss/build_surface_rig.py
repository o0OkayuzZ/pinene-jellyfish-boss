import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(args) not in (3, 4):
    raise SystemExit("Usage: blender SOURCE.blend -b --python build_surface_rig.py -- OUTPUT.blend PREVIEW.png VISUAL_SOURCE.glb [near|far]")
OUT, PREVIEW, VISUAL_SOURCE = map(os.path.abspath, args[:3])
LOD = args[3] if len(args) == 4 else "near"
assert LOD in ("near", "far")
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

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=VISUAL_SOURCE)
visual_source = next(obj for obj in set(bpy.data.objects) - before if obj.type == 'MESH')
visual_source.hide_render = visual_source.hide_viewport = True
source_vertices = [visual_source.matrix_world @ v.co for v in visual_source.data.vertices]
source_polygons = [tuple(p.vertices) for p in visual_source.data.polygons]
source_bvh = BVHTree.FromPolygons(source_vertices, source_polygons)
PEAK = max(v.z for v in source_vertices)
RIM = 0.355

def source_radius(theta, height, fallback):
    radial = Vector((math.cos(theta), math.sin(theta), 0))
    hit, _, _, _ = source_bvh.ray_cast(radial * 1.3 + Vector((0, 0, height)), -radial, 1.3)
    return min(0.63, max(0.008, math.hypot(hit.x, hit.y))) if hit else fallback

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

def add_mottled_color(mat, scale, phase, colors=None):
    if colors is None:
        colors = [
            (0.0010, 0.0004, 0.0020, 1.0),
            (0.018, 0.0010, 0.010, 1.0),
            (0.095, 0.0040, 0.045, 1.0),
            (0.18, 0.0080, 0.090, 1.0),
            (0.003, 0.030, 0.035, 1.0),
            (0.004, 0.0020, 0.008, 1.0),
        ]
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
    color_ramp.elements[0].color = colors[0]
    color_ramp.elements[1].position = 0.84
    color_ramp.elements[1].color = colors[5]
    for position, color in zip((0.50, 0.66, 0.75, 0.79), colors[1:5]):
        item = color_ramp.elements.new(position)
        item.color = color
    links.new(geometry.outputs["Position"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

# Bedrock target: alphablend gel body, opaque inner mass, emissive-alpha markings.
pink = make_material("JF_Gel_Pink", (0.20, 0.008, 0.11), 0.0, 0.28, 0.88,
                     0.05, (0.58, 0.018, 0.31), 0.52, 0.12)
magenta = make_material("JF_Gel_Magenta", (0.080, 0.002, 0.045), 0.0, 0.30, 0.92,
                        0.03, (0.28, 0.009, 0.15), 0.24, 0.10)
violet = make_material("JF_Gel_Violet", (0.008, 0.0015, 0.016), 0.0, 0.26, 0.96,
                       0.02, (0.005, 0.015, 0.020), 0.02, 0.08)
core_material = make_material("JF_Inner_Core", (0.0015, 0.001, 0.0035), 0.0, 0.38, 1.0,
                              0.0, None, 0.0)
cyan_glow = make_material("JF_Cyan_Glow", (0.004, 0.22, 0.26), 0.0, 0.48, 0.96,
                          0.0, (0.006, 0.72, 0.86), 0.85, 0.04)
cyan_bsdf = cyan_glow.node_tree.nodes.get("Principled BSDF")
set_input(cyan_bsdf, "Coat Weight", 0.0)
set_input(cyan_bsdf, "Specular IOR Level", 0.18)
filament = make_material("JF_Gel_Filament", (0.002, 0.008, 0.010), 0.0, 0.28, 0.90,
                         0.04, (0.003, 0.12, 0.14), 0.12, 0.08)
filament_tip = make_material("JF_Gel_Filament_Tip", (0.040, 0.002, 0.025), 0.0, 0.28, 0.86,
                             0.04, (0.16, 0.006, 0.09), 0.10, 0.08)
frill = make_material("JF_Gel_Frill", (0.12, 0.004, 0.070), 0.0, 0.30, 0.84,
                      0.05, (0.52, 0.016, 0.28), 0.42, 0.10)
bell_gel = make_material("JF_Bell_Gel", (0.0006, 0.0015, 0.0025), 0.0, 0.24, 0.91,
                         0.10, (0.002, 0.018, 0.024), 0.015, 0.18)
bell_rim = make_material("JF_Bell_Rim", (0.012, 0.001, 0.008), 0.0, 0.32, 0.94,
                         0.06, (0.05, 0.002, 0.025), 0.04, 0.10)
for bell_material in (bell_gel, bell_rim):
    bell_bsdf = bell_material.node_tree.nodes.get("Principled BSDF")
    set_input(bell_bsdf, "Coat Weight", 0.08)
    set_input(bell_bsdf, "Specular IOR Level", 0.22)
violet_palette = [
    (0.0005, 0.0003, 0.0010, 1.0),
    (0.003, 0.0007, 0.004, 1.0),
    (0.010, 0.0010, 0.012, 1.0),
    (0.025, 0.0015, 0.015, 1.0),
    (0.002, 0.015, 0.018, 1.0),
    (0.001, 0.0020, 0.004, 1.0),
]
magenta_palette = [
    (0.001, 0.0004, 0.0015, 1.0),
    (0.012, 0.0010, 0.008, 1.0),
    (0.065, 0.0030, 0.035, 1.0),
    (0.22, 0.010, 0.12, 1.0),
    (0.004, 0.035, 0.040, 1.0),
    (0.004, 0.0010, 0.005, 1.0),
]
pink_palette = [
    (0.003, 0.0008, 0.0020, 1.0),
    (0.035, 0.0020, 0.020, 1.0),
    (0.14, 0.0080, 0.075, 1.0),
    (0.38, 0.020, 0.20, 1.0),
    (0.008, 0.080, 0.090, 1.0),
    (0.010, 0.0030, 0.012, 1.0),
]
add_mottled_color(violet, 7.5, 0.05, violet_palette)
add_mottled_color(magenta, 8.5, 0.10, magenta_palette)
add_mottled_color(pink, 9.5, 0.15, pink_palette)
add_mottled_color(frill, 12.0, 0.21, pink_palette)
filament_palette = [
    (0.0008, 0.0015, 0.0025, 1.0),
    (0.002, 0.012, 0.015, 1.0),
    (0.005, 0.14, 0.16, 1.0),
    (0.10, 0.003, 0.060, 1.0),
    (0.003, 0.055, 0.065, 1.0),
    (0.0015, 0.004, 0.007, 1.0),
]
add_mottled_color(filament, 11.0, 0.22, filament_palette)
add_mottled_color(filament_tip, 12.0, 0.28, filament_palette)
bell_palette = [
    (0.0003, 0.0005, 0.0008, 1.0),
    (0.0008, 0.0030, 0.0045, 1.0),
    (0.0020, 0.015, 0.020, 1.0),
    (0.018, 0.0010, 0.012, 1.0),
    (0.0015, 0.0080, 0.011, 1.0),
    (0.0005, 0.0015, 0.0025, 1.0),
]
add_mottled_color(bell_gel, 6.5, 0.18, bell_palette)
add_mottled_color(bell_rim, 8.0, 0.24, bell_palette)

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
        theta = 2.0 * math.pi * i / count
        theta += 0.12 * math.sin(i * 2.13) if kind == "outer" else (
            math.pi / 8 + 0.075 * math.sin(i * 1.71)
        )
        radial = Vector((math.cos(theta), math.sin(theta), 0))
        tangent = Vector((-math.sin(theta), math.cos(theta), 0))
        phase = 0.73 * i + (0.4 if kind == "inner" else 0)
        if kind == "outer":
            # Long, fine swimming filaments around the bell perimeter.
            r = 0.50 + 0.040 * math.sin(phase * 1.7)
            final_drop = -0.62 - 0.22 * (0.5 + 0.5 * math.sin(phase * 1.9))
            points = [
                radial * r + Vector((0, 0, 0.34)),
                radial * (r + 0.050) + tangent * (0.08 * math.sin(phase)) + Vector((0, 0, 0.10)),
                radial * r - tangent * (0.17 * math.cos(phase + 0.3)) + Vector((0, 0, -0.16)),
                radial * (r - 0.050) + tangent * (0.24 * math.sin(phase + 0.8)) + Vector((0, 0, -0.42)),
                radial * (r + 0.030) - tangent * (0.25 * math.cos(phase + 0.5)) + Vector((0, 0, final_drop)),
            ]
            widths = [0.026, 0.022, 0.017, 0.009]
        else:
            # Broad oral-arm ribbons form the dense, irregular center mass.
            r = 0.13 + 0.025 * math.cos(phase * 1.3)
            points = [
                radial * r + Vector((0, 0, 0.33)),
                radial * (r + 0.025) + tangent * (0.08 * math.sin(phase + 0.2)) + Vector((0, 0, 0.05)),
                radial * (r + 0.16) - tangent * (0.17 * math.cos(phase + 0.7)) + Vector((0, 0, -0.20)),
                radial * (r + 0.10) + tangent * (0.19 * math.sin(phase + 1.1)) + Vector((0, 0, -0.64 - 0.14 * math.cos(phase))),
            ]
            widths = [0.110, 0.085, 0.055]
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
hood.hide_render = True
hood.hide_viewport = True

def tag_export_cube(obj, bone_name, center, dimensions, rotation_quaternion, material):
    obj["jf_export_cube"] = True
    obj["jf_bone"] = bone_name
    obj["jf_center"] = tuple(float(v) for v in center)
    obj["jf_dimensions"] = tuple(float(v) for v in dimensions)
    obj["jf_quaternion"] = (
        float(rotation_quaternion.w), float(rotation_quaternion.x),
        float(rotation_quaternion.y), float(rotation_quaternion.z)
    )
    obj["jf_material_role"] = material.name

def remove_local_z_caps(obj):
    """Delete only the two length-axis caps used at overlapping joins."""
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    caps = [face for face in bm.faces if abs(face.normal.z) > 0.999]
    bmesh.ops.delete(bm, geom=caps, context="FACES")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

def add_body_lobe(name, location, dimensions, rotation, material, bevel_width):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = "JF_" + name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new("Gel rounding", "BEVEL")
    bevel.width, bevel.segments = bevel_width, 3
    obj.data.materials.append(material)
    tag_export_cube(
        obj, "bell", Vector(location), Vector(dimensions),
        obj.rotation_euler.to_quaternion(), material
    )
    world = obj.matrix_world.copy()
    obj.parent, obj.parent_type, obj.parent_bone = arm, "BONE", "bell"
    obj.matrix_parent_inverse = (arm.matrix_world @ arm.pose.bones["bell"].matrix).inverted()
    obj.matrix_world = world
    return obj

# Irregular inner tissue remains readable through the translucent shell without
# turning the boss into a single obvious cube.
add_body_lobe("Core_Center", (0.00, 0.00, 0.13), (0.26, 0.22, 0.44),
              (0.04, -0.08, 0.18), core_material, 0.052)
add_body_lobe("Core_Left", (-0.14, -0.01, 0.08), (0.14, 0.11, 0.43),
              (-0.24, 0.30, -0.42), violet, 0.036)
add_body_lobe("Core_Right", (0.14, 0.025, 0.09), (0.14, 0.11, 0.45),
              (0.22, -0.30, 0.48), core_material, 0.036)
add_body_lobe("Core_Back", (0.015, 0.12, 0.12), (0.16, 0.12, 0.39),
              (0.28, 0.14, -0.16), core_material, 0.034)
add_body_lobe("Core_Lower", (0.00, -0.02, -0.13), (0.18, 0.16, 0.28),
              (-0.12, 0.18, 0.24), violet, 0.038)
add_body_lobe("Lumen", (0.00, -0.075, 0.19), (0.055, 0.045, 0.18),
              (0.05, 0.10, 0.22), cyan_glow, 0.018)

# Four heavy oral roots restore the source's near-black underside mass.
for i in range(4):
    theta = 2.0 * math.pi * i / 4.0 + 0.35
    radial = Vector((math.cos(theta), math.sin(theta), 0.0))
    location = radial * 0.13 + Vector((0, 0, 0.00))
    rotation = (
        0.14 * math.sin(theta),
        -0.14 * math.cos(theta),
        theta + 0.20 * math.sin(i * 1.9),
    )
    add_body_lobe(
        f"Oral_Root_{i + 1:02d}", location,
        (0.095 + 0.012 * (i % 2), 0.070, 0.44 - 0.035 * (i % 3)),
        rotation, core_material if i % 2 == 0 else violet, 0.026
    )

# Uneven oral curtain hides the hard join between bell and articulated chains.
for i in range(12):
    theta = 2.0 * math.pi * i / 12.0
    radius = 0.39 + 0.018 * math.sin(i * 1.73)
    location = (math.cos(theta) * radius, math.sin(theta) * radius,
                0.305 - 0.014 * (i % 3))
    dimensions = (0.044 + 0.009 * (i % 2), 0.026, 0.12 + 0.026 * ((i + 1) % 3))
    rotation = (0.09 * math.sin(theta), 0.08 * math.cos(theta), theta)
    skirt_material = core_material if i % 3 else violet
    add_body_lobe(f"Skirt_{i + 1:02d}", location, dimensions, rotation,
                  skirt_material, 0.009)

def add_segment(name, start, end, width, bone_name, material,
                depth_scale=0.86, length_scale=1.22):
    direction = end - start
    length = direction.length
    midpoint = (start + end) * 0.5
    bpy.ops.mesh.primitive_cube_add(location=midpoint)
    obj = bpy.context.object
    obj.name = "JF_" + name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    obj.dimensions = (width, max(width * depth_scale, 0.006), length * length_scale)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    remove_local_z_caps(obj)
    obj["jf_open_ends"] = True
    # Runtime cubes have no bevel: keep source and exported previews consistent.
    obj.data.materials.append(material)
    tag_export_cube(
        obj, bone_name, midpoint,
        Vector((width, max(width * depth_scale, 0.006), length * length_scale)),
        obj.rotation_quaternion.copy(), material
    )
    world = obj.matrix_world.copy()
    obj.parent = arm
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_parent_inverse = (arm.matrix_world @ arm.pose.bones[bone_name].matrix).inverted()
    obj.matrix_world = world
    return obj

def add_bell_panel(name, start, end, radial, tangent_width, normal_depth,
                   material, outward_offset=0.0, length_scale=1.07):
    direction = end - start
    length = direction.length
    z_axis = direction.normalized()
    x_axis = Vector((-radial.y, radial.x, 0.0)).normalized()
    y_axis = z_axis.cross(x_axis).normalized()
    midpoint = (start + end) * 0.5 - y_axis * outward_offset
    bpy.ops.mesh.primitive_cube_add(location=midpoint)
    obj = bpy.context.object
    obj.name = "JF_" + name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Matrix((x_axis, y_axis, z_axis)).transposed().to_quaternion()
    obj.dimensions = (tangent_width, normal_depth, length * length_scale)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    remove_local_z_caps(obj)
    obj["jf_open_ends"] = True
    obj["jf_surface_panel"] = True
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.normal.y) < 0.999], context='FACES')
    bm.to_mesh(obj.data)
    bm.free()
    # Bedrock cuboids have hard edges; omitting Blender bevels keeps the preview
    # honest and avoids drawing a fake dark grid around every shell panel.
    obj.data.materials.append(material)
    tag_export_cube(
        obj, "bell", midpoint,
        Vector((tangent_width, normal_depth, length * length_scale)),
        obj.rotation_quaternion.copy(), material
    )
    world = obj.matrix_world.copy()
    obj.parent, obj.parent_type, obj.parent_bone = arm, "BONE", "bell"
    obj.matrix_parent_inverse = (arm.matrix_world @ arm.pose.bones["bell"].matrix).inverted()
    obj.matrix_world = world
    return obj

# Thin, two-face panels follow the archived GLB profile. Color, cyan rays and
# spots are baked into a shared panoramic atlas, not separate cuboids.
bell_cube_count = 0
sector_count = 32 if LOD == "near" else 16
height_fractions = (0, .11, .27, .42, .57, .72, .85, .95, 1) if LOD == "near" else (0, .20, .40, .62, .82, .95, 1)
bell_heights = [RIM + (PEAK - RIM) * f for f in height_fractions]
bell_radii = [source_radius(0, h, .61 * math.sqrt(max(0, 1 - f*f))) for h, f in zip(bell_heights, height_fractions)]
for i in range(sector_count):
    theta = 2.0 * math.pi * (i + .5) / sector_count
    radial = Vector((math.cos(theta), math.sin(theta), 0.0))
    points = []
    for ring, height in enumerate(bell_heights):
        radius = sum(source_radius(theta + step * 2*math.pi/sector_count*.25, height, bell_radii[ring]) * weight for step, weight in ((-1,.25),(0,.5),(1,.25)))
        if ring == len(bell_heights) - 1:
            radius = 0.005
        points.append(radial * radius + Vector((0, 0, height)))
    for tier in range(len(points) - 1):
        start, end = points[tier:tier+2]
        # Use the larger ring radius so adjacent rectangles cover the taper.
        radius = max(math.hypot(p.x, p.y) for p in (start, end))
        width = max(.018, 2*radius*math.tan(math.pi/sector_count)*1.035)
        obj = add_bell_panel(f"Bell_{i+1:02d}_{tier+1:02d}", start, end, radial, width, .005, bell_gel)
        v0 = 360 * (PEAK - end.z) / (PEAK - RIM)
        v1 = 360 * (PEAK - start.z) / (PEAK - RIM)
        obj["jf_uv_rect"] = (i * 512/sector_count, v0, 512/sector_count, v1-v0)
        bell_cube_count += 1

# Three open-ended cuboids per bone preserve curved, overlapping chains.
# Far LOD uses one; independent tentacle bone names and pivots remain stable.
visual_cube_count = 0
for chain in chains:
    for j, bone_name in enumerate(chain["bones"]):
        is_outer = chain["kind"] == "outer"
        if is_outer:
            material = filament_tip if j == len(chain["bones"]) - 1 else filament
            depth_scale = 0.72
            bend_scale = 0.48
            terminal_taper = 0.56 if j == len(chain["bones"]) - 1 else 0.86
        else:
            material = core_material if j == 0 else (
                pink if j == len(chain["bones"]) - 1 else magenta
            )
            depth_scale = 0.46
            bend_scale = 1.08
            terminal_taper = 0.62 if j == len(chain["bones"]) - 1 else 0.86

        start, end = chain["points"][j], chain["points"][j + 1]
        axis = end - start
        side = Vector((-axis.y, axis.x, 0.0))
        if side.length < 0.0001:
            side = Vector((1.0, 0.0, 0.0))
        side.normalize()
        bend_sign = 1.0 if ((chain["index"] + j) % 2 == 0) else -1.0
        bend = chain["widths"][j] * bend_scale * bend_sign
        points = []
        segments = 3 if LOD == "near" else 1
        for k in range(segments + 1):
            u = k / segments
            point = start.lerp(end, u)
            point += side * (math.sin(math.pi * u) * bend)
            points.append(point)
        for k in range(segments):
            u = (k + 0.5) / segments
            width = chain["widths"][j] * (1.0 - (1.0 - terminal_taper) * u)
            add_segment(
                f"{chain['kind']}_{chain['index'] + 1:02d}_{j + 1:02d}_{k + 1:02d}",
                points[k], points[k + 1], width, bone_name, material,
                depth_scale=depth_scale
            )
            visual_cube_count += 1

        if not is_outer and LOD == "near":
            companion_sign = -1.0 if ((chain["index"] + j) % 2 == 0) else 1.0
            offset = side * (0.035 * companion_sign)
            add_segment(f"companion_{chain['index']+1:02d}_{j+1:02d}", points[0]+offset,
                        points[-1]+offset*.6, max(chain["widths"][j]*.38, .014),
                        bone_name, magenta, depth_scale=.28, length_scale=1.22)
            visual_cube_count += 1
            anchor = points[1].lerp(points[2], .45)
            branch_sign = -companion_sign
            length = .075 + .022*j + .015*math.sin(chain["index"]*1.3+j)
            middle = anchor + side*(branch_sign*length*.55) + Vector((0,0,-.028))
            tip = anchor + side*(branch_sign*length) + Vector((0,0,-.065-.015*j))
            add_segment(f"frill_{chain['index']+1:02d}_{j+1:02d}_01", anchor, middle,
                        max(chain["widths"][j]*.32, .014), bone_name, frill, depth_scale=.3)
            add_segment(f"frill_{chain['index']+1:02d}_{j+1:02d}_02", middle, tip,
                        max(chain["widths"][j]*.20, .010), bone_name, frill, depth_scale=.3)
            visual_cube_count += 2
            if j == 2:
                anchor = points[2]
                tip = anchor - side*branch_sign*.06 + Vector((0,0,-.07))
                add_segment(f"leaflet_{chain['index']+1:02d}", anchor, tip, .014,
                            bone_name, pink, depth_scale=.3)
                visual_cube_count += 1

# Stable atlas addresses are shared by both LODs. The shell's upper 360 pixels
# form a continuous source-baked panorama; filaments occupy the lower 144.
body_names = sorted(o.name for o in bpy.data.objects if o.get("jf_export_cube")
                    and not any(o.name.startswith("JF_"+p) for p in ("Bell_", "outer_", "inner_", "companion_", "frill_", "leaflet_")))
for obj in bpy.data.objects:
    if not obj.get("jf_export_cube") or obj.get("jf_surface_panel"):
        continue
    parts = obj.name.split("_")
    kind = parts[1]
    if kind == "outer":
        i, j, k = map(int, parts[2:5])
        index = ((i-1)*4+j-1)*3+k-1
        obj["jf_uv_rect"] = ((index%32)*16, 360+(index//32)*48, 16, 48)
    else:
        if kind == "inner":
            i,j,k = map(int, parts[2:5])
            index = ((i-1)*3+j-1)*3+k-1
        elif kind == "companion":
            i,j = map(int, parts[2:4])
            index = 72+(i-1)*3+j-1
        elif kind == "frill":
            i,j,k = map(int, parts[2:5])
            index = 96+((i-1)*3+j-1)*2+k-1
        elif kind == "leaflet":
            index = 144+int(parts[2])-1
        else:
            index = 152+body_names.index(obj.name)
        obj["jf_uv_rect"] = ((index%32)*16, (index//32)*48, 16, 48)
        if str(obj["jf_material_role"]).startswith("JF_Cyan_Glow"):
            obj["jf_material_role"] = "JF_Inner_Core"

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
                amp * 0.72 * math.cos(t + base_phase + j * 0.40),
                amp * 0.25 * math.sin(2.0 * t + base_phase + j * 0.30),
            )
            pose.keyframe_insert(data_path="rotation_euler", frame=frame)
    bell_pose = arm.pose.bones["bell"]
    pulse = 1.0 + 0.025 * math.sin(t)
    bell_pose.scale = (pulse, pulse, 1.0 - 0.018 * math.sin(t))
    bell_pose.keyframe_insert(data_path="scale", frame=frame)

target = Vector((0, 0, 0.02))
cam_data = bpy.data.cameras.new("JF_Camera")
cam = bpy.data.objects.new("JF_Camera", cam_data)
bpy.context.collection.objects.link(cam)
cam.location = (1.35, -3.85, 0.72)
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 62
scene.camera = cam
for name, loc, energy, color, size in [
    ("JF_Key", (2.4, -2.2, 2.7), 520, (0.62, 0.88, 1.0), 2.4),
    ("JF_Fill", (-2.0, -0.3, 1.1), 110, (1.0, 0.18, 0.48), 2.0),
]:
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.color, data.size = energy, color, size
    lamp = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(lamp)
    lamp.location = loc
    lamp.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

glow_data = bpy.data.lights.new("JF_Internal_Cyan", "POINT")
glow_data.energy = 10
glow_data.color = (0.02, 0.72, 1.0)
glow_data.shadow_soft_size = 0.42
glow_lamp = bpy.data.objects.new("JF_Internal_Cyan", glow_data)
bpy.context.collection.objects.link(glow_lamp)
glow_lamp.location = (0, 0, 0.18)

pink_data = bpy.data.lights.new("JF_Oral_Magenta", "POINT")
pink_data.energy = 65
pink_data.color = (1.0, 0.015, 0.24)
pink_data.shadow_soft_size = 0.38
pink_lamp = bpy.data.objects.new("JF_Oral_Magenta", pink_data)
bpy.context.collection.objects.link(pink_lamp)
pink_lamp.location = (0.0, -0.10, -0.20)

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 700
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = PREVIEW
if scene.world is None:
    scene.world = bpy.data.worlds.new("World")
scene.world.color = (0.004, 0.005, 0.009)
scene.view_settings.exposure = -0.35
try:
    scene.view_settings.look = "AgX - Medium High Contrast"
except TypeError:
    pass
scene["jf_lod"] = LOD
scene["jf_visual_source"] = VISUAL_SOURCE
scene["jf_peak"] = PEAK
scene["jf_rim"] = RIM
scene["jf_primary_source_object"] = visual_source.name
# Preview is rendered from exported JSON later, never from beveled substitutes.
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print(f"SAVED {OUT}")
print(f"PREVIEW {PREVIEW}")
print(f"RIG tentacles={len(chains)} tentacle_bones={sum(len(c['bones']) for c in chains)} tentacle_cubes={visual_cube_count} bell_cubes={bell_cube_count}")
