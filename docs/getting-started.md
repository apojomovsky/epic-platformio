# Getting started

`platform-epic8` (registry id `epic8`) builds a PlatformIO project with
[epic-cc](https://github.com/apojomovsky/epic-cc), the open-source
whole-program C compiler for PIC14/PIC18, instead of Microchip's
licence-gated XC8. Nothing is downloaded from Microchip's servers.

## Install the platform

```bash
pio pkg install -p epic8
```

or, from a checkout of this repository:

```bash
platformio platform install https://github.com/apojomovsky/epic-platformio
```

## A minimal project

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

The build produces `firmware.hex` in `.pio/build/epic8/`. That HEX is the
deliverable; see [Upload](#upload) for what the platform does and does not
do with it.

## Using the HAL

The epic-hal framework is optional. Enable it with `framework = epichal`
and pick the modules with `-DEPIC_HAL_MODULES`:

```ini
[env:epic8]
platform = epic8
board = p16f877a
framework = epichal
build_flags = -DEPIC_HAL_MODULES=tick
```

```c
#include "epic_tick.h"
#include "peripherals/hal_gpio.h"

void main(void)
{
    EPIC_GPIO_Init(GPIOB, GPIO_PIN_0, GPIO_MODE_OUTPUT);
    epic_tick_init(FOSC_HZ);
    for (;;) {
        EPIC_GPIO_TogglePin(GPIOB, GPIO_PIN_0);
        epic_tick_delay_ms(500);
    }
}
```

The builder wires in the family HAL and the selected module sources. The
module list is comma-separated and resolved transitively, so
`-DEPIC_HAL_MODULES=tick` pulls in `epic-common` and the family HAL.

## Worked examples

The `examples/` directory holds one project per supported board, each
buildable from a clean checkout:

| Example | Board | What it proves |
|---|---|---|
| `blink-p16f877a` | PIC16F877A | the compiler path alone |
| `blink-p16f887` | PIC16F887 | a new device on a supported core |
| `blink-p18f4550` | PIC18F4550 | the PIC18 backend |
| `hal-tick-p16f877a` | PIC16F877A | epic-tick plus GPIO, the integration proof |

Copy one into a fresh directory and run `pio run`.

## Config words

Config words are spelled with `EPIC_CONFIG`, not `#pragma config` (docs/31
D-4). The argument is a comma-separated `key=value` list using the
datasheet's own names. Everything unstated takes the device's documented
default, and epic-cc prints the resolved config words so defaults never mean
unexamined silicon state.

`xtal_hz` is not a silicon bit; it is the crystal frequency the compiler
needs to derive `EPIC_FOSC_HZ`, the one source of truth for the system
clock. The PIC18F4550's clock tree needs the oscillator, PLL and CPU
divider named explicitly:

```c
EPIC_CONFIG("osc=hs, xtal_hz=4000000, cpudiv=div1, plldiv=noprescale, usbdiv=off, wdt=off, lvp=off");
```

## Upload

`pio run -t upload` is not supported in v1: the HEX is the deliverable, and
flashing is left to your own programmer (pk2cmd, ipecmd, a bootloader).
The platform fails upload with a clear message rather than pretending to
flash. The decision and its rejected alternatives are recorded in
[`docs/platform-decisions.md`](platform-decisions.md).

## Supported parts

| Part | Core | Notes |
|---|---|---|
| `p16f877a` | PIC14 (mid-range) | the original epic-cc target |
| `p16f887` | PIC14 (mid-range) | same ISA, different device data |
| `p18f4550` | PIC18 | PIC18 backend |

Enhanced mid-range parts (`pic16f193x` and friends) are out of scope:
epic-cc has no backend for that core, and adding one is a separate decision
(docs/31 D-1).
