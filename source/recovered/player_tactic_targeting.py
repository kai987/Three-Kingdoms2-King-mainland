"""Readable player16-tactic target qualification, separate from effect chance.

eligible() is the complete AD80->selected predicate->RTS data behavior. It is
not the AI's action_predicate. can_target() adds the cursor-selection enemy and
range checks, without UI, message/audio preparation or AP/effect consumption.
No IR, CPU executor, ROM fallback or acknowledgement is used.
"""
from dataclasses import dataclass
import hashlib
from .tactical_decisions import TacticalData,ROM_SHA256
from .battle import grid_distance
PLAYER_ENTRIES=(0xADCC,0xADD8,0xADD8,0xADD8,0xADE4,0xADEE,0xADFB,0xAE68,0xAEC4,0xAECE,0xAF0A,0xAF73,0xAF0A,0xAFA1,0xAFD3,0xB01D)
DECLARED_RAM_RANGES=((0x0A,0x0C),(0x10,0x12),(0x509,0x50B),(0x543,0x544))

@dataclass(frozen=True)
class TargetingData:
    tactical:TacticalData
    data_pages:tuple
    chunk_banks:bytes
    player_costs:bytes
    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Targeting data requires the pinned ROM')
        assert tuple(int.from_bytes(rom[0x18DBC+2*i:0x18DBE+2*i],'little')for i in range(16))==PLAYER_ENTRIES
        assert rom[0x1175B:0x117DB]==rom[0x1BBAE:0x1BC2E]
        return cls(TacticalData.from_rom(rom),tuple(bytes(rom[16+8192*i:16+8192*(i+1)])for i in range(32)),bytes((v&63)%32 for v in rom[0x118CB:0x11943]),bytes(rom[0x18BD9:0x18BE9]))

