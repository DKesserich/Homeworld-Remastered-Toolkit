# HWRM level file importer

import math # for pi
import bpy

pi = math.pi

def ImportLevel(levelFileName):

	# open the file and get the data
	levelFile = open(levelFileName,'r')

	print("===================================================================")
	print("===================================================================")
	print("===================================================================")

	print("Importing "+levelFileName+"...")

	for line in levelFile:
		#print (line)
		if "addPoint" in line: # parent points to a point parent for easy grouping?
			thisPointName = line.split("(")[1].split(",")[0].lstrip('"').rstrip('"').lstrip("'").rstrip("'")
			thisPointX = line.split("{")[1].split(",")[0]
			thisPointY = line.split("{")[1].split(",")[1]
			thisPointZ = line.split("{")[1].split(",")[2].rstrip("}")
			print("Creating point: " + thisPointName)
			this_jnt = bpy.data.objects.new("POINT_"+thisPointName, None)
			bpy.context.scene.objects.link(this_jnt)
			this_jnt.location.x = float(thisPointX)
			this_jnt.location.y = float(thisPointZ)
			this_jnt.location.z = float(thisPointY)
		elif "addSphere" in line:
			thisSphereName = line.split("(")[1].split(",")[0].lstrip('"').rstrip('"').lstrip("'").rstrip("'")
			thisSphereX = line.split("{")[1].split(",")[0]
			thisSphereY = line.split("{")[1].split(",")[1]
			thisSphereZ = line.split("{")[1].split(",")[2].rstrip("}")
			thisSphereR = line.split(",")[4].split(")")[0]
			print("Creating sphere: " + thisSphereName)
			this_jnt = bpy.data.objects.new("SPHERE_"+thisSphereName, None)
			bpy.context.scene.objects.link(this_jnt)
			this_jnt.location.x = float(thisSphereX)
			this_jnt.location.y = float(thisSphereZ)
			this_jnt.location.z = float(thisSphereY)
			this_jnt.empty_draw_type = "SPHERE"
			this_jnt.empty_draw_size = float(thisSphereR)
		elif "addPebble" in line:
			thisPebbleName = line.split("(")[1].split(",")[0].lstrip('"').rstrip('"').lstrip("'").rstrip("'")
			thisPebbleX = line.split("{")[1].split(",")[0]
			thisPebbleY = line.split("{")[1].split(",")[1]
			thisPebbleZ = line.split("{")[1].split(",")[2].rstrip("}")
			print("Creating pebble of type: " + thisPebbleName)
			this_jnt = bpy.data.objects.new("PEBBLE_"+thisPebbleName, None)
			bpy.context.scene.objects.link(this_jnt)
			this_jnt.location.x = float(thisPebbleX)
			this_jnt.location.y = float(thisPebbleZ)
			this_jnt.location.z = float(thisPebbleY)
			this_jnt.empty_draw_type = "SPHERE"
			this_jnt.empty_draw_size = 50.0
		elif "addAsteroid" in line:
			thisAsteroidName = line.split("(")[1].split(",")[0].lstrip('"').rstrip('"').lstrip("'").rstrip("'")
			thisAsteroidX = line.split("{")[1].split(",")[0]
			thisAsteroidY = line.split("{")[1].split(",")[1]
			thisAsteroidZ = line.split("{")[1].split(",")[2].rstrip("}")
			thisAsteroidRX = line.split("}")[1].split(",")[2]
			thisAsteroidRY = line.split("}")[1].split(",")[3]
			thisAsteroidRZ = line.split("}")[1].split(",")[4]
			print("Creating asteroid of type: " + thisAsteroidName)
			bpy.ops.mesh.primitive_ico_sphere_add(
				location=(float(thisAsteroidX),float(thisAsteroidZ),float(thisAsteroidY)),
				rotation=(float(thisAsteroidRX)*(pi/180.0),float(thisAsteroidRZ)*(pi/180.0),float(thisAsteroidRY)*(pi/180.0)),
				size=100)
			this_asteroid = bpy.context.active_object
			this_asteroid.name = thisAsteroidName
		elif "setWorldBoundsInner" in line:
			print("Creating world bounds")
			thisWorldR = line.split(",")[4]
			bpy.ops.mesh.primitive_circle_add(radius=float(thisWorldR), location=(0, 0, 0))
			
	levelFile.close()

	print("level file successfully imported!")

