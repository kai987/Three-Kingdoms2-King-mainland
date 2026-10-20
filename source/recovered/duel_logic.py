"""Independent high-level single-combat rules recovered from this ROM.

No instruction IR, original-code adapter, display no-op, or guessed rules are
used here. These functions reproduce declared game-memory and RNG effects;
CPU flags/stack/pointer scratch, mapper writes, graphics and audio are outside
their contract. Returned dialogue requests are pending work, not rendered text.
Numeric action/result IDs stay separate from officer-record status bits.
"""
from dataclasses import dataclass
import hashlib

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
STATE,SUBSTATE,ACTOR=0x04A8,0x04A9,0x04AA
# Exact main-menu and tactical-submenu glyphs/selection IDs, verified against
# the original core NMT/CHR records and real selection-store instructions.
ACTION_NAMES={0:'けんせい',1:'たいきゃく',2:'こうげき',3:'こうさん',
              4:'せんじゅつ',5:'データ',6:'すてみのこうげき',7:'せっとく',8:'ばとう'}


def u8(value):return value&255
def signed_clamp(value):
    value&=255
    return 0 if value&128 else value


@dataclass(frozen=True)
class DuelTables:
    rng:bytes
    template_prg:bytes
    fallback_actions:bytes
    negotiation_results:bytes

    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Wrong ROM')
        return cls(bytes(rom[0x3E8CA:0x3E9CA]),bytes(rom[16+17*8192:16+18*8192]),
                   bytes(rom[0x2F770:0x2F7B8]),bytes(rom[0x2FFC2:0x3009A]))

    def __post_init__(self):
        if tuple(map(len,(self.rng,self.template_prg,self.fallback_actions,self.negotiation_results)))!=(256,8192,72,216):
            raise ValueError('Expected exact ROM data-table extents')


