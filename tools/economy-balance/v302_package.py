"""Assemble and verify the portable V3.0.2 validation archive."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import csv
from hashlib import file_digest
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import NamedTemporaryFile, TemporaryDirectory
import zipfile

from common import TOOL_ROOT, git, to_json

ARCHIVE = 'three-kingdoms-strategic-granary-v302-validation.zip'
BASE = 'dae702d60dc471803abe31bed2c3827cb3629920'
RELEASE = '3f01f3f1ec429cc338bac949414253ba26e5c18d'
UPSTREAM = '099b2ccc57590f6345fc41e5fb89688375051ed7'
LABELS = {'rapid':'快速观战','dry':'五年无天气','winter':'五年天气联动',
          'long':'二十年','holdout':'保留种子','smoke':'全剧本冒烟'}


def checksum(path):
    with path.open('rb') as stream:
        return file_digest(stream,'sha256').hexdigest()


def table(path):
    with path.open(encoding='utf-8',newline='') as stream:
        return list(csv.DictReader(stream))


def valid_numeric(value):
    return None if value in (None,'','null','not_collected','not_applicable') else float(value)


def gate_results(stage):
    path=stage/'checks/technical-gates.json'
    results=json.loads(path.read_text()) if path.is_file() else {}
    if not results:
        return results, False
    engines=all(results[key]['passed_combined']>0 and
                results[key]['passed_combined']+results[key]['skipped']==results[key]['count']
                for key in ('python','rust'))
    browser=results['browser']
    runtime=results['runtime']
    passed=(engines and all(results[k]>0 for k in ('rust_crate','wasm_vectors','node')) and runtime['ok']
            and runtime['cpu_save_bytes_equal'] and runtime['granary_convoy_roundtrip']
            and results['domain_parity']['exact'] and
            {'zh-Hant','ja'} <= {row['locale'] for row in browser if row['forecastRows']==9
                              and row['realOrder'] and not row['horizontalOverflow'] and not row['errors']})
    return results, bool(passed)


def specialized_results(root, scores, manifest):
    data=root/'data'
    long={(row['scenario'],row['group']):row for row in scores if row['wave']=='long'}
    observations={(row['scenario'],row['group']):root/row['output']
                  for row in manifest if row['wave']=='long' and row.get('output')}
    active_granary_deliveries=table(data/'grain-commitment-account.csv')
    settled=[row for row in active_granary_deliveries if row.get('status')=='returned'
             and (valid_numeric(row.get('delivered')) or 0)>0]
    cost_verified=sum(valid_numeric(row.get('actual_cost_cents')) is not None for row in settled)
    lines=['### 空间分布与战争活动','',
           '| 二十年剧本 | 组 | 同势力三月余粮可覆盖次数 | 有合法路线余粮可覆盖次数 | 期末现役 | AI 出征 | 战斗 |',
           '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for (scene,group),row in sorted(long.items()):
        columns=('surplus_covered','legal_surplus_covered','active_troops','ai_sorties','battles')
        numeric=[valid_numeric(row.get(key)) for key in columns]
        lines.append(f'| {scene} | {group} | '+' | '.join('—' if v is None else f'{v:,.0f}' for v in numeric)+' |')
    lines.extend(['','余粮覆盖按发生缺粮时的可用毛量统计。订单的实际发运、终点及时到货与逐局剩余缺口提供另一组观测。'
        '出征和期末兵力来自实际战局，各组并未固定军队规模。',''])
    if long:
        lines.extend(['### 二十年缺粮分布','',
                      '| 剧本 | 组 | 缺粮量最高的五座城 |',
                      '| --- | --- | --- |'])
        for scene,group in sorted(long):
            if group not in ('S1','S3','S4'):
                continue
            source=observations[scene,group]
            gaps=Counter()
            for shortage in table(source/'shortages.csv'):
                gaps[shortage['city']]+=int(shortage['missing'])
            cities='，'.join(f'{city} {grain:,}' for city,grain in gaps.most_common(5))
            lines.append(f'| {scene} | {group} | {cities or "—"} |')
        lines.append('')
    lines.extend(['### 储备占用、运队与到岸成本','',
                  '| 二十年剧本 | 组 | 期末战略储备 | 九旬未动比例 | 发运后九旬来源缺粮城旬 | 护卫实际接收率 | 到货后护卫饥损 |',
                  '| --- | --- | ---: | ---: | ---: | ---: | ---: |'])
    for (scene,group),row in sorted(long.items()):
        columns=('strategic_stock','long_idle_reserve_pct','source_shortage_later',
                 'escort_reception_pct','convoy_return_escort_hunger')
        formatted=[]
        for key in columns:
            value=valid_numeric(row.get(key))
            formatted.append('—' if value is None else f'{value:,.2f}%' if key.endswith('pct') else f'{value:,.0f}')
        lines.append(f'| {scene} | {group} | '+' | '.join(formatted)+' |')
    lines.extend(['',
        f'运粮完成交付且队伍已返回的 {len(settled):,} 笔战略运单中，'
        f'{cost_verified:,} 笔有实付机会成本凭证。失败或仍在途的成本保留对应状态。'
        '区域采购表另列实际支付、到货与运输损耗。中转首段的入仓粮独立列账，终点交付只计最终目的地。','',
        '来源城缺粮按发运后九旬内仍属原势力的同城缺粮记录计算。归因需再检查该城其他军队、收入、耗粮和运输流水。',''])
    cases=[row for row in table(data/'convoy-hunger-comparison.csv') if row.get('wave')=='long' and row.get('group')=='S3']
    for scene in sorted({key[0] for key in long}):
        ranked=sorted((case for case in cases if case['scenario']==scene),
                      key=lambda row:int(row['after_delivery_escort']),reverse=True)
        if ranked:
            largest=ranked[0]
            lines.append(f'- {scene} S3 到货后护卫饥损人数最多的是运队 {largest["convoy_id"]}，'
                         f'{largest["source"]} 至 {largest["target"]}，损失 {largest["after_delivery_escort"]} 人。'
                         '其余案例见 `data/convoy-hunger-comparison.csv`。')
    lines.append('')
    return lines


def summary(root, manifest, status, stage):
    data = root/'data'
    decisions = table(data/'report-audit-errors.csv') if status['accounting_failures'] else []
    scores = table(data/'scenario-scores.csv') if status['outcomes'].get('complete') else []
    alerts = table(data/'balance-alerts.csv') if status['warning_count'] else []
    phase_results = defaultdict(Counter)
    for run in manifest:
        phase_results[run['wave']][run['outcome']] += 1
    technical,checked_runtime=gate_results(stage)
    lines = ['# V3.0.2 战略粮仓验收报告','',
        '普通新战役和旧存档的 302 规则缺省关闭。区域市场继续独立设置。','',
        '## 实现范围','',
        '- 战略储备在原官仓中预留，市场库存独立。九旬预测和来源城安全储备共同约束调粮。',
        '- 调粮使用原有命令书、武将和实体运队。预留、实际发运、在途粮、实际到货及返程的独立凭证随战役保存。',
        '- 主动调拨、冬季提前储备及单站接力可在战略粮仓实验内分别启用。城市情报提供储备、预测、路线和运单操作。',
        '- 配置、Python 领域、Runtime 和前端的逐文件改动见 `sources/changed-files.txt`，规则见 `docs/README.md`。',
        '- 町等级决定逻辑仓容。独立仓房建设与维持费用留待单独验收。S2 含随储备引入的优先级和返程安全措施。','',
        '## 技术回归','']
    if technical:
        for key,label in (('python','Python 战役'),('rust','Rust 战役')):
            test=technical[key]
            lines.append(f'- {label}共 {test["count"]:,} 项。按全量运行和受影响模块复跑合计，'
                         f'通过 {test["passed_combined"]:,} 项，跳过 {test["skipped"]} 项。'
                         f'首次问题及修复记录见 `checks/{test["full_log"]}` 和 `checks/{test["correction_log"]}`。')
        runtime=technical['runtime']
        browser_times='，'.join(f'{entry["locale"]} {entry["turnWaitMilliseconds"]/1000:.3f} 秒'
                               for entry in technical['browser'])
        lines.extend([f'- Rust crate {technical["rust_crate"]} 项、Rust／WASM {technical["wasm_vectors"]:,} 个用例、'
            f'Node {technical["node"]} 项。Pyodide／CPU {runtime["requests"]} 次请求对照，'
            f'战略运单存读 {runtime["granary_convoy_roundtrip"]} 次，'
            f'Python／Rust {technical["domain_parity"]["turns"]} 旬完整领域状态和随机数一致。',
            f'- 真实浏览器检查繁中桌面和日文窄屏。预览、锁粮、确认耗费与发运均有截图及命令记录。'
            f'发运后完成下一旬推进分别为 {browser_times}。',
            '- 历史 1706 的原规则重放保留实际饥损。启用 302 后的合法补给、零余粮及城市易主验证为受控测试。'])
    fix=status.get('relay_fix_reruns')
    if fix:
        lines.append(f'- 修复了首段货粮全部转作返程口粮时的零到货校验。'
                     f'Python 与 Rust 各复跑 22 项相关用例。正式矩阵的原冻结版本记录 '
                     f'{status["empty_relay_receipts"]} 笔空中转回执，已核对 {fix["affected_revalidated"]}／{fix["affected_count"]} 局受影响样本。'
                     f'合计 {fix["matched"]}／{fix["planned"]} 局重放通过，'
                     '零到货日志的预期变化与独立账户记账顺序分别列在清单里。')
    else:
        lines.append('技术证据索引暂未归档。')
    lines.extend(['',
        '## 观战范围','',
        '| 阶段 | 计划 | 到达截止 | 其他结果 |','| --- | ---: | ---: | --- |'])
    for phase, label in LABELS.items():
        outcomes=phase_results[phase]
        other='，'.join(f'{key} {n}' for key,n in sorted(outcomes.items()) if key!='complete') or '—'
        lines.append(f'| {label} | {sum(outcomes.values())} | {outcomes["complete"]} | {other} |')
    lines.extend(['',f'旧 V3.0.1 固定基准文件比较 {status["frozen_equal"]}／{status["frozen_checks"]} 一致。'
                  f'报告解析或对账异常 {len(decisions)} 局。经济或性能警戒线越界 {len(alerts)} 项。',''])
    if phase_results['long']['complete']:
        lines.extend(['## 二十年结果','','| 剧本 | 组 | 缺粮城旬 | 缺粮量 | 官仓粮 | 官仓金 | 运队饥损 | 每旬 CPU 秒 |',
                      '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |'])
        for row in sorted((r for r in scores if r['wave']=='long'),key=lambda r:(r['scenario'],r['group'])):
            columns=('scenario','group','unpaid_city_turns','rations_missing','grain_stock','gold_stock',
                     'convoy_hunger_losses','mean_turn_cpu')
            lines.append('| '+' | '.join(row[k] for k in columns)+' |')
        lines.append('')
    else:
        lines.extend(['## 二十年结果','','到达完整二十年截止点的运行暂未生成结果。',''])
    lines.extend(['## 重点分析','','以同剧本、同种子、同策略、同天气和相同截止时点为配对口径。完整警戒线逐项记录在数据表。',''])
    for wave in ('dry','winter','long','holdout'):
        samples=[row for row in scores if row['wave']==wave]
        if not samples:
            continue
        lines.extend([f'### {LABELS[wave]}','',
                      '| 组 | 局数 | 缺粮城旬 | 缺粮量 | 运队饥损 | 实到调粮 |',
                      '| --- | ---: | ---: | ---: | ---: | ---: |'])
        for group in ('S0','S1','S2','S3','S4','S3-no-winter'):
            subset=[r for r in samples if r['group']==group]
            if subset:
                vals=[sum(int(r[key]) for r in subset) for key in ('unpaid_city_turns','rations_missing','convoy_hunger_losses')]
                grain=[int(r['strategic_delivered']) for r in subset if valid_numeric(r['strategic_delivered']) is not None]
                lines.append(f'| {group} | {len(subset)} | {vals[0]} | {vals[1]} | {vals[2]} | {sum(grain) if grain else "—"} |')
        lines.append('')
    live=[r for r in scores if r['group'] in ('S3','S4')]
    if live:
        lines.extend(['### 空间调粮、冬季与返回',''])
        for group in ('S3','S4'):
            values=[r for r in live if r['group']==group]
            if not values:
                continue
            sent=sum(int(r['proactive_dispatched'])+int(r['winter_dispatched']) for r in values)
            grain=sum(int(r['strategic_delivered']) for r in values)
            timely=sum(int(r['timely_grain']) for r in values)
            refills=sum(int(r['emergency_refills']) for r in values)
            relay_grain=sum(int(r['relay_net_delivered']) for r in values)
            blocked=sum(int(r['source_safety_rejections']) for r in values)
            later=sum(int(r['source_shortage_later']) for r in values)
            requests=sum(int(r['winter_requested']) for r in values if valid_numeric(r['winter_requested']) is not None)
            covered=sum(int(r['winter_delivered_timely']) for r in values
                        if valid_numeric(r['winter_delivered_timely']) is not None)
            timely_rate=f'{covered/requests:.2%}' if requests else 'null'
            lines.append(f'- {group} 直接主动或冬季发运 {sent:,} 笔，交付至终点 {grain:,} 粮，'
                         f'其中期限前 {timely:,}，经中转送至终点 {relay_grain:,}。返程应急接济 {refills:,} 次。'
                         f'来源储备不足拦截 {blocked:,} 次，发运后九旬内同归属来源城出现缺粮 {later:,} 次。'
                         f'观测到的冬季军事补给以 {covered:,}／{requests:,} 粮计，及时率 {timely_rate}。')
        lines.append('')
    if scores:
        lines.extend(specialized_results(root,scores,manifest))
        fiscal_samples=[r for r in scores if r['wave']=='long' and r['group'] in ('S1','S3')]
        accounts=table(data/'fiscal-resource-account.csv')
        for run in fiscal_samples:
            receipts=[r for r in accounts if all(r.get(k)==run[k] for k in ('wave','scenario','group'))]
            credits=Counter()
            debits=Counter()
            for row in receipts:
                ledger=credits if row['direction']=='credit' else debits
                ledger[row['category']]+=int(row['amount'])
            sources='，'.join(f'{tag} {amount:,} 金' for tag,amount in credits.most_common(4))
            if sources:
                lines.append(f'- {run["scenario"]} {run["group"]} 二十年官仓主要贷记为 {sources}。'
                             f'市场净现金 {credits["market_exchange"]-debits["market_exchange"]:+,} 金。')
        if fiscal_samples:
            lines.append('城市划转和运队归队构成单城贷记。期末金钱及市场净现金使用各自的账目口径。')
        lines.append('')
        cpu_change=[r for r in table(data/'pairwise.csv') if r.get('metric')=='mean_turn_cpu'
                    and r.get('baseline')=='S1' and r.get('group') in ('S2','S3','S4')
                    and valid_numeric(r.get('change_pct')) is not None]
        if cpu_change:
            slowest=max(cpu_change,key=lambda row:float(row['change_pct']))
            lines.extend(['### 性能','',f'最大每旬 CPU 增幅出现在 {slowest["wave"]} '
                          f'{slowest["scenario"]}／策略 {slowest["strategy"]} {slowest["group"]}，'
                          f'{float(slowest["before"]):.3f} 秒变为 {float(slowest["after"]):.3f} 秒'
                          f'（{float(slowest["change_pct"]):+.1f}%）。'
                          '逐局 CPU、实际时长、P50／P95、内存及线路探针见 `data/performance-comparison.csv`。',''])
        yellow_performance=[row for row in table(data/'performance-comparison.csv')
                            if row.get('wave')=='long' and row.get('scenario')=='184-02' and
                            row.get('group') in ('S1','S3','S4')]
        if yellow_performance:
            lines.extend(['| 黄巾二十年 | 每旬 CPU P50 秒 | 每旬 CPU P95 秒 | 实际补给线路查询对数 |',
                          '| --- | ---: | ---: | ---: |'])
            for row in yellow_performance:
                routes=json.loads(row['route_queries'])
                lines.append(f'| {row["group"]} | {float(row["cpu_p50"]):.2f} | {float(row["cpu_p95"]):.2f} | '
                             f'{routes["supply_route_pairs"]:,} |')
            lines.extend(['','同一场观战的战局与请求数量会一同变化。这里的差值记录了完整推进的成本。',''])
    if alerts:
        lines.extend(['## 警戒线','','以下为全部越界配对。具体相对变化和百分点在 `data/balance-alerts.csv`。','',
                      '| 阶段 | 剧本／策略 | 组 | 指标 | S1 | 候选 |','| --- | --- | --- | --- | ---: | ---: |'])
        lines.extend(f'| {r["wave"]} | {r["scenario"]}／{r["strategy"]} | {r["group"]} | {r["metric"]} | {r["before"]} | {r["after"]} |'
                     for r in alerts)
        lines.append('')
    hard_errors = sum(int(row['city_resource_mismatches'])+
                      (int(row['reserve_audit_errors']) if valid_numeric(row['reserve_audit_errors']) is not None else 0)
                      for row in scores)
    frozen_equal = status['frozen_checks'] and status['frozen_checks']==status['frozen_equal']
    complete = status['outcomes'].get('complete',0)==status['total']
    relay_revalidated=(not fix or (fix['matched']==fix['planned'] and fix['affected_revalidated']==fix['affected_count']))
    hard_pass = checked_runtime and frozen_equal and relay_revalidated and not hard_errors and not decisions
    historical = json.loads((stage/'historical/historical-convoys.json').read_text()) if (
                  stage/'historical/historical-convoys.json').is_file() else {}
    long_rows={(r['scenario'],r['group']):r for r in scores if r['wave']=='long'}
    def long_metric(scenario,group,key):
        row=long_rows.get((scenario,group))
        return int(row[key]) if row else None
    chibi, chibi_base = (long_metric('208-10',group,'unpaid_city_turns') for group in ('S3','S1'))
    chibi_gap,chibi_base_gap=(long_metric('208-10',group,'rations_missing') for group in ('S3','S1'))
    yellow,yellow_base=(long_metric('184-02',group,'convoy_return_escort_hunger') for group in ('S3','S1'))
    yellow_count,yellow_old_count=(long_metric('184-02',group,'unpaid_city_turns') for group in ('S3','S0'))
    yellow_gap,yellow_old_gap=(long_metric('184-02',group,'rations_missing') for group in ('S3','S0'))
    has_long_cases=all(metric is not None for metric in (chibi,chibi_base,chibi_gap,chibi_base_gap,
                       yellow,yellow_base,yellow_count,yellow_old_count,yellow_gap,yellow_old_gap))
    long_pass=(has_long_cases and chibi<=1727 and chibi_gap<chibi_base_gap and yellow<yellow_base
               and yellow_count<yellow_old_count and yellow_gap<yellow_old_gap
               and not any(row['wave']=='long' for row in alerts))
    def scope(phase):
        return phase_results[phase]['complete']==sum(phase_results[phase].values()) and bool(phase_results[phase])
    five_year = ('有警戒线越界' if any(r['wave'] in ('dry','winter','holdout') for r in alerts) else '未见警戒线越界') if (
        scope('dry') and scope('winter') and scope('holdout')) else '未完成全矩阵'
    long_balance = ('达到赤壁和黄巾专项目标' if long_pass else '未达到全部专项目标') if scope('long') else '未完成全矩阵'
    lines.extend(['## 验收状态','','| 范围 | 结果 |','| --- | --- |',
                  f'| 已采技术与守恒证据 | {"通过已执行检查" if hard_pass else "待复核"} |',
                  f'| 战略储备 | {"账目、释放、存读专项通过" if checked_runtime else "待验证"} |',
                  f'| 主动调粮 | {"实际发运、扣粮、接收专项通过" if checked_runtime else "待验证"} |',
                  f'| 冬季储备 | {"独立开关与区域附加储备专项通过，及时率见配对警戒表" if checked_runtime else "待验证"} |',
                  f'| 单站中转 | {"首段凭证、两次实体发运及终点去重专项通过" if checked_runtime else "待验证"} |',
                  f'| 运队历史与返程 | {"1706 关闭规则重放一致，合法补粮受控回归通过" if historical.get("disabled_1706",{}).get("status")=="matched" and checked_runtime else "待验证"} |',
                  f'| 五年经济平衡 | {five_year} |',
                  f'| 二十年经济平衡 | {long_balance} |',
                  f'| 进入下一阶段 | {"可评审" if complete and hard_pass and long_pass and not alerts else "继续留在 302 实验评估"} |',
                  '| 正式默认启用 | 关闭 |','',
                  f'已报告局核对 {sum(int(row["city_postings"]) for row in scores):,} 笔官仓资源写入，'
                  f'{sum(int(row["market_checks"]) for row in scores):,} 笔市场样本。'
                  f'官仓和战略运单对账差异 {hard_errors}。'
                  '实际测试日志、复跑记录、历史凭证与浏览器截图见对应目录。',''])
    if has_long_cases:
        lines.extend(['### 下一轮验证重点','',
            f'- 赤壁 S3 缺粮城旬 {chibi:,}（S1 {chibi_base:,}），累计缺粮 {chibi_gap:,}（S1 {chibi_base_gap:,}）。'
            '先复核最大缺口城市、可用路权及长期官仓积累。',
            f'- 黄巾 S3 到货后护卫饥损 {yellow:,}（S1 {yellow_base:,}），'
            f'缺粮城旬 {yellow_count:,}（S0 {yellow_old_count:,}）。'
            '先重放真实返程热点和调粮来源城，再决定是否调整实验参数。',
            '- 复核五年天气对照中的小势力、季节补给和候选路线成本。参数筛选使用独立开发种子，现有保留种子继续用于验证。',''])
    report='\n'.join(lines)+'\n'
    (stage/'docs/validation-results.md').write_text(report,encoding='utf-8')
    return report


def copy_contents(source,destination):
    if source.is_dir():
        shutil.copytree(source,destination,dirs_exist_ok=True)
    else:
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)


def run_package(root, out, checks):
    archive=out/ARCHIVE
    out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((root/'data/simulation-manifest.json').read_text())['simulations']
    status=json.loads((root/'data/report-status.json').read_text())
    if len(manifest)!=status['total']:
        raise ValueError('Report and simulation manifest disagree')
    fix=status.get('relay_fix_reruns')
    if fix and fix['reported']<fix['planned']:
        raise ValueError('The final relay revalidation is still running')
    with TemporaryDirectory(prefix='granary-v302-',dir=root.parent) as tmp:
        tmp=Path(tmp)
        stage=tmp/'stage'
        stage.mkdir()
        for name in ('data','historical','screenshots','checks'):
            source=root/name
            if source.exists():
                copy_contents(source,stage/name)
        if checks and checks.exists():
            for log in checks.glob('*.log'):
                copy_contents(log,stage/'checks'/log.name)
        if (root.parent/'browser/opening.json').is_file():
            copy_contents(root.parent/'browser/opening.json',stage/'checks/browser-controlled-save.json')
        copy_contents(TOOL_ROOT/'docs/strategic-granary-v302',stage/'docs')
        for run in manifest:
            path=run.get('output')
            if path:
                if not path.startswith('observed/') or '..' in Path(path).parts:
                    raise ValueError(f'Unexpected recorded output {path}')
                copy_contents(root/path,stage/path)
        if fix:
            reruns=json.loads((root/'data/relay-fix-reruns.json').read_text())['comparisons']
            for run in reruns:
                path=Path(run['after_output'])
                if path.parts[0]!='observed' or '..' in path.parts:
                    raise ValueError(f'Unexpected replay output {path}')
                copy_contents(root.parent/'postfix'/path,stage/'checks/relay-fix-replays'/path)
        for planned in root.glob('planned-*.json'):
            copy_contents(planned,stage/'data'/planned.name)
        for script in ('v302_audit.py','v302_experiments.py','v302_backends.py','v302_report.py',
                       'v302_package.py','v302_historical.py','v301_report.py','v301_replay_1706.py','observer-config.json'):
            copy_contents(TOOL_ROOT/'tools/economy-balance'/script,stage/'scripts'/script)
        for script in ('browser_granary_smoke.mjs','browser_engine_smoke.mjs','browser_static_server.mjs',
                       'test_remake_strategic_granary.py'):
            copy_contents(TOOL_ROOT/'tests'/script,stage/'scripts'/script)
        sources=stage/'sources'
        sources.mkdir()
        head=git('rev-parse','HEAD').decode().strip()
        ref=git('symbolic-ref','HEAD').decode().strip()
        (sources/'v302-from-v301.patch').write_bytes(git('diff','--binary',BASE,head))
        (sources/'changed-files.txt').write_bytes(git('diff','--name-status',BASE,head))
        subprocess.run(['git','bundle','create',str(sources/'v302-source.bundle'),ref,'^'+UPSTREAM],
                       check=True,cwd=TOOL_ROOT,capture_output=True)
        bundle=subprocess.run(['git','bundle','verify',str(sources/'v302-source.bundle')],
                              check=True,cwd=TOOL_ROOT,text=True,capture_output=True)
        (sources/'bundle-verification.txt').write_text(bundle.stdout+bundle.stderr,encoding='utf-8')
        source_paths={name:checksum(TOOL_ROOT/name)
                      for name in git('ls-files','-z','--','source','game/config','game/data/campaigns','crates')
                                 .decode().strip('\x00').split('\x00') if name and (TOOL_ROOT/name).is_file()}
        to_json(sources/'source-sha256.json',source_paths)
        technical,_=gate_results(stage)
        to_json(stage/'data/validation-manifest.json',dict(
            version=302, observer_release=RELEASE, source_head=head, runtime_build=technical.get('static',{}).get('commit'),
            v301_base=BASE, upstream_base=UPSTREAM,
            source_ref=ref, map_sha256=checksum(TOOL_ROOT/'game/assets/map-campaign.png'), **status))

        report=summary(root,manifest,status,stage)
        (stage/'README.txt').write_text('三國大陸戰役 戰略糧倉 V3.0.2 驗收資料\n\n'
            '先閱讀 docs/validation-results.md。data/simulation-manifest.json 記錄每局執行狀態。\n'
            'observed 保存各局原始憑證。checks 保存測試及重跑。\n'
            'SHA256SUMS.txt 可核對每個獨立檔案。\n',encoding='utf-8')
        payload={x.relative_to(stage).as_posix():checksum(x) for x in sorted(stage.rglob('*')) if x.is_file()}
        (stage/'SHA256SUMS.txt').write_text(''.join(f'{digest}  {name}\n' for name,digest in payload.items()),
                                         encoding='utf-8')
        working=tmp/ARCHIVE
        with zipfile.ZipFile(working,'w',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=False) as target:
            for path in sorted(stage.rglob('*')):
                if path.is_file():
                    target.write(path,path.relative_to(stage).as_posix())
        with zipfile.ZipFile(working) as check:
            if (check.testzip() is not None or set(check.namelist())!=set(payload)|{'SHA256SUMS.txt'}
                    or len(check.infolist())!=len(payload)+1):
                raise ValueError('Invalid ZIP member list or CRC')
        validated=tmp/'native'
        native=Path('/usr/bin/ditto')
        if native.is_file():
            subprocess.run([str(native),'-x','-k',str(working),str(validated)],check=True)
        else:
            with zipfile.ZipFile(working) as bundle:
                bundle.extractall(validated)
        if (any(checksum(validated/name)!=digest for name,digest in payload.items()) or
                (validated/'SHA256SUMS.txt').read_bytes()!=(stage/'SHA256SUMS.txt').read_bytes()):
            raise ValueError('ZIP extraction differs from the verified staging files')
        digest=checksum(working)
        with NamedTemporaryFile(dir=out,prefix='.granary-verified-',delete=False) as handle:
            delivery=Path(handle.name)
        try:
            shutil.copy2(working,delivery)
            if checksum(delivery)!=digest:
                raise ValueError('Destination archive checksum differs')
            delivery.replace(archive)
        finally:
            delivery.unlink(missing_ok=True)
        archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n',encoding='ascii')
        archive.with_name(archive.stem+'-summary.md').write_text(report,encoding='utf-8')
        print(json.dumps(dict(output=str(archive),entries=len(payload)+1,bytes=archive.stat().st_size,
                              sha256=digest,status=status),ensure_ascii=False))


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('--out',type=Path,default=Path.home()/'Downloads')
    parser.add_argument('--checks',type=Path)
    args=parser.parse_args()
    run_package(args.root.resolve(),args.out.resolve(),args.checks.resolve() if args.checks else None)


if __name__=='__main__':
    main()
