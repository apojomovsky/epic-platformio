"""Coverage for scripts/summarize_boards.py (PIO-7, epic-platformio#25)."""

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HELPER = ROOT / "scripts" / "summarize_boards.py"

_spec = importlib.util.spec_from_file_location("summarize_boards", HELPER)
summarize_boards = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(summarize_boards)


def _doc(toolchains, fw_toolchains):
    return {"build": {"toolchains": toolchains, "framework_epichal_toolchains": fw_toolchains}}


class DiffSummaryTests(unittest.TestCase):
    def test_no_changes(self):
        before = {"p16f877a": _doc(["epic-cc"], [])}
        after = {"p16f877a": _doc(["epic-cc"], [])}
        self.assertEqual(summarize_boards.diff_summary(before, after), "No board changes.")

    def test_added_board(self):
        before = {}
        after = {"p16f887": _doc(["epic-cc", "xc8"], ["xc8"])}
        out = summarize_boards.diff_summary(before, after)
        self.assertIn("1 new board(s)", out)
        self.assertIn("`p16f887`", out)
        self.assertIn("toolchains=['epic-cc', 'xc8']", out)

    def test_removed_board(self):
        before = {"p10f320": _doc(["epic-cc"], [])}
        after = {}
        out = summarize_boards.diff_summary(before, after)
        self.assertIn("1 board(s) removed", out)
        self.assertIn("`p10f320`", out)

    def test_capability_change(self):
        before = {"p16f877a": _doc(["epic-cc"], [])}
        after = {"p16f877a": _doc(["epic-cc", "xc8"], ["epic-cc", "xc8"])}
        out = summarize_boards.diff_summary(before, after)
        self.assertIn("1 board(s) with capability changes", out)
        self.assertIn("toolchains ['epic-cc'] → ['epic-cc', 'xc8']", out)
        self.assertIn(
            "framework_epichal_toolchains [] → ['epic-cc', 'xc8']", out
        )

    def test_unchanged_board_not_reported_alongside_others(self):
        before = {
            "p16f877a": _doc(["epic-cc"], []),
            "p16f887": _doc(["epic-cc"], []),
        }
        after = {
            "p16f877a": _doc(["epic-cc"], []),
            "p16f887": _doc(["epic-cc", "xc8"], ["xc8"]),
        }
        out = summarize_boards.diff_summary(before, after)
        self.assertIn("p16f887", out)
        self.assertNotIn("p16f877a", out)


class MainEndToEndTests(unittest.TestCase):
    def test_cli_writes_summary_file(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            before_dir = td / "before"
            after_dir = td / "after"
            before_dir.mkdir()
            after_dir.mkdir()
            (before_dir / "p16f877a.json").write_text(json.dumps(_doc(["epic-cc"], [])))
            (after_dir / "p16f877a.json").write_text(json.dumps(_doc(["epic-cc"], [])))
            (after_dir / "p16f887.json").write_text(
                json.dumps(_doc(["epic-cc", "xc8"], ["xc8"]))
            )
            out_path = td / "summary.md"

            subprocess.run(
                [
                    sys.executable, str(HELPER),
                    "--before-dir", str(before_dir),
                    "--after-dir", str(after_dir),
                    "--out", str(out_path),
                ],
                check=True, capture_output=True, text=True,
            )

            content = out_path.read_text()
            self.assertIn("1 new board(s)", content)
            self.assertIn("p16f887", content)


if __name__ == "__main__":
    unittest.main()
