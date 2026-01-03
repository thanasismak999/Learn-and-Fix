import bpy

def detect_unapplied_transforms(obj):
    """
    Εντοπίζει αν το αντικείμενο έχει unapplied scale ή rotation.
    Επιστρέφει dict με περιγραφή και indices (για συμβατότητα).
    """
    if obj is None or obj.type != 'MESH':
        return {"description": "Δεν βρέθηκε mesh αντικείμενο", "indices": []}

    unapplied = []

    # Έλεγχος scale
    if obj.scale[0] != 1.0 or obj.scale[1] != 1.0 or obj.scale[2] != 1.0:
        unapplied.append("scale")

    # Έλεγχος rotation
    if any(abs(r) > 1e-4 for r in obj.rotation_euler):
        unapplied.append("rotation")

    if not unapplied:
        desc = "Όλα τα transforms είναι applied."
    else:
        desc = "Unapplied " + " & ".join(unapplied) + " – προτείνεται Ctrl+A → Apply Transforms."

    return {
        "description": desc,
        "indices": []  # Δεν έχει indices, είναι object-level check
    }