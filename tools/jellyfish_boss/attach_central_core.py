"""Restore only the missing tissue connection from the core to the inner bell."""
import bpy, json, os, sys
from mathutils import Matrix, Quaternion, Vector

LINK_PREFIX = "JF_Core_Link_"

def add_central_connection():
    for obj in list(bpy.data.objects):
        if obj.name.startswith(LINK_PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)
    core = bpy.data.objects["JF_Core_Center"]
    panel = bpy.data.objects["JF_Bell_01_" + ("06" if bpy.context.scene["jf_lod"] == "far" else "08")]
    center = Vector(panel["jf_center"])
    dimensions = Vector(panel["jf_dimensions"])
    rotation = Quaternion(tuple(panel["jf_quaternion"]))
    inward = rotation @ Vector((0,1,0))
    # The entire terminal cap fits on an actually rendered inner panel face.
    tip = center + rotation @ Vector((0,dimensions.y*.5-.0008,dimensions.z*.20))
    neck = tip + inward*.125
    core_rotation = Quaternion(tuple(core["jf_quaternion"]))
    base = Vector(core["jf_center"]) + core_rotation @ Vector((0,0,.20))
    middle = Vector((.004,0,.64))
    points = [base,middle,neck,tip]
    widths = [(.29,.25),(.18,.16),(.030,.064)]
    segments = []
    arm = bpy.data.objects["JF_Rig"]
    for index,(start,end,(width,depth)) in enumerate(zip(points,points[1:],widths),1):
        axis = (end-start).normalized()
        if index == 3:
            tangent = rotation @ Vector((1,0,0))
            orientation = Matrix((tangent,axis.cross(tangent),axis)).transposed().to_quaternion()
        else:
            orientation = axis.to_track_quat("Z","Y")
        length = (end-start).length
        # Keep the roof end flush; overlap only toward the preceding tissue.
        midpoint = (start+end)*.5-axis*.012
        size = Vector((width,depth,length+.024))
        bpy.ops.mesh.primitive_cube_add(location=midpoint)
        obj = bpy.context.object
        obj.name = LINK_PREFIX + f"{index:02d}"
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = orientation
        obj.dimensions = size
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        obj.data.materials.append(core.data.materials[0])
        obj["jf_export_cube"] = True
        obj["jf_bone"] = "bell"
        obj["jf_center"] = list(midpoint)
        obj["jf_dimensions"] = list(size)
        obj["jf_quaternion"] = list(orientation)
        obj["jf_material_role"] = core["jf_material_role"]
        obj["jf_uv_rect"] = core["jf_uv_rect"]
        obj["jf_reuse_uv"] = True
        world = obj.matrix_world.copy()
        obj.parent, obj.parent_type, obj.parent_bone = arm,"BONE","bell"
        obj.matrix_parent_inverse = (arm.matrix_world @ arm.pose.bones["bell"].matrix).inverted()
        obj.matrix_world = world
        segments.append({"object":obj.name,"start":list(start),"end":list(end)})
    record = {"core":core.name,"bell_panel":panel.name,"bone":"bell",
              "segments":segments,"terminal_face_size":[.030,.064],
              "terminal_inset":.0008,"tip":list(tip)}
    bpy.context.scene["jf_core_connection"] = json.dumps(record)
    bpy.context.scene["jf_revision"] = "v19"
    print("CENTRAL_CONNECTION",json.dumps(record),flush=True)
    return record

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--")+1:]
    if len(args) != 1:
        raise SystemExit("Usage: blender MODEL.blend -b --python attach_central_core.py -- OUTPUT.blend")
    add_central_connection()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
