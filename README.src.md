<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/epic-platformio-logo-dark-mode.svg">
    <img src="docs/assets/epic-platformio-logo-light-mode.svg" width="120" alt="epic8 logo: a chip temple inside a laurel wreath">
  </picture>
</p>

# epic-platformio

The PlatformIO platform for 8-bit PIC microcontrollers: a fully open source, MIT licensed path from C to hex file, for hobbyists who want `pio run` instead of a vendor IDE.

[![CI](https://github.com/apojomovsky/epic-platformio/actions/workflows/ci.yml/badge.svg)](https://github.com/apojomovsky/epic-platformio/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/apojomovsky/epic-platformio/blob/master/LICENSE) [![Release](https://img.shields.io/github/v/release/apojomovsky/epic-platformio)](https://github.com/apojomovsky/epic-platformio/releases)

## Why epic-platformio

- **Fully open source, MIT licensed.** The platform, the [epic-cc](https://github.com/apojomovsky/epic-cc) compiler and the [epic-hal](https://github.com/apojomovsky/epic-hal) hardware abstraction layer (HAL) share one licence, so you can read and audit every stage.
- **The usual PlatformIO workflow.** A `platformio.ini` and `pio run`, with build, size check and upload targets. No Microchip download is needed on the default path.
- **Complete on its own.** This page is the whole PlatformIO path; epic-cc and epic-hal document themselves without assuming PlatformIO.

**Status:** ready for hobby projects on the supported boards. See [What's in 1.0](https://apojomovsky.github.io/epic-docs/status/).

## The shortest example

A project is one `platformio.ini` and one source file. Blinking an LED on PB0 of a PIC16F877A:

```ini
--8<-- "examples/hal-tick-pic16f877a/platformio.ini"
```

```c
--8<-- "examples/hal-tick-pic16f877a/src/main.c"
```

```bash
pio run
```

You get `firmware.hex` in `.pio/build/epic8/`. The first build downloads the compiler and the HAL automatically.

## Install

```bash
pio pkg install -g --platform apojomovsky/epic8
```

Always write the platform as `apojomovsky/epic8`, with the owner. To flash a chip, connect a supported programmer and run:

```bash
pio run -t upload
```

The [upload guide](docs/getting-started.md#upload) covers the supported programmers, and the [boards reference](docs/reference/boards.md) lists the boards you can name in `board = ...`.

## Ways to use epic8

- **Command line and Make:** compile with epic-cc and build with epic-hal's Makefiles. Start at [Getting started: command line](https://apojomovsky.github.io/epic-docs/getting-started/cli/).
- **PlatformIO:** add the epic8 platform to a `platformio.ini`. Start at [Getting started: PlatformIO](https://apojomovsky.github.io/epic-docs/getting-started/platformio/).

## Where next

- [Getting started](https://apojomovsky.github.io/epic-docs/getting-started/platformio/): your first blink, step by step.
- [Guides](https://apojomovsky.github.io/epic-docs/guides/): bare metal projects, MPLAB XC8 as an alternate toolchain, programmers.
- [Reference](docs/reference/boards.md): every board, generated from the board definitions.
- [How it works](https://apojomovsky.github.io/epic-docs/explanation/): the design, for the curious.
- [Examples](examples/): one buildable project per supported part and style.

## Contributing and licence

Contributions are welcome: see [Contributing](https://apojomovsky.github.io/epic-docs/contributing/). epic-platformio is MIT licensed; see [LICENSE](LICENSE).
