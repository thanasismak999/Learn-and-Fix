import bmesh
from mathutils import Vector

def detect_inconsistent_normals(obj):
    """
    Detects faces that have inconsistent orientation relative to their neighbors.
    It checks if a face's normal points in the opposite direction of its neighbors.
    This creates 'black lines' in shading and ruins subdivision.
    """
    if obj is None or obj.type != 'MESH':
        return {
            "name": "inconsistent_normals",
            "indices": [],
            "status": "no_mesh",
            "description": "No mesh object found"
        }

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    
    inconsistent_faces = []

    for f in bm.faces:
        # Calculate the average normal of connected neighbor faces
        neighbor_normals = Vector((0,0,0))
        count = 0
        
        for edge in f.edges:
            for neighbor in edge.link_faces:
                if neighbor is not f:
                    neighbor_normals += neighbor.normal
                    count += 1
        
        if count > 0:
            avg_neighbor_normal = (neighbor_normals / count).normalized()
            # Dot product: 1.0 means same direction, -1.0 means opposite.
            if f.normal.dot(avg_neighbor_normal) < -0.1:
                inconsistent_faces.append(f.index)

    bm.free()

    status = "error" if inconsistent_faces else "ok"
    description = (
        f"Found {len(inconsistent_faces)} faces with inconsistent orientation"
        if inconsistent_faces else "Face orientation appears consistent"
    )

    return {
        "name": "inconsistent_normals",
        "indices": inconsistent_faces,
        "status": status,
        "description": description
    }
