/*
 * Bare blink for the PIC16F877A: no HAL, no framework. The compiler path
 * alone is the point, so this is the smallest program that proves `pio run`
 * turns C into a flashable HEX with no Microchip download.
 *
 * Config words are spelled with EPIC_CONFIG (docs/31 D-4), not #pragma
 * config. Everything unstated takes the device's documented default.
 */

#include <epic-cc.h>

EPIC_CONFIG("osc=hs, xtal_hz=4000000, wdt=off, lvp=off");

void main(void)
{
    for (;;) {
        __epic_nop();
    }
}
