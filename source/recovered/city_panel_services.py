"""Readable, bounded bank25/26 city and ruler panel services.

Offline control-flow structuring produced named procedures and phase handlers.
Production reads immutable game data, never opcodes, control IR or PC->operation
tables. Services retain their real caller stack and explicit pending boundary.
CPU-register form is retained where flags/scratch/aliasing are observable.
"""
from dataclasses import dataclass
import hashlib
from .battle_nmi_services import ServiceCall, ServiceWait
from .mapped_memory import UnsupportedHardware

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
C,Z,I,D,B,U,V,N=1,2,4,8,16,32,64,128
STATE=0x400
PHASE=0x401
CITY=0x402
OFFICER_LIST=0x410
OFFICER_INDEX=0x40C
DETAIL_ROW=0x40D
WORLD_CURSOR=0x470
CURRENT_CITY=0x471
NEW_BUTTONS=0x81
REPEAT_BUTTONS=0x87
GLOBAL=0x7A
NMI_SCENE=0x78
PPU_JOBS=0x7E
ACTOR_SLOT=OFFICER_INDEX

@dataclass
class CityPanelRegisters:
    a:int=0
    x:int=0
    y:int=0
    sp:int=0xFD
    p:int=U
    pc:int=0xA02A

class _ContinueLoop_A041(Exception):pass
class _ContinueLoop_A1A9(Exception):pass
class _ContinueLoop_A42B(Exception):pass
class _ContinueLoop_A5F0(Exception):pass
class _ContinueLoop_A7DF(Exception):pass
class _ContinueLoop_A89A(Exception):pass
class _ContinueLoop_A8A5(Exception):pass
class _ContinueLoop_A91A(Exception):pass
class _ContinueLoop_AB3D(Exception):pass
class _ContinueLoop_AB47(Exception):pass
class _ContinueLoop_ABDC(Exception):pass
class _ContinueLoop_AEF0(Exception):pass
class _ContinueLoop_AF2A(Exception):pass
class _ContinueLoop_B7E3(Exception):pass
class _ContinueLoop_B812(Exception):pass
class _ContinueLoop_B829(Exception):pass
class _ContinueLoop_B880(Exception):pass
class _ContinueLoop_B995(Exception):pass
class _ContinueLoop_B9CE(Exception):pass
class _ContinueLoop_B9F8(Exception):pass
class _ContinueLoop_BA0E(Exception):pass
class _ContinueLoop_BA40(Exception):pass
class _ContinueLoop_BA82(Exception):pass
class _ContinueLoop_BB0B(Exception):pass
class _ContinueLoop_BC2C(Exception):pass
class _ContinueLoop_BC2E(Exception):pass
class _ContinueLoop_BC53(Exception):pass
class _ContinueLoop_BC95(Exception):pass
class _ContinueLoop_BCB7(Exception):pass
class _ContinueLoop_BCF4(Exception):pass
class _ContinueLoop_BD8A(Exception):pass
class _ContinueLoop_BD9C(Exception):pass
class _ContinueLoop_BDAF(Exception):pass
class _ContinueLoop_BDE7(Exception):pass
class _ContinueLoop_BE48(Exception):pass
class _ContinueLoop_BFDE(Exception):pass
class _ContinueLoop_C01E(Exception):pass
class _ContinueLoop_C03E(Exception):pass
class _ContinueLoop_C0AB(Exception):pass
class _ContinueLoop_C0C1(Exception):pass
class _ContinueLoop_C10F(Exception):pass
class _ContinueLoop_C17B(Exception):pass
class _ContinueLoop_C1A3(Exception):pass
class _ContinueLoop_C1B7(Exception):pass
class _ContinueLoop_C1E5(Exception):pass
class _ContinueLoop_C22E(Exception):pass
class _ContinueLoop_C2AB(Exception):pass
class _ContinueLoop_C2CD(Exception):pass
class _ContinueLoop_C32C(Exception):pass
class _ContinueLoop_C459(Exception):pass
class _ContinueLoop_C47E(Exception):pass
class _ContinueLoop_C62E(Exception):pass
class _ContinueLoop_C654(Exception):pass
class _ContinueLoop_C71B(Exception):pass

