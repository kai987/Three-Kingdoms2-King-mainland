"""Write the readable concurrency analysis and retain portable detailed evidence."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import csv
from itertools import islice
import json
from pathlib import Path
from common import TOOL_ROOT, git, to_csv, to_json
from v3021_report import file_sha, read
from v3031_experiments import options
from v304_packaging import copy_portable

IDENTITY=('wave','scenario','seed','strategy','weather','requested_months','economy_background','group')
SAMPLE_FIELDS=('wave','scenario','seed','strategy','economy_background','turn','source','target','deadline',
               'shared_limit','convoy_ids','occupied_purposes','actual_request_success','other_eligibility_checked')


def rows(path):
    with path.open(encoding='utf-8',newline='') as file:
        yield from csv.DictReader(file)


def number(value):
    return float(value) if value not in ('true','false','null','') else int(value=='true')


def slot_records(summary,build):
    data=summary/'data'
    raw=build/'derived-observations'
    raw.mkdir(parents=True,exist_ok=True)
    totals={}
    for name in ('urgent-dispatch-blockers','dispatch-priority-conflicts'):
        original=raw/f'{name}-full.csv'
        output=data/f'{name}.csv'
        if not original.exists():
            output.replace(original)
        index=[]
        aggregate=defaultdict(Counter)
        examples={}
        with original.open(encoding='utf-8',newline='') as handle:
            all_rows=csv.DictReader(handle)
            for part,subset in enumerate(iter(lambda:list(islice(all_rows,55_000)),[]),1):
                path=raw/f'{name}-{part:02}.csv'
                with path.open('w',encoding='utf-8',newline='') as result:
                    writer=csv.DictWriter(result,all_rows.fieldnames,lineterminator='\n')
                    writer.writeheader()
                    writer.writerows(subset)
                index.append(dict(file=path.name,rows=len(subset),bytes=path.stat().st_size,sha256=file_sha(path)))
                for row in subset:
                    key=tuple(row[field] for field in IDENTITY)+ (row['shared_limit'],)
                    aggregate[key].update(screened=1,otherwise_eligible_checked=number(row['other_eligibility_checked']),
                        request_succeeded=number(row['actual_request_success']),
                        same_target_in_pool=number(row['demand_destination_overlap']))
                    if key not in examples:
                        examples[key]={field:row[field] for field in SAMPLE_FIELDS}
        to_csv(output,[dict(zip((*IDENTITY,'shared_limit'),key),**values) for key,values in sorted(aggregate.items())])
        to_csv(data/f'{name}-examples.csv',list(examples.values()))
        to_csv(data/f'{name}-partition-index.csv',index)
        totals[name]=sum(row['rows'] for row in index)
    return totals


def split_occupation(summary,build):
    data=summary/'data'
    original=build/'derived-observations'/'origin-slot-occupation-full.csv'
    reduced=data/'origin-slot-occupation.csv'
    if not original.exists():
        reduced.replace(original)
    counts=defaultdict(Counter)
    with original.open(encoding='utf-8',newline='') as stream:
        detail=csv.DictReader(stream)
        for part,batch in enumerate(iter(lambda:list(islice(detail,4500)),[]),1):
            to_csv(data/f'origin-slot-occupation-part-{part:02}.csv',batch)
            for row in batch:
                key=(row['wave'],row['economy_background'],row['group'],row['purpose'])
                counts[key].update(departures=1,days=int(number(row['occupancy_days'])),
                                   still_in_transit=int(row['right_censored']=='true'))
    to_csv(reduced,[dict(zip(('wave','economy_background','group','purpose'),key),**count)
                   for key,count in sorted(counts.items())])


def efficiency(summary):
    selected=defaultdict(Counter)
    fields=('officer_days','officer_cooldown_days','clerk_days','clerk_cooldown_days','escort_troop_days',
            'departures','closed','complete_cycle_days','actual_delivered','command_books',
            'military_only_grain','military_only_days','clerk_only_grain','clerk_only_days','mixed_crew_grain')
    for row in rows(summary/'data/officer-occupation-comparison.csv'):
        if row['economy_background']=='G1' and row['group'] in ('D1','D2'):
            kind=row['wave'],row['group']
            selected[kind].update({key:int(number(row[key])) for key in fields})
    result=[]
    for (wave,group),count in sorted(selected.items()):
        received=count['actual_delivered']
        officer=count['officer_days']+count['officer_cooldown_days']
        clerk=count['clerk_days']+count['clerk_cooldown_days']
        result.append(dict(wave=wave,group=group,**count,
            net_per_officer_day=count['military_only_grain']/count['military_only_days'] if count['military_only_days'] else None,
            net_per_clerk_day=count['clerk_only_grain']/count['clerk_only_days'] if count['clerk_only_days'] else None,
            net_per_all_person_days=received/(officer+clerk) if officer+clerk else None,
            net_per_book=received/count['command_books'] if count['command_books'] else None,
            mean_closed_cycle_days=count['complete_cycle_days']/count['closed'] if count['closed'] else None))
    to_csv(summary/'data'/'officer-unit-efficiency.csv',result)
    return {(row['wave'],row['group']):row for row in result}


def stalled_cases(summary, build):
    result=[]
    for run in read(summary/'data/simulation-manifest.json'):
        if run['input']!='current':
            continue
        folder=(build/run['relative_path']).parent
        cases=[row for row in rows(folder/'convoy-survival.csv') if row['terminal_status']=='dangerous_stalled']
        if not cases:
            continue
        decisions={row['convoy_id']:row for row in rows(folder/'emergency-transport-decisions.csv')}
        for case in cases:
            latest=decisions.get(case['convoy_id'],{})
            result.append(dict({k:run[k] for k in IDENTITY},csv_path=(folder/'convoy-survival.csv').relative_to(
                build).as_posix(),**case,review_decision=latest.get('decision'),
                nearest_legal_exit=latest.get('emergency_target'),exit_rations=latest.get('emergency_route_budget'),
                legal_local_supply=latest.get('available_local_supply')))
    to_csv(summary/'data/stalled-transport-review.csv',result)
    return Counter(row['group'] for row in result)


def selection(summary,build,prior):
    checks=summary/'checks'
    for name in ('historical-transport-index.json','historical-1860-original.json'):
        source=prior/'checks'/name
        copy_portable(source,checks/source.name)
    for name in ('historical-1860-relief-review.json','historical-3634-relief-review.json'):
        source=build/'checks'/name
        copy_portable(source,checks/source.name)
    review=read(checks/'historical-3634-relief-review.json')
    start=read(checks/'historical-3634-replay.json')
    for first,current in zip(start['checkpoints'],review['rows'],strict=True):
        assert first['save_sha256']==current['fixture_sha256']
        assert first['state_sha256']==current['loaded_state_sha256']
    to_csv(summary/'data/historical-return-3634.csv',review['rows'])
    review_old=read(checks/'historical-1860-relief-review.json')
    original=read(checks/'historical-1860-review.json')
    for old,new in zip(original['checkpoints'],review_old['checkpoints'],strict=True):
        assert all(old[k]==new[k] for k in old)
    to_csv(summary/'data/historical-return-1860.csv',review_old['checkpoints'])
    return start,review_old


def score_matrix(scores,wave,scenario,strategy,fields):
    identity=('scenario','seed','strategy','economy_background','group')
    pending=[row for row in scores if row['wave']==wave
             and (scenario is None or row['scenario']==scenario)
             and (strategy is None or row['strategy']==str(strategy))]
    order={'historical-G0':0,'D0':1,'D1':2,'D2':3,'D3':4}
    selected=sorted(pending,key=lambda row:(row['scenario'],row['strategy'],order[row['group']]))
    def render(value):
        if value=='null':
            return '—'
        numeric=float(value)
        return f'{int(numeric):,}' if int(numeric)==numeric else f'{numeric:,.2f}'
    labels={'unpaid_city_turns':'缺粮城旬','rations_missing':'累计缺粮','winter_requested':'冬季申请',
            'winter_delivered_timely':'冬季及时实收','winter_timely_percent':'及时率 %',
            'convoy_hunger_losses':'运队饥损','longest_streak':'最长缺粮连旬','battles':'战斗',
            'small_faction_survival_percent':'小势力存续 %','mean_turn_cpu':'CPU 秒/回合'}
    headers=('剧本','种子','策略','经济背景','组',*(labels[field] for field in fields))
    return '\n'.join(('| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |',
        *('| '+' | '.join([*(row[k] for k in identity),*(render(row[field]) for field in fields)])+' |' for row in selected)))


def origin_limit_summary(summary):
    groups=defaultdict(Counter)
    for row in rows(summary/'data/origin-slot-purpose.csv'):
        groups[row['group']].update({row['purpose']:int(number(row['second_departures']))})
    return groups


def final_docs(summary,run,province,case,units):
    docs=summary/'docs'
    docs.mkdir(parents=True,exist_ok=True)
    data=summary/'data'
    scores=list(rows(data/'scenario-scores.csv'))
    warnings=list(rows(data/'balance-alerts.csv'))
    fixed=run['fixed']
    table='| 组 | 期限前有到货的目标 | 足额目标 | 截止前实收粮 | 战略渠道实收粮 | 合格及时来源组 |\n|---|---:|---:|---:|---:|---:|\n'
    table+='\n'.join(f"| {g} | {fixed[g]['positive']} | {fixed[g]['full']} | {fixed[g]['actual']:,} | "
                    f"{fixed[g]['strategic']:,} | {fixed[g]['timely']} |" for g in ('D0','D1','D2','D3'))
    caution=Counter((row['group'],row['baseline']) for row in warnings)
    concerns=[r for r in warnings if r['group']=='D2' and r['baseline']=='D1']
    caution_table="| 剧本 | 策略 | 背景 | 项目 | D1 | D2 |\n|---|---:|---|---|---:|---:|\n"+'\n'.join(
        f"| {r['scenario']} | {r['strategy']} | {r['economy_background']} | {r['metric']} | "
        f"{float(r['before']):,.2f} | {float(r['after']):,.2f} |" for r in concerns)
    prior=run['prior_c4_second_dispatch_purposes']
    current=origin_limit_summary(summary)['D2']
    purposes='| 用途 | 上轮 C4 | 本轮 D2 |\n|---|---:|---:|\n'+'\n'.join(
        f'| {label} | {format(prior[key],",") if key in prior else "—"} | '
        f'{format(current[key],",") if key in current else "—"} |' for label,key in (
        ('一般调粮','ordinary'),('战略调粮','strategic'),('区域采购','regional'),('前线军队接济','army'),
        ('带期限的城池军粮接济','military_city'),('运队接济','convoy_relief')))
    personnel="| 观测组 | D1 每武将日 | D2 每武将日 | D1 每本 | D2 每本 |\n|---|---:|---:|---:|---:|\n"+'\n'.join(
        f"| {title} | {units[(wave,'D1')]['net_per_officer_day']:.2f} | "
        f"{units[(wave,'D2')]['net_per_officer_day']:.2f} | {units[(wave,'D1')]['net_per_book']:,.2f} | "
        f"{units[(wave,'D2')]['net_per_book']:,.2f} |" for wave,title in (
        ('five','五年 G1'),('long','二十年 G1'),('holdout','保留种子')))
    short_fields=('unpaid_city_turns','rations_missing','convoy_hunger_losses','winter_timely_percent')
    long_fields=(*short_fields,'longest_streak','battles','small_faction_survival_percent','mean_turn_cpu')
    winter_fields=('winter_requested','winter_delivered_timely','winter_timely_percent')
    convoy3634=province['ending']
    after715=next(row for row in province['checkpoints'] if row['turn']==715)
    recent=case['checkpoints'][-1]
    simple_delta=f"{fixed['D2']['actual']-fixed['D1']['actual']:,}"
    text={
        'README':f"""# V3.0.3.1 有限并发验证

