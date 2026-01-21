import bpy
import bmesh
from mathutils import Vector

def detect_flipped_normals(obj):
    if not obj or obj.type != 'MESH':
        return {"status": "skipped", "description": "Not a mesh"}

    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    
    flipped_faces = []
    EPSILON = 0.0001
    matrix_world = obj.matrix_world
    
    for face in bm.faces:
        local_center = face.calc_center_median()
        local_normal = face.normal
        
        world_center = matrix_world @ local_center
        world_normal = (matrix_world.to_3x3() @ local_normal).normalized()
        
        ray_origin = world_center + (world_normal * EPSILON)
        ray_direction = world_normal
        
        hit_count = 0
        curr_origin = ray_origin
        
        for _ in range(10): 
            success, location, normal, index = obj_eval.ray_cast(curr_origin, ray_direction)
            
            if success:
                hit_count += 1
                curr_origin = location + (ray_direction * EPSILON)
            else:
                break
        
        if hit_count % 2 != 0:
            flipped_faces.append(face.index)

    bm.free()

    if flipped_faces:
        return {
            "status": "error",
            "description": "Flipped Normals",
            "indices": flipped_faces
        }
    else:
        return {"status": "clean", "description": "Normals Correct"}
