bl_info = {
    "name": "Learn&Fix",
    "author": "Athanasios Makridis",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Learn&Fix",
    "description": "Learn and fix common mesh mistakes — an interactive topology assistant.",
    "category": "3D View",
}

import bpy
import bmesh
import math
import json
from mathutils import Vector, Euler

# --- imports detection modules ---
from .check_poles import detect_poles
from .check_flipped import detect_flipped_normals
from .check_ngons import detect_ngons
from .check_nonmanifold import detect_nonmanifold
from .check_transforms import detect_unapplied_transforms
from .check_holes import detect_holes
from .check_thin_tris import detect_thin_tris
from .check_isolated import detect_isolated_vertices
import os
import bpy.utils.previews

preview_collections = {}

def load_preview_icons():
    global preview_collections
    pcoll = bpy.utils.previews.new()

    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    logo_path = os.path.join(icons_dir, "learnfix_logo.png")

    if os.path.exists(logo_path):
        pcoll.load("learnfix_logo", logo_path, 'IMAGE')

    preview_collections["main"] = pcoll


def unload_preview_icons():
    global preview_collections
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

def get_learnfix_logo():
    """Returns the Learn&Fix logo image, loading it if necessary."""
    import os
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    image_path = os.path.join(icons_dir, "learnfix_logo.png")

    if os.path.exists(image_path):
        # Look for any already loaded image that matches path
        for img in bpy.data.images:
            if img.filepath and os.path.samefile(bpy.path.abspath(img.filepath), image_path):
                return img

        # Try loading safely
        try:
            img = bpy.data.images.load(image_path)
            return img  # no rename here
        except Exception as e:
            print("⚠️ Error loading logo:", e)
            return None
    else:
        print("❌ Logo file not found at:", image_path)
        return None


# =========================================================
# Property Groups
# =========================================================

class MeshCheckerIndexItem(bpy.types.PropertyGroup):
    value: bpy.props.IntProperty()


class MeshCheckerResultItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    issue_type: bpy.props.StringProperty()


def _update_issue_type(self, context):
    # Όταν αλλάζει κατηγορία, ξεκινάμε από την αρχή και αδειάζουμε τη λίστα
    self.current_index = 0
    self.current_indices.clear()
    self.hole_groups_json = "{}"
    self.progress_value = 0.0


class MeshCheckerProperties(bpy.types.PropertyGroup):
    # Toggle sections
    show_topology: bpy.props.BoolProperty(default=True)
    show_geometry: bpy.props.BoolProperty(default=False)
    show_normals: bpy.props.BoolProperty(default=False)
    show_workflow: bpy.props.BoolProperty(default=False)

    # Results dropdown toggle
    show_results: bpy.props.BoolProperty(name="Results", default=True)

    # --- Topology ---
    check_ngons: bpy.props.BoolProperty(name="N-Gons", default=True)
    check_thin_tris: bpy.props.BoolProperty(name="Long Thin Triangles", default=True)
    thintris_threshold: bpy.props.FloatProperty(
        name="Thin Tri Threshold",
        default=10.0, min=1.0, max=1000.0
    )
    check_poles: bpy.props.BoolProperty(name="Poles", default=True)
    check_edgeflow: bpy.props.BoolProperty(name="Edge Flow Breaks", default=False)
    check_isolated: bpy.props.BoolProperty(name="Isolated Vertices", default=True)

    # --- Geometry ---
    check_duplicates: bpy.props.BoolProperty(name="Duplicate Vertices", default=False)
    check_nonmanifold: bpy.props.BoolProperty(name="Non-Manifold", default=True)
    check_selfintersect: bpy.props.BoolProperty(name="Self Intersections", default=False)
    check_holes: bpy.props.BoolProperty(name="Holes", default=True)
    check_internalfaces: bpy.props.BoolProperty(name="Internal Faces", default=False)

    # --- Normals / Shading ---
    check_flipped: bpy.props.BoolProperty(name="Flipped Normals", default=True)
    check_inconsistent: bpy.props.BoolProperty(name="Inconsistent Orientation", default=False)
    check_overlappinguv: bpy.props.BoolProperty(name="Overlapping UV", default=False)

    # --- Workflow ---
    check_transforms: bpy.props.BoolProperty(name="Unapplied Transforms", default=True)
    check_origin: bpy.props.BoolProperty(name="Wrong Origin Placement", default=False)

    # Αποτελέσματα
    results: bpy.props.CollectionProperty(type=MeshCheckerResultItem)

    # Τύπος προβλήματος για visualization
    issue_type: bpy.props.EnumProperty(
        name="Είδος Προβλήματος",
        description="Διάλεξε ποιο πρόβλημα θέλεις να εικονοποιήσεις",
        items=[
            ('FLIPPED', "Flipped Normals", ""),
            ('POLES', "Poles", ""),
            ('NGONS', "N-Gons", ""),
            ('NONMANIFOLD', "Non-Manifold", ""),
            ('HOLES', "Holes", ""),
            ('THINTRIS', "Thin Triangles", ""),
            ('ISOLATED', "Isolated Vertices", ""),
        ],
        default='FLIPPED',
        update=_update_issue_type
    )

    # Τρέχων δείκτης/λίστα indices για την επιλεγμένη κατηγορία
    current_index: bpy.props.IntProperty(default=0)
    current_indices: bpy.props.CollectionProperty(type=MeshCheckerIndexItem)

    hole_groups_json: bpy.props.StringProperty(default="{}")

    # progress value (0..1)
    progress_value: bpy.props.FloatProperty(default=0.0)


