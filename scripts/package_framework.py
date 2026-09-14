#!/usr/bin/env python3
"""Build a framework-epichal PlatformIO package from epic-hal family bundles.

The framework package is the union of every supported family bundle: the
shared modules (epic-common, epic-tick, ...) are copied once, each family's
hal dir is kept separate, and each family's source manifest is renamed to
`epic-hal-sources-<family>.json` so the builder can pick the right one from
the board's MCU. Every family slug (the hal dir name, the manifest suffix)
comes from each bundle's own epic-hal-sources.json "family" field, not a
hardcoded list here: a new family bundle (PIO-7, epic-platformio#25) needs
no change to this script, only an extra --tar.

Usage:
  package_framework.py \
    --tar epic-hal-pic16f87xa-v0.4.0.tar.gz \
    --tar epic-hal-pic16f88x-v0.4.0.tar.gz \
    --tar epic-hal-pic18fxx5x-v0.4.0.tar.gz \
    --version 0.4.0 --out framework-epichal-0.4.0.tar.gz
"""

import argparse
import json
import pathlib
import tarfile
import tempfile


TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / "packages" / "framework-epichal" / "package.json"


def _read_epiccc_sources(manifest_path: pathlib.Path) -> dict:
    """Read every family's epic-cc source slice from the epic-hal manifest,
    keyed by the same lowercased slug the bundle's own family field uses.

    The epic-cc path links a smaller, conformant source set than the full
    XC8 set (the full set uses XC8-only syntax and exceeds the 877A's GPR
    capacity). The manifest's `epiccc_sources` slice is that set; it is
    recorded per family in the framework package so the builder can pick it.
    """
    import tomllib
    data = tomllib.loads(manifest_path.read_text())
    return {
        fam_name.lower(): fam.get("epiccc_sources", [])
        for fam_name, fam in data["families"].items()
    }


def _extract_single(tar_path: pathlib.Path, td: pathlib.Path) -> pathlib.Path:
    with tarfile.open(tar_path, "r:gz") as tf:
        tf.extractall(td)
    tops = [p for p in td.iterdir() if p.is_dir()]
    if len(tops) != 1:
        raise SystemExit(f"expected one top-level dir in {tar_path}, got {tops}")
    return tops[0]


def build(tar_paths: list[pathlib.Path], version: str, out_path: pathlib.Path,
          epiccc_sources: dict | None = None, hal_repo: pathlib.Path | None = None):
    data = json.loads(TEMPLATE.read_text())
    data["version"] = version
    # Framework is platform-independent.
    data.pop("system", None)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        # Extract every family bundle into its own dir.
        bundles = {}
        for i, tar_path in enumerate(tar_paths):
            sub = td / f"bundle{i}"
            sub.mkdir()
            top = _extract_single(tar_path, sub)
            if not (top / "VERSION").exists():
                raise SystemExit(f"bundle {tar_path} missing VERSION")
            bundles[top] = tar_path

        # Every bundle's top-level entries land in the union, first one in
        # wins: the shared modules (epic-common, epic-tick, ...) are
        # identical byte for byte across bundles, so re-copying from a
        # later one would be wasted work, not a correctness issue, but
        # skipping it once it exists keeps the union O(bundles) instead of
        # O(bundles^2). Each bundle's own hal dir is unique by construction
        # (the family slug names it), so it never collides with another
        # bundle's content.
        root = td / "framework"
        root.mkdir()
        for top, tar_path in bundles.items():
            for child in sorted(top.iterdir()):
                if child.name == "epic-hal-sources.json":
                    continue
                dst = root / child.name
                if dst.exists():
                    continue
                _copy(child, dst)

        # Rename each family's source manifest so the builder can find the
        # one matching the board's MCU, and record the epic-cc source slice.
        built_slugs = []
        for top, tar_path in bundles.items():
            src = top / "epic-hal-sources.json"
            if not src.exists():
                raise SystemExit(f"bundle {tar_path} missing epic-hal-sources.json")
            manifest = json.loads(src.read_text())
            family = manifest.get("family")
            if not family:
                raise SystemExit(f"bundle {tar_path} epic-hal-sources.json missing family")
            slug = family.lower()
            built_slugs.append(slug)
            doc = json.loads(src.read_text())
            if epiccc_sources and slug in epiccc_sources:
                doc["epiccc_sources"] = epiccc_sources[slug]
                # Not in the release bundles: copy from the epic-hal
                # checkout at the manifest's own path (builder/main.py
                # resolves each entry as join(fw_dir, s)), not one rebuilt
                # from a per-family hal dir, which broke once a family's
                # slice moved into the shared pic14-midrange-core.
                if hal_repo:
                    for s in epiccc_sources[slug]:
                        if "/src/epiccc/" not in s:
                            continue
                        src_file = hal_repo / s
                        if not src_file.exists():
                            raise SystemExit(f"epic-cc source {src_file} not found in epic-hal")
                        dst = root / s
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        dst.write_bytes(src_file.read_bytes())
            (root / f"epic-hal-sources-{slug}.json").write_text(
                json.dumps(doc, indent=2, sort_keys=True) + "\n"
            )

        (root / "package.json").write_text(json.dumps(data, indent=2) + "\n")

        with tarfile.open(out_path, "w:gz") as out:
            for child in sorted(root.iterdir()):
                out.add(child, arcname=child.name)

    validate(out_path, built_slugs)


def _copy(src: pathlib.Path, dst: pathlib.Path):
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        for child in sorted(src.iterdir()):
            _copy(child, dst / child.name)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())


def validate(tgz: pathlib.Path, slugs: list[str]):
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        with tarfile.open(tgz, "r:gz") as tf:
            tf.extractall(td)
        if not (td / "package.json").exists():
            raise SystemExit("missing package.json after repack")
        d = json.loads((td / "package.json").read_text())
        if not d.get("version"):
            raise SystemExit("package.json missing version")
        # Every family actually packaged must have its source manifest
        # (the hal dir itself is trusted from the copy step above: its
        # exact name isn't independently known here, only its slug).
        for slug in slugs:
            if not (td / f"epic-hal-sources-{slug}.json").exists():
                raise SystemExit(f"framework package missing epic-hal-sources-{slug}.json")


def main():
    ap = argparse.ArgumentParser(description="Build framework-epichal package")
    ap.add_argument("--tar", required=True, action="append",
                    help="upstream epic-hal family tar.gz (repeat per family)")
    ap.add_argument("--version", required=True, help="package version, e.g. 0.4.0")
    ap.add_argument("--out", required=True, help="output tar.gz path")
    ap.add_argument("--manifest", help="epic-hal modules.toml, for the epic-cc source slice")
    ap.add_argument("--hal-repo", help="epic-hal checkout, for the epic-cc source files")
    args = ap.parse_args()
    epiccc = _read_epiccc_sources(pathlib.Path(args.manifest)) if args.manifest else None
    hal_repo = pathlib.Path(args.hal_repo) if args.hal_repo else None
    build([pathlib.Path(t) for t in args.tar], args.version, pathlib.Path(args.out), epiccc, hal_repo)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
