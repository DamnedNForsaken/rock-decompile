"""Reproduce initial-thread handoff evidence for the verified US executable."""
import argparse
import hashlib
import json
import random
from pathlib import Path

if __package__:
    from .analyze_mips import Executable
    from .rock_iteration import EXPECTED
else:
    from analyze_mips import Executable
    from rock_iteration import EXPECTED


def request_events(exe, entry):
    """Interpret through the ChangeTh call's delay slot; stop at BIOS boundary.

    Only arithmetic, stores and this direct call are accepted. Stack save is
    checked separately and is not reported as a request-global side effect.
    """
    regs = [0] * 32
    regs[4], regs[28], regs[29], regs[31] = entry, 0x80097864, 0x801ff000, 0x81234560
    events = []
    called = False
    for pc in range(0x80012f78, 0x80012f94, 4):
        word = exe.word(pc)
        op, rs, rt = word >> 26, (word >> 21) & 31, (word >> 16) & 31
        imm = word & 65535
        signed = imm - 65536 if imm & 32768 else imm
        if op == 9:
            regs[rt] = (regs[rs] + signed) & 0xffffffff
        elif op == 15:
            regs[rt] = imm << 16
        elif op == 43:
            addr = (regs[rs] + signed) & 0xffffffff
            if addr == 0x801feff8:
                if regs[rt] != 0x81234560:
                    raise ValueError('unexpected saved return address')
            elif addr in (0x80098158, 0x800979d8):
                events.append(('store', addr, regs[rt]))
            else:
                raise ValueError(f'unexpected write: {addr:#x}')
        elif op == 3 and pc == 0x80012f8c:
            target = ((pc + 4) & 0xf0000000) | ((word & 0x3ffffff) << 2)
            if target != 0x8007ff30:
                raise ValueError('unexpected call target')
            regs[31] = pc + 8
            called = True
        else:
            raise ValueError(f'unsupported instruction {word:#x}')
        regs[0] = 0
    if not called:
        raise ValueError('missing ChangeTh call')
    events.append(('ChangeTh', regs[4]))
    return events


def generate(image, output):
    if hashlib.sha256(image.read_bytes()).hexdigest() != EXPECTED:
        raise ValueError('wrong executable hash')
    exe = Executable(image)
    rng = random.Random(60303)
    entries = [0, 0xffffffff, 0x80013420, 0x800155a4] + [rng.getrandbits(32) for _ in range(256)]
    for entry in entries:
        expected = [('store', 0x80098158, entry), ('store', 0x800979d8, 1), ('ChangeTh', 0xff000000)]
        if request_events(exe, entry) != expected:
            raise ValueError(f'request mismatch: {entry:#x}')
    # These are observed table prefixes, not proven full table lengths.
    tables = {
        hex(base): [hex(exe.word(base + 4 * i)) for i in range(count)]
        for base, count in ((0x80080894, 3), (0x80080950, 7), (0x80082114, 11))
    }
    report = {'sha256': EXPECTED, 'table_prefixes': tables,
              'request_validation': {'cases': len(entries), 'result': 'pass',
                  'scope': 'original instructions through BIOS call vs event model; compiled C and context switch not tested'},
              'example_events': request_events(exe, 0x80013420)}
    output.mkdir(parents=True, exist_ok=True)
    for name, start, end in (
        ('entry_155a4', 0x800155a4, 0x80015634),
        ('phase_15634', 0x80015634, 0x80015734),
        ('phase_15734', 0x80015734, 0x80015840),
        ('counter', 0x80016bc0, 0x80016bf4),
        ('numeric_id_bitset_prefix', 0x8001da8c, 0x8001dad0),
        ('flag_set', 0x8001da8c, 0x8001dad0),
        ('phase_15840_prefix', 0x80015840, 0x80015a00),
        ('initial_thread', 0x800131fc, 0x8001326c),
        ('initialize_phase', 0x8001326c, 0x800133d8),
        ('replace_phase', 0x800133d8, 0x80013420),
        ('replacement_entry', 0x80013420, 0x80013578),
        ('next_replace_phase', 0x80013578, 0x800135dc),
        ('request_replacement', 0x80012f78, 0x80012fa4),
        ('consume_replacement', 0x80012d88, 0x80012de0),
    ):
        (output / (name + '.asm.txt')).write_text('\n'.join(str(exe.instruction(a)) for a in range(start, end, 4)) + '\n', encoding='utf-8')
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--output', type=Path, default=Path('build/thread_handoff_iteration'))
    args = parser.parse_args()
    generate(args.image, args.output)
