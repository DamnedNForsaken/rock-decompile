import struct
import tempfile
import unittest
from pathlib import Path

from tools.analyze_mips import Executable
from tools.rock_iteration import execute_initializer


class AnalysisSafetyTests(unittest.TestCase):
    def test_rejects_truncated_executable(self):
        header = bytearray(0x800)
        header[:8] = b'PS-X EXE'
        struct.pack_into('<II', header, 0x18, 0x80010000, 16)
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'bad.exe'
            image.write_bytes(header)
            with self.assertRaisesRegex(ValueError, 'truncated'):
                Executable(image)

    def test_return_delay_slot_executes_store(self):
        # LUI at,0x800c; ADDIU v0,zero,7; JR ra; SB v0,0x3560(at)
        code = [0x3c01800c, 0x24020007, 0x03e00008, 0xa0223560]
        result = execute_initializer(code, 0, bytes([99] * 18))
        self.assertEqual(result, bytes([7] + [99] * 17))

    def test_out_of_range_store_fails(self):
        with self.assertRaisesRegex(ValueError, 'store'):
            execute_initializer([0x3c01800c, 0xa020355f], 0, bytes(18))

    def test_unsupported_instruction_fails(self):
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            execute_initializer([0x0c004000], 0, bytes(18))
