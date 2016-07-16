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

# <pep8 compliant>

# Script copyright (C) Juan Linietsky
# Contact Info: juan@codenix.com

"""
This script is an exporter to the Khronos Collada file format.

http://www.khronos.org/collada/
"""

# TODO:
# Materials & Textures
# Optionally export Vertex Colors
# Morph Targets
# Control bone removal
# Copy textures
# Export Keyframe Optimization
# --
# Morph Targets
# Blender native material? (?)

import os
import time
import math  # math.pi
import shutil
import bpy
import bmesh
from mathutils import Vector, Matrix

#according to collada spec, order matters
S_ASSET=0
S_IMGS=1
S_MATS=2
S_FX=3
S_GEOM=4
S_MORPH=5
S_SKIN=6
S_CONT=7
S_CAMS=8
S_LAMPS=9
S_ANIM_CLIPS=10
S_NODES=11
S_ANIM=12

CMP_EPSILON=0.0001

def snap_tup(tup):
	ret=()
	for x in tup:
		ret+=( x-math.fmod(x,0.0001), )

	return tup


def strmtx(mtx):
	s=" "
	for x in range(4):
		for y in range(4):
			s+=str(mtx[x][y])
			s+=" "
	s+=" "
	return s

def numarr(a,mult=1.0):
	s=" "
	for x in a:
		s+=" "+str(x*mult)
	s+=" "
	return s

def strarr(arr):
	s=" "
	for x in arr:
		s+=" "+str(x)
	s+=" "
	return s



class DaeExporter:

	def validate_id(self,d):
		if (d.find("id-")==0):
			return "z"+d
		return d


	def new_id(self,t):
		self.last_id+=1
		return "id-"+t+"-"+str(self.last_id)

	class Vertex:

		def close_to(v):
			if ( (self.vertex-v.vertex).length() > CMP_EPSILON ):
				return False
			if ( (self.normal-v.normal).length() > CMP_EPSILON ):
				return False
			if ( (self.uv-v.uv).length() > CMP_EPSILON ):
				return False
			if ( (self.uv2-v.uv2).length() > CMP_EPSILON ):
				return False

			return True

		def get_tup(self):
			tup = (self.vertex.x,self.vertex.y,self.vertex.z,self.normal.x,self.normal.y,self.normal.z)
			for t in self.uv:
				tup = tup + (t.x,t.y)
			if (self.color!=None):
				tup = tup + (self.color.x,self.color.y,self.color.z)
			if (self.tangent!=None):
				tup = tup + (self.tangent.x,self.tangent.y,self.tangent.z)
			if (self.bitangent!=None):
				tup = tup + (self.bitangent.x,self.bitangent.y,self.bitangent.z)
			#for t in self.bones:
			#	tup = tup + (t)
			#for t in self.weights:
			#	tup = tup + (t)

			return tup

		def __init__(self):
			self.vertex = Vector( (0.0,0.0,0.0) )
			self.normal = Vector( (0.0,0.0,0.0) )
			self.tangent = None
			self.bitangent = None
			self.color = None
			self.uv = []
			self.uv2 = Vector( (0.0,0.0) )
			self.bones=[]
			self.weights=[]


	def writel(self,section,indent,text):
		if (not (section in self.sections)):
			self.sections[section]=[]
		line=""
		for x in range(indent):
			line+="\t"
		line+=text
		self.sections[section].append(line)


	def export_image(self,image):

		if (image in self.image_cache):
			return self.image_cache[image]

		imgpath = image.image.filepath
		if (imgpath.find("//")==0 or imgpath.find("\\\\")==0):
			#if relative, convert to absolute
			imgpath = bpy.path.abspath(imgpath)

		#path is absolute, now do something!

		if (self.config["use_copy_images"]):
			#copy image
			basedir = os.path.dirname(self.path)+"/images"
			if (not os.path.isdir(basedir)):
				os.makedirs(basedir)
			dstfile=basedir+"/"+os.path.basename(imgpath)
			if (not os.path.isfile(dstfile)):
				shutil.copy(imgpath,dstfile)
			imgpath="images/"+os.path.basename(imgpath)

		else:
			#export relative, always, no one wants absolute paths.
			try:
				imgpath = os.path.relpath(imgpath,os.path.dirname(self.path)).replace("\\","/") # export unix compatible always
			except:
				pass #fails sometimes, not sure why



		imgid = image.name
		self.writel(S_IMGS,1,'<image id="'+imgid+'-image" name="'+image.name+'">')
		self.writel(S_IMGS,2,'<init_from>'+imgpath+'</init_from>')
		self.writel(S_IMGS,1,'</image>')
		self.image_cache[image]=imgid
		return imgid

	def export_material(self,material,double_sided_hint=True):

		if (material in self.material_cache):
			return self.material_cache[material]
		
		#fxid pulls Material Name instead of generating a new id - DL
		fxid = material.name
		self.writel(S_FX,1,'<effect id="'+fxid+'-fx" name="'+material.name+'">')
		self.writel(S_FX,2,'<profile_COMMON>')

		#Find and fetch the textures and create sources
		sampler_table={}
		diffuse_tex=None
		specular_tex=None
		emission_tex=None
		normal_tex=None
		for i in range(len(material.texture_slots)):
			ts=material.texture_slots[i]
			if (not ts):
				continue
			if (not ts.use):
				continue
			if (not ts.texture):
				continue
			if (ts.texture.type!="IMAGE"):
				continue

			if (ts.texture.image==None):
				continue

			#image
			imgid = self.export_image(ts.texture)

			#Don't seem to need any of this surface and sampler stuff - DL
			#surface
			#surface_sid = self.new_id("fx_surf")
			#self.writel(S_FX,3,'<newparam sid="'+surface_sid+'">')
			#self.writel(S_FX,4,'<surface type="2D">')
			#self.writel(S_FX,5,'<init_from>'+imgid+'</init_from>') #this is sooo weird
			#self.writel(S_FX,5,'<format>A8R8G8B8</format>')
			#self.writel(S_FX,4,'</surface>')
			#self.writel(S_FX,3,'</newparam>')
			#sampler, collada sure likes it difficult
			sampler_sid = self.new_id("fx_sampler")
			#self.writel(S_FX,3,'<newparam sid="'+sampler_sid+'">')
			##self.writel(S_FX,4,'<sampler2D>')
			#self.writel(S_FX,5,'<source>'+surface_sid+'</source>')
			#self.writel(S_FX,4,'</sampler2D>')
			#self.writel(S_FX,3,'</newparam>')
			sampler_table[i]=sampler_sid

			if (ts.use_map_color_diffuse and diffuse_tex==None):
				diffuse_tex=ts.texture.name
			if (ts.use_map_color_spec and specular_tex==None):
				specular_tex=ts.texture.name
			if (ts.use_map_emit and emission_tex==None):
				emission_tex=ts.texture.name
			if (ts.use_map_normal and normal_tex==None):
				normal_tex=ts.texture.name
		
		#Changed the technique and shader type to match the 3DS Max DAE output - DL
		self.writel(S_FX,3,'<technique sid="standard">')
		shtype="phong"
		self.writel(S_FX,4,'<'+shtype+'>')
		#ambient? from where?

		self.writel(S_FX,5,'<emission>')
		if (emission_tex!=None):
			self.writel(S_FX,6,'<texture texture="'+emission_tex+'-image" texcoord="CHANNEL0">')
			#added all the Maya technique stuff - DL
			self.writel(S_FX,7,'<extra>')
			self.writel(S_FX,8,'<technique profile="MAYA">')		
			self.writel(S_FX,9,'<wrapU sid="wrapU0">TRUE</wrapU>')
			self.writel(S_FX,9,'<wrapV sid="wrapV0">TRUE</wrapV>')
			self.writel(S_FX,9,'<blend_mode>ADD</blend_mode>')
			self.writel(S_FX,8,'</technique>')			
			self.writel(S_FX,7,'</extra>')
			self.writel(S_FX,6,'</texture>')
		else:
			self.writel(S_FX,6,'<color sid="emission">'+numarr(material.diffuse_color,material.emit)+' </color>') # not totally right but good enough
		self.writel(S_FX,5,'</emission>')

		self.writel(S_FX,5,'<ambient>')
		self.writel(S_FX,6,'<color sid="ambient">'+numarr(self.scene.world.ambient_color)+' '+str(material.ambient)+'</color>')
		self.writel(S_FX,5,'</ambient>')

		self.writel(S_FX,5,'<diffuse>')
		if (diffuse_tex!=None):
			self.writel(S_FX,6,'<texture texture="'+diffuse_tex+'-image" texcoord="CHANNEL0">')
			#Yup, more Maya technique stuff - DL
			self.writel(S_FX,7,'<extra>')
			self.writel(S_FX,8,'<technique profile="MAYA">')		
			self.writel(S_FX,9,'<wrapU sid="wrapU0">TRUE</wrapU>')
			self.writel(S_FX,9,'<wrapV sid="wrapV0">TRUE</wrapV>')
			self.writel(S_FX,9,'<blend_mode>ADD</blend_mode>')
			self.writel(S_FX,8,'</technique>')			
			self.writel(S_FX,7,'</extra>')
			self.writel(S_FX,6,'</texture>')
		else:
			self.writel(S_FX,6,'<color sid="diffuse">'+numarr(material.diffuse_color,material.diffuse_intensity)+'</color>')
		self.writel(S_FX,5,'</diffuse>')

		self.writel(S_FX,5,'<specular>')
		if (specular_tex!=None):
			self.writel(S_FX,6,'<texture texture="'+specular_tex+'-image" texcoord="CHANNEL0">')
			#And again with the Maya technique stuff - DL
			self.writel(S_FX,7,'<extra>')
			self.writel(S_FX,8,'<technique profile="MAYA">')		
			self.writel(S_FX,9,'<wrapU sid="wrapU0">TRUE</wrapU>')
			self.writel(S_FX,9,'<wrapV sid="wrapV0">TRUE</wrapV>')
			self.writel(S_FX,9,'<blend_mode>ADD</blend_mode>')
			self.writel(S_FX,8,'</technique>')			
			self.writel(S_FX,7,'</extra>')
			self.writel(S_FX,6,'</texture>')
		else:
			self.writel(S_FX,6,'<color sid="specular">'+numarr(material.specular_color,material.specular_intensity)+'</color>')
		self.writel(S_FX,5,'</specular>')

		self.writel(S_FX,5,'<shininess>')
		self.writel(S_FX,6,'<float sid="shininess">'+str(material.specular_hardness)+'</float>')
		self.writel(S_FX,5,'</shininess>')

		#Gotta have the reflective params. Don't seem to need the relectivity params that were in the 3DS Max DAE - DL
		self.writel(S_FX,5,'<reflective>')
		self.writel(S_FX,6,'<color>'+strarr(material.mirror_color)+'</color>')
		self.writel(S_FX,5,'</reflective>')

		if (material.use_transparency):
			self.writel(S_FX,5,'<transparency>')
			self.writel(S_FX,6,'<float sid="transparency">'+str(material.alpha)+'</float>')
			self.writel(S_FX,5,'</transparency>')
		else:
			self.writel(S_FX,5,'<transparency>')
			self.writel(S_FX,6,'<float sid="transparency">0.000000</float>')
			self.writel(S_FX,5,'</transparency>')


		self.writel(S_FX,4,'</'+shtype+'>')
		#Don't seem need any of this stuff - DL
		#self.writel(S_FX,4,'<index_of_refraction>'+str(material.specular_ior)+'</index_of_refraction>')

		#self.writel(S_FX,4,'<extra>')
		#self.writel(S_FX,5,'<technique profile="MAYA">')
		#if (normal_tex):
		#	self.writel(S_FX,6,'<bump bumptype="NORMALMAP">')
		#	self.writel(S_FX,7,'<texture texture="'+normal_tex+'-image" texcoord="CHANNEL0"/>')
		#	self.writel(S_FX,6,'</bump>')
		#self.writel(S_FX,6,'<wrapU sid="wrapU0">TRUE</wrapU>')
		#self.writel(S_FX,6,'<wrapV sid="wrapV0">TRUE</wrapV>')
		#self.writel(S_FX,6,'<blend_mode>ADD</blend_mode>')

		#self.writel(S_FX,5,'</technique>')
		#self.writel(S_FX,5,'<technique profile="GOOGLEEARTH">')
		#self.writel(S_FX,6,'<double_sided>'+["0","1"][double_sided_hint]+"</double_sided>")
		#self.writel(S_FX,5,'</technique>')
		#self.writel(S_FX,4,'</extra>')

		self.writel(S_FX,3,'</technique>')
		self.writel(S_FX,2,'</profile_COMMON>')
		self.writel(S_FX,1,'</effect>')

		# Also export blender material in all it's glory (if set as active)


		#Material
		#matid pulls Material Name instead of using randomly generated id - DL
		matid = material.name
		self.writel(S_MATS,1,'<material id="'+matid+'" name="'+material.name+'">')
		self.writel(S_MATS,2,'<instance_effect url="#'+matid+'-fx"/>')
		self.writel(S_MATS,1,'</material>')

		self.material_cache[material]=matid
		return matid


	def export_mesh(self,node,armature=None,skeyindex=-1,skel_source=None,custom_name=None):

		mesh = node.data


		if (node.data in self.mesh_cache):
			return self.mesh_cache[mesh]

		if (skeyindex==-1 and mesh.shape_keys!=None and len(mesh.shape_keys.key_blocks)):
			values=[]
			morph_targets=[]
			md=None
			for k in range(0,len(mesh.shape_keys.key_blocks)):
			    shape = node.data.shape_keys.key_blocks[k]
			    values+=[shape.value] #save value
			    shape.value=0

			mid = self.new_id("morph")

			for k in range(0,len(mesh.shape_keys.key_blocks)):

				shape = node.data.shape_keys.key_blocks[k]
				node.show_only_shape_key=True
				node.active_shape_key_index = k
				shape.value = 1.0
				mesh.update()
				"""
				oldval = shape.value
				shape.value = 1.0

				"""
				p = node.data
				v = node.to_mesh(bpy.context.scene, True, "RENDER")
				node.data = v
