"""Execute controlled regional-market comparisons with read-only transaction capture."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import csv
import gzip
import json

from common import TOOL_ROOT, to_json
from observe import RecordedCampaign, run_scenario
from observer_telemetry import config
from remake import economic_regions, facilities, grain_units, market_pricing, transport_emergency, winter_weather
from v221_experiments import source_identity
from v222_experiments import Recorder as TransportRecorder, STRATEGY

ROOT = TOOL_ROOT / 'build/regional-economy-v301'
FIRST = ((2027,'190-01'), (2028,'207-09'), (2026,'208-10'), (2026,'263-05'))
WINTER = ((2026,'184-02'), (2031,'190-01'), *FIRST[1:])
LONG = ((2026,'184-02'), (2026,'208-10'))
STAGES = ('R0','R1','R2','R3')

TRANSACTION_FIELDS = ('turn year month day city owner kind grain gold rate channel payer opening_stock stock capacity '
                      'monthly_supply last_restock_month restocked purchased sold overflow').split()
CITY_FIELDS = ('turn year month day city region owner town stock capacity supply stock_coverage band base_buy '
               'base_sell season adjustment buy sell purchased_month sold_month').split()
REGION_FIELDS = ('turn year month day region markets stock capacity supply stock_coverage empty severe ample '
                  'buy_mean sell_mean buy_min buy_max sold_month purchased_month in_transit').split()


def stage_cases(wave):
    if wave == 'initial':
        return [(seed, scenario, 211, group, 60, 0) for seed,scenario in FIRST for group in STAGES]
    if wave == 'winter':
        return [(seed, scenario, policy, group, 60, 221) for seed,scenario in WINTER
                for policy in (211,212) for group in ('R0','R2')]
    if wave == 'holdout':
        return [(2034, '207-09', 211, group, 60, 221) for group in ('R0','R2')]
    return [(seed, scenario, 211, group, 240, 221) for seed,scenario in LONG for group in ('R0','R2')]


class RegionalRecorder:
    def __init__(self, writes):
        self.writes=writes
        self.pending=[]
        self.counts=Counter()
        self.previous={}
        self.region_month={}

    def write(self, name, row):
        self.writes[name].writerow(row)
        self.counts[name]+=1

    def event(self, kind, row):
        self.pending.append((kind,row))

    def capture(self, game, state):
        dates={key:getattr(state,key) for key in ('turn','year','month','day')}
        totals=defaultdict(Counter)
        for city, market in state.extension['grain_market'].items():
            town=facilities._pool(state)['cities'][city]['town']
            region=economic_regions.region(city)
            season=facilities.MARKET_MONTHLY_ADJUSTMENTS[state.month-1]
            stock,supply=market['stock'],market['monthly_supply']
            price=market_pricing.snapshot(game,state,city,town)
            if price:
                buy,sell,band,adjust=(price[k] for k in ('buy','sell','band','adjustment'))
            else:
                buy=facilities.market_rate(game,town,'buy',state.month,state=state)
                sell=facilities.market_rate(game,town,'sell',state.month,state=state)
                band=market_pricing.BANDS[market_pricing.inventory_band(stock,supply)]
                adjust=0
            base_buy,base_sell=(facilities.market_base(game,town,d,state) for d in ('buy','sell'))
            base=dict(dates,city=city,region=region,owner=state.cities[city].owner,town=town,stock=stock,
                capacity=market['capacity'],supply=supply,stock_coverage=round(stock/supply,6),band=band,
                base_buy=base_buy,base_sell=base_sell,season=season,adjustment=adjust,buy=buy,sell=sell,
                purchased_month=market['purchased'],sold_month=market['sold'])
            self.write('city-market-prices.csv.gz',base)
            current=(buy,sell,band)
            if self.previous.get(city)!=current:
                self.write('market-price-changes.csv.gz',base)
                self.previous[city]=current
            r=totals[region]
            r.update(markets=1,stock=stock,capacity=market['capacity'],supply=supply,empty=int(stock==0),
                     severe=int(stock*4<supply),ample=int(stock>=2*supply),buy_sum=buy,sell_sum=sell,
                     sold_month=market['sold'],purchased_month=market['purchased'])
            r['buy_min']=min(r.get('buy_min',buy),buy)
            r['buy_max']=max(r['buy_max'],buy)
        for row in state.extension['logistics']['convoys']:
            totals[economic_regions.region(row['target'])]['in_transit']+=row['cargo']['grain']
        for name,r in sorted(totals.items()):
            if not r['markets']:
                continue
            sample=dict(dates,region=name,**r,stock_coverage=round(r['stock']/r['supply'],6),
                        buy_mean=round(r['buy_sum']/r['markets'],6),sell_mean=round(r['sell_sum']/r['markets'],6))
            self.write('regional-market-daily.csv.gz',sample)
            day=state.year*12+state.month
            if self.region_month.get(name)!=day:
                self.write('regional-market-monthly.csv',sample)
                self.region_month[name]=day

    def attach(self, game, command, payload, revision):
        try:
            result=RecordedCampaign._v301_command(game,command,payload,revision)
        except BaseException:
            self.pending.clear()
            raise
        for event,row in self.pending:
            if event=='stock_flow':
                self.write('market-stock-flow.csv.gz',row)
            else:
                self.write('regional-orders.jsonl',dict(event=event,**row))
        self.pending.clear()
        if command in ('new','observe_turn'):
            with grain_units.using(game.state):
                self.capture(game,game.state)
        return result


class JsonLines:
    def __init__(self, stream):
        self.stream=stream

    def writerow(self, row):
        self.stream.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')


def run_case(output, case):
    from contextlib import ExitStack
    seed,scene,policy,group,months,weather=case
    identity=source_identity()
    directory=output/'observed'/f'w{weather}'/f'{group}-{policy}'/str(seed)/str(months)
    directory.mkdir(parents=True,exist_ok=True)
    target=directory/scene
    if (target/'run.json').is_file():
        result=json.loads((target/'run.json').read_text())
        if result['outcome'] in ('complete','natural_end'):
            return result
        raise ValueError(f'Existing failed experiment: {target}')
    with TemporaryDirectory(dir=directory,prefix='.running-') as temporary:
        parent=Path(temporary)
        raw=parent/scene
        with TransportRecorder(raw) as transport, ExitStack() as stack:
            writers={}
            for name,fields in (
                    ('market-stock-flow.csv.gz',TRANSACTION_FIELDS), ('city-market-prices.csv.gz',CITY_FIELDS),
                    ('market-price-changes.csv.gz',CITY_FIELDS), ('regional-market-daily.csv.gz',REGION_FIELDS),
                    ('regional-market-monthly.csv',REGION_FIELDS)):
                opener=gzip.open if name.endswith('.gz') else open
                stream=stack.enter_context(opener(raw/name,'wt',newline='',encoding='utf-8'))
                writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore',lineterminator='\n')
                writer.writeheader()
                writers[name]=writer
            writers['regional-orders.jsonl']=JsonLines(stack.enter_context((raw/'regional-orders.jsonl').open('w',encoding='utf-8')))
            tracker=RegionalRecorder(writers)
            original=RecordedCampaign.command
            def command(game, action, payload, revision):
                return tracker.attach(game,action,payload,revision)
            stack.enter_context(patch.object(RecordedCampaign,'_v301_command',original,create=True))
            stack.enter_context(patch.object(RecordedCampaign,'command',command))
            stack.enter_context(market_pricing.observing(tracker.event))
            stack.enter_context(market_pricing.experiment(STAGES.index(group)))
            stack.enter_context(winter_weather.experiment(5 if weather else 0,adjustments=winter_weather.CORRECTIONS if weather else 0,
                                                         detailed=True,observe=transport))
            stack.enter_context(transport_emergency.experiment(3 if weather else 0))
            settings=config(TOOL_ROOT/'tools/economy-balance/observer-config.json')
            result=run_scenario(scene,seed,months,parent,STRATEGY[policy],settings)
        result.update(group=group,strategy=policy,weather=weather,weather_seed=winter_weather.seed_for(seed) if weather else None,
                      emergency=222 if weather else 0,source_tree_sha256=identity['tree_sha256'],
                      market_stage=STAGES.index(group),regional_streams=dict(tracker.counts))
        if result['outcome'] in ('complete','natural_end'):
            result['transport_survival']=transport.summary(result['terminal']['convoy_loads'],
                result['completed_turns']*10,dict(start_year=result['start_date'][0],start_month=result['start_date'][1]))
        to_json(raw/'run.json',result)
        raw.rename(target)
    return result


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('waves',nargs='+',choices=('initial','winter','long','holdout'))
    parser.add_argument('--groups',nargs='+',choices=STAGES)
    parser.add_argument('--workers',type=int,default=6)
    parser.add_argument('--output',type=Path,default=ROOT)
    parser.add_argument('--scenarios',nargs='+')
    parser.add_argument('--months',type=int)
    args=parser.parse_args()
    cases=[(s,c,p,g,args.months or m,w) for wave in args.waves for s,c,p,g,m,w in stage_cases(wave)
           if (not args.groups or g in args.groups) and (not args.scenarios or c in args.scenarios)]
    identity=source_identity()
    to_json(args.output/'sources'/f"{identity['tree_sha256']}.json",identity)
    failed=False
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        tasks={pool.submit(run_case,args.output,case):case for case in dict.fromkeys(cases)}
        for future in as_completed(tasks):
            try:
                result=future.result()
                print(*tasks[future],result['outcome'],result['completed_turns'],result.get('failure') or '',flush=True)
                failed|=result['outcome'] not in ('complete','natural_end')
            except Exception as error:
                failed=True
                print(*tasks[future],repr(error),flush=True)
    return int(failed)


if __name__=='__main__':
    raise SystemExit(main())
