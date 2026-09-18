#ifndef ROCK_STATE_H
#define ROCK_STATE_H
#include <stdint.h>

/* Descriptive names only; the original type and field meanings are unknown.
 * state points at an 18-byte view beginning at PS1 address 0x800c3560.
 */
void RockState_Init(volatile uint8_t state[18], uint32_t argument);
#endif
