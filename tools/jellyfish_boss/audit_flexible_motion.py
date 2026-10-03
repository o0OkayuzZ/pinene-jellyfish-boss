"""Check exported pivots and centerline continuity through a full joint loop.

Run against the tagged near .blend and exported JSON. This is a mathematical
export check, not evidence of real-game alpha sorting or frame rate.
"""
import bpy
import json
import math
import os
import sys
from mathutils import Euler, Matrix, Vector

args = sys.argv[sys.argv.index("--")+1:]
if len(args) != 3:
    raise SystemExit("Usage: blender NEAR.blend -b --python audit_flexible_motion.py -- GEO ANIMATION REPORT")
geo_path, anim_path, out_path = map(os.path.abspath,args)
with open(geo_path,encoding="utf-8") as f:
    geometries = json.load(f)["minecraft:geometry"]
with open(anim_path,encoding="utf-8") as f:
    animations = json.load(f)["animations"]
idle = animations["animation.pinene.jellyfish_boss.idle"]
pulse = animations["animation.pinene.jellyfish_boss.pulse"]
bones = {}
for geo in geometries:
    if geo["description"]["identifier"].endswith("_far"):
        continue
    for bone in geo["bones"]:
        if bone["name"] in bones:
            assert bone["pivot"] == bones[bone["name"]]["pivot"]
        bones[bone["name"]] = bone
records = json.loads(bpy.context.scene["jf_segment_records"])
attachments = json.loads(bpy.context.scene.get("jf_attachment_records","[]"))
chains = {}
for rec in records:
    if rec["name"].startswith(("JF_outer_","JF_inner_")):
        chain, segment = rec["name"].rsplit("_",1)
        chains.setdefault(chain,[]).append((int(segment),rec))
assert len(chains) == 16
def position(p):
    return Vector((p[0]*152,(p[2]+1)*152,-p[1]*152))
max_attachment_box_gap = 0
max_anchor_roundtrip = 0
near_cubes = [c for g in geometries if not g["description"]["identifier"].endswith("_far")
              for b in g["bones"] for c in b.get("cubes",[])]
if attachments:
    assert len(attachments) == 16
    for attachment in attachments:
        root = Vector(bones[attachment["bone"]]["pivot"])
        max_anchor_roundtrip = max(max_anchor_roundtrip,(root-position(attachment["anchor"])).length)
        support = bpy.data.objects[attachment["support"]]
        center = position(support["jf_center"])
        cube = min(near_cubes,key=lambda c:(Vector(c["origin"])+Vector(c["size"])*.5-center).length)
        assert (Vector(cube["origin"])+Vector(cube["size"])*.5-center).length < .002
        x,y,z = map(math.radians,cube.get("rotation",[0,0,0]))
        rotation = Euler((-x,y,-z),"XYZ").to_matrix()
        pivot = Vector(cube.get("pivot",[0,0,0]))
        local = pivot + rotation.transposed() @ (root-pivot)
        low = Vector(cube["origin"])
        high = low+Vector(cube["size"])
        delta = Vector([max(a-v,0,v-b) for v,a,b in zip(local,low,high)])
        max_attachment_box_gap = max(max_attachment_box_gap,delta.length)
    assert max_attachment_box_gap < .002, max_attachment_box_gap
    assert max_anchor_roundtrip < .002, max_anchor_roundtrip
connection = json.loads(bpy.context.scene.get("jf_core_connection","{}"))
connection_gap = 0
terminal_plane_error = 0
if connection:
    owners = {id(c):b["name"] for g in geometries for b in g["bones"] for c in b.get("cubes",[])}
    def exported_object(name):
        obj = bpy.data.objects[name]
        center = position(obj["jf_center"])
        cube = min(near_cubes,key=lambda c:(Vector(c["origin"])+Vector(c["size"])*.5-center).length)
        assert (Vector(cube["origin"])+Vector(cube["size"])*.5-center).length < .002
        assert owners[id(cube)] == obj["jf_bone"] == "bell"
        x,y,z = map(math.radians,cube.get("rotation",[0,0,0]))
        return cube,Euler((-x,y,-z),"XYZ").to_matrix(),Vector(cube.get("pivot",[0,0,0]))
    def inside_exported(point,name):
        cube,rotation,pivot = exported_object(name)
        local = pivot+rotation.transposed()@(point-pivot)
        low = Vector(cube["origin"])
        high = low+Vector(cube["size"])
        return Vector([max(a-v,0,v-b) for v,a,b in zip(local,low,high)]).length
    links = connection["segments"]
    assert len(links) == 3
    connection_gap = inside_exported(position(links[0]["start"]),connection["core"])
    for index,link in enumerate(links):
        for endpoint in ("start","end"):
            p = position(link[endpoint])
            connection_gap = max(connection_gap,inside_exported(p,link["object"]))
        if index:
            p = position(link["start"])
            connection_gap = max(connection_gap,inside_exported(p,links[index-1]["object"]))
    # Check the complete terminal cap against the exported inner north face.
    cube,rotation,pivot = exported_object(links[-1]["object"])
    panel,panel_rotation,panel_pivot = exported_object(connection["bell_panel"])
    low,high = Vector(cube["origin"]),Vector(cube["origin"])+Vector(cube["size"])
    for x in (low.x,high.x):
        for z in (low.z,high.z):
            p = pivot+rotation@(Vector((x,high.y,z))-pivot)
            connection_gap = max(connection_gap,inside_exported(p,connection["bell_panel"]))
            local = panel_pivot+panel_rotation.transposed()@(p-panel_pivot)
            terminal_plane_error = max(terminal_plane_error,abs(local.z-panel["origin"][2]-connection["terminal_inset"]*152))
    assert connection_gap < .002, connection_gap
    assert terminal_plane_error < .002, terminal_plane_error
