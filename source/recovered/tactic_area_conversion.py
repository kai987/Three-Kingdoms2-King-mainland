"""Independent area-tactic and battlefield-conversion game effects.

This uses readable arithmetic/map/loyalty algorithms, never instruction IR or
an original-ROM CPU executor. apply() starts at the selected effect handler;
the B02B result-buffer reset must already have happened in the real caller.
Rendering, confirmation, AP charge and later postbattle ownership are separate.
"""
from dataclasses import dataclass
import hashlib
from . import battle
from .game_algorithms import PermutationRng
from .tactical_decisions import TacticalData
from .officer_transfer import TransferData,OfficerTransfer,ruler_address

ROM_SHA256=battle.ROM_SHA256
SUPPORTED_IDS=(7,8,10,12,14)
ENTRY_POINTS={7:0xb2cd,8:0xb31c,10:0xb3d0,12:0xb466,14:0xb50c}
DECLARED_RAM_RANGES=((0x12,0x13),(0x30,0x33),(0x50,0x51),(0x42c,0x435),
                     (0x4d8,0x4e0),(0x501,0x502),(0x509,0x50a),
                     (0x51a,0x520),(0x628,0x63c),(0x650,0x664),(0x544,0x545))

@dataclass(frozen=True)
class AreaConversionData:
    fixed_rng:bytes
    map:TacticalData
    transfer:TransferData
    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Area effects require the pinned ROM')
        # Conversion actually calls A006, the loyalty-only helper. Calling an
        # imagined city-membership function here would fabricate SRAM changes.
        assert rom[0x193bd:0x193c2]==bytes.fromhex('2007ee06a0')
        assert rom[0x14016:0x14019]==bytes.fromhex('4c3fcf')
        assert rom[0x1175b:0x117db]==rom[0x1bbae:0x1bc2e]
        return cls(bytes(rom[0x3e8ca:0x3e9ca]),TacticalData.from_rom(rom),TransferData.from_rom(rom))

