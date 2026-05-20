import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path


_ARCHIVE_EXTS = (".zip", ".tar", ".tgz", ".tar.gz", ".tar.bz2", ".tbz2", ".7z", ".rar")


def _is_archive(path: str) -> bool:
    lower = path.lower()
    return any(lower.endswith(ext) for ext in _ARCHIVE_EXTS)


def _parse_output(output_path: str):
    lower = output_path.lower()
    if lower.endswith(".gltf"):
        return "dir", output_path
    for ext in _ARCHIVE_EXTS:
        if lower.endswith(ext):
            stem = output_path[: -len(ext)]
            if stem.lower().endswith(".gltf"):
                return ext, stem
    return None


def _extract_to(path: str, dst: str):
    lower = path.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            zf.extractall(dst)
    elif lower.endswith((".tar", ".tgz", ".tar.gz", ".tar.bz2", ".tbz2")):
        mode = (
            "r:gz"
            if lower.endswith((".tgz", ".tar.gz"))
            else "r:bz2" if lower.endswith((".tar.bz2", ".tbz2")) else "r:"
        )
        with tarfile.open(path, mode) as tf:
            tf.extractall(dst)
    elif lower.endswith(".7z"):
        subprocess.run(["7z", "x", path, f"-o{dst}"], check=True, capture_output=True)
    elif lower.endswith(".rar"):
        subprocess.run(["unar", path, "-o", dst], check=True, capture_output=True)


def _archive_dir(src_dir: str, dst_path: str):
    lower = dst_path.lower()
    parent = os.path.dirname(src_dir)
    basename = os.path.basename(src_dir)
    if lower.endswith(".zip"):
        with zipfile.ZipFile(dst_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for dirpath, _, filenames in os.walk(src_dir):
                for f in filenames:
                    full = os.path.join(dirpath, f)
                    zf.write(full, os.path.relpath(full, parent))
    elif lower.endswith((".tar", ".tgz", ".tar.gz", ".tar.bz2", ".tbz2")):
        mode = (
            "w:gz"
            if lower.endswith((".tgz", ".tar.gz"))
            else "w:bz2" if lower.endswith((".tar.bz2", ".tbz2")) else "w"
        )
        with tarfile.open(dst_path, mode) as tf:
            tf.add(src_dir, arcname=basename)
    elif lower.endswith(".7z"):
        subprocess.run(
            ["7z", "a", os.path.abspath(dst_path), basename],
            cwd=parent,
            check=True,
            capture_output=True,
        )


def _find_pmx_in_dir(dir_path: str):
    pmx_files = []
    for dirpath, _, filenames in os.walk(dir_path):
        for f in filenames:
            if f.lower().endswith(".pmx"):
                pmx_files.append(os.path.join(dirpath, f))
    if not pmx_files:
        print(f"Error: no .pmx file found in {dir_path}", file=sys.stderr)
        sys.exit(1)
    return pmx_files[0], len(pmx_files)


def _create_case_symlinks(tmpdir: str):
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


def main():
    parser = argparse.ArgumentParser(description="Convert a PMX model to separated glTF")
    parser.add_argument("-i", "--input", required=True,
                        help="Input .pmx file, directory, or archive (.zip/.tar/.7z/...)")
    parser.add_argument("-o", "--output", required=True,
                        help="Output .gltf directory or .gltf.<archive_ext> file")
    parser.add_argument("-r", "--report",
                        help="Path to write conversion_report.json (omit for key=val on stdout)")
    args = parser.parse_args()

    blender_script = os.path.join(os.path.dirname(__file__), "convert_pmx_to_gltf.py")
    input_path = args.input
    output_path = args.output

    parsed = _parse_output(output_path)
    if parsed is None:
        exts = sorted(set(e for e in _ARCHIVE_EXTS if not e.startswith(".")))
        print(
            f"Error: output must end with .gltf or .gltf.<ext> where <ext> is one of: "
            f"{', '.join(exts)}",
            file=sys.stderr,
        )
        sys.exit(1)

    output_mode, gltf_dir_name = parsed

    tmpdir_cleanup = None
    if os.path.isdir(input_path):
        work_dir = input_path
    elif os.path.isfile(input_path):
        if _is_archive(input_path):
            tmpdir_cleanup = tempfile.TemporaryDirectory()
            _extract_to(input_path, tmpdir_cleanup.name)
            work_dir = tmpdir_cleanup.name
        elif input_path.lower().endswith(".pmx"):
            work_dir = str(Path(input_path).resolve().parent)
        else:
            print(f"Error: unrecognized input type: {input_path}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    pmx_full, pmx_count = _find_pmx_in_dir(work_dir)
    gltf_stem = os.path.splitext(os.path.basename(gltf_dir_name))[0]
    staging_cleanup = None

    if output_mode == "dir":
        gltf_dir = gltf_dir_name
        os.makedirs(gltf_dir, exist_ok=True)
    else:
        staging_cleanup = tempfile.TemporaryDirectory()
        gltf_dir = os.path.join(staging_cleanup.name, os.path.basename(gltf_dir_name))
        os.makedirs(gltf_dir)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    gltf_path = os.path.join(gltf_dir, gltf_stem + ".gltf")

    _create_case_symlinks(work_dir)

    print(f"  {os.path.basename(pmx_full)} -> {output_path}")
    subprocess.run(
        ["blender", "--background", "--python", blender_script, "--", pmx_full, gltf_path],
        check=True,
    )

    if output_mode != "dir":
        _archive_dir(gltf_dir, output_path)
        staging_cleanup.cleanup()

    if tmpdir_cleanup is not None:
        tmpdir_cleanup.cleanup()

    trust = 1.0 / pmx_count if pmx_count > 0 else 0.0
    report_data = {
        "input": input_path,
        "output": output_path,
        "pmx_count": pmx_count,
        "trust": trust,
        "converted_pmx": os.path.basename(pmx_full),
    }

    if args.report:
        report_path = os.path.abspath(args.report)
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=2)
    else:
        for k, v in report_data.items():
            print(f"{k}={v}")

    print("Done.")


if __name__ == "__main__":
    main()
