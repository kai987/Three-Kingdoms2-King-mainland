"""Paired I3/J1/J2/J3 observation with real convoy and personnel receipts."""
from argparse import ArgumentParser
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import csv
import gzip
import json
import tempfile

from common import TOOL_ROOT, to_json, to_csv
from observe import run_scenario
from observer_telemetry import config
from v221_experiments import TransportRecorder, source_identity
from remake import transport_emergency as emergency, winter_weather as weather

FOCUS = ((2028,'207-09'), (2026,'208-10'), (2026,'184-02'))
PAIRED = (*FOCUS,(2026,'263-05'),(2031,'190-01'))
LONG = ((2026,'184-02'),(2026,'208-10'))
LEVEL = dict(I3=0,J1=1,J2=2,J3=3)
STRATEGY = {211:'F3',212:'G4al'}
OUTPUT = TOOL_ROOT/'build/weather-v222'
STREAMS = dict(
    emergency_decision='emergency-transport-decisions',
    emergency_plan='emergency-evacuation-plans',
    convoy_relief_request='convoy-relief-requests',
    convoy_relief_delivery='convoy-relief-deliveries',
    convoy_terminal='convoy-terminal-events',
    emergency_refill='emergency-local-refills',
    convoy_event='convoy-events',
    convoy_ledger='convoy-ledger',
)
COMMON=('tick convoy_id owner actual_position current_phase initial_escort_troops current_escort_troops '
        'current_officers current_civil_staff current_reserve_cargo current_rations current_grain_cargo '
        'full_return_budget emergency_route_budget emergency_target emergency_reason').split()
EVENT_FIELDS={
    'emergency_decision':'decision rejection_reason available_local_supply',
    'emergency_plan':'decision rejection_reason available_local_supply route days safety',
    'convoy_relief_request':'root_relief_request_id decision rejection_reason gap source sender expected_relief eta',
    'convoy_relief_delivery':'root_relief_request_id sender actual_relief protected_return decision',
    'convoy_terminal':'terminal_status actual_terminal_tick source initial_reserves delivered remaining_gold remaining_treasure',
    'emergency_refill':'amount',
    'convoy_event':'kind_of_event source target initial_reserves bag_loaded delivered lost report_reason grain',
    'convoy_ledger':'kind_of_change before after reference',
}
UNRESOLVED_FIELDS = ('convoy_id owner actual_position current_phase terminal_status consecutive_unresolved_days '
 'consecutive_blocked_days max_consecutive_blocked_days days_since_last_effective_action days_since_delivery '
 'actual_terminal_tick actual_terminal_date initial_escort initial_reserves initial_officers initial_civil_staff '
 'current_escort current_reserves current_officers current_civil_staff escort_hunger_loss reserve_hunger_loss '
 'other_troop_loss received_grain remaining_rations remaining_cargo reason last_effective_tick '
 'delivered_tick').split()


