"""PlatformIO platform class for epic8 (PIO-1, epic-platformio#44).

Two facts `platform.json` cannot express by itself:

- epic-cc ships one bundle per host, while `platform.json` pins one download
  URL per package. Which asset that URL should be is only knowable from the
  running machine, so the pin is remapped here (D-5, the shape
  Community-PIO-CH32V's `configure_default_packages` uses).
- A programmer tool package is worth downloading only for a project that
  asked for the protocol needing it (D-5).

Why the pin is remapped rather than duplicated per host: `platform.json`
stays the single place a version is pinned (D-5, docs/packages.md), and the
remap is a pure function of that pin, so the two hosts cannot drift to two
versions the way two hand-kept pins would.

Design: docs/platform-decisions.md, epic-cc docs/46 D-5 and D-10.
"""

from platformio.public import PlatformBase, get_systype

TOOLCHAIN_PACKAGE = "toolchain-epiccc"

# PlatformIO systype -> the host token in that host's release asset name.
# Both Windows spellings PlatformIO can report map to the one asset this
# repo packs, as packages/toolchain-epiccc/package.json declares them; the
# beta is Linux x86_64 with Windows next (docs/46 D-1).
TOOLCHAIN_HOSTS = {
    "linux_x86_64": "linux_x86_64",
    "windows_amd64": "windows_amd64",
    "windows_x86_64": "windows_amd64",
}

# Upload protocol -> the epic8-tools package providing that programmer
# (D-10). Keys are the tool-driven protocols builder/main.py dispatches;
# custom is dispatched there but maps to nothing, it is the project's own
# upload_command. Activation below only touches a package platform.json
# declares, so a name here is inert until that package exists.
PROTOCOL_TOOL_PACKAGES = {
    "minipro": "tool-minipro",
    "pk2cmd": "tool-pk2cmd",
    "picpro": "tool-picpro",
}


def host_asset_url(url: str, system: str) -> str:
    """The same release asset as `url`, for the host `system`.

    The release tag and version are untouched; only the host token in the
    asset file name moves. A host with no bundle, or a URL naming no packed
    host token, is returned unchanged: a project's own `platform_packages`
    pin (a bare version, a URL this platform does not build per host, or a
    host this platform does not pack) names nothing this class can move.

    Not raising is deliberate. PlatformIO reads `packages` on the removal
    and listing paths too, so a refusal here would leave the platform
    unremovable and unlistable on any other host, and it would break an
    xc8-only project, which never needs the epic-cc toolchain at all.
    """
    asset_host = TOOLCHAIN_HOSTS.get(system)
    if not asset_host:
        return url
    name = url.rsplit("/", 1)[-1]
    for token in sorted(set(TOOLCHAIN_HOSTS.values())):
        if token in name:
            return url[: len(url) - len(name)] + name.replace(token, asset_host)
    return url


class Epic8Platform(PlatformBase):
    @property
    def packages(self):
        """The manifest's packages with this host's toolchain asset.

        The host remap has to live on the property, not in
        `configure_default_packages`, because `packages` re-applies a
        project's `platform_packages` pins on every read: a value written
        into the manifest earlier is overwritten by the pin on the next
        read, and every consumer (the installer included) reads through
        here. Remapping on each read also covers the global install path,
        which never calls `configure_default_packages` because it has no
        project attached.
        """
        packages = super().packages
        if TOOLCHAIN_PACKAGE in packages:
            packages[TOOLCHAIN_PACKAGE]["version"] = host_asset_url(
                packages[TOOLCHAIN_PACKAGE]["version"], get_systype()
            )
        return packages

    def configure_default_packages(self, variables, targets):
        super().configure_default_packages(variables, targets)

        # An explicit `upload_protocol` means the project drives that
        # programmer. The board's own `upload.protocol` default does not
        # count: every board names one, so treating it as a selection would
        # make a plain `pio run` download a tool the user may already have
        # on PATH (the bring-your-own-binary path, docs/platform-decisions.md).
        selected = PROTOCOL_TOOL_PACKAGES.get(variables.get("upload_protocol"))
        for tool_package in PROTOCOL_TOOL_PACKAGES.values():
            if tool_package not in self.packages:
                continue
            if tool_package == selected:
                self.packages[tool_package]["optional"] = False
            elif self.packages[tool_package].get("type") == "uploader":
                # The base class enables every uploader-typed package for an
                # upload target regardless of protocol, so an unselected one
                # has to be turned back off here. A `tool`-typed entry was
                # never enabled, so this branch leaves it alone.
                self.packages[tool_package]["optional"] = True
