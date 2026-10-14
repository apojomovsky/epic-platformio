/*
 * HAL integration proof: tick (the 1 ms timebase) plus the GPIO
 * peripheral, toggling an LED on a 500 ms period. This is the real
 * integration test, the compiler path plus the epic-hal framework in one
 * build. `framework = epichal` and `-DEPIC_HAL_MODULES=tick` select the
 * framework and the module; the builder wires in the family HAL and the
 * module sources (docs/31 D-7).
 *
 * The loop blocks in epic_tick_delay_ms instead of polling the tick: one
 * toggle per period, and on the host sim the delay pumps the harness so
 * simulated time advances.
 */

#include <stdint.h>

#include "epic_tick.h"
#include "peripherals/hal_gpio.h"

/* XC8 spells its config words as #pragma config. The oscillator and the
 * watchdog are named here: left unset, the chip runs on its RC default
 * with the watchdog on and resets every timeout. */
#pragma config FOSC = HS
#pragma config WDTE = OFF
#pragma config PWRTE = ON
#pragma config BOREN = ON
#pragma config LVP = OFF
#pragma config CPD = OFF
#pragma config WRT = OFF
#pragma config CP = OFF

#ifndef FOSC_HZ
#define FOSC_HZ 4000000UL
#endif

#define BLINK_MS 500u

void main(void)
{
    EPIC_GPIO_Init(GPIOB, GPIO_PIN_0, GPIO_MODE_OUTPUT);
    epic_tick_init(FOSC_HZ);

    for (;;) {
        EPIC_GPIO_TogglePin(GPIOB, GPIO_PIN_0);
        epic_tick_delay_ms(BLINK_MS);
    }
}