class Recorder(TransportRecorder):
    def __init__(self,path):
        super().__init__(path)
        self.convoys={}
        self.strength={}

    def __enter__(self):
        super().__enter__()
        fields=('convoy_id tick node moved remaining_work consecutive_unresolved_days '
                'consecutive_blocked_days days_since_last_effective_action days_since_delivery '
                'current_escort current_reserves current_officers current_civil_staff escort_hunger_loss reserve_hunger_loss').split()
        for kind,name in STREAMS.items():
            fields_by_kind=(COMMON if kind!='convoy_ledger' else COMMON[:3])+EVENT_FIELDS[kind].split()
            ending='.csv.gz' if kind=='convoy_ledger' else '.csv'
            self._open(name, fields_by_kind, ending)
        self._open('convoy-resolution-daily',fields,'.csv.gz')
        return self

    def _open(self,name,fields,suffix):
        path=self.path/(name+suffix)
        handle=gzip.open(path,'wt',compresslevel=1,newline='',encoding='utf-8') if suffix.endswith('.gz') else path.open(
            'w',newline='',encoding='utf-8')
        writer=csv.DictWriter(handle,fieldnames=fields,lineterminator='\n',extrasaction='ignore')
        writer.writeheader()
        self.files[name]=(handle,writer)

    def __call__(self,kind,row):
        super().__call__(kind,row)
        if kind in STREAMS:
            export={k:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')) if isinstance(v,(list,dict)) else v
                    for k,v in row.items()}
            self.write(STREAMS[kind],export)
        if kind=='convoy_strength':
            self.strength[row['convoy_id']]=row
        elif kind=='convoy_event':
            self.transport(row)
        elif kind=='convoy_day':
            self.day(row)
        elif kind in ('convoy_terminal','convoy_relief_delivery','emergency_refill','emergency_plan'):
            facts=self.convoys.get(row['convoy_id'])
            if not facts:
                return
            if kind=='convoy_terminal':
                facts.update(terminal_status=row['terminal_status'],actual_terminal_tick=row['actual_terminal_tick'],
                    actual_position=row['actual_position'],current_phase='ended',current_escort=row['current_escort_troops'],
                    current_reserves=row['current_reserve_cargo'],current_officers=row['current_officers'],
                    current_civil_staff=row['current_civil_staff'],remaining_rations=row['current_rations'],
                    remaining_cargo=row['current_grain_cargo'])
            if kind in ('convoy_relief_delivery','emergency_refill'):
                facts['received_grain']+=row.get('actual_relief',row.get('amount',0))
            self.effective(facts,row['tick'])

    def effective(self,facts,tick):
        facts['last_effective_tick']=max(facts['last_effective_tick'],tick)
        facts['consecutive_blocked_days']=0

    def transport(self,row):
        ident=row['convoy_id']
        kind=row['kind_of_event']
        if kind=='transport_departed':
            facts=dict.fromkeys(UNRESOLVED_FIELDS)
            facts.update(convoy_id=ident,owner=row['owner'],current_phase='outbound',
                actual_position=row['actual_position'],last_effective_tick=row['tick'],
                initial_escort=row['initial_escort_troops'],initial_reserves=row['initial_reserves'],
                initial_officers=row['current_officers'],initial_civil_staff=row['current_civil_staff'],
                current_escort=row['current_escort_troops'],current_reserves=row['initial_reserves'],
                current_officers=row['current_officers'],current_civil_staff=row['current_civil_staff'],
                remaining_rations=row['current_rations'],remaining_cargo=row['current_grain_cargo'],
                escort_hunger_loss=0,reserve_hunger_loss=0,other_troop_loss=0,received_grain=0,
                consecutive_blocked_days=0,max_consecutive_blocked_days=0,consecutive_unresolved_days=0)
            self.convoys[ident]=facts
        elif kind=='transport_arrived':
            facts=self.convoys[ident]
            facts['delivered_tick']=row['tick']
            self.effective(facts,row['tick'])
        elif kind=='transport_weather':
            self.convoys[ident]['other_troop_loss']+=row['lost']

    def day(self,row):
        ident=row['convoy']; tick=row['tick']
        facts=self.convoys[ident]
        if row['moved'] or row['supply']:
            self.effective(facts,tick)
        elif row['reason']!='arrival_pending':
            facts['consecutive_blocked_days']+=1
            facts['max_consecutive_blocked_days']=max(facts['consecutive_blocked_days'],facts['max_consecutive_blocked_days'])
        idle=max(0,tick-facts['last_effective_tick'])
        facts.update(actual_position=row['node'] or row['last_node'],current_phase=row['phase'],
            remaining_rations=row['rations_after'],remaining_cargo=row['cargo_after'],reason=row['reason'],
            consecutive_unresolved_days=idle,days_since_last_effective_action=idle,
            days_since_delivery=tick-facts['delivered_tick'] if facts['delivered_tick'] is not None else None)
        strength=self.strength.pop(ident,None)
        if strength:
            for field in ('current_escort','current_reserves','current_officers','current_civil_staff'):
                facts[field]=strength[field]
            for field in ('escort_hunger_loss','reserve_hunger_loss'):
                facts[field]+=strength[field]
        self.write('convoy-resolution-daily',{**facts,**(strength or {}),'tick':tick,
            'node':row['node'],'moved':row['moved'],'remaining_work':row['end_work']})

    def summary(self,final,last_tick,catalog):
        active={r['id']:r for r in final}
        for ident,facts in self.convoys.items():
            if facts['actual_terminal_tick'] is not None:
                date=weather.date_at(catalog,max(1,facts['actual_terminal_tick']))
                facts['actual_terminal_date']='-'.join(map(str,date))
            else:
                if ident not in active:
                    raise ValueError(f'Convoy {ident} disappeared without a terminal receipt')
                facts['remaining_rations']=active[ident]['escort_bag']
                facts['remaining_cargo']=active[ident]['cargo_grain']
                if facts['consecutive_blocked_days']>=30 or last_tick-facts['last_effective_tick']>=30:
                    facts['terminal_status']='dangerous_stalled'
                else:
                    facts['terminal_status']='delivered_returning' if facts['delivered_tick'] is not None else 'not_delivered_in_transit'
            facts['days_since_last_effective_action']=max(0,(facts['actual_terminal_tick'] or last_tick)-facts['last_effective_tick'])
        rows=list(self.convoys.values())
        if rows:
            to_csv(self.path/'convoy-survival.csv',rows)
        else:
            (self.path/'convoy-survival.csv').write_text(','.join(UNRESOLVED_FIELDS)+'\n',encoding='utf-8')
        unresolved=[facts for facts in rows if facts['actual_terminal_tick'] is None]
        if unresolved:
            to_csv(self.path/'unresolved-convoy-cases.csv',unresolved)
        else:
            (self.path/'unresolved-convoy-cases.csv').write_text(','.join(UNRESOLVED_FIELDS)+'\n',encoding='utf-8')
        safe=[x for x in rows if x['terminal_status'] in ('returned_home','received_elsewhere')]
        totals=Counter(x['terminal_status'] for x in rows)
        account_fields=('initial_escort','initial_reserves','initial_officers','initial_civil_staff','current_escort',
            'current_reserves','current_officers','current_civil_staff','escort_hunger_loss','reserve_hunger_loss','other_troop_loss')
        return dict(dispatched=len(rows),ended=len(rows)-len(unresolved),safe_ended=len(safe),unresolved=len(unresolved),
            states=dict(totals),totals={k:sum(x[k] for x in rows) for k in account_fields},
            safe_personnel=sum(x['current_escort']+x['current_reserves'] for x in safe),
            in_transit_personnel=sum(x['current_escort']+x['current_reserves'] for x in unresolved),
            all_escorts_lost=sum(bool(x['initial_escort'] and x['escort_hunger_loss']>=x['initial_escort']) for x in rows),
            max_effective_stall=max((x['max_consecutive_blocked_days'] for x in rows),default=0))


