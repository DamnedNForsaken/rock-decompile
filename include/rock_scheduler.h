#ifndef ROCK_SCHEDULER_H
#define ROCK_SCHEDULER_H
#include <stdint.h>

/* Models only the eligibility block, not the BIOS context switch. */
int RockScheduler_ShouldResume(uint16_t status, uint16_t *ticks);

/* Host-facing model of globals at GP+0x8f4 and GP+0x174. */
typedef struct RockReplacementRequest {
    volatile uint32_t entry;
    volatile uint32_t pending;
} RockReplacementRequest;
typedef void (*RockChangeThread)(uint32_t handle);
void RockThread_RequestReplacement(RockReplacementRequest *request,
                                   uint32_t entry, RockChangeThread change_thread);
#endif
