/*
 * Bare blink for the PIC18F4550, xc8 toolchain: the PIC18 backend
 * counterpart to blink-p18f4550. Config words are XC8's own #pragma
 * config, not EPIC_CONFIG (docs/getting-started.md#xc8). PIC18 reads
 * back PORT (the pin state) rather than the output latch, so LAT is the
 * SFR to toggle, not PORT.
 */

#include <xc.h>
#include <stdint.h>

#pragma config PLLDIV = 5
#pragma config CPUDIV = OSC1_PLL2
#pragma config USBDIV = 1
#pragma config FOSC = HSPLL_HS
#pragma config FCMEN = OFF
#pragma config IESO = OFF
#pragma config PWRT = OFF
#pragma config BOR = OFF
#pragma config VREGEN = OFF
#pragma config WDT = OFF
#pragma config MCLRE = ON
#pragma config LPT1OSC = OFF
#pragma config PBADEN = OFF
#pragma config STVREN = ON
#pragma config LVP = OFF
#pragma config XINST = OFF
#pragma config CP0 = OFF

void main(void)
{
    TRISB = 0x00u;

    for (;;) {
        LATB ^= 0x01u;
        for (volatile uint32_t i = 0u; i < 20000u; i++) {
        }
    }
}
