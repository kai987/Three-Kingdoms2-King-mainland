"""Readable initial battlefield rows and the fixed F09C sprite variant.

Physical23 A009->A2FF builds31 row pairs (counter30..0), invokes the real
fixed EEE6 PPU consumer, and preserves its remaining007E wait. Immutable map
tables and independently recovered scroll primitives are reused; no opcodes,
control IR, original-CPU fallback, cache override or readiness ack is used.
"""
from .battle_nmi_services import BattleNMIServices,NMIRegisters,ServiceCall,ServiceWait
from .battle_graphics_services import GraphicsData,GraphicsRegisters,BattleGraphicsServices,_Binary
from .scroll_graphics_services import ScrollGraphicsServices,DECLARED_RAM_ADDRESSES
from .mapped_memory import UnsupportedHardware

C,Z,V,N=1,2,64,128


class InitialRows(ScrollGraphicsServices):
    """Exact direct A485/AD9F entries, independent of scroll-cache direction."""
    def tile_row(self,registers=None):
        self._start(registers);m=self.memory
        m[0xC]=m[0x8E];m[0xD]=m[0x8F];m[0xF]=m[0x91];m[0xE]=m[0x90]
        self.r.a=(m[0x7E]<<1)&255;self.c=m[0x7E]>>7
        if self.r.a&128:return self._finish(registers)
        ident,y=self._descriptor();m[0x1A]=y;self._chunk(ident)
        m[0x10]=m[(self._word(0xA8)+((y+1)&255))&65535]
        self._tile_lookup(False);m[8]=m[0xC]>>4;m[5]=((m[0xE]&240)+m[8])&255
        self.r.x=0;m[6]=0
        for _ in range(17):
            tile=m[(self._word(0)+m[5])&65535];self._tile_quad(tile,False);self._inc(0x18)
            old=m[5];self._inc(5)
            if old&15==15:self._chunk(m[0x10]);m[5]=old&240
            self._inc(6)
        self._tile_header(0x164);m[0x7E]|=64;self.r.a=m[0x7E]
        self.requests.append(dict(kind='initial_tile_row',address=0x164,request_bit=64))
        return self._finish(registers)

    def attribute_row(self,registers=None):
        self._start(registers);m=self.memory
        m[0xC]=self._add(m[0x8E],4);m[0xD]=self._add(m[0x8F],0,self.c)
        m[0xE]=m[0x90];m[0xF]=m[0x91]
        ident,y=self._descriptor();m[0xA]=y;self._chunk(ident,True)
        m[0xA]=m[(self._word(0xA8)+((y+1)&255))&65535]
        m[6]=0;m[8]=m[0xC]>>5;m[5]=(m[8]+((m[0xE]&224)>>2))&255
        self._attribute_lookup(False);self.r.x=0;m[7]=8+int(bool(m[0xC]&16))
        for _ in range(m[7]):
            m[2]=m[(self._word(0)+m[5])&65535];self._attribute_overlay(2,m[0x18],0x680,0x6A0,True)
            self._inc(0x17,-1);self._inc(0x16,2);self._inc(0x18,2)
            # Both AE58 cache-bit branches implement this same boundary merge.
            if m[6]==8 and m[0xC]&16:m[0x19E]=(m[0x19E]&204)|(m[2]&51)
            else:m[0x19E+self.r.x]=m[2]
            self.r.x=(self.r.x+1)&255;old=m[5];self._inc(5)
            if old&7==7:self._chunk(m[0xA],True);m[5]=old&248
            self._inc(6)
        self._attribute_header(0x19C);m[0x7E]|=16;self.r.a=m[0x7E]
        self.requests.append(dict(kind='initial_attribute_row',address=0x19C,request_bit=16))
        return self._finish(registers)


