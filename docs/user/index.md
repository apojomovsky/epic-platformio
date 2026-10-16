# PlatformIO

This page is for you if you already build with PlatformIO and want `pio run` to compile your project with epic-cc. The epic8 platform adds the PIC boards to PlatformIO and wires in the compiler, so the rest of your `platformio.ini` works as it does for any other board.

If you have not used epic8 before, start with the [PlatformIO getting started guide](https://apojomovsky.github.io/epic-docs/getting-started/platformio/), which builds a blink step by step.

## Choose a board

Set `board` in `platformio.ini` to one of the ids in the [boards list](boards.md). For each part, the list shows its family, its clock, its support level and the upload protocol the platform uses by default.

Boards marked `experimental` have a definition but no curated support level or upload protocol yet. They may compile, but expect to check the result yourself.

## Debugging

The simulator boards debug through `pio debug` and VS Code with stock
gdb: breakpoints, stepping, and typed variables. See [Debugging with
`pio debug`](debugging.md).

## Upload and programmers

The boards list names the default upload protocol for each board. Programmer setup is covered on the [programmers page](https://apojomovsky.github.io/epic-docs/tools/programmers/). Boards reach the `hardware` level through the [hardware sign-off](hardware-signoff.md), which flashes each board's blink on every supported programmer.

## Source and issues

The platform is open source under the MIT licence. Its source, examples and issue tracker are in the [epic-platformio repository](https://github.com/apojomovsky/epic-platformio).
