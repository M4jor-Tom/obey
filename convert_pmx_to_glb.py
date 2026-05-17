import sys
import os
import bpy


argv = sys.argv
argv = argv[argv.index("--") + 1:]
input_path, output_path = argv[0], argv[1]

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()

bpy.ops.preferences.addon_enable(module="mmd_tools")
bpy.ops.mmd_tools.import_model(filepath=input_path)


def _find_file_ci(base_dir, target):
    target_lower = target.lower()
    for dirpath, dirnames, filenames in os.walk(base_dir):
        for f in filenames:
            if f.lower() == target_lower:
                return os.path.join(dirpath, f)
    return None


def reload_images():
    tex_dir = os.path.dirname(input_path)
    for img in bpy.data.images:
        if img.source == "FILE" and not img.has_data and img.filepath:
            orig = bpy.path.abspath(img.filepath)
            if os.path.exists(orig):
                try:
                    img.reload()
                except RuntimeError:
                    pass
            else:
                fname = os.path.basename(orig)
                found = _find_file_ci(tex_dir, fname)
                if found:
                    try:
                        img.filepath = found
                        img.reload()
                    except RuntimeError:
                        pass


def convert_materials():
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        tree = mat.node_tree
        shader_group = None
        base_tex_node = None
        for node in tree.nodes:
            if node.type == "GROUP" and node.node_tree and "MMDShaderDev" == node.node_tree.name:
                shader_group = node
            if node.type == "TEX_IMAGE" and node.name == "mmd_base_tex":
                base_tex_node = node
        if shader_group is None:
            continue

        new_mat = bpy.data.materials.new(name=mat.name)
        new_mat.use_nodes = True
        new_tree = new_mat.node_tree
        new_tree.nodes.clear()
        principled = new_tree.nodes.new("ShaderNodeBsdfPrincipled")
        output = new_tree.nodes.new("ShaderNodeOutputMaterial")

        if base_tex_node and base_tex_node.image:
            tex = new_tree.nodes.new("ShaderNodeTexImage")
            tex.image = base_tex_node.image
            tex.interpolation = "Linear"
            new_tree.links.new(tex.outputs["Color"], principled.inputs["Base Color"])

        new_mat.blend_method = getattr(mat, "blend_method", "OPAQUE")
        new_mat.show_transparent_back = getattr(mat, "show_transparent_back", True)
        try:
            new_mat.alpha_threshold = mat.alpha_threshold
        except Exception:
            pass

        new_tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])

        for obj in bpy.data.objects:
            if obj.type == "MESH":
                for slot_idx, slot in enumerate(obj.material_slots):
                    if slot.material == mat:
                        obj.data.materials[slot_idx] = new_mat

        bpy.data.materials.remove(mat, do_unlink=True)


reload_images()
convert_materials()

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(
    filepath=output_path,
    use_selection=True,
    export_morph=False,
)
