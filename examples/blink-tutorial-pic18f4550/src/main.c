/*
 * Blink written the way a PIC tutorial writes it: no HAL, no framework,
 * `#pragma config` and the `__delay_ms` macro under a real `<xc.h>`. This
 * is the source a hobbyist copies from a forum answer, unchanged on the
 * epic-cc path (docs/46 D-3).
 */

#include <xc.h>

#define _XTAL_FREQ 20000000

#pragma config FOSC = HS, WDT = OFF, LVP = OFF

void main(void)
{
    TRISB = 0x00u;

    for (;;) {
        LATB ^= 0x01u;
        __delay_ms(500);
    }
}
