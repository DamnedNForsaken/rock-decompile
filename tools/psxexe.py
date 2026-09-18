#!/usr/bin/env python3
"""Print the header and basic memory map of a Sony PS-X EXE."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

HEADER_SIZE = 0x800


def word(header: bytes, offset: int) -> int:
    return struct.unpack_from("<I", header, offset)[0]


def inspect(path: Path) -> dict[str, object]:
    file_size = path.stat().st_size
    with path.open("rb") as source:
        header = source.read(HEADER_SIZE)
        source.seek(0)
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if len(header) != HEADER_SIZE or header[:8] != b"PS-X EXE":
        raise ValueError(f"{path} is not a PS-X EXE")
    text_address = word(header, 0x18)
    text_size = word(header, 0x1C)
    if HEADER_SIZE + text_size > file_size:
        raise ValueError(
            f"{path} declares {text_size} text bytes but is only {file_size} bytes"
        )
    return {
        "path": str(path),
        "file_size": file_size,
        "sha256": digest,
        "entry_point": f"0x{word(header, 0x10):08x}",
        "initial_gp": f"0x{word(header, 0x14):08x}",
        "text_address": f"0x{text_address:08x}",
        "text_size": text_size,
        "text_end": f"0x{text_address + text_size:08x}",
        "data_address": f"0x{word(header, 0x20):08x}",
        "data_size": word(header, 0x24),
        "bss_address": f"0x{word(header, 0x28):08x}",
        "bss_size": word(header, 0x2C),
        "stack_address": f"0x{word(header, 0x30):08x}",
        "stack_size": word(header, 0x34),
        "marker": header[0x4C:0x800].split(b"\0", 1)[0].decode("ascii", errors="replace"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()
    try:
        report = inspect(args.executable)
    except (OSError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
