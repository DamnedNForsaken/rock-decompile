#!/usr/bin/env python3
"""Regenerate the first ROCK_NEO map and check a bounded leaf's RAM effects.

This is static evidence plus a restricted instruction interpreter, not a PS1
emulator or a C compiler. Candidate call targets can include data false positives.
"""
import argparse
import csv
import hashlib
import json
import random
import struct
from pathlib import Path

if __package__:
    from .analyze_mips import Executable
    from .find_bios_wrappers import scan
else:
    from analyze_mips import Executable
    from find_bios_wrappers import scan

EXPECTED = '10d2008f2837c466b8a3c3f56ff9b0946096ef29d7f26f09010d78ed4b2568f0'
RANGES = {
    'startup': (0x80068000, 0x800680ac),
    'main': (0x80011c90, 0x80011f04),
    'state_initializer': (0x800680bc, 0x80068120),
}


def execute_initializer(words, argument, initial):
    """Execute only this leaf's instruction subset; reject other instructions.

    Includes JR's delay slot. Bounded writable memory catches unexpected stores.
    No loads or conditional branches occur in this leaf.
    """
    registers = [0] * 32
    registers[4] = argument & 0xffffffff
    memory = bytearray(initial)
    returning = False
    for index, word in enumerate(words):
        op, rs, rt = word >> 26, (word >> 21) & 31, (word >> 16) & 31
        imm = word & 0xffff
        signed = imm - 65536 if imm & 32768 else imm
        delay = returning
        if word == 0:
            pass
        elif word == 0x03e00008:
            returning = True
        elif op == 15:
            registers[rt] = imm << 16
        elif op == 9:
            registers[rt] = (registers[rs] + signed) & 0xffffffff
        elif op in (40, 41):
            address = (registers[rs] + signed) & 0xffffffff
            offset = address - 0x800c3560
            size = 1 if op == 40 else 2
            if offset < 0 or offset + size > len(memory) or address % size:
                raise ValueError('unexpected or unaligned store')
            memory[offset:offset + size] = (registers[rt] & ((1 << (size * 8)) - 1)).to_bytes(size, 'little')
        else:
            raise ValueError(f'unsupported instruction {word:08x}')
        registers[0] = 0
        if delay:
            if index != len(words) - 1:
                raise ValueError('unexpected trailing instructions')
            return memory
    raise ValueError('missing return/delay slot')


def check_initializer(exe):
    start, end = RANGES['state_initializer']
    words = [exe.word(a) for a in range(start, end, 4)]
    randomizer = random.Random(603)
    cases = 0
    for low in range(256):
        for high in (0, 0x12345600, 0xffffff00):
            original = bytearray(randomizer.randrange(256) for _ in range(18))
            expected = bytearray(original)
            expected[0:6] = bytes(6)
            expected[10:18] = bytes((0, 0, 255, 0, 24, low, 255, 255))
            actual = execute_initializer(words, high | low, original)
            if actual != expected:
                raise ValueError(f'initializer mismatch for argument {high | low:#x}')
            cases += 1
    return {'cases': cases, 'result': 'pass', 'scope': 'original MIPS vs documented RAM postcondition; C compilation not tested'}


def generate(image, output):
    if hashlib.sha256(image.read_bytes()).hexdigest() != EXPECTED:
        raise ValueError('wrong executable version/hash')
    exe = Executable(image)
    output.mkdir(parents=True, exist_ok=True)
    calls = []
    for offset in range(0, len(exe.data), 4):
        address = exe.base + offset
        word = exe.word(address)
        if word >> 26 == 3:
            target = ((address + 4) & 0xf0000000) | ((word & 0x3ffffff) << 2)
            if exe.base <= target < exe.base + exe.size:
                calls.append((address, target))
    with (output / 'candidate_calls.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['site', 'target', 'status'])
        writer.writerows((f'0x{site:08x}', f'0x{target:08x}', 'unvalidated_linear_scan') for site, target in calls)
    for name, (start, end) in RANGES.items():
        (output / f'{name}.asm.txt').write_text('\n'.join(str(exe.instruction(a)) for a in range(start, end, 4)) + '\n', encoding='utf-8')
    bios = scan(image)
    report = {
        'sha256': EXPECTED,
        'bios': bios,
        'candidate_call_sites': len(calls),
        'candidate_call_targets': len({target for _, target in calls}),
        'initializer_callers': [f'0x{site:08x}' for site, target in calls if target == 0x800680bc],
        'initializer_validation': check_initializer(exe),
        'main_direct_calls': [{'site': f'0x{site:08x}', 'target': f'0x{target:08x}'} for site, target in calls if 0x80011c90 <= site < 0x80011f04],
    }
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('bios', 'main_direct_calls')}, indent=2))
    print(f'BIOS wrapper patterns: {bios["wrapper_count"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--output', type=Path, default=Path('build/rock_iteration'))
    args = parser.parse_args()
    generate(args.image, args.output)
