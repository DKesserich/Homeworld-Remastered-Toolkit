# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8-80 compliant>

bl_info = {

    "name": "Homeworld Remastered Toolkit",
    "author": "Juan Linietsky, David Lejeune, Dominic Cassidy",
    "blender": (2, 5, 8),
    "api": 38691,
    "location": "File > Import-Export",

    "description": ("A combined toolkit for creating content for Homeworld Remastered. Includes a modified version of the Better Collada Exporter, and new create options to automate Joint creation"),
    "warning": "",
    "wiki_url": (""),
    "tracker_url": "",
    "support": 'OFFICIAL',
    "category": "Import-Export"}


if "bpy" in locals():
    import imp
    if "export_dae" in locals():
        imp.reload(export_dae)

import math
import bpy
import mathutils

from bpy.props import StringProperty, BoolProperty, FloatProperty, EnumProperty, IntProperty

from bpy_extras.io_utils import (ExportHelper,
                                 path_reference_mode,
                                 axis_conversion,
                                 )

class ExportDAE(bpy.types.Operator, ExportHelper):
    '''Selection to DAE'''
    bl_idname = "export_scene.dae"
    bl_label = "Export DAE"
    bl_options = {'PRESET'}

    filename_ext = ".dae"
    filter_glob = StringProperty(default="*.dae", options={'HIDDEN'})

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

   
    object_types = EnumProperty(
            name="Object Types",
            options={'ENUM_FLAG'},
            items=(('EMPTY', "Empty", ""),
                   ('CAMERA', "Camera", ""),
                   ('LAMP', "Lamp", ""),
                   ('ARMATURE', "Armature", ""),
                   ('MESH', "Mesh", ""),
                   ('CURVE', "Curve", ""),
                   ),
            default={'EMPTY', 'CAMERA', 'LAMP', 'ARMATURE', 'MESH','CURVE'},
            )

    use_export_selected = BoolProperty(
            name="Selected Objects",
            description="Export only selected objects (and visible in active layers if that applies).",
            default=False,
            )
    use_mesh_modifiers = BoolProperty(
            name="Apply Modifiers",
            description="Apply modifiers to mesh objects (on a copy!).",
            default=True,
            )
    use_tangent_arrays = BoolProperty(
	    name="Tangent Arrays",
	    description="Export Tangent and Binormal arrays (for normalmapping).",
	    default=False,
	    )
    use_triangles = BoolProperty(
	    name="Triangulate",
	    description="Export Triangles instead of Polygons.",
	    default=True,
	    )

    use_copy_images = BoolProperty(
            name="Copy Images",
            description="Copy Images (create images/ subfolder)",
            default=False,
            )
    use_active_layers = BoolProperty(
            name="Active Layers",
            description="Export only objects on the active layers.",
            default=True,
            )
    use_exclude_ctrl_bones = BoolProperty(
            name="Exclude Control Bones",
            description="Exclude skeleton bones with names that begin with 'ctrl'.",
            default=True,
            )
    use_anim = BoolProperty(
            name="Export Animation",
            description="Export keyframe animation",
            default=True,
            )
    use_anim_action_all = BoolProperty(
            name="All Actions",
            description=("Export all actions for the first armature found in separate DAE files"),
            default=False,
            )
    use_anim_skip_noexp = BoolProperty(
	    name="Skip (-noexp) Actions",
	    description="Skip exporting of actions whose name end in (-noexp). Useful to skip control animations.",
	    default=True,
	    )
    use_anim_optimize = BoolProperty(
            name="Optimize Keyframes",
            description="Remove double keyframes",
            default=True,
            )

    anim_optimize_precision = FloatProperty(
            name="Precision",
            description=("Tolerence for comparing double keyframes "
                        "(higher for greater accuracy)"),
            min=1, max=16,
            soft_min=1, soft_max=16,
            default=6.0,
            )

    use_metadata = BoolProperty(
            name="Use Metadata",
            default=True,
            options={'HIDDEN'},
            )

    @property
    def check_extension(self):
        return True#return self.batch_mode == 'OFF'

    def check(self, context):
        return True
        """
        isretur_def_change = super().check(context)
        return (is_xna_change or is_def_change)
        """

    def execute(self, context):
        if not self.filepath:
            raise Exception("filepath not set")

        """        global_matrix = Matrix()

                global_matrix[0][0] = \
                global_matrix[1][1] = \
                global_matrix[2][2] = self.global_scale
        """

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "global_scale",
                                            "check_existing",
                                            "filter_glob",
                                            "xna_validate",
                                            ))

        from . import export_dae
        return export_dae.save(self, context, **keywords)

