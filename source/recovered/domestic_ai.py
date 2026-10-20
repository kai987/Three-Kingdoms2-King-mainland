"""Reconstructed strategic/domestic rules for this particular ROM.

Pure rules below do not execute original instructions. DomesticAIControl is a
separate lifted IR entry whose outside helpers remain explicit dependencies.
Unconfirmed city fields keep byte-based names until UI/code evidence agrees.
"""
from dataclasses import dataclass
from pathlib import Path
import json

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
ROOT=Path(__file__).resolve().parents[2]
CITY_BASE=0x6000
CITY_STRIDE=32
OFFICER_BASE=0x63C0
OFFICER_STRIDE=12
RULER_BASE=0x6F07
RULER_STRIDE=8
NEIGHBOR_TABLE_FILE=0x21D82
RNG_TABLE_FILE=0x3E8CA

def word(data,address):return data[address]|data[address+1]<<8

def put_word(data,address,value):
    value&=65535;data[address]=value&255;data[address+1]=value>>8

def city_address(city):
    if not 0<=city<30:raise ValueError('Proven city IDs0..29')
    return CITY_BASE+CITY_STRIDE*city

def officer_address(officer):
    if not 0<=officer<237:raise ValueError('Proven officer IDs0..236')
    return OFFICER_BASE+OFFICER_STRIDE*officer

@dataclass(frozen=True)
class CityRecord:
    raw:bytes
    def __post_init__(self):
        if len(self.raw)!=32:raise ValueError('32-byte original city record')
    @property
    def ruler(self):return self.raw[0]&7
    @property
    def flags(self):return self.raw[0]&248
    @property
    def gold(self):return word(self.raw,2)
    @property
    def grain(self):return word(self.raw,4)
    @property
    def field_06(self):return word(self.raw,6)
    @property
    def field_08(self):return word(self.raw,8)
    @property
    def field_12(self):return word(self.raw,12)
    @property
    def field_14(self):return word(self.raw,14)
    @property
    def population_hundreds(self):return self.field_06
    @property
    def displayed_population(self):return self.population_hundreds*100
    @property
    def land(self):return self.field_08
    @property
    def industry(self):return self.field_14
    @property
    def displayed_land(self):return self.land%1000
    @property
    def displayed_industry(self):return self.industry%1000
    @property
    def income_population_hundreds(self):return self.field_06&32767
    @property
    def income_land(self):return self.field_08&1023
    @property
    def income_industry(self):return self.field_14&1023
    @property
    def governance(self):return self.raw[11]
    @property
    def disaster_prevention(self):return self.raw[10]
    @property
    def reserve_troops(self):return self.field_12
    @property
    def treasures(self):return self.raw[16]
    @property
    def roster(self):return tuple(self.raw[17:27])
    @property
    def occupied_prefix_count(self):
        """D307 stops at the first FF; does not count later occupied holes."""
        return next((i for i,value in enumerate(self.roster)if value==255),10)
    @classmethod
    def from_memory(cls,memory,city):
        address=city_address(city);return cls(bytes(memory[address:address+32]))

def city_neighbors(rom,city):
    city_address(city);raw=rom[NEIGHBOR_TABLE_FILE+8*city:NEIGHBOR_TABLE_FILE+8*city+8]
    return tuple(value for value in raw[:next((i for i,v in enumerate(raw)if v&128),8)])

def recruitment_probability(ruler,officer):
    """Bank11 C66F: specific ruler/officer pairs receive90; everyone else10."""
    preferred={4:{109,112,55,183,144},2:{86,99,57,165,156},3:{107,234,235,213,47}}
    return 90 if officer in preferred.get(ruler&255,set())else 10

