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

# Top-level entries every bundle carries under the same name but with
# genuinely per-family content (confirmed against a real v0.6.0 5-family
# repack: MPLABX.md's own wiring steps differ per family, not a byte-for-
# byte match the way epic-common/VERSION/etc are). builder/main.py never
# reads any of these; they document manual MPLAB X project wiring, a
# different audience than a PlatformIO package, so they are dropped
# rather than reconciled or namespaced per family.
_SKIP_TOP_LEVEL = {
    "epic-hal-sources.json",
    "MPLABX.md",
    "QUICKSTART.md",
    "SUPPORT.md",
    "epic-hal.mk",
    "examples",
}


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
        # Extract every family bundle and read its own family slug up
        # front (keyed by slug, not by extraction path), so the union
        # copy below can tell each bundle's own content apart from what's
        # shared across bundles instead of guessing from copy order.
        bundles = {}
        for i, tar_path in enumerate(tar_paths):
            sub = td / f"bundle{i}"
            sub.mkdir()
            top = _extract_single(tar_path, sub)
            if not (top / "VERSION").exists():
                raise SystemExit(f"bundle {tar_path} missing VERSION")
            src = top / "epic-hal-sources.json"
            if not src.exists():
                raise SystemExit(f"bundle {tar_path} missing epic-hal-sources.json")
            manifest = json.loads(src.read_text())
            family = manifest.get("family")
            if not family:
                raise SystemExit(f"bundle {tar_path} epic-hal-sources.json missing family")
            slug = family.lower()
            if slug in bundles:
                raise SystemExit(f"duplicate family {slug!r}: {bundles[slug][1]} and {tar_path}")
            bundles[slug] = (top, tar_path, manifest)

        # A top-level entry name owned by exactly one bundle is that
        # family's own content (its hal dir, typically); a name shared by
        # more than one is assumed identical everywhere (epic-common,
        # epic-tick, ...) and copied once. family_entries lets validate()
        # below confirm each family's own content actually survived the
        # union, and the equality check during the copy itself catches a
        # same-name entry that turns out not to be identical, rather than
        # silently keeping whichever bundle's copy landed first.
        name_owners: dict[str, list[str]] = {}
        for slug, (top, _, _) in bundles.items():
            for child in top.iterdir():
                if child.name in _SKIP_TOP_LEVEL:
                    continue
                name_owners.setdefault(child.name, []).append(slug)

        root = td / "framework"
        root.mkdir()
        family_entries: dict[str, list[str]] = {slug: [] for slug in bundles}
        for slug, (top, tar_path, _) in bundles.items():
            for child in sorted(top.iterdir()):
                if child.name in _SKIP_TOP_LEVEL:
                    continue
                if len(name_owners[child.name]) == 1:
                    family_entries[slug].append(child.name)
                _merge_copy(child, root / child.name, child.name)

        # Rename each family's source manifest so the builder can find the
        # one matching the board's MCU, and record the epic-cc source slice.
        built_slugs = []
        for slug, (top, tar_path, manifest) in bundles.items():
            built_slugs.append(slug)
            doc = dict(manifest)
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

    validate(out_path, built_slugs, family_entries)


def _copy(src: pathlib.Path, dst: pathlib.Path):
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        for child in sorted(src.iterdir()):
            _copy(child, dst / child.name)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())


def _merge_copy(src: pathlib.Path, dst: pathlib.Path, rel: str) -> None:
    """Copy src into dst, additively: a shared core module bundled per
    family can carry a different subset of files depending on what that
    family's own hal_sources actually reference (confirmed against real
    epic-hal v0.6.0 data: pic14-midrange-core's file set differs between
    pic16f628a/pic16f87xa/pic16f88x, but every file more than one of them
    ships is byte-identical), so two bundles' copies of the same
    top-level name are a partial, additive overlap to merge, not
    necessarily an all-or-nothing match. Any real disagreement on a file
    both bundles actually ship is still a hard error, never a silent
    pick-one.
    """
    if not dst.exists():
        _copy(src, dst)
        return
    if src.is_dir() != dst.is_dir():
        raise SystemExit(f"{rel}: file/directory mismatch between bundles")
    if src.is_dir():
        for child in sorted(src.iterdir()):
            _merge_copy(child, dst / child.name, f"{rel}/{child.name}")
    elif src.read_bytes() != dst.read_bytes():
        raise SystemExit(
            f"{rel}: content differs between bundles for the same path, "
            f"refusing to silently pick one"
        )


def validate(tgz: pathlib.Path, slugs: list[str], family_entries: dict[str, list[str]] | None = None):
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        with tarfile.open(tgz, "r:gz") as tf:
            tf.extractall(td)
        if not (td / "package.json").exists():
            raise SystemExit("missing package.json after repack")
        d = json.loads((td / "package.json").read_text())
        if not d.get("version"):
            raise SystemExit("package.json missing version")
        # Every family actually packaged must have its source manifest.
        for slug in slugs:
            if not (td / f"epic-hal-sources-{slug}.json").exists():
                raise SystemExit(f"framework package missing epic-hal-sources-{slug}.json")
        # ... and whatever top-level content was uniquely its own (its
        # hal dir, typically) must have actually made it into the
        # tarball, not just its source manifest: a bug in the union copy
        # could otherwise drop a family's own content while its sidecar
        # JSON is still written independently.
        if family_entries:
            for slug, names in family_entries.items():
                for name in names:
                    if not (td / name).exists():
                        raise SystemExit(
                            f"framework package missing {slug}'s own {name!r} "
                            f"(dropped during packaging?)"
                        )


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
