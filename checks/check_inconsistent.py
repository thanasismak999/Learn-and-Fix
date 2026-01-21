import bpy
import bmesh

def check_inconsistent_normals(obj):
    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
    
    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    
    inconsistent_faces = set()
    
    for edge in bm.edges:
        if len(edge.link_faces) == 2:
            face_a = edge.link_faces[0]
            face_b = edge.link_faces[1]
            
            l_a = next((l for l in face_a.loops if l.edge == edge), None)
            l_b = next((l for l in face_b.loops if l.edge == edge), None)
            
            if l_a and l_b:
                if l_a.vert == l_b.vert:
                    inconsistent_faces.add(face_a)
                    inconsistent_faces.add(face_b)

    bpy.ops.mesh.select_all(action='DESELECT')
    
    if inconsistent_faces:
        for f in inconsistent_faces:
            f.select = True
        
        bmesh.update_edit_mesh(obj.data)
        return list(inconsistent_faces)
    else:
        return []

if bpy.context.active_object:
    check_inconsistent_normals(bpy.context.active_object)