def choose_governor(roster,loyalties,virtues):
    """C9A5..CA18: loyalty100 wins immediately; else largest u8(loyalty+virtue).

    A tie selects the later slot. Empty FF slots are skipped, including holes.
    Returns ten slots with the selected officer exchanged into slot0.
    """
    if len(roster)!=10:raise ValueError('Original city roster has10 slots')
    chosen=None;best=0;result=list(roster)
    for slot,officer in enumerate(roster):
        if officer==255:continue
        loyalty=loyalties[officer]&255
        if loyalty==100:chosen=slot;break
        score=(loyalty+(virtues[officer]&255))&255
        if score>=best:best=score;chosen=slot
    if chosen is not None and chosen!=0:result[0],result[chosen]=result[chosen],result[0]
    return {'roster':result,'chosen_slot':chosen,'score':best}

def weighted_branch(weights,sample_low4):
    """A19C/D4AD exact low-nibble rejection, then three threshold comparisons.

    A resultNone means the caller must consume another RNG byte. The sampled
    range never expands above15 even when the sum of weights exceeds16.
    """
    if len(weights)!=3:raise ValueError('Three original strategy weights')
    first=weights[0]&255;second=(first+(weights[1]&255))&255
    total=(second+(weights[2]&255))&255;sample=sample_low4&15
    if sample>=total:return None
    return 0 if sample<first else 1 if sample<second else 2

def development_branch(ruler,month,roll_0_to_79,roll_0_to_99):
    """BEC7/BF16 routing: pure decision after city selection, before payment.

    Names are mechanical fields. Their formal UI labels are documented
    separately; branch1/2 strategy names are not inferred from a series guide.
    """
    if not 0<=ruler<7:raise ValueError('Original ruler IDs0..6')
    if not 0<=roll_0_to_79<80 or not 0<=roll_0_to_99<100:raise ValueError('Rejection-sampled RNG domains')
    thresholds=(20,50,40,30,40,60,50)
    if roll_0_to_79>=thresholds[ruler]:return 'officer_or_equipment'
    if roll_0_to_99<40:return 'field_08'if 3<=(month&255)<8 else 'field_14'
    if roll_0_to_99<70:return 'field_06'
    if roll_0_to_99<90:return 'field_10'
    return 'field_11'

def byte_pair_cap(value,increment,mask_high,threshold_high,threshold_low,cap):
    """Original AI development: add16bit, maskhigh, independent byte tests.

    This is intentionally not min(total,cap): a high byte above the threshold
    with low byte below threshold is retained by the original comparisons.
    """
    total=(value+increment)&65535
    low=total&255;high=(total>>8)&mask_high
    if high>=threshold_high and low>=threshold_low:return cap
    return low|high<<8

def apply_development_value(value,increment,kind):
    if kind in('field_08','field_14'):return byte_pair_cap(value,increment,3,3,231,999)
    if kind=='field_06':return byte_pair_cap(value,increment,127,39,16,9999)
    if kind in('field_10','field_11'):return min((value+increment)&255,99)
    raise ValueError('Unknown recovered development field')

def raise_city_field_11(value,increment_threshold_input,kind='small'):
    """C1A7/C1C0: per-development side effect capped100 after u8 addition."""
    threshold=31 if kind=='small'else 3000
    bonus=1+int(increment_threshold_input>=threshold)
    return min((value+bonus)&255,100)

def consume_ai_budget(budget,cost,variant):
    """D12D/D152/D165/D178/D18D preserve subtraction and unwind conditions.

    underflow always stores its wrapped byte. The four helper variants differ
    in zero handling and how many caller return-address bytes they discard.
    """
    budget&=255;cost&=255;left=(budget-cost)&255;borrow=budget<cost
    if variant=='continue_cycle':abort=borrow;discard=2 if abort else 0
    elif variant=='task':abort=borrow or left==0;discard=2 if abort else 0
    elif variant=='nested1':abort=borrow;discard=4 if abort else 0
    elif variant=='nested2':abort=borrow;discard=6 if abort else 0
    elif variant=='nested3':abort=borrow;discard=8 if abort else 0
    else:raise ValueError('Unknown original budget-helper variant')
    return {'remaining':left,'abort_turn':abort,'discard_stack_bytes':discard}

def decay_diplomacy_nibbles(values):
    """Pair25 A209: both nonzero nibbles decrease independently by1."""
    return bytes(((v&15)-int(bool(v&15)))|((((v>>4)&15)-int(bool(v&240)))<<4)for v in values)

