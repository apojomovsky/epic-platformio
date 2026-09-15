#!/usr/bin/env python3
"""Human-readable summary of a gen_boards.py regeneration (PIO-7,
epic-platformio#25), for the pull request body the boards-refresh
workflow opens: additions, removals, and capability changes, not a raw
`boards/*.json` diff a reviewer would otherwise have to re-derive by eye.

Usage:
  summarize_boards.py --before-dir /tmp/boards-before --after-dir boards \
    --out /tmp/pr-body.md
"""

from __future__ import annotations

import argparse
import json
import pathlib


def load_boards(dir_path: pathlib.Path) -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text()) for p in dir_path.glob("p*.json")}


def _caps(doc: dict) -> tuple[list, list]:
    build = doc.get("build", {})
    return build.get("toolchains", []), build.get("framework_epichal_toolchains", [])


def diff_summary(before: dict[str, dict], after: dict[str, dict]) -> str:
    added = sorted(after.keys() - before.keys())
    removed = sorted(before.keys() - after.keys())
    changed = []
    for mcu in sorted(before.keys() & after.keys()):
        b_tc, b_fw = _caps(before[mcu])
        a_tc, a_fw = _caps(after[mcu])
        if b_tc != a_tc or b_fw != a_fw:
            changed.append((mcu, b_tc, b_fw, a_tc, a_fw))

    if not added and not removed and not changed:
        return "No board changes."

    sections = []
    if added:
        lines = [f"### {len(added)} new board(s)"]
        for mcu in added:
            tc, fw = _caps(after[mcu])
            lines.append(f"- `{mcu}`: toolchains={tc}, framework_epichal_toolchains={fw}")
        sections.append("\n".join(lines))
    if removed:
        lines = [f"### {len(removed)} board(s) removed (no longer known to either registry)"]
        lines += [f"- `{mcu}`" for mcu in removed]
        sections.append("\n".join(lines))
    if changed:
        lines = [f"### {len(changed)} board(s) with capability changes"]
        for mcu, b_tc, b_fw, a_tc, a_fw in changed:
            lines.append(
                f"- `{mcu}`: toolchains {b_tc} → {a_tc}, "
                f"framework_epichal_toolchains {b_fw} → {a_fw}"
            )
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--before-dir", required=True, type=pathlib.Path)
    ap.add_argument("--after-dir", required=True, type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path, help="write summary here instead of stdout")
    args = ap.parse_args()

    before = load_boards(args.before_dir)
    after = load_boards(args.after_dir)
    summary = diff_summary(before, after)

    if args.out:
        args.out.write_text(summary + "\n")
    else:
        print(summary)


if __name__ == "__main__":
    main()
