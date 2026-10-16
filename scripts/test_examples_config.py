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
    """Each example directory that holds a project (no platformio.ini, no project)."""
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
                # Some boards (pic12f675, pic16f628a, pic16f1937) publish no f_cpu;
                # there is no board clock to compare against, so they are skipped.
                if f_cpu is None:
                    continue
                expected = int(str(f_cpu).rstrip("uUlL"))
                for kind, pairs in _declarations(example):
                    if kind == "epic-config":
                        self.assertEqual(int(pairs["xtal_hz"]), expected, example.name)


# The oscillator words the examples name, by the clock they select. This is
# the subset of each family's FOSC/osc fuse table the examples use; a word
# outside it fails the test until it is added here with its class.
_OSC_CLASS = {
    "HS": "crystal",
    "XT": "crystal",
    "LP": "crystal",
    "HSPLL": "crystal",
    "XTPLL": "crystal",
    "HSPLL_HS": "crystal",
    "XTPLL_XT": "crystal",
    "XT_XT": "crystal",
    "INTRCIO": "internal",
    "INTRCCLKOUT": "internal",
    "INTOSC": "internal",
    "INTOSCIO": "internal",
    "RC": "rc",
    "RCIO": "rc",
    "EC": "external",
    "ECIO": "external",
}

# The clock class lives in the board JSON (scripts/gen_boards.py emits
# build.oscillator from its CURATED table); the frequency still comes
# from build.f_cpu where an example fixed a crystal. A board with
# neither runs on its internal oscillator at 4 MHz, the factory
# calibration the 12F675 ships with.
_XTAL_DEFINE = re.compile(r"#[ \t]*define[ \t]+_XTAL_FREQ[ \t]+(\d+)")
_XTAL_FLAG = re.compile(r"-D_XTAL_FREQ=(\d+)")

def _board_clock(board):
    """(class, hz) of a board: hz is None when no frequency is known."""
    build = json.loads((BOARDS / f"{board}.json").read_text(encoding="utf-8")).get("build", {})
    clock_class = build.get("oscillator")
    assert clock_class in _OSC_CLASS.values(), f"{board} declares no build.oscillator"
    f_cpu = build.get("f_cpu")
    if f_cpu is not None:
        return clock_class, int(str(f_cpu).rstrip("uUlL"))
    if clock_class == "internal":
        return clock_class, 4000000
    return clock_class, None


def _oscillator_words(example):
    """Oscillator word of each declaration, upper-cased: FOSC or osc=."""
    words = []
    for kind, pairs in _declarations(example):
        if kind == "epic-config":
            words.append(pairs["osc"].upper())
        elif "FOSC" in pairs:
            words.append(pairs["FOSC"])
    return words


def _xtal_defines(example):
    """_XTAL_FREQ values from the sources and from platformio.ini build_flags."""
    values = []
    for src in _sources(example):
        values += [int(v) for v in _XTAL_DEFINE.findall(_code(src.read_text(encoding="utf-8")))]
    ini = (example / "platformio.ini").read_text(encoding="utf-8")
    values += [int(v) for v in _XTAL_FLAG.findall(ini)]
    return values


class OscillatorWordsMatchBoardClock(unittest.TestCase):
    def test_every_board_declares_its_clock(self):
        for board in sorted(BOARDS.glob("*.json")):
            with self.subTest(board=board.stem):
                build = json.loads(board.read_text(encoding="utf-8")).get("build", {})
                self.assertIn(build.get("oscillator"), set(_OSC_CLASS.values()), "add build.oscillator to the board JSON")

    def test_every_example_names_an_oscillator(self):
        for example in _examples():
            with self.subTest(example=example.name):
                self.assertTrue(_oscillator_words(example), f"{example.name} names no oscillator")

    def test_oscillator_words_are_known(self):
        for example in _examples():
            for word in _oscillator_words(example):
                with self.subTest(example=example.name, word=word):
                    self.assertIn(word, _OSC_CLASS, "unknown oscillator word")

    def test_oscillator_class_matches_the_board(self):
        for example in _examples():
            clock_class, _ = _board_clock(_board(example))
            for word in _oscillator_words(example):
                with self.subTest(example=example.name, word=word):
                    self.assertEqual(_OSC_CLASS[word], clock_class, f"{word} on a {clock_class} board")

    def test_xtal_define_matches_the_board_clock(self):
        for example in _examples():
            _, hz = _board_clock(_board(example))
            if hz is None:
                continue
            for value in _xtal_defines(example):
                with self.subTest(example=example.name):
                    self.assertEqual(value, hz, "_XTAL_FREQ")


if __name__ == "__main__":
    unittest.main()
