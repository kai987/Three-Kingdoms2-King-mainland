"""Independent tactical decision rules recovered from the pinned NES ROM.

These semantic APIs do not execute ROM code or acknowledge game/UI jobs.
The complete CPU controller is separate. Movement is a two-axis greedy proposal,
not a general path finder. All mutation methods use the caller's shared 64K RAM.
"""
from dataclasses import dataclass
import hashlib
from . import ai
from .terrain_semantics import TerrainSemanticsData, ai_movement_quote

ROM_SHA256 = ai.ROM_SHA256
STRATEGY_ENTRIES = (0xA0B1,0xA105,0xA166,0xA210,0xA2AD,0xA329,0xA507,0xA606)

@dataclass(frozen=True)
class TacticalData:
    costs: TerrainSemanticsData
    rng: bytes
    chunk_pointers: tuple
    chunk_tiles: tuple
    terrain_classes: bytes

    @classmethod
    def from_rom(cls, rom: bytes):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:
            raise ValueError('Tactical data is pinned to the analyzed ROM')
        pointers=tuple(int.from_bytes(rom[0x117DB+2*i:0x117DD+2*i],'little') for i in range(120))
        tiles=[]
        for i,pointer in enumerate(pointers):
            bank=(rom[0x118CB+i]&63)%32
            offset=16+bank*8192+pointer-0x8000
            tiles.append(bytes(rom[offset:offset+256]))
        return cls(TerrainSemanticsData.from_rom(rom),bytes(rom[0x115F5:0x116F5]),pointers,tuple(tiles),bytes(rom[0x1175B:0x117DB]))

