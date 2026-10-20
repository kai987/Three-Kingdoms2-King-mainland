"""Recovered bank31 NMI/IRQ orchestration and fixed display/input services.

This is newly written readable source, not the original author's source. ROM is
data only. No opcode executor or lifted control IR is used. Hardware reads and
unrecovered scene calls remain explicit dependencies. The caller owns actual
PPU/IRQ timing; run_irq implements software IRQ writes, never an automatic ack.
"""
from dataclasses import dataclass,asdict
from .mapped_memory import UnsupportedHardware

C,Z,I,D,B,U,V,N=1,2,4,8,16,32,64,128
SCENE_ENTRIES=(0xFA97,0xFA97,0xF8B5,0xF8FE,0xF96A,0xF9A0,0xF9E4,0xFA13,0xFA53)
IRQ_ENTRIES=(0xFB92,0xFBA4,0xFC8B,0xFBA4,0xFD2A,0xFD95,0xFDF4,
             0xFE03,0xFE69,0xFE96,0xFECD,0xFF31,0xFF48)

@dataclass
class NMIRegisters:
    a:int=0
    x:int=0
    y:int=0
    sp:int=0xFD
    p:int=U
    pc:int=0

@dataclass
class ServiceCall:
    target:int
    return_pc:int
    kind:str
    registers:object
    memory:object
    entry_banks:tuple
    expected_sp:int

@dataclass
class ServiceWait:
    category:str
    pc:int
    address:int|None=None
    value:int|None=None
    reason:str=''
    expected_sp:int|None=None

