/*
 * Bare blink for the PIC16F887: no HAL, no framework. Same ISA as the
 * 877A on different device data, so this is the standing proof that a
 * new device on an already supported core is close to free (docs/31 D-1).
 */

#include <epic-cc.h>

EPIC_CONFIG("osc=hs, xtal_hz=4000000, wdt=off, lvp=off");

void main(void)
{
    for (;;) {
        __epic_nop();
    }
}