实际完成 {run['current_runs']} 局新观战，复用 {run['reused_controls']} 局已核对的 D0/D3 配对，以及 {run['reused_economic_references']} 份历史 G0 基准。固定复放覆盖 89 个目标和 23 个受来源限额影响的来源记录。

{table}

有限并发单独增加 {simple_delta} 粮的期限前实收。放宽位置后短期仍有 {len(concerns)} 条对 D1 的经济或性能警戒。D2 留作下一轮有限并发候选，默认运输规则沿用 D0。

[固定需求凭证](../data/transport-capability-funnel.csv) · [实际回归](validation-results.md) · [综合准入](v304-readiness.md)
""",
        'common-safety-ablation':f"""# 共通安全规则消融

D0 使用原默认运输规则，D1 在 303 下明确关闭物理容量、有限并发、同旬双发、AI 路线方针和周转排序。版本仍启用原有 303 共通保护，包括当旬发运计数、人员资格、留守判断和来源库存保护。D2 在 D1 上只开启有限并发，并启用按势力和来源城计数的语义。

D0 → D1 在相同固定期限的实收从 {fixed['D0']['actual']:,} 降至 {fixed['D1']['actual']:,}，足额目标仍为 {fixed['D1']['full']}。长期差异随场景改变。黄巾策略 211 的累计缺口从 557,913 到 387,568；赤壁策略 211 从 392,075 到 780,525。D1 相对 D0 合计 {caution['D1','D0']} 个逐指标红线。共通规则本身就能改变长期轨迹。

