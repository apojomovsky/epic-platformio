#!/usr/bin/env python3
"""Board generator: the curated beta set in `boards/`, everything else in
`boards-experimental/` (PIO-6 epic-platformio#24, curating PIO-2
epic-platformio#45; docs/46 D-2 supersedes the old "no curation" call).

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

The split is by device, not by file: the CURATED table's six boards get
their board id from the chip's own name (docs/46 D-2: `pic16f877a`, not
`p16f877a`), carry the curated facts below, and live in `boards/`; every
other device gets a capability-only board in `boards-experimental/`, which
PlatformIO does not read on its own, so a user copies the one file they
want into their project's own `boards/` directory.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
BOARDS_DIR = REPO / "boards"
EXPERIMENTAL_DIR = REPO / "boards-experimental"

# The beta's six boards (docs/46 D-2), keyed by board id: the chip's own
# name lowercased (`pic16f877a`), while `build.mcu` stays epic-cc's
# `p16f877a`. Everything is curated, not derived: sizes from epic-cc's
# device TOML (flash words times two per D-7, ram_banks plus the fixed
# region), device names from each tool's own database (picpro has no
# 16F887 or 16F1xxx row), hazards from the DFP's config and pin data.
# f_cpu is where an example fixed a crystal; D-4 reads the code first.
CURATED = {
    "pic16f877a": {
        "maximum_size": 16384,
        "maximum_ram_size": 368,
        "f_cpu": "4000000L",
        "devices": {
            # Same per-package naming as the 1937 below: no bare 877A row.
            "minipro": "PIC16F877A@DIP40",
            "pk2cmd": "PIC16F877A",
            "picpro": "16F877A",
        },
        "hazards": {
            "pgm_pin": "RB3",
            "lvp_scheme": "pgm_pin",
            "osccal_word": None,
            "bandgap_bits": None,
        },
    },
    "pic16f887": {
        "maximum_size": 16384,
        "maximum_ram_size": 368,
        "f_cpu": "4000000L",
        "devices": {
            # No bare 887 row either, same per-package naming as the 1937.
            "minipro": "PIC16F887@DIP40",
            "pk2cmd": "PIC16F887",
        },
        "hazards": {
            "pgm_pin": "RB3",
            "lvp_scheme": "pgm_pin",
            "osccal_word": None,
            "bandgap_bits": None,
        },
    },
    "pic16f628a": {
        "maximum_size": 4096,
        "maximum_ram_size": 224,
        "f_cpu": None,
        "devices": {
            # The 628A is an 18-pin part: DIP18 is its minipro token.
            "minipro": "PIC16F628A@DIP18",
            "pk2cmd": "PIC16F628A",
            "picpro": "16F628A",
        },
        "hazards": {
            "pgm_pin": "RB4",
            "lvp_scheme": "pgm_pin",
            "osccal_word": None,
            "bandgap_bits": None,
        },
    },
    "pic12f675": {
        # 1023 words, not 1024: the top word holds the factory OSCCAL
        # calibration RETLW (epic-cc's p12f675.toml).
        "maximum_size": 2046,
        "maximum_ram_size": 64,
        "f_cpu": None,
        "devices": {
            "minipro": "PIC12F675",
            "pk2cmd": "PIC12F675",
            "picpro": "12F675",
        },
        "hazards": {
            "pgm_pin": None,
            "lvp_scheme": "none",
            "osccal_word": "0x3FF",
            "bandgap_bits": "13:12",
        },
    },
    "pic16f1937": {
        "maximum_size": 16384,
        "maximum_ram_size": 512,
        "f_cpu": None,
        "devices": {
            # minipro's database has no bare 16F1937 row, only per-package
            # ones, so the DIP40 token is the name it accepts.
            "minipro": "PIC16F1937@DIP40",
            "pk2cmd": "PIC16F1937",
        },
        "hazards": {
            "pgm_pin": None,
            "lvp_scheme": "key_sequence",
            "osccal_word": None,
            "bandgap_bits": None,
        },
    },
    "pic18f4550": {
        "maximum_size": 32768,
        "maximum_ram_size": 2048,
        "f_cpu": "20000000L",
        "devices": {
            # No bare 4550 row, same per-package naming as the 1937 above.
            "minipro": "PIC18F4550@DIP40",
            "pk2cmd": "PIC18F4550",
            "picpro": "18F4550",
        },
        "hazards": {
            "pgm_pin": "RB5",
            "lvp_scheme": "pgm_pin",
            "osccal_word": None,
            "bandgap_bits": None,
        },
    },
}

CURATED_PROTOCOL = "minipro"
CURATED_SUPPORT = "simulator"


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


def curated_bare(board_id: str) -> str:
    """Board id -> the matrix's bare device name: "pic16f877a" -> "16F877A"."""
    return board_id[len("pic"):].upper()


