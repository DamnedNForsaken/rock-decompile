# Reconstructed source

`rock_state.c` is the first behavioral reconstruction: a bounded initializer
from `ROCK_NEO.EXE`. Its addresses, verification, and remaining limitations are
documented in `docs/rock-neo-iteration-1.md`. It is not yet compiler matched or
linked into an executable.

`rock_scheduler.c` extracts the thread scheduler's eligibility block. The
full scheduler and BIOS context switching have not yet been reconstructed.

All three exported C behaviors now pass compiled host differential checks in
unoptimized and optimized builds. See `docs/compiled-validation.md` for the
reproduction command and limits. PS1 compiler matching remains outstanding.

`rock_counter.c` adds a fourth compiled behavior: unsigned increment followed by
a cap, preserving wraparound. Its precise game meaning remains unresolved.

`rock_flags.c` now also reconstructs the setter at `0x8001da8c`. Host gcc smoke
tests cover its documented bit math. Original-instruction matching still needs
the local `ROCK_NEO.EXE` run of `tools/verify_compiled.py`.
