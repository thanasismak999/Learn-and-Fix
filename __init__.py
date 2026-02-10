bl_info = {
    "name": "Learn&Fix",
    "author": "Athanasios Makridis",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Header > Learn&Fix",
    "description": "Smart educational workflow assistant.",
    "category": "3D View",
}

import bpy
import bmesh
import json
import time
import os
import sys
import subprocess
import bpy.utils.previews
from bpy.app.handlers import persistent
from mathutils import Vector

# GLOBAL VARIABLES
# =========================================================
addon_start_time = 0.0

# IMPORTS & LOGIC
# =========================================================
from .checks.check_poles import detect_poles
from .checks.check_flipped import detect_flipped_normals
from .checks.check_ngons import detect_ngons
from .checks.check_nonmanifold import detect_nonmanifold
from .checks.check_transforms import detect_unapplied_transforms
from .checks.check_holes import detect_holes
from .checks.check_thin_tris import detect_thin_tris
from .checks.check_isolated import detect_isolated_vertices
from .checks.check_duplicates import detect_duplicates
from .checks.check_selfintersect import detect_self_intersections
from .checks.check_internalfaces import detect_internal_faces
from .checks.check_origin import detect_wrong_origin
from .checks.check_inconsistent import detect_inconsistent_normals
from .checks.check_overlappinguv import detect_overlapping_uvs
from .checks.check_edgeflow import detect_edge_flow

preview_collections = {}

ISSUE_DISPLAY_NAMES = {
    'FLIPPED': "Flipped Normals", 'POLES': "Poles", 'NGONS': "N-Gons",
    'NONMANIFOLD': "Non-Manifold", 'HOLES': "Holes", 'THINTRIS': "Thin Triangles",
    'ISOLATED': "Isolated Vertices", 'DUPLICATES': "Duplicate Vertices",
    'SELFINTERSECT': "Self-Intersections", 'INTERNAL': "Internal Faces",
    'ORIGIN': "Wrong Origin", 'INCONSISTENT': "Inconsistent Normals",
    'OVERLAPPING_UV': "Overlapping UVs", 'EDGEFLOW': "Edge Flow Breaks",
    'TRANSFORMS': "Unapplied Scale"
}

IMAGE_MAPPING = {
    'FLIPPED': "FLIPPED_NORMALS.png", 'POLES': "POLES.png", 'NGONS': "NGONS.png",
    'NONMANIFOLD': "NON_MANIFOLD.png", 'HOLES': "HOLES.png", 'THINTRIS': "THIN_FACES.png",
    'ISOLATED': "ISOLATED_VERTS.png", 'DUPLICATES': "DUPLICATE_VERTS.png",
    'SELFINTERSECT': "SELF_INTERSECT.png", 'INTERNAL': "INTERNAL_FACES.png",
    'ORIGIN': "WRONG_ORIGIN.png", 'INCONSISTENT': "INCONSISTENT_NORMALS.png",
    'OVERLAPPING_UV': "OVERLAPPING_UV.png", 'EDGEFLOW': "EDGE_FLOW.png",
    'TRANSFORMS': "UNAPPLIED_SCALE.png"
}

CHECKS_MAPPING = [
    ('check_ngons', detect_ngons, 'NGONS'),
    ('check_thin_tris', detect_thin_tris, 'THINTRIS'),
    ('check_poles', detect_poles, 'POLES'),
    ('check_edgeflow', detect_edge_flow, 'EDGEFLOW'),
    ('check_isolated', detect_isolated_vertices, 'ISOLATED'),
    ('check_duplicates', detect_duplicates, 'DUPLICATES'),
    ('check_nonmanifold', detect_nonmanifold, 'NONMANIFOLD'),
    ('check_selfintersect', detect_self_intersections, 'SELFINTERSECT'),
    ('check_holes', detect_holes, 'HOLES'),
    ('check_internalfaces', detect_internal_faces, 'INTERNAL'),
    ('check_flipped', detect_flipped_normals, 'FLIPPED'),
    ('check_inconsistent', detect_inconsistent_normals, 'INCONSISTENT'),
    ('check_overlappinguv', detect_overlapping_uvs, 'OVERLAPPING_UV'),
    ('check_transforms', detect_unapplied_transforms, 'TRANSFORMS'),
    ('check_origin', detect_wrong_origin, 'ORIGIN'),
]

