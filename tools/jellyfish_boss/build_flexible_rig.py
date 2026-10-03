import bpy, bmesh, json, math, os, sys
from mathutils import Euler, Vector, Matrix
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(args) not in (3, 4):
    raise SystemExit("Usage: blender SOURCE.blend -b --python build_flexible_rig.py -- OUTPUT.blend PREVIEW.png VISUAL_SOURCE.glb [near|far]")
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
CORE_CENTER = Vector((0,0,.13))
CORE_DIMENSIONS = Vector((.26,.22,.44))
CORE_ROTATION = Euler((.04,-.08,.18),"XYZ").to_quaternion()

def source_radius(theta, height, fallback):
    radial = Vector((math.cos(theta), math.sin(theta), 0))
    hit, _, _, _ = source_bvh.ray_cast(radial * 1.3 + Vector((0, 0, height)), -radial, 1.3)
    # Below an uneven lip, recover the outer bell rather than an oral arm.
    if height < .43 and (hit is None or math.hypot(hit.x,hit.y) < .52):
        candidate, _, _, _ = source_bvh.find_nearest(radial*.57+Vector((0,0,height)))
        if candidate and math.hypot(candidate.x,candidate.y) > .52:
            hit = candidate
    return min(0.63, max(0.008, math.hypot(hit.x, hit.y))) if hit else fallback

def outer_root_surface(theta):
    # Use the actual near model's lowest panel, rather than an arbitrary ring
    # hanging in the hollow bell. Both LOD skeletons keep this same anchor.
    sectors = 32
    sector = int((theta % math.tau) / math.tau * sectors)
    angle = math.tau*(sector+.5)/sectors
    radial = Vector((math.cos(angle),math.sin(angle),0))
    tangent = Vector((-radial.y,radial.x,0))
    heights = [RIM, RIM+(PEAK-RIM)*.11]
    radii = []
    for height in heights:
        fallback = source_radius(0,height,.57)
        radii.append(sum(source_radius(angle+step*math.tau/sectors*.25,height,fallback)*weight
                         for step,weight in ((-1,.25),(0,.5),(1,.25))))
    u = .007/(heights[1]-heights[0])
    radius = radii[0]*(1-u)+radii[1]*u
    point = radial*radius + tangent*(radius*math.tan(theta-angle))
    point.z = RIM+.007
    return point, f"JF_Bell_{sector+1:02d}_01"

def inner_root_surface(point):
    local = CORE_ROTATION.conjugated() @ (point-CORE_CENTER)
    local = Vector(min(max(v,-d*.5+.006),d*.5-.006)
                   for v,d in zip(local,CORE_DIMENSIONS))
    return CORE_CENTER + CORE_ROTATION @ local

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
attachments = []
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
        initial_root = points[0].copy()
        if kind == "outer":
            attached_root, support_name = outer_root_surface(theta)
        else:
            attached_root, support_name = inner_root_surface(initial_root), "JF_Core_Center"
        delta = attached_root-initial_root
        points[0] = attached_root
        points[1] += delta*.25
        attachments.append({"kind":kind,"index":i+1,
                            "bone":f"tentacle_{kind}_{i+1:02d}_01",
                            "initial_anchor":list(initial_root),
                            "anchor":list(attached_root),"support":support_name})
        # Only the proximal anchors change; distal curves retain v17's shape.
        anchors, anchor_widths = points, widths + [widths[-1] * .46]
        joint_count = 8 if kind == "outer" else 6
        def sample_curve(u):
            scaled = min(u, 1.0) * (len(anchors) - 1)
            n = min(int(scaled), len(anchors) - 2)
            t = scaled - n
            p1, p2 = anchors[n], anchors[n + 1]
            p0 = anchors[n - 1] if n else p1 * 2 - p2
            p3 = anchors[n + 2] if n + 2 < len(anchors) else p2 * 2 - p1
            return .5 * ((2*p1) + (-p0+p2)*t
                         + (2*p0-5*p1+4*p2-p3)*t*t
                         + (-p0+3*p1-3*p2+p3)*t*t*t)
        def sample_width(u):
            scaled = min(u, 1.0) * (len(anchor_widths) - 1)
            n = min(int(scaled), len(anchor_widths) - 2)
            t = scaled - n
            t = t*t*(3-2*t)
            return anchor_widths[n]*(1-t) + anchor_widths[n+1]*t
        points = [sample_curve(j / joint_count) for j in range(joint_count + 1)]
        widths = [sample_width((j + .5) / joint_count) for j in range(joint_count)]
        visual_points = [sample_curve(j / (joint_count*2)) for j in range(joint_count*2+1)]
        visual_widths = [sample_width((j + .5) / (joint_count*2)) for j in range(joint_count*2)]
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
                       "widths": widths, "bones": bone_names,
                       "visual_points": visual_points, "visual_widths": visual_widths})

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
add_body_lobe("Core_Center", CORE_CENTER, CORE_DIMENSIONS,
              CORE_ROTATION.to_euler("XYZ"), core_material, 0.052)
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

