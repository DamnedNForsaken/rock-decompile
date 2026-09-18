"""Build host C and compare DLL results with the original PS1 instruction models."""
import argparse
import ctypes as C
import hashlib
import json
import random
import subprocess
from pathlib import Path

if __package__:
    from .flags_model import execute_flag_query
    from .counter_model import execute_counter
    from .analyze_mips import Executable
    from .rock_iteration import EXPECTED, execute_initializer
    from .scheduler_iteration import START, RESUME, original_eligibility
    from .thread_handoff_iteration import request_events
else:
    from flags_model import execute_flag_query
    from counter_model import execute_counter
    from analyze_mips import Executable
    from rock_iteration import EXPECTED, execute_initializer
    from scheduler_iteration import START, RESUME, original_eligibility
    from thread_handoff_iteration import request_events

ROOT = Path(__file__).resolve().parents[1]


class Request(C.Structure):
    _fields_ = [('entry', C.c_uint32), ('pending', C.c_uint32)]


CALLBACK = C.CFUNCTYPE(None, C.c_uint32)


def verify(exe, dll):
    lib = C.CDLL(str(dll.resolve()))
    lib.RockState_Init.argtypes = [C.POINTER(C.c_uint8), C.c_uint32]
    lib.RockState_Init.restype = None
    lib.RockScheduler_ShouldResume.argtypes = [C.c_uint16, C.POINTER(C.c_uint16)]
    lib.RockScheduler_ShouldResume.restype = C.c_int
    lib.RockThread_RequestReplacement.argtypes = [C.POINTER(Request), C.c_uint32, CALLBACK]
    lib.RockThread_RequestReplacement.restype = None
    lib.RockCounter_Tick.argtypes = [C.POINTER(C.c_uint32)]
    lib.RockCounter_Tick.restype = None
    lib.RockFlags_Test.argtypes = [C.POINTER(C.c_uint8), C.c_uint32]
    lib.RockFlags_Test.restype = C.c_int
    rng = random.Random(60304)
    words = [exe.word(a) for a in range(0x800680bc, 0x80068120, 4)]
    init_count = 0
    for low in range(256):
        for high in (0, 0x12345600, 0xffffff00):
            initial = bytes(rng.randrange(256) for _ in range(18))
            expected = execute_initializer(words, high | low, initial)
            # Surround the output with sentinels to detect nearby stray writes.
            buf = (C.c_uint8 * 50).from_buffer_copy(bytes([0xa5] * 16) + initial + bytes([0x5a] * 16))
            pointer = C.cast(C.byref(buf, 16), C.POINTER(C.c_uint8))
            lib.RockState_Init(pointer, high | low)
            if bytes(buf) != bytes([0xa5] * 16) + expected + bytes([0x5a] * 16):
                raise ValueError(f'compiled initializer mismatch: {high | low:#x}')
            init_count += 1
    code = {a: exe.word(a) for a in range(START, RESUME, 4)}
    scheduler_count = 0
    # Every timed countdown, plus each other status at multiple representative
    # countdowns. This is not all 2^32 possible status/countdown pairs.
    for status in range(65536):
        values = range(65536) if status == 1 else (0, 1, 2, 32768, 65535)
        for ticks in values:
            expected = original_eligibility(code, status, ticks)
            actual_ticks = C.c_uint16(ticks)
            result = lib.RockScheduler_ShouldResume(status, C.byref(actual_ticks))
            if (result, actual_ticks.value) != expected:
                raise ValueError(f'compiled scheduler mismatch: {status}, {ticks}')
            scheduler_count += 1
    entries = [0, 0xffffffff, 0x80013420, 0x800155a4] + [rng.getrandbits(32) for _ in range(256)]
    for entry in entries:
        request = Request(rng.getrandbits(32), rng.getrandbits(32))
        observed = []

        @CALLBACK
        def on_change(handle):
            observed.append((request.entry, request.pending, handle))

        events = request_events(exe, entry)
        expected = [(events[0][2], events[1][2], events[2][1])]
        lib.RockThread_RequestReplacement(C.byref(request), entry, on_change)
        if observed != expected or (request.entry, request.pending) != (entry, 1):
            raise ValueError(f'compiled replacement mismatch: {entry:#x}')
    counter_inputs = [0, 1, 10799998, 10799999, 10800000, 0xfffffffe, 0xffffffff]
    counter_inputs += [rng.getrandbits(32) for _ in range(10000)]
    for value in counter_inputs:
        expected = execute_counter(exe, value)
        actual = C.c_uint32(value)
        lib.RockCounter_Tick(C.byref(actual))
        if actual.value != expected:
            raise ValueError(f'compiled counter mismatch: {value:#x}')
    flag_cases = 0
    flags = (C.c_uint8 * 8192)(*[rng.randrange(256) for _ in range(8192)])
    # Every byte value and bit position at representative byte addresses.
    # The allocation is test storage, not a claim about original table capacity.
    for index in (0, 1, 159, 160, 175, 8191):
        for value in range(256):
            flags[index] = value
            for bit in range(8):
                identifier = index * 8 + bit
                expected = execute_flag_query(exe, flags, identifier)
                if lib.RockFlags_Test(flags, identifier) != expected:
                    raise ValueError(f'compiled flag query mismatch: {identifier}, {value}')
                flag_cases += 1
    return {'dll': str(dll.relative_to(ROOT)),
            'dll_sha256': hashlib.sha256(dll.read_bytes()).hexdigest(),
            'initializer_cases': init_count, 'scheduler_cases': scheduler_count,
            'replacement_cases': len(entries), 'counter_cases': len(counter_inputs),
            'flag_query_cases': flag_cases, 'result': 'pass'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    args = parser.parse_args()
    image = args.image.resolve()
    if hashlib.sha256(image.read_bytes()).hexdigest() != EXPECTED:
        raise ValueError('wrong executable hash')
    output = ROOT / 'build/host'
    output.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(['cmd.exe', '/d', '/c', 'tools\\build_host.cmd'],
                               cwd=ROOT, capture_output=True, text=True)
    (output / 'build.log').write_text(completed.stdout + completed.stderr, encoding='utf-8')
    if completed.returncode:
        raise RuntimeError(f'C compilation failed; see {output / "build.log"}')
    exe = Executable(image)
    configurations = []
    for name in ('debug', 'release'):
        result = verify(exe, output / name / 'rock.dll')
        configurations.append(result)
        print(json.dumps(result), flush=True)
    source_files = ['src/rock_state.c', 'src/rock_scheduler.c', 'src/rock_counter.c',
                    'src/rock_flags.c', 'include/rock_flags.h', 'tools/flags_model.py',
                    'include/rock_counter.h', 'tools/counter_model.py',
                    'include/rock_state.h', 'include/rock_scheduler.h',
                    'tools/build_host.cmd', 'tools/verify_compiled.py',
                    'tools/rock_iteration.py', 'tools/scheduler_iteration.py',
                    'tools/thread_handoff_iteration.py', 'tools/analyze_mips.py']
    report = {'image_sha256': EXPECTED, 'configurations': configurations,
              'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_files},
              'limitations': ['Compared to restricted local MIPS interpreters, not a full emulator.',
                              'Host x64 C, not PS1 instruction matching.',
                              'Replacement checks publication at callback time, not the order of individual stores.',
                              'No actual BIOS context switch or concurrent access tested.']}
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