YOUTUBE_URLS = {
    'FLIPPED': "https://www.youtube.com/results?search_query=blender+fix+flipped+normals",
    'INCONSISTENT': "https://www.youtube.com/results?search_query=blender+recalculate+normals",
    'POLES': "https://www.youtube.com/results?search_query=blender+topology+poles+explained",
    'NGONS': "https://www.youtube.com/results?search_query=blender+why+ngons+are+bad",
    'NONMANIFOLD': "https://www.youtube.com/results?search_query=blender+fix+non+manifold",
    'HOLES': "https://www.youtube.com/results?search_query=blender+fill+holes",
    'THINTRIS': "https://www.youtube.com/results?search_query=blender+bad+topology+thin+triangles",
    'ISOLATED': "https://www.youtube.com/results?search_query=blender+clean+up+loose+geometry",
    'DUPLICATES': "https://www.youtube.com/results?search_query=blender+merge+by+distance",
    'SELFINTERSECT': "https://www.youtube.com/results?search_query=blender+fix+self+intersecting",
    'INTERNAL': "https://www.youtube.com/results?search_query=blender+remove+interior+faces",
    'OVERLAPPING_UV': "https://www.youtube.com/results?search_query=blender+uv+pack+overlapping",
    'EDGEFLOW': "https://www.youtube.com/results?search_query=blender+topology+edge+flow",
    'ORIGIN': "https://www.youtube.com/results?search_query=blender+set+origin",
    'TRANSFORMS': "https://www.youtube.com/results?search_query=blender+apply+scale"
}

def get_smart_explanation(issue, mode, count):
    """
    Returns context-aware advice based on Issue Type, Workflow Mode, and Error Count.
    """
    why = "Causes issues."
    fix = "Fix manually."
    

    if issue == 'FLIPPED':
        why = "Inside-out faces. Invisible in Game Engines." if mode == 'GAMES' else "Breaks shading and 3D printing."
        fix = "Edit Mode > Select All > Shift+N."

    elif issue == 'INCONSISTENT':
        why = "Confuses 3D printer slicers (Inside vs Outside)." if mode == 'PRINTING' else "Black shading artifacts."
        fix = "Select All > Shift+N."

    elif issue == 'POLES':
        if mode == 'ANIMATION':
            why = "Creates pinching when mesh deforms."
            fix = "Retopologize manualy (move to flat areas)."
        else:
            why = "Bad topology flow."
            fix = "Manual Retopology or Remesh Modifier."

    elif issue == 'NGONS':
        if mode == 'ANIMATION':
            why = "Unpredictable deformation during bending."
        else:
            why = "May cause concave shading errors."
        
        if count > 50:
            fix = "Mass Error: Use 'Triangulate' Modifier."
        else:
            fix = "Select Face > Ctrl+T or Knife Tool (K)."

    elif issue == 'NONMANIFOLD':
        if mode == 'PRINTING':
            why = "CRITICAL: Object is not watertight. Print will fail."
            fix = "Use 'Solidify' Modifier (Complex Mode) or Remesh."
        else:
            why = "Impossible geometry."
            fix = "Clean Up > Non-Manifold."

    elif issue == 'HOLES':
        if mode == 'PRINTING':
            why = "Resin/Filament will leak. Must be closed."
            fix = "Select Edge > F (Fill) or 'Solidify' Modifier."
        else:
            why = "Open geometry."
            fix = "Select Edge Loop > F."

    elif issue == 'THINTRIS':
        why = "Bad physics collision." if mode == 'GAMES' else "Shading artifacts."
        if count > 100:
            fix = "Mass Error: Use 'Decimate' Modifier (Collapse)."
        else:
            fix = "Slide Vertices (GG) to merge."

    elif issue == 'ISOLATED':
        why = "Increases file size unnecessarily."
        fix = "Mesh > Clean Up > Delete Loose."

    elif issue == 'DUPLICATES':
        why = "Z-Fighting flicker." if mode == 'GAMES' else "Shading errors."
        if count > 50:
            fix = "Mass Error: Use 'Weld' Modifier (Non-Destructive)."
        else:
            fix = "Press M > By Distance."

    elif issue == 'SELFINTERSECT':
        why = "Impossible to 3D Print." if mode == 'PRINTING' else "Bad physics."
        fix = "Sculpt Mode > Smooth or 'Remesh' Modifier."

    elif issue == 'INTERNAL':
        why = "Slicer will print solid walls inside." if mode == 'PRINTING' else "Wasted polygons."
        fix = "Select All by Trait > Interior Faces > Delete."

    elif issue == 'OVERLAPPING_UV':
        why = "Lightmap baking will fail." if mode == 'GAMES' else "Texture glitches."
        fix = "UV > Pack Islands."

    elif issue == 'EDGEFLOW':
        why = "Bad reflections."
        fix = "Manual Retopology."

    elif issue == 'ORIGIN':
        why = "Rotation/Scaling will be offset."
        fix = "Object > Set Origin > Origin to Geometry."

    elif issue == 'TRANSFORMS':
        why = "Modifiers (Bevel/Array) will distort."
        fix = "Ctrl+A > Apply Scale."

    return f"PROBLEM: {ISSUE_DISPLAY_NAMES.get(issue, issue)}\nWHY: {why}\nFIX: {fix}"

