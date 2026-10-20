"""Readable map-refresh, cursor and highlight request construction.

These algorithms build the original nametable command buffer and OAM RAM.
They do not execute ROM instructions, interpret IR, render pixels, issue DMA,
consume the PPU command queue, or acknowledge software readiness. Immutable
ROM data tables are pinned; actual PRG register writes are sent to shared IO.
"""
from dataclasses import dataclass
import hashlib
from .officers import ROM_SHA256

C,Z,V,N=1,2,64,128
# CPUstack writes are excluded, except actual palette0100..1F/unit01B0..B3 data.
DECLARED_RAM_ADDRESSES=tuple(range(0x120))+tuple(range(0x1B0,0x1B4))+tuple(range(0x200,0x800))

@dataclass(frozen=True)
class GraphicsData:
    chunk_pointers:tuple
    attribute_pointers:tuple
    chunk_selectors:bytes
    unit_tile_rows:tuple
    background_metatiles:bytes
    cursor_template:bytes
    highlight_template:bytes
    animation_kinds:bytes
    animation_sprite_tables:tuple
    animation_palette_rows:bytes
    animation_banners:bytes
    portrait_positions:bytes
    normal_palette:bytes
    audio:object
    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Graphics tables require the pinned original ROM')
        def words(o):return tuple(int.from_bytes(rom[o+2*i:o+2*i+2],'little')for i in range(120))
        from .audio_services import AudioData
        return cls(words(0x2E652),words(0x2E742),bytes(rom[0x2E832:0x2E8AA]),
                   tuple(bytes(rom[0x2EAF4+11*i:0x2EAF4+11*(i+1)])for i in range(6)),
                   bytes(rom[0x3F487:0x3F887]),bytes(rom[0x1B691:0x1B69A]),bytes(rom[0x1BCA4:0x1BCA9]),
                   bytes(rom[0x35559:0x35569]),tuple(int.from_bytes(rom[0x3586F+2*i:0x35871+2*i],'little')for i in range(11)),
                   bytes(rom[0x356A2:0x356FA]),bytes(rom[0x3580F:0x3586F]),bytes(rom[0x3539B:0x353B3]),bytes(rom[0x3DC1B:0x3DC3B]),AudioData.from_rom(rom))

@dataclass
class GraphicsRegisters:
    a:int=0
    x:int=0
    y:int=0
    p:int=32

class _Binary:
    """Binary byte arithmetic retaining overflow for returned CPU flags."""
    def __init__(self,p):self.p=p&255
    def add(self,left,right,carry=0):
        total=left+right+carry
        self.p=(self.p&~V)|(V if (~(left^right)&(left^total)&128)else 0)
        return total&255,int(total>255)
    def sub(self,left,right,carry=1):
        total=left-right-(1-carry)
        self.p=(self.p&~V)|(V if ((left^right)&(left^total)&128)else 0)
        return total&255,int(total>=0)
    def flags(self,value,carry=None):
        p=(self.p&~(N|Z))|(N if value&128 else 0)|(Z if value==0 else 0)
        if carry is not None:p=(p&~C)|(C if carry else 0)
        return p

