# AGENTS.md

## Entrypoint

- `nix run . -- -i <input> -o <output>` — converts a PMX model or archive to separated `.gltf`
- `pmx_fs_to_gltf` (shell function, inside `nix develop`) — same
- `nix develop` to enter the dev shell, then use the shell function

## Key files

- `pmx_fs_to_gltf.py` — orchestrator: resolves input (archive/directory/.pmx), finds the single `.pmx`, calls Blender, writes report
- `convert_pmx_to_gltf.py` — Blender script: imports PMX via `mmd_tools`, converts materials to Principled BSDF, exports separated GLTF
- `flake.nix` — provides `blender`, `f3d`, `unzip`, `python3`, and the `mmd_tools` addon

## Critical gotchas

- **Morph targets crash f3d**: VTK's glTF reader can't handle morph targets. `export_morph=False` is mandatory.
- **Custom shader nodes**: `mmd_tools` uses `MMDShaderDev` node groups which the glTF exporter ignores. Materials are converted to `Principled BSDF` with base color texture in `convert_pmx_to_gltf.py`.
- **Case-sensitive texture paths**: PMX files can reference `Tex/` when the ZIP has `tex/` (or vice versa). Symlinks for both cases are created in the orchestrator; `convert_pmx_to_gltf.py` does case-insensitive file search for unloaded images.
- **`mmd_tools` input**: addon fetched via `flake = false` (not a Nix flake). `BLENDER_USER_SCRIPTS` points to a local `.blender-scripts/addons/` symlink.

## Usage

```sh
# Direct (no dev shell needed)
nix run . -- -i models/charA.pmx.zip -o charA.gltf
nix run . -- -i charA.pmx -o charA.gltf.zip
nix run . -- -i extracted_dir/ -o charA.gltf.tar.gz -r report.json

# Or via dev shell
nix develop
pmx_fs_to_gltf -i models/charA.pmx.zip -o charA.gltf
pmx_fs_to_gltf -i charA.pmx -o charA.gltf
pmx_fs_to_gltf -i extracted_dir/ -o charA.gltf.zip -r report.json

# Output is always a directory (<name>.gltf/) or an archive containing one
```
