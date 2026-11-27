"""Recalculate V2.3 summaries from observed city, market and campaign accounts."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import csv
import gzip
import json
from pathlib import Path
import shutil
from statistics import fmean

from common import TOOL_ROOT, git, sha256, to_csv, to_json
from v23_climate import FEATURES

MAIN_FIELDS = {
    'unpaid_city_turns':'shortage_city_turns', 'rations_missing':'grain_gap',
    'convoy_hunger_losses':'convoy_hunger_losses', 'convoy_returned':'convoy_returned',
    'convoy_grain_arrived':'convoy_grain_arrived', 'grain_stock':'grain_stock',
    'market_stock':'market_stock', 'market_monthly_supply':'market_monthly_supply',
    'battles':'battles', 'population':'population', 'active_troops':'active_troops',
    'gold_stock':'gold_stock', 'total_land':'total_land', 'ai_sorties':'ai_sorties',
    'convoy_dispatched':'convoy_dispatched', 'convoy_weather_grain_loss':'convoy_weather_grain_loss',
}
WATCH = {'shortage_city_turns':(20,'relative_up'), 'grain_gap':(20,'relative_up'),
         'winter_timely':(5,'points_down'), 'small_survival':(10,'points_down'),
         'mean_turn_cpu':(30,'relative_up')}
NORTH = {'liaodong','northern_frontier','northwest','qinling_highlands','north_china','central_plains'}
IDENTITY = ('wave','group','scenario','seed','strategy')
EXPECTED_RUNS = {'quick':26, 'five':17, 'long':6, 'holdout':4, 'exceptional':2, 'locality':2}
REQUIRED_GATES = {'native-build','node-tests','pyodide-final','rust-crate','rust-fmt','wasm-parity',
                  'web-build','python-campaign','rust-campaign','browser-full','browser-resupply',
                  'browser-v23-recheck','weather-save-compatibility','weather-cross-save'}
REGIONAL_FIELDS = ('population','grain_stock','market_stock','market_supply','unpaid_city_turns','monthly_regular_grain')


def rows(path):
    with path.open(encoding='utf-8',newline='') as stream:
        return list(csv.DictReader(stream))


def emit(output,name,records, fields=()):
    sequence=list(records)
    if sequence:
        to_csv(output/name,sequence)
    else:
        (output/name).write_text(','.join(fields)+'\n',encoding='utf-8')


def portable_bytes(raw):
    """Remove user-specific path prefixes from logs published on GitHub."""
    return raw.replace(str(TOOL_ROOT).encode(), b'<WORKTREE>').replace(str(Path.home()).encode(), b'<HOME>')


def published_gates(source):
    gates={}
    for path in sorted((source/'checks').glob('*.json')):
        gate=json.loads(path.read_text(encoding='utf-8'))
        if 'log' not in gate:
            continue
        raw=(source/gate['log']).read_bytes()
        assert raw and sha256(raw)==gate['log_sha256'], path.name
        public=portable_bytes(raw)
        if public!=raw:
            gate.update(original_log_sha256=gate['log_sha256'], log_sha256=sha256(public), log_bytes=len(public))
        gates[path.stem]=json.loads(portable_bytes(json.dumps(gate,ensure_ascii=False).encode()))
    return gates


def ident(run):
    return {key: run[key] for key in IDENTITY}


def at_time(history, month):
    return [row for row in history if int(row['elapsed_months']) == month]


def survival(opening, ending, cohort):
    live={row['faction'] for row in ending if int(row['cities'])>0}
    keys={row['faction'] for row in opening if row['faction']!='neutral' and cohort(row)}
    return (100*len(live & keys)/len(keys)) if keys else None


class Case:
    def __init__(self,path,city_regions,crop_regions):
        self.run=json.loads(path.read_text())
        self.folder=path.parent
        self.city_regions=city_regions
        self.crop_regions=crop_regions
        root=self.folder/self.run['scenario']
        self.months={int(row['elapsed_months']):row for row in rows(root/'monthly.csv')}
        self.ending=max(self.months)
        self.factions=rows(root/'factions.csv')
        self.northern=Counter()
        self.holdings=Counter()
        self.regions=defaultdict(Counter)
        for row in rows(root/'cities.csv'):
            region=city_regions[row['city']]
            month=int(row['elapsed_months'])
            self.regions[month,region].update({key:int(row[key]) for key in REGIONAL_FIELDS})
            if month==0:
                self.holdings[row['owner']]+=1
                self.northern[row['owner']]+=region in NORTH
        self.production=defaultdict(Counter)
        self.market=defaultdict(Counter)
        self.prices={}
        self.harvest=defaultdict(Counter)
        self.years=[]
        self.preparation=[]
        self.disasters=[]
        self.read_accounts(city_regions)

    def read_accounts(self,city_regions):
        counts=self.run['measurements']['events']
        with gzip.open(self.folder/'events.jsonl.gz','rt',encoding='utf-8') as stream:
            for line in stream:
                row=json.loads(line)
                kind=row['kind']
                if kind=='agricultural_income':
                    assert row['adjusted']==row['regular']*row['factor']//100
                    city=self.production[row['year'],row['city'],row['region']]
                    city.update(regular=row['regular'], adjusted=row['adjusted'],
                                affected_months=row['factor']!=100,
                                added=max(0,row['adjusted']-row['regular']),
                                reduced=max(0,row['regular']-row['adjusted']))
                elif kind=='warehouse_posting' and row['category']=='regular_income' and not counts.get('agricultural_income'):
                    # W0 and dry observe the actual positive posting with factor 100.
                    year=row['year']+(row['month']==12)
                    self.production[year,row['city'],self.crop_regions[row['city']]].update(
                        regular=row['delta'],adjusted=row['delta'])
                elif kind=='agriculture_year':
                    self.years.append({**ident(self.run),**{k:v for k,v in row.items() if k!='kind'}})
                elif kind=='agricultural_preparation':
                    self.preparation.append({**ident(self.run),**{k:v for k,v in row.items() if k!='kind'}})
                elif kind=='market_price':
                    self.prices[row['turn'],row['city']]=row['buy']
                elif kind=='market_restock':
                    assert row['opening_stock']-row['overflow']+row['restocked']==row['stock']
                    market=self.market[row['year'],row['city'],self.crop_regions[row['city']]]
                    market.update(
                        issued=row['restocked'], overflow=row['overflow'], observations=1,
                        supply=row['monthly_supply'], stock=row['stock'], capacity=row['capacity'])
                    market['final_stock']=row['stock']
                    market['final_capacity']=row['capacity']
                elif kind=='warehouse_posting' and row['category'] in ('harvest_bonus','civil_bonus'):
                    self.harvest[row['year'],row['city'],self.crop_regions[row['city']]][row['category']]+=row['delta']
                elif kind=='city_disaster':
                    self.disasters.append({**ident(self.run), **{k:v for k,v in row.items() if k!='kind'},
                                           'region':city_regions[row['city']]})
        if self.run['wave']=='locality':
            audit=self.run['warehouse_audit']['categories']
            actual=next((item['amount'] for item in audit if item['resource']=='grain'
                         and item['category']=='facilities.month_rollover' and item['direction']=='debit'),0)
            assert sum(event['grain'] for event in self.disasters)==actual

    def score(self,month):
        world=self.months[month]
        turn=int(world['elapsed_turns'])+1
        opening=at_time(self.factions,0)
        closing=at_time(self.factions,month)
        orders=[row for row in self.run['measurements']['winter_army_orders']
                if row['opened']<=turn and row['deadline']<=turn]
        timely=sum(row['actual'] is not None and row['actual']<=row['deadline'] and row['received']>0
                   for row in orders)
        return dict(elapsed_months=month, **{target:int(world[key]) for key,target in MAIN_FIELDS.items()},
                    winter_orders=len(orders),winter_arrived_on_time=timely,
                    winter_timely=100*timely/len(orders) if orders else None,
                    small_survival=survival(opening,closing,lambda row:1<=int(row['cities'])<=3),
                    northern_survival=survival(opening,closing,lambda row:self.northern[row['faction']]*2>=self.holdings[row['faction']]>0),
                    mean_turn_cpu=self.run['performance']['mean_turn_cpu_seconds'] if month==self.ending else None)


def difference(base,value,mode):
    if base is None or value is None:
        return None,'unmeasured'
    if mode=='points_down':
        return base-value, 'measured'
    if base==0:
        return None, 'zero_baseline_increase' if value>0 else 'zero_both'
    return 100*(value-base)/base,'measured'


def paired(cases):
    cohort=defaultdict(dict)
    for case in cases:
        run=case.run
        cohort[run['wave'],run['scenario'],run['seed'],run['strategy']][run['group']]=case
    pairs, alerts, quotes, regional = [], [], [], []
    for _, groups in sorted(cohort.items()):
        if 'W0' not in groups:
            continue
        old=groups['W0']
        for group, case in sorted(groups.items()):
            if group=='W0':
                continue
            month=max(old.months.keys() & case.months.keys())
            a,b=old.score(month),case.score(month)
            pairs.append({**ident(case.run),'common_months':month,
                **{f'W0_{key}':a[key] for key in a if key!='elapsed_months'},
                **{f'{key}':b[key] for key in b if key!='elapsed_months'}})
            paired_quotes=old.prices.keys() & case.prices.keys()
            boundary=int(case.months[month]['elapsed_turns'])+1
            by_region=defaultdict(list)
            for turn,city in sorted(paired_quotes):
                if turn<=boundary:
                    by_region[case.city_regions[city]].append((old.prices[turn,city],case.prices[turn,city]))
            for region, values in sorted(by_region.items()):
                before, after = (fmean(pair[index] for pair in values) for index in range(2))
                quotes.append(dict(**ident(case.run),common_months=month,region=region,quotes=len(values),
                                   W0_mean_buy=before,mean_buy=after,price_change_pct=100*(after-before)/before))
            for checkpoint,region in sorted(old.regions.keys() & case.regions.keys()):
                if checkpoint==month:
                    regional.append(dict(**ident(case.run),common_months=month,region=region,
                        **{f'W0_{key}':old.regions[checkpoint,region][key] for key in REGIONAL_FIELDS},
                        **{key:case.regions[checkpoint,region][key] for key in REGIONAL_FIELDS}))
            for key,(threshold,mode) in WATCH.items():
                change, status = difference(a[key],b[key],mode)
                alerts.append(dict(**ident(case.run), common_months=month, metric=key, baseline=a[key],
                    candidate=b[key], threshold=threshold, units='points' if mode=='points_down' else 'percent',
                    change=change,status=status,alert=(change>threshold if change is not None else status=='zero_baseline_increase')))
    return pairs,alerts,quotes,regional


def metrics(data, group, region, key, column='mean'):
    match=next(row for row in data if row['group']==group and row['region']==region and row['metric']==key)
    return float(match[column])


def summary_totals(cases,group,region):
    total=Counter()
    for case in cases:
        if case.run['group']==group and case.run['wave'] in ('long','holdout'):
            for (_,_,crop),record in case.production.items():
                if crop==region:
                    total.update(record)
    return total


def regional_production(cases):
    fields=('regular','adjusted','added','reduced','affected_months')
    for case in cases:
        regions=defaultdict(Counter)
        for (_,_,region),amounts in case.production.items():
            regions[region].update(amounts)
        for region, total in sorted(regions.items()):
            yield dict(**ident(case.run),region=region,**{key:total[key] for key in fields})


def repeated_risk(cases):
    for case in cases:
        regions=defaultdict(list)
        for year in case.years:
            if year['complete']:
                regions[year['region']].append(year)
        for region, years in sorted(regions.items()):
            runs=Counter()
            peak=Counter()
            previous=None
            for year in sorted(years,key=lambda row:row['year']):
                if previous is not None and year['year']!=previous+1:
                    runs.clear()
                for key,threshold in (('any_loss',100),('moderate_or_severe',95),('severe',90)):
                    runs[key]=runs[key]+1 if year['agriculture_multiplier']<threshold else 0
                    peak[key]=max(peak[key],runs[key])
                previous=year['year']
            yield dict(**ident(case.run),region=region,observed_harvest_years=len(years),**peak)


def balance_notes(path,pairs,alerts,regional):
    significant=[row for row in alerts if row['alert'] and row['group']=='W4'
                 and row['wave'] in ('five','long','holdout')]
    by_run=defaultdict(list)
    pair_index={tuple(row[key] for key in IDENTITY):row for row in pairs}
    for row in regional:
        by_run[tuple(row[key] for key in IDENTITY)].append(row)
    labels=dict(shortage_city_turns='缺糧城旬',grain_gap='糧食缺口',winter_timely='冬季準時送達',
                small_survival='小勢力存續',mean_turn_cpu='每旬 CPU')
    lines=['# 長期經濟與警戒線','',
           '| 比對 | 指標 | 221 | W4 | 首要缺糧增量區域 | 同局觀測 |',
           '|---|---|---:|---:|---|---|']
    for row in significant:
        identity=tuple(row[key] for key in IDENTITY)
        values=by_run[identity]
        pair=pair_index[identity]
        region=max(values,key=lambda r:r['unpaid_city_turns']-r['W0_unpaid_city_turns'],default=None)
        delta='' if region is None else region['unpaid_city_turns']-region['W0_unpaid_city_turns']
        zone=f"{region['region']}（+{delta}）" if region and delta>0 else '沒有正增量'
        evidence=f"戰鬥 {pair['W0_battles']} → {pair['battles']} 場，出運 {pair['W0_convoy_dispatched']} → {pair['convoy_dispatched']} 次"
        if row['metric']=='winter_timely':
            evidence=(f"冬援準時 {pair['W0_winter_arrived_on_time']}/{pair['W0_winter_orders']} → "
                      f"{pair['winter_arrived_on_time']}/{pair['winter_orders']}")
        if row['metric'] in ('shortage_city_turns','grain_gap') and region and delta>0:
            evidence=f"該區期末庫存 {region['W0_grain_stock']:,} → {region['grain_stock']:,}，{evidence}"
        lines.append(f"| {row['wave']} {row['scenario']}／{row['seed']}／{row['strategy']} "
                     f"（{row['common_months']} 月） | {labels[row['metric']]} | {row['baseline']:.4g} | "
                     f"{row['candidate']:.4g} | {zone} | {evidence} |")
    lines.extend(['','各局從相同劇本與種子開始，後續戰局、城市歸屬、用糧及運輸需求可分歧。'
                  '共同比較月份內的地區庫存、產糧及缺糧城旬列於區域 CSV。'
                  '運輸觀測列出原定到期及實收，樣本數小的準時率變動需和單次運隊一併閱讀。',
                  '',f'五年、二十年及保留樣本共 {sum(r["group"]=="W4" and r["wave"] in ("five","long","holdout") for r in pairs)} 組 W0／W4 配對。'])
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')


def readme(output):
    (output/'README.md').write_text("""# V2.3 冬季氣候與農業驗收

