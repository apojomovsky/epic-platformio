# Packages

Maintainer notes for the registry packages this repo publishes: what
each tarball contains and how its version maps to upstream. The
user-facing copy lives in each package's own `README.md`. The release
flow (building the tarballs, publishing, the consistency checker) is in
[`docs/packages.md`](../docs/packages.md).

## toolchain-epiccc layout

The upstream bundle (`epic-cc-<ver>-x86_64-linux.zip`,
`epic-cc-<ver>-x86_64-windows.zip`,
`docs/30-distribution-design.md` "Bundle layout") already carries the pinned
clang 20.1.8 and `llvm-link`. The package adds only `package.json` and
repacks the bundle as a PlatformIO `tar.gz` so it can be installed with the
package manager. No system clang is used.

```
toolchain-epiccc/
  package.json
  epic-cc           # or epic-cc.exe on Windows
  clang/
    bin/clang       # + llvm-link, DLLs on Windows
    lib/clang/20/   # builtin headers
  LICENSE
```

The builder (`builder/main.py`, PIO-1) resolves the compiler as
`platform.get_package_dir("toolchain-epiccc") + "/epic-cc"`.

## framework-epichal layout

```
framework-epichal/
  package.json
  epic-common/
  epic-bus/
  epic-...
  pic16f87xa-hal/
  pic16f88x-hal/
  pic18fxx5x-hal/
  epic-hal-sources-pic16f87xa.json
  epic-hal-sources-pic16f88x.json
  epic-hal-sources-pic18fxx5x.json
  VERSION
```

The package is the union of every supported family bundle: the shared
modules are copied once, each family's hal dir is kept separate, and each
family's source manifest is renamed per family so the builder can pick the
one matching the board's MCU. Each source manifest also carries the
`epiccc_sources` slice, the epic-cc conformant source set, and the
`src/epiccc/` files are copied in from the epic-hal checkout (the release
bundles omit them).

The builder wires the framework into the include path and sources; no
compilation happens inside the package itself.

## Version mapping

Package version equals the upstream tag with the leading `v` stripped
(`epic-cc v0.4.0` -> `toolchain-epiccc 0.4.0`,
`epic-hal v0.6.0` -> `framework-epichal 0.6.0`). A packaging-only fix
without a new upstream tag takes the revision `<upstream>+pioN` from N=1
(`0.4.0+pio1`), recorded against the still-pinned upstream tag in
`packages/versions.json`. That file is the single place where the mapping
lives, per D-6, so a board-definition fix here never forces a compiler
release.
