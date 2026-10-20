"""Readable original text-script producer and its real PPU consumers.

These interpret game text data, never 6502 opcodes or control IR. Requests remain
pending until the actual consumer writes the tiles. Hardware status must be
supplied by the caller; there is no synthetic text/animation completion flag.
"""
from dataclasses import dataclass
import hashlib
from .officers import ROM_SHA256
from .game_algorithms import packed_bcd6

@dataclass(frozen=True)
class TextData:
    rom:bytes
    command_targets:tuple
    message_selectors:bytes
    number_widths:bytes
    actor_panel_template:bytes
    symbol_centering:bytes
    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned original text ROM required')
        base=16+29*8192
        return cls(bytes(rom),tuple(int.from_bytes(rom[base+0x208+2*i:base+0x20A+2*i],'little')for i in range(32)),
                   bytes(rom[base+0x6A7:base+0x6B6]),bytes(rom[base+0x607:base+0x60F]),
                   bytes(rom[base+0x856:base+0x891]),bytes(rom[0x3F36F:0x3F377]))
    def data_byte(self,selector,address):
        if not 0x8000<=address<0xA000:raise ValueError(f'Text data-window address ${address:04X} required')
        return self.rom[16+((selector&63)%32)*8192+address-0x8000]

class TextServices:
    def __init__(self,memory,data):
        self.memory=memory;self.data=data;self._consumer=None;self._consumer_kind=None
    def _byte(self,address):
        address&=65535
        return self.data.data_byte(self.memory[0xE1],address)if 0x8000<=address<0xA000 else self.memory[address]
    def _set(self,address,value):self.memory[address]=value&255
    def _select(self,selector):
        self.memory[0xE1]=selector;self.memory[0xE000]=selector
    def select_message_window(self):
        """A690: low20 messages use globalmode0, others use actual007A."""
        mode=0 if self.memory[0x310]<32 else self.memory[0x7A]
        if not 0<=mode<len(self.data.message_selectors):raise ValueError('Original message mode0..14 required')
        self._select(self.data.message_selectors[mode]);return mode
    def _message_pointer(self):
        mode=self.select_message_window();table=0x8000+self.memory[0x310]*2
        self.memory[0xA6]=self._byte(table)
        self._set(0xA7,self._byte(table+1)+(64 if 3<=mode<9 else 32))
    def _next(self):
        m=self.memory;value=self._byte(m[0xA6]|m[0xA7]<<8)
        self._set(0xA6,m[0xA6]+1)
        if m[0xA6]==0:self._set(0xA7,m[0xA7]+1)
        return value
    def _emit(self,value,column):
        m=self.memory
        if m[0x30C]==0 and value in (0x39,0x3A):
            m[0x34B+column]=value;return column
        self._set(0x31C+column,value+m[0x30F]);return (column+1)&255
    def _flush(self,column):
        self.memory[0x31C+column]=self.memory[0x34C+column]=128
        self.memory[0x7E]|=1
    def _named_symbol(self,ident,column,*,width=None,city=False):
        m=self.memory;restore=m[0xE1];self._select(48)
        address=(0x9A1A+((8*ident)&255))if city else (0x901A+10*ident)
        if width is None:
            for i in range(256):
                value=self._byte(address+i)
                if value==0:break
                column=self._emit(value,column)
            else:raise ValueError('Original symbol terminator missing')
        else:
            accents=0
            for i in range(width):
                value=self._byte(address+i)or 1
                if value in (0x39,0x3A):accents+=1
                column=self._emit(value,column)
            for _ in range(accents):column=self._emit(1,column)
        self._select(restore);return column
    def _decimal(self,value):
        bcd=packed_bcd6(value)
        for i,b in enumerate(bcd):self.memory[7+i]=b
        return [(bcd[2]>>4)&15,bcd[2]&15,(bcd[1]>>4)&15,bcd[1]&15,(bcd[0]>>4)&15,bcd[0]&15]
    def _report_number(self,index,column):
        m=self.memory;a=0x42C+3*index
        digits=self._decimal(m[a]|m[a+1]<<8|m[a+2]<<16);started=False
        for i,digit in enumerate(digits):
            if digit or started or i==5:column=self._emit(0x76+digit,column);started=True
        return column
    def _field_number(self,index,column):
        m=self.memory;a=0x44C+3*index;value=m[a]|m[a+1]<<8|m[a+2]<<16
        if m[a+2]==254:
            for value in (1,0x6F,0x6F):column=self._emit(value,column)
            self._next();return column
        missing=m[a+2]==255
        digits=self._decimal(0 if missing else value)
        width_index=self._next()
        if width_index>=len(self.data.number_widths):raise ValueError('Original number width index0..7 required')
        remaining=self.data.number_widths[width_index];started=False
        for i,digit in enumerate(digits):
            remaining=(remaining-1)&255 if i<5 else remaining
            if i<5 and not started and digit==0:
                if remaining<128:continue
                column=self._emit(1,column)
            else:
                column=self._emit(1 if missing else 0x76+digit,column);started=True
        return column
    def produce_text(self,*,budget=4096):
        """Complete29 A003/A154/A158 worker, one actual row/data window.

        Return after the original end/newline/position command. All32 legal
        text data commands are independent source. Does not consume the job.
        Arithmetic CPU scratch, stack and temporary registers are not its
        semantic API; original0310 queue, all buffers and bank writes are.
        """
        m=self.memory
        if m[0x81]&1:m[0x308]=1
        if m[0x300]==255 or m[0x7E]&1:return {'status':'waiting','progress':m[0x300],'PPU_jobs':m[0x7E]}
        m[0x304]=0;self.select_message_window()
        if m[0x300]==0:
            self._message_pointer();m[0x306]=self._next();m[0x307]=self._next()
            m[0x300]=1;m[0x303]=m[0x308]=m[0x30C]=m[0x30F]=0;m[0x305]=3
        for offset in range(40,0,-1):m[0x31C+offset]=m[0x34C+offset]=1
        m[0x31C]=m[0x306];m[0x31D]=m[0x307]
        m[0x34C]=(m[0x306]-32)&255;m[0x34D]=(m[0x307]-(1 if m[0x306]<32 else 0))&255
        column=2
        for _ in range(budget):
            token=self._next()
            if token<128 or token>=192:column=self._emit(token,column);continue
            if token>=160:raise ValueError(f'Text command ${token:02X} is outside original32-entry table')
            if token==0x80:
                m[0x300]=255;self._flush(column)
                for address in range(0x310,0x313):m[address]=m[address+1]
                m[0x313]=255
                if m[0x310]!=255:m[0x300]=0
                return {'status':'returned','boundary':'message_end','PPU_jobs':m[0x7E],'column':column}
            if token==0x81:
                self._flush(column);address=((m[0x306]|m[0x307]<<8)+64)&65535
                m[0x306]=address&255;m[0x307]=address>>8
                return {'status':'returned','boundary':'next_row','PPU_jobs':m[0x7E],'column':column}
            if token==0x82:
                m[0x309]=m[0x310];m[0x30A]=m[0xA6];m[0x30B]=m[0xA7]
                m[0x310]=self._byte(m[0xA6]|m[0xA7]<<8);self._message_pointer()
            elif token==0x83:
                m[0x310]=m[0x309];self._message_pointer()
                m[0xA6]=m[0x30A];m[0xA7]=m[0x30B];self._next()
            elif token in (0x84,0x85):m[0x303]=128 if token==0x84 else 0
            elif token in (0x86,*range(0x8A,0x90)):
                m[0x306]=self._next();m[0x307]=self._next();self._flush(column)
                return {'status':'returned','boundary':'position','PPU_jobs':m[0x7E],'column':column}
            elif token in (0x87,0x88):m[0x30C]=1 if token==0x87 else 0
            elif token==0x89:m[0x30F]=self._next()
            elif 0x90<=token<=0x97:column=self._named_symbol(m[0x42C+token-0x90],column)
            elif 0x98<=token<=0x9B:column=self._report_number(token-0x98,column)
            elif token==0x9C:
                index=self._next();ident=m[0x42C+index]
                if ident&128:
                    restore=m[0xE1];self._select(48)
                    for _ in range(6):column=self._emit(1,column)
                    self._select(restore)
                else:column=self._named_symbol(ident,column,width=6,city=True)
            elif token==0x9D:column=self._named_symbol(m[0x42C+self._next()],column,width=7)
            elif token==0x9E:column=self._field_number(self._next(),column)
            elif token==0x9F:column=self._named_symbol(m[0x42C+self._next()],column)
        raise RuntimeError('Text script did not reach an original service boundary')

    def _read_port(self,address):
        from .service_memory import IOReadUnavailable
        while True:
            try:return self.memory[address]
            except IOReadUnavailable as exc:
                yield {'status':'dependency','hardware_read':address,'reason':str(exc)}

    def _consume(self,kind,program):
        if self._consumer is not None and self._consumer_kind!=kind:
            raise RuntimeError('A different PPU consumer still owns its pending input')
        if self._consumer is None:self._consumer=program();self._consumer_kind=kind
        try:return next(self._consumer)
        except StopIteration as done:
            self._consumer=None;self._consumer_kind=None;return done.value

    def consume_text(self):
        """Complete29 A000/A048 consumer; pending hardware reads can resume."""
        return self._consume('text',self._text_consumer)

    def _text_consumer(self):
        m=self.memory
        if m[0x7E]&4:return {'status':'waiting','reason':'map job has original priority'}
        if not m[0x303]and not m[0x308]and m[0x5E]&m[0x305]:
            from .battle_nmi_services import BattleNMIServices,NMIRegisters
            palette=BattleNMIServices(m);result=palette.run_service(0xE70E,NMIRegisters())
            while result['status']=='dependency':
                yield result;result=palette.resume()
            return {'status':result['status'],'reason':'original text cadence, actual palette upload','text_job_consumed':False}
        burst=bool(m[0x303]or m[0x308]);cursor=0 if burst else m[0x304]
        if cursor==255:return {'status':'waiting','reason':'caller must have an actual text job'}
        if not burst and m[0x34E+cursor]==128:
            m[0x304]=255;m[0x7E]&=254
            return {'status':'returned','text_job_consumed':True,'characters':0}
        def address(lo,hi,offset=0):
            yield from self._read_port(0x2002)
            m[0x2006]=m[hi];m[0x2006]=(m[lo]+offset)&255
        if burst:
            count=0
            for lo,hi,base in [(0x31C,0x31D,0x31E)]+([]if m[0x30C]else[(0x34C,0x34D,0x34E)]):
                yield from address(lo,hi)
                for i in range(256):
                    value=m[base+i]
                    if value==128:break
                    m[0x2007]=value;count+=1
                else:raise ValueError('Original text row sentinel missing')
            m[0x304]=255;m[0x7E]&=254
            return {'status':'returned','text_job_consumed':True,'tile_writes':count}
        yield from address(0x31C,0x31D,cursor);m[0x2007]=m[0x31E+cursor]
        if not m[0x30C]:
            yield from address(0x34C,0x34D,cursor);m[0x2007]=m[0x34E+cursor]
        self._set(0x304,cursor+1)
        return {'status':'returned','text_job_consumed':False,'characters':1}

    def consume_map_commands(self,*,budget=256):
        """Complete29 A006/A11B: execute real0380 length/address/tile packets.

        EE53 clears its selected bit before entering this service. This method
        never clears that bit or marks other work. Absent hardware inputs leave
        a resumable dependency rather than replaying partially emitted writes.
        """
        return self._consume('map',lambda:self._map_consumer(budget))

    def _map_consumer(self,budget):
        m=self.memory;m[0x2000]=m[0x8B]&251;m[0]=128;m[1]=3
        yield from self._read_port(0x2002)
        index=0;writes=0
        for _ in range(budget):
            count=m[0x380+index]
            if count==255:return {'status':'returned','tile_writes':writes}
            index=(index+1)&255;m[0x2006]=m[0x380+index]
            index=(index+1)&255;m[0x2006]=m[0x380+index];index=(index+1)&255
            for _ in range(count or 256):
                m[0x2007]=m[0x380+index];writes+=1;index=(index+1)&255
        raise ValueError('Original map command sentinel/budget exhausted')

    def cancel_text(self):
        """A10A: explicit original cancellation, separate from rendering."""
        m=self.memory;m[0x300]=m[0x304]=255;m[0x7E]&=254
        return {'status':'returned','cancelled':True}

    def text_ready(self):
        """Exact13 DF27 returnedcarry predicate; no flag is rewritten."""
        return self.memory[0x304]==255 and self.memory[0x300]==255

    def draw_actor_panel(self):
        """Complete29 A027/A830 name-panel command generation.

        This builds the selected officer's two name-glyph rows, not a whole
        portrait framebuffer. Two original F308 data-window requests occur.
        """
        m=self.memory;slot=m[0x509]
        if not 0<=slot<20:raise ValueError('Selected original battle slot0..19 required')
        for i in range(58,-1,-1):m[0x380+i]=self.data.actor_panel_template[i]
        for accents in (True,False):
            ident=m[0x664+slot];self._select(48);address=0x901A+10*ident
            m[2]=ident;m[0]=address&255;m[1]=address>>8
            symbols=[]
            for i in range(256):
                value=self._byte(address+i)
                if value==0:break
                symbols.append(value)
            else:raise ValueError('Name symbol terminator missing')
            length=sum(v not in(0x39,0x3A)for v in symbols)
            if length>=len(self.data.symbol_centering):raise ValueError('Original name centering table exceeded')
            column=self.data.symbol_centering[length]
            for value in symbols:
                if value in(0x39,0x3A):
                    if accents:m[0x3A5+column]=value
                else:
                    if not accents:m[0x3B1+column]=value
                    column=(column+1)&255
        m[0x7E]|=4
        return {'status':'returned','map_commands_pending':True,'selected_slot':slot,'officer_id':ident}