def cases(wave):
    if wave=='focus':
        return [(seed,scene,212,group,60) for seed,scene in FOCUS for group in LEVEL]
    selected=LONG if wave=='long' else ((2034,'207-09'),) if wave=='holdout' else PAIRED
    return [(seed,scene,strategy,group,240 if wave=='long' else 60)
            for seed,scene in selected for strategy in STRATEGY for group in ('I3','J3')]


def run_case(output,seed,scene,strategy,group,months,*,hash_turns=False):
    level=LEVEL[group]
    parent=output/'observed'/f'{group}-{strategy}'/str(seed)/str(months)
    parent.mkdir(parents=True,exist_ok=True)
    target=parent/scene
    identity=source_identity()
    settings=config(TOOL_ROOT/'tools/economy-balance/observer-config.json')
    if (target/'run.json').is_file():
        row=json.loads((target/'run.json').read_text())
        if (row['outcome'] in ('complete','natural_end') and row['source_tree_sha256']==identity['tree_sha256']
                and (not hash_turns or 'committed_save_sha256' in row)):
            return row
        raise ValueError(f'Results exist with a different source at {target}. Select a new output.')
    with tempfile.TemporaryDirectory(prefix='.inflight-',dir=parent) as partial:
        path=Path(partial)
        with Recorder(path/scene) as record, weather.experiment(5, adjustments=weather.CORRECTIONS,
                detailed=True, observe=record), emergency.experiment(level):
            row=run_scenario(scene,seed,months,path,STRATEGY[strategy],settings,hash_turns=hash_turns)
        row.update(group=group,strategy=strategy,stage=level,weather_rules_version=221, climate_generator_version=22,
            weather_seed=weather.seed_for(seed),source_tree_sha256=identity['tree_sha256'],
            weather_totals=dict(record.metrics),seasonal_actions=dict(record.activity))
        if row['outcome'] in ('complete','natural_end'):
            row['transport_survival']=record.summary(row['terminal']['convoy_loads'],row['completed_turns']*10,
                dict(start_year=row['start_date'][0],start_month=row['start_date'][1]))
        row['streams']={name:record.counts[name] for name in record.files}
        to_json(path/scene/'run.json',row)
        (path/scene).rename(target)
    return row


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('waves',nargs='+',choices=('focus','paired','long','holdout'))
    parser.add_argument('--workers',type=int,default=6)
    parser.add_argument('--months',type=int)
    parser.add_argument('--groups',nargs='+',choices=tuple(LEVEL))
    parser.add_argument('--scenarios',nargs='+')
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--hash-turns',action='store_true')
    args=parser.parse_args()
    selection=list(dict.fromkeys((seed,scene,strategy,group,args.months or months)
                  for wave in args.waves for seed,scene,strategy,group,months in cases(wave)
                  if (not args.groups or group in args.groups) and (not args.scenarios or scene in args.scenarios)))
    if not selection:
        parser.error('empty experiment selection')
    identity=source_identity()
    to_json(args.output/'sources'/f"{identity['tree_sha256']}.json",identity)
    failed=False
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        tasks={pool.submit(run_case,args.output,*case,hash_turns=args.hash_turns):case for case in selection}
        for trial in as_completed(tasks):
            case=tasks[trial]
            try:
                row=trial.result()
                failed |= row['outcome'] not in ('complete','natural_end')
                print(*case,row['outcome'],row['completed_turns'],row['seconds'],row.get('failure') or '',flush=True)
            except Exception as error:
                failed=True
                print(*case,'error',repr(error),flush=True)
    return int(failed)


if __name__=='__main__':
    raise SystemExit(main())
