# check_holes.py
import bmesh

def detect_holes(obj, closed_only=True):
    """
    Εντοπίζει holes ως κλειστά loops από boundary edges (edges με 1 face).
    Αν closed_only=True, επιστρέφει μόνο τα κλειστά loops (τρύπες).
    """
    if obj is None or obj.type != 'MESH':
        return {
            "name": "holes",
            "indices": [],
            "groups": [],
            "closed_groups": [],
            "status": "no_mesh",
            "description": "Δεν είναι mesh αντικείμενο"
        }

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.edges.ensure_lookup_table()

    boundary_edges = [e for e in bm.edges if len(e.link_faces) == 1]

    # adjacency: κάθε boundary edge με τις γειτονικές boundary edges που μοιράζονται κορυφή
    edge_set = set(boundary_edges)
    edge_to_neighbors = {}
    for e in boundary_edges:
        neigh = set()
        for v in e.verts:
            for ne in v.link_edges:
                if ne in edge_set and ne is not e:
                    neigh.add(ne)
        edge_to_neighbors[e] = neigh

    # συνδεδεμένα components
    visited = set()
    groups = []
    for e in boundary_edges:
        if e in visited:
            continue
        stack = [e]
        comp = []
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            comp.append(cur)
            stack.extend(edge_to_neighbors[cur] - visited)
        groups.append([ed.index for ed in comp])

    # κλειστό loop => όλες οι κορυφές του comp έχουν βαθμό 2 μέσα στο comp
    closed_groups = []
    for comp in groups:
        vdeg = {}
        for ei in comp:
            e = bm.edges[ei]
            v0, v1 = e.verts[0].index, e.verts[1].index
            vdeg[v0] = vdeg.get(v0, 0) + 1
            vdeg[v1] = vdeg.get(v1, 0) + 1
        if all(deg == 2 for deg in vdeg.values()):
            closed_groups.append(comp)

    bm.free()

    chosen = closed_groups if closed_only else groups
    status = "error" if chosen else "ok"
    description = f"Βρέθηκαν {len(chosen)} τρύπες" if chosen else "Δεν βρέθηκαν τρύπες"

    return {
        "name": "holes",
        "indices": [i for comp in chosen for i in comp],
        "groups": groups,
        "closed_groups": closed_groups,
        "status": status,
        "description": description
    }
