# Initial thread and entry replacement

## Reproduce

```powershell
python tools/thread_handoff_iteration.py extracted/disc/ROCK_NEO.EXE
python -m unittest discover -s tests -v
```

The report and seven assembly listings are generated under
`build/thread_handoff_iteration/`, after verifying the executable SHA-256.

## Static control-flow findings

Main creates slot 0 with entry `0x800131fc`. That entry clears the bytes at
`0x80098b1c` and `0x80098b1d`, then repeatedly uses the signed first byte to
index a pointer table at `0x80080894`. Each handler receives the state address.
After the handler returns, the thread calls the recovered sleep routine with 1.

The observed table prefix contains `0x8001326c`, `0x800133d8`, and `0x80013418`.
Full table length is not established. No bounds check is present at the dispatch.

The first handler initializes several objects and globals, then increments the
state byte. On the next dispatch, the second handler clears three words at
`0x80098aa8..0x80098ab3`, and calls `0x80012f78` with `0x80013420`.

That routine publishes a thread replacement request:

1. Store the new entry at `GP+0x8f4` (`0x80098158`).
2. Store 1 at `GP+0x174` (`0x800979d8`).
3. Yield with `ChangeTh(0xff000000)`; the argument is set in the call delay slot.

The scheduler checks the pending flag after the selected thread yields. At
`0x80012d98` it clears the flag, enters a critical section, closes the current
slot's BIOS thread handle, creates a new thread with the requested entry and
the slot's saved stack/GP, stores the new handle, and exits the critical section.
It then advances to the next slot. On the ordinary path, this slot still has
status 127 from dispatch and is eligible on the next scheduler scan.

This resolves the replacement trigger left open in iteration 2. It is static
evidence of replacing a thread's entry/context, not loading a new executable.

## Following the replacement

Entry `0x80013420` performs setup and dispatches using the signed byte at
`0x80098aa8`, with table base `0x80080950`. It calls `0x80031aa4` after the handler,
then sleeps for one tick. Seven plausible pointers are recorded as a table
prefix; their full meaning and reachable indices remain unresolved.

Its index-zero handler at `0x80013578` toggles byte 3 of the state, sets several
globals, and requests another replacement with entry `0x800155a4`. Because the
previous phase cleared the state words, index zero is the initial selection
absent intervening writes. This is the next useful trace target. No claim about
title-screen or gameplay identity is made without asset or runtime evidence.

## Source and validation

`RockThread_RequestReplacement` in `src/rock_scheduler.c` models the publication
and yield sequence. The host-facing struct represents two separate PS1 globals;
it is not their original memory layout. The callback represents ChangeTh, not
an implementation of BIOS switching. Names are descriptive, not original symbols.

A restricted executor runs the original request instructions through the call
delay slot. Across 260 entry values, it checks both global writes in order and
the yielded handle. Tests include the two observed entry addresses, zero, all
bits set, and seeded random values. This checks the instruction/event model;
the C has not been compiled, and no runtime thread replacement was emulated.
All 10 existing tests also pass.

The address `0x80098158` now has two symbol descriptions: the startup zero-fill
boundary and the replacement-entry global. This is an intentional alias.

## Possible next steps

1. Establish a C compiler and run differential tests of compiled reconstructions
   against the instruction models. This closes the repeated validation gap.
2. Follow entry `0x800155a4` and its handlers to find asset loads and the next
   concrete application state.
3. Set up emulator breakpoints at the scheduler and replacement request to verify
   the actual startup sequence and identify what appears on screen.
