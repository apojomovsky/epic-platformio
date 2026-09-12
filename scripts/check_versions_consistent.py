#!/usr/bin/env python3
"""Fail the PR if packages/versions.json, packages/<name>/package.json and
platform.json disagree about a package's current version.

packages/versions.json is the single source of truth (docs/packages.md,
D-6): its highest-inserted version per package must match the
package.json in that package's dir, and platform.json's download URL for
that package must point at a release tag built from the same version.
Catches the exact drift class this repo shipped with before scripts/
sync_versions.py existed: a hand-edit to one file that forgot the others.
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = "apojomovsky/epic-platformio"


def load(path: pathlib.Path):
    return json.loads(path.read_text())


def main() -> int:
    versions_path = ROOT / "packages" / "versions.json"
    platform_path = ROOT / "platform.json"
    if not versions_path.exists() or not platform_path.exists():
        print("no packages/versions.json or platform.json yet, skipping")
        return 0

    versions = load(versions_path)
    platform = load(platform_path)
    errors = []

    for package, entries in versions.items():
        if not entries:
            continue
        current_version = list(entries.keys())[-1]

        pkg_json_path = ROOT / "packages" / package / "package.json"
        if pkg_json_path.exists():
            pkg_json = load(pkg_json_path)
            if pkg_json.get("version") != current_version:
                errors.append(
                    f"{pkg_json_path}: version {pkg_json.get('version')!r} != "
                    f"{current_version!r} (latest in packages/versions.json)"
                )

        platform_entry = platform.get("packages", {}).get(package)
        if platform_entry is None:
            continue
        url = platform_entry.get("version", "")
        expected_prefix = (
            f"https://github.com/{REPO}/releases/download/{package}-v{current_version}/"
        )
        if not url.startswith(expected_prefix):
            errors.append(
                f"platform.json packages.{package}.version {url!r} does not "
                f"point at tag {package}-v{current_version} (latest in packages/versions.json)"
            )

    if errors:
        print("version consistency check failed:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("packages/versions.json, package.json files and platform.json agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
