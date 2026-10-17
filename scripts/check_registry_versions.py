#!/usr/bin/env python3
"""Refuse a repo state that republishes under an already-published version.

Registry versions are immutable, so moving a pin under a published
platform version strands registry users: 0.1.1 shipped with the
0.4.0+pio1 toolchain pin and #159 moved the repo's 0.1.1 pin to 0.5.0
(epic-platformio#163). When the repo's platform version is already
published, the published platform.json must carry the same version and
every packages.* pin. Tool listings check version identity only: the
registry derives version names from the published manifests, and the
artifacts themselves are 100MB+ with per-artifact system stamping, so
downloading them buys nothing. A version not yet on the registry
passes. Any registry failure fails loudly, never silently.

Tests use recorded fixtures and never touch the network
(scripts/test_check_registry_versions.py). REGISTRY_CHECK=skip bypasses
the gate for offline local runs only and is refused inside CI.
"""

import io
import json
import os
import pathlib
import sys
import tarfile
import urllib.error
import urllib.request

REGISTRY = "https://api.registry.platformio.org/v3/packages"
OWNER = "apojomovsky"
TIMEOUT_SECONDS = 30

LISTINGS = (
    {"registry_type": "platform", "name": "epic8",
     "repo_manifest": "platform.json", "member": "platform.json"},
    {"registry_type": "tool", "name": "toolchain-epiccc",
     "repo_manifest": "packages/toolchain-epiccc/package.json"},
    {"registry_type": "tool", "name": "framework-epichal",
     "repo_manifest": "packages/framework-epichal/package.json"},
)


class RegistryError(Exception):
    """Anything that stops the gate from proving the repo matches."""


def fetch_bytes(url):
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            return response.read()
    except (urllib.error.URLError, OSError) as exc:
        raise RegistryError(f"cannot fetch {url}: {exc}") from exc


def fetch_json(url, fetch):
    try:
        return json.loads(fetch(url))
    except ValueError as exc:
        raise RegistryError(f"cannot parse registry response from {url}: {exc}") from exc


def published_files(listing, url):
    # Version entries carry their artifact list; the first file's
    # download URL is the release tarball the manifest ships in.
    try:
        return {v["name"]: v["files"][0]["download_url"]
                for v in listing["versions"]}
    except (KeyError, TypeError, IndexError) as exc:
        raise RegistryError(
            f"unexpected listing shape at {url}: {exc}") from exc


def extract_manifest(tarball, member, url):
    try:
        with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as archive:
            try:
                extracted = archive.extractfile(member)
            except KeyError as exc:
                raise RegistryError(f"{url} has no {member}") from exc
            if extracted is None:
                raise RegistryError(f"{url} has no {member}")
            return json.loads(extracted.read())
    except (tarfile.TarError, EOFError) as exc:
        raise RegistryError(f"cannot unpack {url}: {exc}") from exc
    except ValueError as exc:
        raise RegistryError(
            f"cannot parse {member} from {url}: {exc}") from exc


def compare_platform(repo, published):
    diffs = []
    if published.get("version") != repo.get("version"):
        diffs.append(
            f"version: repo {repo.get('version')}, "
            f"registry {published.get('version')}")
    repo_packages = repo.get("packages", {})
    published_packages = published.get("packages", {})
    for name in sorted(set(repo_packages) | set(published_packages)):
        repo_pin = (repo_packages.get(name) or {}).get("version")
        published_pin = (published_packages.get(name) or {}).get("version")
        if repo_pin != published_pin:
            diffs.append(
                f"packages.{name} pin: repo {repo_pin}, "
                f"registry {published_pin}")
    return diffs


def check_tree(root, fetch=fetch_bytes):
    notes = []
    errors = []
    for listing in LISTINGS:
        name = listing["name"]
        url = f"{REGISTRY}/{OWNER}/{listing['registry_type']}/{name}"
        repo_manifest = json.loads(
            (root / listing["repo_manifest"]).read_text())
        repo_version = repo_manifest.get("version")
        try:
            published = published_files(fetch_json(url, fetch), url)
        except (RegistryError, OSError) as exc:
            errors.append(f"{name}: {exc} (refusing to pass silently)")
            continue
        if repo_version not in published:
            notes.append(f"{name} {repo_version} is not on the registry: pass")
            continue
        if listing["registry_type"] != "platform":
            notes.append(
                f"{name} {repo_version} is published: versions match, pass")
            continue
        try:
            tarball_url = published[repo_version]
            published_manifest = extract_manifest(
                fetch(tarball_url), listing["member"], tarball_url)
        except (RegistryError, OSError) as exc:
            errors.append(f"{name}: {exc} (refusing to pass silently)")
            continue
        diffs = compare_platform(repo_manifest, published_manifest)
        if diffs:
            errors.append(
                f"{name} version {repo_version} is already published "
                f"with different content: bump it")
            errors.extend(f"  {line}" for line in diffs)
        else:
            notes.append(
                f"{name} {repo_version} matches the published manifest: pass")
    return notes, errors


def main() -> int:
    if os.environ.get("REGISTRY_CHECK") == "skip":
        if os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI"):
            print("error: REGISTRY_CHECK=skip is refused inside CI")
            return 1
        print("REGISTRY_CHECK=skip: bypassing the registry gate "
              "(offline local runs only)")
        return 0
    root = pathlib.Path(__file__).resolve().parent.parent
    try:
        notes, errors = check_tree(root)
    except (OSError, ValueError) as exc:
        print(f"error: cannot read the repo manifests: {exc}")
        return 1
    print("\n".join(notes))
    if errors:
        print("\n".join(errors))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
