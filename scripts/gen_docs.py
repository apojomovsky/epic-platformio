#!/usr/bin/env python3
"""Generated docs and registry-manifest checks (epic-platformio#114).

One script renders every generated page from its source data, so prose
never restates a fact that lives in a manifest:

- `docs/user/boards.md` from `boards/*.json` and `boards-experimental/*.json`
- `README.md` from `README.src.md` with `--8<--` includes resolved
- `registry-README.md` from the same source with relative links and
  images rewritten to absolute URLs (the registry shows a snapshot,
  so relative targets break there)

`--check` verifies the registry surface instead of writing files: at
most 20 keywords per manifest, a licence and readme field on every
package manifest, the owner-qualified platform in every example, and
no relative link left in the registry README.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import shared_includes

REPO = pathlib.Path(__file__).resolve().parent.parent
BOARDS_DIR = REPO / "boards"
BOARDS_EXPERIMENTAL_DIR = REPO / "boards-experimental"
BOARDS_MD = REPO / "docs" / "user" / "boards.md"
README_SRC = REPO / "README.src.md"
README_MD = REPO / "README.md"
REGISTRY_MD = REPO / "registry-README.md"
PLATFORM_JSON = REPO / "platform.json"
PACKAGES_DIR = REPO / "packages"
EXAMPLES_DIR = REPO / "examples"

GITHUB = "https://github.com/apojomovsky/epic-platformio"
BLOB = GITHUB + "/blob/master"
TREE = GITHUB + "/tree/master"
RAW = "https://raw.githubusercontent.com/apojomovsky/epic-platformio/master"
HUB_DEVICES = "https://apojomovsky.github.io/epic-docs/devices/"
OWNER_PLATFORM = "apojomovsky/epic8"
MAX_KEYWORDS = 20

# Canonical MCU stem to hub device-family slug. Core per stem comes from
# epic-cc crates/device/catalog/parts.toml through its CORE_LABELS map, so a
# new board whose stem is absent here fails loudly instead of linking wrong.
PART_FAMILY_SLUG = {
    "p10f320": "pic10f-pic14",
    "p10f322": "pic10f-pic14",
    "p12f509": "pic12f-pic12-baseline",
    "p12f629": "pic12f-pic14",
    "p12f675": "pic12f-pic14",
    "p12f683": "pic12f-pic14",
    "p16f1933": "pic16f-pic14e",
    "p16f1934": "pic16f-pic14e",
    "p16f1936": "pic16f-pic14e",
    "p16f1937": "pic16f-pic14e",
    "p16f1938": "pic16f-pic14e",
    "p16f1939": "pic16f-pic14e",
    "p16f505": "pic16f-pic12-baseline",
    "p16f54": "pic16f-pic12-baseline",
    "p16f57": "pic16f-pic12-baseline",
    "p16f627": "pic16f-pic14",
    "p16f627a": "pic16f-pic14",
    "p16f628": "pic16f-pic14",
    "p16f628a": "pic16f-pic14",
    "p16f630": "pic16f-pic14",
    "p16f631": "pic16f-pic14",
    "p16f639": "pic16f-pic14",
    "p16f648a": "pic16f-pic14",
    "p16f676": "pic16f-pic14",
    "p16f677": "pic16f-pic14",
    "p16f684": "pic16f-pic14",
    "p16f685": "pic16f-pic14",
    "p16f688": "pic16f-pic14",
    "p16f689": "pic16f-pic14",
    "p16f72": "pic16f-pic14",
    "p16f73": "pic16f-pic14",
    "p16f737": "pic16f-pic14",
    "p16f74": "pic16f-pic14",
    "p16f747": "pic16f-pic14",
    "p16f76": "pic16f-pic14",
    "p16f767": "pic16f-pic14",
    "p16f77": "pic16f-pic14",
    "p16f777": "pic16f-pic14",
    "p16f818": "pic16f-pic14",
    "p16f819": "pic16f-pic14",
    "p16f83": "pic16f-pic14",
    "p16f84": "pic16f-pic14",
    "p16f84a": "pic16f-pic14",
    "p16f87": "pic16f-pic14",
    "p16f871": "pic16f-pic14",
    "p16f872": "pic16f-pic14",
    "p16f873a": "pic16f-pic14",
    "p16f874": "pic16f-pic14",
    "p16f874a": "pic16f-pic14",
    "p16f876": "pic16f-pic14",
    "p16f876a": "pic16f-pic14",
    "p16f877": "pic16f-pic14",
    "p16f877a": "pic16f-pic14",
    "p16f88": "pic16f-pic14",
    "p16f882": "pic16f-pic14",
    "p16f883": "pic16f-pic14",
    "p16f884": "pic16f-pic14",
    "p16f886": "pic16f-pic14",
    "p16f887": "pic16f-pic14",
    "p16lf627a": "pic16lf-pic14",
    "p16lf628a": "pic16lf-pic14",
    "p16lf873a": "pic16lf-pic14",
    "p18f1220": "pic18f-pic18",
    "p18f1320": "pic18f-pic18",
    "p18f2220": "pic18f-pic18",
    "p18f2320": "pic18f-pic18",
    "p18f2321": "pic18f-pic18",
    "p18f2331": "pic18f-pic18",
    "p18f242": "pic18f-pic18",
    "p18f2420": "pic18f-pic18",
    "p18f2431": "pic18f-pic18",
    "p18f2450": "pic18f-pic18",
    "p18f2455": "pic18f-pic18",
    "p18f248": "pic18f-pic18",
    "p18f2480": "pic18f-pic18",
    "p18f2510": "pic18f-pic18",
    "p18f2515": "pic18f-pic18",
    "p18f252": "pic18f-pic18",
    "p18f2520": "pic18f-pic18",
    "p18f2525": "pic18f-pic18",
    "p18f2550": "pic18f-pic18",
    "p18f258": "pic18f-pic18",
    "p18f2580": "pic18f-pic18",
    "p18f2585": "pic18f-pic18",
    "p18f2610": "pic18f-pic18",
    "p18f2620": "pic18f-pic18",
    "p18f2680": "pic18f-pic18",
    "p18f26k22": "pic18f-pic18",
    "p18f27j53": "pic18f-pic18",
    "p18f4220": "pic18f-pic18",
    "p18f4320": "pic18f-pic18",
    "p18f4331": "pic18f-pic18",
    "p18f442": "pic18f-pic18",
    "p18f4431": "pic18f-pic18",
    "p18f4455": "pic18f-pic18",
    "p18f448": "pic18f-pic18",
    "p18f452": "pic18f-pic18",
    "p18f4520": "pic18f-pic18",
    "p18f4550": "pic18f-pic18",
    "p18f458": "pic18f-pic18",
    "p18f4580": "pic18f-pic18",
    "p18f4620": "pic18f-pic18",
    "p18f6520": "pic18f-pic18",
    "p18f6525": "pic18f-pic18",
    "p18f6585": "pic18f-pic18",
    "p18f6620": "pic18f-pic18",
    "p18f6621": "pic18f-pic18",
    "p18f6680": "pic18f-pic18",
    "p18f66j94": "pic18f-pic18",
    "p18f6720": "pic18f-pic18",
    "p18f8525": "pic18f-pic18",
    "p18f8585": "pic18f-pic18",
    "p18f8621": "pic18f-pic18",
    "p18f8680": "pic18f-pic18",
    "p18f87j11": "pic18f-pic18",
    "p18lf46k22": "pic18lf-pic18",
}

GENERATED_BY = "<!-- Generated by scripts/gen_docs.py, do not edit. -->"

INCLUDE_RE = re.compile(r'^[ \t]*--8<--[ \t]+["\']([^"\']+)["\'][ \t]*$')
MD_LINK_RE = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)\)")
HTML_ATTR_RE = re.compile(r"(srcset|src|href)\s*=\s*\"([^\"]+)\"")
LICENSE_RE = re.compile(r"^(LicenseRef-\S+|[A-Za-z0-9][A-Za-z0-9.+\-]*)$")
PLATFORM_RE = re.compile(r"^[ \t]*platform[ \t]*=[ \t]*(\S+)[ \t]*$")

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico")


def _rel(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _is_relative(target: str) -> bool:
    return not re.match(r"^(?:[a-zA-Z][a-zA-Z0-9+.\-]*:|#|/)", target)


def _abs_target(target: str, image: bool) -> str:
    path = target[2:] if target.startswith("./") else target
    if image:
        return RAW + "/" + path
    if (REPO / path.split("#")[0]).is_dir():
        return TREE + "/" + path
    return BLOB + "/" + path


def _split_spans(line: str):
    """Split a line into (is_code, text) spans on backtick runs."""
    parts = re.split(r"(`+)", line)
    code = False
    for part in parts:
        if part.startswith("`"):
            code = not code
            yield True, part
            continue
        yield code, part


def _absolutize_text(text: str) -> str:
    def md_link(match: re.Match) -> str:
        bang, label, target = match.groups()
        if not _is_relative(target):
            return match.group(0)
        image = bool(bang) or target.lower().endswith(IMAGE_EXTS)
        return f"{bang}[{label}]({_abs_target(target, image)})"

    def html_attr(match: re.Match) -> str:
        name, value = match.groups()
        if name == "srcset":
            items = []
            for item in value.split(","):
                tokens = item.strip().split()
                if tokens and _is_relative(tokens[0]):
                    tokens[0] = RAW + "/" + tokens[0].removeprefix("./")
                items.append(" ".join(tokens))
            return f"{name}=\"{', '.join(items)}\""
        if _is_relative(value):
            value = _abs_target(value, image=name != "href")
        return f'{name}="{value}"'

    return HTML_ATTR_RE.sub(html_attr, MD_LINK_RE.sub(md_link, text))


def absolutize_markdown(text: str) -> str:
    out = []
    fenced = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            out.append(line)
            continue
        if fenced:
            out.append(line)
            continue
        out.append("".join(
            part if code else _absolutize_text(part)
            for code, part in _split_spans(line)
        ))
    return "\n".join(out) + "\n"


def find_relative_links(text: str) -> list[str]:
    found = []
    fenced = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        for code, part in _split_spans(line):
            if code:
                continue
            for match in MD_LINK_RE.finditer(part):
                if _is_relative(match.group(3)):
                    found.append(match.group(3))
            for match in HTML_ATTR_RE.finditer(part):
                name, value = match.groups()
                urls = [v.split()[0] for v in value.split(",")] if name == "srcset" else [value]
                found.extend(u for u in urls if _is_relative(u))
    return found


def resolve_includes(text: str, seen: tuple = ()) -> str:
    out = []
    for line in text.splitlines():
        match = INCLUDE_RE.match(line)
        if not match:
            out.append(line)
            continue
        rel = match.group(1)
        if rel in seen:
            raise ValueError(f"include cycle: {' -> '.join([*seen, rel])}")
        path = REPO / rel
        if not path.is_file():
            raise ValueError(f"include not found: {rel}")
        out.append(resolve_includes(path.read_text(), (*seen, rel)).rstrip("\n"))
    return "\n".join(out) + "\n"


def render_readme() -> str:
    return GENERATED_BY + "\n" + resolve_includes(README_SRC.read_text())


def render_registry_readme() -> str:
    return GENERATED_BY + "\n" + absolutize_markdown(resolve_includes(README_SRC.read_text()))


def format_clock(f_cpu: str) -> str:
    """Render an `f_cpu` such as `4000000L` as `4 MHz`; unknown forms pass through."""
    match = re.fullmatch(r"(\d+)L?", f_cpu)
    if not match:
        return f_cpu
    hz = int(match.group(1))
    if hz % 1_000_000 == 0:
        return f"{hz // 1_000_000} MHz"
    if hz % 1_000 == 0:
        return f"{hz // 1_000} kHz"
    return f"{hz} Hz"


def _code(value: str) -> str:
    return value if value == "not set" else f"`{value}`"


def device_url(mcu: str) -> str:
    return f"{HUB_DEVICES}families/{PART_FAMILY_SLUG[mcu.lower()]}/"


def board_row(path: pathlib.Path, experimental: bool) -> tuple:
    doc = json.loads(path.read_text())
    build = doc.get("build", {})
    upload = doc.get("upload", {})
    name = str(doc.get("name", ""))
    part = name.removeprefix("Microchip ") or build.get("mcu", "").upper()
    support = "experimental" if experimental else str(doc.get("support", "not set"))
    clock = build.get("f_cpu")
    return (
        f"[{part}]({device_url(str(build.get('mcu', '')))})",
        path.stem,
        str(build.get("epichal_family", "") or "not set"),
        format_clock(str(clock)) if clock else "not set",
        support,
        str(upload.get("protocol", "") or "not set"),
    )


def render_boards() -> str:
    # Curated boards first, then the experimental definitions, each by board id.
    rows = [
        *(board_row(p, experimental=False) for p in sorted(BOARDS_DIR.glob("*.json"))),
        *(board_row(p, experimental=True)
          for p in sorted(BOARDS_EXPERIMENTAL_DIR.glob("*.json"))),
    ]
    lines = [
        GENERATED_BY,
        "# Boards",
        "",
        "Every board definition the platform ships. Boards marked `experimental` come",
        "from `boards-experimental/`: they have a definition but no curated support",
        "level or upload protocol yet.",
        "",
        "| Part | Board | Family | Clock | Support | Upload protocol |",
        "|---|---|---|---|---|---|",
        *[f"| {part} | `{board}` | {_code(family)} | {clock} | {support} | {_code(upload)} |"
          for part, board, family, clock, support, upload in rows],
    ]
    return "\n".join(lines) + "\n"


def check_keywords() -> list[str]:
    errors = []
    manifests = [PLATFORM_JSON, *sorted(PACKAGES_DIR.glob("*/package.json"))]
    for manifest in manifests:
        keywords = json.loads(manifest.read_text()).get("keywords", [])
        if len(keywords) > MAX_KEYWORDS:
            errors.append(
                f"{_rel(manifest)}: {len(keywords)} keywords, "
                f"at most {MAX_KEYWORDS}"
            )
    return errors


def check_package_manifests() -> list[str]:
    errors = []
    for manifest in sorted(PACKAGES_DIR.glob("*/package.json")):
        doc = json.loads(manifest.read_text())
        rel = _rel(manifest)
        if not doc.get("license") or not LICENSE_RE.match(str(doc["license"])):
            errors.append(f"{rel}: licence must be SPDX or LicenseRef")
        readme = doc.get("readme")
        if not readme:
            errors.append(f"{rel}: missing readme field")
        elif not (manifest.parent / readme).is_file():
            errors.append(f"{rel}: readme target {readme} does not exist")
    return errors


def check_examples() -> list[str]:
    errors = []
    for ini in sorted(EXAMPLES_DIR.glob("*/platformio.ini")):
        rel = _rel(ini)
        platforms = [
            m.group(1) for line in ini.read_text().splitlines()
            if (m := PLATFORM_RE.match(line))
        ]
        if not platforms:
            errors.append(f"{rel}: no platform line")
        elif any(p != OWNER_PLATFORM for p in platforms):
            errors.append(f"{rel}: platform must be {OWNER_PLATFORM}")
    return errors


def run_checks() -> list[str]:
    errors = [*check_keywords(), *check_package_manifests(), *check_examples()]
    left = find_relative_links(render_registry_readme())
    errors.extend(f"registry README: relative link left: {link}" for link in left)
    return errors


def generate() -> None:
    BOARDS_MD.parent.mkdir(parents=True, exist_ok=True)
    BOARDS_MD.write_text(render_boards())
    README_MD.write_text(render_readme())
    REGISTRY_MD.write_text(render_registry_readme())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="verify manifests and links, write nothing")
    args = parser.parse_args()
    problems = shared_includes.check(REPO)
    if problems:
        for problem in problems:
            print(f"gen_docs: {problem}", file=sys.stderr)
        return 1
    if args.check:
        errors = run_checks()
        for error in errors:
            print(f"gen_docs: {error}", file=sys.stderr)
        return 1 if errors else 0
    for missing in (README_SRC, BOARDS_DIR, BOARDS_EXPERIMENTAL_DIR):
        if not missing.exists():
            print(f"gen_docs: missing source {missing}", file=sys.stderr)
            return 1
    generate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
