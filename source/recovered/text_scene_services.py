"""Readable, bounded bank29 text and nametable packet services.

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
TEXT_PROGRESS,TEXT_CURSOR,MESSAGE_HEAD=0x300,0x304,0x310
NEW_BUTTONS,GLOBAL,PPU_JOBS=0x81,0x7A,0x7E

@dataclass
class TextRegisters:
    a:int=0
    x:int=0
    y:int=0
    sp:int=0xFD
    p:int=U
    pc:int=0xA003

class TextSceneServices:
    def __init__(self,memory,rom,services=None):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned battle ROM required')
        self.memory=memory;self.rom=bytes(rom);self.services=services
        self.registers=TextRegisters();self.events=[];self.pending=None;self._program=None
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
            if isinstance(self.pending,ServiceWait):self.pending=None
            if self.pending is not None:
                call=self.pending
                if self.services is None:return self._result('dependency')
                result=self.services(call)
                if not isinstance(result,dict)or result.get('status')!='returned':return self._result('dependency')
                if self.registers.pc!=call.return_pc or self.registers.sp!=call.expected_sp:return self._result('dependency')
                self.pending=None
            try:
                self.pending=next(self._program)
                if isinstance(self.pending,ServiceWait):return self._result("dependency")
            except StopIteration:
                self._program=None
                if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:return self._result('nonlocal_return')
                return self._result('returned')
    def _result(self,status):
        return dict(status=status,before=self._before,after=(self.memory[TEXT_PROGRESS],self.memory[TEXT_CURSOR],self.memory[MESSAGE_HEAD]),
                    control_blocks=self._blocks,events=list(self.events),pending=self.pending)
    def resume(self):
        if self._program is None:raise RuntimeError('No pending battle invocation')
        return self._drive()
    def tick(self,registers=None,**kwargs):return self.run_entry(0xA000,registers=registers,**kwargs)
    def run_entry(self,entry=0xA003,*,registers=None,seed_return=False,return_pc=None,max_blocks=200000):
        if self._program is not None:raise RuntimeError('Resume the existing battle invocation first')
        self.registers=registers or TextRegisters();r=self.registers
        if r.p&D:raise ValueError('NES binary arithmetic requires D=0')
        if seed_return:
            if return_pc not in(None,0x0200):raise ValueError('Synthetic fixture return only permits0200')
            self.memory[0x1FE:0x200]=bytes((255,1));r.sp=0xFD
        self._return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535 if return_pc is None else return_pc;self._return_sp=(r.sp+2)&255;self._before=(self.memory[TEXT_PROGRESS],self.memory[TEXT_CURSOR],self.memory[MESSAGE_HEAD])
        self.events=[];self.pending=None;self._blocks=0;self._limit=max_blocks;r.pc=entry
        self._program=self._entry(entry)
        return self._drive()

    PUBLIC_ENTRIES=(0xA000,0xA003,0xA006,0xA048,0xA11B,0xA154,0xA158,0xEE72)
    def __call__(self,call):
        if (tuple(call.entry_banks[1:3])!=(29,30)and call.target!=0xEE72)or call.target not in self.PUBLIC_ENTRIES:
            return {'status':'dependency','reason':'Not an exact bank29 text/packet entry'}
        if self._program is not None:
            if self._call_owner is not call:return {'status':'dependency','reason':'Another caller owns the pending text read'}
            return self.resume()
        self._call_owner=call
        return self.run_entry(call.target,registers=call.registers,return_pc=call.return_pc)
    def _hardware_read(self,address,pc):
        while True:
            self.registers.pc=pc
            try:return self.memory[address]
            except UnsupportedHardware as exc:yield ServiceWait('hardware_read',pc,address,reason=str(exc))

    def _entry(self,entry):
        if entry==0xA000:return self.text_consumer_entry()
        elif entry==0xA003:return self.text_producer_entry()
        elif entry==0xA006:return self.packet_consumer_entry()
        elif entry==0xA048:return self.consume_text()
        elif entry==0xA11B:return self.consume_nametable_packets()
        elif entry==0xA132:return self.next_nametable_packet()
        elif entry==0xA146:return self.write_nametable_packet_tiles()
        elif entry==0xA154:return self.produce_text()
        elif entry==0xA158:return self.begin_text_row()
        elif entry==0xA1C8:return self.parse_text_tokens()
        elif entry==0xA1DF:return self.advance_text_pointer()
        elif entry==0xA1E8:return self.emit_text_symbol()
        elif entry==0xA248:return self.end_message()
        elif entry==0xA281:return self.next_text_row()
        elif entry==0xA2A3:return self.enter_nested_message()
        elif entry==0xA2C2:return self.restore_nested_message()
        elif entry==0xA2DD:return self.enable_burst()
        elif entry==0xA2E5:return self.disable_burst()
        elif entry==0xA2ED:return self.set_next_position()
        elif entry==0xA310:return self.disable_accents()
        elif entry==0xA318:return self.enable_accents()
        elif entry==0xA320:return self.set_symbol_offset()
        elif entry==0xA32D:return self.report_officer_name()
        elif entry==0xA397:return self.parameterized_officer_name()
        elif entry==0xA3B1:return self.report_decimal_number()
        elif entry==0xA411:return self.text_helper_a411()
        elif entry==0xA41A:return self.text_helper_a41a()
        elif entry==0xA426:return self.fixed_city_name()
        elif entry==0xA4B0:return self.fixed_officer_name()
        elif entry==0xA53E:return self.formatted_field_number()
        elif entry==0xA5DE:return self.text_helper_a5de()
        elif entry==0xA5F4:return self.text_helper_a5f4()
        elif entry==0xA60F:return self.clear_text_rows()
        elif entry==0xA61D:return self.message_pointer()
        elif entry==0xA690:return self.select_message_window()
        elif entry==0xEE72:return self.palette_cadence_tail()
        raise ValueError("Entry outside the bounded text service catalog")

    def text_consumer_entry(self):
        """$A000: text consumer entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA000)
        return (yield from self.consume_text())

    def text_producer_entry(self):
        """$A003: text producer entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA003)
        return (yield from self.produce_text())

    def packet_consumer_entry(self):
        """$A006: packet consumer entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA006)
        return (yield from self.consume_nametable_packets())

    def consume_text(self):
        """$A048: consume text; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA048)
        self._a(m[PPU_JOBS])
        self._a(r.a & 0x04)
        self._mark(0xA04D)
        if r.p&Z:
            self._a(m[0x0303])
            self._mark(0xA053)
            if r.p&Z:
                self._a(m[0x0308])
                self._mark(0xA05B)
                if r.p&Z:
                    self._a(m[0x005E])
                    self._a(r.a & m[0x0305])
                    self._mark(0xA066)
                    if r.p&Z:
                        self._y(m[0x0304])
                        self._a(m[(0x034E+r.y)&65535])
                        self._compare(r.a,0x80)
                        self._mark(0xA073)
                        if r.p&Z:
                            self._a(0xFF)
                            m[0x0304]=r.a
                            self._a(m[PPU_JOBS])
                            self._a(r.a & 0xFE)
                            m[PPU_JOBS]=r.a
                            self._mark(0xA0C3)
                            self._rts();return
                        else:
                            self._a((yield from self._hardware_read(0x2002,0xA075)))
                            self._a(m[0x031D])
                            m[0x2006]=r.a
                            self._a(m[0x031C])
                            self._flag(C,False)
                            self._add(m[0x0304])
                            m[0x2006]=r.a
                            self._y(m[0x0304])
                            self._a(m[(0x031E+r.y)&65535])
                            m[0x2007]=r.a
                            self._a(m[0x030C])
                            self._mark(0xA094)
                            if not r.p&Z:
                                pass
                            else:
                                self._a((yield from self._hardware_read(0x2002,0xA096)))
                                self._a(m[0x034D])
                                m[0x2006]=r.a
                                self._a(m[0x034C])
                                self._flag(C,False)
                                self._add(m[0x0304])
                                m[0x2006]=r.a
                                self._y(m[0x0304])
                                self._a(m[(0x034E+r.y)&65535])
                                m[0x2007]=r.a
                                pass
                            m[0x0304]=self._nz(m[0x0304]+1)
                            self._mark(0xA0B5)
                            self._rts();return
                    else:
                        self._mark(0xA068)
                        yield from self._external(0xA068,0xEE72,None,"tail")
                        return
                else:
                    self._a((yield from self._hardware_read(0x2002,0xA0C4)))
                    self._a(m[0x031D])
                    m[0x2006]=r.a
                    self._a(m[0x031C])
                    m[0x2006]=r.a
                    self._y(0x00)
                    while True:  # natural loop $A0D5
                        self._a(m[(0x031E+r.y)&65535])
                        self._compare(r.a,0x80)
                        self._mark(0xA0DA)
                        if r.p&Z:
                            pass
                        else:
                            m[0x2007]=r.a
                            self._y(r.y+1)
                            continue
                        self._a(m[0x030C])
                        self._mark(0xA0E6)
                        if not r.p&Z:
                            pass
                        else:
                            self._a((yield from self._hardware_read(0x2002,0xA0E8)))
                            self._a(m[0x034D])
                            m[0x2006]=r.a
                            self._a(m[0x034C])
                            m[0x2006]=r.a
                            self._y(0x00)
                            while True:  # natural loop $A0F9
                                self._a(m[(0x034E+r.y)&65535])
                                self._compare(r.a,0x80)
                                self._mark(0xA0FE)
                                if r.p&Z:
                                    pass
                                else:
                                    m[0x2007]=r.a
                                    self._y(r.y+1)
                                    continue
                                self._a(0xFF)
                                m[0x0304]=r.a
                                self._a(m[PPU_JOBS])
                                self._a(r.a & 0xFE)
                                m[PPU_JOBS]=r.a
                                self._mark(0xA0C3)
                                self._rts();return
                        self._a(0xFF)
                        m[0x0304]=r.a
                        self._a(m[PPU_JOBS])
                        self._a(r.a & 0xFE)
                        m[PPU_JOBS]=r.a
                        self._mark(0xA0C3)
                        self._rts();return
            else:
                self._a((yield from self._hardware_read(0x2002,0xA0C4)))
                self._a(m[0x031D])
                m[0x2006]=r.a
                self._a(m[0x031C])
                m[0x2006]=r.a
                self._y(0x00)
                while True:  # natural loop $A0D5
                    self._a(m[(0x031E+r.y)&65535])
                    self._compare(r.a,0x80)
                    self._mark(0xA0DA)
                    if r.p&Z:
                        pass
                    else:
                        m[0x2007]=r.a
                        self._y(r.y+1)
                        continue
                    self._a(m[0x030C])
                    self._mark(0xA0E6)
                    if not r.p&Z:
                        pass
                    else:
                        self._a((yield from self._hardware_read(0x2002,0xA0E8)))
                        self._a(m[0x034D])
                        m[0x2006]=r.a
                        self._a(m[0x034C])
                        m[0x2006]=r.a
                        self._y(0x00)
                        while True:  # natural loop $A0F9
                            self._a(m[(0x034E+r.y)&65535])
                            self._compare(r.a,0x80)
                            self._mark(0xA0FE)
                            if r.p&Z:
                                pass
                            else:
                                m[0x2007]=r.a
                                self._y(r.y+1)
                                continue
                            self._a(0xFF)
                            m[0x0304]=r.a
                            self._a(m[PPU_JOBS])
                            self._a(r.a & 0xFE)
                            m[PPU_JOBS]=r.a
                            self._mark(0xA0C3)
                            self._rts();return
                    self._a(0xFF)
                    m[0x0304]=r.a
                    self._a(m[PPU_JOBS])
                    self._a(r.a & 0xFE)
                    m[PPU_JOBS]=r.a
                    self._mark(0xA0C3)
                    self._rts();return
        else:
            self._mark(0xA04F)
            self._rts();return

    def consume_nametable_packets(self):
        """$A11B: consume nametable packets; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA11B)
        self._a(m[0x008B])
        self._a(r.a & 0xFB)
        m[0x2000]=r.a
        self._a(0x80)
        m[0x0000]=r.a
        self._a(0x03)
        m[0x0001]=r.a
        self._a((yield from self._hardware_read(0x2002,0xA12D)))
        self._y(0x00)
        return (yield from self.next_nametable_packet())

    def next_nametable_packet(self):
        """$A132: next nametable packet; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA132)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._compare(r.a,0xFF)
        self._mark(0xA136)
        if r.p&Z:
            self._mark(0xA152)
            self._rts();return
        else:
            self._y(r.y+1)
            self._x(r.a)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x2006]=r.a
            self._y(r.y+1)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x2006]=r.a
            self._y(r.y+1)
            return (yield from self.write_nametable_packet_tiles())

    def write_nametable_packet_tiles(self):
        """$A146: write nametable packet tiles; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        while True:  # natural loop $A146
            self._mark(0xA146)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x2007]=r.a
            self._y(r.y+1)
            self._x(r.x-1)
            self._mark(0xA14D)
            if not r.p&Z:
                continue
            else:
                pass
            return (yield from self.next_nametable_packet())

    def produce_text(self):
        """$A154: produce text; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA154)
        if not (yield from self._local_call(self.begin_text_row,0xA154,0xA157)):return
        self._mark(0xA157)
        self._rts();return

    def begin_text_row(self):
        """$A158: begin text row; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA158)
        self._a(m[NEW_BUTTONS])
        self._a(r.a & 0x01)
        self._mark(0xA15D)
        if r.p&Z:
            pass
        else:
            self._a(0x01)
            m[0x0308]=r.a
            pass
        self._a(m[0x0300])
        self._compare(r.a,0xFF)
        self._mark(0xA169)
        if r.p&Z:
            self._mark(0xA153)
            self._rts();return
        else:
            self._a(m[PPU_JOBS])
            self._a(r.a & 0x01)
            self._mark(0xA170)
            if not r.p&Z:
                self._mark(0xA153)
                self._rts();return
            else:
                self._a(0x00)
                m[0x0304]=r.a
                if not (yield from self._local_call(self.select_message_window,0xA177,0xA17A)):return
                self._a(m[0x0300])
                self._mark(0xA17D)
                if not r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.message_pointer,0xA17F,0xA182)):return
                    self._y(0x00)
                    self._a(m[((m[0xA6]|m[0xA7]<<8)+r.y)&65535])
                    m[0x0306]=r.a
                    if not (yield from self._local_call(self.advance_text_pointer,0xA189,0xA18C)):return
                    self._a(m[((m[0xA6]|m[0xA7]<<8)+r.y)&65535])
                    m[0x0307]=r.a
                    if not (yield from self._local_call(self.advance_text_pointer,0xA191,0xA194)):return
                    self._a(0x01)
                    m[0x0300]=r.a
                    self._a(0x00)
                    m[0x0303]=r.a
                    m[0x0308]=r.a
                    m[0x030C]=r.a
                    m[0x030F]=r.a
                    self._a(0x03)
                    m[0x0305]=r.a
                    pass
                if not (yield from self._local_call(self.clear_text_rows,0xA1AC,0xA1AF)):return
                self._a(m[0x0306])
                m[0x031C]=r.a
                self._flag(C,True)
                self._add(0x20,subtract=True)
                m[0x034C]=r.a
                self._a(m[0x0307])
                m[0x031D]=r.a
                self._add(0x00,subtract=True)
                m[0x034D]=r.a
                self._x(0x02)
                return (yield from self.parse_text_tokens())

    def parse_text_tokens(self):
        """$A1C8: parse text tokens; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        while True:  # natural loop $A1C8
            self._mark(0xA1C8)
            self._y(0x00)
            self._a(m[((m[0xA6]|m[0xA7]<<8)+r.y)&65535])
            if not (yield from self._local_call(self.advance_text_pointer,0xA1CC,0xA1CF)):return
            m[0x0012]=r.a
            self._y(r.a)
            self._mark(0xA1D3)
            if not r.p&N:
                if not (yield from self._local_call(self.emit_text_symbol,0xA1D9,0xA1DC)):return
                continue
            else:
                pass
            self._compare(r.a,0xC0)
            self._mark(0xA1D7)
            if not r.p&C:
                pass
            else:
                if not (yield from self._local_call(self.emit_text_symbol,0xA1D9,0xA1DC)):return
                continue
            self._flag(C,True)
            self._add(0x80,subtract=True)
            self._mark(0xA205)
            index=self._dispatch(0xA205,(41544, 41601, 41635, 41666, 41693, 41701, 41709, 41744, 41752, 41760, 41709, 41709, 41709, 41709, 41709, 41709, 41773, 41773, 41773, 41773, 41773, 41773, 41773, 41773, 41905, 41905, 41905, 41905, 42022, 42160, 42302, 41879))
            return (yield from (self.end_message,self.next_text_row,self.enter_nested_message,self.restore_nested_message,self.enable_burst,self.disable_burst,self.set_next_position,self.disable_accents,self.enable_accents,self.set_symbol_offset,self.set_next_position,self.set_next_position,self.set_next_position,self.set_next_position,self.set_next_position,self.set_next_position,self.report_officer_name,self.report_officer_name,self.report_officer_name,self.report_officer_name,self.report_officer_name,self.report_officer_name,self.report_officer_name,self.report_officer_name,self.report_decimal_number,self.report_decimal_number,self.report_decimal_number,self.report_decimal_number,self.fixed_city_name,self.fixed_officer_name,self.formatted_field_number,self.parameterized_officer_name,)[index]())

    def advance_text_pointer(self):
        """$A1DF: advance text pointer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA1DF)
        m[0x00A6]=self._nz(m[0x00A6]+1)
        self._mark(0xA1E2)
        if not r.p&Z:
            pass
        else:
            m[0x00A7]=self._nz(m[0x00A7]+1)
            pass
        self._mark(0xA1E7)
        self._rts();return

    def emit_text_symbol(self):
        """$A1E8: emit text symbol; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA1E8)
        self._y(m[0x030C])
        self._mark(0xA1EB)
        if not r.p&Z:
            self._flag(C,False)
            self._add(m[0x030F])
            m[(0x031C+r.x)&65535]=r.a
            self._x(r.x+1)
            self._mark(0xA1FD)
            self._rts();return
        else:
            self._compare(r.a,0x39)
            self._mark(0xA1EF)
            if r.p&Z:
                m[(0x034B+r.x)&65535]=r.a
                self._mark(0xA201)
                self._rts();return
            else:
                self._compare(r.a,0x3A)
                self._mark(0xA1F3)
                if r.p&Z:
                    m[(0x034B+r.x)&65535]=r.a
                    self._mark(0xA201)
                    self._rts();return
                else:
                    self._flag(C,False)
                    self._add(m[0x030F])
                    m[(0x031C+r.x)&65535]=r.a
                    self._x(r.x+1)
                    self._mark(0xA1FD)
                    self._rts();return

    def end_message(self):
        """$A248: end message; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA248)
        self._a(0xFF)
        m[0x0300]=r.a
        self._a(0x80)
        m[(0x031C+r.x)&65535]=r.a
        m[(0x034C+r.x)&65535]=r.a
        self._a(m[PPU_JOBS])
        self._a(r.a | 0x01)
        m[PPU_JOBS]=r.a
        self._a(m[0x0311])
        m[0x0310]=r.a
        self._a(m[0x0312])
        m[0x0311]=r.a
        self._a(m[0x0313])
        m[0x0312]=r.a
        self._a(0xFF)
        m[0x0313]=r.a
        self._a(m[0x0310])
        self._compare(r.a,0xFF)
        self._mark(0xA279)
        if r.p&Z:
            pass
        else:
            self._a(0x00)
            m[0x0300]=r.a
            pass
        self._mark(0xA280)
        self._rts();return

    def next_text_row(self):
        """$A281: next text row; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA281)
        self._a(0x80)
        m[(0x031C+r.x)&65535]=r.a
        m[(0x034C+r.x)&65535]=r.a
        self._a(m[0x0306])
        self._flag(C,False)
        self._add(0x40)
        m[0x0306]=r.a
        self._a(m[0x0307])
        self._add(0x00)
        m[0x0307]=r.a
        self._a(m[PPU_JOBS])
        self._a(r.a | 0x01)
        m[PPU_JOBS]=r.a
        self._mark(0xA2A2)
        self._rts();return

    def enter_nested_message(self):
        """$A2A3: enter nested message; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA2A3)
        self._a(m[0x0310])
        m[0x0309]=r.a
        self._a(m[0x00A6])
        m[0x030A]=r.a
        self._a(m[0x00A7])
        m[0x030B]=r.a
        self._y(0x00)
        self._a(m[((m[0xA6]|m[0xA7]<<8)+r.y)&65535])
        m[0x0310]=r.a
        if not (yield from self._local_call(self.message_pointer,0xA2BC,0xA2BF)):return
        return (yield from self.parse_text_tokens())

    def restore_nested_message(self):
        """$A2C2: restore nested message; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA2C2)
        self._a(m[0x0309])
        m[0x0310]=r.a
        if not (yield from self._local_call(self.message_pointer,0xA2C8,0xA2CB)):return
        self._a(m[0x030A])
        m[0x00A6]=r.a
        self._a(m[0x030B])
        m[0x00A7]=r.a
        if not (yield from self._local_call(self.advance_text_pointer,0xA2D7,0xA2DA)):return
        return (yield from self.parse_text_tokens())

    def enable_burst(self):
        """$A2DD: enable burst; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA2DD)
        self._a(0x80)
        m[0x0303]=r.a
        return (yield from self.parse_text_tokens())

    def disable_burst(self):
        """$A2E5: disable burst; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA2E5)
        self._a(0x00)
        m[0x0303]=r.a
        return (yield from self.parse_text_tokens())

    def set_next_position(self):
        """$A2ED: set next position; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA2ED)
        self._y(0x00)
        self._a(m[((m[0xA6]|m[0xA7]<<8)+r.y)&65535])
        m[0x0306]=r.a
        if not (yield from self._local_call(self.advance_text_pointer,0xA2F4,0xA2F7)):return
        self._a(m[((m[0xA6]|m[0xA7]<<8)+r.y)&65535])
        m[0x0307]=r.a
        if not (yield from self._local_call(self.advance_text_pointer,0xA2FC,0xA2FF)):return
        self._a(0x80)
        m[(0x031C+r.x)&65535]=r.a
        m[(0x034C+r.x)&65535]=r.a
        self._a(m[PPU_JOBS])
        self._a(r.a | 0x01)
        m[PPU_JOBS]=r.a
        self._mark(0xA30F)
        self._rts();return

    def disable_accents(self):
        """$A310: disable accents; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA310)
        self._a(0x01)
        m[0x030C]=r.a
        return (yield from self.parse_text_tokens())

    def enable_accents(self):
        """$A318: enable accents; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA318)
        self._a(0x00)
        m[0x030C]=r.a
        return (yield from self.parse_text_tokens())

    def set_symbol_offset(self):
        """$A320: set symbol offset; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA320)
        self._y(0x00)
        self._a(m[((m[0xA6]|m[0xA7]<<8)+r.y)&65535])
        m[0x030F]=r.a
        if not (yield from self._local_call(self.advance_text_pointer,0xA327,0xA32A)):return
        return (yield from self.parse_text_tokens())

    def report_officer_name(self):
        """$A32D: report officer name; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA32D)
        self._a(m[0x00E1])
        self._push(r.a)
        self._y(0x30)
        yield from self._external(0xA333,0xF25F,0xA336,"call",None)
        if r.pc!=0xA336:return  # preserve nonlocal stack return
        self._a(0x00)
        m[0x0001]=r.a
        self._a(m[0x0012])
        self._flag(C,True)
        self._add(0x90,subtract=True)
        self._y(r.a)
        self._a(0x00)
        m[0x0001]=r.a
        self._a(m[(0x042C+r.y)&65535])
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        self._flag(C,False)
        self._add(m[(0x042C+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[0x0001])
        self._add(0x00)
        m[0x0001]=r.a
        m[0x0000]=self._shift(m[0x0000],True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        self._a(m[0x0000])
        self._flag(C,False)
        self._add(0x1A)
        m[0x0000]=r.a
        self._a(m[0x0001])
        self._add(0x90)
        m[0x0001]=r.a
        self._y(0x00)
        while True:  # natural loop $A37A
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._mark(0xA37C)
            if r.p&Z:
                pass
            else:
                m[0x0002]=r.a
                self._a(r.y)
                self._push(r.a)
                self._a(m[0x0002])
                if not (yield from self._local_call(self.emit_text_symbol,0xA386,0xA389)):return
                self._a(self._pop())
                self._y(r.a)
                self._y(r.y+1)
                continue
            self._a(self._pop())
            self._y(r.a)
            yield from self._external(0xA391,0xF25F,0xA394,"call",None)
            if r.pc!=0xA394:return  # preserve nonlocal stack return
            return (yield from self.parse_text_tokens())

    def parameterized_officer_name(self):
        """$A397: parameterized officer name; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA397)
        self._a(m[0x00E1])
        self._push(r.a)
        self._y(0x00)
        self._a(m[((m[0xA6]|m[0xA7]<<8)+r.y)&65535])
        self._push(r.a)
        if not (yield from self._local_call(self.advance_text_pointer,0xA3A0,0xA3A3)):return
        self._y(0x30)
        yield from self._external(0xA3A5,0xF25F,0xA3A8,"call",None)
        if r.pc!=0xA3A8:return  # preserve nonlocal stack return
        self._a(0x00)
        m[0x0001]=r.a
        self._a(self._pop())
        self._y(r.a)
        self._a(0x00)
        m[0x0001]=r.a
        self._a(m[(0x042C+r.y)&65535])
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        self._flag(C,False)
        self._add(m[(0x042C+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[0x0001])
        self._add(0x00)
        m[0x0001]=r.a
        m[0x0000]=self._shift(m[0x0000],True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        self._a(m[0x0000])
        self._flag(C,False)
        self._add(0x1A)
        m[0x0000]=r.a
        self._a(m[0x0001])
        self._add(0x90)
        m[0x0001]=r.a
        self._y(0x00)
        while True:  # natural loop $A37A
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._mark(0xA37C)
            if r.p&Z:
                pass
            else:
                m[0x0002]=r.a
                self._a(r.y)
                self._push(r.a)
                self._a(m[0x0002])
                if not (yield from self._local_call(self.emit_text_symbol,0xA386,0xA389)):return
                self._a(self._pop())
                self._y(r.a)
                self._y(r.y+1)
                continue
            self._a(self._pop())
            self._y(r.a)
            yield from self._external(0xA391,0xF25F,0xA394,"call",None)
            if r.pc!=0xA394:return  # preserve nonlocal stack return
            return (yield from self.parse_text_tokens())

    def report_decimal_number(self):
        """$A3B1: report decimal number; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA3B1)
        self._a(m[0x0012])
        self._flag(C,True)
        self._add(0x98,subtract=True)
        m[0x0000]=r.a
        r.a=self._shift(r.a,True,rotate=False)
        self._flag(C,False)
        self._add(m[0x0000])
        self._y(r.a)
        self._a(m[(0x042C+r.y)&65535])
        m[0x0001]=r.a
        self._a(m[(0x042D+r.y)&65535])
        m[0x0002]=r.a
        self._a(m[(0x042E+r.y)&65535])
        m[0x0003]=r.a
        self._a(r.x)
        self._push(r.a)
        yield from self._external(0xA3D4,0xE9BA,0xA3D7,"call",None)
        if r.pc!=0xA3D7:return  # preserve nonlocal stack return
        self._a(self._pop())
        self._x(r.a)
        self._a(0x00)
        m[0x0000]=r.a
        self._a(m[0x0009])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        if not (yield from self._local_call(self.text_helper_a411,0xA3E5,0xA3E8)):return
        self._a(m[0x0009])
        if not (yield from self._local_call(self.text_helper_a411,0xA3EB,0xA3EE)):return
        self._a(m[0x0008])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        if not (yield from self._local_call(self.text_helper_a411,0xA3F5,0xA3F8)):return
        self._a(m[0x0008])
        if not (yield from self._local_call(self.text_helper_a411,0xA3FB,0xA3FE)):return
        self._a(m[0x0007])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        if not (yield from self._local_call(self.text_helper_a411,0xA405,0xA408)):return
        self._a(m[0x0007])
        if not (yield from self._local_call(self.text_helper_a41a,0xA40B,0xA40E)):return
        return (yield from self.parse_text_tokens())

    def text_helper_a411(self):
        """$A411: text helper a411; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA411)
        self._y(m[0x0000])
        self._mark(0xA414)
        if not r.p&Z:
            return (yield from self.text_helper_a41a())
        else:
            self._a(r.a & 0x0F)
            self._mark(0xA418)
            if r.p&Z:
                self._mark(0xA425)
                self._rts();return
            else:
                return (yield from self.text_helper_a41a())

    def text_helper_a41a(self):
        """$A41A: text helper a41a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA41A)
        self._a(r.a & 0x0F)
        self._flag(C,False)
        self._add(0x76)
        if not (yield from self._local_call(self.emit_text_symbol,0xA41F,0xA422)):return
        m[0x0000]=self._nz(m[0x0000]+1)
        self._mark(0xA425)
        self._rts();return

    def fixed_city_name(self):
        """$A426: fixed city name; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA426)
        self._a(m[0x00E1])
        self._push(r.a)
        self._y(0x00)
        self._a(m[((m[0xA6]|m[0xA7]<<8)+r.y)&65535])
        self._push(r.a)
        if not (yield from self._local_call(self.advance_text_pointer,0xA42F,0xA432)):return
        self._y(0x30)
        yield from self._external(0xA434,0xF25F,0xA437,"call",None)
        if r.pc!=0xA437:return  # preserve nonlocal stack return
        self._a(0x00)
        m[0x0001]=r.a
        self._a(self._pop())
        self._y(r.a)
        self._a(0x00)
        m[0x0001]=r.a
        self._a(m[(0x042C+r.y)&65535])
        self._mark(0xA446)
        if not r.p&N:
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            self._flag(C,False)
            self._add(0x1A)
            m[0x0000]=r.a
            self._a(0x00)
            self._add(0x9A)
            m[0x0001]=r.a
            self._y(0x00)
            m[0x0003]=r.y
            while True:  # natural loop $A475
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._mark(0xA477)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x01)
                    pass
                m[0x0002]=r.a
                self._a(r.y)
                self._push(r.a)
                self._a(m[0x0002])
                self._compare(r.a,0x39)
                self._mark(0xA485)
                if r.p&Z:
                    m[0x0003]=self._nz(m[0x0003]+1)
                    pass
                else:
                    self._compare(r.a,0x3A)
                    self._mark(0xA489)
                    if not r.p&Z:
                        pass
                    else:
                        m[0x0003]=self._nz(m[0x0003]+1)
                        pass
                    pass
                if not (yield from self._local_call(self.emit_text_symbol,0xA48E,0xA491)):return
                self._a(self._pop())
                self._y(r.a)
                self._y(r.y+1)
                self._compare(r.y,0x06)
                self._mark(0xA496)
                if not r.p&C:
                    continue
                else:
                    pass
                while True:  # natural loop $A498
                    self._a(m[0x0003])
                    self._mark(0xA49B)
                    if r.p&Z:
                        pass
                    else:
                        self._a(0x01)
                        if not (yield from self._local_call(self.emit_text_symbol,0xA49F,0xA4A2)):return
                        m[0x0003]=self._nz(m[0x0003]-1)
                        continue
                    self._a(self._pop())
                    self._y(r.a)
                    yield from self._external(0xA4AA,0xF25F,0xA4AD,"call",None)
                    if r.pc!=0xA4AD:return  # preserve nonlocal stack return
                    return (yield from self.parse_text_tokens())
        else:
            self._a(0x00)
            while True:  # natural loop $A44A
                self._push(r.a)
                self._a(0x01)
                if not (yield from self._local_call(self.emit_text_symbol,0xA44D,0xA450)):return
                self._a(self._pop())
                self._flag(C,False)
                self._add(0x01)
                self._compare(r.a,0x06)
                self._mark(0xA456)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(self._pop())
                self._y(r.a)
                yield from self._external(0xA45A,0xF25F,0xA45D,"call",None)
                if r.pc!=0xA45D:return  # preserve nonlocal stack return
                return (yield from self.parse_text_tokens())

    def fixed_officer_name(self):
        """$A4B0: fixed officer name; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA4B0)
        self._a(m[0x00E1])
        self._push(r.a)
        self._y(0x00)
        self._a(m[((m[0xA6]|m[0xA7]<<8)+r.y)&65535])
        self._push(r.a)
        if not (yield from self._local_call(self.advance_text_pointer,0xA4B9,0xA4BC)):return
        self._y(0x30)
        yield from self._external(0xA4BE,0xF25F,0xA4C1,"call",None)
        if r.pc!=0xA4C1:return  # preserve nonlocal stack return
        self._a(0x00)
        m[0x0001]=r.a
        self._a(self._pop())
        self._y(r.a)
        self._a(0x00)
        m[0x0001]=r.a
        self._a(m[(0x042C+r.y)&65535])
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        self._flag(C,False)
        self._add(m[(0x042C+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[0x0001])
        self._add(0x00)
        m[0x0001]=r.a
        m[0x0000]=self._shift(m[0x0000],True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        self._a(m[0x0000])
        self._flag(C,False)
        self._add(0x1A)
        m[0x0000]=r.a
        self._a(m[0x0001])
        self._add(0x90)
        m[0x0001]=r.a
        self._y(0x00)
        m[0x0003]=r.y
        while True:  # natural loop $A503
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._mark(0xA505)
            if not r.p&Z:
                pass
            else:
                self._a(0x01)
                pass
            m[0x0002]=r.a
            self._a(r.y)
            self._push(r.a)
            self._a(m[0x0002])
            self._compare(r.a,0x39)
            self._mark(0xA513)
            if r.p&Z:
                m[0x0003]=self._nz(m[0x0003]+1)
                pass
            else:
                self._compare(r.a,0x3A)
                self._mark(0xA517)
                if not r.p&Z:
                    pass
                else:
                    m[0x0003]=self._nz(m[0x0003]+1)
                    pass
                pass
            if not (yield from self._local_call(self.emit_text_symbol,0xA51C,0xA51F)):return
            self._a(self._pop())
            self._y(r.a)
            self._y(r.y+1)
            self._compare(r.y,0x07)
            self._mark(0xA524)
            if not r.p&C:
                continue
            else:
                pass
            while True:  # natural loop $A526
                self._a(m[0x0003])
                self._mark(0xA529)
                if r.p&Z:
                    pass
                else:
                    self._a(0x01)
                    if not (yield from self._local_call(self.emit_text_symbol,0xA52D,0xA530)):return
                    m[0x0003]=self._nz(m[0x0003]-1)
                    continue
                self._a(self._pop())
                self._y(r.a)
                yield from self._external(0xA538,0xF25F,0xA53B,"call",None)
                if r.pc!=0xA53B:return  # preserve nonlocal stack return
                return (yield from self.parse_text_tokens())

    def formatted_field_number(self):
        """$A53E: formatted field number; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA53E)
        self._a(0x00)
        m[0x0010]=r.a
        self._y(0x00)
        self._a(m[((m[0xA6]|m[0xA7]<<8)+r.y)&65535])
        self._push(r.a)
        if not (yield from self._local_call(self.advance_text_pointer,0xA548,0xA54B)):return
        self._a(self._pop())
        m[0x0000]=r.a
        r.a=self._shift(r.a,True,rotate=False)
        self._flag(C,False)
        self._add(m[0x0000])
        self._y(r.a)
        self._a(m[(0x044C+r.y)&65535])
        m[0x0001]=r.a
        self._a(m[(0x044D+r.y)&65535])
        m[0x0002]=r.a
        self._a(m[(0x044E+r.y)&65535])
        self._compare(r.a,0xFE)
        self._mark(0xA566)
        if not r.p&Z:
            self._compare(r.a,0xFF)
            self._mark(0xA57F)
            if not r.p&Z:
                pass
            else:
                m[0x0010]=self._nz(m[0x0010]+1)
                self._a(0x00)
                m[0x0001]=r.a
                m[0x0002]=r.a
                pass
            m[0x0003]=r.a
            self._a(r.x)
            self._push(r.a)
            yield from self._external(0xA591,0xE9BA,0xA594,"call",None)
            if r.pc!=0xA594:return  # preserve nonlocal stack return
            self._a(self._pop())
            self._x(r.a)
            self._y(0x00)
            self._a(m[((m[0xA6]|m[0xA7]<<8)+r.y)&65535])
            self._push(r.a)
            if not (yield from self._local_call(self.advance_text_pointer,0xA59B,0xA59E)):return
            self._a(self._pop())
            self._y(r.a)
            self._a(m[(0xA607+r.y)&65535])
            m[0x0001]=r.a
            self._a(0x00)
            m[0x0000]=r.a
            self._a(m[0x0009])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            if not (yield from self._local_call(self.text_helper_a5de,0xA5B2,0xA5B5)):return
            self._a(m[0x0009])
            if not (yield from self._local_call(self.text_helper_a5de,0xA5B8,0xA5BB)):return
            self._a(m[0x0008])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            if not (yield from self._local_call(self.text_helper_a5de,0xA5C2,0xA5C5)):return
            self._a(m[0x0008])
            if not (yield from self._local_call(self.text_helper_a5de,0xA5C8,0xA5CB)):return
            self._a(m[0x0007])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            if not (yield from self._local_call(self.text_helper_a5de,0xA5D2,0xA5D5)):return
            self._a(m[0x0007])
            if not (yield from self._local_call(self.text_helper_a5f4,0xA5D8,0xA5DB)):return
            pass
        else:
            self._a(0x01)
            if not (yield from self._local_call(self.emit_text_symbol,0xA56A,0xA56D)):return
            self._a(0x6F)
            if not (yield from self._local_call(self.emit_text_symbol,0xA56F,0xA572)):return
            self._a(0x6F)
            if not (yield from self._local_call(self.emit_text_symbol,0xA574,0xA577)):return
            if not (yield from self._local_call(self.advance_text_pointer,0xA577,0xA57A)):return
            pass
        return (yield from self.parse_text_tokens())

    def text_helper_a5de(self):
        """$A5DE: text helper a5de; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA5DE)
        m[0x0001]=self._nz(m[0x0001]-1)
        self._y(m[0x0000])
        self._mark(0xA5E4)
        if not r.p&Z:
            return (yield from self.text_helper_a5f4())
        else:
            self._a(r.a & 0x0F)
            self._mark(0xA5E8)
            if not r.p&Z:
                return (yield from self.text_helper_a5f4())
            else:
                self._y(m[0x0001])
                self._mark(0xA5ED)
                if not r.p&N:
                    self._mark(0xA606)
                    self._rts();return
                else:
                    self._a(0x01)
                    return (yield from self.emit_text_symbol())

    def text_helper_a5f4(self):
        """$A5F4: text helper a5f4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA5F4)
        self._a(r.a & 0x0F)
        self._flag(C,False)
        self._add(0x76)
        self._y(m[0x0010])
        self._mark(0xA5FC)
        if r.p&Z:
            pass
        else:
            self._a(0x01)
            pass
        if not (yield from self._local_call(self.emit_text_symbol,0xA600,0xA603)):return
        m[0x0000]=self._nz(m[0x0000]+1)
        self._mark(0xA606)
        self._rts();return

    def clear_text_rows(self):
        """$A60F: clear text rows; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA60F)
        self._y(0x28)
        self._a(0x01)
        while True:  # natural loop $A613
            m[(0x031C+r.y)&65535]=r.a
            m[(0x034C+r.y)&65535]=r.a
            self._y(r.y-1)
            self._mark(0xA61A)
            if not r.p&Z:
                continue
            else:
                pass
            self._mark(0xA61C)
            self._rts();return

    def message_pointer(self):
        """$A61D: message pointer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA61D)
        self._a(m[0x0310])
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0000]=self._shift(m[0x0000],True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        if not (yield from self._local_call(self.select_message_window,0xA62E,0xA631)):return
        self._push(r.a)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[0x0000])
        self._flag(C,False)
        self._add(m[(0xA672+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[0x0001])
        self._add(m[(0xA673+r.y)&65535])
        m[0x0001]=r.a
        self._a(self._pop())
        self._compare(r.a,0x09)
        self._mark(0xA64A)
        if r.p&C:
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x00A6]=r.a
            self._y(r.y+1)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._flag(C,False)
            self._add(0x20)
            m[0x00A7]=r.a
            self._mark(0xA660)
            self._rts();return
        else:
            self._compare(r.a,0x03)
            self._mark(0xA64E)
            if r.p&C:
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x00A6]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,False)
                self._add(0x40)
                m[0x00A7]=r.a
                self._mark(0xA671)
                self._rts();return
            else:
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x00A6]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,False)
                self._add(0x20)
                m[0x00A7]=r.a
                self._mark(0xA660)
                self._rts();return

    def select_message_window(self):
        """$A690: select message window; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA690)
        self._a(0x00)
        self._y(m[0x0310])
        self._compare(r.y,0x20)
        self._mark(0xA697)
        if not r.p&C:
            pass
        else:
            self._a(m[GLOBAL])
            pass
        self._push(r.a)
        self._y(r.a)
        self._a(m[(0xA6A7+r.y)&65535])
        self._y(r.a)
        yield from self._external(0xA6A2,0xF25F,0xA6A5,"call",None)
        if r.pc!=0xA6A5:return  # preserve nonlocal stack return
        self._a(self._pop())
        self._mark(0xA6A6)
        self._rts();return

    def palette_cadence_tail(self):
        """$EE72: palette cadence tail; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xEE72)
        yield from self._external(0xEE72,0xE70E,None,"tail")
        return