WORKFLOW_RULES = { 'PRINTING': { 'defaults': {'check_thin_tris': True, 'check_isolated': True} } }

def update_workflow(self, context):
    mode = self.workflow_mode
    if mode == 'SELECT' or mode == 'CUSTOM': return
    rules = WORKFLOW_RULES.get(mode)
    if rules:
        defaults = rules['defaults']
        for prop_name, value in defaults.items():
            if hasattr(self, prop_name): setattr(self, prop_name, value)

def load_preview_icons():
    global preview_collections
    pcoll = bpy.utils.previews.new()
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    if os.path.exists(os.path.join(icons_dir, "learnfix_logo.png")):
        pcoll.load("learnfix_logo", os.path.join(icons_dir, "learnfix_logo.png"), 'IMAGE')
    for key, filename in IMAGE_MAPPING.items():
        path = os.path.join(icons_dir, filename)
        if os.path.exists(path): pcoll.load(key, path, 'IMAGE')
    preview_collections["main"] = pcoll

def unload_preview_icons():
    for pcoll in preview_collections.values(): bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

def get_icon(name):
    pcoll = preview_collections.get("main")
    if pcoll and name in pcoll: return pcoll[name].icon_id
    return 0

class MeshCheckerIndexItem(bpy.types.PropertyGroup): value: bpy.props.IntProperty()
class MeshCheckerResultItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    issue_type: bpy.props.StringProperty()
    count: bpy.props.IntProperty()
    improvement: bpy.props.FloatProperty(min=0.0, max=1.0, subtype='PERCENTAGE')

def _update_issue_type(self, context):
    self.current_index = 0
    self.current_indices.clear()

class MeshCheckerProperties(bpy.types.PropertyGroup):
    workflow_mode: bpy.props.EnumProperty(name="Usage Goal", items=[('SELECT', "Select a Workflow...", ""), ('PRINTING', "3D Printing", ""), ('ANIMATION', "Animation", ""), ('GAMES', "Game Asset", ""), ('CUSTOM', "Expert", "")], default='SELECT', update=update_workflow)
    
    show_explanation: bpy.props.BoolProperty(name="Info", default=False, description="Show detailed explanation")

    auto_check_enabled: bpy.props.BoolProperty(name="Auto-Check", default=False)
    auto_check_threshold: bpy.props.IntProperty(name="Every X Moves", default=10, min=1, max=100)
    edit_operation_count: bpy.props.IntProperty(default=0)
    is_internal_operation: bpy.props.BoolProperty(default=False)
    show_topology: bpy.props.BoolProperty(default=True)
    show_geometry: bpy.props.BoolProperty(default=True)
    show_normals: bpy.props.BoolProperty(default=True)
    show_workflow: bpy.props.BoolProperty(default=True)
    show_results: bpy.props.BoolProperty(name="Results", default=True)
    check_ngons: bpy.props.BoolProperty(name="N-Gons", default=True)
    check_thin_tris: bpy.props.BoolProperty(name="Long Thin Triangles", default=True)
    thintris_threshold: bpy.props.FloatProperty(name="Threshold", default=10.0)
    check_poles: bpy.props.BoolProperty(name="Poles", default=True)
    check_edgeflow: bpy.props.BoolProperty(name="Edge Flow", default=True)
    check_isolated: bpy.props.BoolProperty(name="Isolated", default=True)
    check_duplicates: bpy.props.BoolProperty(name="Duplicates", default=True)
    check_nonmanifold: bpy.props.BoolProperty(name="Non-Manifold", default=True)
    check_selfintersect: bpy.props.BoolProperty(name="Self-Intersect", default=True)
    check_holes: bpy.props.BoolProperty(name="Holes", default=True)
    check_internalfaces: bpy.props.BoolProperty(name="Internal", default=True)
    check_flipped: bpy.props.BoolProperty(name="Flipped", default=True)
    check_inconsistent: bpy.props.BoolProperty(name="Inconsistent", default=True)
    check_overlappinguv: bpy.props.BoolProperty(name="Overlap UV", default=True)
    check_transforms: bpy.props.BoolProperty(name="Transforms", default=True)
    check_origin: bpy.props.BoolProperty(name="Origin", default=True)
    results: bpy.props.CollectionProperty(type=MeshCheckerResultItem)
    issue_type: bpy.props.EnumProperty(name="Issue Type", items=[(k, v, "") for k,v in ISSUE_DISPLAY_NAMES.items()], update=_update_issue_type)
    current_index: bpy.props.IntProperty(default=0)
    current_indices: bpy.props.CollectionProperty(type=MeshCheckerIndexItem)
    baseline_stats: bpy.props.StringProperty(default="{}")
    total_score: bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0, subtype='PERCENTAGE')

