"""Coverage for scripts/check_registry_versions.py (epic-platformio#163).

Fixtures are recorded from the live registry, trimmed to the fields the
gate reads; the platform tarball fixture is repacked around the
recorded platform.json member. Refresh: GET each listing URL in
LISTINGS plus the platform tarball download URL inside, then rerun the
repack. No test touches the network: check_tree takes its fetch
function as an argument.
"""

import importlib.util
import io
import json
import os
import pathlib
import tarfile
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "scripts" / "fixtures" / "registry"
HELPER = ROOT / "scripts" / "check_registry_versions.py"

_spec = importlib.util.spec_from_file_location("check_registry_versions", HELPER)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

LISTING_URLS = {
    listing["name"]: (
        f"{gate.REGISTRY}/{gate.OWNER}/{listing['registry_type']}/"
        f"{listing['name']}"
    )
    for listing in gate.LISTINGS
}
PLATFORM_TARBALL = "platform_0_1_1.tar.gz"


def published_platform_pins():
    with tarfile.open(
            fileobj=io.BytesIO((FIXTURES / PLATFORM_TARBALL).read_bytes()),
            mode="r:gz") as archive:
        member = json.loads(archive.extractfile("platform.json").read())
    return member["packages"]


def fake_fetch(mapping, log=None):
    def fetch(url):
        if log is not None:
            log.append(url)
        if isinstance(mapping.get(url), Exception):
            raise mapping[url]
        return mapping[url]
    return fetch


def fixture_mapping():
    mapping = {}
    for name, fixture in (("epic8", "platform_listing.json"),
                          ("toolchain-epiccc", "toolchain_listing.json"),
                          ("framework-epichal", "framework_listing.json")):
        listing = json.loads((FIXTURES / fixture).read_text())
        mapping[LISTING_URLS[name]] = json.dumps(listing).encode()
        if name == "epic8":
            for version in listing["versions"]:
                url = version["files"][0]["download_url"]
                mapping[url] = (FIXTURES / PLATFORM_TARBALL).read_bytes()
    return mapping


def write_repo(tmp, platform_version, platform_pins, tools):
    (tmp / "packages" / "toolchain-epiccc").mkdir(parents=True)
    (tmp / "packages" / "framework-epichal").mkdir(parents=True)
    (tmp / "platform.json").write_text(json.dumps({
        "version": platform_version,
        "packages": {name: {"version": pin} for name, pin in platform_pins.items()},
    }))
    for name, manifest in tools.items():
        (tmp / "packages" / name / "package.json").write_text(
            json.dumps(manifest))


def incident_repo(tmp):
    pins = {name: entry["version"] if isinstance(entry, dict) else entry
            for name, entry in published_platform_pins().items()}
    pins["toolchain-epiccc"] = "0.5.0"
    write_repo(tmp, "0.1.1", pins, {
        "toolchain-epiccc": {"name": "toolchain-epiccc", "version": "0.5.0"},
        "framework-epichal": {"name": "framework-epichal", "version": "0.6.0+pio1"},
    })


