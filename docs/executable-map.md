# Initial executable map

These facts come directly from the 0x800-byte PS-X EXE headers extracted from the
verified disc image.

| Property | `SLUS_006.03` | `ROCK_NEO.EXE` |
| --- | ---: | ---: |
| File size | 305152 | 825344 |
| SHA-256 | `469670a017e9301ea6c7cd75cc5cfc1b919b839a62f73e69a979f8dafbe80cac` | `10d2008f2837c466b8a3c3f56ff9b0946096ef29d7f26f09010d78ed4b2568f0` |
| Entry point | `0x8001262c` | `0x80068000` |
| Load address | `0x80010000` | `0x80010000` |
| Loaded size | `0x0004a000` | `0x000c9000` |
| Loaded end | `0x8005a000` | `0x800d9000` |
| Initial stack | `0x801ffff0` | `0x801ffff0` |

`SYSTEM.CNF` directly boots `SLUS_006.03`. That executable contains the literal
path `cdrom:\\ROCK_NEO.EXE;1`, confirming a direct relationship with the much
larger executable. The current working model is that `SLUS_006.03` is the initial
loader/title program and `ROCK_NEO.EXE` is the main game program. The next
analysis step is to identify and label the loader's CD-ROM open/read/execute path.

Both headers leave GP, data, BSS, and stack size as zero. Those regions must be
recovered from startup code and references rather than trusted header metadata.

