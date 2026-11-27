"""Publish the V3.0.4 city prototype's measurements and technical proof."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
from shutil import copyfile

from common import TOOL_ROOT, git, to_csv, to_json
from v3021_report import file_sha, read
from v304_packaging import copy_portable


def technical(build,checks):
    runtime=(build/'frozen-source.txt').read_text().strip()
    runner=build/'checks'
    names=('native','build','node','rust-crate','wasm-parity','wasm-rebuilt-parity','pyodide-cpu',
           'browser-transshipment-retry','browser-full','disabled-source-parity','disabled-source-parity-rerun',
           'controlled-route-warehouse-samples','controlled-short-comparison','control-observations-verified',
           'topology-detail')
    history=[]
    for name in ('browser-transshipment','node','build'):
        path=(build.parent/'checks'/f'{name}.json') if name!='browser-transshipment' else runner/f'{name}.json'
        if path.is_file() and read(path)['exit_code']:
            history.append(dict(name=name,manifest=copy_portable(path,checks/f'first-{name}.json')))
    gates={}
    for name in names:
        path=runner/f'{name}.json'
        if not path.is_file():
            gates[name]=dict(status='pending')
            continue
        data=read(path)
        if name.startswith('disabled-source-parity'):
            success=data['compared']==data['matching'] and data['compared']>0
        else:
            success=data['exit_code']==0
        if 'log' not in data:
            log=build/'logs'/f'{name}.log'
            if not log.is_file():
                raise ValueError(f'No execution log for {name}')
            data.update(log=str(log.relative_to(build)),log_sha256=file_sha(log),log_bytes=log.stat().st_size)
        log=build/data['log']
        if file_sha(log)!=data['log_sha256'] or data['log_bytes']<=0:
            raise ValueError(f'Empty or changed gate log: {name}')
        body=log.read_text(encoding='utf-8')
        metrics={}
        if name=='node':
            metrics['tests']=numbers(body,r'# tests (\d+)')
            metrics['passed']=numbers(body,r'# pass (\d+)')
        elif name=='rust-crate':
            metrics['tests']=sum(numbers(body,r'(\d+) passed; \d+ failed') or [])
        elif name=='browser-full':
            known=browser_outcomes(body)
            attempts=[]
            for retry in sorted(runner.glob('browser-original-regressions-retry*.json')):
                result=read(retry)
                raw=build/result['log']
                if file_sha(raw)!=result['log_sha256']:
                    raise ValueError('Browser replay log does not match the recorded run')
                retry_outcomes=browser_outcomes(raw.read_text(encoding='utf-8'))
                for case in set(known)&set(retry_outcomes):
                    if retry_outcomes[case]:
                        known[case]=True
                attempts.append(dict(copy_portable(retry,checks/retry.name),
                                     cases=len(retry_outcomes),passed=sum(retry_outcomes.values())))
            totals_expected=numbers(body,r'Running (\d+) tests')
            success=bool(totals_expected) and len(known)==totals_expected[-1] and all(known.values())
            metrics.update(expected=totals_expected[-1],observed=len(known),passed=sum(known.values()),
                initial_failures=sum(not value for value in browser_outcomes(body).values()),
                unresolved=[case for case,value in known.items() if not value],reruns=attempts)
        elif name in ('browser-transshipment-retry','pyodide-cpu','topology-detail'):
            metrics['results']=[row for row in json_lines(body) if
                any(key in row for key in ('locale','cpu_save_bytes_equal','river_port_approaches'))]
        elif name.startswith('wasm-'):
            metrics['resolved_cases']=numbers(body,r'parity:\s*([0-9,]+)\s*Python')
        elif name.startswith('disabled-source-parity'):
            metrics=dict(compared=data['compared'],matching=data['matching'],groups=data['groups'])
            for key,result in data.get('runs',{}).items():
                sub=result['execution']
                raw=build/sub['log']
                if file_sha(raw)!=sub['log_sha256'] or not sub['log_bytes'] or sub['exit_code']:
                    raise ValueError(f'Invalid parity execution evidence: {key}')
        if not metrics:
            metrics['structured_evidence']=f'{name}.json'
        gates[name]=dict(status='passed' if success else 'failed',source=data.get('source',runtime),
            metrics=metrics,record=copy_portable(path,checks/f'{name}.json'))
    backend=runner/'backend-suite-proof.json'
    if backend.is_file():
        for kind,proof in read(backend).items():
            for shard in proof['shards']:
                assert file_sha(build/shard['log'])==shard['log_sha256'] and shard['log_bytes']>0
                for name in (shard['inventory'],f'checks/{Path(shard["log"]).stem}.json'):
                    source=build/name
                    copy_portable(source,checks/source.name)
            gates[f'campaign-{kind}']=dict(status='passed' if proof['pass_'] else 'failed',
                source=runtime,metrics={k:proof[k] for k in ('files','tests','skips','full_inventory')})
        copy_portable(backend,checks/backend.name)
    else:
        gates.update({f'campaign-{kind}':dict(status='pending') for kind in ('python','rust')})
    const_paths=('source','game','crates','tools/ci','tests')
    exceptions=['tests/browser_transshipment_smoke.mjs']
    fingerprint=read(runner/'browser-transshipment-retry.json')['source']
    changed=git('diff','--name-only',runtime,fingerprint,'--',*const_paths).decode().splitlines()
    if changed!=exceptions:
        raise ValueError(f'Unexpected changes between tested runtime and corrected browser script: {changed}')
    to_json(checks/'technical-gates.json',dict(frozen_runtime=runtime,
        corrected_test_source=fingerprint,changed_files_between_runs=changed,
        historical_attempts=history,gates=gates))
    return gates


def numbers(log,pattern):
    return [int(value.replace(',','')) for value in re.findall(pattern,log)]


def browser_outcomes(log):
    return {case:status=='✓' for status,case in re.findall(
        r'(?m)^\s*([✓✘])\s+\d+ (\[[^\]]+\] › [^\n]+?) \([\d.]+[ms]+\)\s*$',log)}


def json_lines(body):
    for line in body.splitlines():
        if line.startswith('{'):
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def metrics(pairs,short,data,checks):
    score_fields=('group','case','seed','opening_sha256','catalog_sha256','commands','final_grain','transport_handling',
                  'first_final_day','last_final_day','ration_consumed','transport_losses','officer_days_including_cooldown',
                  'final_net_per_officer_day','final_net_per_command','stage_quotes','cpu_seconds','process_peak_rss',
                  'peak_tagged_warehouse_grain','turn_boundary_tagged_grain_days')
    comparison=[]
    for e0,e1 in (pairs,short):
        for field in score_fields[5:]:
            a,b=e0[field],e1[field]
            comparison.append(dict(case=e1['case'],baseline='E0',candidate='E1',metric=field,
                before=a,after=b,change=b-a,relative_percent=100*(b-a)/a if a else None,
                pilot_target_missed=(field in ('final_grain','final_net_per_officer_day','final_net_per_command') and b<a)))
    combined=(*pairs,*short)
    to_csv(data/'scenario-scores.csv',[{field:row[field] for field in score_fields} for row in combined])
    to_csv(data/'pairwise.csv',comparison)
    to_csv(data/'balance-alerts.csv',[row for row in comparison if row['pilot_target_missed']])
    to_csv(data/'intermodal-cost-comparison.csv',[row for row in comparison if row['metric'] in (
        'commands','officer_days_including_cooldown','ration_consumed','transport_losses','last_final_day',
        'turn_boundary_tagged_grain_days','final_net_per_officer_day','final_net_per_command')])
    to_csv(data/'performance-comparison.csv',[row for row in comparison if row['metric'] in (
        'stage_quotes','cpu_seconds','process_peak_rss')])
    to_csv(data/'officer-turnover-comparison.csv',[
        dict(group=row['group'],case=row['case'],officer_days_including_cooldown=row['officer_days_including_cooldown'],
             actual_delivered=row['final_grain'],command_books=row['commands'],clerk_days=0,
             grain_per_officer_day=row['final_net_per_officer_day'],grain_per_book=row['final_net_per_command'])
        for row in combined])
    capacity,throughput,returns,hunger,slots,deadlines=[],[],[],[],[],[]
    plans={row['case']:row['plan'] for row in combined if row['group']=='E1'}
    for row in combined:
        current=plans[row['case']]
        events=row['observed_transit']
        departures={event['id']:event for event in events if event['event']=='departure'}
        terminal={event['id']:event for event in events if event['event']=='terminal'}
        receipts={event['id']:event for event in events if event['event']=='delivery'}
        modes=defaultdict(Counter)
        for ident,event in departures.items():
            arrival,ending=receipts[ident],terminal[ident]
            mode=event['profile']['mode']
            gross=event['cargo']['grain']
            rations=event['rations']
            load=gross+rations
            cap=event['profile']['physical_capacity']
            modes[mode].update(convoys=1,gross=gross,loaded_rations=rations,net=arrival['cargo']['grain'],
                               final_net=arrival['cargo']['grain'] if arrival['target']==current['target'] else 0)
            known=dict(group=row['group'],case=row['case'],convoy=ident,origin=event['source'],target=event['target'])
            capacity.append(dict(known,mode=mode,physical_capacity=cap,actual_load=load,
                                 bottleneck=event['profile']['bottleneck'],legal=load<=cap))
            returns.append(dict(known,outcome=ending['outcome'],return_city=ending['city'],
                                terminal_tick=ending['end_tick'],reusable_turn=ending['reusable_turn']))
            hunger.append(dict(known,soldiers_at_departure=event['escort_troops'],hunger_losses=ending['hunger_losses']))
            slots.append(dict(known,turn=event['turn'],active_after=event['active'],dispatches_after=event['dispatch_count']))
            deadlines.append(dict(known,departed_turn=event['turn'],received_turn=arrival['turn'],
                controlled_promise=current['promise'],first_uncovered_deadline=None,
                net_received=arrival['cargo']['grain'],final_receipt=arrival['target']==current['target']))
        throughput.extend(dict(group=row['group'],case=row['case'],mode=mode,**tally) for mode,tally in modes.items())
    for name,table in (('capacity-counterfactual',capacity),('transport-mode-throughput',throughput),
            ('convoy-return-safety',returns),('convoy-hunger-comparison',hunger),
            ('origin-concurrency-usage',slots),('comparable-dispatch-deadlines',deadlines)):
        to_csv(data/f'{name}.csv',table)
    stages=[]
    for row in combined:
        current=plans[row['case']]
        stages.append(dict(group=row['group'],case=row['case'],actual_origin_grain=sum(a['actual_load'] for a in capacity
                     if a['group']==row['group'] and a['case']==row['case'] and a['origin'] in current['sources']),
                     gross_stage_receipts=row['transport_handling'],actual_final_reception=row['final_grain'],
                     full_opening_target=current['grain'],coverage=row['final_grain']/current['grain']))
    to_csv(data/'transport-capability-funnel.csv',stages)
    to_csv(data/'winter-army-supply-comparison.csv',[dict(scope='304-controlled',status='not_measured',
         winter_test='ice_route_blocker_only',reason='no winter comparative military campaign run')])
    to_csv(data/'long-term-economy-comparison.csv',[dict(scope='304-controlled',status='not_measured',
         reason='formal economy cohort requires the independent physical terminal gate')])
    footprint=read(checks/'end-to-end-grain-account.json')
    assert footprint['residual']==0
    return comparison


def write_documents(summary,scenes,short,gates,status):
    e0,e1=scenes
    topo=read(summary/'checks/topology-audit.json')
    checks=summary/'checks'
    sample=read(checks/'control-edge-cases.json')
    sea=read(checks/'physical-controls.json')['sea']
    grain=read(checks/'end-to-end-grain-account.json')
    batch=e1['plan']['batches']
    pair_header="| 项目 | E0 直运 | E1 城池中转 |\n|---|---:|---:|"
    items=(('实际终点收粮','final_grain'),('末批入账日','last_final_day'),('命令书','commands'),
           ('途中及等待口粮','ration_consumed'),('路线及天气途耗','transport_losses'),
           ('押运武将日（含行动冷却）','officer_days_including_cooldown'),
           ('每押运武将日净到粮','final_net_per_officer_day'),('每本命令书净到粮','final_net_per_command'))
    paired=pair_header+'\n'+'\n'.join(
        f"| {label} | {e0[k]:,.2f} | {e1[k]:,.2f} |" if isinstance(e0[k],float)
        else f"| {label} | {e0[k]:,} | {e1[k]:,} |" for label,k in items)
    direct_river,pilot_river=short
    short_text=(f"将同一受控世界的目标提前到纯河运终点苍梧，两段中转实收 {pilot_river['final_grain']:,} 粮，"
                f"较两队直运的 {direct_river['final_grain']:,} 多 "
                f"{pilot_river['final_grain']-direct_river['final_grain']:,} 粮。"
                f"末批从第 {direct_river['last_final_day']} 天延后到第 {pilot_river['last_final_day']} 天，"
                f"命令书从 {direct_river['commands']} 本增至 {pilot_river['commands']} 本，"
                "单位武将和单位命令书效率仍低于直运。")
    gate_lines="\n".join(f"- {key} · {info['status']}" for key,info in gates.items())
    docs={
        'README':f"""# V3.0.4 城池水陆接驳原型

