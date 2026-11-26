"""Render conclusions and unresolved checks from the readable CSV/JSON layer."""
from argparse import ArgumentParser
import json
from pathlib import Path
from statistics import median

from v3021_report import output, read
from v302_report import csv_file_rows


def rows(data,name):
    path=data/f'{name}.csv'
    return list(csv_file_rows(path)) if path.exists() else []


def show(value):
    if value in (None,'','null','not_applicable'):
        return '—'
    number=float(value)
    return f'{int(number):,}' if number.is_integer() else f'{number:,.2f}'


def group_key(row):
    return (row['wave'],row['scenario'],row['seed'],row['strategy'],row['weather'])


def case_table(scores, wave):
    facts={(*group_key(r),r['group']):r for r in scores if r['wave']==wave}
    cases=sorted({key[:-1] for key in facts})
    lines=['| 剧本 | 种子 | 策略 | 天气 | 组 | 实际旬 | 缺粮城旬 | 缺粮 | 冬季及时率 % | 运队饥损 | 战斗 |',
           '| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    metrics=('completed_turns','unpaid_city_turns','rations_missing','winter_timely_percent',
             'convoy_hunger_losses','battles')
    for case in cases:
        for group in ('G0','G1','G3d','G3','G4','G4-no-winter','G4-relay'):
            if r:=facts.get((*case,group)):
                lines.append('| '+' | '.join([*case[1:],group,*[show(r[k]) for k in metrics]])+' |')
    return '\n'.join(lines)


def fixed(data):
    grouped={}
    for r in rows(data,'fixed-state-performance'):
        name,mode = r['sample'].rsplit('-',2)[0], r['detailed']
        grouped.setdefault((name,mode,r['group']),[]).append(r)
    lines=['| 检查点 | 详细观测 | G1 P95 秒 | G2 P95 秒 | 改变 | 每组重复 |',
           '| --- | --- | ---: | ---: | ---: | ---: |']
    for key, before in sorted(grouped.items()):
        name, mode, group=key
        if group!='G1':
            continue
        after=grouped[name,mode,'G2']
        a,b = (median(float(r['cpu_p95']) for r in values) for values in (before,after))
        lines.append(f'| {name} | {"开" if mode=="true" else "关"} | {a:.3f} | {b:.3f} | {(b-a)/a*100:+.1f}% | {len(before)} |')
    return '\n'.join(lines)


