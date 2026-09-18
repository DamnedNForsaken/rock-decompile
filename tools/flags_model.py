"""Execute flag leaves with original load delay and return slot."""

FLAG_BASE = 0x800be378
QUERY_START, QUERY_END = 0x8001da58, 0x8001da8c
SET_START, SET_END = 0x8001da8c, 0x8001dad0


def documented_flag_mask(identifier):
    return 0x80 >> (identifier & 7)


def documented_flag_test(flags, identifier):
    return int(bool(flags[identifier >> 3] & documented_flag_mask(identifier)))


def documented_flag_set(flags, identifier):
    out = bytearray(flags)
    out[identifier >> 3] |= documented_flag_mask(identifier)
    return bytes(out)


def execute_flag_query(exe, flags, identifier):
    regs = [0] * 32
    regs[4], regs[29] = identifier, 0x801ff000
    pending = None
    returned = False
    for pc in range(QUERY_START, QUERY_END, 4):
        word = exe.word(pc)
        op, rs, rt, rd = word >> 26, (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
        imm = word & 65535
        signed = imm - 65536 if imm & 32768 else imm
        old_load, pending, write = pending, None, None
        if word == 0:
            pass
        elif word == 0x03e00008:
            returned = True
        elif op == 9:
            write = (rt, (regs[rs] + signed) & 0xffffffff)
        elif op == 12:
            write = (rt, regs[rs] & imm)
        elif op == 15:
            write = (rt, imm << 16)
        elif op == 36:
            offset = ((regs[rs] + signed) & 0xffffffff) - FLAG_BASE
            if not 0 <= offset < len(flags):
                raise ValueError('out-of-range flag read')
            pending = (rt, flags[offset])
        elif op == 0:
            fn = word & 63
            if fn == 2:
                value = regs[rt] >> ((word >> 6) & 31)
            elif fn == 7:
                signed_rt = regs[rt] if regs[rt] < 0x80000000 else regs[rt] - 0x100000000
                value = (signed_rt >> (regs[rs] & 31)) & 0xffffffff
            elif fn == 33:
                value = (regs[rs] + regs[rt]) & 0xffffffff
            elif fn == 36:
                value = regs[rs] & regs[rt]
            elif fn == 43:
                value = int(regs[rs] < regs[rt])
            else:
                raise ValueError('unsupported SPECIAL instruction')
            write = (rd, value)
        else:
            raise ValueError('unsupported instruction')
        if old_load:
            regs[old_load[0]] = old_load[1]
        if write:
            regs[write[0]] = write[1]
        regs[0] = 0
    if not returned or regs[29] != 0x801ff000:
        raise ValueError('return/stack mismatch')
    return regs[2]


def execute_flag_set(exe, flags, identifier):
    """Interpret the set-leaf listing, including the return delay slot.

    Extra opcodes beyond the query leaf are the ones required to OR a mask
    and store the byte. Unsupported original instructions fail loudly.
    """
    regs = [0] * 32
    regs[4], regs[29] = identifier & 0xffffffff, 0x801ff000
    memory = bytearray(flags)
    pending = None
    returned = False
    delay = False
    for pc in range(SET_START, SET_END, 4):
        word = exe.word(pc)
        op, rs, rt, rd = word >> 26, (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
        shamt = (word >> 6) & 31
        fn = word & 63
        imm = word & 65535
        signed = imm - 65536 if imm & 32768 else imm
        old_load, pending, write = pending, None, None
        finishing = delay
        if word == 0:
            pass
        elif word == 0x03e00008:
            returned = True
            delay = True
        elif op == 9:
            write = (rt, (regs[rs] + signed) & 0xffffffff)
        elif op == 12:
            write = (rt, regs[rs] & imm)
        elif op == 13:
            write = (rt, regs[rs] | imm)
        elif op == 15:
            write = (rt, imm << 16)
        elif op in (32, 36):
            offset = ((regs[rs] + signed) & 0xffffffff) - FLAG_BASE
            if not 0 <= offset < len(memory):
                raise ValueError('out-of-range flag read')
            value = memory[offset]
            if op == 32 and value >= 128:
                value = (value - 256) & 0xffffffff
            pending = (rt, value)
        elif op == 40:
            offset = ((regs[rs] + signed) & 0xffffffff) - FLAG_BASE
            if not 0 <= offset < len(memory):
                raise ValueError('out-of-range flag write')
            memory[offset] = regs[rt] & 0xff
        elif op == 0:
            if fn == 0:
                value = (regs[rt] << shamt) & 0xffffffff
            elif fn == 2:
                value = regs[rt] >> shamt
            elif fn == 4:
                value = (regs[rt] << (regs[rs] & 31)) & 0xffffffff
            elif fn == 6:
                value = regs[rt] >> (regs[rs] & 31)
            elif fn == 7:
                signed_rt = regs[rt] if regs[rt] < 0x80000000 else regs[rt] - 0x100000000
                value = (signed_rt >> (regs[rs] & 31)) & 0xffffffff
            elif fn == 33:
                value = (regs[rs] + regs[rt]) & 0xffffffff
            elif fn == 36:
                value = regs[rs] & regs[rt]
            elif fn == 37:
                value = regs[rs] | regs[rt]
            elif fn == 38:
                value = regs[rs] ^ regs[rt]
            elif fn == 43:
                value = int(regs[rs] < regs[rt])
            else:
                raise ValueError('unsupported SPECIAL instruction')
            write = (rd, value)
        else:
            raise ValueError(f'unsupported instruction {word:#x}')
        if old_load:
            regs[old_load[0]] = old_load[1]
        if write:
            regs[write[0]] = write[1]
        regs[0] = 0
        if finishing:
            break
    if not returned or regs[29] != 0x801ff000:
        raise ValueError('return/stack mismatch')
    return bytes(memory)
