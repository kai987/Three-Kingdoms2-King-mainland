"""Recovery demand, funded local reserves, and competing fronts."""
from collections import defaultdict
from dataclasses import dataclass, field
from fractions import Fraction

from . import battle_reinforcements, domestic, faction_economy, grain_units, logistics, logistics_strategy
from .historical_campaigns import allied
from .logistics_rules import ceil_div
from .military_budget import REPLACEMENT_PERCENT
from .officers import OFFICER_TROOP_CAP

FIELD = 'ai_war_recovery'
RECENT_TURNS = 12
SUPPLY_HORIZON = 9
LOSS_KINDS = ('battle', 'march', 'convoy', 'allocation')
RISK_MULTIPLIERS = ((1,100), (3,90), (6,70))
LATER = 50
UNFUNDED = 35
OBJECTIVE_SCALE = 150
FRONT_PRESSURE = 8


def record(state, owner, city, kind, count):
    """Called only by the original write sites after a real casualty or allocation."""
    if not count or not logistics_strategy.war_recovery(state) or owner=='neutral':
        return
    index=LOSS_KINDS.index(kind)+1
    dates=state.extension.setdefault(FIELD,{}).setdefault(owner,{}).setdefault(city,[])
    dates[:]=[row for row in dates if state.turn-row[0]<RECENT_TURNS]
    if not dates or dates[-1][0]!=state.turn:
        dates.append([state.turn,0,0,0,0])
    dates[-1][index]+=count


def validate(game,state):
    if FIELD not in state.extension:
        return
    values=state.extension[FIELD]
    if (state.extension.get(logistics_strategy.FIELD)not in logistics_strategy.VERSIONS_WITH_RELIEF
            or not isinstance(values,dict) or not set(values)<=set(game.catalog.factions)):
        raise ValueError('War recovery history')
    for cities in values.values():
        if not isinstance(cities,dict) or not set(cities)<=set(game.catalog.map_cities):
            raise ValueError('War recovery city')
        for dates in cities.values():
            if not isinstance(dates,list) or not 1<=len(dates)<=RECENT_TURNS:
                raise ValueError('War recovery dates')
            previous=0
            for row in dates:
                if (not isinstance(row,list) or len(row)!=5
                        or any(type(n) is not int or not 0<=n<=100000000 for n in row)
                        or not previous<row[0]<=state.turn or not any(row[1:])):
                    raise ValueError('War recovery entry')
                previous=row[0]


def burden(state,owner,city):
    """Real credits can settle earlier losses, up to those actual losses."""
    count=0
    for turn, battle, march, convoy, allocated in state.extension.get(FIELD,{}).get(owner,{}).get(city,()):
        if state.turn-turn<RECENT_TURNS:
            count=max(0,count+battle+march+convoy-allocated)
    return count


def loss_budget(losses,reserves,gold_per_100,grain_per_100):
    allocated=min(max(0,losses),max(0,reserves))
    draft=max(0,losses-allocated)
    return allocated,draft,ceil_div(draft*gold_per_100,100),ceil_div(draft*grain_per_100,100)


def recovery_time(gap, surplus):
    return Fraction(0) if gap<=0 else Fraction(gap,surplus) if surplus>0 else None


def months_for(needs, current, dated, surplus):
    """An inbound load is a one-time amount and is available only after its ETA."""
    if needs<=current:
        return Fraction(0)
    best=recovery_time(needs-current,surplus)
    elapsed=0
    for eta, amount in sorted(dated):
        if surplus<=0:
            current=max(0,current+surplus*Fraction(eta-elapsed,3))+amount
            if current>=needs:
                return Fraction(eta,3)
        else:
            current+=amount
            until=max(Fraction(eta,3),recovery_time(needs-current,surplus))
            best=min(best,until)
        elapsed=eta
    return best


def multiplier(months, policy=None):
    if months is None:
        return policy['no_source'] if policy else UNFUNDED
    return next((value for upper,value in RISK_MULTIPLIERS if months<=upper),policy['after_six'] if policy else LATER)


