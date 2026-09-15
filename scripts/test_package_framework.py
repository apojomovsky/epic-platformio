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
                # Identical shared file across both bundles: merged without complaint.
                self.assertTrue((ex / "epic-common" / "shared.c").exists())
                self.assertEqual(json.loads((ex / "package.json").read_text())["version"], "0.6.0")

    def test_shared_dir_with_a_different_file_subset_per_bundle_is_merged(self):
        """Real epic-hal v0.6.0 data: pic14-midrange-core ships a
        different, family-pruned subset of files per family bundle, with
        every file more than one family ships byte-identical. The merge
        must take the union, not reject on the differing file list."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            tar_paths = []
            for fam, only_file in (
                ("pic16f628a", "gpio.c"),
                ("pic16f87xa", "adc.c"),
            ):
                top = td / f"src-{fam}" / f"epic-hal-{fam}"
                top.mkdir(parents=True)
                (top / "VERSION").write_text("v0.6.0\n")
                (top / "epic-hal-sources.json").write_text(json.dumps({"family": fam}))
                (top / f"{fam}-hal").mkdir()
                (top / f"{fam}-hal" / "src.c").write_text(f"/* {fam} */\n")
                core = top / "pic14-midrange-core"
                core.mkdir()
                (core / "common.c").write_text("shared core file\n")
                (core / only_file).write_text(f"{fam} only\n")
                tar_path = td / f"epic-hal-{fam}-v0.6.0.tar.gz"
                with tarfile.open(tar_path, "w:gz") as tf:
                    tf.add(top, arcname=top.name)
                tar_paths.append(tar_path)

            out = td / "framework-epichal-0.6.0.tar.gz"
            package_framework.build(tar_paths, "0.6.0", out)

            with tempfile.TemporaryDirectory() as ex:
                ex = pathlib.Path(ex)
                with tarfile.open(out, "r:gz") as tf:
                    tf.extractall(ex)
                core = ex / "pic14-midrange-core"
                self.assertEqual((core / "common.c").read_text(), "shared core file\n")
                self.assertEqual((core / "gpio.c").read_text(), "pic16f628a only\n")
                self.assertEqual((core / "adc.c").read_text(), "pic16f87xa only\n")

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

    def test_duplicate_family_fails_loudly(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            tar_a = _make_bundle(td, "pic16f87xa", "pic16f87xa-hal")
            tar_b = _make_bundle(td / "again", "pic16f87xa", "pic16f87xa-hal")
            with self.assertRaises(SystemExit):
                package_framework.build([tar_a, tar_b], "0.6.0", td / "out.tar.gz")

    def test_same_name_entries_that_differ_fail_loudly(self):
        """Two bundles sharing a top-level name (e.g. epic-common) must
        actually be identical; a real divergence must not be silently
        resolved by keeping whichever bundle copied first."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            tar_a = _make_bundle(td, "pic16f87xa", "pic16f87xa-hal", extra_shared="version A\n")
            tar_b = _make_bundle(td, "pic18fxx5x", "pic18fxx5x-hal", extra_shared="version B\n")
            with self.assertRaises(SystemExit):
                package_framework.build([tar_a, tar_b], "0.6.0", td / "out.tar.gz")

    def test_dropped_family_content_caught_by_validate(self):
        """If a family's own unique content never made it into the built
        tarball, validate() must catch it even though its source-manifest
        sidecar was still written."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            out = td / "framework-epichal-0.6.0.tar.gz"
            root = td / "root"
            root.mkdir()
            (root / "epic-hal-sources-pic16f87xa.json").write_text("{}")
            (root / "package.json").write_text(json.dumps({"version": "0.6.0"}))
            with tarfile.open(out, "w:gz") as tf:
                for child in root.iterdir():
                    tf.add(child, arcname=child.name)

            with self.assertRaises(SystemExit):
                package_framework.validate(
                    out, ["pic16f87xa"], {"pic16f87xa": ["pic16f87xa-hal"]}
                )


if __name__ == "__main__":
    unittest.main()
