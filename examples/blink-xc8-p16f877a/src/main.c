/*
 * Bare blink for the PIC16F877A, xc8 toolchain: no HAL, no framework. The
 * xc8 compiler path alone is the point, the same role blink-p16f877a
 * plays for epic-cc. Config words are XC8's own #pragma config, not
 * EPIC_CONFIG (docs/getting-started.md#xc8), since a project under
 * board_build.toolchain = xc8 is a plain XC8 project. The LED is driven
 * by writing the PORTB/TRISB SFRs directly.
 */

#include <xc.h>
#include <stdint.h>

#pragma config FOSC = HS
#pragma config WDTE = OFF
#pragma config PWRTE = ON
#pragma config BOREN = ON
#pragma config LVP = OFF
#pragma config CPD = OFF
#pragma config WRT = OFF
#pragma config CP = OFF

void main(void)
{
    TRISB = 0x00u;                 /* RB0..RB7 outputs */

    for (;;) {
        PORTB ^= 0x01u;             /* toggle RB0 */
        for (volatile uint32_t i = 0u; i < 20000u; i++) {
        }
    }
}