# =========================================================
# Highlight / View helpers
# =========================================================

def highlight_faces(obj, face_indices):
    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        f.select = False
    for idx in face_indices:
        if 0 <= idx < len(bm.faces):
            bm.faces[idx].select = True
    bmesh.update_edit_mesh(obj.data, loop_triangles=True)


def highlight_vertices(obj, vert_indices):
    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        v.select = False
    for idx in vert_indices:
        if 0 <= idx < len(bm.verts):
            bm.verts[idx].select = True
    bmesh.update_edit_mesh(obj.data, loop_triangles=True)


def highlight_edges(obj, edge_indices):
    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    bm.edges.ensure_lookup_table()
    for e in bm.edges:
        e.select = False
    for idx in edge_indices:
        if 0 <= idx < len(bm.edges):
            bm.edges[idx].select = True
    bmesh.update_edit_mesh(obj.data, loop_triangles=True)


def smooth_view_to(context, target_center, target_distance=3.5, target_rotation=None, duration=1.0, steps=30):
    """Ομαλή κίνηση/zoom/περιστροφή του 3D View προς το target, στο ίδιο area με το Panel."""
    if target_rotation is None:
        target_rotation = Euler((math.radians(70), 0, math.radians(25)), 'XYZ').to_quaternion()

    # Βρες το 3D view της τρέχουσας περιοχής (ώστε να μη ζουμάρει σε άλλο monitor)
    area = context.area
    region_3d = None
    if area and area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                region_3d = space.region_3d
                break
    if region_3d is None:
        # fallback: σκάναρε οθόνες
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        region_3d = space.region_3d
                        break
                if region_3d:
                    break
    if region_3d is None:
        return

    start_loc = region_3d.view_location.copy()
    start_dist = region_3d.view_distance
    start_rot = region_3d.view_rotation.copy()

    step_data = {"i": 0}
    step_time = duration / steps

    def _tick():
        t = step_data["i"] / steps
        region_3d.view_location = start_loc.lerp(target_center, t)
        region_3d.view_distance = start_dist + (target_distance - start_dist) * t
        region_3d.view_rotation = start_rot.slerp(target_rotation, t)
        step_data["i"] += 1
        if step_data["i"] > steps:
            return None
        return step_time

    bpy.app.timers.register(_tick)


# =========================================================
# Core visualization logic
# =========================================================

