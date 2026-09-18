#include "rock_counter.h"

/* 0x80016bc0..0x80016bf4. Original global: 0x800c1b1c.
 * Preserve unsigned overflow before the comparison; UINT32_MAX becomes zero.
 * Meaning and rate of the counter are not yet established.
 */
void RockCounter_Tick(uint32_t *counter)
{
    uint32_t next = *counter + UINT32_C(1);
    *counter = next > UINT32_C(10799999) ? UINT32_C(10799999) : next;
}
