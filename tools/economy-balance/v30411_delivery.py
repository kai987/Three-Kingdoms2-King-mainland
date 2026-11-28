"""Package reviewed replay evidence and checks into an independent Git archive."""
import argparse
from collections import Counter, defaultdict
import gzip
from hashlib import sha256
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
from zipfile import ZIP_DEFLATED, ZipFile

from common import ROOT, to_json
from remake.campaign import verified_save_content
from v30411_report import package, rows, write


def content_hash(path):
    with path.open('rb') as stream:
        return sha256(stream.read()).hexdigest()


def git_sha(ref):
    return subprocess.check_output(['git','-C',str(ROOT),'rev-parse',ref],text=True).strip()


def markdown(path, text):
    path.write_text(text.strip()+'\n',encoding='utf-8')


def record_technical_checks(output, logs):
    def raw(name):
        path = logs/name
        return path.read_text(encoding='utf-8',errors='replace') if path.exists() else ''

    checks = {}
    for backend in ('python','rust'):
        name = f'{backend}-full-first.log'
        log = raw(name)
        ran = re.search(r'^Ran (\d+) tests in ([\d.]+)s$', log, re.M)
        passed = re.search(r'^OK(?: \(.*?\))?$', log, re.M)
        checks[f'{backend}_campaign'] = dict(log=name, status=(
            'passed' if passed else 'failed' if ran else 'incomplete'),
            tests=int(ran[1]) if ran else None, seconds=float(ran[2]) if ran else None)
    quick = [('node','node-tests.log',r'^(?:#|ℹ) pass (\d+)',r'^(?:#|ℹ) fail [1-9]'),
             ('rust_crate','rust-crate.log',r'^test result: ok\. (\d+) passed',r'^test result: FAILED')]
    for key,name,success,failure in quick:
        log = raw(name)
        counts = re.findall(success,log,re.M)
        checks[key] = dict(log=name, status=('failed' if re.search(failure,log,re.M)
                                           else 'passed' if counts else 'incomplete'),
                           tests=sum(map(int,counts)) if counts else None)
    pyodide = raw('pyodide-wasm-local.log')
    result = next((json.loads(line) for line in pyodide.splitlines() if line.startswith('{')), None)
    checks['pyodide'] = dict(log='pyodide-wasm-local.log',status=(
        'passed' if result and result.get('ok') else 'incomplete'),result=result)
    for key,name in [('wasm_build','wasm-build-check.log'),('rust_format','rust-format.log'),
                     ('native_wasm_parity','native-wasm-parity.log'),('browser_full','browser-first-full.log'),
                     ('browser_resupply','browser-resupply.log'),('browser_supply_v211','browser-resupply-v211.log')]:
        log = raw(name)
        # The launch commands preserve independent shell exit receipts where available.
        receipt = logs/(name.removesuffix('.log')+'.exit')
        result = int(receipt.read_text()) if receipt.exists() else None
        if key.startswith('browser'):
            totals = {p:int(n) for n,p in re.findall(r'^\s+(\d+) (passed|failed|skipped)\b',log,re.M)}
            counts = dict(passed=totals.get('passed',0),failed=totals.get('failed',0),skipped=totals.get('skipped',0))
            status = 'failed' if counts['failed'] or result else 'passed' if counts['passed'] else 'incomplete'
        else:
            counts = {}
            status = 'passed' if result==0 else 'failed' if result else 'incomplete'
        checks[key] = dict(log=name,status=status,result=result,**counts)
    retry = logs/'browser-retry-results.json'
    if retry.exists():
        checks['browser_isolated_retries'] = json.loads(retry.read_bytes())
    to_json(output/'technical-checks.json', checks)
    return checks


def write_control_equivalence(data, runs, audits):
    controls = {'U0':'T0','U1':'T3','V0':'T4','V1':'T5'}
    reference = {(row['fixture'],row['group']):row['checks'] for row in
                 json.loads((runs/'baseline-fixed/fixed-capacity-replay-traces.json').read_bytes())}
    comparisons = []
    for row in audits:
        if row['group'] not in controls:
            continue
        previous = reference[row['fixture'],controls[row['group']]]
        matches = [{'turn':old['turn'],'domain':old['sha256']==new['sha256'],'rng':old['rng']==new['rng']}
                   for old,new in zip(previous,row['checks']) if old['turn']==new['turn']]
        comparisons.append(dict(group=row['group'],fixture=row['fixture'],turns=len(matches),
            all_domain_equal=len(matches)==len(previous) and all(r['domain'] for r in matches),
            all_rng_equal=len(matches)==len(previous) and all(r['rng'] for r in matches),checks=matches))
    write(data/'old-rule-equivalence.csv', comparisons)
    return comparisons


