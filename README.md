<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/epic-platformio-logo-dark-mode.svg">
    <img src="docs/assets/epic-platformio-logo-light-mode.svg" width="120" alt="Epic8 logo: a chip-temple inside a laurel wreath">
  </picture>
</p>

<h1 align="center">platform-epic8</h1>

<p align="center"><em>pio run for 8-bit PIC. epic-cc is the default toolchain; MPLAB XC8 is a fully supported alternate.</em></p>

<p align="center">

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![CI](https://github.com/apojomovsky/epic-platformio/actions/workflows/ci.yml/badge.svg)](https://github.com/apojomovsky/epic-platformio/actions/workflows/ci.yml) [![Toolchain: epic-cc](https://img.shields.io/badge/toolchain-epic--cc-blue.svg)](https://github.com/apojomovsky/epic-cc) [![Toolchain: MPLAB XC8](https://img.shields.io/badge/toolchain-MPLAB%20XC8-green.svg)](https://www.microchip.com/mpgb/xc8.html) [![HAL: epic-hal](https://img.shields.io/badge/HAL-epic--hal-blue.svg)](https://github.com/apojomovsky/epic-hal) [![status: early](https://img.shields.io/badge/status-early-yellow.svg)](#status)

</p>

PlatformIO is the workflow most embedded developers already use; 8-bit PIC has
so far meant leaving it for Microchip's licence-gated MPLAB X and XC8.
`platform-epic8` closes that gap: it's the PlatformIO platform that builds a
PIC14/PIC18 project with [epic-cc](https://github.com/apojomovsky/epic-cc), a
real open-source compiler, and wires in
[epic-hal](https://github.com/apojomovsky/epic-hal) as an optional framework.
`pio run` just works with epic-cc, and no Microchip download is needed for
that default path. And where a device or workflow needs it, the same project
builds with MPLAB XC8 as a fully supported alternate toolchain: set
`board_build.toolchain = xc8` and the platform drives your own installed XC8
instead.

## Quickstart

```bash
platformio platform install https://github.com/apojomovsky/epic-platformio
```

```ini
; platformio.ini
[env:epic8]
platform = epic8
board = p16f877a
```

```c
// src/main.c
#include <epic-cc.h>

EPIC_CONFIG("osc=hs, xtal_hz=4000000, wdt=off, lvp=off");

void main(void)
{
    for (;;) {
        __epic_nop();
    }
}
```

```bash
pio run
```

That produces `firmware.hex` in `.pio/build/epic8/`. Full walkthrough,
including wiring in the HAL, is in
[`docs/getting-started.md`](docs/getting-started.md); eight worked examples,
the same four again under each toolchain (blink and epic-tick plus GPIO),
live under
[`examples/`](examples/).

## What you get

- **A familiar workflow.** `platformio.ini` + `pio run`, the same shape as
  every other PlatformIO platform: no MPLAB X, no separate toolchain install
  on the epic-cc default path. XC8 users set `board_build.toolchain = xc8`
  and use their existing install.
- **A real compiler underneath.** The default toolchain,
  [epic-cc](https://github.com/apojomovsky/epic-cc), owns every stage from C
  to Intel HEX with no Microchip download; this repo is just the PlatformIO
  glue (platform manifest, SCons builder, board definitions). With
  `board_build.toolchain = xc8`, the glue drives your installed MPLAB XC8
  instead.
- **The HAL is one line away.** `framework = epichal` pulls in
  [epic-hal](https://github.com/apojomovsky/epic-hal)'s register-level drivers
  and module shelf, picked with `-DEPIC_HAL_MODULES`.
- **Board fixes without a compiler release.** A wrong flash size or vector
  table is a board-definition fix in this repo, decoupled from epic-cc's
  release cycle.

## Supported parts

[`boards/`](boards/) has one board per device either epic-cc or epic-hal
supports (115 as of PIO-6), generated from both repos' own device
registries rather than hand-curated: see
[`docs/getting-started.md#supported-parts`](docs/getting-started.md#supported-parts)
for what each board's capability fields mean and how to regenerate the
set.

## Status

**Early.** Building works end-to-end today: `pio run` compiles a supported
part, with epic-cc (no Microchip download on that path) or with MPLAB XC8
as the alternate. Flashing does not yet:
`pio run -t upload` isn't wired to a programmer, and HEX size reporting isn't
wired to `pio run -t size`. Both are open work, tracked in
[`docs/platform-decisions.md`](docs/platform-decisions.md) and the
[issue tracker](https://github.com/apojomovsky/epic-platformio/issues). Not
yet published to the PlatformIO registry: install from the git URL above
until it is.

<details>
<summary><strong>Under the hood</strong>: how this repo fits with epic-cc and epic-hal</summary>

Three repos, three jobs:

| Piece | Repo | Role |
|---|---|---|
| `platform-epic8` | this repo | PlatformIO platform (registry id `epic8`): `platform.json`, `builder/main.py`, `boards/*.json` |
| `toolchain-epiccc` | epic-cc | The compiler, packaged from epic-cc release bundles |
| `framework-epichal` | epic-hal | The HAL and module shelf, packaged from epic-hal releases |

This repo is deliberately thin: it is not the compiler (epic-cc owns every
stage from C to HEX) and not the HAL (epic-hal owns the drivers). It only
tells PlatformIO how to invoke them and describes the boards.

Repository layout:

```
platform.json      # platform metadata and package references
builder/main.py    # SCons builder: sources through epic-cc in one invocation
boards/*.json       # board definitions for the supported parts
packages/           # package manifests and the version mapping
examples/           # worked examples, one per supported board
docs/               # getting started and platform decisions
```

The full decomposition (why this is three repos, and what's left) is in
[`epic-cc/docs/31-ecosystem-integration-design.md`](https://github.com/apojomovsky/epic-cc/blob/master/docs/31-ecosystem-integration-design.md).

</details>

## License

MIT, matching epic-cc and epic-hal. See [LICENSE](LICENSE).
