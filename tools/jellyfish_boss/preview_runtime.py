"""Render exported Bedrock JSON and its actual atlas, not substitute meshes.

Lighting/materials approximate PBR, not a screenshot or an FPS benchmark.
Rotation decoding follows Blockbench's mirror-X / negative-X,Y import path.
"""
import bpy, json, math, os, sys
from mathutils import Vector, Matrix, Euler

args = sys.argv[sys.argv.index('--')+1:]
if len(args) not in (4,5,6):
    raise SystemExit('Usage: blender -b --python preview_runtime.py -- GEOMETRY TEXTURES OUTPUT.png ANIMATION.json [still|loop] [front|underside]')
geometry_path, textures, output, animation_path = map(os.path.abspath,args[:4])
LOOP = len(args) >= 5 and args[4] == 'loop'
UNDERSIDE = len(args) == 6 and args[5] == 'underside'
if LOOP:
    os.makedirs(output,exist_ok=True)
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
with open(geometry_path,encoding='utf-8') as f:
    geometry = json.load(f)['minecraft:geometry']
with open(animation_path,encoding='utf-8') as f:
    animations = json.load(f)['animations']
    idle = animations['animation.pinene.jellyfish_boss.idle']
pulse = animations.get('animation.pinene.jellyfish_boss.pulse')
unit = 16*9.5
conversion = Matrix(((1/unit,0,0,0),(0,0,-1/unit,0),(0,1/unit,0,-1),(0,0,0,1)))
conversion_inv = conversion.inverted()
mesh_objects = {}
def sample(channel,time,default):
    if not channel:
        return default
    pairs = sorted((float(t),v) for t,v in channel.items())
    if time <= pairs[0][0]:
        return pairs[0][1]
    for (a,va),(b,vb) in zip(pairs,pairs[1:]):
        if time <= b:
            fraction = (time-a)/(b-a)
            return [x+(y-x)*fraction for x,y in zip(va,vb)]
    return pairs[-1][1]

def bone_channel(name,time):
    channel = idle['bones'].get(name,{})
    if name == 'bell' and pulse:
        channel = pulse['bones']['bell']
        time %= pulse['animation_length']
    else:
        time %= idle['animation_length']
    return sample(channel.get('rotation'),time,[0,0,0]), sample(channel.get('scale'),time,[1,1,1])

FRAME_TIME = 0.0

def rotation_matrix(values):
    x,y,z = [math.radians(v) for v in values]
    return Euler((-x,y,-z),'XYZ').to_matrix().to_4x4()

def around(pivot, rotation, scale=(1,1,1)):
    p = Vector(pivot)
    return Matrix.Translation(p) @ rotation_matrix(rotation) @ Matrix.Diagonal((*scale,1)) @ Matrix.Translation(-p)

def blender_position(p):
    unit = 16*9.5
    return (p.x/unit, -p.z/unit, (p.y-unit)/unit)

materials = {}
for role in ('shell','tissue'):
    mat = bpy.data.materials.new(role)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    color = nodes.new('ShaderNodeTexImage')
    color.image = bpy.data.images.load(os.path.join(textures,'jellyfish_boss_'+role+'.png'))
    color.interpolation = 'Linear'
    mers = nodes.new('ShaderNodeTexImage')
    mers.image = bpy.data.images.load(os.path.join(textures,'jellyfish_boss_'+role+'_mers.png'))
    mers.image.colorspace_settings.name = 'Non-Color'
    split = nodes.new('ShaderNodeSeparateColor')
    links.new(mers.outputs['Color'],split.inputs['Color'])
    links.new(color.outputs['Color'],bsdf.inputs['Base Color'])
    links.new(color.outputs['Color'],bsdf.inputs['Emission Color'])
    strength = nodes.new('ShaderNodeMath')
    strength.operation = 'MULTIPLY'
    strength.inputs[1].default_value = .65
    links.new(split.outputs['Green'],strength.inputs[0])
    links.new(strength.outputs[0],bsdf.inputs['Emission Strength'])
    links.new(split.outputs['Blue'],bsdf.inputs['Roughness'])
    normal_texture = nodes.new('ShaderNodeTexImage')
    normal_texture.image = bpy.data.images.load(os.path.join(textures,'jellyfish_boss_'+role+'_normal.png'))
    normal_texture.image.colorspace_settings.name = 'Non-Color'
    normal_map = nodes.new('ShaderNodeNormalMap')
    # Blender expects OpenGL +Y; keep the stored game texture DirectX -Y.
    separate_normal = nodes.new('ShaderNodeSeparateColor')
    combine_normal = nodes.new('ShaderNodeCombineColor')
    invert_green = nodes.new('ShaderNodeMath')
    invert_green.operation = 'SUBTRACT'
    invert_green.inputs[0].default_value = 1
    links.new(normal_texture.outputs['Color'],separate_normal.inputs['Color'])
    links.new(separate_normal.outputs['Green'],invert_green.inputs[1])
    links.new(separate_normal.outputs['Red'],combine_normal.inputs['Red'])
    links.new(invert_green.outputs[0],combine_normal.inputs['Green'])
    links.new(separate_normal.outputs['Blue'],combine_normal.inputs['Blue'])
    links.new(combine_normal.outputs['Color'],normal_map.inputs['Color'])
    links.new(normal_map.outputs['Normal'],bsdf.inputs['Normal'])
    bsdf.inputs['IOR'].default_value = 1.34
    # The runtime MERS material has no separate clear-coat layer.
    bsdf.inputs['Coat Weight'].default_value = 0
    bsdf.inputs['Metallic'].default_value = 0
    if role == 'shell':
        links.new(color.outputs['Alpha'],bsdf.inputs['Alpha'])
        bsdf.inputs['Transmission Weight'].default_value = .025
        mat.surface_render_method = 'BLENDED'
    else:
        # Binary alpha-test, like entity_alphatest: no transparent interior layer.
        cutoff = nodes.new('ShaderNodeMath')
        cutoff.operation = 'GREATER_THAN'
        cutoff.inputs[1].default_value = .5
        links.new(color.outputs['Alpha'],cutoff.inputs[0])
        links.new(cutoff.outputs[0],bsdf.inputs['Alpha'])
        mat.surface_render_method = 'DITHERED'
    materials[role] = mat