class PlayerTacticTargeting:
    """All16 AD80 qualifiers; shared SRAM/RAM, original returned carry.

    Declare RAM0A/0B,10/11,0509/050A,0543 and full8KSRAM. CPU scratch
    00..09, registers/flags other than returnedcarry, stack and mapper excluded.
    Logical data bank tracks real F266 reads without writing mapper.
    """
    def __init__(self,memory,data:TargetingData,*,data_window_bank=None):
        self.memory=memory;self.data=data;self._data_bank=data_window_bank if data_window_bank is not None else getattr(memory,'banks',[None])[0]
        if self._data_bank is not None and not 0<=self._data_bank<32:raise ValueError('Physical data bank0..31 required')
    @staticmethod
    def _id(tactic):
        if not isinstance(tactic,int)or not 0<=tactic<16:raise ValueError('Sixteen-entry player tactic domain0..15 required')
    def _slots(self):
        actor=self.memory[0x50A];target=self.memory[0x509]
        if actor>=20 or target>=20:raise ValueError('Original actor/target slots0..19 required')
        return actor,target
    def _sync(self,bank):
        if bank is None and hasattr(self.memory,'banks'):bank=self.memory.banks[0]
        if bank is not None:
            if not 0<=bank<32:raise ValueError('Physical data bank0..31 required')
            self._data_bank=bank
    def _read_descriptor(self,address):
        if 0x8000<=address<0xA000:
            if self._data_bank is None:raise ValueError('ROM descriptor requires current data_window_bank')
            return self.data.data_pages[self._data_bank][address-0x8000]
        return self.memory[address]
    def terrain_at(self,x,y):
        """Complete DB46 terrain result, including raw6/7/8->class2."""
        m=self.memory;x&=255;y&=255;pointer=m[0xA8]|m[0xA9]<<8
        if not(pointer<=0x7FC or 0x6000<=pointer<=0x7FFC or 0x8000<=pointer<=0x9FFC):raise ValueError('Four-byte RAM/SRAM/data-window map descriptor required')
        chunk=self._read_descriptor(pointer+int(x>=16)+2*int(y>=16))
        if chunk>=120:raise ValueError('Original map chunk domain0..119 required')
        tile=self.data.tactical.chunk_tiles[chunk][((y<<4)&255)|(x&15)]
        self._data_bank=self.data.chunk_banks[chunk]
        raw=self.data.tactical.terrain_classes[tile]if tile<128 else 0
        return 2 if raw>=6 else raw
    @staticmethod
    def _normalized_y(y):return(y-1)&255 if y>=16 else y
    def _neighbors(self,target):
        m=self.memory;x=m[0x600+target];y=self._normalized_y(m[0x614+target])
        return [((x+1)&255,y),((x-1)&255,y),(x,(y+1)&255),(x,(y-1)&255)]
    def _actor_adjacent(self,actor,target):
        m=self.memory;ax=m[0x600+actor];ay=self._normalized_y(m[0x614+actor])
        return any(x<32 and y<20 and (x,y)==(ax,ay)for x,y in self._neighbors(target))
    def _enemy_at(self,x,y):
        """AE/AF coordinate helper: highest matching slot; no ID filter."""
        if x>=32 or y>=20:return None
        if y==15:y=16
        m=self.memory;slot=next((s for s in range(19,-1,-1)if m[0x600+s]==x and m[0x614+s]==y),None)
        if slot is None or not((m[0x628+slot]^m[0x504])&128):return None
        return slot,x,y
    def _enemy_neighbor(self,target,terrain_condition=None):
        for x,y in self._neighbors(target):
            found=self._enemy_at(x,y)
            if found is None:continue
            if terrain_condition is None:return True
            # Only AF44's enemy branch writes10/11 then calls DB46.
            self.memory[0x10]=found[1];self.memory[0x11]=found[2]
            if terrain_condition(self.terrain_at(found[1],found[2])):return True
        return False
    def eligibility_suffix(self,tactic_id,target_terrain,actor_terrain):
        """Complete ADA4 dispatch predicates with actual0A/0B input classes.

        This exact suffix is useful when the real AD80 terrain prelude has
        already run. Terrain-neighbor queries still use actual map data.
        Costs are quoted, never charged; successcarry is eligibility only.
        """
        self._id(tactic_id);actor,target=self._slots();m=self.memory
        tt=target_terrain&255;at=actor_terrain&255;m[0x0A]=tt;m[0x0B]=at
        reason=None
        def require(ok,why):return None if ok else why
        if tactic_id==0:reason=require(tt in(0,2),'target_terrain_not_0_or_2')
        elif tactic_id in(1,2,3):reason=require(tt in(0,4),'target_terrain_not_0_or_4')
        elif tactic_id==4:reason=require(tt==3,'target_terrain_not_3')
        elif tactic_id==5:reason=require(target in(0,10),'target_not_army_first_slot')
        elif tactic_id==6:
            reason=require(tt==5,'target_terrain_not_5')
            if reason is None:reason=require(self._actor_adjacent(actor,target),'actor_not_orthogonally_adjacent')
        elif tactic_id==7:
            reason=require(tt in(0,4),'target_terrain_not_0_or_4')
            if reason is None:reason=require(self._enemy_neighbor(target),'no_enemy_orthogonal_neighbor')
        elif tactic_id==8:reason=require(tt!=5,'target_terrain_5')
        elif tactic_id==9:
            reason=require(at in(4,5),'actor_terrain_not_4_or_5')
            if reason is None:reason=require(self._actor_adjacent(actor,target),'actor_not_orthogonally_adjacent')
            if reason is None:reason=require(tt!=5,'target_terrain_5')
        elif tactic_id in(10,12):
            reason=require(tt==3,'target_terrain_not_3')
            if reason is None:reason=require(self._enemy_neighbor(target,lambda t:t==3),'no_enemy_terrain3_neighbor')
        elif tactic_id==11:
            reason=require(at==0,'actor_terrain_not_0')
            if reason is None:
                ident=m[0x664+actor]
                if ident>=237:raise ValueError('Original caster officer domain0..236 required')
                address=0x63C0+12*ident
                reason=require(m[address+9]!=0 or m[address+8]>=100,'caster_raw_troops_below100')
            if reason is None:reason=require(m[0x4D8+(4 if m[0x504]&128 else 0)]==255,'own_ambush_cache_occupied')
        elif tactic_id==13:
            reason=require(at==5,'actor_terrain_not_5')
            if reason is None:reason=require(self._actor_adjacent(actor,target),'actor_not_orthogonally_adjacent')
        elif tactic_id==14:
            reason=require(tt!=5,'target_terrain_5')
            if reason is None:reason=require(self._enemy_neighbor(target,lambda t:t!=5),'no_enemy_non5_neighbor')
        else:reason=require(tt not in(3,5),'target_terrain_3_or_5')
        return dict(status='returned',tactic_id=tactic_id,eligible=reason is None,carry=reason is None,reason=reason,
                    actor_slot=actor,target_slot=target,actor_terrain=at,target_terrain=tt,player_AP_cost=self.data.player_costs[tactic_id],AP_charged=False,effect_probability_tested=False)
    def eligible(self,tactic_id,*,data_window_bank=None):
        """AD80 full qualifier on current050A/0509; no enemy/range precheck."""
        self._id(tactic_id);actor,target=self._slots();self._sync(data_window_bank);m=self.memory
        m[0x10]=m[0x600+target];m[0x11]=m[0x614+target];tt=self.terrain_at(m[0x10],m[0x11]);m[0x0A]=tt
        m[0x10]=m[0x600+actor];m[0x11]=m[0x614+actor];at=self.terrain_at(m[0x10],m[0x11]);m[0x0B]=at
        return self.eligibility_suffix(tactic_id,tt,at)
    def can_target(self,tactic_id,actor_slot,target_slot,*,data_window_bank=None):
        """Cursor gameplay checks AA03: enemy/range<6, exceptself-ID11.

        Selects current050A/0509/0543; no button/message/AP/effect processing.
        UI menu learnability and affordance are separate preconditions.
        """
        self._id(tactic_id)
        if not 0<=actor_slot<20 or not 0<=target_slot<20:raise ValueError('Original actor/target slots0..19 required')
        m=self.memory;m[0x50A]=actor_slot;m[0x543]=tactic_id
        if tactic_id==11:
            m[0x509]=actor_slot;target_slot=actor_slot
        elif not((m[0x628+target_slot]^m[0x504])&128):
            return dict(status='returned',eligible=False,carry=False,reason='cursor_target_same_side',effect_probability_tested=False)
        else:m[0x509]=target_slot
        distance=grid_distance((m[0x600+actor_slot],m[0x614+actor_slot]),(m[0x600+target_slot],m[0x614+target_slot]))
        if distance>=6:return dict(status='returned',eligible=False,carry=False,reason='cursor_distance_at_least6',distance=distance,effect_probability_tested=False)
        return dict(self.eligible(tactic_id,data_window_bank=data_window_bank),distance=distance)
