"""Readable tactical proposal consumption, casts and ambush lifecycle.

No instruction IR or original-ROM CPU executor is used. APIs describe precise
game-data windows between real display/audio/readiness dependencies. Methods
named after_* require that actual preceding service, not an invented ack.
"""
from dataclasses import dataclass
import hashlib
from . import battle
from .game_algorithms import PermutationRng
from .tactical_decisions import TacticalData,TacticalDecisions

ROM_SHA256=battle.ROM_SHA256
SUPPORTED_EFFECT_IDS=(0,2,3,4,6,11,13,15)
SINGLE_TROOP_DAMAGE={0:0xb070,3:0xb188,4:0xb1e3,6:0xb070,13:0xb4c6}
DECLARED_RAM_RANGES=((0x12,0x13),(0x20,0x30),(0x50,0x51),(0xa4,0xa5),
                     (0xc2,0xc6),(0x300,0x301),(0x310,0x314),
                     (0x424,0x426),(0x42c,0x435),(0x4c8,0x4c9),
                     (0x4d8,0x4e0),(0x500,0x502),(0x505,0x506),
                     (0x509,0x50c),(0x51a,0x520),(0x52c,0x52d),(0x52e,0x52f),
                     (0x543,0x545),(0x600,0x678))

@dataclass(frozen=True)
class EffectData:
    player_costs:bytes
    ai_costs:bytes
    effect_messages:bytes
    fixed_rng:bytes
    tactical:TacticalData
    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Effects data requires the pinned ROM')
        assert tuple(int.from_bytes(rom[0x19052+2*i:0x19054+2*i],'little')for i in range(16))==battle.TACTIC_ENTRY_POINTS
        return cls(bytes(rom[0x18bd9:0x18be9]),bytes(rom[0x1a054:0x1a064]),
                   bytes(rom[0x1a110:0x1a120]),bytes(rom[0x3e8ca:0x3e9ca]),TacticalData.from_rom(rom))

class _MemoryView:
    def __init__(self,memory):self.memory=memory
    def __len__(self):return 65536
    def __getitem__(self,address):return self.memory[address]
    def __setitem__(self,address,value):self.memory[address]=value

