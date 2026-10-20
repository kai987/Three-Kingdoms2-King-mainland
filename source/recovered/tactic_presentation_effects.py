"""Sixteen existing effect algorithms with their real presentation bank calls.

The earlier semantic effect layer deliberately excluded mapper IO. These
adapters execute its independent algorithms inside the identified bank windows
and emit the actual protocol, without replaying ROM opcodes or masking missing
services. Contracts cover final game memory and ordered ports, not instruction
cycles or interruption between individual field writes.
"""
from . import battle
from .game_algorithms import PermutationRng
from .tactical_effects import SINGLE_TROOP_DAMAGE
from .tactical_effects_complete import CompleteTacticalEffects
from .tactic_individual_effects import IndividualTactics
from .tactic_area_conversion import AreaConversionTactics
from .officer_transfer import OfficerTransfer,ruler_address

class _Individual(IndividualTactics):
    def __init__(self,memory,data,banked):super().__init__(memory,data);self.banked=banked
    def _troop_phase(self):return self.banked(46,super()._troop_phase)
    def death_settlement(self):
        m=self.memory;actor=m[0x50A];target=m[0x509]
        aa=self._record_address(actor);ta=self._record_address(target)
        a=self._officer(aa);dead=self._officer(ta);actor_id=m[0x664+actor];counter=dead.martial+dead.intelligence
        updated,marker=self.banked(46,lambda:battle.experience_from_accumulated_loss(a,counter));self._write(aa,updated)
        ident=m[0x664+target];m[0x432]=ident
        cache_group=self.banked(40,lambda:self._clear_removed_unit(target))
        return dict(actor_officer_before=actor_id,actor_officer_after=m[0x664+actor],dead_officer=ident,target_slot=target,XP_counter=counter,
                    XP_added=counter>>1,XP_after=updated.experience,level_marker=marker,cleared_cache_group=cache_group,army_counts_or_totals_changed=False)

class _Area(AreaConversionTactics):
    def __init__(self,memory,data,banked,graphics):
        super().__init__(memory,data);self.banked=banked;self.graphics=graphics
    def terrain_at(self,x,y):
        m=self.memory;pointer=m[0xA8]|m[0xA9]<<8
        quadrant=int((x&255)>=16)|2*int((y&255)>=16)
        chunk=m[(pointer+quadrant)&65535]
        self.graphics._far_data(0xA012,0xDB70,chunk)
        # The descriptor was read before E000 changed the data window. Keep
        # that captured chunk even when A8/A9 points into banked ROM.
        if chunk>=120:raise ValueError('Original map chunk domain0..119')
        tile=self.data.map.chunk_tiles[chunk][((y<<4)&255)|(x&15)]
        raw=self.data.map.terrain_classes[tile]if tile<128 else 0
        return raw if raw<6 else 2
    def _damage(self,slot,entry,rng):return self.banked(46,lambda:super(_Area,self)._damage(slot,entry,rng))
    def _conversion(self):
        m=self.memory;slot=m[0x509];account=self.convert_accounting(slot);m[0x628+slot]^=128
        ident=m[0x664+slot];m[0x42C]=ident
        for base in(0x4D8,0x4DC):
            if m[base]==slot:m[base]=255
        m[0x6FA1+slot]=4 if m[0x6FA1+slot]==255 else 255
        low,high=m[0x507]&15,m[0x507]>>4
        new_ruler=high if m[0x628+slot]&128 else low;old_ruler=low if m[0x628+slot]&128 else high
        new_leader=m[ruler_address(new_ruler)];old_leader=m[ruler_address(old_ruler)]
        m[0x30]=new_leader;m[0x31]=ident;m[0x32]=old_leader
        loyalty=self.banked(42,lambda:OfficerTransfer(m,self.data.transfer).loyalty_for_recruitment(new_leader,ident))
        self._set(0x501,m[0x501]+1)
        return dict(accounting=account,slot=slot,new_ruler=new_ruler,new_leader=new_leader,old_leader=old_leader,
                    loyalty=loyalty,city_rosters_changed=False,officer_location_status_changed=False)

class TacticPresentationEffects(CompleteTacticalEffects):
    def __init__(self,memory,data,banked,graphics):
        super().__init__(memory,data);self.banked=banked
        self.individual=_Individual(memory,data.individual,banked)
        self.area_conversion=_Area(memory,data.area_conversion,banked,graphics)
    def _refresh_selectors(self):
        # DB03 first usesF25F/31 before the20 record-cache recalculations.
        self.memory[0xE1]=49;self.memory[0xE000]=49
        return super()._refresh_selectors()
    def level_change_query(self):
        ident=self.memory[0x42C];packed=self.memory[0x63C0+12*ident+11]&240
        if packed==self.memory[0x52C]:return super().level_change_query()
        return self.banked(40,super().level_change_query)
    def dispatch(self):
        tactic=self.memory[0x543]&15
        if tactic not in SINGLE_TROOP_DAMAGE:return super().dispatch()
        if self.individual.pending is not None:raise RuntimeError('Death refresh owns the pending effect')
        m=self.memory
        for address in range(0x42C,0x435):m[address]=0
        m[0x544]=0;actor=m[0x50A];target=m[0x509]
        aa=self._record_address(actor);ta=self._record_address(target);a=self._officer(aa);t=self._officer(ta)
        rng=PermutationRng(self.data.fixed_rng,[m[0x50],0,0,0])
        gate=battle.strategy_gate(a,t,(m[0x600+actor],m[0x614+actor]),(m[0x600+target],m[0x614+target]),m[0x50F],m[0x6F02],rng)
        m[0x12]=[15,10,5,0,251,246][gate.distance]if gate.distance<6 else a.intelligence
        m[0x50]=rng.cursors[0]
        if not gate.passed:
            self._set(0x501,m[0x501]+1);m[0x544]=255
            return dict(status='returned',tactic_id=tactic,success=False,gate=vars(gate))
        amount=battle.strategy_damage_amount(SINGLE_TROOP_DAMAGE[tactic],a,rng)
        a,t,loss,total,marker=self.banked(46,lambda:battle.troop_loss(a,t,amount,0,same_record=aa==ta))
        self._write_officer(ta,t);self._write_officer(aa,a);self._putword(0x42C,total);m[0x42E]=0
        m[0x50]=rng.cursors[0];self._set(0x501,m[0x501]+1)
        return dict(status='returned',tactic_id=tactic,success=True,gate=vars(gate),requested_loss=amount,
                    actual_loss=loss,accumulated_loss=total,level_marker=marker,target_high6_after=m[ta+9]&252,same_record=aa==ta)
