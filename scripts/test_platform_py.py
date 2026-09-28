"""Coverage for platform.py (PIO-1, epic-platformio#44). Stdlib only: the
test substitutes a minimal platformio stub before loading platform.py, so
the suite runs in CI where PlatformIO Core is not installed.

The stub reproduces the two PlatformIO behaviors the class depends on, both
read from PlatformIO 6.1.19's own source, because a stub that gets either
wrong would hide a real defect:

- `packages` is a property that rebuilds the dict from the manifest and
  re-applies `_custom_packages` (a project's `platform_packages` pins) on
  every access (platformio/platform/base.py:88-100). Storing a remap in the
  manifest instead of answering on the property is exactly the bug this
  shape catches.
- `configure_default_packages` enables every `uploader`-typed package for
  an upload/program target (platformio/platform/base.py:199-203).

Imports are stubbed; the real factory loading the real class is verified by
hand against PlatformIO 6.1.19, not here.
"""

import importlib.util
import json
import pathlib
import re
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent

LINUX_URL = (
    "https://github.com/apojomovsky/epic-platformio/releases/download/"
    "toolchain-epiccc-v0.3.0/toolchain-epiccc-linux_x86_64-0.3.0.tar.gz"
)
WINDOWS_URL = LINUX_URL.replace("linux_x86_64", "windows_amd64")


class FakePlatformBase:
    BASE_PACKAGES = {
        "toolchain-epiccc": {"type": "toolchain", "version": LINUX_URL},
        "framework-epichal": {"type": "framework", "optional": True},
    }

    def __init__(self, manifest_path):
        self._manifest = {"packages": {k: dict(v) for k, v in self.BASE_PACKAGES.items()}}
        self._custom_packages = []
        self.super_calls = []

    @property
    def packages(self):
        # The real property: read the manifest, then overlay the project's
        # own pins, on every access.
        packages = self._manifest.get("packages", {})
        for item in self._custom_packages:
            name, _, version = item.partition("@")
            packages.setdefault(name, {})
            packages[name].update(version=version or "*", optional=False)
        return packages

    def configure_default_packages(self, variables, targets):
        self.super_calls.append((variables, targets))
        if any("upload" in t for t in targets) or "program" in targets:
            for name, opts in self.packages.items():
                if opts.get("type") == "uploader":
                    self.packages[name]["optional"] = False


class PlatformioException(Exception):
    pass


