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
| `blink-xc8-p16f877a` | PIC16F877A | the xc8 toolchain path alone ([XC8](#xc8)) |
| `blink-xc8-p16f887` | PIC16F887 | xc8 on a new device on a supported core |
| `blink-xc8-p18f4550` | PIC18F4550 | xc8 on the PIC18 backend |
| `hal-tick-xc8-p16f877a` | PIC16F877A | epic-tick plus GPIO under xc8 |

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

## XC8

`board_build.toolchain = xc8` builds with MPLAB XC8 instead of epic-cc, on
any of the 3 boards above, with or without `framework = epichal`:

```ini
; platformio.ini
[env:epic8]
platform = epic8
board = p16f877a
board_build.toolchain = xc8
```

```c
// src/main.c
#include <xc.h>

#pragma config FOSC = HS
#pragma config WDTE = OFF
#pragma config PWRTE = ON
#pragma config BOREN = ON
#pragma config LVP = OFF
#pragma config CPD = OFF
#pragma config WRT = OFF
#pragma config CP = OFF

void main(void)
{
    TRISB = 0x00u;
    for (;;) {
        PORTB ^= 0x01u;
    }
}
```

Unlike epic-cc, config words are spelled the ordinary XC8 way
(`#pragma config`, from `<xc.h>`), not `EPIC_CONFIG`: the builder does not
translate between the two, so an xc8 project is a plain XC8 project as far
as its own source goes.

**Never vendored** (docs/platform-decisions.md): Microchip's EULA forbids
redistributing XC8, so `platform.json` carries no toolchain package for it,
the same posture as the upload tools below. Install it yourself (the free
tier is enough) from
<https://www.microchip.com/en-us/tools-resources/develop/mplab-xc-compilers>
and put its `bin/` on `PATH`, or point `EPIC8_XC8_PATH` at the `xc8-cc`
binary directly.

A device family whose headers aren't in XC8's own built-in set also needs
its Device Family Pack; see
[epic-hal's README](https://github.com/apojomovsky/epic-hal#readme) for how
to get one for the family your board uses. Point `EPIC8_XC8_DFP_DIR` at the
pack's own `xc8` subdirectory (not the pack's top-level directory), e.g.
`/opt/microchip/xc8/v4.00/pic/packs/Microchip.PIC16Fxxx_DFP/xc8`. Leaving it
unset restricts the build to whatever devices XC8 already supports without
one.

## Upload

`pio run -t upload` drives a **TL866A or TL866II Plus** universal
programmer via [`minipro`](https://gitlab.com/DavidGriffith/minipro) (GPL,
fully independent of Microchip) by default. TL866CS has no ICSP header and
cannot be used. It can also drive a **PICkit2 / PICkit3 / "PICkit3.5"**
clone via a `pk2cmd`-family tool (`pk2cmd-minus` / `PICKitminus`, the
maintained forks that auto-detect and drive both PICkit2 and PICkit3,
including the "PICkit3.5" clones sold on AliExpress, which speak the same
PICkit3 protocol). Select it with `UPLOAD_PROTOCOL=pk2cmd` (or set
`upload.protocol = pk2cmd` on the board).

`minipro` has no Debian/Ubuntu package. Build it from source:

```bash
git clone https://gitlab.com/DavidGriffith/minipro.git
cd minipro && make && sudo make install
```

`pk2cmd` has no Debian/Ubuntu package either. Build it from source (the
`pk2cmd-minus` fork builds on Linux with `make`):

```bash
git clone https://github.com/cjacker/pk2cmd-minus.git
cd pk2cmd-minus && make && sudo make install
```

Then, with the programmer's ICSP header wired to the target (or the
target seated in a supported ZIF adapter):

```bash
pio run -t upload                 # minipro (default)
UPLOAD_PROTOCOL=pk2cmd pio run -t upload   # pk2cmd-family tool
```

If the tool is not on `PATH`, point the platform at it explicitly:

```bash
EPIC8_MINIPRO_PATH=/path/to/minipro pio run -t upload
EPIC8_PK2CMD_PATH=/path/to/pk2cmd UPLOAD_PROTOCOL=pk2cmd pio run -t upload
```

**PICkit3 clone firmware caveat.** Some PICkit3 clones need a one-time
Windows-only firmware update ("scripting firmware") before any Linux tool
can drive them at all; a `pk2cmd`-family tool cannot push that update on
Linux. If `pk2cmd` reports the programmer as not found or not responding
on first use, run the vendor's Windows updater once on a Windows machine,
then the clone works under `pk2cmd` on Linux thereafter.

The exact device-name mapping (`upload.minipro_device` / `upload.pk2cmd_device`
in each board's JSON) is built from the tools' documented `-p <name>` /
`-P<name>` invocation shape and has not been confirmed against real
silicon; if `minipro -l` or `pk2cmd` reports a different spelling for your
device, that is the bug to file. The full history, including the rejected
`ipecmd` alternative and the license discussion, is in
[`docs/platform-decisions.md`](platform-decisions.md).

## Supported parts

Every board under [`boards/`](../boards) is generated (PIO-6,
`scripts/gen_boards.py`) from epic-cc's and epic-hal's own device
registries, one board per device, at whatever capability level that
device actually has: a board's `build.toolchains` lists which
`board_build.toolchain` values it accepts, and `build.framework_epichal_toolchains`
lists which of those also support `framework = epichal` (empty when
epic-hal doesn't cover the device at all). Picking a combination a board
doesn't support fails the build with a message naming what it does
support, rather than a silent wrong build.

Three shapes exist today:

- **epic-cc only** (most devices): epic-hal doesn't cover this part yet.
- **Both toolchains**: epic-cc and epic-hal both cover it; `framework =
  epichal` works under either, once the family has HAL content to build
  (some families are registered with zero HAL modules yet, or a module
  that needs a peripheral driver epic-cc's conformant slice doesn't
  carry, and fail loudly naming the gap rather than miscompiling).
- **xc8 only**: epic-hal covers it but epic-cc's device registry doesn't
  (yet), e.g. some `pic16f88x` siblings.

A scheduled `boards-refresh` workflow (PIO-7) regenerates this list
against the latest epic-cc/epic-hal releases and opens a pull request
when it changes; `scripts/gen_boards.py` (see its own `--help`) is also
runnable by hand against fresher local inputs.
