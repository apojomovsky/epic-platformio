#!/usr/bin/env python3
"""Device x capability matrix generator (PIO-6, epic-platformio#24): a
PlatformIO board per device either epic-cc or epic-hal supports, at
whatever capability level it actually has.

Joins three inputs, none of which require linking either upstream repo:
  --devices-json  epic-cc's release-bundle device manifest (CC-7):
                  [{"name": "p16f877a", "core": "pic14", "pack": ...}, ...]
  --parts-txt     epic-hal's release-bundle part-to-family map:
                  "16F877A pic16f87xa" per line (bundlegen.emit_parts_map)
  --modules-toml  epic-hal's epic-common/manifest/modules.toml, read only
                  for which families declare an epiccc_sources key

The join key is the bare device name (epic-hal's own spelling, "16F877A"),
since epic-cc's own name is always exactly "p" + that name lowercased
(crates/device/src/lib.rs's resolve(), see epic-cc#428 / epic-hal#162):
not a guess, a fixed structural fact once both sides are already in their
own canonical form.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
BOARDS_DIR = REPO / "boards"


def load_devices(path: pathlib.Path) -> list[dict]:
    return json.loads(path.read_text())


def load_parts(path: pathlib.Path) -> dict[str, str]:
    """bare device name -> epic-hal family slug, e.g. "16F877A" -> "pic16f87xa"."""
    parts = {}
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        fields = line.split()
        if len(fields) != 2:
            sys.exit(f"{path}:{lineno}: expected '<part> <family>', got {line!r}")
        bare, fam = fields
        parts[bare] = fam
    return parts


def load_epiccc_families(path: pathlib.Path) -> dict[str, bool]:
    """epic-hal family slug (lowercased, matching parts.txt's own spelling,
    e.g. "pic16f87xa") -> whether it declares epiccc_sources.

    A targeted scan, not a TOML parser: only `[families.NAME]` section
    boundaries and one key's presence within each matter here. re.split
    already cuts the text at every section boundary, so each `scoped`
    slice below is exactly one family's own content.
    """
    text = path.read_text()
    sections = re.split(r"^\[families\.", text, flags=re.M)[1:]
    result = {}
    for section in sections:
        name, scoped = section.split("]", 1)
        result[name.lower()] = bool(re.search(r"^epiccc_sources\s*=", scoped, flags=re.M))
    return result


def cc_name_to_bare(name: str) -> str:
    """"p16f877a" -> "16F877A": the inverse of epic-cc's resolve()."""
    return name[1:].upper() if name[:1].lower() == "p" else name.upper()


def build_matrix(
    devices: list[dict], parts: dict[str, str], epiccc_families: dict[str, bool]
) -> dict[str, dict]:
    """bare device name -> capability facts, per docs/platform-decisions.md's
    "Boards: generated from epic-cc/epic-hal's own registries" section."""
    cc_by_bare = {cc_name_to_bare(d["name"]): d["name"] for d in devices}
    entries = {}
    for bare in sorted(set(cc_by_bare) | set(parts)):
        cc_name = cc_by_bare.get(bare)
        family = parts.get(bare)
        toolchains = []
        if cc_name is not None:
            toolchains.append("epic-cc")
        if family is not None:
            toolchains.append("xc8")
        framework_toolchains = []
        if family is not None:
            if cc_name is not None and epiccc_families.get(family):
                framework_toolchains = ["epic-cc", "xc8"]
            else:
                framework_toolchains = ["xc8"]
        entries[bare] = {
            "mcu": "p" + bare.lower(),
            "cc_name": cc_name,
            "family": family,
            "toolchains": toolchains,
            "framework_toolchains": framework_toolchains,
        }
    return entries


def board_json(bare: str, entry: dict, boards_dir: pathlib.Path) -> dict:
    """The board doc, merged onto whatever <boards_dir>/<mcu>.json already
    has (hand-curated fields like upload.*/url survive unchanged), the
    capability fields always reflecting the freshly computed matrix."""
    mcu = entry["mcu"]
    existing_path = boards_dir / f"{mcu}.json"
    doc = json.loads(existing_path.read_text()) if existing_path.exists() else {}
    build = doc.setdefault("build", {})
    build["mcu"] = mcu
    build["toolchains"] = entry["toolchains"]
    build["framework_epichal_toolchains"] = entry["framework_toolchains"]
    if entry["family"] is not None:
        build["epichal_family"] = entry["family"]
    else:
        build.pop("epichal_family", None)
    doc.setdefault("name", f"Microchip PIC{bare}")
    doc.setdefault("vendor", "Microchip")
    # PlatformIO requires a url field to even load a board.json; follows
    # the same https://www.microchip.com/en-us/product/<PART> scheme the
    # 3 hand-authored boards already used, since PlatformIO's schema
    # leaves no "omit if unverified" option. Not independently confirmed
    # to resolve for every one of these parts, only for the 3 originals.
    doc.setdefault("url", f"https://www.microchip.com/en-us/product/PIC{bare}")
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devices-json", required=True, type=pathlib.Path)
    ap.add_argument("--parts-txt", required=True, type=pathlib.Path)
    ap.add_argument("--modules-toml", required=True, type=pathlib.Path)
    ap.add_argument("--out-dir", default=BOARDS_DIR, type=pathlib.Path)
    args = ap.parse_args()

    devices = load_devices(args.devices_json)
    parts = load_parts(args.parts_txt)
    epiccc_families = load_epiccc_families(args.modules_toml)
    matrix = build_matrix(devices, parts, epiccc_families)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    live_mcus = {entry["mcu"] for entry in matrix.values()}
    removed = 0
    for existing in args.out_dir.glob("p*.json"):
        if existing.stem not in live_mcus:
            existing.unlink()
            removed += 1
    for bare, entry in matrix.items():
        path = args.out_dir / f"{entry['mcu']}.json"
        doc = board_json(bare, entry, args.out_dir)
        path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")

    if removed:
        print(f"removed {removed} board(s) no longer in either registry")
    epic_cc_only = sum(1 for e in matrix.values() if e["toolchains"] == ["epic-cc"])
    xc8_only = sum(1 for e in matrix.values() if e["toolchains"] == ["xc8"])
    both = sum(1 for e in matrix.values() if len(e["toolchains"]) == 2)
    print(
        f"wrote {len(matrix)} boards to {args.out_dir}: "
        f"{epic_cc_only} epic-cc-only, {xc8_only} xc8-only, {both} both-toolchain"
    )


if __name__ == "__main__":
    main()