V3.0.4-A 使用现有真实城池完成集货、入仓、合并水运和分批陆运。中转需在开局菜单主动选用。实验固定剧本、种子、开局状态及其余货运开关，E0 关闭中转，E1 启用中转。

{paired}

同一受控初态下，本例应继续选直运。城池接驳发挥了纯河运单次大容量，最终到货量、军官效率及命令书效率均低于直运。独立水陆接入点与 AI 中转的阶段结论见 [正式准入](v304-formal-readiness.md)。

{short_text}

[原始交割与路线](../checks/controlled-route-results.json) · [苍梧对照](../data/short-chain-comparison.csv) · [独立复算](../sources/v304_recalculate.py)
""",
        'transshipment-node-design':"""# 中转节点

游戏内节点采用剧本现有城池身份。每段第一轮报价、发运及实际交割都会读当前归属、城池库存、道路、可用人员及命令书。原型允许同势力两座来源城、最多两座中转城、三段运输，以及每段两支实体运队。同一势力同时最多两份有效计划，全局同时最多十二份未完成结算的计划。

计划不能环行、重复承诺同一目标城，或在原缺粮期限后继续锁定粮食。完成计划保留最近十六份有实际凭证的历史账。可执行状态和归属均由引擎判定。
""",
        'route-topology-audit':f"""# 路线与接岸证据

