#ifndef ROCK_FLAGS_H
#define ROCK_FLAGS_H
#include <stdint.h>
/* Caller must provide storage through flags[id >> 3]. No original bounds check. */
int RockFlags_Test(const uint8_t *flags, uint32_t id);
#endif
