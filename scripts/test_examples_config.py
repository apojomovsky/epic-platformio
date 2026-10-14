"""Every example declares its config words, watchdog off (epic-platformio#121).

A PIC with no config words runs on whatever the erased fuses say: on the
PIC16F877A that is the RC oscillator with the watchdog enabled, so the
chip resets every timeout. Each example therefore has to spell its
oscillator and its watchdog out, with the EPIC_CONFIG string (epic-cc)
or `#pragma config` (XC8, and the tutorial examples).
"""

import configparser
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
BOARDS = ROOT / "boards"

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")
_EPIC_CONFIG = re.compile(r'EPIC_CONFIG\s*\(\s*"([^"]*)"\s*\)')
_PRAGMA_CONFIG = re.compile(r"^[ \t]*#[ \t]*pragma[ \t]+config[ \t]+([^\n]*)", re.MULTILINE)
_PRAGMA_PAIR = re.compile(r"([A-Za-z0-9_]+)\s*=\s*([A-Za-z0-9_]+)")


def _examples():
    """Each example directory that holds a project (blink-p16f877a is empty)."""
    for path in sorted(EXAMPLES.iterdir()):
        if (path / "platformio.ini").is_file():
            yield path


def _board(example):
    parser = configparser.ConfigParser()
    parser.read(example / "platformio.ini")
    return parser["env:epic8"]["board"]


def _sources(example):
    return sorted((example / "src").rglob("*.c"))


def _code(text):
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))


def _declarations(example):
    """(kind, pairs) for each config declaration in the example's sources.

    kind is "epic-config" with pairs as {key: value} from the EPIC_CONFIG
    string, or "pragma" with pairs as {NAME: VALUE} from `#pragma config`.
    """
    found = []
    for src in _sources(example):
        code = _code(src.read_text(encoding="utf-8"))
        for spec in _EPIC_CONFIG.findall(code):
            pairs = {}
            for item in spec.split(","):
                if "=" in item:
                    key, value = item.split("=", 1)
                    pairs[key.strip().lower()] = value.strip().lower()
            found.append(("epic-config", pairs))
        for body in _PRAGMA_CONFIG.findall(code):
            pairs = {name.upper(): value.upper() for name, value in _PRAGMA_PAIR.findall(body)}
            found.append(("pragma", pairs))
    return found


class ExamplesDeclareConfigWords(unittest.TestCase):
    def test_there_are_examples(self):
        self.assertTrue(list(_examples()))

    def test_every_example_declares_config_words(self):
        for example in _examples():
            with self.subTest(example=example.name):
                self.assertTrue(
                    _declarations(example),
                    f"{example.name} sets no EPIC_CONFIG or #pragma config",
                )

    def test_every_example_turns_the_watchdog_off(self):
        for example in _examples():
            with self.subTest(example=example.name):
                # `#pragma config` spells one setting per line, so the
                # watchdog word can sit on any of them.
                watchdog = []
                for kind, pairs in _declarations(example):
                    if kind == "epic-config":
                        watchdog += [pairs[k] for k in ("wdt",) if k in pairs]
                    else:
                        watchdog += [pairs[k] for k in ("WDTE", "WDT") if k in pairs]
                self.assertTrue(watchdog, f"{example.name} sets no watchdog word")
                self.assertEqual({v.upper() for v in watchdog}, {"OFF"}, example.name)

    def test_epic_config_names_the_oscillator_and_one_crystal(self):
        for example in _examples():
            with self.subTest(example=example.name):
                epic = [pairs for kind, pairs in _declarations(example) if kind == "epic-config"]
                self.assertLessEqual(len(epic), 1, "one EPIC_CONFIG per program")
                for pairs in epic:
                    self.assertIn("osc", pairs, example.name)
                    self.assertIn("xtal_hz", pairs, example.name)

    def test_epic_config_crystal_matches_the_board_clock(self):
        for example in _examples():
            with self.subTest(example=example.name):
                board_path = BOARDS / f"{_board(example)}.json"
                f_cpu = json.loads(board_path.read_text(encoding="utf-8")).get("build", {}).get("f_cpu")
                if f_cpu is None:
                    continue
                expected = int(str(f_cpu).rstrip("uUlL"))
                for kind, pairs in _declarations(example):
                    if kind == "epic-config":
                        self.assertEqual(int(pairs["xtal_hz"]), expected, example.name)


if __name__ == "__main__":
    unittest.main()
