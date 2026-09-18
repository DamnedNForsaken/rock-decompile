# Disc format notes

## Confirmed

- CloneCD descriptor version 3.
- Track 1 begins at LBA 0 and contains unscrambled Mode 2 sectors.
- Track 2 is CD audio and begins at LBA 207295 (`46:05:70`).
- The primary volume descriptor identifies `PLAYSTATION` / `MEGAMAN_LEGENDS`.
- `SYSTEM.CNF` boots `cdrom:\\SLUS_006.03;1`.
- The root filesystem contains the directories `CDDATA`, `DAT`, `STR`, and `XA`.

## Sector handling

A raw CD sector is 2352 bytes. For Mode 2 sectors the first 24 bytes are sync,
address, mode, and duplicated XA subheader. Form 1 then contains 2048 data bytes;
Form 2 contains 2324. `tools/psxdisc.py` checks the sector header and selects the
payload length from the XA submode bit instead of blindly stripping a constant
number of bytes.

The filesystem itself is ISO9660/CD-XA. Directory extents are Form 1. Streaming
files may contain Form 2 sectors, but ISO9660 extent sizes still count 2048-byte
logical blocks. The extractor therefore emits the first 2048 data bytes per
sector and records encountered sector forms. Full Form 2 payloads, XA subheaders,
EDC, and other physical-sector details remain available in the original image.