class BattleBackgroundInitialization:
    """One resumable real background body, with existing caller PC/SP ownership.

    Default EEE6 service is the independent fixed PPU implementation. Its
    hardware reads require explicit ServiceMemory inputs. A supplied services
    callback must implement the same strict ServiceCall return protocol.
    """
    def __init__(self,memory,rom,services=None):
        self.memory=memory;self.data=GraphicsData.from_rom(rom);self.rows=InitialRows(memory,self.data)
        self.graphics=BattleGraphicsServices(memory,self.data);self.services=services
        self.ppu=BattleNMIServices(memory);self.registers=NMIRegisters();self.pending=None
        self._program=None;self._call_owner=None;self.events=[];self.row_pairs=0
    def _nz(self,value):
        value&=255;self.registers.p=(self.registers.p&~(N|Z))|(N if value&128 else 0)|(Z if value==0 else 0)
        return value
    def _a(self,value):self.registers.a=self._nz(value)
    def _flag(self,bit,value):self.registers.p=(self.registers.p&~bit)|(bit if value else 0)
    def _add(self,value,subtract=False):
        r=self.registers;old=r.a;carry=bool(r.p&C)
        total=old-value-(1-carry)if subtract else old+value+carry
        self._flag(C,total>=0 if subtract else total>255)
        self._flag(V,((old^value)&(old^total)&128)if subtract else(~(old^value)&(old^total)&128))
        self._a(total)
    def _lsr(self):
        self._flag(C,self.registers.a&1);self._a(self.registers.a>>1)
    def _push(self,value):
        r=self.registers;self.memory[0x100+r.sp]=value&255;r.sp=(r.sp-1)&255
    def _pop(self):
        r=self.registers;r.sp=(r.sp+1)&255;return self.memory[0x100+r.sp]
    def _rts(self):self.registers.pc=((self._pop()|self._pop()<<8)+1)&65535
    def _row_call(self,attribute=False):
        r=self.registers;pc=0xA31E if attribute else 0xA31B
        self._push((pc+2)>>8);self._push(pc+2)
        gr=GraphicsRegisters(r.a,r.x,r.y,r.p)
        result=(self.rows.attribute_row if attribute else self.rows.tile_row)(gr)
        for k,v in result['registers'].items():setattr(r,k,v)
        self._rts()
    def _fast_ppu_call(self):
        r=self.registers;expected=r.sp;self._push(0xA3);self._push(0x23);r.pc=0xEEE6
        self.events.append(dict(target=0xEEE6,row_pair=self.row_pairs,entry_jobs=self.memory[0x7E]))
        yield ServiceCall(0xEEE6,0xA324,'call',r,self.memory,tuple(getattr(self.memory,'banks',())),expected)
    def _background(self):
        r=self.registers;m=self.memory
        self._a(m[0x8E]);self._push(r.a);self._a(m[0x8F]);self._push(r.a)
        self._a(m[0x90]);m[0x1E]=r.a;self._push(r.a)
        self._a(m[0x91]);m[0x1F]=r.a;self._push(r.a)
        m[0x91]=self._nz(m[0x91]+1);self._a(30)
        while True:
            self._push(r.a);self._row_call();self._row_call(True);self.row_pairs+=1
            while True:
                yield from self._fast_ppu_call()
                self._a(m[0x7E])
                if r.p&Z:break
                if m[0x7E]&15:
                    r.pc=0xA321
                    yield ServiceWait('PPU_jobs_outside_fast_consumer',0xA321,0x7E,m[0x7E],
                                      'Original BNE repeats EEE6; remaining low jobs require their real owner',r.sp)
            self._a(m[0x90]);self._flag(C,True);self._add(8,True);m[0x90]=r.a
            if not r.p&C:
                self._flag(C,True);self._add(16,True);m[0x90]=r.a;m[0x91]=self._nz(m[0x91]-1)
            self._a(self._pop());self._flag(C,True);self._add(1,True)
            if r.p&N:break
        for address in(0x91,0x90,0x8F,0x8E):self._a(self._pop());m[address]=r.a
        self._a(m[0x90]);self._lsr();self._lsr();self._lsr();m[0x92]=r.a
        self._a(m[0x90]);self._flag(C,False);self._add(8)
        for _ in range(4):self._lsr()
        m[0x94]=r.a;self._a(m[0x8E]);self._flag(C,True);self._add(6,True)
        for _ in range(3):self._lsr()
        m[0x95]=r.a;self._a(m[0x8E])
        for _ in range(3):self._lsr()
        m[0x93]=r.a;self._a(144);m[0x9C]=m[0x9D]=r.a
        self._rts()
    def _service(self,call):
        if self.services is not None:return self.services(call)
        return self.ppu.resume()if self.ppu._program is not None else self.ppu.run_service(0xEEE6,call.registers)
    def _drive(self):
        while True:
            if isinstance(self.pending,ServiceCall):
                call=self.pending
                try:result=self._service(call)
                except UnsupportedHardware:return self._result('dependency')
                if not isinstance(result,dict)or result.get('status')!='returned':return self._result('dependency')
                if self.registers.pc!=call.return_pc or self.registers.sp!=call.expected_sp:return self._result('dependency')
                self.pending=None
            elif isinstance(self.pending,ServiceWait):
                if self.registers.pc!=self.pending.pc or self.registers.sp!=self.pending.expected_sp:
                    return self._result('dependency')
                if self.memory[0x7E]&15:return self._result('dependency')
                self.pending=None
            try:self.pending=next(self._program)
            except StopIteration:
                self._program=None
                if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:return self._result('nonlocal_return')
                return self._result('returned')
            if isinstance(self.pending,ServiceWait):return self._result('dependency')
    def _result(self,status):
        return dict(status=status,row_pairs=self.row_pairs,fast_PPU_calls=len(self.events),events=list(self.events),
                    registers=vars(self.registers).copy(),pending=self.pending,
                    original_request_flags=self.memory[0x7E],frames_or_ack_synthesized=False)
    def run_entry(self,entry=0xA009,registers=None,*,return_pc=None):
        if self._program is not None:raise RuntimeError('Resume the existing background invocation')
        if entry not in(0xA009,0xA2FF):raise ValueError('Only physical23A009/A2FF background entry')
        self.registers=registers or NMIRegisters();r=self.registers
        if r.p&8:raise ValueError('NES binary arithmetic excludes decimal fixtures')
        self._return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535 if return_pc is None else return_pc
        self._return_sp=(r.sp+2)&255;r.pc=entry;self.pending=None;self.events=[];self.row_pairs=0
        self._program=self._background();return self._drive()
    def resume(self):
        if self._program is None:raise RuntimeError('No pending background invocation')
        return self._drive()
    def __call__(self,call):
        if call.target==0xF09C:
            if self._program is not None:return dict(status='dependency',reason='Another caller owns the pending background')
            result=self.world_sprites_variant(call.registers)
            self.registers=call.registers;self._rts()
            return result
        if call.target not in(0xA009,0xA2FF):return dict(status='dependency',reason='Not a recovered background entry')
        if tuple(call.entry_banks[1:3])!=(23,24):return dict(status='dependency',reason='Background entry requires physical23/24')
        if self._program is not None:
            if self._call_owner is not call:return dict(status='dependency',reason='Another caller owns the background')
            result=self.resume()
        else:
            self._call_owner=call;result=self.run_entry(call.target,call.registers,return_pc=call.return_pc)
        if result['status']=='returned':self._call_owner=None
        return result

    def world_sprites_variant(self,registers=None):
        """Fixed F09C: keep caller's0003 tile offset /0004 vertical clip.

        F092 alone sets these fields to0/F0. This entry starts at BIT0002 and
        retains the world-coordinate, negative-X complement-without-plus-one
        and partial-OAM quirks of
        the separately recovered renderer. Caller owns its RTS stack pop.
        """
        r=GraphicsRegisters()if registers is None else GraphicsRegisters(registers.a,registers.x,registers.y,registers.p)
        if r.p&8:raise ValueError('Binary sprite contract excludes decimal fixtures')
        alu=_Binary(r.p);m=self.memory;flags=m[2];pointer=m[0]|m[1]<<8
        if flags&128:
            low,_=alu.sub(m[0xA],8)
            if low>=240:low,_=alu.sub(low,16);m[0xB]=(m[0xB]-1)&255
            m[0xA]=low
        if flags&64:
            m[0xC],carry=alu.sub(m[0xC],16)
            if not carry:m[0xD]=(m[0xD]-1)&255
        low,carry=alu.sub(m[0xA],m[0x90])
        if not carry:low,_=alu.sub(low,16);carry=0
        m[0xA]=low;m[0xB],_=alu.sub(m[0xB],m[0x91],carry)
        m[0xC],carry=alu.sub(m[0xC],m[0x8E]);m[0xD],_=alu.sub(m[0xD],m[0x8F],carry)
        r.a=m[0xD];x=m[0x7C];index=0;allocated=0
        for _ in range(65):
            if x==255:
                m[0x7C]=x;r.x=x;r.y=index;r.p=alu.flags(0,True);break
            m[0xF]=m[0xB];dy=m[(pointer+index)&65535]
            if dy==128:
                m[0x7C]=x;r.a=128;r.x=x;r.y=index;r.p=alu.flags(0,True);break
            if flags&128:dy,_=alu.sub(8,dy)
            if dy<128:
                m[0xE],carry=alu.add(dy,m[0xA]);high,_=alu.add(m[0xB],0,carry)
            else:
                magnitude,_=alu.add(dy^255,0,1);m[0xE]=magnitude
                m[0xE],carry=alu.sub(m[0xA],m[0xE]);high,_=alu.sub(m[0xB],0,carry)
            r.a=high
            if high!=0:index=(index+4)&255;continue
            screen_y,_=alu.sub(m[0xE],1);r.a=screen_y
            if screen_y>=m[4]:index=(index+4)&255;continue
            m[0x200+x]=screen_y
            m[0x201+x],_=alu.add(m[(pointer+((index+1)&255))&65535],m[3])
            m[0x202+x]=m[(pointer+((index+2)&255))&65535]^flags
            dx=m[(pointer+((index+3)&255))&65535]
            if flags&64:dx,_=alu.sub(8,dx)
            if dx&128:
                m[0xE]=dx^255;value,carry=alu.sub(m[0xC],m[0xE]);m[0x203+x]=value;high,_=alu.sub(m[0xD],0,carry)
            else:
                value,carry=alu.add(dx,m[0xC]);m[0x203+x]=value;high,_=alu.add(m[0xD],0,carry)
            r.a=high;index=(index+4)&255
            if high==0:
                x=(x+4)&255;allocated+=1
                if x==0:x=255
        else:raise ValueError('Original terminated F09C sprite descriptor required')
        if registers is not None:
            for key,value in vars(r).items():setattr(registers,key,value)
        return dict(status='returned',registers=vars(r),sprites_allocated=allocated,
                    tile_offset=m[3],vertical_clip=m[4],OAM_DMA_requested=False)
