# Flag setter reconstruction

## Scope of this pass

Iteration 4 left two static targets: phase 2 at `0x80015840`, and consumers of
the bitset at `0x800be378`. This pass reconstructs the **setter** whose opening
instructions were already listed as `0x8001da8c..0x8001dad0`. Phase 2 is only
listed as a prefix for the next executable-backed trace. No emulator session
was available in this environment, so on-screen meaning is still unresolved.

## Facts versus inferences

**Fact (from iteration 4 static listing):** calls such as 510, 906, 967, and 1319
reach `0x8001da8c`, which writes `flags[(id >> 3)] |= (0x80 >> (id & 7))` at base
`0x800be378`. Bits are most-significant-first, matching `RockFlags_Test`.

**Strong inference:** the listed range is a complete leaf that ORs one bit and
returns. That matches the existing query leaf sitting immediately before it.

**Guess / unproven:** these identifiers are asset IDs, file indices, or load
requests. No filename or archive mapping is established. Table capacity is
unknown; tests allocate storage, they do not measure the original table.

## Source

`RockFlags_Set` in `src/rock_flags.c` is a portable pointer API, not a global at
`0x800be378`. It does not clear other bits. Re-setting the same ID is a no-op
on the byte.

## Validation that ran here

```text
python -m unittest discover -s tests -v
```

Documented-model tests cover MSB-first masks, neighbor preservation for the four
observed IDs, and idempotence. When gcc is present, a shared-object smoke test
compares compiled `RockFlags_Set` / `RockFlags_Test` to that model.

Original-instruction matching is **not** claimed in this environment because
`ROCK_NEO.EXE` is intentionally absent from the repository. The new interpreter
`execute_flag_set` is wired into `tools/verify_compiled.py` for the local run:

```powershell
python tools/thread_handoff_iteration.py extracted/disc/ROCK_NEO.EXE
python tools/verify_compiled.py extracted/disc/ROCK_NEO.EXE
```

If the original setter uses an opcode the interpreter does not accept, that
command fails instead of silently disagreeing.

The handoff script now also writes `flag_set.asm.txt` and
`phase_15840_prefix.asm.txt`. The phase-2 file is a 0x1c0-byte prefix, not a
proven function bound.

## Next

1. Run the two commands above on the owned dump; keep or correct `execute_flag_set`
   against the real listing.
2. Trace `0x80015840` from that listing: writes to `Thread155a4_State`, further
   numeric IDs, and calls into known BIOS/file helpers.
3. Find other writers/readers of `0x800be378` before naming the table.