def board_json(entry: dict, board_id: str, dest: pathlib.Path, curated: dict | None) -> dict:
    """The board doc, merged onto whatever <dest>/<board_id>.json already
    has (hand-curated fields like upload.*/url survive unchanged), the
    capability fields always reflecting the freshly computed matrix.

    `curated` adds the facts no registry carries (sizes, per-tool device
    names, the D-9 hazards); None leaves a capability-only experimental
    board to PlatformIO's own defaults.
    """
    path = dest / f"{board_id}.json"
    doc = json.loads(path.read_text()) if path.exists() else {}
    build = doc.setdefault("build", {})
    build["mcu"] = entry["mcu"]
    build["toolchains"] = entry["toolchains"]
    build["framework_epichal_toolchains"] = entry["framework_toolchains"]
    if entry["family"] is not None:
        build["epichal_family"] = entry["family"]
    else:
        build.pop("epichal_family", None)
    # Registry, wizards and `pio boards` read the top-level frameworks
    # list, not build.framework_epichal_toolchains, so a board whose
    # family ships HAL content declares epichal here. A bare-metal-only
    # board carries no key at all rather than an empty list.
    if entry["framework_toolchains"]:
        doc["frameworks"] = ["epichal"]
    else:
        doc.pop("frameworks", None)
    bare = curated_bare(board_id) if curated else cc_name_to_bare(entry["mcu"])
    doc.setdefault("name", f"Microchip PIC{bare}")
    doc.setdefault("vendor", "Microchip")
    # PlatformIO requires a url field to even load a board.json; follows
    # the same https://www.microchip.com/en-us/product/<PART> scheme the
    # 3 hand-authored boards already used, since PlatformIO's schema
    # leaves no "omit if unverified" option. Not independently confirmed
    # to resolve for every one of these parts, only for the 3 originals.
    doc.setdefault("url", f"https://www.microchip.com/en-us/product/PIC{bare}")

    if curated is not None:
        # f_cpu is the board's crystal, which a curated board only states
        # when it is the hardware fact the three original boards already
        # recorded; D-4's clock check reads code or EPIC_CONFIG first and
        # treats board_build.f_cpu as the last source, so omitting it
        # leaves the choice to the user rather than guessing a frequency.
        if curated["f_cpu"] is not None:
            build["f_cpu"] = curated["f_cpu"]
        else:
            build.pop("f_cpu", None)
        doc["support"] = CURATED_SUPPORT
        upload = doc.setdefault("upload", {})
        upload["maximum_size"] = curated["maximum_size"]
        upload["maximum_ram_size"] = curated["maximum_ram_size"]
        upload["protocol"] = CURATED_PROTOCOL
        upload["devices"] = dict(curated["devices"])
        upload["hazards"] = dict(curated["hazards"])
    return doc


def _write(dest: pathlib.Path, board_id: str, entry: dict, curated: dict | None) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    doc = board_json(entry, board_id, dest, curated)
    (dest / f"{board_id}.json").write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")


def _prune(dest: pathlib.Path, keep: set[str]) -> int:
    removed = 0
    if not dest.is_dir():
        return removed
    for existing in dest.glob("*.json"):
        if existing.stem not in keep:
            existing.unlink()
            removed += 1
    return removed


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devices-json", required=True, type=pathlib.Path)
    ap.add_argument("--parts-txt", required=True, type=pathlib.Path)
    ap.add_argument("--modules-toml", required=True, type=pathlib.Path)
    ap.add_argument("--curated-dir", default=BOARDS_DIR, type=pathlib.Path)
    ap.add_argument("--experimental-dir", default=EXPERIMENTAL_DIR, type=pathlib.Path)
    args = ap.parse_args()

    devices = load_devices(args.devices_json)
    parts = load_parts(args.parts_txt)
    epiccc_families = load_epiccc_families(args.modules_toml)
    matrix = build_matrix(devices, parts, epiccc_families)

    curated_bares = {curated_bare(board_id) for board_id in CURATED}
    unknown = sorted(curated_bares - set(matrix))
    if unknown:
        sys.exit(f"curated board(s) not in either registry: {', '.join(unknown)}")

    for board_id, facts in CURATED.items():
        _write(args.curated_dir, board_id, matrix[curated_bare(board_id)], facts)
    for bare, entry in sorted(matrix.items()):
        if bare in curated_bares:
            continue
        _write(args.experimental_dir, entry["mcu"], entry, None)

    removed = _prune(args.curated_dir, set(CURATED))
    removed += _prune(
        args.experimental_dir,
        {entry["mcu"] for bare, entry in matrix.items() if bare not in curated_bares},
    )
    if removed:
        print(f"removed {removed} board(s) no longer in either registry")

    experimental = [e for bare, e in matrix.items() if bare not in curated_bares]
    epic_cc_only = sum(1 for e in experimental if e["toolchains"] == ["epic-cc"])
    xc8_only = sum(1 for e in experimental if e["toolchains"] == ["xc8"])
    both = sum(1 for e in experimental if len(e["toolchains"]) == 2)
    print(
        f"wrote {len(CURATED)} curated board(s) to {args.curated_dir} "
        f"and {len(experimental)} board(s) to {args.experimental_dir}: "
        f"{epic_cc_only} epic-cc-only, {xc8_only} xc8-only, {both} both-toolchain"
    )


if __name__ == "__main__":
    main()
