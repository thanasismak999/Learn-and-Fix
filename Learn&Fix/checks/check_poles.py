import bpy
import bmesh
import math
from mathutils import Vector

def detect_poles(obj):
    """
    Detects N-Poles (3 edges) and Star Poles (6+ edges).
    
    INTELLIGENT FILTER:
    - Ignores poles located on 'sharp' corners (like a Cube).
    - Only flags poles on 'smooth' or 'flat' surfaces where they cause shading artifacts.
    """
    
    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
    
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    
    low_valence = []
    high_valence = []
    
    # Define "Sharpness" Threshold (in radians)
    # 0.6 radians is approx 34 degrees.
    # A Cube corner deviation is ~54 degrees (Safe).
    # A Sphere pole deviation is usually < 20 degrees (Flagged).
    SHARPNESS_THRESHOLD = 0.6 
    
    for v in bm.verts:
        if v.is_boundary:
            continue
            
        valence = len(v.link_edges)
        
        # We only care about valence 3 or >5
        if valence == 4 or valence == 5:
            continue
            
        # --- THE INTELLIGENT CHECK ---
        # Check if this vertex is a "Structural Corner"
        is_corner = False
        
        # Calculate angle between vertex normal and connected face normals
        # (Vertex normal is the average of face normals)
        if len(v.link_faces) > 0:
            for f in v.link_faces:
                # Angle in radians between the two vectors
                try:
                    diff = v.normal.angle(f.normal)
                    if diff > SHARPNESS_THRESHOLD:
                        is_corner = True
                        break # Found a sharp angle, stop checking
                except ValueError:
                    # Can happen with zero-length normals
                    continue
        
        # If it's a sharp corner (like a cube), skip it. It's valid topology.
        if is_corner:
            continue

        # --- CLASSIFY POLE ---
        if valence < 4:
            low_valence.append(v.index)
        elif valence > 5:
            high_valence.append(v.index)
            
    # Return Pass if empty
    if len(low_valence) == 0 and len(high_valence) == 0:
        return {"status": "pass"}

    return {
        "indices": {
            "low_valence": low_valence,
            "high_valence": high_valence
        },
        "description": f"Poles: {len(low_valence)} Low & {len(high_valence)} High (Smooth areas only)"
    }