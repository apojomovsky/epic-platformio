"""Coverage for scripts/gen_boards.py (PIO-6, epic-platformio#24; the
curated split is PIO-2, epic-platformio#45). No network, no upstream
checkout: every function is pure over small hand-authored fixtures, run
through the exact same code path as the real inputs (verified separately
against a real epic-cc/epic-hal join).
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
    {"name": "p16f887", "core": "pic14", "pack": "Microchip.PIC16Fxxx_DFP"},
    {"name": "p16f628a", "core": "pic14", "pack": "Microchip.PIC16Fxxx_DFP"},
    {"name": "p12f675", "core": "pic14", "pack": "Microchip.PIC10-12Fxxx_DFP"},
    {"name": "p16f1937", "core": "pic14e", "pack": "Microchip.PIC12-16F1xxx_DFP"},
    {"name": "p18f4550", "core": "pic18", "pack": "Microchip.PIC18Fxxxx_DFP"},
    {"name": "p10f320", "core": "pic14", "pack": "Microchip.PIC10-12Fxxx_DFP"},
    {"name": "p16f819", "core": "pic14", "pack": "Microchip.PIC16Fxxx_DFP"},
]

# 16F877A: epic-hal covers it, family has epiccc_sources -> both toolchains
# get framework support. 16F882: epic-hal covers it, epic-cc does not know
# it at all -> xc8-only, no epic-cc row. p10f320 never appears in parts.
# The six curated parts are present so the generator's own check that a
# curated board still exists upstream passes; one test drops 16F877A on
# purpose to exercise the failure side of that check.
PARTS = {
    "16F877A": "pic16f87xa",
    "16F887": "pic16f88x",
    "16F628A": "pic16f628a",
    "16F1937": "pic16f193x",
    "18F4550": "pic18fxx5x",
    "16F882": "pic16f88x",
    "16F819": "pic16f87xa",
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

[families.PIC16F628A]
hal_dir = "pic16f628a-hal"
epiccc_sources = [
  "a.c",
]

[families.PIC16F193X]
hal_dir = "pic16f193x-hal"
epiccc_sources = [
  "a.c",
]

[families.PIC18Fxx5x]
hal_dir = "pic18fxx5x-hal"
epiccc_sources = [
  "a.c",
]
"""


def entry(mcu, toolchains, framework_toolchains, family=None, cc_name=None):
    return {
        "mcu": mcu,
        "cc_name": cc_name or mcu,
        "family": family,
        "toolchains": toolchains,
        "framework_toolchains": framework_toolchains,
    }


class CanonicalizationTests(unittest.TestCase):
    def test_cc_name_to_bare_strips_leading_p_and_uppercases(self):
        self.assertEqual(gen_boards.cc_name_to_bare("p16f877a"), "16F877A")

    def test_cc_name_to_bare_handles_a_name_with_no_leading_p(self):
        # Defensive only: every real epic-cc device name has the p
        # prefix, but the function must not crash on one that doesn't.
        self.assertEqual(gen_boards.cc_name_to_bare("16f877a"), "16F877A")

    def test_curated_bare_maps_a_board_id_to_the_matrix_device(self):
        self.assertEqual(gen_boards.curated_bare("pic16f877a"), "16F877A")
        self.assertEqual(gen_boards.curated_bare("pic18f4550"), "18F4550")


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
            result["pic16f87xa"], True
        )
        self.assertEqual(result["pic16f88x"], False)


