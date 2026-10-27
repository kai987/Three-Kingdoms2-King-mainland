#!/usr/bin/env python3
"""Check a frozen ruler-affiliation review and render its Japanese report.

The reference is an authored decision, never an output of this program.  This
tool reads compiled opening catalogues, checks the reviewed 67-person pool in
all 29 scenarios, and verifies cheap global identity/provenance/material
contracts.  It does not simulate commands, alter saves, fetch sources, or turn
a regional proxy into a historically attested monthly posting.

--write writes only the two report documents.  --check validates and compares
those documents byte-for-byte without writing anything.  With neither option
the program only validates the inputs.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'source'))
from remake.dated_events import validate_source as validate_dated_source, visible_factions


REFERENCE = ROOT / 'game/config/references/ruler-affiliation-review.json'
CATALOG_DIR = ROOT / 'game/data/campaigns'
REPORT_JSON = ROOT / 'docs/ruler-affiliation-audit-20261027.json'
REPORT_MD = ROOT / 'docs/ruler-affiliation-audit-20261027.md'
EXPECTED_SCENARIOS = 29
EXPECTED_POOL = 67
EXPECTED_PEOPLE = 1052
LOCATION_FIELDS = ('status', 'faction', 'city')
STATE_FIELDS = (*LOCATION_FIELDS, 'ruler')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + ': nonempty text required')


def urls(values, label, *, required=False):
    require(isinstance(values, list) and (bool(values) or not required),
            label + ': source URL list required')
    require(all(isinstance(value, str) for value in values), label + ': invalid source URL')
    require(len(set(values)) == len(values), label + ': duplicate source URL')
    for value in values:
        require(isinstance(value, str), label + ': invalid source URL')
        parsed = urlparse(value)
        require(parsed.scheme in ('https', 'http') and bool(parsed.netloc),
                label + ': invalid source URL')


def indexed(rows, key, label):
    require(isinstance(rows, list), label + ': expected list')
    require(all(isinstance(row, dict) and key in row for row in rows),
            label + ': missing row identity')
    result = {row[key]: row for row in rows}
    require(len(result) == len(rows), label + ': duplicate ' + key)
    return result


def date_parts(value, label):
    if isinstance(value, str):
        try:
            value = [int(part) for part in value.split('-')]
        except ValueError as error:
            raise ValueError(label + ': invalid date') from error
    require(isinstance(value, list) and len(value) == 2
            and all(type(part) is int for part in value)
            and 1 <= value[0] <= 400 and 1 <= value[1] <= 12,
            label + ': invalid date')
    return value


def located(row):
    return {key: row.get(key) for key in LOCATION_FIELDS}


def is_fictional(data):
    metadata = data.get('main_scenario', {})
    return bool(metadata.get('fictional') or metadata.get('group') == 'if')


def city_names(data, presentation):
    """Resolve the existing display-name periods without changing any source."""
    date = (data['start_year'], data['start_month'])
    result = {}
    for city in data['cities']:
        row = presentation.get(city['id'], {})
        name = row.get('displayName', city['name'])
        for year in (212, 221):
            if date[0] < year:
                name = row.get('before' + str(year), name)
        for period in data.get('city_history', {}).get(city['id'], {}).get('names', []):
            start = tuple(period.get('from_date', [period.get('start', 1), 1]))
            end = tuple(period.get('to_date', [period.get('end', 9999), 12]))
            if start <= date <= end:
                name = period['name']
        result[city['id']] = name
    return result


def material_totals(data, active):
    """Sum active-city stocks and carried soldiers, including returned troops."""
    stocks = [data['initial_city_resources'].get(city, data['initial_resources'])
              for city in sorted(active)]
    for row in stocks:
        require(all(type(row.get(key)) is int and row[key] >= 0
                    for key in ('gold', 'grain', 'reserves')),
                data['id'] + ': invalid opening city resources')
    require(all(type(row.get('troops')) is int and row['troops'] >= 0
                for row in data['initial_officers']),
            data['id'] + ': invalid opening troop count')
    return dict(gold=sum(row['gold'] for row in stocks),
                grain=sum(row['grain'] for row in stocks),
                soldiers=sum(row['reserves'] for row in stocks)
                + sum(row['troops'] for row in data['initial_officers']))


def check_catalog(data, decision, pool, presentation):
    ident = data['id']
    actual_date = [data['start_year'], data['start_month']]
    require(date_parts(decision.get('date'), ident) == actual_date,
            ident + ': frozen review date differs')
    require(type(decision.get('fictional')) is bool
            and decision['fictional'] == is_fictional(data),
            ident + ': historical/IF classification differs')
    people = indexed(data['people'], 'person_id', ident + ' people')
    require(len(people) == EXPECTED_PEOPLE, ident + ': expected 1052 complete person plans')
    by_runtime = indexed(data['people'], 'runtime_id', ident + ' runtime identities')
    eras = data['era_assignments']
    require(set(eras) == set(people), ident + ': every person requires exactly one era plan')
    for pid, expected in pool.items():
        require(pid in people and all(people[pid].get(key) == expected.get(key)
                                     for key in ('person_id', 'runtime_id', 'name')),
                ident + ': frozen person identity changed: ' + pid)

    active = set(data['active_cities'])
    cities = indexed(data['cities'], 'id', ident + ' cities')
    require(len(active) == len(data['active_cities']) and active <= set(cities),
            ident + ': invalid active-city identities')
    factions = indexed(data['factions'], 'id', ident + ' factions')
    ids = {pid: person['runtime_id'] for pid, person in people.items()}
    static = SimpleNamespace(data=data, factions=factions, map_cities=cities, ids=ids)
    validate_dated_source(static)
    visible = {row['id']: row for row in visible_factions(static)}
    require(set(data['faction_rulers']) == set(factions),
            ident + ': faction and ruler identities differ')
    for fid, faction in factions.items():
        runtime = data['faction_rulers'][fid]
        require(runtime in by_runtime, ident + ': unknown ruler runtime ID: ' + fid)
        require(faction.get('captain') == by_runtime[runtime]['name'],
                ident + ': captain is not canonical ruler name: ' + fid)
        require(by_runtime[runtime]['person_id'] in pool,
                ident + ': ruler missing from frozen review pool: ' + fid)
    require(all(data['initial_owners'].get(city) in {*visible, 'neutral'} for city in active),
            ident + ': unknown/dormant opening city owner')

    opening = {}
    for kind, field in (('serving', 'initial_officers'), ('free', 'initial_free_officers')):
        for row in data[field]:
            pid, city = row.get('person_id'), row.get('city')
            require(pid in people and pid not in opening,
                    ident + ': duplicate/unknown opening person: ' + str(pid))
            require(city in active, ident + ': opening person at inactive city: ' + pid)
            faction = data['initial_owners'][city] if kind == 'serving' else None
            require(kind != 'serving' or faction in visible,
                    ident + ': serving officer has no active owning faction: ' + pid)
            actual = dict(status=kind, faction=faction, city=city, ruler=bool(row.get('ruler')))
            require(located(eras[pid]) == located(actual),
                    ident + ': opening officer and era placement differ: ' + pid)
            if kind == 'free':
                require(not actual['ruler'], ident + ': free officer marked as ruler: ' + pid)
                require(not row.get('troops', 0), ident + ': free officer carries opening troops: ' + pid)
            opening[pid] = actual

    expected_rulers = indexed(decision.get('rulers'), 'id', ident + ' reviewed rulers')
    require(set(expected_rulers) == set(visible),
            ident + ': frozen review must cover all visible rulers exactly once')
    ruler_ids = set()
    ruler_rows = []
    names = city_names(data, presentation)
    for fid, faction in sorted(visible.items()):
        pid = by_runtime[data['faction_rulers'][fid]]['person_id']
        city = faction['city']
        require(city in active and data['initial_owners'][city] == fid,
                ident + ': ruler capital has wrong owner: ' + fid)
        require(expected_rulers[fid].get('person_id') == pid
                and expected_rulers[fid].get('city') == city,
                ident + ': frozen ruler/capital differs: ' + fid)
        require(opening.get(pid) == dict(status='serving', faction=fid, city=city, ruler=True),
                ident + ': ruler is not flagged at its own capital: ' + pid)
        ruler_ids.add(pid)
        ruler_rows.append(dict(id=fid, person_id=pid, name=people[pid]['name'],
                               city=city, city_name=names[city]))
    require({pid for pid, row in opening.items() if row['ruler']} == ruler_ids,
            ident + ': extraneous/missing opening ruler flags')

    # These summaries describe every plan, not only the 67 ruler candidates.
    reviews = [era.get('placement_review', {}) for era in eras.values()]
    require(all(isinstance(review.get(key), str) and bool(review[key])
                for review in reviews for key in ('historical_certainty', 'basis')),
            ident + ': incomplete placement provenance')
    counts = dict(reference_classes=dict(Counter(row['historical_certainty'] for row in reviews)),
                  bases=dict(Counter(row['basis'] for row in reviews)))
    for key, expected in counts.items():
        require(data['placement_completion'].get(key) == expected,
                ident + ': placement provenance counter is stale: ' + key)

    reviewed_people = indexed(decision.get('people'), 'person_id', ident + ' reviewed people')
    require(set(reviewed_people) == set(pool),
            ident + ': frozen review must cover all 67 candidates exactly once')
    rows = []
    for pid, person in sorted(pool.items(), key=lambda item: item[1]['runtime_id']):
        row, era = reviewed_people[pid], eras[pid]
        require(all(key in row for key in LOCATION_FIELDS),
                ident + ': incomplete frozen placement: ' + pid)
        require(located(row) == located(era), ident + ': frozen placement differs: ' + pid)
        for key in ('review_level', 'disposition', 'note', 'certainty'):
            text(row.get(key), ident + ' ' + pid + ' ' + key)
        urls(row.get('source_urls'), ident + ' ' + pid)
        if era['status'] in ('serving', 'free'):
            require(pid in opening, ident + ': reviewed active person missing from opening: ' + pid)
        rows.append(dict(row, name=person['name'], runtime_id=person['runtime_id'],
                         ruler=pid in ruler_ids, city_name=names.get(era.get('city'))))

    material = material_totals(data, active)
    require(decision.get('material') == material,
            ident + ': gold/grain/soldier totals differ from frozen pre-change material')
    corrections = decision.get('corrections', [])
    require(isinstance(corrections, list), ident + ': correction list required')
    seen_corrections = set()
    for row in corrections:
        pid = row.get('person_id')
        require(pid in people and pid not in seen_corrections,
                ident + ': duplicate/unknown correction person: ' + str(pid))
        seen_corrections.add(pid)
        for key in ('before', 'after'):
            require(isinstance(row.get(key), dict) and all(field in row[key] for field in STATE_FIELDS)
                    and type(row[key]['ruler']) is bool,
                    ident + ': incomplete correction ' + key + ': ' + pid)
        after = dict(located(eras[pid]), ruler=pid in ruler_ids)
        require(row['after'] == after, ident + ': correction result differs: ' + pid)
        require(row['before'] != row['after'], ident + ': correction records no change: ' + pid)
        text(row.get('note'), ident + ' correction ' + pid)
        text(row.get('certainty'), ident + ' correction certainty ' + pid)
        urls(row.get('source_urls'), ident + ' correction ' + pid, required=True)
    chronology = decision.get('chronology', [])
    require(isinstance(chronology, list), ident + ': chronology review list required')
    seen_chronology = set()
    for row in chronology:
        pid = row.get('person_id')
        require(pid in people and pid not in seen_chronology,
                ident + ': duplicate/unknown chronology person: ' + str(pid))
        seen_chronology.add(pid)
        require(type(row.get('death_year')) is int and 1 <= row['death_year'] <= 400,
                ident + ': invalid reviewed death year: ' + pid)
        text(row.get('chronology_basis'), ident + ' chronology basis ' + pid)
        require(people[pid].get('death_year') == row['death_year']
                and people[pid].get('chronology_basis') == row['chronology_basis'],
                ident + ': frozen chronology differs: ' + pid)
        text(row.get('note'), ident + ' chronology note ' + pid)
        text(row.get('certainty'), ident + ' chronology certainty ' + pid)
        urls(row.get('source_urls'), ident + ' chronology ' + pid, required=True)
    return dict(id=ident, date=actual_date, title=data['title'],
                title_ja=data.get('main_scenario', {}).get('title_i18n', {}).get('ja', data['title']),
                fictional=is_fictional(data), rulers=ruler_rows, people=rows,
                material=material, placement_counts=counts,
                corrections=[dict(row, name=people[row['person_id']]['name']) for row in corrections],
                chronology=[dict(row, name=people[row['person_id']]['name']) for row in chronology],
                city_names=names,
                dormant_factions=sorted(set(factions) - set(visible)))


def build_report(reference_path=REFERENCE, catalog_dir=CATALOG_DIR):
    reference_path, catalog_dir = Path(reference_path), Path(catalog_dir)
    review = read(reference_path)
    require(review.get('schema') == 'tk2-ruler-affiliation-review-v1',
            'Unknown ruler affiliation reference schema')
    text(review.get('revision'), 'Review revision')
    text(review.get('base_commit'), 'Review base commit')
    require(isinstance(review.get('limits'), list) and bool(review['limits']), 'Review limits required')
    for limit in review['limits']:
        text(limit, 'Review limit')
    pool = indexed(review.get('pool'), 'person_id', 'Reviewed ruler pool')
    require(len(pool) == EXPECTED_POOL, 'Require the frozen 67-person ruler pool')
    require(len({row.get('runtime_id') for row in pool.values()}) == EXPECTED_POOL,
            'Duplicate reviewed runtime identity')
    for row in pool.values():
        text(row.get('person_id'), 'Reviewed person ID')
        text(row.get('name'), 'Reviewed person name')
        require(type(row.get('runtime_id')) is int, 'Reviewed runtime identity must be integer')
    decisions = indexed(review.get('scenarios'), 'id', 'Reviewed scenarios')
    require(len(decisions) == EXPECTED_SCENARIOS, 'Require all 29 reviewed scenarios')
    compiled_index = read(catalog_dir / 'index.json')
    paths = compiled_index.get('catalogs')
    require(isinstance(paths, list) and len(paths) == EXPECTED_SCENARIOS
            and len(set(paths)) == EXPECTED_SCENARIOS, 'Require 29 unique compiled catalogues')
    # Catalogue paths are fixed filenames from a local index, not arbitrary IO.
    require(all(isinstance(path, str) and path == 'campaigns/' + Path(path).name
                and Path(path).suffix == '.json' for path in paths), 'Invalid compiled catalogue filename')
    presentation_path = ROOT / 'game/assets/map-presentation.json'
    presentation = read(presentation_path)['city_names']
    locale_path = ROOT / 'game/locales/zh-hant.json'
    conversion = read(locale_path)['stages']
    japanese_path = ROOT / 'game/locales/messages-ja.json'
    japanese = read(japanese_path)['names']
    results, seen, all_rulers = [], set(), set()
    for filename in paths:
        path = catalog_dir / Path(filename).name
        data = read(path)
        ident = data.get('id')
        require(ident in decisions and ident not in seen, 'Unknown/duplicate compiled scenario: ' + str(ident))
        require(Path(filename).stem == ident.removeprefix('mainland'), ident + ': catalogue filename differs')
        seen.add(ident)
        result = check_catalog(data, decisions[ident], pool, presentation)
        title = data['title'].split(' · ', 1)[-1]
        result['title_ja'] = data.get('main_scenario', {}).get('title_i18n', {}).get(
            'ja', japanese.get(title, title))
        by_runtime = {row['runtime_id']: row['person_id'] for row in data['people']}
        all_rulers.update(by_runtime[rid] for rid in data['faction_rulers'].values())
        result['catalog_sha256'] = sha256(path.read_bytes()).hexdigest()
        results.append(result)
    require(seen == set(decisions), 'Compiled/reviewed scenario set differs')
    require(all_rulers == set(pool), 'Frozen pool differs from union of all current ruler definitions')
    results.sort(key=lambda row: (*row['date'], row['id']))
    counts = Counter()
    for row in results:
        counts.update(scenarios=1, fictional=int(row['fictional']), historical=int(not row['fictional']),
                      people=len(row['people']), rulers=len(row['rulers']), corrections=len(row['corrections']),
                      chronology=len(row['chronology']))
    require(counts['historical'] == 23 and counts['fictional'] == 6,
            'Require 23 historical and six separately reviewed IF scenarios')
    baseline_count = review.get('baseline_serving_non_ruler_reviews', 0)
    require(type(baseline_count) is int and 0 <= baseline_count <= counts['people'],
            'Invalid baseline serving/non-ruler review count')
    return dict(schema='tk2-ruler-affiliation-audit-v1', review_revision=review['revision'],
                base_commit=review['base_commit'], review_sha256=sha256(reference_path.read_bytes()).hexdigest(),
                presentation_sha256=sha256(presentation_path.read_bytes()).hexdigest(),
                locale_sha256=sha256(locale_path.read_bytes()).hexdigest(),
                japanese_sha256=sha256(japanese_path.read_bytes()).hexdigest(),
                baseline_serving_non_ruler_reviews=baseline_count,
                pool=list(sorted(pool.values(), key=lambda row: row['runtime_id'])),
                summary=dict(counts), limits=review['limits'], sources=review.get('sources', {}),
                scope='Frozen ruler affiliation decisions and global structural checks; not full biographical or monthly-garrison historical certification.',
                material_definition='Active-city gold and grain; soldiers are active-city reserves plus initial_officers carried troops. Free officers carry zero opening troops.',
                conversion=conversion, scenarios=results)


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def markdown(report):
    def human(value):
        result = str(value)
        for stage in report['conversion']:
            result = stage['phrases'].get(result, ''.join(stage['characters'].get(char, char) for char in result))
        return result

    def links(values):
        return '、'.join(f'[史料{index}]({url})' for index, url in enumerate(values, 1)) or '—'

    def place(row, names, cities):
        status = {'serving': '在籍', 'free': '在野', 'chronology_excluded': '年代対象外',
                  'scenario_excluded': '本開幕では登場しない'}.get(row['status'], row['status'])
        faction = names.get(row.get('faction'), row.get('faction')) or '—'
        city = cities.get(row.get('city'), row.get('city')) or '—'
        return human(f'{status} / {faction} / {city}' + (' / 君主' if row.get('ruler') else ''))

    summary = report['summary']
    lines = [
        '# 君主候補の所属レビュー（2026年10月27日）', '',
        f"史実{summary['historical']}本と仮想{summary['fictional']}本を分け、歴代君主候補67人を全29開幕で照合した記録です。"
        '史料・年代から修正した人物、仮想の物語として残した関係、地図への地域代理を区別します。'
        '**全人物の伝記や、すべての月・都市の駐将が史料で確定したという意味ではありません。**', '',
        '固定された[レビュー決定表](../game/config/references/ruler-affiliation-review.json)と現在のコンパイル済みカタログを照合します。'
        'このツールは決定表を自動更新せず、`--write` は本資料と[詳細JSON](ruler-affiliation-audit-20261027.json)だけを書き出します。'
        '`--check` は入力と資料の一致を読むだけで確認します。', '',
        f"照合は人物延べ{summary['people']}件、今回の配置修正は延べ{summary['corrections']}件です。"
        f"年代設定の照合は延べ{summary['chronology']}件です。"
        '変更件数には君主候補以外の随行武将や、所属を維持した移駐も含まれます。', '',
        f"決定表が記録する元の「別勢力で任職する非君主」の候補は{report['baseline_serving_non_ruler_reviews']}件です。"
        'この元候補数と、修正後の全候補1943件の配置照合は別の集計です。'
        '審査メモは繁体字中国語・英語の記録を保持し、表の判定見出しを日本語化しています。'
        'メモは審査者による説明であり、史料本文の直接引用ではありません。', '',
        '## 判定の範囲', '',
        '| 区分 | 意味 |', '| --- | --- |',
        '| 所属・年代のレビュー | 独立、降伏、継承、死亡、拘束などの記録を確認したもの。正確な年月や駐地は別に不確実性を残す場合があります。 |',
        '| 仮想・演義の例外 | 公式の仮想シナリオの前提や利用者指定を維持したもの。現実の歴史へ一律に置き換えません。 |',
        '| 地域代理 | 固定都市にない営地や地域を既存ノードへ対応させたもの。郡全体の実効支配を認定しません。 |',
        '| 構造照合のみ | 既に君主、在野、登場前または対象外で、今回の「他勢力に誤編入」の候補でなかった配置。伝記の再考証を意味しません。 |', '',
        '開幕の君主名・人物ID・本拠都市・所有者・君主フラグ、全1052人の配置根拠集計、資源の保存を別々に検証します。'
        '184年2月の後日起兵する勢力は定義があっても開幕君主に数えず、既定の条件付き起兵処理を維持します。'
        '資金・兵糧は開放都市だけ、兵員は開放都市の予備兵と在籍武将の帯兵の合計です。'
        '在野化するときの帯兵は予備兵へ返し、兵員総数を増減させません。', '',
        '## 29本の照合結果', '',
        '| 年月 | 種別 | シナリオ | 開幕勢力 | 人物候補 | 修正 | 資金 / 兵糧 / 兵員 |',
        '| --- | --- | --- | ---: | ---: | ---: | --- |',
    ]
    for row in report['scenarios']:
        material = row['material']
        values = (f"{row['date'][0]}年{row['date'][1]}月", '仮想' if row['fictional'] else '史実',
                  row['title_ja'], len(row['rulers']), len(row['people']), len(row['corrections']),
                  f"{material['gold']} / {material['grain']} / {material['soldiers']}")
        lines.append('| ' + ' | '.join(cell(value) for value in values) + ' |')
    lines += ['', '## 制限と未確定事項', '']
    lines += ['- ' + str(value) for value in report['limits']]
    lines += ['', '## 開幕ごとの人物配置と修正理由', '']
    pool_names = {row['person_id']: row['name'] for row in report['pool']}
    disposition_names = {'keep': '維持', 'correct': '修正', 'exception': '例外維持',
                         'structural_only': '構造のみ', 'retain': '維持', 'corrected': '修正',
                         'already_independent_at_opening': '開幕で独立済み',
                         'not_another_factions_serving_ruler_case': '今回の誤編入候補ではない',
                         'retained_dated_service': '年代に沿う任職を維持',
                         'retained_with_reviewed_evidence': '根拠を再確認して維持'}
    review_names = {'additional_regional_commander_review': '追加の地方軍営レビュー',
                    'dated_evidence_reconfirmation': '年代資料の再確認',
                    'dated_placement_correction': '年代に基づく配置修正',
                    'reviewed_serving_non_ruler_case': '元の任職候補の個別判定',
                    'structural_existing_ruler': '開幕君主の構造照合',
                    'structural_offstage_or_free_plan': '在野・未登場等の構造照合'}
    certainty_names = {
        'annotated_biography_fugitive_region_proxy': '逃亡確認・滞在地は地域代理',
        'authorial_garrison_relocation': '本作の移駐',
        'authorial_northern_career_proxy': '北方経歴の地域代理',
        'authorial_region_proxy': '地域代理',
        'bounded_authorial_estimate': '未確定年の推定境界',
        'bounded_career_review': '経歴の限定確認',
        'bounded_hierarchy_review': '主従関係の限定確認',
        'contested_month_guest_region_proxy': '月に異説・客居の地域代理',
        'dated_envoy_regional_proxy': '任命月未確定の使節代理',
        'displaced_prefect_region_proxy': '失地後の地域代理',
        'high': '所属関係を確認',
        'local_warband_without_attested_city': '独占都市は未確認',
        'low_exact_posting': '正確な駐地は未確認',
        'medium': '限定確認',
        'primary_career_context_with_regional_posting': '経歴史料・駐地は地域代理',
        'primary_text_captivity': '史料で幽閉を確認',
        'primary_text_chronology': '史料で年を確認',
        'primary_text_dead_by_opening': '開幕前の死去を確認',
        'primary_text_deposed_unavailable': '退位・出任制限',
        'regional_primary_mapping': '史料の地域を地図へ対応',
        'structural_scope_only': '構造のみ',
    }
    for row in report['scenarios']:
        lines += [f"### {row['date'][0]}年{row['date'][1]}月・{row['title_ja']}（{'仮想' if row['fictional'] else '史実'}）", '',
                  '開幕君主：' + '、'.join(human(f"{r['name']}（{r['city_name']}）") for r in row['rulers']) + '。', '']
        if row['dormant_factions']:
            lines += ['後日起兵の定義（開幕では非表示）：' + '、'.join(row['dormant_factions']) + '。', '']
        lines += ['| 人物（固定ID） | 状態 | 所属 | 都市 | 判定 / 確度 | 照合範囲・理由 |',
                  '| --- | --- | --- | --- | --- | --- |']
        faction_names = {r['id']: r['name'] for r in row['rulers']}
        for person in row['people']:
            disposition = disposition_names.get(person['disposition'], person['disposition'])
            level = review_names.get(person['review_level'], person['review_level'])
            certainty = certainty_names.get(person['certainty'], person['certainty'])
            note = person['note']
            if person['review_level'].startswith('structural_'):
                note = ('現在配置の構造を照合した行です。生涯全体や月別の駐地を再考証した認定ではありません。')
            status = {'serving': '在籍', 'free': '在野', 'chronology_excluded': '年代対象外',
                      'scenario_excluded': '本開幕対象外'}.get(person['status'], person['status'])
            values = (human(person['name']) + ('〔君主〕' if person['ruler'] else '') + f" (`{person['person_id']}`)",
                      status, human(faction_names.get(person['faction'], person['faction']) or '—'),
                      human(person['city_name'] or person['city'] or '—'),
                      f"{disposition} / {certainty}",
                      f"{level}：{note} {links(person['source_urls'])}")
            lines.append('| ' + ' | '.join(cell(value) for value in values) + ' |')
        if row['corrections']:
            lines += ['', '今回の修正：', '',
                      '| 人物 | 変更前（状態 / 所属 / 都市） | 変更後 | 根拠・留保 |',
                      '| --- | --- | --- | --- |']
            for change in row['corrections']:
                names = dict(faction_names)
                # A removed ruler need not be a current faction; preserve its ID.
                values = (human(change.get('name', pool_names.get(change['person_id'], change['person_id']))),
                          place(change['before'], names, row['city_names']),
                          place(change['after'], names, row['city_names']),
                          f"{change['note']}（{certainty_names.get(change['certainty'], change['certainty'])}） {links(change['source_urls'])}")
                lines.append('| ' + ' | '.join(cell(value) for value in values) + ' |')
        else:
            lines += ['', '今回の配置修正はありません。維持の記録も、史料がすべての駐地を証明したという意味ではありません。']
        if row['chronology']:
            lines += ['', '今回確認した年代設定：', '',
                      '| 人物 | 退出年 | 年代設定の根拠 | 留保・史料 |',
                      '| --- | ---: | --- | --- |']
            for change in row['chronology']:
                values = (human(change['name']), change['death_year'], change['chronology_basis'],
                          f"{change['note']}（{certainty_names.get(change['certainty'], change['certainty'])}） {links(change['source_urls'])}")
                lines.append('| ' + ' | '.join(cell(value) for value in values) + ' |')
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def rendered_files(report):
    # Locale conversion belongs to presentation and need not duplicate the
    # entire character map inside the audit JSON.
    serializable = {key: value for key, value in report.items() if key != 'conversion'}
    return {REPORT_JSON.name: json.dumps(serializable, ensure_ascii=False, indent=2) + '\n',
            REPORT_MD.name: markdown(report)}


def check(reference_path=REFERENCE, catalog_dir=CATALOG_DIR,
          report_json=REPORT_JSON, report_md=REPORT_MD):
    report = build_report(reference_path, catalog_dir)
    outputs = rendered_files(report)
    for path, name in ((Path(report_json), REPORT_JSON.name), (Path(report_md), REPORT_MD.name)):
        require(path.is_file() and path.read_bytes() == outputs[name].encode('utf-8'),
                'Ruler affiliation report is stale: ' + str(path))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--write', action='store_true', help='Write only the JSON and Japanese Markdown reports')
    mode.add_argument('--check', action='store_true', help='Read-only validation and byte-for-byte report comparison')
    parser.add_argument('--reference', type=Path, default=REFERENCE)
    parser.add_argument('--catalog-dir', type=Path, default=CATALOG_DIR)
    parser.add_argument('--report-dir', type=Path, default=REPORT_JSON.parent)
    args = parser.parse_args(argv)
    if args.check:
        report = check(args.reference, args.catalog_dir,
                       args.report_dir / REPORT_JSON.name, args.report_dir / REPORT_MD.name)
    else:
        report = build_report(args.reference, args.catalog_dir)
        if args.write:
            args.report_dir.mkdir(parents=True, exist_ok=True)
            for name, content in rendered_files(report).items():
                (args.report_dir / name).write_text(content, encoding='utf-8')
    print(json.dumps(dict(report['summary'], check=args.check, write=args.write), ensure_ascii=False))


if __name__ == '__main__':
    main()