[共通规则完整配对](../data/common-safety-ablation.csv) · [实验开关](../sources/reproduction-sources.json)
""",
        'concurrency-results':f"""# 有限并发的独立效果

{table}

D1 → D2 的截止前真实净送达增加 {simple_delta} 粮，足额目标增加 8 个，较 D1 增加 {100*(fixed['D2']['actual']/fixed['D1']['actual']-1):.2f}%。战略渠道实收增加 {fixed['D2']['strategic']-fixed['D1']['strategic']:,}。D2 比 D3 的总实收高 2,964，但少一项足额目标。贡献按实际城市接收凭据和最早需求期限计算。

已送达但仍回程的运输会占用同一来源城位置。D2 允许活动运队上限由 1 变为 2，当旬仍只发 1 次。

[固定来源反事实](../data/capacity-counterfactual.csv) · [完整配对](../data/concurrent-transport-comparison.csv)
""",
        'dispatch-priority-review':f"""# 第二运输位置的用途与竞争

{purposes}

上轮 {sum(prior.values()):,} 次的档案分类将带军事期限的城市补给归在普通渠道中。本轮 D2 {sum(current.values()):,} 次用真实补给调用记录识别这类任务。表中的横线表示本组记录中没有可单列的专用标签。

D1 和 D2 共记录 {run['actual_urgent_slot_screens']:,} 个带期限、季节或受保护人员的来源筛选信号。在需要未出运、其位置已有低优先级运队的记录中，D1 为 650,957 个来源筛选，D2 为 264,545 个。它们证明确有低优先级占位，并保留来源城市、目标、需求期限、运队号和同目标覆盖字段。槽位筛选发生在路线、人员、粮量及收益的逐项检查前。该计数无法确认每个候选都满足剩余条件，也不能换算为损失的运输任务或粮食。资源优先级沿用原规则。