| 可直接瀏覽 | 路徑 |
|---|---|
| 候選准入與 25 項驗收 | [驗收報告](docs/acceptance.md) |
| 凍結參數與歷史依據 | [設計文件](docs/README.md) |
| 長期警戒明細 | [經濟對照](docs/long-term-balance-results.md) |
| 數據覆蓋與限制 | [已知限制](docs/known-issues.md)、[資料字典](docs/data-dictionary.md) |
| 逐局及配對統計 | [逐局](data/scenario-scores.csv)、[配對](data/pairwise.csv)、[警戒](data/balance-alerts.csv)、[區域產糧](data/regional-agriculture-overview.csv) |
| 完整種子和來源 | [實驗清單](data/simulation-manifest.json)、[校驗](SHA256SUMS.txt) |
| 回歸命令及相容性 | [技術門檻](checks/technical-gates.json)、[存檔相容](checks/compatibility.json) |
| 復算工具 | [原始工具及凍結表](sources/) |

解壓 [原始資料包](../archives/) 到同一根目錄後，可以使用對應開發分支的報表腳本重新計算。每包的檔案索引和 SHA-256 可獨立驗證。
""",encoding='utf-8')


def holdout_notes(path,cases,pairs):
    lines=['# 保留種子與江南寒潮對照','',
           '獨立氣候校準採 100000–100999，保留冬春驗證採 200000–200999。'
           '真實戰局保留種子為 2041 與 2042，兩個 W4 對照均採凍結同一組參數。','',
           '| 劇本／種子 | 共同月數 | 缺糧城旬 221 → W4 | 累計缺糧 221 → W4 |',
           '|---|---:|---:|---:|']
    for row in pairs:
        if row['wave']=='holdout':
            lines.append(f"| {row['scenario']}／{row['seed']} | {row['common_months']} | "
                         f"{row['W0_shortage_city_turns']:,} → {row['shortage_city_turns']:,} | "
                         f"{row['W0_grain_gap']:,} → {row['grain_gap']:,} |")
    keyed=next((case for case in cases if case.run['wave']=='exceptional' and case.run['group']=='W2e'),None)
    if keyed:
        events=[f"{year['year']} 年 {year['exceptional_cold_days']} 日" for year in keyed.years
                if year['region']=='southern_basins' and year['exceptional_cold_days']]
        if events:
            lines.extend(['','207-09／2037 的 W2e 實際江南寒潮按農業年度記為'
                          f"{'、'.join(events)}。該種子用於專項重現。"
                          '發生率取獨立氣候樣本，長期 W4 保持此開關關閉。'])
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')


def report_text(docs,climate,cases,pairs,alerts,quotes,tech,compatibility):
    snow=rows(climate/'holdout-winter-snow-days.csv')
    cover=rows(climate/'holdout-snow-cover-duration.csv')
    depth=rows(climate/'holdout-regional-snow-depth-statistics.csv')
    melt=rows(climate/'holdout-spring-melt-dates.csv')
    abnormal=rows(climate/'holdout-exceptional-cold-wave-events.csv')
    agriculture={row['region']:row for row in rows(climate/'agricultural-climate-holdout.csv')}
    ice=rows(climate/'holdout-river-ice-duration-comparison.csv')
    ld=agriculture['liaodong']
    baseline, candidate = (sum(float(row['mean']) for row in ice if row['group']==group and row['metric']=='frozen_days')
                           for group in ('W0','W3'))
    case_counts=Counter(case.run['wave'] for case in cases)
    mature_waves=('five','long','holdout')
    eligible=[row for row in alerts if row['group']=='W4' and row['wave'] in mature_waves and row['alert']]
    active=summary_totals(cases,'W4','liaodong')
    effect=(active['adjusted']-active['regular'])*100/active['regular'] if active['regular'] else None
    city_loss=Counter()
    for case in cases:
        if case.run['wave'] in ('long','holdout') and case.run['group']=='W4':
            for (_,city,_),record in case.production.items():
                city_loss[city]+=record['reduced']
    worst='、'.join(f'{key}（{value:,}）' for key,value in city_loss.most_common(5) if value) or '本次樣本未見'
    missing=sum(row['metric']=='grain_gap' for row in eligible)
    shortage=sum(row['metric']=='shortage_city_turns' for row in eligible)
    decline=sum(row['metric']=='small_survival' for row in eligible)
    loss=sum(len(case.preparation) for case in cases if case.run['group']=='W4')
    mature=[row for row in pairs if row['group']=='W4' and row['wave'] in mature_waves]
    meaningful=[row for row in mature if row['W0_northern_survival'] is not None
                and row['northern_survival'] is not None]
    down=sum(row['northern_survival']<row['W0_northern_survival'] for row in meaningful)
    rise=sum(row['northern_survival']>row['W0_northern_survival'] for row in meaningful)
    regional_quotes=[row for row in quotes if row['group']=='W4' and row['wave'] in mature_waves]
    count=sum(row['quotes'] for row in regional_quotes)
    price_text='無共同報價樣本'
    if count:
        a,b=(sum(row[key]*row['quotes'] for row in regional_quotes)/count
             for key in ('W0_mean_buy','mean_buy'))
        price_text=f'{a:.2f} → {b:.2f}（{count:,} 筆同城同月報價）'
    military=[]
    for prefix in ('W0_',''):
        due=sum(row[prefix+'winter_orders'] for row in mature)
        on_time=sum(row[prefix+'winter_arrived_on_time'] for row in mature)
        military.append(f'{on_time}/{due}（{on_time/due:.1%}）' if due else '無到期需求')
    hunger=[sum(row[key] for row in mature) for key in ('W0_convoy_hunger_losses','convoy_hunger_losses')]
    hunger_up=sum(row['convoy_hunger_losses']>row['W0_convoy_hunger_losses'] for row in mature)
    required_status={name:(tech[name]['exit_code'] if name in tech else None) for name in sorted(REQUIRED_GATES)}
    gating=', '.join(f'{key}={value if value is not None else "待測"}' for key,value in required_status.items())
    technical_passed=all(value==0 for value in required_status.values())
    complete=case_counts==EXPECTED_RUNS
    remaining=(compatibility or {}).get('historic_unverified', [])
    decision=('可送交正式啟用審核' if complete and technical_passed and compatibility and not (eligible or remaining)
              else '繼續保留為實驗候選')
    compat_text=(f"舊版 {compatibility['legacy_frames']:,} 筆逐日記錄與 {compatibility['legacy_checkpoints']} 個戰役狀態一致。"
                 f"新版 {compatibility['candidate_checkpoints']} 個 Python / Rust 領域狀態與隨機數一致。"
                 f"歷史運隊本輪重放 {len(compatibility['historic_replayed'])}/14 組。"
                 if compatibility else '歷史重放校驗待整理。')
    text=f"""# V2.3 候選驗收