def render_stage(output, prior, runs):
    checks, data, docs = output/'checks', output/'data', output/'docs'
    stage = json.loads((checks/'fixed-stage-status.json').read_bytes())
    audit_path = runs/'audit-final/resource-safety.json'
    audits = json.loads(audit_path.read_bytes()) if audit_path.exists() else []
    safety_rows = [row for row in audits if row['group'] in ('U6','V2')]
    audit_totals = Counter()
    for row in safety_rows:
        audit_totals.update(row['safety'])
        audit_totals['city_resource_mismatches'] += row['grain_account']['city_resource_mismatches']
        audit_totals['market_errors'] += row['market'].get('transaction_errors',0)+row['market'].get('account_errors',0)
        audit_totals['city_postings'] += row['grain_account']['city_postings']
        audit_totals['market_transactions'] += row['market'].get('transactions',0)
    safety_pass = len(safety_rows)==10 and all(value==0 for key,value in audit_totals.items()
                                      if key not in ('city_postings','market_transactions'))
    equivalents = write_control_equivalence(data,runs,audits)
    legacy_pass = len(equivalents)==20 and all(row['all_domain_equal'] and row['all_rng_equal']
                                               for row in equivalents)
    south = {(row['group'],row['city']):int(row['missing']) for row in rows(data/'southern-checkpoint-results.csv')}
    cities = sorted(city for group,city in south if group=='U0')
    south_totals = {group:sum(south[group,city] for city in cities) for group in {group for group,_ in south}}
    south_gate = {group: total<=15422 and south[group,'luling']<=807 and south[group,'yidu']<=753
                  and south[group,'baxi']<3779 for group,total in south_totals.items() if group in ('U6','V2')}
    stage.update(safety={'passed':safety_pass,'checked_replays':len(safety_rows),'totals':dict(audit_totals)},
                 old_rules_replay={'passed':legacy_pass,'checked_replays':len(equivalents)},
                 south_totals=south_totals,south_gate=south_gate)
    equivalence_file = data/'incremental-plan-equivalence.csv'
    if equivalence_file.exists():
        write(data/'scheduler-cache-validity.csv', (
            {key:r[key] for key in ('fixture','sha256','compared_turns','domains_equal','decisions_equal',
                                   'decision_events')}
            for r in rows(equivalence_file)))
    consumption_file = data/'fixed-first-deadline-consumption.csv'
    if consumption_file.exists():
        by_group = defaultdict(Counter)
        recovered = []
        consumption = rows(consumption_file)
        for r in consumption:
            group = r['group']
            if r['due_meal_observed'] != 'true':
                by_group[group]['not_observed'] += 1
                continue
            by_group[group].update(observed=1,had_shortage=int(int(r['actual_missing'])>0),
                                   missing_grain=int(r['actual_missing']))
            if int(r['physical_receipts'])==0 and int(r['local_grain_consumed_minimum'])>0:
                by_group[group]['local_only_proven_consumed'] += 1
                if not int(r['actual_missing']):
                    by_group[group]['local_only_proven_consumed_and_first_meal_paid'] += 1
                    recovered.append(r)
        stage['fixed_actual_first_meals'] = {group:dict(counts) for group,counts in by_group.items()}
        write(data/'fixed-local-market-consumed-and-meal-paid.csv',recovered,
              headers=('group','checkpoint','owner','city','deadline','actual_missing',
                       'physical_receipts','local_grain_bought','local_grain_consumed_minimum'))
        by_target = {(r['group'],r['checkpoint'],r['owner'],r['city']):r for r in consumption}
        paired = []
        for control,candidate in (('U0','U6'),('U1','U6'),('V0','V2'),('V1','V2')):
            for before in consumption:
                if before['group']!=control:
                    continue
                after = by_target[candidate,before['checkpoint'],before['owner'],before['city']]
                seen = before['due_meal_observed']==after['due_meal_observed']=='true'
                paired.append(dict(control=control,candidate=candidate,checkpoint=before['checkpoint'],
                    owner=before['owner'],city=before['city'],deadline=before['deadline'],both_observed=seen,
                    control_missing=before['actual_missing'],candidate_missing=after['actual_missing'],
                    change=int(after['actual_missing'])-int(before['actual_missing']) if seen else None))
        write(data/'fixed-first-meal-paired-effect.csv',paired)
        measures = defaultdict(Counter)
        for r in paired:
            if r['both_observed']:
                old,new = int(r['control_missing']),int(r['candidate_missing'])
                measures[r['control']].update(observed=1,before=old,after=new,improved=int(new<old),
                                               worse=int(new>old),new_shortage=int(new>0==old))
        stage['fixed_actual_paired_meals'] = {group:dict(counts) for group,counts in measures.items()}
    else:
        measures = {}
    paid_local = stage.get('fixed_actual_first_meals', {})
    proven_local = '、'.join(
        f"{group} {paid_local.get(group,{}).get('local_only_proven_consumed_and_first_meal_paid',0)} 个"
        for group in ('U6','V2')) if paid_local else '未完成统计'
    perf_path = data/'scheduler-performance-profile.csv'
    perf = {}
    if perf_path.exists():
        perf_rows = rows(perf_path)
        measurements = {(r['label'],r['group']):r for r in perf_rows if r['observation']=='false'}
        for name, group in sorted(measurements):
            if group=='U6' and (name,'U0') in measurements:
                original = float(measurements[name,'U0']['full_turn_cpu_p95'])
                current = float(measurements[name,'U6']['full_turn_cpu_p95'])
                full = measurements.get((name,'U6-full'),{})
                perf[name] = dict(control=original,candidate=current,full=full.get('full_turn_cpu_p95'),
                                  relative=current/original-1,within_30_percent=current<=original*1.3)
    stage['performance'] = perf
    stage['admitted_fixed'] = all(r['covers'] for r in stage['candidates'].values()) and len(south_gate)==2 and all(south_gate.values())
    stage['admitted_safety'] = safety_pass and legacy_pass and len(perf)==5 and all(
        row['within_30_percent'] for row in perf.values())
    stage['observation'] = {'quick_24m':'not_run','five_year':'not_run','twenty_year':'not_run','holdout':'not_run'}
    stage['default_enabled'] = False
    to_json(checks/'stage-status.json',stage)

    def table(groups):
        return '\n'.join(f"| {row['group']} | {row['timely_targets']} | {row['full_targets']} | "
                          f"{row['first_gap_grain']:,} | {row['actual_grain']:,} | {row['returning_delivered']} |"
                          for row in groups)

    header = '| 组 | 及时到货 | 首次足额 | 首次折顶覆盖 | 期限前实收 | 返程样本再到货 |\n|---|---:|---:|---:|---:|---:|'
    paired_table = '\n'.join(f"| {group} | {counts['observed']} | {counts['before']:,} | "
        f"{counts['after']:,} | {counts['worse']} | {counts['new_shortage']} |" for group,counts in measures.items())
    markdown(docs/'fixed-state-acceptance.md',f"""
# 89 个固定目标及 23 个返程来源

{header}
{table(stage['integrated'])}

目标为 U6 的 32／30／20,833／14 以及 V2 的 42／37／24,659／15，依次为及时到货、首次足额、折顶覆盖、返程样本再到货。准入结果见 [阶段检查](../checks/stage-status.json)。

原历史 T3 相对 T0 丢失 21 个原有及时目标。T5 相对 T4 丢失 24 个。共 {stage['actual_historical_losses']} 条逐目标原始发运、到货和新规划证据保存在 [逐目标归因](../data/fixed-demand-regression-attribution.csv)。历史同档旧引擎复跑与原表逐项一致 {stage['prior_identical']}/{stage['exact_prior_pairs']}。不同的集成版值单列。

原表的 T0 35／33／23,147，T3 19／15／9,783，T4 46／41／27,398，T5 26／22／13,648。返程覆盖历史 T0 为 16，T3 为 4，T4 为 17，T5 为 9。重放的来源名册、报价和实际再到货见 [23 个返程样本](../data/returning-slot-coverage-recovery.csv)。

## 首次到期的实际消费

| 对照 → 候选 | 可配对目标 | 对照缺口 | 候选缺口 | 恶化目标 | 新出现缺口 |
|---|---:|---:|---:|---:|---:|
{paired_table}

每组只比较同城、同势力和同一次实际扣粮都有记录的目标。U0／U1 分别比 U6，V0／V1 分别比 V2。没有实体到货而经核实用采购粮参与消费、首期足额的目标为 {proven_local}。两种覆盖口径分别保存在 [配对消费缺口](../data/fixed-first-meal-paired-effect.csv) 和 [购粮实际消耗证据](../data/fixed-local-market-consumed-and-meal-paid.csv)。
""")
    counts = Counter()
    for row in rows(data/'alternative-source-comparison.csv'):
        if row['gained']=='true':
            counts[row['control'],row['candidate'],'gains'] += 1
        if row['lost']=='true':
            counts[row['control'],row['candidate'],'losses'] += 1
    pairs = sorted({(a,b) for a,b,_ in counts})
    lines = '\n'.join(f'| {left} | {right} | {counts[left,right,"gains"]} | {counts[left,right,"losses"]} |'
                      for left,right in pairs)
    markdown(docs/'ablation-results.md',f"""
# 独立消融

| 基准 | 候选 | 新增及时到货目标 | 丢失及时到货目标 |
|---|---|---:|---:|
{lines}

分页 U1→U2，多样性 U2→U3a，重新报价 U2→U3b，组合 U2→U3，来源安全 U3→U4，准备 U4→U5p，过境 U4→U5t。零增零减的组合直接查看 [逐目标配对表](../data/alternative-source-comparison.csv)。V1→V2 只在 D2 内比较。不同时间点的报价数量分别留存。
""")
    ordered_groups = ['U0','U1','U4','U5t','U6','V2']
    city_lines = '\n'.join('| '+city+' | '+' | '.join(str(south[group,city]) for group in ordered_groups)+' |' for city in cities)
    total_line = '| 合计 | '+' | '.join(str(south_totals[group]) for group in ordered_groups)+' |'
    markdown(docs/'baxi-replay.md',f"""
# 八处南方城池的九旬实际缺口

| 城市 | U0 | U1 | U4 | U5t（只加过境） | U6 | V2 |
|---|---:|---:|---:|---:|---:|---:|
{city_lines}
{total_line}

巴西通过 [真实官仓过账](../data/baxi-grain-flow-replay.csv) 对照采购、过境领取及后续消费，旧版的 805／3,779 另保留在原验收表。差额包含实际战役变化。
""")
    perf_table = '\n'.join(f"| {name} | {r['control']:.3f} | {float(r['full']):.3f} | {r['candidate']:.3f} | {r['relative']:.1%} |"
                           for name,r in sorted(perf.items()) if r['full'] is not None)
    markdown(docs/'performance-results.md',f"""
# 固定状态 CPU 与等价

| 检查点 | U0 P95 秒 | U6 完整重算 P95 秒 | U6 增量 P95 秒 | 候选相对 U0 |
|---|---:|---:|---:|---:|
{perf_table}

同一台 {platform.machine()} 机器，Rust 后端，各组重复三次，每次三旬。主表为关闭观察后的结果。CSV 保留观测状态、P50、P95、内存和路线查询。100 个动态库存状态由确定性控制测试比对，实际游戏决策、存档与 RNG 配对结果见 [等价表](../data/incremental-plan-equivalence.csv)。
""")
    markdown(docs/'long-term-balance-results.md',"""
# 长期经济观察

本轮阶段准入结果记录在 stage-status.json。24 个月、五年、二十年结果标为未执行。历史二十年保留黄巾 212,965→711,689、赤壁 211 D0 645,229→611,748、赤壁 212 D0 320,025→325,442、赤壁 211 D2 411,738→593,652 的实际缺粮记录。这些数字属于 V3.0.4.1。

短窗口实际回执不用于推断小势力存续、军粮及时率或长期每本命令书的净收益。
""")
    markdown(docs/'holdout-results.md',"""
# 独立保留种子

2047 黄巾 211 与 2048 赤壁 212 两个 60 月案例未执行。2045、2046 属于上一版验收。所有已执行案例的原种子见输入与运行清单。
""")
    markdown(docs/'known-issues.md',"""
# 已知问题

固定到货使用原始首次期限。同一轮按实时库存重建后续目标，因此新候选可能改善实际消费而减少早到的额外库存。现阶段候选以档案中的实际覆盖结果和警戒线为准。没有原始检查点的历史运队只引用历史观察。

已触发的搜索预算、预计到货和实收独立计数。已开启的 30411 仍属实验，正常开始继续采用原配置。
""")
    markdown(docs/'v3042-readiness.md',f"""
# 后续准入

固定需求准入为 **{'通过' if stage['admitted_fixed'] else '未通过'}**。资源与性能合并准入为 **{'通过' if stage['admitted_safety'] else '未通过'}**。后续交通节点所需证据来自真实路线过长、合法来源不足或返程粮与占位事件，当前游戏保持现有交通设施及默认运输规则。
""")
    return stage


