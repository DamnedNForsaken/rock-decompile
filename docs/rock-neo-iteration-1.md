# ROCK_NEO: startup and first C reconstruction

## Reproduce

From the project root, with Python 3.11+:

```powershell
python tools/rock_iteration.py extracted/disc/ROCK_NEO.EXE
python -m unittest discover -s tests -v
```

The script checks the complete executable SHA-256 before generating local
listings, a call-candidate CSV, and `build/rock_iteration/report.json`.
These reports are derived from the owned image and stay in ignored output.

## Startup findings

| Item | Evidence |
| --- | --- |
| Entry | `0x80068000` from PS-X EXE header |
| Zero-fill interval | `[0x80098158, 0x800c5688)` from loop at `0x80068010` |
| Runtime stack | Startup reads `0x00200000` at `0x800680b0` and sets SP to `0x80200000` |
| Runtime GP | `0x80097864` at `0x80068080..84` |
| Heap | A0:39 wrapper `0x8007fe70`, called at `0x8006808c` |
| Heap arguments | Address `0x800c568c`, size `0x00132978`, directly following instruction arithmetic |
| Main | `0x80011c90`, called at `0x800680a0` |
| Frame loop | `0x80011ce8`, back edge `0x80011ee0` |

Startup replaces the stack selected by the boot loader. The zero-fill range is
established from code even though the EXE header's BSS fields are zero. It also
overlaps part of the loaded payload; zero-fill and loaded-image ranges should
not be treated as disjoint sections without further analysis.

The main routine calls setup code, then repeats synchronization, buffer selection,
and update calls. The report records all 26 direct call sites within its bounded
body. Detailed subsystem names remain unresolved. This is static analysis;
execution has not been observed in an emulator.

The full payload scan finds 3,356 JAL-shaped words targeting 897 distinct in-image
addresses. These are **candidates**, not a proven function count: the payload
contains data as well as instructions. There are also 45 standard BIOS wrapper
patterns; 22 have names in the existing mapping, and the rest retain numeric IDs.
BIOS ID names use the [PSX-SPX kernel reference](https://psx-spx.consoledev.net/kernelbios/).
No specific PSY-Q release or original compiler has been established.

## First reconstructed function

`src/rock_state.c` models `0x800680bc..0x80068120` (exclusive end). It initializes
an 18-byte view at `0x800c3560`. The object's full size and field meanings are
unknown; the current descriptive name is `RockState_Init`.

| Offset | Final bytes |
| --- | --- |
| 0..5 | zero |
| 6..9 | unchanged |
| 10..11 | zero |
| 12 | 255 |
| 13 | zero |
| 14 | 24 |
| 15 | low byte of first argument |
| 16..17 | 255 |

A restricted interpreter executes the original 25 instructions, including the
return delay slot, and checks this postcondition on 768 cases. These cover every
argument byte, three upper-bit patterns, and deterministic randomized initial
memory so untouched fields are checked too. Unsupported instructions or stores
outside the view fail verification.

This validates the original instruction behavior against the documented model.
The C is a manually reviewed translation of that model; no host C compiler was
available in the inspected locations, so it has not been compiled or tested as
machine code. It splits halfword stores into byte stores and assumes ordinary
RAM without concurrent observers. It is not a matching decompilation, linked
PS1 executable, or playable reconstruction.

## Next bounded iteration

Trace callers around `0x80068278` and `0x800684bc` to establish the state block's
purpose. Set up a C toolchain and differential execution of the compiled function
before expanding reconstruction. Follow the frame call at `0x80012c80` to locate
the main program's mode/update dispatcher.