def ensure_indices_for_issue(obj, props):
    """Χτίζει ΜΟΝΟ όταν είναι άδεια η τρέχουσα λίστα indices για το επιλεγμένο issue."""
    issue = props.issue_type

    # Αν έχουμε ήδη λίστα για το τρέχον issue, μην την ξαναχτίζεις
    if len(props.current_indices) > 0:
        return

    if issue == 'FLIPPED':
        data = detect_flipped_normals(obj)
        for i in data.get("indices", []):
            it = props.current_indices.add()
            it.value = i

    elif issue == 'POLES':
        data = detect_poles(obj, min_valence=3, max_valence=6)
        pole_verts = (data["indices"].get("low_valence", []) +
                      data["indices"].get("high_valence", []))
        for i in pole_verts:
            it = props.current_indices.add()
            it.value = i

    elif issue == 'NGONS':
        data = detect_ngons(obj)
        for i in data.get("indices", []):
            it = props.current_indices.add()
            it.value = i

    elif issue == 'NONMANIFOLD':
        data = detect_nonmanifold(obj)
        for i in data.get("indices", []):
            it = props.current_indices.add()
            it.value = i

    elif issue == 'HOLES':
        data = detect_holes(obj, closed_only=True)
        groups = data.get("closed_groups") or data.get("groups") or []

        mapping = {}
        for comp in groups:
            if not comp:
                continue
            rep = comp[0]  # representative edge index
            it = props.current_indices.add()
            it.value = rep
            mapping[str(rep)] = comp  # ολόκληρο το loop

        props.hole_groups_json = json.dumps(mapping)

    elif issue == 'THINTRIS':
        data = detect_thin_tris(obj, aspect_threshold=props.thintris_threshold)
        for i in data.get("indices", []):
            it = props.current_indices.add()
            it.value = i

    elif issue == 'ISOLATED':
        data = detect_isolated_vertices(obj)
        for i in data.get("indices", []):
            it = props.current_indices.add()
            it.value = i

    # πρώτη φορά που γεμίσαμε -> ξεκίνα από 0
    props.current_index = 0


def visualize_current(context):
    """Κάνει highlight το τρέχον στοιχείο και μετακινεί ομαλά το view εκεί."""
    obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return

    props = context.scene.mesh_checker_props
    ensure_indices_for_issue(obj, props)

    count = len(props.current_indices)
    if count == 0:
        props.progress_value = 0.0
        return

    # Clamp τρέχον δείκτη
    if props.current_index < 0:
        props.current_index = 0
    if props.current_index > count - 1:
        props.current_index = count - 1

    idx = props.current_indices[props.current_index].value

    # Καθάρισε επιλογές
    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    for f in bm.faces: f.select = False
    for e in bm.edges: e.select = False
    for v in bm.verts: v.select = False
    bmesh.update_edit_mesh(obj.data, loop_triangles=True)

    selected_positions = []
    issue = props.issue_type

    if issue == 'FLIPPED':
        highlight_faces(obj, [idx])
        bm.faces.ensure_lookup_table()
        if 0 <= idx < len(bm.faces):
            selected_positions = [obj.matrix_world @ bm.faces[idx].calc_center_median()]

    elif issue == 'POLES':
        highlight_vertices(obj, [idx])
        bm.verts.ensure_lookup_table()
        if 0 <= idx < len(bm.verts):
            v = bm.verts[idx]
            selected_positions = [obj.matrix_world @ v.co]

    elif issue == 'NGONS' or issue == 'THINTRIS':
        highlight_faces(obj, [idx])
        bm.faces.ensure_lookup_table()
        if 0 <= idx < len(bm.faces):
            selected_positions = [obj.matrix_world @ bm.faces[idx].calc_center_median()]

    elif issue == 'ISOLATED':
        highlight_vertices(obj, [idx])
        bm.verts.ensure_lookup_table()
        if 0 <= idx < len(bm.verts):
            v = bm.verts[idx]
            selected_positions = [obj.matrix_world @ v.co]

    elif issue == 'NONMANIFOLD':
        highlight_edges(obj, [idx])
        bm.edges.ensure_lookup_table()
        if 0 <= idx < len(bm.edges):
            e = bm.edges[idx]
            edge_center = (e.verts[0].co + e.verts[1].co) / 2.0
            selected_positions = [obj.matrix_world @ edge_center]

    elif issue == 'HOLES':
        rep_idx = idx
        try:
            mapping = json.loads(props.hole_groups_json or "{}")
        except Exception:
            mapping = {}
        loop_edges = mapping.get(str(rep_idx), [rep_idx])

        highlight_edges(obj, loop_edges)

        bm.edges.ensure_lookup_table()
        centers = []
        for ei in loop_edges:
            if 0 <= ei < len(bm.edges):
                e = bm.edges[ei]
                edge_center = (e.verts[0].co + e.verts[1].co) / 2.0
                centers.append(obj.matrix_world @ edge_center)
        if centers:
            center = sum(centers, Vector()) / len(centers)
            selected_positions = [center]

    # Smooth view
    if selected_positions:
        center = sum(selected_positions, Vector()) / len(selected_positions)
        smooth_view_to(context, center, target_distance=3.5)

    # update progress (0..1)
    if count > 0:
        props.progress_value = (props.current_index + 1) / count
    else:
        props.progress_value = 0.0


