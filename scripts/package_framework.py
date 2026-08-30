#!/usr/bin/env python3
"""Build a framework-epichal PlatformIO package from an epic-hal family bundle.

Blocked by HAL-5 for the final distribution shape, but the tooling is usable
now against existing family tarballs for validation.

Usage:
  package_framework.py --tar epic-hal-pic16f87xa-v0.4.0.tar.gz --version 0.4.0 --out framework-epichal-0.4.0.tar.gz
"""

import argparse
import json
import pathlib
import tarfile
import tempfile


TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / "packages" / "framework-epichal" / "package.json"


def build(tar_path: pathlib.Path, version: str, out_path: pathlib.Path):
    data = json.loads(TEMPLATE.read_text())
    data["version"] = version
    # Framework is platform-independent.
    data.pop("system", None)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        with tarfile.open(tar_path, "r:gz") as tf:
            tf.extractall(td)
        tops = [p for p in td.iterdir() if p.is_dir()]
        if len(tops) != 1:
            raise SystemExit(f"expected one top-level dir in {tar_path}, got {tops}")
        top = tops[0]
        if not (top / "VERSION").exists():
            raise SystemExit(f"bundle {tar_path} missing VERSION")
        (top / "package.json").write_text(json.dumps(data, indent=2) + "\n")

        with tarfile.open(out_path, "w:gz") as out:
            for child in sorted(top.iterdir()):
                out.add(child, arcname=child.name)

    # Validate.
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        with tarfile.open(out_path, "r:gz") as tf:
            tf.extractall(td)
        if not (td / "package.json").exists():
            raise SystemExit("missing package.json after repack")
        d = json.loads((td / "package.json").read_text())
        if not d.get("version"):
            raise SystemExit("package.json missing version")


def main():
    ap = argparse.ArgumentParser(description="Build framework-epichal package")
    ap.add_argument("--tar", required=True, help="upstream epic-hal family tar.gz")
    ap.add_argument("--version", required=True, help="package version, e.g. 0.4.0")
    ap.add_argument("--out", required=True, help="output tar.gz path")
    args = ap.parse_args()
    build(pathlib.Path(args.tar), args.version, pathlib.Path(args.out))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
