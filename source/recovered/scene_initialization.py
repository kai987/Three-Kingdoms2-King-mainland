"""Readable battle/attack/duel setup and their actual display prerequisites.

The three global setup routes end at the original E066 main-loop boundary.
Banked calls remain actual owned services; no background, fade or message is
marked ready merely because setup requested it. ROM is immutable game data.
"""
from .scene_shared_services import SceneSharedServices
from .battle_nmi_services import ServiceCall


class SceneInitialization(SceneSharedServices):
    SETUP_ENTRIES=(0xE18B,0xE22F,0xE2E8)
    EXTRA_SETUP=(0xE4DA,0xE370,0xE51F,0xE823)
    FIXED=SceneSharedServices.FIXED+EXTRA_SETUP
    def run_setup(self,entry,registers=None):
        if entry not in self.SETUP_ENTRIES:raise ValueError('Only original battle/attack/duel setup entries allowed')
        return self._start(lambda:self.setup(entry),registers,'global_scene_setup')
    def routine(self,entry):
        if entry==0xE4DA:yield from self.reset_scene_working_display()
        elif entry==0xE370:
            self.y(61);yield from self.call(0xE372,0xF237);yield from self.call(0xE375,0xA01B);yield from self.call(0xE378,0xF206)
        elif entry==0xE51F:yield from self.nametable_configuration()
        elif entry==0xE823:self.y(4);yield from super().routine(0xE825)
        else:yield from super().routine(entry)
    def reset_scene_working_display(self):
        m=self.memory
        yield from self.call(0xE4DA,0xE768);yield from self.call(0xE4DD,0xE74D)
        yield from self.write(0x2001,self.registers.a,0xE4E0)
        yield from self.call(0xE4E3,0xE57F);yield from self.call(0xE4E6,0xE7DF)
        self.a(0)
        for address in(0x90,0x91,0x8E,0x8F,0x98,0x99,0x96,0x97,0x7E,0x5E,0x5F,0x8D,0xA4):m[address]=0
        self.a(255);m[0x300]=m[0x304]=255
        yield from self.routine(0xE823)
    def nametable_configuration(self):
        r=self.registers;m=self.memory
        for _ in range(3):self.shift_a('asl')
        self.y(r.a)
        for index in range(8):
            self.a(m[0xE567+r.y]);m[0xE6+index]=r.a
            if index<4:yield from self.write(0xC000+0x800*index,r.a,0xE529+10*index)
            if index!=7:self.y(r.y+1)
    def _select_pair(self,selector,call_pc):
        self.y(selector);yield from self.call(call_pc,0xF237)
    def setup(self,entry):
        m=self.memory;r=self.registers
        yield from self.call(entry,0xE4DA)
        self.a({0xE18B:3,0xE22F:4,0xE2E8:5}[entry]);m[0x78]=r.a
        if entry==0xE22F:self.a(m[0x544]);self.flag(1,False);self.add(2)
        else:self.a(1 if entry==0xE18B else 10)
        yield from self.call({0xE18B:0xE195,0xE22F:0xE23D,0xE2E8:0xE2F2}[entry],0xE370)
        if entry==0xE18B:
            yield from self._select_pair(55,0xE19A);yield from self.call(0xE19D,0xA027)
            self.a(m[0x500]);self.cmp(r.a,11)
            if r.a==11:yield from self._select_pair(44,0xE1A9);yield from self.call(0xE1AC,0xA006)
            else:yield from self._select_pair(40,0xE1B4);yield from self.call(0xE1B7,0xA003)
            for src,dest in((0x510,0x90),(0x511,0x91),(0x512,0x8E),(0x513,0x8F)):self.a(m[src]);m[dest]=r.a
            self.a(255);m[0x518]=255;yield from self._select_pair(55,0xE1D9);yield from self.call(0xE1DC,0xA009)
            yield from self._select_pair(61,0xE1E1);self.a(1);m[0]=1;yield from self.call(0xE1E9,0xA015);yield from self.call(0xE1EC,0xEAF7)
            self.a(0);m[0x508]=0;self.a(112);m[0x68]=112;self.a(175);m[0x69]=175
            self.a(1);yield from self.call(0xE200,0xE51F);self.a(1);m[0x97]=1;yield from self.call(0xE208,0xECBF)
            self.a(5);m[0x61]=5;self.inc(0x7A);self.a(29);yield from self.call(0xE215,0xE673)
            yield from self.call(0xE218,0xE749);yield from self.call(0xE21B,0xE753)
        elif entry==0xE22F:
            self.a(2);yield from self.call(0xE242,0xE51F);yield from self._select_pair(55,0xE247);yield from self.call(0xE24A,0xA024)
            yield from self._select_pair(61,0xE24F);self.a(m[0x544]);self.flag(1,False);self.add(2);m[0]=r.a;yield from self.call(0xE25B,0xA015)
            self.y(m[0x563]);self.a(m[0xE2DE+r.y]);m[0x107]=m[0x113]=r.a
            self.y(m[0x562]);self.a(m[0xE2DE+r.y]);m[0x10F]=m[0x117]=r.a
            yield from self.call(0xE276,0xEAF7);yield from self._select_pair(61,0xE27B);self.a(1);yield from self.call(0xE280,0xA045)
            self.a(160);m[0x98]=160;yield from self.call(0xE288,0xECBF);self.inc(0x7A);self.a(13);yield from self.call(0xE290,0xE683)
            yield from self.call(0xE293,0xE749);yield from self.call(0xE296,0xE753)
        else:
            self.a(160);m[0x98]=160;self.y(48);yield from self.call(0xE2FC,0xF25F)
            self.a(0);m[0xA]=0;self.a(132);m[0xB]=132;self.a(0);m[0]=0;self.a(32);m[1]=32
            yield from self._select_pair(55,0xE315);yield from self.call(0xE318,0xA003)
            yield from self._select_pair(61,0xE31D);self.a(10);m[0]=10;yield from self.call(0xE325,0xA015);yield from self.call(0xE328,0xEAF7)
            self.x(0);self.a(m[0x4AB]);self.cmp(r.a,1)
            if r.a==1:m[0x106]=m[0x116]=0
            self.a(m[0x4AC]);self.cmp(r.a,1)
            if r.a==1:m[0x10E]=m[0x11A]=0
            yield from self.call(0xE347,0xECBF);yield from self._select_pair(61,0xE34C);self.a(2);yield from self.call(0xE351,0xA045)
            self.a(0);yield from self.call(0xE356,0xE51F);self.inc(0x7A);self.a(18);yield from self.call(0xE35E,0xE67B)
            yield from self.call(0xE361,0xE749);yield from self.call(0xE364,0xE753)
        r.pc=0xE066
    def banked_graphics(self,call):
        """Known pair29/30 palette/CHR/IRQ setup and pair23 raw loaders."""
        pair=tuple(call.entry_banks[1:3]);target=call.target
        methods={(29,30):{0xA015:self.copy_palette,0xDBB1:self.copy_palette,0xA01B:self.load_scene_chr,0xDE7E:self.load_scene_chr,0xA045:self.configure_scene_irq,0xDEB9:self.configure_scene_irq},
                 (23,24):{0xA003:self.copy_nametable,0xA212:self.copy_nametable,0xA027:self.battle_map_descriptors,0xDF15:self.battle_map_descriptors,0xA000:self.inflate_nametable,0xA087:self.inflate_nametable,0xA006:self.expand_metatiles,0xA24E:self.expand_metatiles,0xA024:self.attack_background,0xA02A:self.attack_background,0xA04A:self.attack_background_page}}
        method=methods.get(pair,{}).get(target)
        if method is None:return {'status':'dependency','target':target,'banks':list(call.entry_banks),'reason':'Scene graphics callee is outside recovered setup routines'}
        if self._program is not None:
            if self._call_owner is not call:return {'status':'dependency','reason':'Another caller owns the pending graphics input'}
            return self.resume()
        self._call_owner=call
        def body():yield from method();self.rts()
        result=self._start(body,call.registers,'banked_scene_graphics')
        if result['status']=='returned':self._call_owner=None
        return result
    def copy_palette(self):
        m=self.memory;r=self.registers;self.a(m[0]);self.shift_a('asl');self.y(r.a)
        self.a(m[0xDBCF+r.y]);m[0xA]=r.a;self.a(m[0xDBD0+r.y]);m[0xB]=r.a;self.y(0)
        for index in range(32):self.a(m[((m[0xA]|m[0xB]<<8)+index)&65535]);m[0x100+index]=r.a;self.y(index+1);self.cmp(r.y,32)
        yield from ()
    def load_scene_chr(self):
        m=self.memory;r=self.registers;self.y(33);yield from self.call(0xDE80,0xF25F);self.y(0);m[1]=0;m[0]=r.a
        self.shift_a('asl');self.flag(1,False);self.add(m[0])
        for _ in range(4):self.shift_a('asl');self._shift_memory(1,'rol')
        self.flag(1,False);self.add(108);m[2]=r.a;self.a(148);self.add(m[1]);m[3]=r.a
        for index in range(48):self.a(m[((m[2]|m[3]<<8)+index)&65535]);m[0xAE+index]=r.a;self.y(index+1);self.cmp(r.y,48)
    def configure_scene_irq(self):
        m=self.memory;r=self.registers;m[0]=r.a;self.x(r.a);self.shift_a('asl');self.shift_a('asl');self.flag(1,False);self.add(m[0]);self.shift_a('asl');self.y(r.a)
        for index in range(10):self.a(m[0xDF1A+r.y+index]);m[0x68+index]=r.a
        for src,dest in((0xDF56,0x72),(0xDF5C,0x73),(0xDF62,0x74),(0xDF68,0x61)):self.a(m[src+r.x]);m[dest]=r.a
        yield from ()
    def battle_map_descriptors(self):
        m=self.memory;r=self.registers;self.a(m[0x50E]);self.shift_a('asl');self.y(r.a)
        self.a(m[0xDF4A+r.y]);m[0]=r.a;self.a(m[0xDF4B+r.y]);m[1]=r.a;self.y(0)
        for index in range(4):self.a(m[((m[0]|m[1]<<8)+index)&65535]);m[0xAA+index]=r.a;self.y(index+1)
        # The fourth value has no trailing INY in the original body.
        self.y(3);self.a(170);m[0xA8]=170;self.a(0);m[0xA9]=0
        yield from ()
    def _ppu_destination(self,pc):
        m=self.memory;self.a(m[0x8B]&251);yield from self.write(0x2000,self.registers.a,pc+5)
        self.a((yield from self.read(0x2002,pc+8)));self.a(m[1]);yield from self.write(0x2006,self.registers.a,pc+14)
        self.a(m[0]);yield from self.write(0x2006,self.registers.a,pc+20)
    def copy_nametable(self):
        m=self.memory;r=self.registers;yield from self._ppu_destination(0xA212);self.y(0);m[0xC]=m[0xD]=0
        for _ in range(1024):
            pointer=m[0xA]|m[0xB]<<8;self.a(m[pointer]);yield from self.write(0x2007,r.a,0xA233)
            self.inc(0xA)
            if m[0xA]==0:self.inc(0xB)
            self.inc(0xC)
            if m[0xC]==0:self.inc(0xD)
            self.a(m[0xD]);self.cmp(r.a,4)
    def inflate_nametable(self):
        """Marker/run-length game data; no6502 instruction decoding."""
        m=self.memory;r=self.registers;yield from self._ppu_destination(0xA087);self.y(0)
        self.a(m[m[0xA]|m[0xB]<<8]);m[2]=r.a;self._advance_inflate_pointer()
        for _ in range(65536):
            self.a(m[m[0xA]|m[0xB]<<8]);self.cmp(r.a,m[2])
            if r.a!=m[2]:yield from self.write(0x2007,r.a,0xA0AF);self._advance_inflate_pointer();continue
            self._advance_inflate_pointer();self.a(m[m[0xA]|m[0xB]<<8]);self.x(r.a)
            if r.x==0:return
            self._advance_inflate_pointer();self.a(m[m[0xA]|m[0xB]<<8])
            while r.x:yield from self.write(0x2007,r.a,0xA0C5);self.x(r.x-1)
            self._advance_inflate_pointer()
        raise ValueError('Original compressed nametable terminator not reached')
    def _advance_inflate_pointer(self):
        m=self.memory;r=self.registers;self.a(m[0xA]);self.flag(1,False);self.add(1);m[0xA]=r.a;self.a(m[0xB]);self.add(0);m[0xB]=r.a
    def expand_metatiles(self):
        m=self.memory;r=self.registers;yield from self._ppu_destination(0xA24E)
        self.a(m[0xA]);self.flag(1,True);self.add(64,subtract=True);self.push(r.a);self.a(m[0xB]);self.add(0,subtract=True);self.push(r.a)
        self.y(0);m[2]=m[3]=0
        for _ in range(480):
            self.y(0);m[1]=0;self.a(m[m[0xA]|m[0xB]<<8])
            for _ in range(2):self.shift_a('asl');self._shift_memory(1,'rol')
            self.flag(1,False);self.add(m[0xC]);m[0]=r.a;self.a(m[1]);self.add(m[0xD]);m[1]=r.a
            self.a(m[2]&16)
            if r.a:self.y(2)
            self.a(m[((m[0]|m[1]<<8)+r.y)&65535]);yield from self.write(0x2007,r.a,0xA2A4)
            self.y(r.y+1);self.a(m[((m[0]|m[1]<<8)+r.y)&65535]);yield from self.write(0x2007,r.a,0xA2AA)
            self.inc(0xA)
            if m[0xA]==0:self.inc(0xB)
            self.inc(2);self.a(m[2]&15)
            if r.a==0:
                self.inc(3);self.a(m[3]&1)
                if r.a:
                    self.a(m[0xA]);self.flag(1,True);self.add(16,subtract=True);m[0xA]=r.a;self.a(m[0xB]);self.add(0,subtract=True);m[0xB]=r.a
            self.a(m[3]);self.cmp(r.a,30)
        self.a(self.pop());m[0xB]=r.a;self.a(self.pop());m[0xA]=r.a;self.x(64);self.y(0)
        for _ in range(64):self.a(m[((m[0xA]|m[0xB]<<8)+r.y)&65535]);yield from self.write(0x2007,r.a,0xA2DC);self.y(r.y+1);self.x(r.x-1)
    def attack_background(self):
        self.y(33);yield from self.call(0xA02C,0xF25F);self.a(0);self.memory[0]=0;self.a(32);self.memory[1]=32
        yield from self._local_graphics_call(0xA039,self.attack_background_page)
        self.a(0);self.memory[0]=0;self.a(36);self.memory[1]=36
        yield from self._local_graphics_call(0xA046,self.attack_background_page)
    def _local_graphics_call(self,pc,method):
        self.push((pc+2)>>8);self.push(pc+2);yield from method();self.rts()
    def attack_background_page(self):
        m=self.memory;r=self.registers;self.a(m[0x544]);self.shift_a('asl');self.y(r.a)
        for src,dest in((0xA06B,0xA),(0xA06C,0xB),(0xA079,0xC),(0xA07A,0xD)):self.a(m[src+r.y]);m[dest]=r.a
        yield from self._local_graphics_call(0xA067,self.expand_metatiles)
