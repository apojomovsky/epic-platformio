#!/usr/bin/env python3
"""Fail the PR if packages/versions.json, packages/<name>/package.json and
platform.json disagree about a package's current version.

packages/versions.json is the single source of truth (docs/packages.md,
D-6): its newest version per package must match the
package.json in that package's dir, and platform.json's registry pin for
that package must name the same version under owner apojomovsky.
Catches the exact drift class this repo shipped with before scripts/
sync_versions.py existed: a hand-edit to one file that forgot the others.

Package versions are X.Y.Z, or X.Y.Z+pioN for a packaging-only revision
with no new upstream. platform.json's own version is the platform's
source of truth and must be plain X.Y.Z.
"""

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sync_versions import semver_key

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLATFORM_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


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

    platform_version = platform.get("version", "")
    if not PLATFORM_VERSION_RE.match(str(platform_version)):
        errors.append(
            f"platform.json version {platform_version!r} is not X.Y.Z "
            f"(the platform's source of truth, docs/packages.md)"
        )

    for package, entries in versions.items():
        if not entries:
            continue
        # Newest by version order, the same rule sync_versions.py applies
        # when it moves the live pointers, so an out-of-order re-cut
        # never reads as drift here.
        current_version = max(entries, key=semver_key)

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
        if (
            platform_entry.get("owner") == "apojomovsky"
            and platform_entry.get("version") == current_version
        ):
            continue
        errors.append(
            f"platform.json packages.{package} must pin owner apojomovsky "
            f"version {current_version!r} (latest in packages/versions.json), "
            f"got {platform_entry!r}"
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