class HMRMPanel(bpy.types.Panel):
    """Creates a Panel in the Create window"""
    bl_label = "Hardpoints"
    bl_idname = "HMRM_TOOLS"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = "objectmode"
    bl_category = "Create"
    
    bpy.types.Scene.parent_name = StringProperty(
        name = "Parent")
    
    bpy.types.Scene.hardpoint_name = StringProperty(
        name = "Name",
        default = "Default")

    bpy.types.Scene.hardpoint_num = IntProperty(
        name = "Number",
        min = 0)
        
    bpy.types.Scene.utility_name = IntProperty(
        name = "Hardpoint",
        min = 0)
        
    bpy.types.Scene.ship_name = StringProperty(
        name = "Name",
        default = "Default")
        
    bpy.types.Scene.lod_num = IntProperty(
        name = "LOD",
        min = 0,
        max = 3,
        default = 0
        )
    
    def draw(self, context):
        layout = self.layout
        scn = context.scene
                
        layout.label("Ship")
        layout.prop(scn, 'ship_name')
        layout.prop(scn,'lod_num')
        layout.operator("hmrm.make_ship", "Convert to Ship")
        
        layout.separator()
        
        layout.label("Weapons")
        layout.prop_search(scn, "parent_name", scn, "objects")
        layout.prop(scn, 'hardpoint_name')
        layout.prop(scn,'hardpoint_num')
        layout.operator("hmrm.make_weapon", "Weapon").makeTurret = False
        layout.operator("hmrm.make_weapon", "Turret").makeTurret = True
        
        layout.separator()
        
        layout.label("Utilities")
        layout.prop_search(scn, "parent_name", scn, "objects")
        layout.prop(scn,'utility_name')
        layout.operator("hmrm.make_hardpoint", "Repair").hardName = "RepairPoint"
        layout.operator("hmrm.make_hardpoint", "Salvage").hardName = "SalvagePoint"
        layout.operator("hmrm.make_hardpoint","Capture").hardName = "CapturePoint"
        
        
class HMRMPanelEngines(bpy.types.Panel):
    """Creates a Panel in the Create window"""
    bl_label = "Engines"
    bl_idname = "HMRM_TOOLS_ENGINES"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = "objectmode"
    bl_category = "Create"   
    
    bpy.types.Scene.engine_small = IntProperty(
        name = "Engine",
        min = 1,
        default = 1
        )   
        
    bpy.types.Scene.engine_small_flame = IntProperty(
        name = "Flame Div",
        min = 1,
        default = 1
        )   
    
    def draw(self, context):
        layout = self.layout
        scn = context.scene
        
        layout.label("Large")
        layout.prop_search(scn, "parent_name", scn, "objects")
        
        layout.separator()
        
        layout.label("Small")
        layout.prop_search(scn, "parent_name", scn, "objects")
        layout.prop(scn,'engine_small')
        layout.prop(scn,'engine_small_flame')
        layout.operator("hmrm.make_engine_small","Add").useSelected = False
        layout.operator("hmrm.make_engine_small","Convert Selection").useSelected = True
    
        
class MakeShipLOD(bpy.types.Operator):
    bl_idname = "hmrm.make_ship"
    bl_label = "Add Weapon Hardpoint"
    bl_options = {"UNDO"}
 
    def invoke(self, context, event):
        
        jntName_LOD = "ROOT_LOD[" + str(context.scene.lod_num) + "]"
        jntName = "JNT[" + context.scene.ship_name + "]"
        
        LOD_jnt = bpy.data.objects.new(jntName_LOD, None)
        context.scene.objects.link(LOD_jnt)
        
        ship_jnt = bpy.data.objects.new(jntName, None)
        context.scene.objects.link(ship_jnt)
        ship_jnt.parent = LOD_jnt
        
        bpy.context.selected_objects[0].name = "MULT[" + context.scene.ship_name + "]"
        bpy.context.selected_objects[0].parent = ship_jnt
        
        
        return {"FINISHED"}
        
class MakeWeaponHardpoint(bpy.types.Operator):
    bl_idname = "hmrm.make_weapon"
    bl_label = "Add Weapon Hardpoint"
    bl_options = {"UNDO"}
    makeTurret = bpy.props.BoolProperty()
 
    def invoke(self, context, event):
        
        tempName = context.scene.hardpoint_name
        
        if context.scene.hardpoint_num > 0:
            tempName = context.scene.hardpoint_name  + str(context.scene.hardpoint_num)
            
        jntName_Pos = "JNT[Weapon_" + tempName + "_Position]"
        jntName_Rest = "JNT[Weapon_" + tempName + "_Rest]"
        jntName_Dir = "JNT[Weapon_" + tempName + "_Direction]"
        jntName_Muz = "JNT[Weapon_" + tempName +"_Muzzle]"
        if self.makeTurret:
            jntName_Lat = "JNT[Weapon_" + tempName + "_Latitude]"
            weapon_lat = bpy.data.objects.new(jntName_Lat, None)
            context.scene.objects.link(weapon_lat)
        
        weapon_pos = bpy.data.objects.new(jntName_Pos, None)
        context.scene.objects.link(weapon_pos)
        
        weapon_dir = bpy.data.objects.new(jntName_Dir, None)
        context.scene.objects.link(weapon_dir)
        
        weapon_rest = bpy.data.objects.new(jntName_Rest, None)
        context.scene.objects.link(weapon_rest)

        weapon_muzzle = bpy.data.objects.new(jntName_Muz, None)
        context.scene.objects.link(weapon_muzzle)
		
        if context.scene.parent_name:
            weapon_pos.parent = context.scene.objects[context.scene.parent_name]
            
        weapon_dir.parent = weapon_pos
        weapon_rest.parent = weapon_pos
        weapon_muzzle.parent = weapon_pos
        if self.makeTurret:
            weapon_lat.parent = weapon_pos
        
        #Following standard Blender workflow, create the object at the 3D Cursor location
        #Also, since the Direction and Rest joints are in local space for Postion,
        #and HODOR expects Y-Up, offset Y for Dir and Z for rest.
        #Rotate Pos 90 degrees on X to align with Blender world space.
        
        weapon_pos.location = bpy.context.scene.cursor_location
        weapon_pos.rotation_euler.x = 1.57079633
        weapon_dir.location.xyz = [0,1,0]
        weapon_rest.location.xyz = [0,0,1]
        weapon_muzzle.location.xyz = [0,0,-0.25]
        return {"FINISHED"}
  