class TacticalDecisions:
    """Readable gameplay calculations; CPU registers/stack/mapper are excluded.

    Declared mutable RAM is 0020..002F, 042C..042E and all SRAM6000..7FFF.
    Each method documents its exact original entry and endpoint. Stack scratch,
    data-window selector DE and registerE000 writes of F266 are outside this semantic API.
    """
    def __init__(self,memory,data:TacticalData):
        if len(memory)!=65536: raise ValueError('Shared 64K memory is required')
        self.memory=memory; self.data=data

    def _set(self,address,value): self.memory[address]=value&255
    def _word(self,address): return self.memory[address]|(self.memory[address+1]<<8)
    def _putword(self,address,value): self._set(address,value);self._set(address+1,value>>8)
    def _actor(self):
        slot=self.memory[0x6F8C]
        if slot>=20:raise ValueError('Original active actor domain0..19 required')
        ident=self.memory[0x664+slot]
        if ident>=237:raise ValueError('Original active officer domain0..236 required')
        return slot,ident,0x63C0+12*ident

    def decision_state(self):
        m=self.memory
        return dict(control=m[0x6F8B],actor=m[0x6F8C],action=m[0x6F8D],target=m[0x6F8E],status=m[0x6F8F],
                    scan_cursor=m[0x6F94],no_action_count=m[0x6F95],attempted_count=m[0x6F96],movement_cost=m[0x6F97],
                    action_points=m[0x505],current_side=m[0x504])

    def _scan(self):
        m=self.memory; rescans=0
        while True:
            while m[0x6F94]<20:
                slot=m[0x6F94];self._set(0x6F94,slot+1)
                if m[0x6FA1+slot]==255 or ai.opposing_side_marker(m[0x504],m[0x628+slot]) or m[0x664+slot]==255:continue
                strategy=m[0x6FA1+slot]&15
                if strategy>=8:raise ValueError('Eight-entry strategy table only supports low nibble0..7')
                self._set(0x6F96,m[0x6F96]+1);m[0x6F8C]=slot
                return dict(stop='strategy_entry',actor=slot,strategy=strategy,entry=STRATEGY_ENTRIES[strategy],rescans=rescans)
            if m[0x6F96]==m[0x6F95]:
                m[0x6F8F]=3;m[0x6F94]=0;m[0x6F8B]=255
                return dict(stop='return',rescans=rescans)
            m[0x6F94]=m[0x6F95]=m[0x6F96]=0;rescans+=1

    def prepare_actor(self):
        """A02D prefix: return/secondary routing or stop immediately at A099.

        A qualifying slot increments attempted_count before its strategy runs.
        This does not manufacture a strategy result or commit a battle action.
        """
        flag=self.memory[0x6F8B]
        if flag==255:return dict(stop='return',rescans=0)
        if flag==1:return dict(stop='secondary_entry',entry=0xB933,rescans=0)
        return self._scan()

    def finish_actor(self):
        """A062 suffix using an explicitly present strategy result in6F8F.

        Status3 increments no_action_count and scans the next actor. Other
        statuses yield one proposal by writing6F8B=FF. If scan counts differ,
        the original resets all three counters and scans another pass.
        """
        m=self.memory
        if m[0x6F8F]!=3:
            m[0x6F8B]=255;return dict(stop='return',proposal_yielded=True,rescans=0)
        self._set(0x6F95,m[0x6F95]+1)
        return dict(self._scan(),proposal_yielded=False)

    def _neighbors(self,slot):
        m=self.memory;ids=[m[0x664+i]for i in range(20)];xs=[m[0x600+i]for i in range(20)];ys=[m[0x614+i]for i in range(20)]
        values=ai.orthogonal_neighbors(slot,ids,xs,ys,[m[0x628+i]for i in range(20)],m[0x504])
        for i,value in enumerate(values):
            m[0x6FDD+i]=value
            if value!=255:m[0x24]=value&127
        self._set(0x22,xs[slot]+1);m[0x23]=ai.normalize_y(ys[slot])
        return values

    def _terrain(self,x,y):
        m=self.memory;pointer=self._word(0xA8);quadrant=int(x>=16)|2*int(y>=16);chunk=m[(pointer+quadrant)&65535]
        if chunk>=120:raise ValueError('Original map chunk domain0..119 required')
        self._putword(0x22,self.data.chunk_pointers[chunk]);m[0x24]=0x4B;m[0x25]=0xB7;m[0x26]=x&15
        tile=self.data.chunk_tiles[chunk][((y<<4)&255)|(x&15)]
        raw=self.data.terrain_classes[tile]if tile<128 else 0
        return 2 if raw>=6 else raw

    def quote_direction(self,direction):
        """Complete A740: prospective raw coordinate bounds + AP cost/carry.

        Does not consume AP. Y=15 in the caller encodes an unavailable quote.
        The repeated officer-byte8 read and affinity3 zero-cost row survive.
        """
        slot,ident,record=self._actor();m=self.memory
        if not 0<=direction<4:raise ValueError('Four orthogonal directions0..3 required')
        m[0x20]=m[0x21]=0;delta=1 if direction&1 else 255;m[0x22]=delta
        axis=((direction>>1)&1)^1;m[0x20+axis]=delta
        self._set(0x20,m[0x600+slot]+m[0x20]);x=m[0x20]
        if x>=31:return dict(carry=False,bounds_valid=False,encoded_cost=15,direction=direction)
        self._set(0x21,m[0x614+slot]+m[0x21]);y=m[0x21]
        if y>=20:return dict(carry=False,bounds_valid=False,encoded_cost=15,direction=direction)
        terrain=self._terrain(x,y);self._putword(0x20,record);m[0x22]=(m[record+11]>>2)&3
        quote=ai_movement_quote(terrain,m[record+11],m[record+8],m[0x505],data=self.data.costs)
        return dict(quote,bounds_valid=True,direction=direction,encoded_cost=quote['cost']if quote['carry']else 15,coordinate=[x,y])

    def plan_movement(self,target_x,target_normalized_y):
        """Complete A60C..A836; target0020/21 supplied by strategy caller.

        Compare two desired axes, prefer the larger displacement (vertical on
        ties), then sort these two quotes by cost. A free, affordable neighbor
        proposes status0/direction and cost6F97; nonzero condition0650 blocks
        it. Only literal strategy byte1/5 enables occupied-enemy fallback.
        No coordinate, AP, battle status or troop count is committed here.
        """
        slot,ident,record=self._actor();m=self.memory
        m[0x20]=target_x&255;m[0x21]=target_normalized_y&255
        self._neighbors(slot)
        dx=(m[0x20]-m[0x600+slot])&255;m[0x20]=dx;m[0x22]=ai.abs_signed_u8_difference(target_x,m[0x600+slot])
        m[0x23]=ai.normalize_y(m[0x614+slot]);dy=(m[0x21]-m[0x23])&255;m[0x21]=dy
        m[0x23]=ai.abs_signed_u8_difference(target_normalized_y,ai.normalize_y(m[0x614+slot]))
        horizontal=2 if dx&128 else 3;vertical=0 if dy&128 else 1
        first_horizontal=m[0x23]<m[0x22]
        directions=[horizontal,vertical]if first_horizontal else[vertical,horizontal]
        secondary_axis=1 if first_horizontal else 0
        if m[0x22+secondary_axis]==0:directions[1]=255
        m[0x2A],m[0x2B]=directions
        quotes=[]
        for i,direction in enumerate(directions):
            if direction==255:m[0x2C+i]=255;quotes.append(255);continue
            q=self.quote_direction(direction);cost=q['encoded_cost'];m[0x22]=(cost<<4)&255
            m[0x2A+i]=direction|m[0x22];m[0x2C+i]=m[0x22];quotes.append(cost)
        if m[0x2C]>m[0x2D]:m[0x2A],m[0x2B]=m[0x2B],m[0x2A]
        m[0x2F]=m[0x6FB5+slot]
        for encoded in(m[0x2A],m[0x2B]):
            if encoded>=240:continue
            m[0x20]=encoded;direction=encoded&15
            if m[0x6FDD+direction]!=255:continue
            if m[0x650+slot]:m[0x6F8F]=3;return dict(self.decision_state(),kind='none',reason='condition_nonzero',quotes=quotes)
            m[0x6F8D]=direction;m[0x6F8F]=0;m[0x6F97]=encoded>>4;m[0x6FB5+slot]=direction^1
            return dict(self.decision_state(),kind='movement',quotes=quotes)
        if m[0x6FA1+slot]in(1,5):
            for encoded in(m[0x2A],m[0x2B]):
                if encoded>=240:continue
                value=m[0x6FDD+(encoded&15)]
                if value==255 or not value&128:continue
                m[0x6F8D]=value&127
                if m[0x505]>=2:
                    m[0x6F8F]=1;return dict(self.decision_state(),kind='attack',quotes=quotes)
        m[0x6F8F]=3;return dict(self.decision_state(),kind='none',reason='both_desired_directions_unavailable',quotes=quotes)

    def adjacent_attack(self):
        """Complete A8A8: AP>=2 then first enemy in up/down/left/right order."""
        slot,_,_=self._actor();m=self.memory
        if m[0x505]<2:return dict(success=False)
        for value in self._neighbors(slot):
            if value!=255 and value&128:
                m[0x6F8D]=value&127;m[0x6F8F]=1
                return dict(success=True,target=value&127)
        return dict(success=False)

    def nearest_enemy(self,radius):
        """A17B..A1A6/A2BF..A2E8 candidate scan prefix, strict first tie.

        Produces6FC9 candidate array and minimum signed-marked distance;
        stops before caller-specific fallback and target coordinate load.
        """
        slot,_,_=self._actor();m=self.memory;m[0x22]=radius&255;m[0x20]=m[0x600+slot];m[0x21]=ai.normalize_y(m[0x614+slot])
        self._candidate_map()
        m[0x20]=255
        for target in range(20):
            value=m[0x6FC9+target]
            if value&128 and(value&127)<m[0x20]:m[0x20]=value&127;m[0x21]=target
        return dict(found=m[0x20]!=255,target=m[0x21]if m[0x20]!=255 else None,distance=m[0x20])

    def _candidate_map(self):
        m=self.memory;cx,cy,radius=m[0x20],m[0x21],m[0x22]
        for target in range(20):
            m[0x6FC9+target]=0
            if m[0x664+target]==255:continue
            dx=ai.abs_signed_u8_difference(m[0x600+target],cx)
            if dx>radius:continue
            m[0x23]=dx;dy=ai.abs_signed_u8_difference(ai.normalize_y(m[0x614+target]),cy)
            if dy>radius:continue
            self._set(0x23,dx+dy+int(dy==radius))
            m[0x6FC9+target]=m[0x23]|ai.opposing_side_marker(m[0x504],m[0x628+target])

    def _random_below(self,bound,x):
        draws=[]
        for _ in range(256):
            index=self.memory[0x6F92];value=self.data.rng[index]
            self.memory[0x6F93]=x;self._set(0x6F92,index+1);draws.append(value)
            if value<bound:return value,draws
        raise ValueError('RNG permutation must include an accepted draw')

    def _multiply_scratch(self):
        """B585 unsigned24-by8 product, exact documented scratch bytes."""
        m=self.memory;value=m[0x20]|m[0x21]<<8|m[0x22]<<16;factor=m[0x23];product=value*factor
        m[0x23]=m[0x25]=0;shifted=(value<<8)&0xFFFFFFFF
        for i in range(3):m[0x20+i]=(shifted>>(8*i))&255
        m[0x24]=shifted>>24
        for i in range(4):m[0x26+i]=(product>>(8*i))&255

    def _divide_scratch(self):
        """B536 unsigned24/16 restoring division; retain final trial scratch."""
        m=self.memory;quotient=m[0x20]|m[0x21]<<8|m[0x22]<<16;divisor=self._word(0x23);remainder=0
        for _ in range(24):
            remainder=(remainder<<1)|(quotient>>23);quotient=(quotient<<1)&0xFFFFFF
            trial=(remainder-divisor)&0xFFFFFF
            m[0x28]=trial&255;m[0x29]=(trial>>8)&255
            if remainder>=divisor:remainder=trial;quotient|=1
        for i in range(3):m[0x20+i]=(quotient>>(8*i))&255;m[0x25+i]=(remainder>>(8*i))&255

    def secondary_effect(self):
        """Complete B933..BAB2, including cached-slot bug and discarded RNG.

        This is an existing reserved-effect application, not selection of a
        named tactic. It subtracts masked10-bit troops and preserves byte9's
        upper6 bits. The initial IQ-difference threshold and accepted0..100
        sample are overwritten/discarded in the ROM but still consume RNG.
        """
        actor,ident,record=self._actor();m=self.memory;group=0 if m[0x504]&128 else 4
        m[0x6F8F]=255;m[0x2A]=group;cached=m[0x4D8+group]
        def finish(reason,**extra):
            m[0x6F8B]=255;return dict(self.decision_state(),reason=reason,**extra)
        if cached==255:return finish('no_reserved_slot')
        if cached>=20 or m[0x664+cached]>=237:raise ValueError('Reserved active officer is required')
        m[0x20]=m[0x4D9+group];m[0x21]=m[0x4DA+group]
        # Original B965 deliberately indexes0614 by group0/4, not actor X.
        exact=m[0x600+actor]==m[0x20]and m[0x614+group]==m[0x21]
        if not exact:
            m[0x21]=ai.normalize_y(m[0x21]);m[0x22]=2;self._candidate_map()
            if not m[0x6FC9+actor]:return finish('zero_or_outside_radius')
        m[0x20]=m[0x600+actor];m[0x21]=m[0x614+actor]
        if self._terrain(m[0x20],m[0x21])!=0:return finish('actor_terrain_not_zero')
        cached_record=0x63C0+12*m[0x664+cached];self._putword(0x20,cached_record)
        m[0x23]=m[cached_record+2];m[0x24]=m[cached_record+11];self._putword(0x20,record);m[0x22]=m[record+2]
        difference=(m[0x23]-m[0x22])&255
        m[0x20]=((0 if difference&128 else difference)+10)&255
        unused,draws0=self._random_below(101,cached)
        flags=m[0x24];partial=((flags<<3)&255)+flags
        m[0x2A]=(partial+flags+int(partial>255))&255
        m[0x20]=m[0x23];m[0x21]=m[0x22]=0
        sample,draws1=self._random_below(11,cached);m[0x23]=sample+30
        self._multiply_scratch();m[0x20]=m[0x26];m[0x21]=m[0x27];m[0x23]=10;m[0x22]=m[0x24]=0
        self._divide_scratch();damage=self._word(0x20)+m[0x2A];self._putword(0x22,damage)
        self._putword(0x20,record);m[0x24]=m[record+8];m[0x25]=m[record+9]&3
        troops=self._word(0x24);self._putword(0x26,(troops-damage)&65535)
        if troops<damage:self._putword(0x22,troops);self._putword(0x26,0)
        m[record+8]=m[0x26];m[record+9]=(m[record+9]&252)|m[0x27]
        m[0x42C]=m[0x22];m[0x42D]=m[0x23];m[0x42E]=0;m[0x6F8F]=0
        return finish('applied',lost_troops=self._word(0x22),remaining_low10=self._word(0x26),
                      discarded_sample=unused,effect_sample=sample,random_draws=draws0+draws1)
