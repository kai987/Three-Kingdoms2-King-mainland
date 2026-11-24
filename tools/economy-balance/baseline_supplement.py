"""Check the 16 targeted A runs against the original validation ZIP and package them."""
from argparse import ArgumentParser
from collections import Counter
import csv
import io
import json
import platform
from pathlib import Path
import shutil
import subprocess
import zipfile

from common import TOOL_ROOT, sha256, to_csv, to_json
from observe import SCENARIOS, WEIGHTED_ONLY
from observer_telemetry import FILES

BASELINE = '20c6d3cd8135a48cd3c4b18d5f54489fdc0dbc0b'
OBSERVED = Path('data/observed')
RUNS = ((2026, 240, '184-02'), (2026, 240, '208-10'),
        *((seed, 60, scenario) for seed in (2027, 2028) for scenario in SCENARIOS))
KEYS = {'monthly.csv': ('elapsed_turns',), 'factions.csv': ('elapsed_turns', 'faction'),
        'cities.csv': ('elapsed_turns', 'city')}
METADATA = ('scenario', 'seed', 'requested_months', 'completed_turns', 'full_months',
            'outcome', 'catalog_sha256', 'last_date', 'failure')
CSV_FILES = (*KEYS, 'capture-recovery.csv')
TOOLS = ('observe.py', 'common.py', 'observer_telemetry.py', 'observer_hooks.py', 'observer-config.json',
         'logistics_observer_exports.py', 'verify_observer.py', 'baseline_supplement.py')
EMPTY_PATCH = sha256(b'')


def csv_data(raw):
    handle = io.StringIO(raw.decode('utf-8'), newline='')
    reader = csv.DictReader(handle)
    columns = tuple(reader.fieldnames or ())
    if not columns or len(set(columns)) != len(columns):
        raise ValueError('Empty or duplicate CSV headers')
    rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError('Malformed CSV record')
    return columns, rows


def index(rows, fields):
    result = {}
    for row in rows:
        key = tuple(row[field] for field in fields)
        if key in result:
            raise ValueError(f'Duplicate key {key}')
        result[key] = row
    return result


def compare_csv(name, before, after):
    old_fields, old_rows = before
    _, new_rows = after
    if name == 'capture-recovery.csv':
        old = Counter(tuple(row[col] for col in old_fields) for row in old_rows)
        new = Counter(tuple(row.get(col) for col in old_fields) for row in new_rows)
        missing, extra = sum((old - new).values()), sum((new - old).values())
        fields = {'all_fields_as_multiset': dict(checked=len(old_rows) * len(old_fields),
                                                mismatched=missing+extra, examples=[])}
        return fields, missing, extra
    old, new = index(old_rows, KEYS[name]), index(new_rows, KEYS[name])
    shared = sorted(old.keys() & new.keys())
    fields = {}
    for col in old_fields:
        bad = []
        differences = 0
        for key in shared:
            actual = new[key].get(col)
            expected = old[key][col]
            if actual != expected:
                differences += 1
                if len(bad) < 3:
                    bad.append(dict(key=key, original=expected, replayed=actual))
        fields[col] = dict(checked=len(shared), mismatched=differences, examples=bad)
    return fields, len(old.keys() - new.keys()), len(new.keys() - old.keys())


def raw_count(value):
    if value in ('true', 'false'):
        # A single-entry Counter.update can preserve a Python bool. The
        # underlying one or zero is verified against individual quote receipts.
        return int(value == 'true')
    return int(value)


def normalize_quote_counts(path):
    columns, rows = csv_data(path.read_bytes())
    if not any(row[key] in ('true', 'false') for row in rows for key in ('passed', 'blocked')):
        return
    for row in rows:
        for key in ('passed', 'blocked'):
            row[key] = raw_count(row[key])
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def review_convoy_returns(path):
    """Resolve earlier mission cancellation using the recorded return receipts."""
    route_path = path/'route-changes.csv'
    columns, changes = csv_data(route_path.read_bytes())
    _, convoys = csv_data((path/'convoys.csv').read_bytes())
    first_returns = {}
    for row in convoys:
        if row['stage'] == 'return_ordered':
            first_returns.setdefault(row['convoy_id'], row)
    review = []
    for row in changes:
        if row['unit_kind'] != 'convoy' or row['status'] not in (
            'aborted_for_supply', 'return_interrupted_for_supply'
        ):
            continue
        first = first_returns.get(row['unit_id'])
        if (first is None or int(first['turn']) > int(row['turn'])
                or first['reason'] in ('retreat', 'shortage', 'ration_shortage')):
            continue
        row['status'] = 'return_interrupted_for_supply'
        review.append(dict(convoy_id=row['unit_id'], first_return_turn=first['turn'],
                           first_return_reason=first['reason'], supply_failure_turn=row['turn'],
                           result=row['status']))
    if review:
        with route_path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator='\n')
            writer.writeheader()
            writer.writerows(changes)
    return review


