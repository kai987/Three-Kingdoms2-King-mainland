"""Summarize observed campaigns without projecting missing years or metrics."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

from common import to_csv, to_json


METRICS = {
    'economy': ('grain_stock','gold_stock','market_stock','monthly_regular_grain','monthly_gold',
                'monthly_grain_payroll','monthly_gold_payroll','population','total_land','total_industry',
                'grain_bought','emergency_grain_bought','grain_sold','ai_reserve_purchases',
                'live_factions','small_initial_factions','small_factions_surviving'),
    'military': ('active_troops','reserves','raised_troops','recruit_grain','recruit_gold',
                'postbattle_recruit_grain','postbattle_recruit_gold','ai_sorties','battles','battle_retreats',
                'battle_troops_lost','troop_losses','march_hunger_losses','march_rations','march_base_rations',
                'convoy_rations','convoy_grain_sent','convoy_grain_arrived','convoy_route_grain_loss',
                'convoy_cargo_rations','convoy_weather_grain_loss','battle_grain_bought',
                'ai_sortie_quote_blocked','ai_sortie_quotes','ai_recruit_quote_capped','ai_recruit_quotes',
                'battles_per_active_faction_year','grain_delivered_per_10000_sent'),
    'shortage': ('unpaid_city_turns','rations_missing','market_city_turns','markets_empty_samples',
                 'shortage_city_turns_per_1000','cities_with_recent_shortage','cities_empty_last_month',
                 'requested_aid','granted_aid','received_aid_grain','strategic_aid_transports',
                 'convoy_dispatched','convoy_arrived','convoy_returned','march_food_missing_days',
                 'captured_cities_recovered','median_capture_recovery_turns'),
}


def read(path):
    if not path.exists():
        return []
    with path.open(encoding='utf-8',newline='') as handle:
        return list(csv.DictReader(handle))


def wire(value):
    return float(value) if '.' in value else int(value)


def data(path):
    from statistics import median

    world=read(path/'monthly.csv')
    factions=defaultdict(dict)
    for row in read(path/'factions.csv'):
        factions[int(row['elapsed_months'])][row['faction']]=int(row['cities'])
    opening=factions[0]
    small={key for key,size in opening.items() if key!='neutral' and 0<size<=3}
    city_by_month=defaultdict(list)
    for row in read(path/'cities.csv'):
        city_by_month[int(row['elapsed_months'])].append(row)
    recovered=read(path/'capture-recovery.csv')
    last_shortages={}
    faction_months=0
    results={}
    selected={12,36,60,120,240,int(world[-1]['elapsed_months'])}
    for row in world:
        month=int(row['elapsed_months'])
        live={key for key,cities in factions[month].items() if key!='neutral' and cities>0}
        if month:
            faction_months+=len(live)
        recent=empty=0
        for city in city_by_month[month]:
            key=city['city']
            shortages=int(city['unpaid_city_turns'])
            recent+=shortages>last_shortages.get(key,0)
            empty+=city['owner']!='neutral' and int(city['grain_stock'])==0
            last_shortages[key]=shortages
        if month not in selected:
            continue
        values={key:wire(row[key]) for keys in METRICS.values() for key in keys if key in row}
        periods=values.get('market_city_turns',0)
        values.update(live_factions=len(live),small_initial_factions=len(small),
            small_factions_surviving=len(small&live),cities_with_recent_shortage=recent,
            cities_empty_last_month=empty,
            shortage_city_turns_per_1000=round(values['unpaid_city_turns']*1000/periods,3) if periods else None,
            battles_per_active_faction_year=round(values['battles']*12/faction_months,3) if faction_months else None)
        sent=values.get('convoy_grain_sent')
        values['grain_delivered_per_10000_sent']=round(values['convoy_grain_arrived']*10_000/sent,2) if sent else None
        take=[int(entry['sampled_turn'])-int(entry['capture_turn']) for entry in recovered
              if entry['result']=='one_month_rations' and int(entry['sampled_turn'])<=int(row['elapsed_turns'])+1]
        values.update(captured_cities_recovered=len(take),median_capture_recovery_turns=median(take) if take else None)
        results[month]=values
    return results


def export(root, output, heads):
    runs, phases = [], {}
    for path in sorted(root.glob('*/*/*/*/run.json')):
        group,seed,horizon,scenario=path.relative_to(root).parts[:4]
        run=json.loads(path.read_text(encoding='utf-8'))
        assert run['scenario']==scenario and run['seed']==int(seed) and run['requested_months']==int(horizon)
        year,month=map(int,scenario.split('-')[:2])
        runs.append(dict(group=group, head=heads[group], start_date=[year,month,1],
                         **{key:value for key,value in run.items() if key not in ('group','head','start_date')}))
        for elapsed, line in data(path.parent).items():
            phases[group,int(seed),int(horizon),scenario,elapsed] = dict(line,outcome=run['outcome'])
    output.mkdir(parents=True,exist_ok=True)
    for name, metrics in METRICS.items():
        def lines():
            for (group,seed,horizon,scenario,month), values in sorted(phases.items()):
                baseline=phases.get(('A',seed,horizon,scenario,month),{})
                yield dict(group=group,seed=seed,scenario=scenario,requested_months=horizon,
                           sampled_month=month,outcome=values['outcome'],
                           **{k:values.get(k) for k in metrics},
                           **{k+'_delta_vs_A':round(values[k]-baseline[k],3)
                              if values.get(k) is not None and baseline.get(k) is not None else None
                              for k in metrics})
        to_csv(output/f'long-term-{name}-comparison.csv',lines())
    to_json(output/'simulation-manifest.json',
        dict(groups=heads,run_count=len(runs),outcomes=dict(Counter(run['outcome'] for run in runs)),runs=runs))
    print('Observed campaigns:',len(runs),dict(Counter(run['outcome'] for run in runs)))


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('observed',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--heads',required=True,type=Path)
    arguments=parser.parse_args()
    export(arguments.observed,arguments.output,json.loads(arguments.heads.read_text(encoding='utf-8')))
