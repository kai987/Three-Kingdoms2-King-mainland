#!/usr/bin/env python3
"""Import numerical SAN14 abilities from nine public tables; offline by default.

HTML snapshots live in ignored build/san14-stats. This importer never joins
homonyms by simplified name alone. Explicit disambiguation follows each table's
identity description, not the appearance of a shared stat tuple.
"""
from pathlib import Path
from collections import defaultdict
import argparse
import datetime
import hashlib
import json
import unicodedata
import urllib.request
from build_roster import Tables, load_converter

ROOT = Path(__file__).resolve().parents[2]
PARTS = ('a', 'ka', 'sa', 'ta', 'na', 'ha', 'ma', 'ya', 'ra')
ALIASES = {104: '楽綝', 152: '毌丘倹', 227: '嵆康', 228: '邢道栄', 830: '龐徳'}
# Official independent identities -> global source-table row, counted over the
# numeric rows only. Descriptions were inspected for faction/parent identity.
HOMONYMS = {173: (174, '黄巾'), 174: (175, '公孫康'),
            634: (636, '張昭'), 635: (637, '張延'),
            651: (653, '袁煕'), 652: (654, '蜀'),
            767: (769, '潘璋'), 768: (770, '蜀'),
            917: (917, '李厳'), 918: (918, '魏'), 919: (919, '袁術')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    cache = ROOT / 'build/san14-stats'
    cache.mkdir(parents=True, exist_ok=True)
    rows, sources = [], []
    for part in PARTS:
        url = f'https://sangokushi-fun.com/sangokushi14/san14-bushou-list-{part}-line/'
        path = cache / f'{part}.html'
        if args.fetch:
            path.write_bytes(urllib.request.urlopen(url, timeout=30).read())
        raw = path.read_bytes()
        parsed = Tables(); parsed.feed(raw.decode())
        count = 0
        for table in parsed.tables:
            for number, row in enumerate(table, 1):
                if len(row) < 6 or not all(v.isdigit() for v in row[1:6]):
                    continue
                count += 1
                rows.append({'source_name': row[0], 'source_url': url,
                             'source_table_row': number,
                             'stats': dict(zip(('leadership', 'martial_strength', 'intellect', 'politics', 'charisma'), map(int, row[1:6]))),
                             '_identity': row[6] if len(row) > 6 else ''})
        sources.append({'url': url, 'html_sha256': hashlib.sha256(raw).hexdigest(), 'numeric_rows': count})
    convert = load_converter()
    variants = str.maketrans({'関': '關', '沢': '澤', '黒': '黑', '歩': '步', '来': '來', '呉': '吳', '竜': '龍', '淩': '凌', '曽': '曾', '恵': '惠'})
    def norm(s): return convert(unicodedata.normalize('NFKC', s).translate(variants))
    index = defaultdict(set)
    for i, row in enumerate(rows): index[norm(row['source_name'])].add(i)
    official = json.loads((ROOT / 'expansion/officers/data/roster-candidates.json').read_text())['officers']
    result, used = [], set()
    for person in official:
        n = person['official_list_number']
        if n in HOMONYMS:
            row_number, identity = HOMONYMS[n]
            candidates = {row_number - 1}
            assert identity in rows[row_number - 1]['_identity'], (n, rows[row_number - 1])
            method = 'explicit_same_name_identity_crosswalk'
        else:
            names = [person[k] for k in ('name_traditional', 'name_simplified', 'name_japanese')]
            if n in ALIASES: names.append(ALIASES[n])
            candidates = set().union(*(index[norm(name)] for name in names))
            method = 'explicit_spelling_crosswalk' if n in ALIASES else 'unique_normalized_official_name'
        assert len(candidates) == 1, (n, candidates)
        ident = candidates.pop()
        assert ident not in used
        used.add(ident)
        row = {k: v for k, v in rows[ident].items() if not k.startswith('_')}
        assert all(type(v) is int and 1 <= v <= 100 for v in row['stats'].values())
        result.append({'person_id': person['person_id'], 'name': person['name_simplified'], **row,
                       'join_method': method, 'independently_verified': False})
    assert len(result) == len(used) == len(rows) == 1000
    output = {'schema': 'san14-third-party-numerical-abilities-v1', 'count': len(result),
              'basis': 'third_party_SAN14_base_ability_transcription; not official export',
              'source_review_date': '2026-10-21', 'source_manifests': sources,
              'identity_policy': 'official distinct person IDs retained;11 homonyms explicitly crosswalked; no name-only dedup',
              'license_note': 'Numerical facts with source attribution; no portraits, prose biographies or game binaries copied.',
              'abilities': result}
    target = ROOT / 'expansion/officers/data/san14-abilities.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'count': len(result), 'explicit_homonyms': len(HOMONYMS), 'path': str(target)}, ensure_ascii=False))


if __name__ == '__main__': main()
