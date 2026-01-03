import bmesh

def detect_nonmanifold(obj):
    """
    Εντοπίζει non-manifold γεωμετρία (ανοικτές ακμές, ακμές με >2 γειτονικά faces, κλπ).
    Επιστρέφει dict με indices και περιγραφή.
    """
    if obj is None or obj.type != 'MESH':
        return {
            "name": "non_manifold",
            "indices": [],
            "status": "no_mesh",
            "description": "Δεν είναι mesh αντικείμενο"
        }

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.edges.ensure_lookup_table()

    nonmanifold_edges = [e.index for e in bm.edges if not e.is_manifold]

    bm.free()

    status = "error" if nonmanifold_edges else "ok"
    description = (
        f"Βρέθηκαν {len(nonmanifold_edges)} non-manifold ακμές"
        if nonmanifold_edges else "Δεν βρέθηκαν non-manifold στοιχεία"
    )

    return {
        "name": "non_manifold",
        "indices": nonmanifold_edges,
        "status": status,
        "description": description
    }