def verify_flows(path, run, world):
    tables = {}
    for name in FILES:
        columns, rows = csv_data((path / (name + '.csv')).read_bytes())
        if columns != ('turn', 'year', 'month', 'day', *FILES[name].split()):
            raise ValueError(f'{path}: unexpected detail schema for {name}')
        if len(rows) != run['telemetry']['rows'][name]:
            raise ValueError(f'{path}: row count differs for {name}')
        tables[name] = rows
    last = world[-1]
    shortages, battles = tables['shortages'], tables['battles']
    convoys = tables['convoys']
    departed = [row for row in convoys if row['stage'] == 'departed']
    delivered = [row for row in convoys if row['stage'] == 'delivered']
    request_counts = Counter(row['result'] for row in tables['supply-requests'])
    columns = {
        'unpaid_city_turns': len(shortages),
        'rations_missing': sum(int(row['missing']) for row in shortages),
        'battles': len(battles),
        'battle_troops_lost': sum(int(row['deaths']) for row in battles),
        'battle_days': sum(int(row['days']) for row in battles if row['days'] != 'null'),
        'battle_grain_rations': sum(int(row['rations']) for row in battles if row['rations'] != 'null'),
        'battle_grain_burned': sum(int(row['grain_burned']) for row in battles if row['grain_burned'] != 'null'),
        'convoy_dispatched': len(departed),
        'convoy_grain_sent': sum(int(row['grain_loaded']) for row in departed),
        'convoy_arrived': len(delivered),
        'convoy_grain_arrived': sum(int(row['actual_grain']) for row in delivered),
        'granted_aid': request_counts['delivered_immediately'],
        'requested_aid_refused': request_counts['refused'],
        'march_hunger_losses': sum(int(row['count']) for row in tables['troop-flows']
                                  if row['kind'] == 'march_hunger_deaths'),
        'convoy_hunger_losses': sum(int(row['count']) for row in tables['troop-flows']
                                   if row['kind'] == 'convoy_hunger_deaths'),
    }
    differences = {name: [int(last[name]), value] for name, value in columns.items() if int(last[name]) != value}
    if differences:
        raise ValueError(f'{path}: detail-to-monthly differences {differences}')
    if any(int(row['required']) - int(row['paid']) != int(row['missing']) or int(row['missing']) <= 0
           for row in shortages):
        raise ValueError(f'{path}: invalid shortage equation')
    for row in shortages:
        stocks = json.loads(row['other_city_stock'])
        if row['city'] in stocks or sum(stocks.values()) != int(row['other_stock']):
            raise ValueError(f'{path}: invalid donor stock reconciliations')
        surplus, legal = json.loads(row['reserve_surplus']), json.loads(row['legal_route_surplus'])
        if not (0 <= legal['6'] <= legal['3'] <= legal['1'] <= surplus['1']
                and 0 <= surplus['6'] <= surplus['3'] <= surplus['1']
                and all(legal[key] <= surplus[key] for key in legal)):
            raise ValueError(f'{path}: invalid reserve bands')
    departed_ids = {int(row['convoy_id']) for row in departed}
    for row in tables['supply-requests']:
        if not set(json.loads(row['convoy_ids'])) <= departed_ids:
            raise ValueError(f'{path}: request references a convoy with no dispatch')
    checks = Counter((row['plan_key'], row['outcome']) for row in tables['war-quotes'])
    for row in tables['war-quote-groups']:
        passed = checks.pop((row['plan_key'], 'passed'), 0)
        blocked = checks.pop((row['plan_key'], 'blocked'), 0)
        values = (raw_count(row['passed']), raw_count(row['blocked']), int(row['evaluations']))
        if values != (passed, blocked, passed+blocked):
            raise ValueError(f'{path}: incomplete quote aggregation')
    if checks:
        raise ValueError(f'{path}: ungrouped war quote')
    plan_ids = {row['plan_id'] for row in tables['war-plans'] if row['stage'] == 'assembled'}
    thresholds = run['telemetry']['config']['action_capacity']
    for row in tables['action-capacity']:
        streak = int(row['no_action_streak'])
        if ((row['qualifies'] == 'true') != (streak >= thresholds['report_streak_at'])
                or bool(streak) != (row['status'] == 'blocked')):
            raise ValueError(f'{path}: inconsistent action classification')
    return dict(shortage_events=len(shortages), grain_missing=columns['rations_missing'],
                shipments=len(departed), delivered=len(delivered), supply_requests=sum(request_counts.values()),
                battles=len(battles), war_quote_evaluations=len(tables['war-quotes']),
                assembled_war_plans=len(plan_ids), rerouted=sum(row['status']=='rerouted' for row in tables['route-changes']),
                aborted_for_supply=sum(row['status']=='aborted_for_supply' for row in tables['route-changes']),
                return_interrupted_for_supply=sum(row['status']=='return_interrupted_for_supply'
                                                  for row in tables['route-changes']))


