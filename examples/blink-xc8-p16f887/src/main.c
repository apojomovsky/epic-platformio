/*
 * Bare blink for the PIC16F887, xc8 toolchain: same ISA as the 877A on
 * different device data, the xc8-path counterpart to blink-p16f887.
 * Config words are XC8's own #pragma config, not EPIC_CONFIG
 * (docs/getting-started.md#xc8). The LED is driven by writing the
 * PORTB/TRISB SFRs directly.
 */

#include <xc.h>
#include <stdint.h>

#pragma config FOSC = HS
#pragma config WDTE = OFF
#pragma config PWRTE = ON
#pragma config MCLRE = ON
#pragma config CP = OFF
#pragma config CPD = OFF
#pragma config BOREN = ON
#pragma config IESO = OFF
#pragma config FCMEN = OFF
#pragma config LVP = OFF

void main(void)
{
    TRISB = 0x00u;

    for (;;) {
        PORTB ^= 0x01u;
        for (volatile uint32_t i = 0u; i < 20000u; i++) {
        }
    }
}
