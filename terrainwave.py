import bpy
import math
from mathutils import Vector

def create_wave_terrain(grid_size=20, wave_height=0.05, duration_seconds=10.0, fps=24, noise_scale=0.5, grid_scale=10.0):
    """
    Create an animated wave terrain with shape keys.
    """
    if 'Cube' in bpy.data.objects:
        cube = bpy.data.objects['Cube']
        bpy.context.view_layer.objects.active = cube
        cube.select_set(True)
        bpy.ops.object.delete()

    mesh = bpy.data.meshes.new('WaveTerrain')
    obj = bpy.data.objects.new('WaveTerrain', mesh)
    bpy.context.scene.collection.objects.link(obj)
    
    vertices = []
    faces = []
    
    for y in range(grid_size):
        for x in range(grid_size):
            nx = ((x / (grid_size - 1)) - 0.5) * grid_scale
            ny = ((y / (grid_size - 1)) - 0.5) * grid_scale
            vertices.append(Vector((nx, ny, 0)))
    
    for y in range(grid_size - 1):
        for x in range(grid_size - 1):
            v1 = y * grid_size + x
            v2 = v1 + 1
            v3 = v1 + grid_size
            v4 = v3 + 1
            faces.append((v1, v2, v4, v3))
    
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    
    if obj.data.shape_keys is None:
        obj.shape_key_add(name='Basis')
    
    total_frames = int(duration_seconds * fps)
    bpy.context.scene.frame_end = total_frames 
    
    for frame in range(total_frames):
        try:
            key = obj.shape_key_add(name=f'Wave_{frame}')
        except Exception as e:
            print(f"Error adding shape key for frame {frame}: {e}")
            continue
        
        time = (frame / total_frames) * 2 * math.pi
        for i, v in enumerate(key.data):
            x, y = vertices[i][0], vertices[i][1]
            distance = math.sqrt(x * x + y * y)
            base_freq = 2 * math.pi / duration_seconds
            main_wave = math.sin(distance * 1.5 + time * base_freq)
            secondary_wave = math.sin(distance * 2 + time * base_freq * 1.5) * 0.3
            tertiary_wave = math.sin(distance * 3 + time * base_freq * 2) * 0.15
            noise_x = math.sin(x * 5 + time * base_freq)
            noise_y = math.sin(y * 5 + time * base_freq)
            noise_t = math.sin(time * base_freq * 2)
            noise_value = (noise_x * noise_y * noise_t) * noise_scale * 0.5
            z = (main_wave + secondary_wave + tertiary_wave + noise_value) * wave_height
            v.co = Vector((x, y, z))
        
        key.value = 1.0
        key.keyframe_insert("value", frame=frame)
        key.value = 0.0
        key.keyframe_insert("value", frame=(frame - 1) % total_frames)
        key.keyframe_insert("value", frame=(frame + 1) % total_frames)
    
    return obj

def create_water_material():
    mat = bpy.data.materials.new(name="WaterMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    mix = nodes.new('ShaderNodeMixShader')
    glass = nodes.new('ShaderNodeBsdfGlass')
    glossy = nodes.new('ShaderNodeBsdfGlossy')
    fresnel = nodes.new('ShaderNodeFresnel')
    output.location = (300, 0)
    mix.location = (100, 0)
    glass.location = (-100, -100)
    glossy.location = (-100, 100)
    fresnel.location = (-100, 200)
    glass.inputs['Color'].default_value = (0.1, 0.3, 0.9, 1.0)
    glass.inputs['IOR'].default_value = 1.33
    glossy.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    glossy.inputs['Roughness'].default_value = 0.1
    fresnel.inputs['IOR'].default_value = 1.33
    links.new(fresnel.outputs['Fac'], mix.inputs['Fac'])
    links.new(glossy.outputs['BSDF'], mix.inputs[1])
    links.new(glass.outputs['BSDF'], mix.inputs[2])
    links.new(mix.outputs['Shader'], output.inputs['Surface'])
    return mat

def setup_lighting():
    for light in bpy.data.lights:
        bpy.data.lights.remove(light)
    light_positions = [
        {'loc': (15, 15, 20), 'rot': (-0.6, -0.8, -0.8), 'energy': 1000.0},
        {'loc': (-15, 15, 20), 'rot': (-0.6, 0.8, 0.8), 'energy': 1000.0},
        {'loc': (15, -15, 20), 'rot': (-0.6, 0.8, -0.8), 'energy': 1000.0},
        {'loc': (-15, -15, 20), 'rot': (-0.6, -0.8, 0.8), 'energy': 1000.0},
    ]
    for i, pos in enumerate(light_positions):
        light_data = bpy.data.lights.new(name=f"AreaLight_{i}", type='AREA')
        light_data.energy = pos['energy']
        light_data.size = 10.0
        light_data.color = (1.0, 1.0, 1.0)
        light_object = bpy.data.objects.new(name=f"AreaLight_{i}", object_data=light_data)
        bpy.context.scene.collection.objects.link(light_object)
        light_object.location = pos['loc']
        light_object.rotation_euler = pos['rot']
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.05, 0.05, 0.05, 1)
    bg.inputs[1].default_value = 0.5

def setup_camera_orbit(duration_seconds, fps, radius=20.0):
    """
    Set up a camera to orbit around the origin.
    """
    # Create a camera if not already in the scene
    cam_data = bpy.data.cameras.new("Camera")
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    
    # Position the camera
    cam_obj.location = (radius, 0, 10)
    cam_obj.rotation_euler = (math.radians(60), 0, math.radians(90))
    
    # Animate the camera to orbit around the origin
    total_frames = int(duration_seconds * fps)
    for frame in range(total_frames + 1):
        angle = (frame / total_frames) * 2 * math.pi
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        cam_obj.location = (x, y, 10)
        cam_obj.keyframe_insert(data_path="location", frame=frame)
        cam_obj.rotation_euler = (math.radians(60), 0, angle + math.pi / 2)
        cam_obj.keyframe_insert(data_path="rotation_euler", frame=frame)

bpy.context.scene.frame_start = 0
bpy.context.scene.render.fps = 24

wave_obj = create_wave_terrain(grid_size=40, wave_height=0.3, duration_seconds=10.0, fps=30, noise_scale=0.8, grid_scale=10.0)
water_material = create_water_material()
wave_obj.data.materials.append(water_material)
setup_lighting()

setup_camera_orbit(duration_seconds=10.0, fps=30, radius=20.0)

bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end = int(10.0 * 30)

bpy.ops.screen.animation_play()