# =========================================================
# Sync helper (για μελλοντική χρήση αν χρειαστεί)
# =========================================================

def sync_issue_type_with_results(props):
    """Συγχρονίζει το issue_type με το τρέχον επιλεγμένο αποτέλεσμα (αν χρειαστεί)."""
    if 0 <= props.current_index < len(props.results):
        item = props.results[props.current_index]
        if hasattr(item, "issue_type") and item.issue_type:
            props.issue_type = item.issue_type


# =========================================================
# Operators
# =========================================================

class MESH_OT_RunChecks(bpy.types.Operator):
    bl_idname = "mesh.run_checks"
    bl_label = "Let's check your mesh"

    def execute(self, context):
        obj = context.active_object
        props = context.scene.mesh_checker_props

        if obj is None or obj.type != 'MESH':
            props.results.clear()
            item = props.results.add()
            item.name = "A mesh object was not detected."
            item.issue_type = ""
            return {'CANCELLED'}

        # Καθάρισε παλιά αποτελέσματα
        props.results.clear()

        # --- Σημαντικό: refresh + σωστή ακολουθία modes ---
        prev_mode = obj.mode
        try:
            # 1) Πήγαινε OBJECT για να “ψηθούν” modifiers/geometry και να γίνει depsgraph update
            if obj.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            # Αναγκαστικό update (μερικές φορές χρειάζεται σε 4.0/4.4)
            try:
                obj.data.update()
            except Exception:
                pass
            context.view_layer.update()

            # 2) Πήγαινε EDIT για τα detectors που βασίζονται σε bmesh.from_edit_mesh
            bpy.ops.object.mode_set(mode='EDIT')

            # --- Topology ---
            if props.check_ngons:
                d = detect_ngons(obj)
                if d.get("indices"):
                    item = props.results.add()
                    item.name = d["description"]
                    item.issue_type = "NGONS"

            if props.check_thin_tris:
                d = detect_thin_tris(obj, aspect_threshold=props.thintris_threshold)
                if d.get("indices"):
                    item = props.results.add()
                    item.name = d["description"]
                    item.issue_type = "THINTRIS"

            if props.check_poles:
                d = detect_poles(obj, min_valence=3, max_valence=6)
                if d.get("indices", {}).get("low_valence") or d.get("indices", {}).get("high_valence"):
                    item = props.results.add()
                    item.name = d["description"]
                    item.issue_type = "POLES"

            if props.check_edgeflow:
                # TODO: edgeflow detection
                pass

            if props.check_isolated:
                d = detect_isolated_vertices(obj)
                if d.get("indices"):
                    item = props.results.add()
                    item.name = d["description"]
                    item.issue_type = "ISOLATED"

            # --- Geometry ---
            if props.check_duplicates:
                # TODO
                pass

            if props.check_nonmanifold:
                d = detect_nonmanifold(obj)
                if d.get("indices"):
                    item = props.results.add()
                    item.name = d["description"]
                    item.issue_type = "NONMANIFOLD"

            if props.check_selfintersect:
                # TODO
                pass

            if props.check_holes:
                # προτιμάμε groups/closed_groups
                d = detect_holes(obj, closed_only=True)
                if d.get("closed_groups") or d.get("groups"):
                    item = props.results.add()
                    item.name = d["description"]
                    item.issue_type = "HOLES"

            if props.check_internalfaces:
                # TODO
                pass

            # --- Normals / Shading ---
            if props.check_flipped:
                d = detect_flipped_normals(obj)
                if d.get("indices"):
                    item = props.results.add()
                    item.name = d["description"]
                    item.issue_type = "FLIPPED"

            if props.check_inconsistent:
                # TODO
                pass

            if props.check_overlappinguv:
                # TODO
                pass

            # --- Workflow ---
            if props.check_transforms:
                # Σημείωση: αν ο δικός σου έλεγχος για transforms δουλεύει καλύτερα σε OBJECT,
                # μπορείς να κάνεις ένα προσωρινό flip σε OBJECT εδώ μόνο γι’ αυτόν.
                d = detect_unapplied_transforms(obj)
                if d.get("has_issue"):
                    item = props.results.add()
                    item.name = d["description"]
                    item.issue_type = "TRANSFORMS"

            if props.check_origin:
                # TODO
                pass

        finally:
            # Γύρνα στο αρχικό mode
            if obj.mode != prev_mode:
                try:
                    bpy.ops.object.mode_set(mode=prev_mode)
                except Exception:
                    pass

        # Reset navigation cache
        props.current_indices.clear()
        props.current_index = 0
        props.hole_groups_json = "{}"
        props.progress_value = 0.0

        return {'FINISHED'}


