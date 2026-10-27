#!/usr/bin/env python3
"""Project reviewed original-game equipment labels without changing people.

The original223 equipment records remain frozen, including all source labels
and identity metadata. The only additional reviewed identity is Liaodong's
Wang Jian (cnblogs-line-0229). No original ROM bytes, item rules, signature
overrides, historical years, player saves or canonical people are modified.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_campaign_stats import load, validate_reference

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'game/config/references/cnblogs-officer-stats.json'
PEOPLE = ROOT / 'game/config/campaigns/people.json'
OUTPUT = ROOT / 'game/config/references/original-equipment-v1.json'
SOURCE_FILE = 'game/config/references/cnblogs-officer-stats.json'
BASE_RECORDS_SHA256 = '838143a3bb653f6375c8eb7830823251c6ccca760b206ae271632ec20c9530c9'
BASE_SOURCE_SHA256 = 'e1917f03558182172154e3a9b2a5cc5da13ba6e9c0d83668af4feade51a4c310'
WANG_JIAN = 'historical-wang-jian-liaodong'
WEAPON_ALIASES = {'短剣': 0, '飞剣': 1, '长剣': 2, '破斩剣': 3, '大剣': 4,
    '薤刀': 8, '眉尖刀': 9, '三尖刀': 10, '钩镰刀': 11, '偃月刀': 12, '鳯嘴刀': 13,
    '矛': 16, '双戟': 17, '単钩鎗': 18, '戦斧': 19, '双钩鎗': 20, '方天画戟': 21}
ARMOR_ALIASES = {'纶巾': 0, '笼手': 1, '兜': 2, '硬皮': 3, '鹤氅': 4, '甲胄': 5}


def records_digest(rows):
    # Retain the original reference's exact compact-JSON/newline convention.
    raw = (json.dumps(rows, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
    return sha256(raw).hexdigest()


def build(source_path=SOURCE, people_path=PEOPLE):
    source_path = Path(source_path)
    source = load(source_path)
    validate_reference(source, load(Path(people_path))['people'])
    records = [dict(person_id=row['person_id'], source_row_id=row['source_row_id'],
        source_name=row['name'], weapon_label=row['weapon_label'],
        weapon_id=WEAPON_ALIASES[row['weapon_label']], armor_label=row['armor_label'],
        armor_id=ARMOR_ALIASES[row['armor_label']], basis='cnblogs_original_equipment_transcription')
        for row in source['records'] if row.get('person_id')]
    retained = [row for row in records if row['person_id'] != WANG_JIAN]
    added = [row for row in records if row['person_id'] == WANG_JIAN]
    if len(retained) != 223 or records_digest(retained) != BASE_RECORDS_SHA256:
        raise ValueError('Released223 original equipment records changed')
    expected = dict(person_id=WANG_JIAN, source_row_id='cnblogs-line-0229', source_name='王建',
        weapon_label='飞剣', weapon_id=1, armor_label='纶巾', armor_id=0,
        basis='cnblogs_original_equipment_transcription')
    if added != [expected] or len(records) != 224 or len({r['person_id'] for r in records}) != 224:
        raise ValueError('Only reviewed Wang Jian source0229 may extend the equipment snapshot')
    origin = source['source']
    return dict(schema='tk2-original-equipment-v1', source_file=SOURCE_FILE,
        source_file_sha256=sha256(source_path.read_bytes()).hexdigest(),
        source=dict(page_url=origin['page_url'], archive_url=origin['archive_url'],
            archive_sha256=origin['archive_sha256'], member_sha256=origin['member_sha256'],
            provenance='Third-party original-FC game-stat transcription, not an official export or an independently re-extracted ROM equipment table.'),
        identity_policy='Reuse the223 frozen equipment bindings plus the single explicitly reviewed '
                        'Liaodong Wang Jian source0229 binding; no fuzzy, statistical, portrait or ordinal join.',
        field_policy='Original equipment labels are retained exactly and mapped through explicit spelling aliases to existing zero-based weapon/armor IDs. No iconic novel overrides, new item stats or unrelated source fields are introduced.',
        weapon_aliases=WEAPON_ALIASES, armor_aliases=ARMOR_ALIASES,
        source_records=237, bound_people=224, unbound_source_records=13,
        factual_records_sha256=records_digest(records),
        append_review=dict(base_commit='f65d3abae2c2c50293c5cf08d07f49413d60cbf6',
            base_bound_people=223, base_source_file_sha256=BASE_SOURCE_SHA256,
            retained_records_sha256=BASE_RECORDS_SHA256, added_person_id=WANG_JIAN,
            added_source_row_id='cnblogs-line-0229',
            note='僅加入已審核的遼東王建，飛剣／綸巾取自同一原表0229；原223人完整條目逐物件保留。'
                 '這是原遊戲初裝轉錄，不把兵器、原表年份或位置標籤當成史實。'),
        records=records)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def check(source_path=SOURCE, people_path=PEOPLE, output=OUTPUT):
    expected = build(source_path, people_path)
    if Path(output).read_bytes() != encode(expected):
        raise ValueError('Original equipment reference is stale')
    return expected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Read-only exact reference comparison')
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--people', type=Path, default=PEOPLE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    result = check(args.source, args.people, args.output) if args.check else build(args.source, args.people)
    if not args.check:
        args.output.write_bytes(encode(result))
    print(json.dumps(dict(bound_people=result['bound_people'], unbound=result['unbound_source_records'],
                         retained=223, added_source_row_id='cnblogs-line-0229'), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
