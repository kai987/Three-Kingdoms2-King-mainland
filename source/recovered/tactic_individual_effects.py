"""Independent trap, fire-arrow and rockfall effects from original6502 behavior.

These are reconstructed gameplay algorithms, not original game source. Death
stops at the real D6CC map-refresh dependency and requires an explicit resume
once that service has run. No IR/ROM executor, rendering no-op or automatic
readiness acknowledgement is used. Caller must have actually reset B02B's
result region before apply(). CPU scratch/register/mapper effects are excluded.
"""
from dataclasses import dataclass
import hashlib
from . import battle
from .game_algorithms import PermutationRng

ROM_SHA256=battle.ROM_SHA256
SUPPORTED_IDS=(1,5,9)
EFFECT_ENTRIES={1:0xB0DD,5:0xB243,9:0xB3B6}
DECLARED_RAM_RANGES=((0x12,0x13),(0x50,0x51),(0x42C,0x435),(0x4D8,0x4E0),(0x500,0x502),(0x51A,0x526),(0x600,0x678))

@dataclass(frozen=True)
class IndividualData:
    fixed_rng:bytes
    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Individual effects require the pinned original ROM')
        return cls(bytes(rom[0x3E8CA:0x3E9CA]))

class IndividualTactics:
    def __init__(self,memory,data:IndividualData):
        self.memory=memory;self.data=data;self.pending=None
    def _set(self,address,value):self.memory[address]=value&255
    def _word(self,address):return self.memory[address]|self.memory[address+1]<<8
    def _putword(self,address,value):self._set(address,value);self._set(address+1,value>>8)
    def _record_address(self,slot,*,allow_internal_removed=False):
        if not 0<=slot<20:raise ValueError('Original active slot0..19 required')
        ident=self.memory[0x664+slot]
        if ident>=237 and not(allow_internal_removed and ident==255):raise ValueError('Initial selected officer0..236 required')
        return 0x63C0+12*ident
    def _officer(self,address):return battle.Officer(bytes(self.memory[address+i]for i in range(12)))
    def _write(self,address,record):
        for i,value in enumerate(record.raw):self.memory[address+i]=value
    def _rng(self):return PermutationRng(self.data.fixed_rng,[self.memory[0x50],0,0,0])
    def _save_rng(self,rng):self.memory[0x50]=rng.cursors[0]
    def _increment_sub(self):self._set(0x501,self.memory[0x501]+1)
    def _boundary(self,**extra):
        return dict(status='dependency',pc=0xB615,service='bank13 D6CC real map refresh',resume='after_death_graphics',pending=dict(self.pending),**extra)

    def _gate(self,rng):
        m=self.memory;actor=m[0x50A];target=m[0x509]
        aa=self._record_address(actor);ta=self._record_address(target)
        a=self._officer(aa);t=self._officer(ta)
        result=battle.strategy_gate(a,t,(m[0x600+actor],m[0x614+actor]),(m[0x600+target],m[0x614+target]),m[0x50F],m[0x6F02],rng)
        # Original B7E4 storesactorIQ in12; B812 replaces it only inrange.
        m[0x12]=[15,10,5,0,251,246][result.distance]if result.distance<6 else a.intelligence
        self._save_rng(rng);return result

    def grain_loss(self,requested_loss,*,side_offset):
        """Complete B6F0: saturating raw16 oppositearmy grain and report.

        side_offset is the originalY0/2 argument, not selected targetside.
        Does not award experience or alter the target's officer troops.
        """
        if side_offset not in(0,2):raise ValueError('Original grain side offset0/2 required')
        address=0x522+side_offset;before=self._word(address);applied=min(before,requested_loss&65535)
        self._putword(address,before-applied);self._putword(0x12,before-applied);self._putword(0x42C,applied);self.memory[0x42E]=0
        return dict(status='returned',requested_loss=requested_loss&65535,actual_grain_loss=applied,grain_before=before,grain_after=before-applied,side_offset=side_offset)

    def health_loss(self,requested_loss,*,continuation='health_helper'):
        """B5D8 complete alive branch or death prefix before realD6CC.

        ZeroHP, including preexistingzeroHP withzero loss, setsrecord11|3.
        Deathreport initiallyFF until postgraphics XP/removal suffix runs.
        """
        if continuation not in('health_helper','trap','rockfall'):raise ValueError('Unknown HP continuation')
        if self.pending is not None:raise RuntimeError('A death graphics dependency is still pending')
        m=self.memory;slot=m[0x509];address=self._record_address(slot)
        record,loss,dead=battle.health_loss_core(self._officer(address),requested_loss)
        self._write(address,record);m[0x42F]=loss;m[0x430]=m[0x431]=0;m[0x432]=255
        details=dict(requested_HP_loss=requested_loss&255,actual_HP_loss=loss,HP_after=record.health,dead=dead)
        if dead:
            m[0x12]=0
            self.pending=dict(continuation=continuation,target_slot=slot,target_officer_before=m[0x664+slot],**details)
            return self._boundary(**details)
        return dict(status='returned',**details)

    def _clear_removed_unit(self,slot):
        """bank8A02A→bank9D6CD: six arrays, strategy, first wholecache row.

        No C91E armycount/total accounting is called in this death path.
        A duplicate cachedslot in the second row is retained after firstmatch.
        """
        m=self.memory
        for base in(0x600,0x614,0x628,0x63C,0x650,0x664,0x6FA1):m[base+slot]=255
        for group in(0,4):
            if m[0x4D8+group]==slot:
                for i in range(4):m[0x4D8+group+i]=255
                return group
        return None

    def death_settlement(self):
        """Complete B618..B642 after the real map-refresh service returned.

        far14A009→bank15D8B0 awards caster floor((dead武+dead知)/2),
        preserving the full16 sumcarry, normalwrap/cap/singlelevel advancement.
        Then report0432=deadID and remove only the targetslot/cache reference.
        Political city/ruler removal and C91E accounting do not occur here.
        """
        m=self.memory;actor=m[0x50A];target=m[0x509]
        aa=self._record_address(actor);ta=self._record_address(target)
        a=self._officer(aa);dead=self._officer(ta);actor_id=m[0x664+actor];counter=dead.martial+dead.intelligence
        updated,marker=battle.experience_from_accumulated_loss(a,counter);self._write(aa,updated)
        ident=m[0x664+target];m[0x432]=ident;cache_group=self._clear_removed_unit(target)
        return dict(actor_officer_before=actor_id,actor_officer_after=m[0x664+actor],dead_officer=ident,target_slot=target,XP_counter=counter,
                    XP_added=counter>>1,XP_after=updated.experience,level_marker=marker,cleared_cache_group=cache_group,
                    army_counts_or_totals_changed=False)

    def _troop_phase(self):
        """Complete B188..B1D4, afterrockfall's HP phase if called fromID9.

        A lethal HP phase already clears0664[target]. OriginalF2D7(FF)
        consequently addresses6FB4 in AIwork SRAM. This intentional internal
        path is preserved; it must not be replaced with the old officerID.
        Alias slots/records and casterstat changes fromkillXP remain live.
        """
        m=self.memory;actor=m[0x50A];target=m[0x509]
        aa=self._record_address(actor,allow_internal_removed=True);ta=self._record_address(target,allow_internal_removed=True)
        a=self._officer(aa);t=self._officer(ta);rng=self._rng()
        amount=battle.strategy_damage_amount(0xB188,a,rng);self._save_rng(rng)
        updated_a,updated_t,loss,total,marker=battle.troop_loss(a,t,amount,self._word(0x42C),same_record=aa==ta)
        self._write(ta,updated_t);self._write(aa,updated_a);self._putword(0x42C,total);m[0x42E]=0;self._increment_sub()
        return dict(requested_troop_loss=amount,actual_troop_loss=loss,report_accumulated=total,level_marker=marker,
                    target_address=ta,actor_address=aa,internal_FF_record=ta==0x6FB4 or aa==0x6FB4)

    def _finish_HP_phase(self,continuation,details):
        if continuation=='health_helper':return dict(status='returned',health=details)
        self._increment_sub()
        if continuation=='trap':return dict(status='returned',tactic_id=1,health=details)
        if continuation=='rockfall':
            troops=self._troop_phase();self.memory[0x501]=7
            return dict(status='returned',tactic_id=9,health=details,troops=troops)
        raise ValueError('Unknown HP continuation')

    def after_death_graphics(self,*,map_refresh_returned):
        """Resume after actualD6CC; missing/false signal never settlesdeath; no asyncjob is acknowledged."""
        if self.pending is None:raise RuntimeError('No death map-refresh continuation exists')
        if map_refresh_returned is not True:return self._boundary()
        pending=dict(self.pending);settlement=self.death_settlement();self.pending=None
        result=self._finish_HP_phase(pending['continuation'],pending)
        result['death_settlement']=settlement
        if pending['continuation']!='health_helper':result['success']=True
        return result

    def apply(self,tactic_id):
        """Effectbody1/5/9 after actualB02B reset, with strict deathboundary.

        Gatefailure returns originalRTS withsub++/0544FF. Alive effects return
        completeRTS; fatalHP stops beforeD6CC and needs after_death_graphics.
        Successful fire-arrow reduces opposite0504 grainword; it never modifies
        targettroops/HP or awardsXP. CastAP and renderer preparation are outside.
        """
        if tactic_id not in SUPPORTED_IDS:raise ValueError('This module only recovers tacticIDs1/5/9')
        if self.pending is not None:raise RuntimeError('Resolve existing death graphics dependency first')
        m=self.memory;rng=self._rng();gate=self._gate(rng)
        if not gate.passed:
            self._increment_sub();m[0x544]=255
            return dict(status='returned',tactic_id=tactic_id,success=False,gate=vars(gate))
        actor=m[0x50A];a=self._officer(self._record_address(actor))
        if tactic_id==5:
            factor=rng.bounded(5)+10;side=0 if m[0x504]&128 else 2
            amount=self._word(0x522+side)*factor//100+a.intelligence//5
            self._save_rng(rng);grain=self.grain_loss(amount,side_offset=side);self._increment_sub()
            return dict(status='returned',tactic_id=5,success=True,gate=vars(gate),grain=grain,factor_percent=factor)
        amount=battle.strategy_damage_amount(0xB0EB,a,rng);self._save_rng(rng)
        health=self.health_loss(amount,continuation='trap'if tactic_id==1 else'rockfall')
        if health['status']=='dependency':return dict(health,tactic_id=tactic_id,success=True,gate=vars(gate))
        result=self._finish_HP_phase('trap'if tactic_id==1 else'rockfall',health)
        result.update(success=True,gate=vars(gate));return result
