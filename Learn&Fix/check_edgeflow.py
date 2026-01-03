import bmesh
from mathutils import Vector  # Import Vector directly from mathutils

def detect_edge_flow(obj, flatness_threshold=0.7):
    """
    Detects interruptions in edge flow (Poles) on smooth surfaces.
    
    Logic:
    1. Finds vertices where Valence != 4.
    2. Checks the curvature (angle between connected face normals).
    3. If faces are sharp (like a cube corner), it's ignored (structural pole).
    4. If faces are mostly flat (smooth surface), it's flagged (shading pinch).
    """
    if obj is None or obj.type != 'MESH':
        return {
            "name": "edge_flow",
            "indices": [],
            "status": "no_mesh",
            "description": "No mesh object found"
        }

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    flow_breaks = []

    for v in bm.verts:
        # Skip boundary vertices
        if v.is_boundary:
            continue
            
        valence = len(v.link_edges)
        
        # If it's a perfect grid node, skip
        if valence == 4:
            continue

        # --- SMART CHECK: IS IT A SHARP CORNER? ---
        # Get normals of all connected faces
        face_normals = [f.normal for f in v.link_faces]
        
        if not face_normals:
            continue
            
        # Calculate the Average Normal
        # Χρησιμοποιούμε Vector((0,0,0)) ως αρχική τιμή για να αποφύγουμε errors
        avg_normal = sum(face_normals, Vector((0,0,0)))
        
        # Normalize the result (make it length 1)
        if avg_normal.length_squared > 0:
            avg_normal.normalize()
        else:
            continue

        # Check how much the faces deviate from the average normal.
        min_dot = 1.0
        for n in face_normals:
            dot = n.dot(avg_normal)
            if dot < min_dot:
                min_dot = dot
        
        # Threshold 0.7 covers roughly 45 degrees. 
        if min_dot > flatness_threshold:
            flow_breaks.append(v.index)

    bm.free()

    status = "warning" if flow_breaks else "ok"
    description = (
        f"Found {len(flow_breaks)} poles disrupting flow on smooth surfaces"
        if flow_breaks else "No significant edge flow breaks on smooth surfaces"
    )

    return {
        "name": "edge_flow",
        "indices": flow_breaks,
        "status": status,
        "description": description
    }