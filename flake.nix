{
  description = "Flake providing blender CLI with mmd_tools";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    mmd_tools = {
      url = "github:MMD-Blender/blender_mmd_tools";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, mmd_tools }:
    let
      forAllSystems = nixpkgs.lib.genAttrs [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.buildEnv {
            paths = with pkgs; [ blender ];
          };
          blender = pkgs.blender;
        }
      );

      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [ f3d blender unzip python3 ];

            shellHook = ''
              export BLENDER_USER_SCRIPTS="$PWD/.blender-scripts"
              mkdir -p "$BLENDER_USER_SCRIPTS/addons"
              ln -sfn "${mmd_tools}/mmd_tools" "$BLENDER_USER_SCRIPTS/addons/mmd_tools"

              pmx_fs_to_glb() {
                python3 "$PWD/pmx_fs_to_glb.py" "$@"
              }
              blender_gltf() {
                blender --python-expr "import bpy; bpy.ops.import_scene.gltf(filepath='$1')"
              }
            '';
          };
        }
      );
    };
}
