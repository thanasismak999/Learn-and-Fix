import bmesh
from mathutils.bvhtree import BVHTree

def detect_self_intersections(obj):
    """
    Detects self-intersecting faces (geometry that passes through itself).
    Uses a BVH Tree for efficient overlap calculation.
    Returns a dict with indices and description.
    """
    if obj is None or obj.type != 'MESH':
        return {
            "name": "self_intersect",
            "indices": [],
            "status": "no_mesh",
            "description": "No mesh object found"
        }

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    # Create a BVH Tree from the mesh geometry
    # epsilon is a small margin of error to avoid floating point issues
    tree = BVHTree.FromBMesh(bm, epsilon=0.00001)

    # Find overlapping pairs of faces within the same tree
    overlap_pairs = tree.overlap(tree)

    intersecting_faces = set()

    for i1, i2 in overlap_pairs:
        # Ignore comparing a face with itself
        if i1 == i2:
            continue
        
        f1 = bm.faces[i1]
        f2 = bm.faces[i2]

        # Filter out neighbors: Faces that share vertices naturally "touch"
        # We only want faces that intersect but are NOT connected neighbors.
        # Check if they share any vertices:
        share_verts = any(v in f2.verts for v in f1.verts)
        
        if not share_verts:
            intersecting_faces.add(i1)
            intersecting_faces.add(i2)

    bm.free()

    # Convert to list
    indices = list(intersecting_faces)

    status = "error" if indices else "ok"
    description = (
        f"Found {len(indices)} self-intersecting faces"
        if indices else "No self-intersections found"
    )

    return {
        "name": "self_intersect",
        "indices": indices,
        "status": status,
        "description": description
    }