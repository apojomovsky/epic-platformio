# platform-epic8

**A PlatformIO platform for 8-bit Microchip PIC microcontrollers, built on the
open-source epic-cc toolchain.**

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

`platform-epic8` makes `pio run` compile a project with
[epic-cc](https://github.com/apojomovsky/epic-cc), the whole-program C compiler
for PIC14/PIC18, instead of Microchip's licence-gated XC8. It is the PlatformIO
glue: the platform manifest, the SCons builder, and the board definitions. It is
**not** the compiler and **not** the HAL.

| Piece | Repo | Role |
|---|---|---|
| `platform-epic8` | this repo | PlatformIO platform (registry id `epic8`): `platform.json`, `builder/main.py`, `boards/*.json` |
| `toolchain-epiccc` | epic-cc | The compiler, cut from epic-cc release bundles |
| `framework-epichal` | epic-hal | The register-level HAL and module shelf, cut from epic-hal releases |

## Supported parts

| Part | Core | Notes |
|---|---|---|
| `p16f877a` | PIC14 (mid-range) | The original epic-cc target |
| `p16f887` | PIC14 (mid-range) | Same ISA, different device data |
| `p18f4550` | PIC18 | PIC18 backend |

The list matches the device registry in
[`epic-cc/crates/device/devices/`](https://github.com/apojomovsky/epic-cc/tree/master/crates/device/devices).
Enhanced mid-range parts (`pic16f193x` and friends) are out of scope: epic-cc
has no backend for that core, and adding one is a separate decision
(design doc 31, D-1).

## Status

The platform core (PIO-1) is in place: `platform.json`, the SCons builder
and the board definitions for `p16f877a`, `p16f887` and `p18f4550`. PIO-2
cut the `toolchain-epiccc` and `framework-epichal` packages, and PIO-3 adds
the worked examples and this documentation. A project pointing at this
repository builds with `pio run` and no Microchip download. Upload is not
supported in v1 (the HEX is the deliverable) and size reporting waits on
epic-cc CC-6; both decisions are recorded in
[`docs/platform-decisions.md`](docs/platform-decisions.md). The work is
tracked as PIO-1 through PIO-3 in the
[epic-platformio issues](https://github.com/apojomovsky/epic-platformio/issues),
part of the 14-piece decomposition in
[`epic-cc/docs/31-ecosystem-integration-design.md`](https://github.com/apojomovsky/epic-cc/blob/master/docs/31-ecosystem-integration-design.md)
(D-6, section 3).

## Getting started

See [`docs/getting-started.md`](docs/getting-started.md): install the
platform, write a minimal project, use the HAL, and the worked examples
under `examples/`.

## The one-line install story

A project with a `platformio.ini` pointing at this platform builds with no
Microchip download and no XC8:

```bash
platformio platform install https://github.com/apojomovsky/epic-platformio
pio run
```

Published to the PlatformIO registry (PIO-3), the platform id is `epic8`, so
the same story becomes `platform = epic8` in `platformio.ini` or
`pio pkg install -p epic8`.

That is the goal this repository exists for: a fully open-source 8-bit PIC
toolchain reachable from PlatformIO, touching nothing on Microchip's servers.

## What this repo does not do

- **It is not the compiler.** epic-cc owns every stage from C to Intel HEX.
  This repo only tells PlatformIO how to invoke it.
- **It is not the HAL.** epic-hal owns the register-level drivers and modules.
  This repo only wires the framework package into a project.
- **It does not fix the board definitions.** Board-definition fixes (a wrong
  flash size, a wrong vector) land here without needing a compiler release;
  that is the point of D-6 in the design doc.

## Repository layout

```
platform.json      # platform metadata and package references (PIO-1)
builder/main.py    # SCons builder: sources through epic-cc in one invocation (PIO-1)
boards/*.json      # board definitions for the supported parts (PIO-1)
packages/          # package manifests and the version mapping (PIO-2)
scripts/           # package build tooling (PIO-2)
examples/          # worked examples, one per supported board (PIO-3)
docs/              # getting started and platform decisions (PIO-3)
```

## License

MIT, matching epic-cc and epic-hal. See [LICENSE](LICENSE).