class BattleNMIServices:
    """Synchronous readable services, resumable at real external boundaries.

    callbacks(call) must execute the service and restore its actual caller
    stack/PC. Returning a dependency or leaving PC/SP before the return stops
    this orchestration. resume() retries that same callback; it never fakes RTS.
    Missing port reads can be supplied explicitly on memory then resumed.
    """
    FIXED=(0xE6C6,0xE70E,0xE825,0xE830,0xEAF7,0xEC67,0xEE53,0xEEE6,
           0xEF0B,0xEF71,0xEFC0,0xF028,0xF077,0xF206,0xF237,0xF24B,
           0xF25F,0xF266,0xFAA9,0xFABF,0xFB0B,0xFB28,0xFF62,0xFF9B)

    def __init__(self,memory,callbacks=None):
        self.memory=memory;self.callbacks=callbacks;self.registers=NMIRegisters()
        self.events=[];self.pending=None;self._program=None;self.mode=None

    def nz(self,v):
        v&=255;self.registers.p=(self.registers.p&~(N|Z))|(N if v&128 else 0)|(Z if v==0 else 0);return v
    def a(self,v):self.registers.a=self.nz(v);return self.registers.a
    def x(self,v):self.registers.x=self.nz(v);return self.registers.x
    def y(self,v):self.registers.y=self.nz(v);return self.registers.y
    def flag(self,bit,value):self.registers.p=(self.registers.p&~bit)|(bit if value else 0)
    def cmp(self,left,right):self.flag(C,left>=right);self.nz(left-right)
    def add(self,value,subtract=False):
        r=self.registers;old=r.a;operand=value^255 if subtract else value
        total=old+operand+bool(r.p&C);self.flag(C,total>255)
        self.flag(V,bool((~(old^operand)&(old^total))&128));return self.a(total)
    def shift_a(self,kind):
        r=self.registers;old=r.a;carry=bool(r.p&C)
        self.flag(C,bool(old&128)if kind in ('asl','rol')else bool(old&1))
        return self.a((old<<1)|carry if kind=='rol'else old<<1 if kind=='asl'else old>>1)
    def inc(self,address,delta=1):
        v=self.nz(self.memory[address]+delta);self.memory[address]=v;return v
    def push(self,v):
        r=self.registers;self.memory[0x100+r.sp]=v&255;r.sp=(r.sp-1)&255
    def pop(self):
        r=self.registers;r.sp=(r.sp+1)&255;return self.memory[0x100+r.sp]
    def rts(self):self.registers.pc=((self.pop()|self.pop()<<8)+1)&65535
    def rti(self):
        # B/U are the conventional software status representation used by
        # the independent CPU oracle; B is not a stored physical6502 latch.
        r=self.registers;r.p=self.pop()|B|U;r.pc=self.pop()|self.pop()<<8

    def read(self,address,pc):
        while True:
            self.registers.pc=pc
            try:return self.memory[address]
            except UnsupportedHardware as exc:yield ServiceWait('hardware_read',pc,address,reason=str(exc))
    def write(self,address,value,pc):
        while True:
            self.registers.pc=pc
            try:self.memory[address]=value;return
            except UnsupportedHardware as exc:yield ServiceWait('hardware_write',pc,address,value,str(exc))

    def _external(self,target,kind='call'):
        r=self.registers;r.pc=target
        ret=((self.memory[0x100+((r.sp+1)&255)]|
              self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535
        yield ServiceCall(target,ret,kind,r,self.memory,tuple(getattr(self.memory,'banks',())),(r.sp+2)&255)

    def call(self,pc,target):
        caller_sp=self.registers.sp;return_word=(pc+2)&65535;self.push(return_word>>8);self.push(return_word)
        self.registers.pc=target
        self.events.append({'kind':'call','pc':pc,'target':target,'banks':list(getattr(self.memory,'banks',()))})
        if target in self.FIXED:
            yield from self.routine(target)
            if not(self.registers.sp==caller_sp and self.registers.pc==(pc+3)&65535):self.rts()
        else:yield from self._external(target)

    def routine(self,entry):
        methods={0xE6C6:self.controllers,0xE70E:self.palette_upload,0xE825:self.hide_all_oam,
                 0xE830:self.hide_oam_tail,0xEAF7:self.scroll_control,0xEC67:self.palette_fade,
                 0xEE53:self.pending_ppu,0xEEE6:self.pending_ppu_fast,
                 0xEF0B:self.tile_column,0xEF71:self.tile_row,0xEFC0:self.attribute_column,
                 0xF028:self.attribute_row,0xF077:self.mark_scroll_changes,
                 0xF206:self.chr_banks,0xFB0B:self.nametable_banks,0xFB28:self.wait_irq,
                 0xFF62:lambda:self.prepare_split_address(False),0xFF9B:lambda:self.prepare_split_address(True),
                 0xFAA9:lambda:self.swap_controllers(False),0xFABF:lambda:self.swap_controllers(True)}
        if entry in (0xF237,0xF24B,0xF25F,0xF266):yield from self.mapper_window(entry)
        elif entry in methods:yield from methods[entry]()
        else:yield from self._external(entry)

    def _start(self,program,registers,mode):
        if self._program is not None:raise RuntimeError('A service is already pending; resume it first')
        self.registers=registers or NMIRegisters();self.events=[];self.pending=None;self.mode=mode
        self._program=program();return self._drive()
    def _drive(self):
        while True:
            if isinstance(self.pending,ServiceWait)and self.pending.category=='IRQ_software_flag':
                if self.registers.pc!=self.pending.pc or self.registers.sp!=self.pending.expected_sp:
                    return self.result('dependency',reason='IRQ has not returned to the paused NMI PC/SP')
            if isinstance(self.pending,ServiceCall):
                call=self.pending
                if self.callbacks is None:return self.result('dependency')
                try:outcome=self.callbacks(call)
                except UnsupportedHardware as exc:return self.result('dependency',callback={'category':'callback_hardware_input','reason':str(exc)})
                if isinstance(outcome,dict)and outcome.get('status')in ('dependency','blocked','waiting','failed','error','budget'):
                    return self.result('dependency',callback=outcome)
                if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:
                    return self.result('dependency',reason='Callback has not reached its real caller PC/SP')
                self.events.append({'kind':'callback_return','target':call.target,'return_pc':call.return_pc})
            self.pending=None
            try:self.pending=next(self._program)
            except StopIteration:
                self._program=None;return self.result('returned')
            if isinstance(self.pending,ServiceWait):
                self.pending.expected_sp=self.registers.sp;return self.result('dependency')
    def result(self,status,**extra):
        p=self.pending
        dependency=({'category':'external_call','target':p.target,'return_pc':p.return_pc,
                     'kind':p.kind,'entry_banks':list(p.entry_banks),'expected_sp':p.expected_sp}
                    if isinstance(p,ServiceCall)else asdict(p)if p else None)
        return {'status':status,'mode':self.mode,'registers':asdict(self.registers),
                'dependency':dependency,'events':list(self.events),**extra}
    def resume(self):
        if self._program is None:raise RuntimeError('No pending service')
        return self._drive()
    resume_nmi=resume
    def run_service(self,entry,registers=None):
        def body():
            entry_sp=self.registers.sp;self.registers.pc=entry;yield from self.routine(entry)
            if self.registers.sp==entry_sp:self.rts()
        return self._start(body,registers,'fixed_service')
    def interrupt_entry(self,vector):
        r=self.registers;self.push(r.pc>>8);self.push(r.pc);r.p&=~B
        self.push(r.p|U);r.p|=I;r.pc=vector
    def run_nmi(self,registers=None,*,hardware_entry=False):
        def body():
            if hardware_entry:self.interrupt_entry(0xF800)
            yield from self.nmi_body()
        return self._start(body,registers,'nmi')
    def run_irq(self,registers=None,*,hardware_entry=False):
        def body():
            if hardware_entry:self.interrupt_entry(0xFB2D)
            yield from self.irq_body()
        return self._start(body,registers,'irq')

    def mapper_window(self,entry):
        r=self.registers;m=self.memory
        if entry in (0xF25F,0xF266):
            m[0xE1 if entry==0xF25F else 0xDE]=r.y
            yield from self.write(0xE000,r.y,entry+3);return
        shadow=0xE2 if entry==0xF237 else 0xDF;m[shadow]=r.y
        self.y(r.y+1);m[shadow+1]=r.y;yield from self.write(0xF000,r.y,entry+7)
        self.y(r.y-1);self.push(r.a);self.a(r.y);self.a(r.a|0xC0)
        yield from self.write(0xE800,r.a,entry+15);self.a(self.pop())

    def chr_banks(self):
        for i in range(8):
            self.a(self.memory[0xAE+i]);yield from self.write(0x8000+0x800*i,self.registers.a,0xF209+6*i)
    def scroll_control(self):
        m=self.memory;self.a(m[0x8E]);yield from self.write(0x2005,self.registers.a,0xEAFA)
        self.a(m[0x90]);yield from self.write(0x2005,self.registers.a,0xEB00)
        self.a(m[0x8B]);self.a(self.registers.a&0xFE);m[0x8B]=self.registers.a
        self.a(m[0x8F]);self.a(self.registers.a&1);self.a(self.registers.a|m[0x8B]);m[0x8B]=self.registers.a
        yield from self.write(0x2000,self.registers.a,0xEB16)
    def nametable_banks(self):
        yield from self.call(0xFB0B,0xEAF7)
        for i in range(4):
            self.a(self.memory[0xE6+i]);yield from self.write(0xC000+0x800*i,self.registers.a,0xFB10+5*i)
        while True:
            value=yield from self.read(0x2002,0xFB22)
            self.flag(N,value&128);self.flag(V,value&64);self.flag(Z,not(self.registers.a&value))
            if not value&64:return
            self.registers.pc=0xFB22;yield ServiceWait('PPUSTATUS_sprite_hit',0xFB22,0x2002,value,'BIT/BVS waits for an explicit status sample with bit6 clear')
    def wait_irq(self):
        while True:
            self.a(self.memory[0x62]);self.registers.pc=0xFB28
            if not self.registers.a:return
            yield ServiceWait('IRQ_software_flag',0xFB28,0x62,self.registers.a,'Only actual IRQ service execution or an explicit external IRQ update can change this RAM byte')
    def hide_all_oam(self):
        self.y(0);self.a(0xF0)
        for _ in range(256):self.memory[0x200+self.registers.y]=self.registers.a;self.y(self.registers.y+1)
        yield from ()
    def hide_oam_tail(self):
        r=self.registers;self.x(self.memory[0x7C]);self.cmp(r.x,255)
        if r.x==255:return
        while True:
            for _ in range(64):
                self.a(0xF0);self.memory[0x200+r.x]=r.a
                for _ in range(4):self.x(r.x+1)
                if r.x==0:return
            r.pc=0xE837;yield ServiceWait('unaligned_OAM_cursor',0xE837,0x7C,self.memory[0x7C],'Original X+=4 loop cannot reach zero for a cursor not divisible by4')
    def controllers(self):
        r=self.registers;m=self.memory;self.a(m[0x83]);m[0x84]=r.a;self.a(m[0x85]);m[0x86]=r.a
        self.a(1);yield from self.write(0x4016,r.a,0xE6D4);self.a(0);yield from self.write(0x4016,r.a,0xE6D9);self.x(7)
        for _ in range(8):
            for port,address,pc in ((0x4016,0x83,0xE6DE),(0x4017,0x85,0xE6E8)):
                self.a((yield from self.read(port,pc)));self.a(r.a&3);self.cmp(r.a,1)
                old=m[address];carry=bool(r.p&C);self.flag(C,old&1);m[address]=self.nz((old>>1)|(128 if carry else 0))
            self.x(r.x-1)
        self.a(m[0x83]);self.a(r.a^m[0x84]);self.a(r.a&m[0x83]);m[0x81]=r.a
        self.a(m[0x85]);self.a(r.a^m[0x86]);self.a(r.a&m[0x85]);m[0x82]=r.a
    def swap_controllers(self,reverse):
        r=self.registers;m=self.memory;self.a(m[0x6F44])
        if not r.a:return
        for first,second in ((0x82,0x81),(0x85,0x83))if reverse else((0x81,0x82),(0x83,0x85)):
            self.y(m[first]);self.a(m[second]);m[first]=r.a;m[second]=r.y
        yield from ()
    def prepare_split_address(self,alternate):
        r=self.registers;m=self.memory;self.a(0);m[0x47]=r.a;self.a(m[0x98]);m[0x99]=r.a;self.a(r.a&0xF8)
        for _ in range(2):
            self.shift_a('asl');old=m[0x47];carry=bool(r.p&C);self.flag(C,old&128);m[0x47]=self.nz((old<<1)|carry)
        m[0x9A]=r.a;self.a(m[0x47]);self.flag(C,False);self.add(0x20);m[0x9B]=r.a
        self.a(0xE0);m[0xEA]=r.a
        if not alternate:m[0xEC]=r.a
        self.a(m[0x97]);self.a(r.a&1)
        if r.a:
            if alternate:self.a(m[0x9B]);self.flag(C,False);self.add(4);m[0x9B]=r.a
            self.a(0xE1);m[0xEA]=r.a
            if not alternate:m[0xEC]=r.a
        yield from ()
    def mark_scroll_changes(self):
        r=self.registers;m=self.memory;self.a(m[0x9C]);self.a(r.a^m[0x9D]);self.push(r.a);self.a(r.a&0xC0)
        if r.a:self.y(255);m[0x95]=r.y
        self.a(self.pop());self.a(r.a&0x30)
        if r.a:self.y(255);m[0x94]=r.y
        yield from ()

    def palette_upload(self):
        r=self.registers;m=self.memory;self.a(m[0x8B]);self.a(r.a&0xFB);yield from self.write(0x2000,r.a,0xE713)
        self.a((yield from self.read(0x2002,0xE716)));self.y(0);m[0x7D]=r.y
        self.a(0x3F);yield from self.write(0x2006,r.a,0xE720);yield from self.write(0x2006,r.y,0xE723)
        for _ in range(16):
            self.a(m[0x100+r.y]);yield from self.write(0x2007,r.a,0xE729)
            self.a(m[0x101+r.y]);yield from self.write(0x2007,r.a,0xE72F)
            self.y(r.y+1);self.y(r.y+1);self.cmp(r.y,32)
        self.a(0x3F);yield from self.write(0x2006,r.a,0xE73A);self.a(0)
        for pc in (0xE73F,0xE742,0xE745):yield from self.write(0x2006,r.a,pc)
    def palette_fade(self):
        r=self.registers;m=self.memory;self.a(m[0x87])
        if r.a&128:return
        if not self.inc(0x8A,-1)&128:return
        self.a(m[0x89]);m[0x8A]=r.a;self.a(1);m[0x7D]=r.a;self.a(m[0x87])
        if r.a:self.inc(0x88);self.a(m[0x88]);self.cmp(r.a,4);ended=r.a>=4
        else:ended=self.inc(0x88,-1)==0
        if ended:self.a(255);m[0x87]=r.a
        for addr,value in ((0,0),(1,1),(2,0x20),(3,1)):self.a(value);m[addr]=r.a
        self.y(31)
        while True:
            self.x(m[0x88]);self.a(m[0x120+r.y])
            while True:
                self.x(r.x-1)
                if r.x&128:break
                self.flag(C,True);self.add(0x10,True)
                if r.a&128:self.a(0x0F);break
            m[0x100+r.y]=r.a;self.y(r.y-1)
            if r.y&128:break
        yield from ()

    def pending_ppu(self):
        r=self.registers;m=self.memory;self.a(m[0x7D])
        if r.a:yield from self.palette_upload();return
        self.a(m[0x7E])
        for bit,target,pc in ((7,0xEF0B,0xEE7E),(6,0xEF71,0xEE90),(5,0xEFC0,0),(4,0xF028,0),
                              (3,0xA00C,0),(2,0xA006,0),(1,0xA012,0),(0,0xA000,0)):
            if r.a&128:
                if bit in (7,6):
                    self.push(r.a);self.a(m[0x7E]);self.a(r.a&~(1<<bit));m[0x7E]=r.a
                    yield from self.call(pc,target);self.a(self.pop());return
                if bit==3:self.y(0x3D);yield from self.call(0xEEB0,0xF237)
                if bit:
                    self.a(m[0x7E]);self.a(r.a&~(1<<bit));m[0x7E]=r.a
                if bit in (2,1,0):self.y(0x3D);yield from self.call({2:0xEEC8,1:0xEED8,0:0xEEE0}[bit],0xF237)
                if target in self.FIXED:yield from self.routine(target)
                else:yield from self._external(target,'tail')
                return
            self.shift_a('asl')
        yield from self.palette_upload()
    def pending_ppu_fast(self):
        r=self.registers;m=self.memory;self.a(m[0x7E])
        for bit,target in ((7,0xEF0B),(6,0xEF71),(5,0xEFC0),(4,0xF028)):
            if r.a&128:
                self.a(m[0x7E]);self.a(r.a&~(1<<bit));m[0x7E]=r.a;yield from self.routine(target);return
            if bit>4:self.shift_a('asl')
        yield from ()

    def tile_column(self):
        r=self.registers;m=self.memory;self.a(m[0x141]);m[1]=r.a;self.a(m[0x140]);self.a(r.a&3)
        for _ in range(3):
            old=m[1];self.flag(C,old&128);m[1]=self.nz(old<<1);self.shift_a('rol')
        m[1]=r.a;self.a(30);self.flag(C,True);self.add(m[1],True);m[0]=r.a
        self.a(m[0x8B]);self.a(r.a|4);yield from self.write(0x2000,r.a,0xEF33)
        self.a((yield from self.read(0x2002,0xEF36)));self.a(m[0x140]);yield from self.write(0x2006,r.a,0xEF3C)
        self.a(m[0x141]);yield from self.write(0x2006,r.a,0xEF42);self.y(0)
        while True:
            self.a(m[0x142+r.y]);yield from self.write(0x2007,r.a,0xEF4A);self.y(r.y+1);self.cmp(r.y,m[0])
            if r.y>=m[0]:break
        self.a(m[0x140]);self.a(r.a&0xFC);yield from self.write(0x2006,r.a,0xEF58)
        self.a(m[0x141]);self.a(r.a&31);yield from self.write(0x2006,r.a,0xEF60)
        while True:
            self.cmp(r.y,30)
            if r.y>=30:return
            self.a(m[0x142+r.y]);yield from self.write(0x2007,r.a,0xEF6A);self.y(r.y+1)
            if r.y==0:return
    def tile_row(self):
        r=self.registers;m=self.memory;self.a(m[0x8B]);self.a(r.a&0xFB);yield from self.write(0x2000,r.a,0xEF76)
        self.a((yield from self.read(0x2002,0xEF79)));self.a(m[0x164]);yield from self.write(0x2006,r.a,0xEF7F)
        self.a(m[0x165]);yield from self.write(0x2006,r.a,0xEF85);self.a(r.a&31);m[0]=r.a
        self.a(32);self.flag(C,True);self.add(m[0],True);m[0]=r.a;self.y(0)
        while True:
            self.a(m[0x166+r.y]);yield from self.write(0x2007,r.a,0xEF9B);self.y(r.y+1);self.cmp(r.y,m[0])
            if r.y>=m[0]:break
        self.a(m[0x164]);yield from self.write(0x2006,r.a,0xEFA7)
        self.a(m[0x165]);self.a(r.a&0xE0);yield from self.write(0x2006,r.a,0xEFAF)
        while True:
            self.cmp(r.y,32)
            if r.y>=32:return
            self.a(m[0x166+r.y]);yield from self.write(0x2007,r.a,0xEFB9);self.y(r.y+1)
    def attribute_column(self):
        r=self.registers;m=self.memory;self.a(m[0x189]);m[1]=r.a;self.a(r.a&0x38)
        for _ in range(3):self.shift_a('lsr')
        m[0]=r.a;self.a(8);self.flag(C,True);self.add(m[0],True);m[0]=r.a;self.y(0)
        self.a((yield from self.read(0x2002,0xEFD9)))
        while True:
            self.a(m[0x188]);yield from self.write(0x2006,r.a,0xEFDF)
            self.a(m[1]);yield from self.write(0x2006,r.a,0xEFE5)
            self.a(m[0x18A+r.y]);yield from self.write(0x2007,r.a,0xEFEB)
            self.a(m[1]);self.flag(C,False);self.add(8);m[1]=r.a;self.y(r.y+1);self.cmp(r.y,m[0])
            if r.y>=m[0]:break
        self.a(m[0x189]);self.a(r.a&0xC7);m[1]=r.a
        while True:
            self.cmp(r.y,8)
            if r.y>=8:return
            self.a(m[0x188]);yield from self.write(0x2006,r.a,0xF00C)
            self.a(m[1]);yield from self.write(0x2006,r.a,0xF012)
            self.a(m[0x18A+r.y]);yield from self.write(0x2007,r.a,0xF018)
            self.a(m[1]);self.flag(C,False);self.add(8);m[1]=r.a;self.y(r.y+1)
    def attribute_row(self):
        r=self.registers;m=self.memory;self.a(m[0x8B]);self.a(r.a&0xFB);yield from self.write(0x2000,r.a,0xF02D)
        self.a((yield from self.read(0x2002,0xF030)));self.a(m[0x19C]);yield from self.write(0x2006,r.a,0xF036)
        self.a(m[0x19D]);yield from self.write(0x2006,r.a,0xF03C);self.a(r.a&7);m[0]=r.a
        self.a(8);self.flag(C,True);self.add(m[0],True);m[0]=r.a;self.y(0)
        while True:
            self.a(m[0x19E+r.y]);yield from self.write(0x2007,r.a,0xF052);self.y(r.y+1);self.cmp(r.y,m[0])
            if r.y>=m[0]:break
        self.a(m[0x19C]);yield from self.write(0x2006,r.a,0xF05E)
        self.a(m[0x19D]);self.a(r.a&0xF8);yield from self.write(0x2006,r.a,0xF066)
        while True:
            self.cmp(r.y,8)
            if r.y>=8:return
            self.a(m[0x19E+r.y]);yield from self.write(0x2007,r.a,0xF070);self.y(r.y+1)

    def nmi_body(self):
        r=self.registers;m=self.memory;r.pc=0xF800;self.push(r.a);self.a(r.x);self.push(r.a);self.a(r.y);self.push(r.a)
        self.a((yield from self.read(0x2002,0xF805)));self.a(0);yield from self.write(0x5800,r.a,0xF80A)
        self.a(m[0x68]);yield from self.write(0x5000,r.a,0xF810);self.a(m[0x69]);yield from self.write(0x5800,r.a,0xF816)
        m[0x62]=r.a;self.a(m[0x61]);m[0x60]=r.a;self.flag(I,False)
        for address,value,pc in ((0xC000,0xE0,0xF825),(0xC800,0xE1,0xF82A),(0xD000,0xE0,0xF82F),(0xD800,0xE1,0xF834)):
            self.a(value);yield from self.write(address,r.a,pc)
        self.a(m[0x7B])
        if r.a:yield from self.busy_nmi()
        else:
            for shadow,address,pc in ((0xE1,0xE000,0xF840),(0xE2,0xE800,0xF847),(0xE3,0xF000,0xF84C)):
                self.a(m[shadow]);
                if shadow==0xE2:self.a(r.a|0xC0)
                yield from self.write(address,r.a,pc)
            self.y(0);yield from self.write(0x2003,r.y,0xF851);self.y(r.y+1);m[0x7B]=r.y
            self.a(2);yield from self.write(0x4014,r.a,0xF859);self.a(m[0x8C]);yield from self.write(0x2001,r.a,0xF85F)
            self.a(0);m[0x7C]=r.a;self.a(m[0x78]);self.a(r.a&15);self.shift_a('asl');self.y(r.a)
            scene=r.y//2
            if scene>=len(SCENE_ENTRIES):
                r.pc=0xF86C
                while True:yield ServiceWait('unproven_NMI_scene',0xF86C,0x78,m[0x78],'Only indices0..8 have a bounded original pointer table')
            target=SCENE_ENTRIES[scene];self.a(target&255);m[0]=r.a;self.a(target>>8);m[1]=r.a
            yield from self.scene(scene)
            self.inc(0x7B,-1)
            for shadow,address,pc in ((0xDE,0xE000,0xF892),(0xDF,0xE800,0xF899),(0xE0,0xF000,0xF89E)):
                self.a(m[shadow]);
                if shadow==0xDF:self.a(r.a|0xC0)
                yield from self.write(address,r.a,pc)
            for address in (0x50,0x52,0x54,0x55):self.inc(address)
            if self.inc(0x5E)==0:self.inc(0x5F)
        self.y(self.pop());self.x(self.pop());self.a(self.pop());self.rti()

    def bank_call(self,pc,selector,target):
        self.y(selector);yield from self.call(pc,0xF237);yield from self.call(pc+3,target)
    def scene(self,scene):
        r=self.registers;m=self.memory
        if scene in(0,1):
            for pc,target in ((0xFA97,0xFB0B),(0xFA9A,0xF206),(0xFA9D,0xE6C6),(0xFAA0,0xFF62),(0xFAA3,0xFB28)):
                yield from self.call(pc,target)
            return
        start=SCENE_ENTRIES[scene]
        for offset,target in ((0,0xEE53),(3,0xF206),(6,0xFB0B)):yield from self.call(start+offset,target)
        if scene in(3,4,5):self.a(0);m[0x7C]=r.a
        if scene in(2,3,4,5,7,8):yield from self.call({2:0xF8BE,3:0xF90B,4:0xF977,5:0xF9AD,7:0xFA1C,8:0xFA5C}[scene],0xEC67)
        if scene!=8:yield from self.call({2:0xF8C1,3:0xF90E,4:0xF97A,5:0xF9B0,6:0xF9ED,7:0xFA1F}[scene],0xE6C6)
        yield from self.bank_call({2:0xF8C6,3:0xF913,4:0xF97F,5:0xF9B5,6:0xF9F2,7:0xFA24,8:0xFA61}[scene],0x2E,0xA003)
        if scene==8:
            self.a(0);m[0x81]=r.a;yield from self.bank_call(0xFA6D,0x3D,0xA003)
        if scene==7:yield from self.call(0xFA2A,0xFF9B)
        self.a(0x4C);m[0xA5]=r.a;yield from self.write(0xF800,r.a,{2:0xF8D0,3:0xF91D,4:0xF989,5:0xF9BF,6:0xF9FC,7:0xFA31,8:0xFA77}[scene])
        if scene==2:
            yield from self.call(0xF8D3,0xFF9B);yield from self.call(0xF8D6,0xFAA9)
            yield from self.bank_call(0xF8DB,0x3D,0xA003)
            for pc,target in ((0xF8E1,0xA009),(0xF8E4,0xA00F),(0xF8E7,0xA03F)):yield from self.call(pc,target)
            yield from self.bank_call(0xF8EC,0x3B,0xA000);yield from self.call(0xF8F2,0xFABF)
        elif scene==3:
            yield from self.call(0xF920,0xFF62);self.a(m[0x500]);self.cmp(r.a,12)
            if r.a<12:
                self.a(m[0x8F])
                if r.a==0:
                    yield from self.call(0xF92F,0xF077);yield from self.bank_call(0xF934,0x37,0xA00C);yield from self.call(0xF93A,0xA00F)
            yield from self.call(0xF93D,0xFAA9);yield from self.bank_call(0xF942,0x39,0xA00F)
            yield from self.bank_call(0xF94A,0x2C,0xA000);yield from self.bank_call(0xF952,0x3D,0xA003);yield from self.call(0xF958,0xFABF)
        elif scene==4:
            yield from self.call(0xF98C,0xFF62);yield from self.bank_call(0xF991,0x2E,0xA000)
        elif scene==5:
            yield from self.call(0xF9C2,0xFF62);yield from self.call(0xF9C5,0xFAA9)
            yield from self.bank_call(0xF9CA,0x37,0xA01B);yield from self.bank_call(0xF9D2,0x3D,0xA003);yield from self.call(0xF9D8,0xFABF)
        elif scene==6:yield from self.bank_call(0xFA01,0x2A,0xA003);yield from self.call(0xFA07,0xFF62)
        elif scene==7:
            yield from self.call(0xFA34,0xFAA9);yield from self.bank_call(0xFA39,0x3D,0xA003)
            yield from self.bank_call(0xFA41,0x28,0xA024);yield from self.call(0xFA47,0xFABF)
        elif scene==8:
            yield from self.call(0xFA7A,0xE6C6);yield from self.call(0xFA7D,0xFAA9)
            yield from self.bank_call(0xFA82,0x37,0xA01E);yield from self.call(0xFA88,0xFABF);yield from self.call(0xFA8B,0xFF62)
        yield from self.call({2:0xF8F5,3:0xF95B,4:0xF997,5:0xF9DB,6:0xFA0A,7:0xFA4A,8:0xFA8E}[scene],0xE830)
        if scene==3:self.a(m[0x9C]);m[0x9D]=r.a
        yield from self.call({2:0xF8F8,3:0xF964,4:0xF99A,5:0xF9DE,6:0xFA0D,7:0xFA4D,8:0xFA91}[scene],0xFB28)
    def busy_nmi(self):
        r=self.registers;m=self.memory;yield from self.call(0xFAD5,0xF206);yield from self.call(0xFAD8,0xFB0B)
        for address in (0xE3,0xE2,0xE1):self.a(m[address]);self.push(r.a)
        yield from self.bank_call(0xFAE6,0x2E,0xA003);self.a(m[0xA5]);yield from self.write(0xF800,r.a,0xFAEE)
        for shadow,address,pc in ((0xE1,0xE000,0xFAF4),(0xE2,0xE800,0xFAFC),(0xE3,0xF000,0xFB02)):
            self.a(self.pop());m[shadow]=r.a
            if shadow==0xE2:self.a(r.a|0xC0)
            yield from self.write(address,r.a,pc)
        yield from self.call(0xFB05,0xFB28)

    def irq_stop_counter(self):
        self.flag(I,True);self.a(0);self.memory[0x62]=0
        yield from self.write(0x5000,0,self.registers.pc);yield from self.write(0x5800,0,self.registers.pc)
    def irq_arm_row(self,entry):
        r=self.registers;m=self.memory;self.a(m[0x63]);self.shift_a('asl');self.x(r.a);self.a(0)
        yield from self.write(0x5000,r.a,entry+7);self.a(m[0x6A+r.x]);yield from self.write(0x5000,r.a,entry+13)
        self.a(m[0x6B+r.x]);yield from self.write(0x5800,r.a,entry+19);self.y(m[0x63])
    def irq_chr_row(self,row):
        """Four original scanline CHR groups. Ordering is bank-specific."""
        r=self.registers;m=self.memory;upper=0xC2+8*row;lower=upper-4
        self.a(m[upper]);self.y(m[upper+1]);self.x(m[upper+2])
        for address,value in ((0xA000,r.a),(0xA800,r.y),(0xB000,r.x)):yield from self.write(address,value,r.pc)
        self.a(m[upper+3]);yield from self.write(0xB800,r.a,r.pc)
        if row==0:
            self.a(m[lower]);self.y(m[lower+1]);self.x(m[lower+2])
            for address,value in ((0x8000,r.a),(0x8800,r.y),(0x9000,r.x)):yield from self.write(address,value,r.pc)
            self.a(m[lower+3]);yield from self.write(0x9800,r.a,r.pc)
        elif row==1:
            self.y(m[lower]);self.x(m[lower+1]);self.a(m[lower+2])
            for address,value in ((0x8000,r.y),(0x8800,r.x),(0x9000,r.a)):yield from self.write(address,value,r.pc)
            self.y(m[lower+3]);yield from self.write(0x9800,r.y,r.pc)
        else:
            self.y(m[lower]);self.x(m[lower+1]);yield from self.write(0x8000,r.y,r.pc);yield from self.write(0x8800,r.x,r.pc)
            self.a(m[lower+2]);self.y(m[lower+3]);yield from self.write(0x9000,r.a,r.pc);yield from self.write(0x9800,r.y,r.pc)
        if row==3:self.a(0);m[0x63]=r.a;self.inc(0x60)
        else:self.inc(0x63)
    def irq_normal_chr(self):
        r=self.registers;m=self.memory;self.a(m[0xBA]);self.y(m[0xBB]);self.x(m[0xBC])
        for address,value in ((0xA000,r.a),(0xA800,r.y),(0xB000,r.x)):yield from self.write(address,value,r.pc)
        self.a(m[0xBD]);yield from self.write(0xB800,r.a,r.pc)
        self.a(m[0xB6]);self.y(m[0xB7]);self.x(m[0xB8])
        for address,value in ((0x8000,r.a),(0x8800,r.y),(0x9000,r.x)):yield from self.write(address,value,r.pc)
        self.a(m[0xB9]);yield from self.write(0x9800,r.a,r.pc)
    def irq_scroll(self,selector=0xEA,order='yx',zero=False):
        r=self.registers;m=self.memory;self.a(m[selector])
        if order=='yx':self.y(m[0x9B]);self.x(m[0x9A]);yield from self.write(0x2006,r.y,r.pc);yield from self.write(0x2006,r.x,r.pc)
        else:self.x(m[0x9B]);self.y(m[0x9A]);yield from self.write(0x2006,r.x,r.pc);yield from self.write(0x2006,r.y,r.pc)
        self.x(0 if zero else m[0x96]);yield from self.write(0x2005,r.x,r.pc);yield from self.write(0x2005,r.x,r.pc)
    def irq_body(self):
        r=self.registers;m=self.memory;r.pc=0xFB2D;self.push(r.a);self.a(r.x);self.push(r.a);self.a(r.y);self.push(r.a)
        self.a((yield from self.read(0x5800,0xFB32)));self.a(r.a&127);self.cmp(r.a,127)
        if r.a!=127:
            r.pc=0xFB3C
            while True:yield ServiceWait('IRQ_counter_not_terminal',0xFB3C,0x5800,r.a,'Original program traps forever; later samples cannot release this branch')
        self.y(m[0x60]);mode=r.y
        for _ in range(min(mode,12)):self.y(r.y-1)
        r.pc=IRQ_ENTRIES[mode]if mode<len(IRQ_ENTRIES)else 0xFB92
        if mode in(1,3,7,8):
            yield from self.irq_arm_row(r.pc);row=m[0x63]
            if row==0:
                if mode==7:
                    self.a((yield from self.read(0x2002,0xFE27)));self.a(0xE1);self.x(0x25);self.y(0xB8)
                    for address in (0xC700,0xD000,0xC800,0xD800):yield from self.write(address,r.a,r.pc)
                    yield from self.write(0x2006,r.x,r.pc);yield from self.write(0x2006,r.y,r.pc)
                    self.a(15)
                    for address in (0xA000,0xA800,0xB000,0xB800):yield from self.write(address,r.a,r.pc)
                    self.x(0);yield from self.write(0x2005,r.x,r.pc);yield from self.write(0x2005,r.x,r.pc)
                yield from self.irq_chr_row(0)
            elif row in(1,2):self.y(row-1 if row==1 else 0);yield from self.irq_chr_row(row)
            elif mode==7:
                self.y((row-2)&255);self.a(0);m[0x63]=0;yield from self.irq_final_display(5)
            else:self.y((row-2)&255);yield from self.irq_chr_row(3)
        elif mode in(11,12):
            self.a(0);yield from self.write(0x5000,r.a,r.pc);base=0x6A if mode==11 else 0x6C
            self.a(m[base]);yield from self.write(0x5000,r.a,r.pc);self.a(m[base+1]);yield from self.write(0x5800,r.a,r.pc)
            self.inc(0x60,1 if mode==11 else -1)
            if mode==12:self.inc(0x60,-1)
            yield from self.irq_chr_row(0 if mode==11 else 1)
        elif mode in(2,4,5,9,10):yield from self.irq_final_display(mode)
        else:yield from self.irq_stop_counter()
        self.y(self.pop());self.x(self.pop());self.a(self.pop());self.rti()
    def irq_final_display(self,mode):
        r=self.registers;m=self.memory;yield from self.irq_stop_counter()
        if mode==2:
            self.y(8)
            while True:
                self.y(r.y-1)
                if r.y&128:break
            self.a(m[0x99]);self.a(r.a&7);self.shift_a('asl');self.y(r.a)
            self.a(m[0xFD1A+r.y]);m[0x46]=r.a;self.a(m[0xFD1B+r.y]);m[0x47]=r.a
            self.a(15)
            for address in range(0x8000,0xC000,0x800):yield from self.write(address,r.a,r.pc)
            while self.inc(0x46,-1):pass
            self.a(m[0xEA]);self.y(m[0x9B]);self.x(m[0x9A]);yield from self.write(0xC700,r.a,r.pc)
            yield from self.write(0x2006,r.y,r.pc);yield from self.write(0x2006,r.x,r.pc)
            self.x(m[0x96]);yield from self.write(0x2005,r.x,r.pc);yield from self.write(0x2005,r.x,r.pc)
            while self.inc(0x47,-1):pass
        elif mode==4:
            self.y(15)
            for address in (0xA000,0xA800,0xB000,0xB800):yield from self.write(address,r.y,r.pc)
            self.y(m[0x72])
            while True:
                self.y(r.y-1)
                if r.y&128:break
            yield from self.irq_scroll(order='xy');yield from self.write(0xC700,r.a,r.pc)
            self.y(m[0x73])
            while True:
                self.y(r.y-1)
                if r.y&128:break
        elif mode==5:
            self.a((yield from self.read(0x2002,0xFDA1)));self.a(0xE1);self.x(m[0x9B]);self.y(m[0x9A])
            for address in (0xC700,0xD000,0xC800,0xD800):yield from self.write(address,r.a,r.pc)
            yield from self.write(0x2006,r.x,r.pc);yield from self.write(0x2006,r.y,r.pc)
        elif mode==10:
            self.a((yield from self.read(0x2002,0xFED9)));self.a(m[0xEA]);yield from self.write(0xC000,r.a,r.pc)
            self.a(15);self.y(m[0x9B]);self.x(m[0x9A])
            for address in (0xA000,0xA800,0xB000,0xB800):yield from self.write(address,r.a,r.pc)
            yield from self.write(0x2006,r.y,r.pc);yield from self.write(0x2006,r.x,r.pc)
            self.a(0);yield from self.write(0x2005,r.a,r.pc);yield from self.write(0x2005,r.a,r.pc);self.y(16)
            while True:
                self.y(r.y-1)
                if r.y&128:break
        # Final CHR restoration contains different register load orders and
        # deliberate scanline delays. Preserve their final scratch/flags;
        # no cycle count or actual scanline is invented here.
        if mode in(2,4,5):
            if mode==5:self.y(m[0xBB]);self.x(m[0xBC]);self.a(m[0xBA])
            else:self.a(m[0xBA]);self.y(m[0xBB]);self.x(m[0xBC])
            for address,value in ((0xA000,r.a),(0xA800,r.y),(0xB000,r.x)):yield from self.write(address,value,r.pc)
            self.a(m[0xBD]);yield from self.write(0xB800,r.a,r.pc)
            if mode==5:
                self.x(m[0x96]);yield from self.write(0x2005,r.x,r.pc);yield from self.write(0x2005,r.x,r.pc)
            self.y(0x1B if mode==2 else m[0x74]if mode==4 else 0x30)
            while True:
                self.y(r.y-1)
                if (r.y==0 if mode==2 else r.y&128):break
            self.a(m[0xB6]);self.y(m[0xB7]);self.x(m[0xB8])
            for address,value in ((0x8000,r.a),(0x8800,r.y),(0x9000,r.x)):yield from self.write(address,value,r.pc)
            self.a(m[0xB9]);yield from self.write(0x9800,r.a,r.pc)
        else:yield from self.irq_normal_chr()