class MESH_OT_ShowVisualization(bpy.types.Operator):
    bl_idname = "mesh.show_visualization"
    bl_label = "Let me see"

    def execute(self, context):
        visualize_current(context)
        return {'FINISHED'}


class MESH_OT_PreviousIssue(bpy.types.Operator):
    bl_idname = "mesh.previous_issue"
    bl_label = "Previous"

    def execute(self, context):
        props = context.scene.mesh_checker_props
        if props.current_index > 0:
            props.current_index -= 1
            visualize_current(context)
        return {'FINISHED'}


class MESH_OT_NextIssue(bpy.types.Operator):
    bl_idname = "mesh.next_issue"
    bl_label = "Next"

    def execute(self, context):
        props = context.scene.mesh_checker_props
        if props.current_index < len(props.current_indices) - 1:
            props.current_index += 1
            visualize_current(context)
        return {'FINISHED'}


class MESH_OT_JumpToIssue(bpy.types.Operator):
    bl_idname = "mesh.jump_to_issue"
    bl_label = "Jump to Issue"

    issue_index: bpy.props.IntProperty()

    def execute(self, context):
        props = context.scene.mesh_checker_props

        # Προστασία
        if self.issue_index < 0 or self.issue_index >= len(props.results):
            return {'CANCELLED'}

        # Άλλαξε τύπο προβλήματος σύμφωνα με το result
        result_item = props.results[self.issue_index]
        if result_item.issue_type:
            props.issue_type = result_item.issue_type

        # Reset τρέχοντα indices για το νέο issue
        props.current_indices.clear()
        props.current_index = 0

        obj = context.active_object
        if obj and obj.type == 'MESH':
            ensure_indices_for_issue(obj, props)
            visualize_current(context)

        return {'FINISHED'}


class MESH_OT_WhyItMatters(bpy.types.Operator):
    bl_idname = "mesh.why_it_matters"
    bl_label = "Why it matters?"

    def execute(self, context):
        props = context.scene.mesh_checker_props
        issue = props.issue_type

        explanations = {
            'FLIPPED': "Flipped normals cause shading artifacts, incorrect lighting and can break baking.",
            'POLES': "High-valence poles (>5 edges) create pinching and artifacts during subdivision or deformation.",
            'NGONS': "N-Gons (>4 edges) deform unpredictably and break subdivision flow.",
            'NONMANIFOLD': "Non-manifold edges create invalid geometry, bad for 3D printing and boolean ops.",
            'HOLES': "Holes in the mesh cause rendering issues, physics problems and bad subdivision.",
            'THINTRIS': "Long thin triangles produce bad shading, poor UV unwrapping and deformation artifacts.",
            'ISOLATED': "Isolated vertices are unused geometry data and should be cleaned for performance.",
            'TRANSFORMS': "Unapplied transforms lead to inconsistent scale/rotation and break modifiers/export.",
            'ORIGIN': "Wrong object origin placement makes transforms, modifiers and animation unreliable.",
        }

        msg = explanations.get(issue, "No explanation available for this issue.")

        def draw_popup(self, context):
            self.layout.label(text=msg, icon="INFO")

        bpy.context.window_manager.popup_menu(draw_popup, title="Why it matters?", icon='QUESTION')
        return {'FINISHED'}


