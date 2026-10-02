import bpy, json, sys
from mathutils import Vector

def report(obj):
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    bounds = [[min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)]
    materials = []
    for mat in obj.data.materials:
        images = []
        if mat and mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    images.append({'name': node.image.name, 'size': list(node.image.size), 'colorspace': node.image.colorspace_settings.name})
        materials.append({'name': mat.name if mat else None, 'images': images})
    print(json.dumps({'object': obj.name, 'bounds': bounds, 'vertices': len(points), 'polygons': len(obj.data.polygons), 'uv_layers': [x.name for x in obj.data.uv_layers], 'materials': materials}))

for name in ('Meshy_Mesh_0', 'Meshy_Mesh_0.008'):
    obj = bpy.data.objects.get(name)
    if obj:
        report(obj)
before = set(bpy.data.objects)
path = sys.argv[sys.argv.index('--') + 1]
bpy.ops.import_scene.gltf(filepath=path)
for obj in set(bpy.data.objects) - before:
    if obj.type == 'MESH':
        report(obj)
