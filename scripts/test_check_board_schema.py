"""Coverage for scripts/check_board_schema.py (epic-platformio#168).

CLion refuses a board without top-level `frameworks`, so the check
fails a missing key here instead of in a user IDE.
"""

import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HELPER = ROOT / "scripts" / "check_board_schema.py"

_spec = importlib.util.spec_from_file_location("check_board_schema", HELPER)
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)

CURATED = {
    "build": {"mcu": "p16f877a"},
    "frameworks": ["epichal"],
    "debug": {"default_tools": ["epic-sim"]},
    "name": "Microchip PIC16F877A",
    "upload": {"protocol": "minipro"},
    "url": "https://www.microchip.com/en-us/product/PIC16F877A",
    "vendor": "Microchip",
}


def _root_with(*files):
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "boards").mkdir()
    (tmp / "boards-experimental").mkdir()
    (tmp / "platform.json").write_text(json.dumps({"name": "epic8", "version": "0.1.2"}))
    for directory, stem, doc in files:
        (tmp / directory / f"{stem}.json").write_text(json.dumps(doc))
    return tmp


class CuratedTests(unittest.TestCase):
    def test_full_board_passes(self):
        root = _root_with(("boards", "pic16f877a", dict(CURATED)))
        self.assertEqual(checker.check_tree(root), [])

    def test_missing_frameworks_fails(self):
        doc = dict(CURATED)
        del doc["frameworks"]
        root = _root_with(("boards", "pic16f877a", doc))
        errors = checker.check_tree(root)
        self.assertEqual(len(errors), 1)
        self.assertIn("'frameworks'", errors[0])

    def test_string_frameworks_fails(self):
        doc = dict(CURATED, frameworks="epichal")
        root = _root_with(("boards", "pic16f877a", doc))
        self.assertTrue(
            any("must be a list" in e for e in checker.check_tree(root))
        )

    def test_missing_debug_fails_outside_waiver(self):
        doc = dict(CURATED)
        del doc["debug"]
        root = _root_with(("boards", "pic16f877a", doc))
        self.assertTrue(
            any("'debug'" in e for e in checker.check_tree(root))
        )

    def test_waived_board_needs_no_debug(self):
        doc = dict(CURATED)
        del doc["debug"]
        root = _root_with(("boards", "pic16f1937", doc))
        self.assertEqual(checker.check_tree(root), [])


class ExperimentalTests(unittest.TestCase):
    def test_generated_board_needs_frameworks_key(self):
        root = _root_with(("boards-experimental", "p10f320", {"build": {}}))
        errors = checker.check_tree(root)
        self.assertEqual(len(errors), 1)
        self.assertIn("'frameworks'", errors[0])

    def test_empty_frameworks_list_passes(self):
        root = _root_with(
            ("boards-experimental", "p10f320", {"frameworks": []})
        )
        self.assertEqual(checker.check_tree(root), [])

    def test_experimental_board_needs_no_debug(self):
        root = _root_with(
            ("boards-experimental", "p10f320", {"frameworks": ["epichal"]})
        )
        self.assertEqual(checker.check_tree(root), [])


class PlatformTests(unittest.TestCase):
    def test_missing_platform_version_fails(self):
        root = _root_with(("boards", "pic16f877a", dict(CURATED)))
        (root / "platform.json").write_text(json.dumps({"name": "epic8"}))
        errors = checker.check_tree(root)
        self.assertEqual(len(errors), 1)
        self.assertIn("platform.json", errors[0])


if __name__ == "__main__":
    unittest.main()
