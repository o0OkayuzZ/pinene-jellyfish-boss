"""Render the unchanged visual source from below and report rim samples."""
import bpy
import json
import math
import os
import sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
output = os.path.abspath(sys.argv[sys.argv.index("--")+1])
scene = bpy.context.scene
source = bpy.data.objects[scene["jf_primary_source_object"]]
for obj in bpy.data.objects:
    if obj.type == "MESH":
        obj.hide_render = obj != source
source.hide_render = source.hide_viewport = False
vertices = [source.matrix_world @ v.co for v in source.data.vertices]
bvh = BVHTree.FromPolygons(vertices,[tuple(p.vertices) for p in source.data.polygons])
for i in range(8):
    theta = math.tau*i/8 + .12*math.sin(i*2.13)
    radial = Vector((math.cos(theta),math.sin(theta),0))
    samples = []
    for height in (.34,.355,.37,.40):
        point,normal,face,distance = bvh.ray_cast(radial*1.3+Vector((0,0,height)),-radial,1.3)
        samples.append({"z":height,"hit":list(point) if point else None})
    print("SOURCE_RIM",i+1,json.dumps(samples),flush=True)
target = Vector((0,0,.05))
scene.camera.location = (1.35,-3.85,-2.2)
scene.camera.rotation_euler = (target-scene.camera.location).to_track_quat("-Z","Y").to_euler()
scene.render.resolution_x = scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = output
scene.view_settings.view_transform = "Standard"
scene.view_settings.exposure = 0
bpy.ops.render.render(write_still=True)
print("SOURCE_UNDERSIDE",output)