class CityPanelServices:
    def __init__(self,memory,rom,services=None):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned original UI ROM required')
        self.memory=memory;self.rom=bytes(rom);self.services=services
        self.registers=CityPanelRegisters();self.events=[];self.pending=None;self._program=None
        self._blocks=0;self._limit=200000;self._call_owner=None
    def _nz(self,value):
        value&=255;self.registers.p=(self.registers.p&~(N|Z))|(N if value&128 else 0)|(Z if value==0 else 0)
        return value
    def _a(self,value):self.registers.a=self._nz(value)
    def _x(self,value):self.registers.x=self._nz(value)
    def _y(self,value):self.registers.y=self._nz(value)
    def _flag(self,bit,value):self.registers.p=(self.registers.p&~bit)|(bit if value else 0)
    def _compare(self,left,right):self._flag(C,left>=right);self._nz(left-right)
    def _add(self,value,subtract=False):
        r=self.registers;old=r.a;carry=bool(r.p&C)
        total=old-value-(1-carry)if subtract else old+value+carry
        self._flag(C,total>=0 if subtract else total>255)
        self._flag(V, bool(((old^value)&(old^total)&128)if subtract else (~(old^value)&(old^total)&128)))
        self._a(total)
    def _shift(self,value,left,rotate=False):
        carry=bool(self.registers.p&C);self._flag(C,value&128 if left else value&1)
        return self._nz(((value<<1)|(carry if rotate else 0))if left else ((value>>1)|(128 if rotate and carry else 0)))
    def _push(self,value):
        r=self.registers;self.memory[0x100+r.sp]=value&255;r.sp=(r.sp-1)&255
    def _pop(self):
        r=self.registers;r.sp=(r.sp+1)&255;return self.memory[0x100+r.sp]
    def _rts(self):self.registers.pc=((self._pop()|self._pop()<<8)+1)&65535
    def _local_call(self,method,pc,return_pc):
        self._push((pc+2)>>8);self._push(pc+2)
        yield from method()
        return self.registers.pc==return_pc
    def _mark(self,pc):
        self.registers.pc=pc;self._blocks+=1
        if self._blocks>self._limit:raise RuntimeError('Source control-block budget reached')
    def _dispatch(self,pc,targets):
        r=self.registers;m=self.memory;index=r.a
        if index>=len(targets):raise ValueError(f'Original bounded dispatch index {index} at ${pc:04X}')
        self._push((pc+2)>>8);self._push(pc+2)
        original_y=r.y;m[0]=original_y;base=self._pop()|self._pop()<<8
        m[1],m[2]=base&255,base>>8;target=targets[index];m[3],m[4]=target&255,target>>8
        r.a=target>>8;r.y=original_y;r.pc=target
        r.p=(r.p&~(C|N|Z))|(C if index&128 else 0)|(N if original_y&128 else 0)|(Z if original_y==0 else 0)
        return index
    def _external(self,pc,target,return_pc,kind,inline_target=None):
        r=self.registers;caller_sp=r.sp
        if kind!='tail':self._push((pc+2)>>8);self._push(pc+2)
        else:caller_sp=(r.sp+2)&255
        r.pc=target
        if return_pc is None:return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535
        event=dict(call_pc=pc,target=target,return_pc=return_pc,kind=kind,inline_target=inline_target)
        self.events.append(event)
        yield ServiceCall(target,return_pc,kind,r,self.memory,tuple(getattr(self.memory,'banks',())),caller_sp)
    def _drive(self):
        while True:
            if self.pending is not None:
                call=self.pending
                if self.services is None:return self._result('dependency')
                result=self.services(call)
                if not isinstance(result,dict)or result.get('status')!='returned':return self._result('dependency')
                if self.registers.pc!=call.return_pc or self.registers.sp!=call.expected_sp:return self._result('dependency')
                self.pending=None
            try:self.pending=next(self._program)
            except StopIteration:
                self._program=None
                if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:return self._result('nonlocal_return')
                return self._result('returned')
    def _result(self,status):
        return dict(status=status,before=self._before,after=(self.memory[STATE],self.memory[PHASE],self.memory[ACTOR_SLOT]),
                    control_blocks=self._blocks,events=list(self.events),pending=self.pending)
    def resume(self):
        if self._program is None:raise RuntimeError('No pending battle invocation')
        return self._drive()
    def tick(self,registers=None,**kwargs):return self.run_entry(0xA02A,registers=registers,**kwargs)
    def run_entry(self,entry=0xA02A,*,registers=None,seed_return=False,return_pc=None,max_blocks=200000):
        if self._program is not None:raise RuntimeError('Resume the existing battle invocation first')
        if registers is None:raise ValueError('Supply actual caller registers and an existing RTS frame')
        self.registers=registers;r=self.registers
        if r.p&D:raise ValueError('NES binary arithmetic requires D=0')
        if seed_return:
            if return_pc not in(None,0x0200):raise ValueError('Synthetic fixture return only permits0200')
            self.memory[0x1FE:0x200]=bytes((255,1));r.sp=0xFD
        self._return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535 if return_pc is None else return_pc;self._return_sp=(r.sp+2)&255;self._before=(self.memory[STATE],self.memory[PHASE],self.memory[ACTOR_SLOT])
        self.events=[];self.pending=None;self._blocks=0;self._limit=max_blocks;r.pc=entry
        self._program=self._entry(entry)
        return self._drive()

    def __call__(self,call):
        if tuple(call.entry_banks[1:3])!=(25,26)or call.target not in self.LOCAL_ENTRIES:
            return {'status':'dependency','reason':'No independent panel owns this exact pair/entry'}
        if self._program is not None:
            if self._call_owner is not call:return {'status':'dependency','reason':'Another caller owns this pending panel'}
            return self.resume()
        self._call_owner=call
        return self.run_entry(call.target,registers=call.registers,return_pc=call.return_pc)

    LOCAL_ENTRIES=(40963, 40966, 40969, 40972, 40981, 40984, 40987, 40990, 40996, 40999, 41002, 41005, 41008, 41011, 41014, 41025, 41260, 41310, 41350, 41375, 41410, 41451, 41481, 41536, 41622, 41625, 41660, 41740, 41788, 41827, 41865, 41883, 41957, 41960, 41969, 41988, 42016, 42025, 42282, 42304, 42370, 42410, 42413, 42422, 42441, 42469, 42478, 42735, 42738, 42749, 42784, 42817, 43103, 43158, 43232, 43326, 43397, 43424, 43427, 43438, 43473, 43506, 43742, 43797, 43800, 43813, 43945, 44109, 44186, 44221, 44237, 44265, 44308, 44351, 44417, 44420, 44437, 44458, 44557, 44625, 44736, 44739, 44750, 44916, 44939, 44984, 47065, 47193, 47225, 47319, 47432, 47460, 47728, 47875, 47987, 48094, 48103, 48130, 48256, 48259, 48268, 48277, 48424, 48487, 48518, 48571, 48641, 48644, 48663, 48686, 48771, 48849, 48943, 49081, 49182, 49381, 49409, 49458, 49461, 49476, 49496, 49569, 49627, 49693, 49757, 49792, 49801, 49944, 50042, 50045, 50054, 50114, 50206, 50229, 50232, 50241, 50586, 50617, 50655, 50726, 50758, 50812, 50952, 51059, 51062, 51099, 51168, 51666, 51714, 51727, 51754, 51778, 51844, 51924, 52015, 52095, 52125, 52163, 52182, 52189, 52234, 52262, 52281, 52288, 52333, 52361, 52364, 52373, 52440, 52563, 52591, 52620)
    def _entry(self,entry):
        if entry==0xA003:return self.ruler_panel_entry()
        elif entry==0xA006:return self.city_c773_entry()
        elif entry==0xA009:return self.city_a296_entry()
        elif entry==0xA00C:return self.city_ad81_entry()
        elif entry==0xA015:return self.city_b7d9_entry()
        elif entry==0xA018:return self.city_b8d7_entry()
        elif entry==0xA01B:return self.new_officer_event_entry()
        elif entry==0xA01E:return self.city_c435_entry()
        elif entry==0xA024:return self.city_ba70_entry()
        elif entry==0xA027:return self.city_bb03_entry()
        elif entry==0xA02A:return self.calendar_header_entry()
        elif entry==0xA02D:return self.city_bc02_entry()
        elif entry==0xA030:return self.city_bb73_entry()
        elif entry==0xA033:return self.ruler_panel()
        elif entry==0xA036:return self.panel_helper_a036()
        elif entry==0xA041:return self.panel_helper_a041()
        elif entry==0xA12C:return self.panel_helper_a12c()
        elif entry==0xA15E:return self.panel_helper_a15e()
        elif entry==0xA186:return self.panel_helper_a186()
        elif entry==0xA19F:return self.panel_helper_a19f()
        elif entry==0xA1C2:return self.panel_helper_a1c2()
        elif entry==0xA1EB:return self.find_officer_city()
        elif entry==0xA209:return self.decrement_ruler_counter_nibbles()
        elif entry==0xA240:return self.count_available_nonrulers()
        elif entry==0xA296:return self.panel_helper_a296()
        elif entry==0xA299:return self.panel_helper_a299()
        elif entry==0xA2BC:return self.panel_helper_a2bc()
        elif entry==0xA30C:return self.panel_helper_a30c()
        elif entry==0xA33C:return self.panel_helper_a33c()
        elif entry==0xA363:return self.panel_helper_a363()
        elif entry==0xA389:return self.panel_helper_a389()
        elif entry==0xA39B:return self.panel_helper_a39b()
        elif entry==0xA3E5:return self.panel_helper_a3e5()
        elif entry==0xA3E8:return self.panel_helper_a3e8()
        elif entry==0xA3F1:return self.panel_helper_a3f1()
        elif entry==0xA404:return self.panel_helper_a404()
        elif entry==0xA420:return self.panel_helper_a420()
        elif entry==0xA429:return self.panel_helper_a429()
        elif entry==0xA52A:return self.panel_helper_a52a()
        elif entry==0xA540:return self.panel_helper_a540()
        elif entry==0xA582:return self.panel_helper_a582()
        elif entry==0xA5AA:return self.panel_helper_a5aa()
        elif entry==0xA5AD:return self.panel_helper_a5ad()
        elif entry==0xA5B6:return self.panel_helper_a5b6()
        elif entry==0xA5C9:return self.panel_helper_a5c9()
        elif entry==0xA5E5:return self.panel_helper_a5e5()
        elif entry==0xA5EE:return self.panel_helper_a5ee()
        elif entry==0xA6EF:return self.panel_helper_a6ef()
        elif entry==0xA6F2:return self.panel_helper_a6f2()
        elif entry==0xA6FD:return self.panel_helper_a6fd()
        elif entry==0xA720:return self.panel_helper_a720()
        elif entry==0xA741:return self.panel_helper_a741()
        elif entry==0xA85F:return self.panel_helper_a85f()
        elif entry==0xA896:return self.panel_helper_a896()
        elif entry==0xA8E0:return self.panel_helper_a8e0()
        elif entry==0xA93E:return self.panel_helper_a93e()
        elif entry==0xA985:return self.panel_helper_a985()
        elif entry==0xA9A0:return self.panel_helper_a9a0()
        elif entry==0xA9A3:return self.panel_helper_a9a3()
        elif entry==0xA9AE:return self.panel_helper_a9ae()
        elif entry==0xA9D1:return self.panel_helper_a9d1()
        elif entry==0xA9F2:return self.panel_helper_a9f2()
        elif entry==0xAADE:return self.panel_helper_aade()
        elif entry==0xAB15:return self.panel_helper_ab15()
        elif entry==0xAB18:return self.panel_helper_ab18()
        elif entry==0xAB25:return self.panel_helper_ab25()
        elif entry==0xABA9:return self.panel_helper_aba9()
        elif entry==0xAC4D:return self.panel_helper_ac4d()
        elif entry==0xAC9A:return self.panel_helper_ac9a()
        elif entry==0xACBD:return self.panel_helper_acbd()
        elif entry==0xACCD:return self.panel_helper_accd()
        elif entry==0xACE9:return self.panel_helper_ace9()
        elif entry==0xAD14:return self.panel_helper_ad14()
        elif entry==0xAD3F:return self.panel_helper_ad3f()
        elif entry==0xAD81:return self.panel_helper_ad81()
        elif entry==0xAD84:return self.panel_helper_ad84()
        elif entry==0xAD95:return self.panel_helper_ad95()
        elif entry==0xADAA:return self.panel_helper_adaa()
        elif entry==0xAE0D:return self.panel_helper_ae0d()
        elif entry==0xAE51:return self.panel_helper_ae51()
        elif entry==0xAEC0:return self.panel_helper_aec0()
        elif entry==0xAEC3:return self.panel_helper_aec3()
        elif entry==0xAECE:return self.panel_helper_aece()
        elif entry==0xAF74:return self.panel_helper_af74()
        elif entry==0xAF8B:return self.panel_helper_af8b()
        elif entry==0xAFB8:return self.panel_helper_afb8()
        elif entry==0xB7D9:return self.prepare_battle_departure()
        elif entry==0xB859:return self.remove_departing_roster_ids()
        elif entry==0xB879:return self.compact_departure_city_roster()
        elif entry==0xB8D7:return self.panel_helper_b8d7()
        elif entry==0xB948:return self.panel_helper_b948()
        elif entry==0xB964:return self.new_officer_event()
        elif entry==0xBA70:return self.panel_helper_ba70()
        elif entry==0xBB03:return self.panel_helper_bb03()
        elif entry==0xBB73:return self.panel_helper_bb73()
        elif entry==0xBBDE:return self.calendar_header()
        elif entry==0xBBE7:return self.panel_helper_bbe7()
        elif entry==0xBC02:return self.panel_helper_bc02()
        elif entry==0xBC80:return self.panel_helper_bc80()
        elif entry==0xBC83:return self.panel_helper_bc83()
        elif entry==0xBC8C:return self.panel_helper_bc8c()
        elif entry==0xBC95:return self.panel_helper_bc95()
        elif entry==0xBD28:return self.panel_helper_bd28()
        elif entry==0xBD67:return self.panel_helper_bd67()
        elif entry==0xBD86:return self.panel_helper_bd86()
        elif entry==0xBDBB:return self.panel_helper_bdbb()
        elif entry==0xBE01:return self.panel_helper_be01()
        elif entry==0xBE04:return self.panel_helper_be04()
        elif entry==0xBE17:return self.panel_helper_be17()
        elif entry==0xBE2E:return self.panel_helper_be2e()
        elif entry==0xBE83:return self.panel_helper_be83()
        elif entry==0xBED1:return self.panel_helper_bed1()
        elif entry==0xBF2F:return self.panel_helper_bf2f()
        elif entry==0xBFB9:return self.panel_helper_bfb9()
        elif entry==0xC01E:return self.panel_helper_c01e()
        elif entry==0xC0E5:return self.panel_helper_c0e5()
        elif entry==0xC101:return self.panel_helper_c101()
        elif entry==0xC132:return self.panel_helper_c132()
        elif entry==0xC135:return self.panel_helper_c135()
        elif entry==0xC144:return self.panel_helper_c144()
        elif entry==0xC158:return self.panel_helper_c158()
        elif entry==0xC1A1:return self.panel_helper_c1a1()
        elif entry==0xC1DB:return self.panel_helper_c1db()
        elif entry==0xC21D:return self.panel_helper_c21d()
        elif entry==0xC25D:return self.panel_helper_c25d()
        elif entry==0xC280:return self.panel_helper_c280()
        elif entry==0xC289:return self.panel_helper_c289()
        elif entry==0xC318:return self.panel_helper_c318()
        elif entry==0xC37A:return self.panel_helper_c37a()
        elif entry==0xC37D:return self.panel_helper_c37d()
        elif entry==0xC386:return self.panel_helper_c386()
        elif entry==0xC3C2:return self.panel_helper_c3c2()
        elif entry==0xC41E:return self.panel_helper_c41e()
        elif entry==0xC435:return self.panel_helper_c435()
        elif entry==0xC438:return self.panel_helper_c438()
        elif entry==0xC441:return self.panel_helper_c441()
        elif entry==0xC59A:return self.panel_helper_c59a()
        elif entry==0xC5B9:return self.panel_helper_c5b9()
        elif entry==0xC5DF:return self.panel_helper_c5df()
        elif entry==0xC626:return self.panel_helper_c626()
        elif entry==0xC646:return self.panel_helper_c646()
        elif entry==0xC67C:return self.panel_helper_c67c()
        elif entry==0xC708:return self.panel_helper_c708()
        elif entry==0xC773:return self.panel_helper_c773()
        elif entry==0xC776:return self.panel_helper_c776()
        elif entry==0xC79B:return self.panel_helper_c79b()
        elif entry==0xC7E0:return self.panel_helper_c7e0()
        elif entry==0xC9D2:return self.panel_helper_c9d2()
        elif entry==0xCA02:return self.panel_helper_ca02()
        elif entry==0xCA0F:return self.panel_helper_ca0f()
        elif entry==0xCA2A:return self.panel_helper_ca2a()
        elif entry==0xCA42:return self.panel_helper_ca42()
        elif entry==0xCA84:return self.panel_helper_ca84()
        elif entry==0xCAD4:return self.panel_helper_cad4()
        elif entry==0xCB2F:return self.panel_helper_cb2f()
        elif entry==0xCB7F:return self.panel_helper_cb7f()
        elif entry==0xCB9D:return self.panel_helper_cb9d()
        elif entry==0xCBC3:return self.panel_helper_cbc3()
        elif entry==0xCBD6:return self.panel_helper_cbd6()
        elif entry==0xCBDD:return self.panel_helper_cbdd()
        elif entry==0xCC0A:return self.panel_helper_cc0a()
        elif entry==0xCC26:return self.panel_helper_cc26()
        elif entry==0xCC39:return self.panel_helper_cc39()
        elif entry==0xCC40:return self.panel_helper_cc40()
        elif entry==0xCC6D:return self.panel_helper_cc6d()
        elif entry==0xCC89:return self.panel_helper_cc89()
        elif entry==0xCC8C:return self.panel_helper_cc8c()
        elif entry==0xCC95:return self.panel_helper_cc95()
        elif entry==0xCCD8:return self.panel_helper_ccd8()
        elif entry==0xCD53:return self.panel_helper_cd53()
        elif entry==0xCD6F:return self.panel_helper_cd6f()
        elif entry==0xCD8C:return self.panel_helper_cd8c()
        raise ValueError("Entry outside original city panel closure")

    def ruler_panel_entry(self):
        """$A003: ruler panel entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA003)
        return (yield from self.ruler_panel())

    def city_c773_entry(self):
        """$A006: city c773 entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA006)
        return (yield from self.panel_helper_c773())

    def city_a296_entry(self):
        """$A009: city a296 entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA009)
        return (yield from self.panel_helper_a296())

    def city_ad81_entry(self):
        """$A00C: city ad81 entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA00C)
        return (yield from self.panel_helper_ad81())

    def city_b7d9_entry(self):
        """$A015: city b7d9 entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA015)
        return (yield from self.prepare_battle_departure())

    def city_b8d7_entry(self):
        """$A018: city b8d7 entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA018)
        return (yield from self.panel_helper_b8d7())

    def new_officer_event_entry(self):
        """$A01B: new officer event entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA01B)
        return (yield from self.new_officer_event())

    def city_c435_entry(self):
        """$A01E: city c435 entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA01E)
        return (yield from self.panel_helper_c435())

    def city_ba70_entry(self):
        """$A024: city ba70 entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA024)
        return (yield from self.panel_helper_ba70())

    def city_bb03_entry(self):
        """$A027: city bb03 entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA027)
        return (yield from self.panel_helper_bb03())

    def calendar_header_entry(self):
        """$A02A: calendar header entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA02A)
        return (yield from self.calendar_header())

    def city_bc02_entry(self):
        """$A02D: city bc02 entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA02D)
        return (yield from self.panel_helper_bc02())

    def city_bb73_entry(self):
        """$A030: city bb73 entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA030)
        return (yield from self.panel_helper_bb73())

    def ruler_panel(self):
        """$A033: ruler panel; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA033)
        self._a(m[PHASE])
        return (yield from self.panel_helper_a036())

    def panel_helper_a036(self):
        """$A036: panel helper a036; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA036)
        index=self._dispatch(0xA036,(41025, 41260, 41310, 41350))
        return (yield from (self.panel_helper_a041,self.panel_helper_a12c,self.panel_helper_a15e,self.panel_helper_a186,)[index]())

    def panel_helper_a041(self):
        """$A041: panel helper a041; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        while True:  # natural loop $A041
            try:
                self._mark(0xA041)
                self._a(0xF0)
                m[0x6F41]=r.a
                m[0x6F04]=self._nz(m[0x6F04]+1)
                self._a(m[0x6F04])
                self._compare(r.a,0x07)
                self._mark(0xA04E)
                if not r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[0x6F04]=r.a
                    m[0x6F06]=r.a
                    self._y(m[0x6F01])
                    self._y(r.y+1)
                    self._compare(r.y,0x0C)
                    self._mark(0xA05E)
                    if not r.p&C:
                        pass
                    else:
                        self._y(0x00)
                        m[0x6F00]=self._nz(m[0x6F00]+1)
                        pass
                    m[0x6F01]=r.y
                    if not (yield from self._local_call(self.decrement_ruler_counter_nibbles,0xA068,0xA06B)):return
                    pass
                self._a(m[0x6F45])
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._a(r.a | m[0x6F04])
                self._y(r.a)
                self._a(m[(0xA104+r.y)&65535])
                m[0x6F03]=r.a
                r.a=self._shift(r.a,True,rotate=False)
                self._y(r.a)
                self._a(m[(0xA0D6+r.y)&65535])
                m[0x00EE]=r.a
                self._a(m[(0xA0D7+r.y)&65535])
                m[0x00EF]=r.a
                self._y(0x00)
                self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xA08F)
                if r.p&Z:
                    continue
                else:
                    pass
                if not (yield from self._local_call(self.count_available_nonrulers,0xA091,0xA094)):return
                self._a(m[0x0011])
                self._compare(r.a,0x1E)
                self._mark(0xA099)
                if r.p&C:
                    self._a(m[0x6F03])
                    self._a(r.a & 0x07)
                    if not (yield from self._local_call(self.panel_helper_a19f,0xA0AA,0xA0AD)):return
                    self._y(m[0x0003])
                    self._a(m[(0xA0E4+r.y)&65535])
                    m[0x6F05]=r.a
                    self._y(0x3D)
                    yield from self._external(0xA0B8,0xEE07,0xA0BD,"far_call",40990)
                    if r.pc!=0xA0BD:return  # preserve nonlocal stack return
                    self._y(0x00)
                    self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
                    m[0x000A]=r.a
                    if not (yield from self._local_call(self.find_officer_city,0xA0C4,0xA0C7)):return
                    self._y(0x01)
                    m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535]=r.a
                    self._a(0x0A)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._mark(0xA0D5)
                    self._rts();return
                else:
                    self._a(0x03)
                    m[PHASE]=r.a
                    self._a(0xD5)
                    self._mark(0xA0A2)
                    yield from self._external(0xA0A2,0xF28B,None,"tail")
                    return
            except _ContinueLoop_A041:
                continue

    def panel_helper_a12c(self):
        """$A12C: panel helper a12c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA12C)
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(0x20)
        yield from self._external(0xA131,0xF28B,0xA134,"call",None)
        if r.pc!=0xA134:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
        m[0x042C]=r.a
        self._a(m[0x6F05])
        m[0x042F]=r.a
        self._a(0x00)
        m[0x0430]=r.a
        m[0x0431]=r.a
        self._y(0x01)
        self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
        self._y(r.a)
        self._a(m[(0xC737+r.y)&65535])
        m[0x6F3F]=r.a
        self._a(m[(0xC755+r.y)&65535])
        self._flag(C,False)
        self._add(0x01)
        m[0x6F41]=r.a
        self._mark(0xA15D)
        self._rts();return

    def panel_helper_a15e(self):
        """$A15E: panel helper a15e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA15E)
        self._y(0x3D)
        yield from self._external(0xA160,0xEE07,0xA165,"far_call",40993)
        if r.pc!=0xA165:return  # preserve nonlocal stack return
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xA16A)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xA171)
            if not r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xA173,0xA176)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x01)
                self._mark(0xA17B)
                if r.p&Z:
                    pass
                else:
                    self._a(0x00)
                    m[STATE]=r.a
                    m[PHASE]=r.a
                    pass
                pass
            pass
        self._mark(0xA185)
        self._rts();return

    def panel_helper_a186(self):
        """$A186: panel helper a186; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA186)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xA18B)
        if not r.p&Z:
            self._mark(0xA19E)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xA192)
            if not r.p&Z:
                self._mark(0xA19E)
                self._rts();return
            else:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x01)
                self._mark(0xA199)
                if r.p&Z:
                    self._mark(0xA19E)
                    self._rts();return
                else:
                    self._mark(0xA19B)
                    yield from self._external(0xA19B,0xE000,None,"tail")
                    return

    def panel_helper_a19f(self):
        """$A19F: panel helper a19f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA19F)
        m[0x0002]=r.a
        self._a(0x00)
        m[0x0003]=r.a
        self._a(0x1D)
        while True:  # natural loop $A1A9
            try:
                self._push(r.a)
                yield from self._external(0xA1AA,0xF2AF,0xA1AD,"call",None)
                if r.pc!=0xA1AD:return  # preserve nonlocal stack return
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0x0F)
                self._compare(r.a,m[0x0002])
                self._mark(0xA1B6)
                if not r.p&Z:
                    pass
                else:
                    m[0x0003]=self._nz(m[0x0003]+1)
                    pass
                self._a(self._pop())
                self._flag(C,True)
                self._add(0x01,subtract=True)
                self._mark(0xA1BF)
                if not r.p&N:
                    continue
                else:
                    pass
                self._mark(0xA1C1)
                self._rts();return
            except _ContinueLoop_A1A9:
                continue

    def panel_helper_a1c2(self):
        """$A1C2: panel helper a1c2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA1C2)
        self._a(m[0x005E])
        self._a(r.a & 0x10)
        self._mark(0xA1C7)
        if not r.p&Z:
            self._mark(0xA1E5)
            self._rts();return
        else:
            self._a(0xD8)
            m[0x000A]=r.a
            self._a(0xA0)
            m[0x000C]=r.a
            self._a(0xE6)
            m[0x0000]=r.a
            self._a(0xA1)
            m[0x0001]=r.a
            self._a(0x00)
            m[0x0002]=r.a
            self._mark(0xA1E2)
            yield from self._external(0xA1E2,0xF1AD,None,"tail")
            return

    def find_officer_city(self):
        """A1EB..A208: scan30 cities' ten roster slots for000A; zero if absent."""
        r=self.registers;m=self.memory;self._x(0)
        while True:
            self._mark(0xA1ED);self._a(r.x);yield from self._external(0xA1EE,0xF2AF,0xA1F1,'call')
            if r.pc!=0xA1F1:return
            self._y(17)
            while True:
                self._mark(0xA1F3);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,m[0xA])
                if r.p&Z:self._a(r.x);self._rts();return
                self._y(r.y+1);self._compare(r.y,27)
                if r.p&C:break
            self._x(r.x+1);self._compare(r.x,30)
            if r.p&C:break
        self._a(0);self._rts();return

    def decrement_ruler_counter_nibbles(self):
        """A209..A23F: seven ruler records, four bytes; each nonzero nibble decays."""
        r=self.registers;m=self.memory;self._a(0);m[2]=r.a
        while True:
            self._mark(0xA20E);self._a(m[2]);yield from self._external(0xA211,0xF368,0xA214,'call')
            if r.pc!=0xA214:return
            self._y(4)
            while True:
                self._mark(0xA216);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._a(r.a&15)
                if not r.p&Z:
                    self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._flag(C,True);self._add(1,subtract=True)
                    m[((m[0]|m[1]<<8)+r.y)&65535]=r.a
                self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._a(r.a&240)
                if not r.p&Z:
                    self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._flag(C,True);self._add(16,subtract=True)
                    m[((m[0]|m[1]<<8)+r.y)&65535]=r.a
                self._y(r.y+1);self._compare(r.y,8)
                if r.p&C:break
            m[2]=self._nz(m[2]+1);self._a(m[2]);self._compare(r.a,7)
            if r.p&C:break
        self._rts();return

    def count_available_nonrulers(self):
        """A240..A295: copy seven ruler IDs; count nonrulers whose low state bits are not3."""
        r=self.registers;m=self.memory;self._y(49);yield from self._external(0xA242,0xF25F,0xA245,'call')
        if r.pc!=0xA245:return
        self._y(0);self._x(0)
        while True:
            self._mark(0xA249);self._a(m[(0x6F07+r.y)&65535]);m[(0x42C+r.x)&65535]=r.a
            self._x(r.x+1);self._a(r.x)
            for _ in range(3):r.a=self._shift(r.a,True)
            self._y(r.a);self._compare(r.x,7)
            if r.p&C:break
        self._x(m[0x6F03]);self._a(255);m[(0x42C+r.x)&65535]=r.a
        self._a(0);m[0x10]=m[0x11]=r.a
        while True:
            self._mark(0xA269);self._x(0);is_ruler=False
            while True:
                self._mark(0xA26B);self._a(m[(0x42C+r.x)&65535]);self._compare(r.a,m[0x10])
                if r.p&Z:is_ruler=True;break
                self._x(r.x+1);self._compare(r.x,7)
                if r.p&C:break
            if not is_ruler:
                self._a(m[0x10]);yield from self._external(0xA27B,0xF2D7,0xA27E,'call')
                if r.pc!=0xA27E:return
                self._y(11);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._a(r.a&3);self._compare(r.a,3)
                if not r.p&Z:m[0x11]=self._nz(m[0x11]+1)
            m[0x10]=self._nz(m[0x10]+1);self._a(m[0x10]);self._compare(r.a,237)
            if r.p&C:break
        self._rts();return

    def panel_helper_a296(self):
        """$A296: panel helper a296; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA296)
        self._a(m[PHASE])
        return (yield from self.panel_helper_a299())

    def panel_helper_a299(self):
        """$A299: panel helper a299; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA299)
        index=self._dispatch(0xA299,(41660, 41740, 41788, 41865, 41883, 41827, 41957, 42410, 42735, 43424, 44736, 48256, 48641, 49458, 50042, 43797))
        return (yield from (self.panel_helper_a2bc,self.panel_helper_a30c,self.panel_helper_a33c,self.panel_helper_a389,self.panel_helper_a39b,self.panel_helper_a363,self.panel_helper_a3e5,self.panel_helper_a5aa,self.panel_helper_a6ef,self.panel_helper_a9a0,self.panel_helper_aec0,self.panel_helper_bc80,self.panel_helper_be01,self.panel_helper_c132,self.panel_helper_c37a,self.panel_helper_ab15,)[index]())

    def panel_helper_a2bc(self):
        """$A2BC: panel helper a2bc; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA2BC)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xA2C1)
        if not r.p&Z:
            self._mark(0xA2D9)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xA2C8)
            if not r.p&Z:
                self._mark(0xA2D9)
                self._rts();return
            else:
                self._a(m[PPU_JOBS])
                self._mark(0xA2CD)
                if not r.p&Z:
                    self._mark(0xA2D9)
                    self._rts();return
                else:
                    self._a(m[0x6F06])
                    self._mark(0xA2D2)
                    if r.p&Z:
                        m[0x6F06]=self._nz(m[0x6F06]+1)
                        self._a(m[0x6F01])
                        self._compare(r.a,0x03)
                        self._mark(0xA2E2)
                        if not r.p&Z:
                            self._a(m[0x6F01])
                            self._compare(r.a,0x09)
                            self._mark(0xA2F4)
                            if not r.p&Z:
                                self._a(0x0F)
                                m[PHASE]=r.a
                                self._a(0x00)
                                m[CITY]=r.a
                                self._mark(0xA30B)
                                self._rts();return
                            else:
                                self._a(0x07)
                                m[PHASE]=r.a
                                self._a(0x00)
                                m[CITY]=r.a
                                self._mark(0xA300)
                                self._rts();return
                        else:
                            self._a(0x06)
                            m[PHASE]=r.a
                            self._a(0x00)
                            m[CITY]=r.a
                            self._mark(0xA2EE)
                            self._rts();return
                    else:
                        self._a(0x02)
                        m[PHASE]=r.a
                        self._mark(0xA2D9)
                        self._rts();return

    def panel_helper_a30c(self):
        """$A30C: panel helper a30c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA30C)
        self._a(m[0x6F01])
        self._compare(r.a,0x07)
        self._mark(0xA311)
        if r.p&Z:
            self._a(0x08)
            m[PHASE]=r.a
            self._a(0x00)
            m[CITY]=r.a
            self._mark(0xA321)
            self._rts();return
        else:
            self._compare(r.a,0x08)
            self._mark(0xA315)
            if not r.p&Z:
                self._a(m[0x6F01])
                self._compare(r.a,0x04)
                self._mark(0xA327)
                if r.p&Z:
                    self._a(0x09)
                    m[PHASE]=r.a
                    self._a(0x00)
                    m[CITY]=r.a
                    self._mark(0xA337)
                    self._rts();return
                else:
                    self._compare(r.a,0x05)
                    self._mark(0xA32B)
                    if not r.p&Z:
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._mark(0xA33B)
                        self._rts();return
                    else:
                        self._a(0x09)
                        m[PHASE]=r.a
                        self._a(0x00)
                        m[CITY]=r.a
                        self._mark(0xA337)
                        self._rts();return
            else:
                self._a(0x08)
                m[PHASE]=r.a
                self._a(0x00)
                m[CITY]=r.a
                self._mark(0xA321)
                self._rts();return

    def panel_helper_a33c(self):
        """$A33C: panel helper a33c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA33C)
        self._a(m[0x6F03])
        self._compare(r.a,0x02)
        self._mark(0xA341)
        if not r.p&C:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._mark(0xA362)
            self._rts();return
        else:
            self._compare(r.a,0x05)
            self._mark(0xA345)
            if r.p&Z:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._mark(0xA362)
                self._rts();return
            else:
                self._compare(r.a,0x06)
                self._mark(0xA349)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x05)
                    pass
                self._flag(C,True)
                self._add(0x02,subtract=True)
                r.a=self._shift(r.a,True,rotate=False)
                m[WORLD_CURSOR]=r.a
                self._a(0x0A)
                m[PHASE]=r.a
                self._a(0x00)
                m[CITY]=r.a
                self._mark(0xA35E)
                self._rts();return

    def panel_helper_a363(self):
        """$A363: panel helper a363; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA363)
        self._a(0x00)
        m[WORLD_CURSOR]=r.a
        self._y(0x03)
        self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
        self._compare(r.a,0x03)
        self._mark(0xA36E)
        if not r.p&Z:
            m[0x6F44]=r.a
            self._a(0x0B)
            m[STATE]=r.a
            self._a(0x01)
            m[PHASE]=r.a
            self._mark(0xA388)
            self._rts();return
        else:
            self._a(0x09)
            m[STATE]=r.a
            self._a(0x00)
            m[PHASE]=r.a
            self._mark(0xA37A)
            self._rts();return

    def panel_helper_a389(self):
        """$A389: panel helper a389; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA389)
        self._y(0x00)
        self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
        m[0x040B]=r.a
        self._a(0x0B)
        m[PHASE]=r.a
        self._a(0x00)
        m[CITY]=r.a
        self._mark(0xA39A)
        self._rts();return

    def panel_helper_a39b(self):
        """$A39B: panel helper a39b; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA39B)
        self._y(0x00)
        self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
        m[0x040B]=r.a
        yield from self._external(0xA3A2,0xF2D7,0xA3A5,"call",None)
        if r.pc!=0xA3A5:return  # preserve nonlocal stack return
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._a(r.a & 0x03)
        self._compare(r.a,0x03)
        self._mark(0xA3AD)
        if not r.p&Z:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._mark(0xA3E4)
            self._rts();return
        else:
            self._a(0x05)
            m[WORLD_CURSOR]=r.a
            self._a(0x0E)
            m[CURRENT_CITY]=r.a
            self._a(0x0B)
            m[0x0472]=r.a
            self._a(0x00)
            m[0x0473]=r.a
            self._a(m[0x6F03])
            m[0x040A]=r.a
            self._a(0xFF)
            m[OFFICER_INDEX]=r.a
            self._a(0x0C)
            m[PHASE]=r.a
            self._a(0x00)
            m[CITY]=r.a
            self._y(0x03)
            self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
            self._compare(r.a,0x03)
            self._mark(0xA3DE)
            if r.p&Z:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._mark(0xA3E4)
                self._rts();return
            else:
                self._mark(0xA3E0)
                self._rts();return

    def panel_helper_a3e5(self):
        """$A3E5: panel helper a3e5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA3E5)
        self._a(m[CITY])
        return (yield from self.panel_helper_a3e8())

    def panel_helper_a3e8(self):
        """$A3E8: panel helper a3e8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA3E8)
        index=self._dispatch(0xA3E8,(41969, 41988, 42016))
        return (yield from (self.panel_helper_a3f1,self.panel_helper_a404,self.panel_helper_a420,)[index]())

    def panel_helper_a3f1(self):
        """$A3F1: panel helper a3f1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA3F1)
        self._a(0xBC)
        yield from self._external(0xA3F3,0xF28B,0xA3F6,"call",None)
        if r.pc!=0xA3F6:return  # preserve nonlocal stack return
        m[CITY]=self._nz(m[CITY]+1)
        self._a(0xA6)
        m[0x04D6]=r.a
        self._a(0x20)
        m[0x04A0]=r.a
        self._mark(0xA403)
        self._rts();return

    def panel_helper_a404(self):
        """$A404: panel helper a404; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA404)
        self._a(m[0x04A0])
        self._mark(0xA407)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0140])
            self._mark(0xA40C)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0300])
                self._compare(r.a,0xFF)
                self._mark(0xA413)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x0304])
                    self._compare(r.a,0xFF)
                    self._mark(0xA41A)
                    if not r.p&Z:
                        pass
                    else:
                        m[CITY]=self._nz(m[CITY]+1)
                        pass
                    pass
                pass
            pass
        self._mark(0xA41F)
        self._rts();return

    def panel_helper_a420(self):
        """$A420: panel helper a420; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA420)
        self._a(0x01)
        m[PHASE]=r.a
        if not (yield from self._local_call(self.panel_helper_a429,0xA425,0xA428)):return
        self._mark(0xA428)
        self._rts();return

    def panel_helper_a429(self):
        """$A429: panel helper a429; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA429)
        self._a(0x1D)
        while True:  # natural loop $A42B
            try:
                self._push(r.a)
                yield from self._external(0xA42C,0xF2AF,0xA42F,"call",None)
                if r.pc!=0xA42F:return  # preserve nonlocal stack return
                self._a(m[0x0000])
                m[0x0010]=r.a
                self._a(m[0x0001])
                m[0x0011]=r.a
                self._y(0x06)
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                self._push(r.a)
                self._y(r.y+1)
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                self._a(r.a & 0x7F)
                self._push(r.a)
                self._y(0x0E)
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                m[0x0000]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                self._a(r.a & 0x03)
                m[0x0001]=r.a
                self._a(0x00)
                m[0x0002]=r.a
                m[0x0004]=r.a
                self._y(m[0x6F02])
                self._a(m[(0xA527+r.y)&65535])
                m[0x0003]=r.a
                yield from self._external(0xA466,0xEAA5,0xA469,"call",None)
                if r.pc!=0xA469:return  # preserve nonlocal stack return
                self._y(m[0x6F02])
                self._a(m[0x0000])
                self._flag(C,False)
                self._add(m[(0xA524+r.y)&65535])
                m[0x0003]=r.a
                self._a(m[0x0001])
                self._add(0x00)
                m[0x0004]=r.a
                self._a(self._pop())
                m[0x0001]=r.a
                self._a(self._pop())
                m[0x0000]=r.a
                self._a(0x00)
                m[0x0002]=r.a
                yield from self._external(0xA48B,0xEC22,0xA48E,"call",None)
                if r.pc!=0xA48E:return  # preserve nonlocal stack return
                self._a(m[0x0006])
                m[0x0000]=r.a
                self._a(m[0x0007])
                m[0x0001]=r.a
                self._a(m[0x0008])
                m[0x0002]=r.a
                self._a(0x50)
                m[0x0003]=r.a
                self._a(0x00)
                m[0x0004]=r.a
                yield from self._external(0xA4AA,0xEAA5,0xA4AD,"call",None)
                if r.pc!=0xA4AD:return  # preserve nonlocal stack return
                self._y(0x0B)
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                self._a(r.a & 0x7F)
                self._y(0x32)
                self._compare(r.a,0x33)
                self._mark(0xA4B7)
                if not r.p&C:
                    pass
                else:
                    self._y(0x3C)
                    self._compare(r.a,0x47)
                    self._mark(0xA4BD)
                    if not r.p&C:
                        pass
                    else:
                        self._y(0x46)
                        self._compare(r.a,0x51)
                        self._mark(0xA4C3)
                        if not r.p&C:
                            pass
                        else:
                            self._y(0x50)
                            self._compare(r.a,0x5B)
                            self._mark(0xA4C9)
                            if not r.p&C:
                                pass
                            else:
                                self._y(0x5A)
                                self._compare(r.a,0x64)
                                self._mark(0xA4CF)
                                if not r.p&C:
                                    pass
                                else:
                                    self._y(0x64)
                                    pass
                                pass
                            pass
                        pass
                    pass
                m[0x0003]=r.y
                self._a(0x00)
                m[0x0004]=r.a
                yield from self._external(0xA4DB,0xEC22,0xA4DE,"call",None)
                if r.pc!=0xA4DE:return  # preserve nonlocal stack return
                self._a(m[0x0006])
                m[0x0000]=r.a
                self._a(m[0x0007])
                m[0x0001]=r.a
                self._a(m[0x0008])
                m[0x0002]=r.a
                self._a(0x64)
                m[0x0003]=r.a
                self._a(0x00)
                m[0x0004]=r.a
                yield from self._external(0xA4FA,0xEAA5,0xA4FD,"call",None)
                if r.pc!=0xA4FD:return  # preserve nonlocal stack return
                self._y(0x02)
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x0000])
                m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                self._add(m[0x0001])
                m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a
                self._y(0x02)
                if not (yield from self._local_call(self.panel_helper_a52a,0xA511,0xA514)):return
                if not (yield from self._local_call(self.panel_helper_a540,0xA514,0xA517)):return
                if not (yield from self._local_call(self.panel_helper_a582,0xA517,0xA51A)):return
                self._a(self._pop())
                self._flag(C,True)
                self._add(0x01,subtract=True)
                self._mark(0xA51E)
                if r.p&N:
                    pass
                else:
                    continue
                self._mark(0xA523)
                self._rts();return
            except _ContinueLoop_A42B:
                continue

    def panel_helper_a52a(self):
        """$A52A: panel helper a52a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA52A)
        self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(0x10,subtract=True)
        self._y(r.y+1)
        self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
        self._add(0x27,subtract=True)
        self._mark(0xA534)
        if not r.p&C:
            pass
        else:
            self._a(0x27)
            m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a
            self._y(r.y-1)
            self._a(0x0F)
            m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a
            pass
        self._mark(0xA53F)
        self._rts();return

    def panel_helper_a540(self):
        """$A540: panel helper a540; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA540)
        self._rts();return

    def panel_helper_a582(self):
        """$A582: panel helper a582; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA582)
        self._rts();return

    def panel_helper_a5aa(self):
        """$A5AA: panel helper a5aa; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA5AA)
        self._a(m[CITY])
        return (yield from self.panel_helper_a5ad())

    def panel_helper_a5ad(self):
        """$A5AD: panel helper a5ad; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA5AD)
        index=self._dispatch(0xA5AD,(42422, 42441, 42469))
        return (yield from (self.panel_helper_a5b6,self.panel_helper_a5c9,self.panel_helper_a5e5,)[index]())

    def panel_helper_a5b6(self):
        """$A5B6: panel helper a5b6; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA5B6)
        self._a(0xBD)
        yield from self._external(0xA5B8,0xF28B,0xA5BB,"call",None)
        if r.pc!=0xA5BB:return  # preserve nonlocal stack return
        m[CITY]=self._nz(m[CITY]+1)
        self._a(0xA6)
        m[0x04D6]=r.a
        self._a(0x1D)
        m[0x04A0]=r.a
        self._mark(0xA5C8)
        self._rts();return

    def panel_helper_a5c9(self):
        """$A5C9: panel helper a5c9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA5C9)
        self._a(m[0x04A0])
        self._mark(0xA5CC)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0140])
            self._mark(0xA5D1)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0300])
                self._compare(r.a,0xFF)
                self._mark(0xA5D8)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x0304])
                    self._compare(r.a,0xFF)
                    self._mark(0xA5DF)
                    if not r.p&Z:
                        pass
                    else:
                        m[CITY]=self._nz(m[CITY]+1)
                        pass
                    pass
                pass
            pass
        self._mark(0xA5E4)
        self._rts();return

    def panel_helper_a5e5(self):
        """$A5E5: panel helper a5e5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA5E5)
        self._a(0x01)
        m[PHASE]=r.a
        if not (yield from self._local_call(self.panel_helper_a5ee,0xA5EA,0xA5ED)):return
        self._mark(0xA5ED)
        self._rts();return

    def panel_helper_a5ee(self):
        """$A5EE: panel helper a5ee; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA5EE)
        self._a(0x1D)
        while True:  # natural loop $A5F0
            try:
                self._push(r.a)
                yield from self._external(0xA5F1,0xF2AF,0xA5F4,"call",None)
                if r.pc!=0xA5F4:return  # preserve nonlocal stack return
                self._a(m[0x0000])
                m[0x0010]=r.a
                self._a(m[0x0001])
                m[0x0011]=r.a
                self._y(0x06)
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                self._push(r.a)
                self._y(r.y+1)
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                self._a(r.a & 0x7F)
                self._push(r.a)
                self._y(0x08)
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                m[0x0000]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                self._a(r.a & 0x03)
                m[0x0001]=r.a
                self._a(0x00)
                m[0x0002]=r.a
                m[0x0004]=r.a
                self._y(m[0x6F02])
                self._a(m[(0xA6EC+r.y)&65535])
                m[0x0003]=r.a
                yield from self._external(0xA62B,0xEAA5,0xA62E,"call",None)
                if r.pc!=0xA62E:return  # preserve nonlocal stack return
                self._y(m[0x6F02])
                self._a(m[0x0000])
                self._flag(C,False)
                self._add(m[(0xA6E9+r.y)&65535])
                m[0x0003]=r.a
                self._a(m[0x0001])
                self._add(0x00)
                m[0x0004]=r.a
                self._a(self._pop())
                m[0x0001]=r.a
                self._a(self._pop())
                m[0x0000]=r.a
                self._a(0x00)
                m[0x0002]=r.a
                yield from self._external(0xA650,0xEC22,0xA653,"call",None)
                if r.pc!=0xA653:return  # preserve nonlocal stack return
                self._a(m[0x0006])
                m[0x0000]=r.a
                self._a(m[0x0007])
                m[0x0001]=r.a
                self._a(m[0x0008])
                m[0x0002]=r.a
                self._a(0x3C)
                m[0x0003]=r.a
                self._a(0x00)
                m[0x0004]=r.a
                yield from self._external(0xA66F,0xEAA5,0xA672,"call",None)
                if r.pc!=0xA672:return  # preserve nonlocal stack return
                self._y(0x0B)
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                self._a(r.a & 0x7F)
                self._y(0x32)
                self._compare(r.a,0x33)
                self._mark(0xA67C)
                if not r.p&C:
                    pass
                else:
                    self._y(0x3C)
                    self._compare(r.a,0x47)
                    self._mark(0xA682)
                    if not r.p&C:
                        pass
                    else:
                        self._y(0x46)
                        self._compare(r.a,0x51)
                        self._mark(0xA688)
                        if not r.p&C:
                            pass
                        else:
                            self._y(0x50)
                            self._compare(r.a,0x5B)
                            self._mark(0xA68E)
                            if not r.p&C:
                                pass
                            else:
                                self._y(0x5A)
                                self._compare(r.a,0x64)
                                self._mark(0xA694)
                                if not r.p&C:
                                    pass
                                else:
                                    self._y(0x64)
                                    pass
                                pass
                            pass
                        pass
                    pass
                m[0x0003]=r.y
                self._a(0x00)
                m[0x0004]=r.a
                yield from self._external(0xA6A0,0xEC22,0xA6A3,"call",None)
                if r.pc!=0xA6A3:return  # preserve nonlocal stack return
                self._a(m[0x0006])
                m[0x0000]=r.a
                self._a(m[0x0007])
                m[0x0001]=r.a
                self._a(m[0x0008])
                m[0x0002]=r.a
                self._a(0x64)
                m[0x0003]=r.a
                self._a(0x00)
                m[0x0004]=r.a
                yield from self._external(0xA6BF,0xEAA5,0xA6C2,"call",None)
                if r.pc!=0xA6C2:return  # preserve nonlocal stack return
                self._y(0x04)
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x0000])
                m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                self._add(m[0x0001])
                m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a
                self._y(0x04)
                if not (yield from self._local_call(self.panel_helper_a52a,0xA6D6,0xA6D9)):return
                if not (yield from self._local_call(self.panel_helper_a540,0xA6D9,0xA6DC)):return
                if not (yield from self._local_call(self.panel_helper_a582,0xA6DC,0xA6DF)):return
                self._a(self._pop())
                self._flag(C,True)
                self._add(0x01,subtract=True)
                self._mark(0xA6E3)
                if r.p&N:
                    pass
                else:
                    continue
                self._mark(0xA6E8)
                self._rts();return
            except _ContinueLoop_A5F0:
                continue

    def panel_helper_a6ef(self):
        """$A6EF: panel helper a6ef; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA6EF)
        self._a(m[CITY])
        return (yield from self.panel_helper_a6f2())

    def panel_helper_a6f2(self):
        """$A6F2: panel helper a6f2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA6F2)
        index=self._dispatch(0xA6F2,(42749, 42784, 42817, 43103))
        return (yield from (self.panel_helper_a6fd,self.panel_helper_a720,self.panel_helper_a741,self.panel_helper_a85f,)[index]())

    def panel_helper_a6fd(self):
        """$A6FD: panel helper a6fd; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA6FD)
        self._y(0x00)
        if not (yield from self._local_call(self.panel_helper_a896,0xA6FF,0xA702)):return
        self._a(m[0x0000])
        self._mark(0xA705)
        if not r.p&Z:
            self._a(0xBE)
            yield from self._external(0xA70F,0xF28B,0xA712,"call",None)
            if r.pc!=0xA712:return  # preserve nonlocal stack return
            self._a(0x9F)
            m[0x04D6]=r.a
            self._a(0x1C)
            m[0x04A0]=r.a
            m[CITY]=self._nz(m[CITY]+1)
            self._mark(0xA71F)
            self._rts();return
        else:
            self._a(0x02)
            m[PHASE]=r.a
            self._mark(0xA70C)
            self._rts();return

    def panel_helper_a720(self):
        """$A720: panel helper a720; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA720)
        self._a(m[0x04A0])
        self._mark(0xA723)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0140])
            self._mark(0xA728)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0300])
                self._compare(r.a,0xFF)
                self._mark(0xA72F)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x0304])
                    self._compare(r.a,0xFF)
                    self._mark(0xA736)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(0x00)
                        m[0x0403]=r.a
                        m[CITY]=self._nz(m[CITY]+1)
                        pass
                    pass
                pass
            pass
        self._mark(0xA740)
        self._rts();return

    def panel_helper_a741(self):
        """$A741: panel helper a741; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA741)
        self._y(m[0x0403])
        self._a(m[(0x042D+r.y)&65535])
        self._compare(r.a,0xFF)
        self._mark(0xA749)
        if not r.p&Z:
            yield from self._external(0xA763,0xF2AF,0xA766,"call",None)
            if r.pc!=0xA766:return  # preserve nonlocal stack return
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & 0x07)
            self._compare(r.a,0x07)
            self._mark(0xA76E)
            if r.p&Z:
                m[0x0403]=self._nz(m[0x0403]+1)
                self._a(m[0x0403])
                self._compare(r.a,0x10)
                self._mark(0xA753)
                if not r.p&C:
                    pass
                else:
                    self._a(0x02)
                    m[PHASE]=r.a
                    self._a(0x00)
                    m[0x00A4]=r.a
                    yield from self._external(0xA75F,0xF28B,0xA762,"call",None)
                    if r.pc!=0xA762:return  # preserve nonlocal stack return
                    pass
                self._mark(0xA762)
                self._rts();return
            else:
                if not (yield from self._local_call(self.panel_helper_a8e0,0xA770,0xA773)):return
                self._a(m[0x0010])
                self._compare(r.a,0x0A)
                self._mark(0xA778)
                if not r.p&Z:
                    self._a(m[0x0000])
                    m[0x000A]=r.a
                    self._a(m[0x0001])
                    m[0x000B]=r.a
                    self._y(0x06)
                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                    m[0x0000]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                    m[0x0001]=r.a
                    m[0x0001]=self._shift(m[0x0001],False,rotate=False)
                    m[0x0000]=self._shift(m[0x0000],False,rotate=True)
                    m[0x0001]=self._shift(m[0x0001],False,rotate=False)
                    m[0x0000]=self._shift(m[0x0000],False,rotate=True)
                    self._y(0x06)
                    if not (yield from self._local_call(self.panel_helper_a93e,0xA7B0,0xA7B3)):return
                    self._y(0x08)
                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                    m[0x0000]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                    m[0x0001]=r.a
                    m[0x0001]=self._shift(m[0x0001],False,rotate=False)
                    m[0x0000]=self._shift(m[0x0000],False,rotate=True)
                    m[0x0001]=self._shift(m[0x0001],False,rotate=False)
                    m[0x0000]=self._shift(m[0x0000],False,rotate=True)
                    self._y(0x08)
                    if not (yield from self._local_call(self.panel_helper_a93e,0xA7CE,0xA7D1)):return
                    self._a(m[0x000A])
                    m[0x000C]=r.a
                    self._a(m[0x000B])
                    m[0x000D]=r.a
                    self._y(0x11)
                    while True:  # natural loop $A7DF
                        try:
                            self._a(r.y)
                            self._push(r.a)
                            self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                            self._compare(r.a,0xFF)
                            self._mark(0xA7E5)
                            if r.p&Z:
                                pass
                            else:
                                yield from self._external(0xA7E7,0xF2D7,0xA7EA,"call",None)
                                if r.pc!=0xA7EA:return  # preserve nonlocal stack return
                                self._a(m[0x0000])
                                m[0x000A]=r.a
                                self._a(m[0x0001])
                                m[0x000B]=r.a
                                self._y(0x08)
                                self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                m[0x0000]=r.a
                                self._y(r.y+1)
                                self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                m[0x0001]=r.a
                                m[0x0001]=self._shift(m[0x0001],False,rotate=False)
                                m[0x0000]=self._shift(m[0x0000],False,rotate=True)
                                m[0x0001]=self._shift(m[0x0001],False,rotate=False)
                                m[0x0000]=self._shift(m[0x0000],False,rotate=True)
                                self._y(0x08)
                                if not (yield from self._local_call(self.panel_helper_a93e,0xA811,0xA814)):return
                                pass
                            self._a(self._pop())
                            self._y(r.a)
                            self._y(r.y+1)
                            self._compare(r.y,0x1B)
                            self._mark(0xA819)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            self._y(0x00)
                            self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                            yield from self._external(0xA81F,0xF368,0xA822,"call",None)
                            if r.pc!=0xA822:return  # preserve nonlocal stack return
                            self._y(0x03)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._compare(r.a,0x03)
                            self._mark(0xA828)
                            if not r.p&Z:
                                m[0x6F44]=r.a
                                m[CITY]=self._nz(m[CITY]+1)
                                self._y(m[0x0403])
                                self._a(m[(0x042D+r.y)&65535])
                                m[0x042C]=r.a
                                m[0x0472]=r.a
                                self._a(m[0x0010])
                                m[WORLD_CURSOR]=r.a
                                self._a(m[0x0011])
                                m[CURRENT_CITY]=r.a
                                m[0x0000]=r.a
                                self._a(0x04)
                                m[0x00A4]=r.a
                                self._y(0x3D)
                                yield from self._external(0xA855,0xEE07,0xA85A,"far_call",41002)
                                if r.pc!=0xA85A:return  # preserve nonlocal stack return
                                self._a(0x3F)
                                self._mark(0xA85C)
                                yield from self._external(0xA85C,0xF26D,None,"tail")
                                return
                            else:
                                m[0x0403]=self._nz(m[0x0403]+1)
                                self._a(m[0x0403])
                                self._compare(r.a,0x10)
                                self._mark(0xA753)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(0x02)
                                    m[PHASE]=r.a
                                    self._a(0x00)
                                    m[0x00A4]=r.a
                                    yield from self._external(0xA75F,0xF28B,0xA762,"call",None)
                                    if r.pc!=0xA762:return  # preserve nonlocal stack return
                                    pass
                                self._mark(0xA762)
                                self._rts();return
                        except _ContinueLoop_A7DF:
                            continue
                else:
                    self._a(m[0x0000])
                    m[0x000C]=r.a
                    self._a(m[0x0001])
                    m[0x000D]=r.a
                    pass
                self._y(0x00)
                self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                yield from self._external(0xA81F,0xF368,0xA822,"call",None)
                if r.pc!=0xA822:return  # preserve nonlocal stack return
                self._y(0x03)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,0x03)
                self._mark(0xA828)
                if not r.p&Z:
                    m[0x6F44]=r.a
                    m[CITY]=self._nz(m[CITY]+1)
                    self._y(m[0x0403])
                    self._a(m[(0x042D+r.y)&65535])
                    m[0x042C]=r.a
                    m[0x0472]=r.a
                    self._a(m[0x0010])
                    m[WORLD_CURSOR]=r.a
                    self._a(m[0x0011])
                    m[CURRENT_CITY]=r.a
                    m[0x0000]=r.a
                    self._a(0x04)
                    m[0x00A4]=r.a
                    self._y(0x3D)
                    yield from self._external(0xA855,0xEE07,0xA85A,"far_call",41002)
                    if r.pc!=0xA85A:return  # preserve nonlocal stack return
                    self._a(0x3F)
                    self._mark(0xA85C)
                    yield from self._external(0xA85C,0xF26D,None,"tail")
                    return
                else:
                    m[0x0403]=self._nz(m[0x0403]+1)
                    self._a(m[0x0403])
                    self._compare(r.a,0x10)
                    self._mark(0xA753)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x02)
                        m[PHASE]=r.a
                        self._a(0x00)
                        m[0x00A4]=r.a
                        yield from self._external(0xA75F,0xF28B,0xA762,"call",None)
                        if r.pc!=0xA762:return  # preserve nonlocal stack return
                        pass
                    self._mark(0xA762)
                    self._rts();return
        else:
            m[0x0403]=self._nz(m[0x0403]+1)
            self._a(m[0x0403])
            self._compare(r.a,0x10)
            self._mark(0xA753)
            if not r.p&C:
                pass
            else:
                self._a(0x02)
                m[PHASE]=r.a
                self._a(0x00)
                m[0x00A4]=r.a
                yield from self._external(0xA75F,0xF28B,0xA762,"call",None)
                if r.pc!=0xA762:return  # preserve nonlocal stack return
                pass
            self._mark(0xA762)
            self._rts();return

    def panel_helper_a85f(self):
        """$A85F: panel helper a85f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA85F)
        if not (yield from self._local_call(self.panel_helper_a985,0xA85F,0xA862)):return
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xA867)
        if not r.p&Z:
            self._mark(0xA895)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xA86E)
            if not r.p&Z:
                self._mark(0xA895)
                self._rts();return
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xA870,0xA873)):return
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xA877)
                if not r.p&C:
                    self._mark(0xA895)
                    self._rts();return
                else:
                    self._a(m[WORLD_CURSOR])
                    self._compare(r.a,0x0A)
                    self._mark(0xA87E)
                    if r.p&Z:
                        self._a(0x00)
                        m[WORLD_CURSOR]=r.a
                        self._a(0x03)
                        m[0x00A4]=r.a
                        self._a(0x4D)
                        yield from self._external(0xA892,0xF26D,0xA895,"call",None)
                        if r.pc!=0xA895:return  # preserve nonlocal stack return
                        self._mark(0xA895)
                        self._rts();return
                    else:
                        m[CITY]=self._nz(m[CITY]-1)
                        m[0x0403]=self._nz(m[0x0403]+1)
                        self._a(m[0x0403])
                        self._compare(r.a,0x10)
                        self._mark(0xA753)
                        if not r.p&C:
                            pass
                        else:
                            self._a(0x02)
                            m[PHASE]=r.a
                            self._a(0x00)
                            m[0x00A4]=r.a
                            yield from self._external(0xA75F,0xF28B,0xA762,"call",None)
                            if r.pc!=0xA762:return  # preserve nonlocal stack return
                            pass
                        self._mark(0xA762)
                        self._rts();return

    def panel_helper_a896(self):
        """$A896: panel helper a896; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA896)
        self._x(0x10)
        self._a(0xFF)
        while True:  # natural loop $A89A
            try:
                m[(0x042C+r.x)&65535]=r.a
                self._x(r.x-1)
                self._mark(0xA89E)
                if not r.p&N:
                    continue
                else:
                    pass
                self._x(0x00)
                m[0x0000]=r.x
                while True:  # natural loop $A8A5
                    try:
                        yield from self._external(0xA8A5,0xE856,0xA8A8,"call",None)
                        if r.pc!=0xA8A8:return  # preserve nonlocal stack return
                        self._compare(r.a,0x06)
                        self._mark(0xA8AA)
                        if r.p&C:
                            continue
                        else:
                            pass
                        self._compare(r.a,0x00)
                        self._mark(0xA8AE)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[(0xA8C0+r.y)&65535])
                            m[(0x042D+r.x)&65535]=r.a
                            m[0x0000]=self._nz(m[0x0000]+1)
                            pass
                        self._y(r.y+1)
                        self._x(r.x+1)
                        self._compare(r.x,0x10)
                        self._mark(0xA8BD)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._mark(0xA8BF)
                        self._rts();return
                    except _ContinueLoop_A8A5:
                        continue
            except _ContinueLoop_A89A:
                continue

    def panel_helper_a8e0(self):
        """$A8E0: panel helper a8e0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA8E0)
        self._y(0x0A)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._x(0x0A)
        self._y(0x0A)
        self._compare(r.a,0x63)
        self._mark(0xA8EA)
        if r.p&Z:
            pass
        else:
            self._x(0x08)
            self._y(0x07)
            self._compare(r.a,0x50)
            self._mark(0xA8F2)
            if r.p&C:
                pass
            else:
                self._x(0x06)
                self._y(0x05)
                self._compare(r.a,0x32)
                self._mark(0xA8FA)
                if r.p&C:
                    pass
                else:
                    self._x(0x04)
                    self._y(0x01)
                    self._compare(r.a,0x14)
                    self._mark(0xA902)
                    if r.p&C:
                        pass
                    else:
                        self._x(0x02)
                        self._y(0x00)
                        self._compare(r.a,0x01)
                        self._mark(0xA90A)
                        if r.p&C:
                            pass
                        else:
                            self._x(0x00)
                            self._y(0x00)
                            pass
                        pass
                    pass
                pass
            pass
        m[0x0010]=r.x
        m[0x0011]=r.y
        self._compare(r.y,0x00)
        self._mark(0xA918)
        if r.p&Z:
            pass
        else:
            while True:  # natural loop $A91A
                try:
                    yield from self._external(0xA91A,0xE856,0xA91D,"call",None)
                    if r.pc!=0xA91D:return  # preserve nonlocal stack return
                    self._compare(r.a,0x06)
                    self._mark(0xA91F)
                    if r.p&C:
                        continue
                    else:
                        pass
                    self._flag(C,False)
                    self._add(m[0x0011])
                    self._mark(0xA925)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(0x01)
                        pass
                    m[0x0011]=r.a
                    self._y(0x0A)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._flag(C,True)
                    self._add(m[0x0011],subtract=True)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._y(0x11)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0011]=r.a
                    self._mark(0xA93D)
                    self._rts();return
                except _ContinueLoop_A91A:
                    continue
        self._y(0x11)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0011]=r.a
        self._mark(0xA93D)
        self._rts();return

    def panel_helper_a93e(self):
        """$A93E: panel helper a93e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA93E)
        self._a(m[0x0010])
        self._mark(0xA941)
        if r.p&Z:
            pass
        else:
            self._a(r.y)
            self._push(r.a)
            self._a(m[0x0010])
            m[0x0003]=r.a
            self._a(0x00)
            m[0x0002]=r.a
            yield from self._external(0xA950,0xEBE9,0xA953,"call",None)
            if r.pc!=0xA953:return  # preserve nonlocal stack return
            self._a(m[0x0006])
            m[0x0000]=r.a
            self._a(m[0x0007])
            m[0x0001]=r.a
            self._a(m[0x0008])
            m[0x0002]=r.a
            self._a(0x0A)
            m[0x0003]=r.a
            self._a(0x00)
            m[0x0004]=r.a
            yield from self._external(0xA96F,0xEAA5,0xA972,"call",None)
            if r.pc!=0xA972:return  # preserve nonlocal stack return
            self._a(self._pop())
            self._y(r.a)
            pass
        self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(m[0x0000],subtract=True)
        m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
        self._add(m[0x0001],subtract=True)
        m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535]=r.a
        self._mark(0xA984)
        self._rts();return

    def panel_helper_a985(self):
        """$A985: panel helper a985; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA985)
        self._a(m[0x0472])
        if not (yield from self._local_call(self.panel_helper_bbe7,0xA988,0xA98B)):return
        self._a(m[CURRENT_CITY])
        self._compare(r.a,0xFF)
        self._mark(0xA990)
        if r.p&Z:
            pass
        else:
            m[0x0000]=r.a
            self._a(0xA7)
            m[0x000A]=r.a
            self._x(0x00)
            yield from self._external(0xA99C,0xCE1F,0xA99F,"call",None)
            if r.pc!=0xA99F:return  # preserve nonlocal stack return
            pass
        self._mark(0xA99F)
        self._rts();return

    def panel_helper_a9a0(self):
        """$A9A0: panel helper a9a0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA9A0)
        self._a(m[CITY])
        return (yield from self.panel_helper_a9a3())

    def panel_helper_a9a3(self):
        """$A9A3: panel helper a9a3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA9A3)
        index=self._dispatch(0xA9A3,(43438, 43473, 43506, 43742))
        return (yield from (self.panel_helper_a9ae,self.panel_helper_a9d1,self.panel_helper_a9f2,self.panel_helper_aade,)[index]())

    def panel_helper_a9ae(self):
        """$A9AE: panel helper a9ae; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA9AE)
        self._y(0x10)
        if not (yield from self._local_call(self.panel_helper_a896,0xA9B0,0xA9B3)):return
        self._a(m[0x0000])
        self._mark(0xA9B6)
        if not r.p&Z:
            self._a(0xBF)
            yield from self._external(0xA9C0,0xF28B,0xA9C3,"call",None)
            if r.pc!=0xA9C3:return  # preserve nonlocal stack return
            self._a(0x9F)
            m[0x04D6]=r.a
            self._a(0x1E)
            m[0x04A0]=r.a
            m[CITY]=self._nz(m[CITY]+1)
            self._mark(0xA9D0)
            self._rts();return
        else:
            self._a(0x02)
            m[PHASE]=r.a
            self._mark(0xA9BD)
            self._rts();return

    def panel_helper_a9d1(self):
        """$A9D1: panel helper a9d1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA9D1)
        self._a(m[0x04A0])
        self._mark(0xA9D4)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0140])
            self._mark(0xA9D9)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0300])
                self._compare(r.a,0xFF)
                self._mark(0xA9E0)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x0304])
                    self._compare(r.a,0xFF)
                    self._mark(0xA9E7)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(0x00)
                        m[0x0403]=r.a
                        m[CITY]=self._nz(m[CITY]+1)
                        pass
                    pass
                pass
            pass
        self._mark(0xA9F1)
        self._rts();return

    def panel_helper_a9f2(self):
        """$A9F2: panel helper a9f2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA9F2)
        self._y(m[0x0403])
        self._a(m[(0x042D+r.y)&65535])
        self._compare(r.a,0xFF)
        self._mark(0xA9FA)
        if not r.p&Z:
            yield from self._external(0xAA14,0xF2AF,0xAA17,"call",None)
            if r.pc!=0xAA17:return  # preserve nonlocal stack return
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & 0x07)
            self._compare(r.a,0x07)
            self._mark(0xAA1F)
            if r.p&Z:
                m[0x0403]=self._nz(m[0x0403]+1)
                self._a(m[0x0403])
                self._compare(r.a,0x10)
                self._mark(0xAA04)
                if not r.p&C:
                    pass
                else:
                    self._a(0x02)
                    m[PHASE]=r.a
                    self._a(0x00)
                    m[0x00A4]=r.a
                    yield from self._external(0xAA10,0xF28B,0xAA13,"call",None)
                    if r.pc!=0xAA13:return  # preserve nonlocal stack return
                    pass
                self._mark(0xAA13)
                self._rts();return
            else:
                if not (yield from self._local_call(self.panel_helper_a8e0,0xAA21,0xAA24)):return
                self._a(m[0x0010])
                self._compare(r.a,0x0A)
                self._mark(0xAA29)
                if not r.p&Z:
                    self._a(m[0x0000])
                    m[0x000A]=r.a
                    self._a(m[0x0001])
                    m[0x000B]=r.a
                    self._y(0x06)
                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                    m[0x0000]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                    m[0x0001]=r.a
                    m[0x0001]=self._shift(m[0x0001],False,rotate=False)
                    m[0x0000]=self._shift(m[0x0000],False,rotate=True)
                    m[0x0001]=self._shift(m[0x0001],False,rotate=False)
                    m[0x0000]=self._shift(m[0x0000],False,rotate=True)
                    self._y(0x06)
                    if not (yield from self._local_call(self.panel_helper_a93e,0xAA61,0xAA64)):return
                    self._y(0x0E)
                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                    m[0x0000]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                    m[0x0001]=r.a
                    m[0x0001]=self._shift(m[0x0001],False,rotate=False)
                    m[0x0000]=self._shift(m[0x0000],False,rotate=True)
                    m[0x0001]=self._shift(m[0x0001],False,rotate=False)
                    m[0x0000]=self._shift(m[0x0000],False,rotate=True)
                    self._y(0x0E)
                    if not (yield from self._local_call(self.panel_helper_a93e,0xAA7F,0xAA82)):return
                    self._y(0x04)
                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                    m[0x0000]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                    m[0x0001]=r.a
                    m[0x0001]=self._shift(m[0x0001],False,rotate=False)
                    m[0x0000]=self._shift(m[0x0000],False,rotate=True)
                    self._y(0x04)
                    if not (yield from self._local_call(self.panel_helper_a93e,0xAA97,0xAA9A)):return
                    pass
                else:
                    self._a(m[0x0000])
                    m[0x000A]=r.a
                    self._a(m[0x0001])
                    m[0x000B]=r.a
                    pass
                self._y(0x00)
                self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                yield from self._external(0xAA9E,0xF368,0xAAA1,"call",None)
                if r.pc!=0xAAA1:return  # preserve nonlocal stack return
                self._y(0x03)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,0x03)
                self._mark(0xAAA7)
                if not r.p&Z:
                    m[0x6F44]=r.a
                    m[CITY]=self._nz(m[CITY]+1)
                    self._y(m[0x0403])
                    self._a(m[(0x042D+r.y)&65535])
                    m[0x042C]=r.a
                    m[0x0472]=r.a
                    self._a(m[0x0010])
                    m[WORLD_CURSOR]=r.a
                    self._a(m[0x0011])
                    m[CURRENT_CITY]=r.a
                    m[0x0000]=r.a
                    self._y(0x3D)
                    yield from self._external(0xAACF,0xEE07,0xAAD4,"far_call",41002)
                    if r.pc!=0xAAD4:return  # preserve nonlocal stack return
                    self._a(0x04)
                    m[0x00A4]=r.a
                    self._a(0x45)
                    self._mark(0xAADB)
                    yield from self._external(0xAADB,0xF26D,None,"tail")
                    return
                else:
                    m[0x0403]=self._nz(m[0x0403]+1)
                    self._a(m[0x0403])
                    self._compare(r.a,0x10)
                    self._mark(0xAA04)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x02)
                        m[PHASE]=r.a
                        self._a(0x00)
                        m[0x00A4]=r.a
                        yield from self._external(0xAA10,0xF28B,0xAA13,"call",None)
                        if r.pc!=0xAA13:return  # preserve nonlocal stack return
                        pass
                    self._mark(0xAA13)
                    self._rts();return
        else:
            m[0x0403]=self._nz(m[0x0403]+1)
            self._a(m[0x0403])
            self._compare(r.a,0x10)
            self._mark(0xAA04)
            if not r.p&C:
                pass
            else:
                self._a(0x02)
                m[PHASE]=r.a
                self._a(0x00)
                m[0x00A4]=r.a
                yield from self._external(0xAA10,0xF28B,0xAA13,"call",None)
                if r.pc!=0xAA13:return  # preserve nonlocal stack return
                pass
            self._mark(0xAA13)
            self._rts();return

    def panel_helper_aade(self):
        """$AADE: panel helper aade; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAADE)
        if not (yield from self._local_call(self.panel_helper_a985,0xAADE,0xAAE1)):return
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xAAE6)
        if not r.p&Z:
            self._mark(0xAB14)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xAAED)
            if not r.p&Z:
                self._mark(0xAB14)
                self._rts();return
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xAAEF,0xAAF2)):return
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xAAF6)
                if not r.p&C:
                    self._mark(0xAB14)
                    self._rts();return
                else:
                    self._a(m[WORLD_CURSOR])
                    self._compare(r.a,0x0A)
                    self._mark(0xAAFD)
                    if r.p&Z:
                        self._a(0x00)
                        m[WORLD_CURSOR]=r.a
                        self._a(0x03)
                        m[0x00A4]=r.a
                        self._a(0x4D)
                        yield from self._external(0xAB11,0xF26D,0xAB14,"call",None)
                        if r.pc!=0xAB14:return  # preserve nonlocal stack return
                        self._mark(0xAB14)
                        self._rts();return
                    else:
                        m[CITY]=self._nz(m[CITY]-1)
                        m[0x0403]=self._nz(m[0x0403]+1)
                        self._a(m[0x0403])
                        self._compare(r.a,0x10)
                        self._mark(0xAA04)
                        if not r.p&C:
                            pass
                        else:
                            self._a(0x02)
                            m[PHASE]=r.a
                            self._a(0x00)
                            m[0x00A4]=r.a
                            yield from self._external(0xAA10,0xF28B,0xAA13,"call",None)
                            if r.pc!=0xAA13:return  # preserve nonlocal stack return
                            pass
                        self._mark(0xAA13)
                        self._rts();return

    def panel_helper_ab15(self):
        """$AB15: panel helper ab15; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAB15)
        self._a(m[CITY])
        return (yield from self.panel_helper_ab18())

    def panel_helper_ab18(self):
        """$AB18: panel helper ab18; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAB18)
        index=self._dispatch(0xAB18,(43813, 43945, 44109, 44186, 44221))
        return (yield from (self.panel_helper_ab25,self.panel_helper_aba9,self.panel_helper_ac4d,self.panel_helper_ac9a,self.panel_helper_acbd,)[index]())

    def panel_helper_ab25(self):
        """$AB25: panel helper ab25; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAB25)
        self._a(m[0x6F00])
        self._compare(r.a,0x59)
        self._mark(0xAB2A)
        if not r.p&Z:
            self._x(0x00)
            self._a(0x00)
            while True:  # natural loop $AB3D
                try:
                    m[(0x042C+r.x)&65535]=r.a
                    self._x(r.x+1)
                    self._compare(r.x,0x1E)
                    self._mark(0xAB43)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    self._x(0x00)
                    while True:  # natural loop $AB47
                        try:
                            self._a(r.x)
                            yield from self._external(0xAB48,0xF2AF,0xAB4B,"call",None)
                            if r.pc!=0xAB4B:return  # preserve nonlocal stack return
                            self._y(0x00)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._a(r.a & 0x0F)
                            self._compare(r.a,0x07)
                            self._mark(0xAB53)
                            if r.p&Z:
                                pass
                            else:
                                self._y(0x1B)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                self._mark(0xAB59)
                                if r.p&Z:
                                    self._y(0x0B)
                                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                    self._compare(r.a,0x32)
                                    self._mark(0xAB74)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._y(0x05)
                                        self._compare(r.a,0x28)
                                        self._mark(0xAB7A)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._y(0x0A)
                                            self._compare(r.a,0x1E)
                                            self._mark(0xAB80)
                                            if r.p&C:
                                                pass
                                            else:
                                                self._y(0x1E)
                                                self._compare(r.a,0x14)
                                                self._mark(0xAB86)
                                                if r.p&C:
                                                    pass
                                                else:
                                                    self._y(0x32)
                                                    pass
                                                pass
                                            pass
                                        m[0x0011]=r.y
                                        self._a(0x64)
                                        yield from self._external(0xAB8F,0xE862,0xAB92,"call",None)
                                        if r.pc!=0xAB92:return  # preserve nonlocal stack return
                                        self._compare(r.a,m[0x0011])
                                        self._mark(0xAB95)
                                        if not r.p&C:
                                            self._a(m[0x0011])
                                            m[(0x042C+r.x)&65535]=r.a
                                            self._y(0x1B)
                                            self._a(0x06)
                                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                            pass
                                        else:
                                            pass
                                        pass
                                    pass
                                else:
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                    pass
                                pass
                            self._x(r.x+1)
                            self._compare(r.x,0x1E)
                            self._mark(0xAB63)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            m[CITY]=self._nz(m[CITY]+1)
                            self._a(0x00)
                            m[0x0403]=r.a
                            self._mark(0xAB6D)
                            self._rts();return
                        except _ContinueLoop_AB47:
                            continue
                except _ContinueLoop_AB3D:
                    continue
        else:
            self._a(m[0x6F01])
            self._compare(r.a,0x04)
            self._mark(0xAB31)
            if r.p&C:
                self._x(0x00)
                self._a(0x00)
                while True:  # natural loop $AB3D
                    try:
                        m[(0x042C+r.x)&65535]=r.a
                        self._x(r.x+1)
                        self._compare(r.x,0x1E)
                        self._mark(0xAB43)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._x(0x00)
                        while True:  # natural loop $AB47
                            try:
                                self._a(r.x)
                                yield from self._external(0xAB48,0xF2AF,0xAB4B,"call",None)
                                if r.pc!=0xAB4B:return  # preserve nonlocal stack return
                                self._y(0x00)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                self._a(r.a & 0x0F)
                                self._compare(r.a,0x07)
                                self._mark(0xAB53)
                                if r.p&Z:
                                    pass
                                else:
                                    self._y(0x1B)
                                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                    self._mark(0xAB59)
                                    if r.p&Z:
                                        self._y(0x0B)
                                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                        self._compare(r.a,0x32)
                                        self._mark(0xAB74)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._y(0x05)
                                            self._compare(r.a,0x28)
                                            self._mark(0xAB7A)
                                            if r.p&C:
                                                pass
                                            else:
                                                self._y(0x0A)
                                                self._compare(r.a,0x1E)
                                                self._mark(0xAB80)
                                                if r.p&C:
                                                    pass
                                                else:
                                                    self._y(0x1E)
                                                    self._compare(r.a,0x14)
                                                    self._mark(0xAB86)
                                                    if r.p&C:
                                                        pass
                                                    else:
                                                        self._y(0x32)
                                                        pass
                                                    pass
                                                pass
                                            m[0x0011]=r.y
                                            self._a(0x64)
                                            yield from self._external(0xAB8F,0xE862,0xAB92,"call",None)
                                            if r.pc!=0xAB92:return  # preserve nonlocal stack return
                                            self._compare(r.a,m[0x0011])
                                            self._mark(0xAB95)
                                            if not r.p&C:
                                                self._a(m[0x0011])
                                                m[(0x042C+r.x)&65535]=r.a
                                                self._y(0x1B)
                                                self._a(0x06)
                                                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                                pass
                                            else:
                                                pass
                                            pass
                                        pass
                                    else:
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                        pass
                                    pass
                                self._x(r.x+1)
                                self._compare(r.x,0x1E)
                                self._mark(0xAB63)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                m[CITY]=self._nz(m[CITY]+1)
                                self._a(0x00)
                                m[0x0403]=r.a
                                self._mark(0xAB6D)
                                self._rts();return
                            except _ContinueLoop_AB47:
                                continue
                    except _ContinueLoop_AB3D:
                        continue
            else:
                self._a(0x01)
                m[PHASE]=r.a
                self._mark(0xAB38)
                self._rts();return

    def panel_helper_aba9(self):
        """$ABA9: panel helper aba9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xABA9)
        self._y(m[0x0403])
        self._a(m[(0x042C+r.y)&65535])
        self._mark(0xABAF)
        if not r.p&Z:
            m[WORLD_CURSOR]=r.a
            self._a(r.y)
            yield from self._external(0xABCD,0xF2AF,0xABD0,"call",None)
            if r.pc!=0xABD0:return  # preserve nonlocal stack return
            self._a(m[0x0000])
            m[0x000A]=r.a
            self._a(m[0x0001])
            m[0x000B]=r.a
            while True:  # natural loop $ABDC
                try:
                    yield from self._external(0xABDC,0xE850,0xABDF,"call",None)
                    if r.pc!=0xABDF:return  # preserve nonlocal stack return
                    self._mark(0xABDF)
                    if r.p&Z:
                        continue
                    else:
                        pass
                    m[0x0010]=r.a
                    self._compare(r.a,0x01)
                    self._mark(0xABE6)
                    if not r.p&Z:
                        self._compare(r.a,0x02)
                        self._mark(0xABF0)
                        if not r.p&Z:
                            if not (yield from self._local_call(self.panel_helper_ad14,0xABF8,0xABFB)):return
                            pass
                        else:
                            if not (yield from self._local_call(self.panel_helper_ace9,0xABF2,0xABF5)):return
                            pass
                        pass
                    else:
                        if not (yield from self._local_call(self.panel_helper_accd,0xABE8,0xABEB)):return
                        pass
                    self._y(0x00)
                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                    yield from self._external(0xABFF,0xF368,0xAC02,"call",None)
                    if r.pc!=0xAC02:return  # preserve nonlocal stack return
                    self._y(0x03)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._compare(r.a,0x03)
                    self._mark(0xAC08)
                    if not r.p&Z:
                        m[0x6F44]=r.a
                        m[CITY]=self._nz(m[CITY]+1)
                        self._a(m[0x0403])
                        m[0x044C]=r.a
                        m[0x0472]=r.a
                        self._a(m[0x0010])
                        m[WORLD_CURSOR]=r.a
                        self._a(0xFF)
                        m[CURRENT_CITY]=r.a
                        self._a(m[0x0472])
                        m[0x000A]=r.a
                        self._y(0x3B)
                        yield from self._external(0xAC2F,0xEE07,0xAC34,"far_call",40969)
                        if r.pc!=0xAC34:return  # preserve nonlocal stack return
                        self._a(m[0x000B])
                        self._a(r.a & 0x80)
                        self._a(r.a ^ 0x80)
                        m[0x0150]=r.a
                        self._a(0x9F)
                        m[0x04D6]=r.a
                        self._a(0x1F)
                        m[0x04A0]=r.a
                        self._a(0xE8)
                        self._mark(0xAC4A)
                        yield from self._external(0xAC4A,0xF28B,None,"tail")
                        return
                    else:
                        m[0x0403]=self._nz(m[0x0403]+1)
                        self._a(m[0x0403])
                        self._compare(r.a,0x1E)
                        self._mark(0xABB9)
                        if not r.p&C:
                            pass
                        else:
                            self._a(0x01)
                            m[PHASE]=r.a
                            self._a(0x00)
                            m[0x00A4]=r.a
                            yield from self._external(0xABC5,0xF28B,0xABC8,"call",None)
                            if r.pc!=0xABC8:return  # preserve nonlocal stack return
                            pass
                        self._mark(0xABC8)
                        self._rts();return
                except _ContinueLoop_ABDC:
                    continue
        else:
            m[0x0403]=self._nz(m[0x0403]+1)
            self._a(m[0x0403])
            self._compare(r.a,0x1E)
            self._mark(0xABB9)
            if not r.p&C:
                pass
            else:
                self._a(0x01)
                m[PHASE]=r.a
                self._a(0x00)
                m[0x00A4]=r.a
                yield from self._external(0xABC5,0xF28B,0xABC8,"call",None)
                if r.pc!=0xABC8:return  # preserve nonlocal stack return
                pass
            self._mark(0xABC8)
            self._rts();return

    def panel_helper_ac4d(self):
        """$AC4D: panel helper ac4d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAC4D)
        if not (yield from self._local_call(self.panel_helper_a985,0xAC4D,0xAC50)):return
        self._a(m[0x04A0])
        self._mark(0xAC53)
        if not r.p&Z:
            self._mark(0xAC71)
            self._rts();return
        else:
            self._a(m[0x0140])
            self._mark(0xAC58)
            if not r.p&Z:
                self._mark(0xAC71)
                self._rts();return
            else:
                self._a(m[0x0300])
                self._compare(r.a,0xFF)
                self._mark(0xAC5F)
                if not r.p&Z:
                    self._mark(0xAC71)
                    self._rts();return
                else:
                    self._a(m[0x0304])
                    self._compare(r.a,0xFF)
                    self._mark(0xAC66)
                    if not r.p&Z:
                        self._mark(0xAC71)
                        self._rts();return
                    else:
                        if not (yield from self._local_call(self.panel_helper_a1c2,0xAC68,0xAC6B)):return
                        self._a(m[NEW_BUTTONS])
                        r.a=self._shift(r.a,False,rotate=False)
                        self._mark(0xAC6F)
                        if r.p&C:
                            m[CITY]=self._nz(m[CITY]+1)
                            self._a(0x04)
                            m[0x00A4]=r.a
                            self._a(m[0x0472])
                            yield from self._external(0xAC7D,0xF2AF,0xAC80,"call",None)
                            if r.pc!=0xAC80:return  # preserve nonlocal stack return
                            self._y(0x11)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            m[CURRENT_CITY]=r.a
                            m[0x0000]=r.a
                            self._y(0x3D)
                            yield from self._external(0xAC8C,0xEE07,0xAC91,"far_call",41002)
                            if r.pc!=0xAC91:return  # preserve nonlocal stack return
                            self._a(0xE8)
                            self._flag(C,False)
                            self._add(m[WORLD_CURSOR])
                            self._mark(0xAC97)
                            yield from self._external(0xAC97,0xF26D,None,"tail")
                            return
                        else:
                            self._mark(0xAC71)
                            self._rts();return

    def panel_helper_ac9a(self):
        """$AC9A: panel helper ac9a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAC9A)
        if not (yield from self._local_call(self.panel_helper_a985,0xAC9A,0xAC9D)):return
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xACA2)
        if not r.p&Z:
            self._mark(0xACBC)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xACA9)
            if not r.p&Z:
                self._mark(0xACBC)
                self._rts();return
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xACAB,0xACAE)):return
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xACB2)
                if not r.p&C:
                    self._mark(0xACBC)
                    self._rts();return
                else:
                    m[CITY]=self._nz(m[CITY]+1)
                    self._a(0x00)
                    self._mark(0xACB9)
                    yield from self._external(0xACB9,0xF28B,None,"tail")
                    return

    def panel_helper_acbd(self):
        """$ACBD: panel helper acbd; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xACBD)
        self._a(m[0x0304])
        self._compare(r.a,0xFF)
        self._mark(0xACC2)
        if not r.p&Z:
            self._mark(0xACCC)
            self._rts();return
        else:
            self._a(0x01)
            m[CITY]=r.a
            m[0x0403]=self._nz(m[0x0403]+1)
            self._a(m[0x0403])
            self._compare(r.a,0x1E)
            self._mark(0xABB9)
            if not r.p&C:
                pass
            else:
                self._a(0x01)
                m[PHASE]=r.a
                self._a(0x00)
                m[0x00A4]=r.a
                yield from self._external(0xABC5,0xF28B,0xABC8,"call",None)
                if r.pc!=0xABC8:return  # preserve nonlocal stack return
                pass
            self._mark(0xABC8)
            self._rts();return

    def panel_helper_accd(self):
        """$ACCD: panel helper accd; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xACCD)
        self._x(0x01)
        self._a(m[WORLD_CURSOR])
        self._compare(r.a,0x05)
        self._mark(0xACD4)
        if r.p&Z:
            pass
        else:
            self._x(r.x+1)
            self._compare(r.a,0x0A)
            self._mark(0xACD9)
            if r.p&Z:
                pass
            else:
                self._x(r.x+1)
                self._compare(r.a,0x1E)
                self._mark(0xACDE)
                if r.p&Z:
                    pass
                else:
                    self._x(r.x+1)
                    pass
                pass
            pass
        m[0x0003]=r.x
        self._y(0x06)
        return (yield from self.panel_helper_ad3f())

    def panel_helper_ace9(self):
        """$ACE9: panel helper ace9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xACE9)
        self._x(0x04)
        self._a(m[WORLD_CURSOR])
        self._compare(r.a,0x05)
        self._mark(0xACF0)
        if r.p&Z:
            pass
        else:
            self._x(r.x+1)
            self._x(r.x+1)
            self._compare(r.a,0x0A)
            self._mark(0xACF6)
            if r.p&Z:
                pass
            else:
                self._x(r.x+1)
                self._compare(r.a,0x1E)
                self._mark(0xACFB)
                if r.p&Z:
                    pass
                else:
                    self._x(r.x+1)
                    pass
                pass
            pass
        m[0x0003]=r.x
        m[0x000C]=r.x
        self._y(0x02)
        if not (yield from self._local_call(self.panel_helper_ad3f,0xAD06,0xAD09)):return
        self._a(m[0x000C])
        m[0x0003]=r.a
        self._y(0x04)
        return (yield from self.panel_helper_ad3f())

    def panel_helper_ad14(self):
        """$AD14: panel helper ad14; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAD14)
        self._x(0x04)
        self._a(m[WORLD_CURSOR])
        self._compare(r.a,0x05)
        self._mark(0xAD1B)
        if r.p&Z:
            pass
        else:
            self._x(r.x+1)
            self._x(r.x+1)
            self._compare(r.a,0x0A)
            self._mark(0xAD21)
            if r.p&Z:
                pass
            else:
                self._x(r.x+1)
                self._compare(r.a,0x1E)
                self._mark(0xAD26)
                if r.p&Z:
                    pass
                else:
                    self._x(r.x+1)
                    pass
                pass
            pass
        m[0x0003]=r.x
        m[0x000C]=r.x
        self._y(0x08)
        if not (yield from self._local_call(self.panel_helper_ad3f,0xAD31,0xAD34)):return
        self._a(m[0x000C])
        m[0x0003]=r.a
        self._y(0x0E)
        return (yield from self.panel_helper_ad3f())

    def panel_helper_ad3f(self):
        """$AD3F: panel helper ad3f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAD3F)
        m[0x000D]=r.y
        self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
        m[0x0000]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
        m[0x0001]=r.a
        m[0x0001]=self._shift(m[0x0001],False,rotate=False)
        m[0x0000]=self._shift(m[0x0000],False,rotate=True)
        m[0x0001]=self._shift(m[0x0001],False,rotate=False)
        m[0x0000]=self._shift(m[0x0000],False,rotate=True)
        m[0x0001]=self._shift(m[0x0001],False,rotate=False)
        m[0x0000]=self._shift(m[0x0000],False,rotate=True)
        m[0x0001]=self._shift(m[0x0001],False,rotate=False)
        m[0x0000]=self._shift(m[0x0000],False,rotate=True)
        self._a(0x00)
        m[0x0002]=r.a
        yield from self._external(0xAD6A,0xEBE9,0xAD6D,"call",None)
        if r.pc!=0xAD6D:return  # preserve nonlocal stack return
        self._y(m[0x000D])
        self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(m[0x0006],subtract=True)
        m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
        self._add(m[0x0007],subtract=True)
        m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535]=r.a
        self._mark(0xAD80)
        self._rts();return

    def panel_helper_ad81(self):
        """$AD81: panel helper ad81; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAD81)
        self._a(m[PHASE])
        return (yield from self.panel_helper_ad84())

    def panel_helper_ad84(self):
        """$AD84: panel helper ad84; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAD84)
        index=self._dispatch(0xAD84,(44437, 44458, 44557, 44625, 48641, 49458, 50042))
        return (yield from (self.panel_helper_ad95,self.panel_helper_adaa,self.panel_helper_ae0d,self.panel_helper_ae51,self.panel_helper_be01,self.panel_helper_c132,self.panel_helper_c37a,)[index]())

    def panel_helper_ad95(self):
        """$AD95: panel helper ad95; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAD95)
        self._a(0x00)
        m[0x04E4]=r.a
        self._a(0xF0)
        m[0x6F41]=r.a
        self._y(0x3D)
        yield from self._external(0xADA1,0xEE07,0xADA6,"far_call",40990)
        if r.pc!=0xADA6:return  # preserve nonlocal stack return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._mark(0xADA9)
        self._rts();return

    def panel_helper_adaa(self):
        """$ADAA: panel helper adaa; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xADAA)
        self._a(m[PPU_JOBS])
        self._mark(0xADAD)
        if r.p&Z:
            self._a(m[0x0507])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[OFFICER_INDEX]=r.a
            self._a(m[0x0507])
            self._a(r.a & 0x0F)
            m[0x040A]=r.a
            yield from self._external(0xADC2,0xF368,0xADC5,"call",None)
            if r.pc!=0xADC5:return  # preserve nonlocal stack return
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x040B]=r.a
            yield from self._external(0xADCC,0xF2D7,0xADCF,"call",None)
            if r.pc!=0xADCF:return  # preserve nonlocal stack return
            self._y(0x0B)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & 0x03)
            self._compare(r.a,0x03)
            self._mark(0xADD7)
            if r.p&Z:
                self._a(0x02)
                m[WORLD_CURSOR]=r.a
                self._a(0x06)
                m[CURRENT_CITY]=r.a
                self._a(0x0D)
                m[0x0472]=r.a
                self._a(0x03)
                m[0x0473]=r.a
                self._a(0x04)
                m[PHASE]=r.a
                self._a(0x00)
                m[CITY]=r.a
                self._a(m[0x040A])
                yield from self._external(0xADFE,0xF368,0xAE01,"call",None)
                if r.pc!=0xAE01:return  # preserve nonlocal stack return
                self._y(0x03)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,0x03)
                self._mark(0xAE07)
                if r.p&Z:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._mark(0xADDC)
                    self._rts();return
                else:
                    m[0x6F44]=r.a
                    self._mark(0xAE0C)
                    self._rts();return
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._mark(0xADDC)
                self._rts();return
        else:
            self._mark(0xADAF)
            self._rts();return

    def panel_helper_ae0d(self):
        """$AE0D: panel helper ae0d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAE0D)
        self._a(m[0x0507])
        self._a(r.a & 0x0F)
        m[OFFICER_INDEX]=r.a
        self._a(m[0x0507])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        m[0x040A]=r.a
        yield from self._external(0xAE1F,0xF368,0xAE22,"call",None)
        if r.pc!=0xAE22:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x040B]=r.a
        yield from self._external(0xAE29,0xF2D7,0xAE2C,"call",None)
        if r.pc!=0xAE2C:return  # preserve nonlocal stack return
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._a(r.a & 0x03)
        self._compare(r.a,0x03)
        self._mark(0xAE34)
        if not r.p&Z:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._mark(0xAE50)
            self._rts();return
        else:
            self._a(0x03)
            m[WORLD_CURSOR]=r.a
            self._a(0x06)
            m[CURRENT_CITY]=r.a
            self._a(0x0B)
            m[0x0472]=r.a
            self._a(0x00)
            m[0x0473]=r.a
            self._a(0x04)
            m[PHASE]=r.a
            self._a(0x00)
            m[CITY]=r.a
            self._a(m[0x040A])
            yield from self._external(0xADFE,0xF368,0xAE01,"call",None)
            if r.pc!=0xAE01:return  # preserve nonlocal stack return
            self._y(0x03)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._compare(r.a,0x03)
            self._mark(0xAE07)
            if r.p&Z:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._mark(0xADDC)
                self._rts();return
            else:
                m[0x6F44]=r.a
                self._mark(0xAE0C)
                self._rts();return

    def panel_helper_ae51(self):
        """$AE51: panel helper ae51; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAE51)
        self._a(0x00)
        m[WORLD_CURSOR]=r.a
        m[CURRENT_CITY]=r.a
        self._y(0x03)
        self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
        self._compare(r.a,0x03)
        self._mark(0xAE5F)
        if not r.p&Z:
            m[0x6F44]=r.a
            self._y(0x00)
            self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
            m[0x000A]=r.a
            if not (yield from self._local_call(self.find_officer_city,0xAE95,0xAE98)):return
            self._y(0x01)
            m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535]=r.a
            self._y(0x01)
            self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
            self._y(r.a)
            self._a(m[(0xC737+r.y)&65535])
            m[0x6F3F]=r.a
            self._a(m[(0xC755+r.y)&65535])
            self._flag(C,False)
            self._add(0x01)
            m[0x6F41]=r.a
            self._y(0x3D)
            yield from self._external(0xAEB2,0xEE07,0xAEB7,"far_call",40990)
            if r.pc!=0xAEB7:return  # preserve nonlocal stack return
            self._a(0x00)
            m[STATE]=r.a
            m[PHASE]=r.a
            self._mark(0xAEBF)
            self._rts();return
        else:
            self._a(0xBB)
            yield from self._external(0xAE63,0xF28B,0xAE66,"call",None)
            if r.pc!=0xAE66:return  # preserve nonlocal stack return
            self._y(0x00)
            self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
            m[0x042C]=r.a
            self._a(0x09)
            m[STATE]=r.a
            self._a(0x01)
            m[PHASE]=r.a
            self._a(0x00)
            m[OFFICER_INDEX]=r.a
            self._a(0x00)
            m[0x6F8B]=r.a
            m[0x6F5B]=r.a
            m[0x6F5C]=r.a
            m[0x6F62]=r.a
            self._mark(0xAE8A)
            self._rts();return

    def panel_helper_aec0(self):
        """$AEC0: panel helper aec0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAEC0)
        self._a(m[CITY])
        return (yield from self.panel_helper_aec3())

    def panel_helper_aec3(self):
        """$AEC3: panel helper aec3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAEC3)
        index=self._dispatch(0xAEC3,(44750, 44916, 44939, 44984))
        return (yield from (self.panel_helper_aece,self.panel_helper_af74,self.panel_helper_af8b,self.panel_helper_afb8,)[index]())

    def panel_helper_aece(self):
        """$AECE: panel helper aece; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAECE)
        self._y(0x31)
        yield from self._external(0xAED0,0xF25F,0xAED3,"call",None)
        if r.pc!=0xAED3:return  # preserve nonlocal stack return
        self._a(0x74)
        m[0x0000]=r.a
        self._a(0x8D)
        m[0x0001]=r.a
        self._y(m[WORLD_CURSOR])
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0010]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._flag(C,False)
        self._add(0x60)
        m[0x0011]=r.a
        self._x(0x00)
        while True:  # natural loop $AEF0
            try:
                self._a(r.x)
                self._y(r.a)
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xAEF6)
                if r.p&Z:
                    self._a(0x03)
                    m[PHASE]=r.a
                    self._mark(0xAF1E)
                    self._rts();return
                else:
                    m[0x0012]=r.a
                    yield from self._external(0xAEFB,0xF2D7,0xAEFE,"call",None)
                    if r.pc!=0xAEFE:return  # preserve nonlocal stack return
                    self._y(0x0B)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._a(r.a & 0x03)
                    self._compare(r.a,0x01)
                    self._mark(0xAF06)
                    if r.p&Z:
                        self._x(r.x+1)
                        self._a(r.x)
                        self._y(r.a)
                        self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                        self._compare(r.a,m[0x6F00])
                        self._mark(0xAF15)
                        if r.p&Z:
                            self._y(0x01)
                            self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
                            yield from self._external(0xAF23,0xF2AF,0xAF26,"call",None)
                            if r.pc!=0xAF26:return  # preserve nonlocal stack return
                            self._y(0x11)
                            self._x(0x00)
                            while True:  # natural loop $AF2A
                                try:
                                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                    self._compare(r.a,0xFF)
                                    self._mark(0xAF2E)
                                    if r.p&Z:
                                        pass
                                    else:
                                        self._x(r.x+1)
                                        pass
                                    self._y(r.y+1)
                                    self._compare(r.y,0x1B)
                                    self._mark(0xAF34)
                                    if not r.p&C:
                                        continue
                                    else:
                                        pass
                                    self._compare(r.x,0x0A)
                                    self._mark(0xAF38)
                                    if r.p&Z:
                                        self._a(0x03)
                                        m[PHASE]=r.a
                                        self._mark(0xAF1E)
                                        self._rts();return
                                    else:
                                        self._a(r.x)
                                        self._flag(C,False)
                                        self._add(0x11)
                                        self._y(r.a)
                                        self._a(m[0x0012])
                                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                        self._a(m[0x0012])
                                        yield from self._external(0xAF47,0xF2D7,0xAF4A,"call",None)
                                        if r.pc!=0xAF4A:return  # preserve nonlocal stack return
                                        self._y(0x0B)
                                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                        self._a(r.a & 0xFC)
                                        self._a(r.a | 0x02)
                                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                        self._y(0x03)
                                        self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
                                        self._compare(r.a,0x03)
                                        self._mark(0xAF5A)
                                        if r.p&Z:
                                            self._a(0x03)
                                            m[PHASE]=r.a
                                            self._mark(0xAF1E)
                                            self._rts();return
                                        else:
                                            m[0x6F44]=r.a
                                            self._a(m[0x0012])
                                            m[0x042C]=r.a
                                            self._y(0x00)
                                            self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
                                            m[0x042D]=r.a
                                            m[CITY]=self._nz(m[CITY]+1)
                                            self._a(0x00)
                                            self._mark(0xAF71)
                                            yield from self._external(0xAF71,0xF28B,None,"tail")
                                            return
                                except _ContinueLoop_AF2A:
                                    continue
                        else:
                            self._mark(0xAF17)
                            if not r.p&C:
                                self._y(0x01)
                                self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
                                yield from self._external(0xAF23,0xF2AF,0xAF26,"call",None)
                                if r.pc!=0xAF26:return  # preserve nonlocal stack return
                                self._y(0x11)
                                self._x(0x00)
                                while True:  # natural loop $AF2A
                                    try:
                                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                        self._compare(r.a,0xFF)
                                        self._mark(0xAF2E)
                                        if r.p&Z:
                                            pass
                                        else:
                                            self._x(r.x+1)
                                            pass
                                        self._y(r.y+1)
                                        self._compare(r.y,0x1B)
                                        self._mark(0xAF34)
                                        if not r.p&C:
                                            continue
                                        else:
                                            pass
                                        self._compare(r.x,0x0A)
                                        self._mark(0xAF38)
                                        if r.p&Z:
                                            self._a(0x03)
                                            m[PHASE]=r.a
                                            self._mark(0xAF1E)
                                            self._rts();return
                                        else:
                                            self._a(r.x)
                                            self._flag(C,False)
                                            self._add(0x11)
                                            self._y(r.a)
                                            self._a(m[0x0012])
                                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                            self._a(m[0x0012])
                                            yield from self._external(0xAF47,0xF2D7,0xAF4A,"call",None)
                                            if r.pc!=0xAF4A:return  # preserve nonlocal stack return
                                            self._y(0x0B)
                                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                            self._a(r.a & 0xFC)
                                            self._a(r.a | 0x02)
                                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                            self._y(0x03)
                                            self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
                                            self._compare(r.a,0x03)
                                            self._mark(0xAF5A)
                                            if r.p&Z:
                                                self._a(0x03)
                                                m[PHASE]=r.a
                                                self._mark(0xAF1E)
                                                self._rts();return
                                            else:
                                                m[0x6F44]=r.a
                                                self._a(m[0x0012])
                                                m[0x042C]=r.a
                                                self._y(0x00)
                                                self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
                                                m[0x042D]=r.a
                                                m[CITY]=self._nz(m[CITY]+1)
                                                self._a(0x00)
                                                self._mark(0xAF71)
                                                yield from self._external(0xAF71,0xF28B,None,"tail")
                                                return
                                    except _ContinueLoop_AF2A:
                                        continue
                            else:
                                self._a(0x03)
                                m[PHASE]=r.a
                                self._mark(0xAF1E)
                                self._rts();return
                    else:
                        self._x(r.x+1)
                        self._x(r.x+1)
                        continue
            except _ContinueLoop_AEF0:
                continue

    def panel_helper_af74(self):
        """$AF74: panel helper af74; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAF74)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xAF79)
        if not r.p&Z:
            self._mark(0xAF8A)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xAF80)
            if not r.p&Z:
                self._mark(0xAF8A)
                self._rts();return
            else:
                m[CITY]=self._nz(m[CITY]+1)
                self._a(0x30)
                self._mark(0xAF87)
                yield from self._external(0xAF87,0xF26D,None,"tail")
                return

    def panel_helper_af8b(self):
        """$AF8B: panel helper af8b; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAF8B)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xAF90)
        if not r.p&Z:
            self._mark(0xAFA2)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xAF97)
            if not r.p&Z:
                self._mark(0xAFA2)
                self._rts();return
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xAF99,0xAF9C)):return
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xAFA0)
                if r.p&C:
                    self._a(m[0x042C])
                    m[0x0000]=r.a
                    self._y(0x3D)
                    yield from self._external(0xAFAB,0xEE07,0xAFB0,"far_call",41002)
                    if r.pc!=0xAFB0:return  # preserve nonlocal stack return
                    m[CITY]=self._nz(m[CITY]+1)
                    self._a(0x39)
                    self._mark(0xAFB5)
                    yield from self._external(0xAFB5,0xF26D,None,"tail")
                    return
                else:
                    self._mark(0xAFA2)
                    self._rts();return

    def panel_helper_afb8(self):
        """$AFB8: panel helper afb8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAFB8)
        self._a(m[0x042C])
        m[0x0000]=r.a
        self._a(0xA7)
        m[0x000A]=r.a
        self._x(0x00)
        yield from self._external(0xAFC5,0xCE1F,0xAFC8,"call",None)
        if r.pc!=0xAFC8:return  # preserve nonlocal stack return
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xAFCD)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xAFD4)
            if not r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xAFD6,0xAFD9)):return
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xAFDD)
                if not r.p&C:
                    pass
                else:
                    self._a(0x03)
                    m[PHASE]=r.a
                    pass
                pass
            pass
        self._mark(0xAFE4)
        self._rts();return

    def prepare_battle_departure(self):
        """$B7D9: prepare battle departure; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB7D9)
        self._a(m[CURRENT_CITY])
        yield from self._external(0xB7DC,0xF2AF,0xB7DF,"call",None)
        if r.pc!=0xB7DF:return  # preserve nonlocal stack return
        self._y(0x02)
        self._x(0x26)
        while True:  # natural loop $B7E3
            try:
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[(0x0500+r.x)&65535]=r.a
                self._a(0x00)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._x(r.x+1)
                self._compare(r.x,0x28)
                self._mark(0xB7F0)
                if not r.p&Z:
                    pass
                else:
                    self._x(0x22)
                    pass
                self._compare(r.y,0x06)
                self._mark(0xB7F6)
                if not r.p&C:
                    continue
                else:
                    pass
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x0507]=r.a
                self._a(m[0x0000])
                self._flag(C,False)
                self._add(0x11)
                m[0x0000]=r.a
                self._a(m[0x0001])
                self._add(0x00)
                m[0x0001]=r.a
                self._y(0x09)
                while True:  # natural loop $B812
                    try:
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        m[(0x0664+r.y)&65535]=r.a
                        self._a(0xFF)
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._y(r.y-1)
                        self._mark(0xB81C)
                        if not r.p&N:
                            continue
                        else:
                            pass
                        self._y(0x0A)
                        self._a(m[0x0481])
                        m[(0x0664+r.y)&65535]=r.a
                        self._y(r.y+1)
                        self._x(0x00)
                        while True:  # natural loop $B829
                            try:
                                self._compare(r.x,0x0A)
                                self._mark(0xB82B)
                                if not r.p&C:
                                    self._a(m[(0x0151+r.x)&65535])
                                    self._compare(r.a,m[0x0481])
                                    self._mark(0xB838)
                                    if r.p&Z:
                                        pass
                                    else:
                                        m[(0x0664+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        pass
                                    pass
                                else:
                                    self._a(0xFF)
                                    m[(0x0664+r.y)&65535]=r.a
                                    self._y(r.y+1)
                                    pass
                                self._x(r.x+1)
                                self._compare(r.y,0x14)
                                self._mark(0xB841)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._a(m[CITY])
                                yield from self._external(0xB846,0xF2AF,0xB849,"call",None)
                                if r.pc!=0xB849:return  # preserve nonlocal stack return
                                self._y(0x00)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._a(r.a | m[0x0507])
                                m[0x0507]=r.a
                                self._x(0x00)
                                return (yield from self.remove_departing_roster_ids())
                            except _ContinueLoop_B829:
                                continue
                    except _ContinueLoop_B812:
                        continue
            except _ContinueLoop_B7E3:
                continue

    def remove_departing_roster_ids(self):
        """B859..B878: remove up to ten selected0151 IDs from the city roster.

        The original inner search has no sentinel test. Caller roster validity
        determines termination; byte-index wrapping is preserved.
        """
        r=self.registers;m=self.memory
        while True:
            self._mark(0xB859);self._a(m[(0x151+r.x)&65535]);self._compare(r.a,255)
            if r.p&Z:break
            m[2]=r.a;self._y(17)
            while True:
                self._mark(0xB865);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,m[2])
                if r.p&Z:break
                self._y(r.y+1)
            self._a(255);m[((m[0]|m[1]<<8)+r.y)&65535]=r.a
            self._x(r.x+1);self._compare(r.x,10)
            if r.p&C:break
        yield from self.compact_departure_city_roster()

    def compact_departure_city_roster(self):
        """$B879: compact departure city roster; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB879)
        self._y(0x11)
        self._a(0x10)
        m[0x0003]=r.a
        while True:  # natural loop $B880
            try:
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x0002]=r.a
                self._a(0xFF)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._a(m[0x0002])
                self._compare(r.a,0xFF)
                self._mark(0xB88E)
                if r.p&Z:
                    pass
                else:
                    self._a(r.y)
                    self._x(r.a)
                    m[0x0003]=self._nz(m[0x0003]+1)
                    self._y(m[0x0003])
                    self._a(m[0x0002])
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._a(r.x)
                    self._y(r.a)
                    pass
                self._y(r.y+1)
                self._compare(r.y,0x1B)
                self._mark(0xB8A2)
                if not r.p&C:
                    continue
                else:
                    pass
                self._y(0x11)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xB8AA)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x07)
                    self._y(0x00)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    pass
                self._y(0x02)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,True)
                self._add(m[0x042F],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._add(m[0x0430],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(0x04)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,True)
                self._add(m[0x0432],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._add(m[0x0433],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._mark(0xB8D6)
                self._rts();return
            except _ContinueLoop_B880:
                continue

    def panel_helper_b8d7(self):
        """$B8D7: panel helper b8d7; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB8D7)
        self._a(m[WORLD_CURSOR])
        yield from self._external(0xB8DA,0xF2AF,0xB8DD,"call",None)
        if r.pc!=0xB8DD:return  # preserve nonlocal stack return
        self._y(0x02)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0498]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0499]=r.a
        self._y(0x04)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x049A]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x049B]=r.a
        self._y(0x10)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x049C]=r.a
        self._a(0x00)
        m[0x049D]=r.a
        self._a(m[CURRENT_CITY])
        yield from self._external(0xB906,0xF2AF,0xB909,"call",None)
        if r.pc!=0xB909:return  # preserve nonlocal stack return
        self._y(0x02)
        self._a(0x0F)
        self._flag(C,True)
        self._add(m[((m[0x00]|m[0x01]<<8)+r.y)&65535],subtract=True)
        m[0x0010]=r.a
        self._y(r.y+1)
        self._a(0x27)
        self._add(m[((m[0x00]|m[0x01]<<8)+r.y)&65535],subtract=True)
        m[0x0011]=r.a
        self._y(0x00)
        if not (yield from self._local_call(self.panel_helper_b948,0xB91D,0xB920)):return
        self._y(0x04)
        self._a(0x0F)
        self._flag(C,True)
        self._add(m[((m[0x00]|m[0x01]<<8)+r.y)&65535],subtract=True)
        m[0x0010]=r.a
        self._y(r.y+1)
        self._a(0x27)
        self._add(m[((m[0x00]|m[0x01]<<8)+r.y)&65535],subtract=True)
        m[0x0011]=r.a
        self._y(0x02)
        if not (yield from self._local_call(self.panel_helper_b948,0xB934,0xB937)):return
        self._y(0x10)
        self._a(0x63)
        self._flag(C,True)
        self._add(m[((m[0x00]|m[0x01]<<8)+r.y)&65535],subtract=True)
        m[0x0010]=r.a
        self._a(0x00)
        m[0x0011]=r.a
        self._y(0x04)
        return (yield from self.panel_helper_b948())

    def panel_helper_b948(self):
        """$B948: panel helper b948; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB948)
        self._a(m[0x0010])
        self._flag(C,True)
        self._add(m[(0x0498+r.y)&65535],subtract=True)
        self._a(m[0x0011])
        self._add(m[(0x0499+r.y)&65535],subtract=True)
        self._mark(0xB955)
        if r.p&C:
            pass
        else:
            self._a(m[0x0010])
            m[(0x0498+r.y)&65535]=r.a
            self._a(m[0x0011])
            m[(0x0499+r.y)&65535]=r.a
            pass
        self._mark(0xB963)
        self._rts();return

    def new_officer_event(self):
        """$B964: new officer event; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB964)
        self._y(0x31)
        yield from self._external(0xB966,0xF25F,0xB969,"call",None)
        if r.pc!=0xB969:return  # preserve nonlocal stack return
        self._a(m[CITY])
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0002]=r.a
        self._a(0x14)
        m[0x0003]=r.a
        yield from self._external(0xB97C,0xEBE9,0xB97F,"call",None)
        if r.pc!=0xB97F:return  # preserve nonlocal stack return
        self._a(m[0x0006])
        self._flag(C,False)
        self._add(0x1C)
        m[0x0002]=r.a
        self._a(m[0x0007])
        self._add(0x8B)
        m[0x0003]=r.a
        self._a(0x00)
        m[0x0004]=r.a
        while True:  # natural loop $B995
            try:
                self._y(m[0x0004])
                self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
                m[0x0472]=r.a
                self._compare(r.a,0xFF)
                self._mark(0xB99F)
                if not r.p&Z:
                    yield from self._external(0xB9A4,0xF2D7,0xB9A7,"call",None)
                    if r.pc!=0xB9A7:return  # preserve nonlocal stack return
                    self._y(0x0B)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._a(r.a & 0x03)
                    self._compare(r.a,0x01)
                    self._mark(0xB9AF)
                    if r.p&Z:
                        m[0x0004]=self._nz(m[0x0004]+1)
                        self._y(m[0x0004])
                        self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
                        self._flag(C,True)
                        self._add(0x64,subtract=True)
                        self._compare(r.a,m[0x6F00])
                        self._mark(0xB9C8)
                        if r.p&Z:
                            self._y(0x00)
                            while True:  # natural loop $B9CE
                                try:
                                    self._a(m[(0xBA50+r.y)&65535])
                                    self._compare(r.a,m[0x0472])
                                    self._mark(0xB9D4)
                                    if r.p&Z:
                                        self._y(r.y+1)
                                        self._a(m[(0xBA50+r.y)&65535])
                                        m[0x0473]=r.a
                                        self._a(0x07)
                                        m[WORLD_CURSOR]=r.a
                                        self._mark(0xB9E9)
                                        self._rts();return
                                    else:
                                        self._y(r.y+1)
                                        self._y(r.y+1)
                                        self._compare(r.y,0x24)
                                        self._mark(0xB9DA)
                                        if not r.p&C:
                                            continue
                                        else:
                                            self._mark(0xB9DC)
                                            self._rts();return
                                except _ContinueLoop_B9CE:
                                    continue
                        else:
                            self._mark(0xB9CA)
                            if r.p&C:
                                self._y(0x30)
                                yield from self._external(0xB9EC,0xF25F,0xB9EF,"call",None)
                                if r.pc!=0xB9EF:return  # preserve nonlocal stack return
                                self._a(m[CITY])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._y(r.a)
                                self._x(0x00)
                                while True:  # natural loop $B9F8
                                    try:
                                        self._a(m[(0x9D72+r.y)&65535])
                                        m[(0x0160+r.x)&65535]=r.a
                                        self._y(r.y+1)
                                        self._x(r.x+1)
                                        self._compare(r.x,0x08)
                                        self._mark(0xBA02)
                                        if not r.p&C:
                                            continue
                                        else:
                                            pass
                                        self._y(0x31)
                                        yield from self._external(0xBA06,0xF25F,0xBA09,"call",None)
                                        if r.pc!=0xBA09:return  # preserve nonlocal stack return
                                        self._a(0x00)
                                        m[0x0004]=r.a
                                        while True:  # natural loop $BA0E
                                            try:
                                                self._a(m[0x0004])
                                                yield from self._external(0xBA11,0xF2D7,0xBA14,"call",None)
                                                if r.pc!=0xBA14:return  # preserve nonlocal stack return
                                                self._y(0x0B)
                                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                                self._a(r.a & 0x03)
                                                self._mark(0xBA1A)
                                                if r.p&Z:
                                                    self._a(m[0x0004])
                                                    m[0x0472]=r.a
                                                    self._y(0x05)
                                                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                                    self._compare(r.a,m[CITY])
                                                    self._mark(0xBA39)
                                                    if r.p&Z:
                                                        pass
                                                    else:
                                                        m[0x0005]=r.a
                                                        self._x(0x00)
                                                        while True:  # natural loop $BA40
                                                            try:
                                                                self._a(m[(0x0160+r.x)&65535])
                                                                self._compare(r.a,m[0x0005])
                                                                self._mark(0xBA46)
                                                                if r.p&Z:
                                                                    pass
                                                                else:
                                                                    self._x(r.x+1)
                                                                    self._compare(r.x,0x08)
                                                                    self._mark(0xBA4B)
                                                                    if not r.p&C:
                                                                        continue
                                                                    else:
                                                                        m[0x0004]=self._nz(m[0x0004]+1)
                                                                        self._a(m[0x0004])
                                                                        self._compare(r.a,0xED)
                                                                        self._mark(0xBA24)
                                                                        if not r.p&C:
                                                                            raise _ContinueLoop_BA0E
                                                                        else:
                                                                            self._a(0x80)
                                                                            m[0x0011]=r.a
                                                                            pass
                                                                        pass
                                                                    pass
                                                                self._mark(0xBA2B)
                                                                self._rts();return
                                                            except _ContinueLoop_BA40:
                                                                continue
                                                    pass
                                                else:
                                                    m[0x0004]=self._nz(m[0x0004]+1)
                                                    self._a(m[0x0004])
                                                    self._compare(r.a,0xED)
                                                    self._mark(0xBA24)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        self._a(0x80)
                                                        m[0x0011]=r.a
                                                        pass
                                                    pass
                                                self._mark(0xBA2B)
                                                self._rts();return
                                            except _ContinueLoop_BA0E:
                                                continue
                                    except _ContinueLoop_B9F8:
                                        continue
                            else:
                                self._y(0x00)
                                while True:  # natural loop $B9CE
                                    try:
                                        self._a(m[(0xBA50+r.y)&65535])
                                        self._compare(r.a,m[0x0472])
                                        self._mark(0xB9D4)
                                        if r.p&Z:
                                            self._y(r.y+1)
                                            self._a(m[(0xBA50+r.y)&65535])
                                            m[0x0473]=r.a
                                            self._a(0x07)
                                            m[WORLD_CURSOR]=r.a
                                            self._mark(0xB9E9)
                                            self._rts();return
                                        else:
                                            self._y(r.y+1)
                                            self._y(r.y+1)
                                            self._compare(r.y,0x24)
                                            self._mark(0xB9DA)
                                            if not r.p&C:
                                                continue
                                            else:
                                                self._mark(0xB9DC)
                                                self._rts();return
                                    except _ContinueLoop_B9CE:
                                        continue
                    else:
                        m[0x0004]=self._nz(m[0x0004]+1)
                        m[0x0004]=self._nz(m[0x0004]+1)
                        continue
                else:
                    self._y(0x30)
                    yield from self._external(0xB9EC,0xF25F,0xB9EF,"call",None)
                    if r.pc!=0xB9EF:return  # preserve nonlocal stack return
                    self._a(m[CITY])
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    self._y(r.a)
                    self._x(0x00)
                    while True:  # natural loop $B9F8
                        try:
                            self._a(m[(0x9D72+r.y)&65535])
                            m[(0x0160+r.x)&65535]=r.a
                            self._y(r.y+1)
                            self._x(r.x+1)
                            self._compare(r.x,0x08)
                            self._mark(0xBA02)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            self._y(0x31)
                            yield from self._external(0xBA06,0xF25F,0xBA09,"call",None)
                            if r.pc!=0xBA09:return  # preserve nonlocal stack return
                            self._a(0x00)
                            m[0x0004]=r.a
                            while True:  # natural loop $BA0E
                                try:
                                    self._a(m[0x0004])
                                    yield from self._external(0xBA11,0xF2D7,0xBA14,"call",None)
                                    if r.pc!=0xBA14:return  # preserve nonlocal stack return
                                    self._y(0x0B)
                                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                    self._a(r.a & 0x03)
                                    self._mark(0xBA1A)
                                    if r.p&Z:
                                        self._a(m[0x0004])
                                        m[0x0472]=r.a
                                        self._y(0x05)
                                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                        self._compare(r.a,m[CITY])
                                        self._mark(0xBA39)
                                        if r.p&Z:
                                            pass
                                        else:
                                            m[0x0005]=r.a
                                            self._x(0x00)
                                            while True:  # natural loop $BA40
                                                try:
                                                    self._a(m[(0x0160+r.x)&65535])
                                                    self._compare(r.a,m[0x0005])
                                                    self._mark(0xBA46)
                                                    if r.p&Z:
                                                        pass
                                                    else:
                                                        self._x(r.x+1)
                                                        self._compare(r.x,0x08)
                                                        self._mark(0xBA4B)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            m[0x0004]=self._nz(m[0x0004]+1)
                                                            self._a(m[0x0004])
                                                            self._compare(r.a,0xED)
                                                            self._mark(0xBA24)
                                                            if not r.p&C:
                                                                raise _ContinueLoop_BA0E
                                                            else:
                                                                self._a(0x80)
                                                                m[0x0011]=r.a
                                                                pass
                                                            pass
                                                        pass
                                                    self._mark(0xBA2B)
                                                    self._rts();return
                                                except _ContinueLoop_BA40:
                                                    continue
                                        pass
                                    else:
                                        m[0x0004]=self._nz(m[0x0004]+1)
                                        self._a(m[0x0004])
                                        self._compare(r.a,0xED)
                                        self._mark(0xBA24)
                                        if not r.p&C:
                                            continue
                                        else:
                                            self._a(0x80)
                                            m[0x0011]=r.a
                                            pass
                                        pass
                                    self._mark(0xBA2B)
                                    self._rts();return
                                except _ContinueLoop_BA0E:
                                    continue
                        except _ContinueLoop_B9F8:
                            continue
            except _ContinueLoop_B995:
                continue

    def panel_helper_ba70(self):
        """$BA70: panel helper ba70; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBA70)
        self._x(0x7F)
        self._a(m[WORLD_CURSOR])
        self._mark(0xBA75)
        if r.p&Z:
            pass
        else:
            self._x(0x88)
            self._compare(r.a,0x01)
            self._mark(0xBA7B)
            if r.p&Z:
                pass
            else:
                self._x(0x91)
                pass
            pass
        m[CURRENT_CITY]=r.x
        while True:  # natural loop $BA82
            try:
                yield from self._external(0xBA82,0xE856,0xBA85,"call",None)
                if r.pc!=0xBA85:return  # preserve nonlocal stack return
                self._compare(r.a,0x05)
                self._mark(0xBA87)
                if r.p&C:
                    continue
                else:
                    pass
                m[0x0010]=r.a
                self._a(m[0x0481])
                yield from self._external(0xBA8F,0xF2D7,0xBA92,"call",None)
                if r.pc!=0xBA92:return  # preserve nonlocal stack return
                self._y(0x02)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,0x51)
                self._mark(0xBA98)
                if r.p&C:
                    self._a(m[0x0010])
                    self._flag(C,False)
                    self._add(0x04)
                    m[0x0010]=r.a
                    pass
                else:
                    self._compare(r.a,0x33)
                    self._mark(0xBA9C)
                    if r.p&C:
                        self._a(m[0x0010])
                        self._flag(C,False)
                        self._add(0x02)
                        m[0x0010]=r.a
                        pass
                    else:
                        pass
                    pass
                self._a(m[0x0010])
                self._flag(C,False)
                self._add(m[CURRENT_CITY])
                m[CURRENT_CITY]=r.a
                self._y(m[0x0010])
                self._a(m[(0xBADF+r.y)&65535])
                m[0x0472]=r.a
                self._a(m[WORLD_CURSOR])
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._flag(C,False)
                self._add(m[WORLD_CURSOR])
                self._flag(C,False)
                self._add(m[0x0010])
                self._y(r.a)
                self._a(m[(0xBAE8+r.y)&65535])
                m[0x04A2]=r.a
                self._mark(0xBADE)
                self._rts();return
            except _ContinueLoop_BA82:
                continue

    def panel_helper_bb03(self):
        """$BB03: panel helper bb03; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBB03)
        self._a(m[CITY])
        yield from self._external(0xBB06,0xF2AF,0xBB09,"call",None)
        if r.pc!=0xBB09:return  # preserve nonlocal stack return
        self._y(0x02)
        while True:  # natural loop $BB0B
            try:
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[(0x0000+r.y)&65535]=r.a
                self._y(r.y+1)
                self._compare(r.y,0x05)
                self._mark(0xBB13)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x0002])
                self._flag(C,True)
                self._add(m[0x0004],subtract=True)
                m[0x0006]=r.a
                self._a(m[0x0003])
                self._add(m[0x0005],subtract=True)
                self._mark(0xBB25)
                if not r.p&C:
                    self._y(0x07)
                    pass
                else:
                    self._mark(0xBB27)
                    if not r.p&Z:
                        self._y(0x03)
                        pass
                    else:
                        self._a(m[0x0006])
                        self._mark(0xBB2C)
                        if r.p&Z:
                            pass
                        else:
                            self._y(0x03)
                            pass
                        pass
                    pass
                m[0x042D]=r.y
                self._y(0xF0)
                self._a(0x0A)
                yield from self._external(0xBB3C,0xE862,0xBB3F,"call",None)
                if r.pc!=0xBB3F:return  # preserve nonlocal stack return
                self._compare(r.a,m[0x042D])
                self._mark(0xBB42)
                if not r.p&C:
                    pass
                else:
                    self._y(r.y+1)
                    pass
                m[0x042D]=r.y
                self._a(0x64)
                self._flag(C,True)
                self._add(m[0x042F],subtract=True)
                m[0x0000]=r.a
                self._a(0x00)
                m[0x0001]=r.a
                m[0x0002]=r.a
                self._a(0x04)
                m[0x0003]=r.a
                yield from self._external(0xBB5E,0xEBE9,0xBB61,"call",None)
                if r.pc!=0xBB61:return  # preserve nonlocal stack return
                self._a(m[0x0006])
                m[0x042F]=r.a
                self._a(m[0x0007])
                m[0x0430]=r.a
                self._a(0x00)
                m[0x0431]=r.a
                self._mark(0xBB72)
                self._rts();return
            except _ContinueLoop_BB0B:
                continue

    def panel_helper_bb73(self):
        """$BB73: panel helper bb73; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBB73)
        self._a(m[CITY])
        yield from self._external(0xBB76,0xF2AF,0xBB79,"call",None)
        if r.pc!=0xBB79:return  # preserve nonlocal stack return
        self._y(0x02)
        self._a(m[0x042D])
        self._compare(r.a,0xF0)
        self._mark(0xBB80)
        if r.p&Z:
            pass
        else:
            self._y(0x04)
            pass
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(m[0x042F],subtract=True)
        m[0x0002]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._add(m[0x0430],subtract=True)
        self._mark(0xBB93)
        if r.p&C:
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._y(r.y-1)
            self._a(m[0x0002])
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._a(m[0x042C])
            m[0x000A]=r.a
            if not (yield from self._local_call(self.find_officer_city,0xBBAF,0xBBB2)):return
            self._y(0x02)
            self._a(m[0x042D])
            self._compare(r.a,0xF0)
            self._mark(0xBBB9)
            if r.p&Z:
                pass
            else:
                self._y(0x04)
                pass
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._flag(C,False)
            self._add(m[0x042F])
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._y(r.y+1)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._add(m[0x0430])
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._a(m[0x0000])
            m[0x0010]=r.a
            self._a(m[0x0001])
            m[0x0011]=r.a
            self._y(r.y-1)
            if not (yield from self._local_call(self.panel_helper_a52a,0xBBDA,0xBBDD)):return
            self._mark(0xBBDD)
            self._rts();return
        else:
            self._a(m[0x042D])
            m[0x042E]=r.a
            self._a(0x00)
            m[0x042D]=r.a
            self._mark(0xBBA0)
            self._rts();return

    def calendar_header(self):
        """$BBDE: calendar header; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBBDE)
        self._a(m[0x04E4])
        self._mark(0xBBE1)
        if not r.p&Z:
            self._a(m[CITY])
            return (yield from self.panel_helper_bbe7())
        else:
            self._mark(0xBBE3)
            self._rts();return

    def panel_helper_bbe7(self):
        """$BBE7: panel helper bbe7; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBBE7)
        self._push(r.a)
        self._a(r.a & 0x07)
        self._x(r.a)
        self._a(self._pop())
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._y(r.a)
        self._a(m[(0x04E0+r.y)&65535])
        self._a(r.a | m[(0xBBFA+r.x)&65535])
        m[(0x04E0+r.y)&65535]=r.a
        self._mark(0xBBF9)
        self._rts();return

    def panel_helper_bc02(self):
        """$BC02: panel helper bc02; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBC02)
        self._a(0x40)
        m[0x00A5]=r.a
        m[0xF800]=r.a
        self._a(0x49)
        m[0x6FFC]=r.a
        self._a(0x44)
        m[0x6FFD]=r.a
        self._a(0x00)
        m[0x0000]=r.a
        m[0x0002]=r.a
        m[0x0004]=r.a
        m[0x0005]=r.a
        self._a(0x60)
        m[0x0001]=r.a
        self._a(0x70)
        m[0x0003]=r.a
        while True:  # natural loop $BC2C
            try:
                self._y(0x00)
                while True:  # natural loop $BC2E
                    try:
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        m[((m[0x02]|m[0x03]<<8)+r.y)&65535]=r.a
                        self._flag(C,False)
                        self._add(m[0x0004])
                        m[0x0004]=r.a
                        self._a(m[0x0005])
                        self._add(0x00)
                        m[0x0005]=r.a
                        self._y(r.y+1)
                        self._mark(0xBC42)
                        if not r.p&Z:
                            continue
                        else:
                            pass
                        m[0x0001]=self._nz(m[0x0001]+1)
                        m[0x0003]=self._nz(m[0x0003]+1)
                        self._a(m[0x0001])
                        self._compare(r.a,0x6F)
                        self._mark(0xBC4F)
                        if not r.p&C:
                            raise _ContinueLoop_BC2C
                        else:
                            pass
                        self._y(0x00)
                        while True:  # natural loop $BC53
                            try:
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                m[((m[0x02]|m[0x03]<<8)+r.y)&65535]=r.a
                                self._flag(C,False)
                                self._add(m[0x0004])
                                m[0x0004]=r.a
                                self._a(m[0x0005])
                                self._add(0x00)
                                m[0x0005]=r.a
                                self._y(r.y+1)
                                self._compare(r.y,0xFE)
                                self._mark(0xBC69)
                                if not r.p&Z:
                                    continue
                                else:
                                    pass
                                self._a(m[0x0004])
                                m[0x7FFE]=r.a
                                self._a(m[0x0005])
                                m[0x7FFF]=r.a
                                self._a(0x4C)
                                m[0x00A5]=r.a
                                m[0xF800]=r.a
                                self._mark(0xBC7F)
                                self._rts();return
                            except _ContinueLoop_BC53:
                                continue
                    except _ContinueLoop_BC2E:
                        continue
            except _ContinueLoop_BC2C:
                continue

    def panel_helper_bc80(self):
        """$BC80: panel helper bc80; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBC80)
        self._a(m[CITY])
        return (yield from self.panel_helper_bc83())

    def panel_helper_bc83(self):
        """$BC83: panel helper bc83; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBC83)
        index=self._dispatch(0xBC83,(48268, 48277, 48487))
        return (yield from (self.panel_helper_bc8c,self.panel_helper_bc95,self.panel_helper_bd67,)[index]())

    def panel_helper_bc8c(self):
        """$BC8C: panel helper bc8c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBC8C)
        self._a(0x00)
        m[0x0408]=r.a
        m[CITY]=self._nz(m[CITY]+1)
        self._mark(0xBC94)
        self._rts();return

    def panel_helper_bc95(self):
        """$BC95: panel helper bc95; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        while True:  # natural loop $BC95
            try:
                self._mark(0xBC95)
                self._a(m[0x0408])
                yield from self._external(0xBC98,0xF2AF,0xBC9B,"call",None)
                if r.pc!=0xBC9B:return  # preserve nonlocal stack return
                self._a(m[0x0000])
                m[0x001C]=r.a
                self._a(m[0x0001])
                m[0x001D]=r.a
                self._y(0x00)
                self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                self._a(r.a & 0x07)
                self._compare(r.a,m[0x6F03])
                self._mark(0xBCB0)
                if not r.p&Z:
                    m[0x0408]=self._nz(m[0x0408]+1)
                    self._a(m[0x0408])
                    self._compare(r.a,0x1E)
                    self._mark(0xBD06)
                    if not r.p&C:
                        continue
                    else:
                        self._a(m[0x040B])
                        m[0x040A]=r.a
                        self._a(m[0x001E])
                        m[0x0408]=r.a
                        self._a(m[0x001F])
                        m[0x0409]=r.a
                        if not (yield from self._local_call(self.panel_helper_bd28,0xBD1A,0xBD1D)):return
                        self._a(0x04)
                        m[PHASE]=r.a
                        self._a(0x00)
                        m[CITY]=r.a
                        self._mark(0xBD27)
                        self._rts();return
                else:
                    self._y(0x11)
                    m[0x0409]=r.y
                    while True:  # natural loop $BCB7
                        try:
                            self._y(m[0x0409])
                            self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                            self._compare(r.a,0xFF)
                            self._mark(0xBCBE)
                            if r.p&Z:
                                m[0x0409]=self._nz(m[0x0409]+1)
                                self._a(m[0x0409])
                                self._compare(r.a,0x1B)
                                self._mark(0xBCFC)
                                if not r.p&C:
                                    continue
                                else:
                                    m[0x0408]=self._nz(m[0x0408]+1)
                                    self._a(m[0x0408])
                                    self._compare(r.a,0x1E)
                                    self._mark(0xBD06)
                                    if not r.p&C:
                                        raise _ContinueLoop_BC95
                                    else:
                                        self._a(m[0x040B])
                                        m[0x040A]=r.a
                                        self._a(m[0x001E])
                                        m[0x0408]=r.a
                                        self._a(m[0x001F])
                                        m[0x0409]=r.a
                                        if not (yield from self._local_call(self.panel_helper_bd28,0xBD1A,0xBD1D)):return
                                        self._a(0x04)
                                        m[PHASE]=r.a
                                        self._a(0x00)
                                        m[CITY]=r.a
                                        self._mark(0xBD27)
                                        self._rts();return
                            else:
                                self._compare(r.a,m[0x040B])
                                self._mark(0xBCC3)
                                if not r.p&Z:
                                    m[0x040A]=r.a
                                    if not (yield from self._local_call(self.panel_helper_bd28,0xBCD7,0xBCDA)):return
                                    self._mark(0xBCDA)
                                    if not r.p&C:
                                        m[0x0409]=self._nz(m[0x0409]+1)
                                        self._a(m[0x0409])
                                        self._compare(r.a,0x1B)
                                        self._mark(0xBCFC)
                                        if not r.p&C:
                                            continue
                                        else:
                                            m[0x0408]=self._nz(m[0x0408]+1)
                                            self._a(m[0x0408])
                                            self._compare(r.a,0x1E)
                                            self._mark(0xBD06)
                                            if not r.p&C:
                                                raise _ContinueLoop_BC95
                                            else:
                                                self._a(m[0x040B])
                                                m[0x040A]=r.a
                                                self._a(m[0x001E])
                                                m[0x0408]=r.a
                                                self._a(m[0x001F])
                                                m[0x0409]=r.a
                                                if not (yield from self._local_call(self.panel_helper_bd28,0xBD1A,0xBD1D)):return
                                                self._a(0x04)
                                                m[PHASE]=r.a
                                                self._a(0x00)
                                                m[CITY]=r.a
                                                self._mark(0xBD27)
                                                self._rts();return
                                    else:
                                        self._y(0x03)
                                        self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
                                        self._a(r.a & 0x03)
                                        self._compare(r.a,0x03)
                                        self._mark(0xBCE4)
                                        if r.p&Z:
                                            m[0x0409]=self._nz(m[0x0409]+1)
                                            self._a(m[0x0409])
                                            self._compare(r.a,0x1B)
                                            self._mark(0xBCFC)
                                            if not r.p&C:
                                                continue
                                            else:
                                                m[0x0408]=self._nz(m[0x0408]+1)
                                                self._a(m[0x0408])
                                                self._compare(r.a,0x1E)
                                                self._mark(0xBD06)
                                                if not r.p&C:
                                                    raise _ContinueLoop_BC95
                                                else:
                                                    self._a(m[0x040B])
                                                    m[0x040A]=r.a
                                                    self._a(m[0x001E])
                                                    m[0x0408]=r.a
                                                    self._a(m[0x001F])
                                                    m[0x0409]=r.a
                                                    if not (yield from self._local_call(self.panel_helper_bd28,0xBD1A,0xBD1D)):return
                                                    self._a(0x04)
                                                    m[PHASE]=r.a
                                                    self._a(0x00)
                                                    m[CITY]=r.a
                                                    self._mark(0xBD27)
                                                    self._rts();return
                                        else:
                                            m[CITY]=self._nz(m[CITY]+1)
                                            self._a(m[0x040A])
                                            m[0x042C]=r.a
                                            self._a(0xC1)
                                            self._mark(0xBCF1)
                                            yield from self._external(0xBCF1,0xF28B,None,"tail")
                                            return
                                else:
                                    self._a(m[0x0408])
                                    m[0x001E]=r.a
                                    self._a(m[0x0409])
                                    m[0x001F]=r.a
                                    m[0x0409]=self._nz(m[0x0409]+1)
                                    self._a(m[0x0409])
                                    self._compare(r.a,0x1B)
                                    self._mark(0xBCFC)
                                    if not r.p&C:
                                        continue
                                    else:
                                        m[0x0408]=self._nz(m[0x0408]+1)
                                        self._a(m[0x0408])
                                        self._compare(r.a,0x1E)
                                        self._mark(0xBD06)
                                        if not r.p&C:
                                            raise _ContinueLoop_BC95
                                        else:
                                            self._a(m[0x040B])
                                            m[0x040A]=r.a
                                            self._a(m[0x001E])
                                            m[0x0408]=r.a
                                            self._a(m[0x001F])
                                            m[0x0409]=r.a
                                            if not (yield from self._local_call(self.panel_helper_bd28,0xBD1A,0xBD1D)):return
                                            self._a(0x04)
                                            m[PHASE]=r.a
                                            self._a(0x00)
                                            m[CITY]=r.a
                                            self._mark(0xBD27)
                                            self._rts();return
                        except _ContinueLoop_BCB7:
                            continue
            except _ContinueLoop_BC95:
                continue

    def panel_helper_bd28(self):
        """$BD28: panel helper bd28; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBD28)
        self._y(0x31)
        yield from self._external(0xBD2A,0xF25F,0xBD2D,"call",None)
        if r.pc!=0xBD2D:return  # preserve nonlocal stack return
        self._a(0x58)
        m[0x0002]=r.a
        self._a(0x9C)
        m[0x0003]=r.a
        self._y(m[0x040A])
        self._a(m[0x6F00])
        self._flag(C,True)
        self._add(m[((m[0x02]|m[0x03]<<8)+r.y)&65535],subtract=True)
        self._mark(0xBD40)
        if not r.p&C:
            self._flag(C,False)
            self._mark(0xBD5A)
            self._rts();return
        else:
            self._compare(r.a,0x06)
            self._mark(0xBD44)
            if not r.p&C:
                pass
            else:
                self._a(0x06)
                pass
            self._y(r.a)
            self._a(m[(0xBD60+r.y)&65535])
            m[0x000C]=r.a
            self._a(0xC8)
            yield from self._external(0xBD51,0xE862,0xBD54,"call",None)
            if r.pc!=0xBD54:return  # preserve nonlocal stack return
            self._compare(r.a,m[0x000C])
            self._mark(0xBD57)
            if not r.p&C:
                if not (yield from self._local_call(self.panel_helper_bdbb,0xBD5B,0xBD5E)):return
                self._flag(C,True)
                self._mark(0xBD5F)
                self._rts();return
            else:
                self._flag(C,False)
                self._mark(0xBD5A)
                self._rts();return

    def panel_helper_bd67(self):
        """$BD67: panel helper bd67; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBD67)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xBD6C)
        if not r.p&Z:
            self._mark(0xBD85)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xBD73)
            if not r.p&Z:
                self._mark(0xBD85)
                self._rts();return
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xBD75,0xBD78)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                self._mark(0xBD7D)
                if r.p&Z:
                    self._mark(0xBD85)
                    self._rts();return
                else:
                    m[CITY]=self._nz(m[CITY]-1)
                    while True:  # natural loop $BCF4
                        try:
                            m[0x0409]=self._nz(m[0x0409]+1)
                            self._a(m[0x0409])
                            self._compare(r.a,0x1B)
                            self._mark(0xBCFC)
                            if not r.p&C:
                                self._y(m[0x0409])
                                self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                self._compare(r.a,0xFF)
                                self._mark(0xBCBE)
                                if r.p&Z:
                                    continue
                                else:
                                    self._compare(r.a,m[0x040B])
                                    self._mark(0xBCC3)
                                    if not r.p&Z:
                                        m[0x040A]=r.a
                                        if not (yield from self._local_call(self.panel_helper_bd28,0xBCD7,0xBCDA)):return
                                        self._mark(0xBCDA)
                                        if not r.p&C:
                                            continue
                                        else:
                                            self._y(0x03)
                                            self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
                                            self._a(r.a & 0x03)
                                            self._compare(r.a,0x03)
                                            self._mark(0xBCE4)
                                            if r.p&Z:
                                                continue
                                            else:
                                                m[CITY]=self._nz(m[CITY]+1)
                                                self._a(m[0x040A])
                                                m[0x042C]=r.a
                                                self._a(0xC1)
                                                self._mark(0xBCF1)
                                                yield from self._external(0xBCF1,0xF28B,None,"tail")
                                                return
                                    else:
                                        self._a(m[0x0408])
                                        m[0x001E]=r.a
                                        self._a(m[0x0409])
                                        m[0x001F]=r.a
                                        continue
                            else:
                                m[0x0408]=self._nz(m[0x0408]+1)
                                self._a(m[0x0408])
                                self._compare(r.a,0x1E)
                                self._mark(0xBD06)
                                if not r.p&C:
                                    return (yield from self.panel_helper_bc95())
                                else:
                                    self._a(m[0x040B])
                                    m[0x040A]=r.a
                                    self._a(m[0x001E])
                                    m[0x0408]=r.a
                                    self._a(m[0x001F])
                                    m[0x0409]=r.a
                                    if not (yield from self._local_call(self.panel_helper_bd28,0xBD1A,0xBD1D)):return
                                    self._a(0x04)
                                    m[PHASE]=r.a
                                    self._a(0x00)
                                    m[CITY]=r.a
                                    self._mark(0xBD27)
                                    self._rts();return
                        except _ContinueLoop_BCF4:
                            continue

    def panel_helper_bd86(self):
        """$BD86: panel helper bd86; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBD86)
        self._x(0x00)
        self._a(0xFF)
        while True:  # natural loop $BD8A
            try:
                m[(0x0580+r.x)&65535]=r.a
                self._x(r.x+1)
                self._compare(r.x,0x10)
                self._mark(0xBD90)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x0408])
                yield from self._external(0xBD95,0xF2AF,0xBD98,"call",None)
                if r.pc!=0xBD98:return  # preserve nonlocal stack return
                self._y(0x11)
                self._x(0x00)
                while True:  # natural loop $BD9C
                    try:
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xBDA0)
                        if r.p&Z:
                            pass
                        else:
                            m[(0x0580+r.x)&65535]=r.a
                            self._x(r.x+1)
                            pass
                        self._y(r.y+1)
                        self._compare(r.y,0x1B)
                        self._mark(0xBDA9)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._y(0x11)
                        self._x(0x00)
                        while True:  # natural loop $BDAF
                            try:
                                self._a(m[(0x0580+r.x)&65535])
                                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                self._y(r.y+1)
                                self._x(r.x+1)
                                self._compare(r.y,0x1B)
                                self._mark(0xBDB8)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._mark(0xBDBA)
                                self._rts();return
                            except _ContinueLoop_BDAF:
                                continue
                    except _ContinueLoop_BD9C:
                        continue
            except _ContinueLoop_BD8A:
                continue

    def panel_helper_bdbb(self):
        """$BDBB: panel helper bdbb; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBDBB)
        self._y(0x31)
        yield from self._external(0xBDBD,0xF25F,0xBDC0,"call",None)
        if r.pc!=0xBDC0:return  # preserve nonlocal stack return
        self._a(m[0x040A])
        yield from self._external(0xBDC3,0xF2D7,0xBDC6,"call",None)
        if r.pc!=0xBDC6:return  # preserve nonlocal stack return
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._a(r.a | 0x03)
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._y(0x30)
        yield from self._external(0xBDD0,0xF25F,0xBDD3,"call",None)
        if r.pc!=0xBDD3:return  # preserve nonlocal stack return
        self._a(m[0x0408])
        yield from self._external(0xBDD6,0xF2AF,0xBDD9,"call",None)
        if r.pc!=0xBDD9:return  # preserve nonlocal stack return
        self._y(m[0x0409])
        self._a(0xFF)
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        if not (yield from self._local_call(self.panel_helper_bd86,0xBDE0,0xBDE3)):return
        self._y(0x11)
        self._x(0x00)
        while True:  # natural loop $BDE7
            try:
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xBDEB)
                if r.p&Z:
                    pass
                else:
                    self._x(r.x+1)
                    pass
                self._y(r.y+1)
                self._compare(r.y,0x1B)
                self._mark(0xBDF1)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(r.x)
                self._mark(0xBDF4)
                if not r.p&Z:
                    pass
                else:
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._a(r.a & 0xF8)
                    self._a(r.a | 0x07)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    pass
                self._mark(0xBE00)
                self._rts();return
            except _ContinueLoop_BDE7:
                continue

    def panel_helper_be01(self):
        """$BE01: panel helper be01; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBE01)
        self._a(m[CITY])
        return (yield from self.panel_helper_be04())

    def panel_helper_be04(self):
        """$BE04: panel helper be04; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBE04)
        index=self._dispatch(0xBE04,(48663, 48686, 48771, 48849, 48943, 49081, 49182, 49381))
        return (yield from (self.panel_helper_be17,self.panel_helper_be2e,self.panel_helper_be83,self.panel_helper_bed1,self.panel_helper_bf2f,self.panel_helper_bfb9,self.panel_helper_c01e,self.panel_helper_c0e5,)[index]())

    def panel_helper_be17(self):
        """$BE17: panel helper be17; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBE17)
        self._a(m[0x040B])
        m[0x042C]=r.a
        m[CITY]=self._nz(m[CITY]+1)
        self._a(0xC1)
        yield from self._external(0xBE22,0xF28B,0xBE25,"call",None)
        if r.pc!=0xBE25:return  # preserve nonlocal stack return
        yield from self._external(0xBE25,0xE57F,0xBE28,"call",None)
        if r.pc!=0xBE28:return  # preserve nonlocal stack return
        self._a(0x08)
        yield from self._external(0xBE2A,0xE683,0xBE2D,"call",None)
        if r.pc!=0xBE2D:return  # preserve nonlocal stack return
        self._mark(0xBE2D)
        self._rts();return

    def panel_helper_be2e(self):
        """$BE2E: panel helper be2e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBE2E)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xBE33)
        if not r.p&Z:
            self._mark(0xBE82)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xBE3A)
            if not r.p&Z:
                self._mark(0xBE82)
                self._rts();return
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xBE3C,0xBE3F)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                self._mark(0xBE44)
                if r.p&Z:
                    self._mark(0xBE82)
                    self._rts();return
                else:
                    self._x(0x00)
                    while True:  # natural loop $BE48
                        try:
                            self._a(r.x)
                            yield from self._external(0xBE49,0xF2AF,0xBE4C,"call",None)
                            if r.pc!=0xBE4C:return  # preserve nonlocal stack return
                            self._y(0x00)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._a(r.a & 0x07)
                            self._compare(r.a,m[0x040A])
                            self._mark(0xBE55)
                            if not r.p&Z:
                                self._x(r.x+1)
                                self._compare(r.x,0x1E)
                                self._mark(0xBE62)
                                if not r.p&C:
                                    continue
                                else:
                                    self._a(m[CURRENT_CITY])
                                    m[PHASE]=r.a
                                    self._a(0x00)
                                    m[CITY]=r.a
                                    self._mark(0xBE6F)
                                    self._rts();return
                            else:
                                self._y(0x11)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                self._compare(r.a,0xFF)
                                self._mark(0xBE5D)
                                if not r.p&Z:
                                    m[CITY]=self._nz(m[CITY]+1)
                                    self._a(0x80)
                                    m[0x6F3F]=r.a
                                    self._a(0x41)
                                    m[0x6F41]=r.a
                                    self._a(0xD0)
                                    self._mark(0xBE7F)
                                    yield from self._external(0xBE7F,0xF28B,None,"tail")
                                    return
                                else:
                                    self._x(r.x+1)
                                    self._compare(r.x,0x1E)
                                    self._mark(0xBE62)
                                    if not r.p&C:
                                        continue
                                    else:
                                        self._a(m[CURRENT_CITY])
                                        m[PHASE]=r.a
                                        self._a(0x00)
                                        m[CITY]=r.a
                                        self._mark(0xBE6F)
                                        self._rts();return
                        except _ContinueLoop_BE48:
                            continue

    def panel_helper_be83(self):
        """$BE83: panel helper be83; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBE83)
        if not (yield from self._local_call(self.panel_helper_c67c,0xBE83,0xBE86)):return
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xBE8B)
        if not r.p&Z:
            self._mark(0xBEC6)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xBE92)
            if not r.p&Z:
                self._mark(0xBEC6)
                self._rts();return
            else:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x01)
                self._mark(0xBE99)
                if r.p&Z:
                    self._mark(0xBEC6)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.panel_helper_c708,0xBE9B,0xBE9E)):return
                    self._compare(r.y,0xFF)
                    self._mark(0xBEA0)
                    if r.p&Z:
                        self._a(0x21)
                        self._mark(0xBEC9)
                        yield from self._external(0xBEC9,0xF26D,None,"tail")
                        return
                    else:
                        m[OFFICER_INDEX]=r.y
                        self._a(r.y)
                        yield from self._external(0xBEA6,0xF2AF,0xBEA9,"call",None)
                        if r.pc!=0xBEA9:return  # preserve nonlocal stack return
                        self._y(0x00)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._a(r.a & 0x07)
                        self._compare(r.a,m[0x040A])
                        self._mark(0xBEB2)
                        if not r.p&Z:
                            self._a(0x22)
                            self._mark(0xBECE)
                            yield from self._external(0xBECE,0xF26D,None,"tail")
                            return
                        else:
                            m[CITY]=self._nz(m[CITY]+1)
                            self._a(0x82)
                            m[0x0478]=r.a
                            self._a(0x0F)
                            m[0x047C]=r.a
                            self._a(0xD1)
                            self._mark(0xBEC3)
                            yield from self._external(0xBEC3,0xF26D,None,"tail")
                            return

    def panel_helper_bed1(self):
        """$BED1: panel helper bed1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBED1)
        self._a(m[0x0478])
        self._mark(0xBED4)
        if not r.p&Z:
            self._mark(0xBEFC)
            self._rts();return
        else:
            self._a(m[CITY])
            self._push(r.a)
            self._a(m[OFFICER_INDEX])
            m[CITY]=r.a
            self._y(0x3B)
            yield from self._external(0xBEE2,0xEE07,0xBEE7,"far_call",40966)
            if r.pc!=0xBEE7:return  # preserve nonlocal stack return
            self._a(self._pop())
            m[CITY]=r.a
            self._a(m[0x047C])
            self._mark(0xBEEE)
            if not r.p&N:
                self._mark(0xBEFC)
                self._rts();return
            else:
                self._compare(r.a,0x90)
                self._mark(0xBEF2)
                if not r.p&Z:
                    self._a(0x00)
                    m[0x008F]=r.a
                    self._a(0x03)
                    m[0x0061]=r.a
                    self._a(0x00)
                    m[0x00B2]=r.a
                    self._a(0x05)
                    m[0x00B3]=r.a
                    self._a(0x09)
                    m[0x00B4]=r.a
                    m[CITY]=self._nz(m[CITY]+1)
                    self._a(m[0x0481])
                    m[0x042C]=r.a
                    m[DETAIL_ROW]=r.a
                    self._a(0x00)
                    m[0x0424]=r.a
                    m[0x0425]=r.a
                    self._a(0xD2)
                    self._mark(0xBF2C)
                    yield from self._external(0xBF2C,0xF28B,None,"tail")
                    return
                else:
                    m[CITY]=self._nz(m[CITY]-1)
                    self._a(0xD0)
                    self._mark(0xBEF9)
                    yield from self._external(0xBEF9,0xF26D,None,"tail")
                    return

    def panel_helper_bf2f(self):
        """$BF2F: panel helper bf2f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBF2F)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xBF34)
        if not r.p&Z:
            self._mark(0xBF84)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xBF3B)
            if not r.p&Z:
                self._mark(0xBF84)
                self._rts();return
            else:
                self._a(0xAC)
                m[0x0010]=r.a
                self._a(0xBF)
                m[0x0011]=r.a
                self._a(0x00)
                m[0x0012]=r.a
                yield from self._external(0xBF4C,0xED1E,0xBF4F,"call",None)
                if r.pc!=0xBF4F:return  # preserve nonlocal stack return
                self._a(0xB0)
                m[0x0010]=r.a
                self._a(0xBF)
                m[0x0011]=r.a
                self._a(0xB4)
                m[0x0000]=r.a
                self._a(0xBF)
                m[0x0001]=r.a
                self._a(m[0x0012])
                yield from self._external(0xBF66,0xEDF5,0xBF69,"call",None)
                if r.pc!=0xBF69:return  # preserve nonlocal stack return
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xBF6D)
                if r.p&C:
                    self._a(m[0x0012])
                    self._mark(0xBF88)
                    if not r.p&Z:
                        self._a(0x82)
                        m[0x0478]=r.a
                        self._a(0x0F)
                        m[0x047C]=r.a
                        m[CITY]=self._nz(m[CITY]-1)
                        self._a(0xD1)
                        yield from self._external(0xBF81,0xF26D,0xBF84,"call",None)
                        if r.pc!=0xBF84:return  # preserve nonlocal stack return
                        self._mark(0xBF84)
                        self._rts();return
                    else:
                        self._a(m[0x040A])
                        yield from self._external(0xBF8D,0xF368,0xBF90,"call",None)
                        if r.pc!=0xBF90:return  # preserve nonlocal stack return
                        self._a(m[DETAIL_ROW])
                        m[0x042C]=r.a
                        self._y(0x00)
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._a(m[OFFICER_INDEX])
                        self._y(0x01)
                        m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535]=r.a
                        if not (yield from self._local_call(self.panel_helper_c101,0xBFA1,0xBFA4)):return
                        m[CITY]=self._nz(m[CITY]+1)
                        self._a(0xD3)
                        self._mark(0xBFA9)
                        yield from self._external(0xBFA9,0xF28B,None,"tail")
                        return
                else:
                    r.a=self._shift(r.a,False,rotate=False)
                    self._mark(0xBF70)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x82)
                        m[0x0478]=r.a
                        self._a(0x0F)
                        m[0x047C]=r.a
                        m[CITY]=self._nz(m[CITY]-1)
                        self._a(0xD1)
                        yield from self._external(0xBF81,0xF26D,0xBF84,"call",None)
                        if r.pc!=0xBF84:return  # preserve nonlocal stack return
                        pass
                    self._mark(0xBF84)
                    self._rts();return

    def panel_helper_bfb9(self):
        """$BFB9: panel helper bfb9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBFB9)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xBFBE)
        if not r.p&Z:
            self._mark(0xC01D)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xBFC5)
            if not r.p&Z:
                self._mark(0xC01D)
                self._rts();return
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xBFC7,0xBFCA)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                self._mark(0xBFCF)
                if r.p&Z:
                    self._mark(0xC01D)
                    self._rts();return
                else:
                    self._a(m[0x040A])
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    self._y(r.a)
                    self._flag(C,False)
                    self._add(0x08)
                    m[0x0010]=r.a
                    while True:  # natural loop $BFDE
                        try:
                            self._a(m[(0xC342+r.y)&65535])
                            self._compare(r.a,0xFF)
                            self._mark(0xBFE3)
                            if not r.p&Z:
                                self._compare(r.a,m[DETAIL_ROW])
                                self._mark(0xBFF6)
                                if r.p&Z:
                                    self._a(m[DETAIL_ROW])
                                    yield from self._external(0xC001,0xF2D7,0xC004,"call",None)
                                    if r.pc!=0xC004:return  # preserve nonlocal stack return
                                    self._y(0x03)
                                    self._a(0x64)
                                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                    self._a(m[WORLD_CURSOR])
                                    m[PHASE]=r.a
                                    self._a(0x00)
                                    m[CITY]=r.a
                                    yield from self._external(0xC015,0xE57F,0xC018,"call",None)
                                    if r.pc!=0xC018:return  # preserve nonlocal stack return
                                    self._a(0x81)
                                    yield from self._external(0xC01A,0xE673,0xC01D,"call",None)
                                    if r.pc!=0xC01D:return  # preserve nonlocal stack return
                                    self._mark(0xC01D)
                                    self._rts();return
                                else:
                                    self._y(r.y+1)
                                    self._compare(r.y,m[0x0010])
                                    self._mark(0xBFFC)
                                    if not r.p&C:
                                        continue
                                    else:
                                        self._a(m[DETAIL_ROW])
                                        yield from self._external(0xC001,0xF2D7,0xC004,"call",None)
                                        if r.pc!=0xC004:return  # preserve nonlocal stack return
                                        self._y(0x03)
                                        self._a(0x64)
                                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                        self._a(m[WORLD_CURSOR])
                                        m[PHASE]=r.a
                                        self._a(0x00)
                                        m[CITY]=r.a
                                        yield from self._external(0xC015,0xE57F,0xC018,"call",None)
                                        if r.pc!=0xC018:return  # preserve nonlocal stack return
                                        self._a(0x81)
                                        yield from self._external(0xC01A,0xE673,0xC01D,"call",None)
                                        if r.pc!=0xC01D:return  # preserve nonlocal stack return
                                        self._mark(0xC01D)
                                        self._rts();return
                            else:
                                self._a(0x00)
                                m[0x040E]=r.a
                                self._a(0x11)
                                m[0x040F]=r.a
                                m[CITY]=self._nz(m[CITY]+1)
                                self._mark(0xBFF2)
                                self._rts();return
                        except _ContinueLoop_BFDE:
                            continue

    def panel_helper_c01e(self):
        """$C01E: panel helper c01e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        while True:  # natural loop $C01E
            try:
                self._mark(0xC01E)
                self._a(m[0x040E])
                yield from self._external(0xC021,0xF2AF,0xC024,"call",None)
                if r.pc!=0xC024:return  # preserve nonlocal stack return
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0x07)
                self._compare(r.a,m[0x040A])
                self._mark(0xC02D)
                if not r.p&Z:
                    m[0x040E]=self._nz(m[0x040E]+1)
                    self._a(0x11)
                    m[0x040F]=r.a
                    self._a(m[0x040E])
                    self._compare(r.a,0x1E)
                    self._mark(0xC08C)
                    if not r.p&C:
                        continue
                    else:
                        self._a(m[DETAIL_ROW])
                        yield from self._external(0xC001,0xF2D7,0xC004,"call",None)
                        if r.pc!=0xC004:return  # preserve nonlocal stack return
                        self._y(0x03)
                        self._a(0x64)
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._a(m[WORLD_CURSOR])
                        m[PHASE]=r.a
                        self._a(0x00)
                        m[CITY]=r.a
                        yield from self._external(0xC015,0xE57F,0xC018,"call",None)
                        if r.pc!=0xC018:return  # preserve nonlocal stack return
                        self._a(0x81)
                        yield from self._external(0xC01A,0xE673,0xC01D,"call",None)
                        if r.pc!=0xC01D:return  # preserve nonlocal stack return
                        self._mark(0xC01D)
                        self._rts();return
                else:
                    self._a(m[0x0000])
                    m[0x0010]=r.a
                    self._a(m[0x0001])
                    m[0x0011]=r.a
                    self._y(m[0x040F])
                    while True:  # natural loop $C03E
                        try:
                            self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                            self._compare(r.a,0xFF)
                            self._mark(0xC042)
                            if r.p&Z:
                                m[0x040E]=self._nz(m[0x040E]+1)
                                self._a(0x11)
                                m[0x040F]=r.a
                                self._a(m[0x040E])
                                self._compare(r.a,0x1E)
                                self._mark(0xC08C)
                                if not r.p&C:
                                    raise _ContinueLoop_C01E
                                else:
                                    self._a(m[DETAIL_ROW])
                                    yield from self._external(0xC001,0xF2D7,0xC004,"call",None)
                                    if r.pc!=0xC004:return  # preserve nonlocal stack return
                                    self._y(0x03)
                                    self._a(0x64)
                                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                    self._a(m[WORLD_CURSOR])
                                    m[PHASE]=r.a
                                    self._a(0x00)
                                    m[CITY]=r.a
                                    yield from self._external(0xC015,0xE57F,0xC018,"call",None)
                                    if r.pc!=0xC018:return  # preserve nonlocal stack return
                                    self._a(0x81)
                                    yield from self._external(0xC01A,0xE673,0xC01D,"call",None)
                                    if r.pc!=0xC01D:return  # preserve nonlocal stack return
                                    self._mark(0xC01D)
                                    self._rts();return
                            else:
                                m[0x0031]=r.a
                                self._a(m[DETAIL_ROW])
                                m[0x0030]=r.a
                                self._a(m[0x040A])
                                m[0x0032]=r.a
                                self._a(m[0x040B])
                                m[0x0033]=r.a
                                self._y(0x2A)
                                yield from self._external(0xC05B,0xEE07,0xC060,"far_call",40969)
                                if r.pc!=0xC060:return  # preserve nonlocal stack return
                                self._a(m[0x0031])
                                yield from self._external(0xC063,0xF2D7,0xC066,"call",None)
                                if r.pc!=0xC066:return  # preserve nonlocal stack return
                                self._y(0x03)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                self._compare(r.a,0x1F)
                                self._mark(0xC06C)
                                if r.p&C:
                                    m[0x040F]=self._nz(m[0x040F]+1)
                                    self._y(m[0x040F])
                                    self._compare(r.y,0x1B)
                                    self._mark(0xC07D)
                                    if not r.p&C:
                                        continue
                                    else:
                                        m[0x040E]=self._nz(m[0x040E]+1)
                                        self._a(0x11)
                                        m[0x040F]=r.a
                                        self._a(m[0x040E])
                                        self._compare(r.a,0x1E)
                                        self._mark(0xC08C)
                                        if not r.p&C:
                                            raise _ContinueLoop_C01E
                                        else:
                                            self._a(m[DETAIL_ROW])
                                            yield from self._external(0xC001,0xF2D7,0xC004,"call",None)
                                            if r.pc!=0xC004:return  # preserve nonlocal stack return
                                            self._y(0x03)
                                            self._a(0x64)
                                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                            self._a(m[WORLD_CURSOR])
                                            m[PHASE]=r.a
                                            self._a(0x00)
                                            m[CITY]=r.a
                                            yield from self._external(0xC015,0xE57F,0xC018,"call",None)
                                            if r.pc!=0xC018:return  # preserve nonlocal stack return
                                            self._a(0x81)
                                            yield from self._external(0xC01A,0xE673,0xC01D,"call",None)
                                            if r.pc!=0xC01D:return  # preserve nonlocal stack return
                                            self._mark(0xC01D)
                                            self._rts();return
                                else:
                                    yield from self._external(0xC06E,0xE843,0xC071,"call",None)
                                    if r.pc!=0xC071:return  # preserve nonlocal stack return
                                    self._compare(r.a,0x14)
                                    self._mark(0xC073)
                                    if not r.p&C:
                                        self._a(m[0x0031])
                                        self._compare(r.a,m[DETAIL_ROW])
                                        self._mark(0xC097)
                                        if r.p&Z:
                                            m[0x040F]=self._nz(m[0x040F]+1)
                                            self._y(m[0x040F])
                                            self._compare(r.y,0x1B)
                                            self._mark(0xC07D)
                                            if not r.p&C:
                                                continue
                                            else:
                                                m[0x040E]=self._nz(m[0x040E]+1)
                                                self._a(0x11)
                                                m[0x040F]=r.a
                                                self._a(m[0x040E])
                                                self._compare(r.a,0x1E)
                                                self._mark(0xC08C)
                                                if not r.p&C:
                                                    raise _ContinueLoop_C01E
                                                else:
                                                    self._a(m[DETAIL_ROW])
                                                    yield from self._external(0xC001,0xF2D7,0xC004,"call",None)
                                                    if r.pc!=0xC004:return  # preserve nonlocal stack return
                                                    self._y(0x03)
                                                    self._a(0x64)
                                                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                                    self._a(m[WORLD_CURSOR])
                                                    m[PHASE]=r.a
                                                    self._a(0x00)
                                                    m[CITY]=r.a
                                                    yield from self._external(0xC015,0xE57F,0xC018,"call",None)
                                                    if r.pc!=0xC018:return  # preserve nonlocal stack return
                                                    self._a(0x81)
                                                    yield from self._external(0xC01A,0xE673,0xC01D,"call",None)
                                                    if r.pc!=0xC01D:return  # preserve nonlocal stack return
                                                    self._mark(0xC01D)
                                                    self._rts();return
                                        else:
                                            self._y(0x0B)
                                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                            self._a(r.a & 0xFC)
                                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                            self._y(0x05)
                                            self._a(m[0x040E])
                                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                            self._y(m[0x040F])
                                            while True:  # natural loop $C0AB
                                                try:
                                                    self._compare(r.y,0x1A)
                                                    self._mark(0xC0AD)
                                                    if r.p&Z:
                                                        pass
                                                    else:
                                                        self._y(r.y+1)
                                                        self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                                                        self._y(r.y-1)
                                                        m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a
                                                        self._y(r.y+1)
                                                        continue
                                                    self._a(0xFF)
                                                    m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a
                                                    self._x(0x00)
                                                    self._y(0x11)
                                                    while True:  # natural loop $C0C1
                                                        try:
                                                            self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                                                            self._compare(r.a,0xFF)
                                                            self._mark(0xC0C5)
                                                            if r.p&Z:
                                                                pass
                                                            else:
                                                                self._x(r.x+1)
                                                                pass
                                                            self._y(r.y+1)
                                                            self._compare(r.y,0x1B)
                                                            self._mark(0xC0CB)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                pass
                                                            self._compare(r.x,0x00)
                                                            self._mark(0xC0CF)
                                                            if not r.p&Z:
                                                                pass
                                                            else:
                                                                self._y(0x00)
                                                                self._a(0x07)
                                                                m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a
                                                                pass
                                                            m[CITY]=self._nz(m[CITY]+1)
                                                            self._a(m[0x0031])
                                                            m[0x042C]=r.a
                                                            self._a(0xD4)
                                                            self._mark(0xC0E2)
                                                            yield from self._external(0xC0E2,0xF28B,None,"tail")
                                                            return
                                                        except _ContinueLoop_C0C1:
                                                            continue
                                                except _ContinueLoop_C0AB:
                                                    continue
                                    else:
                                        m[0x040F]=self._nz(m[0x040F]+1)
                                        self._y(m[0x040F])
                                        self._compare(r.y,0x1B)
                                        self._mark(0xC07D)
                                        if not r.p&C:
                                            continue
                                        else:
                                            m[0x040E]=self._nz(m[0x040E]+1)
                                            self._a(0x11)
                                            m[0x040F]=r.a
                                            self._a(m[0x040E])
                                            self._compare(r.a,0x1E)
                                            self._mark(0xC08C)
                                            if not r.p&C:
                                                raise _ContinueLoop_C01E
                                            else:
                                                self._a(m[DETAIL_ROW])
                                                yield from self._external(0xC001,0xF2D7,0xC004,"call",None)
                                                if r.pc!=0xC004:return  # preserve nonlocal stack return
                                                self._y(0x03)
                                                self._a(0x64)
                                                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                                self._a(m[WORLD_CURSOR])
                                                m[PHASE]=r.a
                                                self._a(0x00)
                                                m[CITY]=r.a
                                                yield from self._external(0xC015,0xE57F,0xC018,"call",None)
                                                if r.pc!=0xC018:return  # preserve nonlocal stack return
                                                self._a(0x81)
                                                yield from self._external(0xC01A,0xE673,0xC01D,"call",None)
                                                if r.pc!=0xC01D:return  # preserve nonlocal stack return
                                                self._mark(0xC01D)
                                                self._rts();return
                        except _ContinueLoop_C03E:
                            continue
            except _ContinueLoop_C01E:
                continue

    def panel_helper_c0e5(self):
        """$C0E5: panel helper c0e5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC0E5)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xC0EA)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xC0F1)
            if not r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xC0F3,0xC0F6)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                self._mark(0xC0FB)
                if r.p&Z:
                    pass
                else:
                    m[CITY]=self._nz(m[CITY]-1)
                    pass
                pass
            pass
        self._mark(0xC100)
        self._rts();return

    def panel_helper_c101(self):
        """$C101: panel helper c101; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC101)
        self._a(m[OFFICER_INDEX])
        yield from self._external(0xC104,0xF2AF,0xC107,"call",None)
        if r.pc!=0xC107:return  # preserve nonlocal stack return
        self._a(m[DETAIL_ROW])
        m[0x0002]=r.a
        self._y(0x11)
        while True:  # natural loop $C10F
            try:
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,m[0x0002])
                self._mark(0xC114)
                if r.p&Z:
                    self._a(r.y)
                    self._push(r.a)
                    self._y(0x11)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0003]=r.a
                    self._a(m[0x0002])
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._a(self._pop())
                    self._y(r.a)
                    self._a(m[0x0003])
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._mark(0xC131)
                    self._rts();return
                else:
                    self._y(r.y+1)
                    self._compare(r.y,0x1B)
                    self._mark(0xC119)
                    if not r.p&C:
                        continue
                    else:
                        self._mark(0xC11B)
                        self._rts();return
            except _ContinueLoop_C10F:
                continue

    def panel_helper_c132(self):
        """$C132: panel helper c132; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC132)
        self._a(m[CITY])
        return (yield from self.panel_helper_c135())

    def panel_helper_c135(self):
        """$C135: panel helper c135; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC135)
        index=self._dispatch(0xC135,(49476, 49496, 49627, 49757, 49792, 49801))
        return (yield from (self.panel_helper_c144,self.panel_helper_c158,self.panel_helper_c1db,self.panel_helper_c25d,self.panel_helper_c280,self.panel_helper_c289,)[index]())

    def panel_helper_c144(self):
        """$C144: panel helper c144; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC144)
        m[CITY]=self._nz(m[CITY]+1)
        self._a(0x00)
        m[0x04D0]=r.a
        self._a(m[0x040B])
        m[0x042C]=r.a
        self._a(0xC1)
        yield from self._external(0xC154,0xF28B,0xC157,"call",None)
        if r.pc!=0xC157:return  # preserve nonlocal stack return
        self._mark(0xC157)
        self._rts();return

    def panel_helper_c158(self):
        """$C158: panel helper c158; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC158)
        m[0x04D0]=self._nz(m[0x04D0]+1)
        self._mark(0xC15B)
        if not r.p&Z:
            self._mark(0xC157)
            self._rts();return
        else:
            self._a(m[0x040A])
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            m[0x0010]=r.a
            self._a(0x42)
            self._flag(C,False)
            self._add(m[0x0010])
            m[0x0010]=r.a
            self._a(0xC3)
            self._add(0x00)
            m[0x0011]=r.a
            self._y(0x00)
            m[0x0012]=r.y
            while True:  # natural loop $C17B
                try:
                    self._y(m[0x0012])
                    self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                    self._compare(r.a,0xFF)
                    self._mark(0xC182)
                    if r.p&Z:
                        m[CITY]=self._nz(m[CITY]+1)
                        self._mark(0xC1A0)
                        self._rts();return
                    else:
                        m[DETAIL_ROW]=r.a
                        if not (yield from self._local_call(self.panel_helper_c1a1,0xC187,0xC18A)):return
                        self._mark(0xC18A)
                        if r.p&C:
                            self._a(0x00)
                            m[0x0409]=r.a
                            self._a(0x03)
                            m[CITY]=r.a
                            self._mark(0xC19C)
                            self._rts();return
                        else:
                            m[0x0012]=self._nz(m[0x0012]+1)
                            continue
                except _ContinueLoop_C17B:
                    continue

    def panel_helper_c1a1(self):
        """$C1A1: panel helper c1a1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC1A1)
        self._x(0x00)
        while True:  # natural loop $C1A3
            try:
                self._a(r.x)
                yield from self._external(0xC1A4,0xF2AF,0xC1A7,"call",None)
                if r.pc!=0xC1A7:return  # preserve nonlocal stack return
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0x07)
                self._compare(r.a,m[0x040A])
                self._mark(0xC1B0)
                if not r.p&Z:
                    self._x(r.x+1)
                    self._compare(r.x,0x1E)
                    self._mark(0xC1D7)
                    if not r.p&C:
                        continue
                    else:
                        self._flag(C,False)
                        self._mark(0xC1DA)
                        self._rts();return
                else:
                    self._y(0x11)
                    m[0x0004]=r.y
                    while True:  # natural loop $C1B7
                        try:
                            self._y(m[0x0004])
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._compare(r.a,m[DETAIL_ROW])
                            self._mark(0xC1BF)
                            if not r.p&Z:
                                self._compare(r.a,0xFF)
                                self._mark(0xC1C8)
                                if r.p&Z:
                                    self._x(r.x+1)
                                    self._compare(r.x,0x1E)
                                    self._mark(0xC1D7)
                                    if not r.p&C:
                                        raise _ContinueLoop_C1A3
                                    else:
                                        self._flag(C,False)
                                        self._mark(0xC1DA)
                                        self._rts();return
                                else:
                                    m[0x0004]=self._nz(m[0x0004]+1)
                                    self._a(m[0x0004])
                                    self._compare(r.a,0x1B)
                                    self._mark(0xC1D2)
                                    if not r.p&C:
                                        continue
                                    else:
                                        self._x(r.x+1)
                                        self._compare(r.x,0x1E)
                                        self._mark(0xC1D7)
                                        if not r.p&C:
                                            raise _ContinueLoop_C1A3
                                        else:
                                            self._flag(C,False)
                                            self._mark(0xC1DA)
                                            self._rts();return
                            else:
                                m[OFFICER_INDEX]=r.x
                                self._flag(C,True)
                                self._mark(0xC1C5)
                                self._rts();return
                        except _ContinueLoop_C1B7:
                            continue
            except _ContinueLoop_C1A3:
                continue

    def panel_helper_c1db(self):
        """$C1DB: panel helper c1db; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC1DB)
        self._a(0xFF)
        m[0x0010]=r.a
        self._x(0x00)
        m[0x0011]=r.x
        while True:  # natural loop $C1E5
            try:
                self._a(r.x)
                yield from self._external(0xC1E6,0xF2AF,0xC1E9,"call",None)
                if r.pc!=0xC1E9:return  # preserve nonlocal stack return
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0x07)
                self._compare(r.a,m[0x040A])
                self._mark(0xC1F2)
                if not r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.panel_helper_c21d,0xC1F4,0xC1F7)):return
                    pass
                self._x(r.x+1)
                self._compare(r.x,0x1E)
                self._mark(0xC1FA)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x0010])
                self._compare(r.a,0xFF)
                self._mark(0xC201)
                if r.p&Z:
                    self._a(m[CURRENT_CITY])
                    m[PHASE]=r.a
                    self._a(0x00)
                    m[CITY]=r.a
                    self._mark(0xC21C)
                    self._rts();return
                else:
                    m[DETAIL_ROW]=r.a
                    self._a(0x80)
                    m[0x0409]=r.a
                    self._a(0x03)
                    m[CITY]=r.a
                    self._mark(0xC210)
                    self._rts();return
            except _ContinueLoop_C1E5:
                continue

    def panel_helper_c21d(self):
        """$C21D: panel helper c21d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC21D)
        self._a(m[0x0000])
        m[0x0002]=r.a
        self._a(m[0x0001])
        m[0x0003]=r.a
        self._y(0x11)
        m[0x0004]=r.y
        while True:  # natural loop $C22E
            try:
                self._y(m[0x0004])
                self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xC235)
                if r.p&Z:
                    pass
                else:
                    m[0x0012]=r.a
                    yield from self._external(0xC23A,0xF2D7,0xC23D,"call",None)
                    if r.pc!=0xC23D:return  # preserve nonlocal stack return
                    self._y(0x04)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._compare(r.a,m[0x0011])
                    self._mark(0xC244)
                    if not r.p&C:
                        pass
                    else:
                        m[0x0011]=r.a
                        self._a(m[0x0012])
                        m[0x0010]=r.a
                        m[OFFICER_INDEX]=r.x
                        pass
                    m[0x0004]=self._nz(m[0x0004]+1)
                    self._a(m[0x0004])
                    self._compare(r.a,0x1B)
                    self._mark(0xC25A)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    pass
                self._mark(0xC25C)
                self._rts();return
            except _ContinueLoop_C22E:
                continue

    def panel_helper_c25d(self):
        """$C25D: panel helper c25d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC25D)
        self._a(m[0x040A])
        yield from self._external(0xC260,0xF368,0xC263,"call",None)
        if r.pc!=0xC263:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[DETAIL_ROW])
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        if not (yield from self._local_call(self.panel_helper_c101,0xC26A,0xC26D)):return
        m[CITY]=self._nz(m[CITY]+1)
        self._a(m[DETAIL_ROW])
        m[0x042C]=r.a
        self._a(0x00)
        m[0x04D0]=r.a
        self._a(0xC2)
        self._mark(0xC27D)
        yield from self._external(0xC27D,0xF28B,None,"tail")
        return

    def panel_helper_c280(self):
        """$C280: panel helper c280; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC280)
        m[0x04D0]=self._nz(m[0x04D0]+1)
        self._mark(0xC283)
        if not r.p&Z:
            pass
        else:
            m[CITY]=self._nz(m[CITY]+1)
            pass
        self._mark(0xC288)
        self._rts();return

    def panel_helper_c289(self):
        """$C289: panel helper c289; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC289)
        self._a(m[0x0409])
        self._mark(0xC28C)
        if r.p&N:
            self._a(0x00)
            m[0x0012]=r.a
            while True:  # natural loop $C2AB
                try:
                    self._a(m[0x0012])
                    yield from self._external(0xC2AE,0xF2AF,0xC2B1,"call",None)
                    if r.pc!=0xC2B1:return  # preserve nonlocal stack return
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._a(r.a & 0x07)
                    self._compare(r.a,m[0x040A])
                    self._mark(0xC2BA)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0000])
                        m[0x0010]=r.a
                        self._a(m[0x0001])
                        m[0x0011]=r.a
                        self._y(0x11)
                        m[0x0013]=r.y
                        while True:  # natural loop $C2CD
                            try:
                                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                                self._compare(r.a,0xFF)
                                self._mark(0xC2D1)
                                if r.p&Z:
                                    pass
                                else:
                                    m[0x0031]=r.a
                                    self._a(m[DETAIL_ROW])
                                    m[0x0030]=r.a
                                    self._a(m[0x040A])
                                    m[0x0032]=r.a
                                    self._a(m[0x040B])
                                    m[0x0033]=r.a
                                    self._y(0x2A)
                                    yield from self._external(0xC2EA,0xEE07,0xC2EF,"far_call",40969)
                                    if r.pc!=0xC2EF:return  # preserve nonlocal stack return
                                    self._y(0x03)
                                    self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
                                    self._compare(r.a,0x1F)
                                    self._mark(0xC2F5)
                                    if r.p&C:
                                        pass
                                    else:
                                        yield from self._external(0xC2F7,0xE843,0xC2FA,"call",None)
                                        if r.pc!=0xC2FA:return  # preserve nonlocal stack return
                                        self._compare(r.a,0x14)
                                        self._mark(0xC2FC)
                                        if r.p&C:
                                            pass
                                        else:
                                            if not (yield from self._local_call(self.panel_helper_c318,0xC2FE,0xC301)):return
                                            pass
                                        pass
                                    m[0x0013]=self._nz(m[0x0013]+1)
                                    self._y(m[0x0013])
                                    self._compare(r.y,0x1B)
                                    self._mark(0xC309)
                                    if not r.p&C:
                                        continue
                                    else:
                                        pass
                                    pass
                                m[0x0012]=self._nz(m[0x0012]+1)
                                self._a(m[0x0012])
                                self._compare(r.a,0x1E)
                                self._mark(0xC313)
                                if not r.p&C:
                                    raise _ContinueLoop_C2AB
                                else:
                                    pass
                                self._a(m[DETAIL_ROW])
                                yield from self._external(0xC291,0xF2D7,0xC294,"call",None)
                                if r.pc!=0xC294:return  # preserve nonlocal stack return
                                self._y(0x03)
                                self._a(0x64)
                                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                self._a(m[WORLD_CURSOR])
                                m[PHASE]=r.a
                                self._a(0x00)
                                m[CITY]=r.a
                                self._mark(0xC2A5)
                                self._rts();return
                            except _ContinueLoop_C2CD:
                                continue
                    m[0x0012]=self._nz(m[0x0012]+1)
                    self._a(m[0x0012])
                    self._compare(r.a,0x1E)
                    self._mark(0xC313)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    self._a(m[DETAIL_ROW])
                    yield from self._external(0xC291,0xF2D7,0xC294,"call",None)
                    if r.pc!=0xC294:return  # preserve nonlocal stack return
                    self._y(0x03)
                    self._a(0x64)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._a(m[WORLD_CURSOR])
                    m[PHASE]=r.a
                    self._a(0x00)
                    m[CITY]=r.a
                    self._mark(0xC2A5)
                    self._rts();return
                except _ContinueLoop_C2AB:
                    continue
        else:
            pass
        self._a(m[DETAIL_ROW])
        yield from self._external(0xC291,0xF2D7,0xC294,"call",None)
        if r.pc!=0xC294:return  # preserve nonlocal stack return
        self._y(0x03)
        self._a(0x64)
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._a(m[WORLD_CURSOR])
        m[PHASE]=r.a
        self._a(0x00)
        m[CITY]=r.a
        self._mark(0xC2A5)
        self._rts();return

    def panel_helper_c318(self):
        """$C318: panel helper c318; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC318)
        self._a(m[0x0031])
        self._compare(r.a,m[DETAIL_ROW])
        self._mark(0xC31E)
        if not r.p&Z:
            self._y(0x0B)
            self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
            self._a(r.a & 0xFC)
            m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
            self._y(m[0x0013])
            while True:  # natural loop $C32C
                try:
                    self._compare(r.y,0x1A)
                    self._mark(0xC32E)
                    if r.p&Z:
                        pass
                    else:
                        self._y(r.y+1)
                        self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                        self._y(r.y-1)
                        m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a
                        self._y(r.y+1)
                        continue
                    self._a(0xFF)
                    m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a
                    m[0x0013]=self._nz(m[0x0013]-1)
                    self._mark(0xC341)
                    self._rts();return
                except _ContinueLoop_C32C:
                    continue
        else:
            self._mark(0xC320)
            self._rts();return

    def panel_helper_c37a(self):
        """$C37A: panel helper c37a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC37A)
        self._a(m[CITY])
        return (yield from self.panel_helper_c37d())

    def panel_helper_c37d(self):
        """$C37D: panel helper c37d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC37D)
        index=self._dispatch(0xC37D,(50054, 50114, 50206))
        return (yield from (self.panel_helper_c386,self.panel_helper_c3c2,self.panel_helper_c41e,)[index]())

    def panel_helper_c386(self):
        """$C386: panel helper c386; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC386)
        self._y(m[0x040A])
        self._a(m[(0xC3BB+r.y)&65535])
        m[0x042D]=r.a
        self._a(0xC3)
        yield from self._external(0xC391,0xF28B,0xC394,"call",None)
        if r.pc!=0xC394:return  # preserve nonlocal stack return
        self._a(m[0x040A])
        yield from self._external(0xC397,0xF368,0xC39A,"call",None)
        if r.pc!=0xC39A:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x042C]=r.a
        self._a(0xFF)
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._y(0x03)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._a(r.a & 0x03)
        self._compare(r.a,0x03)
        self._mark(0xC3AD)
        if not r.p&Z:
            pass
        else:
            m[CITY]=self._nz(m[CITY]+1)
            self._a(0x00)
            m[0x04D0]=r.a
            pass
        m[CITY]=self._nz(m[CITY]+1)
        self._mark(0xC3BA)
        self._rts();return

    def panel_helper_c3c2(self):
        """$C3C2: panel helper c3c2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC3C2)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xC3C7)
        if not r.p&Z:
            self._mark(0xC3DA)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xC3CE)
            if not r.p&Z:
                self._mark(0xC3DA)
                self._rts();return
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xC3D0,0xC3D3)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                self._mark(0xC3D8)
                if not r.p&Z:
                    self._a(m[OFFICER_INDEX])
                    self._compare(r.a,0xFF)
                    self._mark(0xC3E0)
                    if r.p&Z:
                        pass
                    else:
                        yield from self._external(0xC3E2,0xF368,0xC3E5,"call",None)
                        if r.pc!=0xC3E5:return  # preserve nonlocal stack return
                        self._y(0x00)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        pass
                    m[0x042E]=r.a
                    self._a(m[0x6F00])
                    self._flag(C,False)
                    self._add(0x64)
                    m[0x042F]=r.a
                    self._a(0x00)
                    self._add(0x00)
                    m[0x0430]=r.a
                    self._a(m[0x6F01])
                    self._flag(C,False)
                    self._add(0x01)
                    m[0x0432]=r.a
                    self._a(0x00)
                    m[0x0431]=r.a
                    m[0x0433]=r.a
                    m[0x0434]=r.a
                    self._a(0x0D)
                    m[GLOBAL]=r.a
                    self._a(0x00)
                    m[0x0541]=r.a
                    m[0x04CA]=r.a
                    self._mark(0xC41D)
                    self._rts();return
                else:
                    self._mark(0xC3DA)
                    self._rts();return

    def panel_helper_c41e(self):
        """$C41E: panel helper c41e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC41E)
        m[0x04D0]=self._nz(m[0x04D0]+1)
        self._mark(0xC421)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0472])
            m[STATE]=r.a
            self._a(m[0x0473])
            m[PHASE]=r.a
            self._a(0x00)
            m[CITY]=r.a
            pass
        self._mark(0xC434)
        self._rts();return

    def panel_helper_c435(self):
        """$C435: panel helper c435; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC435)
        self._a(m[PHASE])
        return (yield from self.panel_helper_c438())

    def panel_helper_c438(self):
        """$C438: panel helper c438; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC438)
        index=self._dispatch(0xC438,(50241, 50617, 50655))
        return (yield from (self.panel_helper_c441,self.panel_helper_c5b9,self.panel_helper_c5df,)[index]())

    def panel_helper_c441(self):
        """$C441: panel helper c441; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC441)
        self._y(0x00)
        self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
        m[0x042C]=r.a
        self._x(0x00)
        m[0x0010]=r.x
        m[0x0011]=r.x
        m[0x0012]=r.x
        m[0x0013]=r.x
        m[0x0014]=r.x
        while True:  # natural loop $C459
            try:
                self._a(r.x)
                yield from self._external(0xC45A,0xF2AF,0xC45D,"call",None)
                if r.pc!=0xC45D:return  # preserve nonlocal stack return
                self._a(m[0x0000])
                m[0x000A]=r.a
                self._a(m[0x0001])
                m[0x000B]=r.a
                self._y(0x0B)
                self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x0012])
                m[0x0012]=r.a
                self._a(0x00)
                self._add(m[0x0013])
                m[0x0013]=r.a
                self._y(0x11)
                while True:  # natural loop $C47E
                    try:
                        self._a(r.y)
                        self._push(r.a)
                        self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xC484)
                        if r.p&Z:
                            pass
                        else:
                            self._compare(r.a,m[0x042C])
                            self._mark(0xC489)
                            if r.p&Z:
                                pass
                            else:
                                yield from self._external(0xC48B,0xF2D7,0xC48E,"call",None)
                                if r.pc!=0xC48E:return  # preserve nonlocal stack return
                                self._y(0x03)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                self._flag(C,False)
                                self._add(m[0x0010])
                                m[0x0010]=r.a
                                self._a(0x00)
                                self._add(m[0x0011])
                                m[0x0011]=r.a
                                m[0x0014]=self._nz(m[0x0014]+1)
                                pass
                            pass
                        self._a(self._pop())
                        self._y(r.a)
                        self._y(r.y+1)
                        self._compare(r.y,0x1B)
                        self._mark(0xC4A9)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._x(r.x+1)
                        self._compare(r.x,0x1E)
                        self._mark(0xC4AE)
                        if not r.p&C:
                            raise _ContinueLoop_C459
                        else:
                            pass
                        self._a(0x00)
                        m[0x0435]=r.a
                        m[0x0436]=r.a
                        m[0x0437]=r.a
                        self._a(m[0x0010])
                        m[0x0001]=r.a
                        self._a(m[0x0011])
                        m[0x0002]=r.a
                        self._a(m[0x0014])
                        m[0x0003]=r.a
                        self._a(0x00)
                        m[0x0004]=r.a
                        if not (yield from self._local_call(self.panel_helper_c59a,0xC4D2,0xC4D5)):return
                        self._a(m[0x0014])
                        m[0x0000]=r.a
                        self._a(0x00)
                        m[0x0001]=r.a
                        m[0x0002]=r.a
                        self._a(0x64)
                        m[0x0003]=r.a
                        yield from self._external(0xC4E8,0xEBE9,0xC4EB,"call",None)
                        if r.pc!=0xC4EB:return  # preserve nonlocal stack return
                        self._a(m[0x0006])
                        m[0x0001]=r.a
                        self._a(m[0x0007])
                        m[0x0002]=r.a
                        self._a(0x82)
                        m[0x0003]=r.a
                        self._a(0x00)
                        m[0x0004]=r.a
                        if not (yield from self._local_call(self.panel_helper_c59a,0xC501,0xC504)):return
                        self._a(m[0x0012])
                        m[0x0001]=r.a
                        self._a(m[0x0013])
                        m[0x0002]=r.a
                        self._a(0x1E)
                        m[0x0003]=r.a
                        self._a(0x00)
                        m[0x0004]=r.a
                        if not (yield from self._local_call(self.panel_helper_c59a,0xC51A,0xC51D)):return
                        self._a(m[0x0435])
                        m[0x0000]=r.a
                        self._a(m[0x0436])
                        m[0x0001]=r.a
                        self._a(m[0x0437])
                        m[0x0002]=r.a
                        self._a(0x03)
                        m[0x0003]=r.a
                        self._a(0x00)
                        m[0x0004]=r.a
                        yield from self._external(0xC539,0xEAA5,0xC53C,"call",None)
                        if r.pc!=0xC53C:return  # preserve nonlocal stack return
                        self._a(m[0x0000])
                        m[0x0435]=r.a
                        self._a(m[0x0001])
                        m[0x0436]=r.a
                        self._a(m[0x0002])
                        m[0x0437]=r.a
                        self._a(m[0x6F00])
                        self._flag(C,True)
                        self._add(0x59,subtract=True)
                        m[0x044C]=r.a
                        self._a(0x00)
                        m[0x044D]=r.a
                        m[0x044E]=r.a
                        self._a(m[0x6F00])
                        self._flag(C,False)
                        self._add(0x64)
                        m[0x042F]=r.a
                        self._a(0x00)
                        self._add(0x00)
                        m[0x0430]=r.a
                        self._a(0x00)
                        m[0x0431]=r.a
                        self._a(m[0x6F01])
                        self._flag(C,False)
                        self._add(0x01)
                        m[0x0432]=r.a
                        self._a(0x00)
                        m[0x0433]=r.a
                        m[0x0434]=r.a
                        self._a(m[0x6F02])
                        self._flag(C,False)
                        self._add(0x01)
                        m[0x044F]=r.a
                        self._a(0x00)
                        m[0x0450]=r.a
                        m[0x0451]=r.a
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._mark(0xC599)
                        self._rts();return
                    except _ContinueLoop_C47E:
                        continue
            except _ContinueLoop_C459:
                continue

    def panel_helper_c59a(self):
        """$C59A: panel helper c59a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC59A)
        yield from self._external(0xC59A,0xEA7C,0xC59D,"call",None)
        if r.pc!=0xC59D:return  # preserve nonlocal stack return
        self._a(m[0x0001])
        self._flag(C,False)
        self._add(m[0x0435])
        m[0x0435]=r.a
        self._a(m[0x0002])
        self._add(m[0x0436])
        m[0x0436]=r.a
        self._a(0x00)
        self._add(m[0x0437])
        m[0x0437]=r.a
        self._mark(0xC5B8)
        self._rts();return

    def panel_helper_c5b9(self):
        """$C5B9: panel helper c5b9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC5B9)
        self._a(m[PPU_JOBS])
        self._mark(0xC5BC)
        if r.p&Z:
            if not (yield from self._local_call(self.panel_helper_c626,0xC5BF,0xC5C2)):return
            self._a(m[0x0010])
            m[0x042D]=r.a
            m[0x0000]=r.a
            self._y(0x3D)
            yield from self._external(0xC5CD,0xEE07,0xC5D2,"far_call",41002)
            if r.pc!=0xC5D2:return  # preserve nonlocal stack return
            self._a(0x03)
            m[0x00A4]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xDF)
            self._mark(0xC5DC)
            yield from self._external(0xC5DC,0xF26D,None,"tail")
            return
        else:
            self._mark(0xC5BE)
            self._rts();return

    def panel_helper_c5df(self):
        """$C5DF: panel helper c5df; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC5DF)
        self._a(m[0x042D])
        m[0x0000]=r.a
        self._a(0xA7)
        m[0x000A]=r.a
        self._x(0x00)
        yield from self._external(0xC5EC,0xCE1F,0xC5EF,"call",None)
        if r.pc!=0xC5EF:return  # preserve nonlocal stack return
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xC5F4)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xC5FB)
            if not r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xC5FD,0xC600)):return
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xC604)
                if not r.p&C:
                    pass
                else:
                    self._a(0x0D)
                    m[GLOBAL]=r.a
                    self._x(0x01)
                    self._a(m[0x0435])
                    self._compare(r.a,0x46)
                    self._mark(0xC612)
                    if r.p&C:
                        pass
                    else:
                        self._x(r.x+1)
                        self._compare(r.a,0x28)
                        self._mark(0xC617)
                        if r.p&C:
                            pass
                        else:
                            self._x(r.x+1)
                            pass
                        pass
                    m[0x0541]=r.x
                    self._a(0x00)
                    m[0x04C9]=r.a
                    m[0x04CA]=r.a
                    pass
                pass
            pass
        self._mark(0xC625)
        self._rts();return

    def panel_helper_c626(self):
        """$C626: panel helper c626; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC626)
        self._x(0x00)
        m[0x0010]=r.x
        m[0x0011]=r.x
        while True:  # natural loop $C62E
            try:
                self._a(r.x)
                yield from self._external(0xC62F,0xF2AF,0xC632,"call",None)
                if r.pc!=0xC632:return  # preserve nonlocal stack return
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0x07)
                self._compare(r.a,m[0x6F03])
                self._mark(0xC63B)
                if not r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.panel_helper_c646,0xC63D,0xC640)):return
                    pass
                self._x(r.x+1)
                self._compare(r.x,0x1E)
                self._mark(0xC643)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xC645)
                self._rts();return
            except _ContinueLoop_C62E:
                continue

    def panel_helper_c646(self):
        """$C646: panel helper c646; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC646)
        self._a(m[0x0000])
        m[0x000A]=r.a
        self._a(m[0x0001])
        m[0x000B]=r.a
        self._y(0x11)
        while True:  # natural loop $C654
            try:
                self._a(r.y)
                self._push(r.a)
                self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xC65A)
                if r.p&Z:
                    pass
                else:
                    m[0x0002]=r.a
                    yield from self._external(0xC65F,0xF2D7,0xC662,"call",None)
                    if r.pc!=0xC662:return  # preserve nonlocal stack return
                    self._y(0x02)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._compare(r.a,m[0x0011])
                    self._mark(0xC669)
                    if not r.p&C:
                        pass
                    else:
                        m[0x0011]=r.a
                        self._a(m[0x0002])
                        m[0x0010]=r.a
                        pass
                    pass
                self._a(self._pop())
                self._y(r.a)
                self._y(r.y+1)
                self._compare(r.y,0x1B)
                self._mark(0xC679)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xC67B)
                self._rts();return
            except _ContinueLoop_C654:
                continue

    def panel_helper_c67c(self):
        """$C67C: panel helper c67c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC67C)
        self._a(m[0x0318])
        m[0x0000]=r.a
        self._a(m[0x0083])
        self._a(r.a & 0xF0)
        m[0x0318]=r.a
        self._mark(0xC68A)
        if r.p&Z:
            self._a(0x00)
            m[0x0319]=r.a
            self._mark(0xC6AD)
            self._rts();return
        else:
            self._compare(r.a,m[0x0000])
            self._mark(0xC68F)
            if not r.p&Z:
                self._a(0x00)
                m[0x0319]=r.a
                self._a(m[0x0083])
                self._mark(0xC6B6)
                if not r.p&N:
                    pass
                else:
                    self._x(m[0x6F3F])
                    self._compare(r.x,0xF8)
                    self._mark(0xC6BD)
                    if r.p&C:
                        pass
                    else:
                        self._push(r.a)
                        self._a(m[0x6F3F])
                        self._flag(C,False)
                        self._add(0x08)
                        m[0x6F3F]=r.a
                        self._a(self._pop())
                        pass
                    pass
                r.a=self._shift(r.a,True,rotate=False)
                self._mark(0xC6CB)
                if not r.p&N:
                    pass
                else:
                    self._x(m[0x6F3F])
                    self._compare(r.x,0x10)
                    self._mark(0xC6D2)
                    if not r.p&C:
                        pass
                    else:
                        self._push(r.a)
                        self._a(m[0x6F3F])
                        self._flag(C,True)
                        self._add(0x08,subtract=True)
                        m[0x6F3F]=r.a
                        self._a(self._pop())
                        pass
                    pass
                r.a=self._shift(r.a,True,rotate=False)
                self._mark(0xC6E0)
                if not r.p&N:
                    pass
                else:
                    self._x(m[0x6F41])
                    self._compare(r.x,0x94)
                    self._mark(0xC6E7)
                    if r.p&C:
                        pass
                    else:
                        self._push(r.a)
                        self._a(m[0x6F41])
                        self._flag(C,False)
                        self._add(0x08)
                        m[0x6F41]=r.a
                        self._a(self._pop())
                        pass
                    pass
                r.a=self._shift(r.a,True,rotate=False)
                self._mark(0xC6F5)
                if not r.p&N:
                    pass
                else:
                    self._x(m[0x6F41])
                    self._compare(r.x,0x10)
                    self._mark(0xC6FC)
                    if not r.p&C:
                        pass
                    else:
                        self._a(m[0x6F41])
                        self._flag(C,True)
                        self._add(0x08,subtract=True)
                        m[0x6F41]=r.a
                        pass
                    pass
                self._mark(0xC707)
                self._rts();return
            else:
                m[0x0319]=self._nz(m[0x0319]+1)
                self._a(m[0x0319])
                self._compare(r.a,0x0F)
                self._mark(0xC699)
                if not r.p&C:
                    self._mark(0xC6A7)
                    self._rts();return
                else:
                    self._a(0x0F)
                    m[0x0319]=r.a
                    self._a(m[0x005E])
                    self._a(r.a & 0x03)
                    self._mark(0xC6A5)
                    if r.p&Z:
                        self._a(m[0x0083])
                        self._mark(0xC6B6)
                        if not r.p&N:
                            pass
                        else:
                            self._x(m[0x6F3F])
                            self._compare(r.x,0xF8)
                            self._mark(0xC6BD)
                            if r.p&C:
                                pass
                            else:
                                self._push(r.a)
                                self._a(m[0x6F3F])
                                self._flag(C,False)
                                self._add(0x08)
                                m[0x6F3F]=r.a
                                self._a(self._pop())
                                pass
                            pass
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xC6CB)
                        if not r.p&N:
                            pass
                        else:
                            self._x(m[0x6F3F])
                            self._compare(r.x,0x10)
                            self._mark(0xC6D2)
                            if not r.p&C:
                                pass
                            else:
                                self._push(r.a)
                                self._a(m[0x6F3F])
                                self._flag(C,True)
                                self._add(0x08,subtract=True)
                                m[0x6F3F]=r.a
                                self._a(self._pop())
                                pass
                            pass
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xC6E0)
                        if not r.p&N:
                            pass
                        else:
                            self._x(m[0x6F41])
                            self._compare(r.x,0x94)
                            self._mark(0xC6E7)
                            if r.p&C:
                                pass
                            else:
                                self._push(r.a)
                                self._a(m[0x6F41])
                                self._flag(C,False)
                                self._add(0x08)
                                m[0x6F41]=r.a
                                self._a(self._pop())
                                pass
                            pass
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xC6F5)
                        if not r.p&N:
                            pass
                        else:
                            self._x(m[0x6F41])
                            self._compare(r.x,0x10)
                            self._mark(0xC6FC)
                            if not r.p&C:
                                pass
                            else:
                                self._a(m[0x6F41])
                                self._flag(C,True)
                                self._add(0x08,subtract=True)
                                m[0x6F41]=r.a
                                pass
                            pass
                        self._mark(0xC707)
                        self._rts();return
                    else:
                        self._mark(0xC6A7)
                        self._rts();return

    def panel_helper_c708(self):
        """$C708: panel helper c708; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC708)
        self._a(m[0x6F3F])
        self._compare(r.a,0x20)
        self._mark(0xC70D)
        if r.p&C:
            self._y(0x1E)
            while True:  # natural loop $C71B
                try:
                    self._a(m[0x6F3F])
                    self._flag(C,True)
                    self._add(m[(0xC737+r.y)&65535],subtract=True)
                    self._compare(r.a,0x10)
                    self._mark(0xC724)
                    if r.p&C:
                        self._y(r.y-1)
                        self._mark(0xC732)
                        if not r.p&N:
                            continue
                        else:
                            self._y(0xFF)
                            pass
                        pass
                    else:
                        self._a(m[0x6F41])
                        self._flag(C,True)
                        self._add(m[(0xC755+r.y)&65535],subtract=True)
                        self._compare(r.a,0x10)
                        self._mark(0xC72F)
                        if not r.p&C:
                            pass
                        else:
                            self._y(r.y-1)
                            self._mark(0xC732)
                            if not r.p&N:
                                continue
                            else:
                                self._y(0xFF)
                                pass
                            pass
                        pass
                    self._mark(0xC736)
                    self._rts();return
                except _ContinueLoop_C71B:
                    continue
        else:
            self._a(m[0x6F41])
            self._compare(r.a,0x20)
            self._mark(0xC714)
            if r.p&C:
                self._y(0x1E)
                while True:  # natural loop $C71B
                    try:
                        self._a(m[0x6F3F])
                        self._flag(C,True)
                        self._add(m[(0xC737+r.y)&65535],subtract=True)
                        self._compare(r.a,0x10)
                        self._mark(0xC724)
                        if r.p&C:
                            self._y(r.y-1)
                            self._mark(0xC732)
                            if not r.p&N:
                                continue
                            else:
                                self._y(0xFF)
                                pass
                            pass
                        else:
                            self._a(m[0x6F41])
                            self._flag(C,True)
                            self._add(m[(0xC755+r.y)&65535],subtract=True)
                            self._compare(r.a,0x10)
                            self._mark(0xC72F)
                            if not r.p&C:
                                pass
                            else:
                                self._y(r.y-1)
                                self._mark(0xC732)
                                if not r.p&N:
                                    continue
                                else:
                                    self._y(0xFF)
                                    pass
                                pass
                            pass
                        self._mark(0xC736)
                        self._rts();return
                    except _ContinueLoop_C71B:
                        continue
            else:
                self._y(0xFF)
                self._mark(0xC718)
                self._rts();return

    def panel_helper_c773(self):
        """$C773: panel helper c773; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC773)
        self._a(m[PHASE])
        return (yield from self.panel_helper_c776())

    def panel_helper_c776(self):
        """$C776: panel helper c776; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC776)
        index=self._dispatch(0xC776,(51099, 51168, 51168, 51168, 51666, 51778, 51778, 51778, 51844, 51924, 52015, 52095, 52125, 52095, 52163, 52262, 52361))
        return (yield from (self.panel_helper_c79b,self.panel_helper_c7e0,self.panel_helper_c7e0,self.panel_helper_c7e0,self.panel_helper_c9d2,self.panel_helper_ca42,self.panel_helper_ca42,self.panel_helper_ca42,self.panel_helper_ca84,self.panel_helper_cad4,self.panel_helper_cb2f,self.panel_helper_cb7f,self.panel_helper_cb9d,self.panel_helper_cb7f,self.panel_helper_cbc3,self.panel_helper_cc26,self.panel_helper_cc89,)[index]())

    def panel_helper_c79b(self):
        """$C79B: panel helper c79b; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC79B)
        self._a(0xBB)
        yield from self._external(0xC79D,0xF28B,0xC7A0,"call",None)
        if r.pc!=0xC7A0:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
        m[0x042C]=r.a
        self._a(0xF0)
        m[0x6F41]=r.a
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(0x00)
        m[OFFICER_INDEX]=r.a
        self._y(m[0x6F05])
        self._a(m[(0xC7CC+r.y)&65535])
        m[0x6F5D]=r.a
        self._a(0x00)
        m[0x6F8B]=r.a
        m[0x6F5B]=r.a
        m[0x6F5C]=r.a
        m[0x6F62]=r.a
        self._mark(0xC7CB)
        self._rts();return

    def panel_helper_c7e0(self):
        """$C7E0: panel helper c7e0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC7E0)
        if not (yield from self._local_call(self.panel_helper_cd8c,0xC7E0,0xC7E3)):return
        self._a(m[OFFICER_INDEX])
        self._mark(0xC7E6)
        if not r.p&Z:
            self._a(m[0x6F03])
            yield from self._external(0xC81E,0xF368,0xC821,"call",None)
            if r.pc!=0xC821:return  # preserve nonlocal stack return
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x000B]=r.a
            self._a(0x00)
            m[0x000A]=r.a
            self._a(m[OFFICER_INDEX])
            m[0x000C]=r.a
            self._y(0x3D)
            yield from self._external(0xC835,0xEE07,0xC83A,"far_call",41026)
            if r.pc!=0xC83A:return  # preserve nonlocal stack return
            self._a(m[0x6F8B])
            self._compare(r.a,0xFE)
            self._mark(0xC83F)
            if r.p&Z:
                if not (yield from self._local_call(self.panel_helper_ca2a,0xC899,0xC89C)):return
                self._a(m[0x6F03])
                yield from self._external(0xC89F,0xF368,0xC8A2,"call",None)
                if r.pc!=0xC8A2:return  # preserve nonlocal stack return
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x000B]=r.a
                self._a(0x01)
                m[0x000A]=r.a
                self._a(0x00)
                m[0x000C]=r.a
                self._y(0x3D)
                yield from self._external(0xC8B5,0xEE07,0xC8BA,"far_call",41026)
                if r.pc!=0xC8BA:return  # preserve nonlocal stack return
                self._a(0x09)
                m[0x04A0]=r.a
                self._a(0x47)
                m[0x04D6]=r.a
                self._a(0x04)
                m[PHASE]=r.a
                self._a(0x00)
                m[OFFICER_INDEX]=r.a
                self._mark(0xC8CE)
                self._rts();return
            else:
                self._compare(r.a,0xFD)
                self._mark(0xC843)
                if not r.p&Z:
                    self._compare(r.a,0xFC)
                    self._mark(0xC84A)
                    if not r.p&Z:
                        self._compare(r.a,0xFB)
                        self._mark(0xC851)
                        if not r.p&Z:
                            self._compare(r.a,0xFA)
                            self._mark(0xC858)
                            if not r.p&Z:
                                self._compare(r.a,0xF9)
                                self._mark(0xC85F)
                                if not r.p&Z:
                                    self._compare(r.a,0xF8)
                                    self._mark(0xC866)
                                    if not r.p&Z:
                                        self._compare(r.a,0xFF)
                                        self._mark(0xC86D)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            m[OFFICER_INDEX]=self._nz(m[OFFICER_INDEX]+1)
                                            self._a(m[OFFICER_INDEX])
                                            self._compare(r.a,0x20)
                                            self._mark(0xC877)
                                            if not r.p&C:
                                                pass
                                            else:
                                                self._a(0x00)
                                                m[STATE]=r.a
                                                m[PHASE]=r.a
                                                m[0x6F05]=r.a
                                                self._a(0xFF)
                                                m[0x000B]=r.a
                                                m[0x000A]=r.a
                                                self._a(0x00)
                                                m[0x000C]=r.a
                                                self._y(0x3D)
                                                yield from self._external(0xC893,0xEE07,0xC898,"far_call",41026)
                                                if r.pc!=0xC898:return  # preserve nonlocal stack return
                                                pass
                                            pass
                                        self._mark(0xC898)
                                        self._rts();return
                                    else:
                                        self._a(m[0x0041])
                                        m[0x042C]=r.a
                                        self._a(m[0x0040])
                                        m[0x042D]=r.a
                                        self._a(m[0x0042])
                                        m[0x042E]=r.a
                                        self._a(0xE2)
                                        yield from self._external(0xC9BF,0xF28B,0xC9C2,"call",None)
                                        if r.pc!=0xC9C2:return  # preserve nonlocal stack return
                                        self._a(0x10)
                                        m[PHASE]=r.a
                                        self._a(0x00)
                                        m[CITY]=r.a
                                        self._a(0x00)
                                        m[OFFICER_INDEX]=r.a
                                        self._mark(0xC9D1)
                                        self._rts();return
                                else:
                                    self._a(m[0x003A])
                                    m[0x042C]=r.a
                                    self._a(m[0x0039])
                                    m[0x042D]=r.a
                                    self._a(0xE6)
                                    yield from self._external(0xC98B,0xF26D,0xC98E,"call",None)
                                    if r.pc!=0xC98E:return  # preserve nonlocal stack return
                                    self._a(m[0x003D])
                                    m[0x0000]=r.a
                                    self._y(0x3D)
                                    yield from self._external(0xC996,0xEE07,0xC99B,"far_call",41002)
                                    if r.pc!=0xC99B:return  # preserve nonlocal stack return
                                    self._a(0x0F)
                                    m[PHASE]=r.a
                                    self._a(0x00)
                                    m[CITY]=r.a
                                    self._a(0x00)
                                    m[OFFICER_INDEX]=r.a
                                    self._mark(0xC9AA)
                                    self._rts();return
                            else:
                                self._a(m[0x0041])
                                m[0x042C]=r.a
                                self._a(m[0x0040])
                                m[0x042D]=r.a
                                self._a(0xE6)
                                yield from self._external(0xC950,0xF26D,0xC953,"call",None)
                                if r.pc!=0xC953:return  # preserve nonlocal stack return
                                self._a(m[0x003D])
                                m[0x0000]=r.a
                                self._y(0x3D)
                                yield from self._external(0xC95B,0xEE07,0xC960,"far_call",41002)
                                if r.pc!=0xC960:return  # preserve nonlocal stack return
                                self._a(0x0E)
                                m[PHASE]=r.a
                                self._a(0x00)
                                m[CITY]=r.a
                                self._a(0x00)
                                m[OFFICER_INDEX]=r.a
                                self._a(m[0x0042])
                                yield from self._external(0xC972,0xF368,0xC975,"call",None)
                                if r.pc!=0xC975:return  # preserve nonlocal stack return
                                self._y(0x03)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                m[0x6F44]=r.a
                                self._mark(0xC97C)
                                self._rts();return
                        else:
                            self._a(m[0x0038])
                            m[0x042C]=r.a
                            self._y(m[0x0040])
                            self._a(m[(0xC93A+r.y)&65535])
                            m[0x042D]=r.a
                            self._a(0xC3)
                            yield from self._external(0xC92C,0xF28B,0xC92F,"call",None)
                            if r.pc!=0xC92F:return  # preserve nonlocal stack return
                            self._a(0x0C)
                            m[PHASE]=r.a
                            self._a(0x00)
                            m[OFFICER_INDEX]=r.a
                            self._mark(0xC939)
                            self._rts();return
                    else:
                        self._a(m[0x0038])
                        m[0x042C]=r.a
                        self._a(0xC1)
                        yield from self._external(0xC90D,0xF28B,0xC910,"call",None)
                        if r.pc!=0xC910:return  # preserve nonlocal stack return
                        self._a(0x0B)
                        m[PHASE]=r.a
                        self._a(0x00)
                        m[OFFICER_INDEX]=r.a
                        self._mark(0xC91A)
                        self._rts();return
                else:
                    if not (yield from self._local_call(self.panel_helper_ca2a,0xC8CF,0xC8D2)):return
                    self._a(m[0x6F03])
                    yield from self._external(0xC8D5,0xF368,0xC8D8,"call",None)
                    if r.pc!=0xC8D8:return  # preserve nonlocal stack return
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x000B]=r.a
                    self._a(0x01)
                    m[0x000A]=r.a
                    self._a(0x00)
                    m[0x000C]=r.a
                    self._y(0x3D)
                    yield from self._external(0xC8EB,0xEE07,0xC8F0,"far_call",41026)
                    if r.pc!=0xC8F0:return  # preserve nonlocal stack return
                    self._a(0x09)
                    m[0x04A0]=r.a
                    self._a(0xA2)
                    m[0x04D6]=r.a
                    self._a(0x08)
                    m[PHASE]=r.a
                    self._a(0x00)
                    m[OFFICER_INDEX]=r.a
                    self._mark(0xC904)
                    self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xC7ED)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0300])
                self._compare(r.a,0xFF)
                self._mark(0xC7F4)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x6F03])
                    yield from self._external(0xC7F9,0xF368,0xC7FC,"call",None)
                    if r.pc!=0xC7FC:return  # preserve nonlocal stack return
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x000B]=r.a
                    self._a(0x00)
                    m[0x000A]=r.a
                    self._a(m[OFFICER_INDEX])
                    m[0x000C]=r.a
                    self._y(0x3D)
                    yield from self._external(0xC810,0xEE07,0xC815,"far_call",41026)
                    if r.pc!=0xC815:return  # preserve nonlocal stack return
                    m[OFFICER_INDEX]=self._nz(m[OFFICER_INDEX]+1)
                    pass
                pass
            self._mark(0xC898)
            self._rts();return

    def panel_helper_c9d2(self):
        """$C9D2: panel helper c9d2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC9D2)
        if not (yield from self._local_call(self.panel_helper_ca02,0xC9D2,0xC9D5)):return
        self._a(m[0x6F03])
        yield from self._external(0xC9D8,0xF368,0xC9DB,"call",None)
        if r.pc!=0xC9DB:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x000B]=r.a
        self._a(0x01)
        m[0x000A]=r.a
        self._a(0x01)
        m[0x000C]=r.a
        self._y(0x3D)
        yield from self._external(0xC9EE,0xEE07,0xC9F3,"far_call",41026)
        if r.pc!=0xC9F3:return  # preserve nonlocal stack return
        self._a(m[0x04A0])
        self._a(r.a | m[0x0140])
        self._mark(0xC9F9)
        if not r.p&Z:
            pass
        else:
            yield from self._external(0xC9FB,0xECEE,0xC9FE,"call",None)
            if r.pc!=0xC9FE:return  # preserve nonlocal stack return
            m[PHASE]=self._nz(m[PHASE]+1)
            pass
        self._mark(0xCA01)
        self._rts();return

    def panel_helper_ca02(self):
        """$CA02: panel helper ca02; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCA02)
        self._a(m[0x050E])
        if not (yield from self._local_call(self.panel_helper_ca0f,0xCA05,0xCA08)):return
        self._a(m[0x003A])
        if not (yield from self._local_call(self.panel_helper_ca0f,0xCA0B,0xCA0E)):return
        self._mark(0xCA0E)
        self._rts();return

    def panel_helper_ca0f(self):
        """$CA0F: panel helper ca0f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCA0F)
        self._push(r.a)
        self._a(r.a & 0x07)
        self._x(r.a)
        self._a(self._pop())
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._y(r.a)
        self._a(m[(0x04E0+r.y)&65535])
        self._a(r.a | m[(0xCA22+r.x)&65535])
        m[(0x04E0+r.y)&65535]=r.a
        self._mark(0xCA21)
        self._rts();return

    def panel_helper_ca2a(self):
        """$CA2A: panel helper ca2a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCA2A)
        self._a(m[0x003A])
        m[0x000A]=r.a
        self._y(0x3B)
        yield from self._external(0xCA32,0xEE07,0xCA37,"far_call",40969)
        if r.pc!=0xCA37:return  # preserve nonlocal stack return
        self._a(m[0x000B])
        self._a(r.a & 0x80)
        self._a(r.a ^ 0x80)
        m[0x0150]=r.a
        self._mark(0xCA41)
        self._rts();return

    def panel_helper_ca42(self):
        """$CA42: panel helper ca42; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCA42)
        if not (yield from self._local_call(self.panel_helper_ca02,0xCA42,0xCA45)):return
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xCA48)
        if not r.p&N:
            pass
        else:
            self._a(0x03)
            m[GLOBAL]=r.a
            self._a(0x00)
            m[0x0510]=r.a
            m[0x0511]=r.a
            m[0x0512]=r.a
            m[0x0513]=r.a
            self._a(0x0A)
            m[0x0500]=r.a
            self._a(0x00)
            m[0x0501]=r.a
            m[0x0502]=r.a
            m[0x0503]=r.a
            self._a(0x80)
            m[0x0504]=r.a
            self._a(0x00)
            m[0x0505]=r.a
            self._a(0x00)
            m[0x0506]=r.a
            self._y(0x2C)
            yield from self._external(0xCA7E,0xEE07,0xCA83,"far_call",40963)
            if r.pc!=0xCA83:return  # preserve nonlocal stack return
            pass
        self._mark(0xCA83)
        self._rts();return

    def panel_helper_ca84(self):
        """$CA84: panel helper ca84; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCA84)
        if not (yield from self._local_call(self.panel_helper_ca02,0xCA84,0xCA87)):return
        self._a(m[0x6F03])
        yield from self._external(0xCA8A,0xF368,0xCA8D,"call",None)
        if r.pc!=0xCA8D:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x000B]=r.a
        self._a(0x01)
        m[0x000A]=r.a
        self._a(0x01)
        m[0x000C]=r.a
        self._y(0x3D)
        yield from self._external(0xCAA0,0xEE07,0xCAA5,"far_call",41026)
        if r.pc!=0xCAA5:return  # preserve nonlocal stack return
        self._a(m[0x04A0])
        self._a(r.a | m[0x0140])
        self._mark(0xCAAB)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x6F03])
            yield from self._external(0xCAB0,0xF368,0xCAB3,"call",None)
            if r.pc!=0xCAB3:return  # preserve nonlocal stack return
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x000B]=r.a
            self._a(0x02)
            m[0x000A]=r.a
            self._a(0x00)
            m[0x000C]=r.a
            self._y(0x3D)
            yield from self._external(0xCAC6,0xEE07,0xCACB,"far_call",41026)
            if r.pc!=0xCACB:return  # preserve nonlocal stack return
            self._a(0x05)
            m[0x04A0]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            pass
        self._mark(0xCAD3)
        self._rts();return

    def panel_helper_cad4(self):
        """$CAD4: panel helper cad4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCAD4)
        if not (yield from self._local_call(self.panel_helper_ca02,0xCAD4,0xCAD7)):return
        self._a(m[0x6F03])
        yield from self._external(0xCADA,0xF368,0xCADD,"call",None)
        if r.pc!=0xCADD:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x000B]=r.a
        self._a(0x01)
        m[0x000A]=r.a
        self._a(0x01)
        m[0x000C]=r.a
        self._y(0x3D)
        yield from self._external(0xCAF0,0xEE07,0xCAF5,"far_call",41026)
        if r.pc!=0xCAF5:return  # preserve nonlocal stack return
        self._a(m[0x04A0])
        self._a(r.a | m[0x0140])
        self._mark(0xCAFB)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0507])
            self._y(m[0x6F8C])
            self._mark(0xCB03)
            if not r.p&Z:
                pass
            else:
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                pass
            self._a(r.a & 0x07)
            yield from self._external(0xCB0B,0xF368,0xCB0E,"call",None)
            if r.pc!=0xCB0E:return  # preserve nonlocal stack return
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x000B]=r.a
            self._a(0x03)
            m[0x000A]=r.a
            self._a(0x00)
            m[0x000C]=r.a
            self._y(0x3D)
            yield from self._external(0xCB21,0xEE07,0xCB26,"far_call",41026)
            if r.pc!=0xCB26:return  # preserve nonlocal stack return
            self._a(0x06)
            m[0x04A0]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            pass
        self._mark(0xCB2E)
        self._rts();return

    def panel_helper_cb2f(self):
        """$CB2F: panel helper cb2f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCB2F)
        if not (yield from self._local_call(self.panel_helper_ca02,0xCB2F,0xCB32)):return
        self._a(m[0x0507])
        self._y(m[0x6F8C])
        self._mark(0xCB38)
        if not r.p&Z:
            pass
        else:
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            pass
        self._a(r.a & 0x07)
        yield from self._external(0xCB40,0xF368,0xCB43,"call",None)
        if r.pc!=0xCB43:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x000B]=r.a
        self._a(0x01)
        m[0x000A]=r.a
        self._a(0x01)
        m[0x000C]=r.a
        self._y(0x3D)
        yield from self._external(0xCB56,0xEE07,0xCB5B,"far_call",41026)
        if r.pc!=0xCB5B:return  # preserve nonlocal stack return
        self._a(m[0x04A0])
        self._a(r.a | m[0x0140])
        self._mark(0xCB61)
        if not r.p&Z:
            self._mark(0xCB2E)
            self._rts();return
        else:
            self._a(0xBB)
            yield from self._external(0xCB65,0xF28B,0xCB68,"call",None)
            if r.pc!=0xCB68:return  # preserve nonlocal stack return
            self._y(0x00)
            self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
            m[0x042C]=r.a
            self._a(0x01)
            m[PHASE]=r.a
            self._a(0x00)
            m[OFFICER_INDEX]=r.a
            self._a(0x01)
            m[0x6F8B]=r.a
            self._mark(0xCB7E)
            self._rts();return

    def panel_helper_cb7f(self):
        """$CB7F: panel helper cb7f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCB7F)
        m[OFFICER_INDEX]=self._nz(m[OFFICER_INDEX]+1)
        self._a(m[OFFICER_INDEX])
        self._compare(r.a,0xF0)
        self._mark(0xCB87)
        if not r.p&C:
            pass
        else:
            self._a(m[0x0027])
            m[0x042C]=r.a
            self._a(0xC2)
            yield from self._external(0xCB91,0xF28B,0xCB94,"call",None)
            if r.pc!=0xCB94:return  # preserve nonlocal stack return
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0x00)
            m[OFFICER_INDEX]=r.a
            pass
        self._mark(0xCB9C)
        self._rts();return

    def panel_helper_cb9d(self):
        """$CB9D: panel helper cb9d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCB9D)
        m[OFFICER_INDEX]=self._nz(m[OFFICER_INDEX]+1)
        self._a(m[OFFICER_INDEX])
        self._compare(r.a,0xF0)
        self._mark(0xCBA5)
        if not r.p&C:
            pass
        else:
            self._a(0xBB)
            yield from self._external(0xCBA9,0xF28B,0xCBAC,"call",None)
            if r.pc!=0xCBAC:return  # preserve nonlocal stack return
            self._y(0x00)
            self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
            m[0x042C]=r.a
            self._a(0x01)
            m[PHASE]=r.a
            self._a(0x00)
            m[OFFICER_INDEX]=r.a
            self._a(0x01)
            m[0x6F8B]=r.a
            pass
        self._mark(0xCBC2)
        self._rts();return

    def panel_helper_cbc3(self):
        """$CBC3: panel helper cbc3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCBC3)
        self._a(m[0x003D])
        m[0x0000]=r.a
        self._a(0xA7)
        m[0x000A]=r.a
        self._x(0x00)
        yield from self._external(0xCBD0,0xCE1F,0xCBD3,"call",None)
        if r.pc!=0xCBD3:return  # preserve nonlocal stack return
        self._a(m[CITY])
        return (yield from self.panel_helper_cbd6())

    def panel_helper_cbd6(self):
        """$CBD6: panel helper cbd6; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCBD6)
        index=self._dispatch(0xCBD6,(52189, 52234))
        return (yield from (self.panel_helper_cbdd,self.panel_helper_cc0a,)[index]())

    def panel_helper_cbdd(self):
        """$CBDD: panel helper cbdd; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCBDD)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xCBE2)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xCBE9)
            if not r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xCBEB,0xCBEE)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                self._mark(0xCBF3)
                if r.p&Z:
                    pass
                else:
                    self._a(m[0x0043])
                    m[0x042C]=r.a
                    self._a(m[0x0040])
                    m[0x042D]=r.a
                    self._a(0xE0)
                    yield from self._external(0xCC03,0xF26D,0xCC06,"call",None)
                    if r.pc!=0xCC06:return  # preserve nonlocal stack return
                    m[CITY]=self._nz(m[CITY]+1)
                    pass
                pass
            pass
        self._mark(0xCC09)
        self._rts();return

    def panel_helper_cc0a(self):
        """$CC0A: panel helper cc0a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC0A)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xCC0F)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xCC16)
            if not r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xCC18,0xCC1B)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                self._mark(0xCC20)
                if r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.panel_helper_cd6f,0xCC22,0xCC25)):return
                    pass
                pass
            pass
        self._mark(0xCC25)
        self._rts();return

    def panel_helper_cc26(self):
        """$CC26: panel helper cc26; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC26)
        self._a(m[0x003D])
        m[0x0000]=r.a
        self._a(0xA7)
        m[0x000A]=r.a
        self._x(0x00)
        yield from self._external(0xCC33,0xCE1F,0xCC36,"call",None)
        if r.pc!=0xCC36:return  # preserve nonlocal stack return
        self._a(m[CITY])
        return (yield from self.panel_helper_cc39())

    def panel_helper_cc39(self):
        """$CC39: panel helper cc39; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC39)
        index=self._dispatch(0xCC39,(52288, 52333))
        return (yield from (self.panel_helper_cc40,self.panel_helper_cc6d,)[index]())

    def panel_helper_cc40(self):
        """$CC40: panel helper cc40; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC40)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xCC45)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xCC4C)
            if not r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xCC4E,0xCC51)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                self._mark(0xCC56)
                if r.p&Z:
                    pass
                else:
                    self._a(m[0x0037])
                    m[0x042C]=r.a
                    self._a(m[0x0039])
                    m[0x042D]=r.a
                    self._a(0xE1)
                    yield from self._external(0xCC66,0xF26D,0xCC69,"call",None)
                    if r.pc!=0xCC69:return  # preserve nonlocal stack return
                    m[CITY]=self._nz(m[CITY]+1)
                    pass
                pass
            pass
        self._mark(0xCC6C)
        self._rts();return

    def panel_helper_cc6d(self):
        """$CC6D: panel helper cc6d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC6D)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xCC72)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xCC79)
            if not r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xCC7B,0xCC7E)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                self._mark(0xCC83)
                if r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.panel_helper_cd6f,0xCC85,0xCC88)):return
                    pass
                pass
            pass
        self._mark(0xCC88)
        self._rts();return

    def panel_helper_cc89(self):
        """$CC89: panel helper cc89; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC89)
        self._a(m[CITY])
        return (yield from self.panel_helper_cc8c())

    def panel_helper_cc8c(self):
        """$CC8C: panel helper cc8c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC8C)
        index=self._dispatch(0xCC8C,(52373, 52440, 52563))
        return (yield from (self.panel_helper_cc95,self.panel_helper_ccd8,self.panel_helper_cd53,)[index]())

    def panel_helper_cc95(self):
        """$CC95: panel helper cc95; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC95)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xCC9A)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xCCA1)
            if not r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xCCA3,0xCCA6)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                self._mark(0xCCAB)
                if r.p&Z:
                    pass
                else:
                    self._a(m[0x0041])
                    m[0x042C]=r.a
                    self._a(0xE3)
                    self._y(m[0x0039])
                    self._mark(0xCCB8)
                    if r.p&Z:
                        pass
                    else:
                        self._a(0xEE)
                        pass
                    yield from self._external(0xCCBC,0xF26D,0xCCBF,"call",None)
                    if r.pc!=0xCCBF:return  # preserve nonlocal stack return
                    m[CITY]=self._nz(m[CITY]+1)
                    self._a(0x00)
                    m[0x0424]=r.a
                    m[0x0425]=r.a
                    self._a(m[0x0042])
                    m[0x0000]=r.a
                    self._y(0x3D)
                    yield from self._external(0xCCD2,0xEE07,0xCCD7,"far_call",41002)
                    if r.pc!=0xCCD7:return  # preserve nonlocal stack return
                    pass
                pass
            pass
        self._mark(0xCCD7)
        self._rts();return

    def panel_helper_ccd8(self):
        """$CCD8: panel helper ccd8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCCD8)
        self._a(m[0x0042])
        m[0x0000]=r.a
        self._a(0xA7)
        m[0x000A]=r.a
        self._x(0x00)
        yield from self._external(0xCCE5,0xCE1F,0xCCE8,"call",None)
        if r.pc!=0xCCE8:return  # preserve nonlocal stack return
        self._a(0x46)
        m[0x0010]=r.a
        self._a(0xCD)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xCCF7,0xED1E,0xCCFA,"call",None)
        if r.pc!=0xCCFA:return  # preserve nonlocal stack return
        self._a(0x4A)
        m[0x0010]=r.a
        self._a(0xCD)
        m[0x0011]=r.a
        self._a(0x4E)
        m[0x0000]=r.a
        self._a(0xCD)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xCD11,0xEDF5,0xCD14,"call",None)
        if r.pc!=0xCD14:return  # preserve nonlocal stack return
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xCD19)
        if not r.p&Z:
            self._mark(0xCD45)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xCD20)
            if not r.p&Z:
                self._mark(0xCD45)
                self._rts();return
            else:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                self._mark(0xCD27)
                if r.p&Z:
                    self._mark(0xCCD7)
                    self._rts();return
                else:
                    self._a(m[0x0040])
                    m[0x042C]=r.a
                    m[CITY]=self._nz(m[CITY]+1)
                    self._a(m[0x0012])
                    m[OFFICER_INDEX]=r.a
                    self._mark(0xCD38)
                    if not r.p&Z:
                        self._a(0xE5)
                        yield from self._external(0xCD42,0xF28B,0xCD45,"call",None)
                        if r.pc!=0xCD45:return  # preserve nonlocal stack return
                        self._mark(0xCD45)
                        self._rts();return
                    else:
                        self._a(0xE4)
                        yield from self._external(0xCD3C,0xF28B,0xCD3F,"call",None)
                        if r.pc!=0xCD3F:return  # preserve nonlocal stack return
                        self._mark(0xCD3F)
                        self._rts();return

    def panel_helper_cd53(self):
        """$CD53: panel helper cd53; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCD53)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xCD58)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xCD5F)
            if not r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.panel_helper_a1c2,0xCD61,0xCD64)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                self._mark(0xCD69)
                if r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.panel_helper_cd6f,0xCD6B,0xCD6E)):return
                    pass
                pass
            pass
        self._mark(0xCD6E)
        self._rts();return

    def panel_helper_cd6f(self):
        """$CD6F: panel helper cd6f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCD6F)
        self._a(0xBB)
        yield from self._external(0xCD71,0xF28B,0xCD74,"call",None)
        if r.pc!=0xCD74:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
        m[0x042C]=r.a
        self._a(m[OFFICER_INDEX])
        m[0x6F8B]=r.a
        self._a(0x01)
        m[PHASE]=r.a
        self._a(0x00)
        m[OFFICER_INDEX]=r.a
        self._mark(0xCD8B)
        self._rts();return

    def panel_helper_cd8c(self):
        """$CD8C: panel helper cd8c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCD8C)
        self._a(m[0xFFF9])
        self._compare(r.a,0xFF)
        self._mark(0xCD91)
        if not r.p&Z:
            self._mark(0xCDDC)
            self._rts();return
        else:
            self._a(m[0x0083])
            self._a(r.a & 0x08)
            self._mark(0xCD98)
            if r.p&Z:
                self._mark(0xCDDC)
                self._rts();return
            else:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x01)
                self._mark(0xCD9F)
                if r.p&Z:
                    self._mark(0xCDDC)
                    self._rts();return
                else:
                    self._a(0x62)
                    yield from self._external(0xCDA3,0xE693,0xCDA6,"call",None)
                    if r.pc!=0xCDA6:return  # preserve nonlocal stack return
                    self._a(m[0x6FE2])
                    self._compare(r.a,0xFF)
                    self._mark(0xCDAB)
                    if r.p&Z:
                        self._a(m[0x6F0A])
                        m[0x6FE2]=r.a
                        self._a(m[0x6F12])
                        m[0x6FE3]=r.a
                        self._a(m[0x6F1A])
                        m[0x6FE4]=r.a
                        self._a(m[0x6F22])
                        m[0x6FE5]=r.a
                        self._a(m[0x6F2A])
                        m[0x6FE6]=r.a
                        self._a(m[0x6F32])
                        m[0x6FE7]=r.a
                        self._a(m[0x6F3A])
                        m[0x6FE8]=r.a
                        self._a(0x03)
                        m[0x6F0A]=r.a
                        m[0x6F12]=r.a
                        m[0x6F1A]=r.a
                        m[0x6F22]=r.a
                        m[0x6F2A]=r.a
                        m[0x6F32]=r.a
                        m[0x6F3A]=r.a
                        self._mark(0xCE1E)
                        self._rts();return
                    else:
                        self._a(m[0x6FE2])
                        m[0x6F0A]=r.a
                        self._a(m[0x6FE3])
                        m[0x6F12]=r.a
                        self._a(m[0x6FE4])
                        m[0x6F1A]=r.a
                        self._a(m[0x6FE5])
                        m[0x6F22]=r.a
                        self._a(m[0x6FE6])
                        m[0x6F2A]=r.a
                        self._a(m[0x6FE7])
                        m[0x6F32]=r.a
                        self._a(m[0x6FE8])
                        m[0x6F3A]=r.a
                        self._a(0xFF)
                        m[0x6FE2]=r.a
                        self._mark(0xCDDC)
                        self._rts();return

