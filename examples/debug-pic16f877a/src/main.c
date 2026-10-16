/*
 * Debug demo for the PIC16F877A: locals and globals a simulator session
 * can break on, step across, and print. Straight-line code with no calls:
 * one volatile local, one global, one bank-0 SFR write. It runs to the end
 * and sleeps, so `continue` finishes instead of spinning. On hardware the
 * PORTB write latches while pins stay inputs, direction setup is omitted
 * because bank-switched SFR setup misattributes the lines after it
 * (epic-cc#1316 tracks the row gaps).
 *
 * Config words are spelled with EPIC_CONFIG (docs/31 D-4), not #pragma
 * config. Everything unstated takes the device's documented default.
 */

#include <stdint.h>
#include <epic-cc.h>

EPIC_CONFIG("osc=hs, xtal_hz=4000000, wdt=off, lvp=off");

/* PORTB data register (DS39582B Table 4-10), bank 0, so no bank switch. */
#define PORTB (*(volatile uint8_t *)0x06u)

int g_a;

void main(void)
{
    volatile int tmp;

    tmp = 41;
    g_a = tmp + 1;
    PORTB = (uint8_t)g_a;
}
