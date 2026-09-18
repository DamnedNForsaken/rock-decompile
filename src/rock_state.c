#include "rock_state.h"

/* Behavioral reconstruction of ROCK_NEO.EXE 0x800680bc..0x80068120.
 * Byte representation makes PS1 little-endian layout explicit on a host.
 * Offset 6..9 is deliberately untouched. Not compiler/byte matched.
 * Original SH writes are split into byte writes in this portable model;
 * equivalence assumes ordinary RAM with no concurrent observer.
 */
void RockState_Init(volatile uint8_t state[18], uint32_t argument)
{
    state[12] = 255;
    state[14] = 24;
    state[15] = (uint8_t)argument;
    state[0] = state[1] = 0;
    state[2] = state[3] = 0;
    state[4] = state[5] = 0;
    state[10] = state[11] = 0;
    state[13] = 0;
    state[17] = 255;
    state[16] = 255;
}
