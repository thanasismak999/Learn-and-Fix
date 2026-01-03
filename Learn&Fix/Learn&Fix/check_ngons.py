import bmesh

def detect_ngons(obj):
    """
    Εντοπίζει N-gons (faces με > 4 edges).
    Επιστρέφει dict με indices και περιγραφή.
    """
    if obj is None or obj.type != 'MESH':
        return {
            "name": "ngons",
            "indices": [],
            "status": "no_mesh",
            "description": "Δεν είναι mesh αντικείμενο"
        }

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    ngons = [f.index for f in bm.faces if len(f.verts) > 4]

    bm.free()

    status = "error" if ngons else "ok"
    description = f"Βρέθηκαν {len(ngons)} N-gons" if ngons else "Δεν βρέθηκαν N-gons"

    return {
        "name": "ngons",
        "indices": ngons,
        "status": status,
        "description": description
    }