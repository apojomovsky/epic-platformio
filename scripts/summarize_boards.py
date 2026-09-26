#!/usr/bin/env python3
"""Human-readable summary of a gen_boards.py regeneration (PIO-7,
epic-platformio#25), for the pull request body the boards-refresh
workflow opens: additions, removals, and capability changes, not a raw
`boards/*.json` diff a reviewer would otherwise have to re-derive by eye.

The curated beta set (docs/46 D-2) and `boards-experimental/` are
reported separately, since they carry different promises: a curated
board's change is a support statement, an experimental board's is
informational.

Usage:
  summarize_boards.py --before-dir /tmp/boards-before --after-dir boards \
    --before-experimental-dir /tmp/boards-experimental-before \
    --after-experimental-dir boards-experimental --out /tmp/pr-body.md
"""

from __future__ import annotations

import argparse
import json
import pathlib


def load_boards(dir_path: pathlib.Path) -> dict[str, dict]:
    if not dir_path.is_dir():
        return {}
    return {p.stem: json.loads(p.read_text()) for p in dir_path.glob("*.json")}


def _caps(doc: dict) -> tuple[list, list]:
    build = doc.get("build", {})
    return build.get("toolchains", []), build.get("framework_epichal_toolchains", [])


def _section(title: str, lines: list[str]) -> str:
    return "\n".join([f"### {title}"] + lines)


def diff_summary(
    before: dict[str, dict],
    after: dict[str, dict],
    label: str = "board",
) -> str:
    added = sorted(after.keys() - before.keys())
    removed = sorted(before.keys() - after.keys())
    changed = []
    for board_id in sorted(before.keys() & after.keys()):
        b_tc, b_fw = _caps(before[board_id])
        a_tc, a_fw = _caps(after[board_id])
        if b_tc != a_tc or b_fw != a_fw:
            changed.append((board_id, b_tc, b_fw, a_tc, a_fw))

    sections = []
    if added:
        lines = [f"- `{board_id}`: toolchains={_caps(after[board_id])[0]}, "
                 f"framework_epichal_toolchains={_caps(after[board_id])[1]}"
                 for board_id in added]
        sections.append(_section(f"{len(added)} new {label}(s)", lines))
    if removed:
        sections.append(
            _section(
                f"{len(removed)} {label}(s) removed (no longer known to either registry)",
                [f"- `{board_id}`" for board_id in removed],
            )
        )
    if changed:
        lines = [
            f"- `{board_id}`: toolchains {b_tc} → {a_tc}, "
            f"framework_epichal_toolchains {b_fw} → {a_fw}"
            for board_id, b_tc, b_fw, a_tc, a_fw in changed
        ]
        sections.append(_section(f"{len(changed)} {label}(s) with capability changes", lines))
    if not sections:
        return f"No {label} changes."
    return "\n\n".join(sections)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--before-dir", required=True, type=pathlib.Path)
    ap.add_argument("--after-dir", required=True, type=pathlib.Path)
    ap.add_argument("--before-experimental-dir", type=pathlib.Path)
    ap.add_argument("--after-experimental-dir", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path, help="write summary here instead of stdout")
    args = ap.parse_args()

    before = load_boards(args.before_dir)
    after = load_boards(args.after_dir)
    parts = [
        diff_summary(before, after, "curated board"),
    ]
    if args.before_experimental_dir is not None and args.after_experimental_dir is not None:
        parts.append(
            diff_summary(
                load_boards(args.before_experimental_dir),
                load_boards(args.after_experimental_dir),
                "experimental board",
            )
        )
    if all(p.startswith("No ") for p in parts):
        summary = "No board changes."
    else:
        summary = "\n\n".join(p for p in parts if not p.startswith("No "))

    if args.out:
        args.out.write_text(summary + "\n")
    else:
        print(summary)


if __name__ == "__main__":
    main()
