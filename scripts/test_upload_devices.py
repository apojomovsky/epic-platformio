"""Spelling gate for upload.devices (epic-platformio#69).

Every boards/*.json device name must resolve in the pinned tool build.
The tools answer without hardware, so this test checks membership in
boards/devices/<tool>-<version>.txt fixtures dumped from those builds.
A fixture whose version no longer matches the pin fails. Refresh: run
the command in the fixture header against the new pin and replace it.
"""

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOARDS = ROOT / "boards"
DEVICES = ROOT / "boards" / "devices"
PLATFORM = ROOT / "platform.json"

# Versions the fixtures must match. minipro's database ships with its
# binary, so its version is read from platform.json; the other two name
# different artifacts than the binary tag (the .dat device file, the
# vendored chipdata.cid), so they name the epic-tools pin they track
# until platform.json references those artifacts directly.
PICPRO_VERSION = "0.4.1"
PK2_DEVICE_FILE_VERSION = "1.62.14"

CASE = {
    "minipro": str.lower,
    "pk2cmd": lambda s: s,
    "picpro": str.lower,
}


def platform_tool_version(tool):
    url = json.loads(PLATFORM.read_text())["packages"][tool]["version"]
    return re.search(r"(\d+\.\d+\.\d+)", url).group(1)


def fixture_names(tool, version):
    path = DEVICES / ("%s-%s.txt" % (tool, version))
    assert path.is_file(), "missing %s: re-dump it per its header" % path.name
    names = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.add(line)
    assert names, "empty fixture %s" % path.name
    return names


class SpellingGateTest(unittest.TestCase):
    def test_every_spelling_resolves(self):
        fixtures = {
            "minipro": fixture_names("minipro", platform_tool_version("tool-minipro")),
            "pk2cmd": fixture_names("pk2cmd", PK2_DEVICE_FILE_VERSION),
            "picpro": fixture_names("picpro", PICPRO_VERSION),
        }
        missing = []
        for path in sorted(BOARDS.glob("*.json")):
            for tool, spelling in json.loads(path.read_text())["upload"]["devices"].items():
                self.assertIn(tool, fixtures, "no fixture for %r (board %s)" % (tool, path.name))
                if CASE[tool](spelling) not in fixtures[tool]:
                    missing.append("%s: %s=%r" % (path.name, tool, spelling))
        self.assertFalse(missing, "unresolvable spellings:\n" + "\n".join(missing))


if __name__ == "__main__":
    unittest.main()
