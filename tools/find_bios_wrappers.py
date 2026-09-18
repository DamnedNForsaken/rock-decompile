#!/usr/bin/env python3
"""Locate standard A0/B0/C0 BIOS call stubs in a PS-X EXE."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

HEADER_SIZE = 0x800
VECTORS = {0xA0: "A0", 0xB0: "B0", 0xC0: "C0"}

# Only names directly established for this project are listed. Unknown calls are
# intentionally emitted by vector/function number instead of being guessed.
KNOWN = {
    (0xB0, 0x0E): "OpenTh",
    (0xB0, 0x0F): "CloseTh",
    (0xB0, 0x10): "ChangeTh",
    (0xA0, 0x13): "setjmp",
    (0xA0, 0x2A): "memcpy",
    (0xA0, 0x39): "InitHeap",
    (0xA0, 0x3F): "printf",
    (0xA0, 0x44): "FlushCache",
    (0xA0, 0x49): "GPU_cw",
    (0xA0, 0x51): "LoadExec",
    (0xA0, 0x71): "_96_init",
    (0xA0, 0x72): "_96_remove",
    (0xB0, 0x07): "DeliverEvent",
    (0xB0, 0x08): "OpenEvent",
    (0xB0, 0x09): "CloseEvent",
    (0xB0, 0x0C): "EnableEvent",
    (0xB0, 0x0D): "DisableEvent",
    (0xB0, 0x12): "InitPAD2",
    (0xB0, 0x13): "StartPAD2",
    (0xB0, 0x14): "StopPAD2",
    (0xB0, 0x15): "PAD_init2",
    (0xB0, 0x17): "ReturnFromException",
    (0xB0, 0x18): "ResetEntryInt",
    (0xB0, 0x19): "HookEntryInt",
    (0xB0, 0x3F): "puts",
    (0xB0, 0x5B): "ChangeClearPAD",
    (0xC0, 0x02): "SysEnqIntRP",
    (0xC0, 0x03): "SysDeqIntRP",
    (0xC0, 0x0A): "ChangeClearRCnt",
}


def scan(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    if raw[:8] != b"PS-X EXE":
        raise ValueError(f"{path} is not a PS-X EXE")
    base, size = struct.unpack_from("<II", raw, 0x18)
    data = raw[HEADER_SIZE : HEADER_SIZE + size]
    words = [item[0] for item in struct.iter_unpack("<I", data[: len(data) & ~3])]
    wrappers: list[dict[str, object]] = []
    for index in range(len(words) - 2):
        first, second, third = words[index : index + 3]
        # addiu t2,zero,vector ; jr t2 ; addiu t1,zero,function
        if first & 0xFFFF0000 != 0x240A0000 or second != 0x01400008:
            continue
        if third & 0xFFFF0000 != 0x24090000:
            continue
        vector = first & 0xFFFF
        function = third & 0xFFFF
        if vector not in VECTORS:
            continue
        wrappers.append({
            "address": f"0x{base + index * 4:08x}",
            "vector": VECTORS[vector],
            "function": f"0x{function:02x}",
            "name": KNOWN.get((vector, function)),
        })
    return {"executable": str(path), "wrapper_count": len(wrappers), "wrappers": wrappers}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()
    try:
        report = scan(args.executable)
    except (OSError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
