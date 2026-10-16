"""Coverage for scripts/hw_signoff.py (epic-platformio#52). No hardware, no
network, no pio: a fake runner records uploads and scripted answers stand
in for the human at the bench.
"""

import importlib.util
import json
import pathlib
import shutil
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HELPER = ROOT / "scripts" / "hw_signoff.py"

_spec = importlib.util.spec_from_file_location("hw_signoff", HELPER)
hw_signoff = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hw_signoff)


def make_repo(root: pathlib.Path) -> pathlib.Path:
    """A fake repo root with the six blink examples and two board JSON."""
    for board in hw_signoff.BOARDS:
        example = root / "examples" / f"blink-tutorial-{board}"
        example.mkdir(parents=True)
        (example / "platformio.ini").write_text(
            "[env:epic8]\nplatform = apojomovsky/epic8\n"
            f"board = {board}\n"
        )
    boards = root / "boards"
    boards.mkdir()
    for board in ("pic16f877a", "pic16f887"):
        (boards / f"{board}.json").write_text(
            json.dumps({"support": "simulator"}) + "\n"
        )
    return root


class Scripted:
    """Canned answers for readline plus a transcript of everything said."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.said = []

    def readline(self, prompt=""):
        self.said.append(prompt)
        return self.answers.pop(0)

    def output(self, message=""):
        self.said.append(message)


class Recorder:
    """A passing runner that records every upload invocation."""

    def __init__(self):
        self.calls = []

    def __call__(self, cmd, cwd, extra_env):
        self.calls.append((list(cmd), cwd, dict(extra_env)))
        return 0


class MatrixTest(unittest.TestCase):
    def test_sixteen_rows_grouped_by_programmer(self):
        rows = hw_signoff.matrix()
        self.assertEqual(len(rows), 16)
        protocols = [protocol for _, protocol in rows]
        self.assertEqual(
            protocols, ["minipro"] * 6 + ["pk2cmd"] * 6 + ["picpro"] * 4
        )

    def test_picpro_covers_only_its_four_parts(self):
        picpro = {board for board, protocol in hw_signoff.matrix() if protocol == "picpro"}
        self.assertEqual(
            picpro, {"pic16f877a", "pic16f628a", "pic12f675", "pic18f4550"}
        )

    def test_minipro_and_pk2cmd_cover_all_six(self):
        for protocol in ("minipro", "pk2cmd"):
            covered = {
                board for board, row in hw_signoff.matrix() if row == protocol
            }
            self.assertEqual(set(hw_signoff.BOARDS), covered)


class ExamplesTest(unittest.TestCase):
    def test_env_comes_from_the_example_ini(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_repo(pathlib.Path(td))
            example = hw_signoff.example_dir(root, "pic16f877a")
            self.assertEqual(hw_signoff.project_env(example), "epic8")

    def test_protocol_travels_in_the_environment(self):
        extra = hw_signoff.upload_environment("pk2cmd", None)
        self.assertEqual(extra["PLATFORMIO_UPLOAD_PROTOCOL"], "pk2cmd")
        self.assertNotIn("PLATFORMIO_UPLOAD_PORT", extra)

    def test_picpro_carries_its_serial_port(self):
        extra = hw_signoff.upload_environment("picpro", "/dev/ttyUSB1")
        self.assertEqual(extra["PLATFORMIO_UPLOAD_PORT"], "/dev/ttyUSB1")


class WalkTest(unittest.TestCase):
    def drive(self, root, answers, results=None, runner=None):
        script = Scripted(answers)
        runner = runner if runner is not None else Recorder()
        out = hw_signoff.walk(
            root,
            results if results is not None else {"version": 1, "rows": {}},
            runner=runner,
            readline=script.readline,
            output=script.output,
        )
        return out, runner, script

    def all_rows_answers(self, verdict="y"):
        # Every row costs one Enter plus one verdict; the first K150 row
        # adds the serial port answer, reused by the rest.
        answers = []
        port_asked = False
        for board, protocol in hw_signoff.matrix():
            if protocol == "picpro" and not port_asked:
                answers.append("")
                port_asked = True
            answers += ["", verdict]
        return answers

    def test_all_yes_records_sixteen_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_repo(pathlib.Path(td))
            out, runner, _ = self.drive(root, self.all_rows_answers("y"))
            self.assertEqual(len(out["rows"]), 16)
            self.assertEqual(set(out["rows"].values()), {"pass"})
            self.assertEqual(len(runner.calls), 16)

    def test_upload_runs_in_the_example_with_the_row_protocol(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_repo(pathlib.Path(td))
            _, runner, script = self.drive(root, self.all_rows_answers("y"))
            self.assertEqual(len(runner.calls), len(hw_signoff.matrix()))
            for (board, protocol), (cmd, cwd, extra) in zip(
                hw_signoff.matrix(), runner.calls
            ):
                self.assertEqual(cmd[:3], ["pio", "run", "-e"])
                self.assertIn("upload", cmd)
                self.assertEqual(cwd, root / "examples" / f"blink-tutorial-{board}")
                self.assertEqual(extra["PLATFORMIO_UPLOAD_PROTOCOL"], protocol)
            ports = [line for line in script.said if "serial port" in line]
            self.assertEqual(len(ports), 1)

    def test_resume_skips_decided_rows_and_reasks_skips(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_repo(pathlib.Path(td))
            rows = dict.fromkeys(
                [hw_signoff.row_key(b, p) for b, p in hw_signoff.matrix()], "skip"
            )
            rows["pic16f877a/minipro"] = "pass"
            rows["pic16f887/minipro"] = "fail"
            answers = []
            port_asked = False
            for board, protocol in hw_signoff.matrix():
                key = hw_signoff.row_key(board, protocol)
                if rows[key] in ("pass", "fail"):
                    continue
                if protocol == "picpro" and not port_asked:
                    answers.append("")
                    port_asked = True
                answers += ["", "y"]
            out, runner, _ = self.drive(root, answers, {"version": 1, "rows": rows})
            self.assertEqual(out["rows"]["pic16f877a/minipro"], "pass")
            self.assertEqual(out["rows"]["pic16f887/minipro"], "fail")
            self.assertEqual(len(runner.calls), 14)

    def test_garbled_verdict_asks_again(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_repo(pathlib.Path(td))
            calls = []

            def once(cmd, cwd, extra_env):
                calls.append(cmd)
                return 0 if len(calls) == 1 else 1

            out, _, _ = self.drive(
                root, ["", "maybe", "y"] + [""] * 11 + ["", ""] * 4, runner=once
            )
            first = hw_signoff.row_key(*hw_signoff.matrix()[0])
            self.assertEqual(out["rows"][first], "pass")

    def test_failed_upload_records_fail_without_asking(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_repo(pathlib.Path(td))

            def failing(cmd, cwd, extra_env):
                return 1

            answers = [""] * 12 + ["", ""] * 4
            out, _, script = self.drive(root, answers, runner=failing)
            self.assertEqual(len(out["rows"]), 16)
            self.assertEqual(set(out["rows"].values()), {"fail"})
            self.assertTrue(
                all("did it blink" not in line for line in script.said)
            )



class GreenBoardsTest(unittest.TestCase):
    def test_only_passes_count_and_unknown_boards_drop_out(self):
        results = {
            "rows": {
                "pic16f877a/minipro": "pass",
                "pic16f887/minipro": "fail",
                "pic16f887/pk2cmd": "skip",
                "nope/minipro": "pass",
            }
        }
        self.assertEqual(hw_signoff.green_boards(results), ["pic16f877a"])


class ApplyTest(unittest.TestCase):
    def test_apply_flips_only_green_boards(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_repo(pathlib.Path(td))
            applied = hw_signoff.apply_support(root, ["pic16f877a"])
            self.assertEqual(applied, ["pic16f877a"])
            doc = json.loads((root / "boards" / "pic16f877a.json").read_text())
            self.assertEqual(doc["support"], "hardware")
            doc = json.loads((root / "boards" / "pic16f887.json").read_text())
            self.assertEqual(doc["support"], "simulator")

    def test_generator_rewrite_survives_and_compiles(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copy(ROOT / "scripts" / "gen_boards.py", scripts / "gen_boards.py")
            hw_signoff.set_hardware_boards(root, ["pic16f877a", "pic12f675"])
            text = (scripts / "gen_boards.py").read_text()
            compile(text, "gen_boards.py", "exec")
            self.assertIn(
                'HARDWARE_BOARDS: frozenset = frozenset({"pic12f675", "pic16f877a"})',
                text,
            )


if __name__ == "__main__":
    unittest.main()
