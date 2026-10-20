"""Small recovered fixed-bank helpers for the lifted scene controllers.

These preserve register, flag, scratch and stack effects. They do not execute
original ROM instructions. Other dependencies are delegated explicitly.
"""
C, Z, V, N = 1, 2, 64, 128


class MissingSharedHelper(RuntimeError):
    pass


class ControlHelpers:
    def __init__(self, fallback=None):
        self.fallback = fallback

    def __call__(self, context, target, return_pc, kind):
        r, memory = context.registers, context.memory
        if target == 0xEADE and kind == 'dispatch':
            # Bank31 EADE..EAF4. The lifted table has already checked the index
            # and supplied its target. EADE removes its own JSR return address.
            original_y = r.y
            memory[0] = original_y
            pointer_base = context.pop() | context.pop() << 8
            memory[1], memory[2] = pointer_base & 255, pointer_base >> 8
            memory[3], memory[4] = return_pc & 255, return_pc >> 8
            carry = C if r.a & 128 else 0
            r.a, r.y, r.pc = return_pc >> 8, original_y, return_pc
            r.p = (r.p & ~(C | N | Z)) | carry | (N if original_y & 128 else 0) | (Z if original_y == 0 else 0)
            return
        if target == 0xF2D7:
            # Bank31 F2D7..F307. The parameter is one byte, including the
            # out-of-domain IDs237..255: address is $63C0 + 12*A.
            officer_id = r.a
            address = 0x63C0 + 12*officer_id
            # Preserve the PHA/PLA's RAM write even though its final SP cancels.
            context.push((3*officer_id) & 255)
            context.pop()
            memory[0], memory[1] = address & 255, address >> 8
            r.a, r.y = address >> 8, 0
            # Final ADC #$63 is nonzero, positive, with no carry or overflow
            # for all256 byte inputs; other flags survive.
            r.p &= ~(C | Z | V | N)
            r.pc = ((context.pop() | context.pop() << 8)+1) & 65535
            return
        if target in (0xE87A,0xE88A,0xE89A,0xE8AA):
            # Fixed-bank permutation RNG. The final LDX restores X and sets
            # NZ from X, rather than from the sampled byte returned in A.
            cursor, scratch = {0xE87A:(0x50,0x51),0xE88A:(0x52,0x53),
                               0xE89A:(0x54,0x53),0xE8AA:(0x55,0x53)}[target]
            memory[scratch] = r.x
            r.a = memory[0xE8BA+memory[cursor]]
            memory[cursor] = (memory[cursor]+1) & 255
            r.p = (r.p & ~(N|Z)) | (N if r.x&128 else 0) | (Z if r.x==0 else 0)
            r.pc = ((context.pop() | context.pop() << 8)+1) & 65535
            return
        if self.fallback is not None:
            return self.fallback(context, target, return_pc, kind)
        raise MissingSharedHelper(f'Unrecovered {kind} helper ${target:04X}')
