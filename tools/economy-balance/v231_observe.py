"""Measure actual supply episodes and seasonal campaign outcomes."""
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import ExitStack
import gzip
import json
from pathlib import Path
from unittest.mock import patch

from common import ROOT, TOOL_ROOT, HeadlessCampaign, git, sha256, to_json
from observe import RecordedCampaign, run_scenario
from observer_v212 import PublishedMeasurements
from remake import army_relief, city_economy, grain_market, grain_units, logistics
from remake import logistics_rules, march_supply, market_pricing, strategic_granary, winter_weather
from v222_experiments import STRATEGY
from v23_climate import FEATURES
from v23_observe import Record
from v302_audit import Audit

DEFAULT_OUT = TOOL_ROOT/'build/winter-agriculture-v231'
OPTIONS = {'F0':None, 'F1':FEATURES['W3'], 'F2':FEATURES['W4'],
           'F3':FEATURES['W3'], 'F4':FEATURES['W4'], 'W2':FEATURES['W2'], 'dry':None}
QUICK=((2026,'184-02',211),(2034,'207-09',211),(2026,'208-10',211),
       (2026,'208-10',212),(2026,'263-05',211))
FIVE=(*QUICK,(2026,'184-02',212))
LONG=((2026,'184-02',211),(2026,'208-10',211),(2026,'208-10',212))
HOLDOUT=((2043,'184-02',211),(2044,'208-10',212))
RUNNER_HASH=sha256(Path(__file__).read_bytes())


def cases(wave,source):
    if wave=='smoke':
        specs=[('F2',QUICK[2],2),('F4',QUICK[2],2)]
    elif wave=='quick':
        specs=[(group,key,24) for key in QUICK for group in ('F1','F2','F3','F4')]
    elif wave=='five':
        focused=[key for key in FIVE if key[1] in ('207-09','208-10')]
        specs=[(group,key,60) for key in FIVE for group in ('F2','F4')]
        specs.extend((group,key,60) for key in focused for group in ('F1','F3'))
        specs.append(('dry',(2031,'190-01',211),60))
    elif wave=='long':
        specs=[('F4',key,240) for key in LONG]
        specs.extend((group,LONG[1],240) for group in ('F2','W2'))
    elif wave=='holdout':
        specs=[(group,key,60) for key in HOLDOUT for group in ('F2','F4')]
        specs.append(('F4',(2041,'184-02',211),60))
    elif wave=='root':
        specs=[('F2',LONG[1],240)]
    else:
        raise ValueError(wave)
    return [dict(wave=wave,group=group,seed=key[0],scenario=key[1],strategy=key[2],months=months,source=source)
            for group,key,months in specs]