# Short dark oral roots meet the moving arms without rigid bars hanging below.
for i in range(4):
    theta = 2.0 * math.pi * i / 4.0 + 0.35
    radial = Vector((math.cos(theta), math.sin(theta), 0.0))
    location = radial * 0.13 + Vector((0, 0, 0.10))
    rotation = (
        0.14 * math.sin(theta),
        -0.14 * math.cos(theta),
        theta + 0.20 * math.sin(i * 1.9),
    )
    add_body_lobe(
        f"Oral_Root_{i + 1:02d}", location,
        (0.095 + 0.012 * (i % 2), 0.070, 0.25 - 0.020 * (i % 3)),
        rotation, core_material if i % 2 == 0 else violet, 0.026
    )

# The former twelve floating curtain blocks become collars at actual roots.
# Eight surround the rim filaments; four join the central oral arms to the core.
for i in range(12):
    chain = chains[i] if i < 8 else chains[8+(i-8)*2]
    axis = (chain["points"][1]-chain["points"][0]).normalized()
    location = chain["points"][0]+axis*(.014 if i < 8 else .018)
    dimensions = (.046,.025,.062) if i < 8 else (.085,.040,.065)
    rotation = axis.to_track_quat("Z","Y").to_euler("XYZ")
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

# Two short open-ended parts per near joint; the far model retains 4/3 spans.
# Reassign the former straight branches to curved secondary ribbons so the
# active face count remains exactly the tested v16 budget.
visual_cube_count = 0
segment_records = []
def record_segment(obj, start, end):
    segment_records.append({"name": obj.name, "bone": str(obj["jf_bone"]),
                            "start": list(start), "end": list(end),
                            "width": float(obj["jf_dimensions"][0])})
for chain in chains:
    is_outer = chain["kind"] == "outer"
    count = len(chain["bones"])
    fine = chain["visual_points"]
    fine_widths = chain["visual_widths"]
    spans = [(j, j+1, j//2) for j in range(count*2)] if LOD == "near" else [
        (j*4, (j+1)*4, j*2) for j in range(count//2)]
    for segment_index, (a, b, joint) in enumerate(spans):
        material = (filament_tip if a >= (count*2-4) else filament) if is_outer else (
            core_material if a < 3 else pink if a >= count*2-4 else magenta)
        width = sum(fine_widths[a:b]) / (b-a)
        obj = add_segment(f"{chain['kind']}_{chain['index']+1:02d}_{segment_index+1:02d}",
                          fine[a], fine[b], width, chain["bones"][joint], material,
                          depth_scale=.66 if is_outer else .30, length_scale=1.18)
        # Both LODs reference the same near-atlas positions.
        atlas_index = chain["index"] * count*2 + a
        rect = ((atlas_index%32)*16, 360+(atlas_index//32)*32, 16, 32) if is_outer else (
            (atlas_index%32)*16, (atlas_index//32)*48, 16, 48)
        obj["jf_uv_rect"] = rect
        record_segment(obj, fine[a], fine[b])
        visual_cube_count += 1
    if not is_outer and LOD == "near":
        # Three gently offset spans form one continuous, finer oral ribbon.
        secondary = []
        for j in range(3, 7):
            point = chain["points"][j]
            axis = chain["points"][min(j+1,count)] - chain["points"][max(0,j-1)]
            side = Vector((-axis.y,axis.x,0))
            if side.length < .0001:
                side = Vector((1,0,0))
            side.normalize()
            offset = (.034 + .006*math.sin(chain["index"]*.9+j*.8)) * (
                -1 if chain["index"] % 2 else 1)
            secondary.append(point + side*offset)
        for k in range(3):
            obj = add_segment(f"companion_{chain['index']+1:02d}_{k+1:02d}",
                              secondary[k], secondary[k+1],
                              max(.012, chain["widths"][k+3]*.32),
                              chain["bones"][k+3], magenta, depth_scale=.22,
                              length_scale=1.24)
            atlas_index = 96 + chain["index"]*3+k
            obj["jf_uv_rect"] = ((atlas_index%32)*16,(atlas_index//32)*48,16,48)
            record_segment(obj, secondary[k], secondary[k+1])
            visual_cube_count += 1

body_objects = sorted((o for o in bpy.data.objects if o.get("jf_export_cube")
                       and not o.get("jf_uv_rect")),key=lambda o:o.name)
for index,obj in enumerate(body_objects,120):
    obj["jf_uv_rect"] = ((index%32)*16,(index//32)*48,16,48)
    if str(obj["jf_material_role"]).startswith("JF_Cyan_Glow"):
        obj["jf_material_role"] = "JF_Inner_Core"

scene = bpy.context.scene
scene["jf_segment_records"] = json.dumps(segment_records)
scene["jf_attachment_records"] = json.dumps(attachments)
scene["jf_revision"] = "v18"
# Exported JSON animation is authoritative. Native previews must also be
# rendered from that JSON, rather than an unrelated Blender rig action.
scene.frame_start, scene.frame_end = 1, 121
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
