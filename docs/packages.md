# Packages

## Version mapping (D-6)

Package versions are not welded to upstream release tags. The mapping lives
in `packages/versions.json`, the single source that decides which upstream
asset a package version wraps.

For `toolchain-epiccc` the package version tracks the upstream `epic-cc`
tag with the leading `v` stripped (`v0.0.3` -> `0.0.3`). When only packaging
needs a fix, bump the package patch version (`0.0.3` -> `0.0.4`) while the
upstream stays pinned. The same rule holds for `framework-epichal` against
`epic-hal` tags.

This is the point of D-6 in `epic-cc/docs/31-ecosystem-integration-design.md`:
a board-definition fix landing here never forces a compiler release.

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
Release in this repository. The release URL is what `platform.json` references
until the packages are uploaded to the PlatformIO registry (PIO-3). For a
packaging-only fix without a new compiler tag, pass the override:
`-f epic_cc_version=v0.0.3 -f package_version=0.0.4`.

The framework package is published by hand from the build command above
(`gh release create framework-epichal-v0.5.0 dist/framework-epichal-0.5.0.tar.gz`),
since it combines several family bundles and the epic-cc source slice rather
than wrapping a single upstream asset.
