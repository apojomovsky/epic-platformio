# framework-epichal

Register-level drivers for 8-bit PIC, ready to use. One line in
`platformio.ini` wires them into your build.

## Try it in 60 seconds

```ini
; platformio.ini
[env:epic8]
platform = apojomovsky/epic8
board = pic16f877a
framework = epichal
build_flags = -DEPIC_HAL_MODULES=tick
```

```c
// src/main.c
#include "epic_tick.h"
#include "peripherals/hal_gpio.h"

void main(void)
{
    EPIC_GPIO_Init(GPIOB, GPIO_PIN_0, GPIO_MODE_OUTPUT);
    epic_tick_init(4000000UL);
    for (;;) {
        EPIC_GPIO_TogglePin(GPIOB, GPIO_PIN_0);
        epic_tick_delay_ms(500);
    }
}
```

`-DEPIC_HAL_MODULES` picks the modules. The `hal-tick` examples show the
shape for the boards whose family bundle ships a tick module.

## Supported parts

The package is the union of every supported family bundle: `pic16f1937`,
`pic16f628a`, `pic16f877a`, `pic16f887` and `pic18f4550` each get their
family HAL, and the builder picks the one matching the board's MCU. The
`pic12f675` has no framework content, it builds compiler-only. Module
coverage differs per family: the tick module ships for `pic16f877a`,
`pic16f887` and `pic18f4550`. It builds with epic-cc or with XC8
(`board_build.toolchain = xc8`), per board.

## One example

The `hal-tick` examples blink through the HAL tick module instead of raw
register writes. Start from
[`examples/hal-tick-pic16f877a`](https://github.com/apojomovsky/epic-platformio/tree/master/examples/hal-tick-pic16f877a);
the same example exists for `pic16f887` and `pic18f4550`.

## Links

- [epic-hal](https://github.com/apojomovsky/epic-hal), the HAL itself
- [epic-platformio](https://github.com/apojomovsky/epic-platformio), the PlatformIO glue
- [Getting started](https://github.com/apojomovsky/epic-platformio/blob/master/docs/getting-started.md)

## Where to report problems

Packaging problems (wrong files in this package, install failures) belong
in [epic-platformio](https://github.com/apojomovsky/epic-platformio/issues).
HAL bugs (wrong registers, broken modules) belong in
[epic-hal](https://github.com/apojomovsky/epic-hal/issues).

## Layout

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

Package version equals the upstream `epic-hal` tag with the leading `v`
stripped (`v0.4.0` -> `0.4.0`). A packaging-only fix bumps the package patch
version, recorded in `packages/versions.json` (D-6).
