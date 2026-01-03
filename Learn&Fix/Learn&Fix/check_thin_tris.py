import bmesh
from mathutils import Vector
import math

def detect_thin_tris(obj, aspect_threshold=10.0, angle_threshold=10.0):
    """
    Εντοπίζει long thin triangles σε mesh.
    - aspect_threshold: max αναλογία πλευράς/ύψους που θεωρείται αποδεκτή
    - angle_threshold: ελάχιστη γωνία (σε μοίρες) που θεωρείται αποδεκτή
    """
    if obj is None or obj.type != 'MESH':
        return {
            "name": "thin_tris",
            "indices": [],
            "status": "no_mesh",
            "description": "Δεν είναι mesh αντικείμενο"
        }

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    bad_faces = []

    for f in bm.faces:
        if len(f.verts) != 3:
            continue

        # υπολόγισε μήκη πλευρών
        verts = [v.co for v in f.verts]
        l = [ (verts[i] - verts[(i+1)%3]).length for i in range(3) ]
        l_max = max(l)

        # εμβαδόν τριγώνου
        area = ((verts[1] - verts[0]).cross(verts[2] - verts[0])).length / 2.0
        if area < 1e-8:  # σχεδόν degenerate
            bad_faces.append(f.index)
            continue

        # aspect ratio: max edge / (2*area/avg_height) -> εναλλακτικός τύπος
        aspect = (l_max * l_max) / (4.0 * math.sqrt(3) * area)

        # υπολόγισε τις γωνίες
        angles = []
        for i in range(3):
            a = verts[i] - verts[(i+1)%3]
            b = verts[i] - verts[(i+2)%3]
            ang = math.degrees(a.angle(b))
            angles.append(ang)
        min_angle = min(angles)

        if aspect > aspect_threshold or min_angle < angle_threshold:
            bad_faces.append(f.index)

    bm.free()

    status = "error" if bad_faces else "ok"
    description = (
        f"Βρέθηκαν {len(bad_faces)} long thin triangles"
        if bad_faces else "Δεν βρέθηκαν long thin triangles"
    )

    return {
        "name": "thin_tris",
        "indices": bad_faces,
        "status": status,
        "description": description
    }
