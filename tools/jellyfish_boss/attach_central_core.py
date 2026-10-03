"""Build a rounded, upward-flaring tissue membrane inside the bell."""
import bpy, bmesh, json, math, os, sys
from mathutils import Matrix, Quaternion, Vector

LINK_PREFIX = "JF_Core_Link_"

def add_central_connection():
    for obj in list(bpy.data.objects):
        if obj.name.startswith(LINK_PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    core = bpy.data.objects["JF_Core_Center"]
    arm = bpy.data.objects["JF_Rig"]
    core_rotation = Quaternion(tuple(core["jf_quaternion"]))
    near = scene["jf_lod"] == "near"
    sectors, tier = (32,7) if near else (16,5)
    spokes = []
    for sector in range(sectors):
        panel = bpy.data.objects[f"JF_Bell_{sector+1:02d}_{tier:02d}"]
        center, dimensions = Vector(panel["jf_center"]),Vector(panel["jf_dimensions"])
        rotation = Quaternion(tuple(panel["jf_quaternion"]))
        inward = rotation @ Vector((0,1,0))
        tangent = rotation @ Vector((1,0,0))
        along = rotation @ Vector((0,0,1))
        inset = .0008
        face_offset = dimensions.y*.5-inset
        along_offset = (.895-center.z-inward.z*face_offset)/along.z
        assert abs(along_offset) < dimensions.z*.5-.009
        tip = center+inward*face_offset+along*along_offset
        shoulder = tip+inward*.18
        theta = (sector+.5)/sectors*math.tau
        radial = Vector((math.cos(theta),math.sin(theta),0))
        # Bury the foot inside the oral tissue instead of ending in a thin
        # neck above it. Small folds follow the eight oral-arm directions.
        fold = .006*math.cos(theta*8-.35)
        base = Vector(core["jf_center"])+core_rotation@Vector(((.107+fold)*math.cos(theta),(.086+fold)*math.sin(theta),.035+.012*math.sin(theta*3+.2)))
        waist = radial*(.153+.005*math.cos(theta*8-.35))+Vector((0,0,.46))
        points = [base,waist,shoulder,tip] if near else [base,shoulder,tip]
        segments = []
        for span,(start,end) in enumerate(zip(points,points[1:])):
            axis = (end-start).normalized()
            x_axis = (tangent-axis*axis.dot(tangent)).normalized()
            orientation = Matrix((x_axis,axis.cross(x_axis),axis)).transposed().to_quaternion()
            radius = max(math.hypot(p.x,p.y) for p in (start,end))
            width = 2*radius*math.tan(math.pi/sectors)*1.035
            length = (end-start).length
            midpoint = (start+end)*.5-axis*.012
            size = Vector((width,.007,length+.024))
            # The upper edge fits entirely into its actual inner bell panel.
            if span == len(points)-2:
                assert width < dimensions.x-.001
            bpy.ops.mesh.primitive_cube_add(location=midpoint)
            obj = bpy.context.object
            obj.name = LINK_PREFIX+f"{sector+1:02d}_{span+1:02d}"
            obj.rotation_mode = "QUATERNION"
            obj.rotation_quaternion = orientation
            obj.dimensions = size
            bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.delete(bm,geom=[f for f in bm.faces if abs(f.normal.y)<.999],context="FACES")
            bm.to_mesh(obj.data)
            bm.free()
            obj.data.materials.append(core.data.materials[0])
            obj["jf_export_cube"] = True
            obj["jf_bone"] = "bell"
            obj["jf_center"] = list(midpoint)
            obj["jf_dimensions"] = list(size)
            obj["jf_quaternion"] = list(orientation)
            obj["jf_material_role"] = core["jf_material_role"]
            obj["jf_open_ends"] = True
            obj["jf_surface_panel"] = True
            # New tiles are outside every existing tissue UV rectangle.
            tile = 142+(sector if near else sector*2)*3+(span if near else (0 if span==0 else 2))
            obj["jf_uv_rect"] = ((tile%32)*16,(tile//32)*48,16,48)
            obj["jf_reuse_uv"] = False
            world = obj.matrix_world.copy()
            obj.parent,obj.parent_type,obj.parent_bone = arm,"BONE","bell"
            obj.matrix_parent_inverse = (arm.matrix_world@arm.pose.bones["bell"].matrix).inverted()
            obj.matrix_world = world
            segments.append({"object":obj.name,"start":list(start),"end":list(end)})
        spokes.append({"bell_panel":panel.name,"segments":segments,"tip":list(tip),"terminal_inset":inset})
    record = {"shape":"upward_flared_membrane","core":core.name,"bone":"bell",
              "attachment_height":.895,"sectors":sectors,"spokes":spokes,
              "surface_panels":sum(len(s["segments"]) for s in spokes),
              "root_blend":"embedded_lower_foot_with_eight_soft_folds"}
    scene["jf_core_connection"] = json.dumps(record)
    scene["jf_revision"] = "v21"
    print("CENTRAL_CONNECTION",json.dumps({k:v for k,v in record.items() if k!="spokes"}),flush=True)
    return record

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--")+1:]
    if len(args) != 1:
        raise SystemExit("Usage: blender MODEL.blend -b --python attach_central_core.py -- OUTPUT.blend")
    add_central_connection()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