审核 {len(topo['catalogs'])} 个剧本和 {topo['current_city_ids']} 个地图城池 ID。实际可通行的有向段中，陆路 {topo['water_directions']['land']:,} 段，混合路 {topo['water_directions']['mixed']:,} 段，纯河段 {topo['water_directions']['river']:,} 段，纯海段 {topo['water_directions'].get('sea',0):,} 段。剧本间共享道路，因此按剧本计数。

郁林、苍梧是同时与纯水段、可衔接陆段相连的两座地图城池，共 {topo['city_hub_scenario_pairs']} 个剧本／城池组合。每份可执行订单还要核查当时的同势力归属和实际人员。

长江江阳至巴郡、黄河金城至朔方、珠江郁林至苍梧及辽东至东莱已列出原路线的分段与固定点工作量。江段和海岸几何样本的加权工作量与原方向相等。

[接岸点清单](../data/transshipment-node-census.csv) · [路径样本](../data/route-split-parity.csv) · [纯水连通城池](../data/city-intermodal-connectivity.csv)
""",
        'physical-transfer-terminal':f"""# 独立水陆接驳节点

地图有 {topo['river_geometry_points']} 个河流几何点、{topo['river_port_approaches']} 个河运接岸标记和 {topo['sea_port_approaches']} 个海运接岸标记。可独立停靠人员并交割粮食的非城池节点为 {topo['independently_legal_noncity_nodes']} 个。逐方向核对每个内部整日位置，现有实体运队只在城池 ID 上取得停靠及交割权限。

