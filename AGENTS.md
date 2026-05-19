# AGENTS.md

## Entrypoint

- `pmx_fs_to_gltf` (shell function) — batch converts `.pmx.zip` files to separated `.gltf`
- `nix develop` to enter the dev shell, then use the command

## Key files

- `pmx_fs_to_gltf.py` — orchestrator: unzips, calls Blender per file, mirrors input dir hierarchy under `gltf/`
- `convert_pmx_to_gltf.py` — Blender script: imports PMX via `mmd_tools`, converts materials to Principled BSDF, exports separated GLTF
- `flake.nix` — provides `blender`, `f3d`, `unzip`, `python3`, and the `mmd_tools` addon

## Critical gotchas

- **Morph targets crash f3d**: VTK's glTF reader can't handle morph targets. `export_morph=False` is mandatory.
- **Custom shader nodes**: `mmd_tools` uses `MMDShaderDev` node groups which the glTF exporter ignores. Materials are converted to `Principled BSDF` with base color texture in `convert_pmx_to_gltf.py`.
- **Case-sensitive texture paths**: PMX files can reference `Tex/` when the ZIP has `tex/` (or vice versa). Symlinks for both cases are created in the orchestrator; `convert_pmx_to_gltf.py` does case-insensitive file search for unloaded images.
- **`mmd_tools` input**: addon fetched via `flake = false` (not a Nix flake). `BLENDER_USER_SCRIPTS` points to a local `.blender-scripts/addons/` symlink.

## Usage

```sh
nix develop
pmx_fs_to_gltf models/charA.pmx.zip models/charB.pmx.zip
# Produces gltf/models/charA.gltf, gltf/models/charB.gltf (each with .bin + textures/)
```
