from __future__ import annotations

import ctypes as C
import random
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.flags_model import documented_flag_set, documented_flag_test

ROOT = Path(__file__).resolve().parents[1]


class DocumentedFlagModelTests(unittest.TestCase):
    def test_msb_first_mask_and_or(self):
        flags = bytearray(4)
        self.assertEqual(documented_flag_test(flags, 0), 0)
        flags[:] = documented_flag_set(flags, 0)
        self.assertEqual(flags[0], 0x80)
        self.assertEqual(documented_flag_test(flags, 0), 1)
        flags[:] = documented_flag_set(flags, 7)
        self.assertEqual(flags[0], 0x81)
        self.assertEqual(documented_flag_test(flags, 7), 1)
        self.assertEqual(documented_flag_test(flags, 1), 0)

    def test_observed_numeric_ids_do_not_clobber_neighbors(self):
        flags = bytearray(256)
        rng = random.Random(60305)
        for i in range(len(flags)):
            flags[i] = rng.randrange(256)
        original = bytes(flags)
        for identifier in (510, 906, 967, 1319):
            flags[:] = documented_flag_set(flags, identifier)
            self.assertEqual(documented_flag_test(flags, identifier), 1)
        for index, value in enumerate(original):
            if index not in {510 >> 3, 906 >> 3, 967 >> 3, 1319 >> 3}:
                self.assertEqual(flags[index], value)

    def test_set_is_idempotent(self):
        flags = documented_flag_set(bytes(8), 3)
        self.assertEqual(documented_flag_set(flags, 3), flags)


class CompiledFlagSetSmokeTests(unittest.TestCase):
    def test_gcc_shared_matches_documented_model(self):
        gcc = subprocess.run(['gcc', '--version'], capture_output=True, text=True)
        if gcc.returncode:
            self.skipTest('gcc not available')
        with tempfile.TemporaryDirectory() as directory:
            so = Path(directory) / 'rock_flags.so'
            built = subprocess.run(
                ['gcc', '-std=c11', '-shared', '-fPIC', '-Iinclude',
                 'src/rock_flags.c', '-o', str(so)],
                cwd=ROOT, capture_output=True, text=True,
            )
            if built.returncode:
                self.fail(built.stderr or built.stdout)
            lib = C.CDLL(str(so))
            lib.RockFlags_Test.argtypes = [C.POINTER(C.c_uint8), C.c_uint32]
            lib.RockFlags_Test.restype = C.c_int
            lib.RockFlags_Set.argtypes = [C.POINTER(C.c_uint8), C.c_uint32]
            lib.RockFlags_Set.restype = None
            rng = random.Random(60306)
            storage = (C.c_uint8 * 256)(*[rng.randrange(256) for _ in range(256)])
            model = bytearray(storage)
            for identifier in list(range(32)) + [510, 906, 967, 1319, 2047]:
                expected = documented_flag_set(model, identifier)
                lib.RockFlags_Set(storage, identifier)
                model[:] = expected
                self.assertEqual(bytes(storage), expected)
                self.assertEqual(lib.RockFlags_Test(storage, identifier), 1)