{personnel}

武将日含纯武将运队的押运日和行动冷却，仅纳入这类运队的实际到粮。地方文吏日与其到粮、混合押运到粮、押运兵人日、完整去回程周期及命令书分别记账。G1 三个配对的单位命令书效率均下降。

[来源筛选摘要](../data/urgent-dispatch-blockers.csv) · [优先级竞争样本](../data/dispatch-priority-conflicts-examples.csv) · [单位效率](../data/officer-unit-efficiency.csv)
""",
        'historical-3634-review':f"""# 运队 3634 · 武都至新城

赤壁 208-10、种子 2026、策略 211、天气 221、二十年 C4。复现原档 {province['matched_reference_receipts']} 条事件与 299 条逐日天气及归队决策。实际初装货粮 {convoy3634['initial_grain']:,}、独立口粮 {convoy3634['original_bag']:,}。战役日 7100 入新城 {convoy3634['delivered']:,} 粮时，口粮袋剩 12,948。返程路径是新城 → 汉中 → 武都。

第 {after715['turn']} 旬到武都时，武都已归马腾。城粮 {after715['city_stock']:,} 没有本方接收权，实带口粮仅 {after715['bag']:,}，最短合法撤离需 {min(row['needed'] for row in after715['best_receiving_options']):,} 粮。没有本方合法会合点，卸货也无货可卸。曾出现较长路线的容量报价拦截，较近撤离方向的实际缺粮才是无法退出的直接障碍。期末仍在武都，饥损 {convoy3634['hunger']:,}，剩 {convoy3634['troops']:,} 人。

[检查点](../data/historical-return-3634.csv) · [逐日及原事件](../checks/historical-3634-replay.json)
""",
        'historical-1860-review':f"""# 运队 1860 · 阴平至汉中

实际在汉中交付 {recent['delivered']:,} 粮，随后经武都回阴平。复核从第 {case['checkpoints'][0]['turn']} 旬到第 {recent['turn']} 旬的 {len(case['checkpoints'])} 份真实状态，确认末态武都归马腾，城粮 {recent['city_stock']:,}，但在途运队无本方会合权、合法本地口粮或空余货粮。最短同势力接收点需 {min(row['needed'] for row in recent['best_receiving_options']):,} 粮。该队口粮为 {recent['bag']}，饥损 {recent['hunger']:,}，期末余 {recent['troops']:,} 人。

