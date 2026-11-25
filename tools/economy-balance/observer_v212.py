"""Independent army supply episodes and faithful escort rejection diagnostics."""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from hashlib import sha256
from json import dumps
from unittest.mock import patch

from common import to_csv
from remake import army_relief, command_books, domestic, logistics, logistics_rules as rules, march_supply


def availability(game, state, source, reason, options):
    """Explain the actual 211 filters, including overlapping officer exclusions."""
    sid, owner = source.id, source.owner
    pool=logistics._pool(state)
    policy=pool['cities'][sid]['policy']
    active=game._march_ids(state)
    convoy_people=logistics.marching_ids(state)
    battle=state.battle or {}
    fighting={row['id'] for side in ('attackers','defenders') for row in battle.get(side,())}
    appointments=domestic.appointments(state,owner)
    delegates={appointments.get('civil'),appointments.get('military')}
    active_orders=state.extension.get('ai_strategy',{}).get(owner,{}).get('orders',())
    booked={i for row in active_orders if row['source']==sid and row['march_id'] is None
            and row['departure_turn']>=state.turn for i in row['officers']}
    eligible=logistics._eligible(game,state,source)
    counts=Counter()
    by_officer={}
    for ident in source.roster.officer_ids:
        officer=state.officers[ident]
        if not officer.alive or officer.faction_id!=owner:
            continue
        flags=[]
        if ident in active: flags.append('officer_on_march')
        if ident in fighting: flags.append('officer_in_battle')
        if ident in delegates: flags.append('delegation_restricted')
        if officer.health<=0: flags.append('officer_unhealthy')
        if pool['receipts'].get(str(ident),0)>state.turn: flags.append('officer_busy')
        if flags:
            by_officer[str(ident)]=flags
            counts.update(flags)
    residents=logistics._present_count(game,state,source)
    if options:
        primary=None
    elif reason=='no_spare_officer':
        if not policy['max_officers']:
            primary='delegation_restricted'
        elif not source.roster.officer_ids:
            primary='no_resident_officer'
        elif residents<=policy['reserve_officers']:
            primary=('officer_on_march' if not residents and counts['officer_on_march']
                     else 'officer_reserved_for_defense')
        else:
            primary=next((key for key in ('officer_in_battle','officer_on_march','delegation_restricted',
                                        'officer_busy','officer_unhealthy') if counts[key]),
                         'other_actual_restriction')
    else:
        primary={'command_books':'no_command_book','defence':'officer_reserved_for_defense',
                 'heavy_escort':'escort_troops_too_heavy'}.get(reason,reason)
    return dict(city_id=sid,faction_id=owner,turn=state.turn,officers_total=len(source.roster.officer_ids),
        resident_officers=residents,available_officers=len(eligible),
        unarmed_officers=sum(state.officers[i].troops==0 for i in eligible),
        light_escort_candidates=sum(state.officers[i].troops<=500 for i in eligible),
        heavy_escort_candidates=sum(state.officers[i].troops>500 for i in eligible),
        convoy_officers=sum(i in convoy_people for i in source.roster.officer_ids),
        military_plan_officers=len(booked),reserve_capacity=logistics.LIMIT-source.reserves,
        command_books=command_books.remaining(state,owner),assigned_escort_id=options[0]['officers'][0] if options else None,
        assignment_result='quoted' if options else 'blocked',original_reason=None if options else reason,
        rejection_reason=primary,officer_on_march=counts['officer_on_march'],officer_in_battle=counts['officer_in_battle'],
        officer_busy=counts['officer_busy'],officer_unhealthy=counts['officer_unhealthy'],
        delegation_restricted=counts['delegation_restricted'],
        officer_reserved_for_defense=(primary=='officer_reserved_for_defense'),
        officer_reserved_for_war=(primary=='officer_reserved_for_war'),
        no_legal_troop_reassignment=(primary=='no_legal_troop_reassignment'),
        officer_exclusions=by_officer)


