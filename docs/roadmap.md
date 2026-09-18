# Reverse-engineering roadmap

## Stage 0 — reproducible inputs (current)

- Fingerprint the owned disc dump.
- Parse the data track without altering the original.
- Produce a deterministic filesystem manifest.
- Identify and inspect the boot PS-X EXE.

## Stage 1 — executable map

- Record the PS-X EXE load address, entry point, GP, and memory extent.
- Import the executable into a MIPS R3000 disassembler/decompiler.
- Identify SDK/library functions, startup code, overlays, and archive loaders.
- Create a symbol map with stable names and provenance notes.

## Stage 2 — first matching module

- Establish a PS1 cross-toolchain and linker layout.
- Select a small leaf subsystem with clear inputs and outputs.
- Reconstruct it in C, compare generated MIPS code, and iterate to a match.
- Add automated byte/object comparison to the build.

## Stage 3 — subsystem recovery

Work outward through input, memory/card I/O, rendering, audio, collision, entity
logic, scripting, and level/archive formats. Keep binary matching separate from
behavioral ports so that each claim remains testable.

## Stage 4 — source-based game

Replace the recovered executable and data pipeline incrementally. A portable
engine or enhancements can branch from the documented reconstruction after the
original behavior and formats are sufficiently understood.