def add_reference_file(original, manifest, key, proofs):
    raw = original.read(key)
    actual = dict(sha256=sha256(raw), bytes=len(raw))
    if actual != manifest['distributed_files'][key]:
        raise ValueError(f'Original verification manifest hash mismatch: {key}')
    proofs[key] = actual
    return raw


def compare_run(original, original_manifest, root, seed, months, scenario, proofs):
    relative = OBSERVED / 'A' / str(seed) / str(months) / scenario
    path = root / relative
    old = json.loads(add_reference_file(original, original_manifest, f'{relative}/run.json', proofs))
    run = json.loads((path / 'run.json').read_bytes())
    if run['head'] != BASELINE or run['worktree_diff_sha256'] != EMPTY_PATCH:
        raise ValueError(f'{relative}: unexpected engine revision or runtime edits')
    if (run['outcome'] != 'complete' or run['failure'] is not None or run['completed_turns'] != months*3
            or run['backend']['engine'] != 'rust' or run['rule_versions'] != {'economy':2,'market':2,'logistics':1}):
        raise ValueError(f'{relative}: replay failed or used the wrong engine configuration')
    run_diff = {key: [old[key], run[key]] for key in METADATA if old[key] != run[key]}
    files, coverage = {}, []
    for filename in CSV_FILES:
        before = csv_data(add_reference_file(original, original_manifest, f'{relative}/{filename}', proofs))
        after = csv_data((path / filename).read_bytes())
        fields, missing, additional = compare_csv(filename, before, after)
        files[filename] = dict(old_rows=len(before[1]), replayed_rows=len(after[1]),
                               keys_missing=missing, keys_added=additional, fields=fields)
        if filename not in KEYS:
            continue
        other = relative.as_posix().replace('observed/A/','observed/D/',1)
        d_columns = csv_data(add_reference_file(original, original_manifest, f'{other}/{filename}', proofs))[0]
        if set(d_columns) - set(after[0]):
            raise ValueError(f'{relative}: missing D-side columns in {filename}: {set(d_columns) - set(after[0])}')
        for col in after[0]:
            counts = Counter(row[col] for row in after[1] if row[col] in ('not_applicable', 'not_collected', 'null'))
            if col in WEIGHTED_ONLY and counts['not_applicable'] != len(after[1]):
                raise ValueError(f'{relative}: invented measurements for inapplicable field {col}')
            coverage.append(dict(seed=seed, requested_months=months, scenario=scenario, file=filename, field=col,
                original='observed' if col in before[0] else 'not_collected',
                shared_with_original_D=col in d_columns,
                measured=len(after[1])-sum(counts.values()), not_applicable=counts['not_applicable'],
                not_collected=counts['not_collected'], contextual_null=counts['null']))
        if filename == 'monthly.csv':
            world = after[1]
    review = review_convoy_returns(path)
    flow = verify_flows(path, run, world)
    normalize_quote_counts(path/'war-quote-groups.csv')
    run['parameters'].update(lifespan='historical', march_core_backend='rust', python_hash_seed=0)
    run['original_run_sha256'] = proofs[f'{relative}/run.json']['sha256']
    run['original_run_field_differences'] = run_diff
    to_json(path/'run.json', run)
    return dict(seed=seed, requested_months=months, scenario=scenario, completed_turns=run['completed_turns'],
                metadata_differences=run_diff, files=files, flow=flow, convoy_return_review=review), coverage