class IncidentTests(unittest.TestCase):
    def test_incident_fails(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        incident_repo(tmp)
        notes, errors = gate.check_tree(tmp, fetch=fake_fetch(fixture_mapping()))
        self.assertTrue(
            any("epic8 version 0.1.1 is already published with "
                "different content: bump it" in e for e in errors),
            errors)
        self.assertTrue(
            any("packages.toolchain-epiccc pin: repo 0.5.0, "
                "registry 0.4.0+pio1" in e for e in errors),
            errors)

    def test_matching_platform_passes(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        pins = {name: entry["version"] if isinstance(entry, dict) else entry
                for name, entry in published_platform_pins().items()}
        write_repo(tmp, "0.1.1", pins, {
            "toolchain-epiccc": {"name": "toolchain-epiccc", "version": "0.5.0"},
            "framework-epichal": {"name": "framework-epichal", "version": "0.6.0+pio1"},
        })
        notes, errors = gate.check_tree(tmp, fetch=fake_fetch(fixture_mapping()))
        self.assertEqual(errors, [])
        self.assertTrue(any("epic8 0.1.1 matches" in n for n in notes), notes)


class UnpublishedTests(unittest.TestCase):
    def test_bumped_platform_passes_without_tarball_fetch(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        incident_repo(tmp)
        platform = json.loads((tmp / "platform.json").read_text())
        platform["version"] = "0.1.2"
        (tmp / "platform.json").write_text(json.dumps(platform))
        log = []
        notes, errors = gate.check_tree(tmp, fetch=fake_fetch(fixture_mapping(), log))
        self.assertEqual(errors, [])
        self.assertTrue(any("epic8 0.1.2 is not on the registry" in n for n in notes))
        self.assertNotIn(
            "https://dl.registry.platformio.org/download/apojomovsky/platform/"
            "epic8/0.1.1/epic8-0.1.1.tar.gz", log)


class ToolTests(unittest.TestCase):
    def test_published_tool_passes_on_version_identity(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        incident_repo(tmp)
        log = []
        notes, errors = gate.check_tree(tmp, fetch=fake_fetch(fixture_mapping(), log))
        self.assertEqual(
            [e for e in errors if e.startswith("framework-epichal")], [])
        self.assertTrue(
            any("framework-epichal 0.6.0+pio1 is published: versions match, pass"
                in n for n in notes), notes)
        self.assertFalse([u for u in log if u.startswith("https://dl.registry") and "/tool/" in u], log)

    def test_unpublished_tool_passes(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        incident_repo(tmp)
        notes, errors = gate.check_tree(tmp, fetch=fake_fetch(fixture_mapping()))
        self.assertEqual(
            [e for e in errors if e.startswith("toolchain-epiccc")], [])
        self.assertTrue(
            any("toolchain-epiccc 0.5.0 is not on the registry" in n for n in notes))


class CompareTests(unittest.TestCase):
    def test_platform_reports_each_drifted_pin(self):
        diffs = gate.compare_platform(
            {"version": "0.1.1",
             "packages": {"a": {"version": "2"}, "b": {"version": "1"}}},
            {"version": "0.1.1", "packages": {"a": {"version": "1"}}})
        self.assertIn("packages.a pin: repo 2, registry 1", diffs)
        self.assertTrue(any("packages.b pin" in d for d in diffs))


class OutageTests(unittest.TestCase):
    def test_listing_outage_fails_loudly(self):
        import urllib.error
        tmp = pathlib.Path(tempfile.mkdtemp())
        incident_repo(tmp)
        mapping = fixture_mapping()
        mapping[LISTING_URLS["epic8"]] = urllib.error.URLError("conn refused")
        notes, errors = gate.check_tree(tmp, fetch=fake_fetch(mapping))
        self.assertTrue(
            any("epic8" in e and "refusing to pass silently" in e for e in errors),
            errors)

    def test_tarball_outage_fails_loudly(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        pins = {name: entry["version"] if isinstance(entry, dict) else entry
                for name, entry in published_platform_pins().items()}
        write_repo(tmp, "0.1.1", pins, {
            "toolchain-epiccc": {"name": "toolchain-epiccc", "version": "0.5.0"},
            "framework-epichal": {"name": "framework-epichal", "version": "0.6.0+pio1"},
        })
        mapping = fixture_mapping()
        mapping["https://dl.registry.platformio.org/download/apojomovsky/platform/"
               "epic8/0.1.1/epic8-0.1.1.tar.gz"] = gate.RegistryError("truncated")
        notes, errors = gate.check_tree(tmp, fetch=fake_fetch(mapping))
        self.assertTrue(
            any("epic8" in e and "refusing to pass silently" in e for e in errors),
            errors)


class SkipTests(unittest.TestCase):
    def setUp(self):
        self.saved = {key: os.environ.get(key)
                      for key in ("REGISTRY_CHECK", "GITHUB_ACTIONS", "CI")}

    def tearDown(self):
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_skip_passes_offline(self):
        os.environ["REGISTRY_CHECK"] = "skip"
        os.environ.pop("GITHUB_ACTIONS", None)
        os.environ.pop("CI", None)
        self.assertEqual(gate.main(), 0)

    def test_skip_refused_in_ci(self):
        os.environ["REGISTRY_CHECK"] = "skip"
        os.environ["GITHUB_ACTIONS"] = "true"
        self.assertEqual(gate.main(), 1)


if __name__ == "__main__":
    unittest.main()
