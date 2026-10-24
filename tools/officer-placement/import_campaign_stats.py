#!/usr/bin/env python3
"""Apply the reviewed campaign-stat policy from pinned, offline references.

The cnblogs table supplies initial health and contextual initial loyalty only.
SAN14 charisma supplies virtue.  No identity is inferred from ability values,
portraits, row order or approximate names.  Existing ROM evidence is retained.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PEOPLE_PATH = ROOT / 'game/config/campaigns/people.json'
REFERENCE_PATH = ROOT / 'game/config/references/cnblogs-officer-stats.json'
SAN14_PATH = ROOT / 'game/config/references/san14-abilities.json'
ROM_PATH = ROOT / 'game/config/references/original-officer-stats.json'
REPORT_PATH = ROOT / 'docs/officer-stat-changes-v1.json'
CSV_PATH = ROOT / 'docs/officer-stat-changes-v1.csv'
POLICY = 'campaign-officer-stats-v1'
CHECKPOINT = 'pre_campaign_stat_policy_v1'
SOURCE_URL = 'https://www.cnblogs.com/strick/p/10171248.html'
ARCHIVE_URL = 'https://files-cdn.cnblogs.com/files/strick/霸王的大陆武将.zip'
ARCHIVE_SHA256 = '6dff28ec4bb74776de6cb6e232388e7210982e8e1761adff45a73adccc2933b0'
TEXT_SHA256 = '231c554b6de801ecf9d2387e42b549ce49a3e12ae94dd237a8e6153f1bb18187'
FACTUAL_RECORDS_SHA256 = '0c7fd397a20a41f8a1672666d9103eed2bea3e66362e2e199b63bb0bdf12236a'
MEMBER_NAME = '霸王的大陆武将.txt'
REFERENCE = 'game/config/references/cnblogs-officer-stats.json'
FACTUAL_FIELDS = ('source_row_id', 'source_line', 'source_line_sha256', 'source_name',
    'name', 'original_appearance', 'city_label', 'level', 'health', 'martial_strength',
    'martial_up', 'intellect', 'loyalty', 'loyalty_display', 'virtue', 'experience_display',
    'lifespan_year', 'terrain_label', 'weapon_label', 'armor_label', 'faction_label')

# These are individual, reviewed spelling/context decisions, not a normalizer.
# The approved target spelling is checked again against the canonical person.
REVIEWED_NAMES = {
    '夏候敦': ('san14-candidate-0124', '夏侯惇', 'reviewed_spelling',
              '候/侯 and 敦/惇 transcription; existing reviewed ROM name 夏侯惇'),
    '严峻': ('san14-candidate-0235', '严畯', 'reviewed_spelling',
             '峻/畯 transcription; existing reviewed ROM name 厳畯'),
    '雍圃': ('san14-candidate-0855', '雍闿', 'reviewed_spelling',
             '圃/闿 transcription; existing reviewed ROM name 雍闓'),
    '程乘': ('san14-candidate-0705', '程秉', 'reviewed_spelling',
             '乘/秉 transcription; existing reviewed ROM name 程秉'),
    '辛昆': ('san14-candidate-0465', '辛毘', 'reviewed_spelling',
             '昆/毗 transcription; existing reviewed ROM name 辛毗 and canonical alias 辛毗'),
    '朱恒': ('san14-candidate-0381', '朱桓', 'reviewed_spelling',
             '恒/桓 transcription; existing reviewed ROM name 朱桓'),
    '藩璋': ('san14-candidate-0781', '潘璋', 'reviewed_spelling',
             '藩/潘 transcription; existing reviewed ROM name 潘璋'),
    '孙诩': ('san14-candidate-0576', '孙翊', 'reviewed_spelling',
             '诩/翊 transcription; existing reviewed ROM name 孫翊'),
    '步隙': ('san14-candidate-0838', '步骘', 'reviewed_spelling',
             '隙/骘 transcription; existing reviewed ROM name 歩隲'),
    '张南': ('san14-candidate-0651', '张南', 'reviewed_context_identity',
             'Explicit 袁绍 faction and 青州 source context identify 袁绍的张南; '
             'not the separate 蜀汉张南 san14-candidate-0652; source lifespan is not historical chronology'),
    '费帏': ('san14-candidate-0787', '费祎', 'reviewed_context_identity',
             'Reviewed 帏/祎 spelling with 涪陵/刘璋 context identifies 費禕; '
             'not an ability-based join; prior ROM identity remains unchanged'),
}

# Deliberately exhaustive source labels.  Location hints mentioning a nearby
# ruler are not that ruler's faction.  No substring matching or inherited Yuan
# family ownership is used.  Retinue labels are reviewed explicit crosswalks.
FACTION_LABELS = {
    '刘备': ['shu'], '曹操': ['wei'], '袁绍': ['yuan_shao'],
    '孙策': ['wu', 'sun_jian'], '董卓': ['dong_zhuo'],
    '刘璋': ['liu_zhang'], '马腾': ['ma_teng'],
    '投奔刘备': ['shu'], '投奔关羽': ['shu'], '投奔张飞': ['shu'],
    '投奔诸葛亮': ['shu'], '投奔曹操': ['wei'], '投奔曹丕': ['wei'],
    '投奔夏侯敦': ['wei'], '投奔夏侯渊': ['wei'], '投奔司马懿': ['wei'],
    '投奔孙策': ['wu', 'sun_jian'], '投奔诸葛瑾': ['wu', 'sun_jian'],
    '投奔马腾': ['ma_teng'], '君主': [],
    '刘备左侧空城': [], '刘璋右下侧空城': [], '刘璋右侧空城': [],
    '刘璋左侧空城': [], '地图中下方空城': [], '孙策下方空城': [],
    '孙策左下侧空城': [], '孙策左侧空城': [], '曹操右侧空城': [],
    '董卓中间空城': [], '袁绍右侧空城': [],
}


def encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def require_integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{label} must be an integer in {low}..{high}')
    return value


def factual_digest(records):
    facts = [{key: record[key] for key in FACTUAL_FIELDS} for record in records]
    return sha256(json.dumps(facts, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':')).encode()).hexdigest()


def parse_archive(archive):
    """Parse the pinned attachment, retaining factual columns, not article prose."""
    if sha256(archive).hexdigest() != ARCHIVE_SHA256:
        raise ValueError('Unreviewed cnblogs archive; import stopped')
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        if zipped.namelist() != [MEMBER_NAME]:
            raise ValueError('Unexpected source archive members')
        raw = zipped.read(MEMBER_NAME)
    if sha256(raw).hexdigest() != TEXT_SHA256:
        raise ValueError('Unreviewed cnblogs source text; import stopped')
    records = []
    for line_number, line in enumerate(raw.decode('utf-8-sig').splitlines(), 1):
        columns = line.split()
        if len(columns) < 4 or not (columns[1] == '初期' or columns[1].isdigit()):
            continue
        if len(columns) != 16 or not columns[3].isdigit():
            raise ValueError(f'Malformed source row {line_number}')
        name = columns[0].rstrip('★▲')
        loyalty = None if columns[8] == '--' else int(columns[8])
        record = dict(source_row_id=f'cnblogs-line-{line_number:04d}',
            source_line=line_number, source_line_sha256=sha256(line.encode()).hexdigest(),
            source_name=columns[0], name=name, original_appearance=columns[1],
            city_label=columns[2], level=int(columns[3]), health=int(columns[4]),
            martial_strength=int(columns[5]), martial_up=int(columns[6]),
            intellect=int(columns[7]), loyalty=loyalty, loyalty_display=columns[8],
            virtue=int(columns[9]), experience_display=int(columns[10]),
            lifespan_year=int(columns[11]), terrain_label=columns[12],
            weapon_label=columns[13], armor_label=columns[14], faction_label=columns[15])
        records.append(record)
    if len(records) != 237 or len({r['name'] for r in records}) != 237:
        raise ValueError('Expected 237 distinct source names')
    return records


def bind_records(records, people):
    """Reviewable exact names/aliases plus the finite approved spelling list."""
    aliases = {}
    for pid, person in people.items():
        for name in set([person['name']] + person.get('aliases', [])):
            aliases.setdefault(name, []).append(pid)
    used = set()
    result = []
    for source in records:
        record = deepcopy(source)
        name = record['name']
        candidates = aliases.get(name, [])
        if name in REVIEWED_NAMES:
            pid, canonical_name, status, basis = REVIEWED_NAMES[name]
            if people[pid]['name'] != canonical_name:
                raise ValueError('Reviewed identity changed: ' + name)
        elif len(candidates) == 1:
            pid, = candidates
            status, basis = ('reviewed_exact_name',
                'Unique exact canonical name or previously reviewed explicit alias; '
                'no fuzzy, statistical, ordinal, portrait or runtime-ID matching')
        else:
            pid, status = None, 'unbound'
            basis = ('No exact person or reviewed spelling identity; source retained '
                     'without overwriting another person')
        if pid in used:
            raise ValueError('Duplicate source binding: ' + pid)
        if pid is not None:
            used.add(pid)
        record.update(person_id=pid, identity_status=status, identity_basis=basis)
        record['faction_ids'] = deepcopy(FACTION_LABELS[record['faction_label']])
        result.append(record)
    counts = Counter(r['identity_status'] for r in result)
    if counts != Counter(reviewed_exact_name=212, reviewed_spelling=9,
                         reviewed_context_identity=2, unbound=14):
        raise ValueError('Identity coverage changed; requires a new review: ' + repr(counts))
    return result


def make_reference(records, people):
    result = dict(schema='tk2-cnblogs-officer-stats-v1',
        source=dict(title='FC游戏《三国志2-霸王的大陆》攻略：武将资料附件',
            author='咖啡机（K.F.J）', page_url=SOURCE_URL, archive_url=ARCHIVE_URL,
            retrieved='2026-10-24', archive_size=6872, archive_sha256=ARCHIVE_SHA256,
            member_name=MEMBER_NAME, member_size=23981, member_sha256=TEXT_SHA256,
            factual_records_sha256=FACTUAL_RECORDS_SHA256,
            encoding='utf-8-sig', line_endings='CRLF',
            provenance='Third-party game-stat transcription, not an official export or historical measurement'),
        field_policy=dict(health='Source initial/current health only; not an attested personal maximum',
            loyalty='Contextual initial loyalty; -- is a ruler display sentinel, retained as null',
            lifespan_year='Original game setting only; does not replace canonical historical chronology',
            faction_label='Literal source faction/retinue/location label; location-only labels map to no faction',
            other_fields='Retained factual source columns only; not applied to martial/intellect/experience/equipment/chronology'),
        identity_policy='Reviewed unique exact canonical names/aliases plus 11 explicit individual spelling/context decisions; '
                        'no approximate-name or ability-based identity joins',
        source_records=237, bound_people=223, unbound_source_records=14,
        identity_counts=dict(Counter(r['identity_status'] for r in records)),
        identity_disagreements=[
            dict(source_row_id='cnblogs-line-0215', source_name='费帏',
                person_id='san14-candidate-0787', prior_rom_record_id=187,
                prior_rom_name='潘濬', prior_rom_person_id='san14-candidate-0780',
                note='Independent transcriptions assign different names to a matching numeric record. '
                     'The new table identity was reviewed from spelling/context; no ROM/portrait identity is changed.'),
            dict(source_row_id='cnblogs-line-0203', source_name='傅婴',
                person_id=next(pid for pid, p in people.items() if p['name'] == '傅婴'),
                prior_rom_record_id=190, prior_rom_name='傅巽',
                prior_rom_person_id='san14-candidate-0807',
                note='Independent transcriptions disagree on the displayed name. '
                     'No ROM/portrait identity is changed, and numeric agreement does not establish identity.')],
        records=records)
    return result


def validate_reference(reference, people):
    if reference.get('schema') != 'tk2-cnblogs-officer-stats-v1':
        raise ValueError('Unsupported cnblogs reference')
    if reference['source']['archive_sha256'] != ARCHIVE_SHA256 or reference['source']['member_sha256'] != TEXT_SHA256:
        raise ValueError('Unreviewed source provenance')
    records = reference['records']
    if (reference['source'].get('factual_records_sha256') != FACTUAL_RECORDS_SHA256
            or factual_digest(records) != FACTUAL_RECORDS_SHA256):
        raise ValueError('Offline source facts differ from the pinned attachment')
    if bind_records([{key: r[key] for key in FACTUAL_FIELDS} for r in records], people) != records:
        raise ValueError('Reviewed name bindings changed')
    ids, people_seen = set(), set()
    for record in records:
        rid, pid = record['source_row_id'], record['person_id']
        if rid != f"cnblogs-line-{record['source_line']:04d}" or rid in ids:
            raise ValueError('Invalid or repeated source row')
        ids.add(rid)
        for field in ('health', 'martial_strength', 'martial_up', 'intellect', 'virtue'):
            require_integer(record[field], 1, 99, field)
        if record['loyalty'] is None:
            if record['loyalty_display'] != '--':
                raise ValueError('Missing loyalty is not a ruler sentinel')
        else:
            require_integer(record['loyalty'], 0, 99, 'source loyalty')
            if record['loyalty_display'] != str(record['loyalty']):
                raise ValueError('Source loyalty display mismatch')
        if record['faction_ids'] != FACTION_LABELS[record['faction_label']]:
            raise ValueError('Unreviewed source faction context')
        if pid is not None:
            if pid not in people or pid in people_seen:
                raise ValueError('Invalid or repeated source person')
            people_seen.add(pid)
    if len(ids) != 237 or len(people_seen) != 223:
        raise ValueError('Unexpected source coverage')


def apply_policy(pool, reference):
    result = deepcopy(pool)
    people = result['people']
    validate_reference(reference, people)
    source_by_person = {r['person_id']: r for r in reference['records'] if r['person_id']}
    for pid in result['order']:
        person = people[pid]
        if CHECKPOINT not in person:
            person[CHECKPOINT] = {key: deepcopy(person.get(key)) for key in
                                 ('profile', 'configuration', 'virtue_design', 'initialization')}
        previous = person[CHECKPOINT]
        record = source_by_person.get(pid)
        health = record['health'] if record else 80
        person['profile']['health_max'] = max(previous['profile']['health_max'], health)
        person['profile']['basis']['health_max'] = (
            'remake_compatibility_cap=max(pre_policy_cap,initial_health); not_original_health_max')
        person['configuration']['health'] = ('cnblogs_initial_health_with_remake_compatibility_cap'
                                            if record else 'remake_default_initial80_with_retained_cap')
        source_loyalty = None
        if record:
            source_loyalty = dict(value=record['loyalty'], display=record['loyalty_display'],
                source_faction_label=record['faction_label'], faction_ids=deepcopy(record['faction_ids']),
                reference=REFERENCE, source_row_id=record['source_row_id'])
        person['initialization'] = dict(schema='tk2-officer-initialization-v1',
                                       health=health, default_loyalty=80, source_loyalty=source_loyalty)
        charisma = person['profile']['source_stats'].get('charisma')
        if charisma is not None:
            value = min(require_integer(charisma, 1, 100, 'SAN14 charisma'), 99)
            status, basis, configuration = ('san14_charisma',
                'SAN14.charisma; max99 compatibility scale', 'SAN14_charisma_conversion')
            sources = [dict(reference='game/config/references/san14-abilities.json', person_id=pid,
                            field='charisma', source_url=person['ability_source']['source_url'])]
            rationale = '使用者指定將本作德對應既有SAN14魅力；保留來源值，100按本作相容上限轉為99。這是遊戲屬性映射，不是歷史道德評判。'
        else:
            value = 60
            status, basis, configuration = ('configured_default',
                'explicit_user_default60; missing_SAN14_charisma', 'explicit_user_default60_missing_SAN14_charisma')
            sources = []
            rationale = '沒有SAN14魅力來源，按使用者明確指示設為60；不推測或冒稱SAN14數值。'
        person['profile']['virtue'] = value
        person['profile']['basis']['virtue'] = basis
        person['configuration']['virtue'] = configuration
        person['virtue_design'] = dict(person_id=pid, name=person['name'], policy_id=POLICY,
            status=status, virtue=value, source_charisma=charisma,
            is_historical_fact=False, dimensions=None, design_rationale=rationale, sources=sources)
    return result


def make_report(pool, reference):
    original = {r['person_id']: r for r in load(ROM_PATH)['records'] if r['person_id']}
    source_by_person = {r['person_id']: r for r in reference['records'] if r['person_id']}
    rows, conflicts = [], []
    for pid in pool['order']:
        person = pool['people'][pid]
        prior = person[CHECKPOINT]
        source = source_by_person.get(pid)
        old_rom = original.get(pid)
        comparison = None
        if source and old_rom:
            raw = bytes.fromhex(old_rom['record_hex'])
            comparison = dict(original_id=old_rom['original_id'], original_name=old_rom['transcribed_name'],
                health=dict(cnblogs=source['health'], rom=raw[0]),
                loyalty=dict(cnblogs=source['loyalty'], rom=raw[3],
                             ruler_sentinel_matches=source['loyalty'] is None and raw[3] == 100),
                virtue=dict(cnblogs=source['virtue'], rom=raw[4]))
            different = [field for field in ('health', 'loyalty', 'virtue')
                if comparison[field]['cnblogs'] != comparison[field]['rom']
                and not comparison[field].get('ruler_sentinel_matches')]
            comparison['different_fields'] = different
            if different:
                conflicts.append(dict(person_id=pid, name=person['name'], source_row_id=source['source_row_id'],
                                      comparison=comparison))
        after_init = deepcopy(person['initialization'])
        rows.append(dict(person_id=pid, name=person['name'],
            previous_virtue=prior['profile']['virtue'], virtue=person['profile']['virtue'],
            virtue_delta=person['profile']['virtue']-prior['profile']['virtue'],
            virtue_source_status=person['virtue_design']['status'],
            previous_virtue_basis=prior['profile']['basis']['virtue'],
            virtue_basis=person['profile']['basis']['virtue'],
            source_charisma=person['profile']['source_stats'].get('charisma'),
            previous_initial_health=(prior['initialization'] or {}).get('health', prior['profile']['health_max']),
            initial_health=after_init['health'],
            previous_health_max=prior['profile']['health_max'], health_max=person['profile']['health_max'],
            health_max_delta=person['profile']['health_max']-prior['profile']['health_max'],
            health_source='cnblogs_initial_health' if source else 'explicit_remake_default80',
            source_row_id=source['source_row_id'] if source else None,
            source_name=source['name'] if source else None,
            previous_default_loyalty=80, default_loyalty=80,
            source_loyalty=after_init['source_loyalty'],
            loyalty_policy='ruler100; free0; numeric_source_only_in_explicit_source_faction_ids; otherwise80',
            original_reference_comparison=comparison))
    summary = dict(people=len(rows), san14_charisma=sum(r['source_charisma'] is not None for r in rows),
        charisma_missing_default60=sum(r['source_charisma'] is None for r in rows),
        virtue_changed=sum(r['virtue_delta'] != 0 for r in rows),
        virtue_increased=sum(r['virtue_delta'] > 0 for r in rows),
        virtue_decreased=sum(r['virtue_delta'] < 0 for r in rows),
        virtue_unchanged=sum(r['virtue_delta'] == 0 for r in rows),
        source_health_people=len(source_by_person), initial_health_default80=len(rows)-len(source_by_person),
        initial_health_changed=sum(r['initial_health'] != r['previous_initial_health'] for r in rows),
        health_max_increased=sum(r['health_max_delta'] > 0 for r in rows),
        health_max_unchanged=sum(r['health_max_delta'] == 0 for r in rows),
        numeric_source_loyalty=sum(r['source_loyalty'] is not None and r['source_loyalty']['value'] is not None for r in rows),
        numeric_source_loyalty_with_faction=sum(r['source_loyalty'] is not None and r['source_loyalty']['value'] is not None
                                               and bool(r['source_loyalty']['faction_ids']) for r in rows),
        source_ruler_sentinel=sum(r['source_loyalty'] is not None and r['source_loyalty']['value'] is None for r in rows),
        cnblogs_rom_same_person_comparisons=sum(r['original_reference_comparison'] is not None for r in rows),
        cnblogs_rom_same_person_conflicts=len(conflicts))
    return dict(schema='tk2-officer-stat-change-report-v1', policy_id=POLICY,
        baseline='Each person.pre_campaign_stat_policy_v1; immutable on re-import',
        source_reference=REFERENCE, source_archive_sha256=ARCHIVE_SHA256,
        field_policy='Initial health is distinct from the remake cap. Loyalty is a faction-qualified initialization template, '
                     'not a permanent rating. Existing campaign saves and original ROM identity records are not migrated.',
        summary=summary, source_identity_counts=reference['identity_counts'],
        unbound_source_records=[deepcopy(r) for r in reference['records'] if not r['person_id']],
        identity_disagreements=reference['identity_disagreements'],
        cnblogs_rom_conflicts=conflicts, people=rows)


def csv_report(report):
    output = io.StringIO(newline='')
    fields = ['person_id', 'name', 'previous_virtue', 'virtue', 'virtue_delta',
              'virtue_source_status', 'source_charisma', 'previous_initial_health', 'initial_health',
              'previous_health_max', 'health_max', 'health_max_delta', 'health_source',
              'source_row_id', 'source_name', 'previous_default_loyalty', 'default_loyalty',
              'source_loyalty_value', 'source_loyalty_display', 'source_faction_label',
              'source_faction_ids', 'loyalty_policy']
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    for person in report['people']:
        row = {key: person.get(key) for key in fields}
        source = person['source_loyalty'] or {}
        row.update(source_loyalty_value=source.get('value'), source_loyalty_display=source.get('display'),
                   source_faction_label=source.get('source_faction_label'),
                   source_faction_ids='|'.join(source.get('faction_ids', [])))
        writer.writerow(row)
    return output.getvalue()


def import_stats(source_zip=None):
    pool = load(PEOPLE_PATH)
    san14 = load(SAN14_PATH)
    expected_abilities = {r['person_id']: r['stats'] for r in san14['abilities']}
    actual_abilities = {pid: person['profile']['source_stats']
                        for pid, person in pool['people'].items()
                        if person['profile']['source_stats'].get('charisma') is not None}
    if actual_abilities != expected_abilities:
        raise ValueError('Canonical SAN14 abilities differ from the retained source reference')
    if source_zip is None:
        reference = load(REFERENCE_PATH)
    else:
        records = bind_records(parse_archive(source_zip), pool['people'])
        reference = make_reference(records, pool['people'])
    updated = apply_policy(pool, reference)
    report = make_report(updated, reference)
    if len(updated['people']) != 1023 or report['summary']['san14_charisma'] != 1000:
        raise ValueError('Campaign-person or SAN14 coverage changed')
    return updated, reference, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-zip', type=Path, help='Optional pinned source attachment; otherwise use offline factual reference')
    parser.add_argument('--check', action='store_true', help='Verify all outputs byte-for-byte without writing')
    args = parser.parse_args()
    pool, reference, report = import_stats(args.source_zip.read_bytes() if args.source_zip else None)
    outputs = {PEOPLE_PATH: encode(pool), REFERENCE_PATH: encode(reference),
               REPORT_PATH: encode(report), CSV_PATH: csv_report(report)}
    for path, content in outputs.items():
        if args.check:
            if path.read_text(encoding='utf-8') != content:
                raise ValueError('Campaign-stat import differs: ' + str(path.relative_to(ROOT)))
        else:
            path.write_text(content, encoding='utf-8')
    print(json.dumps(dict(check=args.check, **report['summary']), ensure_ascii=False))


if __name__ == '__main__':
    main()
