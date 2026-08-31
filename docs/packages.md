# Packages

## Version mapping (D-6)

Package versions are not welded to upstream release tags. The mapping lives
in `packages/versions.json`, the single source that decides which upstream
asset a package version wraps.

For `toolchain-epiccc` the package version tracks the upstream `epic-cc`
tag with the leading `v` stripped (`v0.0.3` -> `0.0.3`). When only packaging
needs a fix, bump the package patch version (`0.0.3` -> `0.0.4`) while the
upstream stays pinned to `v0.0.3`. The same rule holds for
`framework-epichal` against `epic-hal` tags.

This is the point of D-6 in `epic-cc/docs/31-ecosystem-integration-design.md`:
a board-definition fix landing here never forces a compiler release.

## Building

```bash
# toolchain, per-system from the upstream bundles
python3 scripts/package_toolchain.py \
  --zip epic-cc-0.0.3-x86_64-linux.zip \
  --system linux_x86_64 \
  --version 0.0.3 \
  --out dist/toolchain-epiccc-linux_x86_64-0.0.3.tar.gz

python3 scripts/package_toolchain.py \
  --zip epic-cc-0.0.3-x86_64-windows.zip \
  --system windows_amd64 \
  --version 0.0.3 \
  --out dist/toolchain-epiccc-windows_amd64-0.0.3.tar.gz

# framework (platform-independent, HAL-5 gates publication)
python3 scripts/package_framework.py \
  --tar epic-hal-pic16f87xa-v0.4.0.tar.gz \
  --version 0.4.0 \
  --out dist/framework-epichal-0.4.0.tar.gz
```

Each command validates the repacked archive: `package.json` parses, the
toolchain binary runs `--version`, and it compiles a minimal fixture to HEX
via the bundled discovery path (no env vars). The Windows artifact skips
execution on Linux hosts, where the PE format cannot be run.

## Publishing

`gh workflow run package.yml -f epic_cc_version=v0.0.3` cuts the toolchain
packages from the upstream release assets and publishes them as a GitHub
Release in this repository. The release URL is what PIO-1's `platform.json`
will reference until the packages are uploaded to the PlatformIO registry
(PIO-3). For a packaging-only fix without a new compiler tag, pass the
override: `-f epic_cc_version=v0.0.3 -f package_version=0.0.4`. Framework
publishing stays blocked by HAL-5 and is not triggered by this workflow.
