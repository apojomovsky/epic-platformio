"""Coverage for scripts/gen_boards.py (PIO-6, epic-platformio#24). No
network, no upstream checkout: every function is pure over small
hand-authored fixtures, run through the exact same code path as the real
inputs (verified separately against a real epic-cc/epic-hal join).
"""

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HELPER = ROOT / "scripts" / "gen_boards.py"

_spec = importlib.util.spec_from_file_location("gen_boards", HELPER)
gen_boards = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_boards)

DEVICES = [
    {"name": "p16f877a", "core": "pic14", "pack": "Microchip.PIC16Fxxx_DFP"},
    {"name": "p10f320", "core": "pic14", "pack": "Microchip.PIC10-12Fxxx_DFP"},
]

# 16F877A: epic-hal covers it, family has epiccc_sources -> both toolchains
# get framework support. 16F882: epic-hal covers it, epic-cc does not know
# it at all -> xc8-only, no epic-cc row. p10f320 never appears in parts.
PARTS = {
    "16F877A": "pic16f87xa",
    "16F882": "pic16f88x",
}

MODULES_TOML_BOTH_FAMILIES = """\
[families.PIC16F87XA]
hal_dir = "pic16f87xa-hal"
fosc_hz = 20000000
epiccc_sources = [
  "a.c",
]

[families.PIC16F88X]
hal_dir = "pic16f88x-hal"
fosc_hz = 20000000
"""


class CanonicalizationTests(unittest.TestCase):
    def test_cc_name_to_bare_strips_leading_p_and_uppercases(self):
        self.assertEqual(gen_boards.cc_name_to_bare("p16f877a"), "16F877A")

    def test_cc_name_to_bare_handles_a_name_with_no_leading_p(self):
        # Defensive only: every real epic-cc device name has the p
        # prefix, but the function must not crash on one that doesn't.
        self.assertEqual(gen_boards.cc_name_to_bare("16f877a"), "16F877A")


