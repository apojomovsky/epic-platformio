#!/usr/bin/env python3
"""Remove a leading "## [Unreleased]" section from CHANGELOG.md before
`git-cliff --unreleased --prepend` writes a fresh, tagged one over the same
commits.

`--prepend` only ever adds content, it never removes what it superseded:
run it twice in a row without this step and the commits that were under
"## [Unreleased]" stay there, duplicated verbatim under the newly inserted
release section. This only strips the section when it is the very first
one in the file (the shape git-cliff always produces); anything else is
left untouched rather than guessed at.

Usage:
  strip_stale_unreleased.py --changelog CHANGELOG.md
"""

import argparse
import pathlib
import re

HEADER_RE = re.compile(r"^## \[.*?\].*$", re.MULTILINE)


def strip_unreleased(text: str) -> str:
    matches = list(HEADER_RE.finditer(text))
    if not matches:
        return text
    first = matches[0]
    if not first.group(0).startswith("## [Unreleased]"):
        return text
    later = matches[1:]
    end = later[0].start() if later else len(text)
    prefix = text[:first.start()].rstrip("\n")
    suffix = text[end:].lstrip("\n")
    if suffix:
        return f"{prefix}\n\n{suffix}"
    return prefix + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--changelog", required=True)
    args = ap.parse_args()

    path = pathlib.Path(args.changelog)
    before = path.read_text()
    after = strip_unreleased(before)
    if after != before:
        path.write_text(after)
        print(f"stripped stale Unreleased section from {args.changelog}")
    else:
        print(f"no leading Unreleased section in {args.changelog}, left as is")


if __name__ == "__main__":
    main()
