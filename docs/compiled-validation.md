# Compiled C validation

The three recovered C behaviors now compile and pass differential checks against
the original instruction models. Visual Studio 2026 Community was already
installed under `C:\\Program Files\\Microsoft Visual Studio\\18\\Community`; its
compiler was absent from PATH in the earlier investigation. No installation was
needed.

## Run

Use 64-bit Python 3.11+ on Windows:

```powershell
python tools/verify_compiled.py extracted/disc/ROCK_NEO.EXE
```

The script initializes the x64 MSVC environment, builds both C sources into DLLs
with `/Od` and `/O2`, and calls the exported functions through Python ctypes.
Both configurations use C11 and `/W4 /WX` (warnings treated as errors).
To use another Visual Studio installation, set `ROCK_VCVARS` to its
`VC\\Auxiliary\\Build\\vcvars64.bat` before running the script.

Compiler diagnostics/version go to `build/host/build.log`. Results, input image
hash, source/tool hashes, and DLL hashes go to `build/host/verification.json`.
Outputs stay under the ignored `build/` directory. Each run rebuilds the DLLs.

## Results per configuration

| Compiled function | Cases | Observations compared |
| --- | ---: | --- |
| RockState_Init | 768 | All 18 state bytes plus 32 surrounding sentinel bytes |
| RockScheduler_ShouldResume | 393211 | Exact boolean return and updated 16-bit countdown |
| RockThread_RequestReplacement | 260 | Callback count, handle, state seen during callback, final request state |

Both configurations passed all cases: 788478 comparisons total. The scheduler
checks every 16-bit countdown for status 1, and every other 16-bit status at five
countdown values (0, 1, 2, 32768, 65535). This is not exhaustive over all 2^32
status/countdown pairs. The initializer covers every argument byte with three
upper-bit patterns and randomized starting memory. Replacement checks include
observed entries, boundary values, and seeded random addresses.

The C sources needed no changes to pass. This closes the compiled-behavior gap
recorded in the previous three iteration reports.

Subsequently, `RockCounter_Tick` was added with 10007 passing cases per build.
The current runner tests four behaviors and performs 808492 total comparisons.
See `rock-neo-iteration-4.md` for its scope and overflow edge case.

`RockFlags_Set` is exported next to `RockFlags_Test`. Query cases are unchanged.
Set cases compare compiled stores to `execute_flag_set` over observed IDs plus
256 random identifiers. Run `verify_compiled.py` locally against `ROCK_NEO.EXE`
to add those original-instruction comparisons.

## Limits

The reference is our restricted MIPS instruction execution, not an independently
validated full emulator. This tests host x64 behavior, not matching PS1 machine
code, rendering, or a playable game. The replacement callback confirms the
published values at yield time but does not observe the order of individual
stores. Real BIOS context switches and concurrent access are not exercised.
The initializer's split byte stores retain the previously documented ordinary-
RAM assumption.

Next practical step: trace `0x800155a4` using the now-testable C project, or add
emulator observations as an independent check of the startup handoff.
