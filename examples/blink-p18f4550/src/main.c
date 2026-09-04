/*
 * Bare blink for the PIC18F4550: no HAL, no framework. The PIC18 clock
 * tree is nastier than PIC14's, so the config words name the oscillator,
 * the PLL and the CPU divider explicitly (docs/31 D-4).
 */

#include <epic-cc.h>

EPIC_CONFIG("osc=hs, xtal_hz=4000000, cpudiv=div1, plldiv=noprescale, usbdiv=off, wdt=off, lvp=off");

void main(void)
{
    for (;;) {
        __epic_nop();
    }
}
