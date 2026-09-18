from __future__ import annotations

import hashlib
import struct
import tempfile
import unittest
from pathlib import Path, PurePosixPath

from tools.psxdisc import FORM1_SIZE, Entry, parse_record
from tools.psxexe import HEADER_SIZE, inspect
from tools.mips import decode
from tools.find_bios_wrappers import scan as scan_bios_wrappers


class PsxExeTests(unittest.TestCase):
    def test_reads_header_and_hash(self) -> None:
        header = bytearray(HEADER_SIZE)
        header[:8] = b"PS-X EXE"
        struct.pack_into("<I", header, 0x10, 0x80012340)
        struct.pack_into("<I", header, 0x14, 0x80050000)
        struct.pack_into("<I", header, 0x18, 0x80010000)
        struct.pack_into("<I", header, 0x1C, FORM1_SIZE)
        image = bytes(header) + bytes(FORM1_SIZE)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "TEST.EXE"
            path.write_bytes(image)
            report = inspect(path)
        self.assertEqual(report["entry_point"], "0x80012340")
        self.assertEqual(report["initial_gp"], "0x80050000")
        self.assertEqual(report["text_end"], "0x80010800")
        self.assertEqual(report["sha256"], hashlib.sha256(image).hexdigest())

    def test_rejects_truncated_text(self) -> None:
        header = bytearray(HEADER_SIZE)
        header[:8] = b"PS-X EXE"
        struct.pack_into("<I", header, 0x1C, FORM1_SIZE)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "BAD.EXE"
            path.write_bytes(header)
            with self.assertRaisesRegex(ValueError, "declares"):
                inspect(path)


class IsoRecordTests(unittest.TestCase):
    def test_parses_file_record_and_strips_version(self) -> None:
        name = b"ROCK_NEO.EXE;1"
        record = bytearray(33 + len(name))
        record[0] = len(record)
        struct.pack_into("<I", record, 2, 1234)
        struct.pack_into("<I", record, 10, 825344)
        record[32] = len(name)
        record[33:] = name
        self.assertEqual(
            parse_record(bytes(record), PurePosixPath(".")),
            Entry("ROCK_NEO.EXE", 1234, 825344, False, 0),
        )


class MipsDecoderTests(unittest.TestCase):
    def test_decodes_loader_style_address_construction(self) -> None:
        self.assertEqual(str(decode(0x3C048006, 0x80020000)), "80020000: 3c048006  lui a0, 0x8006")
        self.assertEqual(
            str(decode(0x24849B24, 0x80020004)),
            "80020004: 24849b24  addiu a0, a0, -25820",
        )

    def test_decodes_jal_target(self) -> None:
        instruction = decode(0x0C004D00, 0x80020000)
        self.assertEqual(instruction.mnemonic, "jal")
        self.assertEqual(instruction.operands, "0x80013400")


class BiosWrapperTests(unittest.TestCase):
    def test_finds_a0_loadexec_thunk(self) -> None:
        header = bytearray(HEADER_SIZE)
        header[:8] = b"PS-X EXE"
        struct.pack_into("<I", header, 0x18, 0x80010000)
        body = struct.pack("<IIII", 0x240A00A0, 0x01400008, 0x24090051, 0)
        struct.pack_into("<I", header, 0x1C, len(body))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "BIOS.EXE"
            path.write_bytes(header + body)
            report = scan_bios_wrappers(path)
        self.assertEqual(report["wrapper_count"], 1)
        self.assertEqual(report["wrappers"][0]["name"], "LoadExec")


if __name__ == "__main__":
    unittest.main()
