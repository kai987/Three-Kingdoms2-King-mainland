"""Independent readable implementations of all eight bank8 tactical strategies.

The pinned ROM supplies immutable tables only. This module neither interprets
IR nor executes original instructions. It writes gameplay RAM/SRAM; CPU flags,
registers, stack and mapper-window scratch remain the separate CPU controller's
contract. A cooperative update proposes an action; it never applies a renderer
acknowledgement, movement/AP commit, attack or tactic effect.
"""
from dataclasses import dataclass
import hashlib
from . import ai
from .tactical_decisions import TacticalData, TacticalDecisions, ROM_SHA256

STRATEGY_ENTRIES=(0xA0B1,0xA105,0xA166,0xA210,0xA2AD,0xA329,0xA507,0xA606)

@dataclass(frozen=True)
class StrategyData:
    tactical: TacticalData
    city_neighbors: tuple
    city_base_xy: tuple
    service_coordinates: tuple
    resource_prices: bytes
    initial_health: bytes
    data_pages: tuple
    chunk_banks: bytes

    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:
            raise ValueError('Strategy tables require the pinned original ROM')
        neighbors=tuple(tuple(rom[0x21D82+8*i:0x21D8A+8*i])for i in range(30))
        bases=[]
        for city in range(30):
            pointer=int.from_bytes(rom[0xCC62+2*city:0xCC64+2*city],'little')
            offset=0xC010+pointer-0x8000
            # Original table stores Y then X; source API uses X,Y.
            bases.append((rom[offset+1],rom[offset]))
        services=tuple(tuple((rom[0x23BB4+6*c+2*i],rom[0x23BB5+6*c+2*i])for i in range(3))for c in range(30))
        return cls(TacticalData.from_rom(rom),neighbors,tuple(bases),services,
                   bytes(rom[0x20FD0+2*c+1]for c in range(30)),
                   bytes(rom[0x22010+12*i]for i in range(237)),
                   tuple(bytes(rom[16+8192*i:16+8192*(i+1)])for i in range(32)),
                   bytes((v&63)%32 for v in rom[0x118CB:0x11943]))

class _DataWindow:
    """Read immutable bank data while sharing every RAM/SRAM mutation."""
    def __init__(self,owner):self.owner=owner
    def __len__(self):return 65536
    def __getitem__(self,address):
        if 0x8000<=address<0xA000:
            bank=self.owner._data_bank
            if bank is None:raise ValueError('ROM map descriptor needs explicit current data_window_bank')
            return self.owner.data.data_pages[bank][address-0x8000]
        return self.owner.memory[address]
    def __setitem__(self,address,value):self.owner.memory[address]=value

class _StrategyMovement(TacticalDecisions):
    def __init__(self,owner):self.owner=owner;super().__init__(_DataWindow(owner),owner.data.tactical)
    def _terrain(self,x,y):
        pointer=self._word(0xA8)
        if not (pointer<=0x7FC or 0x6000<=pointer<=0x7FFC or 0x8000<=pointer<=0x9FFC):
            raise ValueError('Map descriptor must be four readable RAM/SRAM/data-window bytes')
        chunk=self.memory[(pointer+int(x>=16)+2*int(y>=16))&65535]
        result=super()._terrain(x,y)
        self.owner._data_bank=self.owner.data.chunk_banks[chunk]
        return result