class DuelLogic:
    """Game-memory rules over a shared 64KiB CPU address space.

    Actor must be0/1. Unusual byte inputs, aliased officer IDs, byte wrap and the
    original AI's HP-derived array index are deliberately retained. Public
    method addresses/verification scope are recorded in the phase4 analysis.
    """
    def __init__(self,memory,tables):
        self.memory,self.tables=memory,tables
        self.draws=[]

    def side(self):
        side=self.memory[ACTOR]
        if side not in (0,1):raise ValueError('Duel actor must be0 or1')
        return side

    def record_address(self,side):return 0x63C0+12*self.memory[0x04AD+side]
    def field(self,side,offset):return self.memory[self.record_address(side)+offset]
    def leader_ids(self):return tuple(self.memory[0x6F07+8*i] for i in range(7))
    def is_ruler(self,side=None):
        """Bank24 D262: compare selected officer ID to seven ruler records."""
        side=self.side() if side is None else side
        return self.memory[0x04AD+side] in self.leader_ids()

    def sample(self,mask=255,bound=None):
        """Fixed E87A family: exact cursor0 consumption/rejection, game scope."""
        while True:
            cursor=self.memory[0x50];raw=self.tables.rng[cursor]
            self.memory[0x50]=(cursor+1)&255
            value=raw&mask
            self.draws.append({'cursor':cursor,'raw':raw,'sample':value,'mask':mask,'bound':bound})
            if bound is None or value<bound:return value

    def threshold(self,entry):
        """The four real AI comparison formulas, preserving SBC/BPL wrap."""
        side=self.side();other=side^1
        if entry==0xB7DD:
            return signed_clamp(124-u8(self.memory[0x04B1+side]+max(self.field(side,1),self.field(side,2))))
        if entry==0xB816:
            return signed_clamp(50-signed_clamp(self.field(side,1)-self.field(other,1)))
        if entry==0xB851:
            return signed_clamp(u8(self.field(side,2)+self.field(side,4))-u8(self.field(other,3)+self.field(side,1)))
        if entry==0xB89B:
            return signed_clamp(max(self.field(other,1)-self.field(other,2),0)+10)
        raise ValueError(f'Unknown AI formula {entry:04X}')

    def _choose(self,category,reason):
        self.memory[0x04BF]=category;self.memory[STATE]=1;self.memory[SUBSTATE]=3
        return {'selected':category,'reason':reason,'next_state':1,'next_substate':3}

    def ai_step(self):
        """One complete state2/sub0..4 game-rule handler, no external hooks.

        B7B3 returns the SRAM pointer's high byte, not a random probability.
        B666 XORs the loaded actor HP with1 for its indexed read; it does NOT
        XOR the actor index. Both surprising original behaviors are preserved.
        """
        m=self.memory;side=self.side();other=side^1;sub=m[SUBSTATE]
        own_hp=m[0x04B1+side];other_hp=m[0x04B1+other]
        if sub==0:
            original_half=self.tables.template_prg[12*m[0x04AD+side]]>>1
            if own_hp>=original_half:
                m[SUBSTATE]=u8(sub+2)
                return {'selected':None,'reason':'skip_low_hp_checks','original_half':original_half}
            if own_hp<other_hp and not self.is_ruler():
                pointer_high=self.record_address(side)>>8
                if pointer_high<own_hp and own_hp!=0:
                    return self._choose(3,'B7B3_pointer_high_comparison')
            m[SUBSTATE]=u8(sub+1)
            return {'selected':None,'reason':'low_hp_check_not_selected','original_half':original_half}
        if sub==1:
            if u8(own_hp+30)<other_hp:
                threshold=self.threshold(0xB7DD);roll=self.sample(bound=100)
                if roll<threshold and threshold!=0:return self._choose(6,'B7DD_gate')
            m[SUBSTATE]=u8(sub+1);return {'selected':None,'reason':'category6_not_selected'}
        if sub==2:
            # Preserve the real register-derived read, including outside-pair bytes.
            indexed_hp=m[0x04B1+(own_hp^1)] if own_hp<30 else None
            if own_hp<30 and indexed_hp>=50:
                threshold=self.threshold(0xB816);roll=self.sample(bound=100)
                if roll<threshold and threshold!=0:return self._choose(2,'B816_gate')
            m[SUBSTATE]=u8(sub+1)
            return {'selected':None,'reason':'category2_not_selected','hp_derived_read':indexed_hp}
        if sub==3:
            if not m[0x04B5+side]&127:
                if self.field(other,2)<self.field(side,2):
                    threshold=self.threshold(0xB851);roll=self.sample(bound=100)
                    if roll<threshold and threshold!=0:return self._choose(7,'B851_gate')
                if self.field(other,1)>=self.field(side,1):
                    threshold=self.threshold(0xB89B);roll=self.sample(bound=100)
                    if roll<threshold and not m[0x04B5+side]&128 and not m[0x04B5+other]&127:
                        return self._choose(8,'B89B_gate_and_status_flags')
            m[SUBSTATE]=u8(sub+1);return {'selected':None,'reason':'tactical_actions_not_selected'}
        if sub==4:
            other_bucket=0 if other_hp<31 else 1 if other_hp<61 else 2
            own_bucket=0 if own_hp<31 else 1 if own_hp<61 else 2
            index=24*other_bucket+8*own_bucket+self.sample(mask=7)
            return self._choose(self.tables.fallback_actions[index],'B760_hp_weighted_table')
        raise ValueError(f'Invalid AI substate{sub}')

    def choose_ai_action(self):
        """Advance the real five-stage AI until it returns state1/sub3."""
        steps=[]
        for _ in range(5):
            result=self.ai_step();steps.append(result)
            if result['selected'] is not None:return {'category':result['selected'],'steps':steps,'draws':list(self.draws)}
        raise RuntimeError('AI did not select within its five proven stages')

    def advance_turn(self):
        """B361..B3C3 game effects: selection/reseed and effect duration decay.

        On a nonzero low7 duration the bit7 marker is cleared by the real AND/
        SBC/store. A pure80 marker persists. Player portrait/dialogue requests
        remain explicit pending work; CPU/display-helper side effects excluded.
        """
        m=self.memory;side=self.side()
        if m[0x04C0]==0:m[ACTOR]=side^1
        m[0x04C0]=u8(m[0x04C0]+1)
        if m[0x04C0]>=3:
            for i in (0,1):m[0x04BD+i]=u8(m[0x04B3+i]+self.sample(mask=15,bound=11))
            m[ACTOR]=1 if m[0x04BD]>=m[0x04BE] else 0
            m[0x04C0]=1
        m[ACTOR]^=1;side=m[ACTOR]
        remaining=m[0x04B5+side]&127
        if remaining:m[0x04B5+side]=remaining-1
        if m[0x04AB+side]&128:
            m[STATE]=2
            return {'next':'computer_action','actor':side,'remaining_effect':m[0x04B5+side]}
        m[0x00A4]=2 if m[0x04B5+side]&127 else 0
        m[SUBSTATE]=u8(m[SUBSTATE]+1)
        return {'next':'player_action','actor':side,'remaining_effect':m[0x04B5+side],
                'pending_portrait_id':m[0x04AD+side],'pending_dialogue_id':0x2B}

    def attempt_status_effect(self):
        """C08A..C115: category8 ばとう effect and paired dialogue IDs."""
        m=self.memory;side=self.side();other=side^1
        m[0x04B5+side]=128
        combined=u8(self.field(side,2)+self.field(side,4))
        difference=max(combined-self.field(other,2),0)
        threshold_input=u8(u8(difference+1)+self.sample(mask=15,bound=10))
        succeeded=threshold_input>=110
        if succeeded:
            duration=self.sample(mask=3)
            while duration==0:duration=self.sample(mask=3)
            m[0x04B5+other]=duration+2;m[0x04C3+other]=2
        m[0x04BE]=0x2E if succeeded else 0x2F;m[0x04BD]=0x2D
        m[STATE]=9;m[SUBSTATE]=0;m[0x04BF]=0
        return {'succeeded':succeeded,'threshold_input':threshold_input,
                'target_duration':m[0x04B5+other],'pending_dialogue_ids':[0x2D,m[0x04BE]]}

    def attempt_insult(self):return self.attempt_status_effect()

    def negotiation_choice(self):
        """BE86..BF42: all216 literal outcome weights and their setup effects."""
        m=self.memory;side=self.side();other=side^1
        loyalty,health=self.field(other,3),self.field(other,0)
        capability=u8(self.field(side,2)+self.field(side,4))
        loyalty_bucket=0 if loyalty>=80 else 1 if loyalty>=50 else 2
        health_bucket=0 if health>=80 else 1 if health>=50 else 2
        capability_bucket=0 if capability>=180 else 1 if capability>=130 else 2
        index=24*loyalty_bucket+8*health_bucket+72*capability_bucket+self.sample(mask=7)
        outcome=self.tables.negotiation_results[index]
        m[0x04BF]=outcome;m[0x04BE]=u8(outcome+0x33);m[0x04BD]=u8(outcome+0x2F)
        if outcome<3:m[0x04C3+other]=2
        m[STATE]=9;m[SUBSTATE]=0
        return {'outcome':outcome,'table_index':index,'uses_permanent_hp':True,
                'pending_dialogue_ids':[m[0x04BD],m[0x04BE]]}

    def persuasion_choice(self):return self.negotiation_choice()

    def negotiation_outcome(self,substate,*,queues_finished=None,buttons=None):
        """BF43/BF66/BF7E gameplay cores; caller supplies real completion input."""
        m=self.memory;side=self.side();other=side^1
        if substate==1:
            m[0x0515+2*other]=1;m[0x0515+2*side]=0;m[STATE]=15;m[SUBSTATE]=0
        elif substate==2:
            m[0x0515]=0;m[0x0517]=0;m[STATE]=14;m[SUBSTATE]=0;m[0x04C0]=255
        elif substate==3:
            if queues_finished is None or buttons is None:
                raise TypeError('State7/sub3 requires explicit queues_finished and buttons')
            if not queues_finished or not buttons&3:return {'waiting':True}
            m[0x0515+2*side]=0;m[0x0515+2*other]=4
            m[STATE]=14;m[SUBSTATE]=0;m[0x04C0]=255
        else:raise ValueError('Expected state7 substate1/2/3')
        return {'waiting':False,'result_codes':[m[0x515],m[0x517]],'next_state':m[STATE]}

    def persuasion_outcome(self,substate,**kwargs):return self.negotiation_outcome(substate,**kwargs)

    def finish_action3(self,*,queues_finished,buttons):
        """BE53..BE76 game result writes after action3's real animation/wait."""
        m=self.memory;side=self.side()
        if not queues_finished or not buttons&3:return {'waiting':True}
        m[0x0515+2*side]=3;m[0x0515+2*(side^1)]=0
        m[0x04C0]=128;m[STATE]=14;m[SUBSTATE]=0
        return {'waiting':False,'result_code':3,'result_side':side,'next_state':14}

    def finish_surrender(self,*,queues_finished,buttons):
        """Official menu category3 こうさん, not the category1 retreat path."""
        return self.finish_action3(queues_finished=queues_finished,buttons=buttons)

    def strike(self):
        """B8D3..B9A4 complete temporary-HP game effects for action0/2/6.

        Reuses the independently recovered and verified arithmetic source,
        never a ROM adapter. Permanent HP awaits the confirmation method.
        Nonzero effect low7 raises the numeric roll by20 (usually WORSE hit
        chance) and increases wrapped damage by floor(u8(3*damage)/10).
        """
        from .battle import duel_strike_effect
        logic=self
        class Rng:
            def bounded(self,bound):return logic.sample(mask=15 if bound<15 else 255,bound=bound)
            def next_u8(self):return logic.sample()
        m=self.memory;side=self.side();other=side^1
        original_side=0 if m[0x04AD+side]==m[0x0560] else 1
        result=duel_strike_effect(m[0x04C1+original_side],m[0x0570+original_side],
            m[0x056E+(original_side^1)],m[0x04B1+side],m[0x04B1+other],
            m[0x04B5+side],m[0x04BF],m[0x04C5+side],Rng())
        m[SUBSTATE]=u8(m[SUBSTATE]+1)
        m[0x04B1+side]=result['actor_health'];m[0x04B1+other]=result['target_health']
        if result['reported_damage'] is not None:
            m[0x042C]=result['reported_damage'];m[0x042D]=0;m[0x042E]=0
        return {**result,'pending_dialogue_id':result['message'],
                'category':m[0x04BF],'action_name':ACTION_NAMES.get(m[0x04BF])}

    def commit_confirmed_hp(self,*,queues_finished,buttons):
        """B9A5 game writes after actual dialogue completion/confirmation.

        Health display work remains a real host dependency. Flag007E&4 is set
        to wait for it; this method does not silently mark rendering finished.
        Same-ID writes retain the original side1-last behavior.
        """
        if not queues_finished or not buttons&3:return {'waiting':True}
        from .duel_state_machine import commit_duel_hp
        writes=commit_duel_hp(self.memory)
        self.memory[SUBSTATE]=u8(self.memory[SUBSTATE]+1);self.memory[0x7E]|=4
        return {'waiting':False,'permanent_writes':writes,'pending_health_display':True}

    def check_strike_result(self):
        """B9C8 game writes: wait for display, continue or mark result2."""
        from .duel_state_machine import check_duel_strike_end
        return check_duel_strike_end(self.memory)

    def action1_response_gate(self):
        """BB18..BB3F: random gate before action1 interception/HP loss."""
        m=self.memory;side=self.side()
        threshold=u8(2*m[0x04B3+(side^1)]);roll=self.sample(bound=100)
        skipped_penalty=roll<threshold
        m[SUBSTATE]=9 if skipped_penalty else u8(m[SUBSTATE]+1)
        return {'skipped_penalty':skipped_penalty,'roll':roll,'threshold':threshold,
                'pending_dialogue_id':0x3C if skipped_penalty else 0}

    def action1_hp_penalty(self):
        """BB5B..BB92: directly subtract5..14 from the other permanent record."""
        m=self.memory;other=self.side()^1;address=self.record_address(other)
        loss=self.sample(mask=15,bound=10)+5
        m[address]=signed_clamp(m[address]-loss)
        m[0x042F]=loss;m[0x0430]=0;m[0x0431]=0;m[0x042C]=m[0x04AD+other]
        m[SUBSTATE]=u8(m[SUBSTATE]+1)
        return {'applied_parameter':loss,'target_side':other,'permanent_hp':m[address],'pending_dialogue_id':0x3D}

    def action1_exit_result(self,*,zero_hp=False,incoming_y=0):
        """BBD0..BBFF or BC16..BC3A final numeric result writes.

        For BC16 the new actor0 path retains incoming Y instead of explicitly
        clearing it. Normal callers supply0; unusual Y values are preserved as
        a CPU-addressed write, not silently replaced by an idealized side index.
        """
        m=self.memory;side=self.side();other=side^1
        if zero_hp:
            m[0x042C]=m[0x04AD+other]
            m[0x0515+2*other]=2;m[0x0515+2*side]=0
            m[STATE]=14;m[SUBSTATE]=0;m[0x04C0]=255
            return {'result_code':2,'result_side':other,'next_state':14}
        m[ACTOR]=other;offset=2 if other else incoming_y&255
        m[0x0515+offset]=1;m[0x0515+(offset^2)]=0
        m[STATE]=15;m[SUBSTATE]=0
        return {'result_code':1,'result_side':other,'result_offset':offset,'next_state':15}

    def reward_after_zero_hp(self):
        """C35D..C44E: all special-ID and one-time leader weapon/armor awards."""
        m=self.memory;offset=m[0x04BD]
        if offset not in (0,2):raise ValueError('Defeated result offset must be0 or2')
        defeated=m[0x0514+offset];winner=m[0x0514+(offset^2)]
        winner_address=0x63C0+12*winner
        item=message=None;armor=False
        if defeated==131:
            if self.sample(bound=100)<30:item,message=6,0x3F
        elif defeated==173:
            if (m[winner_address+11]&0xF0)<0x20:item,message=7,0x40
        elif defeated==182:item,message=5,0x3E
        elif defeated==222:item,message=7,0x42;armor=True
        elif not m[0x6FE1]&1 and defeated in self.leader_ids():
            if self.sample(bound=100)<50:
                m[0x6FE1]|=1;item,message=14,0x41
        if item is None:
            m[SUBSTATE]=1
            return {'awarded':False,'winner_id':winner,'defeated_id':defeated}
        m[0x042C]=winner
        m[winner_address+10]=(m[winner_address+10]&31)|0xE0 if armor else (m[winner_address+10]&0xE0)|item
        m[SUBSTATE]=u8(m[SUBSTATE]+1)
        return {'awarded':True,'winner_id':winner,'defeated_id':defeated,
                'kind':'armor' if armor else 'weapon','item_id':item,'pending_dialogue_id':message}