@persistent
def on_depsgraph_update(scene, depsgraph):
    props = scene.mesh_checker_props
    if props.is_internal_operation:
        props.is_internal_operation = False 
        return
    if not props.auto_check_enabled: return
    obj = bpy.context.active_object
    if not obj or obj.mode != 'EDIT': return
    for update in depsgraph.updates:
        if update.id.original == obj:
            if update.is_updated_geometry:
                props.edit_operation_count += 1
                if props.edit_operation_count >= props.auto_check_threshold:
                    props.edit_operation_count = 0
                    bpy.app.timers.register(trigger_auto_check, first_interval=0.1)
                break 

def trigger_auto_check():
    if bpy.context.active_object: bpy.ops.mesh.run_checks()
    return None

class SmoothViewController:
    def __init__(self):
        self._timer = None; self.start_time = 0; self.duration = 0.8; self.region_3d = None
    def start_animation(self, context, target_center, target_normal=None, dist=3.5):
        if self._timer: 
            try: bpy.app.timers.unregister(self._timer)
            except: pass
        area = context.area
        if area.type == 'VIEW_3D':
            for s in area.spaces: 
                if s.type == 'VIEW_3D': self.region_3d = s.region_3d; break
        if not self.region_3d: return
        self.start_loc = self.region_3d.view_location.copy()
        self.start_dist = self.region_3d.view_distance
        self.start_rot = self.region_3d.view_rotation.copy()
        self.target_loc = target_center; self.target_dist = dist
        self.target_rot = target_normal.to_track_quat('Z', 'Y') if target_normal else self.start_rot.copy()
        self.start_time = time.time()
        self._timer = self._tick
        bpy.app.timers.register(self._timer)
    def _tick(self):
        if not self.region_3d: return None
        elapsed = time.time() - self.start_time
        t = elapsed / self.duration
        if t >= 1.0:
            self.region_3d.view_location = self.target_loc; self.region_3d.view_distance = self.target_dist
            self.region_3d.view_rotation = self.target_rot; self._timer = None; return None
        prog = 1 - (1 - t) ** 3
        self.region_3d.view_location = self.start_loc.lerp(self.target_loc, prog)
        self.region_3d.view_distance = self.start_dist + (self.target_dist - self.start_dist) * prog
        self.region_3d.view_rotation = self.start_rot.slerp(self.target_rot, prog)
        return 0.01
view_controller = SmoothViewController()

def highlight_generic(obj, indices, mode_type):
    if obj.mode != 'EDIT': bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    if mode_type=='faces': bm.faces.ensure_lookup_table(); [setattr(f, 'select', i in indices) for i,f in enumerate(bm.faces)]
    elif mode_type=='verts': bm.verts.ensure_lookup_table(); [setattr(v, 'select', i in indices) for i,v in enumerate(bm.verts)]
    elif mode_type=='edges': bm.edges.ensure_lookup_table(); [setattr(e, 'select', i in indices) for i,e in enumerate(bm.edges)]
    bmesh.update_edit_mesh(obj.data)

