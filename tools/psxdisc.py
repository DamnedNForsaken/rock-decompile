#!/usr/bin/env python3
"""Inspect and extract an ISO9660 filesystem from a raw PS1 Mode 2 track."""

from __future__ import annotations

import argparse
import json
import struct
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

RAW_SECTOR_SIZE = 2352
MODE2_DATA_OFFSET = 24
FORM1_SIZE = 2048
FORM2_SIZE = 2324
SYNC = bytes.fromhex("00ffffffffffffffffffff00")


class DiscError(RuntimeError):
    pass


@dataclass(frozen=True)
class Entry:
    path: str
    lba: int
    iso_size: int
    is_directory: bool
    xa_attributes: int


class RawMode2Image:
    def __init__(self, path: Path):
        self.path = path
        self.file = path.open("rb")

    def close(self) -> None:
        self.file.close()

    def sector(self, lba: int) -> tuple[bytes, int]:
        self.file.seek(lba * RAW_SECTOR_SIZE)
        raw = self.file.read(RAW_SECTOR_SIZE)
        if len(raw) != RAW_SECTOR_SIZE:
            raise DiscError(f"short read at LBA {lba}")
        if raw[:12] != SYNC or raw[15] != 2:
            raise DiscError(f"LBA {lba} is not a raw Mode 2 sector")
        submode = raw[18]
        size = FORM2_SIZE if submode & 0x20 else FORM1_SIZE
        return raw[MODE2_DATA_OFFSET : MODE2_DATA_OFFSET + size], size

    def form1_extent(self, lba: int, size: int) -> bytes:
        output = bytearray()
        while len(output) < size:
            payload, payload_size = self.sector(lba)
            if payload_size != FORM1_SIZE:
                raise DiscError(f"expected Form 1 filesystem data at LBA {lba}")
            output.extend(payload)
            lba += 1
        return bytes(output[:size])


def u32le(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def clean_identifier(raw: bytes) -> str:
    name = raw.decode("ascii", errors="replace")
    return name.rsplit(";", 1)[0]


def parse_record(record: bytes, parent: PurePosixPath) -> Entry:
    extent = u32le(record, 2)
    size = u32le(record, 10)
    flags = record[25]
    name_len = record[32]
    identifier = record[33 : 33 + name_len]
    if identifier == b"\x00":
        name = "."
    elif identifier == b"\x01":
        name = ".."
    else:
        name = clean_identifier(identifier)
    # ISO9660 System Use begins after the identifier and its even-byte padding.
    system_use = 33 + name_len + (1 if name_len % 2 == 0 else 0)
    xa_attributes = 0
    if len(record) >= system_use + 6 and record[system_use + 4 : system_use + 6] == b"XA":
        xa_attributes = int.from_bytes(record[system_use : system_use + 2], "big")
    path = parent if name == "." else parent / name
    return Entry(str(path), extent, size, bool(flags & 0x02), xa_attributes)


def volume_info(image: RawMode2Image) -> dict[str, object]:
    pvd, size = image.sector(16)
    if size != FORM1_SIZE or pvd[0] != 1 or pvd[1:6] != b"CD001":
        raise DiscError("LBA 16 is not an ISO9660 primary volume descriptor")
    return {
        "system_id": pvd[8:40].decode("ascii").strip(),
        "volume_id": pvd[40:72].decode("ascii").strip(),
        "volume_sectors": u32le(pvd, 80),
        "logical_block_size": int.from_bytes(pvd[128:130], "little"),
        "root_record": pvd[156 : 156 + pvd[156]],
    }


def walk(image: RawMode2Image, directory: Entry) -> list[Entry]:
    data = image.form1_extent(directory.lba, directory.iso_size)
    entries: list[Entry] = []
    offset = 0
    parent = PurePosixPath(directory.path)
    children: list[Entry] = []
    while offset < len(data):
        length = data[offset]
        if length == 0:
            offset = ((offset // FORM1_SIZE) + 1) * FORM1_SIZE
            continue
        record = data[offset : offset + length]
        child = parse_record(record, parent)
        offset += length
        if child.path in (str(parent), str(parent / "..")):
            continue
        children.append(child)
        entries.append(child)
    for child in children:
        if child.is_directory:
            entries.extend(walk(image, child))
    return entries


def scan(path: Path) -> tuple[dict[str, object], list[Entry]]:
    image = RawMode2Image(path)
    try:
        volume = volume_info(image)
        root = parse_record(volume.pop("root_record"), PurePosixPath("."))
        entries = walk(image, root)
        return volume, entries
    finally:
        image.close()


def extract_file(image: RawMode2Image, entry: Entry, destination: Path) -> dict[str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    remaining = entry.iso_size
    lba = entry.lba
    forms = {"form1_sectors": 0, "form2_sectors": 0}
    with destination.open("wb") as output:
        # ISO9660 sizes count 2048-byte logical blocks even when a physical
        # Mode 2 Form 2 sector exposes 2324 data bytes. Emitting the entire
        # Form 2 payload would shift every subsequent block in the file.
        while remaining > 0:
            payload, size = image.sector(lba)
            key = "form2_sectors" if size == FORM2_SIZE else "form1_sectors"
            forms[key] += 1
            take = min(remaining, FORM1_SIZE)
            output.write(payload[:take])
            remaining -= take
            lba += 1
    return forms


def command_inventory(args: argparse.Namespace) -> None:
    volume, entries = scan(args.image)
    manifest = {"image": str(args.image), "volume": volume, "entries": [asdict(e) for e in entries]}
    encoded = json.dumps(manifest, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
        print(f"Wrote {len(entries)} entries to {args.output}")
    else:
        print(encoded, end="")


def command_extract(args: argparse.Namespace) -> None:
    volume, entries = scan(args.image)
    image = RawMode2Image(args.image)
    report: dict[str, object] = {"image": str(args.image), "volume": volume, "files": []}
    try:
        for entry in entries:
            destination = args.output.joinpath(*PurePosixPath(entry.path).parts)
            if entry.is_directory:
                destination.mkdir(parents=True, exist_ok=True)
                continue
            forms = extract_file(image, entry, destination)
            report["files"].append({**asdict(entry), **forms})
    finally:
        image.close()
    report_path = args.output / "_extraction.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(report['files'])} files to {args.output}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)
    inventory = subparsers.add_parser("inventory", help="write an ISO filesystem manifest")
    inventory.add_argument("image", type=Path)
    inventory.add_argument("--output", "-o", type=Path)
    inventory.set_defaults(func=command_inventory)
    extract = subparsers.add_parser("extract", help="extract ISO files from the data track")
    extract.add_argument("image", type=Path)
    extract.add_argument("--output", "-o", type=Path, required=True)
    extract.set_defaults(func=command_extract)
    return result


def main() -> None:
    args = parser().parse_args()
    try:
        args.func(args)
    except (DiscError, OSError) as error:
        raise SystemExit(f"error: {error}") from error


if __name__ == "__main__":
    main()