def calendar_step(year,month,turn):
    """Pair25 A046..A068: every7 ruler slots increments a zero-based month."""
    turn=((turn&255)+1)&255;year&=255;month&=255;month_changed=turn>=7
    if month_changed:
        turn=0;month=(month+1)&255
        if month>=12:month=0;year=(year+1)&255
    return {'year':year,'month':month,'turn':turn,'month_changed':month_changed}

def tax_rate(field_11):
    value=field_11&127
    return 50 if value<51 else 60 if value<71 else 70 if value<81 else 80 if value<91 else 90 if value<100 else 100

def seasonal_income(raw_city,difficulty,kind):
    """Pair25 A429/A5EE: Aprilgold / Octobergrain, u24 intermediate products.

    Only these original month routes call the annual collection. A540/A582 are
    immediate RTS bytes in this supplied ROM; no upkeep is invented there.
    The income quotient's lowword is added with16bit wrap, then capped9999.
    """
    if len(raw_city)!=32 or not 0<=difficulty<3:raise ValueError('32-byte city and difficulty0..2')
    if kind=='gold':resource,level,divisor=2,14,80
    elif kind=='grain':resource,level,divisor=4,8,60
    else:raise ValueError('Original seasonal outputs gold/grain')
    base=(100,60,60)[difficulty]+((word(raw_city,level)&1023)//(3,3,4)[difficulty])
    population=word(raw_city,6)&32767
    intermediate=((population*base)&0xffffff)//divisor
    income=(((intermediate*tax_rate(raw_city[11]))&0xffffff)//100)&65535
    value=min((word(raw_city,resource)+income)&65535,9999)
    return {'kind':kind,'income_low16':income,'value':value,'population_hundreds':population,'coefficient':base}

def initial_strategy_weights(rom,difficulty,ruler,owned_or_empty_edges,owned_edges_low_count):
    """A043..A0D2 afterA0D3 summary; all table arithmetic wraps to u8."""
    if not 0<=difficulty<3 or not 0<=ruler<7:raise ValueError('Proven difficulty0..2/ruler0..6')
    row=8*difficulty+ruler
    # A133/A14B/A163 are three3×8 tables; A17B etc are3×4 tier corrections.
    def data(cpu):return rom[0x14010+cpu-0xa000]
    ratio=255 if not owned_or_empty_edges else (owned_edges_low_count*100//owned_or_empty_edges)&255
    tier=0 if ratio<31 else 1 if ratio<71 else 2
    correction=4*difficulty+tier
    weights=[(data(cpu+row)+data(adj+correction))&255 for cpu,adj in[(0xa133,0xa17b),(0xa14b,0xa186),(0xa163,0xa191)]]
    return {'weights':weights,'ratio_low_byte':ratio,'tier':tier}

class DomesticRandom:
    """Fixed original permutation, with separate52/54/55 byte cursors."""
    def __init__(self,memory,rom):self.memory=memory;self.table=rom[RNG_TABLE_FILE:RNG_TABLE_FILE+256]
    def next_byte(self,cursor=0x52):
        if cursor not in(0x52,0x54,0x55):raise ValueError('Proven strategic RNG cursors')
        index=self.memory[cursor];self.memory[cursor]=(index+1)&255
        return self.table[index]
    def below(self,limit,low_nibble=False,cursor=0x52):
        limit&=255
        if limit==0:raise ValueError('Original rejection loop cannot terminate for zero bound')
        # D4BB selects nibble sampling for bounds<15; D4AD always maskslow4.
        mask=15 if low_nibble or limit<15 else 255
        for _ in range(256):
            value=self.next_byte(cursor)&mask
            if value<limit:return value
        raise RuntimeError('Original RNG table supplied no acceptable sample')

def _clamp_finances(memory,address):
    """D105 callsD69D; reading a city also clamps both financewords9999."""
    for offset in(2,4):put_word(memory,address+offset,min(word(memory,address+offset),9999))

def next_domestic_city(memory):
    """BEE6: preincrement citycursor; abort on the third all-city wrap."""
    ruler=memory[0x6f03]
    if not 0<=ruler<7:raise ValueError('Original ruler IDs0..6')
    for _ in range(91):
        cursor=(memory[0x6f83+ruler]+1)&255;memory[0x6f83+ruler]=cursor
        if cursor>=30:
            memory[0x6f62]=(memory[0x6f62]+1)&255
            if memory[0x6f62]==3:
                memory[0x6f62]=0
                memory[0x6f5b]=2;memory[0x6f8b]=255;memory[0x6f8d]=0
                return None
            cursor=0;memory[0x6f83+ruler]=0
        memory[0x6f5e]=cursor;address=city_address(cursor);_clamp_finances(memory,address)
        if memory[address]&7==ruler:return cursor
    raise RuntimeError('Corrupt city-cycle scratch inputs exceed the proven loop bound')

def pay_city_resource(memory,city,resource,base_cost,random_range,random):
    """D36F/D3A9 payment; failed payment keeps initial financeclamping/RNG."""
    address=city_address(city);_clamp_finances(memory,address)
    cost=(base_cost+(random.below(random_range)if random_range else 0))&65535
    _clamp_finances(memory,address);offset=2 if resource=='gold'else 4 if resource=='grain'else None
    if offset is None:raise ValueError('Original payment resources gold/grain')
    available=word(memory,address+offset)
    if available<cost:return {'paid':False,'cost':cost}
    put_word(memory,address+offset,available-cost)
    if resource=='gold':_clamp_finances(memory,address)
    return {'paid':True,'cost':cost}

def domestic_development_once(memory,rom):
    """One BEC7 development selection/effect, stopping at its loop tail.

    The C1E0 officer/equipment branch is returned explicitly as next_stage;
    callers may run its recovered controller or provide a separate rule. This
    API does not silently pretend that branch has been completed.
    """
    ruler=memory[0x6f03];difficulty=memory[0x6f02]
    if not 0<=difficulty<3:raise ValueError('Original difficulty rows0..2')
    city=next_domestic_city(memory)
    if city is None:return {'next_stage':'turn_end','city':None}
    random=DomesticRandom(memory,rom);first=random.below(80)
    thresholds=(20,50,40,30,40,60,50)
    if first>=thresholds[ruler]:return {'next_stage':'officer_or_equipment','city':city}
    roll=random.below(100);kind=development_branch(ruler,memory[0x6f01],first,roll)
    address=city_address(city);offset={'field_06':6,'field_08':8,'field_10':10,'field_11':11,'field_14':14}[kind]
    base_cost,random_range=(30,30)if kind=='field_11'else(10,10)if kind=='field_10'else(10,14)
    paid=pay_city_resource(memory,city,'gold',base_cost,random_range,random)
    if not paid['paid']:return {'next_stage':'development_loop','city':city,'kind':kind,'changed':False,'payment':paid}
    total_cost=paid['cost']
    if kind=='field_11':
        grain=pay_city_resource(memory,city,'grain',30,30,random)
        if not grain['paid']:return {'next_stage':'development_loop','city':city,'kind':kind,'changed':False,'payment':paid,'grain_payment':grain}
        total_cost=(total_cost+grain['cost'])&65535
        increment=total_cost//(25,20,15)[difficulty]
    else:
        multiplier=(6,7,8)[difficulty]if kind=='field_10'else(12,15,18)[difficulty]
        increment=(total_cost*multiplier)//10
        if kind=='field_06':increment//=2
    if kind in('field_06','field_08','field_14'):
        if kind=='field_06':memory[address+11]=raise_city_field_11(memory[address+11],increment,'population')
        else:memory[address+11]=raise_city_field_11(memory[address+11],increment&255)
        put_word(memory,address+offset,apply_development_value(word(memory,address+offset),increment,kind))
    else:memory[address+offset]=apply_development_value(memory[address+offset],increment,kind)
    budget=consume_ai_budget(memory[0x6f5d],5,'task');memory[0x6f5d]=budget['remaining']
    if budget['abort_turn']:
        memory[0x6f5b]=2;memory[0x6f8b]=255;memory[0x6f8d]=0
    return {'next_stage':'turn_end'if budget['abort_turn']else'development_loop','city':city,'kind':kind,'changed':True,'increment':increment,'payment':paid,'budget':budget}

def choose_attack_target(memory,rom,ruler):
    """A240..A2D2: neighbor target by roster count and packed diplomacy timers.

    Enemycount ties accept the later distinct enemy. Repeated occurrences of
    the same target accept the own city with at least as many prefix officers.
    The original scan order is retained instead of replacing it with sorting.
    """
    if not 0<=ruler<7:raise ValueError('Original ruler IDs0..6')
    best_enemy_count=255;target=255;best_own_count=0;source=255
    for city in range(30):
        address=city_address(city);_clamp_finances(memory,address)
        if memory[address]&7!=ruler:continue
        own_count=CityRecord.from_memory(memory,city).occupied_prefix_count
        for neighbor in city_neighbors(rom,city):
            na=city_address(neighbor);_clamp_finances(memory,na);owner=memory[na]&7
            if owner in(7,ruler):continue
            diplomacy=memory[RULER_BASE+8*ruler+4+owner//2]
            if diplomacy&(15 if owner%2==0 else 240):continue
            enemy_count=CityRecord.from_memory(memory,neighbor).occupied_prefix_count
            if enemy_count>best_enemy_count:continue
            best_enemy_count=enemy_count
            if neighbor==target and own_count<best_own_count:continue
            target=neighbor;source=city;best_own_count=own_count
    return {'target_city':target,'source_city':source,'enemy_prefix_officers':best_enemy_count,'own_prefix_officers':best_own_count}

def choose_reinforcement_officer(roster,martial,loyalties,leader_id,mode):
    """A3D6 selection: largestmartial, orlargestloyalty excludingfirstslot.

    Only valid roster preconditions are modeled here. Original fallback writes
    to offset0 if there is no eligible officer; lifted IR retains that anomaly.
    """
    if len(roster)!=10:raise ValueError('10-slot original roster')
    selected=None;best=0
    for slot,officer in enumerate(roster):
        if officer in(255,leader_id)or mode and slot==0:continue
        score=(loyalties if mode else martial)[officer]&255
        if score>=best:best=score;selected=slot
    return {'slot':selected,'officer':None if selected is None else roster[selected],'score':best}

def choose_lowest_officer(roster,values,available,loyalty=False):
    """C248/C2EB selection: strict smaller value, earlier tie; clear chosenflag.

    Candidate100 is excluded only on the loyalty route. A value255 is never
    selected because the original initial best isFF and comparison isstrict.
    """
    if len(roster)!=10 or len(available)!=10:raise ValueError('10 roster/mask slots')
    best=255;chosen=None
    for slot,officer in enumerate(roster):
        if officer==255 or not available[slot]:continue
        value=values[officer]&255
        if loyalty and value==100:continue
        if value<best:best=value;chosen=slot
    mask=list(available)
    if chosen is not None:mask[chosen]=0
    return {'slot':chosen,'officer':None if chosen is None else roster[chosen],'value':best,'available':mask}

class DomesticDispatch:
    """Independent D494 inline dispatch convention; outside hooks explicit."""
    def __init__(self,fallback=None):self.fallback=fallback
    def __call__(self,context,target,return_pc,kind):
        if target!=0xD494:
            if self.fallback is None:
                from .battle_state_machine import UnresolvedDependency
                raise UnresolvedDependency(target,context.events[-1]['call_pc'],kind)
            return self.fallback(context,target,return_pc,kind)
        r=context.registers;index=r.a;pc=context.events[-1]['call_pc']
        domains={0xA039:3,0xA1BC:3}
        if pc not in domains or index>=domains[pc]:
            from .battle_state_machine import InvalidState
            raise InvalidState(f'Unproven domestic dispatch index{index} at{pc:04X}')
        context.memory[0x20]=r.y
        context.flag(1,bool(r.a&128));r.a=context.nz(r.a<<1);r.y=context.nz(r.a);r.y=context.nz(r.y+1)
        r.a=context.nz(context.pop());context.memory[0x21]=r.a
        r.a=context.nz(context.pop());context.memory[0x22]=r.a
        pointer=word(context.memory,0x21)
        r.a=context.nz(context.memory[(pointer+r.y)&65535]);context.memory[0x23]=r.a
        r.y=context.nz(r.y+1)
        r.a=context.nz(context.memory[(pointer+r.y)&65535]);context.memory[0x24]=r.a
        r.y=context.nz(context.memory[0x20]);r.pc=word(context.memory,0x23)

def _make_control(memory,hooks=None,program=None):
    if program is None:program=json.loads((ROOT/'analysis/phase5/domestic-ai/program.json').read_text())
    return _TurnExecutor(memory,DomesticDispatch(hooks),program)

from .battle_state_machine import BattleStateMachine
CONTROL_FIELDS={'main_state_0400':0x400,'substate_0401':0x401,'event_phase_0402':0x402,
                'ruler_6f03':0x6f03,'ai_flag_6f8b':0x6f8b,'ai_phase_6f5b':0x6f5b,
                'ai_budget_6f5d':0x6f5d,'selected_city_6f5e':0x6f5e}

def _control_snapshot(memory):return {name:memory[address]for name,address in CONTROL_FIELDS.items()}

class _TurnExecutor(BattleStateMachine):
    """Same CPU executor; external-call diagnostics useactualdomestic fields."""
    def external(self,item,target,return_pc,kind):
        self.events.append({'call_pc':item['pc'],'target':target,'kind':kind,
                            'control':_control_snapshot(self.memory),
                            'registers':vars(self.registers).copy(),'inline_target':item.get('inline_target')})
        self.hooks(self,target,return_pc,kind)

class DomesticAIControl:
    """Bounded lifted bank10/11 control; same executor, custom inline helper.

    Not a complete global/NMI scheduler. entryA00F may initialize, perform a
    domestic decision, or prepare battle according to6F8B/6F5B. Missing external
    helpers raise; supplying an original-code oracle does not recover them.
    """
    def __init__(self,memory,hooks=None,program=None):self.machine=_make_control(memory,hooks,program)
    def run_entry(self,entry=0xA00F,**kwargs):
        before=_control_snapshot(self.machine.memory)
        result=self.machine.run_entry(entry,**kwargs)
        result.update(before=before,after=_control_snapshot(self.machine.memory),control_fields=dict(CONTROL_FIELDS))
        return result
    def step(self,**kwargs):return self.run_entry(**kwargs)
    @property
    def registers(self):return self.machine.registers
    @property
    def executed(self):return self.machine.executed

class RulerTurnControl:
    """Independent pair25/26 calendar, turnevents and rulerAI bridge.

    These three cooperative controllers use0401; turnevents also use0402.
    Callers must map thepair25/26 code/datawindow context explicitly. Hooks
    remain required for outside renderer, farbank, input and reset services.
    Busy/ack states are left as the original code leaves them, not auto-cleared.
    """
    ENTRIES={'calendar':0xa033,'turn_events':0xa296,'ruler_ai_scene':0xc773}
    def __init__(self,memory,hooks=None,program=None):
        if program is None:program=json.loads((ROOT/'analysis/phase5/domestic-ai/turn-program.json').read_text())
        self.machine=_TurnExecutor(memory,hooks,program)
        self.memory=memory
    def run_entry(self,entry,**kwargs):
        before=_control_snapshot(self.memory)
        result=self.machine.run_entry(entry,**kwargs)
        result.update(before=before,after=_control_snapshot(self.memory),control_fields=dict(CONTROL_FIELDS))
        return result
    def tick(self,controller,**kwargs):
        if controller not in self.ENTRIES:raise ValueError('Three recovered turncontroller names')
        return self.run_entry(self.ENTRIES[controller],**kwargs)
    @property
    def registers(self):return self.machine.registers
    @property
    def executed(self):return self.machine.executed

