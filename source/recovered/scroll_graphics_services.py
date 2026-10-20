"""Original row/column tile and attribute request construction, without PPU consumption.

Physical23 A00C→A387 and A00F→AB53. ROM is immutable table data only.
The algorithms retain scratch/cache writes, unit overlap priority, literal seam
arithmetic and request flags. No instruction interpreter, DMA, rendering,
readiness acknowledgement or original-CPU fallback is used by this module.
"""
from .battle_graphics_services import GraphicsData, GraphicsRegisters, BattleGraphicsServices, _Binary
from .officers import ROM_SHA256

# Page1 includes real scroll buffers; unused CPU-stack residue is outside scope.
DECLARED_RAM_ADDRESSES=tuple(range(0x120))+tuple(range(0x140,0x1B4))+tuple(range(0x200,0x800))

class ScrollGraphicsServices:
    """One cooperative scroll service. Optional registers describe body-end AXYP.

    Caller SP is preserved; the caller owns the real RTS stack pop. Returned
    flags assume binary arithmetic. Current mapped memory is used for map
    descriptors/chunks, including genuine E000 mapper writes.
    """
    def __init__(self,memory,data:GraphicsData):
        self.memory=memory;self.data=data;self.port_writes=[]
        self.units=BattleGraphicsServices(memory,data)
    def _word(self,a):return self.memory[a]|self.memory[a+1]<<8
    def _putword(self,a,v):self.memory[a]=v&255;self.memory[a+1]=(v>>8)&255
    def _inc(self,a,n=1):self.memory[a]=(self.memory[a]+n)&255
    def _start(self,registers):
        self.r=GraphicsRegisters()if registers is None else GraphicsRegisters(registers.a&255,registers.x&255,registers.y&255,registers.p&255)
        if self.r.p&8:raise ValueError('Binary CPU contract excludes decimal-mode fixtures')
        self.alu=_Binary(self.r.p);self.c=self.r.p&1
        self.port_writes=[];self.requests=[]
    def _add(self,a,b,c=0):v,self.c=self.alu.add(a,b,c);return v
    def _sub(self,a,b,c=1):v,self.c=self.alu.sub(a,b,c);return v
    def _finish(self,registers):
        self.r.p=self.alu.flags(self.r.a,self.c)
        if registers is not None:
            for k in ('a','x','y','p'):setattr(registers,k,getattr(self.r,k))
        return dict(status='returned',requests=self.requests,registers=vars(self.r),
                    contract_registers=vars(self.r),port_writes=list(self.port_writes),PPU_queue_consumed=False)
    def _equal_return(self,value,registers):
        self.r.a=value;result=self._finish(registers)
        # Final CMP equality, not LDA's NZ. Preserve its A and overflow.
        self.r.p=(self.r.p&~0x83)|3
        result['registers']=result['contract_registers']=vars(self.r)
        if registers is not None:registers.p=self.r.p
        return result
    def _descriptor(self,secondary=False):
        m=self.memory;a=0x1C if secondary else 0xC
        y=((m[a+3]*2)+m[a+1])&255
        return m[(self._word(0xA8)+y)&65535],y
    def _chunk(self,ident,attribute=False,secondary=False):
        if not 0<=ident<120:raise ValueError('Original chunk descriptor0..119 required')
        pointers=self.data.attribute_pointers if attribute else self.data.chunk_pointers
        self._putword(0x10 if secondary else 0,pointers[ident])
        if secondary:return
        if not attribute:self._putword(2,0xF477)
        selector=self.data.chunk_selectors[ident];self.memory[0xE1]=selector
        self.memory[0xE000]=selector;self.port_writes.append(dict(address=0xE000,value=selector))
    def _tile_lookup(self,column):
        m=self.memory;m[0x18]=((m[0xC]|(m[0xD]&1)<<8)>>4)&255
        m[0x19]=((m[0xE]|(m[0xF]&1)<<8)>>4)&255
        for a in range(0x680,0x6C0):m[a]=255
        for slot in range(19,-1,-1):
            if m[(0x600 if column else 0x614)+slot]==m[0x18 if column else 0x19]:
                m[0x680+m[(0x614 if column else 0x600)+slot]]=slot
    def _tile_quad(self,tile,column):
        m=self.memory;slot=m[0x680+m[0x19 if column else 0x18]]
        if slot!=255:
            self.units.unit_tiles(slot);self._putword(8,0x1B0)
        else:self._putword(8,(self._word(2)+tile*4)&65535)
        if column:offsets=(1,3)if m[0xC]&8 else(0,2);skip=bool(m[0xE]&8);base=0x142
        else:offsets=(2,3)if m[0xE]&8 else(0,1);skip=bool(m[0xC]&8);base=0x166
        for i,offset in enumerate(offsets):
            if i==0 and m[6]==0 and skip:continue
            m[base+self.r.x]=m[(self._word(8)+offset)&65535];self.r.x=(self.r.x+1)&255
    def _tile_header(self,address):
        m=self.memory;self._putword(0,address);m[address]=32;m[address+1]=m[0xC]>>3
        product=(m[0xE]&248)*4;m[0xF]=product>>8
        m[address+1]=self._add(product&255,m[address+1]);m[address]=self._add(m[address],m[0xF])
        self.r.x=32;self.r.y=0
    def _tile_column(self):
        m=self.memory
        if m[0x9C]&128:
            m[0xC]=self._add(m[0x8E],248);m[0xD]=self._add(m[0x8F],0,self.c)
        else:m[0xC]=m[0x8E];m[0xD]=m[0x8F]
        m[0xE]=m[0x90];m[0xF]=m[0x91];self.r.a=m[0x7E]
        if self.r.a&128:return
        ident,y=self._descriptor();m[0x1A]=y;self._chunk(ident)
        m[0x10]=m[(self._word(0xA8)+((y+2)&255))&65535]
        self._tile_lookup(True);self.r.x=0;m[6]=m[7]=0
        m[8]=m[0xC]>>4;m[5]=((m[0xE]&240)+m[8])&255
        for _ in range(16):
            tile=m[(self._word(0)+m[5])&65535];self._tile_quad(tile,True);self._inc(0x19)
            index=(m[5]+16)&255
            if index>=240:
                index&=15;self._chunk(m[0x10]);self._inc(7);self._inc(0x19)
            m[5]=index;self._inc(6)
        self._tile_header(0x140);m[0x7E]|=128;self.r.a=m[0x7E]
        self.requests.append(dict(kind='tile_column',address=0x140,request_bit=128))
    def _tile_row(self):
        m=self.memory;m[0xC]=m[0x8E];m[0xD]=m[0x8F];m[0xF]=m[0x91]
        if m[0x9C]&32:
            self._inc(0xF);value=self._add(m[0x90],240)
            if not self.c:value=self._sub(value,16);self._inc(0xF,-1)
            m[0xE]=value
        else:m[0xE]=m[0x90]
        self.r.a=(m[0x7E]<<1)&255;self.c=m[0x7E]>>7
        if self.r.a&128:return
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
        self.requests.append(dict(kind='tile_row',address=0x164,request_bit=64))
    def tile_scroll(self,registers=None):
        """23A00C/A387..A603: caches, busy gates, 16-column/17-row metatiles."""
        self._start(registers);m=self.memory;value=m[0x8E]
        if value>=254:value=self._add(value,2)
        value>>=3;self.c=int(value>=m[0x93]);self.r.a=value
        if value!=m[0x93]:m[0x93]=value;self._tile_column()
        value=m[0x90]>>3;self.c=int(value>=m[0x92]);self.r.a=value
        if value==m[0x92]:return self._equal_return(value,registers)
        m[0x92]=value;self._tile_row();return self._finish(registers)
    def _attribute_origin(self):
        m=self.memory
        for dest,low,high in ((0x18,0xC,0xD),(0x19,0xE,0xF),(0x16,0x1C,0x1D),(0x17,0xE,0xF)):
            m[dest]=(((m[low]|(m[high]&1)<<8)>>5)*2)&255
    def _attribute_lookup(self,column):
        m=self.memory;self._attribute_origin()
        for a in range(0x680,0x700 if column else 0x6C0):m[a]=255
        for slot in range(19,-1,-1):
            x,y=m[0x600+slot],m[0x614+slot]
            if column:
                for coord,base in ((m[0x18],0x680),((m[0x18]+1)&255,0x6A0),(m[0x16],0x6C0),((m[0x16]+1)&255,0x6E0)):
                    if x==coord:m[base+y]=slot
            else:
                if y==m[0x19]:m[0x680+x]=slot
                if y==(m[0x19]+1)&255:m[0x6A0+x]=slot
    def _attribute_overlay(self,target,index,left,right,row=False):
        m=self.memory
        checks=((left+index,252,2),(right+index,207 if row else 243,32 if row else 8),
                (left+index+1,243 if row else 207,8 if row else 32),(right+index+1,63,128))
        for address,mask,bits in checks:
            if not m[address]&128:m[target]=(m[target]&mask)|bits
    def _attribute_header(self,address):
        m=self.memory;self._putword(0,address);m[address]=35
        m[address+1]=self._add(m[0xC]>>5,192)
        m[address+1]=self._add((m[0xE]&224)>>2,m[address+1]);self.r.x=35;self.r.y=1
    def _merge_column(self):
        m=self.memory;reverse=bool(m[0x9C]&64);half=bool(m[0xC]&16);last=m[6]==8
        if reverse!=half:
            if last and m[0xE]&16:m[0x18A]=(m[0x18A]&240)|(m[2]&15)
            else:m[0x18A+self.r.x]=m[2]
        elif reverse:
            if last:m[2]&=12;m[0x18A]=(m[0x18A]&240)|m[2]|(m[3]&3)
            else:m[2]&=204;m[0x18A+self.r.x]=m[2]|(m[3]&51)
        else:
            if last and m[0xE]&16:m[2]&=3;m[0x18A]=(m[0x18A]&240)|m[2]|(m[3]&12)
            else:m[2]&=51;m[0x18A+self.r.x]=m[2]|(m[3]&204)
        self.r.x=(self.r.x+1)&255
    def _attribute_column(self):
        m=self.memory
        for i in range(4):m[0xC+i]=m[0x8E+i];m[0x1C+i]=m[0x8E+i]
        self._inc(0x1D if m[0x9C]&64 else 0xD)
        ident,y=self._descriptor();m[0xA]=y;self._chunk(ident,True)
        m[0xA]=m[(self._word(0xA8)+((y+2)&255))&65535]
        ident,y=self._descriptor(True);m[0x1A]=y;self._chunk(ident,True,True)
        m[0x1A]=m[(self._word(0xA8)+((y+2)&255))&65535]
        m[8]=m[0xC]>>5;m[5]=(m[8]+((m[0xE]&224)>>2))&255
        self._attribute_lookup(True);self.r.x=0;m[6]=0;m[7]=8+int(bool(m[0xE]&16))
        for _ in range(m[7]):
            m[2]=m[(self._word(0)+m[5])&65535];m[3]=m[(self._word(0x10)+m[5])&65535]
            self._attribute_overlay(2,m[0x19],0x680,0x6A0)
            if (m[0xC]+8)&16:
                self._attribute_overlay(3,m[0x19],0x6C0,0x6E0);self._inc(0x17,-1)
            self._inc(0x17,2);self._inc(0x19,2);self._merge_column()
            index=(m[5]+8)&255
            if index>=64:
                index&=7;self._chunk(m[0xA],True);self._chunk(m[0x1A],True,True)
            m[5]=index;self._inc(6)
        self._attribute_header(0x188);m[0x7E]|=32;self.r.a=m[0x7E]
        self.requests.append(dict(kind='attribute_column',address=0x188,request_bit=32))
    def _attribute_row(self):
        m=self.memory;m[0xC]=self._add(m[0x8E],4);m[0xD]=self._add(m[0x8F],0,self.c)
        m[0xE]=m[0x90];m[0xF]=m[0x91]
        if not m[0x9C]&16:
            value=self._add(m[0x90],160);m[0xE]=value
            if self.c or value>=240:m[0xE]=self._add(value,16);self._inc(0xF)
        ident,y=self._descriptor();m[0xA]=y;self._chunk(ident,True)
        m[0xA]=m[(self._word(0xA8)+((y+1)&255))&65535]
        m[6]=0;m[8]=m[0xC]>>5;m[5]=(m[8]+((m[0xE]&224)>>2))&255
        self._attribute_lookup(False);self.r.x=0;m[7]=8+int(bool(m[0xC]&16))
        for _ in range(m[7]):
            m[2]=m[(self._word(0)+m[5])&65535];self._attribute_overlay(2,m[0x18],0x680,0x6A0,True)
            self._inc(0x17,-1);self._inc(0x16,2);self._inc(0x18,2)
            if m[6]==8 and m[0xC]&16:m[0x19E]=(m[0x19E]&204)|(m[2]&51)
            else:m[0x19E+self.r.x]=m[2]
            self.r.x=(self.r.x+1)&255;old=m[5];self._inc(5)
            if old&7==7:self._chunk(m[0xA],True);m[5]=old&248
            self._inc(6)
        self._attribute_header(0x19C);m[0x7E]|=16;self.r.a=m[0x7E]
        self.requests.append(dict(kind='attribute_row',address=0x19C,request_bit=16))
    def attribute_scroll(self,registers=None):
        """23A00F/AB53..B0FF: one prioritized attribute row or column request."""
        self._start(registers);m=self.memory;value=self._sub(m[0x8E],6)>>3;self.r.a=value;self.c=int(value>=m[0x95])
        if value!=m[0x95]:m[0x95]=value;self._attribute_column();return self._finish(registers)
        value=m[0x90]>>4;self.r.a=value;self.c=int(value>=m[0x94])
        if value==m[0x94]:return self._equal_return(value,registers)
        m[0x94]=value;self._attribute_row();return self._finish(registers)