class MESH_OT_HowToFix(bpy.types.Operator):
    bl_idname = "mesh.how_to_fix"
    bl_label = "How to fix"

    def execute(self, context):
        props = context.scene.mesh_checker_props
        issue = props.issue_type

        fixes = {
            'FLIPPED': "Edit Mode → Select All → Shift+N (recalculate). Ή Flip χειροκίνητα ανά face.",
            'POLES': "Redirect edge flow, dissolve περιττές edges, προτίμησε quads όπου γίνεται.",
            'NGONS': "Knife (K) ή dissolve/insert edges ώστε τα N-gons να γίνουν quads/tris.",
            'NONMANIFOLD': "Select → Select All by Trait → Non-Manifold και καθάρισμα με Merge/Fill.",
            'HOLES': "Επέλεξε border edges → F για Fill ή Grid Fill για καλύτερο topology.",
            'THINTRIS': "Ξαναχάραξε edge flow, πρόσθεσε supporting geo ή κάνε retopo των λεπτών tris.",
            'ISOLATED': "Select → Select All by Trait → Loose Geometry και Delete.",
            'TRANSFORMS': "Ctrl+A → Apply Scale/Rotation πριν από modifiers/export.",
            'ORIGIN': "Object → Set Origin → Origin to Geometry/3D Cursor ανάλογα με την ανάγκη.",
        }

        msg = fixes.get(issue, "No fix instructions available for this issue.")

        def draw_popup(self, context):
            self.layout.label(text=msg, icon="INFO")

        bpy.context.window_manager.popup_menu(draw_popup, title="How to fix", icon='GREASEPENCIL')
        return {'FINISHED'}


# =========================================================
# Panel
# =========================================================

