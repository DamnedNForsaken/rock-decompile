"""Restricted execution of the original counter leaf, including delay slots."""
def execute_counter(exe, initial):
    regs = [0] * 32
    regs[31] = 0x12345678
    memory = initial
    pc, branch, load = 0x80016bc0, None, None
    for _ in range(32):
        if pc == 0x12345678:
            return memory
        word = exe.word(pc)
        op, rs, rt = word >> 26, (word >> 21) & 31, (word >> 16) & 31
        imm = word & 65535
        signed = imm - 65536 if imm & 32768 else imm
        old_branch, old_load = branch, load
        branch = load = None
        write = None
        if word == 0:
            pass
        elif op == 15:
            write = (rt, imm << 16)
        elif op == 13:
            write = (rt, regs[rs] | imm)
        elif op == 9:
            write = (rt, (regs[rs] + signed) & 0xffffffff)
        elif op in (35, 43):
            if (regs[rs] + signed) & 0xffffffff != 0x800c1b1c:
                raise ValueError('unexpected memory address')
            if op == 35:
                load = (rt, memory)
            else:
                memory = regs[rt]
        elif op == 0 and word & 63 == 43:
            write = ((word >> 11) & 31, int(regs[rs] < regs[rt]))
        elif op == 4:
            branch = pc + 4 + signed * 4 if regs[rs] == regs[rt] else pc + 8
        elif word == 0x03e00008:
            branch = regs[31]
        else:
            raise ValueError(f'unsupported instruction {word:#x}')
        if old_load:
            regs[old_load[0]] = old_load[1]
        if write:
            regs[write[0]] = write[1]
        regs[0] = 0
        pc = old_branch if old_branch is not None else pc + 4
    raise ValueError('counter exceeded instruction budget')
