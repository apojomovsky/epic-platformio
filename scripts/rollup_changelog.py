#!/usr/bin/env python3
"""Roll an upstream repo's CHANGELOG.md section into this repo's own
release entry, so bumping a pinned tag shows what actually changed
upstream instead of just a version bump.

Run after git-cliff has already written this repo's own entry for
--repo-tag (e.g. via `git-cliff --tag <repo-tag> --unreleased --prepend
CHANGELOG.md`): this script finds that entry's header and inserts an
"### Upstream: <name> <old> -> <new>" subsection under it.

The caller fetches the upstream text (gh api .../CHANGELOG.md at the new
tag, or a git log between the two tags when no CHANGELOG.md exists there
yet) and passes it via --upstream-changelog or --fallback-log. Neither is
required: without one, a placeholder line is inserted rather than failing
the release.

Usage:
  rollup_changelog.py --changelog CHANGELOG.md \\
    --repo-tag toolchain-epiccc-v0.1.1 --upstream-name epic-cc \\
    --new-upstream-tag v0.1.1 --old-upstream-tag v0.1.0 \\
    --upstream-changelog /tmp/epic-cc-CHANGELOG.md
"""

import argparse
import pathlib
import re

HEADER_RE = re.compile(r"^## \[([^\]]+)\](?:\s*-\s*.+)?\s*$", re.MULTILINE)


def strip_v(tag):
    if tag is None:
        return None
    return tag[1:] if tag.startswith("v") else tag


def slice_upstream_changelog(text: str, old_ver: str | None, new_ver: str) -> str | None:
    """Return the text between the new version's header and the old
    version's header (exclusive of the old one), newest-first order.
    None if the new version's own header cannot be found.

    When old_ver's header is missing (upstream regenerated/squashed its
    changelog, or the pin skipped straight past a version it removed),
    falls back to the rest of the text rather than the next header down:
    a multi-version jump must not silently drop the versions in between
    just because the exact lower boundary could not be located. Over
    including (repeating an already-rolled-up older entry) is the safer
    failure mode for a changelog than under-reporting what shipped."""
    matches = list(HEADER_RE.finditer(text))
    starts = {m.group(1): m.start() for m in matches}
    if new_ver not in starts:
        return None
    if old_ver and old_ver in starts:
        segment_end = starts[old_ver]
    else:
        segment_end = len(text)
    return text[starts[new_ver]:segment_end].strip("\n")


def demote_headers(body: str) -> str:
    """Push every markdown header down two levels, so an upstream
    changelog slice (## [version], ### Group) nests cleanly under this
    repo's own "### Upstream: ..." subsection instead of appearing as a
    sibling heading of the same or higher level."""
    return re.sub(r"^(#+)(\s)", r"##\1\2", body, flags=re.MULTILINE)


def build_subsection(upstream_name: str, old_tag: str | None, new_tag: str,
                      body: str | None) -> str:
    arrow = f"{old_tag} -> {new_tag}" if old_tag else f"{new_tag} (initial tracked release)"
    heading = f"### Upstream: {upstream_name} {arrow}"
    if body:
        return f"{heading}\n\n{body}\n"
    return f"{heading}\n\nNo upstream changelog available at this tag.\n"


def insert_subsection(changelog_text: str, repo_tag: str, subsection: str) -> str:
    marker = f"## [{repo_tag}]"
    idx = changelog_text.find(marker)
    if idx == -1:
        raise SystemExit(
            f"repo tag header {marker!r} not found in changelog, "
            "run git-cliff to write the entry before rolling up"
        )
    line_end = changelog_text.find("\n", idx)
    line_end = line_end + 1 if line_end != -1 else len(changelog_text)
    next_header = changelog_text.find("\n## [", line_end)
    insert_at = next_header + 1 if next_header != -1 else len(changelog_text)

    prefix = changelog_text[:insert_at].rstrip("\n")
    suffix = changelog_text[insert_at:].lstrip("\n")
    body = subsection.strip("\n")
    if suffix:
        return f"{prefix}\n\n{body}\n\n{suffix}"
    return f"{prefix}\n\n{body}\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--changelog", required=True)
    ap.add_argument("--repo-tag", required=True, help="e.g. toolchain-epiccc-v0.1.1")
    ap.add_argument("--upstream-name", required=True, help="e.g. epic-cc")
    ap.add_argument("--new-upstream-tag", required=True, help="e.g. v0.1.1")
    ap.add_argument("--old-upstream-tag", help="previous pinned tag, empty for a first release")
    ap.add_argument("--upstream-changelog", help="path to the upstream repo's CHANGELOG.md at the new tag")
    ap.add_argument("--fallback-log", help="path to a plain `git log --oneline old..new` dump")
    args = ap.parse_args()

    body = None
    if args.upstream_changelog and pathlib.Path(args.upstream_changelog).exists():
        text = pathlib.Path(args.upstream_changelog).read_text()
        body = slice_upstream_changelog(text, strip_v(args.old_upstream_tag), strip_v(args.new_upstream_tag))
        if body:
            body = demote_headers(body)

    if body is None and args.fallback_log and pathlib.Path(args.fallback_log).exists():
        log_text = pathlib.Path(args.fallback_log).read_text().strip()
        if log_text:
            body = "\n".join(f"- {line}" for line in log_text.splitlines())

    subsection = build_subsection(args.upstream_name, args.old_upstream_tag,
                                   args.new_upstream_tag, body)

    path = pathlib.Path(args.changelog)
    updated = insert_subsection(path.read_text(), args.repo_tag, subsection)
    path.write_text(updated.rstrip("\n") + "\n")
    print(f"rolled up {args.upstream_name} {args.old_upstream_tag or '(none)'} -> "
          f"{args.new_upstream_tag} into {args.changelog}")


if __name__ == "__main__":
    main()
