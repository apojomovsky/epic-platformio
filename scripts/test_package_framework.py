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


def _make_bundle(td: pathlib.Path, family: str, hal_subdir: str, extra_shared: str | None = None,
                 shared_hal: dict | None = None, demos: dict | None = None) -> pathlib.Path:
    """A minimal epic-hal release bundle tar.gz in the post-restructure
    layout (epic-hal#307): the family HAL nested under the shared `hal/`
    tree (e.g. `hal/pic14/16f87xa`), the shared contract under `common/`,
    and an optional single-owner `demos/` tree, to exercise the union-copy
    merge of a top-level name every bundle carries."""
    root = td / f"src-{family}"
    top = root / f"epic-hal-{family}"
    top.mkdir(parents=True)
    (top / "VERSION").write_text("v0.6.0\n")
    (top / "epic-hal-sources.json").write_text(json.dumps({"family": family}))
    hal = top / "hal" / hal_subdir
    hal.mkdir(parents=True)
    (hal / "src.c").write_text(f"/* {family} */\n")
    for rel, content in (shared_hal or {}).items():
        p = top / "hal" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    if extra_shared:
        shared = top / "common"
        shared.mkdir(exist_ok=True)
        (shared / "shared.c").write_text(extra_shared)
    for rel, content in (demos or {}).items():
        p = top / "demos" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

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
            tar_a = _make_bundle(td, "pic16f87xa", "pic14/16f87xa", extra_shared="shared\n")
            tar_b = _make_bundle(td, "pic18fxx5x", "pic18/18fxx5x", extra_shared="shared\n")
            out = td / "framework-epichal-0.6.0.tar.gz"

            package_framework.build([tar_a, tar_b], "0.6.0", out)

            with tempfile.TemporaryDirectory() as ex:
                ex = pathlib.Path(ex)
                with tarfile.open(out, "r:gz") as tf:
                    tf.extractall(ex)
                self.assertTrue((ex / "epic-hal-sources-pic16f87xa.json").exists())
                self.assertTrue((ex / "epic-hal-sources-pic18fxx5x.json").exists())
                self.assertTrue((ex / "hal" / "pic14" / "16f87xa" / "src.c").exists())
                self.assertTrue((ex / "hal" / "pic18" / "18fxx5x" / "src.c").exists())
                # Identical shared file across both bundles: merged without complaint.
                self.assertTrue((ex / "common" / "shared.c").exists())
                self.assertEqual(json.loads((ex / "package.json").read_text())["version"], "0.6.0")

    def test_single_owner_demos_tree_is_packaged_not_skipped(self):
        """Only families with demo support ship a top-level `demos/`
        (epic-hal#307); it is consumer content like the family HAL, not
        wiring docs like `examples/`, so the union copy must keep it."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            tar_a = _make_bundle(
                td, "pic18fxx5x", "pic18/18fxx5x",
                demos={"menu/src/menu_demo_core.c": "/* menu */\n"},
            )
            tar_b = _make_bundle(td, "pic16f87xa", "pic14/16f87xa")
            out = td / "framework-epichal-0.6.0.tar.gz"

            package_framework.build([tar_a, tar_b], "0.6.0", out)

            with tempfile.TemporaryDirectory() as ex:
                ex = pathlib.Path(ex)
                with tarfile.open(out, "r:gz") as tf:
                    tf.extractall(ex)
                self.assertEqual(
                    (ex / "demos" / "menu" / "src" / "menu_demo_core.c").read_text(),
                    "/* menu */\n",
                )

    def test_shared_hal_tree_with_a_different_file_subset_per_bundle_is_merged(self):
        """The shared `hal/` tree ships a different, family-pruned subset
        of files per family bundle (e.g. `hal/pic14/core` carries each
        family's own files next to the byte-identical overlap). The merge
        must take the union, not reject on the differing file list."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            tar_paths = [
                _make_bundle(
                    td, "pic16f628a", "pic14/16f628a",
                    shared_hal={
                        "pic14/core/common.c": "shared core file\n",
                        "pic14/core/gpio.c": "pic16f628a only\n",
                    },
                ),
                _make_bundle(
                    td / "again", "pic16f87xa", "pic14/16f87xa",
                    shared_hal={
                        "pic14/core/common.c": "shared core file\n",
                        "pic14/core/adc.c": "pic16f87xa only\n",
                    },
                ),
            ]

            out = td / "framework-epichal-0.6.0.tar.gz"
            package_framework.build(tar_paths, "0.6.0", out)

            with tempfile.TemporaryDirectory() as ex:
                ex = pathlib.Path(ex)
                with tarfile.open(out, "r:gz") as tf:
                    tf.extractall(ex)
                core = ex / "hal" / "pic14" / "core"
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
            tar_a = _make_bundle(td, "pic16f87xa", "pic14/16f87xa")
            tar_b = _make_bundle(td / "again", "pic16f87xa", "pic14/16f87xa")
            with self.assertRaises(SystemExit):
                package_framework.build([tar_a, tar_b], "0.6.0", td / "out.tar.gz")

    def test_same_name_entries_that_differ_fail_loudly(self):
        """Two bundles sharing a top-level name (e.g. common) must
        actually be identical; a real divergence must not be silently
        resolved by keeping whichever bundle copied first."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            tar_a = _make_bundle(td, "pic16f87xa", "pic14/16f87xa", extra_shared="version A\n")
            tar_b = _make_bundle(td, "pic18fxx5x", "pic18/18fxx5x", extra_shared="version B\n")
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
            (root / "epic-hal-sources-pic18fxx5x.json").write_text("{}")
            (root / "package.json").write_text(json.dumps({"version": "0.6.0"}))
            with tarfile.open(out, "w:gz") as tf:
                for child in root.iterdir():
                    tf.add(child, arcname=child.name)

            with self.assertRaises(SystemExit):
                package_framework.validate(
                    out, ["pic18fxx5x"], {"pic18fxx5x": ["demos"]}
                )


if __name__ == "__main__":
    unittest.main()