class MakeHardpoint(bpy.types.Operator):
    bl_idname = "hmrm.make_hardpoint"
    bl_label = "Add Hardpoint"
    bl_options = {"UNDO"}
    hardName = bpy.props.StringProperty()
    
    def invoke(self, context, event):

        jntName_Pos = "JNT[" + self.hardName + str(context.scene.utility_name) + "]"
        jntName_Head = "JNT[" + self.hardName + str(context.scene.utility_name) + "Heading]"
        jntName_Left = "JNT[" + self.hardName + str(context.scene.utility_name) + "Left]"
        jntName_Up = "JNT[" + self.hardName + str(context.scene.utility_name) + "Up]"
        
        hardp_pos = bpy.data.objects.new(jntName_Pos, None)
        context.scene.objects.link(hardp_pos)
        
        hardp_head = bpy.data.objects.new(jntName_Head, None)
        context.scene.objects.link(hardp_head)
        
        hardp_left = bpy.data.objects.new(jntName_Left, None)
        context.scene.objects.link(hardp_left)
        
        hardp_up = bpy.data.objects.new(jntName_Up, None)
        context.scene.objects.link(hardp_up)
        
        if context.scene.parent_name:
            hardp_pos.parent = context.scene.objects[context.scene.parent_name]
            
        hardp_head.parent = hardp_pos
        hardp_left.parent = hardp_pos
        hardp_up.parent = hardp_pos
        
        hardp_pos.location = bpy.context.scene.cursor_location
        hardp_pos.rotation_euler.x = 1.57079633
        hardp_up.location.xyz = [0,1,0]
        hardp_head.location.xyz = [0,0,1]
        hardp_left.location.xyz = [1,0,0]
        
        return {"FINISHED"}
    
    
class MakeEngineSmall(bpy.types.Operator):
    bl_idname = "hmrm.make_engine_small"
    bl_label = "Create Small Engine"
    bl_options = {"UNDO"}
    useSelected = bpy.props.BoolProperty()
    
    def invoke(self, context, event):
    
        jntNozzle = "JNT[EngineNozzle" + str(context.scene.engine_small) + "]"
        jntBurn = "BURN[EngineBurn" + str(context.scene.engine_small) + "]"
        jntShape = "ETSH[EngineShape" + str(context.scene.engine_small) + "]"
        
        engine_nozzle = bpy.data.objects.new(jntNozzle, None)
        context.scene.objects.link(engine_nozzle)
        
        engine_burn = bpy.data.objects.new(jntBurn, None)
        context.scene.objects.link(engine_burn)
        
        if self.useSelected:
            bpy.context.selected_objects[0].name = jntShape
        else:
            verts = [(0.5,-0.5,0),(0.5,0.5,0),(-0.5,-0.5,0),(-0.5,0.5,0)]
            faces = [(2,3,1,0)]
            engine_mesh = bpy.data.meshes.new(jntShape)
            engine_shape = bpy.data.objects.new(jntShape,engine_mesh)
            context.scene.objects.link(engine_shape)
            engine_shape.parent = engine_nozzle
            engine_mesh.from_pydata(verts,[],faces)
            engine_mesh.update(calc_edges=True)
        
        if context.scene.parent_name:
            engine_nozzle.parent = context.scene.objects[context.scene.parent_name]
            
        engine_burn.parent = engine_nozzle
        
        for f in range (0, context.scene.engine_small_flame):
            flameDiv = "Flame[0]_Div[" + str(f) + "]"
            flame_div = bpy.data.objects.new(flameDiv, None)
            context.scene.objects.link(flame_div)
            
            flame_div.parent = engine_burn
            flame_div.location.z = 0-f
        
        
        engine_nozzle.rotation_euler.x = 1.57079633
        if self.useSelected:
            engine_nozzle.location = bpy.context.selected_objects[0].location
            bpy.context.selected_objects[0].parent = engine_nozzle
            bpy.context.selected_objects[0].location.xyz = [0,0,0]
        else:
            engine_nozzle.location = bpy.context.scene.cursor_location
    
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(ExportDAE.bl_idname, text="Better Collada - HW (.dae)")

def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_export.append(menu_func)

def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_export.remove(menu_func)

if __name__ == "__main__":
    register()
