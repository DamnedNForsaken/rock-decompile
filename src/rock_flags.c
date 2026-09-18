#include "rock_flags.h"

/* Complete leaf 0x8001da58..0x8001da8c. Original base: 0x800be378.
 * IDs select bits most-significant first. Actual table capacity is unresolved.
 */
int RockFlags_Test(const uint8_t *flags, uint32_t id)
{
    return (flags[id >> 3] & (UINT32_C(0x80) >> (id & 7u))) != 0;
}
