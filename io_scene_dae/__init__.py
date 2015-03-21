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
    "name": "Better Collada Exporter - HW Edition",
    "author": "Juan Linietsky, David Lejeune",
    "blender": (2, 5, 8),
    "api": 38691,
    "location": "File > Import-Export",
    "description": ("Export DAE Scenes to be compatible with the HODOR tool for Homeworld Remastered."),
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

from bpy.props import StringProperty, BoolProperty, FloatProperty, EnumProperty

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
	    default=False,
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
            default=False,
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
    bl_label = "HomeworldRM"
    bl_idname = "HMRM_TOOLS"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = "objectmode"
    bl_category = "Create"
    
    bpy.types.Scene.hardpoint_name = StringProperty(
        name = "Name")
    
    def draw(self, context):
        layout = self.layout
        scn = context.scene
        
        layout.prop(scn, 'hardpoint_name')
        layout.operator("hmrm.make_weapon", "Weapon")
        layout.operator("hmrm.make_turret", "Turret")
        layout.operator("hmrm.make_repair", "Repair")
        
class MakeWeaponHardpoint(bpy.types.Operator):
    bl_idname = "hmrm.make_weapon"
    bl_label = "Add Weapon Hardpoint"
    bl_options = {"UNDO"}
 
    def invoke(self, context, event):
        
        jntName_Pos = "JNT[Weapon_" + context.scene.hardpoint_name + "_Position]"
        jntName_Rest = "JNT[Weapon_" + context.scene.hardpoint_name + "_Rest]"
        jntName_Dir = "JNT[Weapon_" + context.scene.hardpoint_name + "_Direction]"
        
        weapon_pos = bpy.data.objects.new(jntName_Pos, None)
        context.scene.objects.link(weapon_pos)
        
        weapon_dir = bpy.data.objects.new(jntName_Dir, None)
        context.scene.objects.link(weapon_dir)
        
        weapon_rest = bpy.data.objects.new(jntName_Rest, None)
        context.scene.objects.link(weapon_rest)
        
        weapon_dir.parent = weapon_pos
        weapon_rest.parent = weapon_pos
        
        weapon_dir.location.xyz = [0,0,1]
        weapon_rest.location.xyz = [0,1,0]
        
        return {"FINISHED"}
    
class MakeTurretHardpoint(bpy.types.Operator):
    bl_idname = "hmrm.make_turret"
    bl_label = "Add Turret Hardpoint"
    bl_options = {"UNDO"}
    
    def invoke(self, context, event):

        jntName_Pos = "JNT[Weapon_" + context.scene.hardpoint_name + "_Position]"
        jntName_Rest = "JNT[Weapon_" + context.scene.hardpoint_name + "_Rest]"
        jntName_Dir = "JNT[Weapon_" + context.scene.hardpoint_name + "_Direction]"
        jntName_Lat = "JNT[Weapon_" + context.scene.hardpoint_name + "_Latitude]"
        jntName_Muz = "JNT[Weapon_" + context.scene.hardpoint_name + "_Muzzle]"
        
        weapon_pos = bpy.data.objects.new(jntName_Pos, None)
        context.scene.objects.link(weapon_pos)
        
        weapon_dir = bpy.data.objects.new(jntName_Dir, None)
        context.scene.objects.link(weapon_dir)
        
        weapon_rest = bpy.data.objects.new(jntName_Rest, None)
        context.scene.objects.link(weapon_rest)
        
        weapon_lat = bpy.data.objects.new(jntName_Lat, None)
        context.scene.objects.link(weapon_lat)
        
        weapon_muz = bpy.data.objects.new(jntName_Muz, None)
        context.scene.objects.link(weapon_muz)
        
        weapon_dir.parent = weapon_pos
        weapon_rest.parent = weapon_pos
        weapon_lat.parent = weapon_pos
        weapon_muz.parent = weapon_pos
        
        weapon_dir.location.xyz = [0,0,1]
        weapon_rest.location.xyz = [0,1,0]
        
        
        return {"FINISHED"}
		
class MakeRepairHardpoint(bpy.types.Operator):
    bl_idname = "hmrm.make_repair"
    bl_label = "Add Repair Hardpoint"
    bl_options = {"UNDO"}
    
    def invoke(self, context, event):

        jntName_Pos = "JNT[RepairPoint" + context.scene.hardpoint_name + "]"
        jntName_Head = "JNT[RepairPoint" + context.scene.hardpoint_name + "Heading]"
        jntName_Left = "JNT[RepairPoint" + context.scene.hardpoint_name + "Left]"
        jntName_Up = "JNT[RepairPoint" + context.scene.hardpoint_name + "Up]"
        
        hardp_pos = bpy.data.objects.new(jntName_Pos, None)
        context.scene.objects.link(hardp_pos)
        
        hardp_head = bpy.data.objects.new(jntName_Head, None)
        context.scene.objects.link(hardp_head)
        
        hardp_left = bpy.data.objects.new(jntName_Left, None)
        context.scene.objects.link(hardp_left)
        
        hardp_up = bpy.data.objects.new(jntName_Up, None)
        context.scene.objects.link(hardp_up)
        
        hardp_head.parent = hardp_pos
        hardp_left.parent = hardp_pos
        hardp_up.parent = hardp_pos
        
        hardp_up.location.xyz = [0,0,1]
        hardp_head.location.xyz = [0,1,0]
        hardp_left.location.xyz = [-1,0,0]
        
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
