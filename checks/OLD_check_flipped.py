import bpy
import bmesh
from mathutils import Vector

def detect_flipped_normals(obj):
    """
    Detects faces pointing towards the object's center (Centroid Check).
    This assumes a generally convex shape.
    """
    if obj is None or obj.type != 'MESH':
        return {"name": "flipped", "indices": [], "status": "error", "description": "No mesh"}

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    flipped_faces = []

    center_of_mass = Vector((0,0,0))
    if len(bm.verts) > 0:
        for v in bm.verts:
            center_of_mass += v.co
        center_of_mass /= len(bm.verts)

    for f in bm.faces:
        face_center = f.calc_center_median()

        vector_to_center = (center_of_mass - face_center)

        if vector_to_center.length_squared < 0.0001:
            continue
            
        vector_to_center.normalize()

        if f.normal.dot(vector_to_center) > 0.1:
            flipped_faces.append(f.index)

    bm.free()

    status = "error" if flipped_faces else "ok"

    if flipped_faces:
        desc = f"Found {len(flipped_faces)} faces pointing towards center"
    else:
        desc = "All normals pointing outwards"

    return {
        "name": "flipped",
        "indices": flipped_faces,
        "status": status,
        "description": desc
    }