#				self.export_node(node,il,shape.name)
				node.data.update()
				if (armature and k==0):
					md=self.export_mesh(node,armature,k,mid,shape.name)
				else:
					md=self.export_mesh(node,None,k,None,shape.name)

				node.data = p
				node.data.update()
				shape.value = 0.0
				morph_targets.append(md)

				"""
				shape.value = oldval
				"""
			node.show_only_shape_key=False
			node.active_shape_key_index = 0


			self.writel(S_MORPH,1,'<controller id="'+mid+'" name="">')
			#if ("skin_id" in morph_targets[0]):
			#	self.writel(S_MORPH,2,'<morph source="#'+morph_targets[0]["skin_id"]+'" method="NORMALIZED">')
			#else:
			self.writel(S_MORPH,2,'<morph source="#'+morph_targets[0]["id"]+'" method="NORMALIZED">')

			self.writel(S_MORPH,3,'<source id="'+mid+'-morph-targets">')
			self.writel(S_MORPH,4,'<IDREF_array id="'+mid+'-morph-targets-array" count="'+str(len(morph_targets)-1)+'">')
			marr=""
			warr=""
			for i in range(len(morph_targets)):
				if (i==0):
				    continue
				elif (i>1):
					marr+=" "

				if ("skin_id" in morph_targets[i]):
					marr+=morph_targets[i]["skin_id"]
				else:
					marr+=morph_targets[i]["id"]

				warr+=" 0"

			self.writel(S_MORPH,5,marr)
			self.writel(S_MORPH,4,'</IDREF_array>')
			self.writel(S_MORPH,4,'<technique_common>')
			self.writel(S_MORPH,5,'<accessor source="#'+mid+'-morph-targets-array" count="'+str(len(morph_targets)-1)+'" stride="1">')
			self.writel(S_MORPH,6,'<param name="MORPH_TARGET" type="IDREF"/>')
			self.writel(S_MORPH,5,'</accessor>')
			self.writel(S_MORPH,4,'</technique_common>')
			self.writel(S_MORPH,3,'</source>')

			self.writel(S_MORPH,3,'<source id="'+mid+'-morph-weights">')
			self.writel(S_MORPH,4,'<float_array id="'+mid+'-morph-weights-array" count="'+str(len(morph_targets)-1)+'" >')
			self.writel(S_MORPH,5,warr)
			self.writel(S_MORPH,4,'</float_array>')
			self.writel(S_MORPH,4,'<technique_common>')
			self.writel(S_MORPH,5,'<accessor source="#'+mid+'-morph-weights-array" count="'+str(len(morph_targets)-1)+'" stride="1">')
			self.writel(S_MORPH,6,'<param name="MORPH_WEIGHT" type="float"/>')
			self.writel(S_MORPH,5,'</accessor>')
			self.writel(S_MORPH,4,'</technique_common>')
			self.writel(S_MORPH,3,'</source>')

			self.writel(S_MORPH,3,'<targets>')
			self.writel(S_MORPH,4,'<input semantic="MORPH_TARGET" source="#'+mid+'-morph-targets"/>')
			self.writel(S_MORPH,4,'<input semantic="MORPH_WEIGHT" source="#'+mid+'-morph-weights"/>')
			self.writel(S_MORPH,3,'</targets>')
			self.writel(S_MORPH,2,'</morph>')
			self.writel(S_MORPH,1,'</controller>')
			if (armature!=None):

				self.armature_for_morph[node]=armature

			meshdata={}
			if (armature):
				meshdata = morph_targets[0]
				meshdata["morph_id"]=mid
			else:
				meshdata["id"]=morph_targets[0]["id"]
				meshdata["morph_id"]=mid
				meshdata["material_assign"]=morph_targets[0]["material_assign"]



			self.mesh_cache[node.data]=meshdata
			return meshdata

		apply_modifiers = len(node.modifiers) and self.config["use_mesh_modifiers"]

		#Turned off all the to_mesh ops since they were messing with the mesh names - DL
		#mesh=node.to_mesh(self.scene,apply_modifiers,"RENDER") #is this allright?

		triangulate=self.config["use_triangles"]
		if (triangulate):
			bpy.context.scene.objects.active = node
			bpy.ops.object.modifier_add(type='TRIANGULATE')
			bpy.ops.object.modifier_apply(modifier="Triangulate")
		#	bm = bmesh.new()
		#	bm.from_mesh(mesh)
		#	bmesh.ops.triangulate(bm, faces=bm.faces)
		#	bm.to_mesh(mesh)
		#	bm.free()


		mesh.update(calc_tessface=True)
		vertices=[]
		vertex_map={}
		surface_indices={}
		materials={}

		materials={}

		si=None
		if (armature!=None):
			si=self.skeleton_info[armature]

		has_uv=False
		has_uv2=False
		has_weights=armature!=None
		has_tangents=self.config["use_tangent_arrays"] # could detect..
		has_colors=len(mesh.vertex_colors)
		mat_assign=[]

		uv_layer_count=len(mesh.uv_textures)
		if (len(mesh.uv_textures)):
			try:
				mesh.calc_tangents()
			except:
				print("Warning, blender API is fucked up, not exporting UVs for this object.")
				uv_layer_count=0
				mesh.calc_normals_split()
				has_tangents=False

		else:
			mesh.calc_normals_split()
			has_tangents=False


		for fi in range(len(mesh.polygons)):
			f=mesh.polygons[fi]

			if (not (f.material_index in surface_indices)):
				surface_indices[f.material_index]=[]
				print("Type: "+str(type(f.material_index)))
				print("IDX: "+str(f.material_index)+"/"+str(len(mesh.materials)))

				try:
					#Bizarre blender behavior i don't understand, so catching exception
					mat = mesh.materials[f.material_index]
				except:
					mat= None

				if (mat!=None):
					materials[f.material_index]=self.export_material( mat,mesh.show_double_sided )
				else:
					materials[f.material_index]=None #weird, has no material?

			indices = surface_indices[f.material_index]
			vi=[]
			#vertices always 3
			"""
			if (len(f.vertices)==3):
				vi.append(0)
				vi.append(1)
				vi.append(2)
			elif (len(f.vertices)==4):
				#todo, should use shortest path
				vi.append(0)
				vi.append(1)
				vi.append(2)
				vi.append(0)
				vi.append(2)
				vi.append(3)
			"""

			for lt in range(f.loop_total):
				loop_index = f.loop_start + lt
				ml = mesh.loops[loop_index]
				mv = mesh.vertices[ml.vertex_index]

				v = self.Vertex()
				v.vertex = Vector( mv.co )

				for xt in mesh.uv_layers:
					v.uv.append( Vector( xt.data[loop_index].uv ) )

				if (has_colors):
					v.color = Vector( mesh.vertex_colors[0].data[loop_index].color )

				v.normal = Vector( ml.normal )

				if (has_tangents):
					v.tangent = Vector( ml.tangent )
					v.bitangent = Vector( ml.bitangent )


			       # if (armature):
			       #         v.vertex = node.matrix_world * v.vertex

				#v.color=Vertex(mv. ???

				if (armature!=None):
					wsum=0.0
					for vg in mv.groups:
						if vg.group >= len(node.vertex_groups):
							continue;
						name = node.vertex_groups[vg.group].name
						if (name in si["bone_index"]):
							#could still put the weight as 0.0001 maybe
							if (vg.weight>0.001): #blender has a lot of zero weight stuff
								v.bones.append(si["bone_index"][name])
								v.weights.append(vg.weight)
								wsum+=vg.weight


				tup = v.get_tup()
				idx = 0
				if (skeyindex==-1 and tup in vertex_map): #do not optmize if using shapekeys
					idx = vertex_map[tup]
				else:
					idx = len(vertices)
					vertices.append(v)
					vertex_map[tup]=idx

				vi.append(idx)

			if (len(vi)>2):
				#only triangles and above
				indices.append(vi)

		#meshid pulls Mesh Name instead of using randomly generated ID - DL
		meshid = mesh.name
		if (custom_name!=None):
			self.writel(S_GEOM,1,'<geometry id="'+meshid+'" name="'+custom_name+'">')
		else:
			self.writel(S_GEOM,1,'<geometry id="'+meshid+'" name="'+mesh.name+'">')

		self.writel(S_GEOM,2,'<mesh>')


		# Vertex Array
		self.writel(S_GEOM,3,'<source id="'+meshid+'-positions">')
		#NTS: "float_values" is the container for the array of vertices - DL
		float_values=""
		#NTS: loops through all the vertices in the mesh and adds their x, y, and z coordinates to the float_values array -DL
		for v in mesh.vertices:
			print(v.co)
			float_values+=" "+str(v.co[0])+" "+str(v.co[1])+" "+str(v.co[2])
		#NTS: writes the entire float_vales array to a string - DL
		self.writel(S_GEOM,4,'<float_array id="'+meshid+'-positions-array" count="'+str(len(mesh.vertices)*3)+'">'+float_values+'</float_array>')
		self.writel(S_GEOM,4,'<technique_common>')
		#NTS: Tells the software that is viewing the DAE how to parse the vertex array - DL
		self.writel(S_GEOM,4,'<accessor source="#'+meshid+'-positions-array" count="'+str(len(mesh.vertices))+'" stride="3">')
		self.writel(S_GEOM,5,'<param name="X" type="float"/>')
		self.writel(S_GEOM,5,'<param name="Y" type="float"/>')
		self.writel(S_GEOM,5,'<param name="Z" type="float"/>')
		self.writel(S_GEOM,4,'</accessor>')
		self.writel(S_GEOM,4,'</technique_common>')
		self.writel(S_GEOM,3,'</source>')

		# Normal Array

		self.writel(S_GEOM,3,'<source id="'+meshid+'-normals">')
		float_values=""
		count=0
		for v in mesh.loops:
			 float_values+=" "+str(v.normal.x)+" "+str(v.normal.y)+" "+str(v.normal.z)
			 count += 3
		self.writel(S_GEOM,4,'<float_array id="'+meshid+'-normals-array" count="'+str(count)+'">'+float_values+'</float_array>')
		self.writel(S_GEOM,4,'<technique_common>')
		self.writel(S_GEOM,4,'<accessor source="#'+meshid+'-normals-array" count="'+str(count/3)+'" stride="3">')
		self.writel(S_GEOM,5,'<param name="X" type="float"/>')
		self.writel(S_GEOM,5,'<param name="Y" type="float"/>')
		self.writel(S_GEOM,5,'<param name="Z" type="float"/>')
		self.writel(S_GEOM,4,'</accessor>')
		self.writel(S_GEOM,4,'</technique_common>')
		self.writel(S_GEOM,3,'</source>')
		

		if (has_tangents):
			self.writel(S_GEOM,3,'<source id="'+meshid+'-tangents">')
			float_values=""
			for v in vertices:
				float_values+=" "+str(v.tangent.x)+" "+str(v.tangent.y)+" "+str(v.tangent.z)
			self.writel(S_GEOM,4,'<float_array id="'+meshid+'-tangents-array" count="'+str(len(vertices)*3)+'">'+float_values+'</float_array>')
			self.writel(S_GEOM,4,'<technique_common>')
			self.writel(S_GEOM,4,'<accessor source="#'+meshid+'-tangents-array" count="'+str(len(vertices))+'" stride="3">')
			self.writel(S_GEOM,5,'<param name="X" type="float"/>')
			self.writel(S_GEOM,5,'<param name="Y" type="float"/>')
			self.writel(S_GEOM,5,'<param name="Z" type="float"/>')
			self.writel(S_GEOM,4,'</accessor>')
			self.writel(S_GEOM,4,'</technique_common>')
			self.writel(S_GEOM,3,'</source>')

			self.writel(S_GEOM,3,'<source id="'+meshid+'-bitangents">')
			float_values=""
			for v in vertices:
				float_values+=" "+str(v.bitangent.x)+" "+str(v.bitangent.y)+" "+str(v.bitangent.z)
			self.writel(S_GEOM,4,'<float_array id="'+meshid+'-bitangents-array" count="'+str(len(vertices)*3)+'">'+float_values+'</float_array>')
			self.writel(S_GEOM,4,'<technique_common>')
			self.writel(S_GEOM,4,'<accessor source="#'+meshid+'-bitangents-array" count="'+str(len(vertices))+'" stride="3">')
			self.writel(S_GEOM,5,'<param name="X" type="float"/>')
			self.writel(S_GEOM,5,'<param name="Y" type="float"/>')
			self.writel(S_GEOM,5,'<param name="Z" type="float"/>')
			self.writel(S_GEOM,4,'</accessor>')
			self.writel(S_GEOM,4,'</technique_common>')
			self.writel(S_GEOM,3,'</source>')



		# UV Arrays

		for uvi in mesh.uv_layers:

			self.writel(S_GEOM,3,'<source id="'+meshid+'-texcoord-'+str(uvi.name)+'">')
			float_values=""
			count=0
			
			for v in uvi.data:
				float_values+=" "+str(v.uv.x)+" "+str(v.uv.y)+"\n"
				count+=2

			self.writel(S_GEOM,4,'<float_array id="'+meshid+'-texcoord-'+str(uvi.name)+'-array" count="'+str(count)+'">'+float_values+'</float_array>')
			self.writel(S_GEOM,4,'<technique_common>')
			self.writel(S_GEOM,4,'<accessor source="#'+meshid+'-texcoord-'+str(uvi.name)+'-array" count="'+str(count/2)+'" stride="2">')
			self.writel(S_GEOM,5,'<param name="S" type="float"/>')
			self.writel(S_GEOM,5,'<param name="T" type="float"/>')
			self.writel(S_GEOM,4,'</accessor>')
			self.writel(S_GEOM,4,'</technique_common>')
			self.writel(S_GEOM,3,'</source>')

		# Color Arrays

		if (has_colors):
			self.writel(S_GEOM,3,'<source id="'+meshid+'-colors">')
			float_values=""
			for v in vertices:
				float_values+=" "+str(v.color.x)+" "+str(v.color.y)+" "+str(v.color.z)
			self.writel(S_GEOM,4,'<float_array id="'+meshid+'-colors-array" count="'+str(len(vertices)*3)+'">'+float_values+'</float_array>')
			self.writel(S_GEOM,4,'<technique_common>')
			self.writel(S_GEOM,4,'<accessor source="#'+meshid+'-colors-array" count="'+str(len(vertices))+'" stride="3">')
			self.writel(S_GEOM,5,'<param name="X" type="float"/>')
			self.writel(S_GEOM,5,'<param name="Y" type="float"/>')
			self.writel(S_GEOM,5,'<param name="Z" type="float"/>')			
			self.writel(S_GEOM,4,'</accessor>')
			self.writel(S_GEOM,4,'</technique_common>')
			self.writel(S_GEOM,3,'</source>')

		# Triangle Lists
		self.writel(S_GEOM,3,'<vertices id="'+meshid+'-vertices">')
		self.writel(S_GEOM,4,'<input semantic="POSITION" source="#'+meshid+'-positions"/>')
		self.writel(S_GEOM,3,'</vertices>')

		prim_type=""
		if (triangulate):
			prim_type="triangles"
		else:
			prim_type="polygons"


		for m in surface_indices:
			indices = surface_indices[m]
			mat = materials[m]
			
			

			if (mat!=None):
				#matref = self.new_id("trimat")
				matref = mat
				self.writel(S_GEOM,3,'<'+prim_type+' count="'+str(int(len(indices)))+'" material="'+matref+'">') # todo material
				mat_assign.append( (mat,matref) )
			else:
				self.writel(S_GEOM,3,'<'+prim_type+' count="'+str(int(len(indices)))+'">') # todo material


			self.writel(S_GEOM,4,'<input semantic="VERTEX" offset="0" source="#'+meshid+'-vertices"/>')
			self.writel(S_GEOM,4,'<input semantic="NORMAL" offset="1" source="#'+meshid+'-normals"/>')
			
			offset=1

			for uvi in range(0,len(mesh.uv_layers)):
				self.writel(S_GEOM,4,'<input semantic="TEXCOORD" offset="'+str(offset)+'" set="'+str(uvi)+'" source="#'+meshid+'-texcoord-'+str(mesh.uv_layers[uvi].name)+'"/>')
				

			if (has_colors):
				self.writel(S_GEOM,4,'<input semantic="COLOR" offset="0" source="#'+meshid+'-colors"/>')
			if (has_tangents):
				self.writel(S_GEOM,4,'<input semantic="TEXTANGENT" source="#'+meshid+'-tangents" offset="0"/>')
				self.writel(S_GEOM,4,'<input semantic="TEXBINORMAL" source="#'+meshid+'-bitangents" offset="0"/>')

				#TODO: Figure out a better solution for the Texcoord and Normal <p> data
			if (triangulate):
				int_values="<p>"
				pVerts=[]
				pInds=[]
				for p in mesh.polygons:
					for i in p.vertices:
						pVerts.append(i)
				for i in range(0,len(pVerts)):
					pInds.append(i)
				for p in mesh.polygons:
					if (p.material_index==m):
						for i in p.loop_indices:
							int_values+=" "+str(pVerts[i])+" "+str(i)
						"""for i in p.vertices:
							int_values+=" "+str(pVerts[pVerts.index(i)])+" "+str(pInds[pVerts.index(i)])
							pVerts[pVerts.index(i)]=-1"""
										
				"""for pv in range(0,len(pVerts)):
					int_values+=" "+str(pVerts[pv])+" "+str(pv)
					#if(offset > 1):
					#	for o in range(offset-1):
					#		int_values+=" "+str(pv)"""
				int_values+=" </p>"
				self.writel(S_GEOM,4,int_values)
			else:
				for p in indices:
					int_values="<p>"
					for i in p:
						int_values+=" "+str(i)
					int_values+=" </p>"
					self.writel(S_GEOM,4,int_values)

			self.writel(S_GEOM,3,'</'+prim_type+'>')


		self.writel(S_GEOM,2,'</mesh>')
		self.writel(S_GEOM,1,'</geometry>')


		meshdata={}
		meshdata["id"]=meshid
		meshdata["material_assign"]=mat_assign
		if (skeyindex==-1):
			self.mesh_cache[node.data]=meshdata


		# Export armature data (if armature exists)

		if (armature!=None and (skel_source!=None or skeyindex==-1)):

			contid = self.new_id("controller")

			self.writel(S_SKIN,1,'<controller id="'+contid+'">')
			if (skel_source!=None):
				self.writel(S_SKIN,2,'<skin source="#'+skel_source+'">')
			else:
				self.writel(S_SKIN,2,'<skin source="#'+meshid+'">')

			self.writel(S_SKIN,3,'<bind_shape_matrix>'+strmtx(node.matrix_world)+'</bind_shape_matrix>')
			#Joint Names
			self.writel(S_SKIN,3,'<source id="'+contid+'-joints">')
			name_values=""
			for v in si["bone_names"]:
				name_values+=" "+v

			self.writel(S_SKIN,4,'<Name_array id="'+contid+'-joints-array" count="'+str(len(si["bone_names"]))+'">'+name_values+'</Name_array>')
			self.writel(S_SKIN,4,'<technique_common>')
			self.writel(S_SKIN,4,'<accessor source="#'+contid+'-joints-array" count="'+str(len(si["bone_names"]))+'" stride="1">')
			self.writel(S_SKIN,5,'<param name="JOINT" type="Name"/>')
			self.writel(S_SKIN,4,'</accessor>')
			self.writel(S_SKIN,4,'</technique_common>')
			self.writel(S_SKIN,3,'</source>')
			#Pose Matrices!
			self.writel(S_SKIN,3,'<source id="'+contid+'-bind_poses">')
			pose_values=""
			for v in si["bone_bind_poses"]:
				pose_values+=" "+strmtx(v)

			self.writel(S_SKIN,4,'<float_array id="'+contid+'-bind_poses-array" count="'+str(len(si["bone_bind_poses"])*16)+'">'+pose_values+'</float_array>')
			self.writel(S_SKIN,4,'<technique_common>')
			self.writel(S_SKIN,4,'<accessor source="#'+contid+'-bind_poses-array" count="'+str(len(si["bone_bind_poses"]))+'" stride="16">')
			self.writel(S_SKIN,5,'<param name="TRANSFORM" type="float4x4"/>')
			self.writel(S_SKIN,4,'</accessor>')
			self.writel(S_SKIN,4,'</technique_common>')
			self.writel(S_SKIN,3,'</source>')
			#Skin Weights!
			self.writel(S_SKIN,3,'<source id="'+contid+'-skin_weights">')
			skin_weights=""
			skin_weights_total=0
			for v in vertices:
				skin_weights_total+=len(v.weights)
				for w in v.weights:
					skin_weights+=" "+str(w)

			self.writel(S_SKIN,4,'<float_array id="'+contid+'-skin_weights-array" count="'+str(skin_weights_total)+'">'+skin_weights+'</float_array>')
			self.writel(S_SKIN,4,'<technique_common>')
			self.writel(S_SKIN,4,'<accessor source="#'+contid+'-skin_weights-array" count="'+str(skin_weights_total)+'" stride="1">')
			self.writel(S_SKIN,5,'<param name="WEIGHT" type="float"/>')
			self.writel(S_SKIN,4,'</accessor>')
			self.writel(S_SKIN,4,'</technique_common>')
			self.writel(S_SKIN,3,'</source>')


			self.writel(S_SKIN,3,'<joints>')
			self.writel(S_SKIN,4,'<input semantic="JOINT" source="#'+contid+'-joints"/>')
			self.writel(S_SKIN,4,'<input semantic="INV_BIND_MATRIX" source="#'+contid+'-bind_poses"/>')
			self.writel(S_SKIN,3,'</joints>')
			self.writel(S_SKIN,3,'<vertex_weights count="'+str(len(vertices))+'">')
			self.writel(S_SKIN,4,'<input semantic="JOINT" source="#'+contid+'-joints" offset="0"/>')
			self.writel(S_SKIN,4,'<input semantic="WEIGHT" source="#'+contid+'-skin_weights" offset="1"/>')
			vcounts=""
			vs=""
			vcount=0
			for v in vertices:
				vcounts+=" "+str(len(v.weights))
				for b in v.bones:
					vs+=" "+str(b)
					vs+=" "+str(vcount)
					vcount+=1
			self.writel(S_SKIN,4,'<vcount>'+vcounts+'</vcount>')
			self.writel(S_SKIN,4,'<v>'+vs+'</v>')
			self.writel(S_SKIN,3,'</vertex_weights>')


			self.writel(S_SKIN,2,'</skin>')
			self.writel(S_SKIN,1,'</controller>')
			meshdata["skin_id"]=contid


		return meshdata


	def export_mesh_node(self,node,il):

		if (node.data==None):
			return
		armature=None

		if (node.parent!=None):
			if (node.parent.type=="ARMATURE"):
				armature=node.parent

		if (node.data.shape_keys!=None):
				sk = node.data.shape_keys
				if (sk.animation_data):
					print("HAS ANIM")
					print("DRIVERS: "+str(len(sk.animation_data.drivers)))
					for d in sk.animation_data.drivers:
						if (d.driver):
							for v in d.driver.variables:
								for t in v.targets:
									if (t.id!=None and t.id.name in self.scene.objects):
										print("LINKING "+str(node)+" WITH "+str(t.id.name))
										self.armature_for_morph[node]=self.scene.objects[t.id.name]


		meshdata = self.export_mesh(node,armature)
		close_controller=False

		if ("skin_id" in meshdata):
			close_controller=True
			self.writel(S_NODES,il,'<instance_controller url="#'+meshdata["skin_id"]+'">')
			for sn in self.skeleton_info[armature]["skeleton_nodes"]:
				self.writel(S_NODES,il+1,'<skeleton>#'+sn+'</skeleton>')
		elif ("morph_id" in meshdata):
			self.writel(S_NODES,il,'<instance_controller url="#'+meshdata["morph_id"]+'">')
			close_controller=True
		elif (armature==None):
			self.writel(S_NODES,il,'<instance_geometry url="#'+meshdata["id"]+'">')		


		if (len(meshdata["material_assign"])>0):

			self.writel(S_NODES,il+1,'<bind_material>')
			self.writel(S_NODES,il+2,'<technique_common>')
			for m in meshdata["material_assign"]:
				self.writel(S_NODES,il+3,'<instance_material symbol="'+m[1]+'" target="#'+m[0]+'"/>')

			self.writel(S_NODES,il+2,'</technique_common>')
			self.writel(S_NODES,il+1,'</bind_material>')

		if (close_controller):
			self.writel(S_NODES,il,'</instance_controller>')
		else:
			self.writel(S_NODES,il,'</instance_geometry>')


	def export_armature_bone(self,bone,il,si):
		boneid = self.new_id("bone")
		boneidx = si["bone_count"]
		si["bone_count"]+=1
		bonesid = si["id"]+"-"+str(boneidx)
		si["bone_index"][bone.name]=boneidx
		si["bone_ids"][bone]=boneid
		si["bone_names"].append(bonesid)
		self.writel(S_NODES,il,'<node id="'+boneid+'" sid="'+bonesid+'" name="'+bone.name+'" type="JOINT">')
		il+=1
		xform = bone.matrix_local
		si["bone_bind_poses"].append((si["armature_xform"] * xform).inverted())

		if (bone.parent!=None):
			xform = bone.parent.matrix_local.inverted() * xform
		else:
			si["skeleton_nodes"].append(boneid)

		self.writel(S_NODES,il,'<matrix sid="transform">'+strmtx(xform)+'</matrix>')
		for c in bone.children:
			self.export_armature_bone(c,il,si)
		il-=1
		self.writel(S_NODES,il,'</node>')


	def export_armature_node(self,node,il):

		if (node.data==None):
			return

		self.skeletons.append(node)

		armature = node.data
		self.skeleton_info[node]={ "bone_count":0, "id":self.new_id("skelbones"),"name":node.name, "bone_index":{},"bone_ids":{},"bone_names":[],"bone_bind_poses":[],"skeleton_nodes":[],"armature_xform":node.matrix_world }



		for b in armature.bones:
			if (b.parent!=None):
				continue
			self.export_armature_bone(b,il,self.skeleton_info[node])

		if (node.pose):
			for b in node.pose.bones:
				for x in b.constraints:
					if (x.type=='ACTION'):
						self.action_constraints.append(x.action)


	def export_camera_node(self,node,il):

		if (node.data==None):
			return

		camera=node.data
		camid=self.new_id("camera")
		self.writel(S_CAMS,1,'<camera id="'+camid+'" name="'+camera.name+'">')
		self.writel(S_CAMS,2,'<optics>')
		self.writel(S_CAMS,3,'<technique_common>')
		if (camera.type=="PERSP"):
			self.writel(S_CAMS,4,'<perspective>')
			self.writel(S_CAMS,5,'<yfov> '+str(math.degrees(camera.angle))+' </yfov>') # I think?
			self.writel(S_CAMS,5,'<aspect_ratio> '+str(self.scene.render.resolution_x / self.scene.render.resolution_y)+' </aspect_ratio>')
			self.writel(S_CAMS,5,'<znear> '+str(camera.clip_start)+' </znear>')
			self.writel(S_CAMS,5,'<zfar> '+str(camera.clip_end)+' </zfar>')
			self.writel(S_CAMS,4,'</perspective>')
		else:
			self.writel(S_CAMS,4,'<orthografic>')
			self.writel(S_CAMS,5,'<xmag> '+str(camera.ortho_scale)+' </xmag>') # I think?
			self.writel(S_CAMS,5,'<aspect_ratio> '+str(self.scene.render.resolution_x / self.scene.render.resolution_y)+' </aspect_ratio>')
			self.writel(S_CAMS,5,'<znear> '+str(camera.clip_start)+' </znear>')
			self.writel(S_CAMS,5,'<zfar> '+str(camera.clip_end)+' </zfar>')
			self.writel(S_CAMS,4,'</orthografic>')

		self.writel(S_CAMS,3,'</technique_common>')
		self.writel(S_CAMS,2,'</optics>')
		self.writel(S_CAMS,1,'</camera>')


		self.writel(S_NODES,il,'<instance_camera url="#'+camid+'"/>')

	def export_lamp_node(self,node,il):

		if (node.data==None):
			return

		light=node.data
		lightid=self.new_id("light")
		self.writel(S_LAMPS,1,'<light id="'+lightid+'" name="'+light.name+'">')
		#self.writel(S_LAMPS,2,'<optics>')
		self.writel(S_LAMPS,3,'<technique_common>')

		if (light.type=="POINT"):
			self.writel(S_LAMPS,4,'<point>')
			self.writel(S_LAMPS,5,'<color>'+strarr(light.color)+'</color>')
			att_by_distance = 2.0 / light.distance # convert to linear attenuation
			self.writel(S_LAMPS,5,'<linear_attenuation>'+str(att_by_distance)+'</linear_attenuation>')
			if (light.use_sphere):
				self.writel(S_LAMPS,5,'<zfar>'+str(light.distance)+'</zfar>')

			self.writel(S_LAMPS,4,'</point>')
		elif (light.type=="SPOT"):
			self.writel(S_LAMPS,4,'<spot>')
			self.writel(S_LAMPS,5,'<color>'+strarr(light.color)+'</color>')
			att_by_distance = 2.0 / light.distance # convert to linear attenuation
			self.writel(S_LAMPS,5,'<linear_attenuation>'+str(att_by_distance)+'</linear_attenuation>')
			self.writel(S_LAMPS,5,'<falloff_angle>'+str(math.degrees(light.spot_size))+'</falloff_angle>')
			self.writel(S_LAMPS,4,'</spot>')


		else: #write a sun lamp for everything else (not supported)
			self.writel(S_LAMPS,4,'<directional>')
			self.writel(S_LAMPS,5,'<color>'+strarr(light.color)+'</color>')
			self.writel(S_LAMPS,4,'</directional>')


		self.writel(S_LAMPS,3,'</technique_common>')
		#self.writel(S_LAMPS,2,'</optics>')
		self.writel(S_LAMPS,1,'</light>')


		self.writel(S_NODES,il,'<instance_light url="#'+lightid+'"/>')


	def export_curve(self,curve):

		splineid = self.new_id("spline")

		self.writel(S_GEOM,1,'<geometry id="'+splineid+'" name="'+curve.name+'">')
		self.writel(S_GEOM,2,'<spline closed="0">')

		points=[]
		interps=[]
		handles_in=[]
		handles_out=[]
		tilts=[]

		for cs in curve.splines:

			if (cs.type=="BEZIER"):
				for s in cs.bezier_points:
					points.append(s.co[0])
					points.append(s.co[1])
					points.append(s.co[2])


					handles_in.append(s.handle_left[0])
					handles_in.append(s.handle_left[1])
					handles_in.append(s.handle_left[2])

					handles_out.append(s.handle_right[0])
					handles_out.append(s.handle_right[1])
					handles_out.append(s.handle_right[2])


					tilts.append(s.tilt)
					interps.append("BEZIER")
			else:

				for s in cs.points:
					points.append(s.co[0])
					points.append(s.co[1])
					points.append(s.co[2])
					handles_in.append(s.co[0])
					handles_in.append(s.co[1])
					handles_in.append(s.co[2])
					handles_out.append(s.co[0])
					handles_out.append(s.co[1])
					handles_out.append(s.co[2])
					tilts.append(s.tilt)
					interps.append("LINEAR")




		self.writel(S_GEOM,3,'<source id="'+splineid+'-positions">')
		position_values=""
		for x in points:
			position_values+=" "+str(x)
		self.writel(S_GEOM,4,'<float_array id="'+splineid+'-positions-array" count="'+str(len(points))+'">'+position_values+'</float_array>')
		self.writel(S_GEOM,4,'<technique_common>')
		self.writel(S_GEOM,4,'<accessor source="#'+splineid+'-positions-array" count="'+str(len(points)/3)+'" stride="3">')
		self.writel(S_GEOM,5,'<param name="X" type="float"/>')
		self.writel(S_GEOM,5,'<param name="Y" type="float"/>')
		self.writel(S_GEOM,5,'<param name="Z" type="float"/>')
		self.writel(S_GEOM,4,'</accessor>')
		self.writel(S_GEOM,3,'</source>')

		self.writel(S_GEOM,3,'<source id="'+splineid+'-intangents">')
		intangent_values=""
		for x in handles_in:
			intangent_values+=" "+str(x)
		self.writel(S_GEOM,4,'<float_array id="'+splineid+'-intangents-array" count="'+str(len(points))+'">'+intangent_values+'</float_array>')
		self.writel(S_GEOM,4,'<technique_common>')
		self.writel(S_GEOM,4,'<accessor source="#'+splineid+'-intangents-array" count="'+str(len(points)/3)+'" stride="3">')
		self.writel(S_GEOM,5,'<param name="X" type="float"/>')
		self.writel(S_GEOM,5,'<param name="Y" type="float"/>')
		self.writel(S_GEOM,5,'<param name="Z" type="float"/>')
		self.writel(S_GEOM,4,'</accessor>')
		self.writel(S_GEOM,3,'</source>')

		self.writel(S_GEOM,3,'<source id="'+splineid+'-outtangents">')
		outtangent_values=""
		for x in handles_out:
			outtangent_values+=" "+str(x)
		self.writel(S_GEOM,4,'<float_array id="'+splineid+'-outtangents-array" count="'+str(len(points))+'">'+outtangent_values+'</float_array>')
		self.writel(S_GEOM,4,'<technique_common>')
		self.writel(S_GEOM,4,'<accessor source="#'+splineid+'-outtangents-array" count="'+str(len(points)/3)+'" stride="3">')
		self.writel(S_GEOM,5,'<param name="X" type="float"/>')
		self.writel(S_GEOM,5,'<param name="Y" type="float"/>')
		self.writel(S_GEOM,5,'<param name="Z" type="float"/>')
		self.writel(S_GEOM,4,'</accessor>')
		self.writel(S_GEOM,3,'</source>')

		self.writel(S_GEOM,3,'<source id="'+splineid+'-interpolations">')
		interpolation_values=""
		for x in interps:
			interpolation_values+=" "+x
		self.writel(S_GEOM,4,'<Name_array id="'+splineid+'-interpolations-array" count="'+str(len(interps))+'">'+interpolation_values+'</Name_array>')
		self.writel(S_GEOM,4,'<technique_common>')
		self.writel(S_GEOM,4,'<accessor source="#'+splineid+'-interpolations-array" count="'+str(len(interps))+'" stride="1">')
		self.writel(S_GEOM,5,'<param name="INTERPOLATION" type="name"/>')
		self.writel(S_GEOM,4,'</accessor>')
		self.writel(S_GEOM,3,'</source>')


		self.writel(S_GEOM,3,'<source id="'+splineid+'-tilts">')
		tilt_values=""
		for x in tilts:
			tilt_values+=" "+str(x)
		self.writel(S_GEOM,4,'<float_array id="'+splineid+'-tilts-array" count="'+str(len(tilts))+'">'+tilt_values+'</float_array>')
		self.writel(S_GEOM,4,'<technique_common>')
		self.writel(S_GEOM,4,'<accessor source="#'+splineid+'-tilts-array" count="'+str(len(tilts))+'" stride="1">')
		self.writel(S_GEOM,5,'<param name="TILT" type="float"/>')
		self.writel(S_GEOM,4,'</accessor>')
		self.writel(S_GEOM,3,'</source>')

		self.writel(S_GEOM,3,'<control_vertices>')
		self.writel(S_GEOM,4,'<input semantic="POSITION" source="#'+splineid+'-positions"/>')
		self.writel(S_GEOM,4,'<input semantic="IN_TANGENT" source="#'+splineid+'-intangents"/>')
		self.writel(S_GEOM,4,'<input semantic="OUT_TANGENT" source="#'+splineid+'-outtangents"/>')
		self.writel(S_GEOM,4,'<input semantic="INTERPOLATION" source="#'+splineid+'-interpolations"/>')
		self.writel(S_GEOM,4,'<input semantic="TILT" source="#'+splineid+'-tilts"/>')
		self.writel(S_GEOM,3,'</control_vertices>')


		self.writel(S_GEOM,2,'</spline>')
		self.writel(S_GEOM,1,'</geometry>')

		return splineid

	def export_curve_node(self,node,il):

		if (node.data==None):
			return
		curveid = self.export_curve(node.data)

		self.writel(S_NODES,il,'<instance_geometry url="#'+curveid+'">')
		self.writel(S_NODES,il,'</instance_geometry>')



	def export_node(self,node,il):
		if (not node in self.valid_nodes):
			return
		bpy.context.scene.objects.active = node

		#Parse Lamp data and custom properties into a Navlight node. - DL
		if (node.type=="LAMP"):
			lamp = node.data
			lampColorR = str(lamp.color.r)
			lampColorG = str(lamp.color.g)
			lampColorB = str(lamp.color.b)
			lampSize = str(lamp.energy)
			lampDist = str(lamp.distance)
			lampPhase = str(lamp["Phase"])
			lampFreq = str(lamp["Freq"])
			lampType = lamp["Type"]
					  
			nodeName = node.name+'_Type['+lampType+']_Sz['+lampSize+']_Ph['+lampPhase+']_Fr['+lampFreq+']_Col['+lampColorR+','+lampColorG+','+lampColorB+']_Dist['+lampDist+']'
			if hasattr(lamp,'["Flags"]'):
				lampFlags = lamp["Flags"]	
				nodeName = nodeName+'_Flags['+lampFlags+']'
		
		#Check if node is a Dock Path node and parse and append dock path data into node name
		elif ("DOCK[" in node.name):
			shipFam = node["Fam"]
			nodeName = node.name+'_Fam['+shipFam+']'
			if hasattr(node,'["Link"]'):
				dockLink = node["Link"]
				nodeName = nodeName+'_Link['+dockLink+']'
			if hasattr(node,'["Flags"]'):
				dockFlags = node["Flags"]
				nodeName = nodeName+'_Flags['+dockFlags+']'
			if hasattr(node,'["MAD"]'):
				dockMAD = str(node["MAD"])
				nodeName = nodeName+'_MAD['+dockMAD+']'
		#Check if node is a dock Seg node and parse and append segue data into node name
		elif ("SEG[" in node.name):
			#Remove the .00x in the event this isn't the first SEG node with this index
			nodeName = node.name[0]+node.name[1]+node.name[2]+node.name[3]+node.name[4]+node.name[5]
			segTol = str(int(node.empty_draw_size))
			segSpeed = str(node["Speed"])
			nodeName = nodeName+'_Tol['+segTol+']_Spd['+segSpeed+']'
			if hasattr(node,'["Flags"]'):
				nodeFlags = node["Flags"]
				nodeName = nodeName+'_Flags['+nodeFlags+']'
		else:
			nodeName = node.name

		

		self.writel(S_NODES,il,'<node name="'+nodeName+'" id="'+nodeName+'" sid="'+nodeName+'">')
		il+=1

		#self.writel(S_NODES,il,'<matrix sid="transform">'+strmtx(node.matrix_local)+'</matrix>')
		#Pull XYZ coordinates relative to parent object - DL
		nodeXCoord=node.matrix_local.to_translation()[0]
		nodeYCoord=node.matrix_local.to_translation()[1]
		nodeZCoord=node.matrix_local.to_translation()[2]
		#pull XYZ rotation relative to parent object
		nodeXrot=str(math.degrees(node.matrix_local.to_euler()[0]))
		nodeYrot=str(math.degrees(node.matrix_local.to_euler()[1]))
		nodeZrot=str(math.degrees(node.matrix_local.to_euler()[2]))
		#Write XYZ coordinates and rotations to the XML following the format of the 3DS Max DAE output
		self.writel(S_NODES,il,'<translate sid="translate">'+str(nodeXCoord)+' '+str(nodeYCoord)+' '+str(nodeZCoord)+'</translate>')
		self.writel(S_NODES,il,'<rotate sid="rotateZ">0 0 1 '+nodeZrot+'</rotate>')
		self.writel(S_NODES,il,'<rotate sid="rotateY">0 1 0 '+nodeYrot+'</rotate>')
		self.writel(S_NODES,il,'<rotate sid="rotateX">1 0 0 '+nodeXrot+'</rotate>')
		print("NODE TYPE: "+node.type+" NAME: "+node.name)
		if (node.type=="MESH"):
			self.export_mesh_node(node,il)
		elif (node.type=="CURVE"):
			self.export_curve_node(node,il)
		elif (node.type=="ARMATURE"):
			self.export_armature_node(node,il)
		elif (node.type=="CAMERA"):
			self.export_camera_node(node,il)
		#elif (node.type=="LAMP"):
		#	self.export_lamp_node(node,il)

		for x in node.children:
			self.export_node(x,il)

		il-=1
		self.writel(S_NODES,il,'</node>')

	def is_node_valid(self,node):
		if (not node.type in self.config["object_types"]):
			return False
		if (self.config["use_active_layers"]):
			valid=False
			print("NAME: "+node.name)
			for i in range(20):
				if (node.layers[i] and  self.scene.layers[i]):
					valid=True
					break
			if (not valid):
				return False

		if (self.config["use_export_selected"] and not node.select):
			return False

		return True


	def export_scene(self):


		self.writel(S_NODES,0,'<library_visual_scenes>')
		self.writel(S_NODES,1,'<visual_scene id="'+self.scene_name+'" name="scene">')

		#validate nodes
		for obj in self.scene.objects:
			if (obj in self.valid_nodes):
				continue
			if (self.is_node_valid(obj)):
				n = obj
				while (n!=None):
					if (not n in self.valid_nodes):
						self.valid_nodes.append(n)
					n=n.parent



		for obj in self.scene.objects:
			if (obj in self.valid_nodes and obj.parent==None):
				self.export_node(obj,2)

		self.writel(S_NODES,1,'</visual_scene>')
		self.writel(S_NODES,0,'</library_visual_scenes>')

	def export_asset(self):


		self.writel(S_ASSET,0,'<asset>')
		# Why is this time stuff mandatory?, no one could care less...
		self.writel(S_ASSET,1,'<contributor>')
		self.writel(S_ASSET,2,'<author> Anonymous </author>') #Who made Collada, the FBI ?
		self.writel(S_ASSET,2,'<authoring_tool> Collada Exporter for Blender 2.6+, by Juan Linietsky (juan@codenix.com) </authoring_tool>') #Who made Collada, the FBI ?
		self.writel(S_ASSET,1,'</contributor>')
		self.writel(S_ASSET,1,'<created>'+time.strftime("%Y-%m-%dT%H:%M:%SZ     ")+'</created>')
		self.writel(S_ASSET,1,'<modified>'+time.strftime("%Y-%m-%dT%H:%M:%SZ")+'</modified>')
		self.writel(S_ASSET,1,'<unit meter="1.0" name="meter"/>')
		self.writel(S_ASSET,1,'<up_axis>Z_UP</up_axis>')
		self.writel(S_ASSET,0,'</asset>')


	def export_animation_transform_channel(self,target,keys,matrices=True):

		frame_total=len(keys)
		#Following the formatting of the 3DS Max DAE output, the animation id should be the Parent object name with -anim suffix - DL
		#anim_id=self.new_id("anim")
		anim_id=target
		self.writel(S_ANIM,1,'<animation id="'+anim_id+'-anim" name="'+anim_id+'"></animation>')
		source_frames = ""
		source_Xtransforms = ""
		source_Ytransforms = ""
		source_Ztransforms = ""
		source_Xrotations = ""
		source_Yrotations = ""
		source_Zrotations = ""
		source_interps = ""

		for k in keys:
			source_frames += " "+str(k[0])
			if (matrices):
				#source_transforms += " "+strmtx(k[1])
				source_Xtransforms += " "+str(k[1].to_translation()[0])
				source_Ytransforms += " "+str(k[1].to_translation()[1])
				source_Ztransforms += " "+str(k[1].to_translation()[2])
				source_Xrotations += " "+str(math.degrees(k[1].to_euler()[0]))
				source_Yrotations += " "+str(math.degrees(k[1].to_euler()[1]))
				source_Zrotations += " "+str(math.degrees(k[1].to_euler()[2]))
			else:
				source_transforms += " "+str(k[1])

			source_interps +=" LINEAR"

		#X Transform
		# Time Source
		self.writel(S_ANIM,1,'<animation>')
		self.writel(S_ANIM,2,'<source id="'+anim_id+'-translate.X-input">')
		self.writel(S_ANIM,3,'<float_array id="'+anim_id+'-translate.X-input-array" count="'+str(frame_total)+'">'+source_frames+'</float_array>')
		self.writel(S_ANIM,3,'<technique_common>')
		self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-translate.X-input-array" count="'+str(frame_total)+'" stride="1">')
		self.writel(S_ANIM,5,'<param type="float"></param>')
		self.writel(S_ANIM,4,'</accessor>')
		self.writel(S_ANIM,3,'</technique_common>')
		self.writel(S_ANIM,2,'</source>')

		if (matrices):
			# Transform Source
			self.writel(S_ANIM,2,'<source id="'+anim_id+'-translate.X-output">')
			self.writel(S_ANIM,3,'<float_array id="'+anim_id+'-translate.X-output-array" count="'+str(frame_total)+'">'+source_Xtransforms+'</float_array>')
			self.writel(S_ANIM,3,'<technique_common>')
			self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-translate.X-output-array" count="'+str(frame_total)+'" stride="1">')
			self.writel(S_ANIM,5,'<param type="float"></param>')
			self.writel(S_ANIM,4,'</accessor>')
			self.writel(S_ANIM,3,'</technique_common>')
			self.writel(S_ANIM,2,'</source>')
		

		# Interpolation Source
		self.writel(S_ANIM,2,'<source id="'+anim_id+'-translate.X-interpolation">')
		self.writel(S_ANIM,3,'<Name_array id="'+anim_id+'-translate.X-interpolation-array" count="'+str(frame_total)+'">'+source_interps+'</Name_array>')
		self.writel(S_ANIM,3,'<technique_common>')
		self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-translate.X-interpolation-array" count="'+str(frame_total)+'" stride="1">')
		self.writel(S_ANIM,5,'<param type="name"/>')
		self.writel(S_ANIM,4,'</accessor>')
		self.writel(S_ANIM,3,'</technique_common>')
		self.writel(S_ANIM,2,'</source>')

		#In Tangent - For Bezier Interpolation - Not Supported - DL

		#Out Tangent - For Bezier Inerpolation - Not Supported - DL

		self.writel(S_ANIM,2,'<sampler id="'+anim_id+'-translate.X">')
		self.writel(S_ANIM,3,'<input semantic="INPUT" source="#'+anim_id+'-translate.X-input"/>')
		self.writel(S_ANIM,3,'<input semantic="OUTPUT" source="#'+anim_id+'-translate.X-output"/>')
		self.writel(S_ANIM,3,'<input semantic="INTERPOLATION" source="#'+anim_id+'-translate.X-interpolation"/>')
		self.writel(S_ANIM,2,'</sampler>')
		if (matrices):
			self.writel(S_ANIM,2,'<channel source="#'+anim_id+'-translate.X" target="'+target+'/translate.X"></channel>')
		self.writel(S_ANIM,1,'</animation>')

		#Y Transform
		# Time Source
		self.writel(S_ANIM,1,'<animation>')
		self.writel(S_ANIM,2,'<source id="'+anim_id+'-translate.Y-input">')
		self.writel(S_ANIM,3,'<float_array id="'+anim_id+'-translate.Y-input-array" count="'+str(frame_total)+'">'+source_frames+'</float_array>')
		self.writel(S_ANIM,3,'<technique_common>')
		self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-translate.Y-input-array" count="'+str(frame_total)+'" stride="1">')
		self.writel(S_ANIM,5,'<param type="float"></param>')
		self.writel(S_ANIM,4,'</accessor>')
		self.writel(S_ANIM,3,'</technique_common>')
		self.writel(S_ANIM,2,'</source>')

		if (matrices):
			# Transform Source
			self.writel(S_ANIM,2,'<source id="'+anim_id+'-translate.Y-output">')
			self.writel(S_ANIM,3,'<float_array id="'+anim_id+'-translate.Y-output-array" count="'+str(frame_total)+'">'+source_Ytransforms+'</float_array>')
			self.writel(S_ANIM,3,'<technique_common>')
			self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-translate.Y-output-array" count="'+str(frame_total)+'" stride="1">')
			self.writel(S_ANIM,5,'<param type="float"></param>')
			self.writel(S_ANIM,4,'</accessor>')
			self.writel(S_ANIM,3,'</technique_common>')
			self.writel(S_ANIM,2,'</source>')
		
		# Interpolation Source
		self.writel(S_ANIM,2,'<source id="'+anim_id+'-translate.Y-interpolation">')
		self.writel(S_ANIM,3,'<Name_array id="'+anim_id+'-translate.Y-interpolation-array" count="'+str(frame_total)+'">'+source_interps+'</Name_array>')
		self.writel(S_ANIM,3,'<technique_common>')
		self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-translate.Y-interpolation-array" count="'+str(frame_total)+'" stride="1">')
		self.writel(S_ANIM,5,'<param type="name"/>')
		self.writel(S_ANIM,4,'</accessor>')
		self.writel(S_ANIM,3,'</technique_common>')
		self.writel(S_ANIM,2,'</source>')

		#In Tangent - For Bezier Interpolation - Not Supported - DL

		#Out Tangent - For Bezier Inerpolation - Not Supported - DL

		self.writel(S_ANIM,2,'<sampler id="'+anim_id+'-translate.Y">')
		self.writel(S_ANIM,3,'<input semantic="INPUT" source="#'+anim_id+'-translate.Y-input"/>')
		self.writel(S_ANIM,3,'<input semantic="OUTPUT" source="#'+anim_id+'-translate.Y-output"/>')
		self.writel(S_ANIM,3,'<input semantic="INTERPOLATION" source="#'+anim_id+'-translate.Y-interpolation"/>')
		self.writel(S_ANIM,2,'</sampler>')
		if (matrices):
			self.writel(S_ANIM,2,'<channel source="#'+anim_id+'-translate.Y" target="'+target+'/translate.Y"></channel>')
		self.writel(S_ANIM,1,'</animation>')

		#Z Transform
		# Time Source
		self.writel(S_ANIM,1,'<animation>')
		self.writel(S_ANIM,2,'<source id="'+anim_id+'-translate.Z-input">')
		self.writel(S_ANIM,3,'<float_array id="'+anim_id+'-translate.Z-input-array" count="'+str(frame_total)+'">'+source_frames+'</float_array>')
		self.writel(S_ANIM,3,'<technique_common>')
		self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-translate.Z-input-array" count="'+str(frame_total)+'" stride="1">')
		self.writel(S_ANIM,5,'<param type="float"></param>')
		self.writel(S_ANIM,4,'</accessor>')
		self.writel(S_ANIM,3,'</technique_common>')
		self.writel(S_ANIM,2,'</source>')

		if (matrices):
			# Transform Source
			self.writel(S_ANIM,2,'<source id="'+anim_id+'-translate.Z-output">')
			self.writel(S_ANIM,3,'<float_array id="'+anim_id+'-translate.Z-output-array" count="'+str(frame_total)+'">'+source_Ztransforms+'</float_array>')
			self.writel(S_ANIM,3,'<technique_common>')
			self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-translate.Z-output-array" count="'+str(frame_total)+'" stride="1">')
			self.writel(S_ANIM,5,'<param type="float"></param>')
			self.writel(S_ANIM,4,'</accessor>')
			self.writel(S_ANIM,3,'</technique_common>')
			self.writel(S_ANIM,2,'</source>')
		
		# Interpolation Source
		self.writel(S_ANIM,2,'<source id="'+anim_id+'-translate.Z-interpolation">')
		self.writel(S_ANIM,3,'<Name_array id="'+anim_id+'-translate.Z-interpolation-array" count="'+str(frame_total)+'">'+source_interps+'</Name_array>')
		self.writel(S_ANIM,3,'<technique_common>')
		self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-translate.Z-interpolation-array" count="'+str(frame_total)+'" stride="1">')
		self.writel(S_ANIM,5,'<param type="name"/>')
		self.writel(S_ANIM,4,'</accessor>')
		self.writel(S_ANIM,3,'</technique_common>')
		self.writel(S_ANIM,2,'</source>')

		#In Tangent - For Bezier Interpolation - Not Supported - DL

		#Out Tangent - For Bezier Inerpolation - Not Supported - DL

		self.writel(S_ANIM,2,'<sampler id="'+anim_id+'-translate.Z">')
		self.writel(S_ANIM,3,'<input semantic="INPUT" source="#'+anim_id+'-translate.Z-input"/>')
		self.writel(S_ANIM,3,'<input semantic="OUTPUT" source="#'+anim_id+'-translate.Z-output"/>')
		self.writel(S_ANIM,3,'<input semantic="INTERPOLATION" source="#'+anim_id+'-translate.Z-interpolation"/>')
		self.writel(S_ANIM,2,'</sampler>')
		if (matrices):
			self.writel(S_ANIM,2,'<channel source="#'+anim_id+'-translate.Z" target="'+target+'/translate.Z"></channel>')
		
		self.writel(S_ANIM,1,'</animation>')

		#X Rotation
		# Time Source
		self.writel(S_ANIM,1,'<animation>')
		self.writel(S_ANIM,2,'<source id="'+anim_id+'-rotateX.ANGLE-input">')
		self.writel(S_ANIM,3,'<float_array id="'+anim_id+'-rotateX.ANGLE-input-array" count="'+str(frame_total)+'">'+source_frames+'</float_array>')
		self.writel(S_ANIM,3,'<technique_common>')
		self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-rotateX.ANGLE-input-array" count="'+str(frame_total)+'" stride="1">')
		self.writel(S_ANIM,5,'<param type="float"></param>')
		self.writel(S_ANIM,4,'</accessor>')
		self.writel(S_ANIM,3,'</technique_common>')
		self.writel(S_ANIM,2,'</source>')

		if (matrices):
			# Transform Source
			self.writel(S_ANIM,2,'<source id="'+anim_id+'-rotateX.ANGLE-output">')
			self.writel(S_ANIM,3,'<float_array id="'+anim_id+'-rotateX.ANGLE-output-array" count="'+str(frame_total)+'">'+source_Xrotations+'</float_array>')
			self.writel(S_ANIM,3,'<technique_common>')
			self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-rotateX.ANGLE-output-array" count="'+str(frame_total)+'" stride="1">')
			self.writel(S_ANIM,5,'<param type="float"></param>')
			self.writel(S_ANIM,4,'</accessor>')
			self.writel(S_ANIM,3,'</technique_common>')
			self.writel(S_ANIM,2,'</source>')
		
		# Interpolation Source
		self.writel(S_ANIM,2,'<source id="'+anim_id+'-rotateX.ANGLE-interpolation">')
		self.writel(S_ANIM,3,'<Name_array id="'+anim_id+'-rotateX.ANGLE-interpolation-array" count="'+str(frame_total)+'">'+source_interps+'</Name_array>')
		self.writel(S_ANIM,3,'<technique_common>')
		self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-rotateX.ANGLE-interpolation-array" count="'+str(frame_total)+'" stride="1">')
		self.writel(S_ANIM,5,'<param type="name"/>')
		self.writel(S_ANIM,4,'</accessor>')
		self.writel(S_ANIM,3,'</technique_common>')
		self.writel(S_ANIM,2,'</source>')

		#In Tangent - For Bezier Interpolation - Not Supported - DL

		#Out Tangent - For Bezier Inerpolation - Not Supported - DL

		self.writel(S_ANIM,2,'<sampler id="'+anim_id+'-rotateX.ANGLE">')
		self.writel(S_ANIM,3,'<input semantic="INPUT" source="#'+anim_id+'-rotateX.ANGLE-input"/>')
		self.writel(S_ANIM,3,'<input semantic="OUTPUT" source="#'+anim_id+'-rotateX.ANGLE-output"/>')
		self.writel(S_ANIM,3,'<input semantic="INTERPOLATION" source="#'+anim_id+'-rotateX.ANGLE-interpolation"/>')
		self.writel(S_ANIM,2,'</sampler>')
		if (matrices):
			self.writel(S_ANIM,2,'<channel source="#'+anim_id+'-rotateX.ANGLE" target="'+target+'/rotateX.ANGLE"></channel>')
		self.writel(S_ANIM,1,'</animation>')

		#Y Rotation
		# Time Source
		self.writel(S_ANIM,1,'<animation>')
		self.writel(S_ANIM,2,'<source id="'+anim_id+'-rotateY.ANGLE-input">')
		self.writel(S_ANIM,3,'<float_array id="'+anim_id+'-rotateY.ANGLE-input-array" count="'+str(frame_total)+'">'+source_frames+'</float_array>')
		self.writel(S_ANIM,3,'<technique_common>')
		self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-rotateY.ANGLE-input-array" count="'+str(frame_total)+'" stride="1">')
		self.writel(S_ANIM,5,'<param type="float"></param>')
		self.writel(S_ANIM,4,'</accessor>')
		self.writel(S_ANIM,3,'</technique_common>')
		self.writel(S_ANIM,2,'</source>')

		if (matrices):
			# Transform Source
			self.writel(S_ANIM,2,'<source id="'+anim_id+'-rotateY.ANGLE-output">')
			self.writel(S_ANIM,3,'<float_array id="'+anim_id+'-rotateY.ANGLE-output-array" count="'+str(frame_total)+'">'+source_Yrotations+'</float_array>')
			self.writel(S_ANIM,3,'<technique_common>')
			self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-rotateY.ANGLE-output-array" count="'+str(frame_total)+'" stride="1">')
			self.writel(S_ANIM,5,'<param type="float"></param>')
			self.writel(S_ANIM,4,'</accessor>')
			self.writel(S_ANIM,3,'</technique_common>')
			self.writel(S_ANIM,2,'</source>')
		
		# Interpolation Source
		self.writel(S_ANIM,2,'<source id="'+anim_id+'-rotateY.ANGLE-interpolation">')
		self.writel(S_ANIM,3,'<Name_array id="'+anim_id+'-rotateY.ANGLE-interpolation-array" count="'+str(frame_total)+'">'+source_interps+'</Name_array>')
		self.writel(S_ANIM,3,'<technique_common>')
		self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-rotateY.ANGLE-interpolation-array" count="'+str(frame_total)+'" stride="1">')
		self.writel(S_ANIM,5,'<param type="name"/>')
		self.writel(S_ANIM,4,'</accessor>')
		self.writel(S_ANIM,3,'</technique_common>')
		self.writel(S_ANIM,2,'</source>')

		#In Tangent - For Bezier Interpolation - Not Supported - DL

		#Out Tangent - For Bezier Interpolation - Not Supported - DL

		self.writel(S_ANIM,2,'<sampler id="'+anim_id+'-rotateY.ANGLE">')
		self.writel(S_ANIM,3,'<input semantic="INPUT" source="#'+anim_id+'-rotateY.ANGLE-input"/>')
		self.writel(S_ANIM,3,'<input semantic="OUTPUT" source="#'+anim_id+'-rotateY.ANGLE-output"/>')
		self.writel(S_ANIM,3,'<input semantic="INTERPOLATION" source="#'+anim_id+'-rotateY.ANGLE-interpolation"/>')
		self.writel(S_ANIM,2,'</sampler>')
		if (matrices):
			self.writel(S_ANIM,2,'<channel source="#'+anim_id+'-rotateY.ANGLE" target="'+target+'/rotateY.ANGLE"></channel>')
		self.writel(S_ANIM,1,'</animation>')

		#Z Rotation
		# Time Source
		self.writel(S_ANIM,1,'<animation>')
		self.writel(S_ANIM,2,'<source id="'+anim_id+'-rotateZ.ANGLE-input">')
		self.writel(S_ANIM,3,'<float_array id="'+anim_id+'-rotateZ.ANGLE-input-array" count="'+str(frame_total)+'">'+source_frames+'</float_array>')
		self.writel(S_ANIM,3,'<technique_common>')
		self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-rotateZ.ANGLE-input-array" count="'+str(frame_total)+'" stride="1">')
		self.writel(S_ANIM,5,'<param type="float"></param>')
		self.writel(S_ANIM,4,'</accessor>')
		self.writel(S_ANIM,3,'</technique_common>')
		self.writel(S_ANIM,2,'</source>')

		if (matrices):
			# Transform Source
			self.writel(S_ANIM,2,'<source id="'+anim_id+'-rotateZ.ANGLE-output">')
			self.writel(S_ANIM,3,'<float_array id="'+anim_id+'-rotateZ.ANGLE-output-array" count="'+str(frame_total)+'">'+source_Zrotations+'</float_array>')
			self.writel(S_ANIM,3,'<technique_common>')
			self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-rotateZ.ANGLE-output-array" count="'+str(frame_total)+'" stride="1">')
			self.writel(S_ANIM,5,'<param type="float"></param>')
			self.writel(S_ANIM,4,'</accessor>')
			self.writel(S_ANIM,3,'</technique_common>')
			self.writel(S_ANIM,2,'</source>')
		
		# Interpolation Source
		self.writel(S_ANIM,2,'<source id="'+anim_id+'-rotateZ.ANGLE-interpolation">')
		self.writel(S_ANIM,3,'<Name_array id="'+anim_id+'-rotateZ.ANGLE-interpolation-array" count="'+str(frame_total)+'">'+source_interps+'</Name_array>')
		self.writel(S_ANIM,3,'<technique_common>')
		self.writel(S_ANIM,4,'<accessor source="#'+anim_id+'-rotateZ.ANGLE-interpolation-array" count="'+str(frame_total)+'" stride="1">')
		self.writel(S_ANIM,5,'<param type="name"/>')
		self.writel(S_ANIM,4,'</accessor>')
		self.writel(S_ANIM,3,'</technique_common>')
		self.writel(S_ANIM,2,'</source>')

		#In Tangent - For Bezier Interpolation - Not Supported - DL

		#Out Tangent - For Bezier Inerpolation - Not Supported - DL

		self.writel(S_ANIM,2,'<sampler id="'+anim_id+'-rotateZ.ANGLE">')
		self.writel(S_ANIM,3,'<input semantic="INPUT" source="#'+anim_id+'-rotateZ.ANGLE-input"/>')
		self.writel(S_ANIM,3,'<input semantic="OUTPUT" source="#'+anim_id+'-rotateZ.ANGLE-output"/>')
		self.writel(S_ANIM,3,'<input semantic="INTERPOLATION" source="#'+anim_id+'-rotateZ.ANGLE-interpolation"/>')
		self.writel(S_ANIM,2,'</sampler>')
		if (matrices):
			self.writel(S_ANIM,2,'<channel source="#'+anim_id+'-rotateZ.ANGLE" target="'+target+'/rotateZ.ANGLE"></channel>')
		self.writel(S_ANIM,1,'</animation>')

		return [anim_id]


	def export_animation(self,start,end,allowed=None):

		#Blender -> Collada frames needs a little work
		#Collada starts from 0, blender usually from 1
		#The last frame must be included also

		frame_orig = self.scene.frame_current

		frame_len = 1.0 / self.scene.render.fps
		frame_total = end - start + 1
		frame_sub = 0
		if (start>0):
			frame_sub=start*frame_len

		tcn = []
		xform_cache={}
		blend_cache={}
		# Change frames first, export objects last
		# This improves performance enormously

		print("anim from: "+str(start)+" to "+str(end)+" allowed: "+str(allowed))

		for node in self.scene.objects:
			name = None
			if node.animation_data is not None and node.animation_data.action is not None:				
				name = node.name
				if (not (name in xform_cache)):
					xform_cache[name]=[]
				startFrame = node.animation_data.action.frame_range[0]
				endFrame = node.animation_data.action.frame_range[1]
				self.scene.frame_set(startFrame)
				#xform_cache[name].append( (self.scene.frame_current, node.matrix_local.copy()) )
				while self.scene.frame_current <= endFrame: 
					xform_cache[name].append( (self.scene.frame_current/self.scene.render.fps, node.matrix_local.copy()) )
					#bpy.ops.screen.keyframe_jump()
					self.scene.frame_set(self.scene.frame_current + 1)
					if self.scene.frame_current == endFrame:
						break
		
		### This whole section is bullshit and dumb
		"""for t in range(start,end+1):
			self.scene.frame_set(t)
			key = t * frame_len - frame_sub
			print("Export Anim Frame "+str(t)+"/"+str(self.scene.frame_end+1))

			for node in self.scene.objects:

				if (not node in self.valid_nodes):
					continue
				if (allowed!=None and not (node in allowed)):
					if (node.type=="MESH" and node.data!=None and (node in self.armature_for_morph) and (self.armature_for_morph[node] in allowed)):
						pass #all good you pass with flying colors for morphs inside of action
					else:
						#print("fail "+str((node in self.armature_for_morph)))
						continue
				if (node.type=="MESH" and node.data!=None and node.data.shape_keys!=None and (node.data in self.mesh_cache) and len(node.data.shape_keys.key_blocks)):
					target = self.mesh_cache[node.data]["morph_id"]
					for i in range(len(node.data.shape_keys.key_blocks)):

						if (i==0):
							continue

						name=target+"-morph-weights("+str(i-1)+")"
						if (not (name in blend_cache)):
							blend_cache[name]=[]

						blend_cache[name].append( (key,node.data.shape_keys.key_blocks[i].value) )


				if (node.type=="MESH" and node.parent and node.parent.type=="ARMATURE"):

					continue #In Collada, nodes that have skin modifier must not export animation, animate the skin instead.

				if (len(node.constraints)>0 or node.animation_data!=None):
					#If the node has constraints, or animation data, then export a sampled animation track
					name=self.validate_id(node.name)
					if (not (name in xform_cache)):
						xform_cache[name]=[]

					mtx = node.matrix_local.copy()
					#if (node.parent):
					#	mtx = node.parent.matrix_local.inverted() * mtx

					xform_cache[name].append( (key,mtx) )

				if (node.type=="ARMATURE"):
					#All bones exported for now

					for bone in node.data.bones:

						bone_name=self.skeleton_info[node]["bone_ids"][bone]

						if (not (bone_name in xform_cache)):
							print("has bone: "+bone_name)
							xform_cache[bone_name]=[]

						posebone = node.pose.bones[bone.name]
						parent_posebone=None

						mtx = posebone.matrix.copy()
						if (bone.parent):
							parent_posebone=node.pose.bones[bone.parent.name]
							parent_invisible=False

							for i in range(3):
								if (parent_posebone.scale[i]==0.0):
								    parent_invisible=True

							if (not parent_invisible):
								mtx = parent_posebone.matrix.inverted() * mtx


						xform_cache[bone_name].append( (key,mtx) )

		self.scene.frame_set(frame_orig)"""

		#export animation xml
		for nid in xform_cache:
			tcn+=self.export_animation_transform_channel(nid,xform_cache[nid],True)
		for nid in blend_cache:
			tcn+=self.export_animation_transform_channel(nid,blend_cache[nid],False)

		return tcn

	def export_animations(self):
		tmp_mat = []												# workaround by ndee					
		for s in self.skeletons:									# workaround by ndee
			tmp_bone_mat = []										# workaround by ndee
			for bone in s.pose.bones:								# workaround by ndee
				tmp_bone_mat.append(Matrix(bone.matrix_basis))		# workaround by ndee
			tmp_mat.append([Matrix(s.matrix_local),tmp_bone_mat])	# workaround by ndee -> stores skeleton and bone transformations
			
		self.writel(S_ANIM,0,'<library_animations>')


		if (self.config["use_anim_action_all"] and len(self.skeletons)):

			cached_actions = {}

			for s in self.skeletons:
				if s.animation_data and s.animation_data.action:
					cached_actions[s] = s.animation_data.action.name


			self.writel(S_ANIM_CLIPS,0,'<library_animation_clips>')

			for x in bpy.data.actions[:]:
				if x.users==0 or x in self.action_constraints:
					continue
				if (self.config["use_anim_skip_noexp"] and x.name.endswith("-noexp")):
					continue

				bones=[]
				#find bones used
				for p in x.fcurves:
					dp = str(p.data_path)
					base = "pose.bones[\""
					if (dp.find(base)==0):
						dp=dp[len(base):]
						if (dp.find('"')!=-1):
							dp=dp[:dp.find('"')]
							if (not dp in bones):
								bones.append(dp)

				allowed_skeletons=[]
				for i,y in enumerate(self.skeletons):				# workaround by ndee
					if (y.animation_data):
						for z in y.pose.bones:
							if (z.bone.name in bones):
								if (not y in allowed_skeletons):
									allowed_skeletons.append(y)
						y.animation_data.action=x;
						
						y.matrix_local = tmp_mat[i][0]				# workaround by ndee -> resets the skeleton transformation. 
						for j,bone in enumerate(s.pose.bones):		# workaround by ndee
							bone.matrix_basis = Matrix()			# workaround by ndee -> resets the bone transformations. Important if bones in follwing actions miss keyframes
							

				print("allowed skeletons "+str(allowed_skeletons))

				print(str(x))

				tcn = self.export_animation(int(x.frame_range[0]),int(x.frame_range[1]+0.5),allowed_skeletons)
				framelen=(1.0/self.scene.render.fps)
				start = x.frame_range[0]*framelen
				end = x.frame_range[1]*framelen
				print("Export anim: "+x.name)
				self.writel(S_ANIM_CLIPS,1,'<animation_clip name="'+x.name+'" start="'+str(start)+'" end="'+str(end)+'">')
				for z in tcn:
					self.writel(S_ANIM_CLIPS,2,'<instance_animation url="#'+z+'"/>')
				self.writel(S_ANIM_CLIPS,1,'</animation_clip>')


			self.writel(S_ANIM_CLIPS,0,'</library_animation_clips>')

			for i,s in enumerate(self.skeletons):					# workaround by ndee
				if (s.animation_data==None):
					continue
				if s in cached_actions:
					s.animation_data.action = bpy.data.actions[cached_actions[s]]
				else:
					s.animation_data.action = None
					for j,bone in enumerate(s.pose.bones):			# workaround by ndee
						bone.matrix_basis = tmp_mat[i][1][j]		# workaround by ndee  -> resets the bone transformation to what they were before exporting.
		else:
			self.export_animation(self.scene.frame_start,self.scene.frame_end)
		
			
		
		self.writel(S_ANIM,0,'</library_animations>')

	def export(self):

		self.writel(S_GEOM,0,'<library_geometries>')
		self.writel(S_CONT,0,'<library_controllers>')
		self.writel(S_CAMS,0,'<library_cameras>')
		self.writel(S_LAMPS,0,'<library_lights>')
		self.writel(S_IMGS,0,'<library_images>')
		self.writel(S_MATS,0,'<library_materials>')
		self.writel(S_FX,0,'<library_effects>')


		self.skeletons=[]
		self.action_constraints=[]
		self.export_asset()
		self.export_scene()

		self.writel(S_GEOM,0,'</library_geometries>')

		#morphs always go before skin controllers
		if S_MORPH in self.sections:
			for l in self.sections[S_MORPH]:
				self.writel(S_CONT,0,l)
			del self.sections[S_MORPH]

		#morphs always go before skin controllers
		if S_SKIN in self.sections:
			for l in self.sections[S_SKIN]:
				self.writel(S_CONT,0,l)
			del self.sections[S_SKIN]

		self.writel(S_CONT,0,'</library_controllers>')
		self.writel(S_CAMS,0,'</library_cameras>')
		self.writel(S_LAMPS,0,'</library_lights>')
		self.writel(S_IMGS,0,'</library_images>')
		self.writel(S_MATS,0,'</library_materials>')
		self.writel(S_FX,0,'</library_effects>')

		if (self.config["use_anim"]):
		    self.export_animations()

		try:
			f = open(self.path,"wb")
		except:
			return False

		f.write(bytes('<?xml version="1.0" encoding="utf-8"?>\n',"UTF-8"))
		f.write(bytes('<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">\n',"UTF-8"))


		s=[]
		for x in self.sections.keys():
			s.append(x)
		s.sort()
		for x in s:
			for l in self.sections[x]:
				f.write(bytes(l+"\n","UTF-8"))

		f.write(bytes('<scene>\n',"UTF-8"))
		f.write(bytes('\t<instance_visual_scene url="#'+self.scene_name+'" />\n',"UTF-8"))
		f.write(bytes('</scene>\n',"UTF-8"))
		f.write(bytes('</COLLADA>\n',"UTF-8"))
		return True

	def __init__(self,path,kwargs):
		self.scene=bpy.context.scene
		self.last_id=0
		self.scene_name=self.new_id("scene")
		self.sections={}
		self.path=path
		self.mesh_cache={}
		self.curve_cache={}
		self.material_cache={}
		self.image_cache={}
		self.skeleton_info={}
		self.config=kwargs
		self.valid_nodes=[]
		self.armature_for_morph={}





def save(operator, context,
	filepath="",
	use_selection=False,
	**kwargs
	):

	exp = DaeExporter(filepath,kwargs)
	exp.export()

	return {'FINISHED'}  # so the script wont run after we have batch exported.


