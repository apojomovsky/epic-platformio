# toolchain-epiccc

A free, open-source C compiler for 8-bit PIC. No XC8 licence needed.
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

## Layout

The upstream bundle (`epic-cc-<ver>-x86_64-linux.zip`,
`epic-cc-<ver>-x86_64-windows.zip`,
`docs/30-distribution-design.md` "Bundle layout") already carries the pinned
clang 20.1.8 and `llvm-link`. This package adds only `package.json` and
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

## Version mapping

Package version equals the upstream `epic-cc` tag with the leading `v`
stripped (`v0.4.0` -> `0.4.0`). A packaging-only fix without a compiler
change takes the revision `<upstream>+pioN` from N=1 (`0.4.0+pio1`),
recorded against the still-pinned upstream tag in
`packages/versions.json`. That file is the single place where the mapping
lives, per D-6, so a board-definition fix here never forces a compiler
release.
