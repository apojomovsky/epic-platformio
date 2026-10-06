<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/apojomovsky/epic-platformio/master/docs/assets/epic-platformio-logo-dark-mode.svg">
    <img src="https://raw.githubusercontent.com/apojomovsky/epic-platformio/master/docs/assets/epic-platformio-logo-light-mode.svg" width="120" alt="Epic8 logo: a chip-temple inside a laurel wreath">
  </picture>
</p>

<h1 align="center">platform-epic8</h1>

<p align="center"><em>pio run for 8-bit PIC. epic-cc is the default toolchain; MPLAB XC8 is a fully supported alternate.</em></p>

<p align="center">

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/apojomovsky/epic-platformio/blob/master/LICENSE) [![CI](https://github.com/apojomovsky/epic-platformio/actions/workflows/ci.yml/badge.svg)](https://github.com/apojomovsky/epic-platformio/actions/workflows/ci.yml) [![Toolchain: epic-cc](https://img.shields.io/badge/toolchain-epic--cc-blue.svg)](https://github.com/apojomovsky/epic-cc) [![Toolchain: MPLAB XC8](https://img.shields.io/badge/toolchain-MPLAB%20XC8-green.svg)](https://www.microchip.com/mpgb/xc8.html) [![HAL: epic-hal](https://img.shields.io/badge/HAL-epic--hal-blue.svg)](https://github.com/apojomovsky/epic-hal) [![status: early](https://img.shields.io/badge/status-early-yellow.svg)](#status)

</p>

PlatformIO is the workflow most embedded developers already use; 8-bit PIC has
so far meant leaving it for Microchip's MPLAB X and XC8.
`platform-epic8` closes that gap with a fully open-source, MIT licensed
toolchain you can read and audit from C to HEX: it's the PlatformIO platform
that builds a PIC14/PIC18 project with [epic-cc](https://github.com/apojomovsky/epic-cc)
and wires in [epic-hal](https://github.com/apojomovsky/epic-hal) as an
optional framework under the same licence. `pio run` just works with
epic-cc, and no Microchip download is needed for that default path. And
where a device or workflow needs it, the same project builds with MPLAB
XC8 as a fully supported alternate toolchain: set
`board_build.toolchain = xc8` and the platform drives your own installed XC8
instead.

## Quickstart

```bash
pio pkg install -g --platform apojomovsky/epic8
```

```ini
; platformio.ini
[env:epic8]
platform = apojomovsky/epic8
board = pic16f877a
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
[`docs/getting-started.md`](https://github.com/apojomovsky/epic-platformio/blob/master/docs/getting-started.md);
worked examples live under
[`examples/`](https://github.com/apojomovsky/epic-platformio/tree/master/examples/),
a tutorial-style blink per beta board plus the HAL integration proof and the
XC8 variants.

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

[`boards/`](https://github.com/apojomovsky/epic-platformio/tree/master/boards/) is the curated beta set: six boards, one per beta part
(`pic16f877a`, `pic16f887`, `pic16f628a`, `pic12f675`, `pic16f1937`,
`pic18f4550`), each carrying sizes, per-tool device names and the
programming hazards its part needs warned about. Everything else either
registry knows lives in
[`boards-experimental/`](https://github.com/apojomovsky/epic-platformio/tree/master/boards-experimental/),
capability-only files you copy into your project's own `boards/`. Both sets
are generated from the two upstream registries rather than hand-maintained;
see
[`docs/getting-started.md#supported-parts`](https://github.com/apojomovsky/epic-platformio/blob/master/docs/getting-started.md#supported-parts)
for what each board's capability fields mean and how to regenerate the
sets.

## Compatibility

The beta publishes platform, toolchain and framework to the PlatformIO
registry under the personal owner. The platform pins exact package
versions, so a beta project builds the same toolchain and framework
everywhere:

| Piece | Registry package | Version | Upstream |
|---|---|---|---|
| platform | `apojomovsky/epic8` | `0.1.1` | this repo |
| toolchain | `apojomovsky/toolchain-epiccc` | `0.4.0+pio1` | [epic-cc `v0.4.0`](https://github.com/apojomovsky/epic-cc/releases/tag/v0.4.0) |
| framework | `apojomovsky/framework-epichal` | `0.6.0+pio1` | [epic-hal `v0.6.0`](https://github.com/apojomovsky/epic-hal/releases/tag/v0.6.0) |

Programmer tools install only when the project selects their protocol.
`tool-minipro` (`0.7.4+pio3`) and `tool-pk2cmd` (`1.27.1+pio2`) are published to the registry by #85:
`minipro` or `pk2cmd` pulls the package, otherwise the builder falls back
to `EPIC8_*_PATH` or `PATH`. `tool-picpro` (`0.4.1+pio3`) is live: selecting
`picpro` pulls the package, otherwise the builder falls back to
`EPIC8_PICPRO_PATH` or `PATH`.

## Status

**Early.** Building works end-to-end today: `pio run` compiles a supported
part, with epic-cc (no Microchip download on that path) or with MPLAB XC8
as the alternate. Flashing works through `pio run -t upload` (plus
`erase` and `readback`) with a TL866 programmer, a PICkit, a K150, or a
custom `upload_command`; see
[`docs/getting-started.md#upload`](https://github.com/apojomovsky/epic-platformio/blob/master/docs/getting-started.md#upload) and one
guide per programmer under [`docs/programmers/`](https://github.com/apojomovsky/epic-platformio/tree/master/docs/programmers/). `pio
run -t size` prints PlatformIO's program-size bar from the driver's own
build report, and the same check gates `pio run -t upload` so an oversized
image is refused before flashing. The beta is on the PlatformIO registry
as `apojomovsky/epic8`: install it with the command above.

<details>
<summary><strong>Under the hood</strong>: how this repo fits with epic-cc and epic-hal</summary>

Three repos, three jobs:

| Piece | Repo | Role |
|---|---|---|
| `platform-epic8` | this repo | PlatformIO platform (registry id `epic8`): `platform.json`, `builder/main.py`, `boards/` |
| `toolchain-epiccc` | epic-cc | The compiler, packaged from epic-cc release bundles |
| `framework-epichal` | epic-hal | The HAL and module shelf, packaged from epic-hal releases |

This repo is deliberately thin: it is not the compiler (epic-cc owns every
stage from C to HEX) and not the HAL (epic-hal owns the drivers). It only
tells PlatformIO how to invoke them and describes the boards.

Repository layout:

```
platform.json      # platform metadata and package references
platform.py         # per-host package selection (PlatformIO platform class)
builder/main.py    # SCons builder: sources through epic-cc in one invocation
boards/             # the curated beta boards
boards-experimental # generated copy-into-your-project boards
packages/           # package manifests and the version mapping
examples/           # worked examples, tutorial-style and HAL, per beta board
docs/               # getting started and platform decisions
```

The full decomposition (why this is three repos, and what's left) is in
[`epic-cc/docs/31-ecosystem-integration-design.md`](https://github.com/apojomovsky/epic-cc/blob/master/docs/31-ecosystem-integration-design.md).

</details>

## License

MIT, matching epic-cc and epic-hal. See [LICENSE](https://github.com/apojomovsky/epic-platformio/blob/master/LICENSE).
