#!/usr/bin/env python3
"""Build a toolchain-epiccc PlatformIO package from an epic-cc release zip.

Inputs are the upstream bundle zips already produced by epic-cc's release
workflow (docs/30-distribution-design.md "Bundle layout"). This script only
adds package.json and repacks as tar.gz. No system clang is ever consulted.

Usage:
  package_toolchain.py --zip epic-cc-0.0.3-x86_64-linux.zip --system linux_x86_64 --version 0.0.3 --out toolchain-epiccc-linux_x86_64-0.0.3.tar.gz
  package_toolchain.py --zip epic-cc-0.0.3-x86_64-windows.zip --system windows_amd64 --version 0.0.3 --out toolchain-epiccc-windows_amd64-0.0.3.tar.gz

The caller decides version mapping. By default it equals the upstream tag
stripped of leading v. See packages/versions.json and packages/README.
"""

import argparse
import json
import pathlib
import tarfile
import tempfile
import zipfile
import subprocess
import sys


TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / "packages" / "toolchain-epiccc" / "package.json"


def load_template():
    return json.loads(TEMPLATE.read_text())


def build(zip_path: pathlib.Path, system: str, version: str, out_path: pathlib.Path):
    data = load_template()
    data["version"] = version
    if system == "*":
        data.pop("system", None)
    else:
        if system == "windows_amd64":
            data["system"] = ["windows_amd64", "windows_x86_64"]
        else:
            data["system"] = [system]
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(td)
        tops = [p for p in td.iterdir() if p.is_dir()]
        if len(tops) != 1:
            raise SystemExit(f"expected one top-level dir in {zip_path}, got {tops}")
        top = tops[0]
        for bin_file in [top / "epic-cc", top / "epic-cc.exe"]:
            if bin_file.exists():
                bin_file.chmod(bin_file.stat().st_mode | 0o111)
        clang_bin = top / "clang" / "bin"
        if clang_bin.exists():
            for p in clang_bin.iterdir():
                if p.is_file():
                    p.chmod(p.stat().st_mode | 0o111)

        if not ((top / "epic-cc").exists() or (top / "epic-cc.exe").exists()):
            raise SystemExit(f"bundle {zip_path} missing epic-cc binary")
        if not (top / "clang").exists():
            raise SystemExit(f"bundle {zip_path} missing clang/")

        (top / "package.json").write_text(json.dumps(data, indent=2) + "\n")

        with tarfile.open(out_path, "w:gz") as tf:
            for child in sorted(top.iterdir()):
                tf.add(child, arcname=child.name)

    validate(out_path)


def validate(tgz: pathlib.Path):
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        with tarfile.open(tgz, "r:gz") as tf:
            tf.extractall(td)
        pj = td / "package.json"
        if not pj.exists():
            raise SystemExit(f"validation failed: {tgz} missing package.json")
        data = json.loads(pj.read_text())
        if not data.get("version"):
            raise SystemExit("package.json missing version")
        if not data.get("name"):
            raise SystemExit("package.json missing name")
        binary = td / "epic-cc.exe" if (td / "epic-cc.exe").exists() else td / "epic-cc"
        if not binary.exists():
            raise SystemExit(f"validation failed: {tgz} missing epic-cc")
        binary.chmod(binary.stat().st_mode | 0o111)
        clang_bin = td / "clang" / "bin"
        if clang_bin.exists():
            for p in clang_bin.iterdir():
                if p.is_file():
                    p.chmod(p.stat().st_mode | 0o111)
        try:
            result = subprocess.run(
                [str(binary), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                print(f"warning: {binary} --version failed: {result.stderr}", file=sys.stderr)
        except Exception as exc:
            print(f"warning: smoke --version failed: {exc}", file=sys.stderr)

        fixture = pathlib.Path(__file__).resolve().parents[2] / "epic-cc" / "crates" / "driver" / "tests" / "fixtures" / "add.c"
        if fixture.exists():
            out_hex = td / "smoke.hex"
            result = subprocess.run(
                [str(binary), str(fixture), "-o", str(out_hex)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise SystemExit(f"smoke compile failed: {result.stderr}")
            if not out_hex.exists() or out_hex.stat().st_size == 0:
                raise SystemExit("smoke compile produced no output")


def main():
    ap = argparse.ArgumentParser(description="Build toolchain-epiccc package")
    ap.add_argument("--zip", required=True, help="upstream epic-cc-*-x86_64-*.zip")
    ap.add_argument("--system", required=True, help="PlatformIO system, e.g. linux_x86_64, windows_amd64, or *")
    ap.add_argument("--version", required=True, help="package version, e.g. 0.0.3")
    ap.add_argument("--out", required=True, help="output tar.gz path")
    args = ap.parse_args()
    build(pathlib.Path(args.zip), args.system, args.version, pathlib.Path(args.out))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
