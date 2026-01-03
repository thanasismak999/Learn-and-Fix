import bmesh

def detect_isolated_vertices(obj):
    """
    Εντοπίζει isolated (ορφανές) κορυφές.
    Επιστρέφει dict με περιγραφή και λίστα indices.
    """
    if obj is None or obj.type != 'MESH':
        return {
            "name": "isolated",
            "indices": [],
            "status": "no_mesh",
            "description": "Δεν είναι mesh αντικείμενο"
        }

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    isolated = [v.index for v in bm.verts if not v.link_edges and not v.link_faces]

    bm.free()

    status = "error" if isolated else "ok"
    description = (
        f"Βρέθηκαν {len(isolated)} isolated vertices"
        if isolated else "Δεν βρέθηκαν isolated vertices"
    )

    return {
        "name": "isolated",
        "indices": isolated,
        "status": status,
        "description": description
    }
