#!/usr/bin/env python3
"""Write back a just-published package version to the three places that
must agree: packages/versions.json (the D-6 mapping, docs/packages.md),
packages/<name>/package.json, and platform.json's download URL. Before
this script existed those were hand-edited in a separate PR, which is
exactly how they drifted (stale platform.json version, stale package.json
version, upstream_url pointing at an old zip).

Usage:
  sync_versions.py --package toolchain-epiccc --pkg-version 0.1.1 \\
    --upstream-tag v0.1.1 \\
    --upstream-url-linux https://github.com/apojomovsky/epic-cc/releases/download/v0.1.1/epic-cc-0.1.1-x86_64-linux.zip \\
    --upstream-url-windows https://github.com/apojomovsky/epic-cc/releases/download/v0.1.1/epic-cc-0.1.1-x86_64-windows.zip

  sync_versions.py --package framework-epichal --pkg-version 0.6.0 \\
    --upstream-tag v0.6.0

Prints "old_upstream_tag=<value>" (empty if this is the package's first
entry) to stdout, the range start the changelog rollup needs, before this
script overwrites packages/versions.json with the new pin. Pass
--github-output to also append that line to a GITHUB_OUTPUT file.
"""

import argparse
import json
import pathlib
import re

REPO = "apojomovsky/epic-platformio"
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")

DEFAULT_ASSET = {
    "toolchain-epiccc": "toolchain-epiccc-linux_x86_64-{ver}.tar.gz",
    "framework-epichal": "framework-epichal-{ver}.tar.gz",
}


def semver_key(version: str) -> tuple[int, int, int]:
    return tuple(int(p) for p in version.split("."))


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: pathlib.Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def sync_versions_json(root: pathlib.Path, package: str, pkg_version: str,
                        upstream_tag: str, url_linux: str | None,
                        url_windows: str | None, note: str | None) -> str | None:
    path = root / "packages" / "versions.json"
    data = load_json(path)
    entries = data.setdefault(package, {})

    # The highest version already on record, other than pkg_version itself
    # (a re-cut of an already-published version must not treat itself as
    # its own predecessor): semver order, not dict insertion order, since
    # an out-of-order re-cut (see the is_latest comment below) can leave a
    # higher version earlier in the dict than a lower one added after it.
    old_upstream_tag = None
    prior = [v for v in entries if v != pkg_version]
    if prior:
        old_upstream_tag = entries[max(prior, key=semver_key)].get("upstream")

    entry = {"upstream": upstream_tag}
    if url_linux:
        entry["upstream_url_linux"] = url_linux
    if url_windows:
        entry["upstream_url_windows"] = url_windows
    if note:
        entry["note"] = note
    entries[pkg_version] = entry

    write_json(path, data)
    return old_upstream_tag


def sync_package_json(root: pathlib.Path, package: str, pkg_version: str) -> None:
    path = root / "packages" / package / "package.json"
    data = load_json(path)
    data["version"] = pkg_version
    write_json(path, data)


def sync_platform_json(root: pathlib.Path, package: str, pkg_version: str,
                        asset_name: str) -> None:
    path = root / "platform.json"
    data = load_json(path)
    tag = f"{package}-v{pkg_version}"
    url = f"https://github.com/{REPO}/releases/download/{tag}/{asset_name}"
    data["packages"][package]["version"] = url
    write_json(path, data)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--package", required=True,
                     choices=["toolchain-epiccc", "framework-epichal"])
    ap.add_argument("--pkg-version", required=True, help="e.g. 0.1.1")
    ap.add_argument("--upstream-tag", required=True, help="e.g. v0.1.1")
    ap.add_argument("--upstream-url-linux")
    ap.add_argument("--upstream-url-windows")
    ap.add_argument("--asset-name", help="release asset platform.json's URL should point at")
    ap.add_argument("--note")
    ap.add_argument("--root", default=".", help="repo root, default cwd")
    ap.add_argument("--github-output", help="also append old_upstream_tag= here")
    args = ap.parse_args()

    if not SEMVER_RE.match(args.pkg_version):
        raise SystemExit(f"--pkg-version {args.pkg_version!r} is not X.Y.Z")

    if args.package == "toolchain-epiccc" and not (args.upstream_url_linux and args.upstream_url_windows):
        raise SystemExit("toolchain-epiccc requires --upstream-url-linux and --upstream-url-windows")

    root = pathlib.Path(args.root)
    asset_name = args.asset_name or DEFAULT_ASSET[args.package].format(ver=args.pkg_version)

    old_upstream_tag = sync_versions_json(
        root, args.package, args.pkg_version, args.upstream_tag,
        args.upstream_url_linux, args.upstream_url_windows, args.note,
    )

    # packages/versions.json is an append-only log, so publishing an older
    # version out of order (a manual re-cut) is fine to record there. But
    # package.json and platform.json are live pointers: overwriting them
    # with anything but the newest known version would regress the
    # platform's actual install target.
    all_versions = load_json(root / "packages" / "versions.json")[args.package]
    is_latest = max(all_versions, key=semver_key) == args.pkg_version
    if is_latest:
        sync_package_json(root, args.package, args.pkg_version)
        sync_platform_json(root, args.package, args.pkg_version, asset_name)
    else:
        print(
            f"{args.pkg_version} is not the newest entry for {args.package} "
            f"in packages/versions.json, leaving package.json and platform.json alone"
        )

    line = f"old_upstream_tag={old_upstream_tag or ''}"
    print(line)
    if args.github_output:
        with open(args.github_output, "a") as f:
            f.write(line + "\n")


if __name__ == "__main__":
    main()
