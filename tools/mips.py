#!/usr/bin/env python3
"""Small dependency-free MIPS R3000 disassembler used by the PS1 analysis tools."""

from __future__ import annotations

from dataclasses import dataclass

REGISTERS = (
    "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
    "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
    "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
    "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra",
)


def signed16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


@dataclass(frozen=True)
class Instruction:
    address: int
    word: int
    mnemonic: str
    operands: str = ""

    def __str__(self) -> str:
        suffix = f" {self.operands}" if self.operands else ""
        return f"{self.address:08x}: {self.word:08x}  {self.mnemonic}{suffix}"


def decode(word: int, address: int) -> Instruction:
    op = word >> 26
    rs = (word >> 21) & 31
    rt = (word >> 16) & 31
    rd = (word >> 11) & 31
    shift = (word >> 6) & 31
    function = word & 63
    immediate = word & 0xFFFF
    simm = signed16(immediate)
    r = REGISTERS

    if word == 0:
        return Instruction(address, word, "nop")
    if op == 0:
        shifts = {0: "sll", 2: "srl", 3: "sra"}
        variable_shifts = {4: "sllv", 6: "srlv", 7: "srav"}
        arithmetic = {
            32: "add", 33: "addu", 34: "sub", 35: "subu",
            36: "and", 37: "or", 38: "xor", 39: "nor",
            42: "slt", 43: "sltu",
        }
        if function in shifts:
            return Instruction(address, word, shifts[function], f"{r[rd]}, {r[rt]}, {shift}")
        if function in variable_shifts:
            return Instruction(address, word, variable_shifts[function], f"{r[rd]}, {r[rt]}, {r[rs]}")
        if function == 8:
            return Instruction(address, word, "jr", r[rs])
        if function == 9:
            return Instruction(address, word, "jalr", f"{r[rd]}, {r[rs]}")
        if function in (12, 13):
            return Instruction(address, word, "syscall" if function == 12 else "break")
        move_special = {16: "mfhi", 17: "mthi", 18: "mflo", 19: "mtlo"}
        if function in move_special:
            register = r[rd] if function in (16, 18) else r[rs]
            return Instruction(address, word, move_special[function], register)
        multiply = {24: "mult", 25: "multu", 26: "div", 27: "divu"}
        if function in multiply:
            return Instruction(address, word, multiply[function], f"{r[rs]}, {r[rt]}")
        if function in arithmetic:
            return Instruction(address, word, arithmetic[function], f"{r[rd]}, {r[rs]}, {r[rt]}")
    if op in (2, 3):
        target = ((address + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
        return Instruction(address, word, "j" if op == 2 else "jal", f"0x{target:08x}")
    branches = {4: "beq", 5: "bne"}
    if op in branches:
        target = (address + 4 + simm * 4) & 0xFFFFFFFF
        return Instruction(address, word, branches[op], f"{r[rs]}, {r[rt]}, 0x{target:08x}")
    single_branches = {6: "blez", 7: "bgtz"}
    if op in single_branches:
        target = (address + 4 + simm * 4) & 0xFFFFFFFF
        return Instruction(address, word, single_branches[op], f"{r[rs]}, 0x{target:08x}")
    if op == 1:
        names = {0: "bltz", 1: "bgez", 16: "bltzal", 17: "bgezal"}
        if rt in names:
            target = (address + 4 + simm * 4) & 0xFFFFFFFF
            return Instruction(address, word, names[rt], f"{r[rs]}, 0x{target:08x}")
    immediate_ops = {8: "addi", 9: "addiu", 10: "slti", 11: "sltiu"}
    if op in immediate_ops:
        return Instruction(address, word, immediate_ops[op], f"{r[rt]}, {r[rs]}, {simm}")
    logical_ops = {12: "andi", 13: "ori", 14: "xori"}
    if op in logical_ops:
        return Instruction(address, word, logical_ops[op], f"{r[rt]}, {r[rs]}, 0x{immediate:04x}")
    if op == 15:
        return Instruction(address, word, "lui", f"{r[rt]}, 0x{immediate:04x}")
    memory_ops = {
        32: "lb", 33: "lh", 34: "lwl", 35: "lw", 36: "lbu",
        37: "lhu", 38: "lwr", 40: "sb", 41: "sh", 42: "swl",
        43: "sw", 46: "swr", 50: "lwc2", 58: "swc2",
    }
    if op in memory_ops:
        return Instruction(address, word, memory_ops[op], f"{r[rt]}, {simm}({r[rs]})")
    if op in (16, 18):
        cop = 0 if op == 16 else 2
        transfers = {0: "mfc", 2: "cfc", 4: "mtc", 6: "ctc"}
        if rs in transfers:
            return Instruction(address, word, f"{transfers[rs]}{cop}", f"{r[rt]}, ${rd}")
        return Instruction(address, word, f"cop{cop}", f"0x{word & 0x01ffffff:07x}")
    return Instruction(address, word, ".word", f"0x{word:08x}")

