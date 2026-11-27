"""Assemble a browsable validation summary and independently extractable archives."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import csv
import gzip
from hashlib import sha256 as stream_hash
from io import BytesIO, StringIO
import json
from pathlib import Path
import re
import shutil
from zipfile import ZIP_DEFLATED, ZipFile

from common import TOOL_ROOT, git, sha256, to_csv, to_json
from remake.campaign import digest, verified_save_content
from v3041_report import table


DIRECT = (
    'scenario-scores.csv', 'pairwise.csv', 'balance-alerts.csv', 'baseline-verification.csv',
    'simulation-manifest.json', 'report-status.json', 'winter-grain-timely-comparison.csv',
    'winter-order-timely-comparison.csv', 'transport-priority-distribution.csv',
    'officer-unit-efficiency.csv', 'transport-shadow-comparison.csv',
    'transport-efficiency-by-purpose.csv', 'coordination-safety-totals.csv',
)
MAX_PACKAGE = 90_000_000


def check_file(path):
    digest = stream_hash()
    with path.open('rb') as stream:
        while block := stream.read(1024*1024):
            digest.update(block)
    return dict(bytes=path.stat().st_size, sha256=digest.hexdigest())


def table_text(columns, rows):
    def text(value):
        if value in (None, 'null'):
            return '—'
        if type(value) is float or (isinstance(value, str) and re.fullmatch(r'-?\d+\.\d+', value)):
            return f'{float(value):,.2f}'
        return str(value)
    return '\n'.join(['| '+' | '.join(columns)+' |', '| '+' | '.join('---' for _ in columns)+' |',
                     *('| '+' | '.join(text(cell) for cell in row)+' |' for row in rows)])


def document(path, title, *paragraphs):
    path.write_text(f'# {title}\n\n'+'\n\n'.join(paragraphs)+'\n', encoding='utf-8')


def decision_summary(path, scores, fixed, south, warnings, performance, data):
    major = [r for r in scores if r['wave'] == 'long']
    chibi = [r for r in major if r['scenario'] == '208-10' and r['strategy'] == '211']
    valid = defaultdict(list)
    for row in fixed:
        if row['l5_actual_reception'] != 'null':
            valid[row['group']].append(int(row['l5_actual_reception']))
    fixed_totals = table_text(('组别', '覆盖的原始目标', '期限前收粮目标', '期限前实收粮'),
        ((group, len(grain), sum(value > 0 for value in grain), sum(grain))
         for group, grain in sorted(valid.items())))
    southern = defaultdict(list)
    for row in south:
        southern[row['group']].append(int(row['missing']))
    climate = table_text(('组别', '真实申请', '及时实收', '及时率 %', '首次期限及时率 %', '未满足', '未发运未满足'),
        ([r[k] for k in ('variant', 'requested_grain', 'timely_received_grain', 'timely_grain_rate',
                         'original_deadline_grain_rate', 'unresolved_grain', 'no_dispatch_unresolved_grain')]
         for r in sorted(chibi, key=lambda row: row['variant'])))
    reasons = Counter(row['metric'] for row in warnings)
    shadows = table(data/'transport-shadow-comparison.csv') if (data/'transport-shadow-comparison.csv').is_file() else []
    shared = [r for r in shadows if r['actual_same_source'] != '[]']
    overlap = [r for r in shared if r['actual_overlapping_escorts'] != '[]' and r['same_target'] == 'false']
    active = [r for r in scores if r['variant'] in ('T2', 'T3', 'T5')]

    def total(column):
        return sum(int(r[column]) for r in active if r.get(column, 'null') != 'null')

    long_economy = table_text(('剧本', '策略', '组别', '月数', '缺粮城旬', '累计缺口', '最长连续缺粮', '战斗', '出征',
                               '小势力存续', '北方势力存续'),
        ((r['scenario'], r['strategy'], r['variant'], r['full_months'], r['unpaid_city_turns'],
          r['rations_missing'], r['maximum_city_shortage_streak'], r['battles'], r['ai_sorties'],
          f"{r['surviving_small_factions']}/{r['small_factions']}",
          f"{r['surviving_northern_factions']}/{r['northern_factions']}")
         for r in sorted(major, key=lambda row: (row['scenario'], row['strategy'], row['variant']))))
    long_efficiency = table_text(('剧本', '策略', '组别', '每本命令书', '每武将日', '每文吏日', '每占位日',
                                  '平均完整周期 日', '小额长途', '第二位置粮运'),
        ((r[k] for k in ('scenario', 'strategy', 'variant', 'net_per_book', 'net_per_officer_day',
                         'net_per_clerk_day', 'net_per_slot_day', 'mean_completed_period',
                         'small_long_grain_orders', 'second_slot_grain_orders'))
         for r in sorted(major, key=lambda row: (row['scenario'], row['strategy'], row['variant']))))
    observed_cpu = {r['label']:{} for r in performance}
    for r in performance:
        if r['observation'] == 'true':
            observed_cpu[r['label']][r['group']] = float(r['full_turn_cpu_p95'])
    cpu = table_text(('检查点', '原规则 p95 秒', '效率组 p95 秒', '变化 %'),
        ((label, groups['T0'], groups['T3'], (groups['T3']/groups['T0']-1)*100)
         for label, groups in observed_cpu.items() if {'T0', 'T3'} <= groups.keys()))
    document(path, '验收结论与证据',
        '## 原调度与需求竞用',
        '原有普通调粮、战略粮仓、区域采购与军事筹粮在首次内政、城市行动及自动委任阶段竞争。'
        f'影子组共有 {len(shadows):,} 条建议，其中 {len(shared):,} 条在同势力同旬使用的来源上遇到旧任务。'
        f'{len(overlap):,} 条的目标不同且押运者重合，其中紧急建议 {sum(int(r["priority"])<=2 for r in overlap):,} 条。'
        '这些记录确认共同资源被使用。是否因此错过实际期限还需在当时的状态比较替代来源。 [竞争记录](../data/transport-shadow-comparison.csv)',
        '需求去重按同一城市九旬缺口回算，军队与运队采用独立目标。'
        '原调度缺少同口径需求段，因此仅对统一账内的重复凭证与真实交割做核对。',
        f'执行组观察到原期限已经经过的紧急需求段 {total("urgent_episodes"):,} 个，'
        f'其中 {total("feasible_urgent_episodes"):,} 个有完整及时报价，'
        f'{total("quote_only_urgent_episodes"):,} 个当时有报价但期限内未发运或购粮。'
        f'按各需求段首次实际缺口折顶归属的及时粮为 {total("urgent_initial_gap_covered"):,}。'
        '各需求的报价共用资源，该统计以逐段实际回执为准。 [调度对账汇总](../data/coordination-safety-totals.csv)',
        '## 固定检查点与第二运输位置',
        fixed_totals,
        'D2 的收益以同检查点 T4 对 T5 衡量。返程占位与实际运输见 [23 个返程样本](../data/returning-slot-replay.csv)。',
        '九旬南方案例的合计缺口。'
        + (' '.join(f'{group} 为 {sum(values):,} 粮' for group, values in sorted(southern.items())) if southern else '暂无合计。'),
        '[八城复放及逐城阻塞](southern-basin-replay.md)',
        '## 二十年军粮与地方经济',
        climate,
        long_economy,
        '黄巾、赤壁 212、魏灭蜀及保留种子的战争活动、人口、库存与小势力分母见 [剧本结果](../data/scenario-scores.csv)。',
        '## 命令书与人员效率',
        long_efficiency,
        '每位置日和人员日采用已经观察到结束与释放的运输。紧急军需和普通调粮使用各自的真实用途统计。'
        '小额长途使用不足 1,000 货粮且实际发运路线去程预计不少于 20 日的口径。'
        '回执、实际押运粮和饥损以独立分包的运输账为准。 [各类运输效率](../data/transport-efficiency-by-purpose.csv)',
        '## 资源安全、气候与性能',
        f'原始粮食流水对账累计差异为 {sum(int(row["resource_mismatches"]) for row in scores):,}。'
        f'执行组的重复运队回执 {total("duplicate_convoy_receipts"):,} 条，'
        f'实际命令书扣减偏离报价 {total("insufficient_book_postings"):,} 条。'
        f'同旬同势力押运复用 {total("simultaneous_escort_overlaps"):,} 次，'
        f'运输位超额 {total("transport_position_overruns"):,} 次，'
        f'同来源超出每旬发运次数 {total("repeated_origin_dispatches"):,} 次。',
        '来源城扣粮安全以实际发运表和粮食流水复核。'
        f'{total("cross_city_dispatches"):,} 笔跨城发运中，'
        f'{total("fully_observed_source_dispatches"):,} 笔有完整九旬源城观察窗，'
        f'{total("followed_by_source_shortage"):,} 笔之后观察到源城缺粮。',
        'V2.3.1 现有预测提供天气到达时间及额外耗粮。紧急报价采用保守时间窗并核验返程粮。'
        '实际返程和历史队伍状态见 [历史运队复放](historical-transport-safety.md)。',
        cpu,
        f'配对越过警戒线的计数按指标记录。共 {sum(reasons.values())} 项。 [实际警戒线](../data/balance-alerts.csv)',
        '## V3.0.4.2 准入',
        'V3.0.4.1 默认关闭。后续交通节点原型可以使用路线过长、合法来源受限的未改善检查点检验。'
        '经济候选的默认准入取决于紧急覆盖、长期缺粮及 CPU 警戒线。 [准入复核](v3042-readiness.md)')


def prior_terminal_proof(root, summary, commit):
    prefix = 'validation/v231/archives/'
    manifest = json.loads(git('show', f'{commit}:{prefix}archive-index.json'))
    entries = {row['original_path']:row['archive'] for row in manifest['files']}
    cases, prior_archives = [], {}

    def identity(raw):
        data = json.loads(gzip.decompress(raw))
        state = verified_save_content(data.get('save', data))['state']
        return dict(gzip_sha256=sha256(raw), domain_sha256=digest(state), rng=state['rng'])

    for case in ('184-02-2026-211', '208-10-2026-211', '208-10-2026-212'):
        member = f'campaigns/long/F4/{case}/terminal-save.json.gz'
        current = root/'observed'/'T0'/member
        if not current.is_file():
            continue
        name = entries[member]
        if name not in prior_archives:
            prior_archives[name] = git('show', f'{commit}:{prefix}{name}')
        with ZipFile(BytesIO(prior_archives[name])) as archived:
            old = identity(archived.read(member))
        new = identity(current.read_bytes())
        same = all(old[key] == new[key] for key in ('domain_sha256', 'rng'))
        cases.append(dict(case=case, archive=name, member=member, prior=old, current=new, same_domain_and_rng=same))
    if cases:
        to_json(summary/'checks'/'historical-f4-terminal-verification.json',
                dict(prior_archive_commit=commit, cases=cases))


def reference_tables(root, summary, scores):
    winter_commit = '015a21f178a338b9758e341211f669be15499225'
    referenced = ('scenario-scores.csv', 'winter-grain-timely-comparison.csv',
                  'historical-transport-replay-index.csv')
    pinned = {}
    for name in referenced:
        artifact = f'validation/v231/summary/data/{name}'
        content = git('show', f'{winter_commit}:{artifact}')
        pinned[name] = dict(path=artifact, commit=winter_commit, sha256=sha256(content))
        if name == 'historical-transport-replay-index.csv':
            (summary/'sources'/name).write_bytes(content)
            continue
        records = list(csv.DictReader(StringIO(content.decode('utf-8'))))
        selected = [r for r in records if r['group'] == 'F4' and r['wave'] in ('five', 'long')]
        if name == 'scenario-scores.csv':
            fields = ('wave', 'scenario', 'seed', 'strategy')
            old = {tuple(r[k] for k in fields):r for r in selected}
            metrics = {'unpaid_city_turns':'shortage_city_turns', 'rations_missing':'grain_gap',
                       'battles':'battles', 'final_population':'population', 'final_grain':'grain_stock',
                       'final_active_troops':'active_troops', 'convoy_dispatched':'convoy_dispatched'}
            pairs = []
            for score in scores:
                key = tuple(score[k] for k in fields)
                if score['variant'] != 'T0' or key not in old:
                    continue
                ref = old[key]
                for new, base in metrics.items():
                    actual, previous = int(score[new]), int(ref[base])
                    pairs.append(dict(zip(fields, key, strict=True), metric=new,
                        prior_F4=previous, current_T0=actual, same_months=ref['months'] == score['full_months'],
                        match=actual == previous))
            if pairs:
                to_csv(summary/'checks'/'historical-f4-macro-verification.csv', pairs)
            selected += [r for r in records if r['wave'] == 'holdout' and r['seed'] in
                         ('2041', '2042', '2043', '2044')]
        if selected:
            to_csv(summary/'sources'/f'prior-v231-{name}', selected)
    early_convoy = 'validation/v231/summary/checks/historical-convoy-2.json'
    data = git('show', f'{winter_commit}:{early_convoy}')
    (summary/'sources'/'prior-v231-historical-convoy-2.json').write_bytes(data)
    pinned['historical-convoy-2.json'] = dict(path=early_convoy, commit=winter_commit, sha256=sha256(data))
    to_json(summary/'sources'/'historical-evidence.json', pinned)
    prior_terminal_proof(root, summary, winter_commit)


def score_docs(root, summary, data, fixed, south, performance, technical, source):
    folder = summary/'docs'
    folder.mkdir(parents=True, exist_ok=True)
    for item in (TOOL_ROOT/'docs/transport-coordination-v3041').glob('*.md'):
        content = item.read_text(encoding='utf-8').replace('(baseline.json)', '(../sources/baseline.json)')
        (folder/item.name).write_text(content, encoding='utf-8')
    scores = table(data/'scenario-scores.csv')
    reference_tables(root, summary, scores)
    manifest = json.loads((data/'simulation-manifest.json').read_text())
    warnings = table(data/'balance-alerts.csv') if (data/'balance-alerts.csv').exists() else []
    expected = dict(quick=18, five=24, long=8, holdout=4)
    counts = Counter(row['wave'] for row in scores)

    def overview(wave):
        rows = [r for r in scores if r['wave'] == wave]
        return table_text(('剧本', '种子', '策略', '分组', '月数', '缺粮城旬', '累计缺粮', '冬季及时率 %',
            '每本命令书净到粮'), ([r[k] for k in ('scenario', 'seed', 'strategy', 'variant', 'full_months',
                           'unpaid_city_turns', 'rations_missing', 'timely_grain_rate', 'net_per_book')] for r in rows))

    document(folder/'baseline-and-scope.md', '基准与范围',
        f'运输引擎验收源码为 `{source}`。剧本、地图和背景规则的哈希与开关记录在 [基准文件](../sources/baseline.json)。',
        '[V3.0.3.1 验收](https://github.com/kai987/Three-Kingdoms2-King-mainland/tree/codex/v3031-validation-archives/validation/v3031/summary) · [V3.0.4 原型](https://github.com/kai987/Three-Kingdoms2-King-mainland/tree/codex/v304-prototype-validation-archives/validation/v304-prototype/summary) · [V2.3.1 验收](https://github.com/kai987/Three-Kingdoms2-King-mainland/tree/codex/winter-agriculture-v231-validation-archives/validation/v231/summary)')
    document(folder/'existing-ai-call-chain.md', '原有 AI 运输入口',
        '城市首次内政会使用本地缺粮恢复、普通调粮、盟友援助、战略粮仓和区域采购。在城市循环中，前线、终局和行军接驳点会各自筹粮。委任结束时还会使用危险运队接济、前线接济及政策运队，商业贸易最后运行。',
        '这些入口共用命令书、来源余粮、押运人员和在途运队位置。实际顺序及接管边界见 [回合结算](ai-turn-integration.md)。')
    topics = {
        'unified-demand-model': ('统一需求', '城市缺口使用城池 ID，军队与运队各使用自己的实际队伍 ID。需求段保留首次旬和原始期限。进度用发运链接和到货凭证追踪。'),
        'demand-deduplication': ('需求去重', '普通调粮、采购与粮仓读取同一城市九旬缺口。一笔可靠到货按实际预计日期进入一次余额计算。季节风险及合法未发运承诺在条件列单独列示。'),
        'priority-rules': ('优先级规则', '优先检验紧急程度、可用时间窗和原始期限前的有效到货。效率组比较单位命令书、押运占用和往返消耗，并为只能使用单个来源的紧急目标保留候选。'),
        'candidate-generation': ('候选生成', '路线、返程、押运资格、仓库、市场及条款使用现有报价服务。报价按势力和阶段共享路线。发运后重建动态资源与军粮承诺。'),
        'faction-command-budget': ('势力命令书', '出征订单的到期命令从择机用粮任务的可用预算中预留。紧急调拨使用剩余真实命令。跨城采购成功消耗两笔操作，已购未运只记录实际完成的操作。'),
        'officer-and-clerk-allocation': ('武将与地方文吏', '使用同一名册及任职、健康、行动、军令和冷却检查。占用期按实际终止和人员可重新使用的日期计算。武将、文吏和押运士兵分别记账。'),
        'origin-slot-coordination': ('运输位置', 'D0 使用旧上限，D2 同来源最多两支活动运队，每旬至多一次发运。返程占用持续至合法结算。'),
        'small-load-economics': ('小额长途运输', '效率组按已有经济装载参考与口粮成本筛选可延后的货运。紧急需求仍可使用小额合法报价。统计以初始货粮低于 1,000 且去程不少于 20 日标记小额长途样本。'),
        'seasonal-forecast-integration': ('季节预报联动', '严格期限候选同时检查普通与保守季节时间窗。原引擎报价、实际行军和返程粮袋负责最终结算。统计同时保留预估净到货及实际回执。'),
        'transactional-dispatch': ('真实发运事务', '行动以现有命令入口扣除资源。市场买入后发运失败时，实际成交库存留在来源城。中转货权在发运条件变化时按原批次恢复。'),
        'military-demand-funnel': ('真实军粮能力漏斗', 'L0–L6 记录已观测资源或已证实的完整报价依赖。L7 表示存在原期限前的报价，L8 表示实发或即时购粮，L9 对应实际及时收粮。缺少直接观察的中间指标保留空值。'),
        'save-compatibility': ('存档兼容', '版本字段属于战役自身。同旬完成标记和供粮目标随正常及紧凑存档保存。关闭时旧存档沿用原规则。专项回归涵盖 Python 与 Rust 的交叉载入和续跑。'),
    }
    for slug, (title, paragraph) in topics.items():
        document(folder/f'{slug}.md', title, paragraph, '[回合入口和序列](ai-turn-integration.md)')
    document(folder/'ablation-results.md', '快速消融', overview('quick'),
             '[相同剧本种子配对](../data/pairwise.csv)')
    document(folder/'long-term-balance-results.md', '五年与二十年观战', overview('five'), overview('long'),
             f'共记录 {len(warnings)} 项警戒线超标。逐项保留真实缺粮、及时率和回合 CPU 警戒。'
             '实际分子和分母见 [观战总表](../data/scenario-scores.csv)。与已发布的 V2.3.1 F4 对照见 '
             '[历史 F4 宏观基准](../checks/historical-f4-macro-verification.csv) · '
             '[期末实际状态与随机数](../checks/historical-f4-terminal-verification.json)')
    document(folder/'holdout-results.md', '冻结候选的保留种子', overview('holdout'),
             '2041–2044 使用已经发布的历史数据作为参照，2045 与 2046 为本轮保留种子。'
             ' [本轮运行清单](../data/simulation-manifest.json) · [历史参照](../sources/prior-v231-scenario-scores.csv)')
    shadow = (data/'baseline-verification.csv')
    shadow_rows = table(shadow) if shadow.exists() else []
    document(folder/'shadow-mode-results.md', '影子调度',
        table_text(('剧本', '种子', '期末存档', '随机数', '三张统计表'),
                   ([r[k] for k in ('scenario', 'seed', 'terminal_checksum', 'rng', 'table_sha256')]
                    for r in shadow_rows)),
        '同一来源城、同一旬发生的旧调度与影子推荐是已观察到的竞争。要确认旧任务实际阻止了推荐，需要另核对真实空位、其余来源和期限。')
    if fixed:
        delivery = defaultdict(Counter)
        for r in fixed:
            if r['l5_actual_reception'] != 'null':
                net = int(r['l5_actual_reception'])
                count = delivery[r['group']]
                gap = int(r['first_uncovered_grain'])
                count.update(cases=1, received=int(net>0), grain=net,
                    covered=net>=gap, credited=min(gap, net),
                    opening_quote_no_reception=bool(int(r['l4_estimated_net_upper_bound'])) and net==0,
                    books=int(r.get('books_spent', 0)), incomplete=int(r.get('staff_period_incomplete', 0)),
                    officer_days=int(r.get('measured_officer_days', 0)), clerk_days=int(r.get('measured_clerk_days', 0)))
        returning = defaultdict(Counter)
        path = summary/'data'/'returning-slot-replay.csv'
        if path.is_file():
            for row in table(path):
                shipments = json.loads(row['actual_shipments'])
                returning[row['group']].update(samples=1, with_delivery=bool(shipments),
                    with_offer=bool(json.loads(row['timely_quotes'])))
        accounted = 'books_spent' in fixed[0]
        document(folder/'fixed-demand-replay.md', '89 个目标与 23 个返程案例',
            table_text(('分组', '回放数', '期限前收粮目标', '覆盖首次缺口', '实收粮', '首次缺口获粮',
                        '开局可估算却未收粮'),
                       ((g, *(v[k] for k in ('cases', 'received', 'covered', 'grain', 'credited',
                                             'opening_quote_no_reception')))
                        for g, v in sorted(delivery.items()))),
            table_text(('分组', '受检返程位置', '原始期限前有报价', '观察到实际到货'),
                ((g, v['samples'], v['with_offer'], v['with_delivery']) for g, v in sorted(returning.items()))),
            table_text(('分组', '已花命令书', '已核算武将日', '已核算文吏日', '期末占用未完结样本'),
                ((g, v['books'], v['officer_days'], v['clerk_days'], v['incomplete'])
                 for g, v in sorted(delivery.items()) if accounted)),
            '截止日按原观测口径。期限当旬的卸粮晚于评估扣粮，因此只累计该旬之前的实际新发运到货。'
            '「开局可估算却未收粮」是冻结检查点上有估算净载荷的目标数，同一来源仍可能被多个目标竞争。'
            '可观察到实际结束和冷却的押运周期与期末仍在途样本分别记录。',
            '[到货记录](../data/fixed-demand-replay.csv) · [返程位置案例](../data/returning-slot-replay.csv)')
    if south:
        document(folder/'southern-basin-replay.md', '南方缺粮检查点',
            table_text(('城市', '分组', '原 F4 缺粮', '九旬实缺', '差额', '原始状态合法来源', '最快去程 日'),
                       ([r[k] for k in ('city', 'group', 'previous_F4_missing', 'missing', 'delta', 'legal_sources',
                                        'minimum_eta')]
                        for r in south)),
            '庐陵的 T3 第 72 旬收到豫章发运的 19,011 粮。宜都的 T5 第 192 旬收到南郡发运的 1,464 粮。'
            '巴东的开局最快合法去程为 45 日，建安开局没有合法来源。',
            '巴西的 T3 在第 269、270 旬分别购入 1,510 和 1,123 粮，两笔随后被行军部队从同一官仓领走。'
            '这两个观察到的库存变化说明过境口粮会与驻城口粮竞争。完整缺口同时受后续战局影响。',
            '检查点日期、库存、所属与输入哈希见 [逐城数据](../data/city-shortage-checkpoint-replay.csv)。'
            '相关实际凭证位于分包中的 replays/south/southern-basin-replay.json。')
    if performance:
        document(folder/'performance-results.md', '固定状态性能',
            table_text(('检查点', '分组', '观测', '重复', '回合 CPU p50', '回合 CPU p95', '路线批查询'),
                       ([r[k] for k in ('label', 'group', 'observation', 'repeats', 'full_turn_cpu_p50',
                                        'full_turn_cpu_p95', 'route_queries')] for r in performance)),
            '[逐次记录](../data/scheduler-performance-profile.csv)')
    document(folder/'validation-results.md', '技术验收',
        table_text(('检查', '退出码', '日志所示测试数', '源码', '日志字节数'),
                   ((name, proof['exit_code'], proof.get('reported_tests'), proof['source'][:8], proof['log_bytes'])
                    for name, proof in sorted(technical.items()))),
        '旧尝试及失败后的重试保留独立记录。检查证据与最终发布候选的取值分别参见 [验收清单](../checks/technical-checks.json)。')
    document(folder/'known-issues.md', '已知限制与缺项',
        '自动生成的持有者和运输人员只在游戏名册允许时参与。首版有界候选搜索保留最紧急的真实需求，并可能延后排在边界之外的任务。',
        '无充分证据的阻塞和人日分项留空，报价和真实回执分开。期末未归队的人员周期为右删失，未按理论回程天数填补。',
        '观战逐组样本数量及是否跑满月份见 [运行清单](../data/simulation-manifest.json)。控制表不补造缺失观战。')
    complete = all(counts[name] >= n for name, n in expected.items())
    document(folder/'v3042-readiness.md', 'V3.0.4.2 准入复核',
        f'快速、五年、二十年与保留种子完成数分别为 {counts["quick"]}、{counts["five"]}、{counts["long"]}、{counts["holdout"]}。'
        + ('矩阵样本数已齐备。' if complete else '验收矩阵仍有缺项。'),
        f'警戒线超标记录共 {len(warnings)} 项。'
        + ('现有证据不足以默认启用 3041。' if warnings or not complete else '是否默认启用还需逐项核对验收目标。'),
        '在缺少可执行来源或路线过长的案例中，可继续单独验证港口和渡口接驳能否改变真实到货。')
    document(folder/'data-dictionary.md', '观测数据字典',
        'requested_grain 是真实军粮申请。timely_received_grain、timely_at_original_deadline 和 unresolved_grain 分别为当前期限前、首次期限前实收及未满足粮。',
        'actual_received_grain 是实体运队实际交割量。officer_occupation_days 与 clerk_occupation_days 按调离至任务终止及释放的已观测时间核算。net_per_book 以实际发运操作计费，区域采购加入市场操作。',
        'donor_stock 是势力他城实际库存。L2–L6 的空值表示证据不足。零值在观测到实际无交易或无货物时保留。初始没启用的机制按规则版本解释。',
        'transport-demand-episodes 每个需求段只出现一次。及时报价取该段中观察到的最大单笔完整报价。'
        '同一来源提出的多笔候选仍需分配共同库存。实际到货按需求段和运队凭证入账。',
        'source-safety-after-dispatch 记录发运当旬及后续八旬可观察到的减粮结算。记录缺粮表示发运后发生过缺粮，因果还需核对该城后续事件。',
        '运输时间使用每旬十天和既有结算先后次序。货粮、独立押运口粮、金与预备兵使用引擎的实际单位。')
    decision_summary(folder/'acceptance-findings.md', scores, fixed, south, warnings, performance, data)
    to_json(summary/'checks'/'matrix-status.json', dict(expected=expected, scored=dict(counts),
        complete=complete, warning_count=len(warnings), failures=[r for r in manifest if r['failure']]))


def pack(destination, category, root, paths):
    archives, chunk, size = [], [], 0

    def seal(rows):
        index = len(archives)+1
        name = 'v3041-summary.zip' if category == 'summary' and index == 1 else f'v3041-{category}-{index:02}.zip'
        path = destination/name
        with ZipFile(path, 'w', compression=ZIP_DEFLATED, compresslevel=3) as archive:
            hashes = []
            for source in rows:
                relative = source.relative_to(root).as_posix()
                archive.write(source, relative)
                hashes.append(dict(file=relative, **check_file(source)))
            archive.writestr('FILE-MANIFEST.json', json.dumps(hashes, indent=2)+'\n')
        with ZipFile(path) as archive:
            assert archive.testzip() is None and len(archive.namelist()) == len(rows)+1
        if path.stat().st_size > 100_000_000:
            raise ValueError(f'Archive exceeds 100 MB: {name}')
        archives.append(dict(name=name, **check_file(path), files=hashes))

    for path in sorted(paths):
        length = path.stat().st_size
        if chunk and size+length > MAX_PACKAGE:
            seal(chunk)
            chunk, size = [], 0
        chunk.append(path)
        size += length
    if chunk:
        seal(chunk)
    return archives


def fixed_accounting_proof(root, summary):
    bag = root/'replays/fixed-accounted'
    if not (bag/'fixed-capacity-replay-traces.json').is_file():
        return False
    merged = summary/'data'/'fixed-demand-replay.csv'
    completed = 'transport-capability-funnel.csv'
    key_fields = ('checkpoint_sha256', 'group', 'owner', 'target')
    expected = {tuple(row[key] for key in key_fields):row for row in table(merged)}
    observed = {tuple(row[key] for key in key_fields):row for row in table(bag/completed)}
    assert expected.keys() == observed.keys()
    for key, actual in observed.items():
        for field in ('deadline_turn', 'l5_replay_end_turn', 'l5_actual_reception', 'l5_actual_receipts'):
            assert expected[key][field] == actual[field], (key, field)
    state = {}
    traces = 'fixed-capacity-replay-traces.json'
    for phase in ('fixed', 'fixed-d2-control', 'fixed-accounted'):
        path = root/'replays'/phase/traces
        for trace in json.loads(path.read_text(encoding='utf-8')):
            key = trace['fixture_sha256'], trace['group']
            checks = (trace['forecast_state_sha256'], [(r['turn'], r['rng'], r['sha256']) for r in trace['checks']])
            if key in state:
                assert state[key] == checks, key
            else:
                state[key] = checks
    assert len(state) == 25
    to_json(summary/'checks'/'fixed-accounting-consistency.json',
        dict(checkpoint_pairs=len(state), same_domain_and_rng=True, matched_targets=len(observed),
             observation='prior fixed replay compared with additional ration and transport accounting'))
    shutil.copy2(bag/completed, merged)
    return True


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('run_root', type=Path)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    root, archive = args.run_root, args.archive
    data, technical = root/'report', root/'technical'
    summary = archive/'summary'
    for suffix in ('data', 'checks', 'docs', 'sources'):
        (summary/suffix).mkdir(parents=True, exist_ok=True)
    for name in DIRECT:
        source = data/name
        if source.is_file():
            shutil.copy2(source, summary/'data'/name)
    fixed, south, performance = [], [], []
    for phase, old, new, target in (
            ('south', 'city-shortage-checkpoint-replay.csv', 'city-shortage-checkpoint-replay.csv', south),
            ('fixed', 'transport-capability-funnel.csv', 'fixed-demand-replay.csv', fixed),
            ('fixed', 'capacity-counterfactual.csv', 'returning-slot-replay.csv', []),
            ('performance', 'scheduler-performance-profile.csv', 'scheduler-performance-profile.csv', performance)):
        source = root/'replays'/phase/old
        if not source.exists():
            continue
        shutil.copy2(source, summary/'data'/new)
        target.extend(table(source))
    for old, new in (('transport-capability-funnel.csv', 'fixed-demand-replay.csv'),
                     ('capacity-counterfactual.csv', 'returning-slot-replay.csv')):
        d2 = root/'replays/fixed-d2-control'/old
        merged = summary/'data'/new
        if d2.is_file() and merged.is_file():
            to_csv(merged, [*table(merged), *table(d2)])
    merged_fixed = summary/'data'/'fixed-demand-replay.csv'
    if merged_fixed.is_file():
        fixed_accounting_proof(root, summary)
        fixed = table(merged_fixed)
    checks = {}
    for item in (technical/'checks').glob('*.json'):
        proof = json.loads(item.read_text())
        log = technical/proof['log']
        if log.exists():
            assert check_file(log) == dict(bytes=proof['log_bytes'], sha256=proof['log_sha256']), log
            content = log.read_text(errors='replace')
            counts = re.findall(r'(?:Ran |running |Running )(\d+) tests?\b|^# tests (\d+)\s*$', content, re.M)
            if counts:
                proof['reported_tests'] = sum(int(a or b) for a,b in counts)
        checks[item.stem] = proof
    to_json(summary/'checks'/'technical-checks.json', checks)
    for name in ('browser-chain-input-equivalence.json', 'final-source-identity.json'):
        evidence = technical/name
        if evidence.is_file():
            shutil.copy2(evidence, summary/'checks'/name)
    documentation = TOOL_ROOT/'docs/transport-coordination-v3041'
    shutil.copy2(documentation/'baseline.json', summary/'sources'/'baseline.json')
    for name in ('v3041_campaigns.py', 'v3041_replays.py', 'v3041_report.py', 'v3041_verify_archive.py'):
        shutil.copy2(Path(__file__).with_name(name), summary/'sources'/name)
    if (root/'reference/south/checkpoint-sources.json').is_file():
        shutil.copy2(root/'reference/south/checkpoint-sources.json', summary/'sources')
    for phase, names in (('fixed', ('fixed-replay-inputs.json', 'fixed-capacity-replay-traces.json')),
                         ('performance', ('scheduler-performance-profile.json',))):
        for name in names:
            item = root/'replays'/phase/name
            if item.is_file():
                shutil.copy2(item, summary/'checks'/name)
    historical_cases = {}
    for phase in ('historical', 'historical-legacy', 'historical-forty', 'historical-more', 'historical-assets'):
        item = root/'replays'/phase/'historical-convoy-safety.json'
        if item.is_file():
            for row in json.loads(item.read_text())['results']:
                key = row['convoy'], row['group'], row['checkpoint_sha256']
                earlier = historical_cases.get(key)
                if earlier is None or len(row['snapshots']) >= len(earlier['snapshots']):
                    historical_cases[key] = row
    historical = list(historical_cases.values())
    if historical:
        to_json(summary/'checks'/'historical-convoy-safety.json', historical)
        rows = []
        for case in historical:
            snapshots = case['snapshots']
            terminal = next((entry['row'] for entry in case['receipts'] if entry['event'] == 'terminal'), None)
            assets = next((entry['row']['cargo'] for entry in case['receipts']
                           if entry['event'] == 'returned_assets'), None)
            last = snapshots[-1]['convoy']
            rows.append((case['convoy'], case['group'], snapshots[0]['turn'], snapshots[-1]['turn'],
                         terminal['outcome'] if terminal else '仍在途' if last else '未观察到终止事件',
                         terminal['hunger_losses'] if terminal else last['hunger'] if last else None,
                         terminal['troops_received'] if terminal else last['troops'] if last else None,
                         assets['gold'] if assets else last.get('aboard_resources', {}).get('gold') if last else None))
        document(summary/'docs'/'historical-transport-safety.md', '历史运队复放',
            table_text(('运队', '分组', '原始旬', '末旬', '真实状态', '断粮损失', '在队或收容兵士', '在队或回库金'), rows),
            '开局保存原归属、在途口粮和路线。战局分叉会改变路线与归属。终止凭证以原游戏结算为准。',
            '[真实终止凭证及原始输入哈希](../checks/historical-convoy-safety.json) · '
            '[历史运队证据索引](../sources/historical-transport-replay-index.csv) · '
            '[上版广陵第 39 旬的原记录](../sources/prior-v231-historical-convoy-2.json)')
    source = (technical/'frozen-source.txt').read_text().strip()
    score_docs(root, summary, data, fixed, south, performance, checks, source)
    document(summary/'sources'/'reproduce.md', '复现与校验',
        f'游戏引擎验收提交为 `{source}`。矩阵使用 [真实命令与配置](../data/simulation-manifest.json) 中的剧本、种子、规则版本和观察月数。',
        '从源码运行 `tools/economy-balance/v3041_campaigns.py` 重放观战。配对输入保持相同种子、剧本、策略及月份。使用 `v3041_replays.py` 读入原始存档和上一轮数据，原始输入及引用见检查清单。',
        '将对应观战 ZIP 解压到同一个目录后，可使用 `v3041_report.py` 重新汇总 CSV。'
        + '在已有汇总目录中运行 `python3 -B summary/sources/v3041_verify_archive.py .` 检查 ZIP、文件 SHA-256、军粮比率及期末经济总数。')
    document(archive/'README.md', 'V3.0.4.1 运输统筹验收',
        '[设计与运行方法](summary/docs/README.md) · [快速消融](summary/docs/ablation-results.md) · '
        '[长期观战](summary/docs/long-term-balance-results.md) · [验收及已知限制](summary/docs/validation-results.md)',
        '[观战清单](summary/data/simulation-manifest.json) · [警戒线记录](summary/data/balance-alerts.csv) · '
        '[分包目录](archives/archive-index.json) · [压缩包 SHA-256](archives/SHA256SUMS.txt)')
    summary_members = sorted(p for p in summary.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.txt')
    checksum = summary/'SHA256SUMS.txt'
    checksum.write_text(''.join(f"{check_file(p)['sha256']}  {p.relative_to(summary).as_posix()}\n"
                                for p in summary_members), encoding='utf-8')
    destination = archive/'archives'
    destination.mkdir(parents=True, exist_ok=True)
    files = pack(destination, 'summary', archive, (*summary_members, checksum))
    for category, base in (('technical', 'technical'), ('fixed-demand-replay', 'replays'),
                           ('detailed-ledgers', 'report')):
        paths = [p for p in (root/base).rglob('*') if p.is_file()]
        files.extend(pack(destination, category, root, paths))
    waves = defaultdict(list)
    for path in (root/'observed').rglob('*'):
        if path.is_file():
            variant, _, wave, *_ = path.relative_to(root/'observed').parts
            category = ('shadow-replay' if variant == 'T1' else
                        {'five':'five-year', 'long':'twenty-year', 'smoke':'compatibility-smoke'}.get(wave, wave))
            waves[category].append(path)
    for wave, items in sorted(waves.items()):
        files.extend(pack(destination, wave, root, items))
    to_json(destination/'archive-index.json', dict(engine_source=source, archives=files))
    manifest = sorted(p for p in destination.iterdir() if p.is_file() and p.name != 'SHA256SUMS.txt')
    (destination/'SHA256SUMS.txt').write_text(''.join(f"{check_file(p)['sha256']}  {p.name}\n" for p in manifest))
    print(json.dumps(dict(archives=len(files), summary_files=len(summary_members)+1,
                          archive_bytes=sum(row['bytes'] for row in files)), ensure_ascii=False))


if __name__ == '__main__':
    main()