def consistency_summary(path, results, parity):
    lines = ['# A 组重跑一致性报告', '',
             '原包未包含这 16 局可复原逐日耗粮和运输交割的流水。重跑使用原提交、原剧本、原种子、正常难度和历史寿命。',
             '按已保存数据逐项精确比对。月份和回合日期、城池归属、兵力、人口、金粮库存、战斗、配给和采购均在比对范围内。'
             '攻占恢复表按完整记录多重集比对。计时与后台缓存调用量属于运行元数据。',
             '', '| 种子 | 剧本 | 月数 | 旬数 | 月度行 | 势力行 | 城池行 | 攻占恢复行 | 比对字段值 | 键或值差异 |',
             '| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    checked = differences = 0
    for result in results:
        files = result['files']
        comparisons = sum(field['checked'] for row in files.values() for field in row['fields'].values())
        errors = (len(result['metadata_differences']) +
                  sum(row['keys_missing'] + row['keys_added'] +
                      (sum(field['mismatched'] for field in row['fields'].values())
                       if name != 'capture-recovery.csv' else 0) for name, row in files.items()))
        counts = ' | '.join(str(files[name]['old_rows']) for name in CSV_FILES)
        lines.append(f"| {result['seed']} | {result['scenario']} | {result['requested_months']} | "
                     f"{result['completed_turns']} | {counts} | {comparisons} | {errors} |")
        checked += comparisons
        differences += errors
    totals = {key: sum(item['flow'][key] for item in results) for key in results[0]['flow']}
    lines.extend(['', f'共核对 {checked:,} 个原表字段值。差异 {differences} 处。',
                  '每局分别校验了新增流水的缺粮、口粮、战斗、运输、盟援与月度合计。',
                  f"补充流水合计 {totals['shortage_events']:,} 次城池缺粮、{totals['shipments']:,} 次实际发运、"
                  f"{totals['delivered']:,} 次交付、{totals['battles']:,} 场战斗。",
                  f"{totals['aborted_for_supply']} 支运队因补给问题中止。另有 "
                  f"{totals['return_interrupted_for_supply']} 支已因其他原因返程的运队随后受断粮影响，"
                  '由原运单的最早返程回执区分。', '',
                  '## 只读旁路验证', ''])
    for proof in parity:
        lines.append(f"- {proof['group']} 组 {proof['scenario']}、种子 {proof['seed']}，启用和关闭观测后，"
                     f"全部 {proof['matched_state_hashes']} 份开局及逐旬紧凑存档校验值一致，包含 RNG 状态。")
    lines.extend(['', '种子 2026 已有的 7 局五年观战及原包其他组次沿用原包。', ''])
    path.write_text('\n'.join(lines), encoding='utf-8')
    return checked, differences


def file_proof(path):
    return dict(sha256=sha256(path.read_bytes()), bytes=path.stat().st_size)


def worktree(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args]).decode().strip()