def delivery_table(data):
    fields = ('delivered_grain','order_window_pct','first_forecast_window_pct')
    cohorts = {(*group_key(row),row['group']):row for row in rows(data,'comparable-dispatch-deadlines')
               if row['wave'] in ('long','holdout')}
    lines = ['| 观战 | 剧本 | 种子 | 策略 | 净到粮 | 运单期限及时率 % | 发运当旬最早缺口及时率 % |',
             '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for key in sorted({key[:-1] for key in cohorts},reverse=True):
        base, candidate = (cohorts.get((*key,group)) for group in ('G1','G4'))
        if base and candidate:
            label = '二十年' if key[0]=='long' else '保留种子'
            values = [f'{show(base[field])} → {show(candidate[field])}' for field in fields]
            lines.append('| '+' | '.join((label,*key[1:4],*values))+' |')
    return '\n'.join(lines)


def returns(build, summary):
    evidence=read(build/'historical/historical-return-traces.json')
    result=[]
    for item in evidence:
        ident=item['convoy']
        path=build/'checks'/f'return-{ident}.json'
        old=item['convoy-survival'][0]
        match=None
        after=None
        action=None
        if path.exists():
            checks=read(path)
            ctrl=checks['control']
            exp=checks['candidate_return_only']
            if ctrl['terminal'] and exp['terminal']:
                expected=ctrl['terminal']
                match=(expected['city']==old['actual_position'] and expected['tick']==int(old['actual_terminal_tick'])
                       and expected['hunger']==int(old['escort_hunger_loss'])
                       and ctrl['starting']['delivered']==exp['starting']['delivered'])
                after=exp['terminal']
                action=[{'kind':r['event'],'decision':r.get('decision'), 'tick':r['tick'],'city':r.get('actual_position'),
                         'amount':r.get('amount')} for r in exp['trace'] if r['event'] in
                        ('emergency_refill','emergency_decision','emergency_plan')]
            target=summary/'checks'/path.name
            target.write_bytes(path.read_bytes())
        result.append(dict(convoy=ident, archived= item['path'],control_matches_historical=match,
            archived_received_city=old['actual_position'],archived_terminal_tick=int(old['actual_terminal_tick']),
            archived_hunger=int(old['escort_hunger_loss']), new_received_city=after['city'] if after else None,
            new_terminal_tick=after['tick'] if after else None,new_hunger=after['hunger'] if after else None,
            receipt_balanced=after['balanced'] if after else None,new_node_actions=action))
    output(summary/'data/return-ration-replay.csv',result)
    return result


def write(folder,name,body):
    (folder/f'{name}.md').write_text(body.strip()+'\n',encoding='utf-8')


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('summary',type=Path)
    args=parser.parse_args()
    summary=args.summary
    docs,data=summary/'docs',summary/'data'
    docs.mkdir(parents=True,exist_ok=True)
    scores=rows(data,'scenario-scores')
    alert=rows(data,'balance-alerts')
    status=read(data/'report-status.json')
    gate=read(summary/'checks/technical-gates.json')
    manifest=read(data/'simulation-manifest.json')['simulations']
    old_holdout=returns(args.build,summary)
    successes=(sum(g['passed'] is True for g in gate['gates']),len(gate['gates']))
    main_alerts=[r for r in alert if r['group']=='G4']
    finals={group_key(row):row for row in scores if row['group']=='G4'}
    comparable={group_key(row) for row in scores if row['group']=='G1' and
                finals.get(group_key(row),{}).get('completed_turns')==row['completed_turns']}
    long_count=sum(key[0]=='long' for key in comparable)
    holdout_count=sum(key[0]=='holdout' for key in comparable)
    unfinished=[r for r in manifest if r['status'] not in ('complete','natural_end')]
    old_limits=rows(data,'historical-source-convoy-limit-analysis')
    capability=rows(data,'spatial-grain-capability-funnel')
    no_lift=sum(int(r['l0_other_city_stock'])>0 and r['l3_distinct_sources']=='0' for r in capability)
    can_meet=sum(int(r['l4_estimated_net_upper_bound'])>0 for r in capability)
    actual_receptions=[int(r['l5_actual_reception']) for r in capability if r['l5_actual_reception']!='null']
    waiting_for_escort=[r for r in rows(data,'escort-persistence-by-city')
                        if r['wave']=='long' and r['scenario']=='184-02' and r['group']=='G4']
    sustained=len({row['source'] for row in waiting_for_escort
                   if int(row['longest_consecutive_observed_turns'])>=3})
    occupied_with_staff=[
        row for row in rows(data,'source-task-blockers')
        if int(row['surplus'])>0 and int(row['personally_qualified_available'])>0
        and any(phase=='returning' and delivered for phase,delivered in
                zip(json.loads(row['phases']),json.loads(row['cargo_delivered'])))
    ]
    custody=rows(data,'reserve-overlap-audit')
    overlap=sum(int(r['overlapping_tag'])>0 for r in custody)
    physical=sum(int(r['pair_rejections']) for r in old_limits
                 if r['group']=='S3' and r['scenario'] in ('184-02','208-10'))
    alerts_text=['| 剧本 | 种子 | 策略 | 指标 | G0 | G4 |','| --- | ---: | ---: | --- | ---: | ---: |']
    for row in main_alerts:
        alerts_text.append('| '+' | '.join((row['scenario'],row['seed'],row['strategy'],row['metric'],
                                            show(row['before']),show(row['after'])))+' |')
    balance_unknown=(long_count<3 or holdout_count<2)
    technical=(successes[0]==successes[1] and status['fixed_state_parity']['all_exact']
               and len(status['fixed_state_parity']['by_checkpoint'])==4
               and status['city_account_errors']==0 and status['reserve_account_errors']==0)
    structural_alerts = [r for r in rows(data,'pairwise') if r['wave']=='long'
                         and r['group']=='G4' and r['baseline']=='G1'
                         and ((r['metric'] in ('unpaid_city_turns','rations_missing')
                               and r['change_pct']!='null' and float(r['change_pct'])>20)
                              or (r['metric']=='winter_timely_percent' and float(r['delta']) < -5))]
    readjust=bool(structural_alerts)
    ablation={r['group']:r for r in scores if (r['wave'],r['scenario'],r['strategy'])==('winter','184-02','211')}
    if all(key in ablation for key in ('G3d','G3','G4')):
        a,b,c=(ablation[key] for key in ('G3d','G3','G4'))
        node=[r for r in rows(data,'return-review-interventions')
              if (r['wave'],r['scenario'],r['strategy'],r['group'])==('winter','184-02','211','G4')]
        write(docs,'ablation-results',f'''
# 黄巾策略消融

同一 184-02／2026／211／221 的五年轨迹，G3d 只变更剩余需求，G3 再打开储备协调，G4 再打开返程节点动作。

| 指标 | G3d | G3 | G4 |
| --- | ---: | ---: | ---: |
| 缺粮城旬 | {a['unpaid_city_turns']} | {b['unpaid_city_turns']} | {c['unpaid_city_turns']} |
| 累计缺口 | {show(a['rations_missing'])} | {show(b['rations_missing'])} | {show(c['rations_missing'])} |
| 运队饥损 | {a['convoy_hunger_losses']} | {b['convoy_hunger_losses']} | {c['convoy_hunger_losses']} |

G4 记录到 {len(node)} 次新的节点动作。该实验的长期战况可因人员接收位置及实际补粮支出而分叉，观察到的差额只适用于本种子。返程历史专项核对了每笔货粮与人员直接效果。''')
    return_count=sum(r['control_matches_historical'] is True and r['receipt_balanced'] is True for r in old_holdout)
    admission='可独立开展容量原型' if technical and not balance_unknown and not readjust and return_count==3 else '暂缓依赖本候选的 V3.0.3 验收'
    checks='全部通过' if technical else '仍有硬性检查未完成或未通过'
    backend_results = {row['gate']:row['results'] for row in gate['gates']}
    py_results = '、'.join(note for note in backend_results.get('final-python',[]) if note.startswith(('Ran ','OK')))
    rust_results = '、'.join(note for note in backend_results.get('final-rust',[]) if note.startswith(('Ran ','OK')))
    return_results = '，'.join(f"{row['convoy']} 号 {row['archived_hunger']} → {row['new_hunger']} 人"
                              for row in old_holdout if row['new_hunger'] is not None)
    encode = {row['group']:row['value'] for row in rows(data,'route-cache-profile')
              if row['sample']=='yellow-long-detail-r1' and row['metric']=='_encode_request'}
    encoding_result = (f"黄巾后期九旬编码调用 {show(encode['G1'])} → {show(encode['G2'])}。"
                       if {'G1','G2'} <= encode.keys() else '')
    write(docs,'validation-results',f'''
# V3.0.2.1 验证结果

固定候选源码 `{gate['source']}`。完成或复用了 {status['completed_runs']}／{status['expected_runs']} 局观战，其中历史档 {status['reused_runs']} 局。各组实际截止日期和无法配对的原因见 `simulation-manifest.json`。目前有 {len(unfinished)} 个槽位没有合格完成记录。

官仓资源核对差异 {status['city_account_errors']}，战略储备及运单核对差异 {status['reserve_account_errors']}。技术门槛 {successes[0]}／{successes[1]} 通过。固定状态比对 {status['fixed_state_parity']['turns']} 个配对旬，详细结果见下表与逐旬 SHA。

同天气种子的已完成配对中，逐日天气文件精确一致 {status.get('weather_traces_exact',0)}／{status.get('weather_traces_compared',0)} 份。真实固定点有 {len(capability)} 个目标评估，其中 {no_lift} 个目标虽有其他同势力库存，仍未找到合格来源。{can_meet} 个目标有赶得上最早缺口的预计净量。{len(actual_receptions)} 个期限窗已从同起点实跑到结算前一旬，其中 {sum(n>0 for n in actual_receptions)} 个有新增调粮的实际接收记录。仓内分账审视 {len(custody)} 个城池样本，标签与现有承诺有数值重叠的样本 {overlap} 个。

{fixed(data)}

## 五年天气与对照

{case_table(scores,'winter')}

## 五年无天气

{case_table(scores,'dry')}

## 净到粮与及时率

表内由 G1 到 G4。及时率按粮量计，分母是同批匹配收据的实际净到粮。发运当旬最早缺口这一列使用各局真实观测的最早期限，能看出延长运单期限对及时率的影响。

{delivery_table(data)}

## 平衡警戒线

{chr(10).join(alerts_text) if main_alerts else '当前已有合格配对中，G4 相对 G0 未触发警戒线。'}

## 逐项结论

| 问题 | 基于现有证据的回答 |
| --- | --- |
| 黄巾缺粮城旬接近翻倍 | 2,166 次里重叠出现了晚到、来源资格和已有运单阻塞。单次中位缺口从 157.5 到 30 粮。证据可确认城市级去重缺陷，发生频率变化的全部经济因果仍待核实。 |
| 是否有储备重复保护 | 302 的可售余额与规划承诺口径不一致。3021 按真实承诺后再分配逻辑标签。实际旧档分账样本见 `reserve-overlap-audit.csv`，不能外推至全部城旬。 |
| 现有运单是否拦截后续补给 | 是。黄巾 S3 的 1,119 次目标阻塞中，1,098 次同旬预测仍有缺口。新的实运单专项覆盖了部分到货、足额和到货过晚。 |
| 押运人员缺乏的组成 | 区分无驻城、最低留守、君主和官职、既定出征、体力、回执冷却、当旬已行动。黄巾二十年 G4 有 {sustained} 座城市至少连续三旬被观测到无合资格押运。合法调人能改善多少城尚未确认。 |
| 来源已在运输的实际损失 | 两局旧长期 S3 留下 {physical:,} 条来源上限候选拒绝。固定点有 {len(occupied_with_staff)} 条来源样本在已有运队交付后返程期间仍有余粮与合格人员。若放开上限能多送到多少粮未确认。 |
| 有无不改运力的解决方案 | 日期化的剩余需求、有效承诺分账、节点补粮及就地接收都用原有人员和运输限制。 |
| 储备与紧急军事补给如何协调 | 保护已核实的承诺和来源地必要口粮。满足两至三旬缺口的及时运输才评估条件释放。 |
| 有多少来源缺粮由预算错误造成 | 九旬原口径下，黄巾 25 城旬、赤壁 28 城旬与此前发运共现。七笔和四笔属于三旬内的逐运单统计。因果数量未确认。 |
| 战略调粮及时率 | 三个二十年配对的运单期限及时率均上升。按发运当旬最早缺口，两个策略 211 配对下降，策略 212 小幅上升。 |
| 冬季军粮补给 | 二十年赤壁 211 改善，黄巾 211 和赤壁 212 下降。赤壁 2036 保留种子相对 G0 的差额触发五个百分点警戒，逐局实付见冬季表。 |
| 真实净送达量 | 三个二十年配对均增加，两个保留种子配对略降。最终目标实收单独统计，中转首腿在明细中保留。 |
| 2170／1228／219 | {return_count} 项真实复放与原记录及收据核对一致。实际饥损为 {return_results}。2170 途中天气改变且无中间节点。1228 提前在陈留接收，219 在颍川补到真实余粮。 |
| 性能主要热点 | 冬季合法路网反复准备方向及调用编码。战斗、预算和视图亦有占用。 |
| 实际工作减少多少 | {encoding_result} 逐旬请求、路径及候选见性能表。 |
| 纯性能实际行为 | 已完成的固定点全等价标记为 {status['fixed_state_parity']['all_exact']}，详见逐旬及 RNG。 |
| 黄巾后期 P95 | 本页固定点表报告测量。整场实际 CPU 在 `performance-comparison.csv`。 |
| 赤壁长期改善 | 见长期报告实测值。没有合格 G1／G4 对照时保持未确认。 |
| 策略 212 二十年 | 见长期报告单列对照及实际终点。 |
| 新保留种子 | 已有 {holdout_count} 个 G1／G4 配对，S1 差值及冬季警戒线见独立报告。 |
| 真实运输容量限制 | 来源任务、押运人手、合法路线和实际期限仍是约束，现有数据没有支持提前更改运力参数。 |
| Python／Rust 最终全量回归 | Python {py_results}，Rust {rust_results}。Python 的一项原生兼容用例由 Rust 覆盖。 |
| V3.0.3 准入 | {admission}。 |
''')
    write(docs,'long-term-balance-results',f'''
# 二十年配对

完成 {long_count}／3 组 G1 与 G4 的可比分组。表内所有有数值的记录均来自实际结算。若某组未运行至同一实际截止日，只保留其独立记录，比较数量保持原样。

{case_table(scores,'long')}

横向包含黄巾、赤壁策略 211 与赤壁策略 212。赤壁策略 211 的部分旧档运行带有非空工作区差异摘要，作为历史参考保留，合格 G1 使用同剧本、同种子和同策略新跑。在应用 G0 警戒线时不以 G1 取代 S1。''')
    write(docs,'holdout-results',f'''
# 冻结后的保留种子

种子 2035 和 2036 在冻结的同一候选提交后运行。旧 2034 归到历史回归，不属于本次保留样本。每个配对配置在启动前记录，保持天气种子、剧本和实际截止日一致。赤壁使用策略 212。

{case_table(scores,'holdout')}

固定候选上的实际告警见 `balance-alerts.csv`。冬季及时率的绝对下降超过五个百分点才触发此项警告，分母只含实际有冬季军事请求的运行。''')
    write(docs,'known-issues',f'''
# 已知限制和未决事项

- 旧用户官渡存档的剧本摘要与当前目录不符，V3.0.2 基线和候选拒绝原因相同。基线引擎生成的同版官渡档在两个后端及普通／紧凑格式下通过逐字节回读。
- 历史缺粮关联未建立全部因果。旧运行没有采集各来源限额解除后的反事实净粮，也不能从月末库存倒推出这部分。
- 固定点详细采样包含引擎观察钩子。完整 CSV、ZIP 和浏览器 CPU 等开销分开报告。
- {len(unfinished)} 个槽位没有合格完成记录，{len(main_alerts)} 条 G4 警告保留在总表。
- 仍然受真实地理和人员限制。2170 一类无中间节点的行程可能受途中实际天气影响。
''')
    write(docs,'v303-readiness',f'''
# V3.0.3 准入

**{admission}。**

技术状态为{checks}。相同截止日的二十年配对 {long_count}／3，独立新种子配对 {holdout_count}／2，历史返程符合原记录及账的复放 {return_count}／3。

候选保持手动选用。黄巾缺粮城旬有所下降，累计缺口仍高于 G0、G1 和候选目标，且老基线的缺粮还无法主要归因于运输容量。赤壁策略 212 的二十年冬季军粮及时率低于 G1，保留种子 2036 也低于 G0，均超过五个百分点。后续独立容量原型可用已验证的运输限制和 G0／G1 对照单独评估。''')


if __name__=='__main__':
    main()