实际调用补给申请判定复核接济，没有找到可在现有状态及时发生的合法撤离、补给或卸载方案。原存档继续保留危险等待的真实结算。

[逐旬接收资格和撤离报价](../data/historical-return-1860.csv) · [原始接济复核](../checks/historical-1860-relief-review.json)
""",
        'long-term-balance-results':f"""# 二十年指标与短期魏灭蜀

{score_matrix(scores,'long',None,None,long_fields)}

黄巾 211 的 D2 缺粮改善保留，累计缺口从 D1 的 387,568 降到 233,888，也低于 D3 的 244,571。赤壁 211 从 D3 的 641,682 降到 D2 的 516,100，仍高于 D0 的 392,075。赤壁 211 运队饥损较 D3 减少 3,631。赤壁 212 较 D1 缺粮减少，但运队饥损从 1,538 增至 2,523。

{score_matrix(scores,'five','263-05',211,short_fields)}

魏灭蜀累计缺口较 D3 和 D1 减少，仍比 D0 高 25.0%。缺粮城旬与运队饥损也未回到 D0 水平。

## 冬季申请量、实收量及及时率

{score_matrix(scores,'long',None,None,winter_fields)}

三个二十年 D2 的及时比例相对 D1 上升，及时实收粮均下降。申请和实收量与比率分别汇报。

[完整长期对比](../data/long-term-economy-comparison.csv) · [冬季报告](../data/winter-army-supply-comparison.csv)
""",
        'holdout-results':f"""# 独立保留种子

{score_matrix(scores,'holdout',None,None,(*short_fields,'small_faction_survival_percent','mean_turn_cpu'))}

2039 黄巾与 2040 赤壁共四局，每局 60 月。两组相对 D1 均未触发规定的五项警戒线。该保留结果与五年主样本的冬季警戒并存。

[保留种子的完整指标](../data/holdout-comparison.csv)
""",
        'validation-results':f"""# V3.0.3.1 回归和证据

- {run['current_runs']} 个已计划的 D1/D2 正式观察全部完整结束。
- 四组固定输入逐项吻合，含种子、剧本标识、校验摘要及相同计数截止旬。
- 已汇报的粮仓失衡项 {run['warehouse_issues']}，运输凭证核对异常 {run['ledger_issues']}。
- 两个历史运队已核对途经位置、真实粮、接收权和摘要。
- 共通保护沿用已验证的 303 引擎。代码差异及完整技术命令列入凭证。

[技术门槛](../checks/technical-gates.json) · [一次运行清单](../data/simulation-manifest.json) · [独立验算](../sources/v304_recalculate.py)
""",
        'known-issues':f"""# 已识别限制与警戒

{caution_table}

旧官渡档的剧本摘要不一致仍按既有加载判定。原始记录中的未知渠道、观察结束时的在途状态、以及未采样的组合保留为空或文字状态。赤壁 3634 和 1860 处于敌城缺粮等待，历史回放保留其实际后果。

D1 与 D2 分别有 {run['dangerous_stalls'].get('D1',0)} 和 {run['dangerous_stalls'].get('D2',0)} 条期末危险滞留记录。D2 的中山 80 与张掖 2190 实际口粮和合法本地粮为零，最近报价分别缺 11、39 粮。广陵运队 2 在 D1 与 D2 都停在无回程路线状态，现役及押运人员均耗尽，但状态仍待清理。该共同问题留作后续个案，观察数据没有给滞留队补粮或强制结算。

[所有基准警戒](../data/balance-alerts.csv) · [期末滞留](../data/stalled-transport-review.csv) · [字段口径](data-dictionary.md)
""",
        'v304-readiness':"""# 后续运力基础

D2 保留为最有说服力的有限并发实验候选。固定需求及时到货、黄巾长期缺口和赤壁 211 的运输安全均优于完整 D3。D2 的短期冬季补给与单位成本仍需要更强的证据。现阶段正式默认沿用 D0。

V3.0.4 原型采用同一 D1 经济背景及相同的单独物理容量开关，分别试验直运和实际城市中转。若未来要调整来源优先级，应以单独的实验开关继续验证真实可执行的紧急订单。
""",
        'data-dictionary':"""# 统计口径