def assemble(source, root, output, baseline_root):
    if source.resolve() == output.resolve():
        raise ValueError('The original archive must be preserved')
    actual = sorted(path.parent.relative_to(root).as_posix() for path in root.glob('data/observed/*/*/*/*/run.json'))
    expected = sorted((OBSERVED/'A'/str(seed)/str(months)/scenario).as_posix() for seed, months, scenario in RUNS)
    if expected != actual:
        raise ValueError(f'Run coverage differs. Missing {set(expected)-set(actual)}. Extra {set(actual)-set(expected)}.')
    if worktree(baseline_root, 'rev-parse', 'HEAD') != BASELINE:
        raise ValueError('Baseline checkout moved')
    parity = [json.loads((root/'checks'/f'read-only-{group}.json').read_bytes()) for group in ('A','D')]
    if (parity[0]['engine_commit'] != BASELINE or any(row['matched_state_hashes'] != row['completed_turns']+1
                                                   for row in parity)):
        raise ValueError('Parity check is incomplete')
    results, coverage, original_proofs = [], [], {}
    with zipfile.ZipFile(source) as original:
        original_manifest = json.loads(original.read('data/validation-manifest.json'))
        groups = json.loads(original.read('data/simulation-manifest.json'))['groups']
        if groups['A'] != BASELINE:
            raise ValueError('Incorrect reference archive')
        for entry in RUNS:
            proof, fields = compare_run(original, original_manifest, root, *entry, original_proofs)
            results.append(proof)
            coverage.extend(fields)
    to_csv(root/'checks'/'field-coverage.csv', coverage)
    review = [dict(seed=row['seed'], scenario=row['scenario'], **entry)
              for row in results for entry in row['convoy_return_review']]
    if review:
        to_csv(root/'checks'/'convoy-return-review.csv', review)
    to_json(root/'checks'/'baseline-consistency.json', results)
    checked, differences = consistency_summary(root/'checks'/'baseline-consistency.md', results, parity)
    if differences:
        raise ValueError(f'{differences} legacy differences. See {root / "checks/baseline-consistency.json"}')
    for name in ('data-dictionary.md', 'observer-v21.md', 'baseline-field-availability.md'):
        dest = root/'docs'/name
        dest.parent.mkdir(exist_ok=True)
        shutil.copyfile(TOOL_ROOT/'docs/logistics-v2'/name, dest)
    shutil.copyfile(TOOL_ROOT/'tools/economy-balance/observer-config.json', root/'observer-config.json')
    members = sorted(path for folder in ('data','docs','checks') for path in (root/folder).rglob('*') if path.is_file())
    members.append(root/'observer-config.json')
    manifest = dict(schema='tk2-logistics-baseline-supplement-v1', baseline_engine_commit=BASELINE,
        reference_D_commit=groups['D'], observer_repository_commit=worktree(TOOL_ROOT,'rev-parse','HEAD'),
        native_library=file_proof(baseline_root/'build/march-core'/(
            'libmarch_core.dylib' if platform.system()=='Darwin' else 'libmarch_core.so')),
        source_archive=dict(name=source.name, **file_proof(source)), original_members=original_proofs,
        python=platform.python_version(), platform=platform.platform(),
        observer_tools={name:file_proof(TOOL_ROOT/'tools/economy-balance'/name) for name in TOOLS},
        replay_configuration=dict(faction='observer', difficulty='normal', lifespan='historical', record_journal=False,
            runtime_backend='rust', python_hash_seed=0, strategic_turns_per_month=3, worker_counts={'2026':2,'2027':3,'2028':3}),
        runs=[dict(seed=row['seed'], requested_months=row['requested_months'], scenario=row['scenario'],
                   completed_turns=row['completed_turns'], observations=row['flow']) for row in results],
        old_cells_compared=checked, legacy_differences=differences,
        distributed_files={path.relative_to(root).as_posix():file_proof(path) for path in members})
    to_json(root/'manifest.json', manifest)
    members.append(root/'manifest.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    (root/'SHA256SUMS').write_text(''.join(f"{file_proof(path)['sha256']}  {path.relative_to(root).as_posix()}\n"
                                         for path in sorted(members)), encoding='utf-8')
    members.append(root/'SHA256SUMS')
    temporary = output.with_suffix('.partial.zip')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(members):
            archive.write(path, path.relative_to(root).as_posix())
    with zipfile.ZipFile(temporary) as archive:
        for record in archive.read('SHA256SUMS').decode().splitlines():
            expected_hash, name = record.split('  ', 1)
            if sha256(archive.read(name)) != expected_hash:
                raise ValueError(f'ZIP integrity check failed: {name}')
    temporary.replace(output)
    print(f'{len(results)} runs, {checked:,} original values, no differences. {output}')


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--replay', type=Path, required=True)
    parser.add_argument('--baseline-root', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args()
    assemble(args.original, args.replay, args.bundle, args.baseline_root)