def face_points(face, a, b):
    x,y,z = a
    X,Y,Z = b
    return {
        'north':[(x,Y,z),(X,Y,z),(X,y,z),(x,y,z)],
        'south':[(X,Y,Z),(x,Y,Z),(x,y,Z),(X,y,Z)],
        'east':[(X,Y,z),(X,Y,Z),(X,y,Z),(X,y,z)],
        'west':[(x,Y,Z),(x,Y,z),(x,y,z),(x,y,Z)],
        'up':[(x,Y,Z),(X,Y,Z),(X,Y,z),(x,Y,z)],
        'down':[(x,y,z),(X,y,z),(X,y,Z),(x,y,Z)],
    }[face]

for item in geometry:
    identifier = item['description']['identifier']
    if identifier.endswith('_far'):
        continue
    role = identifier.rsplit('.',1)[-1]
    bone_transforms = {}
    for bone in item['bones']:
        rotation,scale = bone_channel(bone['name'],FRAME_TIME)
        local = around(bone['pivot'],rotation,scale)
        transform = bone_transforms.get(bone.get('parent'),Matrix.Identity(4)) @ local
        bone_transforms[bone['name']] = transform
        points, faces, uv_quads = [], [], []
        for cube in bone.get('cubes',[]):
            a = Vector(cube['origin'])
            b = a+Vector(cube['size'])
            cube_transform = around(cube.get('pivot',[0,0,0]),cube.get('rotation',[0,0,0]))
            uv = cube['uv']
            assert isinstance(uv,dict), 'Surface export requires per-face UV'
            for face, entry in uv.items():
                quad = face_points(face,a,b)
                indices = []
                for p in quad:
                    indices.append(len(points))
                    points.append(blender_position(cube_transform @ Vector(p)))
                faces.append(indices)
                u,v = entry['uv']
                w,h = entry['uv_size']
                uv_quads.append([(u/512,1-v/512),((u+w)/512,1-v/512),
                                 ((u+w)/512,1-(v+h)/512),(u/512,1-(v+h)/512)])
        if not faces:
            continue
        mesh = bpy.data.meshes.new(role+'_'+bone['name'])
        mesh.from_pydata(points,[],faces)
        mesh.update()
        uv_layer = mesh.uv_layers.new()
        for poly, coords in zip(mesh.polygons,uv_quads):
            for loop_index, coord in zip(poly.loop_indices,coords):
                uv_layer.data[loop_index].uv = coord
        obj = bpy.data.objects.new(mesh.name,mesh)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(materials[role])
        obj.matrix_world = conversion @ transform @ conversion_inv
        mesh_objects[(role,bone['name'])] = obj

scene = bpy.context.scene
target = Vector((0,0,.02))
cam_data = bpy.data.cameras.new('camera')
cam = bpy.data.objects.new('camera',cam_data)
bpy.context.collection.objects.link(cam)
cam.location = (1.3,-4.0,-2.2) if UNDERSIDE else (1.3,-4.0,.70)
cam.rotation_euler = (target-cam.location).to_track_quat('-Z','Y').to_euler()
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 2.45
scene.camera = cam
for name,location,energy,color,size in [
    ('key',(2,-3,3),160,(.78,.92,1),3),
    ('fill',(-2,-1,1),65,(.9,.6,.76),3),
    ('rim',(1,2,2),90,(.2,.72,.9),3),
]:
    data = bpy.data.lights.new(name,'AREA')
    data.energy,data.color,data.size = energy,color,size
    lamp = bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(lamp)
    lamp.location = location
    lamp.rotation_euler = (target-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 480 if LOOP else 800
if LOOP:
    scene.eevee.taa_render_samples = 16
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = output
if not scene.world:
    scene.world = bpy.data.worlds.new('World')
scene.world.color = (.018,.022,.030)
scene.view_settings.view_transform = 'Standard'
scene.view_settings.exposure = 0
if LOOP:
    frames = 144  # 12 seconds closes the 6s tentacles and 4s bell at 12 fps.
    for frame in range(frames):
        time = frame/12
        for item in geometry:
            identifier = item['description']['identifier']
            if identifier.endswith('_far'):
                continue
            role = identifier.rsplit('.',1)[-1]
            transforms = {}
            for bone in item['bones']:
                rotation,scale = bone_channel(bone['name'],time)
                transform = transforms.get(bone.get('parent'),Matrix.Identity(4)) @ around(bone['pivot'],rotation,scale)
                transforms[bone['name']] = transform
                obj = mesh_objects.get((role,bone['name']))
                if obj:
                    obj.matrix_world = conversion @ transform @ conversion_inv
        scene.render.filepath = os.path.join(output,f'frame_{frame:04d}.png')
        bpy.ops.render.render(write_still=True)
        print('MOTION_PREVIEW_FRAME',frame,flush=True)
else:
    bpy.ops.render.render(write_still=True)
print('RUNTIME_PREVIEW',output)
