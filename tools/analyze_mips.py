#!/usr/bin/env python3
"""Find strings, address constructions, and nearby calls in a PS-X EXE."""

from __future__ import annotations

import argparse
import json
import struct
from dataclasses import asdict, dataclass
from pathlib import Path

if __package__:
    from .mips import Instruction, decode, signed16
else:
    from mips import Instruction, decode, signed16

HEADER_SIZE = 0x800


@dataclass(frozen=True)
class AddressReference:
    target: int
    high_address: int
    low_address: int
    register: int


class Executable:
    def __init__(self, path: Path):
        raw = path.read_bytes()
        if len(raw) < HEADER_SIZE or raw[:8] != b"PS-X EXE":
            raise ValueError(f"{path} is not a PS-X EXE")
        self.path = path
        self.base = struct.unpack_from("<I", raw, 0x18)[0]
        self.size = struct.unpack_from("<I", raw, 0x1C)[0]
        self.entry = struct.unpack_from("<I", raw, 0x10)[0]
        if not self.size or self.size % 4 or len(raw) < HEADER_SIZE + self.size:
            raise ValueError("invalid or truncated executable payload")
        self.data = raw[HEADER_SIZE : HEADER_SIZE + self.size]

    def address_of_offset(self, offset: int) -> int:
        return self.base + offset

    def offset_of_address(self, address: int) -> int:
        offset = address - self.base
        if offset < 0 or offset >= len(self.data):
            raise ValueError(f"address 0x{address:08x} is outside the loaded image")
        return offset

    def word(self, address: int) -> int:
        if address % 4 or address + 4 > self.base + len(self.data):
            raise ValueError("instruction address must be aligned and inside the payload")
        return struct.unpack_from("<I", self.data, self.offset_of_address(address))[0]

    def instruction(self, address: int) -> Instruction:
        return decode(self.word(address), address)

    def find_bytes(self, needle: bytes) -> list[int]:
        if not needle:
            raise ValueError("empty search string")
        results: list[int] = []
        start = 0
        while True:
            offset = self.data.find(needle, start)
            if offset < 0:
                return results
            results.append(self.address_of_offset(offset))
            start = offset + 1

    def address_references(self, target: int, distance: int = 12) -> list[AddressReference]:
        words = [item[0] for item in struct.iter_unpack("<I", self.data[: len(self.data) & ~3])]
        results: list[AddressReference] = []
        for index, word in enumerate(words):
            if word >> 26 != 15:
                continue
            register = (word >> 16) & 31
            high = (word & 0xFFFF) << 16
            for later in range(index + 1, min(index + 1 + distance, len(words))):
                low_word = words[later]
                op = low_word >> 26
                rs = (low_word >> 21) & 31
                rt = (low_word >> 16) & 31
                if rt == register and op == 9 and rs == register:
                    value = (high + signed16(low_word & 0xFFFF)) & 0xFFFFFFFF
                elif rt == register and op == 13 and rs == register:
                    value = high | (low_word & 0xFFFF)
                else:
                    if rt == register and op not in (4, 5, 40, 41, 42, 43, 46):
                        break
                    continue
                if value == target:
                    results.append(AddressReference(
                        target,
                        self.address_of_offset(index * 4),
                        self.address_of_offset(later * 4),
                        register,
                    ))
                break
        return results

    def window(self, center: int, before: int, after: int) -> list[Instruction]:
        start = max(self.base, (center & ~3) - before * 4)
        end = min(self.base + len(self.data), (center & ~3) + (after + 1) * 4)
        return [self.instruction(address) for address in range(start, end, 4)]


def direct_calls(instructions: list[Instruction]) -> list[int]:
    return sorted({
        int(item.operands, 16) for item in instructions if item.mnemonic == "jal"
    })


def run(args: argparse.Namespace) -> None:
    exe = Executable(args.executable)
    result: dict[str, object] = {
        "executable": str(args.executable),
        "load_address": f"0x{exe.base:08x}",
        "entry_point": f"0x{exe.entry:08x}",
        "query": args.text,
        "matches": [],
    }
    for address in exe.find_bytes(args.text.encode("ascii")):
        match: dict[str, object] = {"string_address": f"0x{address:08x}", "references": []}
        for reference in exe.address_references(address):
            instructions = exe.window(reference.high_address, args.before, args.after)
            match["references"].append({
                **asdict(reference),
                "target": f"0x{reference.target:08x}",
                "high_address": f"0x{reference.high_address:08x}",
                "low_address": f"0x{reference.low_address:08x}",
                "instructions": [str(item) for item in instructions],
                "direct_calls_in_window": [f"0x{item:08x}" for item in direct_calls(instructions)],
            })
        result["matches"].append(match)
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("text", help="ASCII string whose code references should be located")
    parser.add_argument("--before", type=int, default=24)
    parser.add_argument("--after", type=int, default=48)
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()
    try:
        run(args)
    except (OSError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error


if __name__ == "__main__":
    main()
