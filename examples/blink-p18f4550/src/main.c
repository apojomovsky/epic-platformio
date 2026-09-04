/*
 * Bare blink for the PIC18F4550: no HAL, no framework. The PIC18 clock
 * tree is nastier than PIC14's, so the config words name the oscillator,
 * the PLL and the CPU divider explicitly (docs/31 D-4). The LED is driven
 * through the LATB latch, which avoids the read-modify-write hazard of
 * toggling PORTB directly.
 */

#include <stdint.h>
#include <epic-cc.h>

EPIC_CONFIG("osc=hs, xtal_hz=4000000, cpudiv=div1, plldiv=noprescale, usbdiv=off, wdt=off, lvp=off");

/* SFR addresses (DS39632D Tables 2-1..2-3): TRISB is the direction
 * register, LATB the output latch. */
#define TRISB (*(volatile uint8_t *)0xF93u)
#define LATB  (*(volatile uint8_t *)0xF8Au)

void main(void)
{
    TRISB = 0x00u;                 /* RB0..RB7 outputs */

    for (;;) {
        LATB ^= 0x01u;             /* toggle RB0 */
        /* Approximate delay: the instruction-cycle count depends on
         * codegen, so the period is not a timing contract, just long
         * enough to see the LED. */
        for (volatile uint32_t i = 0u; i < 20000u; i++) {
        }
    }
}
