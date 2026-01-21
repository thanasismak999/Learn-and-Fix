import bmesh
from mathutils import kdtree

def detect_duplicates(obj, distance=0.0001):
    """
    Detects duplicate vertices (vertices that share the exact same location).
    - distance: The maximum distance to consider two vertices as duplicates (merge threshold).
    Returns a dict with indices and a description.
    """
    if obj is None or obj.type != 'MESH':
        return {
            "name": "duplicates",
            "indices": [],
            "status": "no_mesh",
            "description": "No mesh object found"
        }

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    # Create a KDTree
    size = len(bm.verts)
    kd = kdtree.KDTree(size)
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()

    duplicates = set()

    for v in bm.verts:
        if v.index in duplicates:
            continue
        #range use
        nearby = kd.find_range(v.co, distance)
        if len(nearby) > 1:
            for item in nearby:
                idx = item[1]
                duplicates.add(idx)

    bm.free()

    duplicate_indices = list(duplicates)

    status = "error" if duplicate_indices else "ok"
    description = (
        f"Found {len(duplicate_indices)} duplicate vertices"
        if duplicate_indices else "No duplicate vertices found"
    )

    return {
        "name": "duplicates",
        "indices": duplicate_indices,
        "status": status,
        "description": description
    }