V3.0.4-B 技术阻塞。独立接岸需要地图赋权的地点 ID、实体人员可达接口、独立仓储和归属处理。E2 暂无矿点、港口或仓库资产。海运装载在隔离样本实际发运 {sea['actual_dispatched_total']:,} 粮，其中货粮 {sea['cargo']:,}，口粮 {sea['rations']:,}。样本为纯海物理规则测试。

[连接审计](../data/physical-node-connectivity-audit.csv) · [受控海运装载](../checks/physical-controls.json)
""",
        'city-hub-storage':f"""# 城池中转仓储

中转批次的已入仓量通过真实官仓收据建立。保护标签在本地军粮、日常支出、既有运输承诺和战略储备之后取得空间。当地储备紧张时，标签依法降级并释放到普通库存。中转批次仍在路上时，使用在途额度检查接收能力。

受控链路单仓最高保护 {e1['peak_tagged_warehouse_grain']:,} 粮。每旬边界样本记录实际库存、剩余容量及中转标签，仓容沿用既有上限。标签当前为空或城市易主时不能再调用当地的运队装载旧粮。

[仓容与实仓抽样](../data/hub-capacity-utilization.csv) · [入仓与释放](../data/hub-stock-postings.csv)
""",
        'batch-consolidation':f"""# 多批集货与合并

