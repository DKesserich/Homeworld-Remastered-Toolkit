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

def ColorToArrayToString(color):
    colorArray = []
    colorArray.append(color.r)
    colorArray.append(color.g)
    colorArray.append(color.b)
    colorArray = str(colorArray)
    colorArray = colorArray.translate({ord(c):None for c in '[],'})
    return colorArray

def writeTextures(texName):
    thisImage = ET.SubElement(libImages,'image',id=texName+'-image',name=texName)
    init = ET.SubElement(thisImage,'init_from')
    init.text = D.textures[texName].image.filepath

def writeMaterials(matName):
    thisMaterial = ET.SubElement(libMats,'material',id=matName,name=matName)
    instance = ET.SubElement(thisMaterial,'instance_effect',url='#'+matName+'-fx')
    
    thisEffect = ET.SubElement(libEffects,'effect',id=matName+'-fx',name=matName)
    profile = ET.SubElement(thisEffect,'profile_COMMON')
    technique = ET.SubElement(profile,'technique',sid='standard')
    shtype = ET.SubElement(technique,D.materials[matName].specular_shader)
    
    #Get Textures
    diffuse_tex = []
    specular_tex = []
    emission_tex = []
    normal_tex = []
    for t in D.materials[matName].texture_slots:
        if t is not None:
            if t.use_map_color_diffuse:
                diffuse_tex.append(t)
            if t.use_map_specular:
                specular_tex.append(t)
            if t.use_map_emission:
                emission_tex.append(t)
            if t.use_map_normal:
                normal_tex.append(t)
    
    #Emission Element
    emit = ET.SubElement(shtype,'emission')
    color = ET.SubElement(emit,'color',sid='emission')   
    color.text = ColorToArrayToString(D.materials[matName].diffuse_color)
    if (len(emission_tex) > 0):
        for t in emission_tex:
            texture = ET.SubElement(emit,'texture',texture=t.name+'-image',texcoord='CHANNEL0')
            extra = ET.SubElement(texture,'extra')
            technique = ET.SubElement(extra,'technique',profile='MAYA')
            wrapU = ET.SubElement(technique,'wrapU',sid='wrapU0')
            wrapU.text='TRUE'
            wrapV = ET.SubElement(technique,'wrapV',sid='wrapV0')
            wrapV.text='TRUE'
            blend = ET.SubElement(technique,'blend_mode')
            blend.text = t.blend_type
    
    #Ambient
    ambient = ET.SubElement(shtype,'ambient')
    color = ET.SubElement(ambient,'color',sid='ambient')
    color.text = ColorToArrayToString(D.worlds['World'].ambient_color)+' '+str(D.materials[matName].ambient)
    
    #Diffuse
    diffuse = ET.SubElement(shtype,'diffuse')
    color = ET.SubElement(diffuse,'color',sid='diffuse')
    color.text = ColorToArrayToString(D.materials[matName].diffuse_color)
    if (len(diffuse_tex)>0):
        for t in diffuse_tex:
            texture = ET.SubElement(diffuse,'texture',texture=t.name+'-image',texcoord='CHANNEL0')
            extra = ET.SubElement(texture,'extra')
            technique = ET.SubElement(extra,'technique',profile='MAYA')
            wrapU = ET.SubElement(technique,'wrapU',sid='wrapU0')
            wrapU.text='TRUE'
            wrapV = ET.SubElement(technique,'wrapV',sid='wrapV0')
            wrapV.text='TRUE'
            blend = ET.SubElement(technique,'blend_mode')
            blend.text = t.blend_type
    
    #Specular
    specular = ET.SubElement(shtype,'specular')
    color = ET.SubElement(specular,'color',sid='specular')
    color.text = ColorToArrayToString(D.materials[matName].specular_color)
    if (len(specular_tex)>0):
        for t in specular_tex:
            texture = ET.SubElement(specular,'texture',texture=t.name+'-image',texcoord='CHANNEL0')
            extra = ET.SubElement(texture,'extra')
            technique = ET.SubElement(extra,'technique',profile='MAYA')
            wrapU = ET.SubElement(technique,'wrapU',sid='wrapU0')
            wrapU.text="TRUE"
            wrapV = ET.SubElement(technique,'wrapV',sid='wrapV0')
            wrapV.text = 'TRUE'
            blend = ET.SubElement(technique,'blend_mode')
            blend.text = t.blend_type
    shininess = ET.SubElement(shtype,'shininess')
    shine = ET.SubElement(shininess,'float',sid='shininess')
    shine.text = str(D.materials[matName].specular_hardness)
    
    #Reflective
    reflective = ET.SubElement(shtype,'reflective')
    color = ET.SubElement(reflective,'color')
    color.text = ColorToArrayToString(D.materials[matName].mirror_color)
    
    #Transparency
    transparency = ET.SubElement(shtype,'transparency')
    float = ET.SubElement(transparency,'float',sid='transparency')
    float.text = str(D.materials[matName].alpha)

