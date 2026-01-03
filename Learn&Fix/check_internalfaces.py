import bmesh

def detect_internal_faces(obj):
    """
    Detects internal faces based on edge valence.
    Faces connected to edges that are shared by more than 2 faces are flagged.
    This typically indicates geometry inside a solid volume (partitions).
    """
    if obj is None or obj.type != 'MESH':
        return {
            "name": "internal_faces",
            "indices": [],
            "status": "no_mesh",
            "description": "No mesh object found"
        }

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    internal_faces = set()

    # Iterate over edges to find those shared by > 2 faces
    for e in bm.edges:
        if len(e.link_faces) > 2:
            # All faces connected to this "crowded" edge are potentially internal/non-manifold
            for f in e.link_faces:
                internal_faces.add(f.index)

    bm.free()

    indices = list(internal_faces)

    status = "error" if indices else "ok"
    description = (
        f"Found {len(indices)} faces connected to non-manifold edges (potential internal faces)"
        if indices else "No internal faces found"
    )

    return {
        "name": "internal_faces",
        "indices": indices,
        "status": status,
        "description": description
    }