class TacticalStrategyAI:
    """Complete0..7 strategy and A02D cooperative gameplay behavior.

    Shared-memory effects are SRAM6000..7FFF and gameplay RAM0500..0677.
    Internal zero-page temporaries are maintained where they influence a later
    decision (notably2F sort-pass input), but arbitrary CPU scratch is excluded
    from this API's equivalence claim. RNG savedX6F93 is preserved separately
    because it resides in SRAM. Actor/record/city/ruler inputs require the
    original valid table domains; out-of-table paths are source guards.
    """
    def __init__(self,memory,data:StrategyData,*,data_window_bank=None):
        self.memory=memory;self.data=data
        self._data_bank=data_window_bank if data_window_bank is not None else getattr(memory,'banks',[None])[0]
        if self._data_bank is not None and not 0<=self._data_bank<32:raise ValueError('Physical data bank0..31 required')
        self.decisions=_StrategyMovement(self)
        self._x=0;self.random_draws=[];self.events=[];self._in_update=False

    def _sync_context(self,data_window_bank=None):
        """Readhostbank at each public wholeupdate, withoutwritingmapper.

        FlatRAM has no bank metadata: retain this owner's logical context or
        pass data_window_bank explicitly when an external host changes it.
        """
        bank=data_window_bank
        if bank is None and hasattr(self.memory,'banks'):bank=self.memory.banks[0]
        if bank is not None:
            if not 0<=bank<32:raise ValueError('Physical data bank0..31 required')
            self._data_bank=bank

    def _set(self,address,value):self.memory[address]=value&255
    def _word(self,address):return self.memory[address]|self.memory[address+1]<<8
    def _putword(self,address,value):self._set(address,value);self._set(address+1,value>>8)
    def _actor(self):return self.decisions._actor()
    def _city(self):
        city=self.memory[0x50E]
        if city>=30:raise ValueError('Original city domain0..29 required')
        return city
    def _side_offset(self):return 2 if self.memory[0x504]&128 else 0
    def _ruler(self):
        ruler=(self.memory[0x507]>>(4 if self.memory[0x504]&128 else 0))&15
        if ruler>=7:raise ValueError('Original ruler domain0..6 required')
        return ruler
    def _record(self,slot):
        if not 0<=slot<20:raise ValueError('Original unit slot0..19 required')
        ident=self.memory[0x664+slot]
        if ident>=237:raise ValueError('Selected unit must contain officer0..236')
        return 0x63C0+12*ident
    def _random(self,bound=256,mask=255):
        for _ in range(256):
            index=self.memory[0x6F92];raw=self.data.tactical.rng[index]
            self._set(0x6F92,index+1);self.memory[0x6F93]=self._x&255
            self.random_draws.append(raw)
            if raw&mask<bound:return raw&mask
        raise ValueError('Pinned RNG permutation must contain an accepted value')
    def _neighbors(self,slot):
        result=self.decisions._neighbors(slot);self._x=3;return result
    def _terrain(self,slot):
        terrain=self.decisions._terrain(self.memory[0x600+slot],self.memory[0x614+slot]);self._x=0;return terrain
    def _arrays(self):
        m=self.memory
        return([m[0x664+i]for i in range(20)],[m[0x600+i]for i in range(20)],
               [m[0x614+i]for i in range(20)],[m[0x628+i]for i in range(20)])
    def _candidates(self,center_slot,radius):
        m=self.memory;ids,xs,ys,sides=self._arrays()
        values=ai.nearby_candidates(center_slot,ids,xs,ys,sides,m[0x504],radius)
        for i,value in enumerate(values):m[0x6FC9+i]=value
        return values
    def _rank(self):
        m=self.memory;ids,_,_,_=self._arrays()
        raw=[self._word(0x63C8+12*i)for i in range(237)]+[0]*19
        masks=[m[0x6FC9+i]for i in range(20)]
        count=sum(bool(value&128)for value in masks)
        ranking=ai.rank_enemy_candidates(masks,ids,raw,m[0x2F])
        for i,value in enumerate(ranking.slots):m[0x6FC9+i]=value
        m[0x2F]=ranking.remaining_pass_counter;self._x=count if count<2 else count-1
        return ranking.slots

    def army_totals(self):
        """Complete B067 raw16 troop sums, modulo65536, both signed sides."""
        totals=[0,0];m=self.memory
        for slot in range(20):
            if m[0x664+slot]==255:continue
            group=int(bool(ai.opposing_side_marker(m[0x504],m[0x628+slot])))
            self._x=2*group
            totals[group]=(totals[group]+self._word(self._record(slot)+8))&65535
        return tuple(totals)

    def retreat_destination(self):
        """AFF6: negative side uses052A; positive side scans eight neighbors.

        First same-ruler city with anyFF roster slot wins; otherwise last
        neutral city wins. An occupied neutral roster does not disqualify it.
        """
        m=self.memory
        if m[0x504]&128:return m[0x52A]
        ruler=self._ruler();fallback=255
        self._data_bank=16
        for index,neighbor in enumerate(self.data.city_neighbors[self._city()]):
            self._x=index
            if neighbor&128:continue
            if neighbor>=30:raise ValueError('Neighbor city ID outside original30-city table')
            base=0x6000+32*neighbor;owner=m[base]&7
            if owner==7:fallback=neighbor
            elif owner==ruler and any(m[base+i]==255 for i in range(17,27)):
                return neighbor
        self._x=8;return fallback

    def retreat(self):
        """Complete AF0D: role-specific rawtroops/HP gates and destination.

        Leaders: rawtroops<301 AND HP<51. Nonleader slot0/10 commanders:
        immediate retreat if ownsum<1757 and ownsum+3499<enemysum, else
        rawtroops<101 AND HP<41. Others: rawtroops<201 AND HP<100,
        then rejection-sampled0..99 must be<70. Destination sign must clear.
        """
        slot,ident,record=self._actor();m=self.memory;self._x=m[0x504]
        leader=m[0x6F07+8*self._ruler()];troops=self._word(record+8);hp=m[record]
        if ident==leader:eligible=troops<301 and hp<51;role='leader'
        elif slot in(0,10):
            own,enemy=self.army_totals();forced=own<1757 and own+3499<enemy
            eligible=forced or(troops<101 and hp<41);role='commander'
        else:
            eligible=troops<201 and hp<100;role='officer'
            if eligible:eligible=self._random(100)<70
        if not eligible:return dict(success=False,role=role)
        m[0x6F8D]=255;destination=self.retreat_destination();m[0x6F8D]=destination
        if destination&128:return dict(success=False,role=role,destination=destination)
        m[0x6F8F]=4;self.events.append(dict(kind='withdraw',destination=destination))
        return dict(success=True,role=role,destination=destination)

    def _suitable(self,target,action):
        """Full AC7B sixteen original terrain/adjacency/record predicates."""
        m=self.memory;m[0x2B]=target;m[0x2C]=action
        actor,_,actor_record=self._actor();target_record=self._record(target)
        target_terrain=self._terrain(target);actor_terrain=self._terrain(actor)
        if action==0:return target_terrain in(0,2)
        if action in(1,2,3):return target_terrain in(0,4)
        if action==4:return target_terrain==3
        if action==5:return target in(0,10)
        if action==6:
            return target_terrain==5 and any((v&127)==actor for v in self._neighbors(target))
        if action==7:
            return target_terrain in(0,4)and any(v!=255 and v&128 for v in self._neighbors(target))
        if action==8:return target_terrain!=5 and m[target_record+3]<50
        if action==9:
            if actor_terrain not in(4,5):return False
            adjacent=any((v&127)==target for v in self._neighbors(actor))
            return adjacent and target_terrain==5
        if action in(10,12):
            if target_terrain!=3:return False
            for v in self._neighbors(target):
                if v!=255 and v&128 and self._terrain(v&127)==3:return True
            return False
        if action==11:
            group=4 if m[0x504]&128 else 0
            return actor_terrain==0 and(self._word(actor_record+8)!=0 and(m[actor_record+9]!=0 or m[actor_record+8]>=100))and m[0x4D8+group]==255
        if action==13:
            return actor_terrain==5 and any((v^128)==target for v in self._neighbors(actor))
        if action==14:
            if target_terrain==5:return False
            for v in self._neighbors(target):
                if v!=255 and v&128 and self._terrain(v&127)!=5:return True
            return False
        if action==15:
            return target_terrain!=5 and(m[target_record+1]>=85 or m[target_record+2]>=85)and m[target_record+9]>=2 and m[target_record+8]>=188
        raise ValueError('Original16tactic predicate domain required')

    def plan_tactic(self,special=False,*,data_window_bank=None):
        """Complete A95C or AAF8: all candidates, raw16 ranking and chooser."""
        if not self._in_update:self._sync_context(data_window_bank)
        m=self.memory;actor,ident,record=self._actor()
        level=m[record+11]>>4;iq=m[record+2]
        m[0x2A]=ident if special else ai.knowledge_tier(iq)
        if special:
            if iq<92:return dict(success=False,gate='intelligence')
            m[0x36]=level
            if level<3:return dict(success=False,gate='level')
        self._candidates(actor,5);ranked=self._rank()
        for position,target in enumerate(ranked):
            if target==255:break
            self._x=target
            if m[0x664+target]==255:continue
            m[0x2B]=target;m[0x2F]=position
            troops=self._word(self._record(target)+8)
            predicate=lambda action:self._suitable(target,action)
            if special:
                decision=ai.choose_special_action(ident,level,m[0x505],troops,m[0x650+target],predicate,m[0x6F8F],m[0x2C])
            else:
                decision=ai.choose_basic_action(ai.knowledge_tier(iq),m[0x505],troops,m[0x650+target],predicate,self._random,m[0x6F8F],m[0x2C])
            m[0x2C]=decision.scratch_action;m[0x6F8F]=decision.final_status
            if decision.success:
                m[0x6F8D]=decision.scratch_action;m[0x6F8E]=target;m[0x6F8F]=2
                self.events.append(dict(kind='tactic',action=decision.scratch_action,target=target,special=special))
                return dict(success=True,action=decision.scratch_action,target=target)
        m[0x6F8F]=3;return dict(success=False)

    def _move(self,x,y):return self.decisions.plan_movement(x,ai.normalize_y(y))
    def _move_slot(self,slot):return self._move(self.memory[0x600+slot],self.memory[0x614+slot])
    def _opposing_or_base(self):
        if not self.memory[0x504]&128:return self._move_slot(10)
        self._data_bank=6
        return self._move(*self.data.city_base_xy[self._city()])
    def _nearest(self,center,radius):
        masks=self._candidates(center,radius);distance=255;selected=None
        for slot,value in enumerate(masks):
            if value&128 and(value&127)<distance:distance=value&127;selected=slot
        return selected
    def _preflight(self,adjacent=False):
        if self.retreat()['success']:return True
        if self.plan_tactic(True)['success']:return True
        return bool(self.decisions.adjacent_attack()['success'])if adjacent else False

    def _facility(self,index):
        """A329/A507 movement and raw prospective-arrival test, withoutcommit."""
        actor,_,_=self._actor();m=self.memory;self._data_bank=17
        xy=self.data.service_coordinates[self._city()][index]
        result=self._move(*xy)
        if m[0x6F8F]!=0:return False
        self._data_bank=17
        direction=m[0x6F8D];next_xy=[m[0x600+actor],m[0x614+actor]]
        axis=((direction>>1)&1)^1;next_xy[axis]=(next_xy[axis]+(1 if direction&1 else-1))&255
        # No row15 skip here; the original test is before its later commit.
        if tuple(next_xy)!=xy:return False
        m[0x6FA1+actor]=(m[0x6FA1+actor]&240)|7;return True

    def resupply(self):
        """Complete A329: move to service0, then original budgeted grain buy.

        Arrival first marks strategy7, even if resources provide no benefit.
        Shortage is a wrapping u16 subtraction; it is not clamped atzero.
        Demand floors4*rawarmy/1000 BEFORE multiplying remainingrounds.
        """
        m=self.memory
        if not self._facility(0):return dict(applied=False)
        own,enemy=self.army_totals();rounds=(30-m[0x506])&255
        demand=((own*4//1000)*rounds)&65535;side=self._side_offset()
        gold_address=0x526+side;grain_address=0x522+side
        gold=self._word(gold_address);grain=self._word(grain_address);budget=(gold*7//10)&65535
        shortage=(demand-grain)&65535;self._data_bank=16;price=self.data.resource_prices[self._city()]
        cost=(shortage*100//price)&65535 if price else 65535
        if budget>=cost:spent=cost;gained=shortage
        else:spent=budget;gained=(budget*price//100)&65535
        self._putword(gold_address,gold-spent);self._putword(grain_address,grain+gained)
        self._x=side
        self.events.append(dict(kind='resupply',spent_gold=spent,gained_grain=gained,demand=demand))
        return dict(applied=True,spent_gold=spent,gained_grain=gained,demand=demand,shortage=shortage,budget=budget)

    def heal(self):
        """Complete A507: move to service2, markstrategy7, spend50 thenheal."""
        m=self.memory
        if not self._facility(2):return dict(applied=False)
        actor,ident,record=self._actor();side=self._side_offset();gold_address=0x526+side
        gold=self._word(gold_address)
        if gold<50:return dict(applied=False,arrived=True,reason='insufficient_gold')
        self._putword(gold_address,gold-50);self._x=side
        amount=self._random(11,15)+35;self._data_bank=17;hp=(m[record]+amount)&255;ceiling=self.data.initial_health[ident]
        m[record]=min(hp,ceiling)
        self.events.append(dict(kind='heal',amount=amount,health=m[record]))
        return dict(applied=True,health=m[record],sampled_heal=amount,gold_cost=50)

    def run_strategy(self,strategy,*,data_window_bank=None):
        """One complete original strategy body0..7, independent ofIR."""
        self._sync_context(data_window_bank);previous=self._in_update;self._in_update=True
        try:return self._run_strategy_body(strategy)
        finally:self._in_update=previous

    def _run_strategy_body(self,strategy):
        if not 0<=strategy<8:raise ValueError('Eight original strategies0..7 required')
        actor,_,_=self._actor();self._city();m=self.memory
        self.events.append(dict(kind='strategy',strategy=strategy,actor=actor))
        if strategy==7:m[0x6F8F]=3
        elif strategy==5:self.resupply()
        elif strategy==6:self.heal()
        elif not self._preflight(strategy in(0,2,3,4)and bool(strategy or m[0x504]&128)):
            if strategy==0:
                if self.plan_tactic()['success']:pass
                elif m[0x504]&128:
                    if self._random()&3:moves=self._move_slot(0)
                    else:m[0x6F8F]=3
            elif strategy==1:
                target=0 if m[0x504]&128 else 10
                adjacent=m[0x505]>=2 and any((v&127)==target for v in self._neighbors(actor))
                if adjacent:m[0x6F8D]=target;m[0x6F8F]=1
                else:self._opposing_or_base()
            elif strategy==2:
                target=self._nearest(actor,2)
                if target is None:self._opposing_or_base()
                else:self._move_slot(target)
            elif strategy==3:
                own_leader=10 if m[0x504]&128 else 0;target=self._nearest(own_leader,2)
                if target is not None:
                    m[0x6F8E]=target
                    supported=any(not v&128 and v not in(0,10)for v in self._neighbors(target))
                    if supported:self.plan_tactic()
                    else:self._move_slot(target)
                elif not self.plan_tactic()['success']:self._move_slot(own_leader)
            elif strategy==4:
                target=self._nearest(actor,3)
                if target is not None:m[0x6F8E]=target;self._move_slot(target)
                elif not self.plan_tactic()['success']:self._move_slot(10 if m[0x504]&128 else 0)
        return dict(after=self.decisions.decision_state(),events=list(self.events),random_draws=list(self.random_draws))

    def step(self,*,maximum_strategy_calls=256,data_window_bank=None):
        """Complete A02D cooperative update; proposals never auto-committed.

        A finite caller budget returns statusbudget with actual partial writes.
        No status/action or request flag is invented to make a loop finish.
        """
        if maximum_strategy_calls<0:raise ValueError('Strategy-call budget must be nonnegative')
        self._sync_context(data_window_bank);previous=self._in_update;self._in_update=True
        try:return self._cooperative_body(maximum_strategy_calls)
        finally:self._in_update=previous

    def _cooperative_body(self,maximum_strategy_calls):
        self.random_draws=[];self.events=[];route=self.decisions.prepare_actor();calls=0
        if route['stop']=='secondary_entry':
            effect=self.decisions.secondary_effect()
            return dict(status='returned',after=self.decisions.decision_state(),strategy_calls=0,secondary_effect=effect,events=list(self.events))
        while route['stop']=='strategy_entry':
            if calls>=maximum_strategy_calls:
                return dict(status='budget',after=self.decisions.decision_state(),strategy_calls=calls,events=list(self.events))
            self._run_strategy_body(route['strategy']);calls+=1;route=self.decisions.finish_actor()
        return dict(status='returned',after=self.decisions.decision_state(),strategy_calls=calls,events=list(self.events),random_draws=list(self.random_draws))