實際觀戰 {len(cases)} 局。按波次分布為 {dict(case_counts)}。遊戲背景固定 D0、G1，數值來源見同包 CSV 和真實流水。

## 天氣和地區

1. 遼東完整保留季無雪比率為 {metrics(snow,'W3','liaodong','winter_snow_days','zero_fraction'):.1%}。
2. 221 到 W3 的遼東平均降雪日為 {metrics(snow,'W0','liaodong','winter_snow_days'):.2f} → {metrics(snow,'W3','liaodong','winter_snow_days'):.2f}。冬季積雪日為 {metrics(cover,'W0','liaodong','winter_snow_cover_days'):.2f} → {metrics(cover,'W3','liaodong','winter_snow_cover_days'):.2f}。
3. 遼東平均最大積雪指數 {metrics(depth,'W0','liaodong','max_snow_depth'):.2f} → {metrics(depth,'W3','liaodong','max_snow_depth'):.2f}。最後積雪日平均為 11 月起算第 {metrics(melt,'W0','liaodong','melt_last_day'):.2f} → {metrics(melt,'W3','liaodong','melt_last_day'):.2f} 日。
4. 西北平均降雪 {metrics(snow,'W3','northwest','winter_snow_days'):.2f} 日，低於遼東；基準寒冷曲線仍按西北規則。
5. 秦嶺平均最大積雪指數為 {metrics(depth,'W3','qinling_highlands','max_snow_depth'):.2f}，分布在積雪統計表可查。
6. 華北、中原按月份查同一公開機率表。每旬排程邊界和 W1 單變量有專項測試。
7. W3 江南低地無普通降雪。W2e 保留樣本的江南寒潮率為 {1-metrics(abnormal,'W2e','southern_basins','exceptional_cold_days','zero_fraction'):.1%}。
8. 15 處河段完全冰封的平均合計河段日為 {baseline:.2f} → {candidate:.2f}。每段逐級天數另列 CSV。
9. 遼東保留樣本的 6 月 30 日剩餘積雪最大值為 {metrics(melt,'W3','liaodong','remaining_snow_june30','maximum'):.0f}，保留融雪公式及正常河冰消退。