def ensure_indices_for_issue(obj, props):
    if len(props.current_indices) > 0: return
    issue = props.issue_type; data = {}
    func = None
    for prop, f, code in CHECKS_MAPPING:
        if code == issue: func = f; break
    if func:
        d = func(obj, props.thintris_threshold) if issue=='THINTRIS' else func(obj)
        data = d
        if d.get("indices") and isinstance(d["indices"], dict):
            data = {"indices": d["indices"].get("low_valence", []) + d["indices"].get("high_valence", [])}
    if data.get("indices"): 
        for i in data["indices"]: item=props.current_indices.add(); item.value=i
    props.current_index = 0

def visualize_current(context):
    obj = context.active_object
    props = context.scene.mesh_checker_props
    ensure_indices_for_issue(obj, props)
    if not props.current_indices: return
    if props.current_index >= len(props.current_indices): props.current_index = len(props.current_indices)-1
    idx = props.current_indices[props.current_index].value
    issue = props.issue_type; mw = obj.matrix_world; rot = mw.to_3x3()
    pos = Vector((0,0,0)); norm = None
    if issue in ['POLES', 'ISOLATED', 'DUPLICATES', 'EDGEFLOW']:
        highlight_generic(obj, [idx], 'verts'); bm=bmesh.from_edit_mesh(obj.data); bm.verts.ensure_lookup_table()
        if idx<len(bm.verts): v=bm.verts[idx]; pos=mw@v.co; norm=rot@v.normal if v.normal.length_squared>0 else None
    elif issue in ['NONMANIFOLD', 'HOLES']:
        highlight_generic(obj, [idx], 'edges'); bm=bmesh.from_edit_mesh(obj.data); bm.edges.ensure_lookup_table()
        if idx<len(bm.edges): e=bm.edges[idx]; pos=mw@((e.verts[0].co+e.verts[1].co)/2); norm=Vector((0,0,1))
    else:
        highlight_generic(obj, [idx], 'faces'); bm=bmesh.from_edit_mesh(obj.data); bm.faces.ensure_lookup_table()
        if idx<len(bm.faces): f=bm.faces[idx]; pos=mw@f.calc_center_median(); norm=rot@f.normal
    view_controller.start_animation(context, pos, norm)

class MESH_OT_RunChecks(bpy.types.Operator):
    bl_idname = "mesh.run_checks"; bl_label = "Check Mesh"
    def execute(self, context):
        obj = context.active_object; props = context.scene.mesh_checker_props; props.results.clear()
        if not obj or obj.type!='MESH': return {'CANCELLED'}
        props.is_internal_operation = True 
        if obj.mode == 'EDIT': bmesh.update_edit_mesh(obj.data)
        try: base=json.loads(props.baseline_stats)
        except: base={}
        curr=0; base_tot=0; first=None
        for prop, func, code in CHECKS_MAPPING:
            if getattr(props, prop):
                d = func(obj, props.thintris_threshold) if code=='THINTRIS' else func(obj)
                cnt=0; has=False
                if d.get("indices"): 
                    cnt = len(d["indices"].get("low_valence",[])+d["indices"].get("high_valence",[])) if isinstance(d["indices"],dict) else len(d["indices"]); has=True
                elif d.get("status")=="error": cnt=1; has=True
                if has:
                    it=props.results.add(); it.name=d["description"]; it.issue_type=code; it.count=cnt
                    if not first: first=code
                    if code not in base: base[code]=cnt
                    if base[code]>0: it.improvement=max(0.0, 1.0-(cnt/base[code]))
                    curr+=cnt; base_tot+=base[code]
                elif code in base: base_tot+=base[code]
        if first: props.issue_type=first
        if curr==0: props.baseline_stats="{}"; props.total_score=1.0
        else: props.baseline_stats=json.dumps(base); props.total_score=max(0.0,1.0-(curr/base_tot)) if base_tot>0 else 0.0
        props.current_indices.clear(); props.current_index=0
        return {'FINISHED'}

class MESH_OT_RefreshActive(bpy.types.Operator):
    bl_idname = "mesh.refresh_active"; bl_label = "Refresh Active"
    def execute(self, context):
        obj = context.active_object; props = context.scene.mesh_checker_props
        active_type = props.issue_type
        props.is_internal_operation = True
        if obj.mode == 'EDIT': bmesh.update_edit_mesh(obj.data)
        func = None
        for p, f, c in CHECKS_MAPPING:
            if c == active_type: func = f; break
        if func:
            d = func(obj, props.thintris_threshold) if active_type=='THINTRIS' else func(obj)
            cnt = 0
            if d.get("indices"): cnt = len(d["indices"].get("low_valence",[])+d["indices"].get("high_valence",[])) if isinstance(d["indices"],dict) else len(d["indices"])
            elif d.get("status")=="error": cnt=1
            item = next((r for r in props.results if r.issue_type == active_type), None)
            if item:
                item.count = cnt
                try: base=json.loads(props.baseline_stats)
                except: base={}
                if active_type in base and base[active_type]>0: item.improvement = max(0.0, 1.0-(cnt/base[active_type]))
                if cnt == 0: self.report({'INFO'}, f"{ISSUE_DISPLAY_NAMES[active_type]} Fixed!")
        props.current_indices.clear(); props.current_index = 0
        return {'FINISHED'}

