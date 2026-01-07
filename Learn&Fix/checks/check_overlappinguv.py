import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def detect_overlapping_uvs(obj):
    if obj is None or obj.type != 'MESH':
        return {"name": "overlapping_uv", "indices": [], "status": "error", "description": "No mesh"}

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    uv_layer = bm.loops.layers.uv.verify()

    tri_verts = []
    tri_face_map = []
    EPSILON_SHRINK = 0.0001

    for face in bm.faces:
        uvs = [l[uv_layer].uv for l in face.loops]
        if not uvs: continue

        center = Vector((0, 0))
        for uv in uvs: center += uv
        center /= len(uvs)

        shrunk_uvs = []
        for uv in uvs:
            direction = (center - uv)
            new_uv = uv + (direction * EPSILON_SHRINK)
            shrunk_uvs.append(Vector((new_uv.x, new_uv.y, 0.0)))

        for i in range(1, len(shrunk_uvs) - 1):
            v0 = shrunk_uvs[0]
            v1 = shrunk_uvs[i]
            v2 = shrunk_uvs[i+1]

            tri_verts.extend([v0, v1, v2])
            tri_face_map.append(face.index)

    if not tri_verts:
        bm.free()
        return {"name": "overlapping_uv", "indices": [], "status": "ok", "description": "No UVs found"}

    polygons = [(i, i+1, i+2) for i in range(0, len(tri_verts), 3)]

    tree = BVHTree.FromPolygons(tri_verts, polygons)

    overlap_pairs = tree.overlap(tree)

    overlapping_faces = set()

    for i1, i2 in overlap_pairs:
        face_idx_1 = tri_face_map[i1]
        face_idx_2 = tri_face_map[i2]

        if face_idx_1 == face_idx_2:
            continue

        overlapping_faces.add(face_idx_1)
        overlapping_faces.add(face_idx_2)

    bm.free()

    indices_list = list(overlapping_faces)
    status = "error" if indices_list else "ok"
    desc = f"Found {len(indices_list)} faces with overlapping UVs" if indices_list else "UV Map is clean"

    return {
        "name": "overlapping_uv",
        "indices": indices_list,
        "status": status,
        "description": desc
    }