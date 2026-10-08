"""Coverage for scripts/check_versions_consistent.py (epic-platformio#104).

Own builds pin the exact +pioN version; externally published tools pin
the bare upstream so a registry cleanup cannot strand the release.
"""

import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HELPER = ROOT / "scripts" / "check_versions_consistent.py"

_spec = importlib.util.spec_from_file_location("check_versions_consistent", HELPER)
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)


def _root_with(*own_packages):
    import tempfile

    tmp = pathlib.Path(tempfile.mkdtemp())
    for package in own_packages:
        pkg_dir = tmp / "packages" / package
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "package.json").write_text(json.dumps({"version": "1.0.0+pio1"}))
    return tmp


class BaseVersionTests(unittest.TestCase):
    def test_strips_packaging_revision(self):
        self.assertEqual(checker.base_version("0.7.4+pio3"), "0.7.4")

    def test_bare_version_unchanged(self):
        self.assertEqual(checker.base_version("1.27.1"), "1.27.1")


class OwnPackageTests(unittest.TestCase):
    def test_exact_pin_passes(self):
        root = _root_with("toolchain-epiccc")
        versions = {"toolchain-epiccc": {"1.0.0+pio1": {"upstream": "v1.0.0"}}}
        platform = {
            "version": "0.1.1",
            "packages": {
                "toolchain-epiccc": {"owner": "apojomovsky", "version": "1.0.0+pio1"}
            },
        }
        self.assertEqual(checker.check_tree(root, versions, platform), [])

    def test_bare_pin_rejected_for_own_build(self):
        root = _root_with("toolchain-epiccc")
        versions = {"toolchain-epiccc": {"1.0.0+pio1": {"upstream": "v1.0.0"}}}
        platform = {
            "version": "0.1.1",
            "packages": {
                "toolchain-epiccc": {"owner": "apojomovsky", "version": "1.0.0"}
            },
        }
        errors = checker.check_tree(root, versions, platform)
        self.assertEqual(len(errors), 1)
        self.assertIn("toolchain-epiccc", errors[0])


class ToolPinTests(unittest.TestCase):
    def test_bare_upstream_pin_passes(self):
        root = _root_with()
        versions = {"tool-minipro": {"0.7.4+pio3": {"upstream": "0.7.4"}}}
        platform = {
            "version": "0.1.1",
            "packages": {"tool-minipro": {"owner": "apojomovsky", "version": "0.7.4"}},
        }
        self.assertEqual(checker.check_tree(root, versions, platform), [])

    def test_build_metadata_pin_rejected(self):
        root = _root_with()
        versions = {"tool-minipro": {"0.7.4+pio3": {"upstream": "0.7.4"}}}
        platform = {
            "version": "0.1.1",
            "packages": {
                "tool-minipro": {"owner": "apojomovsky", "version": "0.7.4+pio3"}
            },
        }
        errors = checker.check_tree(root, versions, platform)
        self.assertEqual(len(errors), 1)
        self.assertIn("tool-minipro", errors[0])

    def test_stale_base_rejected_after_repackaging(self):
        root = _root_with()
        versions = {
            "tool-minipro": {
                "0.7.4+pio3": {"upstream": "0.7.4"},
                "0.7.5+pio1": {"upstream": "0.7.5"},
            }
        }
        platform = {
            "version": "0.1.1",
            "packages": {"tool-minipro": {"owner": "apojomovsky", "version": "0.7.4"}},
        }
        errors = checker.check_tree(root, versions, platform)
        self.assertEqual(len(errors), 1)
        self.assertIn("0.7.5", errors[0])


class PinLengthTests(unittest.TestCase):
    def test_overlong_pin_rejected(self):
        root = _root_with()
        versions = {"tool-minipro": {"0.7.4+pio3": {"upstream": "0.7.4"}}}
        platform = {
            "version": "0.1.1",
            "packages": {
                "tool-minipro": {"owner": "apojomovsky", "version": "x" * 101}
            },
        }
        errors = checker.check_tree(root, versions, platform)
        self.assertTrue(any("100" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