## 農業與實際後勤

10. 遼東正常或有利共 {float(ld['normal'])+float(ld['moisture']):.1%}，完整冬季的常態下雪本身不扣糧。
11. 遼東有利年 {float(ld['moisture']):.1%}。
12. 遼東輕、中、重分別 {float(ld['mild']):.1%}、{float(ld['moderate']):.1%}、{float(ld['severe']):.1%}。其他地區請查保留樣本表。
13. 等月產量基礎下，遼東保留樣本全年常規糧平均變化 {float(ld['annual_change_pct']):+.3f}%。二十年及保留真實觀戰的遼東 W4 實際加減額相對同期未套倍率基礎為 {f'{effect:+.3f}%' if effect is not None else '無樣本'}。
14. 二十年及保留局累計氣候減產量最高的城市是 {worst}。此欄是各城積算減產量。
15. 以開局北方多數城的勢力為隊列，長期可比較樣本中 W4 有 {down} 局存續率下降、{rise} 局上升。細節及同局戰事列在區域對照表。
16. 五年、二十年及保留局中，缺糧城旬警戒越界 {shortage} 局，缺糧總額越界 {missing} 局。配對買糧均價為 {price_text}。各地區溢出與補貨分開記。
17. 九旬測試驗證已凍結的六月帳使用 90%，仍待觀測時基準帳使用 100%。
18. W4 觀測中有 {loss} 次不確定農業風險觸發、且實際發出的備糧運輸。市場或官倉方法及有效期限可逐筆查。
19. 五年、二十年及保留局的冬季軍需準時送達為 {military[0]} → {military[1]}。比較依派遣時的報到旬與實際入帳。各局樣本數列於 CSV。
20. 同期運隊缺糧減員為 {hunger[0]:,} → {hunger[1]:,} 人，{len(mature)} 組中 {hunger_up} 組增加。運輸安全對照 CSV 另列回運。
21. 官倉以寫入核對、市場以實際補貨和買賣核對，留存來源。
22. 9 月專項測試以調整後的常規與內政收入計原豐收率一次。
23. {compat_text}歷史樣本沒有可重放的原存檔時，保留已有流水及原報告。
24. 技術門檻的退出值為 {gating}。完整命令、源 SHA 和日誌列於技術清單。
25. 准入判斷為**{decision}**。五年、二十年及保留組的 W4 共 {len(eligible)} 項越線，其中小勢力存續警戒 {decline} 項。正式預設維持既有規則。
"""
    (docs/'acceptance.md').write_text(text,encoding='utf-8')
    return dict(decision=decision,long_term_alerts=len(eligible),campaigns=len(cases),wave_counts=dict(case_counts),
                technical_passed=technical_passed,expected_runs_present=complete,missing_historical_replays=remaining)


def build(source,output):
    output.mkdir(parents=True,exist_ok=True)
    data,docs,checks,sources=(output/name for name in ('data','docs','checks','sources'))
    for folder in (data,docs,checks,sources):
        folder.mkdir(exist_ok=True)
    for p in (TOOL_ROOT/'docs/winter-agriculture-v23').glob('*.md'):
        shutil.copy2(p,docs/p.name)
    climate=source/'climate-frozen' if (source/'climate-frozen/holdout-config.json').exists() else source/'climate'
    for p in climate.glob('*.csv'):
        shutil.copy2(p,data/p.name)
    for p in climate.glob('*.json'):
        shutil.copy2(p,data/p.name)
    geography=rows(climate/'city-climate-audit.csv')
    weather_regions={row['city_id']:row['region'] for row in geography}
    crop_regions={row['city_id']:row['crop_region'] for row in geography}
    cases=[Case(path,weather_regions,crop_regions) for path in sorted(source.glob('campaigns/*/*/*/run-v23.json'))
           if json.loads(path.read_text())['outcome'] in ('complete','natural_end')]
    if not cases:
        raise ValueError('No real campaigns to report')
    frozen=(source/'frozen-source.txt').read_text(encoding='utf-8').strip()
    fingerprints={tuple(case.run[key] for key in IDENTITY) for case in cases}
    assert len(fingerprints)==len(cases) and all(case.run['source']==frozen for case in cases)
    pairs,alerts,quotes,regional=paired(cases)
    emit(data,'scenario-scores.csv',(dict(**ident(case.run),**case.score(case.ending)) for case in cases))
    emit(data,'pairwise.csv',pairs)
    emit(data,'balance-alerts.csv',alerts)
    emit(data,'agricultural-year-summary.csv',(row for case in cases for row in case.years))
    emit(data,'agricultural-repeated-risk.csv',repeated_risk(cases))
    emit(data,'regional-agriculture-overview.csv',regional_production(cases))
    emit(data,'agricultural-production-comparison.csv',(dict(**ident(case.run),year=year,city=city,region=region,
        regular=values['regular'],adjusted=values['adjusted'],added=values['added'],reduced=values['reduced'],
        affected_months=values['affected_months']) for case in cases
        for (year,city,region),values in sorted(case.production.items())))
    emit(data,'agricultural-grain-account.csv',(dict(**ident(case.run),**row,
        audit_mismatches=case.run['warehouse_audit']['city_resource_mismatches'])
        for case in cases for row in case.run['warehouse_audit']['categories'] if row['resource']=='grain'))
    emit(data,'harvest-bonus-comparison.csv',(dict(**ident(case.run),year=year,city=city,region=region,
        harvest_bonus=values['harvest_bonus'],civil_bonus=values['civil_bonus'])
        for case in cases for (year,city,region),values in sorted(case.harvest.items())))
    emit(data,'city-disaster-grain.csv',(event for case in cases for event in case.disasters),
         (*IDENTITY,'id','year','month','day','city','disaster','grain','region'))
    market=[dict(**ident(case.run),year=year,city=city,region=region,**values)
            for case in cases for (year,city,region),values in sorted(case.market.items())]
    emit(data,'climate-market-supply-comparison.csv',market)
    emit(data,'climate-market-overflow-comparison.csv',(dict(**{key:row[key] for key in (*IDENTITY,'year','city','region')},
              overflow=row['overflow'],stock=row['stock'],capacity=row['capacity']) for row in market))
    emit(data,'market-price-comparison.csv',quotes)
    emit(data,'agriculture-forecast-comparison.csv',(row for case in cases for row in case.preparation),
         ('wave','group','scenario','seed','strategy','turn','year','month','owner','city','method','grain','deadline'))
    emit(data,'regional-climate-economic-balance.csv',regional)
    emit(data,'long-term-economy-comparison.csv',(row for row in pairs if row['wave'] in ('long','holdout')))
    for name,selected in (
        ('convoy-hunger-comparison',('convoy_hunger_losses',)),
        ('convoy-return-safety',('convoy_returned','convoy_grain_arrived')),
        ('climate-transport-safety',('convoy_returned','convoy_hunger_losses','winter_timely')),
        ('performance-comparison',('mean_turn_cpu',)),
    ):
        emit(data,name+'.csv',({key:row[key] for key in (*IDENTITY,'common_months',*selected,
             *('W0_'+field for field in selected))} for row in pairs))
    emit(data,'winter-army-supply-comparison.csv',(dict(**ident(case.run),**row)
         for case in cases for row in case.run['measurements']['winter_army_orders']),
         (*IDENTITY,'convoy','owner','source','target','deadline','opened','actual','received','reason'))
    fields=('convoy_days','hungry_convoy_days','ice_blocked_convoy_days','extra_military_grain',
            'weather_delay_work','convoy_hunger_loss')
    emit(data,'campaign-weather-exposure.csv',(dict(**ident(case.run),
        **{key:case.run['measurements']['weather'].get(key,0) if case.run['weather'] else None for key in fields})
        for case in cases))
    gates=published_gates(source)
    to_json(checks/'technical-gates.json',gates)
    compatibility_path=source/'compatibility/compatibility.json'
    compatibility=None
    if compatibility_path.is_file():
        compatibility=json.loads(compatibility_path.read_text())
        shutil.copy2(compatibility_path,checks/compatibility_path.name)
    fields=(*IDENTITY,'source','catalog_sha256','map_sha256','transport','weather','weather_seed','options','granary',
            'emergency','output','completed_turns','requested_months','runner_sha256','outcome')
    provenance=source/'provenance'
    variants={wave:file_sha256(provenance/script) for wave,script in (
        ('quick','v23_observe_quick.py'), ('five','v23_observe_five_long.py'),
        ('long','v23_observe_five_long.py'), ('holdout','v23_observe_five_long.py'),
        ('exceptional','v23_observe_five_long.py')) if (provenance/script).is_file()}
    to_json(data/'simulation-manifest.json', {'groups':FEATURES,'simulations':[
        {key:variants.get(case.run['wave'],case.run.get(key)) if key=='runner_sha256'
                   else case.run.get(key) for key in fields} for case in cases]})
    for name in ('v23_climate.py','v23_observe.py','v23_compat.py','v23_report.py','v23_package.py'):
        shutil.copy2(TOOL_ROOT/'tools/economy-balance'/name,sources/name)
    for name in ('winter_climate.py','winter_agriculture_normals.py'):
        shutil.copy2(TOOL_ROOT/'source/remake'/name,sources/name)
    for path in provenance.glob('*.py'):
        shutil.copy2(path,sources/path.name)
    decision=report_text(docs,climate,cases,pairs,alerts,quotes,gates,compatibility)
    balance_notes(docs/'long-term-balance-results.md',pairs,alerts,regional)
    holdout_notes(docs/'holdout-results.md',cases,pairs)
    readme(output)
    to_json(data/'report-status.json',decision | dict(source=frozen,
        validation_tools_source=git('rev-parse','HEAD').decode().strip(), technical_gates=len(gates)))
    paths=sorted(p for p in output.rglob('*') if p.is_file() and p.name not in ('SHA256SUMS.txt','validation-manifest.json'))
    manifest=[dict(path=str(p.relative_to(output)),bytes=p.stat().st_size,sha256=file_sha256(p)) for p in paths]
    to_json(data/'validation-manifest.json',dict(**decision,files=manifest))
    paths=sorted([*paths,data/'validation-manifest.json'])
    (output/'SHA256SUMS.txt').write_text(''.join(f'{file_sha256(p)}  {p.relative_to(output)}\n' for p in paths),encoding='utf-8')
    return decision


def file_sha256(path):
    return sha256(path.read_bytes())


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    options=parser.parse_args()
    print(json.dumps(build(options.source.resolve(),options.output.resolve()),ensure_ascii=False))