首轮受控案例，两支陆运队在郁林先后实际入仓 {batch[0]['receipt']['grain']:,} 粮和 {batch[1]['receipt']['grain']:,} 粮。河运批次 {batch[2]['convoy']} 引用前两张凭证，合计装载 {batch[2]['grain']+batch[2]['rations']:,} 粮。额外隔离案例只有第一支运队入仓时，界面账记录 {sample['partial']['visible_stock']:,} 粮，扣押运口粮后可发 {sample['partial']['eligible_to_load']:,} 粮。

每段只从上一站已入仓且经过结算的可用份额扣除装货及口粮。完成加载后，前序凭证立即扣账。

[合批原始凭证](../data/batch-consolidation.csv) · [部分到货](../checks/control-edge-cases.json)
""",
        'batch-splitting':f"""# 水运后分批陆运

郁林到苍梧真实河运入仓 {batch[2]['receipt']['grain']:,} 粮。苍梧按同一仓库收据分两批陆运，最终分别在南海入账 {batch[3]['receipt']['grain']:,} 与 {batch[4]['receipt']['grain']:,} 粮。两段都核查真实陆路装载容量，分别使用独立武将、周转和命令书。

[分批父凭证及结清账](../data/batch-splitting.csv)
""",
        'cargo-custody-ledger':f"""# 交割凭证和粮账

链路来源实扣 {grain['origin_cargo']+grain['origin_rations']:,} 粮。途中合法补充 {grain['external_ration_draw']:,} 粮。最终入南海 {grain['final_received']:,}，消耗口粮 {grain['travel_and_wait_rations']:,}，路线及天气途耗 {grain['route_loss']+grain['weather_loss']:,}，合法返库 {grain['returned_grain']:,}，账差 {grain['residual']}。

运队编号和收据为单次身份。运输作业量可把每段收据相加。净经济交付只统计最终目的城实际收粮。加载来自上一站收据时，以同一批次记出入账，最终汇总时抵销。严格存档校验核对父凭证时序、重复占用和容量。

[全链路粮账](../checks/end-to-end-grain-account.json) · [实际收据](../data/transshipment-receipt-ledger.csv)
""",
        'escort-and-origin-slots':"""# 人员和共用运输位置

所有中转队沿用实体运队的来源城槽位、当旬发运数量、行动冷却及命令书。原型仍受任职限制、留守武将数、防御兵力及健康约束。多批次行程共用了苍梧的同一来源位置，第二支队在第一支结束相应占用后才发运。到港量与回城、人员重新可用分别计时。

[来源城实际发运](../data/parent-origin-slot-usage.csv) · [周转](../data/officer-turnover-comparison.csv)
""",
        'intermodal-route-planning':f"""# 直运和分段运输

受控珠江线路使用 227-02 剧本真实道路及既有人员。在两边完全相同的开局中人为对齐来源城资金与官仓，用于隔离操作差异。E0 与 E1 同时启用物理容量，其他 V3.0.3 候选开关全关。混合路径使用沿途最小容量。真实入仓并另行装运后，才核算新段容量。

{paired}

本例直运更合适。候选中转的适用条件是稳定的纯水运段、足够的前后段吞吐、合资格人员，以及能覆盖所有真实腿程和周转的期限。长江、黄河及接海样本当前提供拓扑与容量核对，经济比较以珠江实收为依据。

{short_text}
""",
        'deadline-and-cancellation':"""# 截止旬及取消

缺粮计划保留建立时的最早缺粮旬和承诺期限。每次实际发运重新核对库存、计划缺口、天气和完整末段到达估计。跨城交割有至少一个结算边界。储备案使用储备期限。已被既有在途调粮覆盖的缺口不接受重复派船。

