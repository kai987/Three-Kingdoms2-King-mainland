"""Readable banked global UI controllers and auxiliary city presentation jobs.

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
STATE,PHASE,COMMAND,SIDE,AP=0x500,0x501,0x502,0x504,0x505
ROUND,RULERS,SELECTED_SLOT,ACTOR_SLOT,CITY,CONTROLLER=0x506,0x507,0x509,0x50A,0x50E,0x50F
TACTIC,TACTIC_FAILED,ANIMATION=0x543,0x544,0x4C8
NEW_BUTTONS,REPEAT_BUTTONS,GLOBAL,NMI_SCENE,PPU_JOBS=0x81,0x87,0x7A,0x78,0x7E

@dataclass
class UIRegisters:
    a:int=0
    x:int=0
    y:int=0
    sp:int=0xFD
    p:int=U
    pc:int=0xA028

class UIControlBase:
    def __init__(self,memory,rom,services=None):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned battle ROM required')
        self.memory=memory;self.rom=bytes(rom);self.services=services
        self.registers=UIRegisters();self.events=[];self.pending=None;self._program=None
        self._blocks=0;self._limit=200000
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
        return dict(status=status,before=self._before,after=self.fields(),
                    control_blocks=self._blocks,events=list(self.events),pending=self.pending)
    def resume(self):
        if self._program is None:raise RuntimeError('No pending battle invocation')
        return self._drive()
    def tick(self,registers=None,**kwargs):return self.run_entry(self.PUBLIC_ENTRIES[0],registers=registers,**kwargs)
    def run_entry(self,entry=None,*,registers=None,seed_return=False,return_pc=None,max_blocks=200000):
        if self._program is not None:raise RuntimeError('Resume the existing UI invocation first')
        if entry is None:entry=self.PUBLIC_ENTRIES[0]
        self.registers=registers or UIRegisters();r=self.registers
        if r.p&D:raise ValueError('NES binary arithmetic requires D=0')
        if seed_return:
            if return_pc not in(None,0x0200):raise ValueError('Synthetic fixture return only permits0200')
            self.memory[0x1FE:0x200]=bytes((255,1));r.sp=0xFD
        self._return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535 if return_pc is None else return_pc;self._return_sp=(r.sp+2)&255;self._before=self.fields()
        self.events=[];self.pending=None;self._blocks=0;self._limit=max_blocks;r.pc=entry
        self._program=self._entry(entry)
        return self._drive()

    def fields(self):
        m=self.memory
        return dict(global_state=m[0x7A],NMI_scene=m[0x78],UI_state=m[0x540],UI_phase=m[0x541],
                    panel_job=m[0x140],panel_kind=m[0x150],list_job=m[0x478],
                    animation_job=m[0x4A0],animation_kind=m[0x4A2],PPU_jobs=m[0x7E])
    def __call__(self,call):
        if tuple(call.entry_banks[1:3])!=self.PAIR or call.target not in self.PUBLIC_ENTRIES:
            return {'status':'dependency','reason':'UI caller pair/entry outside this owned domain'}
        if self._program is not None:
            if self._call_owner is not call:return {'status':'dependency','reason':'Another caller owns the pending UI request'}
            return self.resume()
        self._call_owner=call
        return self.run_entry(call.target,registers=call.registers,return_pc=call.return_pc)


UI_STATE,UI_PHASE=0x540,0x541

class CityUIWorkers(UIControlBase):
    PAIR=(29, 30)
    PUBLIC_ENTRIES=(40969, 40975, 41023, 40993, 40996, 41005, 41017)
    def fields(self):
        m=self.memory
        return dict(global_state=m[0x7A],NMI_scene=m[0x78],parent_city_state=m[0x400],parent_city_phase=m[0x401],
                    panel_job=m[0x140],panel_kind=m[0x150],list_job=m[0x478],list_mode=m[0x479],list_cursor=m[0x47A],
                    animation_job=m[0x4A0],animation_phase=m[0x4A1],animation_kind=m[0x4A2],PPU_jobs=m[0x7E])

    def _entry(self,entry):
        if entry==0xA009:return self.panel_entry()
        elif entry==0xA00F:return self.list_entry()
        elif entry==0xA021:return self.header_entry()
        elif entry==0xA024:return self.header_packet_entry()
        elif entry==0xA02D:return self.alternate_header_entry()
        elif entry==0xA039:return self.block_menu_entry()
        elif entry==0xA03F:return self.animation_entry()
        elif entry==0xA77F:return self.header_cadence_16()
        elif entry==0xA78A:return self.header_cadence_4()
        elif entry==0xA7B2:return self.request_6F05_header()
        elif entry==0xABD2:return self.update_panel_job()
        elif entry==0xAD92:return self.initialize_city_panel()
        elif entry==0xADF3:return self.open_panel_row_group()
        elif entry==0xAEC9:return self.close_panel_row_group()
        elif entry==0xAF66:return self.cityuiworkers_af66()
        elif entry==0xAF77:return self.cityuiworkers_af77()
        elif entry==0xB040:return self.cityuiworkers_b040()
        elif entry==0xB091:return self.cityuiworkers_b091()
        elif entry==0xB0AB:return self.cityuiworkers_b0ab()
        elif entry==0xB14C:return self.cityuiworkers_b14c()
        elif entry==0xB23A:return self.cityuiworkers_b23a()
        elif entry==0xB27A:return self.cityuiworkers_b27a()
        elif entry==0xB989:return self.update_list_job()
        elif entry==0xBC71:return self.block_menu_tick()
        elif entry==0xBC83:return self.cityuiworkers_bc74_phase_0()
        elif entry==0xBC9B:return self.cityuiworkers_bc74_phase_1()
        elif entry==0xBD03:return self.cityuiworkers_bc74_phase_2()
        elif entry==0xBD38:return self.cityuiworkers_bc74_phase_3()
        elif entry==0xBD60:return self.cityuiworkers_bc74_phase_4()
        elif entry==0xBD92:return self.cityuiworkers_bc74_phase_5()
        elif entry==0xBDF1:return self.cityuiworkers_bdf1()
        elif entry==0xBDFE:return self.cityuiworkers_bdfe()
        elif entry==0xBE36:return self.update_animation_job()
        elif entry==0xBEBB:return self.cityuiworkers_be72_phase_0()
        elif entry==0xBEEB:return self.cityuiworkers_be72_phase_1()
        elif entry==0xBF2F:return self.cityuiworkers_be72_phase_2()
        elif entry==0xBF70:return self.cityuiworkers_be72_phase_3()
        elif entry==0xBFBF:return self.cityuiworkers_be72_phase_4()
        elif entry==0xBFF3:return self.cityuiworkers_be72_phase_5()
        elif entry==0xC046:return self.cityuiworkers_be72_phase_6()
        elif entry==0xC090:return self.cityuiworkers_be72_phase_7()
        elif entry==0xC0C8:return self.cityuiworkers_be72_phase_8()
        elif entry==0xC123:return self.cityuiworkers_be72_phase_9()
        elif entry==0xC168:return self.cityuiworkers_be72_phase_10()
        elif entry==0xC1AC:return self.cityuiworkers_be72_phase_11()
        elif entry==0xC1FA:return self.cityuiworkers_be72_phase_12()
        elif entry==0xC25D:return self.cityuiworkers_be72_phase_13()
        elif entry==0xC2DD:return self.cityuiworkers_be72_phase_14()
        elif entry==0xC33D:return self.cityuiworkers_be72_phase_15()
        elif entry==0xC3A2:return self.cityuiworkers_be72_phase_16()
        elif entry==0xC3F6:return self.cityuiworkers_be72_phase_17()
        elif entry==0xC43E:return self.cityuiworkers_be72_phase_18()
        elif entry==0xC4E1:return self.cityuiworkers_be72_phase_19()
        elif entry==0xC511:return self.cityuiworkers_be72_phase_20()
        elif entry==0xC556:return self.cityuiworkers_be72_phase_21()
        elif entry==0xC5B1:return self.cityuiworkers_be72_phase_22()
        elif entry==0xC5F7:return self.cityuiworkers_be72_phase_23()
        elif entry==0xC636:return self.cityuiworkers_be72_phase_24()
        elif entry==0xC67D:return self.cityuiworkers_be72_phase_25()
        elif entry==0xC6C6:return self.cityuiworkers_be72_phase_26()
        elif entry==0xC75F:return self.cityuiworkers_be72_phase_27()
        elif entry==0xC7D1:return self.cityuiworkers_be72_phase_28()
        elif entry==0xC800:return self.cityuiworkers_be72_phase_29()
        elif entry==0xC830:return self.cityuiworkers_be72_phase_30()
        elif entry==0xC87D:return self.cityuiworkers_be72_phase_31()
        elif entry==0xC8B4:return self.cityuiworkers_be72_phase_32()
        elif entry==0xC8F1:return self.cityuiworkers_be72_phase_33()
        elif entry==0xC926:return self.cityuiworkers_be72_phase_34()
        elif entry==0xC96D:return self.cityuiworkers_c96d()
        elif entry==0xC98A:return self.cityuiworkers_c98a()
        elif entry==0xC994:return self.cityuiworkers_c994()
        elif entry==0xC996:return self.cityuiworkers_c996()
        elif entry==0xC9D0:return self.cityuiworkers_c9c5_phase_1()
        elif entry==0xC9E8:return self.cityuiworkers_c9c5_phase_0()
        elif entry==0xCA4E:return self.cityuiworkers_c9c5_phase_2()
        elif entry==0xCAC5:return self.initialize_packet_animation()
        elif entry==0xCB52:return self.cityuiworkers_c9c5_phase_3()
        elif entry==0xCBD2:return self.finish_animation_row_batch()
        elif entry==0xCC09:return self.cityuiworkers_cc09()
        raise ValueError("Entry outside immutable UI procedure catalog")

    def panel_entry(self):
        """$A009: panel entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA009)
        return (yield from self.update_panel_job())

    def list_entry(self):
        """$A00F: list entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA00F)
        return (yield from self.update_list_job())

    def header_entry(self):
        """$A021: header entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA021)
        return (yield from self.header_cadence_16())

    def header_packet_entry(self):
        """$A024: header packet entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA024)
        return (yield from self.request_6F05_header())

    def alternate_header_entry(self):
        """$A02D: alternate header entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA02D)
        return (yield from self.header_cadence_4())

    def block_menu_entry(self):
        """$A039: block menu entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA039)
        return (yield from self.block_menu_tick())

    def animation_entry(self):
        """$A03F: animation entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA03F)
        return (yield from self.update_animation_job())

    def header_cadence_16(self):
        """$A77F: header cadence 16; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA77F)
        self._a(m[0x005E])
        self._flag(C,False)
        self._add(0x05)
        self._a(r.a & 0x0F)
        self._mark(0xA787)
        if r.p&Z:
            return (yield from self.request_6F05_header())
        else:
            self._mark(0xA789)
            self._rts();return

    def header_cadence_4(self):
        """$A78A: header cadence 4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA78A)
        self._a(m[0x005E])
        self._flag(C,False)
        self._add(0x01)
        self._a(r.a & 0x03)
        self._mark(0xA792)
        if not r.p&Z:
            self._mark(0xA7B1)
            self._rts();return
        else:
            self._a(m[0x005E])
            self._flag(C,False)
            self._add(0x01)
            self._a(r.a & 0x04)
            self._mark(0xA79C)
            if not r.p&Z:
                return (yield from self.request_6F05_header())
            else:
                self._y(0x3A)
                while True:  # natural loop $A7A0
                    self._a(m[(0xA7F6+r.y)&65535])
                    m[(0x0380+r.y)&65535]=r.a
                    self._y(r.y-1)
                    self._mark(0xA7A7)
                    if not r.p&N:
                        continue
                    else:
                        pass
                    self._a(m[PPU_JOBS])
                    self._a(r.a | 0x04)
                    m[PPU_JOBS]=r.a
                    self._mark(0xA7B1)
                    self._rts();return

    def request_6F05_header(self):
        """$A7B2: request 6F05 header; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA7B2)
        self._a(0x00)
        m[0x0002]=r.a
        self._a(m[0x6F05])
        m[0x0001]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        m[0x0003]=r.a
        yield from self._external(0xA7C5,0xE9BA,0xA7C8,"call",None)
        if r.pc!=0xA7C8:return  # preserve nonlocal stack return
        self._y(0x3A)
        while True:  # natural loop $A7CA
            self._a(m[(0xA7F6+r.y)&65535])
            m[(0x0380+r.y)&65535]=r.a
            self._y(r.y-1)
            self._mark(0xA7D1)
            if not r.p&N:
                continue
            else:
                pass
            self._a(m[0x0007])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xA7DA)
            if r.p&Z:
                pass
            else:
                self._flag(C,False)
                self._add(0x76)
                m[0x03AA]=r.a
                pass
            self._a(m[0x0007])
            self._a(r.a & 0x0F)
            self._flag(C,False)
            self._add(0x76)
            m[0x03AB]=r.a
            self._a(m[PPU_JOBS])
            self._a(r.a | 0x04)
            m[PPU_JOBS]=r.a
            self._mark(0xA7F5)
            self._rts();return

    def update_panel_job(self):
        """$ABD2: update panel job; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xABD2)
        self._a(m[0x037C])
        self._mark(0xABD5)
        if r.p&Z:
            pass
        else:
            self._y(0x31)
            yield from self._external(0xABD9,0xF25F,0xABDC,"call",None)
            if r.pc!=0xABDC:return  # preserve nonlocal stack return
            self._a(m[0x037D])
            self._compare(r.a,0xFF)
            self._mark(0xABE1)
            if r.p&Z:
                pass
            else:
                self._a(0x01)
                if not (yield from self._local_call(self.cityuiworkers_b14c,0xABE5,0xABE8)):return
                pass
            self._a(m[0x037E])
            self._compare(r.a,0xFF)
            self._mark(0xABED)
            if r.p&Z:
                pass
            else:
                self._a(0x02)
                if not (yield from self._local_call(self.cityuiworkers_b14c,0xABF1,0xABF4)):return
                pass
            pass
        self._a(m[0x0140])
        self._mark(0xABF7)
        if r.p&Z:
            self._mark(0xAC38)
            self._rts();return
        else:
            self._a(m[0x0140])
            self._mark(0xABFC)
            if r.p&N:
                self._a(0x00)
                m[0x037C]=r.a
                self._a(0x05)
                m[0x0140]=r.a
                self._a(0x00)
                m[0x0143]=r.a
                self._a(0x80)
                m[0x0144]=r.a
                self._a(0x38)
                m[0x0154]=r.a
                self._a(m[0x0150])
                self._a(r.a & 0x0F)
                self._mark(0xAC57)
                if not r.p&Z:
                    self._a(0x83)
                    m[0x0152]=r.a
                    self._a(0xB6)
                    m[0x0153]=r.a
                    self._a(0x09)
                    m[0x00B4]=r.a
                    m[0x00C4]=r.a
                    m[0x00CC]=r.a
                    m[0x00D4]=r.a
                    m[0x00DC]=r.a
                    self._y(0x80)
                    self._a(m[0x0150])
                    self._mark(0xAC7C)
                    if not r.p&N:
                        pass
                    else:
                        self._y(0x40)
                        pass
                    m[0x0420]=r.y
                    self._a(r.a & 0x0F)
                    self._compare(r.a,0x01)
                    self._mark(0xAC87)
                    if r.p&Z:
                        self._a(0x05)
                        m[0x0149]=r.a
                        self._a(0xB3)
                        m[0x014A]=r.a
                        self._a(m[0x0402])
                        yield from self._external(0xACDA,0xF2AF,0xACDD,"call",None)
                        if r.pc!=0xACDD:return  # preserve nonlocal stack return
                        self._y(0x11)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        m[0x037E]=r.a
                        self._y(0x00)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._compare(r.a,0x07)
                        self._mark(0xACEA)
                        if not r.p&Z:
                            r.a=self._shift(r.a,True,rotate=False)
                            self._y(r.a)
                            self._a(m[(0xAD84+r.y)&65535])
                            m[0x0000]=r.a
                            self._a(m[(0xAD85+r.y)&65535])
                            m[0x0001]=r.a
                            self._y(0x00)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            pass
                        else:
                            self._a(0xFF)
                            pass
                        m[0x037D]=r.a
                        self._a(0x08)
                        m[0x00B4]=r.a
                        m[0x00C4]=r.a
                        m[0x00CC]=r.a
                        m[0x00D4]=r.a
                        self._a(0x01)
                        m[0x00B3]=r.a
                        m[0x00C3]=r.a
                        m[0x00CB]=r.a
                        pass
                    else:
                        self._compare(r.a,0x02)
                        self._mark(0xAC8B)
                        if r.p&Z:
                            self._a(0xE5)
                            m[0x0149]=r.a
                            self._a(0xB3)
                            m[0x014A]=r.a
                            self._a(0x01)
                            m[0x00B3]=r.a
                            m[0x00C3]=r.a
                            m[0x00CB]=r.a
                            self._a(0x05)
                            pass
                        else:
                            self._compare(r.a,0x03)
                            self._mark(0xAC8F)
                            if r.p&Z:
                                self._a(0xC1)
                                m[0x0149]=r.a
                                self._a(0xB4)
                                m[0x014A]=r.a
                                self._a(0x05)
                                m[0x00B3]=r.a
                                m[0x00C3]=r.a
                                m[0x00CB]=r.a
                                pass
                            else:
                                self._compare(r.a,0x04)
                                self._mark(0xAC93)
                                if r.p&Z:
                                    self._a(0x9C)
                                    m[0x0149]=r.a
                                    self._a(0xB5)
                                    m[0x014A]=r.a
                                    self._a(0x05)
                                    m[0x00B3]=r.a
                                    m[0x00C3]=r.a
                                    m[0x00CB]=r.a
                                    pass
                                else:
                                    self._a(0xE5)
                                    m[0x0149]=r.a
                                    self._a(0xB3)
                                    m[0x014A]=r.a
                                    self._a(0x01)
                                    m[0x00B3]=r.a
                                    m[0x00C3]=r.a
                                    m[0x00CB]=r.a
                                    self._a(0x05)
                                    pass
                                pass
                            pass
                        pass
                    m[0x00D3]=r.a
                    m[0x00DB]=r.a
                    self._a(0x00)
                    m[0x00C2]=r.a
                    m[0x00CA]=r.a
                    m[0x00D2]=r.a
                    m[0x00DA]=r.a
                    self._a(m[0x0150])
                    self._a(0x20)
                    m[0x0142]=r.a
                    self._a(0x23)
                    m[0x0148]=r.a
                    self._a(m[0x0150])
                    self._mark(0xAD43)
                    if not r.p&N:
                        self._a(0xC0)
                        m[0x0147]=r.a
                        self._a(0x7B)
                        m[0x0145]=r.a
                        self._a(0xB6)
                        m[0x0146]=r.a
                        self._x(0x02)
                        self._y(0xC8)
                        pass
                    else:
                        self._a(0xC4)
                        m[0x0147]=r.a
                        self._a(0x7F)
                        m[0x0145]=r.a
                        self._a(0xB6)
                        m[0x0146]=r.a
                        self._x(0x10)
                        self._y(0xCC)
                        pass
                    m[0x0141]=r.x
                    self._a(r.y)
                    self._flag(C,False)
                    self._add(m[0x0143])
                    m[0x0143]=r.a
                    self._a(0x03)
                    self._add(m[0x0144])
                    m[0x0144]=r.a
                    return (yield from self.open_panel_row_group())
                else:
                    return (yield from self.initialize_city_panel())
            else:
                self._a(r.a & 0x0F)
                self._compare(r.a,0x01)
                self._mark(0xAC02)
                if r.p&Z:
                    self._a(0x00)
                    m[0x0140]=r.a
                    self._a(m[0x0150])
                    self._a(r.a & 0x0F)
                    self._mark(0xAC22)
                    if not r.p&Z:
                        pass
                    else:
                        m[0x0420]=r.a
                        pass
                    self._compare(r.a,0x01)
                    self._mark(0xAC29)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(0xFF)
                        m[0x037C]=r.a
                        pass
                    self._a(m[0x0150])
                    self._a(r.a & 0x80)
                    m[0x0150]=r.a
                    self._mark(0xAC38)
                    self._rts();return
                else:
                    self._a(m[PPU_JOBS])
                    self._a(r.a & 0x08)
                    self._mark(0xAC09)
                    if not r.p&Z:
                        self._mark(0xAC38)
                        self._rts();return
                    else:
                        self._a(m[0x0150])
                        self._a(r.a & 0x0F)
                        self._mark(0xAC10)
                        if not r.p&Z:
                            return (yield from self.open_panel_row_group())
                        else:
                            return (yield from self.close_panel_row_group())

    def initialize_city_panel(self):
        """$AD92: initialize city panel; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAD92)
        self._a(0x22)
        m[0x0142]=r.a
        self._a(0x03)
        m[0x0146]=r.a
        self._a(0x23)
        m[0x0148]=r.a
        self._a(0x00)
        m[0x037C]=r.a
        self._a(m[0x0150])
        self._mark(0xADA9)
        if not r.p&N:
            self._a(0xE0)
            m[0x0145]=r.a
            self._a(0xE8)
            m[0x0147]=r.a
            self._x(0x82)
            self._y(0x02)
            pass
        else:
            self._a(0xE4)
            m[0x0145]=r.a
            self._a(0xEC)
            m[0x0147]=r.a
            self._x(0x90)
            self._y(0x10)
            pass
        m[0x0141]=r.x
        self._a(m[0x0143])
        self._flag(C,False)
        self._add(m[0x0145])
        m[0x0145]=r.a
        self._a(m[0x0146])
        self._add(m[0x0144])
        m[0x0146]=r.a
        self._a(r.y)
        self._flag(C,False)
        self._add(m[0x0143])
        m[0x0143]=r.a
        self._a(m[0x0144])
        self._add(0x02)
        m[0x0144]=r.a
        return (yield from self.close_panel_row_group())

    def open_panel_row_group(self):
        """$ADF3: open panel row group; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xADF3)
        m[0x0140]=self._nz(m[0x0140]-1)
        self._y(0x30)
        yield from self._external(0xADF8,0xF25F,0xADFB,"call",None)
        if r.pc!=0xADFB:return  # preserve nonlocal stack return
        self._a(m[0x0149])
        m[0x0010]=r.a
        self._a(m[0x014A])
        m[0x0011]=r.a
        self._y(0x00)
        self._x(0x00)
        while True:  # natural loop $AE0B
            self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
            self._compare(r.a,0xF0)
            self._mark(0xAE0F)
            if r.p&C:
                if not (yield from self._local_call(self.cityuiworkers_af77,0xAE19,0xAE1C)):return
                pass
            else:
                m[(0x0160+r.x)&65535]=r.a
                self._y(r.y+1)
                self._x(r.x+1)
                pass
            self._compare(r.x,0x38)
            self._mark(0xAE1E)
            if not r.p&C:
                continue
            else:
                pass
            self._a(r.y)
            self._y(0x09)
            if not (yield from self._local_call(self.cityuiworkers_af66,0xAE23,0xAE26)):return
            self._a(m[0x0145])
            m[0x0010]=r.a
            self._a(m[0x0146])
            m[0x0011]=r.a
            self._a(m[0x0143])
            m[0x0012]=r.a
            self._a(m[0x0144])
            m[0x0013]=r.a
            self._y(0x00)
            self._a(m[((m[0x12]|m[0x13]<<8)+r.y)&65535])
            self._a(r.a & 0x33)
            self._a(r.a | m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
            m[(0x014B+r.y)&65535]=r.a
            self._y(r.y+1)
            while True:  # natural loop $AE4A
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                m[(0x014B+r.y)&65535]=r.a
                self._y(r.y+1)
                self._compare(r.y,0x03)
                self._mark(0xAE52)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[((m[0x12]|m[0x13]<<8)+r.y)&65535])
                self._a(r.a & 0xCC)
                self._a(r.a | m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                m[(0x014B+r.y)&65535]=r.a
                self._a(0x08)
                self._y(0x07)
                if not (yield from self._local_call(self.cityuiworkers_af66,0xAE61,0xAE64)):return
                self._a(0x08)
                self._y(0x03)
                if not (yield from self._local_call(self.cityuiworkers_af66,0xAE68,0xAE6B)):return
                self._a(0x80)
                self._y(0x01)
                if not (yield from self._local_call(self.cityuiworkers_af66,0xAE6F,0xAE72)):return
                self._a(m[0x0150])
                self._a(r.a & 0x0F)
                self._compare(r.a,0x01)
                self._mark(0xAE79)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x0140])
                    self._compare(r.a,0x04)
                    self._mark(0xAE80)
                    if not r.p&Z:
                        pass
                    else:
                        if not (yield from self._local_call(self.cityuiworkers_b0ab,0xAE82,0xAE85)):return
                        pass
                    self._a(m[0x0402])
                    yield from self._external(0xAE88,0xF2AF,0xAE8B,"call",None)
                    if r.pc!=0xAE8B:return  # preserve nonlocal stack return
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._compare(r.a,0x07)
                    self._mark(0xAE91)
                    if r.p&Z:
                        pass
                    else:
                        self._a(m[0x0140])
                        self._compare(r.a,0x04)
                        self._mark(0xAE98)
                        if r.p&Z:
                            self._a(0x00)
                            if not (yield from self._local_call(self.cityuiworkers_b23a,0xAEA7,0xAEAA)):return
                            pass
                        else:
                            self._compare(r.a,0x03)
                            self._mark(0xAE9C)
                            if r.p&Z:
                                self._a(0x01)
                                if not (yield from self._local_call(self.cityuiworkers_b23a,0xAEAF,0xAEB2)):return
                                if not (yield from self._local_call(self.cityuiworkers_b27a,0xAEB2,0xAEB5)):return
                                pass
                            else:
                                self._compare(r.a,0x02)
                                self._mark(0xAEA0)
                                if r.p&Z:
                                    self._a(0x02)
                                    m[0x000F]=r.a
                                    if not (yield from self._local_call(self.cityuiworkers_b27a,0xAEBD,0xAEC0)):return
                                    pass
                                else:
                                    pass
                                pass
                            pass
                        pass
                    pass
                self._a(m[PPU_JOBS])
                self._a(r.a | 0x08)
                m[PPU_JOBS]=r.a
                self._mark(0xAEC8)
                self._rts();return

    def close_panel_row_group(self):
        """AEC9: produce four14-tile rows and one4-byte attribute group.

        The original source strides32 bytes per row. Queue bit08 is a request;
        this producer does not upload PPU bytes or acknowledge consumption.
        """
        r=self.registers;m=self.memory;self._mark(0xAEC9)
        m[0x140]=self._nz(m[0x140]-1)
        self._y(48)
        yield from self._external(0xAECE,0xF25F,0xAED1,'call')
        if r.pc!=0xAED1:return
        self._a(m[0x143]);m[0x10]=r.a;self._a(m[0x144]);m[0x11]=r.a;self._x(0)
        while True:
            self._y(0)
            while True:
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535]);m[0x160+r.x]=r.a
                self._y(r.y+1);self._x(r.x+1);self._compare(r.y,14)
                if r.p&C:break
            self._a(m[0x10]);self._flag(C,False);self._add(32);m[0x10]=r.a
            self._a(m[0x11]);self._add(0);m[0x11]=r.a;self._compare(r.x,56)
            if r.p&C:break
        self._a(m[0x143]);self._flag(C,True);self._add(128,subtract=True);m[0x143]=r.a
        self._a(m[0x144]);self._add(0,subtract=True);m[0x144]=r.a
        self._a(m[0x145]);m[0x10]=r.a;self._a(m[0x146]);m[0x11]=r.a;self._y(0)
        while True:
            self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535]);m[0x14B+r.y]=r.a
            self._y(r.y+1);self._compare(r.y,4)
            if r.p&C:break
        # Source/attribute/destination pointers move upwards for the next job.
        for lo,amount in ((0x145,8),(0x147,8),(0x141,128)):
            self._a(m[lo]);self._flag(C,True);self._add(amount,subtract=True);m[lo]=r.a
            self._a(m[lo+1]);self._add(0,subtract=True);m[lo+1]=r.a
        self._a(m[0x7E]);self._a(r.a|8);m[0x7E]=r.a;self._rts()

    def cityuiworkers_af66(self):
        """$AF66: cityuiworkers af66; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAF66)
        self._flag(C,False)
        self._add(m[(0x0140+r.y)&65535])
        m[(0x0140+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(0x00)
        self._add(m[(0x0140+r.y)&65535])
        m[(0x0140+r.y)&65535]=r.a
        self._mark(0xAF76)
        self._rts();return

    def cityuiworkers_af77(self):
        """$AF77: cityuiworkers af77; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAF77)
        m[0x0012]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
        m[0x0013]=r.a
        self._y(r.y+1)
        self._a(r.y)
        self._push(r.a)
        self._a(m[0x0402])
        yield from self._external(0xAF86,0xF2AF,0xAF89,"call",None)
        if r.pc!=0xAF89:return  # preserve nonlocal stack return
        self._a(self._pop())
        self._y(r.a)
        self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
        self._y(r.y+1)
        self._flag(C,False)
        self._add(m[0x0000])
        m[0x0017]=r.a
        self._a(m[0x0001])
        self._add(0x00)
        m[0x0018]=r.a
        self._a(r.y)
        self._push(r.a)
        self._a(m[0x0012])
        self._compare(r.a,0xF0)
        self._mark(0xAFA4)
        if r.p&Z:
            self._y(0x00)
            m[0x0003]=r.y
            m[0x0002]=r.y
            m[0x0001]=r.y
            while True:  # natural loop $AFDE
                self._a(m[((m[0x17]|m[0x18]<<8)+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xAFE2)
                if r.p&Z:
                    pass
                else:
                    m[0x0001]=self._nz(m[0x0001]+1)
                    pass
                self._y(r.y+1)
                self._compare(r.y,0x0A)
                self._mark(0xAFEA)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(r.x)
                self._push(r.a)
                yield from self._external(0xB034,0xE9BA,0xB037,"call",None)
                if r.pc!=0xB037:return  # preserve nonlocal stack return
                self._a(self._pop())
                self._x(r.a)
                self._a(self._pop())
                self._y(r.a)
                self._a(0xB6)
                m[0x0017]=r.a
                return (yield from self.cityuiworkers_b040())
        else:
            self._compare(r.a,0xF1)
            self._mark(0xAFA8)
            if r.p&Z:
                self._y(0x00)
                m[0x0003]=r.y
                self._a(m[((m[0x17]|m[0x18]<<8)+r.y)&65535])
                m[0x0001]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x17]|m[0x18]<<8)+r.y)&65535])
                m[0x0002]=r.a
                pass
            else:
                self._compare(r.a,0xF3)
                self._mark(0xAFAC)
                if r.p&Z:
                    self._y(0x00)
                    m[0x0002]=r.y
                    m[0x0003]=r.y
                    m[0x0004]=r.y
                    while True:  # natural loop $AFFA
                        self._a(m[((m[0x17]|m[0x18]<<8)+r.y)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xAFFE)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xB000,0xF2D7,0xB003,"call",None)
                            if r.pc!=0xB003:return  # preserve nonlocal stack return
                            self._y(0x08)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._flag(C,False)
                            self._add(m[0x0002])
                            m[0x0002]=r.a
                            self._y(r.y+1)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._add(m[0x0003])
                            m[0x0003]=r.a
                            m[0x0004]=self._nz(m[0x0004]+1)
                            self._y(m[0x0004])
                            self._compare(r.y,0x0A)
                            self._mark(0xB01F)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            pass
                        self._a(m[0x0002])
                        m[0x0001]=r.a
                        self._a(m[0x0003])
                        m[0x0002]=r.a
                        self._a(0x00)
                        m[0x0003]=r.a
                        self._a(r.x)
                        self._push(r.a)
                        yield from self._external(0xB034,0xE9BA,0xB037,"call",None)
                        if r.pc!=0xB037:return  # preserve nonlocal stack return
                        self._a(self._pop())
                        self._x(r.a)
                        self._a(self._pop())
                        self._y(r.a)
                        self._a(0xB6)
                        m[0x0017]=r.a
                        return (yield from self.cityuiworkers_b040())
                else:
                    self._y(0x00)
                    self._a(m[((m[0x17]|m[0x18]<<8)+r.y)&65535])
                    m[0x0001]=r.a
                    self._a(0x00)
                    m[0x0002]=r.a
                    m[0x0003]=r.a
                    pass
                pass
            pass
        self._a(r.x)
        self._push(r.a)
        yield from self._external(0xB034,0xE9BA,0xB037,"call",None)
        if r.pc!=0xB037:return  # preserve nonlocal stack return
        self._a(self._pop())
        self._x(r.a)
        self._a(self._pop())
        self._y(r.a)
        self._a(0xB6)
        m[0x0017]=r.a
        return (yield from self.cityuiworkers_b040())

    def cityuiworkers_b040(self):
        """$B040: cityuiworkers b040; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB040)
        self._a(0x01)
        m[0x0016]=r.a
        self._a(m[0x0013])
        self._compare(r.a,0x02)
        self._mark(0xB04A)
        if r.p&Z:
            pass
        else:
            self._compare(r.a,0x03)
            self._mark(0xB04E)
            if r.p&Z:
                pass
            else:
                self._compare(r.a,0x04)
                self._mark(0xB052)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x05)
                    self._mark(0xB056)
                    if r.p&Z:
                        pass
                    else:
                        self._a(m[0x0009])
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        if not (yield from self._local_call(self.cityuiworkers_b091,0xB05F,0xB062)):return
                        pass
                    self._a(m[0x0009])
                    self._a(r.a & 0x0F)
                    if not (yield from self._local_call(self.cityuiworkers_b091,0xB067,0xB06A)):return
                    pass
                self._a(m[0x0008])
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                if not (yield from self._local_call(self.cityuiworkers_b091,0xB071,0xB074)):return
                pass
            self._a(m[0x0008])
            self._a(r.a & 0x0F)
            if not (yield from self._local_call(self.cityuiworkers_b091,0xB079,0xB07C)):return
            pass
        self._a(m[0x0007])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        if not (yield from self._local_call(self.cityuiworkers_b091,0xB083,0xB086)):return
        self._a(m[0x0017])
        m[0x0016]=r.a
        self._a(m[0x0007])
        self._a(r.a & 0x0F)
        return (yield from self.cityuiworkers_b091())

    def cityuiworkers_b091(self):
        """$B091: cityuiworkers b091; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB091)
        if not r.p&Z:
            self._flag(C,False)
            self._add(m[0x0017])
            m[(0x0160+r.x)&65535]=r.a
            self._a(m[0x0017])
            m[0x0016]=r.a
            pass
        else:
            self._a(m[0x0016])
            m[(0x0160+r.x)&65535]=r.a
            pass
        self._x(r.x+1)
        self._mark(0xB0AA)
        self._rts();return

    def cityuiworkers_b0ab(self):
        """$B0AB: cityuiworkers b0ab; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB0AB)
        self._a(0x00)
        m[0x0000]=r.a
        m[0x0001]=r.a
        self._a(m[0x0402])
        r.a=self._shift(r.a,True,rotate=False)
        self._flag(C,False)
        self._add(m[0x0402])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        self._flag(C,False)
        self._add(m[0x0402])
        m[0x0000]=r.a
        self._a(m[0x0001])
        self._add(0x00)
        m[0x0001]=r.a
        self._a(m[0x0000])
        self._flag(C,False)
        self._add(m[0x0152])
        m[0x0000]=r.a
        self._a(m[0x0001])
        self._add(m[0x0153])
        m[0x0001]=r.a
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x00B2]=r.a
        m[0x00C2]=r.a
        m[0x00CA]=r.a
        m[0x00D2]=r.a
        m[0x00DA]=r.a
        self._y(r.y+1)
        self._x(0x00)
        while True:  # natural loop $B0F8
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[(0x016F+r.x)&65535]=r.a
            self._y(r.y+1)
            self._x(r.x+1)
            self._compare(r.y,0x07)
            self._mark(0xB101)
            if not r.p&C:
                continue
            else:
                pass
            self._x(0x00)
            while True:  # natural loop $B105
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[(0x017D+r.x)&65535]=r.a
                self._y(r.y+1)
                self._x(r.x+1)
                self._compare(r.y,0x0D)
                self._mark(0xB10E)
                if not r.p&C:
                    continue
                else:
                    pass
                self._y(0x30)
                yield from self._external(0xB112,0xF25F,0xB115,"call",None)
                if r.pc!=0xB115:return  # preserve nonlocal stack return
                self._a(m[0x0402])
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._flag(C,False)
                self._add(0x1A)
                m[0x0000]=r.a
                self._a(0x9A)
                self._add(0x00)
                m[0x0001]=r.a
                self._y(0x00)
                self._x(0x00)
                while True:  # natural loop $B12C
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._mark(0xB12E)
                    if r.p&Z:
                        pass
                    else:
                        self._flag(C,False)
                        self._add(0x80)
                        self._compare(r.a,0xB9)
                        self._mark(0xB135)
                        if r.p&Z:
                            self._x(r.x-1)
                            m[(0x0175+r.x)&65535]=r.a
                            pass
                        else:
                            self._compare(r.a,0xBA)
                            self._mark(0xB139)
                            if r.p&Z:
                                self._x(r.x-1)
                                m[(0x0175+r.x)&65535]=r.a
                                pass
                            else:
                                m[(0x0183+r.x)&65535]=r.a
                                pass
                            pass
                        self._y(r.y+1)
                        self._x(r.x+1)
                        self._compare(r.y,0x08)
                        self._mark(0xB149)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        pass
                    self._mark(0xB14B)
                    self._rts();return

    def cityuiworkers_b14c(self):
        """$B14C: cityuiworkers b14c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB14C)
        m[0x0006]=r.a
        self._x(0x00)
        self._a(m[0x0150])
        self._mark(0xB154)
        if not r.p&N:
            pass
        else:
            self._x(0x70)
            pass
        m[0x0005]=r.x
        self._y(m[0x0006])
        self._x(m[0x0006])
        self._a(0x40)
        m[0x0007]=r.a
        self._a(0x00)
        self._compare(r.y,0x01)
        self._mark(0xB16A)
        if r.p&Z:
            pass
        else:
            self._a(0x80)
            m[0x0007]=r.a
            self._a(0x20)
            pass
        m[0x0006]=r.a
        self._a(m[(0x037C+r.y)&65535])
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        self._a(m[0x0000])
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        self._flag(C,False)
        self._add(m[(0x037C+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[0x0001])
        self._add(0x00)
        m[0x0001]=r.a
        self._a(m[0x0000])
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        self._flag(C,False)
        self._add(m[(0x037C+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[0x0001])
        self._add(0x00)
        m[0x0001]=r.a
        self._a(0xB4)
        self._flag(C,False)
        self._add(m[0x0000])
        m[0x0000]=r.a
        self._a(0x8D)
        self._add(m[0x0001])
        m[0x0001]=r.a
        self._a(0x22)
        m[0x0002]=r.a
        self._a(0xB2)
        m[0x0003]=r.a
        self._y(0x00)
        m[0x0004]=r.y
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[(0x00AE+r.x)&65535]=r.a
        m[(0x00BE+r.x)&65535]=r.a
        m[(0x00C6+r.x)&65535]=r.a
        m[(0x00CE+r.x)&65535]=r.a
        m[(0x00D6+r.x)&65535]=r.a
        self._x(m[0x007C])
        while True:  # natural loop $B1E5
            self._y(r.y+1)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xB1EA)
            if r.p&Z:
                pass
            else:
                self._flag(C,False)
                self._add(m[0x0007])
                m[(0x0201+r.x)&65535]=r.a
                self._a(0x01)
                m[(0x0202+r.x)&65535]=r.a
                self._a(r.y)
                self._push(r.a)
                self._y(m[0x0004])
                self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x0005])
                m[(0x0203+r.x)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x0006])
                m[(0x0200+r.x)&65535]=r.a
                self._y(r.y+1)
                m[0x0004]=r.y
                self._x(r.x+1)
                self._x(r.x+1)
                self._x(r.x+1)
                self._x(r.x+1)
                self._a(self._pop())
                self._y(r.a)
                self._compare(r.y,0x0C)
                self._mark(0xB21C)
                if not r.p&C:
                    continue
                else:
                    pass
                pass
            m[0x007C]=r.x
            self._mark(0xB221)
            self._rts();return

    def cityuiworkers_b23a(self):
        """$B23A: cityuiworkers b23a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB23A)
        m[0x000F]=r.a
        self._a(m[0x0402])
        yield from self._external(0xB240,0xF2AF,0xB243,"call",None)
        if r.pc!=0xB243:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._compare(r.a,0x07)
        self._mark(0xB249)
        if r.p&Z:
            pass
        else:
            self._y(0x01)
            self._a(m[0x000F])
            self._mark(0xB250)
            if r.p&Z:
                pass
            else:
                self._y(0x02)
                pass
            self._a(m[(0x037C+r.y)&65535])
            yield from self._external(0xB257,0xF308,0xB25A,"call",None)
            if r.pc!=0xB25A:return  # preserve nonlocal stack return
            self._y(0x00)
            self._x(0x00)
            while True:  # natural loop $B25E
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._mark(0xB260)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x39)
                    self._mark(0xB264)
                    if r.p&Z:
                        self._x(r.x-1)
                        self._flag(C,False)
                        self._add(0x80)
                        m[(0x0190+r.x)&65535]=r.a
                        pass
                    else:
                        self._compare(r.a,0x3A)
                        self._mark(0xB268)
                        if r.p&Z:
                            self._x(r.x-1)
                            self._flag(C,False)
                            self._add(0x80)
                            m[(0x0190+r.x)&65535]=r.a
                            pass
                        else:
                            pass
                        pass
                    self._x(r.x+1)
                    self._y(r.y+1)
                    continue
                self._mark(0xB279)
                self._rts();return
        self._mark(0xB279)
        self._rts();return

    def cityuiworkers_b27a(self):
        """$B27A: cityuiworkers b27a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB27A)
        self._y(m[0x000F])
        self._a(m[(0x037C+r.y)&65535])
        yield from self._external(0xB280,0xF308,0xB283,"call",None)
        if r.pc!=0xB283:return  # preserve nonlocal stack return
        self._y(0x00)
        self._x(0x00)
        while True:  # natural loop $B287
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._mark(0xB289)
            if r.p&Z:
                pass
            else:
                self._compare(r.a,0x39)
                self._mark(0xB28D)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x3A)
                    self._mark(0xB291)
                    if r.p&Z:
                        pass
                    else:
                        self._flag(C,False)
                        self._add(0x80)
                        m[(0x0166+r.x)&65535]=r.a
                        self._x(r.x+1)
                        pass
                    pass
                self._y(r.y+1)
                continue
            self._mark(0xB29E)
            self._rts();return

    def update_list_job(self):
        """$B989: update list job; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB989)
        self._a(m[0x0140])
        self._mark(0xB98C)
        if not r.p&Z:
            self._mark(0xB9CE)
            self._rts();return
        else:
            self._a(m[PPU_JOBS])
            self._a(r.a & 0x02)
            self._mark(0xB993)
            if not r.p&Z:
                self._mark(0xB9CE)
                self._rts();return
            else:
                self._a(m[0x0478])
                self._mark(0xB998)
                if r.p&Z:
                    self._mark(0xB9CE)
                    self._rts();return
                else:
                    self._mark(0xB99A)
                    if not r.p&N:
                        self._compare(r.a,0x10)
                        self._mark(0xB9A1)
                        if r.p&Z:
                            self._a(0x00)
                            m[0x0478]=r.a
                            m[0x047A]=r.a
                            m[0x0480]=r.a
                            m[0x0424]=r.a
                            m[0x0425]=r.a
                            self._a(m[0x047C])
                            self._compare(r.a,0x0F)
                            self._mark(0xB9E5)
                            if not r.p&Z:
                                pass
                            else:
                                m[0x047B]=self._nz(m[0x047B]-1)
                                pass
                            self._a(0x06)
                            m[0x0061]=r.a
                            self._a(0x08)
                            m[0x00B2]=r.a
                            self._a(0x09)
                            m[0x00B3]=r.a
                            self._a(0x06)
                            m[0x00B4]=r.a
                            self._y(0x01)
                            m[0x008F]=r.y
                            self._a(0xFF)
                            while True:  # natural loop $BA05
                                m[(0x0480+r.y)&65535]=r.a
                                self._y(r.y+1)
                                self._compare(r.y,0x0B)
                                self._mark(0xBA0B)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._mark(0xBA0D)
                                self._rts();return
                        else:
                            self._compare(r.a,0x02)
                            self._mark(0xB9A5)
                            if not r.p&C:
                                self._a(m[0x0478])
                                self._compare(r.a,0x0F)
                                self._mark(0xBAA2)
                                if r.p&Z:
                                    self._y(0x00)
                                    self._a(0xAA)
                                    while True:  # natural loop $BB07
                                        m[(0x0160+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._compare(r.y,0x40)
                                        self._mark(0xBB0D)
                                        if not r.p&C:
                                            continue
                                        else:
                                            pass
                                        self._a(0xC0)
                                        m[0x0480]=r.a
                                        self._a(0x27)
                                        m[0x0481]=r.a
                                        m[0x0478]=self._nz(m[0x0478]+1)
                                        self._a(m[PPU_JOBS])
                                        self._a(r.a | 0x02)
                                        m[PPU_JOBS]=r.a
                                        self._mark(0xBB27)
                                        self._rts();return
                                else:
                                    self._compare(r.a,0x02)
                                    self._mark(0xBAA6)
                                    if not r.p&C:
                                        self._a(m[0x0482])
                                        m[0x001A]=r.a
                                        self._a(m[0x0483])
                                        m[0x001B]=r.a
                                        self._y(0x00)
                                        while True:  # natural loop $BAC5
                                            self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                            m[(0x0160+r.y)&65535]=r.a
                                            self._y(r.y+1)
                                            self._compare(r.y,0x40)
                                            self._mark(0xBACD)
                                            if not r.p&C:
                                                continue
                                            else:
                                                pass
                                            self._a(m[0x0482])
                                            self._flag(C,False)
                                            self._add(0x40)
                                            m[0x0482]=r.a
                                            self._a(m[0x0483])
                                            self._add(0x00)
                                            m[0x0483]=r.a
                                            self._a(m[0x0480])
                                            self._flag(C,False)
                                            self._add(0x40)
                                            m[0x0480]=r.a
                                            self._a(m[0x0481])
                                            self._add(0x00)
                                            m[0x0481]=r.a
                                            m[0x0478]=self._nz(m[0x0478]+1)
                                            self._a(m[PPU_JOBS])
                                            self._a(r.a | 0x02)
                                            m[PPU_JOBS]=r.a
                                            self._mark(0xBB27)
                                            self._rts();return
                                    else:
                                        self._a(m[0x0486])
                                        self._mark(0xBAAB)
                                        if not r.p&Z:
                                            self._a(0x01)
                                            self._y(0x00)
                                            while True:  # natural loop $BAE7
                                                m[(0x0160+r.y)&65535]=r.a
                                                self._y(r.y+1)
                                                self._compare(r.y,0x40)
                                                self._mark(0xBAED)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    pass
                                                self._a(m[0x0480])
                                                self._flag(C,False)
                                                self._add(0x40)
                                                m[0x0480]=r.a
                                                self._a(m[0x0481])
                                                self._add(0x00)
                                                m[0x0481]=r.a
                                                m[0x0478]=self._nz(m[0x0478]+1)
                                                self._a(m[PPU_JOBS])
                                                self._a(r.a | 0x02)
                                                m[PPU_JOBS]=r.a
                                                self._mark(0xBB27)
                                                self._rts();return
                                        else:
                                            m[0x0486]=self._nz(m[0x0486]+1)
                                            self._a(m[0x047C])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xBAB5)
                                            if r.p&Z:
                                                self._a(0x01)
                                                self._y(0x00)
                                                while True:  # natural loop $BAE7
                                                    m[(0x0160+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._compare(r.y,0x40)
                                                    self._mark(0xBAED)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        pass
                                                    self._a(m[0x0480])
                                                    self._flag(C,False)
                                                    self._add(0x40)
                                                    m[0x0480]=r.a
                                                    self._a(m[0x0481])
                                                    self._add(0x00)
                                                    m[0x0481]=r.a
                                                    m[0x0478]=self._nz(m[0x0478]+1)
                                                    self._a(m[PPU_JOBS])
                                                    self._a(r.a | 0x02)
                                                    m[PPU_JOBS]=r.a
                                                    self._mark(0xBB27)
                                                    self._rts();return
                                            else:
                                                self._a(m[0x0482])
                                                m[0x001A]=r.a
                                                self._a(m[0x0483])
                                                m[0x001B]=r.a
                                                self._y(0x00)
                                                while True:  # natural loop $BAC5
                                                    self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                                    m[(0x0160+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._compare(r.y,0x40)
                                                    self._mark(0xBACD)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        pass
                                                    self._a(m[0x0482])
                                                    self._flag(C,False)
                                                    self._add(0x40)
                                                    m[0x0482]=r.a
                                                    self._a(m[0x0483])
                                                    self._add(0x00)
                                                    m[0x0483]=r.a
                                                    self._a(m[0x0480])
                                                    self._flag(C,False)
                                                    self._add(0x40)
                                                    m[0x0480]=r.a
                                                    self._a(m[0x0481])
                                                    self._add(0x00)
                                                    m[0x0481]=r.a
                                                    m[0x0478]=self._nz(m[0x0478]+1)
                                                    self._a(m[PPU_JOBS])
                                                    self._a(r.a | 0x02)
                                                    m[PPU_JOBS]=r.a
                                                    self._mark(0xBB27)
                                                    self._rts();return
                            else:
                                self._compare(r.a,0x0C)
                                self._mark(0xB9A9)
                                if r.p&C:
                                    self._a(m[0x0478])
                                    self._compare(r.a,0x0F)
                                    self._mark(0xBAA2)
                                    if r.p&Z:
                                        self._y(0x00)
                                        self._a(0xAA)
                                        while True:  # natural loop $BB07
                                            m[(0x0160+r.y)&65535]=r.a
                                            self._y(r.y+1)
                                            self._compare(r.y,0x40)
                                            self._mark(0xBB0D)
                                            if not r.p&C:
                                                continue
                                            else:
                                                pass
                                            self._a(0xC0)
                                            m[0x0480]=r.a
                                            self._a(0x27)
                                            m[0x0481]=r.a
                                            m[0x0478]=self._nz(m[0x0478]+1)
                                            self._a(m[PPU_JOBS])
                                            self._a(r.a | 0x02)
                                            m[PPU_JOBS]=r.a
                                            self._mark(0xBB27)
                                            self._rts();return
                                    else:
                                        self._compare(r.a,0x02)
                                        self._mark(0xBAA6)
                                        if not r.p&C:
                                            self._a(m[0x0482])
                                            m[0x001A]=r.a
                                            self._a(m[0x0483])
                                            m[0x001B]=r.a
                                            self._y(0x00)
                                            while True:  # natural loop $BAC5
                                                self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                                m[(0x0160+r.y)&65535]=r.a
                                                self._y(r.y+1)
                                                self._compare(r.y,0x40)
                                                self._mark(0xBACD)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    pass
                                                self._a(m[0x0482])
                                                self._flag(C,False)
                                                self._add(0x40)
                                                m[0x0482]=r.a
                                                self._a(m[0x0483])
                                                self._add(0x00)
                                                m[0x0483]=r.a
                                                self._a(m[0x0480])
                                                self._flag(C,False)
                                                self._add(0x40)
                                                m[0x0480]=r.a
                                                self._a(m[0x0481])
                                                self._add(0x00)
                                                m[0x0481]=r.a
                                                m[0x0478]=self._nz(m[0x0478]+1)
                                                self._a(m[PPU_JOBS])
                                                self._a(r.a | 0x02)
                                                m[PPU_JOBS]=r.a
                                                self._mark(0xBB27)
                                                self._rts();return
                                        else:
                                            self._a(m[0x0486])
                                            self._mark(0xBAAB)
                                            if not r.p&Z:
                                                self._a(0x01)
                                                self._y(0x00)
                                                while True:  # natural loop $BAE7
                                                    m[(0x0160+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._compare(r.y,0x40)
                                                    self._mark(0xBAED)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        pass
                                                    self._a(m[0x0480])
                                                    self._flag(C,False)
                                                    self._add(0x40)
                                                    m[0x0480]=r.a
                                                    self._a(m[0x0481])
                                                    self._add(0x00)
                                                    m[0x0481]=r.a
                                                    m[0x0478]=self._nz(m[0x0478]+1)
                                                    self._a(m[PPU_JOBS])
                                                    self._a(r.a | 0x02)
                                                    m[PPU_JOBS]=r.a
                                                    self._mark(0xBB27)
                                                    self._rts();return
                                            else:
                                                m[0x0486]=self._nz(m[0x0486]+1)
                                                self._a(m[0x047C])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xBAB5)
                                                if r.p&Z:
                                                    self._a(0x01)
                                                    self._y(0x00)
                                                    while True:  # natural loop $BAE7
                                                        m[(0x0160+r.y)&65535]=r.a
                                                        self._y(r.y+1)
                                                        self._compare(r.y,0x40)
                                                        self._mark(0xBAED)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            pass
                                                        self._a(m[0x0480])
                                                        self._flag(C,False)
                                                        self._add(0x40)
                                                        m[0x0480]=r.a
                                                        self._a(m[0x0481])
                                                        self._add(0x00)
                                                        m[0x0481]=r.a
                                                        m[0x0478]=self._nz(m[0x0478]+1)
                                                        self._a(m[PPU_JOBS])
                                                        self._a(r.a | 0x02)
                                                        m[PPU_JOBS]=r.a
                                                        self._mark(0xBB27)
                                                        self._rts();return
                                                else:
                                                    self._a(m[0x0482])
                                                    m[0x001A]=r.a
                                                    self._a(m[0x0483])
                                                    m[0x001B]=r.a
                                                    self._y(0x00)
                                                    while True:  # natural loop $BAC5
                                                        self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                                        m[(0x0160+r.y)&65535]=r.a
                                                        self._y(r.y+1)
                                                        self._compare(r.y,0x40)
                                                        self._mark(0xBACD)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            pass
                                                        self._a(m[0x0482])
                                                        self._flag(C,False)
                                                        self._add(0x40)
                                                        m[0x0482]=r.a
                                                        self._a(m[0x0483])
                                                        self._add(0x00)
                                                        m[0x0483]=r.a
                                                        self._a(m[0x0480])
                                                        self._flag(C,False)
                                                        self._add(0x40)
                                                        m[0x0480]=r.a
                                                        self._a(m[0x0481])
                                                        self._add(0x00)
                                                        m[0x0481]=r.a
                                                        m[0x0478]=self._nz(m[0x0478]+1)
                                                        self._a(m[PPU_JOBS])
                                                        self._a(r.a | 0x02)
                                                        m[PPU_JOBS]=r.a
                                                        self._mark(0xBB27)
                                                        self._rts();return
                                else:
                                    self._y(m[0x047A])
                                    m[0x047A]=self._nz(m[0x047A]+1)
                                    self._a(m[(0x0151+r.y)&65535])
                                    self._compare(r.a,0xFF)
                                    self._mark(0xB9B6)
                                    if r.p&Z:
                                        self._a(m[0x0478])
                                        self._compare(r.a,0x0F)
                                        self._mark(0xBAA2)
                                        if r.p&Z:
                                            self._y(0x00)
                                            self._a(0xAA)
                                            while True:  # natural loop $BB07
                                                m[(0x0160+r.y)&65535]=r.a
                                                self._y(r.y+1)
                                                self._compare(r.y,0x40)
                                                self._mark(0xBB0D)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    pass
                                                self._a(0xC0)
                                                m[0x0480]=r.a
                                                self._a(0x27)
                                                m[0x0481]=r.a
                                                m[0x0478]=self._nz(m[0x0478]+1)
                                                self._a(m[PPU_JOBS])
                                                self._a(r.a | 0x02)
                                                m[PPU_JOBS]=r.a
                                                self._mark(0xBB27)
                                                self._rts();return
                                        else:
                                            self._compare(r.a,0x02)
                                            self._mark(0xBAA6)
                                            if not r.p&C:
                                                self._a(m[0x0482])
                                                m[0x001A]=r.a
                                                self._a(m[0x0483])
                                                m[0x001B]=r.a
                                                self._y(0x00)
                                                while True:  # natural loop $BAC5
                                                    self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                                    m[(0x0160+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._compare(r.y,0x40)
                                                    self._mark(0xBACD)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        pass
                                                    self._a(m[0x0482])
                                                    self._flag(C,False)
                                                    self._add(0x40)
                                                    m[0x0482]=r.a
                                                    self._a(m[0x0483])
                                                    self._add(0x00)
                                                    m[0x0483]=r.a
                                                    self._a(m[0x0480])
                                                    self._flag(C,False)
                                                    self._add(0x40)
                                                    m[0x0480]=r.a
                                                    self._a(m[0x0481])
                                                    self._add(0x00)
                                                    m[0x0481]=r.a
                                                    m[0x0478]=self._nz(m[0x0478]+1)
                                                    self._a(m[PPU_JOBS])
                                                    self._a(r.a | 0x02)
                                                    m[PPU_JOBS]=r.a
                                                    self._mark(0xBB27)
                                                    self._rts();return
                                            else:
                                                self._a(m[0x0486])
                                                self._mark(0xBAAB)
                                                if not r.p&Z:
                                                    self._a(0x01)
                                                    self._y(0x00)
                                                    while True:  # natural loop $BAE7
                                                        m[(0x0160+r.y)&65535]=r.a
                                                        self._y(r.y+1)
                                                        self._compare(r.y,0x40)
                                                        self._mark(0xBAED)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            pass
                                                        self._a(m[0x0480])
                                                        self._flag(C,False)
                                                        self._add(0x40)
                                                        m[0x0480]=r.a
                                                        self._a(m[0x0481])
                                                        self._add(0x00)
                                                        m[0x0481]=r.a
                                                        m[0x0478]=self._nz(m[0x0478]+1)
                                                        self._a(m[PPU_JOBS])
                                                        self._a(r.a | 0x02)
                                                        m[PPU_JOBS]=r.a
                                                        self._mark(0xBB27)
                                                        self._rts();return
                                                else:
                                                    m[0x0486]=self._nz(m[0x0486]+1)
                                                    self._a(m[0x047C])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xBAB5)
                                                    if r.p&Z:
                                                        self._a(0x01)
                                                        self._y(0x00)
                                                        while True:  # natural loop $BAE7
                                                            m[(0x0160+r.y)&65535]=r.a
                                                            self._y(r.y+1)
                                                            self._compare(r.y,0x40)
                                                            self._mark(0xBAED)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                pass
                                                            self._a(m[0x0480])
                                                            self._flag(C,False)
                                                            self._add(0x40)
                                                            m[0x0480]=r.a
                                                            self._a(m[0x0481])
                                                            self._add(0x00)
                                                            m[0x0481]=r.a
                                                            m[0x0478]=self._nz(m[0x0478]+1)
                                                            self._a(m[PPU_JOBS])
                                                            self._a(r.a | 0x02)
                                                            m[PPU_JOBS]=r.a
                                                            self._mark(0xBB27)
                                                            self._rts();return
                                                    else:
                                                        self._a(m[0x0482])
                                                        m[0x001A]=r.a
                                                        self._a(m[0x0483])
                                                        m[0x001B]=r.a
                                                        self._y(0x00)
                                                        while True:  # natural loop $BAC5
                                                            self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                                            m[(0x0160+r.y)&65535]=r.a
                                                            self._y(r.y+1)
                                                            self._compare(r.y,0x40)
                                                            self._mark(0xBACD)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                pass
                                                            self._a(m[0x0482])
                                                            self._flag(C,False)
                                                            self._add(0x40)
                                                            m[0x0482]=r.a
                                                            self._a(m[0x0483])
                                                            self._add(0x00)
                                                            m[0x0483]=r.a
                                                            self._a(m[0x0480])
                                                            self._flag(C,False)
                                                            self._add(0x40)
                                                            m[0x0480]=r.a
                                                            self._a(m[0x0481])
                                                            self._add(0x00)
                                                            m[0x0481]=r.a
                                                            m[0x0478]=self._nz(m[0x0478]+1)
                                                            self._a(m[PPU_JOBS])
                                                            self._a(r.a | 0x02)
                                                            m[PPU_JOBS]=r.a
                                                            self._mark(0xBB27)
                                                            self._rts();return
                                    else:
                                        self._x(r.a)
                                        yield from self._external(0xB9B9,0xF2D7,0xB9BC,"call",None)
                                        if r.pc!=0xB9BC:return  # preserve nonlocal stack return
                                        self._a(m[0x0000])
                                        m[0x001C]=r.a
                                        self._a(m[0x0001])
                                        m[0x001D]=r.a
                                        self._a(0x01)
                                        self._y(0x00)
                                        while True:  # natural loop $BB2C
                                            m[(0x0160+r.y)&65535]=r.a
                                            self._y(r.y+1)
                                            self._compare(r.y,0x40)
                                            self._mark(0xBB32)
                                            if not r.p&C:
                                                continue
                                            else:
                                                pass
                                            self._a(r.x)
                                            yield from self._external(0xBB35,0xF308,0xBB38,"call",None)
                                            if r.pc!=0xBB38:return  # preserve nonlocal stack return
                                            self._y(0x00)
                                            self._x(0x00)
                                            while True:  # natural loop $BB3C
                                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                                self._mark(0xBB3E)
                                                if r.p&Z:
                                                    pass
                                                else:
                                                    self._compare(r.a,0x39)
                                                    self._mark(0xBB42)
                                                    if r.p&Z:
                                                        self._x(r.x-1)
                                                        m[(0x0163+r.x)&65535]=r.a
                                                        pass
                                                    else:
                                                        self._compare(r.a,0x3A)
                                                        self._mark(0xBB46)
                                                        if r.p&Z:
                                                            self._x(r.x-1)
                                                            m[(0x0163+r.x)&65535]=r.a
                                                            pass
                                                        else:
                                                            m[(0x0183+r.x)&65535]=r.a
                                                            pass
                                                        pass
                                                    self._x(r.x+1)
                                                    self._y(r.y+1)
                                                    continue
                                                self._a(0x76)
                                                m[0x0017]=r.a
                                                self._a(0x02)
                                                m[0x0013]=r.a
                                                self._a(0x2B)
                                                m[0x0014]=r.a
                                                self._y(0x00)
                                                while True:  # natural loop $BB68
                                                    self._a(0x00)
                                                    m[0x0002]=r.a
                                                    m[0x0003]=r.a
                                                    self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                                    m[0x0001]=r.a
                                                    self._compare(r.a,0x64)
                                                    self._mark(0xBB77)
                                                    if not r.p&Z:
                                                        yield from self._external(0xBB80,0xE9BA,0xBB83,"call",None)
                                                        if r.pc!=0xBB83:return  # preserve nonlocal stack return
                                                        self._x(m[0x0014])
                                                        if not (yield from self._local_call(self.cityuiworkers_b040,0xBB86,0xBB89)):return
                                                        pass
                                                    else:
                                                        self._compare(r.y,0x03)
                                                        self._mark(0xBB7B)
                                                        if not r.p&Z:
                                                            yield from self._external(0xBB80,0xE9BA,0xBB83,"call",None)
                                                            if r.pc!=0xBB83:return  # preserve nonlocal stack return
                                                            self._x(m[0x0014])
                                                            if not (yield from self._local_call(self.cityuiworkers_b040,0xBB86,0xBB89)):return
                                                            pass
                                                        else:
                                                            self._x(m[0x0014])
                                                            self._a(0x32)
                                                            m[(0x0160+r.x)&65535]=r.a
                                                            self._x(r.x+1)
                                                            m[(0x0160+r.x)&65535]=r.a
                                                            pass
                                                        pass
                                                    self._a(m[0x0014])
                                                    self._flag(C,False)
                                                    self._add(0x03)
                                                    m[0x0014]=r.a
                                                    self._y(r.y+1)
                                                    self._compare(r.y,0x04)
                                                    self._mark(0xBB95)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        pass
                                                    self._a(m[0x0479])
                                                    self._mark(0xBB9A)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._a(0x00)
                                                        m[0x0002]=r.a
                                                        m[0x0003]=r.a
                                                        self._y(0x04)
                                                        self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                                        m[0x0001]=r.a
                                                        yield from self._external(0xBBAB,0xE9BA,0xBBAE,"call",None)
                                                        if r.pc!=0xBBAE:return  # preserve nonlocal stack return
                                                        self._x(0x37)
                                                        if not (yield from self._local_call(self.cityuiworkers_b040,0xBBB0,0xBBB3)):return
                                                        pass
                                                    self._y(0x06)
                                                    self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                                    m[0x0001]=r.a
                                                    self._y(r.y+1)
                                                    self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                                    m[0x0002]=r.a
                                                    self._a(0x00)
                                                    m[0x0003]=r.a
                                                    m[0x0001]=self._shift(m[0x0001],True,rotate=False)
                                                    m[0x0002]=self._shift(m[0x0002],True,rotate=True)
                                                    m[0x0003]=self._shift(m[0x0003],True,rotate=True)
                                                    yield from self._external(0xBBCE,0xE9BA,0xBBD1,"call",None)
                                                    if r.pc!=0xBBD1:return  # preserve nonlocal stack return
                                                    self._a(m[0x0008])
                                                    m[0x0007]=r.a
                                                    self._a(m[0x0009])
                                                    m[0x0008]=r.a
                                                    self._a(0x03)
                                                    m[0x0013]=r.a
                                                    self._x(0x37)
                                                    self._a(m[0x0479])
                                                    self._mark(0xBBE7)
                                                    if not r.p&Z:
                                                        if not (yield from self._local_call(self.cityuiworkers_b040,0xBBF1,0xBBF4)):return
                                                        self._y(0x08)
                                                        self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                                        m[0x0001]=r.a
                                                        self._y(r.y+1)
                                                        self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                                        self._a(r.a & 0x03)
                                                        m[0x0002]=r.a
                                                        self._a(0x00)
                                                        m[0x0003]=r.a
                                                        yield from self._external(0xBC08,0xE9BA,0xBC0B,"call",None)
                                                        if r.pc!=0xBC0B:return  # preserve nonlocal stack return
                                                        self._a(0x04)
                                                        m[0x0013]=r.a
                                                        self._x(0x3B)
                                                        if not (yield from self._local_call(self.cityuiworkers_b040,0xBC12,0xBC15)):return
                                                        pass
                                                    else:
                                                        self._x(0x3A)
                                                        if not (yield from self._local_call(self.cityuiworkers_b040,0xBBEB,0xBBEE)):return
                                                        pass
                                                    self._a(m[0x0480])
                                                    self._flag(C,False)
                                                    self._add(0x40)
                                                    m[0x0480]=r.a
                                                    self._a(m[0x0481])
                                                    self._add(0x00)
                                                    m[0x0481]=r.a
                                                    m[0x0478]=self._nz(m[0x0478]+1)
                                                    self._a(m[PPU_JOBS])
                                                    self._a(r.a | 0x02)
                                                    m[PPU_JOBS]=r.a
                                                    self._mark(0xBC31)
                                                    self._rts();return
                    else:
                        self._a(m[0x0478])
                        self._a(r.a & 0x0F)
                        m[0x0479]=r.a
                        self._a(0x00)
                        m[0x0478]=r.a
                        m[0x047A]=r.a
                        m[0x047B]=r.a
                        m[0x0486]=r.a
                        self._a(0xC0)
                        m[0x0480]=r.a
                        self._a(0x23)
                        m[0x0481]=r.a
                        self._y(0x30)
                        yield from self._external(0xBA30,0xF25F,0xBA33,"call",None)
                        if r.pc!=0xBA33:return  # preserve nonlocal stack return
                        self._a(m[0x047C])
                        self._compare(r.a,0xFF)
                        self._mark(0xBA38)
                        if not r.p&Z:
                            self._a(m[0x0402])
                            self._y(m[0x0479])
                            self._compare(r.y,0x02)
                            self._mark(0xBA5B)
                            if not r.p&Z:
                                pass
                            else:
                                self._a(0x00)
                                m[0x0479]=r.a
                                self._a(m[0x040C])
                                pass
                            yield from self._external(0xBA65,0xF2AF,0xBA68,"call",None)
                            if r.pc!=0xBA68:return  # preserve nonlocal stack return
                            self._y(0x11)
                            self._x(0x00)
                            while True:  # natural loop $BA6C
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                m[(0x0151+r.x)&65535]=r.a
                                self._compare(r.a,0xFF)
                                self._mark(0xBA73)
                                if r.p&Z:
                                    pass
                                else:
                                    m[0x047B]=self._nz(m[0x047B]+1)
                                    pass
                                self._x(r.x+1)
                                self._y(r.y+1)
                                self._compare(r.x,0x0A)
                                self._mark(0xBA7C)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._a(m[0x0479])
                                self._mark(0xBA81)
                                if r.p&Z:
                                    self._a(0xC9)
                                    m[0x0482]=r.a
                                    self._a(0xB8)
                                    m[0x0483]=r.a
                                    pass
                                else:
                                    self._a(0x09)
                                    m[0x0482]=r.a
                                    self._a(0xB8)
                                    m[0x0483]=r.a
                                    pass
                                self._a(m[0x0478])
                                self._compare(r.a,0x0F)
                                self._mark(0xBAA2)
                                if r.p&Z:
                                    self._y(0x00)
                                    self._a(0xAA)
                                    while True:  # natural loop $BB07
                                        m[(0x0160+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._compare(r.y,0x40)
                                        self._mark(0xBB0D)
                                        if not r.p&C:
                                            continue
                                        else:
                                            pass
                                        self._a(0xC0)
                                        m[0x0480]=r.a
                                        self._a(0x27)
                                        m[0x0481]=r.a
                                        m[0x0478]=self._nz(m[0x0478]+1)
                                        self._a(m[PPU_JOBS])
                                        self._a(r.a | 0x02)
                                        m[PPU_JOBS]=r.a
                                        self._mark(0xBB27)
                                        self._rts();return
                                else:
                                    self._compare(r.a,0x02)
                                    self._mark(0xBAA6)
                                    if not r.p&C:
                                        self._a(m[0x0482])
                                        m[0x001A]=r.a
                                        self._a(m[0x0483])
                                        m[0x001B]=r.a
                                        self._y(0x00)
                                        while True:  # natural loop $BAC5
                                            self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                            m[(0x0160+r.y)&65535]=r.a
                                            self._y(r.y+1)
                                            self._compare(r.y,0x40)
                                            self._mark(0xBACD)
                                            if not r.p&C:
                                                continue
                                            else:
                                                pass
                                            self._a(m[0x0482])
                                            self._flag(C,False)
                                            self._add(0x40)
                                            m[0x0482]=r.a
                                            self._a(m[0x0483])
                                            self._add(0x00)
                                            m[0x0483]=r.a
                                            self._a(m[0x0480])
                                            self._flag(C,False)
                                            self._add(0x40)
                                            m[0x0480]=r.a
                                            self._a(m[0x0481])
                                            self._add(0x00)
                                            m[0x0481]=r.a
                                            m[0x0478]=self._nz(m[0x0478]+1)
                                            self._a(m[PPU_JOBS])
                                            self._a(r.a | 0x02)
                                            m[PPU_JOBS]=r.a
                                            self._mark(0xBB27)
                                            self._rts();return
                                    else:
                                        self._a(m[0x0486])
                                        self._mark(0xBAAB)
                                        if not r.p&Z:
                                            self._a(0x01)
                                            self._y(0x00)
                                            while True:  # natural loop $BAE7
                                                m[(0x0160+r.y)&65535]=r.a
                                                self._y(r.y+1)
                                                self._compare(r.y,0x40)
                                                self._mark(0xBAED)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    pass
                                                self._a(m[0x0480])
                                                self._flag(C,False)
                                                self._add(0x40)
                                                m[0x0480]=r.a
                                                self._a(m[0x0481])
                                                self._add(0x00)
                                                m[0x0481]=r.a
                                                m[0x0478]=self._nz(m[0x0478]+1)
                                                self._a(m[PPU_JOBS])
                                                self._a(r.a | 0x02)
                                                m[PPU_JOBS]=r.a
                                                self._mark(0xBB27)
                                                self._rts();return
                                        else:
                                            m[0x0486]=self._nz(m[0x0486]+1)
                                            self._a(m[0x047C])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xBAB5)
                                            if r.p&Z:
                                                self._a(0x01)
                                                self._y(0x00)
                                                while True:  # natural loop $BAE7
                                                    m[(0x0160+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._compare(r.y,0x40)
                                                    self._mark(0xBAED)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        pass
                                                    self._a(m[0x0480])
                                                    self._flag(C,False)
                                                    self._add(0x40)
                                                    m[0x0480]=r.a
                                                    self._a(m[0x0481])
                                                    self._add(0x00)
                                                    m[0x0481]=r.a
                                                    m[0x0478]=self._nz(m[0x0478]+1)
                                                    self._a(m[PPU_JOBS])
                                                    self._a(r.a | 0x02)
                                                    m[PPU_JOBS]=r.a
                                                    self._mark(0xBB27)
                                                    self._rts();return
                                            else:
                                                self._a(m[0x0482])
                                                m[0x001A]=r.a
                                                self._a(m[0x0483])
                                                m[0x001B]=r.a
                                                self._y(0x00)
                                                while True:  # natural loop $BAC5
                                                    self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                                    m[(0x0160+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._compare(r.y,0x40)
                                                    self._mark(0xBACD)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        pass
                                                    self._a(m[0x0482])
                                                    self._flag(C,False)
                                                    self._add(0x40)
                                                    m[0x0482]=r.a
                                                    self._a(m[0x0483])
                                                    self._add(0x00)
                                                    m[0x0483]=r.a
                                                    self._a(m[0x0480])
                                                    self._flag(C,False)
                                                    self._add(0x40)
                                                    m[0x0480]=r.a
                                                    self._a(m[0x0481])
                                                    self._add(0x00)
                                                    m[0x0481]=r.a
                                                    m[0x0478]=self._nz(m[0x0478]+1)
                                                    self._a(m[PPU_JOBS])
                                                    self._a(r.a | 0x02)
                                                    m[PPU_JOBS]=r.a
                                                    self._mark(0xBB27)
                                                    self._rts();return
                        else:
                            self._a(r.a & 0x0F)
                            m[0x047C]=r.a
                            self._y(0x00)
                            while True:  # natural loop $BA41
                                self._a(m[(0x0151+r.y)&65535])
                                self._compare(r.a,0xFF)
                                self._mark(0xBA46)
                                if r.p&Z:
                                    pass
                                else:
                                    m[0x047B]=self._nz(m[0x047B]+1)
                                    pass
                                self._y(r.y+1)
                                self._compare(r.y,0x0A)
                                self._mark(0xBA4E)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._a(m[0x0479])
                                self._mark(0xBA81)
                                if r.p&Z:
                                    self._a(0xC9)
                                    m[0x0482]=r.a
                                    self._a(0xB8)
                                    m[0x0483]=r.a
                                    pass
                                else:
                                    self._a(0x09)
                                    m[0x0482]=r.a
                                    self._a(0xB8)
                                    m[0x0483]=r.a
                                    pass
                                self._a(m[0x0478])
                                self._compare(r.a,0x0F)
                                self._mark(0xBAA2)
                                if r.p&Z:
                                    self._y(0x00)
                                    self._a(0xAA)
                                    while True:  # natural loop $BB07
                                        m[(0x0160+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._compare(r.y,0x40)
                                        self._mark(0xBB0D)
                                        if not r.p&C:
                                            continue
                                        else:
                                            pass
                                        self._a(0xC0)
                                        m[0x0480]=r.a
                                        self._a(0x27)
                                        m[0x0481]=r.a
                                        m[0x0478]=self._nz(m[0x0478]+1)
                                        self._a(m[PPU_JOBS])
                                        self._a(r.a | 0x02)
                                        m[PPU_JOBS]=r.a
                                        self._mark(0xBB27)
                                        self._rts();return
                                else:
                                    self._compare(r.a,0x02)
                                    self._mark(0xBAA6)
                                    if not r.p&C:
                                        self._a(m[0x0482])
                                        m[0x001A]=r.a
                                        self._a(m[0x0483])
                                        m[0x001B]=r.a
                                        self._y(0x00)
                                        while True:  # natural loop $BAC5
                                            self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                            m[(0x0160+r.y)&65535]=r.a
                                            self._y(r.y+1)
                                            self._compare(r.y,0x40)
                                            self._mark(0xBACD)
                                            if not r.p&C:
                                                continue
                                            else:
                                                pass
                                            self._a(m[0x0482])
                                            self._flag(C,False)
                                            self._add(0x40)
                                            m[0x0482]=r.a
                                            self._a(m[0x0483])
                                            self._add(0x00)
                                            m[0x0483]=r.a
                                            self._a(m[0x0480])
                                            self._flag(C,False)
                                            self._add(0x40)
                                            m[0x0480]=r.a
                                            self._a(m[0x0481])
                                            self._add(0x00)
                                            m[0x0481]=r.a
                                            m[0x0478]=self._nz(m[0x0478]+1)
                                            self._a(m[PPU_JOBS])
                                            self._a(r.a | 0x02)
                                            m[PPU_JOBS]=r.a
                                            self._mark(0xBB27)
                                            self._rts();return
                                    else:
                                        self._a(m[0x0486])
                                        self._mark(0xBAAB)
                                        if not r.p&Z:
                                            self._a(0x01)
                                            self._y(0x00)
                                            while True:  # natural loop $BAE7
                                                m[(0x0160+r.y)&65535]=r.a
                                                self._y(r.y+1)
                                                self._compare(r.y,0x40)
                                                self._mark(0xBAED)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    pass
                                                self._a(m[0x0480])
                                                self._flag(C,False)
                                                self._add(0x40)
                                                m[0x0480]=r.a
                                                self._a(m[0x0481])
                                                self._add(0x00)
                                                m[0x0481]=r.a
                                                m[0x0478]=self._nz(m[0x0478]+1)
                                                self._a(m[PPU_JOBS])
                                                self._a(r.a | 0x02)
                                                m[PPU_JOBS]=r.a
                                                self._mark(0xBB27)
                                                self._rts();return
                                        else:
                                            m[0x0486]=self._nz(m[0x0486]+1)
                                            self._a(m[0x047C])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xBAB5)
                                            if r.p&Z:
                                                self._a(0x01)
                                                self._y(0x00)
                                                while True:  # natural loop $BAE7
                                                    m[(0x0160+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._compare(r.y,0x40)
                                                    self._mark(0xBAED)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        pass
                                                    self._a(m[0x0480])
                                                    self._flag(C,False)
                                                    self._add(0x40)
                                                    m[0x0480]=r.a
                                                    self._a(m[0x0481])
                                                    self._add(0x00)
                                                    m[0x0481]=r.a
                                                    m[0x0478]=self._nz(m[0x0478]+1)
                                                    self._a(m[PPU_JOBS])
                                                    self._a(r.a | 0x02)
                                                    m[PPU_JOBS]=r.a
                                                    self._mark(0xBB27)
                                                    self._rts();return
                                            else:
                                                self._a(m[0x0482])
                                                m[0x001A]=r.a
                                                self._a(m[0x0483])
                                                m[0x001B]=r.a
                                                self._y(0x00)
                                                while True:  # natural loop $BAC5
                                                    self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                                    m[(0x0160+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._compare(r.y,0x40)
                                                    self._mark(0xBACD)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        pass
                                                    self._a(m[0x0482])
                                                    self._flag(C,False)
                                                    self._add(0x40)
                                                    m[0x0482]=r.a
                                                    self._a(m[0x0483])
                                                    self._add(0x00)
                                                    m[0x0483]=r.a
                                                    self._a(m[0x0480])
                                                    self._flag(C,False)
                                                    self._add(0x40)
                                                    m[0x0480]=r.a
                                                    self._a(m[0x0481])
                                                    self._add(0x00)
                                                    m[0x0481]=r.a
                                                    m[0x0478]=self._nz(m[0x0478]+1)
                                                    self._a(m[PPU_JOBS])
                                                    self._a(r.a | 0x02)
                                                    m[PPU_JOBS]=r.a
                                                    self._mark(0xBB27)
                                                    self._rts();return

    def block_menu_tick(self):
        """$BC71: block menu tick; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBC71)
        self._a(m[0x0401])
        self._mark(0xBC74)
        index=self._dispatch(0xBC74,(48259, 48283, 48387, 48440, 48480, 48530))
        return (yield from (self.cityuiworkers_bc74_phase_0,self.cityuiworkers_bc74_phase_1,self.cityuiworkers_bc74_phase_2,self.cityuiworkers_bc74_phase_3,self.cityuiworkers_bc74_phase_4,self.cityuiworkers_bc74_phase_5,)[index]())

    def cityuiworkers_bc74_phase_0(self):
        """$BC83: cityuiworkers bc74 phase 0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBC83)
        self._a(0x00)
        m[0x0470]=r.a
        self._a(0x88)
        m[0x0471]=r.a
        self._a(0x00)
        m[0x0472]=r.a
        self._a(0x24)
        m[0x0473]=r.a
        m[0x0401]=self._nz(m[0x0401]+1)
        self._mark(0xBC9A)
        self._rts();return

    def cityuiworkers_bc74_phase_1(self):
        """$BC9B: cityuiworkers bc74 phase 1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBC9B)
        self._y(0x30)
        yield from self._external(0xBC9D,0xF25F,0xBCA0,"call",None)
        if r.pc!=0xBCA0:return  # preserve nonlocal stack return
        self._a(0x40)
        m[0x0380]=r.a
        self._a(m[0x0473])
        m[0x0381]=r.a
        self._a(m[0x0472])
        m[0x0382]=r.a
        self._a(m[0x0470])
        m[0x0000]=r.a
        self._a(m[0x0471])
        m[0x0001]=r.a
        self._y(0x00)
        while True:  # natural loop $BCBF
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[(0x0383+r.y)&65535]=r.a
            self._y(r.y+1)
            self._compare(r.y,0x40)
            self._mark(0xBCC7)
            if not r.p&C:
                continue
            else:
                pass
            self._a(0xFF)
            m[(0x0383+r.y)&65535]=r.a
            self._a(m[0x0470])
            self._flag(C,False)
            self._add(0x40)
            m[0x0470]=r.a
            self._a(m[0x0471])
            self._add(0x00)
            m[0x0471]=r.a
            self._a(m[0x0472])
            self._flag(C,False)
            self._add(0x40)
            m[0x0472]=r.a
            self._a(m[0x0473])
            self._add(0x00)
            m[0x0473]=r.a
            self._compare(r.a,0x28)
            self._mark(0xBCF2)
            if not r.p&Z:
                pass
            else:
                m[0x0401]=self._nz(m[0x0401]+1)
                yield from self._external(0xBCF7,0xECEE,0xBCFA,"call",None)
                if r.pc!=0xBCFA:return  # preserve nonlocal stack return
                pass
            self._a(m[PPU_JOBS])
            self._a(r.a | 0x04)
            m[PPU_JOBS]=r.a
            self._mark(0xBD02)
            self._rts();return

    def cityuiworkers_bc74_phase_2(self):
        """$BD03: cityuiworkers bc74 phase 2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBD03)
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xBD06)
        if not r.p&N:
            self._mark(0xBD37)
            self._rts();return
        else:
            self._a(0x0A)
            m[0x00B3]=r.a
            self._a(0x0B)
            m[0x00C3]=r.a
            self._a(0x0E)
            m[0x00CB]=r.a
            self._a(0x14)
            m[0x00D3]=r.a
            self._a(0x15)
            m[0x00DB]=r.a
            self._a(0xE1)
            m[0x00E6]=r.a
            self._a(0x00)
            m[0x0000]=r.a
            yield from self._external(0xBD2B,0xDBB1,0xBD2E,"call",None)
            if r.pc!=0xBD2E:return  # preserve nonlocal stack return
            m[0x0401]=self._nz(m[0x0401]+1)
            if not (yield from self._local_call(self.cityuiworkers_bdfe,0xBD31,0xBD34)):return
            self._mark(0xBD34)
            yield from self._external(0xBD34,0xECBF,None,"tail")
            return

    def cityuiworkers_bc74_phase_3(self):
        """$BD38: cityuiworkers bc74 phase 3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBD38)
        self._a(0xF0)
        m[0x0200]=r.a
        m[0x0204]=r.a
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xBD43)
        if not r.p&N:
            self._mark(0xBD5F)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a | m[0x0082])
            self._a(r.a & 0x04)
            self._mark(0xBD4D)
            if r.p&Z:
                self._mark(0xBD5F)
                self._rts();return
            else:
                self._a(m[0x0083])
                self._compare(r.a,0x1C)
                self._mark(0xBD54)
                if not r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.cityuiworkers_bdf1,0xBD56,0xBD59)):return
                    pass
                m[0x0401]=self._nz(m[0x0401]+1)
                self._mark(0xBD5C)
                yield from self._external(0xBD5C,0xECEE,None,"tail")
                return

    def cityuiworkers_bc74_phase_4(self):
        """$BD60: cityuiworkers bc74 phase 4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBD60)
        self._a(0xF0)
        m[0x0200]=r.a
        m[0x0204]=r.a
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xBD6B)
        if not r.p&N:
            self._mark(0xBD91)
            self._rts();return
        else:
            self._a(0x01)
            m[0x00B3]=r.a
            m[0x00C3]=r.a
            m[0x00CB]=r.a
            m[0x00D3]=r.a
            m[0x00DB]=r.a
            self._a(0xE0)
            m[0x00E6]=r.a
            self._a(0x00)
            m[0x0000]=r.a
            yield from self._external(0xBD88,0xDBB1,0xBD8B,"call",None)
            if r.pc!=0xBD8B:return  # preserve nonlocal stack return
            m[0x0401]=self._nz(m[0x0401]+1)
            self._mark(0xBD8E)
            yield from self._external(0xBD8E,0xECBF,None,"tail")
            return

    def cityuiworkers_bc74_phase_5(self):
        """$BD92: cityuiworkers bc74 phase 5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBD92)
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xBD95)
        if not r.p&N:
            pass
        else:
            self._a(0x40)
            m[0x0380]=r.a
            self._a(0x27)
            m[0x0381]=r.a
            self._a(0xC0)
            m[0x0382]=r.a
            self._y(0x39)
            self._a(0xAA)
            while True:  # natural loop $BDAA
                m[(0x0383+r.y)&65535]=r.a
                self._y(r.y-1)
                self._mark(0xBDAE)
                if not r.p&N:
                    continue
                else:
                    pass
                self._a(0xFF)
                m[0x03C3]=r.a
                self._a(m[PPU_JOBS])
                self._a(r.a | 0x04)
                m[PPU_JOBS]=r.a
                self._a(0x40)
                m[0x0068]=r.a
                self._a(0x14)
                m[0x006A]=r.a
                self._a(0x1E)
                m[0x006C]=r.a
                self._a(0x20)
                m[0x006E]=r.a
                self._a(0xF2)
                m[0x006F]=r.a
                self._a(0x0D)
                m[0x0070]=r.a
                self._a(0xF2)
                m[0x0071]=r.a
                self._a(0x00)
                m[0x0400]=r.a
                m[0x0401]=r.a
                self._y(0x03)
                while True:  # natural loop $BDEA
                    m[(0x0470+r.y)&65535]=r.a
                    self._y(r.y-1)
                    self._mark(0xBDEE)
                    if not r.p&N:
                        continue
                    else:
                        pass
                    self._mark(0xBDF0)
                    self._rts();return
        self._mark(0xBDF0)
        self._rts();return

    def cityuiworkers_bdf1(self):
        """$BDF1: cityuiworkers bdf1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBDF1)
        self._a(m[0x6F05])
        self._compare(r.a,0x02)
        self._mark(0xBDF6)
        if not r.p&C:
            pass
        else:
            self._a(0x01)
            m[0x6F05]=r.a
            pass
        self._mark(0xBDFD)
        self._rts();return

    def cityuiworkers_bdfe(self):
        """$BDFE: cityuiworkers bdfe; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBDFE)
        self._a(0x03)
        m[0x0061]=r.a
        self._a(0x28)
        m[0x0068]=r.a
        self._a(0xE9)
        m[0x0069]=r.a
        self._a(0x20)
        m[0x006A]=r.a
        self._a(0xF2)
        m[0x006B]=r.a
        self._a(0x20)
        m[0x006C]=r.a
        self._a(0xF2)
        m[0x006D]=r.a
        self._a(0x20)
        m[0x006E]=r.a
        self._a(0xF2)
        m[0x006F]=r.a
        self._a(0xF0)
        m[0x0070]=r.a
        self._a(0xF1)
        m[0x0071]=r.a
        self._mark(0xBE35)
        self._rts();return

    def update_animation_job(self):
        """$BE36: update animation job; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBE36)
        self._a(m[0x04A0])
        self._mark(0xBE39)
        if not r.p&Z:
            self._mark(0xBE3C)
            if r.p&N:
                self._a(r.a & 0x0F)
                self._mark(0xBE5F)
                if not r.p&Z:
                    m[0x04A3]=self._nz(m[0x04A3]+1)
                    m[0x04D0]=self._nz(m[0x04D0]+1)
                    self._y(0x36)
                    yield from self._external(0xBE6C,0xF25F,0xBE6F,"call",None)
                    if r.pc!=0xBE6F:return  # preserve nonlocal stack return
                    self._a(m[0x04A2])
                    self._mark(0xBE72)
                    index=self._dispatch(0xBE72,(48827, 48875, 48943, 49008, 49087, 49139, 49222, 49296, 49352, 49443, 49512, 49580, 49658, 49757, 49885, 49981, 50082, 50166, 50238, 50401, 50449, 50518, 50609, 50679, 50742, 50813, 50886, 51039, 51153, 51200, 51248, 51325, 51380, 51441, 51494))
                    return (yield from (self.cityuiworkers_be72_phase_0,self.cityuiworkers_be72_phase_1,self.cityuiworkers_be72_phase_2,self.cityuiworkers_be72_phase_3,self.cityuiworkers_be72_phase_4,self.cityuiworkers_be72_phase_5,self.cityuiworkers_be72_phase_6,self.cityuiworkers_be72_phase_7,self.cityuiworkers_be72_phase_8,self.cityuiworkers_be72_phase_9,self.cityuiworkers_be72_phase_10,self.cityuiworkers_be72_phase_11,self.cityuiworkers_be72_phase_12,self.cityuiworkers_be72_phase_13,self.cityuiworkers_be72_phase_14,self.cityuiworkers_be72_phase_15,self.cityuiworkers_be72_phase_16,self.cityuiworkers_be72_phase_17,self.cityuiworkers_be72_phase_18,self.cityuiworkers_be72_phase_19,self.cityuiworkers_be72_phase_20,self.cityuiworkers_be72_phase_21,self.cityuiworkers_be72_phase_22,self.cityuiworkers_be72_phase_23,self.cityuiworkers_be72_phase_24,self.cityuiworkers_be72_phase_25,self.cityuiworkers_be72_phase_26,self.cityuiworkers_be72_phase_27,self.cityuiworkers_be72_phase_28,self.cityuiworkers_be72_phase_29,self.cityuiworkers_be72_phase_30,self.cityuiworkers_be72_phase_31,self.cityuiworkers_be72_phase_32,self.cityuiworkers_be72_phase_33,self.cityuiworkers_be72_phase_34,)[index]())
                else:
                    self._a(m[0x04A1])
                    self._mark(0xC9C5)
                    index=self._dispatch(0xC9C5,(51688, 51664, 51790, 52050))
                    return (yield from (self.cityuiworkers_c9c5_phase_0,self.cityuiworkers_c9c5_phase_1,self.cityuiworkers_c9c5_phase_2,self.cityuiworkers_c9c5_phase_3,)[index]())
            else:
                m[0x04A2]=r.a
                m[0x04A2]=self._nz(m[0x04A2]-1)
                self._a(0x00)
                m[0x04A1]=r.a
                self._x(0x40)
                self._a(m[0x0150])
                self._mark(0xBE4E)
                if r.p&N:
                    pass
                else:
                    self._x(0x80)
                    pass
                m[0x0420]=r.x
                self._a(0x80)
                m[0x04A0]=r.a
                self._a(m[0x04A1])
                self._mark(0xC9C5)
                index=self._dispatch(0xC9C5,(51688, 51664, 51790, 52050))
                return (yield from (self.cityuiworkers_c9c5_phase_0,self.cityuiworkers_c9c5_phase_1,self.cityuiworkers_c9c5_phase_2,self.cityuiworkers_c9c5_phase_3,)[index]())
        else:
            self._mark(0xBE3B)
            self._rts();return

    def cityuiworkers_be72_phase_0(self):
        """$BEBB: cityuiworkers be72 phase 0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBEBB)
        self._a(m[0x04A1])
        self._mark(0xBEBE)
        if not r.p&Z:
            self._a(0x00)
            m[0x0010]=r.a
            self._a(0x80)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xBED6,0xBED9)):return
            self._a(m[0x04A3])
            self._a(r.a & 0x04)
            self._mark(0xBEDE)
            if r.p&Z:
                pass
            else:
                self._a(0x01)
                pass
            m[0x04A1]=r.a
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xE8)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xBEC2,0xBEC5)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xBEC8)
            self._rts();return

    def cityuiworkers_be72_phase_1(self):
        """$BEEB: cityuiworkers be72 phase 1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBEEB)
        self._a(m[0x04A1])
        self._mark(0xBEEE)
        if not r.p&Z:
            self._a(0xF6)
            m[0x0010]=r.a
            self._a(0x80)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xBF0B,0xBF0E)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x07)
            self._compare(r.a,0x06)
            self._mark(0xBF18)
            if not r.p&Z:
                pass
            else:
                self._a(0x00)
                m[0x04A3]=r.a
                pass
            self._y(r.a)
            self._a(m[(0xBF29+r.y)&65535])
            m[0x04A1]=r.a
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xDC)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xBEF2,0xBEF5)):return
            self._a(0xDF)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xBEF7,0xBEFA)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xBEFD)
            self._rts();return

    def cityuiworkers_be72_phase_2(self):
        """$BF2F: cityuiworkers be72 phase 2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBF2F)
        self._a(m[0x04A1])
        self._mark(0xBF32)
        if not r.p&Z:
            self._a(0x72)
            m[0x0010]=r.a
            self._a(0x81)
            m[0x0011]=r.a
            self._y(0x01)
            if not (yield from self._local_call(self.cityuiworkers_c994,0xBF49,0xBF4C)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x1F)
            self._compare(r.a,0x15)
            self._mark(0xBF56)
            if r.p&C:
                pass
            else:
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                m[0x0000]=r.a
                self._y(0x54)
                self._a(0xF0)
                while True:  # natural loop $BF61
                    m[(0x0200+r.y)&65535]=r.a
                    self._y(r.y-1)
                    self._y(r.y-1)
                    self._y(r.y-1)
                    self._y(r.y-1)
                    self._compare(r.y,m[0x0000])
                    self._mark(0xBF6B)
                    if not r.p&Z:
                        continue
                    else:
                        pass
                    self._a(m[0x04D0])
                    self._compare(r.a,m[0x04CC])
                    self._mark(0xC93A)
                    if not r.p&C:
                        pass
                    else:
                        self._a(m[0x04A2])
                        self._mark(0xC93F)
                        if r.p&Z:
                            pass
                        else:
                            self._compare(r.a,0x04)
                            self._mark(0xC943)
                            if r.p&Z:
                                pass
                            else:
                                self._compare(r.a,0x08)
                                self._mark(0xC947)
                                if r.p&Z:
                                    pass
                                else:
                                    yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                                    if r.pc!=0xC94C:return  # preserve nonlocal stack return
                                    self._a(0x81)
                                    yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                                    if r.pc!=0xC951:return  # preserve nonlocal stack return
                                    pass
                                pass
                            pass
                        self._a(0x01)
                        m[0x007D]=r.a
                        self._a(0x00)
                        m[0x0000]=r.a
                        self._y(0x3D)
                        yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                        if r.pc!=0xC962:return  # preserve nonlocal stack return
                        self._a(0x80)
                        m[0x0140]=r.a
                        self._a(0x22)
                        m[0x04A2]=r.a
                        pass
                    self._mark(0xC96C)
                    self._rts();return
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xE1)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xBF36,0xBF39)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xBF3C)
            self._rts();return

    def cityuiworkers_be72_phase_3(self):
        """$BF70: cityuiworkers be72 phase 3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBF70)
        self._a(m[0x04A1])
        self._mark(0xBF73)
        if not r.p&Z:
            self._a(0xCD)
            m[0x0010]=r.a
            self._a(0x81)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xBF95,0xBF98)):return
            self._y(m[0x04A4])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xBF9B,0xBF9E)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[0x0000]=r.a
            self._a(r.a & 0x01)
            self._flag(C,False)
            self._add(0x01)
            m[0x04A1]=r.a
            self._a(m[0x0000])
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x01)
            self._flag(C,False)
            self._add(0x03)
            m[0x04A4]=r.a
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xE9)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xBF77,0xBF7A)):return
            self._a(0xEA)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xBF7C,0xBF7F)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(0x03)
            m[0x04A4]=r.a
            self._mark(0xBF87)
            self._rts();return

    def cityuiworkers_be72_phase_4(self):
        """$BFBF: cityuiworkers be72 phase 4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBFBF)
        self._a(m[0x04A1])
        self._mark(0xBFC2)
        if not r.p&Z:
            self._a(0x39)
            m[0x0010]=r.a
            self._a(0x82)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xBFDF,0xBFE2)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x01)
            m[0x04A1]=r.a
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xD1)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xBFC6,0xBFC9)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(0x80)
            m[0x04CC]=r.a
            self._mark(0xBFD1)
            self._rts();return

    def cityuiworkers_be72_phase_5(self):
        """$BFF3: cityuiworkers be72 phase 5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBFF3)
        self._a(m[0x04A1])
        self._mark(0xBFF6)
        if not r.p&Z:
            self._a(0xA7)
            m[0x0010]=r.a
            self._a(0x82)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC01D,0xC020)):return
            self._y(m[0x04A4])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC023,0xC026)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[0x0000]=r.a
            self._a(r.a & 0x01)
            self._flag(C,False)
            self._add(0x01)
            m[0x04A1]=r.a
            self._a(m[0x0000])
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x01)
            self._flag(C,False)
            self._add(0x03)
            m[0x04A4]=r.a
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xC6)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xBFFA,0xBFFD)):return
            self._a(0xCF)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xBFFF,0xC002)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(0x03)
            m[0x04A4]=r.a
            self._a(0x80)
            m[0x04CC]=r.a
            self._mark(0xC00F)
            self._rts();return

    def cityuiworkers_be72_phase_6(self):
        """$C046: cityuiworkers be72 phase 6; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC046)
        self._a(m[0x04A1])
        self._mark(0xC049)
        if not r.p&Z:
            self._a(0x83)
            m[0x0010]=r.a
            self._a(0x83)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC06B,0xC06E)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x0F)
            self._y(r.a)
            self._a(m[(0xC080+r.y)&65535])
            m[0x04A1]=r.a
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xEA)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC04D,0xC050)):return
            self._a(0xEB)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xC052,0xC055)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(0x78)
            m[0x04A3]=r.a
            self._mark(0xC05D)
            self._rts();return

    def cityuiworkers_be72_phase_7(self):
        """$C090: cityuiworkers be72 phase 7; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC090)
        self._a(m[0x04A1])
        self._mark(0xC093)
        if not r.p&Z:
            self._a(0x54)
            m[0x0010]=r.a
            self._a(0x84)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC0AB,0xC0AE)):return
            self._a(m[0x04A1])
            self._compare(r.a,0x03)
            self._mark(0xC0B3)
            if r.p&Z:
                pass
            else:
                self._a(m[0x04A3])
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                self._a(r.a & 0x03)
                self._flag(C,False)
                self._add(0x01)
                m[0x04A1]=r.a
                pass
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xB7)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC097,0xC09A)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC09D)
            self._rts();return

    def cityuiworkers_be72_phase_8(self):
        """$C0C8: cityuiworkers be72 phase 8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC0C8)
        self._a(m[0x04A1])
        self._mark(0xC0CB)
        if not r.p&Z:
            self._a(0x59)
            m[0x0010]=r.a
            self._a(0x85)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC0F4,0xC0F7)):return
            self._y(m[0x04A4])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC0FA,0xC0FD)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[0x0000]=r.a
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x01)
            self._flag(C,False)
            self._add(0x01)
            m[0x04A1]=r.a
            self._a(m[0x0000])
            self._a(r.a & 0x03)
            self._compare(r.a,0x03)
            self._mark(0xC116)
            if not r.p&Z:
                pass
            else:
                self._a(0x01)
                pass
            self._flag(C,False)
            self._add(0x03)
            m[0x04A4]=r.a
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xCA)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC0CF,0xC0D2)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(0x03)
            m[0x04A4]=r.a
            self._a(m[0x04D6])
            self._compare(r.a,0x47)
            self._mark(0xC0DF)
            if r.p&Z:
                pass
            else:
                self._a(0x80)
                m[0x04CC]=r.a
                pass
            self._mark(0xC0E6)
            self._rts();return

    def cityuiworkers_be72_phase_9(self):
        """$C123: cityuiworkers be72 phase 9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC123)
        self._a(m[0x04A1])
        self._mark(0xC126)
        if not r.p&Z:
            self._a(0x3C)
            m[0x0010]=r.a
            self._a(0x86)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC143,0xC146)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x0F)
            self._y(r.a)
            self._a(m[(0xC158+r.y)&65535])
            m[0x04A1]=r.a
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xF1)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC12A,0xC12D)):return
            self._a(0xF2)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xC12F,0xC132)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC135)
            self._rts();return

    def cityuiworkers_be72_phase_10(self):
        """$C168: cityuiworkers be72 phase 10; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC168)
        self._a(m[0x04A1])
        self._mark(0xC16B)
        if not r.p&Z:
            self._a(0x60)
            m[0x0010]=r.a
            self._a(0x87)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC188,0xC18B)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x0F)
            self._y(r.a)
            self._a(m[(0xC19C+r.y)&65535])
            m[0x04A1]=r.a
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xF0)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC16F,0xC172)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(0x28)
            m[0x04A3]=r.a
            self._mark(0xC17A)
            self._rts();return

    def cityuiworkers_be72_phase_11(self):
        """$C1AC: cityuiworkers be72 phase 11; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC1AC)
        self._a(m[0x04A1])
        self._mark(0xC1AF)
        if not r.p&Z:
            self._a(0xD1)
            m[0x0010]=r.a
            self._a(0x87)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC1D7,0xC1DA)):return
            self._y(0x04)
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC1DC,0xC1DF)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x07)
            self._y(r.a)
            self._a(m[(0xC1F2+r.y)&65535])
            m[0x04A1]=r.a
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xE9)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC1B3,0xC1B6)):return
            self._a(0xEB)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xC1B8,0xC1BB)):return
            self._a(0xC3)
            m[0x00C1]=r.a
            m[0x00C9]=r.a
            m[0x00D1]=r.a
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC1C9)
            self._rts();return

    def cityuiworkers_be72_phase_12(self):
        """$C1FA: cityuiworkers be72 phase 12; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC1FA)
        self._a(m[0x04A1])
        self._mark(0xC1FD)
        if not r.p&Z:
            self._a(0xD5)
            m[0x0010]=r.a
            self._a(0x88)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC225,0xC228)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x0F)
            self._y(r.a)
            self._compare(r.a,0x0A)
            self._mark(0xC233)
            if not r.p&Z:
                pass
            else:
                self._a(0x00)
                m[0x04A3]=r.a
                pass
            self._a(m[(0xC252+r.y)&65535])
            m[0x04A1]=r.a
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x01)
            self._flag(C,False)
            self._add(0x05)
            self._y(r.a)
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC24C,0xC24F)):return
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xF8)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC201,0xC204)):return
            self._a(0xF9)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xC206,0xC209)):return
            self._a(0xFA)
            m[0x00C1]=r.a
            m[0x00C9]=r.a
            m[0x00D1]=r.a
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC217)
            self._rts();return

    def cityuiworkers_be72_phase_13(self):
        """$C25D: cityuiworkers be72 phase 13; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC25D)
        self._a(m[0x04A1])
        self._mark(0xC260)
        if not r.p&Z:
            self._a(0xB7)
            m[0x0010]=r.a
            self._a(0x89)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC297,0xC29A)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[0x0000]=r.a
            self._a(r.a & 0x03)
            self._compare(r.a,0x03)
            self._mark(0xC2A8)
            if not r.p&Z:
                pass
            else:
                self._a(0x01)
                pass
            m[0x04A1]=r.a
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._y(0x04)
            self._a(m[0x0000])
            self._a(r.a & 0x02)
            self._mark(0xC2B9)
            if r.p&Z:
                pass
            else:
                self._y(0x05)
                pass
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC2BD,0xC2C0)):return
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xF7)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC264,0xC267)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._y(0x00)
            self._x(0x00)
            self._a(m[0x0150])
            self._mark(0xC271)
            if not r.p&N:
                pass
            else:
                self._x(0x0D)
                pass
            while True:  # natural loop $C275
                self._a(m[(0xC2C3+r.x)&65535])
                m[(0x0380+r.y)&65535]=r.a
                self._x(r.x+1)
                self._y(r.y+1)
                self._compare(r.y,0x0D)
                self._mark(0xC27F)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[PPU_JOBS])
                self._a(r.a | 0x04)
                m[PPU_JOBS]=r.a
                self._mark(0xC289)
                self._rts();return

    def cityuiworkers_be72_phase_14(self):
        """$C2DD: cityuiworkers be72 phase 14; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC2DD)
        self._a(m[0x04A1])
        self._mark(0xC2E0)
        if not r.p&Z:
            self._a(0x52)
            m[0x0010]=r.a
            self._a(0x8A)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC2FD,0xC300)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[0x0000]=r.a
            self._a(r.a & 0x0F)
            self._y(r.a)
            self._compare(r.a,0x0A)
            self._mark(0xC30E)
            if not r.p&Z:
                pass
            else:
                self._a(0x00)
                m[0x04A3]=r.a
                pass
            self._a(m[(0xC332+r.y)&65535])
            m[0x04A1]=r.a
            self._y(0x01)
            self._a(m[0x0000])
            self._a(r.a & 0x0F)
            self._compare(r.a,0x05)
            self._mark(0xC324)
            if r.p&C:
                pass
            else:
                self._a(r.a & 0x01)
                self._mark(0xC328)
                if r.p&Z:
                    pass
                else:
                    self._y(0x02)
                    pass
                pass
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC32C,0xC32F)):return
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xF3)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC2E4,0xC2E7)):return
            self._a(0xF4)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xC2E9,0xC2EC)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC2EF)
            self._rts();return

    def cityuiworkers_be72_phase_15(self):
        """$C33D: cityuiworkers be72 phase 15; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC33D)
        self._a(m[0x04A1])
        self._mark(0xC340)
        if not r.p&Z:
            m[0x04A5]=self._nz(m[0x04A5]+1)
            self._a(0x55)
            m[0x0010]=r.a
            self._a(0x8B)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            self._x(m[0x04A4])
            if not (yield from self._local_call(self.cityuiworkers_c996,0xC363,0xC366)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[0x0000]=r.a
            self._a(r.a & 0x03)
            self._compare(r.a,0x03)
            self._mark(0xC374)
            if not r.p&Z:
                pass
            else:
                self._a(0x01)
                pass
            self._flag(C,False)
            self._add(0x01)
            self._compare(r.a,m[0x04A1])
            self._mark(0xC37E)
            if r.p&Z:
                pass
            else:
                m[0x04A4]=self._nz(m[0x04A4]-1)
                pass
            m[0x04A1]=r.a
            self._a(m[0x04A5])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x03)
            self._compare(r.a,0x03)
            self._mark(0xC391)
            if not r.p&Z:
                pass
            else:
                self._a(0x00)
                m[0x04A5]=r.a
                pass
            self._flag(C,False)
            self._add(0x04)
            self._y(r.a)
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC39C,0xC39F)):return
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xF0)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC344,0xC347)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(0x20)
            m[0x04A4]=r.a
            self._mark(0xC34F)
            self._rts();return

    def cityuiworkers_be72_phase_16(self):
        """$C3A2: cityuiworkers be72 phase 16; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC3A2)
        self._a(m[0x04A1])
        self._mark(0xC3A5)
        if not r.p&Z:
            self._a(0x03)
            m[0x0010]=r.a
            self._a(0x8C)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC3C7,0xC3CA)):return
            self._y(0x05)
            self._x(m[0x04A5])
            if not (yield from self._local_call(self.cityuiworkers_c996,0xC3CF,0xC3D2)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x03)
            self._flag(C,False)
            self._add(0x01)
            m[0x04A1]=r.a
            self._a(m[0x04A3])
            self._a(r.a & 0x0F)
            self._compare(r.a,0x08)
            self._mark(0xC3E7)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x04A3])
                self._a(r.a & 0x10)
                self._mark(0xC3EE)
                if r.p&Z:
                    pass
                else:
                    m[0x04A5]=self._nz(m[0x04A5]-1)
                    pass
                pass
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xD0)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC3A9,0xC3AC)):return
            self._a(0xD1)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xC3AE,0xC3B1)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(0x20)
            m[0x04A5]=r.a
            self._mark(0xC3B9)
            self._rts();return

    def cityuiworkers_be72_phase_17(self):
        """$C3F6: cityuiworkers be72 phase 17; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC3F6)
        self._a(m[0x04A1])
        self._mark(0xC3F9)
        if not r.p&Z:
            self._a(0x2E)
            m[0x0010]=r.a
            self._a(0x8D)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC421,0xC424)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x07)
            self._y(r.a)
            self._a(m[(0xC436+r.y)&65535])
            m[0x04A1]=r.a
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xF5)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC3FD,0xC400)):return
            self._a(0xF7)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xC402,0xC405)):return
            self._a(0xD7)
            m[0x00C1]=r.a
            m[0x00C9]=r.a
            m[0x00D1]=r.a
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC413)
            self._rts();return

    def cityuiworkers_be72_phase_18(self):
        """$C43E: cityuiworkers be72 phase 18; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC43E)
        self._a(m[0x04A1])
        self._mark(0xC441)
        if not r.p&Z:
            self._a(0x37)
            m[0x0010]=r.a
            self._a(0x8E)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC487,0xC48A)):return
            self._a(m[0x04A3])
            self._mark(0xC48D)
            if not r.p&N:
                pass
            else:
                self._a(0x06)
                m[0x04A1]=r.a
                pass
            m[0x04A4]=self._nz(m[0x04A4]+1)
            self._a(m[0x04A4])
            self._mark(0xC49A)
            if r.p&N:
                self._compare(r.a,0x85)
                self._mark(0xC4A3)
                if not r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[0x04A4]=r.a
                    pass
                self._y(0x02)
                pass
            else:
                self._y(0x01)
                pass
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC4AC,0xC4AF)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x01)
            self._flag(C,False)
            self._add(0x03)
            self._y(r.a)
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC4BB,0xC4BE)):return
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xF8)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC445,0xC448)):return
            self._a(0xFA)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xC44A,0xC44D)):return
            self._a(0x00)
            m[0x04A3]=r.a
            m[0x04A4]=r.a
            self._a(0x05)
            m[0x04A1]=r.a
            self._y(0x00)
            self._x(0x00)
            self._a(m[0x0150])
            self._mark(0xC461)
            if not r.p&N:
                pass
            else:
                self._x(0x10)
                pass
            while True:  # natural loop $C465
                self._a(m[(0xC4C1+r.x)&65535])
                m[(0x0380+r.y)&65535]=r.a
                self._x(r.x+1)
                self._y(r.y+1)
                self._compare(r.y,0x10)
                self._mark(0xC46F)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[PPU_JOBS])
                self._a(r.a | 0x04)
                m[PPU_JOBS]=r.a
                self._mark(0xC479)
                self._rts();return

    def cityuiworkers_be72_phase_19(self):
        """$C4E1: cityuiworkers be72 phase 19; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC4E1)
        self._a(m[0x04A1])
        self._mark(0xC4E4)
        if not r.p&Z:
            self._a(0xDD)
            m[0x0010]=r.a
            self._a(0x8E)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC4FC,0xC4FF)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x01)
            self._flag(C,False)
            self._add(0x01)
            m[0x04A1]=r.a
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xE7)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC4E8,0xC4EB)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC4EE)
            self._rts();return

    def cityuiworkers_be72_phase_20(self):
        """$C511: cityuiworkers be72 phase 20; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC511)
        self._a(m[0x04A1])
        self._mark(0xC514)
        if not r.p&Z:
            self._a(0x6B)
            m[0x0010]=r.a
            self._a(0x8F)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC531,0xC534)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x0F)
            self._y(r.a)
            self._a(m[(0xC546+r.y)&65535])
            m[0x04A1]=r.a
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xFB)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC518,0xC51B)):return
            self._a(0xFC)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xC51D,0xC520)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC523)
            self._rts();return

    def cityuiworkers_be72_phase_21(self):
        """$C556: cityuiworkers be72 phase 21; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC556)
        self._a(m[0x04A1])
        self._mark(0xC559)
        if not r.p&Z:
            self._a(0x77)
            m[0x0010]=r.a
            self._a(0x90)
            m[0x0011]=r.a
            self._x(m[0x04A5])
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c996,0xC589,0xC58C)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x03)
            self._compare(r.a,0x03)
            self._mark(0xC596)
            if not r.p&Z:
                pass
            else:
                self._a(0x00)
                m[0x04A3]=r.a
                pass
            self._flag(C,False)
            self._add(0x01)
            m[0x04A1]=r.a
            self._compare(r.a,m[0x04A4])
            self._mark(0xC5A6)
            if r.p&Z:
                pass
            else:
                m[0x04A4]=r.a
                m[0x04A5]=self._nz(m[0x04A5]-1)
                pass
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xEA)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC55D,0xC560)):return
            self._a(0xEB)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xC562,0xC565)):return
            self._a(0xED)
            m[0x00C1]=r.a
            m[0x00C9]=r.a
            m[0x00D1]=r.a
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(0x20)
            m[0x04A5]=r.a
            self._mark(0xC578)
            self._rts();return

    def cityuiworkers_be72_phase_22(self):
        """$C5B1: cityuiworkers be72 phase 22; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC5B1)
        self._a(m[0x04A1])
        self._mark(0xC5B4)
        if not r.p&Z:
            self._a(0x40)
            m[0x0010]=r.a
            self._a(0x91)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC5D1,0xC5D4)):return
            self._y(m[0x04A4])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC5D7,0xC5DA)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x01)
            self._flag(C,False)
            self._add(0x01)
            m[0x04A1]=r.a
            self._a(m[0x04A3])
            self._a(r.a & 0x40)
            self._mark(0xC5ED)
            if r.p&Z:
                pass
            else:
                self._a(0x04)
                m[0x04A4]=r.a
                pass
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xF6)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC5B8,0xC5BB)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(0x03)
            m[0x04A4]=r.a
            self._mark(0xC5C3)
            self._rts();return

    def cityuiworkers_be72_phase_23(self):
        """$C5F7: cityuiworkers be72 phase 23; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC5F7)
        self._a(m[0x04A1])
        self._mark(0xC5FA)
        if not r.p&Z:
            self._a(0xDC)
            m[0x0010]=r.a
            self._a(0x91)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC617,0xC61A)):return
            self._a(m[0x04A1])
            self._flag(C,False)
            self._add(0x02)
            self._y(r.a)
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC621,0xC624)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x01)
            self._flag(C,False)
            self._add(0x01)
            m[0x04A1]=r.a
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xF7)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC5FE,0xC601)):return
            self._a(0xDF)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xC603,0xC606)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC609)
            self._rts();return

    def cityuiworkers_be72_phase_24(self):
        """$C636: cityuiworkers be72 phase 24; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC636)
        self._a(m[0x04A1])
        self._mark(0xC639)
        if not r.p&Z:
            self._a(0xA0)
            m[0x0010]=r.a
            self._a(0x92)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC651,0xC654)):return
            self._a(m[0x04A1])
            self._flag(C,False)
            self._add(0x02)
            self._y(r.a)
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC65B,0xC65E)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,True,rotate=True)
            r.a=self._shift(r.a,True,rotate=True)
            r.a=self._shift(r.a,True,rotate=True)
            r.a=self._shift(r.a,True,rotate=True)
            self._a(r.a & 0x01)
            self._flag(C,False)
            self._add(0x03)
            m[0x04A1]=r.a
            self._y(0x01)
            self._a(m[0x04A3])
            self._compare(r.a,0x60)
            self._mark(0xC674)
            if not r.p&C:
                pass
            else:
                self._y(r.y+1)
                pass
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC677,0xC67A)):return
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xC5)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC63D,0xC640)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC643)
            self._rts();return

    def cityuiworkers_be72_phase_25(self):
        """$C67D: cityuiworkers be72 phase 25; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC67D)
        self._a(m[0x04A1])
        self._mark(0xC680)
        if not r.p&Z:
            self._a(0x42)
            m[0x0010]=r.a
            self._a(0x93)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC6A8,0xC6AB)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x07)
            self._y(r.a)
            self._a(m[(0xC6BE+r.y)&65535])
            m[0x04A1]=r.a
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xF4)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC684,0xC687)):return
            self._a(0xF5)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xC689,0xC68C)):return
            self._a(0xD4)
            m[0x00C1]=r.a
            m[0x00C9]=r.a
            m[0x00D1]=r.a
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC69A)
            self._rts();return

    def cityuiworkers_be72_phase_26(self):
        """$C6C6: cityuiworkers be72 phase 26; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC6C6)
        self._a(m[0x04A1])
        self._mark(0xC6C9)
        if not r.p&Z:
            self._a(0x77)
            m[0x0010]=r.a
            self._a(0x94)
            m[0x0011]=r.a
            self._x(m[0x04A5])
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c996,0xC70D,0xC710)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[0x0000]=r.a
            self._a(r.a & 0x07)
            self._y(r.a)
            self._a(m[(0xC731+r.y)&65535])
            m[0x04A1]=r.a
            self._compare(r.a,m[0x04A4])
            self._mark(0xC726)
            if r.p&Z:
                pass
            else:
                m[0x04A4]=r.a
                m[0x04A5]=self._nz(m[0x04A5]-1)
                pass
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xC1)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC6CD,0xC6D0)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(0x01)
            m[0x04A4]=r.a
            self._a(0x20)
            m[0x04A5]=r.a
            self._y(0x00)
            self._x(0x00)
            self._a(m[0x0150])
            self._mark(0xC6E4)
            if not r.p&N:
                pass
            else:
                self._x(0x13)
                pass
            while True:  # natural loop $C6E8
                self._a(m[(0xC739+r.x)&65535])
                m[(0x0380+r.y)&65535]=r.a
                self._x(r.x+1)
                self._y(r.y+1)
                self._compare(r.y,0x13)
                self._mark(0xC6F2)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[PPU_JOBS])
                self._a(r.a | 0x04)
                m[PPU_JOBS]=r.a
                self._mark(0xC6FC)
                self._rts();return

    def cityuiworkers_be72_phase_27(self):
        """$C75F: cityuiworkers be72 phase 27; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC75F)
        self._a(m[0x04A1])
        self._mark(0xC762)
        if not r.p&Z:
            self._a(0x91)
            m[0x0010]=r.a
            self._a(0x96)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC799,0xC79C)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x03)
            self._compare(r.a,0x03)
            self._mark(0xC7A7)
            if not r.p&Z:
                pass
            else:
                self._a(0x00)
                m[0x04A3]=r.a
                pass
            self._flag(C,False)
            self._add(0x01)
            m[0x04A1]=r.a
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xFC)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC766,0xC769)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._y(0x00)
            self._x(0x00)
            self._a(m[0x0150])
            self._mark(0xC773)
            if not r.p&N:
                pass
            else:
                self._x(0x0D)
                pass
            while True:  # natural loop $C777
                self._a(m[(0xC7B7+r.x)&65535])
                m[(0x0380+r.y)&65535]=r.a
                self._x(r.x+1)
                self._y(r.y+1)
                self._compare(r.y,0x0D)
                self._mark(0xC781)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[PPU_JOBS])
                self._a(r.a | 0x04)
                m[PPU_JOBS]=r.a
                self._mark(0xC78B)
                self._rts();return

    def cityuiworkers_be72_phase_28(self):
        """$C7D1: cityuiworkers be72 phase 28; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC7D1)
        self._a(m[0x04A1])
        self._mark(0xC7D4)
        if not r.p&Z:
            self._a(0x33)
            m[0x0010]=r.a
            self._a(0x97)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC7EC,0xC7EF)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x01)
            self._flag(C,False)
            self._add(0x01)
            m[0x04A1]=r.a
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xC2)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC7D8,0xC7DB)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC7DE)
            self._rts();return

    def cityuiworkers_be72_phase_29(self):
        """$C800: cityuiworkers be72 phase 29; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC800)
        self._a(m[0x04A1])
        self._mark(0xC803)
        if not r.p&Z:
            self._a(0x69)
            m[0x0010]=r.a
            self._a(0x97)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC81B,0xC81E)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x01)
            m[0x04A1]=r.a
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xD1)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC807,0xC80A)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC80D)
            self._rts();return

    def cityuiworkers_be72_phase_30(self):
        """$C830: cityuiworkers be72 phase 30; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC830)
        self._a(m[0x04A1])
        self._mark(0xC833)
        if not r.p&Z:
            self._a(0x1F)
            m[0x0010]=r.a
            self._a(0x98)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC850,0xC853)):return
            self._y(m[0x04A4])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC856,0xC859)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[0x0000]=r.a
            self._a(r.a & 0x01)
            m[0x04A1]=r.a
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._y(0x03)
            self._a(m[0x0000])
            self._a(r.a & 0x07)
            self._compare(r.a,0x07)
            self._mark(0xC873)
            if not r.p&Z:
                pass
            else:
                self._y(0x04)
                pass
            m[0x04A4]=r.y
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xC6)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC837,0xC83A)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(0x03)
            m[0x04A4]=r.a
            self._mark(0xC842)
            self._rts();return

    def cityuiworkers_be72_phase_31(self):
        """$C87D: cityuiworkers be72 phase 31; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC87D)
        self._a(m[0x04A1])
        self._mark(0xC880)
        if not r.p&Z:
            self._a(0x93)
            m[0x0010]=r.a
            self._a(0x98)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC898,0xC89B)):return
            self._a(m[0x04A1])
            self._compare(r.a,0x04)
            self._mark(0xC8A0)
            if r.p&Z:
                pass
            else:
                self._a(m[0x04A3])
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                self._a(r.a & 0x03)
                self._flag(C,False)
                self._add(0x01)
                m[0x04A1]=r.a
                pass
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xBD)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC884,0xC887)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC88A)
            self._rts();return

    def cityuiworkers_be72_phase_32(self):
        """$C8B4: cityuiworkers be72 phase 32; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC8B4)
        self._a(m[0x04A1])
        self._mark(0xC8B7)
        if not r.p&Z:
            self._a(0xDF)
            m[0x0010]=r.a
            self._a(0x99)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC8D4,0xC8D7)):return
            self._a(m[0x04A1])
            self._compare(r.a,0x03)
            self._mark(0xC8DC)
            if r.p&Z:
                pass
            else:
                self._a(m[0x04A3])
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                self._a(r.a & 0x03)
                self._flag(C,False)
                self._add(0x01)
                m[0x04A1]=r.a
                pass
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xB7)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC8BB,0xC8BE)):return
            self._a(0xB7)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xC8C0,0xC8C3)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC8C6)
            self._rts();return

    def cityuiworkers_be72_phase_33(self):
        """$C8F1: cityuiworkers be72 phase 33; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC8F1)
        self._a(m[0x04A1])
        self._mark(0xC8F4)
        if not r.p&Z:
            self._a(0xE4)
            m[0x0010]=r.a
            self._a(0x9A)
            m[0x0011]=r.a
            self._y(m[0x04A1])
            if not (yield from self._local_call(self.cityuiworkers_c994,0xC911,0xC914)):return
            self._a(m[0x04A3])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x01)
            m[0x04A1]=r.a
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._a(m[0x04D0])
            self._compare(r.a,m[0x04CC])
            self._mark(0xC93A)
            if not r.p&C:
                pass
            else:
                self._a(m[0x04A2])
                self._mark(0xC93F)
                if r.p&Z:
                    pass
                else:
                    self._compare(r.a,0x04)
                    self._mark(0xC943)
                    if r.p&Z:
                        pass
                    else:
                        self._compare(r.a,0x08)
                        self._mark(0xC947)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xC949,0xE57F,0xC94C,"call",None)
                            if r.pc!=0xC94C:return  # preserve nonlocal stack return
                            self._a(0x81)
                            yield from self._external(0xC94E,0xE673,0xC951,"call",None)
                            if r.pc!=0xC951:return  # preserve nonlocal stack return
                            pass
                        pass
                    pass
                self._a(0x01)
                m[0x007D]=r.a
                self._a(0x00)
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC95D,0xEE07,0xC962,"far_call",40981)
                if r.pc!=0xC962:return  # preserve nonlocal stack return
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x22)
                m[0x04A2]=r.a
                pass
            self._mark(0xC96C)
            self._rts();return
        else:
            self._a(0xAA)
            if not (yield from self._local_call(self.cityuiworkers_c96d,0xC8F8,0xC8FB)):return
            self._a(0xAB)
            if not (yield from self._local_call(self.cityuiworkers_c98a,0xC8FD,0xC900)):return
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC903)
            self._rts();return

    def cityuiworkers_be72_phase_34(self):
        """$C926: cityuiworkers be72 phase 34; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC926)
        self._a(m[0x0140])
        self._mark(0xC929)
        if not r.p&Z:
            pass
        else:
            self._a(0x00)
            m[0x04A0]=r.a
            m[0x04A2]=r.a
            pass
        self._mark(0xC933)
        self._rts();return

    def cityuiworkers_c96d(self):
        """$C96D: cityuiworkers c96d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC96D)
        m[0x00BF]=r.a
        m[0x00C7]=r.a
        m[0x00CF]=r.a
        self._y(0x0C)
        while True:  # natural loop $C978
            self._a(m[(0x0120+r.y)&65535])
            m[(0x0100+r.y)&65535]=r.a
            self._a(m[(0x0130+r.y)&65535])
            m[(0x0110+r.y)&65535]=r.a
            self._y(r.y+1)
            self._compare(r.y,0x10)
            self._mark(0xC987)
            if not r.p&C:
                continue
            else:
                pass
            self._mark(0xC989)
            self._rts();return

    def cityuiworkers_c98a(self):
        """$C98A: cityuiworkers c98a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC98A)
        m[0x00C0]=r.a
        m[0x00C8]=r.a
        m[0x00D0]=r.a
        self._mark(0xC993)
        self._rts();return

    def cityuiworkers_c994(self):
        """$C994: cityuiworkers c994; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC994)
        self._x(0x20)
        return (yield from self.cityuiworkers_c996())

    def cityuiworkers_c996(self):
        """$C996: cityuiworkers c996; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC996)
        self._y(r.y-1)
        self._a(r.y)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
        m[0x0000]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(0x40,subtract=True)
        m[0x0001]=r.a
        self._a(m[0x0150])
        self._mark(0xC9AB)
        if not r.p&N:
            pass
        else:
            self._a(r.x)
            self._flag(C,False)
            self._add(0x70)
            self._x(r.a)
            pass
        m[0x000C]=r.x
        self._a(0x2F)
        m[0x000A]=r.a
        self._a(0x03)
        m[0x0002]=r.a
        self._mark(0xC9BF)
        yield from self._external(0xC9BF,0xF1AD,None,"tail")
        return

    def cityuiworkers_c9c5_phase_1(self):
        """$C9D0: cityuiworkers c9c5 phase 1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC9D0)
        self._a(0x01)
        m[0x007D]=r.a
        self._y(0x0C)
        self._a(0x0F)
        while True:  # natural loop $C9D9
            m[(0x0100+r.y)&65535]=r.a
            m[(0x0110+r.y)&65535]=r.a
            self._y(r.y+1)
            self._compare(r.y,0x10)
            self._mark(0xC9E2)
            if not r.p&C:
                continue
            else:
                pass
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xC9E7)
            self._rts();return

    def cityuiworkers_c9c5_phase_0(self):
        """$C9E8: cityuiworkers c9c5 phase 0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC9E8)
        self._a(0x40)
        m[0x0000]=r.a
        self._a(0xCC)
        m[0x0001]=r.a
        self._a(m[0x0150])
        self._mark(0xC9F5)
        if not r.p&N:
            pass
        else:
            self._a(m[0x0000])
            self._flag(C,False)
            self._add(0x1C)
            m[0x0000]=r.a
            self._a(m[0x0001])
            self._add(0x00)
            m[0x0001]=r.a
            pass
        self._y(0x00)
        while True:  # natural loop $CA0A
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[(0x0380+r.y)&65535]=r.a
            self._y(r.y+1)
            self._compare(r.y,0x1C)
            self._mark(0xCA12)
            if not r.p&C:
                continue
            else:
                pass
            self._a(0xFF)
            m[(0x0380+r.y)&65535]=r.a
            self._a(m[PPU_JOBS])
            self._a(r.a | 0x04)
            m[PPU_JOBS]=r.a
            self._a(0x78)
            m[0x04D4]=r.a
            self._a(0xCC)
            m[0x04D5]=r.a
            self._x(0x02)
            self._a(m[0x0150])
            self._mark(0xCA30)
            if not r.p&N:
                pass
            else:
                self._x(0x10)
                pass
            m[0x04D2]=r.x
            self._a(0x02)
            m[0x00C4]=r.a
            m[0x00CC]=r.a
            m[0x00D4]=r.a
            m[0x00DC]=r.a
            self._a(0x04)
            m[0x04A3]=r.a
            m[0x04A1]=self._nz(m[0x04A1]+1)
            self._mark(0xCA4D)
            self._rts();return

    def cityuiworkers_c9c5_phase_2(self):
        """CA4E: copy at most five14-tile packets, retaining earlyFF marker."""
        r=self.registers;m=self.memory;self._mark(0xCA4E)
        m[0x4A3]=self._nz(m[0x4A3]-1);self._a(m[0x4A3])
        if r.p&N:return (yield from self.initialize_packet_animation())
        self._a(m[0x4D4]);m[0]=r.a;self._a(m[0x4D5]);m[1]=r.a;self._y(0);self._x(0)
        terminated=False
        while True:
            self._a(14);m[0x380+r.x]=r.a;self._x(r.x+1)
            self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,255)
            if r.p&Z:
                self._x(r.x-1);m[0x380+r.x]=r.a;terminated=True;break
            m[0x380+r.x]=r.a;self._x(r.x+1);self._y(r.y+1)
            self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._flag(C,False);self._add(m[0x4D2]);m[0x380+r.x]=r.a
            self._x(r.x+1);self._y(r.y+1);self._a(0);m[2]=0
            while True:
                self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);m[0x380+r.x]=r.a
                self._x(r.x+1);self._y(r.y+1);m[2]=self._nz(m[2]+1)
                self._a(m[2]);self._compare(r.a,14)
                if r.p&C:break
            self._compare(r.y,80)
            if r.p&C:break
        if not terminated:
            self._a(255);m[0x380+r.x]=r.a
            self._a(m[0]);self._flag(C,False);self._add(80);m[0x4D4]=r.a
            self._a(m[1]);self._add(0);m[0x4D5]=r.a
        self._a(m[0x7E]);self._a(r.a|4);m[0x7E]=r.a;self._rts()

    def initialize_packet_animation(self):
        """$CAC5: initialize packet animation; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCAC5)
        self._a(0x20)
        m[0x04D3]=r.a
        self._x(0xC4)
        self._a(m[0x0150])
        self._mark(0xCACF)
        if not r.p&N:
            pass
        else:
            self._x(0xD2)
            pass
        m[0x04D2]=r.x
        self._x(m[0x04A2])
        m[0x0003]=r.x
        self._a(0x6C)
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0002]=r.a
        yield from self._external(0xCAE9,0xEBE9,0xCAEC,"call",None)
        if r.pc!=0xCAEC:return  # preserve nonlocal stack return
        self._a(0x59)
        self._flag(C,False)
        self._add(m[0x0006])
        m[0x0000]=r.a
        self._a(0xCD)
        self._add(m[0x0007])
        m[0x0001]=r.a
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x00C3]=r.a
        m[0x00CB]=r.a
        m[0x00D3]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x00C2]=r.a
        m[0x00CA]=r.a
        m[0x00D2]=r.a
        self._y(r.y+1)
        self._x(0x0D)
        while True:  # natural loop $CB19
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[(0x0120+r.x)&65535]=r.a
            self._x(r.x+1)
            self._y(r.y+1)
            self._compare(r.y,0x05)
            self._mark(0xCB22)
            if not r.p&C:
                continue
            else:
                pass
            self._x(0x1D)
            while True:  # natural loop $CB26
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[(0x0120+r.x)&65535]=r.a
                self._x(r.x+1)
                self._y(r.y+1)
                self._compare(r.y,0x08)
                self._mark(0xCB2F)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(0x0F)
                m[0x010C]=r.a
                m[0x011C]=r.a
                self._a(r.y)
                self._flag(C,False)
                self._add(m[0x0000])
                m[0x04D4]=r.a
                self._a(0x00)
                self._add(m[0x0001])
                m[0x04D5]=r.a
                self._a(0x01)
                m[0x04A3]=r.a
                m[0x04A1]=self._nz(m[0x04A1]+1)
                self._mark(0xCB51)
                self._rts();return

    def cityuiworkers_c9c5_phase_3(self):
        """CB52: five10-tile rows; source stride10, destination stride32."""
        r=self.registers;m=self.memory;self._mark(0xCB52)
        for src,dst in ((0x4D2,2),(0x4D3,3),(0x4D4,0),(0x4D5,1)):
            self._a(m[src]);m[dst]=r.a
        self._x(0);self._y(0)
        while True:
            self._a(10);m[0x380+r.x]=r.a;self._x(r.x+1)
            self._a(m[3]);m[0x380+r.x]=r.a;self._x(r.x+1)
            self._a(m[2]);m[0x380+r.x]=r.a;self._x(r.x+1);self._y(0)
            while True:
                self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);m[0x380+r.x]=r.a
                self._x(r.x+1);self._y(r.y+1);self._compare(r.y,10)
                if r.p&C:break
            for lo,amount in ((0,10),(2,32)):
                self._a(m[lo]);self._flag(C,False);self._add(amount);m[lo]=r.a
                self._a(m[lo+1]);self._add(0);m[lo+1]=r.a
            self._compare(r.x,65)
            if r.p&C:break
        self._a(255);m[0x380+r.x]=r.a
        for src,dst in ((2,0x4D2),(3,0x4D3),(0,0x4D4),(1,0x4D5)):
            self._a(m[src]);m[dst]=r.a
        return (yield from self.finish_animation_row_batch())

    def finish_animation_row_batch(self):
        """$CBD2: finish animation row batch; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCBD2)
        m[0x04A3]=self._nz(m[0x04A3]-1)
        self._a(m[0x04A3])
        self._mark(0xCBD8)
        if not r.p&N:
            pass
        else:
            self._a(m[0x04A2])
            self._compare(r.a,0x04)
            self._mark(0xCBDF)
            if r.p&Z:
                pass
            else:
                self._compare(r.a,0x05)
                self._mark(0xCBE3)
                if r.p&Z:
                    pass
                else:
                    yield from self._external(0xCBE5,0xE57F,0xCBE8,"call",None)
                    if r.pc!=0xCBE8:return  # preserve nonlocal stack return
                    if not (yield from self._local_call(self.cityuiworkers_cc09,0xCBE8,0xCBEB)):return
                    pass
                pass
            self._a(0x81)
            m[0x04A0]=r.a
            self._a(0xFF)
            m[0x04CC]=r.a
            self._a(0x00)
            m[0x04A1]=r.a
            m[0x04A3]=r.a
            m[0x04D0]=r.a
            pass
        self._a(m[PPU_JOBS])
        self._a(r.a | 0x04)
        m[PPU_JOBS]=r.a
        self._mark(0xCC08)
        self._rts();return

    def cityuiworkers_cc09(self):
        """$CC09: cityuiworkers cc09; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC09)
        self._a(m[0x04D6])
        self._compare(r.a,0x32)
        self._mark(0xCC0E)
        if r.p&Z:
            self._mark(0xCC3D)
            yield from self._external(0xCC3D,0xE67B,None,"tail")
            return
        else:
            self._compare(r.a,0x47)
            self._mark(0xCC12)
            if r.p&Z:
                self._mark(0xCC3D)
                yield from self._external(0xCC3D,0xE67B,None,"tail")
                return
            else:
                self._compare(r.a,0x2E)
                self._mark(0xCC16)
                if r.p&Z:
                    self._mark(0xCC3A)
                    yield from self._external(0xCC3A,0xE68B,None,"tail")
                    return
                else:
                    self._compare(r.a,0x3E)
                    self._mark(0xCC1A)
                    if r.p&Z:
                        self._mark(0xCC3A)
                        yield from self._external(0xCC3A,0xE68B,None,"tail")
                        return
                    else:
                        self._compare(r.a,0x52)
                        self._mark(0xCC1E)
                        if r.p&Z:
                            self._mark(0xCC3A)
                            yield from self._external(0xCC3A,0xE68B,None,"tail")
                            return
                        else:
                            self._compare(r.a,0xA2)
                            self._mark(0xCC22)
                            if r.p&Z:
                                self._mark(0xCC3A)
                                yield from self._external(0xCC3A,0xE68B,None,"tail")
                                return
                            else:
                                self._compare(r.a,0xA6)
                                self._mark(0xCC26)
                                if r.p&Z:
                                    self._mark(0xCC3A)
                                    yield from self._external(0xCC3A,0xE68B,None,"tail")
                                    return
                                else:
                                    self._compare(r.a,0x38)
                                    self._mark(0xCC2A)
                                    if r.p&Z:
                                        self._mark(0xCC37)
                                        yield from self._external(0xCC37,0xE693,None,"tail")
                                        return
                                    else:
                                        self._compare(r.a,0x3B)
                                        self._mark(0xCC2E)
                                        if r.p&Z:
                                            self._mark(0xCC37)
                                            yield from self._external(0xCC37,0xE693,None,"tail")
                                            return
                                        else:
                                            self._compare(r.a,0x9F)
                                            self._mark(0xCC32)
                                            if r.p&Z:
                                                self._mark(0xCC37)
                                                yield from self._external(0xCC37,0xE693,None,"tail")
                                                return
                                            else:
                                                self._mark(0xCC34)
                                                yield from self._external(0xCC34,0xE683,None,"tail")
                                                return

class TitleUIController(UIControlBase):
    PAIR=(10, 11)
    PUBLIC_ENTRIES=(40963,)
    def fields(self):
        m=self.memory
        return dict(global_state=m[0x7A],NMI_scene=m[0x78],title_state=m[0x540],title_phase=m[0x541],
                    title_work_0542=m[0x542],title_index=m[0x543],title_timer=m[0x544],PPU_jobs=m[0x7E])

    def _entry(self,entry):
        if entry==0xA003:return self.title_entry()
        elif entry==0xD717:return self.title_tick()
        elif entry==0xD72A:return self.titleuicontroller_d71d_phase_0()
        elif entry==0xD732:return self.reset_title()
        elif entry==0xD73C:return self.titleuicontroller_d735_phase_0()
        elif entry==0xD74C:return self.titleuicontroller_d735_phase_1()
        elif entry==0xD74F:return self.introduction()
        elif entry==0xD799:return self.titleuicontroller_d784_phase_0()
        elif entry==0xD7BD:return self.titleuicontroller_d784_phase_1()
        elif entry==0xD7EC:return self.titleuicontroller_d784_phase_2()
        elif entry==0xD83B:return self.titleuicontroller_d784_phase_3()
        elif entry==0xD856:return self.titleuicontroller_d784_phase_4()
        elif entry==0xD890:return self.titleuicontroller_d784_phase_5()
        elif entry==0xD8AD:return self.titleuicontroller_d784_phase_6()
        elif entry==0xD8D9:return self.titleuicontroller_d784_phase_7()
        elif entry==0xD8F8:return self.titleuicontroller_d784_phase_8()
        elif entry==0xD99C:return self.title_menu()
        elif entry==0xD9A8:return self.titleuicontroller_d99f_phase_0()
        elif entry==0xD9D0:return self.titleuicontroller_d99f_phase_1()
        elif entry==0xDA1B:return self.titleuicontroller_d99f_phase_2()
        elif entry==0xDA7E:return self.scenario_menu()
        elif entry==0xDA95:return self.titleuicontroller_da84_phase_0()
        elif entry==0xDAA6:return self.titleuicontroller_da84_phase_1()
        elif entry==0xDAFD:return self.titleuicontroller_da84_phase_2()
        elif entry==0xDB2B:return self.titleuicontroller_da84_phase_3()
        elif entry==0xDB7B:return self.titleuicontroller_da84_phase_4()
        elif entry==0xDBC1:return self.titleuicontroller_da84_phase_5()
        elif entry==0xDBF1:return self.titleuicontroller_da84_phase_6()
        elif entry==0xDC2F:return self.titleuicontroller_dc2f()
        elif entry==0xDC97:return self.titleuicontroller_dc97()
        elif entry==0xDCC8:return self.advance_intro_palette()
        elif entry==0xDD0F:return self.intro_palette_group()
        elif entry==0xDD34:return self.update_title_sprites()
        elif entry==0xDD53:return self.titleuicontroller_dd53()
        elif entry==0xDD79:return self.titleuicontroller_dd79()
        elif entry==0xDEAF:return self.titleuicontroller_deaf()
        elif entry==0xDF4C:return self.titleuicontroller_df4c()
        raise ValueError("Entry outside immutable UI procedure catalog")

    def title_entry(self):
        """$A003: title entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA003)
        return (yield from self.title_tick())

    def title_tick(self):
        """$D717: title tick; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD717)
        if not (yield from self._local_call(self.update_title_sprites,0xD717,0xD71A)):return
        self._a(m[UI_STATE])
        self._mark(0xD71D)
        index=self._dispatch(0xD71D,(55082, 55119, 55708, 55934, 55090))
        return (yield from (self.titleuicontroller_d71d_phase_0,self.introduction,self.title_menu,self.scenario_menu,self.reset_title,)[index]())

    def titleuicontroller_d71d_phase_0(self):
        """$D72A: titleuicontroller d71d phase 0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD72A)
        self._y(0x37)
        yield from self._external(0xD72C,0xEE07,0xD731,"far_call",40993)
        if r.pc!=0xD731:return  # preserve nonlocal stack return
        self._mark(0xD731)
        self._rts();return

    def reset_title(self):
        """$D732: reset title; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD732)
        self._a(m[UI_PHASE])
        self._mark(0xD735)
        index=self._dispatch(0xD735,(55100, 55116))
        return (yield from (self.titleuicontroller_d735_phase_0,self.titleuicontroller_d735_phase_1,)[index]())

    def titleuicontroller_d735_phase_0(self):
        """$D73C: titleuicontroller d735 phase 0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD73C)
        self._y(0x00)
        self._a(0x0F)
        while True:  # natural loop $D740
            m[(0x0100+r.y)&65535]=r.a
            self._y(r.y+1)
            self._compare(r.y,0x20)
            self._mark(0xD746)
            if not r.p&C:
                continue
            else:
                pass
            m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
            self._mark(0xD74B)
            self._rts();return

    def titleuicontroller_d735_phase_1(self):
        """$D74C: titleuicontroller d735 phase 1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD74C)
        yield from self._external(0xD74C,0xE000,None,"tail")
        return

    def introduction(self):
        """$D74F: introduction; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD74F)
        m[0x0470]=self._nz(m[0x0470]+1)
        self._mark(0xD752)
        if not r.p&Z:
            pass
        else:
            m[0x0471]=self._nz(m[0x0471]+1)
            pass
        self._a(m[0x0470])
        self._compare(r.a,0x58)
        self._mark(0xD75C)
        if not r.p&Z:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x08)
            self._mark(0xD775)
            if r.p&Z:
                self._a(m[UI_PHASE])
                self._mark(0xD784)
                index=self._dispatch(0xD784,(55193, 55229, 55276, 55355, 55382, 55440, 55469, 55513, 55544))
                return (yield from (self.titleuicontroller_d784_phase_0,self.titleuicontroller_d784_phase_1,self.titleuicontroller_d784_phase_2,self.titleuicontroller_d784_phase_3,self.titleuicontroller_d784_phase_4,self.titleuicontroller_d784_phase_5,self.titleuicontroller_d784_phase_6,self.titleuicontroller_d784_phase_7,self.titleuicontroller_d784_phase_8,)[index]())
            else:
                self._a(m[UI_PHASE])
                self._compare(r.a,0x07)
                self._mark(0xD77C)
                if r.p&Z:
                    self._a(m[UI_PHASE])
                    self._mark(0xD784)
                    index=self._dispatch(0xD784,(55193, 55229, 55276, 55355, 55382, 55440, 55469, 55513, 55544))
                    return (yield from (self.titleuicontroller_d784_phase_0,self.titleuicontroller_d784_phase_1,self.titleuicontroller_d784_phase_2,self.titleuicontroller_d784_phase_3,self.titleuicontroller_d784_phase_4,self.titleuicontroller_d784_phase_5,self.titleuicontroller_d784_phase_6,self.titleuicontroller_d784_phase_7,self.titleuicontroller_d784_phase_8,)[index]())
                else:
                    self._a(0x28)
                    m[0x0121]=r.a
                    self._a(0x19)
                    m[0x0122]=r.a
                    self._a(0x17)
                    m[0x0123]=r.a
                    self._y(0x00)
                    while True:  # natural loop $D91E
                        self._a(m[(0x0120+r.y)&65535])
                        m[(0x0100+r.y)&65535]=r.a
                        self._y(r.y+1)
                        self._compare(r.y,0x20)
                        self._mark(0xD927)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._a(0x0F)
                        m[0x0542]=r.a
                        m[0x0543]=r.a
                        self._a(0x06)
                        m[UI_PHASE]=r.a
                        self._a(0xFF)
                        m[REPEAT_BUTTONS]=r.a
                        self._mark(0xD93B)
                        self._rts();return
        else:
            self._a(m[0x0471])
            self._compare(r.a,0x0B)
            self._mark(0xD763)
            if not r.p&Z:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x08)
                self._mark(0xD775)
                if r.p&Z:
                    self._a(m[UI_PHASE])
                    self._mark(0xD784)
                    index=self._dispatch(0xD784,(55193, 55229, 55276, 55355, 55382, 55440, 55469, 55513, 55544))
                    return (yield from (self.titleuicontroller_d784_phase_0,self.titleuicontroller_d784_phase_1,self.titleuicontroller_d784_phase_2,self.titleuicontroller_d784_phase_3,self.titleuicontroller_d784_phase_4,self.titleuicontroller_d784_phase_5,self.titleuicontroller_d784_phase_6,self.titleuicontroller_d784_phase_7,self.titleuicontroller_d784_phase_8,)[index]())
                else:
                    self._a(m[UI_PHASE])
                    self._compare(r.a,0x07)
                    self._mark(0xD77C)
                    if r.p&Z:
                        self._a(m[UI_PHASE])
                        self._mark(0xD784)
                        index=self._dispatch(0xD784,(55193, 55229, 55276, 55355, 55382, 55440, 55469, 55513, 55544))
                        return (yield from (self.titleuicontroller_d784_phase_0,self.titleuicontroller_d784_phase_1,self.titleuicontroller_d784_phase_2,self.titleuicontroller_d784_phase_3,self.titleuicontroller_d784_phase_4,self.titleuicontroller_d784_phase_5,self.titleuicontroller_d784_phase_6,self.titleuicontroller_d784_phase_7,self.titleuicontroller_d784_phase_8,)[index]())
                    else:
                        self._a(0x28)
                        m[0x0121]=r.a
                        self._a(0x19)
                        m[0x0122]=r.a
                        self._a(0x17)
                        m[0x0123]=r.a
                        self._y(0x00)
                        while True:  # natural loop $D91E
                            self._a(m[(0x0120+r.y)&65535])
                            m[(0x0100+r.y)&65535]=r.a
                            self._y(r.y+1)
                            self._compare(r.y,0x20)
                            self._mark(0xD927)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            self._a(0x0F)
                            m[0x0542]=r.a
                            m[0x0543]=r.a
                            self._a(0x06)
                            m[UI_PHASE]=r.a
                            self._a(0xFF)
                            m[REPEAT_BUTTONS]=r.a
                            self._mark(0xD93B)
                            self._rts();return
            else:
                self._a(0x04)
                m[UI_STATE]=r.a
                self._a(0x00)
                m[UI_PHASE]=r.a
                self._mark(0xD76F)
                self._rts();return

    def titleuicontroller_d784_phase_0(self):
        """$D799: titleuicontroller d784 phase 0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD799)
        m[0x0544]=self._nz(m[0x0544]+1)
        self._a(m[0x0544])
        self._compare(r.a,0x40)
        self._mark(0xD7A1)
        if r.p&Z:
            self._a(0x04)
            m[0x0088]=r.a
            self._a(0x88)
            m[0x0089]=r.a
            self._a(0x00)
            m[REPEAT_BUTTONS]=r.a
            m[0x0543]=r.a
            m[0x0544]=r.a
            m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
            self._mark(0xD7BC)
            self._rts();return
        else:
            self._mark(0xD7A3)
            self._rts();return

    def titleuicontroller_d784_phase_1(self):
        """$D7BD: titleuicontroller d784 phase 1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD7BD)
        if not (yield from self._local_call(self.advance_intro_palette,0xD7BD,0xD7C0)):return
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xD7C3)
        if not r.p&N:
            pass
        else:
            m[0x0543]=self._nz(m[0x0543]+1)
            self._a(m[0x0543])
            self._compare(r.a,0xB8)
            self._mark(0xD7CD)
            if not r.p&Z:
                pass
            else:
                self._a(0x28)
                m[0x0121]=r.a
                self._a(0x19)
                m[0x0122]=r.a
                self._a(0x17)
                m[0x0123]=r.a
                self._a(0x08)
                m[0x0543]=r.a
                m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
                self._a(0x5A)
                yield from self._external(0xD7E8,0xE69B,0xD7EB,"call",None)
                if r.pc!=0xD7EB:return  # preserve nonlocal stack return
                pass
            pass
        self._mark(0xD7EB)
        self._rts();return

    def titleuicontroller_d784_phase_2(self):
        """$D7EC: titleuicontroller d784 phase 2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD7EC)
        self._y(0x21)
        yield from self._external(0xD7EE,0xF25F,0xD7F1,"call",None)
        if r.pc!=0xD7F1:return  # preserve nonlocal stack return
        self._a(m[0x0543])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x000C]=r.a
        self._a(0x00)
        self._flag(C,True)
        self._add(m[0x000C],subtract=True)
        m[0x000A]=r.a
        self._a(m[0x000C])
        r.a=self._shift(r.a,True,rotate=False)
        m[0x000C]=r.a
        self._a(m[0x970C])
        m[0x0000]=r.a
        self._a(m[0x970D])
        m[0x0001]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        yield from self._external(0xD81B,0xF1AD,0xD81E,"call",None)
        if r.pc!=0xD81E:return  # preserve nonlocal stack return
        self._y(0x00)
        while True:  # natural loop $D820
            self._a(m[(0x0200+r.y)&65535])
            self._mark(0xD823)
            if not r.p&N:
                pass
            else:
                self._a(0xF0)
                m[(0x0200+r.y)&65535]=r.a
                pass
            self._y(r.y+1)
            self._y(r.y+1)
            self._y(r.y+1)
            self._y(r.y+1)
            self._compare(r.y,0x4C)
            self._mark(0xD830)
            if not r.p&C:
                continue
            else:
                pass
            m[0x0543]=self._nz(m[0x0543]-1)
            self._mark(0xD835)
            if not r.p&N:
                pass
            else:
                m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
                pass
            self._mark(0xD83A)
            self._rts();return

    def titleuicontroller_d784_phase_3(self):
        """$D83B: titleuicontroller d784 phase 3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD83B)
        self._a(0x00)
        m[REPEAT_BUTTONS]=r.a
        m[0x0543]=r.a
        self._a(0x04)
        m[0x0088]=r.a
        self._a(0x44)
        m[0x0089]=r.a
        self._a(0x07)
        m[0x0542]=r.a
        m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
        self._mark(0xD855)
        self._rts();return

    def titleuicontroller_d784_phase_4(self):
        """$D856: titleuicontroller d784 phase 4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD856)
        if not (yield from self._local_call(self.advance_intro_palette,0xD856,0xD859)):return
        self._a(m[0x0088])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._x(0x00)
        while True:  # natural loop $D861
            self._a(m[(0xD880+r.y)&65535])
            m[(0x0100+r.x)&65535]=r.a
            self._y(r.y+1)
            self._x(r.x+1)
            self._compare(r.x,0x04)
            self._mark(0xD86B)
            if not r.p&C:
                continue
            else:
                pass
            self._a(m[REPEAT_BUTTONS])
            self._mark(0xD870)
            if not r.p&N:
                pass
            else:
                m[0x0543]=self._nz(m[0x0543]+1)
                self._a(m[0x0543])
                self._compare(r.a,0x20)
                self._mark(0xD87A)
                if not r.p&Z:
                    pass
                else:
                    m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
                    pass
                pass
            self._mark(0xD87F)
            self._rts();return

    def titleuicontroller_d784_phase_5(self):
        """$D890: titleuicontroller d784 phase 5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD890)
        self._a(0x00)
        m[REPEAT_BUTTONS]=r.a
        self._a(0x04)
        m[0x0088]=r.a
        self._a(0x33)
        m[0x0089]=r.a
        self._a(0x0F)
        m[0x0542]=r.a
        self._a(0x00)
        m[0x0543]=r.a
        m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
        self._mark(0xD8AC)
        self._rts();return

    def titleuicontroller_d784_phase_6(self):
        """$D8AD: titleuicontroller d784 phase 6; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD8AD)
        if not (yield from self._local_call(self.advance_intro_palette,0xD8AD,0xD8B0)):return
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xD8B3)
        if not r.p&N:
            pass
        else:
            self._y(0x00)
            while True:  # natural loop $D8B7
                self._a(m[(0xD93C+r.y)&65535])
                self._mark(0xD8BA)
                if r.p&Z:
                    pass
                else:
                    m[(0x0380+r.y)&65535]=r.a
                    self._y(r.y+1)
                    continue
                self._a(0xFF)
                m[(0x0380+r.y)&65535]=r.a
                self._a(m[PPU_JOBS])
                self._a(r.a | 0x04)
                m[PPU_JOBS]=r.a
                self._a(0x1F)
                m[0x0542]=r.a
                m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
                self._mark(0xD8D8)
                self._rts();return
        self._mark(0xD8D8)
        self._rts();return

    def titleuicontroller_d784_phase_7(self):
        """$D8D9: titleuicontroller d784 phase 7; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD8D9)
        self._y(0x00)
        while True:  # natural loop $D8DB
            self._a(m[(0xD962+r.y)&65535])
            self._mark(0xD8DE)
            if r.p&Z:
                pass
            else:
                m[(0x0380+r.y)&65535]=r.a
                self._y(r.y+1)
                continue
            self._a(0xFF)
            m[(0x0380+r.y)&65535]=r.a
            self._a(m[PPU_JOBS])
            self._a(r.a | 0x04)
            m[PPU_JOBS]=r.a
            m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
            self._mark(0xD8F7)
            self._rts();return

    def titleuicontroller_d784_phase_8(self):
        """$D8F8: titleuicontroller d784 phase 8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD8F8)
        self._a(m[0x0543])
        self._mark(0xD8FB)
        if not r.p&Z:
            m[UI_STATE]=self._nz(m[UI_STATE]+1)
            self._a(0x00)
            m[UI_PHASE]=r.a
            pass
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x08)
            self._mark(0xD902)
            if r.p&Z:
                pass
            else:
                m[UI_STATE]=self._nz(m[UI_STATE]+1)
                self._a(0x00)
                m[UI_PHASE]=r.a
                pass
            pass
        self._mark(0xD90C)
        self._rts();return

    def title_menu(self):
        """$D99C: title menu; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD99C)
        self._a(m[UI_PHASE])
        self._mark(0xD99F)
        index=self._dispatch(0xD99F,(55720, 55760, 55835))
        return (yield from (self.titleuicontroller_d99f_phase_0,self.titleuicontroller_d99f_phase_1,self.titleuicontroller_d99f_phase_2,)[index]())

    def titleuicontroller_d99f_phase_0(self):
        """$D9A8: titleuicontroller d99f phase 0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD9A8)
        self._y(0x08)
        self._a(0x0F)
        while True:  # natural loop $D9AC
            m[(0x0100+r.y)&65535]=r.a
            self._y(r.y+1)
            self._compare(r.y,0x10)
            self._mark(0xD9B2)
            if not r.p&C:
                continue
            else:
                pass
            m[0x011D]=r.a
            m[0x011E]=r.a
            m[0x011F]=r.a
            self._a(0xC0)
            m[0x0543]=r.a
            self._a(0x21)
            m[0x0544]=r.a
            self._a(0x17)
            m[0x0542]=r.a
            m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
            self._mark(0xD9CF)
            self._rts();return

    def titleuicontroller_d99f_phase_1(self):
        """$D9D0: titleuicontroller d99f phase 1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD9D0)
        self._a(0x40)
        m[0x0380]=r.a
        self._a(m[0x0544])
        m[0x0381]=r.a
        self._a(m[0x0543])
        m[0x0382]=r.a
        self._y(0x00)
        self._a(0x21)
        while True:  # natural loop $D9E5
            m[(0x0383+r.y)&65535]=r.a
            self._y(r.y+1)
            self._compare(r.y,0x40)
            self._mark(0xD9EB)
            if not r.p&C:
                continue
            else:
                pass
            self._a(0xFF)
            m[(0x0383+r.y)&65535]=r.a
            self._a(m[0x0543])
            self._flag(C,False)
            self._add(0x40)
            m[0x0543]=r.a
            self._a(m[0x0544])
            self._add(0x00)
            m[0x0544]=r.a
            self._a(m[0x0543])
            self._compare(r.a,0xC0)
            self._mark(0xDA08)
            if not r.p&Z:
                pass
            else:
                m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
                self._a(0x17)
                m[0x0542]=r.a
                pass
            self._a(m[PPU_JOBS])
            self._a(r.a | 0x04)
            m[PPU_JOBS]=r.a
            self._mark(0xDA1A)
            self._rts();return

    def titleuicontroller_d99f_phase_2(self):
        """$DA1B: titleuicontroller d99f phase 2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDA1B)
        self._y(0x00)
        while True:  # natural loop $DA1D
            self._a(m[(0xDA3F+r.y)&65535])
            self._mark(0xDA20)
            if r.p&Z:
                pass
            else:
                m[(0x0380+r.y)&65535]=r.a
                self._y(r.y+1)
                continue
            self._a(0xFF)
            m[(0x0380+r.y)&65535]=r.a
            self._a(m[PPU_JOBS])
            self._a(r.a | 0x04)
            m[PPU_JOBS]=r.a
            m[UI_STATE]=self._nz(m[UI_STATE]+1)
            self._a(0x00)
            m[UI_PHASE]=r.a
            self._mark(0xDA3E)
            self._rts();return

    def scenario_menu(self):
        """$DA7E: scenario menu; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDA7E)
        yield from self._external(0xDA7E,0xEC67,0xDA81,"call",None)
        if r.pc!=0xDA81:return  # preserve nonlocal stack return
        self._a(m[UI_PHASE])
        self._mark(0xDA84)
        index=self._dispatch(0xDA84,(55957, 55974, 56061, 56107, 56187, 56257, 56305))
        return (yield from (self.titleuicontroller_da84_phase_0,self.titleuicontroller_da84_phase_1,self.titleuicontroller_da84_phase_2,self.titleuicontroller_da84_phase_3,self.titleuicontroller_da84_phase_4,self.titleuicontroller_da84_phase_5,self.titleuicontroller_da84_phase_6,)[index]())

    def titleuicontroller_da84_phase_0(self):
        """$DA95: titleuicontroller da84 phase 0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDA95)
        m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
        self._a(0x00)
        m[0x0424]=r.a
        m[0x0425]=r.a
        self._a(0x00)
        m[0x0545]=r.a
        self._mark(0xDAA5)
        self._rts();return

    def titleuicontroller_da84_phase_1(self):
        """$DAA6: titleuicontroller da84 phase 1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDAA6)
        if not (yield from self._local_call(self.titleuicontroller_dd79,0xDAA6,0xDAA9)):return
        if not (yield from self._local_call(self.titleuicontroller_df4c,0xDAA9,0xDAAC)):return
        self._a(0xD4)
        m[0x0010]=r.a
        self._a(0xDB)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xDABB,0xED19,0xDABE,"call",None)
        if r.pc!=0xDABE:return  # preserve nonlocal stack return
        self._a(0xD8)
        m[0x0010]=r.a
        self._a(0xDB)
        m[0x0011]=r.a
        self._a(0xDE)
        m[0x0000]=r.a
        self._a(0xDB)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xDAD5,0xEDF5,0xDAD8,"call",None)
        if r.pc!=0xDAD8:return  # preserve nonlocal stack return
        self._a(m[NEW_BUTTONS])
        self._a(r.a & 0x08)
        self._mark(0xDADD)
        if r.p&Z:
            self._mark(0xDAFC)
            self._rts();return
        else:
            self._a(m[0x0012])
            m[0x0543]=r.a
            self._compare(r.a,0x02)
            self._mark(0xDAE7)
            if not r.p&Z:
                m[0x6F43]=r.a
                self._a(0x03)
                m[UI_PHASE]=r.a
                self._mark(0xDAFC)
                self._rts();return
            else:
                if not (yield from self._local_call(self.titleuicontroller_dc2f,0xDAE9,0xDAEC)):return
                self._mark(0xDAEC)
                if not r.p&C:
                    self._mark(0xDAFC)
                    self._rts();return
                else:
                    m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
                    self._mark(0xDAF1)
                    yield from self._external(0xDAF1,0xECEE,None,"tail")
                    return

    def titleuicontroller_da84_phase_2(self):
        """$DAFD: titleuicontroller da84 phase 2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDAFD)
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xDB00)
        if not r.p&N:
            self._mark(0xDAFC)
            self._rts();return
        else:
            if not (yield from self._local_call(self.titleuicontroller_dc97,0xDB02,0xDB05)):return
            self._a(0x00)
            m[UI_PHASE]=r.a
            self._a(0x01)
            m[GLOBAL]=r.a
            self._a(0x0D)
            m[0x0400]=r.a
            self._a(0x03)
            m[0x0401]=r.a
            self._a(m[0x6F03])
            r.a=self._shift(r.a,True,rotate=False)
            self._y(r.a)
            self._a(m[(0xDBE3+r.y)&65535])
            m[0x00EE]=r.a
            self._a(m[(0xDBE4+r.y)&65535])
            m[0x00EF]=r.a
            self._mark(0xDB2A)
            self._rts();return

    def titleuicontroller_da84_phase_3(self):
        """$DB2B: titleuicontroller da84 phase 3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDB2B)
        self._y(0x00)
        while True:  # natural loop $DB2D
            self._a(m[(0xDB4F+r.y)&65535])
            m[(0x0380+r.y)&65535]=r.a
            self._compare(r.a,0xFF)
            self._mark(0xDB35)
            if r.p&Z:
                pass
            else:
                self._y(r.y+1)
                continue
            self._a(0x00)
            m[0x0424]=r.a
            m[0x0425]=r.a
            m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
            self._a(m[PPU_JOBS])
            self._a(r.a | 0x04)
            m[PPU_JOBS]=r.a
            self._mark(0xDB4E)
            self._rts();return

    def titleuicontroller_da84_phase_4(self):
        """$DB7B: titleuicontroller da84 phase 4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDB7B)
        self._a(0xD4)
        m[0x0010]=r.a
        self._a(0xDB)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xDB8A,0xED19,0xDB8D,"call",None)
        if r.pc!=0xDB8D:return  # preserve nonlocal stack return
        self._a(0xBB)
        m[0x0010]=r.a
        self._a(0xDB)
        m[0x0011]=r.a
        self._a(0xDE)
        m[0x0000]=r.a
        self._a(0xDB)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xDBA4,0xEDF5,0xDBA7,"call",None)
        if r.pc!=0xDBA7:return  # preserve nonlocal stack return
        self._a(m[NEW_BUTTONS])
        self._a(r.a & 0x08)
        self._mark(0xDBAC)
        if r.p&Z:
            pass
        else:
            self._a(m[0x0012])
            m[0x0544]=r.a
            yield from self._external(0xDBB4,0xECEE,0xDBB7,"call",None)
            if r.pc!=0xDBB7:return  # preserve nonlocal stack return
            m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
            pass
        self._mark(0xDBBA)
        self._rts();return

    def titleuicontroller_da84_phase_5(self):
        """$DBC1: titleuicontroller da84 phase 5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDBC1)
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xDBC4)
        if not r.p&N:
            self._mark(0xDBBA)
            self._rts();return
        else:
            self._a(0x00)
            m[UI_STATE]=r.a
            m[UI_PHASE]=r.a
            self._a(0x0B)
            m[GLOBAL]=r.a
            self._mark(0xDBD3)
            self._rts();return

    def titleuicontroller_da84_phase_6(self):
        """$DBF1: titleuicontroller da84 phase 6; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDBF1)
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xDBF4)
        if not r.p&N:
            pass
        else:
            self._a(0x00)
            m[UI_STATE]=r.a
            self._a(0x01)
            m[UI_PHASE]=r.a
            self._a(0x0D)
            m[GLOBAL]=r.a
            self._a(0x00)
            self._y(r.a)
            while True:  # natural loop $DC08
                m[(0x042C+r.y)&65535]=r.a
                self._y(r.y+1)
                self._compare(r.y,0x40)
                self._mark(0xDC0E)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(0xDE)
                m[0x042C]=r.a
                self._a(0xC8)
                m[0x042F]=r.a
                self._a(0x01)
                m[0x0432]=r.a
                self._a(0x64)
                m[0x0435]=r.a
                self._a(0x0B)
                m[0x044C]=r.a
                self._a(0x03)
                m[0x044F]=r.a
                self._mark(0xDC2E)
                self._rts();return
        self._mark(0xDC2E)
        self._rts();return

    def titleuicontroller_dc2f(self):
        """$DC2F: titleuicontroller dc2f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDC2F)
        self._a(m[0x7FFC])
        self._compare(r.a,0x49)
        self._mark(0xDC34)
        if not r.p&Z:
            self._flag(C,False)
            self._mark(0xDC96)
            self._rts();return
        else:
            self._a(m[0x7FFD])
            self._compare(r.a,0x44)
            self._mark(0xDC3B)
            if not r.p&Z:
                self._flag(C,False)
                self._mark(0xDC96)
                self._rts();return
            else:
                self._a(0x00)
                m[0x0000]=r.a
                m[0x0002]=r.a
                m[0x0003]=r.a
                self._a(0x70)
                m[0x0001]=r.a
                self._y(0x00)
                while True:  # natural loop $DC4F
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._flag(C,False)
                    self._add(m[0x0002])
                    m[0x0002]=r.a
                    self._a(m[0x0003])
                    self._add(0x00)
                    m[0x0003]=r.a
                    self._y(r.y+1)
                    self._mark(0xDC61)
                    if not r.p&Z:
                        continue
                    else:
                        pass
                    m[0x0001]=self._nz(m[0x0001]+1)
                    self._a(m[0x0001])
                    self._compare(r.a,0x7F)
                    self._mark(0xDC6B)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    while True:  # natural loop $DC6D
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._flag(C,False)
                        self._add(m[0x0002])
                        m[0x0002]=r.a
                        self._a(m[0x0003])
                        self._add(0x00)
                        m[0x0003]=r.a
                        self._y(r.y+1)
                        self._compare(r.y,0xFE)
                        self._mark(0xDC81)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._a(m[0x7FFE])
                        self._compare(r.a,m[0x0002])
                        self._mark(0xDC89)
                        if not r.p&Z:
                            self._flag(C,False)
                            self._mark(0xDC96)
                            self._rts();return
                        else:
                            self._a(m[0x7FFF])
                            self._compare(r.a,m[0x0003])
                            self._mark(0xDC91)
                            if not r.p&Z:
                                self._flag(C,False)
                                self._mark(0xDC96)
                                self._rts();return
                            else:
                                self._flag(C,True)
                                self._mark(0xDC94)
                                self._rts();return

    def titleuicontroller_dc97(self):
        """$DC97: titleuicontroller dc97; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDC97)
        self._a(0x4C)
        m[0x00A5]=r.a
        m[0xF800]=r.a
        self._a(0x00)
        m[0x0000]=r.a
        m[0x0002]=r.a
        self._a(0x70)
        m[0x0001]=r.a
        self._a(0x60)
        m[0x0003]=r.a
        self._y(0x00)
        while True:  # natural loop $DCB3
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[((m[0x02]|m[0x03]<<8)+r.y)&65535]=r.a
            self._y(r.y+1)
            self._mark(0xDCB8)
            if not r.p&Z:
                continue
            else:
                pass
            m[0x0003]=self._nz(m[0x0003]+1)
            m[0x0001]=self._nz(m[0x0001]+1)
            self._a(m[0x0001])
            self._compare(r.a,0x80)
            self._mark(0xDCC5)
            if not r.p&C:
                continue
            else:
                pass
            self._mark(0xDCC7)
            self._rts();return

    def advance_intro_palette(self):
        """$DCC8: advance intro palette; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDCC8)
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xDCCB)
        if r.p&N:
            pass
        else:
            m[0x008A]=self._nz(m[0x008A]-1)
            self._mark(0xDCD0)
            if not r.p&N:
                pass
            else:
                self._a(0x04)
                m[0x008A]=r.a
                m[0x0088]=self._nz(m[0x0088]-1)
                self._mark(0xDCDA)
                if not r.p&Z:
                    pass
                else:
                    self._a(0xFF)
                    m[REPEAT_BUTTONS]=r.a
                    pass
                self._a(0x00)
                m[0x0000]=r.a
                self._a(0x01)
                m[0x0001]=r.a
                self._a(0x20)
                m[0x0002]=r.a
                self._a(0x01)
                m[0x0003]=r.a
                self._a(m[0x0089])
                m[0x0010]=r.a
                self._y(0x00)
                while True:  # natural loop $DCFD
                    self._a(m[0x0010])
                    r.a=self._shift(r.a,True,rotate=False)
                    m[0x0010]=r.a
                    self._mark(0xDD04)
                    if not r.p&C:
                        pass
                    else:
                        if not (yield from self._local_call(self.intro_palette_group,0xDD06,0xDD09)):return
                        pass
                    self._y(r.y+1)
                    self._compare(r.y,0x08)
                    self._mark(0xDD0C)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    self._mark(0xDD0E)
                    self._rts();return
            pass
        self._mark(0xDD0E)
        self._rts();return

    def intro_palette_group(self):
        """DD0F: four-color palette group, subtract16 repeatedly then clamp0F."""
        if False:yield None
        r=self.registers;m=self.memory;self._mark(0xDD0F)
        self._a(r.y);self._push(r.a)
        r.a=self._shift(r.a,True);r.a=self._shift(r.a,True);self._y(r.a)
        self._flag(C,False);self._add(4);m[0x11]=r.a
        while True:
            self._x(m[0x88]);self._a(m[((m[2]|m[3]<<8)+r.y)&65535])
            while True:
                self._x(r.x-1)
                if r.p&N:break
                self._flag(C,True);self._add(16,subtract=True)
                if r.p&N:self._a(15);break
            m[((m[0]|m[1]<<8)+r.y)&65535]=r.a
            self._y(r.y+1);self._compare(r.y,m[0x11])
            if r.p&C:break
        self._a(self._pop());self._y(r.a);self._rts()

    def update_title_sprites(self):
        """$DD34: update title sprites; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDD34)
        self._y(0x21)
        yield from self._external(0xDD36,0xF25F,0xDD39,"call",None)
        if r.pc!=0xDD39:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[0x0542])
        m[0x0012]=r.a
        while True:  # natural loop $DD41
            self._a(m[0x0012])
            r.a=self._shift(r.a,False,rotate=False)
            m[0x0012]=r.a
            self._mark(0xDD48)
            if not r.p&C:
                pass
            else:
                if not (yield from self._local_call(self.titleuicontroller_dd53,0xDD4A,0xDD4D)):return
                pass
            self._y(r.y+1)
            self._compare(r.y,0x05)
            self._mark(0xDD50)
            if not r.p&C:
                continue
            else:
                pass
            self._mark(0xDD52)
            self._rts();return

    def titleuicontroller_dd53(self):
        """$DD53: titleuicontroller dd53; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDD53)
        self._a(r.y)
        self._push(r.a)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0x970C+r.y)&65535])
        m[0x0000]=r.a
        self._y(r.y+1)
        self._a(m[(0x970C+r.y)&65535])
        m[0x0001]=r.a
        self._a(0x00)
        m[0x000C]=r.a
        self._a(0x00)
        m[0x000A]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        yield from self._external(0xDD73,0xF1AD,0xDD76,"call",None)
        if r.pc!=0xDD76:return  # preserve nonlocal stack return
        self._a(self._pop())
        self._y(r.a)
        self._mark(0xDD78)
        self._rts();return

    def titleuicontroller_dd79(self):
        """$DD79: titleuicontroller dd79; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDD79)
        self._a(m[0x0546])
        self._mark(0xDD7C)
        if r.p&N:
            if not (yield from self._local_call(self.titleuicontroller_deaf,0xDDC7,0xDDCA)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xDDCF)
            if r.p&Z:
                pass
            else:
                self._a(m[0x0083])
                self._a(r.a & 0x01)
                self._mark(0xDDD6)
                if r.p&Z:
                    pass
                else:
                    yield from self._external(0xDDD8,0xE57F,0xDDDB,"call",None)
                    if r.pc!=0xDDDB:return  # preserve nonlocal stack return
                    pass
                self._a(m[0x0545])
                r.a=self._shift(r.a,True,rotate=False)
                self._y(r.a)
                self._a(m[(0xDE5F+r.y)&65535])
                self._compare(r.a,0x02)
                self._mark(0xDDE5)
                if r.p&Z:
                    self._a(m[(0xDE60+r.y)&65535])
                    yield from self._external(0xDE07,0xE69B,0xDE0A,"call",None)
                    if r.pc!=0xDE0A:return  # preserve nonlocal stack return
                    pass
                else:
                    self._compare(r.a,0x03)
                    self._mark(0xDDE9)
                    if r.p&Z:
                        self._a(m[(0xDE60+r.y)&65535])
                        yield from self._external(0xDE10,0xE693,0xDE13,"call",None)
                        if r.pc!=0xDE13:return  # preserve nonlocal stack return
                        pass
                    else:
                        self._compare(r.a,0x04)
                        self._mark(0xDDED)
                        if r.p&Z:
                            self._a(m[(0xDE60+r.y)&65535])
                            yield from self._external(0xDE19,0xE68B,0xDE1C,"call",None)
                            if r.pc!=0xDE1C:return  # preserve nonlocal stack return
                            pass
                        else:
                            self._compare(r.a,0x05)
                            self._mark(0xDDF1)
                            if r.p&Z:
                                self._a(m[(0xDE60+r.y)&65535])
                                yield from self._external(0xDE22,0xE683,0xDE25,"call",None)
                                if r.pc!=0xDE25:return  # preserve nonlocal stack return
                                pass
                            else:
                                self._compare(r.a,0x06)
                                self._mark(0xDDF5)
                                if r.p&Z:
                                    self._a(m[(0xDE60+r.y)&65535])
                                    yield from self._external(0xDE2B,0xE67B,0xDE2E,"call",None)
                                    if r.pc!=0xDE2E:return  # preserve nonlocal stack return
                                    pass
                                else:
                                    self._compare(r.a,0x07)
                                    self._mark(0xDDF9)
                                    if r.p&Z:
                                        self._a(m[(0xDE60+r.y)&65535])
                                        yield from self._external(0xDE34,0xE673,0xDE37,"call",None)
                                        if r.pc!=0xDE37:return  # preserve nonlocal stack return
                                        pass
                                    else:
                                        self._a(m[(0xDE60+r.y)&65535])
                                        yield from self._external(0xDDFE,0xE609,0xDE01,"call",None)
                                        if r.pc!=0xDE01:return  # preserve nonlocal stack return
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    pass
                pass
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x80)
            self._mark(0xDE3C)
            if r.p&Z:
                pass
            else:
                m[0x0545]=self._nz(m[0x0545]+1)
                self._a(m[0x0545])
                self._compare(r.a,0x28)
                self._mark(0xDE46)
                if not r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[0x0545]=r.a
                    pass
                pass
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x40)
            self._mark(0xDE52)
            if r.p&Z:
                pass
            else:
                m[0x0545]=self._nz(m[0x0545]-1)
                self._mark(0xDE57)
                if not r.p&N:
                    pass
                else:
                    self._a(0x27)
                    m[0x0545]=r.a
                    pass
                pass
            self._mark(0xDE5E)
            self._rts();return
        else:
            self._a(m[0x0083])
            self._a(r.a & 0x01)
            self._mark(0xDD83)
            if not r.p&Z:
                self._a(m[0x0546])
                self._mark(0xDD8E)
                if r.p&Z:
                    self._a(m[NEW_BUTTONS])
                    self._a(r.a & 0x10)
                    self._mark(0xDDA1)
                    if r.p&Z:
                        pass
                    else:
                        self._mark(0xDDA3)
                        if not r.p&Z:
                            m[0x0546]=self._nz(m[0x0546]+1)
                            pass
                        else:
                            self._a(m[NEW_BUTTONS])
                            self._a(r.a & 0x20)
                            self._mark(0xDDAA)
                            if r.p&Z:
                                pass
                            else:
                                self._mark(0xDDAC)
                                if not r.p&Z:
                                    m[0x0546]=self._nz(m[0x0546]+1)
                                    pass
                                else:
                                    self._a(m[NEW_BUTTONS])
                                    self._a(r.a & 0x40)
                                    self._mark(0xDDB3)
                                    if r.p&Z:
                                        pass
                                    else:
                                        self._mark(0xDDB5)
                                        if not r.p&Z:
                                            m[0x0546]=self._nz(m[0x0546]+1)
                                            pass
                                        else:
                                            self._a(m[NEW_BUTTONS])
                                            self._a(r.a & 0x80)
                                            self._mark(0xDDBC)
                                            if r.p&Z:
                                                pass
                                            else:
                                                self._a(0x80)
                                                m[0x0546]=r.a
                                                m[0x0546]=self._nz(m[0x0546]+1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    pass
                else:
                    self._compare(r.a,0x01)
                    self._mark(0xDD92)
                    if r.p&Z:
                        self._a(m[NEW_BUTTONS])
                        self._a(r.a & 0x20)
                        self._mark(0xDDAA)
                        if r.p&Z:
                            pass
                        else:
                            self._mark(0xDDAC)
                            if not r.p&Z:
                                m[0x0546]=self._nz(m[0x0546]+1)
                                pass
                            else:
                                self._a(m[NEW_BUTTONS])
                                self._a(r.a & 0x40)
                                self._mark(0xDDB3)
                                if r.p&Z:
                                    pass
                                else:
                                    self._mark(0xDDB5)
                                    if not r.p&Z:
                                        m[0x0546]=self._nz(m[0x0546]+1)
                                        pass
                                    else:
                                        self._a(m[NEW_BUTTONS])
                                        self._a(r.a & 0x80)
                                        self._mark(0xDDBC)
                                        if r.p&Z:
                                            pass
                                        else:
                                            self._a(0x80)
                                            m[0x0546]=r.a
                                            m[0x0546]=self._nz(m[0x0546]+1)
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    else:
                        self._compare(r.a,0x02)
                        self._mark(0xDD96)
                        if r.p&Z:
                            self._a(m[NEW_BUTTONS])
                            self._a(r.a & 0x40)
                            self._mark(0xDDB3)
                            if r.p&Z:
                                pass
                            else:
                                self._mark(0xDDB5)
                                if not r.p&Z:
                                    m[0x0546]=self._nz(m[0x0546]+1)
                                    pass
                                else:
                                    self._a(m[NEW_BUTTONS])
                                    self._a(r.a & 0x80)
                                    self._mark(0xDDBC)
                                    if r.p&Z:
                                        pass
                                    else:
                                        self._a(0x80)
                                        m[0x0546]=r.a
                                        m[0x0546]=self._nz(m[0x0546]+1)
                                        pass
                                    pass
                                pass
                            pass
                        else:
                            self._compare(r.a,0x03)
                            self._mark(0xDD9A)
                            if r.p&Z:
                                self._a(m[NEW_BUTTONS])
                                self._a(r.a & 0x80)
                                self._mark(0xDDBC)
                                if r.p&Z:
                                    pass
                                else:
                                    self._a(0x80)
                                    m[0x0546]=r.a
                                    m[0x0546]=self._nz(m[0x0546]+1)
                                    pass
                                pass
                            else:
                                self._a(m[NEW_BUTTONS])
                                self._a(r.a & 0x10)
                                self._mark(0xDDA1)
                                if r.p&Z:
                                    pass
                                else:
                                    self._mark(0xDDA3)
                                    if not r.p&Z:
                                        m[0x0546]=self._nz(m[0x0546]+1)
                                        pass
                                    else:
                                        self._a(m[NEW_BUTTONS])
                                        self._a(r.a & 0x20)
                                        self._mark(0xDDAA)
                                        if r.p&Z:
                                            pass
                                        else:
                                            self._mark(0xDDAC)
                                            if not r.p&Z:
                                                m[0x0546]=self._nz(m[0x0546]+1)
                                                pass
                                            else:
                                                self._a(m[NEW_BUTTONS])
                                                self._a(r.a & 0x40)
                                                self._mark(0xDDB3)
                                                if r.p&Z:
                                                    pass
                                                else:
                                                    self._mark(0xDDB5)
                                                    if not r.p&Z:
                                                        m[0x0546]=self._nz(m[0x0546]+1)
                                                        pass
                                                    else:
                                                        self._a(m[NEW_BUTTONS])
                                                        self._a(r.a & 0x80)
                                                        self._mark(0xDDBC)
                                                        if r.p&Z:
                                                            pass
                                                        else:
                                                            self._a(0x80)
                                                            m[0x0546]=r.a
                                                            m[0x0546]=self._nz(m[0x0546]+1)
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    pass
                self._mark(0xDDC6)
                self._rts();return
            else:
                self._a(0x00)
                m[0x0546]=r.a
                self._mark(0xDD8A)
                self._rts();return

    def titleuicontroller_deaf(self):
        """$DEAF: titleuicontroller deaf; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDEAF)
        self._a(0xA2)
        m[0x00D8]=r.a
        self._a(0xA5)
        m[0x00D9]=r.a
        self._x(m[0x007C])
        self._a(0x90)
        m[(0x0200+r.x)&65535]=r.a
        self._a(0x02)
        m[(0x0202+r.x)&65535]=r.a
        self._a(0xBC)
        m[(0x0203+r.x)&65535]=r.a
        self._a(0x90)
        m[(0x0204+r.x)&65535]=r.a
        self._a(0x02)
        m[(0x0206+r.x)&65535]=r.a
        self._a(0xC4)
        m[(0x0207+r.x)&65535]=r.a
        self._a(m[0x0545])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._y(r.a)
        self._a(m[(0xDF3C+r.y)&65535])
        m[(0x0201+r.x)&65535]=r.a
        self._a(m[0x0545])
        self._a(r.a & 0x0F)
        self._y(r.a)
        self._a(m[(0xDF3C+r.y)&65535])
        m[(0x0205+r.x)&65535]=r.a
        self._a(r.x)
        self._flag(C,False)
        self._add(0x08)
        m[0x007C]=r.a
        self._a(0x17)
        m[0x0000]=r.a
        self._a(0xDF)
        m[0x0001]=r.a
        self._a(0xB0)
        m[0x000C]=r.a
        self._a(0x78)
        m[0x000A]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        self._mark(0xDF14)
        yield from self._external(0xDF14,0xF1AD,None,"tail")
        return

    def titleuicontroller_df4c(self):
        """$DF4C: titleuicontroller df4c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDF4C)
        self._y(m[0x0547])
        self._a(m[(0xDF7F+r.y)&65535])
        self._mark(0xDF52)
        if not r.p&N:
            self._a(m[0x0083])
            self._y(m[0x0547])
            self._a(r.a & m[(0xDF7F+r.y)&65535])
            self._mark(0xDF6B)
            if not r.p&Z:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & m[(0xDF88+r.y)&65535])
                self._mark(0xDF79)
                if r.p&Z:
                    pass
                else:
                    m[0x0547]=self._nz(m[0x0547]+1)
                    pass
                self._mark(0xDF7E)
                self._rts();return
            else:
                self._a(0x00)
                m[0x0547]=r.a
                self._mark(0xDF72)
                self._rts();return
        else:
            yield from self._external(0xDF54,0xECEE,0xDF57,"call",None)
            if r.pc!=0xDF57:return  # preserve nonlocal stack return
            self._a(0x06)
            m[UI_PHASE]=r.a
            self._a(0x62)
            yield from self._external(0xDF5E,0xE693,0xDF61,"call",None)
            if r.pc!=0xDF61:return  # preserve nonlocal stack return
            self._mark(0xDF61)
            self._rts();return

class RulerSelectionUIController(UIControlBase):
    PAIR=(8, 9)
    PUBLIC_ENTRIES=(40996,)
    def fields(self):
        m=self.memory
        return dict(global_state=m[0x7A],NMI_scene=m[0x78],ruler_state=m[0x540],ruler_phase=m[0x541],
                    ruler_cursor=m[0x46C],inspected_officer=m[0x46D],players_requested=m[0x6F43],PPU_jobs=m[0x7E])

    def _entry(self,entry):
        if entry==0xA024:return self.ruler_selection_entry()
        elif entry==0xD70F:return self.ruler_selection_tick()
        elif entry==0xD723:return self.ruler_selection()
        elif entry==0xD73A:return self.initialize_ruler_selection()
        elif entry==0xD778:return self.acknowledge_first_prompt()
        elif entry==0xD7B0:return self.select_first_ruler()
        elif entry==0xD80C:return self.acknowledge_second_prompt()
        elif entry==0xD844:return self.select_second_ruler()
        elif entry==0xD8A0:return self.inspect_selected_ruler()
        elif entry==0xD8E4:return self.confirm_rulers_and_start()
        elif entry==0xD906:return self.ruler_menu_and_details()
        elif entry==0xD97A:return self.initialize_seven_ruler_records()
        elif entry==0xDA48:return self.rulerselectionuicontroller_da48()
        elif entry==0xDAD9:return self.blink_prompt_marker()
        elif entry==0xDAFE:return self.text_idle()
        elif entry==0xDB10:return self.track_first_input_sequence()
        elif entry==0xDB62:return self.track_second_input_sequence()
        elif entry==0xDBB4:return self.track_third_input_sequence()
        elif entry==0xDBFF:return self.track_fourth_input_sequence()
        elif entry==0xDC4A:return self.apply_selection_option_bits()
        elif entry==0xDC9C:return self.install_option_profile()
        raise ValueError("Entry outside immutable UI procedure catalog")

    def ruler_selection_entry(self):
        """$A024: ruler selection entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA024)
        return (yield from self.ruler_selection_tick())

    def ruler_selection_tick(self):
        """$D70F: ruler selection tick; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD70F)
        if not (yield from self._local_call(self.track_first_input_sequence,0xD70F,0xD712)):return
        if not (yield from self._local_call(self.track_second_input_sequence,0xD712,0xD715)):return
        if not (yield from self._local_call(self.track_third_input_sequence,0xD715,0xD718)):return
        if not (yield from self._local_call(self.track_fourth_input_sequence,0xD718,0xD71B)):return
        self._a(m[UI_STATE])
        self._mark(0xD71E)
        index=self._dispatch(0xD71E,(55075,))
        return (yield from (self.ruler_selection,)[index]())

    def ruler_selection(self):
        """$D723: ruler selection; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD723)
        if not (yield from self._local_call(self.rulerselectionuicontroller_da48,0xD723,0xD726)):return
        self._a(m[UI_PHASE])
        self._mark(0xD729)
        index=self._dispatch(0xD729,(55098, 55160, 55216, 55308, 55364, 55456, 55524))
        return (yield from (self.initialize_ruler_selection,self.acknowledge_first_prompt,self.select_first_ruler,self.acknowledge_second_prompt,self.select_second_ruler,self.inspect_selected_ruler,self.confirm_rulers_and_start,)[index]())

    def initialize_ruler_selection(self):
        """$D73A: initialize ruler selection; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD73A)
        if not (yield from self._local_call(self.initialize_seven_ruler_records,0xD73A,0xD73D)):return
        self._a(0x00)
        m[0x0545]=r.a
        m[0x0546]=r.a
        m[0x0547]=r.a
        m[0x0548]=r.a
        m[0x0549]=r.a
        self._a(m[0x0543])
        m[0x6F43]=r.a
        self._a(m[0x0544])
        m[0x6F02]=r.a
        self._a(0x00)
        m[0x6F44]=r.a
        m[0x00A4]=r.a
        m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
        self._a(0x01)
        m[0x042C]=r.a
        self._a(0x00)
        m[0x042D]=r.a
        m[0x042E]=r.a
        self._a(0xDA)
        self._mark(0xD774)
        yield from self._external(0xD774,0xF28B,None,"tail")
        return

    def acknowledge_first_prompt(self):
        """$D778: acknowledge first prompt; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD778)
        if not (yield from self._local_call(self.text_idle,0xD778,0xD77B)):return
        self._mark(0xD77B)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.blink_prompt_marker,0xD77D,0xD780)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xD785)
            if r.p&Z:
                pass
            else:
                m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
                self._a(0x00)
                m[0x0424]=r.a
                m[0x0425]=r.a
                m[0x040C]=r.a
                m[0x040D]=r.a
                m[0x046C]=r.a
                self._a(0xDE)
                m[0x0410]=r.a
                self._a(0x00)
                m[0x0098]=r.a
                self._a(0x01)
                m[0x0097]=r.a
                self._a(0x06)
                m[0x00BB]=r.a
                pass
            pass
        self._mark(0xD7AF)
        self._rts();return

    def select_first_ruler(self):
        """$D7B0: select first ruler; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD7B0)
        if not (yield from self._local_call(self.ruler_menu_and_details,0xD7B0,0xD7B3)):return
        self._mark(0xD7B3)
        if not r.p&C:
            self._mark(0xD7E2)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xD7BA)
            if r.p&Z:
                self._mark(0xD7E2)
                self._rts();return
            else:
                self._a(m[0x0083])
                self._a(r.a & 0x08)
                self._mark(0xD7C1)
                if r.p&Z:
                    self._y(m[0x0012])
                    self._a(m[(0xDA07+r.y)&65535])
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    self._y(r.a)
                    self._a(0x00)
                    m[(0x6F0A+r.y)&65535]=r.a
                    self._a(m[0x6F43])
                    self._mark(0xD7D8)
                    if not r.p&Z:
                        m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
                        self._a(0x01)
                        m[0x6F44]=r.a
                        self._a(0xA0)
                        m[0x0098]=r.a
                        self._a(0x00)
                        m[0x0097]=r.a
                        self._a(0x09)
                        m[0x00BB]=r.a
                        self._a(0x02)
                        m[0x042C]=r.a
                        self._a(0x00)
                        m[0x042D]=r.a
                        m[0x042E]=r.a
                        self._a(0xDA)
                        self._mark(0xD809)
                        yield from self._external(0xD809,0xF28B,None,"tail")
                        return
                    else:
                        self._a(0x06)
                        m[UI_PHASE]=r.a
                        yield from self._external(0xD7DF,0xECEE,0xD7E2,"call",None)
                        if r.pc!=0xD7E2:return  # preserve nonlocal stack return
                        self._mark(0xD7E2)
                        self._rts();return
                else:
                    return (yield from self.confirm_rulers_and_start())

    def acknowledge_second_prompt(self):
        """$D80C: acknowledge second prompt; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD80C)
        if not (yield from self._local_call(self.text_idle,0xD80C,0xD80F)):return
        self._mark(0xD80F)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.blink_prompt_marker,0xD811,0xD814)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xD819)
            if r.p&Z:
                pass
            else:
                m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
                self._a(0x00)
                m[0x0424]=r.a
                m[0x0425]=r.a
                m[0x040C]=r.a
                m[0x040D]=r.a
                m[0x046C]=r.a
                self._a(0xDE)
                m[0x0410]=r.a
                self._a(0x00)
                m[0x0098]=r.a
                self._a(0x01)
                m[0x0097]=r.a
                self._a(0x06)
                m[0x00BB]=r.a
                pass
            pass
        self._mark(0xD843)
        self._rts();return

    def select_second_ruler(self):
        """$D844: select second ruler; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD844)
        if not (yield from self._local_call(self.ruler_menu_and_details,0xD844,0xD847)):return
        self._mark(0xD847)
        if not r.p&C:
            self._mark(0xD86C)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xD84E)
            if r.p&Z:
                self._mark(0xD86C)
                self._rts();return
            else:
                self._y(m[0x0012])
                self._a(m[(0xDA07+r.y)&65535])
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._y(r.a)
                self._a(m[(0x6F0A+r.y)&65535])
                self._mark(0xD85D)
                if r.p&Z:
                    self._y(m[0x0012])
                    self._a(m[(0xDA07+r.y)&65535])
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    self._y(r.a)
                    self._a(m[(0xDA0F+r.y)&65535])
                    m[0x046D]=r.a
                    m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
                    self._a(0xA0)
                    m[0x0098]=r.a
                    self._a(0x00)
                    m[0x0097]=r.a
                    self._a(0x09)
                    m[0x00BB]=r.a
                    self._a(m[0x046D])
                    m[0x0000]=r.a
                    self._y(0x3D)
                    yield from self._external(0xD896,0xEE07,0xD89B,"far_call",41002)
                    if r.pc!=0xD89B:return  # preserve nonlocal stack return
                    self._a(0xDB)
                    self._mark(0xD89D)
                    yield from self._external(0xD89D,0xF26D,None,"tail")
                    return
                else:
                    self._a(0x01)
                    m[(0x6F0A+r.y)&65535]=r.a
                    self._a(0x06)
                    m[UI_PHASE]=r.a
                    yield from self._external(0xD869,0xECEE,0xD86C,"call",None)
                    if r.pc!=0xD86C:return  # preserve nonlocal stack return
                    self._mark(0xD86C)
                    self._rts();return

    def inspect_selected_ruler(self):
        """$D8A0: inspect selected ruler; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD8A0)
        self._a(m[0x046D])
        m[0x0000]=r.a
        self._x(0x00)
        self._a(0xA7)
        m[0x000A]=r.a
        self._y(0x39)
        yield from self._external(0xD8AF,0xEE07,0xD8B4,"far_call",40960)
        if r.pc!=0xD8B4:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_idle,0xD8B4,0xD8B7)):return
        self._mark(0xD8B7)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.blink_prompt_marker,0xD8B9,0xD8BC)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xD8C1)
            if r.p&Z:
                pass
            else:
                m[UI_PHASE]=self._nz(m[UI_PHASE]-1)
                self._a(m[0x046D])
                m[0x0410]=r.a
                self._a(0x00)
                m[0x040C]=r.a
                m[0x040D]=r.a
                self._a(0x00)
                m[0x0098]=r.a
                self._a(0x01)
                m[0x0097]=r.a
                self._a(0x06)
                m[0x00BB]=r.a
                pass
            pass
        self._mark(0xD8E3)
        self._rts();return

    def confirm_rulers_and_start(self):
        """$D8E4: confirm rulers and start; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD8E4)
        self._a(0xA7)
        m[0x000A]=r.a
        self._a(m[0x0410])
        m[0x0000]=r.a
        self._x(0x00)
        self._y(0x39)
        yield from self._external(0xD8F3,0xEE07,0xD8F8,"far_call",40960)
        if r.pc!=0xD8F8:return  # preserve nonlocal stack return
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xD8FB)
        if not r.p&N:
            self._mark(0xD905)
            self._rts();return
        else:
            self._a(0x01)
            m[GLOBAL]=r.a
            return (yield from self.apply_selection_option_bits())

    def ruler_menu_and_details(self):
        """$D906: ruler menu and details; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD906)
        self._a(0x35)
        m[0x0010]=r.a
        self._a(0xDA)
        m[0x0011]=r.a
        self._a(0x43)
        m[0x0000]=r.a
        self._a(0xDA)
        m[0x0001]=r.a
        self._a(m[0x046C])
        yield from self._external(0xD91D,0xEDF5,0xD920,"call",None)
        if r.pc!=0xD920:return  # preserve nonlocal stack return
        self._a(0xA7)
        m[0x000A]=r.a
        self._a(m[0x0410])
        m[0x0000]=r.a
        self._x(0x00)
        self._y(0x39)
        yield from self._external(0xD92F,0xEE07,0xD934,"far_call",40960)
        if r.pc!=0xD934:return  # preserve nonlocal stack return
        self._a(m[0x040D])
        self._compare(r.a,0xFF)
        self._mark(0xD939)
        if r.p&Z:
            self._a(0x2B)
            m[0x0010]=r.a
            self._a(0xDA)
            m[0x0011]=r.a
            self._a(0x00)
            m[0x0012]=r.a
            yield from self._external(0xD953,0xED1E,0xD956,"call",None)
            if r.pc!=0xD956:return  # preserve nonlocal stack return
            self._a(m[0x0012])
            self._compare(r.a,m[0x046C])
            self._mark(0xD95C)
            if not r.p&Z:
                m[0x046C]=r.a
                self._y(r.a)
                self._a(m[(0xDA07+r.y)&65535])
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._y(r.a)
                self._a(m[(0xDA0F+r.y)&65535])
                m[0x0410]=r.a
                self._a(0x00)
                m[0x040C]=r.a
                m[0x040D]=r.a
                self._flag(C,False)
                self._mark(0xD979)
                self._rts();return
            else:
                self._flag(C,True)
                self._mark(0xD95F)
                self._rts();return
        else:
            self._y(0x39)
            yield from self._external(0xD93D,0xEE07,0xD942,"far_call",40978)
            if r.pc!=0xD942:return  # preserve nonlocal stack return
            self._flag(C,False)
            self._mark(0xD943)
            self._rts();return

    def initialize_seven_ruler_records(self):
        """$D97A: initialize seven ruler records; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD97A)
        self._a(0xAD)
        m[0x6F07]=r.a
        self._a(0x00)
        m[0x6F08]=r.a
        self._a(0x00)
        m[0x6F09]=r.a
        self._a(0x03)
        m[0x6F0A]=r.a
        self._a(0x08)
        m[0x6F0F]=r.a
        self._a(0x00)
        m[0x6F10]=r.a
        self._a(0x00)
        m[0x6F11]=r.a
        self._a(0x03)
        m[0x6F12]=r.a
        self._a(0x83)
        m[0x6F17]=r.a
        self._a(0x00)
        m[0x6F18]=r.a
        self._a(0x00)
        m[0x6F19]=r.a
        self._a(0x03)
        m[0x6F1A]=r.a
        self._a(0x8A)
        m[0x6F1F]=r.a
        self._a(0x00)
        m[0x6F20]=r.a
        self._a(0x00)
        m[0x6F21]=r.a
        self._a(0x03)
        m[0x6F22]=r.a
        self._a(0xDE)
        m[0x6F27]=r.a
        self._a(0x00)
        m[0x6F28]=r.a
        self._a(0x00)
        m[0x6F29]=r.a
        self._a(0x03)
        m[0x6F2A]=r.a
        self._a(0xDC)
        m[0x6F2F]=r.a
        self._a(0x00)
        m[0x6F30]=r.a
        self._a(0x00)
        m[0x6F31]=r.a
        self._a(0x03)
        m[0x6F32]=r.a
        self._a(0xB6)
        m[0x6F37]=r.a
        self._a(0x00)
        m[0x6F38]=r.a
        self._a(0x00)
        m[0x6F39]=r.a
        self._a(0x03)
        m[0x6F3A]=r.a
        self._mark(0xDA06)
        self._rts();return

    def rulerselectionuicontroller_da48(self):
        """$DA48: rulerselectionuicontroller da48; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDA48)
        self._a(0x68)
        m[0x0000]=r.a
        self._a(0xDA)
        m[0x0001]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        self._a(m[0x0003])
        self._a(0x20)
        m[0x000A]=r.a
        self._a(0x48)
        m[0x000C]=r.a
        yield from self._external(0xDA64,0xF1AD,0xDA67,"call",None)
        if r.pc!=0xDA67:return  # preserve nonlocal stack return
        self._mark(0xDA67)
        self._rts();return

    def blink_prompt_marker(self):
        """$DAD9: blink prompt marker; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDAD9)
        self._a(m[0x005E])
        self._a(r.a & 0x10)
        self._mark(0xDADE)
        if r.p&Z:
            pass
        else:
            self._a(0x00)
            m[0x0002]=r.a
            m[0x000C]=r.a
            m[0x000A]=r.a
            self._a(0xF9)
            m[0x0000]=r.a
            self._a(0xDA)
            m[0x0001]=r.a
            yield from self._external(0xDAF5,0xF1AD,0xDAF8,"call",None)
            if r.pc!=0xDAF8:return  # preserve nonlocal stack return
            pass
        self._mark(0xDAF8)
        self._rts();return

    def text_idle(self):
        """$DAFE: text idle; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDAFE)
        self._a(m[0x0304])
        self._compare(r.a,0xFF)
        self._mark(0xDB03)
        if not r.p&Z:
            self._flag(C,False)
            self._mark(0xDB0F)
            self._rts();return
        else:
            self._a(m[0x0300])
            self._compare(r.a,0xFF)
            self._mark(0xDB0A)
            if not r.p&Z:
                self._flag(C,False)
                self._mark(0xDB0F)
                self._rts();return
            else:
                self._flag(C,True)
                self._mark(0xDB0D)
                self._rts();return

    def track_first_input_sequence(self):
        """$DB10: track first input sequence; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDB10)
        self._a(m[UI_PHASE])
        self._compare(r.a,0x01)
        self._mark(0xDB15)
        if not r.p&Z:
            self._mark(0xDB50)
            self._rts();return
        else:
            self._y(m[0x0545])
            self._a(m[(0xDB51+r.y)&65535])
            self._mark(0xDB1D)
            if not r.p&N:
                self._a(m[0x0083])
                self._y(m[0x0545])
                self._a(r.a & m[(0xDB51+r.y)&65535])
                self._mark(0xDB3D)
                if not r.p&Z:
                    self._a(m[NEW_BUTTONS])
                    self._a(r.a & m[(0xDB5A+r.y)&65535])
                    self._mark(0xDB4B)
                    if r.p&Z:
                        pass
                    else:
                        m[0x0545]=self._nz(m[0x0545]+1)
                        pass
                    self._mark(0xDB50)
                    self._rts();return
                else:
                    self._a(0x00)
                    m[0x0545]=r.a
                    self._mark(0xDB44)
                    self._rts();return
            else:
                self._a(m[0x6FEA])
                self._a(r.a & 0x01)
                self._mark(0xDB24)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x6FEA])
                    self._a(r.a | 0x01)
                    m[0x6FEA]=r.a
                    self._a(0x62)
                    yield from self._external(0xDB30,0xE693,0xDB33,"call",None)
                    if r.pc!=0xDB33:return  # preserve nonlocal stack return
                    pass
                self._mark(0xDB33)
                self._rts();return

    def track_second_input_sequence(self):
        """$DB62: track second input sequence; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDB62)
        self._a(m[UI_PHASE])
        self._compare(r.a,0x03)
        self._mark(0xDB67)
        if not r.p&Z:
            self._mark(0xDBA2)
            self._rts();return
        else:
            self._y(m[0x0546])
            self._a(m[(0xDBA3+r.y)&65535])
            self._mark(0xDB6F)
            if not r.p&N:
                self._a(m[0x0085])
                self._y(m[0x0546])
                self._a(r.a & m[(0xDBA3+r.y)&65535])
                self._mark(0xDB8F)
                if not r.p&Z:
                    self._a(m[0x0082])
                    self._a(r.a & m[(0xDBAC+r.y)&65535])
                    self._mark(0xDB9D)
                    if r.p&Z:
                        pass
                    else:
                        m[0x0546]=self._nz(m[0x0546]+1)
                        pass
                    self._mark(0xDBA2)
                    self._rts();return
                else:
                    self._a(0x00)
                    m[0x0546]=r.a
                    self._mark(0xDB96)
                    self._rts();return
            else:
                self._a(m[0x6FEA])
                self._a(r.a & 0x02)
                self._mark(0xDB76)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x6FEA])
                    self._a(r.a | 0x02)
                    m[0x6FEA]=r.a
                    self._a(0x62)
                    yield from self._external(0xDB82,0xE693,0xDB85,"call",None)
                    if r.pc!=0xDB85:return  # preserve nonlocal stack return
                    pass
                self._mark(0xDB85)
                self._rts();return

    def track_third_input_sequence(self):
        """$DBB4: track third input sequence; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDBB4)
        self._y(m[0x0547])
        self._a(m[(0xDBEE+r.y)&65535])
        self._mark(0xDBBA)
        if not r.p&N:
            self._a(m[0x0083])
            self._y(m[0x0547])
            self._a(r.a & m[(0xDBEE+r.y)&65535])
            self._mark(0xDBDA)
            if not r.p&Z:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & m[(0xDBF7+r.y)&65535])
                self._mark(0xDBE8)
                if r.p&Z:
                    pass
                else:
                    m[0x0547]=self._nz(m[0x0547]+1)
                    pass
                self._mark(0xDBED)
                self._rts();return
            else:
                self._a(0x00)
                m[0x0547]=r.a
                self._mark(0xDBE1)
                self._rts();return
        else:
            self._a(m[0x6FEA])
            self._a(r.a & 0x04)
            self._mark(0xDBC1)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x6FEA])
                self._a(r.a | 0x04)
                m[0x6FEA]=r.a
                self._a(0x62)
                yield from self._external(0xDBCD,0xE693,0xDBD0,"call",None)
                if r.pc!=0xDBD0:return  # preserve nonlocal stack return
                pass
            self._mark(0xDBD0)
            self._rts();return

    def track_fourth_input_sequence(self):
        """$DBFF: track fourth input sequence; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDBFF)
        self._y(m[0x0548])
        self._a(m[(0xDC39+r.y)&65535])
        self._mark(0xDC05)
        if not r.p&N:
            self._a(m[0x0083])
            self._y(m[0x0548])
            self._a(r.a & m[(0xDC39+r.y)&65535])
            self._mark(0xDC25)
            if not r.p&Z:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & m[(0xDC42+r.y)&65535])
                self._mark(0xDC33)
                if r.p&Z:
                    pass
                else:
                    m[0x0548]=self._nz(m[0x0548]+1)
                    pass
                self._mark(0xDC38)
                self._rts();return
            else:
                self._a(0x00)
                m[0x0548]=r.a
                self._mark(0xDC2C)
                self._rts();return
        else:
            self._a(m[0x6FEA])
            self._a(r.a & 0x08)
            self._mark(0xDC0C)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x6FEA])
                self._a(r.a | 0x08)
                m[0x6FEA]=r.a
                self._a(0x62)
                yield from self._external(0xDC18,0xE693,0xDC1B,"call",None)
                if r.pc!=0xDC1B:return  # preserve nonlocal stack return
                pass
            self._mark(0xDC1B)
            self._rts();return

    def apply_selection_option_bits(self):
        """$DC4A: apply selection option bits; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDC4A)
        self._a(m[0x6FEA])
        self._a(r.a & 0x01)
        self._mark(0xDC4F)
        if r.p&Z:
            pass
        else:
            self._a(0x00)
            m[0x0002]=r.a
            while True:  # natural loop $DC56
                yield from self._external(0xDC56,0xF368,0xDC59,"call",None)
                if r.pc!=0xDC59:return  # preserve nonlocal stack return
                self._y(0x03)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,0x00)
                self._mark(0xDC5F)
                if not r.p&Z:
                    m[0x0002]=self._nz(m[0x0002]+1)
                    self._a(m[0x0002])
                    self._compare(r.a,0x07)
                    self._mark(0xDC72)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    pass
                else:
                    self._a(m[0x0002])
                    if not (yield from self._local_call(self.install_option_profile,0xDC64,0xDC67)):return
                    pass
                self._a(m[0x6FEA])
                self._a(r.a & 0x02)
                self._mark(0xDC79)
                if r.p&Z:
                    self._mark(0xDC9B)
                    self._rts();return
                else:
                    self._a(0x00)
                    m[0x0002]=r.a
                    while True:  # natural loop $DC80
                        yield from self._external(0xDC80,0xF368,0xDC83,"call",None)
                        if r.pc!=0xDC83:return  # preserve nonlocal stack return
                        self._y(0x03)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._compare(r.a,0x01)
                        self._mark(0xDC89)
                        if not r.p&Z:
                            m[0x0002]=self._nz(m[0x0002]+1)
                            self._a(m[0x0002])
                            self._compare(r.a,0x07)
                            self._mark(0xDC99)
                            if not r.p&C:
                                continue
                            else:
                                self._mark(0xDC9B)
                                self._rts();return
                        else:
                            self._a(m[0x0002])
                            return (yield from self.install_option_profile())
        self._a(m[0x6FEA])
        self._a(r.a & 0x02)
        self._mark(0xDC79)
        if r.p&Z:
            self._mark(0xDC9B)
            self._rts();return
        else:
            self._a(0x00)
            m[0x0002]=r.a
            while True:  # natural loop $DC80
                yield from self._external(0xDC80,0xF368,0xDC83,"call",None)
                if r.pc!=0xDC83:return  # preserve nonlocal stack return
                self._y(0x03)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,0x01)
                self._mark(0xDC89)
                if not r.p&Z:
                    m[0x0002]=self._nz(m[0x0002]+1)
                    self._a(m[0x0002])
                    self._compare(r.a,0x07)
                    self._mark(0xDC99)
                    if not r.p&C:
                        continue
                    else:
                        self._mark(0xDC9B)
                        self._rts();return
                else:
                    self._a(m[0x0002])
                    return (yield from self.install_option_profile())

    def install_option_profile(self):
        """$DC9C: install option profile; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDC9C)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xDCB7+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[(0xDCB8+r.y)&65535])
        m[0x0001]=r.a
        self._y(0x02)
        while True:  # natural loop $DCAC
            self._a(m[(0xDCC3+r.y)&65535])
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._y(r.y+1)
            self._compare(r.y,0x11)
            self._mark(0xDCB4)
            if not r.p&C:
                continue
            else:
                pass
            self._mark(0xDCB6)
            self._rts();return

