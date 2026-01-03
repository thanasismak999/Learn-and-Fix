import bpy
import bmesh
from mathutils import Vector

def detect_flipped_normals(obj):
    if obj is None or obj.type != 'MESH':
        return {"name": "flipped_normals", "indices": [], "status": "no_mesh", "description": "Δεν είναι mesh αντικείμενο"}

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.normal_update()

    # κέντρο μάζας αντικειμένου (world space)
    center = obj.matrix_world @ obj.location

    flipped = []
    for f in bm.faces:
        world_normal = (obj.matrix_world.to_3x3() @ f.normal).normalized()
        face_center = obj.matrix_world @ f.calc_center_median()
        direction = (face_center - center).normalized()

        # αν το normal δείχνει προς τα μέσα
        if world_normal.dot(direction) < 0:
            flipped.append(f.index)

    bm.free()

    status = "error" if flipped else "ok"
    description = f"Βρέθηκαν {len(flipped)} flipped faces" if flipped else "Δεν βρέθηκαν flipped normals"

    return {"name": "flipped_normals", "indices": flipped, "status": status, "description": description}
