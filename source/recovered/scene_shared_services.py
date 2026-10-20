"""Readable shared scene calls: messages, menus, fades, pointers and arithmetic.

Each routine consumes the real caller frame through the recovered service
protocol. Unavailable hardware remains resumable. ROM supplies immutable data,
never executable opcodes or control IR. These software requests do not imply a
completed NES frame, message, fade or sound.
"""
import hashlib
from .battle_nmi_services import BattleNMIServices,ServiceWait
from .battle_graphics_services import BattleGraphicsServices,GraphicsData,GraphicsRegisters
from .audio_services import AudioServices,AudioData
from .controller_helpers import ControlHelpers
from .officers import ROM_SHA256


class SceneSharedServices(BattleNMIServices):
    EXTRA=(0xE749,0xE74D,0xE753,0xE768,0xE774,0xE7DF,0xE7B5,
           0xECBF,0xECEE,0xED19,0xED1E,0xED23,0xED28,0xED2D,0xED32,0xED37,0xED3C,0xED41,0xEDDD,0xEDF5,
           0xF26D,0xF283,0xF28B,0xF293,0xF29B,0xF2AF,0xF2D7,0xF368,0xF387,
           0xE843,0xE84B,0xE850,0xE856,0xE85C,0xE862,0xE87A,0xE88A,0xE89A,0xE8AA,
           0xEA7C,0xEAA5,0xEBCA,0xEBE9,0xE9BA,0xF092,0xF1AD,0xEE07,
           0xE57F,0xE609,0xE66B,0xE673,0xE67B,0xE683,0xE68B,0xE693,0xE69B)
    FIXED=BattleNMIServices.FIXED+EXTRA
    def __init__(self,memory,rom,callbacks=None):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned original scene ROM required')
        super().__init__(memory,callbacks)
        self.rom=bytes(rom);self.graphics=BattleGraphicsServices(memory,GraphicsData.from_rom(rom))
        self.audio=AudioServices(memory,AudioData.from_rom(rom));self._call_owner=None
    def __call__(self,call):
        if call.target not in self.FIXED:return {'status':'dependency','target':call.target,'reason':'Shared scene body has no recovered owner'}
        if self._program is not None:
            if self._call_owner is not call:return {'status':'dependency','reason':'Another caller owns the pending shared service'}
            result=self.resume()
        else:
            self._call_owner=call;result=self.run_service(call.target,call.registers)
        if result['status']=='returned':self._call_owner=None
        return result
    def routine(self,entry):
        if entry in (0xF26D,0xF283,0xF28B,0xF293,0xF29B):self.queue_message(entry)
        elif entry in (0xECBF,0xECEE):self.begin_palette_transition(entry==0xECBF)
        elif entry in (0xE749,0xE74D):self.a(30 if entry==0xE749 else 0);self.memory[0x8C]=self.registers.a
        elif entry==0xE768:
            self.a(self.memory[0x8B]&127);self.memory[0x8B]=self.registers.a
            yield from self.write(0x2000,self.registers.a,0xE770)
        elif entry==0xE753:
            self.a((yield from self.read(0x2002,0xE753)));self.y(0);self.memory[0x7B]=self.memory[0x7E]=0
            self.a(self.memory[0x8B]|128);self.memory[0x8B]=self.registers.a
            yield from self.write(0x2000,self.registers.a,0xE770)
        elif entry in (0xE774,0xE7DF,0xE7B5):yield from self.clear_nametables(entry)
        elif entry in range(0xED19,0xED42,5)or entry in (0xED41,0xEDDD):yield from self.menu(entry)
        elif entry==0xEDF5:yield from self.menu_sprite()
        elif entry==0xEE07:yield from self.far_call()
        elif entry in (0xF2AF,0xF2D7,0xF368,0xF387):yield from self.record_pointer(entry)
        elif entry in (0xE87A,0xE88A,0xE89A,0xE8AA):
            ControlHelpers()(self,entry,None,'call')
        elif entry in (0xE843,0xE84B,0xE850,0xE856,0xE85C,0xE862):yield from self.random_range(entry)
        elif entry in (0xEA7C,0xEAA5):self.divide(entry==0xEAA5)
        elif entry==0xEBE9:self.multiply()
        elif entry==0xEBCA:
            self.a(0);self.memory[2]=0;yield from self.call(0xEBCE,0xEBE9)
            for src,dest in ((6,0),(7,1),(8,2)):self.a(self.memory[src]);self.memory[dest]=self.registers.a
            self.a(100);self.memory[3]=100;self.a(0);self.memory[4]=0;yield from self.call(0xEBE5,0xEAA5)
        elif entry==0xE9BA:self.decimal_digits()
        elif entry in (0xF092,0xF1AD):
            r=self.registers;gr=GraphicsRegisters(r.a,r.x,r.y,r.p)
            result=(self.graphics.world_sprites if entry==0xF092 else self.graphics.screen_sprites)(gr)
            for k,v in result['registers'].items():setattr(r,k,v)
        elif entry in (0xE57F,0xE609,0xE66B,0xE673,0xE67B,0xE683,0xE68B,0xE693,0xE69B):
            r=self.registers;result=self.audio.reset(registers=r)if entry==0xE57F else self.audio.request(r.a,entry=entry,registers=r)
            if result['status']!='returned':yield ServiceWait('audio_service',entry,reason='Original driver did not return')
            else:
                for k,v in result['contract_registers'].items():setattr(r,k,v)
        else:yield from super().routine(entry)
    def queue_message(self,entry):
        m=self.memory
        if entry==0xF29B:m[0x310]=self.registers.a;self.a(255);m[0x311]=255
        else:
            m[0x311]=self.registers.a;self.a({0xF26D:0,0xF283:2,0xF28B:4,0xF293:5}[entry]);m[0x310]=self.registers.a;self.a(255)
        m[0x312]=m[0x313]=255;self.a(0);m[0x300]=0
    def begin_palette_transition(self,fade_in):
        m=self.memory;self.a(0 if fade_in else 1);m[0x87]=self.registers.a
        self.a(4 if fade_in else 0);m[0x88]=self.registers.a;self.a(4);m[0x89]=4
        m[0]=0;m[1]=1;m[2]=32;m[3]=1;self.y(0)
        for index in range(32):
            self.a(m[0x100+index]);m[0x120+index]=self.registers.a
            if fade_in:self.a(15);m[0x100+index]=15
            self.y(index+1);self.cmp(self.registers.y,32)
    def clear_nametables(self,entry):
        m=self.memory
        if entry!=0xE7B5:
            for index,(address,value)in enumerate(((0xC000,224),(0xC800,225),(0xD000,224),(0xD800,225))):
                self.a(value);yield from self.write(address,value,entry+2+5*index)
            for index,high in enumerate((32,36,40)):
                self.a((yield from self.read(0x2002,entry+20+16*index)));self.a(1);m[2]=1
                self.a(170 if entry==0xE7DF else 0);m[3]=self.registers.a;self.a(high)
                if index<2:yield from self.call((0xE800 if entry==0xE7DF else 0xE795)+16*index,0xE7B5)
                else:yield from self.routine(0xE7B5)
            return
        yield from self.write(0x2006,self.registers.a,0xE7B5);self.a(0);yield from self.write(0x2006,0,0xE7BA);self.y(0);self.a(3);m[1]=3;self.a(m[2])
        for block in range(3):
            for _ in range(256):yield from self.write(0x2007,self.registers.a,0xE7C4);self.y(self.registers.y-1)
            self.inc(1,-1)
        for _ in range(192):yield from self.write(0x2007,self.registers.a,0xE7CE);self.y(self.registers.y+1);self.cmp(self.registers.y,192)
        self.a(m[3])
        for _ in range(64):yield from self.write(0x2007,self.registers.a,0xE7D8);self.y(self.registers.y+1)
    def record_pointer(self,entry):
        m=self.memory;r=self.registers
        if entry==0xF2D7:ControlHelpers()(self,entry,None,'call');return
        if entry==0xF368:
            self.a(r.a&15);self.shift_a('asl');self.y(r.a)
            self.a(m[0xF379+r.y]);m[0]=r.a;self.a(m[0xF37A+r.y]);m[1]=r.a;return
        ident=r.a
        if entry==0xF387:self.y(49);yield from self.call(0xF389,0xF25F)
        self.y(0);m[1]=0
        if entry==0xF2AF:
            for _ in range(5):self.shift_a('asl');self._shift_memory(1,'rol')
            self.flag(1,False);self.add(0);m[0]=r.a;self.a(m[1]);self.add(96);m[1]=r.a
        else:
            m[0]=r.a;self.shift_a('asl');self._shift_memory(1,'rol');self.flag(1,False);self.add(m[0]);self.push(r.a)
            self.a(m[1]);self.add(0);m[1]=r.a;self.a(self.pop())
            for _ in range(2):self.shift_a('asl');self._shift_memory(1,'rol')
            self.flag(1,False);self.add(0);m[0]=r.a;self.a(m[1]);self.add(128);m[1]=r.a
    def random_range(self,entry):
        m=self.memory;r=self.registers
        if entry==0xE862:m[0x10]=r.a;self.cmp(r.a,15)
        bound=100 if entry==0xE843 else m[0x10]if entry==0xE862 else None
        mask={0xE850:3,0xE856:7,0xE85C:15}.get(entry,15 if entry==0xE862 and bound<15 else 255)
        site={0xE843:0xE843,0xE84B:0xE84B,0xE850:0xE850,0xE856:0xE856,0xE85C:0xE85C,0xE862:0xE868 if bound is not None and bound<15 else 0xE872}[entry]
        if bound==0:
            while True:
                r.pc=site;yield ServiceWait('nonterminating_zero_rng_bound',site,address=0x10,value=0,reason='Original rejection loop has no accepted byte')
        for _ in range(256):
            yield from self.call(site,0xE87A)
            if entry==0xE84B:self.shift_a('lsr');return
            if mask!=255:self.a(r.a&mask)
            if bound is None:return
            self.cmp(r.a,bound)
            if r.a<bound:return
        raise ValueError('Pinned permutation failed its expected bounded draw')
    def _shift_memory(self,address,kind):
        v=self.memory[address];carry=bool(self.registers.p&1)
        self.flag(1,bool(v&128)if kind in ('asl','rol')else bool(v&1))
        self.memory[address]=self.nz(v<<1 if kind=='asl'else(v<<1)|carry if kind=='rol'else v>>1)
    def divide(self,wide):
        """Restoring long division, preserving quotient/remainder scratch."""
        m=self.memory;r=self.registers;self.a(0);m[5]=m[6]=0
        if wide:m[7]=0
        self.y(23 if wide else 15)
        for _ in range(24 if wide else 16):
            for address in ((0,1,2,5,6,7)if wide else(1,2,5,6)):self._shift_memory(address,'asl'if address==(0 if wide else 1)else'rol')
            self.a(m[5]);self.flag(1,True);self.add(m[3],subtract=True);m[8 if wide else 7]=r.a
            self.a(m[6]);self.add(m[4],subtract=True)
            if wide:m[9]=r.a;self.a(m[7]);self.add(0,subtract=True)
            if r.p&1:
                m[7 if wide else 6]=r.a;self.a(m[8 if wide else 7]);m[5]=r.a
                if wide:self.a(m[9]);m[6]=r.a
                self.inc(0 if wide else 1)
            self.y(r.y-1)
    def multiply(self):
        """Original eight-step8×16 product and four-byte work registers."""
        m=self.memory;r=self.registers;self.y(7);self.a(0)
        for i in range(4,10):m[i]=0
        for _ in range(8):
            self._shift_memory(3,'lsr')
            if r.p&1:
                for index,operand in enumerate((0,1,2,4)):
                    self.a(m[operand]);
                    if index==0:self.flag(1,False)
                    self.add(m[6+index]);m[6+index]=r.a
            for index in (0,1,2,4):self._shift_memory(index,'asl'if index==0 else'rol')
            self.y(r.y-1)
    def decimal_digits(self):
        """Six packed digits via the original destructive decimal remainders."""
        m=self.memory;r=self.registers;self.a(0);m[7]=m[8]=m[9]=0
        for amount,width,destination,high_digit in ((1000000,3,None,False),(100000,3,9,True),(10000,3,9,False),(1000,2,8,True),(100,2,8,False),(10,2,7,True)):
            while True:
                self.a(m[1]);self.flag(1,True);self.add(amount&255,subtract=True);m[4]=r.a
                self.a(m[2]);self.add((amount>>8)&255,subtract=True)
                if width==3:m[5]=r.a;self.a(m[3]);self.add(amount>>16,subtract=True)
                if not r.p&1:break
                m[width]=r.a;self.a(m[4]);m[1]=r.a
                if width==3:self.a(m[5]);m[2]=r.a
                if destination is not None:
                    if high_digit:self.a(m[destination]);self.add(15);m[destination]=r.a
                    else:self.inc(destination)
        self.a(m[1]|m[7]);m[7]=r.a
    def _menu_value(self):
        m=self.memory;r=self.registers;self.a(0);self.y(m[0x425]);self.cmp(r.y,0)
        while r.y:
            self.flag(1,False);self.add(m[0]);self.y(r.y-1);self.cmp(r.y,0)
        self.flag(1,False);self.add(m[0x424]);self.y(r.a);self.a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535]);return r.a
    def menu(self,entry):
        m=self.memory;r=self.registers
        if entry==0xEDDD:self._menu_value();return
        if entry!=0xED41:self.a((entry-0xED19)//5+1)
        m[0]=r.a;buttons=m[0x81]
        if buttons&128:
            self.inc(0x424);value=self._menu_value()
            if value&128 or m[0x424]>=m[0]:
                self.inc(0x424,-1)
                if m[0x12]==0:self.a(0);m[0x424]=0
        if buttons&64:
            self.inc(0x424,-1)
            if m[0x424]&128:
                self.inc(0x424)
                if m[0x12]==0:
                    self.a(m[0]);m[0x424]=r.a
                    while True:
                        found=False
                        for _ in range(256):
                            self.inc(0x424,-1);value=self._menu_value();self.cmp(value,255)
                            if value!=255:found=True;break
                        if found:break
                        r.pc=0xED9E;yield ServiceWait('menu_no_valid_column',0xED9E,reason='Original sentinel search is still cyclic')
        if buttons&32:
            self.inc(0x425);value=self._menu_value()
            if value&128:
                self.inc(0x425,-1)
                if m[0x12]==0:self.a(0);m[0x425]=0
        if buttons&16:
            self.inc(0x425,-1)
            if m[0x425]&128:
                self.inc(0x425)
                if m[0x12]==0:
                    self.x(255);self.y(m[0x424])
                    while True:
                        found=False
                        for _ in range(256):
                            self.x(r.x+1);self.a(r.y);self.flag(1,False);self.add(m[0]);self.y(r.a)
                            self.a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                            if r.a&128:found=True;break
                        if found:break
                        r.pc=0xEDCF;yield ServiceWait('menu_no_end_sentinel',0xEDCF,reason='Original column scan is still cyclic')
                    m[0x425]=r.x
        value=self._menu_value();m[0x12]=value
    def menu_sprite(self):
        m=self.memory;r=self.registers;self.shift_a('asl');self.y(r.a)
        self.a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535]);m[0xA]=r.a;self.y(r.y+1)
        self.a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535]);m[0xC]=r.a;self.a(0);m[2]=0
        yield from self.routine(0xF1AD)
    def far_call(self):
        """EE07 real inline word, saved PRG pair and callee return frame.

        The two bytes after the caller JSR are a data pointer. Only a known
        source callee may satisfy it; no opcode is fetched or executed here.
        """
        m=self.memory;r=self.registers;self.a(m[0xE2]);m[0x58]=r.a;m[0x5D]=r.y
        self.a(self.pop());self.flag(1,False);self.add(1);m[0x59]=r.a
        self.a(self.pop());self.add(0);m[0x5A]=r.a;self.y(0)
        pointer=m[0x59]|m[0x5A]<<8;self.a(m[pointer]);m[0x5B]=r.a
        self.y(1);self.a(m[(pointer+1)&65535]);m[0x5C]=r.a
        self.y(m[0x5D]);yield from self.call(0xEE2D,0xF237)
        self.inc(0x59)
        if m[0x59]==0:self.inc(0x5A)
        self.a(m[0x5A]);self.push(r.a);self.a(m[0x59]);self.push(r.a)
        self.a(m[0x58]);self.push(r.a);self.a(238);self.push(r.a);self.a(76);self.push(r.a)
        yield from self._external(m[0x5B]|m[0x5C]<<8,'far_callee')
        self.a(self.pop());self.y(r.a);yield from self.call(0xEE4F,0xF237)
