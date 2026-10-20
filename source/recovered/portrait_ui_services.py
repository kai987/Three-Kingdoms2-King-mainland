"""Original portrait OAM requests, with actual mapper and caller protocol.

Physical25 A000 is JMP physical26 CE1F. It constructs two portrait layers;
it does not draw the numerical officer card, upload CHR, perform OAM DMA or
complete a video frame. ROM supplies immutable maps and sprite descriptors.
No original CPU, opcode decoder, IR or fabricated readiness is used here.
"""
from dataclasses import dataclass
import hashlib
from .battle_nmi_services import BattleNMIServices,ServiceWait

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'

@dataclass(frozen=True)
class PortraitData:
    chr_page_by_byte_id:bytes
    resource_bank1:bytes
    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned original ROM required')
        return cls(bytes(rom[0x34EE6:0x34FE6]),bytes(rom[0x2010:0x4010]))

class PortraitUIServices(BattleNMIServices):
    """One real caller-owned service; pending original loops remain pending.

    ``run_entry(entry,registers)`` consumes the existing caller RTS frame.
    ``services`` is accepted for the common service-owner API; every helper
    in this particular closure is independently recovered locally.
    """
    FIXED=(0xA000,0xCE1F,0xF1B7,0xF25F)
    def __init__(self,memory,data,services=None):
        super().__init__(memory,callbacks=services)
        self.data=data if isinstance(data,PortraitData)else PortraitData.from_rom(data)
        self._call_owner=None;self.source_locations=[];self.layers=[]
    def mark(self,pc):
        self.registers.pc=pc;self.source_locations.append(pc)
    def result(self,status,**extra):
        value=super().result(status,**extra)
        return dict(value,source_locations=list(self.source_locations),portrait_layers=list(self.layers),
                    full_NES_frame=False,CHR_upload_completed=False,OAM_DMA_requested=False)
    def run_entry(self,entry=0xA000,registers=None):
        if entry not in self.FIXED:raise ValueError('Entry is outside the independently recovered portrait closure')
        if self._program is not None:raise RuntimeError('An original service is pending; resume its owner first')
        if entry in(0xA000,0xCE1F)and tuple(getattr(self.memory,'banks',())[1:3])!=(25,26):
            raise ValueError('Portrait entry requires its actual physical25/26 caller pair')
        if registers is None:raise ValueError('Supply real caller registers and an existing RTS frame')
        self.source_locations=[];self.layers=[]
        return self.run_service(entry,registers)
    def portrait(self,registers=None):return self.run_entry(0xA000,registers)
    def __call__(self,call):
        if call.target not in self.FIXED:return dict(status='dependency',reason='No portrait body owns this exact entry',target=call.target)
        if call.target in(0xA000,0xCE1F)and tuple(call.entry_banks[1:3])!=(25,26):
            return dict(status='dependency',reason='Portrait target belongs to another physical bank pair')
        if self._program is not None:
            if self._call_owner is not call:return dict(status='dependency',reason='Another caller owns the pending portrait service')
            result=self.resume()
        else:
            self._call_owner=call;result=self.run_entry(call.target,call.registers)
        if result['status']=='returned':
            self._call_owner=None
            if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:
                return dict(status='dependency',reason='Portrait did not reach its actual caller PC/SP',body=result)
        return result
    def routine(self,entry):
        if entry==0xA000:
            self.mark(0xA000);yield from self.draw_portrait()
        elif entry==0xCE1F:yield from self.draw_portrait()
        elif entry==0xF1B7:yield from self.append_screen_sprites()
        elif entry==0xF25F:
            self.mark(0xF25F);self.memory[0xE1]=self.registers.y
            yield from self.write(0xE000,self.registers.y,0xF262)
        else:raise ValueError('Unrecovered portrait service entry')
    def draw_portrait(self):
        """CE1F..CED5: body and mouth layers, CHR shadows and blink choice."""
        m=self.memory;r=self.registers
        self.mark(0xCE1F);self.a(m[0x6FEA]);self.a(r.a&4)
        if r.a:self.mark(0xCE26);self.a(3);m[0xA4]=r.a
        self.mark(0xCE2B);self.a(m[0x6FEA]);self.a(r.a&8)
        if r.a:self.mark(0xCE32);self.a(4);m[0xA4]=r.a
        self.mark(0xCE37);self.y(33);yield from self.call(0xCE39,0xF25F)
        self.mark(0xCE3C);self.a(m[0]);self.y(r.a);ident=r.y
        self.a(r.x);self.a(r.a&1)
        if r.a:
            self.mark(0xCE45);self.a(64);m[3]=r.a;self.a(self.data.chr_page_by_byte_id[r.y]);m[0xB9]=r.a
        else:
            self.mark(0xCE53);self.a(0);m[3]=r.a;self.a(self.data.chr_page_by_byte_id[r.y]);m[0xB8]=r.a
        self.mark(0xCE5E);self.a(0);m[5]=r.a
        self.a(m[0xA4]);self.a(r.a&7);self.flag(1,False);self.add(m[0x99A0+r.y]);self.shift_a('asl')
        self.push(r.a);self.y(r.a)
        self.a(m[0x9AA0+r.y]);m[0]=r.a;self.a(m[0x9AA1+r.y]);m[1]=r.a
        self.a(m[0x4BC])
        if not r.a:self.a(16)
        m[0xC]=r.a;self.a(0);m[2]=r.a;self.a(160);m[4]=r.a
        self.layers.append(dict(kind='body',officer_byte_id=ident,valid_officer_id=ident<237,pointer=m[0]|m[1]<<8))
        self.mark(0xCE8F);yield from self.call(0xCE8F,0xF1B7)
        self.mark(0xCE92);self.a(0);m[0x4BC]=r.a;self.a(self.pop());self.y(r.a)
        self.a(m[0xA4])
        talking=False
        if not r.a&128:
            self.mark(0xCE9E);self.a(m[0x7E]);self.a(r.a&1)
            if r.a:
                self.mark(0xCEA5);self.a(m[0x304]);self.cmp(r.a,255)
                if r.a!=255:
                    self.mark(0xCEAC);self.a(m[0x303])
                    if not r.a:
                        self.mark(0xCEB1);self.a(m[0x5E]);self.a(r.a&8);talking=bool(r.a)
        self.mark(0xCEC7 if talking else 0xCEB8)
        table=0x9D64 if talking else 0x9BAC
        self.a(m[table+r.y]);m[0]=r.a;self.a(m[table+1+r.y]);m[1]=r.a
        self.layers.append(dict(kind='talking_mouth'if talking else'ordinary_mouth',pointer=m[0]|m[1]<<8))
        self.mark(0xCED3 if talking else 0xCEC4)
        yield from self.append_screen_sprites()  # actual tailJMP F1B7; one caller RTS
    def append_screen_sprites(self):
        """F1B7..F205: caller parameter variant, not the F1AD zero prelude.

        m03 offsets tile IDs; m04 clips absolute Y; m02 XORs attributes.
        The m05 byte is written by CE1F but not consumed by this helper.
        All offsets, Y/X and OAM addresses keep the original unsigned wrap.
        """
        m=self.memory;r=self.registers;self.mark(0xF1B7);self.y(0);self.x(m[0x7C])
        scans=0;check_capacity=True
        while True:
            if check_capacity:
                self.mark(0xF1BC);self.cmp(r.x,255)
                if r.x==255:self.mark(0xF1C0);m[0x7C]=r.x;return
            self.mark(0xF1C4);pointer=m[0]|m[1]<<8;self.a(m[(pointer+r.y)&65535]);self.cmp(r.a,128)
            if r.a==128:self.mark(0xF1C0);m[0x7C]=r.x;return
            self.flag(1,False);self.add(m[0xA]);self.cmp(r.a,m[4])
            if r.a<m[4]:
                self.mark(0xF1D3)
                for _ in range(4):self.y(r.y+1)
                check_capacity=False
            else:
                self.mark(0xF1DA);m[0x200+r.x]=r.a;self.y(r.y+1)
                self.a(m[(pointer+r.y)&65535]);self.flag(1,False);self.add(m[3]);m[0x201+r.x]=r.a;self.y(r.y+1)
                self.a(m[(pointer+r.y)&65535]);self.a(r.a^m[2]);m[0x202+r.x]=r.a;self.y(r.y+1)
                self.a(m[(pointer+r.y)&65535]);self.flag(1,False);self.add(m[0xC]);m[0x203+r.x]=r.a;self.y(r.y+1)
                for _ in range(4):self.x(r.x+1)
                if r.x==0:self.mark(0xF201);self.x(255);self.mark(0xF1C0);m[0x7C]=r.x;return
                check_capacity=True
            scans+=1
            if scans==64:
                scans=0;pc=0xF1BC if check_capacity else 0xF1C4;self.mark(pc)
                yield ServiceWait('cyclic_sprite_descriptors',pc,reason='Original byte-index scan is still running; no terminator or OAM saturation has returned')