class AreaConversionTactics:
    """Mutates all shared SRAM and the declared gameplay RAM windows.

    CPU flags, stack, mapper and other arithmetic work bytes are outside this
    semantic API. No helper is implemented by executing original instructions.
    """
    def __init__(self,memory,data:AreaConversionData):self.memory=memory;self.data=data
    def _set(self,a,v):self.memory[a]=v&255
    def _word(self,a):return self.memory[a]|self.memory[a+1]<<8
    def _putword(self,a,v):self._set(a,v);self._set(a+1,v>>8)
    def _address(self,slot):
        if not 0<=slot<20:raise ValueError('Original active slot domain0..19')
        ident=self.memory[0x664+slot]
        if ident>=237:raise ValueError('Original officer domain0..236')
        return 0x63c0+12*ident
    def _officer(self,a):return battle.Officer(bytes(self.memory[a+i]for i in range(12)))
    def _write(self,a,record):
        for i,v in enumerate(record.raw):self.memory[a+i]=v
    @staticmethod
    def _ny(y):return (y-1)&255 if y>=16 else y
    def _enemy(self,slot):return bool((self.memory[0x628+slot]^self.memory[0x504])&128)
    def terrain_at(self,x,y):
        """DB46 normalized terrain through the true four loaded map chunks."""
        m=self.memory;x&=255;y&=255;pointer=self._word(0xa8);q=int(x>=16)|2*int(y>=16);chunk=m[(pointer+q)&65535]
        if chunk>=120:raise ValueError('Original map chunk domain0..119')
        tile=self.data.map.chunk_tiles[chunk][((y<<4)&255)|(x&15)]
        raw=self.data.map.terrain_classes[tile]if tile<128 else 0
        return raw if raw<6 else 2
    def _gate(self,rng,conversion=False):
        m=self.memory;actor=m[0x50a];target=m[0x509];a=self._officer(self._address(actor));t=self._officer(self._address(target))
        ax=(m[0x600+actor],m[0x614+actor]);tx=(m[0x600+target],m[0x614+target])
        if conversion:result=battle.conversion_gate(a,t,ax,tx,rng)
        else:
            result=battle.strategy_gate(a,t,ax,tx,m[0x50f],m[0x6f02],rng)
            m[0x12]=[15,10,5,0,251,246][result.distance]if result.distance<6 else a.intelligence
        m[0x50]=rng.cursors[0];return result
    def _damage(self,slot,entry,rng):
        """B070/B1E3/B55C -> B68B, repeated NEW-accumulator XP per hit."""
        m=self.memory;aa=self._address(m[0x50a]);ta=self._address(slot)
        actor=self._officer(aa);target=self._officer(ta)
        requested=battle.strategy_damage_amount(entry,actor,rng)
        actor,target,loss,total,marker=battle.troop_loss(actor,target,requested,self._word(0x42c),same_record=aa==ta)
        self._write(ta,target);self._write(aa,actor);self._putword(0x42c,total);m[0x42e]=0;m[0x50]=rng.cursors[0]
        # B55C returns without INC0501; B070/B1E3 each increment it.
        if entry in [0xb070,0xb1e3]:self._set(0x501,m[0x501]+1)
        return {'slot':slot,'officer_id':m[0x664+slot],'requested_loss':requested,'actual_loss':loss,
                'new_accumulated_loss':total,'level_marker':marker,'same_record':aa==ta}
    def connected_candidates(self,center=None):
        """Complete B8A1 graph: first ascending enemy at each coordinate.

        Breadth-first right/left/down/up expansion, unique slot IDs, normalized
        Y; class5 blocks the first matched slot. Initial center is unconditional.
        No active-officer or friendly check is added beyond the original code.
        """
        m=self.memory;center=m[0x509]if center is None else center
        if not 0<=center<20:raise ValueError('Original center slot0..19')
        queue=[center]
        for i in range(20):m[0x6fc9+i]=255
        m[0x6fc9]=center
        cursor=0
        while cursor<len(queue):
            slot=queue[cursor];x=m[0x600+slot];y=self._ny(m[0x614+slot]);m[0x12]=x
            for nx,ny in [((x+1)&255,y),((x-1)&255,y),(x,(y+1)&255),(x,(y-1)&255)]:
                # B8CE has shared12/13 coordinate scratch; keep12's true
                # final x, even though13/14 are outside this API contract.
                m[0x12]=nx
                found=next((i for i in range(20)if m[0x600+i]==nx and self._ny(m[0x614+i])==ny and self._enemy(i)),None)
                if found is None:continue
                if self.terrain_at(m[0x600+found],m[0x614+found])==5:continue
                if found not in queue:
                    queue.append(found);m[0x6fc9+len(queue)-1]=found
            cursor+=1
        return queue
    def convert_accounting(self,slot=None):
        """C886..C91D before sign flip: byte counts wrap, source total clamps.

        The unit's0628 sign chooses donor; active0504 is irrelevant. Receiver
        raw16 total wraps on addition. Officer troops use the masked10-bit word.
        """
        m=self.memory;slot=m[0x509]if slot is None else slot;address=self._address(slot);old_high=bool(m[0x628+slot]&128)
        donor_total=0x51c if old_high else 0x51a;receiver_total=0x51a if old_high else 0x51c
        donor_count=0x51f if old_high else 0x51e;receiver_count=0x51e if old_high else 0x51f
        troops=m[address+8]|(m[address+9]&3)<<8
        before={'donor_total':self._word(donor_total),'receiver_total':self._word(receiver_total),'donor_count':m[donor_count],'receiver_count':m[receiver_count]}
        self._set(donor_count,m[donor_count]-1);self._putword(donor_total,max(0,before['donor_total']-troops))
        self._set(receiver_count,m[receiver_count]+1);self._putword(receiver_total,before['receiver_total']+troops)
        return {'slot':slot,'donor_side':128 if old_high else 0,'masked_troops':troops,'before':before,
                'after':{'donor_total':self._word(donor_total),'receiver_total':self._word(receiver_total),'donor_count':m[donor_count],'receiver_count':m[receiver_count]}}
    def _conversion(self):
        m=self.memory;slot=m[0x509];account=self.convert_accounting(slot);m[0x628+slot]^=128
        ident=m[0x664+slot];m[0x42c]=ident
        for base in [0x4d8,0x4dc]:
            if m[base]==slot:m[base]=255
        m[0x6fa1+slot]=4 if m[0x6fa1+slot]==255 else 255
        low,high=m[0x507]&15,m[0x507]>>4
        new_ruler=high if m[0x628+slot]&128 else low;old_ruler=low if m[0x628+slot]&128 else high
        new_leader=m[ruler_address(new_ruler)];old_leader=m[ruler_address(old_ruler)]
        m[0x30]=new_leader;m[0x31]=ident;m[0x32]=old_leader
        loyalty=OfficerTransfer(m,self.data.transfer).loyalty_for_recruitment(new_leader,ident)
        self._set(0x501,m[0x501]+1)
        return {'accounting':account,'slot':slot,'new_ruler':new_ruler,'new_leader':new_leader,'old_leader':old_leader,
                'loyalty':loyalty,'city_rosters_changed':False,'officer_location_status_changed':False}
    def _cross_target(self,cx,cy,dx,dy):
        """B67B/B643: raw +/-1, skip row15, highest matching slot wins."""
        m=self.memory;x=(cx+dx)&255;y=(cy+dy)&255
        if y==15:y=16 if cy==14 else 14
        if x>=32 or y>=20:return None
        slot=next((i for i in range(19,-1,-1)if m[0x600+i]==x and m[0x614+i]==y),None)
        # D6B6's no-match Y=FF is rejected by B672 BMI before DC4B.
        if slot is None:return None
        return slot if self._enemy(slot)else None
    def apply(self,tactic_id):
        """Selected7/8/10/12/14 effect body, after actual B02B reset."""
        if tactic_id not in SUPPORTED_IDS:raise ValueError('Five recovered area/conversion tactic IDs only')
        m=self.memory;target=m[0x509];self._address(m[0x50a]);self._address(target)
        rng=PermutationRng(self.data.fixed_rng,[m[0x50],0,0,0]);gate=self._gate(rng,tactic_id==8)
        if not gate.passed:
            self._set(0x501,m[0x501]+1);m[0x544]=255
            return {'status':'returned','tactic_id':tactic_id,'success':False,'gate':vars(gate),'hits':[]}
        if tactic_id==8:return {'status':'returned','tactic_id':8,'success':True,'gate':vars(gate),**self._conversion()}
        hits=[]
        if tactic_id==7:
            hits.append(self._damage(target,0xb070,rng));cx,cy=m[0x600+target],m[0x614+target]
            for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                slot=self._cross_target(cx,cy,dx,dy)
                if slot is not None:
                    m[0x509]=slot;hits.append(self._damage(slot,0xb070,rng));m[0x509]=target
            m[0x501]=7;return {'status':'returned','tactic_id':7,'success':True,'gate':vars(gate),'hits':hits}
        candidates=self.connected_candidates(target)
        for slot in candidates:
            m[0x12]=slot;terrain=self.terrain_at(m[0x600+slot],m[0x614+slot])
            if tactic_id==10:
                if terrain!=3:continue
                sample=rng.bounded(2);m[0x650+slot]=sample+3+bool(m[0x504]&128);hits.append({'slot':slot,'terrain':terrain,'condition':m[0x650+slot],'sample':sample})
            elif tactic_id==12:
                if terrain!=3:continue
                m[0x509]=slot;hits.append(self._damage(slot,0xb1e3,rng));m[0x509]=target
            else:
                if terrain==5:continue
                m[0x509]=slot;hits.append(self._damage(slot,0xb55c,rng));m[0x509]=target
        m[0x50]=rng.cursors[0]
        if tactic_id in [10,12]:m[0x501]=7
        else:self._set(0x501,m[0x501]+1)
        return {'status':'returned','tactic_id':tactic_id,'success':True,'gate':vars(gate),'candidates':candidates,'hits':hits}
