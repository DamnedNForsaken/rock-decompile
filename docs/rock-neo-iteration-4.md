# Entry 0x800155a4 and counter reconstruction

## Control flow recovered

The replacement entry at `0x800155a4` clears a word at `0x800c1b10`, then uses
its signed first byte to select a handler from the table at `0x80082114`.
Each pass calls the handler, `0x80031aa4`, the counter at `0x80016bc0`, and
`0x80016bf4`, then sleeps for one scheduler tick. No dispatch bounds check is
present. Eleven function pointers are recorded as an observed table prefix,
not a proven full table size.

The initial handler `0x80015634` clears several fields, initializes subsystems,
then writes phase 1 and subphase 0. Handler `0x80015734` handles that subphase,
performs additional calls, copies some fields, and writes phase 2/subphase 1
while clearing bit zero at state+0x82. These are evidence-backed state labels;
their player-visible meaning remains unresolved.

An earlier unknown global now has more context: the first handler writes zero
to `0x800c356c`, one of the bytes touched by `RockState_Init`. The second handler
uses a larger view beginning eight bytes earlier at `0x800c3558`. This proves
shared state access but still does not identify its subsystem or full layout.

## Counter behavior and compiled checks

`RockCounter_Tick` in `src/rock_counter.c` reconstructs the leaf at
`0x80016bc0..0x80016bf4`. It increments the 32-bit word at `0x800c1b1c`, then
clamps the unsigned result to 10799999. The addition wraps first, so an input
of `0xffffffff` becomes zero. A simple saturating-add implementation would be
wrong on that boundary.

The portable API accepts a pointer instead of addressing the original global.
It models final RAM contents, not intermediate stores or concurrent observers.
The counter is updated once per pass through this thread loop, but the unit
and wall-clock rate are not established; it is not yet named a play-time timer.

Compiled /Od and /O2 builds each pass 10007 counter comparisons against a
restricted execution of the original instructions, including load and branch
delay slots. Inputs include seven boundary values and 10000 seeded random values.
The previous compiled checks also pass, for 808492 comparisons across both builds.

## Numeric IDs and loading investigation

Calls to `0x8001da8c` receive values such as 510, 906, 967, and 1319. Its opening
instructions set a bit at `0x800be378 + (id >> 3)`, with mask `0x80 >> (id & 7)`.
This is concrete bitset behavior. It does not establish that these are asset
IDs, file indices, or loading requests. No filenames or archive mappings were
proven in this iteration.

## Reproduce and continue

```powershell
python tools/thread_handoff_iteration.py extracted/disc/ROCK_NEO.EXE
python tools/verify_compiled.py extracted/disc/ROCK_NEO.EXE
```

The first command now also emits this entry's listings, initial handlers,
counter, and numeric-ID bitset prefix. The second rebuilds all four recovered
behaviors and tests actual host C. Full emulator execution and PS1 compiler
matching remain untested.

Next targets are phase 2 at `0x80015840`, the consumers of the bitset at
`0x800be378`, and emulator observations tying these states to visible behavior.
