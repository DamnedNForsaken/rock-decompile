"""Execute the bit-query leaf with its original load delay and return slot."""
def execute_flag_query(exe, flags, identifier):
    regs = [0] * 32
    regs[4], regs[29] = identifier, 0x801ff000
    pending = None
    returned = False
    for pc in range(0x8001da58, 0x8001da8c, 4):
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
            offset = ((regs[rs] + signed) & 0xffffffff) - 0x800be378
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
