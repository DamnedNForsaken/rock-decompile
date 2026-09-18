# Research log

## 2026-09-18 — project bootstrap

- Fingerprinted all three CloneCD source files with SHA-256.
- Parsed the descriptor: data track LBA 0, audio track LBA 207295.
- Confirmed volume `MEGAMAN_LEGENDS` and boot serial `SLUS_006.03`.
- Implemented and validated a local Mode 2 ISO9660 inventory/extraction tool.
- Enumerated 247 files in four directories (`CDDATA`, `DAT`, `STR`, `XA`).
- Confirmed all extracted logical file sizes against their directory records.
- Parsed and fingerprinted both PS-X EXE headers.
- Located `cdrom:\\ROCK_NEO.EXE;1` in the boot executable.

Next: load both executable images at their declared addresses in a MIPS little-
endian disassembler, identify the SDK signatures, and trace the `ROCK_NEO.EXE`
launch path before naming any reconstructed functions.

## 2026-09-18 — boot-to-main executable trace

- Added a dependency-free R3000 instruction decoder and address-reference tool.
- Located the main executable path at runtime address `0x80059b24`.
- Recovered the entry → main loop → mode dispatcher → loader control flow.
- Identified the four-entry boot-mode handler table at `0x8001df94`.
- Bounded the mode-3 function at `0x80012300..0x800125e8`.
- Confirmed standard BIOS thunks by their A0-vector instruction sequence:
  `InitHeap` (A0:39), `LoadExec` (A0:51), and `_96_init` (A0:71).
- Confirmed `LoadExec("cdrom:\\ROCK_NEO.EXE;1", 0x801fff00, 0)` at `0x8001252c`.
- Added the first versioned symbol map in `config/slus_00603_symbols.csv`.

## Main executable iteration

- Traced ROCK_NEO startup, zero-fill, runtime GP/stack, heap arguments, and main loop.
- Added `config/rock_neo_symbols.csv` with confidence and evidence per symbol.
- Generated 45 BIOS wrapper candidates and a clearly labeled linear call scan.
- Reconstructed the small state initializer at `0x800680bc` in portable C.
- Checked its original MIPS RAM effects on 768 cases against the documented model.
- Added reproducible listings and reports through `tools/rock_iteration.py`.
- Hardened executable reads against truncated payloads, unaligned words, and empty searches.
- C compilation and emulator execution remain future verification steps.

## Scheduler iteration

- Identified a four-slot cooperative thread scheduler at 0x80012c80.
- Mapped create, sleep, exit, BIOS thread thunks, and partial slot fields.
- Added a C extraction of the scheduler eligibility rule.
- Checked original instruction decisions/countdown writes across 131071 cases.
- Confirmed zero countdown wraps rather than immediately resuming.
- Traced three initializer callers; subsystem identity remains unresolved.
- Reproduction and limitations: `docs/rock-neo-iteration-2.md`.

## Initial-thread handoff iteration

- Traced slot-zero entry 0x800131fc and its initial handler-table prefix.
- Connected request producer 0x80012f78 to the scheduler close/recreate path.
- Recovered handoffs to 0x80013420 and subsequently 0x800155a4.
- Added the request routine's C behavior model and 260 passing event checks.
- Recorded signed dispatch indices and unresolved table extents explicitly.

## Compiled C verification

- Located an existing Visual Studio 2026 installation outside PATH.
- Added reproducible C11 x64 DLL builds at /Od and /O2 with warnings as errors.
- Compared actual compiled functions to original instruction models: 768
  initializer, 393211 eligibility, and 260 replacement cases per configuration.
- Both configurations passed without modifying the reconstructed C.
- Captured compiler log and hash-bound verification report under build/host.
- Previous reports' uncompiled-C limitation is superseded by
  `docs/compiled-validation.md`; emulator/PS1 matching remain outstanding.

## Entry 0x800155a4 iteration

- Recovered its signed-byte dispatcher and first phase transitions.
- Connected accesses to the previously reconstructed state initializer's memory.
- Reconstructed counter at 0x80016bc0, preserving wrap-before-clamp semantics.
- Both compiled configurations passed 10007 new cases each, plus prior checks.
- Traced numeric-ID calls to a bitset write; asset-loading interpretation unproven.
- See `docs/rock-neo-iteration-4.md` for evidence and reproduction.
- Details and possible next steps: `docs/rock-neo-iteration-3.md`.

## Flag-set iteration

- Reconstructed `RockFlags_Set` from the documented OR/mask rule at `0x8001da8c`.
- Added a restricted original-instruction interpreter for that listing range.
- Host gcc smoke tests match the documented model; MSVC differential checks
  against original words remain a local `verify_compiled.py` step.
- Listed a prefix of phase 2 at `0x80015840` for the next static pass. No
  emulator or on-screen identity is claimed.
- See `docs/rock-neo-iteration-5.md`.
