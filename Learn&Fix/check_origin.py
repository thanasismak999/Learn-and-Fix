import bpy
from mathutils import Vector

def detect_wrong_origin(obj):
    """
    Detects if the object's origin is significantly far from its geometry.
    It calculates the center of the bounding box and checks the distance to the origin (0,0,0 local).
    If the origin is outside the bounding box or too far, it flags it.
    """
    if obj is None or obj.type != 'MESH':
        return {
            "name": "origin",
            "indices": [],  # Object-level error, no specific vertices
            "status": "no_mesh",
            "description": "No mesh object found"
        }

    # Calculate Bounding Box center in local space
    # obj.bound_box contains 8 corners
    bbox_corners = [Vector(corner) for corner in obj.bound_box]
    bbox_center = sum(bbox_corners, Vector()) / 8.0

    # The origin in local space is always (0, 0, 0).
    # We calculate the distance from the origin to the center of geometry.
    distance_from_center = bbox_center.length

    # Calculate the max dimension (size) of the object to use as a relative threshold
    max_dimension = max((corner - bbox_center).length for corner in bbox_corners)
    
    is_bad_origin = False
    
    # Check if origin is outside the bounding box (approximate)
    min_corner = Vector(min(c[i] for c in bbox_corners) for i in range(3))
    max_corner = Vector(max(c[i] for c in bbox_corners) for i in range(3))
    
    origin = Vector((0,0,0))
    
    # Check if origin is strictly inside the bbox limits
    if not (min_corner.x <= origin.x <= max_corner.x and
            min_corner.y <= origin.y <= max_corner.y and
            min_corner.z <= origin.z <= max_corner.z):
        is_bad_origin = True

    status = "error" if is_bad_origin else "ok"
    description = (
        "Object origin is outside geometry bounds or misaligned."
        if is_bad_origin else "Object origin seems correct."
    )
    
    return {
        "name": "origin",
        "indices": [], 
        "status": status,
        "description": description
    }