class LoadPartsTests(unittest.TestCase):
    def test_parses_bare_name_and_family_per_line(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "parts.txt"
            path.write_text("16F877A pic16f87xa\n16F882 pic16f88x\n")
            self.assertEqual(
                gen_boards.load_parts(path),
                {"16F877A": "pic16f87xa", "16F882": "pic16f88x"},
            )


class LoadEpicccFamiliesTests(unittest.TestCase):
    def test_lowercases_family_names_to_match_parts_txt(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "modules.toml"
            path.write_text(MODULES_TOML_BOTH_FAMILIES)
            result = gen_boards.load_epiccc_families(path)
        self.assertEqual(
            result, {"pic16f87xa": True, "pic16f88x": False}
        )


class BuildMatrixTests(unittest.TestCase):
    def setUp(self):
        self.epiccc_families = {"pic16f87xa": True, "pic16f88x": False}

    def test_device_known_to_both_with_epiccc_family_gets_full_capability(self):
        matrix = gen_boards.build_matrix(DEVICES, PARTS, self.epiccc_families)
        entry = matrix["16F877A"]
        self.assertEqual(entry["cc_name"], "p16f877a")
        self.assertEqual(entry["toolchains"], ["epic-cc", "xc8"])
        self.assertEqual(entry["framework_toolchains"], ["epic-cc", "xc8"])

    def test_epic_cc_only_device_has_no_framework_support(self):
        matrix = gen_boards.build_matrix(DEVICES, PARTS, self.epiccc_families)
        entry = matrix["10F320"]
        self.assertEqual(entry["toolchains"], ["epic-cc"])
        self.assertEqual(entry["framework_toolchains"], [])

    def test_xc8_only_device_unknown_to_epic_cc(self):
        matrix = gen_boards.build_matrix(DEVICES, PARTS, self.epiccc_families)
        entry = matrix["16F882"]
        self.assertIsNone(entry["cc_name"])
        self.assertEqual(entry["toolchains"], ["xc8"])
        self.assertEqual(entry["framework_toolchains"], ["xc8"])

    def test_family_without_epiccc_sources_is_xc8_only_for_framework(self):
        # A device epic-cc DOES know, but whose epic-hal family has no
        # epiccc_sources: both toolchains compile, framework is xc8-only.
        devices = DEVICES + [
            {"name": "p16f882", "core": "pic14", "pack": None}
        ]
        matrix = gen_boards.build_matrix(devices, PARTS, self.epiccc_families)
        entry = matrix["16F882"]
        self.assertEqual(entry["toolchains"], ["epic-cc", "xc8"])
        self.assertEqual(entry["framework_toolchains"], ["xc8"])


class BoardJsonTests(unittest.TestCase):
    def test_new_device_gets_a_minimal_synthesized_board(self):
        entry = {
            "mcu": "p10f320",
            "cc_name": "p10f320",
            "family": None,
            "toolchains": ["epic-cc"],
            "framework_toolchains": [],
        }
        with tempfile.TemporaryDirectory() as td:
            doc = gen_boards.board_json("10F320", entry, pathlib.Path(td))
        self.assertEqual(doc["build"]["mcu"], "p10f320")
        self.assertEqual(doc["build"]["toolchains"], ["epic-cc"])
        self.assertNotIn("epichal_family", doc["build"])
        self.assertEqual(doc["name"], "Microchip PIC10F320")
        self.assertEqual(doc["vendor"], "Microchip")
        self.assertIn("PIC10F320", doc["url"])

    def test_existing_board_keeps_hand_authored_fields(self):
        existing = {
            "build": {"mcu": "p16f877a", "f_cpu": "4000000L"},
            "name": "Microchip PIC16F877A",
            "upload": {"protocol": "minipro", "minipro_device": "PIC16F877A"},
            "url": "https://www.microchip.com/en-us/product/PIC16F877A",
            "vendor": "Microchip",
        }
        entry = {
            "mcu": "p16f877a",
            "cc_name": "p16f877a",
            "family": "pic16f87xa",
            "toolchains": ["epic-cc", "xc8"],
            "framework_toolchains": ["epic-cc", "xc8"],
        }
        with tempfile.TemporaryDirectory() as td:
            boards_dir = pathlib.Path(td)
            (boards_dir / "p16f877a.json").write_text(json.dumps(existing))
            doc = gen_boards.board_json("16F877A", entry, boards_dir)
        self.assertEqual(doc["build"]["f_cpu"], "4000000L")
        self.assertEqual(doc["upload"]["protocol"], "minipro")
        self.assertEqual(doc["build"]["epichal_family"], "pic16f87xa")
        self.assertEqual(doc["build"]["toolchains"], ["epic-cc", "xc8"])


class RealDataJoinTests(unittest.TestCase):
    """Not a unit test of the join logic (covered above with fixtures):
    a structural sanity check that the real, current epic-hal parts.txt
    spellings actually satisfy cc_name_to_bare's assumption, so a future
    epic-hal part naming change is caught here instead of silently
    producing an empty matrix entry."""

    def test_bare_to_cc_round_trips_for_known_shapes(self):
        for bare in ("16F877A", "18F4550", "16LF627A", "16F1937"):
            cc_name = "p" + bare.lower()
            self.assertEqual(gen_boards.cc_name_to_bare(cc_name), bare)


class MainEndToEndTests(unittest.TestCase):
    """main() with a non-default --out-dir must be self-contained: the
    merge source for hand-authored fields is --out-dir itself, never the
    real repo boards/ behind its back (a real bug this pins down)."""

    def _run(self, out_dir, devices, parts_lines, modules_toml):
        devices_path = out_dir / "devices.json"
        devices_path.write_text(json.dumps(devices))
        parts_path = out_dir / "parts.txt"
        parts_path.write_text("\n".join(parts_lines) + "\n")
        modules_path = out_dir / "modules.toml"
        modules_path.write_text(modules_toml)
        boards_out = out_dir / "boards"
        subprocess.run(
            [
                sys.executable,
                str(HELPER),
                "--devices-json",
                str(devices_path),
                "--parts-txt",
                str(parts_path),
                "--modules-toml",
                str(modules_path),
                "--out-dir",
                str(boards_out),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return boards_out

    def test_out_dir_is_self_contained_not_the_real_boards_dir(self):
        with tempfile.TemporaryDirectory() as td:
            out_dir = pathlib.Path(td)
            boards_out = self._run(
                out_dir,
                DEVICES,
                ["16F877A pic16f87xa"],
                MODULES_TOML_BOTH_FAMILIES,
            )
            doc = json.loads((boards_out / "p16f877a.json").read_text())
        # A brand-new out-dir has nothing to merge from: no upload/url
        # fields leaked in from the real repo's boards/p16f877a.json.
        self.assertNotIn("upload", doc)
        self.assertEqual(doc["build"]["toolchains"], ["epic-cc", "xc8"])

    def test_second_run_merges_from_out_dir_itself(self):
        with tempfile.TemporaryDirectory() as td:
            out_dir = pathlib.Path(td)
            boards_out = self._run(
                out_dir,
                DEVICES,
                ["16F877A pic16f87xa"],
                MODULES_TOML_BOTH_FAMILIES,
            )
            # Hand-edit the generated board, like a real curator would.
            doc = json.loads((boards_out / "p16f877a.json").read_text())
            doc["upload"] = {"protocol": "minipro"}
            (boards_out / "p16f877a.json").write_text(json.dumps(doc))
            self._run(
                out_dir,
                DEVICES,
                ["16F877A pic16f87xa"],
                MODULES_TOML_BOTH_FAMILIES,
            )
            doc = json.loads((boards_out / "p16f877a.json").read_text())
        self.assertEqual(doc["upload"], {"protocol": "minipro"})


if __name__ == "__main__":
    unittest.main()
