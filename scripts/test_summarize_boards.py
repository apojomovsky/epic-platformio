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
        self.assertEqual(
            summarize_boards.diff_summary(before, after, "curated board"), "No curated board changes."
        )

    def test_added_board(self):
        before = {}
        after = {"p16f887": _doc(["epic-cc", "xc8"], ["xc8"])}
        out = summarize_boards.diff_summary(before, after, "curated board")
        self.assertIn("1 new curated board(s)", out)
        self.assertIn("`p16f887`", out)
        self.assertIn("toolchains=['epic-cc', 'xc8']", out)

    def test_removed_board(self):
        before = {"p10f320": _doc(["epic-cc"], [])}
        after = {}
        out = summarize_boards.diff_summary(before, after, "curated board")
        self.assertIn("1 curated board(s) removed", out)
        self.assertIn("`p10f320`", out)

    def test_capability_change(self):
        before = {"p16f877a": _doc(["epic-cc"], [])}
        after = {"p16f877a": _doc(["epic-cc", "xc8"], ["epic-cc", "xc8"])}
        out = summarize_boards.diff_summary(before, after, "curated board")
        self.assertIn("1 curated board(s) with capability changes", out)
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
        out = summarize_boards.diff_summary(before, after, "curated board")
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
            self.assertIn("1 new curated board(s)", content)
            self.assertIn("p16f887", content)


class TwoDirEndToEndTests(unittest.TestCase):
    """The four-dir CLI path the boards-refresh workflow depends on: both
    sections must appear when each dir changed, and the no-change
    aggregation must collapse to one line."""

    def _doc(self, tc, fw):
        return {"build": {"toolchains": tc, "framework_epichal_toolchains": fw}}

    def test_both_dirs_changed_produces_both_sections(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            for name in ("before", "after"):
                (td / name).mkdir()
            for name in ("before-exp", "after-exp"):
                (td / name).mkdir()
            (td / "before" / "pic16f877a.json").write_text(json.dumps(self._doc(["epic-cc"], [])))
            (td / "after" / "pic16f877a.json").write_text(json.dumps(self._doc(["epic-cc", "xc8"], ["epic-cc", "xc8"])))
            (td / "before-exp" / "p16f882.json").write_text(json.dumps(self._doc(["xc8"], ["xc8"])))
            (td / "after-exp" / "p16f883.json").write_text(json.dumps(self._doc(["xc8"], ["xc8"])))
            out_path = td / "summary.md"
            subprocess.run(
                [sys.executable, str(HELPER),
                 "--before-dir", str(td / "before"),
                 "--after-dir", str(td / "after"),
                 "--before-experimental-dir", str(td / "before-exp"),
                 "--after-experimental-dir", str(td / "after-exp"),
                 "--out", str(out_path)],
                check=True, capture_output=True, text=True,
            )
            content = out_path.read_text()
            self.assertIn("1 curated board(s) with capability changes", content)
            self.assertIn("1 new experimental board(s)", content)

    def test_no_changes_in_either_dir_collapses_to_one_line(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            for name in ("before", "after", "before-exp", "after-exp"):
                (td / name).mkdir()
            for name in ("before", "after"):
                (td / name / "pic16f877a.json").write_text(json.dumps(self._doc(["epic-cc"], [])))
            for name in ("before-exp", "after-exp"):
                (td / name / "p16f882.json").write_text(json.dumps(self._doc(["xc8"], ["xc8"])))
            out_path = td / "summary.md"
            subprocess.run(
                [sys.executable, str(HELPER),
                 "--before-dir", str(td / "before"),
                 "--after-dir", str(td / "after"),
                 "--before-experimental-dir", str(td / "before-exp"),
                 "--after-experimental-dir", str(td / "after-exp"),
                 "--out", str(out_path)],
                check=True, capture_output=True, text=True,
            )
            self.assertEqual(out_path.read_text().strip(), "No board changes.")


if __name__ == "__main__":
    unittest.main()