class EndingUIController(UIControlBase):
    PAIR=(23, 24)
    PUBLIC_ENTRIES=(40990,)
    def fields(self):
        m=self.memory
        return dict(global_state=m[0x7A],NMI_scene=m[0x78],ending_mode=m[0x541],ending_phase=m[0x542],
                    ending_animation_04C9=m[0x4C9],ending_animation_04CA=m[0x4CA],ending_work_04CB=m[0x4CB],
                    ending_counter=m[0x4CD]|m[0x4CE]<<8,PPU_jobs=m[0x7E])

    def _entry(self,entry):
        if entry==0xA01E:return self.ending_entry()
        elif entry==0xD693:return self.ending_tick()
        elif entry==0xD6AA:return self.loss_or_extinction_notice()
        elif entry==0xD76D:return self.loss_palette()
        elif entry==0xD79B:return self.score_high_ending()
        elif entry==0xD83A:return self.score_middle_ending()
        elif entry==0xD8C9:return self.score_low_ending()
        elif entry==0xD920:return self.final_text()
        elif entry==0xD932:return self.endinguicontroller_d923_phase_0()
        elif entry==0xD950:return self.endinguicontroller_d923_phase_1()
        elif entry==0xD95A:return self.endinguicontroller_d923_phase_2()
        elif entry==0xD976:return self.endinguicontroller_d923_phase_3()
        elif entry==0xD9B4:return self.endinguicontroller_d923_phase_4()
        elif entry==0xD9C2:return self.endinguicontroller_d923_phase_5()
        elif entry==0xD9CA:return self.officer_credits()
        elif entry==0xD9DE:return self.endinguicontroller_d9cd_phase_0()
        elif entry==0xDA41:return self.endinguicontroller_d9cd_phase_1()
        elif entry==0xDA87:return self.endinguicontroller_d9cd_phase_2()
        elif entry==0xDAB6:return self.endinguicontroller_d9cd_phase_3()
        elif entry==0xDAE0:return self.endinguicontroller_d9cd_phase_4()
        elif entry==0xDB50:return self.endinguicontroller_db50()
        elif entry==0xDB90:return self.endinguicontroller_d9cd_phase_5()
        elif entry==0xDBDA:return self.endinguicontroller_d9cd_phase_6()
        elif entry==0xDBF3:return self.ending_frame_sprites()
        elif entry==0xDC13:return self.endinguicontroller_dc13()
        elif entry==0xDCE1:return self.endinguicontroller_dce1()
        raise ValueError("Entry outside immutable UI procedure catalog")

    def ending_entry(self):
        """$A01E: ending entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA01E)
        return (yield from self.ending_tick())

    def ending_tick(self):
        """$D693: ending tick; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD693)
        self._y(0x26)
        yield from self._external(0xD695,0xF25F,0xD698,"call",None)
        if r.pc!=0xD698:return  # preserve nonlocal stack return
        self._a(m[UI_PHASE])
        self._mark(0xD69B)
        index=self._dispatch(0xD69B,(54954, 55195, 55354, 55497, 55754, 55584))
        return (yield from (self.loss_or_extinction_notice,self.score_high_ending,self.score_middle_ending,self.score_low_ending,self.officer_credits,self.final_text,)[index]())

    def loss_or_extinction_notice(self):
        """$D6AA: loss or extinction notice; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD6AA)
        self._a(m[0x04CA])
        self._mark(0xD6AD)
        if not r.p&Z:
            m[0x04CD]=self._nz(m[0x04CD]+1)
            self._a(0x7E)
            m[0x0010]=r.a
            self._a(0x9A)
            m[0x0011]=r.a
            self._y(m[0x04CB])
            self._mark(0xD6E2)
            if r.p&N:
                pass
            else:
                if not (yield from self._local_call(self.ending_frame_sprites,0xD6E4,0xD6E7)):return
                pass
            self._y(m[0x04CA])
            if not (yield from self._local_call(self.ending_frame_sprites,0xD6EA,0xD6ED)):return
            self._a(m[0x04CA])
            self._flag(C,False)
            self._add(0x04)
            self._y(r.a)
            if not (yield from self._local_call(self.ending_frame_sprites,0xD6F4,0xD6F7)):return
            self._a(m[0x04CD])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x03)
            self._flag(C,False)
            self._add(0x01)
            m[0x04CA]=r.a
            self._a(m[0x04CB])
            self._compare(r.a,0xFE)
            self._mark(0xD70A)
            if r.p&Z:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x01)
                self._mark(0xD72F)
                if r.p&Z:
                    self._mark(0xD751)
                    self._rts();return
                else:
                    self._a(m[0x6F43])
                    self._mark(0xD734)
                    if r.p&Z:
                        self._mark(0xD752)
                        yield from self._external(0xD752,0xE000,None,"tail")
                        return
                    else:
                        self._a(0x00)
                        m[0x6F43]=r.a
                        self._a(m[0x0472])
                        m[0x0400]=r.a
                        self._a(m[0x0473])
                        m[0x0401]=r.a
                        self._a(0x00)
                        m[0x0402]=r.a
                        self._a(0x01)
                        m[GLOBAL]=r.a
                        self._mark(0xD751)
                        self._rts();return
            else:
                self._a(m[0x0300])
                self._compare(r.a,0xFF)
                self._mark(0xD711)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x0304])
                    self._compare(r.a,0xFF)
                    self._mark(0xD718)
                    if not r.p&Z:
                        pass
                    else:
                        m[0x04CE]=self._nz(m[0x04CE]+1)
                        self._a(m[0x04CE])
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        self._y(r.a)
                        self._a(m[(0xD755+r.y)&65535])
                        m[0x04CB]=r.a
                        pass
                    pass
                self._mark(0xD729)
                self._rts();return
        else:
            self._a(0x00)
            m[0x04CD]=r.a
            m[0x04CE]=r.a
            m[0x04CA]=self._nz(m[0x04CA]+1)
            self._a(0xFF)
            m[0x04CB]=r.a
            if not (yield from self._local_call(self.loss_palette,0xD6BF,0xD6C2)):return
            self._a(0xD9)
            self._x(m[0x042E])
            self._compare(r.x,0xFF)
            self._mark(0xD6C9)
            if r.p&Z:
                pass
            else:
                self._a(0xD8)
                pass
            yield from self._external(0xD6CD,0xF28B,0xD6D0,"call",None)
            if r.pc!=0xD6D0:return  # preserve nonlocal stack return
            yield from self._external(0xD6D0,0xECBF,0xD6D3,"call",None)
            if r.pc!=0xD6D3:return  # preserve nonlocal stack return
            self._mark(0xD6D3)
            self._rts();return

    def loss_palette(self):
        """$D76D: loss palette; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD76D)
        self._y(0x00)
        while True:  # natural loop $D76F
            self._a(m[(0xD77B+r.y)&65535])
            m[(0x0100+r.y)&65535]=r.a
            self._y(r.y+1)
            self._compare(r.y,0x20)
            self._mark(0xD778)
            if not r.p&C:
                continue
            else:
                pass
            self._mark(0xD77A)
            self._rts();return

    def score_high_ending(self):
        """$D79B: score high ending; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD79B)
        self._a(m[0x04CA])
        self._mark(0xD79E)
        if not r.p&Z:
            self._a(m[0x04C9])
            self._mark(0xD7DA)
            if not r.p&N:
                m[0x04CD]=self._nz(m[0x04CD]+1)
                self._mark(0xD7E2)
                if not r.p&Z:
                    pass
                else:
                    m[0x04CE]=self._nz(m[0x04CE]+1)
                    pass
                self._a(0xD9)
                m[0x0010]=r.a
                self._a(0x9C)
                m[0x0011]=r.a
                self._y(m[0x04CA])
                if not (yield from self._local_call(self.ending_frame_sprites,0xD7F2,0xD7F5)):return
                self._a(m[0x04CD])
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                self._a(r.a & 0x03)
                m[0x0000]=r.a
                self._flag(C,False)
                self._add(0x01)
                m[0x04CA]=r.a
                self._a(m[0x04CE])
                self._compare(r.a,0x03)
                self._mark(0xD80A)
                if not r.p&C:
                    pass
                else:
                    self._a(0x80)
                    m[0x04C9]=r.a
                    yield from self._external(0xD811,0xECEE,0xD814,"call",None)
                    if r.pc!=0xD814:return  # preserve nonlocal stack return
                    pass
                self._mark(0xD814)
                self._rts();return
            else:
                self._a(m[REPEAT_BUTTONS])
                self._mark(0xD818)
                if not r.p&N:
                    pass
                else:
                    self._a(0x70)
                    m[0x006A]=r.a
                    self._a(0x20)
                    m[0x006C]=r.a
                    self._a(0xF2)
                    m[0x006D]=r.a
                    self._a(0x00)
                    m[0x04C9]=r.a
                    m[0x04CA]=r.a
                    m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
                    self._a(0x00)
                    yield from self._external(0xD836,0xF28B,0xD839,"call",None)
                    if r.pc!=0xD839:return  # preserve nonlocal stack return
                    pass
                self._mark(0xD839)
                self._rts();return
        else:
            self._a(m[0x04C9])
            self._mark(0xD7A3)
            if not r.p&Z:
                pass
            else:
                self._a(0xA0)
                m[0x006A]=r.a
                self._a(0xF8)
                m[0x006C]=r.a
                self._a(0xF1)
                m[0x006D]=r.a
                if not (yield from self._local_call(self.endinguicontroller_dce1,0xD7B4,0xD7B7)):return
                pass
            if not (yield from self._local_call(self.endinguicontroller_dc13,0xD7B7,0xD7BA)):return
            self._a(m[0x04C9])
            self._compare(r.a,0x10)
            self._mark(0xD7BF)
            if not r.p&C:
                pass
            else:
                self._a(0x00)
                m[0x04CD]=r.a
                m[0x04CE]=r.a
                self._a(0x02)
                m[0x04CA]=r.a
                self._a(0xDC)
                yield from self._external(0xD7D0,0xF28B,0xD7D3,"call",None)
                if r.pc!=0xD7D3:return  # preserve nonlocal stack return
                yield from self._external(0xD7D3,0xECBF,0xD7D6,"call",None)
                if r.pc!=0xD7D6:return  # preserve nonlocal stack return
                pass
            self._mark(0xD7D6)
            self._rts();return

    def score_middle_ending(self):
        """$D83A: score middle ending; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD83A)
        self._a(m[0x04CA])
        self._mark(0xD83D)
        if not r.p&Z:
            self._a(m[0x04C9])
            self._mark(0xD86A)
            if not r.p&N:
                m[0x04CD]=self._nz(m[0x04CD]+1)
                self._mark(0xD872)
                if not r.p&Z:
                    pass
                else:
                    m[0x04CE]=self._nz(m[0x04CE]+1)
                    pass
                self._a(0x75)
                m[0x0010]=r.a
                self._a(0x9E)
                m[0x0011]=r.a
                self._y(m[0x04CA])
                if not (yield from self._local_call(self.ending_frame_sprites,0xD882,0xD885)):return
                self._a(m[0x04CA])
                self._flag(C,False)
                self._add(0x03)
                self._y(r.a)
                if not (yield from self._local_call(self.ending_frame_sprites,0xD88C,0xD88F)):return
                self._a(m[0x04CD])
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                self._a(r.a & 0x03)
                self._compare(r.a,0x03)
                self._mark(0xD899)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x02)
                    pass
                self._flag(C,False)
                self._add(0x01)
                m[0x04CA]=r.a
                self._a(m[0x04CE])
                self._compare(r.a,0x03)
                self._mark(0xD8A8)
                if not r.p&C:
                    pass
                else:
                    self._a(0x80)
                    m[0x04C9]=r.a
                    yield from self._external(0xD8AF,0xECEE,0xD8B2,"call",None)
                    if r.pc!=0xD8B2:return  # preserve nonlocal stack return
                    pass
                self._mark(0xD8B2)
                self._rts();return
            else:
                self._a(m[REPEAT_BUTTONS])
                self._mark(0xD8B6)
                if not r.p&N:
                    pass
                else:
                    m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
                    self._a(0x00)
                    m[0x04C9]=r.a
                    m[0x04CA]=r.a
                    self._a(0x00)
                    yield from self._external(0xD8C5,0xF28B,0xD8C8,"call",None)
                    if r.pc!=0xD8C8:return  # preserve nonlocal stack return
                    pass
                self._mark(0xD8C8)
                self._rts();return
        else:
            self._a(m[0x04C9])
            self._mark(0xD842)
            if not r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.endinguicontroller_dce1,0xD844,0xD847)):return
                pass
            if not (yield from self._local_call(self.endinguicontroller_dc13,0xD847,0xD84A)):return
            self._a(m[0x04C9])
            self._compare(r.a,0x10)
            self._mark(0xD84F)
            if not r.p&C:
                pass
            else:
                self._a(0x00)
                m[0x04CD]=r.a
                m[0x04CE]=r.a
                self._a(0x01)
                m[0x04CA]=r.a
                self._a(0xDD)
                yield from self._external(0xD860,0xF28B,0xD863,"call",None)
                if r.pc!=0xD863:return  # preserve nonlocal stack return
                yield from self._external(0xD863,0xECBF,0xD866,"call",None)
                if r.pc!=0xD866:return  # preserve nonlocal stack return
                pass
            self._mark(0xD866)
            self._rts();return

    def score_low_ending(self):
        """$D8C9: score low ending; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD8C9)
        self._a(m[0x04CA])
        self._mark(0xD8CC)
        if not r.p&Z:
            m[0x04CD]=self._nz(m[0x04CD]+1)
            self._mark(0xD8F9)
            if not r.p&Z:
                pass
            else:
                m[0x04CE]=self._nz(m[0x04CE]+1)
                pass
            self._a(m[0x04CE])
            self._compare(r.a,0x03)
            self._mark(0xD903)
            if not r.p&C:
                self._mark(0xD914)
                self._rts();return
            else:
                self._a(m[0x0435])
                self._compare(r.a,0x46)
                self._mark(0xD90A)
                if not r.p&C:
                    self._a(0x05)
                    m[UI_PHASE]=r.a
                    self._a(0x04)
                    m[0x0542]=r.a
                    self._mark(0xD91F)
                    self._rts();return
                else:
                    m[UI_PHASE]=self._nz(m[UI_PHASE]+1)
                    self._a(0x00)
                    m[0x0542]=r.a
                    self._mark(0xD914)
                    self._rts();return
        else:
            self._a(m[0x04C9])
            self._mark(0xD8D1)
            if not r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.endinguicontroller_dce1,0xD8D3,0xD8D6)):return
                pass
            if not (yield from self._local_call(self.endinguicontroller_dc13,0xD8D6,0xD8D9)):return
            self._a(m[0x04C9])
            self._compare(r.a,0x10)
            self._mark(0xD8DE)
            if not r.p&C:
                pass
            else:
                self._a(0x00)
                m[0x04CD]=r.a
                m[0x04CE]=r.a
                self._a(0x01)
                m[0x04CA]=r.a
                self._a(0xDE)
                yield from self._external(0xD8EF,0xF28B,0xD8F2,"call",None)
                if r.pc!=0xD8F2:return  # preserve nonlocal stack return
                yield from self._external(0xD8F2,0xECBF,0xD8F5,"call",None)
                if r.pc!=0xD8F5:return  # preserve nonlocal stack return
                pass
            self._mark(0xD8F5)
            self._rts();return

    def final_text(self):
        """$D920: final text; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD920)
        self._a(m[0x0542])
        self._mark(0xD923)
        index=self._dispatch(0xD923,(55602, 55632, 55642, 55670, 55732, 55746))
        return (yield from (self.endinguicontroller_d923_phase_0,self.endinguicontroller_d923_phase_1,self.endinguicontroller_d923_phase_2,self.endinguicontroller_d923_phase_3,self.endinguicontroller_d923_phase_4,self.endinguicontroller_d923_phase_5,)[index]())

    def endinguicontroller_d923_phase_0(self):
        """$D932: endinguicontroller d923 phase 0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD932)
        self._a(0x00)
        m[0x0098]=r.a
        self._a(0x08)
        m[0x00BA]=r.a
        self._a(0x09)
        m[0x00BB]=r.a
        self._a(0xA7)
        m[0x00BD]=r.a
        self._a(0xF2)
        m[0x0543]=r.a
        m[0x0542]=self._nz(m[0x0542]+1)
        self._a(0x01)
        m[0x0544]=r.a
        self._mark(0xD94F)
        self._rts();return

    def endinguicontroller_d923_phase_1(self):
        """$D950: endinguicontroller d923 phase 1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD950)
        self._a(m[0x0543])
        yield from self._external(0xD953,0xF28B,0xD956,"call",None)
        if r.pc!=0xD956:return  # preserve nonlocal stack return
        m[0x0542]=self._nz(m[0x0542]+1)
        self._mark(0xD959)
        self._rts();return

    def endinguicontroller_d923_phase_2(self):
        """$D95A: endinguicontroller d923 phase 2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD95A)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xD95F)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xD966)
            if not r.p&Z:
                pass
            else:
                m[0x0544]=self._nz(m[0x0544]-1)
                self._mark(0xD96B)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x00)
                    m[0x0409]=r.a
                    m[0x0542]=self._nz(m[0x0542]+1)
                    pass
                pass
            pass
        self._mark(0xD975)
        self._rts();return

    def endinguicontroller_d923_phase_3(self):
        """$D976: endinguicontroller d923 phase 3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD976)
        m[0x0098]=self._nz(m[0x0098]+1)
        self._a(m[0x0098])
        self._compare(r.a,0xF0)
        self._mark(0xD97E)
        if not r.p&C:
            pass
        else:
            self._a(0x00)
            m[0x0098]=r.a
            pass
        m[0x0409]=self._nz(m[0x0409]+1)
        self._a(m[0x0409])
        self._compare(r.a,0x50)
        self._mark(0xD98D)
        if not r.p&C:
            self._mark(0xD9B3)
            self._rts();return
        else:
            m[0x0542]=self._nz(m[0x0542]-1)
            m[0x0542]=self._nz(m[0x0542]-1)
            self._a(0x60)
            m[0x0544]=r.a
            m[0x0543]=self._nz(m[0x0543]+1)
            self._a(m[0x0543])
            self._compare(r.a,0xF9)
            self._mark(0xD9A2)
            if not r.p&Z:
                self._compare(r.a,0xFA)
                self._mark(0xD9AC)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x04)
                    m[0x0542]=r.a
                    pass
                self._mark(0xD9B3)
                self._rts();return
            else:
                self._a(0x01)
                m[0x0544]=r.a
                self._mark(0xD9A9)
                self._rts();return

    def endinguicontroller_d923_phase_4(self):
        """$D9B4: endinguicontroller d923 phase 4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD9B4)
        self._a(m[NEW_BUTTONS])
        self._a(r.a & 0x08)
        self._mark(0xD9B9)
        if r.p&Z:
            pass
        else:
            yield from self._external(0xD9BB,0xECEE,0xD9BE,"call",None)
            if r.pc!=0xD9BE:return  # preserve nonlocal stack return
            m[0x0542]=self._nz(m[0x0542]+1)
            pass
        self._mark(0xD9C1)
        self._rts();return

    def endinguicontroller_d923_phase_5(self):
        """$D9C2: endinguicontroller d923 phase 5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD9C2)
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xD9C5)
        if not r.p&N:
            self._mark(0xD9C1)
            self._rts();return
        else:
            self._mark(0xD9C7)
            yield from self._external(0xD9C7,0xE000,None,"tail")
            return

    def officer_credits(self):
        """$D9CA: officer credits; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD9CA)
        self._a(m[0x0542])
        self._mark(0xD9CD)
        index=self._dispatch(0xD9CD,(55774, 55873, 55943, 55990, 56032, 56208, 56282))
        return (yield from (self.endinguicontroller_d9cd_phase_0,self.endinguicontroller_d9cd_phase_1,self.endinguicontroller_d9cd_phase_2,self.endinguicontroller_d9cd_phase_3,self.endinguicontroller_d9cd_phase_4,self.endinguicontroller_d9cd_phase_5,self.endinguicontroller_d9cd_phase_6,)[index]())

    def endinguicontroller_d9cd_phase_0(self):
        """D9DE: credits buffer from all30 city rosters, retaining byte wrap.

        PrefixFE, highlighted officer042C, then each nonFF/nonhighlighted ID.
        The write cursor is byte-sized and neither deduplicates nor grows the
        original buffer. FE/FF markers finish it exactly as the original does.
        """
        r=self.registers;m=self.memory;self._mark(0xD9DE)
        self._y(48);yield from self._external(0xD9E0,0xF25F,0xD9E3,'call')
        if r.pc!=0xD9E3:return
        self._a(254);m[0x410]=r.a;self._a(m[0x42C]);m[0x411]=r.a
        self._x(0);self._a(2);m[2]=r.a
        while True:
            self._a(r.x);self._push(r.a)
            yield from self._external(0xD9F6,0xF2AF,0xD9F9,'call')
            if r.pc!=0xD9F9:return
            self._y(17)
            while True:
                self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,255)
                if not r.p&Z:
                    self._compare(r.a,m[0x411])
                    if not r.p&Z:
                        self._x(m[2]);m[0x410+r.x]=r.a;m[2]=self._nz(m[2]+1)
                self._y(r.y+1);self._compare(r.y,27)
                if r.p&C:break
            self._a(self._pop());self._x(r.a);self._x(r.x+1);self._compare(r.x,30)
            if r.p&C:break
        self._a(254);self._x(m[2]);m[0x410+r.x]=r.a;self._x(r.x+1)
        self._a(255);m[0x410+r.x]=r.a;self._a(0)
        m[0x40C]=m[0x40D]=m[0x401]=r.a;self._a(192);m[0x543]=r.a
        self._a(6);m[0x542]=r.a;self._a(241)
        yield from self._external(0xDA3D,0xF28B,0xDA40,'call')
        if r.pc!=0xDA40:return
        self._rts()

    def endinguicontroller_d9cd_phase_1(self):
        """$DA41: endinguicontroller d9cd phase 1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDA41)
        self._y(0x39)
        yield from self._external(0xDA43,0xEE07,0xDA48,"far_call",40978)
        if r.pc!=0xDA48:return  # preserve nonlocal stack return
        self._a(m[0x040D])
        self._compare(r.a,0xFF)
        self._mark(0xDA4D)
        if r.p&Z:
            self._a(0x08)
            m[0x00BA]=r.a
            self._a(0x06)
            m[0x00BB]=r.a
            self._a(0x00)
            m[0x0096]=r.a
            self._a(0x01)
            m[0x0097]=r.a
            self._a(0x00)
            m[0x0098]=r.a
            self._a(0x01)
            m[0x0061]=r.a
            self._a(0x20)
            m[0x006E]=r.a
            self._a(0xC0)
            m[0x0070]=r.a
            self._a(0xE1)
            m[0x00E8]=r.a
            m[0x0542]=self._nz(m[0x0542]+1)
            self._a(0x03)
            m[0x0401]=r.a
            self._a(0x20)
            m[0x0543]=r.a
            self._a(0x00)
            m[0x0408]=r.a
            self._mark(0xDA86)
            self._rts();return
        else:
            self._mark(0xDA4F)
            self._rts();return

    def endinguicontroller_d9cd_phase_2(self):
        """$DA87: endinguicontroller d9cd phase 2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDA87)
        self._a(0xAE)
        m[0x000A]=r.a
        self._x(m[0x0408])
        self._a(m[(0x0410+r.x)&65535])
        m[0x0000]=r.a
        self._y(0x39)
        yield from self._external(0xDA95,0xEE07,0xDA9A,"far_call",40960)
        if r.pc!=0xDA9A:return  # preserve nonlocal stack return
        m[0x0542]=self._nz(m[0x0542]+1)
        self._a(0x00)
        m[0x0409]=r.a
        m[0x040A]=r.a
        self._a(0x00)
        m[0x040D]=r.a
        self._y(m[0x0408])
        self._y(r.y+1)
        self._a(m[(0x0410+r.y)&65535])
        self._a(r.y)
        m[0x040C]=r.a
        self._mark(0xDAB5)
        self._rts();return

    def endinguicontroller_d9cd_phase_3(self):
        """$DAB6: endinguicontroller d9cd phase 3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDAB6)
        self._y(0x39)
        yield from self._external(0xDAB8,0xEE07,0xDABD,"far_call",40978)
        if r.pc!=0xDABD:return  # preserve nonlocal stack return
        self._a(0xAE)
        m[0x000A]=r.a
        self._x(m[0x0408])
        self._a(m[(0x0410+r.x)&65535])
        m[0x0000]=r.a
        self._y(0x39)
        yield from self._external(0xDACB,0xEE07,0xDAD0,"far_call",40960)
        if r.pc!=0xDAD0:return  # preserve nonlocal stack return
        self._a(m[0x040D])
        self._compare(r.a,0xFF)
        self._mark(0xDAD5)
        if not r.p&Z:
            pass
        else:
            m[0x0543]=self._nz(m[0x0543]-1)
            self._mark(0xDADA)
            if not r.p&Z:
                pass
            else:
                m[0x0542]=self._nz(m[0x0542]+1)
                pass
            pass
        self._mark(0xDADF)
        self._rts();return

    def endinguicontroller_d9cd_phase_4(self):
        """$DAE0: endinguicontroller d9cd phase 4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDAE0)
        self._a(m[0x0409])
        self._compare(r.a,0x40)
        self._mark(0xDAE5)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x040E])
            m[0x00BC]=r.a
            self._a(m[0x040F])
            m[0x00BD]=r.a
            pass
        m[0x0098]=self._nz(m[0x0098]+1)
        self._a(m[0x0098])
        self._compare(r.a,0xF0)
        self._mark(0xDAF7)
        if not r.p&C:
            pass
        else:
            self._a(0x00)
            m[0x0098]=r.a
            pass
        self._a(m[0x0409])
        self._compare(r.a,0x29)
        self._mark(0xDB02)
        if r.p&C:
            self._a(0xFC)
            self._flag(C,True)
            self._add(m[0x0409],subtract=True)
            self._compare(r.a,0xAE)
            self._mark(0xDB32)
            if r.p&C:
                pass
            else:
                self._a(0xAE)
                pass
            m[0x000A]=r.a
            self._x(m[0x0408])
            self._x(r.x+1)
            if not (yield from self._local_call(self.endinguicontroller_db50,0xDB3C,0xDB3F)):return
            self._a(0xAC)
            self._flag(C,True)
            self._add(m[0x0409],subtract=True)
            m[0x000A]=r.a
            self._x(m[0x0408])
            if not (yield from self._local_call(self.endinguicontroller_db50,0xDB4A,0xDB4D)):return
            pass
        else:
            self._a(0xAC)
            self._flag(C,True)
            self._add(m[0x0409],subtract=True)
            m[0x000A]=r.a
            self._x(m[0x0408])
            if not (yield from self._local_call(self.endinguicontroller_db50,0xDB0F,0xDB12)):return
            self._a(0xFC)
            self._flag(C,True)
            self._add(m[0x0409],subtract=True)
            self._compare(r.a,0xAE)
            self._mark(0xDB1A)
            if r.p&C:
                pass
            else:
                self._a(0xAE)
                pass
            m[0x000A]=r.a
            self._x(m[0x0408])
            self._x(r.x+1)
            if not (yield from self._local_call(self.endinguicontroller_db50,0xDB24,0xDB27)):return
            pass
        m[0x0409]=self._nz(m[0x0409]+1)
        self._a(m[0x0409])
        self._compare(r.a,0x50)
        self._mark(0xDB65)
        if not r.p&C:
            pass
        else:
            m[0x0542]=self._nz(m[0x0542]-1)
            m[0x0542]=self._nz(m[0x0542]-1)
            m[0x0408]=self._nz(m[0x0408]+1)
            self._a(0x20)
            m[0x0543]=r.a
            self._y(m[0x0408])
            self._y(r.y+1)
            self._a(m[(0x0410+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xDB7E)
            if not r.p&Z:
                pass
            else:
                self._a(0x05)
                m[0x0542]=r.a
                self._a(0x80)
                m[0x0543]=r.a
                self._a(0x27)
                m[0x0544]=r.a
                pass
            pass
        self._mark(0xDB8F)
        self._rts();return

    def endinguicontroller_db50(self):
        """$DB50: endinguicontroller db50; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDB50)
        self._a(m[(0x0410+r.x)&65535])
        m[0x0000]=r.a
        self._y(0x39)
        yield from self._external(0xDB57,0xEE07,0xDB5C,"far_call",40960)
        if r.pc!=0xDB5C:return  # preserve nonlocal stack return
        self._mark(0xDB5C)
        self._rts();return

    def endinguicontroller_d9cd_phase_5(self):
        """$DB90: endinguicontroller d9cd phase 5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDB90)
        self._a(0x40)
        m[0x0380]=r.a
        self._a(m[0x0544])
        m[0x0381]=r.a
        self._a(m[0x0543])
        m[0x0382]=r.a
        self._y(0x00)
        self._a(0x01)
        while True:  # natural loop $DBA5
            m[(0x0383+r.y)&65535]=r.a
            self._y(r.y+1)
            self._compare(r.y,0x40)
            self._mark(0xDBAB)
            if not r.p&C:
                continue
            else:
                pass
            self._a(0xFF)
            m[(0x0383+r.y)&65535]=r.a
            self._a(m[0x0543])
            self._flag(C,True)
            self._add(0x40,subtract=True)
            m[0x0543]=r.a
            self._a(m[0x0544])
            self._add(0x00,subtract=True)
            m[0x0544]=r.a
            self._compare(r.a,0x23)
            self._mark(0xDBC5)
            if not r.p&Z:
                pass
            else:
                self._a(0x05)
                m[UI_PHASE]=r.a
                self._a(0x00)
                m[0x0542]=r.a
                pass
            self._a(m[PPU_JOBS])
            self._a(r.a | 0x04)
            m[PPU_JOBS]=r.a
            self._mark(0xDBD9)
            self._rts();return

    def endinguicontroller_d9cd_phase_6(self):
        """$DBDA: endinguicontroller d9cd phase 6; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDBDA)
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xDBDF)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xDBE6)
            if not r.p&Z:
                pass
            else:
                m[0x0543]=self._nz(m[0x0543]-1)
                self._mark(0xDBEB)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x01)
                    m[0x0542]=r.a
                    pass
                pass
            pass
        self._mark(0xDBF2)
        self._rts();return

    def ending_frame_sprites(self):
        """$DBF3: ending frame sprites; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDBF3)
        self._x(0x10)
        m[0x000C]=r.x
        self._y(r.y-1)
        self._a(r.y)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
        m[0x0000]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
        m[0x0001]=r.a
        self._a(0x1F)
        m[0x000A]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        self._mark(0xDC10)
        yield from self._external(0xDC10,0xF1AD,None,"tail")
        return

    def endinguicontroller_dc13(self):
        """$DC13: endinguicontroller dc13; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDC13)
        self._y(0x26)
        yield from self._external(0xDC15,0xF25F,0xDC18,"call",None)
        if r.pc!=0xDC18:return  # preserve nonlocal stack return
        self._a(m[0x04C9])
        self._compare(r.a,0x02)
        self._mark(0xDC1D)
        if r.p&C:
            self._a(0x1C)
            m[0x0380]=r.a
            self._a(m[0x04D5])
            m[0x0381]=r.a
            self._a(m[0x04D4])
            m[0x0382]=r.a
            self._a(m[0x04D2])
            m[0x0010]=r.a
            self._a(m[0x04D3])
            m[0x0011]=r.a
            self._y(0x00)
            while True:  # natural loop $DC41
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                m[(0x0383+r.y)&65535]=r.a
                self._y(r.y+1)
                self._compare(r.y,0x1C)
                self._mark(0xDC49)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(0xFF)
                m[(0x0383+r.y)&65535]=r.a
                self._a(m[0x0010])
                self._flag(C,False)
                self._add(0x1C)
                m[0x04D2]=r.a
                self._a(m[0x0011])
                self._add(0x00)
                m[0x04D3]=r.a
                self._a(m[0x04D4])
                self._flag(C,False)
                self._add(0x20)
                m[0x04D4]=r.a
                self._a(m[0x04D5])
                self._add(0x00)
                m[0x04D5]=r.a
                m[0x04C9]=self._nz(m[0x04C9]+1)
                self._a(m[PPU_JOBS])
                self._a(r.a | 0x04)
                m[PPU_JOBS]=r.a
                self._mark(0xDC7D)
                self._rts();return
        else:
            self._a(0x20)
            m[0x0380]=r.a
            self._a(0x23)
            m[0x0381]=r.a
            self._a(0xC8)
            m[0x0382]=r.a
            self._a(m[UI_PHASE])
            self._flag(C,True)
            self._add(0x01,subtract=True)
            r.a=self._shift(r.a,True,rotate=False)
            self._y(r.a)
            self._a(m[(0xDCDB+r.y)&65535])
            m[0x0010]=r.a
            self._y(r.y+1)
            self._a(m[(0xDCDB+r.y)&65535])
            m[0x0011]=r.a
            self._y(0x00)
            while True:  # natural loop $DCA4
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                m[(0x0383+r.y)&65535]=r.a
                self._y(r.y+1)
                self._compare(r.y,0x20)
                self._mark(0xDCAC)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(0xFF)
                m[(0x0383+r.y)&65535]=r.a
                self._a(m[UI_PHASE])
                self._flag(C,True)
                self._add(0x01,subtract=True)
                r.a=self._shift(r.a,True,rotate=False)
                self._y(r.a)
                self._a(m[(0xDCD5+r.y)&65535])
                m[0x04D2]=r.a
                self._y(r.y+1)
                self._a(m[(0xDCD5+r.y)&65535])
                m[0x04D3]=r.a
                self._a(0x82)
                m[0x04D4]=r.a
                self._a(0x20)
                m[0x04D5]=r.a
                m[0x04C9]=self._nz(m[0x04C9]+1)
                self._a(m[PPU_JOBS])
                self._a(r.a | 0x04)
                m[PPU_JOBS]=r.a
                self._mark(0xDC7D)
                self._rts();return

    def endinguicontroller_dce1(self):
        """$DCE1: endinguicontroller dce1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDCE1)
        self._a(m[UI_PHASE])
        self._flag(C,True)
        self._add(0x01,subtract=True)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._x(0x00)
        while True:  # natural loop $DCEF
            self._a(m[(0xDD05+r.y)&65535])
            m[(0x00BE+r.x)&65535]=r.a
            self._a(m[(0xDD65+r.y)&65535])
            m[(0x0100+r.x)&65535]=r.a
            self._y(r.y+1)
            self._x(r.x+1)
            self._compare(r.x,0x20)
            self._mark(0xDCFF)
            if not r.p&C:
                continue
            else:
                pass
            m[0x04C9]=self._nz(m[0x04C9]+1)
            self._mark(0xDD04)
            self._rts();return


from .scene_initialization import SceneInitialization

MAIN_TARGETS=(0xE09A,0xE0DA,0xE17D,0xE18B,0xE221,0xE22F,0xE2E2,0xE2E8,
              0xE36A,0xE37C,0xE3EB,0xE3EE,0xE3EB,0xE46A,0xE3EB)

class GlobalUIController(SceneInitialization):
    """One main-loop update plus the three banked UI domains.

    run_main ends at the next real E066 boundary, without popping a synthetic
    RTS frame. Battle/attack/duel initialization is the existing independently
    recovered SceneInitialization. Banked callbacks retain their real caller.
    Unknown services, PPU input and fade completion remain explicit waits.
    """
    def __init__(self,memory,rom,services=None):
        self.services=services;self._pending_ui_owner=None;self._pending_ui_call=None
        super().__init__(memory,rom,self._strict_service)
        self.city_workers=CityUIWorkers(memory,rom,services)
        self.title=TitleUIController(memory,rom,services)
        self.rulers=RulerSelectionUIController(memory,rom,services)
        self.ending=EndingUIController(memory,rom,services)
    def _strict_service(self,call):
        if self.services is None:return {'status':'dependency','reason':'Unowned original UI service'}
        result=self.services(call)
        if not isinstance(result,dict)or result.get('status')!='returned':
            return {'status':'dependency','reason':'UI service has not returned explicitly'}
        return result
    def __call__(self,call):
        pair=tuple(call.entry_banks[1:3])
        owner={(29,30):self.city_workers,(10,11):self.title,(8,9):self.rulers,(23,24):self.ending}.get(pair)
        if self._pending_ui_owner is not None and self._pending_ui_call is not call:
            return {'status':'dependency','reason':'Another actual caller owns the pending UI domain'}
        if owner is not None and call.target in owner.PUBLIC_ENTRIES:
            owner.services=self.services
            result=owner(call)
            if result['status']=='returned':self._pending_ui_owner=self._pending_ui_call=None
            elif owner._program is not None:self._pending_ui_owner=owner;self._pending_ui_call=call
            return result
        return {'status':'dependency','reason':'Not a recovered global UI bank/entry','target':call.target}
    def resume(self):
        if self._pending_ui_owner is not None:
            owner=self._pending_ui_owner;owner.services=self.services;result=owner.resume()
            if result['status']=='returned':self._pending_ui_owner=self._pending_ui_call=None
            return result
        return super().resume()
    def run_main(self,entry=0xE066,registers=None):
        if self._pending_ui_owner is not None:raise RuntimeError('Resume the genuine pending banked UI caller first')
        if entry not in (0xE05E,0xE066,*MAIN_TARGETS):raise ValueError('Outside the15 main-state entries')
        def body():
            self.registers.pc=entry
            if entry==0xE05E:
                yield from self.call(0xE05E,0xF3BD);self.a(0);self.memory[0x7A]=0
                yield from self.dispatch_main()
            elif entry==0xE066:yield from self.dispatch_main()
            else:yield from self.main_body(entry)
        return self._start(body,registers,'global_main_boundary')
    tick_main=run_main
    def dispatch_main(self):
        r=self.registers;m=self.memory
        self.a(m[0x7A]);self.a(r.a&31);index=r.a
        if index>=15:raise ValueError('Main007A&31 outside original15 pointer words')
        self.shift_a('asl');self.y(r.a)
        self.a(m[0xE07C+r.y]);m[0x4E]=r.a;self.a(m[0xE07D+r.y]);m[0x4F]=r.a
        target=m[0x4E]|m[0x4F]<<8;r.pc=target
        yield from self.main_body(target)
    def main_body(self,entry):
        r=self.registers;m=self.memory
        if entry==0xE09A:yield from self.boot_display()
        elif entry==0xE0DA:yield from self.city_display()
        elif entry in self.SETUP_ENTRIES:yield from self.setup(entry)
        elif entry in (0xE17D,0xE221):
            pc=0xE17D if entry==0xE17D else 0xE221
            yield from self.call(pc,0xE87A)
            self.y(42 if entry==0xE17D else 40);yield from self.call(pc+5,0xF24B)
            yield from self.call(pc+8,0xA000)
        elif entry in (0xE2E2,0xE36A):yield from self.call(entry,0xE87A)
        elif entry==0xE37C:yield from self.title_display()
        elif entry==0xE3EE:yield from self.ruler_display()
        elif entry==0xE46A:yield from self.ending_display()
        elif entry!=0xE3EB:raise ValueError('Uncatalogued original main-state target')
        r.pc=0xE066
    def boot_display(self):
        r=self.registers;m=self.memory
        yield from self.call(0xE09A,0xE768);yield from self.call(0xE09D,0xE74D)
        yield from self.write(0x2001,r.a,0xE0A0);yield from self.call(0xE0A3,0xE57F)
        self.x(31);self.a(15)
        while True:
            m[0x100+r.x]=r.a;self.x(r.x-1)
            if r.p&N:break
        while True:
            self.a((yield from self.read(0x2002,0xE0B0)))
            if r.p&N:break
        self.a(76);m[0xA5]=r.a;yield from self.write(0xF800,r.a,0xE0BA)
        self.a(0);yield from self.call(0xE0BF,0xE51F)
        self.a(16);m[0x8B]=r.a;yield from self.write(0x2000,r.a,0xE0C7)
        self.a(0);m[0x8C]=r.a;yield from self.write(0x2001,r.a,0xE0CF)
        self.a(9);m[0x7A]=r.a
    def city_display(self):
        r=self.registers;m=self.memory
        yield from self.call(0xE0DA,0xE4DA);self.a(2);m[0x78]=r.a
        self.a(0);yield from self.call(0xE0E4,0xE370)
        self.y(48);yield from self.call(0xE0E9,0xF25F)
        self.a(0);m[0xA]=r.a;self.a(128);m[0xB]=r.a;self.a(32);m[1]=r.a
        self.a(0)
        for address in (0,4,5,6):m[address]=r.a
        self.a(4);m[7]=r.a;yield from self._select_pair(55,0xE110);yield from self.call(0xE113,0xA003)
        yield from self._select_pair(61,0xE118);self.a(0);m[0]=r.a;yield from self.call(0xE120,0xA015)
        yield from self.call(0xE123,0xEAF7);self.a(m[0x400]);self.cmp(r.a,13)
        if not r.p&Z:self.a(255);m[0x6F8B]=r.a
        yield from self._select_pair(61,0xE134);yield from self.call(0xE137,0xA036)
        yield from self.call(0xE13A,0xECBF);yield from self._select_pair(61,0xE13F)
        self.a(0);yield from self.call(0xE144,0xA045);self.a(160);m[0x98]=r.a;self.a(0)
        for address in(0x420,0x4E0,0x4E1,0x4E2,0x4E3):m[address]=r.a
        self.a(240);m[0x6F41]=r.a;self.a(128);m[0x6F3F]=r.a
        self.a(0);yield from self.call(0xE169,0xE51F);self.inc(0x7A)
        self.a(129);yield from self.call(0xE171,0xE673)
        yield from self.call(0xE174,0xE749);yield from self.call(0xE177,0xE753)
    def _raw_background_request(self,selector,pointer,select_pc,call_pc,clear=(0,4,5,6)):
        r=self.registers;m=self.memory;self.y(selector);yield from self.call(select_pc,0xF25F)
        self.a(pointer&255);m[0xA]=r.a;self.a(pointer>>8);m[0xB]=r.a
        self.a(32);m[1]=r.a;self.a(0)
        for address in clear:m[address]=r.a
        self.a(4);m[7]=r.a;yield from self._select_pair(55,call_pc-3);yield from self.call(call_pc,0xA003)
    def title_display(self):
        r=self.registers;m=self.memory;yield from self.call(0xE37C,0xE4DA)
        self.a(6);m[0x78]=r.a;self.a(11);yield from self.call(0xE386,0xE370)
        yield from self._raw_background_request(53,0x9A90,0xE38B,0xE3B5)
        yield from self._select_pair(61,0xE3BA);self.a(11);m[0]=r.a;yield from self.call(0xE3C2,0xA015)
        yield from self.call(0xE3C5,0xEAF7);yield from self.call(0xE3C8,0xECBF)
        yield from self._select_pair(61,0xE3CD);self.a(3);yield from self.call(0xE3D2,0xA045)
        self.a(160);m[0x98]=r.a;self.a(2);yield from self.call(0xE3DC,0xE51F)
        self.inc(0x7A);yield from self.call(0xE3E2,0xE749);yield from self.call(0xE3E5,0xE753)
    def ruler_display(self):
        r=self.registers;m=self.memory;yield from self.call(0xE3EE,0xE4DA)
        self.a(7);m[0x78]=r.a;self.a(12);yield from self.call(0xE3F8,0xE370)
        yield from self._raw_background_request(50,0x9AE3,0xE3FD,0xE427)
        yield from self._select_pair(61,0xE42C);yield from self.call(0xE42F,0xA018)
        yield from self._select_pair(61,0xE434);self.a(12);m[0]=r.a;yield from self.call(0xE43C,0xA015)
        yield from self.call(0xE43F,0xEAF7);yield from self.call(0xE442,0xECBF)
        yield from self._select_pair(61,0xE447);self.a(4);yield from self.call(0xE44C,0xA045)
        self.a(160);m[0x98]=r.a;self.a(2);yield from self.call(0xE456,0xE51F)
        self.inc(0x7A);self.a(8);yield from self.call(0xE45E,0xE683)
        yield from self.call(0xE461,0xE749);yield from self.call(0xE464,0xE753)
    def ending_display(self):
        r=self.registers;m=self.memory;yield from self.call(0xE46A,0xE4DA)
        self.a(8);m[0x78]=r.a;self.a(13);yield from self.call(0xE474,0xE370)
        self.y(54);yield from self.call(0xE479,0xF25F)
        self.a(146);m[0xA]=r.a;self.a(155);m[0xB]=r.a;self.a(0);m[0]=r.a;self.a(32);m[1]=r.a
        yield from self._select_pair(55,0xE492);yield from self.call(0xE495,0xA003)
        yield from self._select_pair(61,0xE49A);self.a(13);m[0]=r.a;yield from self.call(0xE4A2,0xA015)
        yield from self.call(0xE4A5,0xEAF7);yield from self._select_pair(61,0xE4AA)
        self.a(5);yield from self.call(0xE4AF,0xA045);self.a(160);m[0x98]=r.a
        self.a(2);yield from self.call(0xE4B9,0xE51F);self.inc(0x7A);self.y(m[0x541])
        if r.y:self.a(170);yield from self.call(0xE4CE,0xE67B)
        else:self.a(152);yield from self.call(0xE4C6,0xE673)
        yield from self.call(0xE4D1,0xE749);yield from self.call(0xE4D4,0xE753)
