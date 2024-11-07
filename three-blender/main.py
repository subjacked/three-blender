import bpy
from mathutils import Vector
from os import makedirs, path

blend_dir = bpy.path.abspath("//")
export_dir = path.join(blend_dir, "exported_gltfs")

imports = "import * as THREE from 'three';\n"

print("const scene = new THREE.Scene();")

# Convert Blender color to HEX (Three.js format)
def bpy_color_to_hex(bpy_color):
    rgb = tuple(int(channel * 255) for channel in bpy_color)
    return '0x{:02x}{:02x}{:02x}'.format(*rgb)

# Generate position and rotation properties for objects
def addobjprop(object):
    location = object.location
    rotation = object.rotation_euler
    code = f"{object.name}.position.set({location.x}, {location.y}, {location.z});\n"
    code += f"{object.name}.rotation.set({rotation.x}, {rotation.y}, {rotation.z});\n"
    return code

# CAMERAS
cam_code = ""
for camera in bpy.data.cameras:
    cam_code += f"const {camera.name} = new THREE.PerspectiveCamera({camera.lens}, window.innerWidth / window.innerHeight, 0.1, 1000);\n"
    cam_code += addobjprop(bpy.data.objects[camera.name])
    cam_code += "\n"

print(cam_code)

# LIGHTS
light_code = ""
for light in bpy.data.lights:
    # POINT LIGHT
    if light.type == "POINT":
        light_code += f"const {light.name} = new THREE.PointLight({bpy_color_to_hex(light.color)});\n"
        location = bpy.data.objects[light.name].location
        light_code += f"{light.name}.position.set({location.x}, {location.y}, {location.z});\n"

    # SPOT LIGHT
    elif light.type == "SPOT":
        light_object = bpy.data.objects[light.name]
        spot_size = light_object.data.spot_size
        light_code += f"const {light.name} = new THREE.SpotLight({bpy_color_to_hex(light.color)}, {light.energy}, {light.cutoff_distance}, {spot_size}, 0, 1);\n"
        light_code += f"{light.name}.castShadow = true; // enable shadow\n"
        
        location = light_object.location
        light_code += f"{light.name}.position.set({location.x}, {location.y}, {location.z});\n"
        
        # Determining target location based on constraints
        if light_object.constraints:
            for constraint in light_object.constraints:
                if constraint.type in {'TRACK_TO', 'DAMPED_TRACK', 'LOCKED_TRACK'} and constraint.target:
                    target_location = constraint.target.location
                    break
        else:
            # Calculate the target position if no constraint
            target_location = location + light_object.rotation_euler.to_matrix() @ Vector((0, 0, -1))
        
        light_code += f"{light.name}.target.position.set({target_location.x}, {target_location.y}, {target_location.z});\n"

    # AREA LIGHT
    elif light.type == "AREA":
        light_code += f"const {light.name} = new THREE.DirectionalLight({bpy_color_to_hex(light.color)}, {light.energy});\n"
    
    light_code += f"scene.add({light.name});\n\n"

print(light_code)

# OBJECTS
obj_code = ""

def loader(path, object):
    location = bpy.data.objects[object.name].location
    rotation = bpy.data.objects[object.name].rotation_euler

    load_code = f"loader.load('{path}',\n"
    load_code += "\t(gltf) => {\n"
    load_code += f"\t\tconst {object.name} = gltf.scene;\n"
    load_code += f"\t\t{object.name}.position.set({location.x}, {location.y}, {location.z});\n"
    load_code += f"\t\t{object.name}.rotation.set({rotation.x}, {rotation.y}, {rotation.z});\n"
    load_code += f"\t\tscene.add({object.name});\n"
    load_code += "\t},\n"
    load_code += "\t(xhr) => {\n"
    load_code += f"\t\tconsole.log('{object.name} loaded: ' + (xhr.loaded / xhr.total * 100) + '%');\n"
    load_code += "\t},\n"
    load_code += "\t(error) => {\n"
    load_code += f"\t\tconsole.error('An error happened loading the model {object.name}', error);\n"
    load_code += "\t}\n"
    load_code += ");\n"
    return load_code

def export_obj(obj):
    bpy.ops.object.select_all(action='DESELECT')

    if obj.type == "MESH":
        obj.select_set(True)
        export_path = path.join(export_dir, f"{obj.name}.gltf")
        bpy.ops.export_scene.gltf(filepath=export_path, use_selection=True)
        obj.select_set(False)
        return export_path

# Check if GLTFLoader is needed
if bpy.data.objects:
    imports += "import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';\n"
    obj_code += "const loader = new GLTFLoader();\n"
    makedirs(export_dir, exist_ok=True)  # Create directory if it doesn't exist

for obj in bpy.data.objects:
    if obj.type == "MESH":
        obj_code += f"\n// {obj.name}\n"
        obj_code += loader(export_obj(obj), obj) + "\n"

print(obj_code)

# RENDERER
renderer_code = "const renderer = new THREE.WebGLRenderer();\n"
renderer_code += "renderer.setSize(window.innerWidth, window.innerHeight);\n"
renderer_code += "document.body.appendChild(renderer.domElement);\n"

# Background color
background_color = bpy.context.scene.world.color
renderer_code += f"// Background Color\n"
renderer_code += f"scene.background = new Three.Color({bpy_color_to_hex(background_color)});\n"
