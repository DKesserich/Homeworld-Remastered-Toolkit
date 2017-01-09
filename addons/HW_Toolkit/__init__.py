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
    "author": "David Lejeune, Dominic Cassidy",
    "version": "112",
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
	if "newDaeExport" in locals():
		imp.reload(newDaeExport)
	

import math
import bpy
import mathutils

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


def menu_func(self, context):
    self.layout.operator(ExportDAE.bl_idname, text="HWRM Collada (.dae)")


def register():
	bpy.utils.register_module(__name__)
	
	bpy.types.INFO_MT_file_export.append(menu_func)
	
	
def unregister():
	
	bpy.utils.unregister_module(__name__)
	
	bpy.types.INFO_MT_file_export.remove(menu_func)
	

if __name__ == "__main__":
    register()

