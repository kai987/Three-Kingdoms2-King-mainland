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


def summary(root, manifest, status, stage):
    data = root/'data'
    decisions = table(data/'report-audit-errors.csv') if status['accounting_failures'] else []
    scores = table(data/'scenario-scores.csv') if status['outcomes'].get('complete') else []
    alerts = table(data/'balance-alerts.csv') if status['warning_count'] else []
    phase_results = defaultdict(Counter)
    for run in manifest:
        phase_results[run['wave']][run['outcome']] += 1
    lines = ['# V3.0.2 战略粮仓验收报告', '',
        '普通新战役和旧存档的 302 规则缺省关闭。区域市场继续独立设置。','',
        '## 观战范围','',
        '| 阶段 | 计划 | 到达截止 | 其他结果 |','| --- | ---: | ---: | --- |']
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
            blocked=sum(int(r['source_safety_rejections']) for r in values)
            later=sum(int(r['source_shortage_later']) for r in values)
            requests=sum(int(r['winter_requested']) for r in values if valid_numeric(r['winter_requested']) is not None)
            covered=sum(int(r['winter_delivered_timely']) for r in values
                        if valid_numeric(r['winter_delivered_timely']) is not None)
            timely_rate=f'{covered/requests:.2%}' if requests else 'null'
            lines.append(f'- {group} 实际发运 {sent:,} 笔，交付 {grain:,} 粮，其中期限前 {timely:,}。'
                         f'来源储备不足拦截 {blocked:,} 次，发运后九旬内同归属来源城出现缺粮 {later:,} 次。'
                         f'观测到的冬季军事补给以 {covered:,}／{requests:,} 粮计，及时率 {timely_rate}。')
        lines.append('')
    if scores:
        r2=[r for r in scores if r['wave']=='long' and r['group']=='S1']
        accounts=table(data/'fiscal-resource-account.csv')
        for run in r2:
            receipts=[r for r in accounts if all(r.get(k)==run[k] for k in ('wave','scenario','group'))]
            credits=Counter()
            for row in receipts:
                if row['direction']=='credit':
                    credits[row['category']]+=int(row['amount'])
            sources='，'.join(f'{tag} {amount:,} 金' for tag,amount in credits.most_common(5))
            if sources:
                lines.append(f'- {run["scenario"]} S1 二十年官仓主要贷记为 {sources}。城市间划转及运队归队会重复计作单城贷记，逐笔账按来源区分。')
        lines.append('')
    if alerts:
        lines.extend(['## 警戒线','','以下为全部越界配对。具体相对变化和百分点在 `data/balance-alerts.csv`。','',
                      '| 阶段 | 剧本／策略 | 组 | 指标 | S1 | 候选 |','| --- | --- | --- | --- | ---: | ---: |'])
        lines.extend(f'| {r["wave"]} | {r["scenario"]}／{r["strategy"]} | {r["group"]} | {r["metric"]} | {r["before"]} | {r["after"]} |'
                     for r in alerts)
        lines.append('')
    hard_errors = sum(int(row['city_resource_mismatches'])+
                      (int(row['reserve_audit_errors']) if valid_numeric(row['reserve_audit_errors']) is not None else 0)
                      for row in scores)
    checked_runtime = (stage/'checks/technical-gates.json').is_file()
    frozen_equal = status['frozen_checks'] and status['frozen_checks']==status['frozen_equal']
    complete = status['outcomes'].get('complete',0)==status['total']
    hard_pass = checked_runtime and frozen_equal and not hard_errors and not decisions
    historical = json.loads((stage/'historical/historical-convoys.json').read_text()) if (
                  stage/'historical/historical-convoys.json').is_file() else {}
    long_rows={(r['scenario'],r['group']):r for r in scores if r['wave']=='long'}
    def long_metric(scenario,group,key):
        row=long_rows.get((scenario,group))
        return int(row[key]) if row else None
    chibi, chibi_base = (long_metric('208-10',group,'unpaid_city_turns') for group in ('S3','S1'))
    chibi_gap,chibi_base_gap=(long_metric('208-10',group,'rations_missing') for group in ('S3','S1'))
    yellow,yellow_base=(long_metric('184-02',group,'convoy_hunger_losses') for group in ('S3','S1'))
    long_pass=chibi is not None and chibi_base is not None and chibi<=1727 and chibi_gap<chibi_base_gap and (
              yellow is not None and yellow_base is not None and yellow<yellow_base)
    def scope(phase):
        return phase_results[phase]['complete']==sum(phase_results[phase].values()) and bool(phase_results[phase])
    five_year = ('有警戒线越界' if any(r['wave'] in ('dry','winter','holdout') for r in alerts) else '未见警戒线越界') if (
        scope('dry') and scope('winter') and scope('holdout')) else '未完成全矩阵'
    long_balance = ('达到赤壁和黄巾专项目标' if long_pass else '未达到全部专项目标') if scope('long') else '未完成全矩阵'
    lines.extend(['## 验收状态','','| 范围 | 结果 |','| --- | --- |',
                  f'| 已采技术与守恒证据 | {"通过已执行检查" if hard_pass else "待复核"} |',
                  f'| 战略储备与主动调粮 | {"通过账目、存读和真实发运专项" if checked_runtime else "待验证"} |',
                  f'| 冬季储备与单站中转 | {"通过独立开关与实际回执专项" if checked_runtime else "待验证"} |',
                  f'| 运队历史与返程 | {"1706 关闭规则重放一致，合法补粮受控回归通过" if historical.get("disabled_1706",{}).get("status")=="matched" and checked_runtime else "待验证"} |',
                  f'| 五年经济平衡 | {five_year} |',
                  f'| 二十年经济平衡 | {long_balance} |',
                  f'| 进入下一阶段 | {"可评审" if complete and hard_pass and long_pass and not alerts else "继续留在 302 实验评估"} |',
                  '| 正式默认启用 | 关闭 |','',
                  f'已报告局的官仓和战略运单对账差异 {hard_errors}。'
                  '实际测试日志、复跑记录、历史凭证与浏览器截图见对应目录。',''])
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
        for planned in root.glob('planned-*.json'):
            copy_contents(planned,stage/'data'/planned.name)
        for script in ('v302_audit.py','v302_experiments.py','v302_backends.py','v302_report.py',
                       'v302_package.py','v302_historical.py','v301_replay_1706.py','observer-config.json'):
            copy_contents(TOOL_ROOT/'tools/economy-balance'/script,stage/'scripts'/script)
        for script in ('browser_granary_smoke.mjs','browser_engine_smoke.mjs','browser_static_server.mjs',
                       'test_remake_strategic_granary.py'):
            copy_contents(TOOL_ROOT/'tests'/script,stage/'scripts'/script)
        sources=stage/'sources'
        sources.mkdir()
        head=git('rev-parse','HEAD').decode().strip()
        ref=git('symbolic-ref','HEAD').decode().strip()
        (sources/'v302-from-v301.patch').write_bytes(git('diff','--binary',BASE,head))
        subprocess.run(['git','bundle','create',str(sources/'v302-source.bundle'),ref,'^'+UPSTREAM],
                       check=True,cwd=TOOL_ROOT,capture_output=True)
        bundle=subprocess.run(['git','bundle','verify',str(sources/'v302-source.bundle')],
                              check=True,cwd=TOOL_ROOT,text=True,capture_output=True)
        (sources/'bundle-verification.txt').write_text(bundle.stdout+bundle.stderr,encoding='utf-8')
        source_paths={name:checksum(TOOL_ROOT/name)
                      for name in git('ls-files','-z','--','source','game/config','game/data/campaigns','crates')
                                 .decode().strip('\x00').split('\x00') if name and (TOOL_ROOT/name).is_file()}
        to_json(sources/'source-sha256.json',source_paths)
        to_json(stage/'data/validation-manifest.json',dict(
            version=302, observer_release=RELEASE, source_head=head, v301_base=BASE, upstream_base=UPSTREAM,
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
