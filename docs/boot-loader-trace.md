# Boot loader trace

This trace covers the exact path from the PS-X EXE entry point to the handoff to
`ROCK_NEO.EXE`. Addresses refer to the North American `SLUS_006.03` executable
identified in `config/slus_00603.json`.

## Control flow

1. `PsxEntry` at `0x8001262c` clears `0x80059b40..0x8005da40`, establishes the
   runtime stack/GP, invokes the A0:39 `InitHeap` BIOS wrapper, and calls
   `BootMain` at `0x800107e8`.
2. `BootMain` initializes the boot program and enters its frame loop at
   `0x80010818`. Each frame calls `BootMode_Dispatch` at `0x800125e8`.
3. `BootMode_Dispatch` reads `g_BootMode` at `0x80059c50` and indirectly calls
   one of four functions from `BootMode_HandlerTable` at `0x8001df94`:

   | Index | Handler |
   | ---: | ---: |
   | 0 | `0x80012094` |
   | 1 | `0x800121d8` |
   | 2 | `0x80012264` |
   | 3 | `0x80012300` (`BootMode3_Update`) |

4. `BootMode3_Update` reads `g_BootMode3Phase` at `0x80059c51`. Phase 2 branches
   to `BootMode3_LaunchMainExecutable` at `0x800124fc`.
5. The launch block performs three still-unnamed cleanup calls, invokes the A0:71
   `_96_init` BIOS wrapper, and then calls A0:51 `LoadExec` with:

   ```text
   a0 = 0x80059b24 -> "cdrom:\ROCK_NEO.EXE;1"
   a1 = 0x801fff00
   a2 = 0
   call 0x8001a264 -> A0:51 LoadExec
   ```

The A0 wrapper is structurally unambiguous:

```text
8001a264: addiu t2, zero, 0x00a0
8001a268: jr    t2
8001a26c: addiu t1, zero, 0x0051   ; delay slot
```

The BIOS receives function number `0x51` in `t1`; this is `LoadExec`. The main
executable header then directs the BIOS to load 823296 bytes at `0x80010000` and
begin execution at `0x80068000`. This overwrites the boot executable's load
region, so the handoff is intentionally one-way during normal operation.

The same structural scan identifies 26 standard BIOS thunks in the boot program,
including heap initialization, memory/string helpers, GPU access, events, pad
input, interrupt-chain management, cache flushing, and CD initialization. Their
addresses and API names are recorded in `config/slus_00603_symbols.csv`; the
scanner can regenerate the evidence from the executable at any time.

## Current unknowns

The calls at `0x80016b28`, `0x8001b6e8`, and `0x8001a4ac` immediately before
`_96_init` are not yet named. Their position strongly suggests subsystem
shutdown or synchronization, but names will wait for call-graph and side-effect
analysis. This distinction is recorded in the symbol map rather than hidden by
premature labels.
