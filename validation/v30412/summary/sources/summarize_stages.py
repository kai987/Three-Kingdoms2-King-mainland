"""Derive the observation gate and human-readable pair table from the accepted run artifacts."""

from collections import Counter, defaultdict
import csv
import gzip
import json
from pathlib import Path
import sys


def read_csv(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({key: 'null' if row.get(key) is None else row[key] for key in fields})


def read_json(path):
    return json.loads(path.read_bytes())


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def integer(value):
    return f'{int(value):,}' if value not in ('null', '', None) else '未采集'


def percentage(value):
    return f'{float(value):.1f}%' if value not in ('null', '', None) else '不适用'


def label(row):
    return f"{row['scenario']} / {row['strategy']} / {row['seed']}"


def actual_observations(root, summary):
    plans = read_json(root/'observations/quick-plan.json')['cases']
    completed = read_json(root/'observations/quick-completed.json')
    scores = read_csv(summary/'data/scenario-scores.csv')

    def identity(row):
        return row['variant'], row['scenario'], int(row['strategy']), int(row['seed'])

    if {identity(row) for row in plans} != {identity(row) for row in completed}:
        raise ValueError('A planned observation was not completed')
    by_case = {identity(row): row for row in scores}
    if len(by_case) != len(scores) or not {identity(row) for row in completed} <= by_case.keys():
        raise ValueError('Observation summary does not reconcile')
    if any(row['full_months'] != '24' or row['completed_turns'] != '72' for row in scores):
        raise ValueError('Incomplete observations cannot be compared')

    fixed = read_json(summary/'checks/fixed-stage-status.json')
    alerts = read_csv(summary/'data/balance-alerts.csv')
    with_failure = defaultdict(list)
    for row in alerts:
        with_failure['D0' if row['baseline'] == 'K0' else 'D2'].append(
            {'scenario': row['scenario'], 'strategy': int(row['strategy']), 'seed': int(row['seed']),
             'metric': row['metric'], 'baseline': float(row['baseline_value']),
             'candidate': float(row['candidate_value']), 'delta': float(row['delta']),
             'threshold': int(row['threshold']), 'unit': row['unit']})
    stage = {
        'stage': 'quick',
        'engine_sha': fixed['engine_sha'],
        'admitted_backgrounds': [],
        'fixed': {'status': 'passed_for_quick', 'admitted_backgrounds': fixed['admitted_backgrounds'],
                  'windows': 30, 'unique_input_checkpoints': 5, 'targets_per_group': 89,
                  'returning_slot_samples_per_group': 23, 'south_checkpoints': 8,
                  'historical_replayed_checkpoints': 8, 'performance_checkpoints': 5},
        'quick': {'status': 'complete_not_admitted', 'formal_runs': len(plans),
                  'supplemental_runs': len(scores) - len(plans), 'runs_with_24_months': len(scores),
                  'alerts': dict(with_failure),
                  'reason_by_background': {
                      'D0': '208-10 AI 211 acute city food regression; 263-05 AI 211 severe first-deadline and march hunger regression',
                      'D2': '184-02 AI 211 first-deadline regression; 208-10 AI 211 city food and march hunger regression',
                  }},
        'five': {'status': 'not_run', 'reason': 'quick_gate_not_met', 'planned_runs': {'D0': 14, 'D2': 8}},
        'long': {'status': 'not_run', 'reason': 'five_year_gate_not_met', 'planned_runs': {'D0': 6, 'D2': 2}},
        'holdout': {'status': 'not_run', 'reason': 'economic_candidate_not_frozen',
                    'protected_seeds': [2047, 2048]},
        'candidate': {'engineering_sha': fixed['engine_sha'], 'economic_frozen': False,
                      'experimental_version': 30412, 'enabled_by_default': False},
    }
    write_json(summary/'checks/economic-stage-status.json', stage)
    with (summary/'data/pairwise.csv').open(encoding='utf-8', newline='') as stream:
        header = next(csv.reader(stream))
    for name in ('long-term-economy-comparison', 'holdout-comparison'):
        with (summary/'data'/f'{name}.csv').open('w', encoding='utf-8', newline='') as stream:
            csv.writer(stream, lineterminator='\n').writerow(header)

    fields = {
        'city_food_required': '城市应付粮',
        'city_food_paid': '城市实付粮',
        'city_food_missing': '城市实际欠粮',
        'march_hunger_losses': '行军饥损',
        'original_deadline_grain_rate': '军粮首次期限及时率',
        'unresolved_grain': '未满足军粮',
        'battles': '战斗数',
        'grain_security_books': '全渠道命令书',
    }
    lines = [
        '# 24 个月真实观战',
        '',
        '16 局正式观战和 5 局补充对照均完成 72 旬。每一对共用引擎、剧本、种子、策略和规则背景。'
        '农业 V2、市场 301、粮仓 G1 加 G2 性能优化、应急 222、气候 23 和预测 231 均启用。'
        '城市中转及江南异常寒潮均关闭。D2 只额外开启有限并发。',
        '',
        '| 背景 | 剧本 / AI / 种子 | ' + ' | '.join(fields.values()) + ' |',
        '| --- | --- | ' + ' | '.join(['---:'] * len(fields)) + ' |',
    ]
    for row in sorted(plans, key=lambda r: (r['variant'][0], r['scenario'], r['strategy'], r['seed'])):
        variant, scenario, strategy, seed = identity(row)
        if variant not in ('K0', 'L0'):
            continue
        before = by_case[variant, scenario, strategy, seed]
        after = by_case[variant[0]+'2', scenario, strategy, seed]
        values = []
        for key in fields:
            format_value = percentage if key == 'original_deadline_grain_rate' else integer
            values.append(f'{format_value(before[key])} → {format_value(after[key])}')
        lines.append('| ' + ' | '.join(['D0' if variant=='K0' else 'D2', label(row), *values]) + ' |')
    lines += [
        '',
        'D0 的魏灭蜀 211 欠粮城市的库存有所改善，行军饥损却由 15,585 增至 49,560。'
        '军粮首次期限及时率减少 36.6 个百分点。蜀军 111 号需求 28,311，实际另外取得 15,018，'
        '仍差 13,293，现场没有实际发运。第 60 旬的紧急报价记录显示 18 笔人员限制和 1 笔路线限制。'
        '同旬自由调度阶段也已没有可用命令书。D0 赤壁 211 同时出现城市实际欠粮和军粮及时率退化。',
        '',
        '263-05 同存档切换调度的七旬复放中，原调度下的葭萌欠粮 1,343、111 号军队饥损 6,106。'
        '30411 和 30412 均为城市欠粮 0、军队饥损 6,792。本地实际补粮由 5,122 变为 2,794，'
        '三组均无运队交接。该城和该军在共享库存下的得失同时存在，且差异在 30411 已出现。',
        '',
        'D2 黄巾城市欠粮和行军饥损均下降，军粮首次期限及时率仍减少 22.6 个百分点。'
        'D2 赤壁 211 的城市欠粮全部发生在玄菟。第 44 旬扣粮前的同存档控制中，'
        '三种调度各应付 1,683，库存可付 571，缺 1,112。市场库存为零，国内城没有合资格的押运人员。'
        '该首次扣粮的原始需求在三种调度中相同。自然战役后续数值包含人口、兵力和库存分歧。',
        '',
        '| 30411 补充组 | 剧本 / AI / 种子 | 城市实际欠粮 | 行军饥损 | 军粮首次期限及时率 |',
        '| --- | --- | ---: | ---: | ---: |',
    ]
    for row in scores:
        if row['variant'] in ('K1', 'L1'):
            lines.append('| ' + ' | '.join([row['variant'], label(row), integer(row['city_food_missing']),
                                          integer(row['march_hunger_losses']),
                                          percentage(row['original_deadline_grain_rate'])]) + ' |')
    lines += [
        '',
        '逐局应付／实付、人口、兵力、实际在途补给、运队粮耗、参战、命令书以及 CPU 分位数可在逐局记录核对。'
        '实际军粮及时率的分子为首次原期限前可归因粮，分母为真实申请粮。弃用或目标离开也保留在流水中。',
        '',
        '[逐局记录](../data/scenario-scores.csv) · [配对数据](../data/pairwise.csv) · '
        '[警戒记录](../data/balance-alerts.csv) · [军粮明细](../data/military-grain-request-ledger.csv) · '
        '[玄菟同状态控制](../checks/xuantu-same-state-comparison.json) · '
        '[263-05 蜀军补给诊断](../data/weimieshu-march-111-trace.csv) · '
        '[263-05 同状态复放](../checks/weimieshu-same-state-comparison.json)',
        '',
    ]
    (summary/'docs/quick-observation-results.md').write_text('\n'.join(lines), encoding='utf-8')


def march_case(root, summary):
    campaign = root/'observations/K2/campaigns/quick/F4/263-05-2026-211'
    with gzip.open(campaign/'coordination.jsonl.gz', 'rt', encoding='utf-8') as stream:
        rows = [dict(row, blockers=json.dumps(row.get('blockers'), sort_keys=True))
                for row in map(json.loads, stream)
                if row.get('army') == 111 or (row.get('target_kind') == 'march' and row.get('target') == 111)]
    write_csv(summary/'data/weimieshu-march-111-trace.csv', rows)


def small_loads(summary):
    rows = read_csv(summary/'data/small-load-transport-audit.csv')
    groups = defaultdict(Counter)
    columns = ('wave', 'scenario', 'seed', 'strategy', 'variant', 'purpose', 'priority')
    for row in rows:
        if int(row['outbound_days']) < 20:
            continue
        group = groups[tuple(row[column] for column in columns)]
        group.update(transport_orders=1)
        group.update({name: int(row[name]) for name in
                      ('initial_grain', 'delivered_grain', 'allocated_books', 'hunger_losses')
                      if row[name] not in ('null', '')})
    write_csv(summary/'data/small-load-by-real-purpose.csv',
              [dict(zip(columns, key, strict=True), **values) for key, values in sorted(groups.items())])


def fixed_equivalence(root, summary):
    earlier = read_json(root/'fixed-final/results.json')
    final = read_json(root/'fixed-clean/results.json')
    def indexed(data):
        return {(row['fixture'], row['group']): row for row in data['results']}
    previous, current = indexed(earlier), indexed(final)
    if previous.keys() != current.keys() or len(current) != 30:
        raise ValueError('Clean fixed-state replay did not cover the original sample')
    evidence = []
    for key, row in sorted(current.items()):
        old = previous[key]
        for field in old.keys() - {'checks', 'actual'}:
            if row[field] != old[field]:
                raise ValueError(f'Clean fixed-state replay differs for {key}: {field}')
        for field, excluded in (('checks', {'cpu', 'wall'}), ('actual', {'reached_route_endpoint'})):
            for before, after in zip(old[field], row[field], strict=True):
                if any(before.get(k) != after.get(k) for k in (before.keys() | after.keys()) - excluded):
                    raise ValueError(f'Clean fixed-state replay differs for {key}: {field}')
        evidence.append(dict(fixture=key[0], group=key[1], checkpoint_sha256=row['sha256'],
                             turns=len(row['checks']), actual_events=len(row['actual'])))
    write_json(summary/'checks/final-source-fixed-equiv.json',
               dict(earlier_source=earlier['source'], clean_source=final['source'],
                    clean_engine_patch_sha256=final['working_patch_sha256'],
                    ignored_performance_and_new_observation_fields=['cpu', 'wall', 'reached_route_endpoint'],
                    execution_equal=True, runs=evidence))
    return final['results']


def additional_replay_results(root, summary, fixed_runs):
    quote_rows = []
    commitments = []
    for run in fixed_runs:
        for row in run['actual']:
            if row['event'] == 'forecast_requote':
                quote_rows.append(dict(phase='fixed-clean', group=run['group'], checkpoint=run['sha256'], **row))
            if row['event'] == 'staging_node':
                commitments.append(dict(group=run['group'], checkpoint_sha256=run['sha256'], **row))
    hold_cases = list(commitments)
    endpoints = {}
    actual = summary/'data/transit-march-safety-comparison.csv'
    safety = read_csv(actual)
    for phase in ('south-final', 'baxi-final', 'transit-ablation'):
        for path in sorted((root/phase/'actual').glob('*.jsonl.gz')):
            case, group = path.name.split('.json.gz-')
            group = group.removesuffix('.jsonl.gz')
            with gzip.open(path, 'rt', encoding='utf-8') as stream:
                for row in map(json.loads, stream):
                    if row['event'] == 'forecast_requote':
                        quote_rows.append(dict(phase=phase, group=group, checkpoint=case, **row))
                    if row['event'] == 'staging_node':
                        hold_cases.append(dict(group=group, checkpoint=case, **row))
                    if (phase == 'baxi-final' and row['event'] == 'unit_meal_settled'
                            and row['unit_kind'] == 'march' and row['unit_id'] == 282
                            and row.get('reached_route_endpoint')):
                        endpoints[group] = row['tick'], row['route'][-1]
    for path in (actual, summary/'data/baxi-city-and-army-balance.csv'):
        values = safety if path == actual else read_csv(path)
        for row in values:
            if row['city'] == 'baxi' and row['march_id'] == '282' and row['group'] in endpoints:
                row['actual_route_arrival'], row['actual_route_endpoint'] = endpoints[row['group']]
        write_csv(path, values)
    write_csv(summary/'data/forecast-requote-results.csv', quote_rows)
    write_csv(summary/'data/transit-commitment-settlement.csv', hold_cases)
    counts = Counter((row['phase'], row['channel']) for row in quote_rows)
    macro = read_csv(summary/'data/scenario-scores.csv')
    write_json(summary/'checks/forecast-requote-observation.json', {
        'fixed_windows_observed': len(fixed_runs),
        'fixed_quote_corrections': sum(row['phase'] == 'fixed-clean' for row in quote_rows),
        'other_replay_events': [dict(phase=phase, channel=channel, corrected_quotes=count)
                                for (phase, channel), count in sorted(counts.items())],
        'twenty_four_month_quotes': [
            dict(variant=row['variant'], scenario=row['scenario'], strategy=int(row['strategy']), seed=int(row['seed']),
                 corrected_quotes=None if row['requotes_observed'] in ('null', '') else int(row['requotes_observed']))
            for row in macro],
        'scope': 'Corrected legal offers emitted by quote calculation. Counts include repeated evaluations and replay overlaps.',
        'dispatched_or_delivered_from_requoted_offer': None,
        'controlled_case': 'test_requote_pays_higher_return_cost_with_a_smaller_legal_load',
    })


if __name__ == '__main__':
    raw_root, report_root = map(Path, sys.argv[1:])
    actual_observations(raw_root, report_root)
    march_case(raw_root, report_root)
    small_loads(report_root)
    additional_replay_results(raw_root, report_root, fixed_equivalence(raw_root, report_root))
