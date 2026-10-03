"""Bake original April GLB colors onto supported cuboids, not invented paint."""
import bpy, json, math, os, struct, sys, zlib
import numpy as np
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

args = sys.argv[sys.argv.index('--')+1:]
if len(args) != 1:
    raise SystemExit('Usage: blender MODEL.blend -b --python bake_source_atlas.py -- TEXTURE_DIR')
folder = os.path.abspath(args[0])
os.makedirs(folder, exist_ok=True)
scene = bpy.context.scene
source = bpy.data.objects[scene['jf_primary_source_object']]
vertices = [source.matrix_world @ v.co for v in source.data.vertices]
polygons = [tuple(p.vertices) for p in source.data.polygons]
bvh = BVHTree.FromPolygons(vertices, polygons)
uvs = source.data.uv_layers.active.data
mat = source.data.materials[0]
bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
image = bsdf.inputs['Base Color'].links[0].from_node.image
iw, ih = image.size
pixels = np.empty(iw*ih*4, dtype=np.float32)
image.pixels.foreach_get(pixels)
pixels = pixels.reshape(ih, iw, 4)
triangles = [tuple(vertices[i] for i in p.vertices) for p in source.data.polygons]
triangle_uvs = [tuple(Vector((*uvs[i].uv,0)) for i in p.loop_indices) for p in source.data.polygons]
normal_transform = source.matrix_world.to_3x3().inverted().transposed()
source_normals = [normal_transform @ v.normal for v in source.data.vertices]
triangle_normals = [tuple(source_normals[i] for i in p.vertices) for p in source.data.polygons]

def source_color(point, face_index):
    triangle, coords = triangles[face_index], triangle_uvs[face_index]
    uv = barycentric_transform(point, *triangle, *coords)
    x, y = (uv.x % 1)*(iw-1), (uv.y % 1)*(ih-1)
    x0, y0 = int(x), int(y)
    tx, ty = x-x0, y-y0
    x1, y1 = min(iw-1,x0+1), min(ih-1,y0+1)
    return (pixels[y0,x0]*(1-tx)+pixels[y0,x1]*tx)*(1-ty)+(pixels[y1,x0]*(1-tx)+pixels[y1,x1]*tx)*ty

def nearest_color(point):
    hit, _, index, _ = bvh.find_nearest(point)
    return source_color(hit, index)

def write_png(path, array):
    array = np.clip(array, 0, 255).astype(np.uint8)
    h, w, _ = array.shape
    def chunk(tag, data):
        return struct.pack('>I', len(data))+tag+data+struct.pack('>I', zlib.crc32(tag+data)&0xffffffff)
    raw = b''.join(b'\0'+row.tobytes() for row in array)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b''))

atlases = {role: np.zeros((512,512,4), dtype=np.float32) for role in ('shell','tissue')}
atlases['shell'][:] = (3,7,11,238)
atlases['tissue'][:] = (12,3,12,255)
bell_normals = np.zeros((512,512,4),dtype=np.float32)
bell_normals[:] = (128,128,255,255)
fractions = (0,.11,.27,.42,.57,.72,.85,.95,1)
panel_frames = {(i,j):Quaternion(tuple(bpy.data.objects[f'JF_Bell_{i+1:02d}_{j+1:02d}']['jf_quaternion'])).conjugated()
                for i in range(32) for j in range(8)}
