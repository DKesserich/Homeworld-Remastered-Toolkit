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
    "author": "David Lejeune, Dominic Cassidy & Dom2",
    "version": "200",
    "blender": (2, 5, 8),
    "api": 38691,
    "location": "File > Import-Export",
    "description": ("A combined toolkit for creating content for Homeworld Remastered. Includes a modified version of the Better Collada Exporter, new create options to automate Joint creation and a DAE importer."),
    "warning": "",
    "wiki_url": (""),
    "tracker_url": "",
    "support": 'OFFICIAL',
    "category": "Import-Export"}


if "bpy" in locals():
	import imp
	if "newDaeExport" in locals():
		imp.reload(newDaeExport)
	if "import_dae" in locals():
		imp.reload(import_dae)
	if "import_level" in locals():
		imp.reload(import_level)
	

import math
import bpy
import mathutils
import os
import bpy_extras

from bpy.props import StringProperty, BoolProperty, FloatProperty, EnumProperty, IntProperty

from bpy_extras.io_utils import (ExportHelper,
                                 path_reference_mode,
                                 axis_conversion,
                                 )

from . import joint_tools

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
        
        #obs = bpy.data.objects
        #for ob in obs:
        #    if "ROOT" in ob.name:
        #        ob.select = True
        #        bpy.ops.object.select_pattern(pattern="ROOT")
        #        bpy.ops.transform.rotate(value=(-90.0*2*math.pi/360.0), constraint_axis=(True, False, False))
        #        bpy.ops.object.transform_apply(location=False, rotation =True, scale=False)

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

        from . import newDaeExport
        return newDaeExport.save(self.filepath)

class ImportDAE(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
	"""Import HWRM DAE"""
	bl_idname = "import_scene.dae"
	bl_label = "Import HWRM DAE"
	bl_options = {'UNDO'}

	filename_ext = ".dae"

	filter_glob = bpy.props.StringProperty(
			default="*.dae",
			options={'HIDDEN'},
			)
	files = bpy.props.CollectionProperty(
			name="File Path",
			type=bpy.types.OperatorFileListElement,
			)
	directory = bpy.props.StringProperty(
			subtype='DIR_PATH',
			)

	import_as_visual_mesh = bpy.props.BoolProperty(
			name="Import as visual mesh",
			description="Import LOD[0] only as visual mesh",
			default=False,
			)
			
	merge_goblins = bpy.props.BoolProperty(
			name="Merge goblins",
			description="Merge goblins into LOD[0] mesh",
			default=False,
			)

	use_smoothing = bpy.props.BoolProperty(
			name="Split normals",
			description="Sometimes splitting normals causes Crash To Desktop for unknown reasons. If you get CTD, try turning this off...",
			default=True,
			)
	
	dock_path_vis = bpy.props.EnumProperty(
            name="Display dock segments as ",
            items=(('CONE', "Cone", ""),
                   ('SPHERE', "Sphere", ""),
				   ('CUBE', "Cube", ""),
				   ('CIRCLE', "Circle", ""),
                   ('SINGLE_ARROW', "Single Arrow", ""),
				   ('ARROWS', "Arrows", ""),
				   ('PLAIN_AXES', "Plain Axes", ""),
                   ),
            default='SPHERE',
            )

	def execute(self, context):
		print("Executing HWRM DAE import")
		print(self.filepath)
		from . import import_dae # re-import, just in case!
		if self.import_as_visual_mesh:
			print("Importing visual mesh only...")
			import_dae.ImportLOD0(self.filepath, self.use_smoothing)
		else:
			import_dae.ImportDAE(self.filepath, self.use_smoothing, self.dock_path_vis, self.merge_goblins)
		return {'FINISHED'}
###############################################################################
class ImportLevel(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
	"""Import HWRM Level"""
	bl_idname = "import_scene.level"
	bl_label = "Import HWRM Level"
	bl_options = {'UNDO'}

	filename_ext = ".level"

	filter_glob = bpy.props.StringProperty(
			default="*.level",
			options={'HIDDEN'},
			)
	files = bpy.props.CollectionProperty(
			name="File Path",
			type=bpy.types.OperatorFileListElement,
			)
	directory = bpy.props.StringProperty(
			subtype='DIR_PATH',
			)
	def execute(self, context):
		print("Executing HWRM Level import")
		print(self.filepath)
		from . import import_level # re-import, just in case!
		import_level.ImportLevel(self.filepath)
		return {'FINISHED'}
###############################################################################
def menu_func(self, context):
    self.layout.operator(ExportDAE.bl_idname, text="HWRM Collada (.dae)")

def menu_import(self, context):
	self.layout.operator(ImportDAE.bl_idname, text="HWRM DAE (.dae)")
	self.layout.operator(ImportLevel.bl_idname, text="HWRM Level (.level)")

def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_export.append(menu_func)
	bpy.types.INFO_MT_file_import.append(menu_import)
	
	
def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_export.remove(menu_func)
	bpy.types.INFO_MT_file_import.remove(menu_import)

if __name__ == "__main__":
    register()

