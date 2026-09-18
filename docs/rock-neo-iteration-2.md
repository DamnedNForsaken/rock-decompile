# Cooperative thread scheduler

The per-frame call at `0x80011e70` enters `0x80012c80`, now named
`RockScheduler_Tick`. It scans four records at `0x801f8100`, `0x801f8180`,
`0x801f8200`, and `0x801f8280`. Their stride is 128 bytes. The current-record
pointer is stored at `0x801f8300`; after the scan it points one past the table.

## Evidence and record layout

| Offset | Interpretation | Evidence |
| --- | --- | --- |
| 0x00 | 16-bit scheduler status | Compared at 0x80012cb8; written by create/sleep/exit |
| 0x02 | 16-bit countdown | Decremented at 0x80012cfc; sleep stores argument here |
| 0x08 | BIOS thread handle | OpenTh result; passed to ChangeTh and CloseTh |
| 0x10 | Initial stack value | OpenTh second argument |
| 0x44 | Initial GP value | OpenTh third argument |
| 0x70 | Context-helper flag | Controls calls around the context switch; exact meaning unresolved |

Three local thunks identify thread operations unambiguously: `0x8007ff10` is
B0:0e, `0x8007ff20` is B0:0f, and `0x8007ff30` is B0:10. These map to OpenTh,
CloseTh, and ChangeTh in the [BIOS reference](https://psx-spx.consoledev.net/kernelbios/).
They create, close, and explicitly switch threads. This supports the cooperative
scheduler interpretation, rather than relying on the appearance of a loop alone.

## Observed scheduling rule

| Status | Action on this scan |
| --- | --- |
| 1 | Decrement countdown modulo 65536; resume only if result is zero |
| 2, 4, 127 | Resume |
| Other values | Skip |

Before ChangeTh, the scheduler sets status to 127. A resumed thread can yield
through `RockThread_Sleep` (`0x80012e98`), which writes status 1 and its argument's
low 16 bits to the countdown, then calls ChangeTh with handle `0xff000000`.
`RockThread_Create` (`0x80012e10`) stores an OpenTh result and sets status 2.
`RockThread_Exit` (`0x80012ecc`) clears status, closes its handle, and switches
to `0xff000000`. That handle's role as the scheduler thread is a strong inference
from this call pattern, not an observed runtime trace.

A zero sleep count does not resume on the next tick: it wraps to 65535 and takes
65536 eligible scans to reach zero. Status 4 is runnable, but its higher-level
purpose remains unknown. The post-switch path can also close/recreate a thread
when the word at GP+0x174 is nonzero; its trigger is not yet traced.

## Reconstruction and verification

`src/rock_scheduler.c` extracts the eligibility decision into a portable helper.
This is a basic-block reconstruction, not an original standalone function and
not the full context-switching scheduler. A restricted executor runs the original
block with branch and load delay behavior and compares its exits and countdown
writes to the documented rule. All 65,536 countdown values for status 1 and all
65,535 other status values are checked: 131,071 passing cases.

```powershell
python tools/scheduler_iteration.py extracted/disc/ROCK_NEO.EXE
```

This regenerates ignored listings and a hash-bound report in
`build/scheduler_iteration/`. The compiled C has not been tested; neither this
check nor the earlier initializer check executes an emulator or validates BIOS
thread context switching.

## Initializer callers

The callers at `0x80068278`, `0x800682b0`, and `0x800684bc` pass selectors 0, 1,
and 2 respectively. They also modify bit 1 of flags in objects reached through
their input structures. That establishes selectable initialization behavior,
but does not prove whether the state belongs to a camera, UI, actor, or another
subsystem. `RockState_Init` retains its descriptive name.

Next: trace slot setup and the first thread entry `0x800131fc` (passed by main
to the create routine), and validate compiled C against the instruction models.
