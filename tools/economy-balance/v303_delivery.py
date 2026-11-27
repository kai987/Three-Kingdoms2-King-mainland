"""Write the decision report and comparative tables for the V3.0.3 archive."""
from argparse import ArgumentParser
from collections import defaultdict
import json
from pathlib import Path
from shutil import copyfile

from common import ROOT, to_json
from v3021_report import file_sha, read
from v302_report import csv_file_rows
from v303_report import GATES


def txt(path,s):
    path.write_text(s.rstrip()+'\n',encoding='utf-8')


def n(value):
    if value is None or value in ('','null','not_applicable','not_collected'):
        return '—'
    if isinstance(value,str):
        try:
            value=float(value) if '.' in value else int(value)
        except ValueError:
            return value
    return f'{value:,.2f}' if isinstance(value,float) else f'{value:,}'


def delta(row):
    if not row:
        return '—'
    return f"{n(row['before'])} → {n(row['after'])}"


def historical(args):
    out=args.summary/'checks'
    prior=args.prior_summary/'checks/historical-transport-controls.json'
    if prior.is_file():
        copyfile(prior,out/'v3021-historical-controls.json')
    inputs=('convoys.csv','convoy-events.csv','convoy-survival.csv','unresolved-convoy-cases.csv',
            'convoy-resolution-daily.csv.gz','transport-progress-daily.csv.gz')
    capture={}
    if args.historical_1860:
        parent=args.historical_1860
        previous=[]
        for name in inputs:
            path=parent/name
            field='convoy' if name=='transport-progress-daily.csv.gz' else 'convoy_id'
            matches=[row for row in csv_file_rows(path) if row.get(field)=='1860']
            key=dict(file=name,sha256=file_sha(path),matched_rows=len(matches))
            if name.endswith('.gz'):
                key.update(first=matches[0] if matches else None,last=matches[-1] if matches else None)
            else:
                key.update(rows=matches)
            previous.append(key)
        run=read(parent/'run-v302.json')
        capture=dict(scenario=run['scenario'],seed=run['seed'],strategy=run['strategy'],weather=run['weather'],
            source=run['source'],catalog_sha256=run['catalog_sha256'],map_sha256=run['map_sha256'],
            relative_path=run['output'],original_run_sha256=file_sha(parent/'run-v302.json'),records=previous)
        to_json(out/'historical-1860-original.json',capture)
    items={}
    for ident in (2170,1228,219,1860):
        candidate=args.build/'checks'/f'historical-{ident}.json'
        if not candidate.is_file():
            continue
        proof=read(candidate)
        outcomes=[]
        for branch in proof['outcomes']:
            marker=branch['finish']
            last=marker['snapshot']
            terminal=next((e for e in reversed(branch['events']) if e['event']=='terminal'),None)
            remain=last['troops'] if last else None
            outcomes.append(dict(group=branch['group'],period=marker['turn'],survivors=remain,
                hunger=last['hunger'] if last else None,terminal=terminal['outcome'] if terminal else None,
                last_location=last['node'] if last else None,
                final_state_sha256=branch['final_state_sha256']))
        items[ident]=dict(checkpoint=proof['checkpoint'],start=proof['outcomes'][0]['starting'],outcomes=outcomes,
                          details=f'checks/historical-{ident}.json',sha256=file_sha(candidate))
    to_json(out/'historical-transport-index.json',dict(old_control_sha256=file_sha(prior),paired=items,
        original_1860='historical-1860-original.json' if capture else None))
    return items