@dataclass
class Episode:
    army_id: int
    owner: str
    sequence: int
    first_day: int
    original_deadline: int
    deadline: int
    original_need: int
    additional_need: int = 0
    supply: list = field(default_factory=list)
    convoys: list = field(default_factory=list)
    blockers: Counter = field(default_factory=Counter)
    planned: bool = False
    lost: int = 0

    @property
    def remaining(self):
        return self.original_need+self.additional_need-sum(r['credited'] for r in self.supply)

    def update(self, required, deadline, *, revised=False):
        # Repeated forecasts are the unfilled balance of one episode. A larger
        # real balance increases the requirement once, independent of quote fan-out.
        self.additional_need+=max(0, required-self.remaining)
        if revised:
            self.deadline=deadline

    def deliver(self, grain, tick, kind, source):
        credited=min(grain,self.remaining)
        if credited:
            self.supply.append(dict(day=tick,kind=kind,source=source,actual=grain,credited=credited,
                                    timely=tick<=self.deadline))

    def row(self, tick, *, unresolved=None):
        early = sum(r['credited'] for r in self.supply if r['timely'])
        late = sum(r['credited'] for r in self.supply if not r['timely'])
        if not self.remaining:
            pathways={r['kind'] for r in self.supply}
            terminal=('supplied_late' if late else 'resolved_by_city_supply' if pathways=={'city'}
                      else 'fully_supplied' if 'convoy' in pathways else 'resolved_by_other_legal_supply')
        else:
            terminal=unresolved or 'failed'
        return dict(supply_episode_id=f'{self.army_id}:{self.sequence}',army_id=self.army_id,
            faction_id=self.owner,first_request_time=self.first_day,original_shortage_deadline=self.original_deadline,
            updated_shortage_deadline=self.deadline,original_required_grain=self.original_need,
            additional_required_grain=self.additional_need,assigned_convoy_ids=list(self.convoys),
            timely_delivered_grain=early,late_delivered_grain=late,
            direct_city_resupply=sum(r['credited'] for r in self.supply if r['kind']=='city'),
            remaining_unmet_grain=self.remaining,resolved_time=None if terminal=='pending_at_observation_end' else tick,
            terminal_status=terminal,progress=('fully_supplied' if not self.remaining else
            'partially_supplied' if self.supply else 'dispatched' if self.convoys
            else 'planned' if self.planned else 'awaiting_plan'), failure_reason=self.blockers.most_common(1)[0][0]
            if self.remaining and self.blockers else None,blockers=dict(self.blockers),
            hunger_losses=self.lost, actual_deliveries=list(self.supply))