class BuildMatrixTests(unittest.TestCase):
    def setUp(self):
        self.epiccc_families = {"pic16f87xa": True, "pic16f88x": False}

    def test_device_known_to_both_with_epiccc_family_gets_full_capability(self):
        matrix = gen_boards.build_matrix(DEVICES, PARTS, self.epiccc_families)
        e = matrix["16F877A"]
        self.assertEqual(e["cc_name"], "p16f877a")
        self.assertEqual(e["toolchains"], ["epic-cc", "xc8"])
        self.assertEqual(e["framework_toolchains"], ["epic-cc", "xc8"])

    def test_epic_cc_only_device_has_no_framework_support(self):
        matrix = gen_boards.build_matrix(DEVICES, PARTS, self.epiccc_families)
        e = matrix["10F320"]
        self.assertEqual(e["toolchains"], ["epic-cc"])
        self.assertEqual(e["framework_toolchains"], [])

    def test_xc8_only_device_unknown_to_epic_cc(self):
        matrix = gen_boards.build_matrix(DEVICES, PARTS, self.epiccc_families)
        e = matrix["16F882"]
        self.assertIsNone(e["cc_name"])
        self.assertEqual(e["toolchains"], ["xc8"])
        self.assertEqual(e["framework_toolchains"], ["xc8"])

    def test_family_without_epiccc_sources_is_xc8_only_for_framework(self):
        # A device epic-cc DOES know, but whose epic-hal family has no
        # epiccc_sources: both toolchains compile, framework is xc8-only.
        devices = DEVICES + [{"name": "p16f882", "core": "pic14", "pack": None}]
        matrix = gen_boards.build_matrix(devices, PARTS, self.epiccc_families)
        e = matrix["16F882"]
        self.assertEqual(e["toolchains"], ["epic-cc", "xc8"])
        self.assertEqual(e["framework_toolchains"], ["xc8"])


class BoardJsonTests(unittest.TestCase):
    def test_experimental_board_is_capability_only(self):
        # No curated facts: no sizes, no devices, no hazards, no support
        # tier. A user copying one out gets the capability fields alone.
        e = entry("p10f320", ["epic-cc"], [], cc_name="p10f320")
        with tempfile.TemporaryDirectory() as td:
            doc = gen_boards.board_json(e, "p10f320", pathlib.Path(td), None)
        self.assertEqual(doc["build"]["mcu"], "p10f320")
        self.assertEqual(doc["build"]["toolchains"], ["epic-cc"])
        self.assertNotIn("epichal_family", doc["build"])
        self.assertNotIn("upload", doc)
        self.assertNotIn("support", doc)
        self.assertEqual(doc["name"], "Microchip PIC10F320")
        self.assertEqual(doc["vendor"], "Microchip")
        self.assertIn("PIC10F320", doc["url"])

    def test_curated_board_carries_the_beta_facts(self):
        e = entry(
            "p16f877a", ["epic-cc", "xc8"], ["epic-cc", "xc8"], family="pic16f87xa"
        )
        curated = {
            "maximum_size": 16384,
            "maximum_ram_size": 368,
            "f_cpu": "4000000L",
            "devices": {"minipro": "PIC16F877A", "pk2cmd": "PIC16F877A"},
            "hazards": {
                "pgm_pin": "RB3",
                "lvp_scheme": "pgm_pin",
                "osccal_word": None,
                "bandgap_bits": None,
            },
        }
        with tempfile.TemporaryDirectory() as td:
            doc = gen_boards.board_json(
                e, "pic16f877a", pathlib.Path(td), curated
            )
        # The board id is the chip name; build.mcu stays epic-cc's.
        self.assertEqual(doc["name"], "Microchip PIC16F877A")
        self.assertEqual(doc["build"]["mcu"], "p16f877a")
        self.assertEqual(doc["build"]["f_cpu"], "4000000L")
        self.assertEqual(doc["upload"]["maximum_size"], 16384)
        self.assertEqual(doc["upload"]["maximum_ram_size"], 368)
        self.assertEqual(doc["upload"]["devices"]["minipro"], "PIC16F877A")
        self.assertEqual(doc["upload"]["hazards"]["pgm_pin"], "RB3")
        self.assertEqual(doc["support"], "simulator")

    def test_curated_board_with_no_board_crystal_omits_f_cpu(self):
        # D-4's clock check treats board_build.f_cpu as the last source,
        # so a part whose curated entry records no crystal must not carry
        # one (the board would otherwise overrule the code's own value).
        e = entry("p16f628a", ["epic-cc", "xc8"], ["epic-cc", "xc8"], family="pic16f628a")
        curated = {
            "maximum_size": 4096,
            "maximum_ram_size": 224,
            "f_cpu": None,
            "devices": {"minipro": "PIC16F628A"},
            "hazards": {
                "pgm_pin": "RB4",
                "lvp_scheme": "pgm_pin",
                "osccal_word": None,
                "bandgap_bits": None,
            },
        }
        with tempfile.TemporaryDirectory() as td:
            dest = pathlib.Path(td)
            (dest / "pic16f628a.json").write_text(
                json.dumps({"build": {"f_cpu": "4000000L"}})
            )
            doc = gen_boards.board_json(e, "pic16f628a", dest, curated)
        self.assertNotIn("f_cpu", doc["build"])

    def test_existing_board_keeps_hand_authored_fields(self):
        existing = {
            "build": {"mcu": "p16f877a", "f_cpu": "4000000L"},
            "name": "Microchip PIC16F877A",
            "upload": {"protocol": "minipro", "devices": {"minipro": "PIC16F877A"}},
            "url": "https://www.microchip.com/en-us/product/PIC16F877A",
            "vendor": "Microchip",
        }
        e = entry(
            "p16f877a", ["epic-cc", "xc8"], ["epic-cc", "xc8"], family="pic16f87xa"
        )
        with tempfile.TemporaryDirectory() as td:
            dest = pathlib.Path(td)
            (dest / "pic16f877a.json").write_text(json.dumps(existing))
            doc = gen_boards.board_json(e, "pic16f877a", dest, None)
        self.assertEqual(doc["build"]["f_cpu"], "4000000L")
        self.assertEqual(doc["upload"]["protocol"], "minipro")
        self.assertEqual(doc["build"]["epichal_family"], "pic16f87xa")
        self.assertEqual(doc["build"]["toolchains"], ["epic-cc", "xc8"])


