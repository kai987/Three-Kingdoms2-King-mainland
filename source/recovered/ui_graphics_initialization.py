"""Independent map-resource and unit-tile services, physical23/24.

These are the three original table/record producers A012/A015/A018. They
retain the caller's stack, flags and mapper requests. They do not upload a
nametable, render a frame, consume a queue, or synthesize a ready flag. ROM
is immutable data; no opcode, control-IR or original-CPU executor is used.
"""
from dataclasses import dataclass
import hashlib
from .battle_nmi_services import BattleNMIServices, NMIRegisters, ServiceCall
from .scene_shared_services import SceneSharedServices

ROM_SHA256 = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
C, Z, N = 1, 2, 128

@dataclass(frozen=True)
class UIGraphicsData:
    rom: bytes

    @classmethod
    def from_rom(cls, rom):
        if hashlib.sha256(rom).hexdigest() != ROM_SHA256:
            raise ValueError('Pinned original ROM required')
        return cls(bytes(rom))

class UIGraphicsInitialization(BattleNMIServices):
    """Real-call adapter for three bounded graphics data services.

    Supply the actual physical23/24 pair, registers and an existing RTS
    frame. ServiceCall ownership is preserved across a real dependency.
    Chunk IDs0..119 and active slots0..19 are the proven data domains.
    """
    FIXED = ()
    LOCAL_ENTRIES = (0xA012, 0xA015, 0xA018, 0xA61C, 0xAEF0, 0xA983, 0xA9A8)

    def __init__(self, memory, data, services=None):
        super().__init__(memory, callbacks=self._resolve_service)
        self.data = data if isinstance(data, UIGraphicsData) else UIGraphicsData.from_rom(data)
        self.shared = SceneSharedServices(memory, self.data.rom, callbacks=services)
        self.external_services = services
        self._call_owner = None

    def _resolve_service(self, call):
        if call.target in self.shared.FIXED:
            result = self.shared(call)
        elif self.external_services is not None:
            result = self.external_services(call)
        else:
            return dict(status='dependency', reason='No independent graphics helper owns the callee')
        if not isinstance(result, dict) or result.get('status') != 'returned':
            return dict(status='dependency', body=result)
        if call.registers.pc != call.return_pc or call.registers.sp != call.expected_sp:
            return dict(status='dependency', reason='Helper has not returned to actual caller PC/SP', body=result)
        return result

    def call(self, pc, target):
        sp = self.registers.sp
        word = pc + 2
        self.push(word >> 8); self.push(word)
        self.registers.pc = target
        if target == 0xA9A8:
            yield from self.ruler_controller()
        else:
            yield ServiceCall(target, pc + 3, 'call', self.registers, self.memory,
                              tuple(self.memory.banks), sp)
        if self.registers.pc != pc + 3 or self.registers.sp != sp:
            raise RuntimeError('Graphics helper has not returned to its actual caller')

    def result(self, status, **extra):
        return dict(super().result(status, **extra), full_NES_frame=False,
                    PPU_upload_completed=False, queue_acknowledged=False)

    def run_entry(self, entry=0xA012, registers=None):
        if entry not in self.LOCAL_ENTRIES:
            raise ValueError('Entry is outside the recovered graphics data closure')
        if self._program is not None:
            raise RuntimeError('A graphics service is pending; resume it first')
        if registers is None:
            raise ValueError('Actual caller registers and RTS frame required')
        if tuple(self.memory.banks[1:3]) != (23, 24):
            raise ValueError('Actual physical23/24 pair required')
        m = self.memory
        if entry in (0xA012, 0xA015, 0xA61C, 0xAEF0) and m[0] >= 120:
            raise ValueError('Proven map chunk IDs are0..119')
        if entry in (0xA018, 0xA983):
            slot = m[0]
            if slot >= 20 or m[0x63C + slot] > 10:
                raise ValueError('Active slot0..19 and displayed hundreds0..10 required')
            ruler = (m[0x507] >> 4) if m[0x628 + slot] & 128 else m[0x507] & 15
            if ruler >= 7:
                raise ValueError('Original ruler ID0..6 required')
        if entry == 0xA9A8 and registers.a & 15 >= 7:
            raise ValueError('Original ruler ID0..6 required')
        methods = {0xA012:self.chunk_resource, 0xA61C:self.chunk_resource,
                   0xA015:self.attribute_resource, 0xAEF0:self.attribute_resource,
                   0xA018:self.unit_tiles, 0xA983:self.unit_tiles,
                   0xA9A8:self.ruler_controller}
        return self._start(methods[entry], registers, 'ui_graphics_data')

    def __call__(self, call):
        if call.target not in self.LOCAL_ENTRIES or tuple(call.entry_banks[1:3]) != (23,24):
            return dict(status='dependency', reason='No graphics data body owns this pair/entry')
        if self._program is not None:
            if self._call_owner is not call:
                return dict(status='dependency', reason='Another caller owns pending graphics')
            result = self.resume()
        else:
            self._call_owner = call
            result = self.run_entry(call.target, call.registers)
        if result['status'] == 'returned':
            self._call_owner = None
            if call.registers.pc != call.return_pc or call.registers.sp != call.expected_sp:
                return dict(status='dependency', reason='Graphics body did not reach actual caller PC/SP')
        return result

    def chunk_resource(self):
        """23A61C..A641: chunk pointer, fixed metatile pointer, data bank."""
        r=self.registers; m=self.memory
        self.a(m[0]); self.push(r.a); self.shift_a('asl'); self.y(r.a)
        self.a(m[0xA642+r.y]); m[0]=r.a
        self.a(m[0xA643+r.y]); m[1]=r.a
        self.a(0x77); m[2]=r.a; self.a(0xF4); m[3]=r.a
        self.a(self.pop()); self.y(r.a); self.a(m[0xA822+r.y]); self.y(r.a)
        yield from self.call(0xA63E,0xF25F)
        self.rts()

    def attribute_resource(self):
        """23AEF0..AF0B: attribute pointer and same chunk data bank."""
        r=self.registers; m=self.memory
        self.a(m[0]); self.push(r.a); self.shift_a('asl'); self.y(r.a)
        self.a(m[0xA732+r.y]); m[0]=r.a
        self.a(m[0xA733+r.y]); m[1]=r.a
        self.a(self.pop()); self.y(r.a); self.a(m[0xA822+r.y]); self.y(r.a)
        yield from self.call(0xAF08,0xF25F)
        self.rts()

    def ruler_controller(self):
        """23A9A8..A9C3: saved chunk/slot pointer, ruler record byte3."""
        r=self.registers; m=self.memory
        self.y(r.a); self.a(m[0]); self.push(r.a)
        self.a(m[1]); self.push(r.a); self.a(r.y)
        yield from self.call(0xA9B2,0xF368)
        self.y(3); self.a(m[(m[0]|m[1]<<8)+r.y]); self.y(r.a)
        self.a(self.pop()); m[1]=r.a; self.a(self.pop()); m[0]=r.a
        self.a(r.y); self.rts()

    def unit_tiles(self):
        """23A983..AAE3: controller/leader/hundreds/affinity four tiles.

        Controller0,1 and all remaining raw values select three tile families.
        Affinity3 deliberately retains each family's original default tiles.
        """
        r=self.registers; m=self.memory
        self.y(m[0]); self.a(r.y); self.push(r.a)
        self.a(m[0x507]); self.push(r.a); self.a(m[0x628+r.y])
        if r.p & N:
            self.a(self.pop())
            for _ in range(4): self.shift_a('lsr')
            self.push(r.a)
        self.a(self.pop()); self.a(r.a&15)
        yield from self.call(0xA99A,0xA9A8)
        self.cmp(r.a,0)
        if r.p & Z:
            self._unit_family_zero()
        else:
            self.cmp(r.a,1)
            if r.p & Z: self._unit_family_one()
            else: self._unit_family_other()
        self.rts()

    def _unit_top(self, first, second, leader, full_first, full_second, compare_a=False):
        r=self.registers; m=self.memory
        self.a(self.pop()); self.y(r.a); self.push(r.a)
        self.a(m[0x63C+r.y]); self.y(r.a)
        self.a(m[first+r.y]); m[0x1B0]=r.a
        self.a(m[second+r.y]); m[0x1B1]=r.a
        self.a(self.pop()); self.y(r.a)
        is_leader = bool(r.p & Z)
        if not is_leader:
            self.cmp(r.a if compare_a else r.y,10)
            is_leader = bool(r.p & Z)
        if is_leader:
            self.a(leader); m[0x1B0]=r.a
            self.a(m[0x63C+r.y]); self.cmp(r.a,10)
            if r.p & Z:
                self.a(full_first); m[0x1B0]=r.a
                self.a(full_second); m[0x1B1]=r.a

    def _unit_bottom(self, default, flat, special, special_affinity):
        r=self.registers; m=self.memory
        self.a(default[0]); m[0x1B2]=r.a; self.a(default[1]); m[0x1B3]=r.a
        self.a(m[0x628+r.y]); self.a(r.a&3)
        if r.p & Z:
            self.a(flat[0]); m[0x1B2]=r.a; self.a(flat[1]); m[0x1B3]=r.a
        self.a(m[0x628+r.y]); self.a(r.a&3); self.cmp(r.a,special_affinity)
        if r.p & Z:
            self.a(special[0]); m[0x1B2]=r.a; self.a(special[1]); m[0x1B3]=r.a

    def _unit_family_zero(self):
        self._unit_top(0xAAE4,0xAAEF,0xBB,0xBA,0xAB,True)
        self._unit_bottom((0xAE,0xAF),(0xBD,0xBE),(0xAC,0xAD),1)

    def _unit_family_one(self):
        self._unit_top(0xAAFA,0xAB05,0xB1,0xB0,0x8B)
        self._unit_bottom((0x8C,0x8D),(0xB3,0xB4),(0x8E,0x8F),2)

    def _unit_family_other(self):
        self._unit_top(0xAB10,0xAB1B,0xB6,0xB5,0x9B)
        self._unit_bottom((0x9C,0x9D),(0xB8,0xB9),(0x9E,0x9F),2)
