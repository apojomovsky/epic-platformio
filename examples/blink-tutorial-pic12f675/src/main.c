/*
 * Blink written the way a PIC12 tutorial writes it: no HAL, `#pragma
 * config` and `__delay_ms` under a real `<xc.h>`. The 12F675 has no
 * PORTB: its pins are GPIO with the direction in TRISIO, and the internal
 * oscillator fixes the clock at 4 MHz, so `_XTAL_FREQ` must say 4 MHz too.
 */

#include <xc.h>

#define _XTAL_FREQ 4000000

#pragma config FOSC = INTRCIO, WDTE = OFF

void main(void)
{
    TRISIO = 0x00u;

    for (;;) {
        GPIO ^= 0x01u;
        __delay_ms(500);
    }
}