class CampaignObservation(Record):
    """All evidence is emitted from the committed command or a real ledger callback."""
    def __init__(self,stream,*,flows):
        super().__init__(stream)
        self.flows=flows
        self.armies=PublishedMeasurements()
        self.weather_costs={}
        self.actual_cargo=0
        self.extra_cargo=0
        self.incident_cargo=0
        self.checkpoint_cities=set()
        self.turn_shortages=[]
        self.planning_seen=set()

    def writerow(self,row):
        if self.flows and row['resource'] in ('grain','ownership'):
            self.write('warehouse_posting',row)
        else:
            super().writerow(row)

    def weather(self,kind,row):
        if kind=='travel' and row['unit_kind']=='convoy':
            self.weather_costs[row['unit_id'],row['tick']]=(row['normal_cargo_weight'],row['extra_grain'])
        elif kind=='cargo':
            normal, _ = self.weather_costs[row['unit_id'],row['tick']]
            base=logistics_rules.cargo_loss(row['grain'],normal,row['previous_credit'])[0]
            actual, _=logistics_rules.cargo_loss(row['grain'],row['rate'],row['previous_credit'])
            assert actual==row['lost'] and actual>=base
            self.actual_cargo+=actual
            self.extra_cargo+=actual-base
            self.write('convoy_weather_cargo',dict(row,base_loss=base,weather_extra_loss=actual-base))
        elif kind=='convoy_day':
            weights=self.weather_costs.pop((row['convoy'],row['tick']),None)
            self.incident_cargo+=row['incident_loss']
            self.write('convoy_grain_daily',dict(row,weather_extra_rations=weights[1] if weights else None,
                            base_rations=row['paid']-weights[1] if weights else None))
        super().weather(kind,row)

    def observe_transport(self,state,kind,row,values):
        amounts=row['cargo'] if values.get('amounts') is None else values['amounts']
        reason=values.get('reason','outbound')
        self.armies.transport(state,kind,row,values)
        super().track_convoy(state,kind,row,reason,amounts)
        if row['target_march'] is None:
            return
        first=row['journeys'][0]
        relief=row.get('relief',{})
        self.write('army_convoy',dict(convoy=row['id'],army=row['target_march'],owner=row['owner'],
            event=kind,turn=state.turn,tick=row['journeys'][-1]['supply']['clock_tick']+1,
            source=row['source'],target=row['target'],year=state.year,month=state.month,day=state.day,
            reason=reason,grain=amounts['grain'],first_arrival_turn=first['arrival_turn'],
            original_eta=row.get('original_eta'),rations=first['supply']['loaded'],
            original_request=relief.get('need_id'),original_need_deadline=relief.get('deadline')))

    def attach(self,stack):
        advance, event = march_supply.advance_unit, logistics._event
        settle = city_economy.settle_turn_grain
        create_planner = army_relief.Planner.__init__
        estimates = army_relief.Planner.estimates
        candidates = army_relief.Planner.candidates

        def meal(game,state,unit,journey,*args,**values):
            detail=self.armies.before_meal(game,state,unit,journey,**values)
            result=advance(game,state,unit,journey,*args,**values)
            self.armies.after_meal(detail,journey)
            return result

        def transport(game,state,kind,row,**values):
            self.observe_transport(state,kind,row,values)
            return event(game,state,kind,row,**values)

        def planner_init(planner,game,state,owner):
            create_planner(planner,game,state,owner)
            for ident,need in planner.demands.items():
                key=(state.turn,ident,need.deadline,need.required)
                if need.required and key not in self.planning_seen:
                    self.planning_seen.add(key)
                    self.write('army_demand_observed',dict(turn=state.turn,army=ident,owner=owner,
                        required=need.required,deadline=need.deadline,urgent=need.urgent,
                        stopped=need.stopped,window_count=len(planner.windows.get(ident,()))))

        def published_estimates(planner,ident,**values):
            found=list(estimates(planner,ident,**values))
            need=planner.demands.get(ident)
            if need is not None and need.required and not values and found:
                covered=sum(grain for eta,grain in found if eta<=need.deadline)
                key=(planner.state.turn,ident,need.deadline,need.required,covered)
                if key not in self.planning_seen:
                    self.planning_seen.add(key)
                    self.write('army_reliable_inbound',dict(turn=planner.state.turn,army=ident,
                        owner=planner.owner,required=need.required,deadline=need.deadline,covered=covered,
                        uncovered=max(0,need.required-covered)))
            return iter(found)

        def observed_candidates(planner,source,*args,**kwargs):
            found,reason=candidates(planner,source,*args,**kwargs)
            if found:
                army=found[0]['march_id']
                episode=self.armies.open.get(army)
                if episode is not None:
                    episode.planned=True
            return found,reason

        def city_meal(game,state):
            if self.flows:
                self.city_meal(game,state)
            return settle(game,state)

        for obj,name,hook in (
                (march_supply,'advance_unit',meal),(logistics,'_event',transport),
                (army_relief.Planner,'__init__',planner_init),(army_relief.Planner,'estimates',published_estimates),
                (army_relief.Planner,'candidates',observed_candidates),(city_economy,'settle_turn_grain',city_meal)):
            stack.enter_context(patch.object(obj,name,hook))

    def city_meal(self,game,state):
        active=city_economy.stationed_troops(game,state)
        military=city_economy.garrison_grain(game,state,stationed=active)
        development=state.extension['city_development']['cities']
        installment={11:1,21:2,1:3}[state.day]
        for key,troops in active.items():
            city=state.cities[key]
            population=development[key]['population']
            residents=city_economy.civilian_grain(population,city_economy.town_level(game,state,key),state=state)
            total=city_economy.turn_rations(residents+military[key],installment)
            resident_due=city_economy.turn_rations(residents,installment)
            missing=max(0,total-city.grain)
            self.write('city_rations',dict(turn=state.turn,year=state.year,month=state.month,day=state.day,
                city=key,owner=city.owner,stock=city.grain,required=total,paid=total-missing,missing=missing,
                resident_due=resident_due,garrison_due=total-resident_due,population=population,active=troops,
                reserves=city.reserves,market_stock=grain_market.row(state,key)['stock']))
            if missing and missing*4>=total:
                self.turn_shortages.append((key,missing))

    def after_command(self,game,old_state,checkpoint_dir):
        state=game.state
        self.armies.turn(state)
        self.planning_seen.clear()
        if checkpoint_dir is not None and old_state is not None and len(self.checkpoint_cities)<8:
            for key,missing in sorted(self.turn_shortages,key=lambda row:-row[1]):
                region=game.catalog.climate.cities[key]['climate_region_id']
                if region!='southern_basins' or key in self.checkpoint_cities:
                    continue
                if len(self.checkpoint_cities)>=8:
                    break
                self.checkpoint_cities.add(key)
                name=f'{old_state.turn:04d}-{key}.json.gz'
                checkpoint_dir.mkdir(parents=True,exist_ok=True)
                original=HeadlessCampaign(game.catalog,record_journal=False)
                original.state=old_state
                with gzip.open(checkpoint_dir/name,'wt',compresslevel=2,encoding='utf-8') as saved:
                    json.dump(original.export_save(compact=True),saved,ensure_ascii=False)
                self.write('shortage_checkpoint',dict(city=key,turn=old_state.turn,missing=missing,file=name))
        self.turn_shortages.clear()


