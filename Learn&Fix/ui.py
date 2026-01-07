import bpy
import os

# =========================================================================
# 1. HELPER FUNCTIONS & DATA
# =========================================================================

def get_error_image_path(error_key):
    """
    Returns the absolute path to the icon image based on the error key.
    Example: 'ngons' -> '.../addons/LearnFix/icons/NGONS.png'
    """
    # Get the folder where this script (ui.py) is located
    addon_folder = os.path.dirname(__file__)
    
    # Construct the full path: AddonFolder / icons / ERROR_NAME.png
    # We use upper() because your files are named NGONS.png, POLES.png, etc.
    filename = f"{error_key.upper()}.png"
    return os.path.join(addon_folder, "icons", filename)

# Dictionary of explanations (You can move this to a constants.py file later)
EXPLANATION_DATA = {
    "ngons": {
        "title": "N-Gons Detected",
        "desc": "An N-Gon is a face with more than 4 vertices. They cause shading artifacts and ruin subdivision surfaces.",
        "url": "https://www.youtube.com/results?search_query=blender+ngons+fix"
    },
    "poles": {
        "title": "E-Poles (Stars)",
        "desc": "A vertex connected to 5 or more edges. While sometimes necessary, they cause pinching if placed on curved surfaces.",
        "url": "https://www.youtube.com/results?search_query=blender+poles+topology"
    },
    "flipped_normals": {
        "title": "Flipped Normals",
        "desc": "Some faces are pointing inwards. This causes invisible faces in game engines and black spots in renders.",
        "url": "https://www.youtube.com/results?search_query=blender+recalculate+normals"
    },
    # ... add default fallback for others ...
}

def get_explanation(error_key):
    return EXPLANATION_DATA.get(error_key, {
        "title": error_key.replace("_", " ").title(),
        "desc": "This geometry issue may cause problems in shading or printing. See the diagram for details.",
        "url": "https://www.youtube.com/results?search_query=blender+" + error_key
    })


# =========================================================================
# 2. THE EXPLAIN & FIX POPUP (Modal Dialog)
# =========================================================================

class LearnFix_OT_Explain_Popup(bpy.types.Operator):
    bl_idname = "learnfix.explain_popup"
    bl_label = "Explain & Fix"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    # We pass the error key (e.g. 'ngons') to this operator
    error_key: bpy.props.StringProperty()

    def invoke(self, context, event):
        # Set the width of the popup window
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):
        layout = self.layout
        data = get_explanation(self.error_key)
        
        # --- HEADER ---
        layout.label(text=data['title'], icon='INFO')
        layout.separator()
        
        # --- IMAGE SECTION ---
        # 1. Get Path
        image_path = get_error_image_path(self.error_key)
        
        # 2. Try to load and display
        img = None
        try:
            # check_existing=True ensures we don't reload it if it's already in memory
            if os.path.exists(image_path):
                img = bpy.data.images.load(image_path, check_existing=True)
            else:
                layout.label(text=f"Image missing: {self.error_key.upper()}.png", icon='ERROR')
        except:
            layout.label(text="Error loading image", icon='ERROR')

        if img:
            row = layout.row()
            row.alignment = 'CENTER'
            # Display the image inside a box
            box = row.box()
            # scale_x/y controls the display size in the popup
            box.template_image(img, "pixels", scale_x=6, scale_y=4)

        layout.separator()

        # --- EXPLANATION TEXT ---
        box = layout.box()
        # Text wrapping is tricky in Blender API, we simulate it by using multiple labels or a paragraph
        # Ideally, keep descriptions short (under 80 chars) or split lines.
        col = box.column()
        col.label(text="WHY IS THIS BAD?")
        
        # Simple word wrap logic for the UI
        words = data['desc'].split()
        chunk_size = 8
        for i in range(0, len(words), chunk_size):
            line = " ".join(words[i:i+chunk_size])
            col.label(text=line)

        layout.separator()

        # --- ACTIONS ---
        row = layout.row()
        row.scale_y = 1.5
        
        # Button 1: YouTube Link
        op = row.operator("wm.url_open", text="Watch Tutorial", icon='URL')
        op.url = data['url']
        
        # Button 2: Quick Fix (Calls the fix operator)
        fix_op = row.operator("learnfix.fix_error", text="Auto-Fix (Try)", icon='MODIFIER')
        fix_op.error_key = self.error_key


# =========================================================================
# 3. THE MAIN N-PANEL UI
# =========================================================================

class LearnFix_PT_Main(bpy.types.Panel):
    bl_label = "Learn & Fix"
    bl_idname = "LEARNFIX_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Learn & Fix'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Access your PropertyGroup (Assuming you named it 'learnfix_props' in __init__.py)
        props = scene.learnfix_props 

        # --- STEP 1: CONFIGURATION ---
        box = layout.box()
        box.label(text="Step 1: Workflow", icon='SETTINGS')
        row = box.row()
        row.prop(props, "workflow_mode", text="") # Dropdown (3D Print / Game / etc.)

        # --- STEP 2: ACTION ---
        row = layout.row()
        row.scale_y = 1.5
        row.operator("learnfix.check_mesh", text="Check Mesh", icon='SHADING_BBOX')

        layout.separator()

        # --- STEP 3: RESULTS (Hidden until checked) ---
        if props.has_checked:
            
            # HEALTH BAR VISUALIZATION
            # We use a progress bar to show health
            row = layout.row()
            row.prop(props, "health_score", text="Mesh Health", slider=True, emboss=False)
            
            # Color coding the bar (Visual trick)
            if props.health_score > 0.8:
                row.alert = False # Normal (Greenish in theme)
            elif props.health_score > 0.5:
                pass # Default Grey
            else:
                row.alert = True # Red

            layout.separator()

            # FOCUS MODE CARD
            if len(props.error_list) > 0:
                current_error = props.error_list[props.active_error_index]
                
                # The "Card"
                box = layout.box()
                
                # Header of Card
                row = box.row()
                row.alignment = 'CENTER'
                row.label(text=f"Issue {props.active_error_index + 1} of {len(props.error_list)}")
                
                # Error Name
                row = box.row()
                row.alignment = 'CENTER'
                # Format name: "ngons" -> "N Gons" or similar
                display_name = current_error.name.replace("_", " ").upper()
                row.label(text=f"⚠ {display_name}")

                # Count
                row = box.row()
                row.alignment = 'CENTER'
                row.label(text=f"Count: {current_error.count} faces/verts")

                box.separator()

                # NAVIGATION (Previous | Show | Next)
                row = box.row(align=True)
                row.scale_y = 1.2
                
                # Prev
                row.operator("learnfix.navigate_error", text="", icon='TRIA_LEFT').direction = 'PREV'
                
                # Show / Refresh
                show_btn = row.operator("learnfix.focus_camera", text="SHOW", icon='VIEW_CAMERA')
                show_btn.error_index = props.active_error_index
                
                # Next
                row.operator("learnfix.navigate_error", text="", icon='TRIA_RIGHT').direction = 'NEXT'

                box.separator()
                
                # EDUCATIONAL ACTION
                row = box.row()
                row.scale_y = 1.5
                op = row.operator("learnfix.explain_popup", text="Explain & Fix", icon='HELP')
                op.error_key = current_error.key # Pass the key (e.g. 'ngons') to the popup

            else:
                # Success State
                col = layout.column(align=True)
                col.alert = False
                col.label(text="No errors found!", icon='CHECKMARK')
                col.label(text="Your mesh is clean.")


# =========================================================================
# REGISTRATION
# =========================================================================

classes = (
    LearnFix_OT_Explain_Popup,
    LearnFix_PT_Main,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)