- 截止前实收到粮由真正的交付事件累计。quoted 与 forecast 只表示估计。
- 每条槽位筛选记录代表调用中的一个来源，不等于独立需求、一次失去的命令或潜在缺粮量。otherwise_eligible_checked 为 0 表示早于余下的报价检查。
- actual_delivered 是实体运队同一交付的真实净到粮，统计分组不改变粮账。负责押运的武将和文吏分开按日计，押运兵另记人日。按武将和文吏计算净到粮效率时，分子与分母来自相同类型的独立运队。截至截断时剩余占用未来尚未发生。全部实际运输另提供全员日比率。
- null 表示字段在这一组不适用或缺少证据。真实 0 是经采集后确认为零。原始作业与警戒表分开即可复核。
- 大量逐来源筛选以独立分片保留，普通文本目录保存可直接读的汇总、样本和分片 SHA-256 索引。
- 时效以各固定检查点保留的最早缺粮旬统一比较。期末仍执行的任务标为 right_censored。
"""
    }
    for name,body in text.items():
        (docs/f'{name}.md').write_text(body,encoding='utf-8')


def delivery(args):
    summary,built=args.summary,args.build
    data=summary/'data'
    selected=read(data/'report-status.json')
    totals=slot_records(summary,built)
    split_occupation(summary,built)
    assert totals=={'urgent-dispatch-blockers':selected['actual_urgent_slot_screens'],
        'dispatch-priority-conflicts':selected['actual_unsatisfied_requests_with_low_priority_slot']}
    province,case=selection(summary,built,args.prior)
    stalls=stalled_cases(summary,built)
    e=efficiency(summary)
    frozen=(built/'frozen-source.txt').read_text().strip()
    engine_baseline=args.base
    changed=git('diff','--name-only',engine_baseline,frozen,'--','source','game','crates','tests').decode().splitlines()
    if changed:
        raise ValueError(f'The observation branch changed game code: {changed}')
    expected={'capture-3634','review-1860','fixed','five-holdout','g4','long','smoke'}
    checks={}
    for name in sorted(expected):
        log=built/'logs'/f'{name}.log'
        exit=int((built/'checks'/f'{name}.exit').read_text())
        if log.stat().st_size<=0 or exit:
            raise ValueError(f'Incomplete observer gate {name}')
        checks[name]=dict(exit_code=exit,log=f'logs/{name}.log',log_bytes=log.stat().st_size,
                          log_sha256=file_sha(log),source=frozen)
    departures=list(rows(data/'observed-origin-account.csv'))
    activity=dict(orders=sum(int(row['departures']) for row in departures),
        over_activity_limit=sum(int(row['over_activity_limit']) for row in departures),
        over_turn_limit=sum(int(row['over_turn_limit']) for row in departures))
    to_json(summary/'checks/technical-gates.json',dict(observations=checks,parity=dict(
        inherited_source=engine_baseline,frozen_source=frozen,unchanged_game_paths=True),
        completed_runs=selected['current_runs'],warehouse_issues=selected['warehouse_issues'],
        convoy_receipt_issues=selected['ledger_issues'],fixed_matched=dict(targets=89,origins=23),
        actual_departures=activity,stalled_counts=stalls))
    mk=dict(source=frozen,previous_source=engine_baseline,previous_archive=args.previous_archive,
        map_sha256=next(row['map_sha256'] for row in read(data/'simulation-manifest.json') if row['input']=='current'),
        flags={name:None if name=='D0' else options(name) for name in ('D0','D1','D2','D3')},
        tools={name:file_sha(TOOL_ROOT/'tools/economy-balance'/name) for name in (
            'v3031_experiments.py','v3031_replays.py','v3031_report.py','v3031_delivery.py','v304_recalculate.py')})
    to_json(summary/'sources/reproduction-sources.json',mk)
    selected.update(holdout_approved=not any(row['wave']=='holdout' and row['group']=='D2' and row['baseline']=='D1'
                                for row in rows(data/'balance-alerts.csv')),default_change_approved=False,
                    second_dispatch_purposes=origin_limit_summary(summary)['D2'],dangerous_stalls=stalls)
    to_json(data/'report-status.json',selected)
    final_docs(summary,selected,province,case,e)
    print(json.dumps(dict(screens=totals,technical_gates=len(checks),runs=selected['current_runs']),ensure_ascii=False))


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('summary',type=Path)
    parser.add_argument('--prior',type=Path,required=True)
    parser.add_argument('--base',required=True)
    parser.add_argument('--previous-archive',required=True)
    delivery(parser.parse_args())
