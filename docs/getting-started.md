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

`pio run -t upload` drives a **TL866A or TL866II Plus** universal
programmer via [`minipro`](https://gitlab.com/DavidGriffith/minipro) (GPL,
fully independent of Microchip). TL866CS has no ICSP header and cannot be
used.

`minipro` has no Debian/Ubuntu package. Build it from source:

```bash
git clone https://gitlab.com/DavidGriffith/minipro.git
cd minipro && make && sudo make install
```

Then, with the programmer's ICSP header wired to the target (or the
target seated in a supported ZIF adapter):

```bash
pio run -t upload
```

If `minipro` is not on `PATH`, point the platform at it explicitly:

```bash
EPIC8_MINIPRO_PATH=/path/to/minipro pio run -t upload
```

**PICkit2, PICkit3 and "PICkit3.5" clones** (PKOB too) are driven by
[`pk2cmd`](https://github.com/jaka-fi/pk2cmd), a maintained fork of
Microchip's own tool. Read
[`docs/pk2cmd-LICENSE.md`](pk2cmd-LICENSE.md) before using it: unlike
`minipro`, this is Microchip's own licensed software, not MIT, fetched
here unmodified. Install it with:

```bash
scripts/install-pk2cmd.sh
```

which downloads a checksum-pinned release, extracts it (AppImages need
FUSE, which not every environment has, so the script extracts rather
than running the AppImage directly), and prints the `udev` rule you need
for USB access without root. Then select the protocol and upload:

```ini
[env:epic8]
platform = epic8
board = p16f877a
upload_protocol = pk2cmd
```

```bash
pio run -t upload
```

**PICkit3/PKOB-specific gotcha.** These need a one-time "scripting
firmware" update before any Linux tool can drive them at all; `pk2cmd`
does not support pushing that update itself. If yours doesn't have it
already, you need the Windows GUI once, first, to update the firmware.
PICkit2 has no such requirement.

If `pk2cmd` is not where the install script put it, point the platform
at it explicitly:

```bash
EPIC8_PK2CMD_PATH=/path/to/pk2cmd EPIC8_PK2CMD_DIR=/path/to/its/PK2DeviceFile.dat/dir pio run -t upload
```

The exact device-name mappings (`upload.minipro_device`,
`upload.pk2cmd_device` in each board's JSON) were confirmed directly
against the real tools (`minipro`'s documented `-p <name> -w <file>`
shape; `pk2cmd`'s device database was grepped directly for
`PIC16F877A`/`PIC16F887`/`PIC18F4550`) but not against real silicon,
since neither tool run here has hardware attached. If programming fails
with a device-not-recognized error, that mapping is the first thing to
check. The full history, including the original "not supported in v1"
call and why it changed, is in
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