def action_score(advantage,defender,weight,fronts,local_deficit,*,necessary=False):
    """Compare a prospective attack with actual preparation alternatives."""
    advantage_score=min(100,max(0,advantage)*100//max(1,defender))
    weight=100 if necessary else weight
    # A clear local advantage may justify a campaign despite some recovery
    # pressure. Existing fronts and a poor recovery queue improve the value
    # of using orders on defence, transfers, food or recruitment instead.
    appeal=(OBJECTIVE_SCALE+advantage_score)*weight//100
    prepare=0 if necessary or weight==100 and not fronts and not local_deficit else (
        OBJECTIVE_SCALE-weight//2 + FRONT_PRESSURE*min(fronts,4) + min(35,local_deficit))
    return appeal,prepare


@dataclass
class CityResources:
    grain: int
    gold: int
    reserves: int
    grain_surplus: int
    gold_surplus: int
    gold_rate: int
    grain_rate: int
    recoverable: int
    actual_deficit: int
    real_losses: int
    committed_grain: int
    incoming_grain: list = field(default_factory=list)
    incoming_gold: list = field(default_factory=list)


class Forecast:
    """One snapshot for scoring a faction's candidates at the current state."""
    def __init__(self,game,state,owner,economy=None):
        self.owner,self.game,self.state=owner,game,state
        self.economy=economy or faction_economy.plan(game,state,owner)
        self.resources={}
        self.pending={}
        self.fronts=defaultdict(set)
        self.deployed=0
        self.enroute=0
        self.losses=defaultdict(int)
        self.committed={}
        self._capture()

    def _capture(self):
        game,state,owner=self.game,self.state,self.owner
        plan=self.economy
        counts=defaultdict(int)
        already=set()
        travel=state.extension['travel']['marches']
        for march in travel:
            if march['owner']!=owner:
                continue
            soldiers=sum(state.officers[i].troops for i in march['officers'])
            self.enroute+=1
            if march['kind']!='attack' or march['supply']['retreat_requested']:
                continue
            self.deployed+=soldiers
            self.fronts[march['source']].add(march['target'])
            counts[march['source']]+=ceil_div(soldiers*REPLACEMENT_PERCENT,100)
            already.update(march['officers'])
        if state.battle:
            battle=state.battle
            homes={ident:city.id for city in state.cities.values() for ident in city.roster.officer_ids}
            for side in ('attackers','defenders'):
                for unit in battle[side]:
                    ident=unit['id']
                    if ident in already or state.officers[ident].faction_id!=owner:
                        continue
                    city=homes.get(ident,battle['target'])
                    troop=unit['troops']
                    self.deployed+=troop
                    self.fronts[city].add(battle['target'])
                    counts[city]+=ceil_div(troop*REPLACEMENT_PERCENT,100)
                    already.add(ident)
            for order in battle['extended'].get(battle_reinforcements.FIELD,{}).get('pending',()):
                if order['owner']!=owner:
                    continue
                self.enroute+=1
                self.fronts[order['source']].add(battle['target'])
                soldiers=sum(state.officers[ident].troops for ident in order['officers'] if ident not in already)
                self.deployed+=soldiers
                counts[order['source']]+=ceil_div(soldiers*REPLACEMENT_PERCENT,100)
                already.update(order['officers'])
        for order in state.extension['ai_strategy'].get(owner,{}).get('orders',()):
            if order['march_id'] is not None or order['departure_turn']<state.turn:
                continue
            city=state.cities.get(order['source'])
            target=state.cities.get(order['target'])
            if (city is None or city.owner!=owner or target is None or target.owner==owner
                    or allied(state,owner,target.owner)):
                continue
            ids=[i for i in order['officers'] if i not in already and i in city.roster.officer_ids
                 and state.officers[i].alive and state.officers[i].faction_id==owner]
            if not ids:
                continue
            predicted=ceil_div(sum(state.officers[i].troops for i in ids)*REPLACEMENT_PERCENT,100)
            self.pending[city.id,target.id]=(predicted,order.get('provision',0))
            self.fronts[city.id].add(target.id)
            counts[city.id]+=predicted
            already.update(ids)
        absent=self.game._march_ids(state)
        office=domestic.appointments(state,owner)
        policy=office.get('policy',domestic.DEFAULT_POLICY)
        leader=office.get('military')
        automatic=leader is not None and leader in state.officers and policy['recruit_enabled']
        automatic_rate=domestic._recruit_gold_per_100(state.officers[leader].profile.martial_strength) if automatic else None
        cache=game.catalog.data['rules']
        incoming=defaultdict(list)
        for row in state.extension['logistics']['convoys']:
            target=state.cities[row['target']]
            if (row['owner']!=owner or target.owner!=owner or row['delivery_done']
                    or row['target_march'] is not None or row['status']!='outbound'
                    or row['journeys'][-1]['supply']['retreat_requested']):
                continue
            eta=max(1,row['journeys'][-1]['arrival_turn']-state.turn)
            if eta<=SUPPLY_HORIZON:
                incoming[target.id].append((eta,logistics.inbound_grain(game,row,state),row['cargo']['gold']))
        for key,budget in plan.budgets.items():
            city=state.cities[key]
            here=[state.officers[i] for i in city.roster.officer_ids
                  if i not in absent and state.officers[i].alive and state.officers[i].faction_id==owner
                  and state.officers[i].health>0]
            roster_spare=sum(OFFICER_TROOP_CAP-o.troops for o in here)
            physical_guard=min(city.reserves, 500 if budget['threatened'] else 0)
            held=plan.commitments.amount(key)
            floor=max(budget['minimum_export_floor'],budget['safety_reserve'],budget['next_installment'])
            guard_cost=budget['wage_gold']+max(0,policy['gold_floor']) if budget['threatened'] else budget['wage_gold']
            rate=cache['recruit_gold_per_100'] if automatic_rate is None else automatic_rate
            grain_rate=grain_units.amount(cache['recruit_grain_per_100'] if automatic_rate is None else 30)
            actual=burden(state,owner,key)
            if actual:
                self.losses[key]=actual
            if counts[key]:
                self.committed[key]=counts[key]
            # A city that cannot sustainably rebuild every lost soldier
            # targets the number it can legally and permanently support.
            sustainable=max(0,budget['sustainable_combined']-budget['active'])
            self.resources[key]=CityResources(
                max(0,city.grain-floor-held),max(0,city.gold-guard_cost),max(0,city.reserves-physical_guard),
                budget['regular']-budget['fixed'],budget['regular_gold']-budget['wage_gold'],
                rate,grain_rate,min(roster_spare,sustainable),budget['current_shortfall'],actual,held,
                [(eta,grain) for eta,grain,_ in incoming[key]],[(eta,gold) for eta,_,gold in incoming[key]])

    def assess(self, columns=(), *, target=None):
        proposed=defaultdict(int)
        launching=defaultdict(int)
        for key,soldiers,funded in columns:
            proposed[key]+=ceil_div(soldiers*REPLACEMENT_PERCENT,100)
            launching[key]+=funded
        fields = defaultdict(int)
        waiting=Fraction(0)
        no_regular=False
        fronts={front for all_targets in self.fronts.values() for front in all_targets if front!=target}
        other_fronts=0
        cities=[]
        for key in sorted(set(self.losses)|set(proposed)|set(self.committed)):
            row=self.resources.get(key)
            if row is None:
                continue
            existing,already_funded=self.pending.get((key,target),(0,0))
            commitments=max(0,self.committed.get(key,0)-existing)
            # Retain only the current plan's actual spare orders. Already paid
            # outbound bags are outside city stock and never deducted again.
            new_need=proposed[key]
            loss=min(row.real_losses,row.recoverable) + commitments + new_need
            reserve,draft,gold,grain=loss_budget(loss,row.reserves,row.gold_rate,row.grain_rate)
            immediate=max(0,row.grain-max(0,launching[key]-already_funded))
            mg=months_for(grain,immediate,row.incoming_grain,row.grain_surplus)
            mm=months_for(gold,row.gold,row.incoming_gold,row.gold_surplus)
            eta=max(mg,mm) if mg is not None and mm is not None else None
            no_regular |= eta is None
            waiting=max(waiting,eta) if eta is not None else waiting
            competing=len(self.fronts.get(key,set())-{target})
            if new_need:
                other_fronts+=competing
            fields['actual_losses']+=row.real_losses
            fields['existing_commitment']+=commitments
            fields['prospective_losses']+=new_need
            fields['reserves_assigned']+=reserve
            fields['soldiers_to_draft']+=draft
            fields['grain_need']+=grain
            fields['gold_need']+=gold
            fields['grain_available']+=immediate
            fields['gold_available']+=row.gold
            fields['incoming_grain']+=sum(n for _,n in row.incoming_grain)
            fields['incoming_gold']+=sum(n for _,n in row.incoming_gold)
            fields['held_grain']+=row.committed_grain
            if key in proposed:
                fields['source_grain_pressure']+=min(35, row.actual_deficit)
            if loss and (key in proposed or row.real_losses or commitments):
                cities.append(dict(city=key,losses=loss,reserves=reserve,grain=grain,gold=gold,
                                   grain_gap=max(0,grain-immediate),gold_gap=max(0,gold-row.gold),
                                   months=round(float(eta),3) if eta is not None else None))
        months=None if no_regular else waiting
        return dict(fields,months=round(float(waiting),3) if not no_regular else None,
                    multiplier=multiplier(months,self.state.extension.get(logistics_strategy.POLICY)),no_reliable_surplus=no_regular,
                    other_fronts=len(fronts),overlapping_fronts=other_fronts,
                    committed_wars=len(fronts)+int(any(target in f for f in self.fronts.values())),
                    deployed=self.deployed,enroute=self.enroute,cities=cities)

    def view(self):
        result=self.assess()
        result.update(current_grain=sum(row['stock'] for row in self.economy.budgets.values()),
                      current_gold=sum(row['gold'] for row in self.economy.budgets.values()),
                      reservable_grain=sum(row.grain for row in self.resources.values()),
                      reservable_gold=sum(row.gold for row in self.resources.values()),
                      pending_grain=sum(row.committed_grain for row in self.resources.values()))

        result['status']=('shortage' if result['no_reliable_surplus']
                          else 'recovering' if result['months']>1 else 'ready')
        return result
