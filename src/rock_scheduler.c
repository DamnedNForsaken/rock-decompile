#include "rock_scheduler.h"

/* Behavioral extraction of 0x80012cb8..0x80012d18.
 * This block is inside the scheduler, not an original standalone function.
 * true means branch to 0x80012d18; false means skip to 0x80012de0.
 */
int RockScheduler_ShouldResume(uint16_t status, uint16_t *ticks)
{
    if (status == 1) {
        *ticks = (uint16_t)(*ticks - 1u);
        return *ticks == 0;
    }
    return status == 2 || status == 4 || status == 127;
}

/* 0x80012f78: publish a replacement then yield to the scheduler.
 * The struct adapts two separate PS1 globals; it is not their physical layout.
 * BIOS ChangeTh and the scheduler's close/create logic are supplied externally.
 */
void RockThread_RequestReplacement(RockReplacementRequest *request,
                                   uint32_t entry, RockChangeThread change_thread)
{
    request->entry = entry;
    request->pending = 1;
    change_thread(UINT32_C(0xff000000));
}
