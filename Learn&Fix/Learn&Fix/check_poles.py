import bmesh

def detect_poles(obj, min_valence=3, max_valence=6):
    """
    Εντοπίζει poles σε mesh.
    - min_valence: vertices με valence < min_valence θεωρούνται low-valence poles
    - max_valence: vertices με valence > max_valence θεωρούνται high-valence poles
    Επιστρέφει dict με περιγραφή και λίστες indices.
    """
    if obj is None or obj.type != 'MESH':
        return {"description": "Δεν βρέθηκε mesh αντικείμενο", "indices": {"low_valence": [], "high_valence": []}}

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    low_valence = []
    high_valence = []

    for v in bm.verts:
        valence = len(v.link_edges)
        if valence < min_valence:
            low_valence.append(v.index)
        elif valence > max_valence:
            high_valence.append(v.index)

    bm.free()

    desc = f"Βρέθηκαν {len(low_valence)} low-valence poles και {len(high_valence)} high-valence poles."
    return {
        "description": desc,
        "indices": {
            "low_valence": low_valence,
            "high_valence": high_valence
        }
    }
