import argparse
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def find_pmx_in_zip(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        pmx_files = [n for n in names if n.lower().endswith(".pmx")]
        if not pmx_files:
            print(f"Warning: no .pmx found in {zip_path}", file=sys.stderr)
            return None
        return pmx_files[0]


def main():
    parser = argparse.ArgumentParser(description="Convert PMX ZIPs to separated glTF")
    parser.add_argument("zips", nargs="+", help="Input .pmx.zip files")
    parser.add_argument("-o", "--output-dir", default="gltf", help="Output directory (default: gltf)")
    args = parser.parse_args()

    blender_script = os.path.join(os.path.dirname(__file__), "convert_pmx_to_glb.py")

    for zip_path_str in args.zips:
        zip_path = Path(zip_path_str)
        if not zip_path.exists():
            print(f"Error: {zip_path} not found", file=sys.stderr)
            continue

        pmx_inside = find_pmx_in_zip(zip_path)
        if pmx_inside is None:
            continue

        try:
            rel_dir = zip_path.resolve().parent.relative_to(Path.cwd())
        except ValueError:
            rel_dir = Path(".")
        stem = zip_path.stem.removesuffix(".pmx")
        out_name = stem + ".gltf"
        out_path = Path(args.output_dir) / rel_dir / stem / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tmpdir)

            dirs_on_disk = set(os.listdir(tmpdir))
            for name in list(dirs_on_disk):
                full = os.path.join(tmpdir, name)
                if os.path.isdir(full):
                    lower = name.lower()
                    upper = name.upper()
                    if lower != name and lower not in dirs_on_disk:
                        os.symlink(name, os.path.join(tmpdir, lower))
                    if upper != name and upper not in dirs_on_disk:
                        os.symlink(name, os.path.join(tmpdir, upper))

            pmx_full = os.path.join(tmpdir, pmx_inside)

            print(f"  {zip_path} -> {out_path}")
            subprocess.run(
                ["blender", "--background", "--python", blender_script, "--", pmx_full, str(out_path)],
                check=True,
            )

    print("Done.")


if __name__ == "__main__":
    main()