class BattleGraphicsServices:
    """Complete D6CC/D657/DC63/DC70 returns, without queue consumption.

    All nonstackRAM, palette0100..1F/unit01B0..B3, SRAM and ports are preserved.
    Optional returned A/X/Y/P permit a separate caller to pop its real RTS.
    This API does not synthesize that stack pop or a CPU instruction count.
    """
    def __init__(self,memory,data:GraphicsData):self.memory=memory;self.data=data;self.port_writes=[]
    def _set(self,address,value):self.memory[address]=value&255
    def _word(self,address):return self.memory[address]|self.memory[address+1]<<8
    def _putword(self,address,value):self._set(address,value);self._set(address+1,value>>8)
    def _port(self,address,value):
        value&=255;self.port_writes.append(dict(address=address,value=value))
        if hasattr(self.memory,'io_write'):self.memory.io_write(address,value)
        else:self.memory[address]=value
    def _registers(self,registers):
        r=GraphicsRegisters()if registers is None else GraphicsRegisters(registers.a&255,registers.x&255,registers.y&255,registers.p&255)
        if r.p&8:raise ValueError('Binary arithmetic CPU contract excludes decimal-mode py65 fixtures')
        return r
    def _program_pair(self,selector):
        m=self.memory;m[0xE2]=selector;m[0xE3]=(selector+1)&255
        self._port(0xF000,m[0xE3]);self._port(0xE800,selector|192)
    def _far_data(self,entry,inline_pc,argument):
        """EE07/37 wrapper for the three concrete recovered table helpers.

        This models their bank requests and real scratch, not an instruction
        executor. Each helper is an independent table/record algorithm below.
        """
        m=self.memory;old=m[0xE2];m[0x58]=old;m[0x5D]=55
        self._putword(0x59,inline_pc+1);self._putword(0x5B,entry);self._program_pair(55)
        if entry in(0xA012,0xA015):
            if not 0<=argument<120:raise ValueError('Original map chunk0..119 required')
            pointers=self.data.chunk_pointers if entry==0xA012 else self.data.attribute_pointers
            self._putword(0,pointers[argument])
            if entry==0xA012:self._putword(2,0xF477)
            selector=self.data.chunk_selectors[argument];m[0xE1]=selector;self._port(0xE000,selector)
        elif entry==0xA018:self.unit_tiles(argument)
        else:raise ValueError('Three concrete graphics helpers only')
        self._program_pair(old)
    @staticmethod
    def _camera_x(value):return 16 if value+4>255 else(value+4)>>4
    def unit_tiles(self,slot=None):
        """23A983..AAE3: four unitBG tiles, controller/strength/affinity."""
        m=self.memory;slot=m[0]if slot is None else slot
        if not 0<=slot<20:raise ValueError('Original unit slot0..19 required')
        strength=m[0x63C+slot]
        if strength>10:raise ValueError('Original displayed troop-hundreds cache0..10 required')
        rulers=m[0x507];ruler=(rulers>>4)if m[0x628+slot]&128 else rulers&15
        if ruler>=7:raise ValueError('Original ruler0..6 required')
        controller=m[0x6F07+8*ruler+3];kind=0 if controller==0 else 1 if controller==1 else 2
        top_left=self.data.unit_tile_rows[2*kind][strength];top_right=self.data.unit_tile_rows[2*kind+1][strength]
        if slot in(0,10):
            top_left=(0xBB,0xB1,0xB6)[kind]
            if strength==10:top_left,top_right=((0xBA,0xAB),(0xB0,0x8B),(0xB5,0x9B))[kind]
        affinity=m[0x628+slot]&3
        bottom=((0xBD,0xBE)if affinity==0 else(0xAC,0xAD)if affinity==1 else(0xAE,0xAF))if kind==0 else \
               ((0xB3,0xB4)if affinity==0 else(0x8E,0x8F)if affinity==2 else(0x8C,0x8D))if kind==1 else \
               ((0xB8,0xB9)if affinity==0 else(0x9E,0x9F)if affinity==2 else(0x9C,0x9D))
        tiles=(top_left,top_right,*bottom)
        for i,value in enumerate(tiles):m[0x1B0+i]=value
        return dict(status='returned',slot=slot,controller_raw=controller,tiles=list(tiles))
    def _overlay_quadrant(self,slot,x,y,mask,bits):
        m=self.memory
        if m[0x600+slot]==x and m[0x614+slot]==y:m[0]=(m[0]&mask)|bits
    def overlay_unit_attributes(self):
        """D88E..DA16: 2x2 palette overlay, including horizontal seam order."""
        m=self.memory;m[2]=m[0x10]&30;m[3]=m[0x11]&30;origin=self._camera_x(m[0x8E])
        for slot in range(19,-1,-1):
            if m[0x12]==0 and slot==m[0x509]:continue
            seam=None
            if origin&1:
                m[4]=origin&31;delta=(m[0x10]-m[4])&255
                if delta==0:seam='left'
                elif delta==15:seam='right'
            if seam=='left':
                m[2]=(m[0x10]+15)&255;self._overlay_quadrant(slot,m[2],m[3],252,2)
                m[3]=(m[3]+1)&255;self._overlay_quadrant(slot,m[2],m[3],207,32)
                m[2]=(m[2]-15)&255;self._overlay_quadrant(slot,m[2],m[3],63,128)
                m[3]=(m[3]-1)&255;self._overlay_quadrant(slot,m[2],m[3],243,8)
            elif seam=='right':
                m[2]=m[0x10];self._overlay_quadrant(slot,m[2],m[3],252,2)
                m[3]=(m[3]+1)&255;self._overlay_quadrant(slot,m[2],m[3],207,32)
                m[2]=(m[2]-15)&255;self._overlay_quadrant(slot,m[2],m[3],63,128)
                m[3]=(m[3]-1)&255;self._overlay_quadrant(slot,m[2],m[3],243,8);m[2]=(m[2]+15)&255
            else:
                self._overlay_quadrant(slot,m[2],m[3],252,2);m[2]=(m[2]+1)&255
                self._overlay_quadrant(slot,m[2],m[3],243,8);m[3]=(m[3]+1)&255
                self._overlay_quadrant(slot,m[2],m[3],63,128);m[2]=(m[2]-1)&255
                self._overlay_quadrant(slot,m[2],m[3],207,32);m[3]=(m[3]-1)&255
        return m[0]
    def map_refresh(self,registers=None):
        """Complete13D6CC, queue two2-tile writes and oneattribute byte."""
        r=self._registers(registers);alu=_Binary(r.p);m=self.memory;slot=m[0x509]
        if slot>=20:raise ValueError('Original unit slot0..19 required')
        m[0x10]=m[0x600+slot];m[0x11]=m[0x614+slot];m[0]=m[0x90]>>4
        delta,carry=alu.sub(m[0x11],m[0]);r.y=slot
        if delta>=15:
            r.a=delta;r.p=alu.flags((delta-15)&255,True)
            return dict(status='returned',queued=False,reason='outside_vertical_view',registers=vars(r))
        origin=self._camera_x(m[0x8E]);alu.add(m[0x8E],4);m[0]=origin
        delta,carry=alu.sub(m[0x10],origin)
        if delta>=16:
            r.a=delta;r.p=alu.flags((delta-16)&255,True)
            return dict(status='returned',queued=False,reason='outside_horizontal_view',registers=vars(r))
        pointer=self._word(0xA8);q=int(m[0x10]>=16)|2*int(m[0x11]>=16)
        primary=m[(pointer+q)&65535];neighbor=m[(pointer+(q^1))&65535];m[0]=primary
        self._far_data(0xA012,0xD731,primary)
        m[8]=m[0x10]&15;row=(m[0x11]<<4)&255;tile=m[(self._word(0)+ (row|m[8]))&65535]
        m[4]=tile>>6;tile_pointer=(0xF477+tile*4)&65535;self._putword(2,tile_pointer)
        for source_offset,dest in enumerate((0x383,0x384,0x388,0x389)):m[dest]=self.data.background_metatiles[tile*4+source_offset]
        m[8]=(m[8]<<1)&255;m[0xB]=row>>6;address=0x2000+row*4+m[8]
        self._putword(0x381,((address&255)<<8)|(address>>8))
        self._putword(0x386,(((address+32)&255)<<8)|((address+32)>>8));m[0x380]=m[0x385]=2
        if m[0x12]:
            m[0]=slot;self._far_data(0xA018,0xD7B8,slot);self._putword(0,0x1B0)
            for i,dest in enumerate((0x383,0x384,0x388,0x389)):m[dest]=m[0x1B0+i]
        m[0]=primary;self._far_data(0xA015,0xD7E3,primary)
        m[8]=(m[0x10]&14)>>1;attribute_index=((m[0x11]&14)<<2)|m[8];m[0xA]=m[(self._word(0)+attribute_index)&65535];m[0]=neighbor
        if origin&1:
            m[4]=origin&31;delta=(m[0x10]-m[4])&255
            if delta==0:
                m[0xA]&=204;self._far_data(0xA015,0xD82A,neighbor);m[0xA]|=m[(self._word(0)+attribute_index)&65535]&51
            elif delta==15:
                m[0xA]&=51;self._far_data(0xA015,0xD84A,neighbor);m[0xA]|=m[(self._word(0)+attribute_index)&65535]&204
        m[0]=m[0xA];self.overlay_unit_attributes();m[0x38D]=m[0]
        m[0]=(m[0x10]&14)>>1;m[0x38C]=(((m[0x11]&14)<<2)|m[0])|192
        m[0x38B]=35;m[0x38A]=1;m[0x38E]=255;m[0x7E]|=4
        alu.add(m[0x8E],4);r.a=m[0x7E];r.x=origin;r.y=255;r.p=alu.flags(r.a,False)
        return dict(status='returned',queued=True,request_bit=4,command_address=0x380,command_bytes=list(m[a]for a in range(0x380,0x38F)),registers=vars(r),PPU_queue_consumed=False)
    def _template_byte(self,pointer,index,template):
        if template is not None:
            if index>=len(template):raise ValueError('Terminated sprite data required')
            return template[index]
        return self.memory[(pointer+index)&65535]
    def world_sprites(self,registers=None,*,template=None):
        """Complete fixedF092: world-relative sprite records, flags/flips/clips."""
        r=self._registers(registers);alu=_Binary(r.p);m=self.memory;m[3]=0;m[4]=240;flags=m[2];pointer=self._word(0)
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
                m[0x7C]=x;r.x=x;r.y=index;r.p=alu.flags(0,True)
                return dict(status='returned',sprites_allocated=allocated,buffer_full=True,registers=vars(r),OAM_DMA_requested=False)
            m[0xF]=m[0xB];dy=self._template_byte(pointer,index,template)
            if dy==128:
                m[0x7C]=x;r.a=128;r.x=x;r.y=index;r.p=alu.flags(0,True)
                return dict(status='returned',sprites_allocated=allocated,buffer_full=False,registers=vars(r),OAM_DMA_requested=False)
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
            tile=self._template_byte(pointer,(index+1)&255,template);m[0x201+x],_=alu.add(tile,m[3])
            m[0x202+x]=self._template_byte(pointer,(index+2)&255,template)^flags
            dx=self._template_byte(pointer,(index+3)&255,template)
            if flags&64:dx,_=alu.sub(8,dx)
            if dx&128:
                m[0xE]=dx^255;value,carry=alu.sub(m[0xC],m[0xE]);m[0x203+x]=value;high,_=alu.sub(m[0xD],0,carry)
            else:
                value,carry=alu.add(dx,m[0xC]);m[0x203+x]=value;high,_=alu.add(m[0xD],0,carry)
            r.a=high;index=(index+4)&255
            if high==0:
                x=(x+4)&255;allocated+=1
                if x==0:x=255
        raise ValueError('Original terminated sprite descriptor required; source guard rejects unbounded records')
    def cursor(self,registers=None):
        """Complete13D657 cursor prelude and world-relative F092 renderer."""
        m=self.memory
        for source,dest in((0x6F41,0xA),(0x6F42,0xB),(0x6F3F,0xC),(0x6F40,0xD)):m[dest]=m[source]
        self._putword(0,0xD681);m[2]=0
        return self.world_sprites(registers,template=self.data.cursor_template)
    def screen_sprites(self,registers=None,*,template=None):
        """Complete fixedF1AD: absolute-screen OAM records, byte wraps."""
        r=self._registers(registers);alu=_Binary(r.p);m=self.memory;m[3]=m[4]=0;pointer=self._word(0);x=m[0x7C];index=0;allocated=0;r.a=0
        for _ in range(65):
            if x==255:
                m[0x7C]=x;r.x=x;r.y=index;r.p=alu.flags(0,True)
                return dict(status='returned',sprites_allocated=allocated,buffer_full=True,registers=vars(r),OAM_DMA_requested=False)
            dy=self._template_byte(pointer,index,template)
            if dy==128:
                m[0x7C]=x;r.a=128;r.x=x;r.y=index;r.p=alu.flags(0,True)
                return dict(status='returned',sprites_allocated=allocated,buffer_full=False,registers=vars(r),OAM_DMA_requested=False)
            row,_=alu.add(dy,m[0xA]);r.a=row
            if row<m[4]:index=(index+4)&255;continue
            m[0x200+x]=row;tile=self._template_byte(pointer,(index+1)&255,template);m[0x201+x],_=alu.add(tile,m[3])
            m[0x202+x]=self._template_byte(pointer,(index+2)&255,template)^m[2]
            value,_=alu.add(self._template_byte(pointer,(index+3)&255,template),m[0xC]);m[0x203+x]=value;r.a=value
            index=(index+4)&255;x=(x+4)&255;allocated+=1
            if x==0:
                x=255;m[0x7C]=x;r.x=x;r.y=index;r.p=alu.flags(255,False)
                return dict(status='returned',sprites_allocated=allocated,buffer_full=True,registers=vars(r),OAM_DMA_requested=False)
        raise ValueError('Original terminated sprite descriptor required; source guard rejects unbounded records')
    def highlight(self,registers=None,*,alternate=False):
        """Complete13DC63/DC70; blink-bit skip preserves existing OAM."""
        r=self._registers(registers);m=self.memory;m[0xA]=224 if alternate else 216;m[0xC]=160
        if m[0x5E]&16:
            r.a=16;r.p=(r.p&~(N|Z))
            return dict(status='returned',blink_skipped=True,registers=vars(r),OAM_DMA_requested=False)
        self._putword(0,0xDC94);m[2]=0
        return dict(self.screen_sprites(r,template=self.data.highlight_template),blink_skipped=False)

    def _data_bank(self,selector):
        self.memory[0xE1]=selector;self._port(0xE000,selector)
    def _dispatch_scratch(self,return_address,target,original_y):
        """Actual EADE caller scratch for known semantic dispatch tables."""
        self.memory[0]=original_y;self._putword(1,return_address);self._putword(3,target)
    def _packed_decimal_work(self):
        """E9BA decimal extraction and original residual arithmetic scratch."""
        m=self.memory;value=(m[1]|m[2]<<8|m[3]<<16)%1000000
        remaining=value%10000;m[5]=((remaining-10000)&65535)>>8
        m[1]=value%10;m[2]=m[3]=0;m[4]=(m[1]-10)&255
        m[7]=((value//10%10)<<4)|(value%10);m[8]=((value//1000%10)<<4)|(value//100%10)
        m[9]=((value//100000%10)<<4)|(value//10000%10)
    def _number_pair(self,packed,x,leading_mode):
        m=self.memory;high=packed>>4
        if high==0 and leading_mode!=255:code=1
        else:code=(high+246)&255;leading_mode=255
        m[0x3BA+x]=code
        if leading_mode!=1:leading_mode=255
        low=packed&15
        if low==0 and leading_mode!=255:code=1
        else:code=(low+246)&255;leading_mode=255
        m[0x3BB+x]=code
        return leading_mode
    def _animation_stat_digits(self):
        """D75C real setup display, including100 specialglyph andrawtroops."""
        m=self.memory;field=m[0x4D1]
        if field==1:
            m[2]=m[0x42C];m[1]=m[0x42D];m[3]=0;self._packed_decimal_work()
            m[0]=m[8];mode=self._number_pair(m[0],0,1)
            m[0]=m[7];self._number_pair(m[0],2,255 if mode==255 else 0)
        else:
            value=m[0x42C+field]
            if value==100:m[0x3BA]=m[0x3BB]=235;return
            m[1]=value;m[2]=m[3]=0;self._packed_decimal_work();m[0]=m[7];self._number_pair(m[0],0,0)
    def _animation_portrait(self):
        """26D2EA, actual13B portrait record and fixed OAM arrangement."""
        m=self.memory;slot=m[0x509]
        if slot>=20:raise ValueError('Original animation targetslot0..19 required')
        ident=m[0x664+slot]
        if ident>=237:raise ValueError('Original initial portrait officer0..236 required')
        self._data_bank(49);self._putword(0,0x8DB4+13*ident);m[2]=(4*ident)>>8;m[4]=0
        m[0xC1]=m[self._word(0)];x=m[0x7C]
        for index in range(1,13):
            tile=m[(self._word(0)+index)&65535]
            if tile==255:break
            m[0x201+x]=(tile+192)&255;m[0x202+x]=0
            m[0x203+x]=self.data.portrait_positions[m[4]]
            m[0x200+x]=(self.data.portrait_positions[m[4]+1]+8)&255;m[4]=(m[4]+2)&255;x=(x+4)&255
        m[0x7C]=x
    def _animation_sprite(self,frame,x=16):
        """D2C9/D2CB with F1AD, actual frame table and XORattribute3."""
        m=self.memory;m[0xC]=x&255;offset=(((frame-1)&255)<<1)&255;pointer=self._word(0x10)
        self._putword(0,m[(pointer+offset)&65535]|m[(pointer+((offset+1)&255))&65535]<<8)
        m[0xA]=64;m[2]=3;self.screen_sprites()
    def _audio_reset_request(self,sequence,entry):
        from .audio_services import AudioServices
        audio=AudioServices(self.memory,self.data.audio);audio.reset();audio.request(sequence,entry=entry)
    def _normal_palette(self):
        """Actual far3DA015->30DBB1, used byanimationfinish withmode1."""
        m=self.memory;old=m[0xE2];m[0x58]=old;m[0x5D]=61;self._putword(0x59,0xD3EB);self._putword(0x5B,0xA015);self._program_pair(61)
        self._putword(0xA,0xDC0B)
        for i,value in enumerate(self.data.normal_palette):m[0x100+i]=value
        self._program_pair(old)
    def _animation_finish(self):
        """D3AB..D41E: real end requests, palette/audio, clear04C8."""
        m=self.memory;m[0x380]=32;m[0x381]=39;m[0x382]=216
        for i in range(32):m[0x383+i]=170
        m[0x3A3]=255;m[0x7E]|=4;m[0x4C8]=0;m[0x518]=1;m[0x7D]=1;m[0]=1;self._normal_palette()
        for address in(0xC2,0xCA,0xD2,0xC5,0xCD,0xD5):m[address]=136
        for address in(0xC3,0xCB,0xD3):m[address]=137
        for address in(0xC4,0xCC,0xD4):m[address]=138
        self._audio_reset_request(29,0xE673)
    def _animation_setup(self,stage,original_y):
        m=self.memory;targets=(0xD42F,0xD476,0xD559,0xD5F2,0xD6EA)
        if stage>=5:raise ValueError('Five actual animation setup substates0..4 required')
        self._dispatch_scratch(0xD424,targets[stage],original_y)
        if stage==0:
            m[0x4D4]=80;m[0x4D5]=140;m[0x4D2]=192;m[0x4D3]=37
            slot=m[0x509]
            if slot>=20 or m[0x664+slot]>=237:raise ValueError('Initial animation selected officer0..236 required')
            self._putword(0,0x63C0+12*m[0x664+slot]);a=self._word(0)
            for offset,dest in((0,0x430),(2,0x42F),(3,0x42E),(8,0x42D),(9,0x42C)):m[dest]=m[a+offset]
            m[0x4D1]=6;m[0x4CA]=(m[0x4CA]+1)&255
        elif stage==1:
            self._data_bank(33);self._putword(0,self._word(0x4D4));address=self._word(0x4D2)
            m[0x380]=64;m[0x381]=address>>8;m[0x382]=address&255
            for i in range(64):m[0x383+i]=m[(self._word(0)+i)&65535]
            m[0x3C3]=255;self._putword(0x4D4,self._word(0)+64);self._putword(0x4D2,address+64)
            if 0<m[0x4D1]<5:self._animation_stat_digits()
            m[0x4D1]=(m[0x4D1]-1)&255
            if m[0x4D1]&128:
                m[0x4D2]=2;m[0x4D3]=38;ident=m[0x4C9]
                if ident>=16:raise ValueError('Original16 animation tacticIDs required')
                index=self.data.animation_kinds[ident];m[0x4C9]=index>>1
                pointer=m[0x8E10+index]|m[0x8E11+index]<<8;pointer=(pointer+0x6000)&65535;self._putword(0,pointer)
                for i,address in enumerate((0xC3,0xC4,0xCB,0xCC,0xD3,0xD4)):m[address]=m[(pointer+i)&65535]
                self._putword(0x4D4,pointer+6);m[0x4D1]=4;m[0x4CA]=(m[0x4CA]+1)&255
            m[0x7E]|=4
        elif stage==2:
            self._data_bank(33);self._putword(2,self._word(0x4D2));self._putword(0,self._word(0x4D4));x=0
            for _ in range(2):
                address=self._word(2);m[0x380+x]=14;m[0x381+x]=address>>8;m[0x382+x]=address&255
                for i in range(14):m[0x383+x+i]=m[(self._word(0)+i)&65535]
                x+=17;self._putword(0,self._word(0)+14);self._putword(2,address+32)
            m[0x380+x]=255;self._putword(0x4D2,self._word(2));self._putword(0x4D4,self._word(0));m[0x4D1]=(m[0x4D1]-1)&255
            if m[0x4D1]&128:m[0x4CA]=(m[0x4CA]+1)&255
            m[0x7E]|=4
        elif stage==3:
            kind=m[0x4C9]
            if kind>=11:raise ValueError('Actual11 animation classes0..10 required')
            m[2]=(kind*8+8)&255
            for i in range(8):m[0x10C+i if i<4 else 0x118+i]=self.data.animation_palette_rows[kind*8+i]
            page=1 if kind==1 else 2 if kind==4 else 0;self._putword(0,0xD7FF+32*page)
            m[0x380]=32;m[0x381]=39;m[0x382]=216
            for i,value in enumerate(self.data.animation_banners[32*page:32*(page+1)]):m[0x383+i]=value
            m[0x3A3]=255;m[0x7E]|=4;m[0x111]=15;m[0x112]=27;m[0x113]=40
            for address in(0xC2,0xCA,0xD2):m[address]=2
            for address in(0xC5,0xCD,0xD5):m[address]=6
            m[0x4CA]=(m[0x4CA]+1)&255
        else:
            for i in range(3,70):m[0x380+i]=1
            m[0x3C6]=255;m[0x380]=m[0x3A3]=32;m[0x381]=37;m[0x382]=160;m[0x3A4]=39;m[0x3A5]=128
            m[0x7E]|=4;m[0x4C8]=129
            for address in(0x4CA,0x4CD,0x4CE,0x4D0,0x518):m[address]=0
            sequences=(149,136,136,141,141,141,145,136,149,136,149);sequence=sequences[m[0x4C9]]
            entry=0xE683 if sequence==136 else 0xE693 if sequence==149 else 0xE68B
            self._audio_reset_request(sequence,entry)
    def _animation_frame(self):
        m=self.memory;kind=m[0x4C9]
        if kind>=11:raise ValueError('Actual11 animation classes0..10 required')
        m[0x4D0]=(m[0x4D0]+1)&255;self._animation_portrait();self._putword(0x10,self.data.animation_sprite_tables[kind]);m[0x4CD]=(m[0x4CD]+1)&255;m[0x4CE]=(m[0x4CE]+1)&255
        entries=(0xD04A,0xD07C,0xD0B8,0xD0F5,0xD132,0xD18C,0xD1C3,0xD206,0xD232,0xD263,0xD294)
        self._dispatch_scratch(0xD033,entries[kind],kind*2+1);phase=m[0x4CA];timer=m[0x4CD]
        if kind==1:
            if phase==m[0x4CB]:m[0x4CA]=(timer>>3)&3
            else:
                m[0x4CB]=phase
                palette=bytes((22,38,39,38,39,38,39,38,22,38,22,38))
                for i in range(3):m[0x10D+i]=palette[phase*3+i]
        elif phase==0:
            if kind in(0,2,3,4,5,6):
                first={0:251,2:252,3:240,4:236,5:229,6:239}[kind]
                for address in(0xBE,0xC6,0xCE):m[address]=first
            if kind in(2,3,4,5,7,8,9,10):
                second={2:254,3:242,4:237,5:229,7:187,8:185,9:216,10:227}[kind]
                for address in(0xBF,0xC7,0xCF):m[address]=second
            m[0x4CA]=16 if kind==10 else 1
            if kind in(4,6):m[0x4CB]=3
            if kind==4:m[0x101]=39;m[0x102]=25;m[0x103]=10
            if kind==10:m[0x4CB]=16
            return
        elif kind==10:
            self._animation_sprite(1,m[0x4CB]);m[0x4CB]=(((timer>>3)&1)+m[0x4CA])&255
        else:
            self._animation_sprite(phase)
            if kind in(4,6):self._animation_sprite(m[0x4CB])
            if kind in(0,2,3,8,9):
                value=(timer>>(3 if kind in(8,9)else 4))&3;m[0x4CA]=(1 if value==3 else value)+1
            elif kind in(5,7):m[0x4CA]=((timer>>4)&1)+1
            elif kind==4:
                if timer==64:m[0x4CA]=2
                elif timer==96:m[0x4CB]=4
            elif kind==6:
                if timer==96:m[0x4CA]=2
                m[0x4CB]=((timer>>4)&1)+3
        if m[0x4D0]==176:self._animation_finish()
    def animation_tick(self,registers=None):
        """Complete25A00F->26CFD6, actual16 IDs/11classes/5setupstates.

        The existing0300/0304 jobs gate advancement. It may legitimately clear
        04C8 only after the original176 counter path; no hostready is inserted.
        Builds requests/OAM/palette/audio data, without rendering or time.
        Unlike the three basic services, finalCPUregisters are not contracted.
        Caller invokes once at the actual NMI service point, not on fakeframes.
        """
        r=self._registers(registers);m=self.memory;request=m[0x4C8]
        if request==0:return dict(status='returned',animation_active=False,register_contract=False)
        if m[0x300]!=255 or m[0x304]!=255:return dict(status='waiting',animation_active=True,job_flags=[m[0x300],m[0x304]],register_contract=False)
        if request<128:
            if request>16:raise ValueError('Initial16 tactic animation requests1..16 required')
            m[0x4C9]=request-1;m[0x4CA]=0;m[0x4C8]=128;m[0x4D1]=7;self._animation_setup(0,r.y)
        else:
            stage=request&15
            if stage>=2:raise ValueError('Actual animation controller states80/81 required')
            self._dispatch_scratch(0xD00B,0xD41F if stage==0 else 0xD010,r.y)
            if stage==0:self._animation_setup(m[0x4CA],r.y)
            else:self._animation_frame()
        return dict(status='returned',animation_active=m[0x4C8]!=0,request_04C8=m[0x4C8],kind_04C9=m[0x4C9],substate_04CA=m[0x4CA],counter_04D0=m[0x4D0],register_contract=False,PPU_rendered=False,PCM_generated=False)