peak, rim = scene['jf_peak'], scene['jf_rim']
for y in range(360):
    height = peak-(y+.5)/360*(peak-rim)
    for x in range(512):
        theta = (x+.5)/512*math.tau
        radial = Vector((math.cos(theta),math.sin(theta),0))
        hit, _, index, _ = bvh.ray_cast(radial*1.3+Vector((0,0,height)),-radial,1.3)
        if height < .43 and (hit is None or math.hypot(hit.x,hit.y) < .52):
            candidate, _, candidate_index, _ = bvh.find_nearest(radial*.57+Vector((0,0,height)))
            if candidate and math.hypot(candidate.x,candidate.y) > .52:
                hit, index = candidate, candidate_index
        color = source_color(hit,index) if hit else nearest_color(radial*.03+Vector((0,0,height)))
        if hit:
            normal = barycentric_transform(hit,*triangles[index],*triangle_normals[index]).normalized()
            if normal.dot(radial) < 0:
                normal = -normal
            fraction = (height-rim)/(peak-rim)
            tier = next(j for j in range(8) if fraction <= fractions[j+1])
            local = panel_frames[(x//16,tier)] @ normal
            tangent = Vector((local.x,local.z,-local.y)).normalized()
            # Minecraft texture sets use DirectX normal convention (negative Y).
            bell_normals[y,x] = (128+tangent.x*127,128-tangent.y*127,128+tangent.z*127,255)
        # Dark, dense jelly is slightly translucent; only the lower membrane
        # is substantially see-through. Cyan markings retain their source RGB.
        alpha = 246 if y < 300 else 246-32*((y-300)/60)
        atlases['shell'][y,x] = (*np.clip(color[:3]*255,0,255), alpha)
    if y % 90 == 0:
        print('BAKE bell rows', y, flush=True)

for obj in sorted(bpy.data.objects, key=lambda o:o.name):
    if not obj.get('jf_export_cube') or obj.name.startswith('JF_Bell_') or obj.get('jf_reuse_uv'):
        continue
    role = 'shell' if obj.name.startswith('JF_outer_') else 'tissue'
    u0,v0,w,h = map(int,obj['jf_uv_rect'])
    center = Vector(obj['jf_center'])
    dims = Vector(obj['jf_dimensions'])
    rotation = Quaternion(tuple(obj['jf_quaternion']))
    for y in range(h):
        for x in range(w):
            local = Vector((((x+.5)/w-.5)*dims.x, -dims.y*.5, (.5-(y+.5)/h)*dims.z))
            point = center+rotation@local
            if obj.name.startswith('JF_Core_Link_'):
                # The new membrane occupies space above the archived oral
                # tissue. Sampling there would pick unrelated bell colors.
                # Continue the actual oral-stalk palette over the new shape.
                point.z = .16+(point.z-.16)*(.34/.735)
                radius = math.hypot(point.x,point.y)
                if radius > .16:
                    point.x *= .16/radius
                    point.y *= .16/radius
            color = nearest_color(point)
            rgb = np.clip(color[:3]*255,0,255)
            # Broad inner roots stay dark. Thin ribbons inherit the source's
            # mottled magenta, avoiding a uniformly hot-pink center.
            if obj.name.startswith(('JF_Core_','JF_Oral_Root_','JF_Skirt_')):
                rgb *= .50
            alpha = 238 if role == 'shell' else 255
            if obj.name.startswith(('JF_frill_', 'JF_leaflet_')):
                edge = abs((x+.5)/w-.5)*2
                threshold = .84+.14*(.5+.5*math.sin(y*.83+u0*.11))
                if edge > threshold:
                    alpha = 0
            atlases[role][v0+y,u0+x] = (*rgb,alpha)

for role, color in atlases.items():
    stem = 'jellyfish_boss_'+role
    rgb = color[:,:,:3]/255
    cyan = np.clip((np.minimum(rgb[:,:,1],rgb[:,:,2])-rgb[:,:,0]*1.35-.075)*2.0,0,1)
    magenta = np.clip(rgb[:,:,0]-rgb[:,:,1]*1.5-.18,0,1)
    mers = np.zeros_like(color)
    mers[:,:,1] = cyan*210 + magenta*(16 if role=='tissue' else 8)
    mers[:,:,2] = 82 if role=='shell' else 90
    mers[:,:,3] = 148 if role=='shell' else 80
    normal = np.zeros_like(color)
    normal[:] = (128,128,255,255)
    if role == 'shell':
        normal = bell_normals
    write_png(os.path.join(folder,stem+'.png'),color)
    write_png(os.path.join(folder,stem+'_normal.png'),normal)
    write_png(os.path.join(folder,stem+'_mers.png'),mers)
    payload = {'format_version':'1.21.30','minecraft:texture_set':{
        'color':stem,'normal':stem+'_normal','metalness_emissive_roughness_subsurface':stem+'_mers'}}
    with open(os.path.join(folder,stem+'.texture_set.json'),'w',encoding='utf-8') as f:
        json.dump(payload,f,indent=2)
        f.write('\n')
    print('BAKED',role,'source=',image.name,'size=512',flush=True)