class Measurements:
    def __init__(self):
        self.open={}
        self.serial=Counter()
        self.fingerprints={}
        self.proposed={}
        self.escorts=[]
        self.episodes=[]
        self.extra=defaultdict(list)
        self.departures={}
        self.cpu_counts=Counter()

    def attach(self, hooks):
        real=army_relief.Planner.candidates

        def candidates(planner,source,*args,**kwargs):
            result=real(planner,source,*args,**kwargs)
            if kwargs.get('selected') is None and kwargs.get('live') is None and planner.windows:
                options,reason=result
                data=availability(planner.game,planner.state,source,reason,options)
                self.escorts.append(data)
                self.cpu_counts['escort_scans']+=1
                self.cpu_counts['roster_checks']+=data['officers_total']
                for army in planner.windows:
                    episode=self.open.get(army)
                    if episode and not options and data['rejection_reason']:
                        episode.blockers[data['rejection_reason']]+=1
                for option in options[:1]:
                    ident=option['march_id']
                    row=self.open.get(ident)
                    if row:
                        row.planned=True
            return result

        hooks.enter_context(patch.object(army_relief.Planner,'candidates',candidates))

    def before_meal(self, game,state,army,journey,**values):
        if values.get('unit_kind')=='convoy':
            return None
        book=journey['supply']
        tick=values.get('absolute_tick')
        if tick is None or book['clock_tick']>=tick or book['closed_tick'] is not None:
            return None
        ident=army['id']
        if ident not in self.departures:
            self.departures[ident]=sum(army.get('departure_troops',{}).values())
        route=journey['quote']
        if army.get('status')=='returning' or book.get('retreat_requested'):
            return None
        progress=book['route_days']
        if progress>=route['days']:
            return ident,tick,len(book['refills']),book['lost']
        version=march_supply.book_version(book)
        span=march_supply.next_supply_days(state,route,army['owner'],progress)
        units=march_supply.ration_units(state,army['officers'])
        parts=values.get('parts')
        if parts is None and version==rules.CURRENT:
            parts=rules.plan(route,march_supply.travel_rules(game))
        weight=(lambda days:rules.weight(parts,progress,days)) if parts is not None else (lambda days:days)
        divisor=march_supply.book_denominator(book)
        funded=book['remaining']*divisor+book['credit_units']
        need=max(0,rules.ceil_div(units*weight(span)-funded,divisor))
        if need:
            lo,hi=1,span
            while lo<hi:
                mid=(lo+hi)//2
                if units*weight(mid)>funded:
                    hi=mid
                else:
                    lo=mid+1
            # City receipts are served before this meal; a convoy receipt at
            # the end of this simulated day uses the preceding tick boundary.
            deadline=tick+lo-1
            entry=self.open.get(ident)
            fingerprint=(book['start_tick'],tuple(route['path']))
            if not entry:
                self.serial[ident]+=1
                self.open[ident]=Episode(ident,army['owner'],self.serial[ident],tick,deadline,deadline,need)
            elif entry.owner==army['owner']:
                entry.update(need,deadline,revised=self.fingerprints.get(ident)!=fingerprint)
            self.fingerprints[ident]=fingerprint
        return ident,tick,len(book['refills']),book['lost']

    def after_meal(self, token,journey):
        if token is None:
            return
        ident,tick,length,lost=token
        entry=self.open.get(ident)
        if entry:
            entry.lost+=journey['supply']['lost']-lost
            for row in journey['supply']['refills'][length:]:
                entry.deliver(row['grain'],tick,row['kind'],row['source'])
            if not entry.remaining:
                self.finish(ident,tick)

    def transport(self,state,kind,row,values):
        ident=row.get('target_march')
        if ident is None:
            return
        entry=self.open.get(ident)
        if entry is None or entry.owner!=row['owner']:
            return
        if kind=='transport_departed' and row['id'] not in entry.convoys:
            entry.convoys.append(row['id'])
        if kind=='transport_arrived':
            grain=(values.get('amounts') or {}).get('grain',0)
            tick=row['journeys'][-1]['supply']['clock_tick']+1
            entry.deliver(grain,tick,'convoy',row['id'])
            if not entry.remaining:
                self.finish(ident,tick)

    def finish(self, ident,tick,**kwargs):
        self.episodes.append(self.open.pop(ident).row(tick,**kwargs))
        self.fingerprints.pop(ident,None)

    def turn(self,state):
        live={row['id']:row for row in state.extension['travel']['marches']}
        for ident,entry in list(self.open.items()):
            march=live.get(ident)
            if (march is None or march['owner']!=entry.owner
                    or march.get('status')=='returning' or march['supply']['retreat_requested']):
                expired=(state.turn-1)*10>=entry.deadline
                status='failed' if expired or entry.lost else 'cancelled_no_longer_needed'
                self.finish(ident,(state.turn-1)*10,unresolved=status)

    def write(self,folder,state):
        for ident in list(self.open):
            self.finish(ident,(state.turn-1)*10,unresolved='pending_at_observation_end')
        files={'escort-availability':self.escorts,'supply-episodes':self.episodes,**self.extra}
        from csv import writer
        for name,rows in files.items():
            file=folder/(name+'.csv')
            if rows:
                to_csv(file,rows)
            else:
                headers=availability_headers if name=='escort-availability' else Episode(0,'',0,0,0,0,0).row(0)
                with file.open('w',encoding='utf-8',newline='') as out:
                    writer(out,lineterminator='\n').writerow(headers)
        return dict(escort_calls=len(self.escorts),episodes=len(self.episodes), counters=self.cpu_counts,
                    march_departure_troops=sum(self.departures.values()),
                    definition='tk2-independent-march-supply-episodes-v1')


availability_headers=('city_id','faction_id','turn','officers_total','resident_officers','available_officers',
    'unarmed_officers','light_escort_candidates','heavy_escort_candidates','convoy_officers',
    'military_plan_officers','reserve_capacity','command_books','assigned_escort_id','assignment_result',
    'original_reason','rejection_reason','officer_on_march','officer_in_battle','officer_busy','officer_unhealthy',
    'delegation_restricted','officer_reserved_for_defense','officer_reserved_for_war',
    'no_legal_troop_reassignment','officer_exclusions')
