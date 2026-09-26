/*
 * Bare blink for the PIC16F877A: no HAL, no framework. The compiler path
 * alone is the point, so this is the smallest program that proves `pio run`
 * turns C into a flashable HEX with no Microchip download. The LED is
 * driven by writing the PORTB/TRISB SFRs directly, the same registers the
 * HAL's GPIO driver wraps.
 *
 * Config words are spelled with EPIC_CONFIG (docs/31 D-4), not #pragma
 * config. Everything unstated takes the device's documented default.
 */

#include <stdint.h>
#include <epic-cc.h>

EPIC_CONFIG("osc=hs, xtal_hz=4000000, wdt=off, lvp=off");

/* SFR addresses (DS39582B Tables 4-2..4-10): TRISB is the Bank-1
 * direction register, PORTB the Bank-0 port. The compiler's banking pass
 * inserts the BANKSELs. */
#define TRISB (*(volatile uint8_t *)0x86u)
#define PORTB (*(volatile uint8_t *)0x06u)

void main(void)
{
    TRISB = 0x00u;                 /* RB0..RB7 outputs */

    for (;;) {
        PORTB ^= 0x01u;            /* toggle RB0 */
        /* Approximate delay: the instruction-cycle count depends on
         * codegen, so the period is not a timing contract, just long
         * enough to see the LED. */
        for (volatile uint32_t i = 0u; i < 20000u; i++) {
        }
    }
}