class MESH_OT_OpenSpecificDoc(bpy.types.Operator):
    bl_idname = "mesh.open_specific_doc"; bl_label = "Open Explanation Doc"; issue_type: bpy.props.StringProperty()
    def execute(self, context):
        addon_dir = os.path.dirname(__file__); filename = f"{self.issue_type}.rtf"; filepath = os.path.join(addon_dir, "docs", filename)
        if not os.path.exists(filepath): self.report({'ERROR'}, f"Document not found: docs/{filename}"); return {'CANCELLED'}
        try:
            if sys.platform == 'win32': os.startfile(filepath)
            elif sys.platform == 'darwin': subprocess.call(('open', filepath))
            else: subprocess.call(('xdg-open', filepath))
        except Exception as e: self.report({'ERROR'}, f"Could not open file: {e}"); return {'CANCELLED'}
        return {'FINISHED'}

class MESH_OT_EduDialog(bpy.types.Operator):
    bl_idname = "mesh.edu_dialog"; bl_label = "Learn More"; issue_type: bpy.props.StringProperty()
    def execute(self, context): return {'FINISHED'}
    def draw(self, context):
        # Fallback dialog (not really used now that we have the HUD)
        layout = self.layout
        layout.label(text="See HUD for details")
    def invoke(self, context, event): return context.window_manager.invoke_props_dialog(self, width=500)

class MESH_OT_NavType(bpy.types.Operator):
    bl_idname = "mesh.nav_type"; bl_label = "Nav Type"; direction: bpy.props.IntProperty()
    def execute(self, context):
        props = context.scene.mesh_checker_props; current_type = props.issue_type
        bpy.ops.mesh.run_checks()
        if len(props.results) == 0: return {'FINISHED'}
        cur_idx = 0
        for i, r in enumerate(props.results):
            if r.issue_type == current_type: cur_idx = i; break
        new_idx = (cur_idx + self.direction) % len(props.results)
        props.issue_type = props.results[new_idx].issue_type
        props.current_indices.clear(); props.current_index = 0
        return {'FINISHED'}

class MESH_OT_NavIssue(bpy.types.Operator):
    bl_idname = "mesh.nav_issue"; bl_label = "Nav Issue"; direction: bpy.props.IntProperty()
    def execute(self, context):
        props = context.scene.mesh_checker_props; obj = context.active_object
        props.is_internal_operation = True
        if obj.mode == 'EDIT': bmesh.update_edit_mesh(obj.data)
        active_type = props.issue_type; func = None
        for p, f, c in CHECKS_MAPPING:
            if c == active_type: func = f; break
        if func:
            d = func(obj, props.thintris_threshold) if active_type=='THINTRIS' else func(obj)
            new_indices = []
            if d.get("indices"): new_indices = d["indices"].get("low_valence", []) + d["indices"].get("high_valence", []) if isinstance(d["indices"], dict) else d["indices"]
            item = next((r for r in props.results if r.issue_type == active_type), None)
            if item: item.count = len(new_indices)
            if len(new_indices) == 0: self.report({'INFO'}, "All fixed!"); props.current_indices.clear(); return {'FINISHED'}
            props.current_indices.clear()
            for i in new_indices: it = props.current_indices.add(); it.value = i
        if len(props.current_indices) > 0:
            new_idx = (props.current_index + self.direction) % len(props.current_indices)
            props.current_index = new_idx
            visualize_current(context)
        return {'FINISHED'}

class MESH_OT_Show(bpy.types.Operator):
    bl_idname = "mesh.show_vis"; bl_label = "Show"
    def execute(self, context): visualize_current(context); return {'FINISHED'}

