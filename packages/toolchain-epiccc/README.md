# toolchain-epiccc

PlatformIO package wrapping the `epic-cc` release bundle.

The upstream bundle (`epic-cc-<ver>-x86_64-linux.zip`, `epic-cc-<ver>-x86_64-windows.zip`,
`docs/30-distribution-design.md` "Bundle layout") already carries the pinned
clang 20.1.8 and `llvm-link`. This package adds only `package.json` and
repacks the bundle as a PlatformIO `tar.gz` so it can be installed with the
package manager. No system clang is used.

## Layout

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

## Version mapping

Package version equals the upstream `epic-cc` tag with the leading `v`
stripped (`v0.0.3` -> `0.0.3`). When packaging needs a fix without a compiler
change, bump the package patch version (`0.0.3` -> `0.0.4`) and record the
upstream still pinned to `v0.0.3` in `packages/versions.json`. That file is
the single place where the mapping lives, per D-6, so a board-definition fix
here never forces a compiler release.