class MESH_PT_CheckerPanel(bpy.types.Panel):
    bl_label = "Mesh Checker"
    bl_idname = "MESH_PT_checker"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Learn&Fix"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mesh_checker_props
        # --- Topology ---
        box = layout.box()
        row = box.row()
        row.prop(props, "show_topology",
                 icon="TRIA_DOWN" if props.show_topology else "TRIA_RIGHT",
                 emboss=False)
        row.label(text="Topology (5)")
        if props.show_topology:
            col = box.column(align=True)
            col.prop(props, "check_ngons", text="N-gons (>4 edges)")
            r = col.row(align=True)
            r.prop(props, "check_thin_tris", text="Long thin triangles")
            r.prop(props, "thintris_threshold", text="")
            col.prop(props, "check_poles", text="Poles >5 edges")
            col.prop(props, "check_edgeflow", text="Edge flow breaks")
            col.prop(props, "check_isolated", text="Isolated vertices")

        # --- Geometry ---
        box = layout.box()
        row = box.row()
        row.prop(props, "show_geometry",
                 icon="TRIA_DOWN" if props.show_geometry else "TRIA_RIGHT",
                 emboss=False)
        row.label(text="Geometry (5)")
        if props.show_geometry:
            col = box.column(align=True)
            col.prop(props, "check_duplicates", text="Duplicate vertices")
            col.prop(props, "check_nonmanifold", text="Non-manifold edges")
            col.prop(props, "check_selfintersect", text="Self-intersections")
            col.prop(props, "check_holes", text="Holes in mesh")
            col.prop(props, "check_internalfaces", text="Internal faces")

        # --- Normals / Shading ---
        box = layout.box()
        row = box.row()
        row.prop(props, "show_normals",
                 icon="TRIA_DOWN" if props.show_normals else "TRIA_RIGHT",
                 emboss=False)
        row.label(text="Normals / Shading (3)")
        if props.show_normals:
            col = box.column(align=True)
            col.prop(props, "check_flipped", text="Flipped normals")
            col.prop(props, "check_inconsistent", text="Inconsistent face orientation")
            col.prop(props, "check_overlappinguv", text="Overlapping UV islands")

        # --- Workflow ---
        box = layout.box()
        row = box.row()
        row.prop(props, "show_workflow",
                 icon="TRIA_DOWN" if props.show_workflow else "TRIA_RIGHT",
                 emboss=False)
        row.label(text="Workflow (2)")
        if props.show_workflow:
            col = box.column(align=True)
            col.prop(props, "check_transforms", text="Unapplied transforms")
            col.prop(props, "check_origin", text="Wrong object origin placement")

        # --- Run checks ---
        layout.operator("mesh.run_checks", text="Let's check your mesh", icon="MESH_DATA")

        # --- Results dropdown (only if findings exist) ---
        if len(props.results) > 0:
            layout.separator()
            box = layout.box()
            row = box.row()
            row.prop(
                props, "show_results",
                text=f"Results ({len(props.results)}) - Click to select error",
                icon="TRIA_DOWN" if props.show_results else "TRIA_RIGHT",
                emboss=False
            )
            if props.show_results:
                col = box.column(align=True)
                for i, r in enumerate(props.results):
                    op_row = col.row(align=True)
                    op_row.alignment = 'LEFT'  # left-aligned
                    op = op_row.operator("mesh.jump_to_issue", text=r.name, icon="DOT", emboss=False)
                    if op is not None:
                        op.issue_index = i

        # --- Progress (bar + %) ---
        count = len(props.current_indices)
        if count > 0:
            progress = (props.current_index + 1) / count
            row = layout.row()
            split = row.split(factor=0.30)
            split.label(text=f"Progress: {props.current_index+1}/{count}")

            split2 = split.split(factor=0.75)
            bar_len = 25
            filled = int(progress * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            split2.label(text=bar)

            right = split2.row()
            right.alignment = 'RIGHT'
            right.label(text=f"{int(progress * 100)}%")

        # --- Nav + info buttons ---
        layout.separator()
        row = layout.row(align=True)
        sub = row.row(align=True); sub.enabled = props.current_index > 0 and count > 0
        sub.operator("mesh.previous_issue", text="Previous")
        sub = row.row(align=True); sub.enabled = True
        sub.operator("mesh.show_visualization", text="Let me see")
        sub = row.row(align=True); sub.enabled = props.current_index < count - 1
        sub.operator("mesh.next_issue", text="Next")

        layout.separator()
        row = layout.row(align=True)
        row.operator("mesh.why_it_matters", text="Why it matters?", icon="QUESTION")
        row.operator("mesh.how_to_fix", text="How to fix", icon="MODIFIER")
        layout.separator()
        img = get_learnfix_logo()
        # --- Logo footer ---
        # --- Learn&Fix Footer (dark background, scale 1) ---
        layout.separator()
        if "main" in preview_collections:
            pcoll = preview_collections["main"]
            if "learnfix_logo" in pcoll:
                box = layout.box()
                row = box.row()
                row.alignment = 'CENTER'
                row.scale_y = 0.9
                row.template_icon(icon_value=pcoll["learnfix_logo"].icon_id, scale=2.0)


# =========================================================
# Register
# =========================================================

classes = (
    MeshCheckerIndexItem,
    MeshCheckerResultItem,
    MeshCheckerProperties,
    MESH_OT_RunChecks,
    MESH_OT_ShowVisualization,
    MESH_OT_PreviousIssue,
    MESH_OT_NextIssue,
    MESH_OT_JumpToIssue,
    MESH_OT_WhyItMatters,
    MESH_OT_HowToFix,
    MESH_PT_CheckerPanel,
)
def load_previews():
    """Load preview icons (like the Learn&Fix logo)."""
    global preview_collections
    pcoll = bpy.utils.previews.new()

    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    logo_path = os.path.join(icons_dir, "learnfix_logo.png")

    if os.path.exists(logo_path):
        try:
            pcoll.load("learnfix_logo", logo_path, 'IMAGE')
            print(f"✅ Learn&Fix logo loaded from: {logo_path}")
        except Exception as e:
            print(f"⚠️ Could not load logo: {e}")
    else:
        print(f"⚠️ Logo not found at: {logo_path}")

    preview_collections["main"] = pcoll


def unload_previews():
    """Clean up preview icons when addon is disabled."""
    global preview_collections
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
    print("🧹 Learn&Fix previews unloaded.")


# =========================================================
# Register / Unregister
# =========================================================

def register():
    load_previews()
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mesh_checker_props = bpy.props.PointerProperty(type=MeshCheckerProperties)
    print("✅ Learn&Fix registered successfully.")


def unregister():
    unload_previews()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.mesh_checker_props
    print("❌ Learn&Fix unregistered.")


if __name__ == "__main__":
    register()