class MESH_OT_SelectAll(bpy.types.Operator):
    bl_idname = "mesh.select_all_issues"; bl_label = "Select All"
    def execute(self, context):
        obj = context.active_object; props = context.scene.mesh_checker_props
        ensure_indices_for_issue(obj, props)
        if not props.current_indices: self.report({'INFO'}, "No issues to select."); return {'CANCELLED'}
        all_indices = [item.value for item in props.current_indices]; issue = props.issue_type
        mode_type = 'faces'
        if issue in ['POLES', 'ISOLATED', 'DUPLICATES', 'EDGEFLOW']: mode_type = 'verts'
        elif issue in ['NONMANIFOLD', 'HOLES']: mode_type = 'edges'
        highlight_generic(obj, all_indices, mode_type)
        self.report({'INFO'}, f"Selected {len(all_indices)} {issue} elements.")
        return {'FINISHED'}


# THE FLOATING HUD (PROPS DIALOG)
# =========================================================
class MESH_OT_OpenHUD(bpy.types.Operator):
    """Opens the Learn & Fix Floating Panel"""
    bl_idname = "mesh.open_hud"
    bl_label = "Learn & Fix"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        props = context.scene.mesh_checker_props
        mode = props.workflow_mode
        
        header = layout.row()
        header.alignment = 'EXPAND'
        
        icon_id = get_icon("learnfix_logo")
        if icon_id:
            header.label(text="", icon_value=icon_id)
        else:
            header.label(text="L&F", icon="SHADERFX")
            
        header.label(text="")
        
        layout.separator()

        box = layout.box()
        box.label(text="Step 1: Choose Workflow", icon="CHECKBOX_HLT")
        box.row().prop(props, "workflow_mode", text="")
        if mode=='SELECT': return

        layout.separator()
        layout.label(text="Step 2: Detect Errors", icon="VIEWZOOM")
        if mode=='CUSTOM':
            b=layout.box()
            b.prop(props,"show_topology",icon="TRIA_DOWN" if props.show_topology else "TRIA_RIGHT", emboss=False)
            b.label(text="Topology")
            if props.show_topology: 
                c=b.column(align=True)
                c.prop(props,"check_ngons")
                c.prop(props,"check_poles")
                c.prop(props,"check_thin_tris")
                c.prop(props,"check_isolated")
                c.prop(props,"check_edgeflow")
            b=layout.box()
            b.prop(props,"show_geometry",icon="TRIA_DOWN" if props.show_geometry else "TRIA_RIGHT", emboss=False)
            b.label(text="Geometry")
            if props.show_geometry: 
                c=b.column(align=True)
                c.prop(props,"check_duplicates")
                c.prop(props,"check_nonmanifold")
                c.prop(props,"check_selfintersect")
                c.prop(props,"check_holes")
                c.prop(props,"check_internalfaces")
            b=layout.box()
            b.prop(props,"show_normals",icon="TRIA_DOWN" if props.show_normals else "TRIA_RIGHT", emboss=False)
            b.label(text="Normals")
            if props.show_normals: 
                c=b.column(align=True)
                c.prop(props,"check_flipped")
                c.prop(props,"check_inconsistent")
                c.prop(props,"check_overlappinguv")
            b=layout.box()
            b.prop(props,"show_workflow",icon="TRIA_DOWN" if props.show_workflow else "TRIA_RIGHT", emboss=False)
            b.label(text="Transforms")
            if props.show_workflow: 
                c=b.column(align=True)
                c.prop(props,"check_transforms")
                c.prop(props,"check_origin")

        row=layout.row()
        row.scale_y=1.5; row.operator("mesh.run_checks", text="Check Mesh", icon="CHECKMARK")
        
        layout.separator()
        row = layout.row(align=True)
        row.prop(props, "auto_check_enabled", toggle=True, text="Auto-Check")
        if props.auto_check_enabled:
             row.prop(props, "auto_check_threshold", text="Moves")
        
        if len(props.results)>0:
            layout.separator()
            box=layout.box()
            row=box.row()
            row.label(text="Health:")
            row.prop(props,"total_score",text=f"{int(props.total_score*100)}%",slider=True)
            
            col=box.column()
            idx=0
            active=None
            for i,r in enumerate(props.results):
                if r.issue_type==props.issue_type: 
                    idx=i+1
                    active=r
                    break
            
            nav=col.row(align=True)
            nav.scale_y=1.2; nav.alignment='CENTER'
            nav.operator("mesh.nav_type",text="",icon="TRIA_LEFT").direction=-1
            lbl = f"{ISSUE_DISPLAY_NAMES.get(active.issue_type, active.issue_type)} ({idx}/{len(props.results)})" if active else "Select Error"
            nav.label(text=f"  {lbl}  ", icon="FILE_TEXT")
            nav.operator("mesh.nav_type",text="",icon="TRIA_RIGHT").direction=1
            col.separator()

            if active:
                ibox=col.box()
                
                h_row = ibox.row()
                h_row.label(text=f"{active.name} [{active.count}]")
                h_row.operator("mesh.refresh_active", text="", icon="FILE_REFRESH")
                
                if active.improvement>0:
                    ibox.prop(active,"improvement",text="Fixed",slider=True,emboss=False)
                
                r=ibox.row(align=True)
                r.operator("mesh.nav_issue",text="Prev").direction=-1
                r.operator("mesh.show_vis",text="Show")
                r.operator("mesh.nav_issue",text="Next").direction=1
                
                ibox.operator("mesh.select_all_issues", text=f"Select All", icon="RESTRICT_SELECT_OFF")

                info_row = ibox.row()
                info_icon = "TRIA_DOWN" if props.show_explanation else "TRIA_RIGHT"
                info_row.prop(props, "show_explanation", text="How to Fix & Tutorials", icon="INFO", toggle=True) 
                

                if props.show_explanation:
                    
                    info_box = ibox.box()
                    
                    pcoll = preview_collections.get("main")
                    icon_name = active.issue_type
                    
                    if pcoll and icon_name in pcoll:
                        icon_val = pcoll[icon_name].icon_id
                        row_icon = info_box.row()
                        row_icon.alignment = 'CENTER'
                        row_icon.template_icon(icon_value=icon_val, scale=8.0) 
                        info_box.separator()

                    explanation = get_smart_explanation(active.issue_type, mode, active.count)
                    
                    col = info_box.column()
                    for line in explanation.split('\n'):
                        col.label(text=line)
                    
                    info_box.separator()
                    
                    edu_row = info_box.row()
                    edu_row.scale_y=1.3
                    
                    op = edu_row.operator("wm.url_open", text="Tutorial", icon="URL")
                    op.url = YOUTUBE_URLS.get(active.issue_type, "https://youtube.com")
                    
                    doc_op = edu_row.operator("mesh.open_specific_doc", text="Theory", icon="FILE_TEXT")
                    doc_op.issue_type = active.issue_type
                
        elif props.total_score==1.0 and mode!='SELECT':
            layout.box().label(text="Perfect Score!", icon="CHECKMARK")

