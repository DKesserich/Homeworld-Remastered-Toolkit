import xml.etree.ElementTree as ET
import bpy
import math
import time
from mathutils import *

C = bpy.context
D = bpy.data

#############
#DAE Schemas#
#############

#Just defining all the DAE attributes here so the processing functions are more easily readable

#Utility Schemas
DAENode = "{http://www.collada.org/2005/11/COLLADASchema}node"
DAETranslation = "{http://www.collada.org/2005/11/COLLADASchema}translate"
DAEInit = "{http://www.collada.org/2005/11/COLLADASchema}init_from"
DAEInput = "{http://www.collada.org/2005/11/COLLADASchema}input"
DAEFloats = "{http://www.collada.org/2005/11/COLLADASchema}float_array"
DAESource = "{http://www.collada.org/2005/11/COLLADASchema}source"
DAEInstance = "{http://www.collada.org/2005/11/COLLADASchema}instance_geometry"

##Material Schemas
DAELibMaterials = "{http://www.collada.org/2005/11/COLLADASchema}library_materials"
DAEMaterials = "{http://www.collada.org/2005/11/COLLADASchema}material"
DAELibEffects = "{http://www.collada.org/2005/11/COLLADASchema}library_effects"
DAEfx = "{http://www.collada.org/2005/11/COLLADASchema}effect"
DAELibImages = "{http://www.collada.org/2005/11/COLLADASchema}library_images"
DAEimage = "{http://www.collada.org/2005/11/COLLADASchema}image"
DAETex = "{http://www.collada.org/2005/11/COLLADASchema}texture"
DAEProfile = "{http://www.collada.org/2005/11/COLLADASchema}profile_COMMON"
DAETechnique = "{http://www.collada.org/2005/11/COLLADASchema}technique"
DAEPhong = "{http://www.collada.org/2005/11/COLLADASchema}phong"

#Geometry Schemas
DAEGeo = "{http://www.collada.org/2005/11/COLLADASchema}geometry"
DAEMesh = "{http://www.collada.org/2005/11/COLLADASchema}mesh"
DAEVerts = "{http://www.collada.org/2005/11/COLLADASchema}vertices"
DAETris = "{http://www.collada.org/2005/11/COLLADASchema}triangles"
DAEp = "{http://www.collada.org/2005/11/COLLADASchema}p"

#Animation Schemas
DAELibAnims = "{http://www.collada.org/2005/11/COLLADASchema}library_animations"
DAEAnim = "{http://www.collada.org/2005/11/COLLADASchema}animation"
DAEChannel = "{http://www.collada.org/2005/11/COLLADASchema}channel"


def writeNodes(parentNode,objectName):
    thisNode = ET.SubElement(parentNode,'node',name=objectName,id=objectName,sid=objectName)
    thisPosition = ET.SubElement(thisNode,'translate',sid='translate')
    thisPosition.text = str(D.objects[objectName].location.x)+' '+str(D.objects[objectName].location.y)+' '+str(D.objects[objectName].location.z)
    rotZ = ET.SubElement(thisNode,'rotate',sid='rotateZ')
    rotZ.text = '0 0 1 '+str(math.degrees(D.objects[objectName].rotation_euler.z))
    rotY = ET.SubElement(thisNode,'rotate',sid='rotateY')
    rotY.text = '0 1 0 '+str(math.degrees(D.objects[objectName].rotation_euler.y))
    rotX = ET.SubElement(thisNode,'rotate',sid='rotateX')
    rotX.text = '1 0 0 '+str(math.degrees(D.objects[objectName].rotation_euler.x))
    if D.objects[objectName].type == 'MESH':
        geoInstance = ET.SubElement(thisNode,'instance_geometry',url='#'+objectName)
        bindMat = ET.SubElement(geoInstance,'bind_material')
        matTechnique = ET.SubElement(bindMat,'technique_common')
        for m in D.objects[objectName].material_slots:
            matInstance = ET.SubElement(matTechnique,'instance_material',symbol = m.name,target='#'+m.name)
    

#Set up Collada Header Stuff
root = ET.Element('COLLADA',version='1.4.1',xmlns = 'http://www.collada.org/2005/11/COLLADASchema')
asset = ET.SubElement(root,'asset')
contributorTag = ET.SubElement(asset,'contributor')
contribAuthor = ET.SubElement(contributorTag,'author')
contribAuthor.text = 'Anonymous'
contribTool = ET.SubElement(contributorTag,'authoring_tool')
contribTool.text = 'New Collada Exporter for Blender, by David Lejeune'
createdDate = ET.SubElement(asset,'created')
createdDate.text = time.ctime()
modifiedDate = ET.SubElement(asset,'modified')
modifiedDate.text = time.ctime()
units = ET.SubElement(asset,'unit',meter='1.0',name='meter')
upAxis = ET.SubElement(asset,'up_axis')
upAxis.text = 'Z_UP'

#Write the Library Visual Scenes Stuff
libScenes = ET.SubElement(root,'library_visual_scenes')
thisScene = ET.SubElement(libScenes,'visual_scene',id=C.scene.name+'-id',name=C.scene.name)
daeScene = ET.SubElement(root,'scene')
visScene = ET.SubElement(daeScene,'instance_visual_scene',url='#'+thisScene.attrib["id"])

for ob in D.objects:
    if ob.parent is None:
        writeNodes(thisScene,ob.name)
    else:
        for n in thisScene.findall('node'):
            if n.attrib['id'] == ob.parent.name:
                writeNodes(n,ob.name)
    
        

doc = ET.ElementTree(root)
doc.write('C:\\Users\\Fafhrd\\Desktop\\Test.dae',encoding = 'UTF-8',xml_declaration=True)