import sys
import bpy


argv = sys.argv
argv = argv[argv.index("--") + 1:]
input_path, output_path = argv[0], argv[1]

bpy.ops.preferences.addon_enable(module="mmd_tools")
bpy.ops.mmd_tools.import_model(filepath=input_path)
bpy.ops.export_scene.gltf(filepath=output_path)