def acceptance_answers(output, stage, shipments):
    data, docs = output/'data', output/'docs'
    outcomes = {r['group']:r for r in stage['integrated']}
    regressions = rows(data/'fixed-demand-regression-attribution.csv')
    all_pairs = rows(data/'alternative-source-comparison.csv')

    def ablation(left,right):
        matched = [r for r in all_pairs if (r['control'],r['candidate'])==(left,right)]
        gained = sum(r['gained']=='true' for r in matched)
        lost = sum(r['lost']=='true' for r in matched)
        return gained,lost

    def history(which):
        targets = [r for r in regressions if r['comparison']==which]
        counts = Counter(cause for r in targets for cause in json.loads(r['indicators']))
        return (f"{len(targets)} 个。{counts['some_passes_not_evaluated']} 个曾落在旧首屏之外，"
                f"{counts['eligible_deadline_quote_not_launched']} 个有期内报价但未发运，"
                f"{counts['shipment_without_on_time_receipt']} 个发运后未按期到货，"
                f"{counts['revalidation_failed']} 个有提交失败，"
                f"{counts['market_purchase_observed_consumer_attribution_separate']} 个有实际本地采购。"
                "同一目标可能同时具备多项证据。")

    safety = stage['safety']
    south = {(r['group'],r['city']):int(r['missing']) for r in rows(data/'southern-checkpoint-results.csv')}
    flow = defaultdict(Counter)
    for row in rows(data/'baxi-grain-flow-replay.csv'):
        if row['resource']=='grain' and row['delta']!='null':
            flow[row['group']][row['site']] += int(row['delta'])
    flows = '，'.join(f"{g} 购入 {flow[g]['facilities._settle_grain_trade']:,}、行军净领取 "
                     f"{-flow[g]['march_supply.advance_unit']:,}" for g in ('U0','U1','U5t','U6','V2'))
    reversals = data/'repeated-grain-transfer-audit.csv'
    reverse_count = len(rows(reversals)) if reversals.exists() else 0
    p3 = Counter(row['group'] for row in rows(data/'p3-resource-occupation.csv')
                 if row['event']=='dispatch' and row['convoy']!='null')
    small = Counter(row['group'] for row in rows(data/'small-load-by-priority.csv'))
    funded = defaultdict(Counter)
    economy = data/'effective-demand-per-command-book.csv'
    if economy.exists():
        for row in rows(economy):
            funded[row['group']].update({k:int(row[k]) for k in (
                'market_books','transport_books','direct_resupply_books','fixed_first_gap_covered')})
    results = []
    for group in ('U0','U1','U6','V0','V1','V2'):
        rec = funded[group]
        books = rec['market_books']+rec['transport_books']+rec['direct_resupply_books']
        if books:
            results.append(f"{group} {rec['fixed_first_gap_covered']/books:.2f}")
    guard = '、'.join(f"{name} {entry['relative']:+.1%}" for name,entry in stage['performance'].items())
    confirmations = rows(data/'incremental-plan-equivalence.csv') if (data/'incremental-plan-equivalence.csv').exists() else []
    options = {(r['convoy'],r['group']):r for r in shipments}
    retention = '、'.join(f"{convoy} 号 {options[convoy,'U6']['hunger_losses']} 饥损，"
                           f"{options[convoy,'U6']['troops_received']} 人归还"
                           for convoy in (2,3634) if (convoy,'U6') in options)
    gain, loss = ablation('U1','U2')
    quote_gain, quote_loss = ablation('U2','U3')
    answers = [
        f"原 T3 丢失目标。{history('T0-T3')}",
        f"原 T5 丢失目标。{history('T4-T5')}",
        f"分页 U1→U2 恢复 {gain} 个，丢失 {loss} 个。",
        f"多样性和重报价 U2→U3 恢复 {quote_gain} 个、丢失 {quote_loss} 个及时到货目标。"
        f"重报价单独将有再到货的来源由 {outcomes['U2']['returning_delivered']} 增至 {outcomes['U3b']['returning_delivered']}。",
        "来源承诺在固定开局按唯一类别入账。所观察的分解与承诺总额一致。"
        "未确认存在同一硬性承诺被扣除两次。后方安全留量偏紧与已证实的双扣有不同证据。",
        f"原库存、押运、返程报价和额度由真实服务验证。{safety['checked_replays']} 个固定候选回放"
        f"的资源账硬性检查{'通过' if safety['passed'] else '未通过或未完成'}。",
        f"首次缺口覆盖仍差门槛。U6 {outcomes['U6']['timely_targets']}／{outcomes['U6']['full_targets']}／"
        f"{outcomes['U6']['first_gap_grain']:,}，V2 {outcomes['V2']['timely_targets']}／"
        f"{outcomes['V2']['full_targets']}／{outcomes['V2']['first_gap_grain']:,}。",
        f"23 个返程占位样本中 U6 {outcomes['U6']['returning_delivered']} 个后来实际到货，"
        f"V2 {outcomes['V2']['returning_delivered']} 个。D0 未到 14，D2 达到 15。",
        f"固定目标回放的 P3 发运记录 U1 {p3['U1']} 笔，U5p {p3['U5p']} 笔，U6 {p3['U6']} 笔。"
        "拆分准备减少了普通前线储量与紧急补给争用。长期占用未验证。",
        f"观察到 {reverse_count} 段三旬内反向发运配对。两次发运的货量、用途和时间可核查，仍须逐笔判断是否属于无效往返。",
        "实发记录按城市缺口、军粮和储量分开。战略粮仓渠道只说明实际运输服务。"
        "短回放无法推断长期渠道集中是否来自储粮。",
        f"巴西九旬官仓流水中的实际购粮和军粮支出为 {flows}。"
        "确认的行军预留和城内扣粮可在时间线逐笔核对。",
        f"候选实测发现 {safety['totals'].get('city_resource_mismatches','未完成')} 个官仓过账不符。"
        "未证实重复扣实物粮。已锁定补给与实际领取分别列示。",
        f"巴西九旬缺口 U0 {south['U0','baxi']:,}、U1 {south['U1','baxi']:,}、"
        f"只加过境 U5t {south['U5t','baxi']:,}、U6 {south['U6','baxi']:,}、V2 {south['V2','baxi']:,}。",
        f"庐陵 U6/V2 为 {south['U6','luling']:,}/{south['V2','luling']:,}。"
        f"宜都为 {south['U6','yidu']:,}/{south['V2','yidu']:,}。历史参考是庐陵 807，宜都 753 或 334。",
        f"固定目标中的小额长途发运 U5 {small['U5']} 笔、U6 {small['U6']} 笔。"
        "该口径为实发小于 1,000 粮且去程至少二十日。长期比例未执行。",
        "紧急小额救援专项通过。实际发运仍受真实合法来源、额度、人员和往返粮约束。",
        "固定首次实体覆盖粮除以全部已记录粮食保障命令书，可作短窗对照。"
        f"{'、'.join(results)}。完整消费归属的长期效率尚未测量。",
        "完整军粮首次期限及时率和实际未满足量未测量。实发和实收保留在固定窗口流水中。",
        "黄巾二十年观战未执行。",
        "赤壁 D0、D2 二十年观战未执行。",
        f"历史救援没有完整保留。{retention}。以实收回执和期末在途状态为准。",
        f"增量与完整重算在 {sum(r['domains_equal']=='true' and r['decisions_equal']=='true' for r in confirmations)}"
        " 个固定检查点的三旬数据中决策、领域状态和 RNG 相同。",
        f"同机 P95 相对 U0 的变化为 {guard}。完整 P50、P95 与内存见性能表。",
        "两个新独立保留种子未执行。",
        "固定需求与历史返程仍有阻塞。八城虽达到缺口目标，运输调度仍保留为实验版本。",
        "V3.0.4.2 尚未准入。已保留真实交通、来源和返程案例供后续重放。"
    ]
    markdown(docs/'acceptance-answers.md', '\n'.join(['# 验收问题逐项答复','',
        *(f'{i}. {answer}' for i,answer in enumerate(answers,1)),
        '', '[固定需求和逐目标证据](fixed-state-acceptance.md) · '
        '[南方八城与巴西](baxi-replay.md) · [历史运队](historical-transport-review.md) · '
        '[性能](performance-results.md) · [运行状态](../checks/stage-status.json)']))