def run(output,case,*,observe=True):
    group=case['group']
    result_path=(output/'campaigns'/case['wave']/group/
                 f"{case['scenario']}-{case['seed']}-{case['strategy']}")
    final=result_path/'run-v231.json'
    if final.is_file():
        existing=json.loads(final.read_text())
        if (existing['outcome'] in ('complete','natural_end') and existing['source']==case['source']
                and existing['runner_sha256']==RUNNER_HASH):
            return existing
    result_path.mkdir(parents=True,exist_ok=True)
    initial=dict(weather_rules_version=0 if group=='dry' else 221 if group=='F0' else 23,
                 transport_emergency_rules_version=222)
    if OPTIONS[group]:
        from remake.winter_climate import flags
        initial['weather_options']=flags(*OPTIONS[group])
    if group in ('F3','F4'):
        initial['weather_forecast_version']=231
    activate=initial['weather_rules_version']!=0
    flows=case['scenario']=='208-10' and case['strategy']==211
    focus=flows and case['months']==240
    assert git('rev-parse','HEAD').decode().strip()==case['source']
    original=RecordedCampaign.command
    with gzip.open(result_path/'events.jsonl.gz','wt',compresslevel=2,encoding='utf-8') as stream, ExitStack() as stack:
        record=CampaignObservation(stream,flows=flows)
        audit=Audit(record)
        game_ref=[]

        def capture(game,action,payload,revision):
            if not game_ref:
                game_ref.append(game)
            old=game.state
            if action=='new':
                payload=dict(payload,**initial)
            if observe:
                with audit.command(game,action):
                    result=original(game,action,payload,revision)
                record.after_command(game,old,result_path/'checkpoints' if focus else None)
            else:
                result=original(game,action,payload,revision)
            return result

        stack.enter_context(patch.object(RecordedCampaign,'command',capture))
        stack.enter_context(market_pricing.experiment(2))
        stack.enter_context(strategic_granary.experiment(proactive=True,winter=True,relay=False))
        stack.enter_context(winter_weather.experiment(5 if activate else 0,
            adjustments=winter_weather.CORRECTIONS if activate else 0,detailed=observe,
            observe=record.weather if observe else None))
        if observe:
            record.attach(stack)
            stack.enter_context(audit.install())
        result=run_scenario(case['scenario'],case['seed'],case['months'],result_path,STRATEGY[case['strategy']])
        game=game_ref[0]
        if result['outcome'] in ('complete','natural_end'):
            checkpoint=game.export_save(compact=True)
            with gzip.open(result_path/'terminal-save.json.gz','wt',compresslevel=2,encoding='utf-8') as saved:
                json.dump(checkpoint,saved,ensure_ascii=False)
            if observe:
                result['military_episodes']=record.armies.write(result_path,game.state)
    if audit.errors:
        raise ValueError(f'Warehouse reconciliation mismatches: {audit.errors}')
    result.update(case,options=initial,output=str(result_path.relative_to(output)),
                  observed=observe,warehouse_audit=audit.metrics(), measurements=record.finish(),
                  cargo_audit=dict(route_weather_inclusive=record.actual_cargo,route_weather_increment=record.extra_cargo,
                                  incident_weather=record.incident_cargo) if activate and observe else None,
                  runner_sha256=RUNNER_HASH,
                  map_sha256=sha256((ROOT/'game/assets/map-campaign.png').read_bytes()))
    to_json(final,result)
    return result


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('waves',nargs='+',choices=('quick','five','long','holdout','root','smoke'))
    parser.add_argument('--output',type=Path,default=DEFAULT_OUT)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--group',action='append',choices=OPTIONS)
    parser.add_argument('--no-observation',action='store_true')
    args=parser.parse_args()
    source=git('rev-parse','HEAD').decode().strip()
    plan=[case for wave in args.waves for case in cases(wave,source)
          if args.group is None or case['group'] in args.group]
    to_json(args.output/('plan-'+'-'.join(args.waves)+'.json'),plan)
    failures=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(run,args.output,case,observe=not args.no_observation):case for case in plan}
        for future in as_completed(futures):
            row=future.result()
            print(json.dumps({key:row.get(key) for key in ('wave','group','scenario','seed',
                'strategy','completed_turns','outcome','failure','source','output')},ensure_ascii=False),flush=True)
            if row['outcome'] not in ('complete','natural_end'):
                failures.append(row)
    return bool(failures)


if __name__=='__main__':
    raise SystemExit(main())