def _load_platform_module(systype, packages=None):
    fake_public = types.ModuleType("platformio.public")
    fake_exception = types.ModuleType("platformio.exception")
    fake_exception.PlatformioException = PlatformioException

    class WithPackages(FakePlatformBase):
        BASE_PACKAGES = dict(FakePlatformBase.BASE_PACKAGES)
        BASE_PACKAGES.update(packages or {})

    fake_public.PlatformBase = WithPackages
    fake_public.get_systype = lambda: systype
    fake_root = types.ModuleType("platformio")
    fake_root.public = fake_public
    fake_root.exception = fake_exception

    stubbed = {
        "platformio": fake_root,
        "platformio.public": fake_public,
        "platformio.exception": fake_exception,
    }
    saved = {name: sys.modules.get(name) for name in stubbed}
    sys.modules.update(stubbed)
    try:
        spec = importlib.util.spec_from_file_location("epic8_platform", ROOT / "platform.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return module


class HostAssetUrlTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_platform_module("linux_x86_64")

    def test_maps_each_packed_host_to_its_asset(self):
        self.assertEqual(
            self.module.host_asset_url(LINUX_URL, "linux_x86_64"), LINUX_URL
        )
        self.assertEqual(
            self.module.host_asset_url(LINUX_URL, "windows_amd64"), WINDOWS_URL
        )

    def test_swaps_back_from_the_other_hosts_asset(self):
        self.assertEqual(
            self.module.host_asset_url(WINDOWS_URL, "linux_x86_64"), LINUX_URL
        )

    def test_both_windows_spellings_name_the_one_windows_asset(self):
        for system in ("windows_amd64", "windows_x86_64"):
            self.assertEqual(
                self.module.host_asset_url(LINUX_URL, system), WINDOWS_URL
            )

    def test_leaves_a_url_with_no_host_token_alone(self):
        # A project's own platform_packages pin names no host to move.
        for url in ("0.3.0", "https://example.com/toolchain.tar.gz"):
            self.assertEqual(self.module.host_asset_url(url, "windows_amd64"), url)

    def test_an_unpacked_host_leaves_the_url_alone(self):
        # Not raising is deliberate: packages is read on uninstall, update
        # and pio pkg list as well, so a refusal here would make the
        # platform unremovable outside the beta hosts.
        for system in ("darwin_arm64", "darwin_x86_64", "linux_aarch64", "windows_x86"):
            self.assertEqual(self.module.host_asset_url(LINUX_URL, system), LINUX_URL)


class PackagesPropertyTests(unittest.TestCase):
    """The host remap must survive a read that re-applies project pins,
    which is why it lives on the property rather than in
    configure_default_packages."""

    def _platform(self, systype, packages=None):
        module = _load_platform_module(systype, packages)
        return module, module.Epic8Platform(ROOT / "platform.json")

    def test_remaps_the_pinned_toolchain_url_for_this_host(self):
        module, platform = self._platform("windows_amd64")
        self.assertEqual(
            platform.packages["toolchain-epiccc"]["version"], WINDOWS_URL
        )

    def test_leaves_the_toolchain_url_alone_on_the_host_it_pins(self):
        module, platform = self._platform("linux_x86_64")
        self.assertEqual(
            platform.packages["toolchain-epiccc"]["version"], LINUX_URL
        )

    def test_remap_still_holds_after_a_project_pin_is_reapplied(self):
        # A project's platform_packages pin is overlaid on every read; the
        # host token in it must be moved too, or the Windows host gets the
        # Linux binary (its system is linux_x86_64, so the tool manager
        # then hides the package entirely).
        module, platform = self._platform("windows_amd64")
        platform._custom_packages = ["toolchain-epiccc@" + LINUX_URL]
        self.assertEqual(
            platform.packages["toolchain-epiccc"]["version"], WINDOWS_URL
        )

    def test_a_project_pin_with_no_host_token_is_left_alone(self):
        module, platform = self._platform("windows_amd64")
        platform._custom_packages = ["toolchain-epiccc@https://example.com/x.tar.gz"]
        self.assertEqual(
            platform.packages["toolchain-epiccc"]["version"], "https://example.com/x.tar.gz"
        )

    def test_delegates_to_the_base_property(self):
        # The framework entry (not host-specific) must come through from
        # the base unchanged.
        module, platform = self._platform("linux_x86_64")
        self.assertEqual(platform.packages["framework-epichal"]["optional"], True)


class ConfigureDefaultPackagesTests(unittest.TestCase):
    def _platform(self, systype, packages=None):
        module = _load_platform_module(systype, packages)
        return module, module.Epic8Platform(ROOT / "platform.json")

    TOOLS = {
        "tool-minipro": {"optional": True},
        "tool-pk2cmd": {"optional": True},
        "tool-picpro": {"optional": True},
    }

    def test_selecting_a_protocol_pulls_its_tool_package(self):
        module, platform = self._platform("linux_x86_64", self.TOOLS)
        platform.configure_default_packages(
            {"board": "pic16f877a", "upload_protocol": "minipro"}, ["upload"]
        )
        self.assertFalse(platform.packages["tool-minipro"]["optional"])

    def test_another_protocol_does_not_pull_it(self):
        module, platform = self._platform("linux_x86_64", self.TOOLS)
        platform.configure_default_packages(
            {"board": "pic16f877a", "upload_protocol": "pk2cmd"}, ["upload"]
        )
        self.assertTrue(platform.packages["tool-minipro"]["optional"])
        self.assertFalse(platform.packages["tool-pk2cmd"]["optional"])

    def test_an_uploader_typed_package_is_turned_back_off(self):
        # The base class enables every uploader-typed package for an upload
        # target; an unselected one must be left optional anyway.
        tools = {name: {"optional": True, "type": "uploader"} for name in self.TOOLS}
        module, platform = self._platform("linux_x86_64", tools)
        platform.configure_default_packages(
            {"board": "pic16f877a", "upload_protocol": "minipro"}, ["upload"]
        )
        self.assertFalse(platform.packages["tool-minipro"]["optional"])
        self.assertTrue(platform.packages["tool-pk2cmd"]["optional"])

    def test_a_protocol_with_no_package_declared_is_a_no_op(self):
        # Until epic8-tools publishes, a mapped protocol must build, not
        # fail on a package that does not exist yet.
        module, platform = self._platform("linux_x86_64")
        self.assertIn("minipro", module.PROTOCOL_TOOL_PACKAGES)
        platform.configure_default_packages(
            {"board": "pic16f877a", "upload_protocol": "minipro"}, ["upload"]
        )
        self.assertNotIn("tool-minipro", platform.packages)

    def test_a_boards_own_default_protocol_does_not_pull_a_tool(self):
        module, platform = self._platform("linux_x86_64", self.TOOLS)
        platform.configure_default_packages({"board": "pic16f877a"}, [])
        self.assertTrue(platform.packages["tool-minipro"]["optional"])

    def test_delegates_to_the_base_class(self):
        module, platform = self._platform("linux_x86_64")
        variables = {"board": "pic16f877a"}
        platform.configure_default_packages(variables, ["upload"])
        self.assertEqual(platform.super_calls, [(variables, ["upload"])])


class MappingContractTests(unittest.TestCase):
    def test_every_mapped_protocol_is_one_the_builder_dispatches(self):
        # A mapped protocol the builder does not dispatch would pull a tool
        # package and then fail the upload with "protocol not supported".
        # custom is dispatched but maps to nothing: it is the project's
        # own upload_command, so it is the one dispatched name allowed to
        # stay out of the mapping.
        module = _load_platform_module("linux_x86_64")
        builder = (ROOT / "builder" / "main.py").read_text()
        block = re.search(r"UPLOAD_PROTOCOLS = \{(.*?)\}", builder, re.S).group(1)
        dispatched = set(re.findall(r'"(\w+)":', block))
        self.assertEqual(set(module.PROTOCOL_TOOL_PACKAGES), dispatched - {"custom"})

    def test_selecting_picpro_pulls_its_tool_package(self):
        module = _load_platform_module("linux_x86_64")
        platform = module.Epic8Platform(ROOT / "platform.json")
        platform._manifest["packages"].update(
            {k: dict(v) for k, v in ConfigureDefaultPackagesTests.TOOLS.items()}
        )
        platform.configure_default_packages(
            {"board": "pic16f877a", "upload_protocol": "picpro"}, ["upload"]
        )
        self.assertFalse(platform.packages["tool-picpro"]["optional"])


if __name__ == "__main__":
    unittest.main()
