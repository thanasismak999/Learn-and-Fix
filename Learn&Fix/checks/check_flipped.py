import bpy
import bmesh
from mathutils import Vector

def detect_flipped_normals(obj):
    """
    Detects faces pointing towards the object's center (Centroid Check).
    This assumes a generally convex shape.
    """
    if obj is None or obj.type != 'MESH':
        return {"name": "flipped", "indices": [], "status": "error", "description": "No mesh"}

    # Δημιουργία BMesh σε Edit Mode για να πάρει τα πιο πρόσφατα δεδομένα
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    flipped_faces = []

    # 1. Υπολογισμός Κέντρου Βάρους (Centroid)
    # Παίρνουμε τον μέσο όρο όλων των vertices
    center_of_mass = Vector((0,0,0))
    if len(bm.verts) > 0:
        for v in bm.verts:
            center_of_mass += v.co
        center_of_mass /= len(bm.verts)
    
    # 2. Έλεγχος Κατεύθυνσης (Dot Product)
    for f in bm.faces:
        face_center = f.calc_center_median()
        
        # Διάνυσμα από το πρόσωπο προς το κέντρο του αντικειμένου
        vector_to_center = (center_of_mass - face_center)
        
        # Αν το πρόσωπο είναι πολύ κοντά στο κέντρο, το αγνοούμε (αποφυγή error)
        if vector_to_center.length_squared < 0.0001:
            continue
            
        vector_to_center.normalize()
        
        # Dot Product:
        # > 0: Το Normal κοιτάει ΠΡΟΣ το κέντρο (Lattice/Inwards) -> FLIPPED
        # < 0: Το Normal κοιτάει ΜΑΚΡΙΑ από το κέντρο (Outwards) -> CORRECT
        
        # Χρησιμοποιούμε ένα μικρό threshold (0.1) για να μην πιάνουμε τα εντελώς κάθετα (90 μοίρες)
        if f.normal.dot(vector_to_center) > 0.1:
            flipped_faces.append(f.index)

    bm.free()

    status = "error" if flipped_faces else "ok"
    
    # Δημιουργία περιγραφής
    if flipped_faces:
        desc = f"Found {len(flipped_faces)} faces pointing towards center"
    else:
        desc = "All normals pointing outwards"

    return {
        "name": "flipped",
        "indices": flipped_faces,
        "status": status,
        "description": desc
    }