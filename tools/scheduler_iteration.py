"""Record scheduler evidence and check eligibility against original instructions.

The restricted executor includes branch/load delay slots. C compilation and
BIOS context switching are outside this check.
"""
import argparse
import hashlib
import json
from pathlib import Path

if __package__:
    from .analyze_mips import Executable
    from .rock_iteration import EXPECTED
else:
    from analyze_mips import Executable
    from rock_iteration import EXPECTED

START, RESUME, SKIP = 0x80012cb8, 0x80012d18, 0x80012de0


def original_eligibility(code, status, ticks):
    regs = [0] * 32
    regs[4], regs[17] = 0x801f8100, 127
    pc, branch, load = START, None, None
    for _ in range(64):
        if pc in (RESUME, SKIP):
            return pc == RESUME, ticks
        word = code[pc]
        op, rs, rt = word >> 26, (word >> 21) & 31, (word >> 16) & 31
        imm = word & 65535
        signed = imm - 65536 if imm & 32768 else imm
        old_branch, old_load = branch, load
        branch = load = None
        write = None
        if word == 0:
            pass
        elif op == 37:  # LHU; value becomes visible after next instruction
            addr = (regs[rs] + signed) & 0xffffffff
            if addr not in (0x801f8100, 0x801f8102):
                raise ValueError('unexpected load')
            load = (rt, status if addr == 0x801f8100 else ticks)
        elif op == 9:
            write = (rt, (regs[rs] + signed) & 0xffffffff)
        elif op == 15:
            write = (rt, imm << 16)
        elif op == 10:
            value = regs[rs] if regs[rs] < 0x80000000 else regs[rs] - 0x100000000
            write = (rt, int(value < signed))
        elif op in (4, 5):
            taken = (regs[rs] == regs[rt]) == (op == 4)
            branch = pc + 4 + signed * 4 if taken else pc + 8
        elif op == 2:
            branch = ((pc + 4) & 0xf0000000) | ((word & 0x3ffffff) << 2)
        elif op == 41:
            if regs[rs] + signed != 0x801f8102:
                raise ValueError('unexpected store')
            ticks = regs[rt] & 65535
        elif op == 0 and word & 63 == 0:
            write = ((word >> 11) & 31, (regs[rt] << ((word >> 6) & 31)) & 0xffffffff)
        else:
            raise ValueError(f'unsupported opcode {word:08x}')
        if old_load:
            regs[old_load[0]] = old_load[1]
        if write:
            regs[write[0]] = write[1]
        regs[0] = 0
        pc = old_branch if old_branch is not None else pc + 4
    raise ValueError('instruction limit exceeded')


def validate(exe):
    code = {a: exe.word(a) for a in range(START, RESUME, 4)}
    cases = 0
    # Exhaust all countdown values on the timed path, and every status on the
    # untimed paths. This covers the complete state space of the extracted rule.
    for status, ticks in [(1, n) for n in range(65536)] + [(n, 43210) for n in range(65536) if n != 1]:
        expected_ticks = (ticks - 1) & 65535 if status == 1 else ticks
        expected_resume = expected_ticks == 0 if status == 1 else status in (2, 4, 127)
        actual = original_eligibility(code, status, ticks)
        if actual != (expected_resume, expected_ticks):
            raise ValueError(f'mismatch: status={status}, ticks={ticks}, actual={actual}')
        cases += 1
    return {'cases': cases, 'result': 'pass', 'scope': 'original instructions vs eligibility model; not compiled C'}


def generate(image, output):
    if hashlib.sha256(image.read_bytes()).hexdigest() != EXPECTED:
        raise ValueError('wrong executable hash')
    exe = Executable(image)
    report = {
        'sha256': EXPECTED,
        'record_base': '0x801f8100', 'record_stride': 128, 'record_count': 4,
        'current_record_pointer': '0x801f8300',
        'validation': validate(exe),
        'sleep_zero_next_tick': original_eligibility({a: exe.word(a) for a in range(START, RESUME, 4)}, 1, 0),
    }
    output.mkdir(parents=True, exist_ok=True)
    for name, start, end in (
        ('scheduler', 0x80012c80, 0x80012e10),
        ('thread_create', 0x80012e10, 0x80012e98),
        ('thread_sleep', 0x80012e98, 0x80012ecc),
        ('thread_exit', 0x80012ecc, 0x80012f24),
        ('initializer_callers', 0x80068244, 0x80068508),
    ):
        (output / (name + '.asm.txt')).write_text('\n'.join(str(exe.instruction(a)) for a in range(start, end, 4)) + '\n', encoding='utf-8')
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--output', type=Path, default=Path('build/scheduler_iteration'))
    args = parser.parse_args()
    generate(args.image, args.output)
