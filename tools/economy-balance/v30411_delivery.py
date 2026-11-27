"""Package reviewed replay evidence and checks into an independent Git archive."""
import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path
import platform
import shutil
import subprocess
from zipfile import ZIP_DEFLATED, ZipFile

from common import ROOT, to_json
from v30411_report import package, rows, write


def content_hash(path):
    with path.open('rb') as stream:
        return sha256(stream.read()).hexdigest()


def git_sha(ref):
    return subprocess.check_output(['git','-C',str(ROOT),'rev-parse',ref],text=True).strip()


def markdown(path, text):
    path.write_text(text.strip()+'\n',encoding='utf-8')


def render_stage(output, prior, runs):
    checks, data, docs = output/'checks', output/'data', output/'docs'
    stage = json.loads((checks/'fixed-stage-status.json').read_bytes())
    experiments = {r['group']:r for r in stage['integrated']}
    audit_path = runs/'audit/resource-safety.json'
    audits = json.loads(audit_path.read_bytes()) if audit_path.exists() else []
    audit_totals = Counter()
    for row in audits:
        audit_totals.update(row['safety'])
        audit_totals['city_resource_mismatches'] += row['grain_account']['city_resource_mismatches']
        audit_totals['market_errors'] += row['market'].get('transaction_errors',0)+row['market'].get('account_errors',0)
        audit_totals['city_postings'] += row['grain_account']['city_postings']
        audit_totals['market_transactions'] += row['market'].get('transactions',0)
    safety_pass = bool(audits) and all(value==0 for key,value in audit_totals.items()
                                      if key not in ('city_postings','market_transactions'))
    south = {(row['group'],row['city']):int(row['missing']) for row in rows(data/'southern-checkpoint-results.csv')}
    cities = sorted(city for group,city in south if group=='U0')
    south_totals = {group:sum(south[group,city] for city in cities) for group in {group for group,_ in south}}
    south_gate = {group: total<=15422 and south[group,'luling']<=807 and south[group,'yidu']<=753
                  and south[group,'baxi']<3779 for group,total in south_totals.items() if group in ('U6','V2')}
    stage.update(safety={'passed':safety_pass,'checked_replays':len(audits),'totals':dict(audit_totals)},
                 south_totals=south_totals,south_gate=south_gate)
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
    stage['admitted_safety'] = safety_pass and all(r['within_30_percent'] for r in perf.values()) and bool(perf)
    stage['observation'] = {'quick_24m':'not_run','five_year':'not_run','twenty_year':'not_run','holdout':'not_run'}
    stage['default_enabled'] = False
    to_json(checks/'stage-status.json',stage)

    def table(groups):
        return '\n'.join(f"| {row['group']} | {row['timely_targets']} | {row['full_targets']} | "
                          f"{row['first_gap_grain']:,} | {row['actual_grain']:,} | {row['returning_delivered']} |"
                          for row in groups)

    header = '| 组 | 及时到货 | 首次足额 | 首次折顶覆盖 | 期限前实收 | 返程样本再到货 |\n|---|---:|---:|---:|---:|---:|'
    markdown(docs/'fixed-state-acceptance.md',f"""
# 89 个固定目标及 23 个返程来源

{header}
{table(stage['integrated'])}

目标为 U6 的 32／30／20,833／14 以及 V2 的 42／37／24,659／15，依次为及时到货、首次足额、折顶覆盖、返程样本再到货。准入结果见 [阶段检查](../checks/stage-status.json)。

原历史 T3 相对 T0 丢失 21 个原有及时目标。T5 相对 T4 丢失 24 个。共 {stage['actual_historical_losses']} 条逐目标原始发运、到货和新规划证据保存在 [逐目标归因](../data/fixed-demand-regression-attribution.csv)。历史同档旧引擎复跑与原表逐项一致 {stage['prior_identical']}/{stage['exact_prior_pairs']}。不同的集成版值单列。

原表的 T0 35／33／23,147，T3 19／15／9,783，T4 46／41／27,398，T5 26／22／13,648。返程覆盖历史 T0 为 16，T3 为 4，T4 为 17，T5 为 9。重放的来源名册、报价和实际再到货见 [23 个返程样本](../data/returning-slot-coverage-recovery.csv)。
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
    for path in (args.runs/'audit').glob('*'):
        if path.is_file():
            shutil.copy2(path,(checks if path.suffix=='.json' else data)/path.name)
    for name in ('fixed-replay-inputs.json','fixed-capacity-replay-traces.json'):
        shutil.copy2(args.runs/'fixed-ablation'/name,checks/name)
    for name in ('historical-transport-replay-index.csv','checkpoint-sources.json'):
        shutil.copy2(args.prior/'summary/sources'/name,sources/name)
    manifest = json.loads((args.runs/'inputs/input-manifest.json').read_bytes())
    for row in manifest:
        if 'container' in row:
            parts = Path(row['container']).parts
            root = parts.index('worktrees')+1 if 'worktrees' in parts else len(parts)-1
            row['container'] = '/'.join(parts[root:])
    to_json(checks/'replay-inputs.json',manifest)
    shipments = []
    for path in (args.runs/'historical').glob('*/historical-convoy-safety.json'):
        shutil.copy2(path,checks/f'historical-convoy-{path.parent.name}.json')
        for row in json.loads(path.read_bytes())['results']:
            terminal = next((item['row'] for item in row['receipts'] if item['event']=='terminal'),{})
            shipments.append(dict(convoy=row['convoy'],group=row['group'],first_turn=row['snapshots'][0]['turn'],
                final_turn=row['snapshots'][-1]['turn'],active=row['snapshots'][-1]['convoy'] is not None,
                last_snapshot=row['snapshots'][-1]['convoy'],terminal=terminal,sha256=row['checkpoint_sha256']))
    write(data/'historical-convoy-regression.csv',shipments)
    markdown(docs/'historical-transport-review.md', '\n'.join([
        '# 历史运队', '', '| 运输队 | 分组 | 末旬 | 期末在途 | 终止饥损 |','|---|---|---:|---|---:|',
        *(f"| {r['convoy']} | {r['group']} | {r['final_turn']} | {str(r['active']).lower()} | "
          f"{r['terminal'].get('hunger_losses','—')} |" for r in sorted(shipments,key=lambda r:(r['convoy'],r['group']))),
        '', '[原 14 支运队索引](../sources/historical-transport-replay-index.csv) · [实际末态与终止凭证](../data/historical-convoy-regression.csv)']))
    stage = render_stage(out,args.prior,args.runs)
    metadata = dict(source_sha=git_sha('HEAD'),integration_base=git_sha('3ec93fbd'), prior_engine=git_sha('d096f47a'),
        prior_technical=git_sha('e6d24513'), prior_archive=git_sha('d5bceee7'), weather_221_locked_inputs=True,
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
    technical=[(f'logs/{p.name}',p) for p in sorted((args.runs/'logs').glob('*.log'))]
    raw=[(p.relative_to(args.runs).as_posix(),p) for folder in
         ('fixed-ablation','historical-attribution','south','performance','audit')
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