class TacticalEffects:
    """Semantic game effects; CPU registers/stack/mapper are outside the API.

    All SRAM6000..7FFF and DECLARED_RAM_RANGES are comparison windows. Scratch
    20..2F is included only for trigger(), which reuses its exact semantic body;
    other methods intentionally exclude CPU work pointers and arithmetic scratch.
    No rendering callback defaults to a no-op; boundaries are returned as data.
    """
    def __init__(self,memory,data:EffectData):self.memory=memory;self.data=data
    def _set(self,a,v):self.memory[a]=v&255
    def _word(self,a):return self.memory[a]|self.memory[a+1]<<8
    def _putword(self,a,v):self._set(a,v);self._set(a+1,v>>8)
    def _record_address(self,slot):
        if not 0<=slot<20:raise ValueError('Original active slot domain0..19')
        ident=self.memory[0x664+slot]
        if ident>=237:raise ValueError('Original active officer domain0..236')
        return 0x63c0+12*ident
    def _officer(self,address):return battle.Officer(bytes(self.memory[address+i]for i in range(12)))
    def _write_officer(self,address,officer):
        for i,v in enumerate(officer.raw):self.memory[address+i]=v
    def _queue(self,message,job):
        m=self.memory;m[0x311]=message;m[0x310]=job;m[0x312]=m[0x313]=255;m[0x300]=0
    def _boundary(self,pc,service,**extra):return {'status':'dependency','pc':pc,'service':service,**extra}
    def _refresh_selectors(self):
        for slot in range(19,-1,-1):
            if self.memory[0x664+slot]==255:self.memory[0x63c+slot]=255;continue
            address=self._record_address(slot);troops=self.memory[address+8]|(self.memory[address+9]&3)<<8
            self.memory[0x63c+slot]=troops//100
    def ambush_eligible(self,terrain_class):
        """Player AF73..AFA0 gate: raw word>=100, class0, own cache empty."""
        address=self._record_address(self.memory[0x50a]);group=4 if self.memory[0x504]&128 else 0
        return (terrain_class&255)==0 and self._word(address+8)>=100 and self.memory[0x4d8+group]==255
    def deploy(self):
        """Complete B42A..B465. Raw16 minus100 wraps; no AP debit here."""
        m=self.memory;actor=m[0x50a];address=self._record_address(actor);group=4 if m[0x504]&128 else 0
        m[0x4d9+group]=m[0x600+actor];m[0x4da+group]=m[0x614+actor]
        m[0x4db+group]=5;m[0x4d8+group]=actor
        before=self._word(address+8);self._putword(address+8,before-100);self._set(0x501,m[0x501]+1)
        return {'status':'returned','tactic_id':11,'cache_group':group,'troops_raw_before':before,
                'troops_raw_after':self._word(address+8),'troops_cost':100,'ap_debited':0,'ttl':5}
    def dispatch(self):
        """B02B reset and independently recovered single-target effect bodies.

        Remaining IDs stop at their real effect entry after the reset. They are
        not silently successful. Alias actor/target IDs share the same record.
        """
        m=self.memory
        for a in range(0x42c,0x435):m[a]=0
        m[0x544]=0;tactic=m[0x543]&15
        if tactic==11:return self.deploy()
        if tactic not in SUPPORTED_EFFECT_IDS:return self._boundary(battle.TACTIC_ENTRY_POINTS[tactic],'unrecovered_effect_body',tactic_id=tactic)
        actor=m[0x50a];target=m[0x509];aa=self._record_address(actor);ta=self._record_address(target)
        a=self._officer(aa);t=self._officer(ta);rng=PermutationRng(self.data.fixed_rng,[m[0x50],0,0,0])
        gate=battle.strategy_gate(a,t,(m[0x600+actor],m[0x614+actor]),(m[0x600+target],m[0x614+target]),m[0x50f],m[0x6f02],rng)
        # B7E4 first stores actor IQ in the shared0012 scratch; B812
        # replaces it by the distance table byte only when distance<6.
        m[0x12]=[15,10,5,0,251,246][gate.distance]if gate.distance<6 else a.intelligence
        m[0x50]=rng.cursors[0]
        if not gate.passed:
            self._set(0x501,m[0x501]+1);m[0x544]=255
            return {'status':'returned','tactic_id':tactic,'success':False,'gate':vars(gate)}
        details={}
        if tactic in SINGLE_TROOP_DAMAGE:
            amount=battle.strategy_damage_amount(SINGLE_TROOP_DAMAGE[tactic],a,rng)
            a,t,loss,total,marker=battle.troop_loss(a,t,amount,0,same_record=aa==ta)
            self._write_officer(ta,t);self._write_officer(aa,a);self._putword(0x42c,total);m[0x42e]=0
            details.update(requested_loss=amount,actual_loss=loss,accumulated_loss=total,level_marker=marker,
                           target_high6_after=m[ta+9]&252,same_record=aa==ta)
        elif tactic==2:m[0x650+target]=3 if m[0x504]&128 else 2
        elif tactic==15:
            duration=((rng.next_u8()&3)+5)<<4
            m[0x650+target]=(duration+(16 if m[0x504]&128 else 0))&255
        m[0x50]=rng.cursors[0];self._set(0x501,m[0x501]+1)
        return {'status':'returned','tactic_id':tactic,'success':True,'gate':vars(gate),**details}
    def prepare(self):
        """C004 prefix; ID11 bypasses ordinary AP debit and target summary."""
        m=self.memory;tactic=m[0x6f8d]
        if tactic>=16:raise ValueError('Original AI proposal tactic domain0..15')
        if tactic==11:
            m[0x543]=tactic;m[0x509]=m[0x50a]=m[0x6f8c]
            effect=self.dispatch();self._refresh_selectors();m[0x12]=1
            return self._boundary(0xc1c8,'D6CC unit graphics',effect=effect,ap_debited=0,resume='finish_ambush_after_first_graphics')
        m[0x509]=m[0x6f8e]
        return self._boundary(0xc016,'bank29 A027 target summary',resume='prepare_after_portrait')
    def prepare_after_portrait(self):
        """C01B..C03B; preceding real target summary is caller-owned."""
        m=self.memory;tactic=m[0x6f8d]
        if tactic>=16:raise ValueError('Original AI proposal tactic domain0..15')
        cost=self.data.ai_costs[tactic];self._set(0x505,m[0x505]-cost)
        m[0x42c]=tactic;m[0x42d]=m[0x42e]=0;self._queue(0xa1,2)
        return self._boundary(0xc03d,'E69B audio request65',ap_cost=cost,resume='advance_after_audio')
    def advance_after_audio(self):
        """C040..C043 after the real audio-request service returned."""
        self._set(0x501,self.memory[0x501]+1);return {'status':'returned'}
    def cast_after_portrait(self):
        """C083..C0A7 after real DC36 target drawing. Stop before D6CC."""
        m=self.memory;m[0x543]=m[0x6f8d];m[0x50a]=m[0x6f8c];m[0x509]=m[0x6f8e]
        if not 0<=m[0x509]<20:raise ValueError('Active target slot0..19')
        m[0x650+m[0x509]]=0;effect=self.dispatch()
        if effect['status']!='returned':return effect
        self._refresh_selectors();m[0x12]=1
        return self._boundary(0xc0a7,'D6CC unit graphics',effect=effect,resume='finish_after_graphics')
    def finish_after_graphics(self):
        """C0AA..C0FD exact result-message queue; no completion is claimed."""
        m=self.memory;m[0x501]=11
        if m[0x544]:m[0xa4]=3;message,job=0xa2,2
        else:
            m[0xa4]=4;tactic=m[0x543]&15
            if tactic==8:message,job=0xb7,5
            else:
                selected=tactic
                if tactic==9 and not self._word(0x42c):selected=1
                if selected in [1,9]and m[0x432]!=255:
                    m[0x42c]=m[0x432];m[0x501]=15;message,job=0x4e,5
                else:message,job=self.data.effect_messages[selected],2
        self._queue(message,job);return {'status':'returned','message_request':message,'job':job,'message_completed':False}
    def queue_player_animation_after_confirmation(self):
        """AA3F..AA6B after actual text/input confirmation; queue only."""
        m=self.memory;self._set(0x501,m[0x501]+1)
        m[0xc3]=0x89;m[0xc4]=0x8a;m[0xc5]=m[0xc2]=0x88
        if not 0<=m[0x509]<20:raise ValueError('Active target slot0..19')
        m[0x650+m[0x509]]=0;self._set(0x4c8,m[0x543]+1);m[0x310]=5;m[0x300]=0
        return {'status':'returned','animation_requested':True,'animation_completed':False}
    def player_cast_after_animation(self):
        """AA6C..AAA6: wait for real04C8==0, charge player cost and cast."""
        m=self.memory
        if m[0x4c8]:return {'status':'waiting','flag_address':0x4c8,'flag_value':m[0x4c8]}
        tactic=m[0x543]
        if tactic>=16:raise ValueError('Player selected tactic domain0..15')
        a=self._record_address(m[0x50a]);m[0x52c]=m[a+11]&240;m[0x52e]=m[a+1]
        cost=self.data.player_costs[tactic];self._set(0x505,m[0x505]-cost);effect=self.dispatch()
        if effect['status']!='returned':return effect
        self._refresh_selectors();m[0x50b]=0
        return {'status':'returned','ap_cost':cost,'effect':effect}
    def finish_ambush_after_first_graphics(self):
        """C1CB -> A1F7 prefix after first actual D6CC returned."""
        self._queue(5,5);self.memory[0x12]=1
        return self._boundary(0xa200,'D6CC cursor graphics',resume='finish_ambush_after_second_graphics')
    def finish_ambush_after_second_graphics(self):
        """A203..A20B then C1F0..C1FB, after second actual D6CC."""
        m=self.memory;m[0x424]=m[0x425]=m[0x500]=m[0x501]=m[0xa4]=0;return {'status':'returned'}
    def tick_expiry(self):
        """Bank9 CE20..CE3F, once per original side0->128 round hook.

        FF skips. Byte0 underflows toFF and does not clear the cached slot;
        only1->0 clears its slot. XY and the expired TTL itself remain stored.
        """
        events=[];m=self.memory
        for group in [0,4]:
            before=m[0x4db+group]
            if before==255:continue
            after=(before-1)&255;m[0x4db+group]=after
            if after==0:m[0x4d8+group]=255
            events.append({'group':group,'before':before,'after':after,'slot_cleared':after==0})
        return {'status':'returned','events':events,'real_time_advanced':False}
    def clear_cached_slot(self,slot,*,full_record=False):
        """B343/C82C/BC5E clear both references; D6E7 clears first whole row."""
        if not 0<=slot<20:raise ValueError('Active slot0..19')
        m=self.memory;groups=[]
        for group in [0,4]:
            if m[0x4d8+group]!=slot:continue
            groups.append(group)
            if full_record:
                for i in range(4):m[0x4d8+group+i]=255
                break
            m[0x4d8+group]=255
        return {'status':'returned','cleared_groups':groups,'whole_record':full_record}
    def remove_unit(self,slot):
        """Bank9 D6CD..D70E unit arrays/strategy and first matching cache row."""
        if not 0<=slot<20:raise ValueError('Active slot0..19')
        for base in [0x600,0x614,0x628,0x63c,0x650,0x664,0x6fa1]:self.memory[base+slot]=255
        return self.clear_cached_slot(slot,full_record=True)
    def detach_unit_accounting(self,slot=None):
        """Complete bank13 C91E..C98B, before BC2D city-roster commit.

        Side comes from0628[slot], not active0504. Decrement the side's byte
        count modulo256; subtract masked10-bit troops from its raw16 total
        with saturation. Officer/roster/cache/AP data is untouched here.
        An explicit slot selects the already validated caller input; it does
        not itself rewrite the UI's0509 selection field.
        """
        m=self.memory;slot=m[0x509]if slot is None else slot;address=self._record_address(slot)
        high=bool(m[0x628+slot]&128);counter=0x51f if high else 0x51e;total_address=0x51c if high else 0x51a
        count_before=m[counter];self._set(counter,count_before-1)
        troops=m[address+8]|(m[address+9]&3)<<8;before=self._word(total_address);remaining=max(0,before-troops)
        self._putword(total_address,remaining)
        return {'status':'returned','slot':slot,'side_sign':128 if high else 0,'masked_troops':troops,
                'count_before':count_before,'count_after':m[counter],'total_before':before,'total_after':remaining,
                'city_roster_commit_performed':False}
    def request_secondary_after_move(self):
        """A51F..A534, no forced FF/ack: request B933 for moved0509."""
        m=self.memory
        if m[0x6f8b]!=255:return {'status':'waiting','request':m[0x6f8b]}
        m[0x6f8b]=1;m[0x6f8c]=m[0x509];self._set(0x501,m[0x501]+1);return {'status':'returned','request':1}
    def trigger(self):
        """Complete bank8 B933 gameplay contract; no battle UI progression."""
        return TacticalDecisions(_MemoryView(self.memory),self.data.tactical).secondary_effect()
    def consume_secondary(self):
        """A535..A5BB game-data/experience suffix up to real portrait call."""
        m=self.memory
        if m[0x6f8b]!=255:return {'status':'waiting','request':m[0x6f8b]}
        if m[0x6f8f]!=0:
            m[0x500]=m[0x501]=0;self._queue(5,5);m[0x12]=1
            return self._boundary(0xa200,'D6CC cursor graphics',resume='finish_cursor_reset_after_graphics')
        self._set(0x501,m[0x501]+1);group=0 if m[0x504]&128 else 4;slot=m[0x4d8+group]
        address=self._record_address(slot);record=self._officer(address)
        m[0x52c]=record.raw[11]&240;m[0x52e]=record.raw[1]
        updated,marker=battle.experience_from_accumulated_loss(record,self._word(0x42c));self._write_officer(address,updated)
        self._refresh_selectors();m[0x50a]=m[0x509]
        if m[0x6fa1+m[0x6f8c]]!=255:m[0x509]=slot;m[0xa4]=4;message=0xb9
        else:m[0xa4]=3;m[0x52e]=0;message=0xb8
        self._queue(message,2)
        return self._boundary(0xa5bb,'bank29 A027 unit portrait',level_marker=marker,resume='finish_secondary_after_portrait')
    def finish_secondary_after_portrait(self):
        """A5C0..A5CD after actual portrait call; swap actor/target fields."""
        m=self.memory;old=m[0x509];m[0x509]=m[0x50a];m[0x50a]=old;return {'status':'returned'}
    def clear_triggered_cache_after_confirmation(self):
        """A5EA..A606 after actual draw, text-idle and confirm input.

        Clearing happens at confirmation, not immediately on B933's damage.
        The real level-change popup/scene effect remains an explicit boundary.
        """
        m=self.memory;group=0 if m[0x504]&128 else 4;m[0x4d8+group]=255
        if not m[0x52e]:
            m[0x500]=m[0x501]=0;self._queue(5,5);m[0x12]=1
            return self._boundary(0xa200,'D6CC cursor graphics',resume='finish_cursor_reset_after_graphics')
        ident=m[0x664+m[0x50a]];m[0x42c]=ident
        return self._boundary(0xa606,'DEE9 real level-change query and popup',cache_slot_cleared=True)
    def finish_cursor_reset_after_graphics(self):
        self.memory[0x424]=self.memory[0x425]=0;return {'status':'returned'}