class CuratedTableTests(unittest.TestCase):
    """The curated table is data the generator does not derive, so its own
    internal consistency is what keeps it honest."""

    def test_every_curated_entry_is_shaped_the_way_the_generator_reads_it(self):
        for board_id, facts in gen_boards.CURATED.items():
            self.assertTrue(board_id.startswith("pic"), board_id)
            self.assertIsInstance(facts["maximum_size"], int)
            self.assertIsInstance(facts["maximum_ram_size"], int)
            self.assertTrue(facts["devices"], board_id)
            self.assertIn(facts["hazards"]["lvp_scheme"], ("pgm_pin", "key_sequence", "none"))
            # A part with a PGM pin names it; the others do not.
            if facts["hazards"]["lvp_scheme"] == "pgm_pin":
                self.assertTrue(facts["hazards"]["pgm_pin"])
            else:
                self.assertIsNone(facts["hazards"]["pgm_pin"])

    def test_12f675_carries_the_calibration_and_bandgap_facts(self):
        # D-9's second hazard is specific to this part.
        hazards = gen_boards.CURATED["pic12f675"]["hazards"]
        self.assertEqual(hazards["osccal_word"], "0x3FF")
        self.assertEqual(hazards["bandgap_bits"], "13:12")

    def test_the_default_protocol_names_a_tool_every_curated_board_has(self):
        # The generator writes CURATED_PROTOCOL into every curated board's
        # upload.protocol; a default naming a tool absent from that board's
        # devices map would fail at upload with "no handler".
        for board_id, facts in gen_boards.CURATED.items():
            self.assertIn(gen_boards.CURATED_PROTOCOL, facts["devices"])

    def test_picpro_lacks_the_two_parts_its_device_list_does_not_carry(self):
        for board_id in ("pic16f887", "pic16f1937"):
            self.assertNotIn("picpro", gen_boards.CURATED[board_id]["devices"])
        for board_id in ("pic12f675", "pic16f877a", "pic16f628a", "pic18f4550"):
            self.assertIn("picpro", gen_boards.CURATED[board_id]["devices"])


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
    """main() with non-default output dirs must be self-contained: the
    merge source for hand-authored fields is the output dir itself, never
    the real repo's boards/ or boards-experimental/ behind its back (a
    real bug this pins down)."""

    def _run(self, out_dir, devices, parts_lines, modules_toml):
        devices_path = out_dir / "devices.json"
        devices_path.write_text(json.dumps(devices))
        parts_path = out_dir / "parts.txt"
        parts_path.write_text("\n".join(parts_lines) + "\n")
        modules_path = out_dir / "modules.toml"
        modules_path.write_text(modules_toml)
        curated_out = out_dir / "boards"
        experimental_out = out_dir / "boards-experimental"
        subprocess.run(
            [
                sys.executable,
                str(HELPER),
                "--devices-json", str(devices_path),
                "--parts-txt", str(parts_path),
                "--modules-toml", str(modules_path),
                "--curated-dir", str(curated_out),
                "--experimental-dir", str(experimental_out),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return curated_out, experimental_out

    def test_splits_curated_from_experimental_by_device(self):
        with tempfile.TemporaryDirectory() as td:
            curated_out, experimental_out = self._run(
                pathlib.Path(td),
                DEVICES,
                ["16F877A pic16f87xa", "16F882 pic16f88x"],
                MODULES_TOML_BOTH_FAMILIES,
            )
            curated = sorted(p.name for p in curated_out.glob("*.json"))
            experimental = sorted(p.name for p in experimental_out.glob("*.json"))
        # Every curated part lands only in the curated dir, under its
        # chip-derived id; the rest go to experimental under their mcu.
        self.assertIn("pic16f877a.json", curated)
        self.assertIn("pic16f887.json", curated)
        self.assertEqual(len(curated), 6)
        self.assertNotIn("p10f320.json", curated)
        self.assertIn("p10f320.json", experimental)
        self.assertIn("p16f882.json", experimental)
        self.assertNotIn("p16f877a.json", experimental)

    def test_out_dir_is_self_contained_not_the_real_boards_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            curated_out, _ = self._run(
                pathlib.Path(td), DEVICES, ["16F877A pic16f87xa"], MODULES_TOML_BOTH_FAMILIES
            )
            doc = json.loads((curated_out / "pic16f877a.json").read_text())
        # A brand-new out-dir has nothing to merge from: no fields leaked
        # in from the real repo's curated board.
        self.assertEqual(doc["build"]["toolchains"], ["epic-cc", "xc8"])

    def test_prune_removes_stale_files_from_each_dir_and_keeps_live_ones(self):
        # A stale experimental twin of a curated device in boards/, a stale
        # curated id in boards-experimental/, and a live experimental board
        # that must survive: the generator removes exactly the two stale
        # files and leaves the live one alone.
        with tempfile.TemporaryDirectory() as td:
            out_dir = pathlib.Path(td)
            curated_out = out_dir / "boards"
            experimental_out = out_dir / "boards-experimental"
            curated_out.mkdir()
            experimental_out.mkdir()
            # A live experimental board the next run must keep.
            (experimental_out / "p16f819.json").write_text("{}")
            # A stale experimental twin of a curated device.
            (experimental_out / "pic16f877a.json").write_text("{}")
            # A stale curated id whose device is not in this run's fixtures.
            (curated_out / "pic16f630.json").write_text("{}")
            curated_out, experimental_out = self._run(
                out_dir,
                DEVICES,
                ["16F877A pic16f87xa", "16F882 pic16f88x"],
                MODULES_TOML_BOTH_FAMILIES,
            )
            self.assertNotIn("pic16f630.json", [p.name for p in curated_out.glob("*.json")])
            self.assertNotIn("pic16f877a.json", [p.name for p in experimental_out.glob("*.json")])
            self.assertIn("p16f819.json", [p.name for p in experimental_out.glob("*.json")])

    def test_a_curated_device_missing_from_the_registries_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            devices = [d for d in DEVICES if d["name"] != "p16f877a"]
            with self.assertRaises(subprocess.CalledProcessError) as caught:
                self._run(pathlib.Path(td), devices, ["16F882 pic16f88x"], MODULES_TOML_BOTH_FAMILIES)
            self.assertIn("not in either registry", caught.exception.stderr)


if __name__ == "__main__":
    unittest.main()
