"""Coverage for scripts/package_framework.py's family discovery (PIO-7,
epic-platformio#25): the union-copy and family-slug logic no longer reads
a hardcoded family list, so a regression there would silently drop or
misname a family instead of failing loudly.
"""

import importlib.util
import json
import pathlib
import tarfile
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HELPER = ROOT / "scripts" / "package_framework.py"

_spec = importlib.util.spec_from_file_location("package_framework", HELPER)
package_framework = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(package_framework)


def _make_bundle(td: pathlib.Path, family: str, hal_dir: str, extra_shared: str | None = None) -> pathlib.Path:
    """A minimal epic-hal release bundle tar.gz: VERSION, epic-hal-sources.json,
    the family's own hal dir, and (optionally) a shared file every bundle
    carries identically, to exercise the union-copy dedup."""
    root = td / f"src-{family}"
    top = root / f"epic-hal-{family}"
    top.mkdir(parents=True)
    (top / "VERSION").write_text("v0.6.0\n")
    (top / "epic-hal-sources.json").write_text(json.dumps({"family": family}))
    hal = top / hal_dir
    hal.mkdir()
    (hal / "src.c").write_text(f"/* {family} */\n")
    if extra_shared:
        shared = top / "epic-common"
        shared.mkdir(exist_ok=True)
        (shared / "shared.c").write_text(extra_shared)

    tar_path = td / f"epic-hal-{family}-v0.6.0.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        tf.add(top, arcname=top.name)
    return tar_path


class ReadEpiccSourcesTests(unittest.TestCase):
    def test_lowercases_family_names(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = pathlib.Path(td) / "modules.toml"
            manifest.write_text(
                '[families.PIC16F87XA]\nepiccc_sources = ["a.c"]\n\n'
                '[families.PIC16F88X]\nfosc_hz = 1\n'
            )
            result = package_framework._read_epiccc_sources(manifest)
            self.assertEqual(result["pic16f87xa"], ["a.c"])
            self.assertEqual(result["pic16f88x"], [])


class BuildTests(unittest.TestCase):
    def test_packages_every_family_bundle_passed(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            tar_a = _make_bundle(td, "pic16f87xa", "pic16f87xa-hal", extra_shared="shared\n")
            tar_b = _make_bundle(td, "pic18fxx5x", "pic18fxx5x-hal", extra_shared="shared\n")
            out = td / "framework-epichal-0.6.0.tar.gz"

            package_framework.build([tar_a, tar_b], "0.6.0", out)

            with tempfile.TemporaryDirectory() as ex:
                ex = pathlib.Path(ex)
                with tarfile.open(out, "r:gz") as tf:
                    tf.extractall(ex)
                self.assertTrue((ex / "epic-hal-sources-pic16f87xa.json").exists())
                self.assertTrue((ex / "epic-hal-sources-pic18fxx5x.json").exists())
                self.assertTrue((ex / "pic16f87xa-hal" / "src.c").exists())
                self.assertTrue((ex / "pic18fxx5x-hal" / "src.c").exists())
                # Shared file present once, from whichever bundle contributed it first.
                self.assertTrue((ex / "epic-common" / "shared.c").exists())
                self.assertEqual(json.loads((ex / "package.json").read_text())["version"], "0.6.0")

    def test_missing_family_field_fails_loudly(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            top = td / "src" / "epic-hal-broken"
            top.mkdir(parents=True)
            (top / "VERSION").write_text("v0.6.0\n")
            (top / "epic-hal-sources.json").write_text(json.dumps({}))
            tar_path = td / "epic-hal-broken-v0.6.0.tar.gz"
            with tarfile.open(tar_path, "w:gz") as tf:
                tf.add(top, arcname=top.name)

            with self.assertRaises(SystemExit):
                package_framework.build([tar_path], "0.6.0", td / "out.tar.gz")


if __name__ == "__main__":
    unittest.main()
