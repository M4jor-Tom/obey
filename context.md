# PMX → GLB conversion pipeline (output files are `.glb`, default output directory is `glb/`)

## Problem 1: need a script to convert PMX files to viewable glb

**Need**: Convert MikuMikuDance `.pmx` models (often distributed as `.pmx.zip` bundles containing mesh + textures) to GLB format for viewing with `f3d`.

**Solution**:
- `pmx_fs_to_glb.py` — orchestrator that takes one or more `.pmx.zip` files, extracts each to a temp dir, calls Blender CLI per-file, and mirrors the input directory hierarchy under an output root (default `glb/`).
- `convert_pmx_to_glb.py` — Blender Python script that imports the PMX via the `mmd_tools` addon and exports as GLB.
- `flake.nix` — Nix flake providing `blender`, `f3d`, `unzip`, `python3`, and the `mmd_tools` Blender addon (fetched from GitHub, `flake = false` since it's not a Nix project).
- `pmx2glb` was first attempted as a shell function but replaced by `pmx_fs_to_glb` to support batch processing and hierarchy mirroring.

Each input ZIP becomes a `.glb` file mirroring the input path hierarchy under `glb/`.

**Usage**: `nix develop` then `pmx_fs_to_glb models/charA.pmx.zip models/charB.pmx.zip`

---

## Problem 2: f3d "failed to load scene"

**Need**: f3d refuses to open the exported `.glb` files with `failed to load scene`.

**Solution**: VTK's glb reader (used by f3d) cannot handle glb morph targets. MMD models use morph targets extensively for facial expressions, and the default Blender glb export includes them.

**Fix**: Set `export_morph=False` in the glb export call.

---

## Problem 3: textures not included in the GLB

**Need**: The exported `.glb` files have mesh data but no textures (0 images in the GLB).

**Root cause 1** — custom shader nodes: `mmd_tools` creates materials with a custom `MMDShaderDev` node group, not the standard `Principled BSDF`. The glb exporter only recognizes standard node types, so it has no way to find the texture images.

**Root cause 2** — unloaded images: many texture files aren't loaded by `mmd_tools` during import, either because:
- Case-sensitive filesystem: the PMX references `Tex/` but the ZIP has `tex/` (or vice versa)
- Some formats (TGA, BMP) fail to load when the path is wrong

**Fix 1** — material conversion in `convert_pmx_to_glb.py`:
- After import, iterate all materials
- If a material uses the `MMDShaderDev` node group, create a new `Principled BSDF`-based material
- Find the `mmd_base_tex` image node and connect its image to `Base Color`
- Preserve `blend_method` for transparency
- Assign the new material to all meshes that used the original
- Remove the old material

**Fix 2** — case-insensitive texture search in `convert_pmx_to_glb.py`:
- For images with `has_data=False`, try `img.reload()` on the original path first
- If the file doesn't exist, search the texture directory case-insensitively (`os.walk` + lowercase match) and update the filepath

**Fix 3** — symlinks in `pmx_fs_to_glb.py`:
- After extracting the ZIP, create lowercase and uppercase symlinks for every directory (e.g., `Tex` → `tex` and `tex` → `Tex`) to handle any path case the PMX might reference

---

## Problem 4: clean error messages for wrong invocations

**Need**: Passing wrong number of args should show a clean usage message, not a Python traceback.

**Solution**: The shell function `pmx_fs_to_glb` delegates to Python, and argparse handles usage messages automatically:
```
usage: pmx_fs_to_glb.py [-h] [-o OUTPUT_DIR] zips [zips ...]
```
