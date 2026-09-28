"""Coverage for builder/size_report.py (epic-platformio#48).

The helper is the bridge between the driver's --report JSON (ADR-025) and
PlatformIO's CheckUploadSize: its stdout line is parsed by
SIZEPROGREGEXP/SIZEDATAREGEXP, so the column order and the words-to-bytes
conversion (docs/46 D-7: a board's maximum_size is bytes, two per word)
are the contract this pins.
"""

import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parent.parent
HELPER = ROOT / "builder" / "size_report.py"

_spec = importlib.util.spec_from_file_location("size_report", HELPER)
size_report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(size_report)


def _write(report):
    fd, path = tempfile.mkstemp(suffix=".json")
    with open(fd, "w") as fp:
        json.dump(report, fp)
    return path


def _render(report):
    path = _write(report)
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = size_report.main(path)
        return rc, buf.getvalue().strip()
    finally:
        pathlib.Path(path).unlink()


class SizeReportTests(unittest.TestCase):
    def test_flash_words_are_reported_as_bytes(self):
        rc, out = _render(
            {
                "flash_words": {"used": 180, "total": 8192},
                "ram_bytes": {"used": 17, "total": 368},
            }
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, "360 16384 17 368")

    def test_columns_match_the_size_regexps(self):
        # SIZEPROGREGEXP "^(\d+)\s" reads column 1; SIZEDATAREGEXP
        # "^\d+\s+\d+\s+(\d+)\s" reads column 3. Both must be integers.
        _, out = _render(
            {
                "flash_words": {"used": 2, "total": 4},
                "ram_bytes": {"used": 5, "total": 6},
            }
        )
        cols = out.split()
        self.assertEqual(len(cols), 4)
        for c in cols:
            self.assertTrue(c.isdigit())

    def test_missing_argument_exits_two(self):
        # The __main__ guard, exercised the way the builder runs it (by
        # path, with no report argument).
        import subprocess

        proc = subprocess.run(
            [sys.executable, str(HELPER)], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("usage:", proc.stderr)


if __name__ == "__main__":
    unittest.main()
