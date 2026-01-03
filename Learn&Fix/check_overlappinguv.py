import bmesh
from mathutils.geometry import intersect_tri_tri_2d
from mathutils import Vector

def detect_overlapping_uvs(obj):
    """
    Detects overlapping UV faces.
    Overlapping UVs cause texture baking errors (artifacts).
    WARNING: This check can be slow on high-poly meshes.
    """
    if obj is None or obj.type != 'MESH':
        return {
            "name": "overlapping_uv",
            "indices": [],
            "status": "no_mesh",
            "description": "No mesh object found"
        }

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    # Get the active UV layer
    uv_layer = bm.loops.layers.uv.verify()

    overlapping_faces = set()
    
    # Pre-calculate UV coordinates and bounding boxes for optimization
    face_data = []
    for f in bm.faces:
        # Get UV coords for this face
        uvs = [l[uv_layer].uv for l in f.loops]
        
        # We only handle triangles/quads for simple intersection checks
        # If it's an N-gon, we take the first 3 verts (simplification for speed)
        if len(uvs) < 3: 
            continue
            
        # Calculate Bounding Box (min_x, min_y, max_x, max_y)
        min_x = min(uv.x for uv in uvs)
        min_y = min(uv.y for uv in uvs)
        max_x = max(uv.x for uv in uvs)
        max_y = max(uv.y for uv in uvs)
        
        face_data.append({
            "index": f.index,
            "uvs": uvs, # Store Vector list
            "bbox": (min_x, min_y, max_x, max_y)
        })

    # Check for overlaps
    # Optimization: Only check if Bounding Boxes overlap first
    count = len(face_data)
    # Limit check count for performance safety in Python (optional)
    # checking all vs all is O(N^2)
    
    for i in range(count):
        f1 = face_data[i]
        for j in range(i + 1, count):
            f2 = face_data[j]
            
            # 1. Bounding Box Check (Fast)
            if (f1["bbox"][0] > f2["bbox"][2] or f1["bbox"][2] < f2["bbox"][0] or
                f1["bbox"][1] > f2["bbox"][3] or f1["bbox"][3] < f2["bbox"][1]):
                continue # No overlap possible
            
            # 2. Detailed Triangle Intersection (Slow)
            # We assume triangulation for the check (v0, v1, v2)
            if intersect_tri_tri_2d(
                f1["uvs"][0], f1["uvs"][1], f1["uvs"][2],
                f2["uvs"][0], f2["uvs"][1], f2["uvs"][2]
            ):
                overlapping_faces.add(f1["index"])
                overlapping_faces.add(f2["index"])

    bm.free()

    indices = list(overlapping_faces)
    status = "error" if indices else "ok"
    description = (
        f"Found {len(indices)} faces with overlapping UVs"
        if indices else "No UV overlaps found"
    )

    return {
        "name": "overlapping_uv",
        "indices": indices,
        "status": status,
        "description": description
    }