def zip_group(target, paths):
    with ZipFile(target,'w',compression=ZIP_DEFLATED,compresslevel=5) as archive:
        for arcname,path in paths:
            archive.write(path,arcname)
    with ZipFile(target) as archive:
        assert archive.testzip() is None
    if target.stat().st_size>=100_000_000:
        raise ValueError(f'Resplit {target.name} by experiment')
    return dict(name=target.name,bytes=target.stat().st_size,sha256=content_hash(target),
                files=[dict(path=arc,sha256=content_hash(path)) for arc,path in paths])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs',type=Path)
    parser.add_argument('prior',type=Path)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    out = args.destination/'summary'
    args.output = out
    package(args)
    docs, checks, sources, data = (out/folder for folder in ('docs','checks','sources','data'))
    for folder in (docs,checks,sources,data):
        folder.mkdir(parents=True,exist_ok=True)
    for path in (ROOT/'docs/transport-coordination-v30411').glob('*.md'):
        shutil.copy2(path,docs/path.name)
    for path in (ROOT/'tools/economy-balance').glob('v30411_*.py'):
        shutil.copy2(path,sources/path.name)
    for path in (args.runs/'audit-final').glob('*'):
        if path.is_file():
            shutil.copy2(path,(checks if path.suffix=='.json' else data)/path.name)
    for name in ('fixed-replay-inputs.json','fixed-capacity-replay-traces.json'):
        shutil.copy2(args.runs/'fixed-ablation'/name,checks/name)
    for name in ('historical-transport-replay-index.csv','checkpoint-sources.json'):
        shutil.copy2(args.prior/'summary/sources'/name,sources/name)
    manifest = json.loads((args.runs/'inputs/input-manifest.json').read_bytes())
    for row in manifest:
        if row['restored'] and row['group']!='reference':
            with gzip.open(args.runs/'inputs'/row['file'],'rt',encoding='utf-8') as stream:
                original = json.load(stream)
            frame = verified_save_content(original.get('save',original))
            state = frame['state']
            row.update(seed=state['seed'], snapshot_turn=state['turn'], catalog_scenario=frame['scenario'],
                       saved_rules={name:value for name,value in state['extension'].items()
                                    if name.endswith('_rules_version') and type(value) is int})
        if 'container' in row:
            parts = Path(row['container']).parts
            root = parts.index('worktrees')+1 if 'worktrees' in parts else len(parts)-1
            row['container'] = '/'.join(parts[root:])
    to_json(checks/'replay-inputs.json',manifest)
    shipments = []
    historical_paths = (path for folder in ('historical','historical-rescue-ablation')
                        for path in sorted((args.runs/folder).glob('*/historical-convoy-safety.json')))
    for path in historical_paths:
        cohort = path.parent.parent.name
        shutil.copy2(path,checks/f'{cohort}-convoy-{path.parent.name}.json')
        for row in json.loads(path.read_bytes())['results']:
            terminal = next((item['row'] for item in row['receipts'] if item['event']=='terminal'),{})
            returned = next((item['row']['cargo'] for item in row['receipts'] if item['event']=='returned_assets'),{})
            last = row['snapshots'][-1]['convoy']
            owner = row['snapshots'][0]['convoy']['source_owner']
            changed = next((snap['turn'] for snap in row['snapshots']
                            if snap['convoy'] and snap['convoy']['source_owner']!=owner),None)
            shipments.append(dict(convoy=row['convoy'],group=row['group'],first_turn=row['snapshots'][0]['turn'],
                final_turn=row['snapshots'][-1]['turn'],active=last is not None,
                hunger_losses=terminal.get('hunger_losses',(last or {}).get('hunger')),
                troops_received=terminal.get('troops_received',0) if terminal else 0,
                source_changed_in_observation=changed,returned_assets=returned,last_snapshot=last,terminal=terminal,
                seed=row['seed'],strategy=row['strategy'],weather=row['winter'],sha256=row['checkpoint_sha256']))
    write(data/'historical-convoy-regression.csv',shipments)
    replayed = {r['convoy'] for r in shipments}
    write(data/'historical-evidence-coverage.csv',(dict(row,current_replay=int(row['convoy']) in replayed)
          for row in rows(sources/'historical-transport-replay-index.csv')))
    markdown(docs/'historical-transport-review.md', '\n'.join([
        '# 历史运队', '', '| 运输队 | 分组 | 末旬 | 期末在途 | 观察饥损 | 实收兵员 |',
        '|---|---|---:|---|---:|---:|',
        *(f"| {r['convoy']} | {r['group']} | {r['final_turn']} | {str(r['active']).lower()} | "
          f"{r['hunger_losses']} | {r['troops_received']} |" for r in sorted(shipments,key=lambda r:(r['convoy'],r['group']))),
        '', '219 与 1228 使用同一份原固定需求存档，从各自打开的真实节点再推八旬。'
        '其余原件按前一版同一回放窗口推进。没有找到原始存档的六例保留索引和先前验收来源。',
        '', '[原 14 支运队索引](../sources/historical-transport-replay-index.csv) · [实际末态与终止凭证](../data/historical-convoy-regression.csv)']))
    stage = render_stage(out,args.prior,args.runs)
    acceptance_answers(out,stage,shipments)
    record_technical_checks(checks,args.runs/'logs')
    metadata = dict(source_sha=git_sha('HEAD'), game_engine_sha=git_sha('f2f442ad'),
        integration_base=git_sha('3ec93fbd'),prior_engine=git_sha('d096f47a'),
        prior_technical=git_sha('e6d24513'),prior_archive=git_sha('d5bceee7'),
        original_archive_sums=(args.prior/'archives/SHA256SUMS.txt').read_text(encoding='utf-8').splitlines(),
        background='Fixed states use archived weather. Southern and performance runs use F4 (221 with 231 forecast).',
        march_core_backend='rust',performance_cpu=platform.processor(),performance_machine=platform.machine(),
        map_sha256=content_hash(ROOT/'game/assets/map-campaign.png'),
        scenario_sha256={path.stem:content_hash(path) for path in sorted((ROOT/'game/data/campaigns').glob('*.json'))},
        stage=stage['observation'],seeds=sorted({x['seed'] for x in manifest if x.get('seed') is not None}),
        python=platform.python_version(),os=platform.platform())
    to_json(checks/'experiment-manifest.json',metadata)
    summary_files = sorted(p for p in out.rglob('*') if p.is_file() and p.name not in ('SHA256SUMS.txt','file-index.json'))
    to_json(out/'file-index.json',[dict(path=p.relative_to(out).as_posix(),bytes=p.stat().st_size,
                                      sha256=content_hash(p)) for p in summary_files])
    summary_files.append(out/'file-index.json')
    (out/'SHA256SUMS.txt').write_text(''.join(
        f'{content_hash(p)}  {p.relative_to(out).as_posix()}\n' for p in summary_files),encoding='utf-8')
    summaries=[(p.relative_to(args.destination).as_posix(),p) for p in (*summary_files,out/'SHA256SUMS.txt')]
    technical=[(f'logs/{p.name}',p) for p in sorted((args.runs/'logs').glob('*'))
               if p.is_file() and p.suffix in ('.log','.json','.exit')]
    raw=[(p.relative_to(args.runs).as_posix(),p) for folder in
         ('baseline-fixed','fixed-ablation','historical-attribution','rolling-deadline','south','baxi-timeline',
          'performance','performance-isolated','audit','audit-final','historical','historical-rescue-ablation')
         for p in sorted((args.runs/folder).rglob('*')) if p.is_file()]
    archives = args.destination/'archives'
    archives.mkdir(parents=True,exist_ok=True)
    packages=[zip_group(archives/name, files) for name,files in (
        ('v30411-summary.zip',summaries),('v30411-fixed-replays.zip',raw),('v30411-technical.zip',technical))]
    to_json(archives/'index.json',packages)
    (archives/'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {r['name']}\n" for r in packages),encoding='utf-8')
    print(json.dumps({'stages':stage['observation'],'fixed':stage['admitted_fixed'],'technical_resources':stage['safety'],
                      'archive_bytes':sum(r['bytes'] for r in packages)},ensure_ascii=False))


if __name__=='__main__':
    main()
