# toolchain-epiccc

A fully open-source, MIT licensed C compiler for 8-bit PIC.
This package is the compiler behind `pio run` on the epic8 platform.

## Try it in 60 seconds

You never install this package by hand. The epic8 platform pulls it in.

```ini
; platformio.ini
[env:epic8]
platform = apojomovsky/epic8
board = pic16f877a
```

```bash
pio run
```

That builds `firmware.hex` with epic-cc. No Microchip download involved.

## Supported parts

Six beta parts, through the epic8 boards: `pic12f675`, `pic16f1937`,
`pic16f628a`, `pic16f877a`, `pic16f887` and `pic18f4550`. The compiler
itself covers the PIC14 and PIC18 architectures. It ships its own
clang 20.1.8, so your system compiler is never consulted.

## One example

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

More, including a blink per beta board, live under
[`examples/`](https://github.com/apojomovsky/epic-platformio/tree/master/examples).
The full walkthrough is in
[`docs/getting-started.md`](https://github.com/apojomovsky/epic-platformio/blob/master/docs/getting-started.md).

## Links

- [epic-cc](https://github.com/apojomovsky/epic-cc), the compiler itself
- [epic-platformio](https://github.com/apojomovsky/epic-platformio), the PlatformIO glue

## Where to report problems

Packaging problems (wrong files in this package, install failures) belong
in [epic-platformio](https://github.com/apojomovsky/epic-platformio/issues).
Compiler bugs (wrong code, missing parts) belong in
[epic-cc](https://github.com/apojomovsky/epic-cc/issues).