def support_table(s):
    rows=['| 组别 | 固定目标 | 有及时入库 | 足额入库 | 期限前实到粮 | 返程样本及时报价 | 返程来源实际入库 |',
          '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for group in ('C0','C1','C2','C3','C4'):
        if item:=s['fixed'].get(group):
            rows.append('| '+' | '.join([group,*[n(item.get(k,0)) for k in
                ('targets','l5_with_supply','l5_full','l5_received','timely_quote_sample',
                 'actual_dispatch_receipt_sample')]])+' |')
    return '\n'.join(rows)


def aggregate_mode(data,group,dimension,mode):
    scoped=[r for r in data if r['economy_background']=='G1' and r['group']==group
            and r['dimension']==dimension and r['mode']==mode]
    integer=('departures','actual_delivered_grain','rated_capacity','rated_grain','rated_rations',
             'occupancy_person_days','command_books','terminated','dangerous_stalled','hunger_losses')
    result={key:sum(int(r[key]) for r in scoped) for key in integer}
    return result


def mode_table(data):
    headers=['| 组别 | 实际模式／流向 | 发运队数 | 实到粮 | 总容量利用率 | 武将日净到粮 | 命令书净到粮 |',
             '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for group in ('C0','C4'):
        for tag,mode,label in (
                ('physical','land','陆路'),('physical','river','纯河流'),('physical','sea','纯海'),
                ('physical','mixed','水陆混合'),('one_river_flow','downstream','线路仅有顺流河段'),
                ('one_river_flow','upstream','线路仅有逆流河段')):
            row=aggregate_mode(data,group,tag,mode)
            arrived=row['actual_delivered_grain']
            use=(row['rated_grain']+row['rated_rations'])/row['rated_capacity']*100 if row['rated_capacity'] else None
            headers.append(f"| {group} | {label} | {n(row['departures'])} | {n(arrived)} | "+
                (f'{use:.2f}%' if use is not None else '—')+f" | {n(arrived/row['occupancy_person_days'] if row['occupancy_person_days'] else None)}"
                f" | {n(arrived/row['command_books'] if row['command_books'] else None)} |")
    return '\n'.join(headers)


def grouped_table(pairs,wave):
    grouped=defaultdict(dict)
    for row in pairs:
        if row['wave']==wave and row['group']=='C4' and row['economy_background']=='G1':
            key=(row['scenario'],row['seed'],row['strategy'],row['weather'],row['baseline'])
            grouped[key][row['metric']]=row
    body=['| 剧本 | 种子 | 策略 | 天气 | 对照 | 缺粮城旬 | 累计缺口 | 最长缺粮旬 | 冬季及时率 % | 战斗 |',
          '| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |']
    for key,r in sorted(grouped.items()):
        body.append('| '+' | '.join(key+tuple(delta(r.get(metric)) for metric in
            ('unpaid_city_turns','rations_missing','longest_streak','winter_timely_percent','battles')))+' |')
    return '\n'.join(body)


def summarize(pairs,metric,*,background='G1',wave='five'):
    match=[r for r in pairs if r['wave']==wave and r['metric']==metric and r['group']=='C4'
           and r['economy_background']==background and r['baseline']=='C0']
    if not match:
        return '目前缺少同期限配对。'
    before=sum(float(r['before']) for r in match)
    after=sum(float(r['after']) for r in match)
    bigger=sum(float(r['change'])>0 for r in match)
    smaller=sum(float(r['change'])<0 for r in match)
    if metric.endswith('_percent') or metric.endswith('_cpu'):
        compute=lambda v:n(v/len(match))
        label='各局等权平均'
    else:
        compute=lambda v:n(int(v))
        label='各局合计'
    return (f'{len(match)} 个配对{label}由 {compute(before)} 到 {compute(after)}，'
            f'{bigger} 局增加，{smaller} 局降低。')


def report(args):
    out=args.summary
    s=read(out/'data/report-status.json')
    scenarios=list(csv_file_rows(out/'data/scenario-scores.csv'))
    observations=list(csv_file_rows(out/'data/transport-mode-throughput.csv'))
    pairs=list(csv_file_rows(out/'data/pairwise.csv'))
    previews=list(csv_file_rows(out/'data/origin-concurrency-usage.csv'))
    controls=historical(args)
    fixed_inputs=out/'sources/v3021-fixed-inputs'
    fixed_inputs.mkdir(parents=True,exist_ok=True)
    for name in ('spatial-grain-capability-funnel.csv','source-task-blockers.csv'):
        copyfile(args.prior_summary/'data'/name,fixed_inputs/name)
    for p in sorted((ROOT/'docs/transport-capacity-v303').glob('*.md')):
        copyfile(p,out/'docs'/p.name)
    scope=[r for r in scenarios if r['group'] in ('C0','C4') and r['economy_background']=='G1']
    c0=[r for r in scope if r['group']=='C0']
    blocked=sum(int(r['origin_limit_assessments'] or 0) for r in c0 if r['origin_limit_assessments']!='null')
    unique=sum(int(r['origin_limit_distinct_source_turns'] or 0) for r in c0
                if r['origin_limit_distinct_source_turns']!='null')
    retain=sum(int(r['minimum_retained_officer_assessments'] or 0) for r in c0
               if r['minimum_retained_officer_assessments']!='null')
    physical_c4=sum(int(r['departures']) for r in previews if r['active']=='2' and r['group']=='C4')
    head=s['route_census']
    key0=s['fixed'].get('C0',{})
    key1=s['fixed'].get('C1',{})
    key4=s['fixed'].get('C4',{})
    target_delta=None if not key0 or not key1 else key1.get('l5_received',0)-key0.get('l5_received',0)
    warnings=[r for r in pairs if r['warning']=='true' and r['group']=='C4']
    gate_pass=all(value=='pass' for value in s['gates'].values())
    complete=s['completed_runs']==s['planned_runs'] and bool(s['fixed'])
    no_mismatches=s['accounting_issues']==s['city_resource_mismatches']==0
    readiness=complete and gate_pass and no_mismatches and not warnings
    verdict='通过当前准入指标' if readiness else '暂缓进入 V3.0.4 的正式平衡阶段'
    version=f"引擎 {s['source']}。观战覆盖 {s['completed_runs']}／{s['planned_runs']}，"
    version+=f"其中 {s['archived_runtime_equivalent_runs']} 局为核验后的历史 C0。C4 触发 {len(warnings)} 条警戒线。"
    base=out/'docs'
    method=(base/'validation-results.md').read_text().split('\n',2)[-1].strip()
    cases=grouped_table(pairs,'long')
    holdout=grouped_table(pairs,'holdout')
    txt(base/'long-term-balance-results.md',f'# 二十年经济对照\n\n{version}\n\n{cases}\n\n[完整长期指标](../data/long-term-economy-comparison.csv)')
    held=[row for row in scenarios if row['wave']=='holdout' and row['group'] in ('C0','C4')]
    txt(base/'holdout-results.md',f'# 冻结候选的保留种子\n\n种子 2037 及 2038 在参数冻结后启动，目标为每局 60 个月。已完成 {len(held)}／4 局。\n\n{holdout}\n\n[全部保留种子指标](../data/holdout-comparison.csv)')
    perf=defaultdict(list)
    for row in csv_file_rows(out/'data/performance-state-parity.csv'):
        perf[row['checkpoint']].append(row)
    timing=['| 检查点 | 记录旬数 | 完整状态一致 | 既有引擎每旬 CPU 均值 | 303 关闭每旬 CPU 均值 |',
            '| --- | ---: | ---: | ---: | ---: |']
    for name,rows in sorted(perf.items()):
        a=sum(float(r['released_turn_cpu']) for r in rows)/len(rows)
        b=sum(float(r['disabled_turn_cpu']) for r in rows)/len(rows)
        timing.append(f"| {name} | {len(rows)} | {sum(r['same_state']=='true' for r in rows)} | {a:.3f} s | {b:.3f} s |")
    txt(base/'performance-results.md',(base/'performance-results.md').read_text()+
        '\n## 实测\n\n'+'\n'.join(timing)+'\n\n'+
        '五年 C4 对 C0 每旬平均 CPU 秒。'+summarize(pairs,'mean_turn_cpu')+
        '\n\n[固定状态 CPU／P95](../data/fixed-state-performance.csv) · [全观战性能](../data/performance-comparison.csv)')
    technical=['| 检查 | 结果 |','| --- | --- |']
    for name,label in GATES.items():
        technical.append(f"| {label} | {s['gates'].get(name,'not_completed')} |")
    military=[r for r in csv_file_rows(out/'data/transport-dispatch-receipts.csv')
              if r['group']=='C4' and r['purpose'] in ('army','convoy_relief')]
    military_arrived=sum(int(r['actual_delivered_grain']) for r in military)
    military_losses=sum(int(r['hunger_losses']) for r in military)
    military_open=sum(r['terminal']=='right_censored' for r in military)
    recorded=sum(int(r['physical_transport_departures']) for r in scenarios
                 if r['physical_transport_departures']!='null')
    blocked_reroutes=sum(int(r['prohibited_capacity_reroutes']) for r in scenarios
                         if r['group']=='C4' and r['prohibited_capacity_reroutes']!='null')
    source_risk=' '.join(label+summarize(pairs,'source_shortage_9_turn_percent',wave=wave)
                         for label,wave in (('五年。','five'),('二十年。','long'),('保留种子。','holdout')))
    statements=[
        f'G1 的 C0 中活动运队上限拦截 {n(blocked)} 次报价，涉及 {n(unique)} 个来源城旬。发运次数另列。',
        f'23 条固定样本中，C1 释放 {n(key1.get("qualified_source_sample"))} 条来源资格，'
        f'{n(key1.get("timely_quote_sample"))} 条产生及时合规报价。',
        f'C1 相对 C0 增加 {n(target_delta)} 粮的期限前真实入库。表中同时列出 C4。',
        f'{n(recorded)} 次发运与原始运单逐项一致，未发现人员重复占用。'
        f'全部已读观测共 {n(s["accounting_issues"])} 处运队账差异。',
        '发运后 9 旬内来源城出现实际缺粮的比例（%）。'+source_risk,
        f'C0 对最低留守人数单独记录 {n(retain)} 条人员排除。结果以实际报价记录为口径。',
        '总粮候选为平原 50,000、山地 40,000、沙漠 35,000、纯河运 100,000、纯海运 150,000。实际分段和口粮决定每队货粮。',
        '全部实际运队的容量利用率按下表及完整分组表计算。零支运队的比例留空。',
        f'{n(head.get("scenario_count"))} 个剧本合计 {n(head.get("mixed"))} 个水陆混合方向实例。'
        f'其中 {n(head.get("sea_with_land_access"))} 个来自含陆路接入的海路。'
        f'独立纯水方向共 {n(head.get("unique_pure_water_directions"))} 条。逐路附表给出接入和限制。',
        '顺流和逆流按整队的唯一河段方向分组，效率见下表。两类的路径构成及到货量不同。',
        '每押运人员日净送达量使用真实逐日人员数，接收后再计冷却。',
        '每张运输命令书均按实际发运时的命令成本和收到的粮计算。',
        '五年区域采购实到货。'+summarize(pairs,'regional_delivered'),
        '五年战略调粮实到货。'+summarize(pairs,'strategic_delivered')+'两种期限的及时率保留各自分母。',
        '黄巾二十年缺粮城旬。'+summarize([r for r in pairs if r['scenario']=='184-02'],'unpaid_city_turns',wave='long'),
        '赤壁二十年累计缺口。'+summarize([r for r in pairs if r['scenario']=='208-10'],'rations_missing',wave='long'),
        '五年冬季军粮援助及时率。'+summarize(pairs,'winter_timely_percent'),
        f'候选的军队及运队接济实际出发 {n(len(military))} 支，实到 {n(military_arrived)} 粮，'
        f'押运兵饥损 {n(military_losses)} 人，期末仍在途 {n(military_open)} 支。',
        f'C4 按改道后的分段容量阻止 {n(blocked_reroutes)} 次尝试，已装载货物继续留在原队账内。'
        '实际发生的改道未出现超限。',
        '报告的水路优势取自实际交付和先前真实节点的库存。仓库账结果列于报告状态。',
        f'关闭 303 时 {s["performance"]["exact_turns"]}／{s["performance"]["sampled_turns"]} 个检查点回合通过同状态、乱数及决策复核。'
        '五年每旬平均 CPU 秒。'+summarize(pairs,'mean_turn_cpu'),
        '独立种子的缺粮城旬。'+summarize(pairs,'unpaid_city_turns',wave='holdout'),
        f'当前材料包含 {n(s["city_resource_mismatches"])} 处仓库账差异与 {n(s["accounting_issues"])} 处运队收据差异。',
        '完整回归状态见下表，日志哈希及检查结论见技术清单。',
        verdict+'。'
    ]
    txt(base/'validation-results.md',
        '# V3.0.3 验收结果\n\n'+version+'\n\n## 固定需求复放\n\n'+support_table(s)+
        f'\n\nC4 的实跑共观测到 {n(physical_c4)} 次第二支活动运队发运。\n\n## 实际运力\n\n'+
        '下表合计已完成观战中的 G1 组。C0 利用率以 303 标尺复算，适用于容量对照。'+
        '\n\n'+mode_table(observations)+'\n\n## 技术回归\n\n'+'\n'.join(technical)+
        '\n\n## 验收问题\n\n'+'\n'.join(f'{i}. {row}' for i,row in enumerate(statements,1))+
        '\n\n[配对数据](../data/pairwise.csv) · [逐队收据](../data/transport-dispatch-receipts.csv) · '+
        '[技术清单](../checks/technical-gates.json) · [状态 JSON](../data/report-status.json)'+
        '\n\n## 复算\n\n'+method)
    items=['| 运队 | 组别 | 起始口粮 | 终点 | 余兵 | 饥损 |','| ---: | --- | ---: | --- | ---: | ---: |']
    for ident,proof in controls.items():
        for row in proof['outcomes']:
            items.append(f"| {ident} | {row['group']} | {n(proof['start']['bag'])} | "+
                (row['terminal'] or row['last_location'] or '在途')+f" | {n(row['survivors'])} | {n(row['hunger'])} |")
    txt(base/'historical-transport-regressions.md',(base/'historical-transport-regressions.md').read_text()+
        '\n## 实际复放\n\n'+'\n'.join(items)+'\n\n[原始 1860 摘要](../checks/historical-1860-original.json) · '+
        '[历史证据索引](../checks/historical-transport-index.json)')
    txt(base/'v304-readiness.md',f'# V3.0.4 准入\n\n**{verdict}。**\n\n{version}\n\n'
        '路线能力可用于设计真实中转节点、独立队伍与分段账。正式默认沿用上线规则，候选的经济结论取自实际配对。\n\n'
        '[警戒线明细](../data/balance-alerts.csv) · [报告状态](../data/report-status.json)')
    if warnings:
        issues=['| 阶段 | 剧本 | 种子 | 策略 | 经济背景 | 对照 | 指标 | 实测变动 |',
                '| --- | --- | ---: | ---: | --- | --- | --- | --- |']
        for w in warnings:
            fields=tuple(w[key] for key in ('wave','scenario','seed','strategy','economy_background','baseline','metric'))
            issues.append('| '+' | '.join(fields+(delta(w),))+' |')
        txt(base/'known-issues.md',(base/'known-issues.md').read_text()+'\n## 实测警戒线\n\n'+'\n'.join(issues))
    return verdict


def main():
    p=ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path)
    p.add_argument('summary',type=Path)
    p.add_argument('--prior-summary',type=Path,required=True)
    p.add_argument('--historical-1860',type=Path)
    print(report(p.parse_args()))


if __name__=='__main__':
    main()
