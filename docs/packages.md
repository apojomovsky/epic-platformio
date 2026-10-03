# Packages

## Version mapping (D-6)

Package versions map 1:1 to upstream release tags: the package version is
the upstream tag without the leading `v` (`epic-cc v0.4.0` wraps as
`toolchain-epiccc 0.4.0`). The mapping lives in `packages/versions.json`,
the single source that decides which upstream asset a package version
wraps. `packages/versions.json` records the upstream tag plus a note,
exactly as the release policy requires.

A packaging-only fix, with no new upstream, never reuses an upstream
version number. It takes the policy's packaging revision, `<upstream>+pio<N>`
starting at N=1 (`0.4.0+pio1`), which stays valid SemVer where a fourth
component would not, and sorts alongside the version it fixes instead of
before it the way a pre-release suffix would. The `package_version` /
`framework_package_version` overrides in `package.yml` exist only for these
revisions. History stays untouched: `toolchain-epiccc 0.0.4` wrapped
untagged master and cannot be renamed into this scheme, so it stands as
the precedent this rule prevents repeating.

This is the point of D-6 in `epic-cc/docs/31-ecosystem-integration-design.md`:
a board-definition fix landing here never forces a compiler release.

The programmer tool packages (`tool-minipro`, `tool-pk2cmd`,
`tool-picpro`) are the exception: epic-tools versions and publishes
them, so `platform.json` pins their registry versions directly and
`packages/versions.json` does not list them. The consistency checker
only covers packages listed there.

## Platform versioning

The `epic8` platform itself is versioned independently of the packages it
pins. `platform.json`'s `version` is the source of truth: `0.0.1` since
day one, `0.1.0` from this policy. A platform release is cut as tag
`epic8-vX.Y.Z` and published to the registry at that version. Before 1.0,
breaking changes bump minor, features bump minor, fixes bump patch, per
the release policy.

Breaking for the platform means one of three surfaces:

- board ids: a board renamed, removed, or moved between `boards/` and
  `boards-experimental/`;
- `platformio.ini` options: a `board_build.*` or `upload_*` option this
  platform reads, renamed, removed, or given new required values;
- minimum package versions: a platform release that no longer installs
  against an older pinned package.

The platform pins the exact epic-cc and epic-hal pair its CI proved: the
`compat` workflow builds the examples against those pins, and a platform
release follows only on green.

## Host selection (PIO-1, epic-platformio#44)