取消、需求已覆盖、超过期限、归属改变和批次用尽都释放可用保护标签。取消保留实际官仓余额及已出发实体运队，后续交付仍沿用正常的路线及易主结算。

[真实发运与入账旬](../data/transshipment-deadline-comparison.csv) · [取消证据](../data/transshipment-cancellation.csv)
""",
        'capacity-unload-and-reroute':f"""# 真实城池减载和重选路线

隔离场景将已发运河运队保持在实际所在的郁林等待。切换陆路时，过载 {sample['unload']['grain']:,} 粮全部实际入郁林官仓，改道初始总载重 {sample['unload']['after_physical_load']:,}。对未占据的合浦发出同指令被拒，保存态一致。

合法改道保持人员同行、原行程工作量和路线载荷校核。历史武都滞留运队位于敌城且货粮已耗空，因此不符合该减载机制的前提。

[卸货和改道凭据](../data/capacity-unload-and-reroute.csv)
""",
        'performance-results':f"""# 原型运行成本

两条受控轨迹的路线报价调用分别为 {e0['stage_quotes']}、{e1['stage_quotes']} 次，进程 CPU 时间分别为 {e0['cpu_seconds']:.3f}、{e1['cpu_seconds']:.3f} 秒。同一运行进程的 RSS 高水位按测量结束点采集。数值只反映单个短期受控样本，包含必要的多段报价和结算；E3 的回合 CPU、内存及长期吞吐待后续测量。

候选计划、阶段批次、保存历史都有固定上界。引擎按指令、回合边界核对标签及结算，关闭原型的领域状态通过同种子校验。

[控制性能数据](../data/performance-comparison.csv)
""",
        'save-compatibility':"""# 存档与兼容

V3.0.4 使用独立实验版本字段。普通及紧凑存档均记录计划、仓库标签、已发运批次、原始归属和收据。

在初批集货完成、河运尚待发运时进行了普通及紧凑往返校验。繁中桌面和日文触控另在真实 Worker 发出河运后下载及读档，计划状态逐字段一致。原粮仓 302、3021 和运输容量 303 使用各自既有版本。关闭中转时，新旧源码在两组各九旬的固定赤壁回放中使用相同状态及随机序列。

旧官渡个人存档存在既往剧本摘要差异的记录。此轮保留原有摘要校验。

[同态验证](../checks/disabled-source-parity-rerun.json) · [浏览器存续证据](../checks/browser-transshipment-retry.json)
""",
        'validation-results':f"""# 技术回归

{gate_lines}

现有测试用真实剧本与受控边界样例覆盖多来源集货、原地减载、仓容耗尽、未到货、来源和中转易主、冻结、合法撤回和毁损检查。技术凭证列出已实际执行的命令、运行源码、日志哈希和结果。浏览器首次专项验证在返回按钮选择器失败，修正操作路径后重跑。

[技术门槛](../checks/technical-gates.json) · [受控边界](../checks/control-edge-cases.json)
""",
        'known-issues':"""# 已识别限制

- 接岸标记还没有可授权运队停靠和交割粮食的独立游戏位置。
- 珠江三段样本增加了中间作业量、命令书和等待，最终到粮与单位人员效率低于直接运输。
- 苍梧两段样本有少量额外净到粮，代价是更慢的达成和额外命令书。
- 纯海大容量是实际发运的受控规则样本。真实海陆接入及冬季相对运输收益待验证。
- 历史武都滞留案例未解决。两支运队无可卸货粮，且位于不具备接收权限的城市。
""",
        'v304-formal-readiness':f"""# 正式经济阶段准入

V3.0.4-A 的开发状态是 {status['city_transshipment'] }。V3.0.4-B 缺少具备独立人员和仓储账的合法接岸点。E3 依赖 E2 通过，当前阶段停留在确定性机理验证。

1. 独立非城泊点 0 处，77 处只是水路接入标记。
2. 珠江有完成实际收据的纯河运，成功合并两批并分两次陆运。
3. 有权仓库减载后安全改道成立，异地卸货被引擎拒绝。
4. 分段路线保留真实工作量。南海三段链路比同一初态直运更慢、单位成本更高，最终实收率较低。
5. 本例现有人员、槽位及实际命令书足够跑完五个订单，吞吐受实际结算限制。
6. 冻结阻断已确认。冬季运输收益、地图独立接驳和自然观战经济目标尚未确认。