# HEADER ANIMATION LOGIC
# =========================================================
def redraw_header_timer():
    if time.time() - addon_start_time > 10.0:
        return None 
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    return 0.1

def draw_header_button(self, context):
    layout = self.layout
    elapsed = time.time() - addon_start_time
    is_flashing = False
    if elapsed < 10.0:
        if int(elapsed * 4) % 2 == 0:
            layout.alert = True
            is_flashing = True
    
    icon_id = get_icon("learnfix_logo")
    if icon_id:
        layout.operator("mesh.open_hud", text="Learn & Fix", icon_value=icon_id)
    else:
        layout.operator("mesh.open_hud", text="Learn & Fix", icon="HELP")
        
    if is_flashing: layout.alert = False

classes = (MeshCheckerIndexItem, MeshCheckerResultItem, MeshCheckerProperties, MESH_OT_RunChecks, MESH_OT_RefreshActive, MESH_OT_NavType, MESH_OT_NavIssue, MESH_OT_Show, MESH_OT_SelectAll, MESH_OT_EduDialog, MESH_OT_OpenSpecificDoc, MESH_OT_OpenHUD)

def register():
    global addon_start_time
    addon_start_time = time.time()
    load_preview_icons()
    for c in classes: bpy.utils.register_class(c)
    bpy.types.Scene.mesh_checker_props=bpy.props.PointerProperty(type=MeshCheckerProperties)
    bpy.types.VIEW3D_HT_header.append(draw_header_button)
    bpy.app.timers.register(redraw_header_timer, first_interval=0.1)
    if on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(on_depsgraph_update)

def unregister():
    if on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(on_depsgraph_update)
    bpy.types.VIEW3D_HT_header.remove(draw_header_button)
    unload_preview_icons()
    del bpy.types.Scene.mesh_checker_props
    for c in reversed(classes): bpy.utils.unregister_class(c)


if __name__ == "__main__": register()

