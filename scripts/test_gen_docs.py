"""Coverage for scripts/gen_docs.py (epic-platformio#114). No network, no
registry: rendering and checks run against small hand-authored fixtures
through the same code path as the real tree.
"""

import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HELPER = ROOT / "scripts" / "gen_docs.py"

_spec = importlib.util.spec_from_file_location("gen_docs", HELPER)
gen_docs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_docs)


def make_board(board_id, mcu="pmcu", f_cpu="4000000L", protocol="minipro",
               tools=("minipro", "pk2cmd"), support="simulator"):
    doc = {
        "build": {"mcu": mcu, "toolchains": ["epic-cc"]},
        "name": f"Microchip {board_id.upper()}",
        "support": support,
        "upload": {"devices": dict.fromkeys(tools, "DEV"), "protocol": protocol},
    }
    if f_cpu is not None:
        doc["build"]["f_cpu"] = f_cpu
    return doc


class BoardsTest(unittest.TestCase):
    def test_table_columns_and_sort(self):
        with tempfile.TemporaryDirectory() as tmp:
            boards = pathlib.Path(tmp)
            (boards / "b-regular.json").write_text(json.dumps(make_board("b")))
            (boards / "a-no-fcpu.json").write_text(
                json.dumps(make_board("a", f_cpu=None, tools=("minipro",))))
            old, gen_docs.BOARDS_DIR = gen_docs.BOARDS_DIR, boards
            try:
                out = gen_docs.render_boards()
            finally:
                gen_docs.BOARDS_DIR = old
        self.assertTrue(out.startswith(gen_docs.GENERATED_BY + "\n# Boards\n"))
        self.assertIn("| Board | MCU | Frequency | Upload | Support |", out)
        a_line = [l for l in out.splitlines() if l.startswith("| `a-no-fcpu`")][0]
        b_line = [l for l in out.splitlines() if l.startswith("| `b-regular`")][0]
        self.assertLess(out.index(a_line), out.index(b_line))
        self.assertIn("not set", a_line)
        self.assertIn("`4000000L`", b_line)
        self.assertIn("minipro (minipro, pk2cmd)", b_line)


class IncludesTest(unittest.TestCase):
    def test_nested_missing_and_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            (repo / "inc").mkdir()
            (repo / "inc" / "inner.md").write_text("inner\n")
            (repo / "inc" / "outer.md").write_text('head\n--8<-- "inc/inner.md"\n')
            old, gen_docs.REPO = gen_docs.REPO, repo
            try:
                out = gen_docs.resolve_includes('top\n--8<-- "inc/outer.md"\n')
                self.assertEqual(out, "top\nhead\ninner\n")
                with self.assertRaises(ValueError):
                    gen_docs.resolve_includes('--8<-- "inc/gone.md"\n')
                (repo / "inc" / "loop.md").write_text('--8<-- "inc/loop.md"\n')
                with self.assertRaises(ValueError):
                    gen_docs.resolve_includes('--8<-- "inc/loop.md"\n')
            finally:
                gen_docs.REPO = old


class AbsolutizeTest(unittest.TestCase):
    def test_links_images_html_and_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            (repo / "docs").mkdir()
            (repo / "docs" / "page.md").write_text("x")
            (repo / "docs" / "shots").mkdir()
            old, gen_docs.REPO = gen_docs.REPO, repo
            try:
                out = gen_docs.absolutize_markdown(
                    "[page](docs/page.md)\n"
                    "[dir](docs/shots)\n"
                    "![shot](docs/shots/a.png)\n"
                    '<img src="docs/shots/a.png">\n'
                    '<a href="docs/page.md">p</a>\n'
                    "[abs](https://example.com/x)\n"
                    "[frag](#status)\n"
                    "```\n[code](docs/page.md)\n```\n"
                    "`[span](docs/page.md)`\n")
            finally:
                gen_docs.REPO = old
        blob = gen_docs.BLOB + "/docs/page.md"
        self.assertIn(f"[page]({blob})", out)
        self.assertIn(f"[dir]({gen_docs.TREE}/docs/shots)", out)
        self.assertIn(f"![shot]({gen_docs.RAW}/docs/shots/a.png)", out)
        self.assertIn(f'<img src="{gen_docs.RAW}/docs/shots/a.png">', out)
        self.assertIn(f'<a href="{blob}">p</a>', out)
        self.assertIn("[abs](https://example.com/x)", out)
        self.assertIn("[frag](#status)", out)
        self.assertIn("[code](docs/page.md)", out)
        self.assertIn("`[span](docs/page.md)`", out)

    def test_find_relative_links(self):
        self.assertEqual(
            gen_docs.find_relative_links("[a](docs/x.md) and <img src=\"i.png\">\n"),
            ["docs/x.md", "i.png"])
        self.assertEqual(
            gen_docs.find_relative_links(
                f"[a]({gen_docs.BLOB}/docs/x.md)\n```\n[b](docs/y.md)\n```\n"), [])


class ChecksTest(unittest.TestCase):
    def write_tree(self, root, keywords=(), license="MIT", readme="README.md",
                   platform="apojomovsky/epic8", manifest=True):
        (root / "packages" / "pkg-a").mkdir(parents=True)
        pkg = root / "packages" / "pkg-a" / "package.json"
        if manifest:
            doc = {"keywords": list(keywords)}
            if license is not None:
                doc["license"] = license
            if readme is not None:
                doc["readme"] = readme
                (root / "packages" / "pkg-a" / readme).write_text("pkg\n")
            pkg.write_text(json.dumps(doc))
        (root / "platform.json").write_text(json.dumps({"keywords": list(keywords)}))
        (root / "examples" / "ex-a").mkdir(parents=True)
        (root / "examples" / "ex-a" / "platformio.ini").write_text(
            f"[env:a]\nplatform = {platform}\nboard = pic16f877a\n")
        return pkg

    def run_with(self, root):
        olds = (gen_docs.PLATFORM_JSON, gen_docs.PACKAGES_DIR, gen_docs.EXAMPLES_DIR)
        gen_docs.PLATFORM_JSON = root / "platform.json"
        gen_docs.PACKAGES_DIR = root / "packages"
        gen_docs.EXAMPLES_DIR = root / "examples"
        try:
            return (gen_docs.check_keywords() + gen_docs.check_package_manifests()
                    + gen_docs.check_examples())
        finally:
            (gen_docs.PLATFORM_JSON, gen_docs.PACKAGES_DIR,
             gen_docs.EXAMPLES_DIR) = olds

    def test_clean_tree_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_tree(pathlib.Path(tmp), keywords=("a", "b"))
            self.assertEqual(self.run_with(pathlib.Path(tmp)), [])

    def test_keyword_cap_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.write_tree(root, keywords=tuple(f"k{i}" for i in range(21)))
            errors = self.run_with(root)
            self.assertTrue(any("21 keywords" in e for e in errors))

    def test_licence_readme_and_platform(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.write_tree(root, license="all rights reserved", readme=None,
                            platform="epic8")
            errors = self.run_with(root)
            self.assertTrue(any("licence" in e for e in errors))
            self.assertTrue(any("readme field" in e for e in errors))
            self.assertTrue(any("apojomovsky/epic8" in e for e in errors))

    def test_missing_readme_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            pkg = self.write_tree(root)
            (root / "packages" / "pkg-a" / "README.md").unlink()
            errors = self.run_with(root)
            self.assertTrue(any("does not exist" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