{short_text}

当前未达到 V3.0.4 正式经济阶段的准入条件。
""",
        'data-dictionary':"""# 数据字典

- actual_received 是对应运输队在目标处的真实入库。final_destination 标记其是否计入计划最终经济实收。
- 多个中间批次可对同一笔粮形成多张作业收据。transport_handling 加总全部运输作业，final_grain 仅加总真正终点。
- actual_stock 才是实际官仓，tagged_stock 是其中已标记用途的份额。tagged_utilization 除以原物理仓容。
- original_deadline 与 promise 使用回合数。日序采用凭证落账旬开始时的战役日。额度空值表示本实验没有适用记录。
- 额度选择的世界仅用于受控试验。physical-controls 的纯海样本保留地图配置模板及实际装载口粮，不能用作自然观战海运实收。
- 路线报告的 work 是引擎固定点工作量，1 天等于 DAY_TICKS。接岸审计的计数按剧本及允许方向累加。
- process_peak_rss 是进程高水位。短样本 CPU 行不作为正式回合性能门槛。
"""
    }
    for name,body in docs.items():
        target=summary/'docs'/f'{name}.md'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(body,encoding='utf-8')


def build(args):
    built,summary=args.build,args.summary
    data,checks,sources=(summary/name for name in ('data','checks','sources'))
    for folder in (data,checks,sources):
        folder.mkdir(parents=True,exist_ok=True)
    for folder in ('controlled-samples','observed-metrics','topology'):
        for path in sorted((built/folder).iterdir()):
            if path.suffix in {'.csv','.json'}:
                copy_portable(path,(checks if path.suffix=='.json' else data)/path.name)
    for name in ('playwright-final.config.mjs','playwright-retry.config.mjs'):
        copy_portable(built.parent/name,sources/name)
    scenes=read(checks/'controlled-route-results.json')
    short=read(checks/'short-chain-comparison.json')
    comparison=metrics(scenes,short,data,checks)
    gates=technical(built,checks)
    mandatory=all(row['status']=='passed' for row in gates.values())
    pipeline=dict(sequence=('E0','E1','E2','E3'),transport_flags=scenes[0]['candidate_303'],
        initial_state_sha256=scenes[0]['opening_sha256'],map_sha256=read(checks/'topology-audit.json')['map_sha256'],
        catalog_sha256=scenes[0]['catalog_sha256'],games=[
            dict(group=row['group'],case=row['case'],source=row['source'],scenario='227-02',seed=row['seed'],kind='controlled',
                 natural_run=False, opening_sha256=row['opening_sha256'],
                 transshipment_rules_version=304 if row['group']=='E1' else 0) for row in (*scenes,*short)],
        blocked=[dict(group='E2',reason='no_actor_or_stock_custody_at_noncity_nodes'),
                 dict(group='E3',reason='prior_technical_gate_E2_unmet')])
    readiness=dict(city_transshipment='本地技术验证通过' if mandatory else '部分回归待确认',
        real_city_control_completed=True,independent_terminal='blocked',ai_observation='not_started',
        formal_economy_ready=False,disabled_by_default=True,
        unfavorable_pilot_metrics=[dict(case=row['case'],metric=row['metric'])
                                   for row in comparison if row['pilot_target_missed']],
        technical_gates_passed=mandatory)
    to_json(data/'simulation-manifest.json',pipeline)
    to_json(data/'report-status.json',readiness)
    names=('v304_gate_runner.py','v304_scenarios.py','v304_observations.py','v304_topology.py',
           'v304_report.py','v304_packaging.py','v304_recalculate.py')
    to_json(sources/'reproduction-sources.json',dict(
        runtime_git=(built/'frozen-source.txt').read_text().strip(),
        tested_scope_tree=git('rev-parse',scenes[0]['source']+'^{tree}').decode().strip(),
        flags=pipeline['transport_flags'],map_sha256=pipeline['map_sha256'],
        audited_catalogs=read(checks/'topology-audit.json')['catalogs'],
        tools={name:file_sha(TOOL_ROOT/'tools/economy-balance'/name) for name in names}))
    write_documents(summary,scenes,short,gates,readiness)
    print(json.dumps(readiness,ensure_ascii=False))


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('summary',type=Path)
    build(parser.parse_args())