def writeGeometry(geoName):
    #Triangulate the Mesh
    thisGeo = ET.SubElement(libGeometries,'geometry',name = geoName,id=geoName)
    thisMesh = ET.SubElement(thisGeo,'mesh')
    C.scene.objects.active = D.objects[geoName]
    bpy.ops.object.modifier_add(type='TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier='Triangulate')
    
    mesh = D.objects[geoName].data
    mesh.update(calc_tessface=True)
    mesh.calc_normals_split()
    
    #Create the Vertices
    vertices = []
    for v in mesh.vertices:
        vertices.append(v.co.x)
        vertices.append(v.co.y)
        vertices.append(v.co.z)    
    meshPositions = ET.SubElement(thisMesh,'source',id=geoName+'-positions')
    vertArray = ET.SubElement(meshPositions,'float_array',id=meshPositions.attrib['id']+'-array',count=str(len(vertices)))
    vertices = str(vertices)    
    vertArray.text = vertices.translate({ord(c):None for c in '[],'})
    technique = ET.SubElement(meshPositions,'technique_common')
    accessor = ET.SubElement(technique,'accessor',source='#'+vertArray.attrib['id'],count=str(len(mesh.vertices)),stride='3')
    paramX = ET.SubElement(accessor,'param',name='X',type='float')
    paramY = ET.SubElement(accessor,'param',name='Y',type='float')
    paramZ = ET.SubElement(accessor,'param',name='Z',type='float')
    
    #Create the Normals
    normals = []
    for v in mesh.loops:
        normals.append(v.normal.x)
        normals.append(v.normal.y)
        normals.append(v.normal.z)    
    meshNormals = ET.SubElement(thisMesh,'source',id=geoName+'-normals')
    normalArray = ET.SubElement(meshNormals,'float_array',id=meshNormals.attrib['id']+'-array',count = str(len(normals)))
    normals = str(normals)
    normalArray.text = normals.translate({ord(c):None for c in '[],'})
    technique = ET.SubElement(meshNormals,'technique_common')
    accessor = ET.SubElement(technique,'accessor',source='#'+normalArray.attrib['id'],count=str(len(mesh.loops)),stride='3')
    paramX = ET.SubElement(accessor,'param',name='X',type='float')
    paramY = ET.SubElement(accessor,'param',name='Y',type='float')
    paramZ = ET.SubElement(accessor,'param',name='Z',type='float')
    
    #Create UVs
    uvMaps = []
    for uvi in mesh.uv_layers:
        thisMap = ET.SubElement(thisMesh,'source',id=geoName+'-texcoord-'+uvi.name)
        uvMaps.append(thisMap)
        coords = []
        for v in uvi.data:
            coords.append(v.uv.x)
            coords.append(v.uv.y)
        array = ET.SubElement(thisMap,'float_array',id=thisMap.attrib['id']+'-array',count = str(len(coords)))
        coords = str(coords)
        array.text = coords.translate({ord(c):None for c in '[],'})
        technique = ET.SubElement(thisMap,'technique_common')
        accessor = ET.SubElement(technique,'accessor',source='#'+array.attrib['id'],count = str(len(uvi.data)),stride='2')
        paramS = ET.SubElement(accessor,'param',name='S',type='float')
        paramT = ET.SubElement(accessor,'param',name='T',type='float')
    
    #Tell it where the vertices are
    vertElement = ET.SubElement(thisMesh,'vertices',id=geoName+'-vertices')
    input = ET.SubElement(vertElement,'input',semantic='POSITION',source='#'+meshPositions.attrib['id'])
    
    #Make the Triangles
    for m in range(0,len(mesh.materials)):
        mat = mesh.materials[m]
        polys = []
        for p in mesh.polygons:
            if p.material_index == m:
                polys.append(p)
        tris = ET.SubElement(thisMesh,'triangles',material = mat.name,count=str(len(polys)))
        inputVert = ET.SubElement(tris,'input',semantic='VERTEX',offset='0',source='#'+vertElement.attrib['id'])
        inputNormal = ET.SubElement(tris,'input',semantic='NORMAL',offset ='1',source = '#'+ meshNormals.attrib['id'])
        for u in range(0,len(uvMaps)):
            map = ET.SubElement(tris,'input',semantic = 'TEXCOORD',offset='1',set=str(u),source='#'+uvMaps[u].attrib['id'])
        pElement = ET.SubElement(tris,'p')
        pVerts = []
        pInds = []
        for p in mesh.polygons:
            for i in p.vertices:
                pVerts.append(i)
        for p in mesh.polygons:
            if (p.material_index==m):
                for i in p.loop_indices:
                    pInds.append(pVerts[i])
                    pInds.append(i)
        pInds = str(pInds)
        pElement.text = pInds.translate({ord(c):None for c in '[],'})
        
def writeAnims(objName):
    thisAnim = ET.SubElement(libAnimations,'animation',id=objName+'-anim',name=objName)
    
    for curve in D.objects[objName].animation_data.action.fcurves:
        thisCurve = ET.SubElement(libAnimations,'animation')
        
        
        baseID = None
        
        if curve.data_path == 'location':
            baseID = objName+'-translate'
            if curve.array_index == 0:
                baseID = baseID+'.X'
            if curve.array_index == 1:
                baseID = baseID+'.Y'
            if curve.array_index == 2:
                baseID = baseID+'.Z'
        if curve.data_path == 'rotation_euler':
            baseID = objName+'-rotate'
            if curve.array_index == 0:
                baseID = baseID+'X.ANGLE'
            if curve.array_index == 1:
                baseID = baseID+'Y.ANGLE'
            if curve.array_index == 2:
                baseID = baseID+'Z.ANGLE'
        
        keys = []
        values = []
        interp = []
        intan = []
        outtan = []
        for k in curve.keyframe_points:
            keys.append(k.co.x/C.scene.render.fps)
            if curve.data_path == 'location':
                values.append(k.co.y)
            if curve.data_path == 'rotation_euler':
                values.append(math.degrees(k.co.y))
            interp.append(k.interpolation)
            intan.append(k.handle_left.x)
            intan.append(k.handle_left.y)
            outtan.append(k.handle_right.x)
            outtan.append(k.handle_right.y)
        
        #Sampler
        sampler = ET.SubElement(thisCurve,'sampler',id=baseID)
        
        #Create the input values (keyframes)
        source = ET.SubElement(thisCurve,'source',id=baseID+'-input')
        input = ET.SubElement(sampler,'input',semantic = 'INPUT',source='#'+source.attrib['id'])
        array = ET.SubElement(source,'float_array',id=baseID+'-input-array',count = str(len(keys)))
        array.text = str(keys).translate({ord(c):None for c in '[],'})
        technique = ET.SubElement(source,'technique_common')
        accessor = ET.SubElement(technique,'accessor',source='#'+array.attrib['id'],count = array.attrib['count'],stride = '1')
        param = ET.SubElement(accessor,'param',type='float')
        
        #Create the output values (actual values)
        source = ET.SubElement(thisCurve,'source',id=baseID+'-output')
        input = ET.SubElement(sampler,'input',semantic = 'OUTPUT',source='#'+source.attrib['id'])
        array = ET.SubElement(source,'float_array',id=baseID+'-output-array',count = str(len(values)))
        array.text = str(values).translate({ord(c):None for c in '[],'})
        technique = ET.SubElement(source,'technique_common')
        accessor = ET.SubElement(technique,'accessor',source='#'+array.attrib['id'],count = array.attrib['count'],stride = '1')
        param = ET.SubElement(accessor,'param',type='float')
        
        #Create the interpolations
        source = ET.SubElement(thisCurve,'source',id=baseID+'-interpolation')
        input = ET.SubElement(sampler,'input',semantic='INTERPOLATION',source='#'+source.attrib['id'])
        array = ET.SubElement(source,'Name_array',id=baseID+'-interpolation-array',count = str(len(interp)))
        array.text = str(interp).translate({ord(c):None for c in '[],\''})
        technique = ET.SubElement(source,'technique_common')
        accessor = ET.SubElement(technique,'accessor',source='#'+array.attrib['id'],count = array.attrib['count'],stride='1')
        param = ET.SubElement(accessor,'param',type='name')
        
        #Intangents for Bezier Curves
        source = ET.SubElement(thisCurve,'source',id=baseID+'-intan')
        input = ET.SubElement(sampler,'input',semantic='IN_TANGENT',source='#'+source.attrib['id'])
        array = ET.SubElement(source,'float_array',id=baseID+'-intan-array',count = str(len(intan)))
        array.text = str(intan).translate({ord(c):None for c in '[],'})
        technique = ET.SubElement(source,'technique_common')
        accessor = ET.SubElement(technique,'accessor',source = '#'+array.attrib['id'],count = str(len(intan)/2),stride = '2')
        paramA = ET.SubElement(accessor,'param',type='float')
        paramB = ET.SubElement(accessor,'param',type='float')
        
        #Outtangents for Bezier Curves
        source = ET.SubElement(thisCurve,'source',id=baseID+'-outtan')
        input = ET.SubElement(sampler,'input',semantic='OUT_TANGENT',source='#'+source.attrib['id'])
        array = ET.SubElement(source,'float_array',id=baseID+'-outtan-array',count = str(len(outtan)))
        array.text = str(outtan).translate({ord(c):None for c in '[],'})
        technique = ET.SubElement(source,'technique_common')
        accessor = ET.SubElement(technique,'accessor',source='#'+array.attrib['id'],count = str(len(outtan)/2),stride = '2')
        paramA = ET.SubElement(accessor,'param',type='float')
        paramB = ET.SubElement(accessor,'param',type='float')
        
        channel = ET.SubElement(thisCurve,'channel',source='#'+baseID,target=baseID.split('-')[0]+'/'+baseID.split('-')[1])
        
        
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
    if D.objects[objectName].animation_data is not None:
        writeAnims(objectName)
    if D.objects[objectName].type == 'MESH':
        geoInstance = ET.SubElement(thisNode,'instance_geometry',url='#'+objectName)
        bindMat = ET.SubElement(geoInstance,'bind_material')
        matTechnique = ET.SubElement(bindMat,'technique_common')
        for m in D.objects[objectName].material_slots:
            matInstance = ET.SubElement(matTechnique,'instance_material',symbol = m.name,target='#'+m.name)
        writeGeometry(objectName)
    if D.objects[objectName].children is not None:
        for c in D.objects[objectName].children:
            writeNodes(thisNode,c.name)

def prettify(element, indent='  '):
    queue = [(0, element)]  # (level, element)
    while queue:
        level, element = queue.pop(0)
        children = [(level + 1, child) for child in list(element)]
        if children:
            element.text = '\n' + indent * (level+1)  # for child open
        if queue:
            element.tail = '\n' + indent * queue[0][0]  # for sibling open
        else:
            element.tail = '\n' + indent * (level-1)  # for parent close
        queue[0:0] = children  # prepend so children come before siblings  

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

libImages = ET.SubElement(root,'library_images')
libMats = ET.SubElement(root,'library_materials')
libEffects = ET.SubElement(root,'library_effects')
libGeometries = ET.SubElement(root,'library_geometries')
libAnimations = ET.SubElement(root,'library_animations')

for ob in D.objects:
    if ob.parent is None:
        writeNodes(thisScene,ob.name)
   
for mat in D.materials:
    writeMaterials(mat.name)   

for tex in D.textures:
    writeTextures(tex.name)
        
prettify(root)
doc = ET.ElementTree(root)
doc.write('C:\\Users\\Fafhrd\\Desktop\\Test.dae',encoding = 'utf-8',xml_declaration=True)