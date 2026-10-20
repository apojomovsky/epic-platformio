#!/usr/bin/env python3
"""Fail the PR when a board JSON misses a key PlatformIO requires.

CLion project creation fails without top-level `frameworks`
(epic-platformio#125, #167), and ci.yml only syntax-linted the
manifests, so a schema-incomplete board shipped silently. Curated
boards in boards/ need build, frameworks, name, upload, url and
vendor, plus a debug section unless waived below; generated boards in
boards-experimental/ need the frameworks key the generator always
emits (empty list where no HAL family applies).
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

REQUIRED_BOARD_KEYS = frozenset(
    {"build", "frameworks", "name", "upload", "url", "vendor"}
)

REQUIRED_PLATFORM_KEYS = frozenset({"name", "version"})

# Boards with no debug section, and why: the sim behind `pio debug`
# (epic-cc-gdbserver) covers the pic14/pic18 cores in
# gen_boards.DEBUG_CORES only, and the 1937 is enhanced mid-range.
DEBUG_WAIVED = {
    "pic16f1937": "pic14e core, no simulator in the pinned toolchain",
}


def load(path: pathlib.Path):
    return json.loads(path.read_text())


def check_board(doc, board_id: str, *, curated: bool) -> list:
    errors = []
    wanted = REQUIRED_BOARD_KEYS if curated else frozenset({"frameworks"})
    for key in sorted(wanted - set(doc)):
        errors.append(f"{board_id}.json: missing required key {key!r}")
    if "frameworks" in doc and not isinstance(doc["frameworks"], list):
        errors.append(f"{board_id}.json: 'frameworks' must be a list")
    if curated and "debug" not in doc and board_id not in DEBUG_WAIVED:
        errors.append(f"{board_id}.json: missing 'debug' (or waive it in DEBUG_WAIVED)")
    return errors


def check_tree(root: pathlib.Path) -> list:
    errors = []
    for path in sorted((root / "boards").glob("*.json")):
        errors.extend(check_board(load(path), path.stem, curated=True))
    for path in sorted((root / "boards-experimental").glob("*.json")):
        errors.extend(check_board(load(path), path.stem, curated=False))
    platform = load(root / "platform.json")
    for key in sorted(REQUIRED_PLATFORM_KEYS - set(platform)):
        errors.append(f"platform.json: missing required key {key!r}")
    return errors


def main() -> int:
    errors = check_tree(ROOT)
    for error in errors:
        print(f"error: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