def sample(channel,time,default):
    if not channel:
        return default
    pairs = sorted((float(t),v) for t,v in channel.items())
    for (a,va),(b,vb) in zip(pairs,pairs[1:]):
        if time <= b:
            u = max(0,(time-a)/(b-a))
            return [x+(y-x)*u for x,y in zip(va,vb)]
    return pairs[-1][1]
max_gap = 0
max_radius = 0
min_y, max_y = 1e6, -1e6
sample_count = 481
for frame in range(sample_count):
    time = 12*frame/(sample_count-1)
    transforms = {}
    for name,bone in bones.items():
        animation = pulse if name == "bell" else idle
        channel = animation["bones"].get(name,{})
        t = time % animation["animation_length"]
        angles = sample(channel.get("rotation"),t,[0,0,0])
        scale = sample(channel.get("scale"),t,[1,1,1])
        x,y,z = map(math.radians,angles)
        pivot = Vector(bone["pivot"])
        local = Matrix.Translation(pivot) @ Euler((-x,y,-z),"XYZ").to_matrix().to_4x4()
        local = local @ Matrix.Diagonal((*scale,1)) @ Matrix.Translation(-pivot)
        transforms[name] = transforms.get(bone.get("parent"),Matrix.Identity(4)) @ local
    for chain in chains.values():
        items = [r for _,r in sorted(chain)]
        for left,right in zip(items,items[1:]):
            a = transforms[left["bone"]] @ position(left["end"])
            b = transforms[right["bone"]] @ position(right["start"])
            max_gap = max(max_gap,(a-b).length)
        for rec in items:
            for endpoint in ("start","end"):
                p = transforms[rec["bone"]] @ position(rec[endpoint])
                max_radius = max(max_radius,math.hypot(p.x,p.z)/16)
                min_y, max_y = min(min_y,p.y/16),max(max_y,p.y/16)
assert max_gap < .002, max_gap
assert max_radius < 7.5 and min_y > -1 and max_y < 20.3
seam_velocity_change = 0
for bone in idle["bones"].values():
    keys = list(bone["rotation"].values())
    for a,b,c,d in zip(keys[0],keys[1],keys[-2],keys[-1]):
        seam_velocity_change = max(seam_velocity_change,abs((b-a)-(d-c))/.125)
assert seam_velocity_change < 1.5, seam_velocity_change
report = {
    "revision":bpy.context.scene.get("jf_revision","v17"),"sampled_poses":sample_count,
    "independent_tentacles":16,"near_animated_bones":113,
    "maximum_centerline_joint_gap_model_units":max_gap,
    "maximum_centerline_radius_blocks":max_radius,
    "centerline_y_blocks":[min_y,max_y],
    "maximum_loop_velocity_change_degrees_per_second":seam_velocity_change,
    "verified_root_attachments":len(attachments),
    "maximum_root_to_support_box_gap_model_units":max_attachment_box_gap,
    "maximum_root_anchor_roundtrip_error_model_units":max_anchor_roundtrip,
    "root_attachments":attachments,
    "verified_core_connection_links":len(connection.get("segments",[])),
    "maximum_core_connection_gap_model_units":connection_gap,
    "maximum_terminal_inner_face_plane_error_model_units":terminal_plane_error,
    "core_connection":connection,
    "scope":"Exported pivot math; excludes engine/material/FPS verification"}
with open(out_path,"w",encoding="utf-8") as f:
    json.dump(report,f,indent=2)
    f.write("\n")
print("MOTION_AUDIT",json.dumps(report),flush=True)