The upstream bundles are per host, and so are the packages built from them
(`toolchain-epiccc-linux_x86_64-<ver>.tar.gz`,
`toolchain-epiccc-windows_amd64-<ver>.tar.gz`). `platform.json` pins the
registry version under owner `apojomovsky`; which hosts that version
covers is the package's own `system` list. A URL pin (a project's own
`platform_packages` override) still names one host's asset, and
`platform.py` remaps that pin to the running host's asset at build time
(the reasoning is in
[`docs/platform-decisions.md`](platform-decisions.md#distribution-platformpy-picks-the-hosts-toolchain-tools-arrive-on-selection)).

Consequences for a release:

- `packages/toolchain-epiccc/package.json` declares the real `system` list
  (`linux_x86_64`, `windows_amd64`), and `scripts/package_toolchain.py`
  stamps the matching subset into each artifact it builds, so the registry
  and the package manager filter per host rather than offering every host
  the Linux binary.
- The remap answers on `packages`, so it also covers the global install
  path (`platformio platform install <url>`), which has no project attached
  and never calls `configure_default_packages`. A project's own
  `platform_packages` pin is remapped too, since `packages` re-applies those
  pins on every read.
- A host with no bundle is not refused: a URL pin naming it is passed
  through unchanged, and the toolchain package's own `system` list is what stops it
  installing there. `packages` is read on uninstall, update and `pio pkg
  list` as well as on install, so raising from it would leave the platform
  unremovable and unlistable outside the beta hosts, and would break a
  project with `board_build.toolchain = xc8`, which never needs the
  epic-cc toolchain at all.
- Adding a host (macOS, ARM) is one `TOOLCHAIN_HOSTS` entry, one real
  `system` entry here, and a bundle to pack; the remap needs no new pin.

## Building

```bash
# toolchain, per-system from the upstream bundles
python3 scripts/package_toolchain.py \
  --zip epic-cc-0.1.0-x86_64-linux.zip \
  --system linux_x86_64 \
  --version 0.1.0 \
  --out dist/toolchain-epiccc-linux_x86_64-0.1.0.tar.gz

python3 scripts/package_toolchain.py \
  --zip epic-cc-0.1.0-x86_64-windows.zip \
  --system windows_amd64 \
  --version 0.1.0 \
  --out dist/toolchain-epiccc-windows_amd64-0.1.0.tar.gz

# framework: the union of every family bundle, plus the epic-cc source
# slice (epiccc_sources) and the epic-cc source files, which the release
# bundles do not carry. --manifest and --hal-repo point at the epic-hal
# checkout.
python3 scripts/package_framework.py \
  --tar epic-hal-pic16f87xa-v0.5.0.tar.gz \
  --tar epic-hal-pic16f88x-v0.5.0.tar.gz \
  --tar epic-hal-pic18fxx5x-v0.5.0.tar.gz \
  --manifest /path/to/epic-hal/epic-common/manifest/modules.toml \
  --hal-repo /path/to/epic-hal \
  --version 0.5.0 \
  --out dist/framework-epichal-0.5.0.tar.gz
```

Each command validates the repacked archive: `package.json` parses, the
toolchain binary runs `--version`, and it compiles a minimal fixture to HEX
via the bundled discovery path (no env vars). The Windows artifact skips
execution on Linux hosts, where the PE format cannot be run.

## The epic-cc source slice

The epic-cc path links a smaller, conformant source set than the full XC8
set: the full set uses XC8-only syntax and exceeds the 877A's GPR capacity.
The epic-hal manifest records that set as `epiccc_sources`, and the framework
package build records it per family in `epic-hal-sources-<family>.json` and
copies the `src/epiccc/` files (which the release bundles omit) from the
epic-hal checkout. The builder uses the slice when present.

## Publishing

`gh workflow run package.yml -f epic_cc_version=v0.1.0` cuts the toolchain
packages from the upstream release assets and publishes them as a GitHub
Release in this repository. `platform.json` pins the registry package
(owner `apojomovsky`, exact version), not the release URL; the GitHub
Release stays the build artifact each registry upload is cut from (PIO-3).
For a packaging-only fix without a new compiler tag, pass the
packaging-revision override: `-f epic_cc_version=v0.0.3 -f package_version=0.0.3+pio1`.

`-f epic_hal_version=v0.5.0` does the same for the framework package (with
its own `-f framework_package_version=...` override for a packaging-only
revision). Both inputs can be set in the same dispatch; the `framework` job
waits on `toolchain` so the two never race to push to master. The
`framework` job discovers which family bundles that epic-hal tag actually
published (`epic-hal-<family>-<tag>.tar.gz` assets on its GitHub Release)
before downloading and packaging them, so a new family needs no change
here (PIO-7, epic-platformio#25), only a `--tar` per family when calling
`package_framework.py` by hand, as in the example above.

## Keeping the boards current

A separate scheduled workflow, `boards-refresh.yml`, regenerates the
curated `boards/` set and `boards-experimental/` (`scripts/gen_boards.py`)
against the latest epic-cc and epic-hal releases and opens a pull request
when the result differs from what's committed (PIO-7,
epic-platformio#25); see
[`docs/platform-decisions.md`](platform-decisions.md) for the design.
It runs independently of `package.yml` above: a board can list a
toolchain/family combination before that family's package is actually
cut, and the builder's own validation is what catches that gap at build
time, not a dependency between these two workflows.

Neither job stops at publishing the GitHub Release: each finishes by
running `scripts/finish_release.sh`, which writes the new version back into
`packages/versions.json`, the package's own `package.json` and
`platform.json`'s registry pin (so those three never drift the way they
did before this existed), rolls the upstream repo's `CHANGELOG.md` section
for the new tag into this repo's own `CHANGELOG.md` via
`scripts/rollup_changelog.py`, and commits and pushes the result straight
to `master`. `scripts/check_versions_consistent.py` runs in CI on every
push and PR to catch the three files drifting again if someone hand-edits
one without the others.
