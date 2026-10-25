#!/usr/bin/env python3
"""Validate reviewed historical openings and render a deterministic audit.

This checks that authored review decisions reached the current catalogs. It
does not certify every mapped city/month as an attested historical posting.
--check is read-only; no game, save, network or generated source is executed.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / 'game/config/references/scenario-history-review.json'
REPORT_JSON = ROOT / 'docs/scenario-history-audit-20261025.json'
REPORT_MD = ROOT / 'docs/scenario-history-audit-20261025.md'
CATEGORIES = ('史料による所属・年代', '演義・ゲーム互換の配置', '地域代理・本作の配置', '実効支配・月界の未確定事項')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def urls(values, label):
    require(isinstance(values, list) and bool(values), label + ': source URLs required')
    for value in values:
        require(isinstance(value, str) and urlparse(value).scheme in ('https', 'http')
                and bool(urlparse(value).netloc), label + ': invalid source URL')


def latest(rows, field):
    """A person may be moved twice during a review; verify its final decision."""
    result = {}
    for row in rows:
        require(isinstance(row, dict) and row.get(field), 'Missing review key: ' + field)
        result[row[field]] = row
    return [result[key] for key in sorted(result)]


def category(certainty):
    value = certainty.lower()
    if 'novel' in value or 'romance' in value:
        return CATEGORIES[1]
    if any(word in value for word in ('unresolved', 'contested', 'uncertain', 'unknown', 'pending')):
        return CATEGORIES[3]
    if any(word in value for word in ('proxy', 'mapping', 'inference', 'authorial', 'relocation')):
        return CATEGORIES[2]
    return CATEGORIES[0]


def display_names(catalog, presentation):
    date = (catalog['start_year'], catalog['start_month'])
    result = {}
    for city in catalog['cities']:
        row = presentation.get(city['id'], {})
        name = row.get('displayName', city['name'])
        for year in (212, 221):
            if date[0] < year:
                name = row.get('before' + str(year), name)
        for period in catalog.get('city_history', {}).get(city['id'], {}).get('names', []):
            start = tuple(period.get('from_date', [period.get('start', 1), 1]))
            end = tuple(period.get('to_date', [period.get('end', 9999), 12]))
            if start <= date <= end:
                name = period['name']
        result[city['id']] = name
    return result


def opening_people(catalog, active, factions):
    people = {row['person_id']: row for row in catalog['people']}
    require(len(people) == len(catalog['people']), catalog['id'] + ': duplicate person IDs')
    actual = {}
    for kind, rows in (('serving', catalog['initial_officers']), ('free', catalog['initial_free_officers'])):
        for row in rows:
            ident, city = row['person_id'], row['city']
            require(ident in people and ident not in actual, catalog['id'] + ': duplicate/unknown opening person ' + ident)
            require(city in active, catalog['id'] + ': person at inactive city ' + ident)
            faction = catalog['initial_owners'][city] if kind == 'serving' else None
            if kind == 'serving':
                require(faction in factions, catalog['id'] + ': serving person has no owning faction ' + ident)
                era = catalog.get('era_assignments', {}).get(ident, {})
                require(era.get('faction') == faction and era.get('city') == city,
                        catalog['id'] + ': opening owner and era assignment differ ' + ident)
            actual[ident] = dict(person_id=ident, name=people[ident]['name'],
                                 status=kind, faction=faction, city=city,
                                 ruler=bool(row.get('ruler', False)), appearance_basis='explicit_' + kind)
    # A new campaign also materializes eligible dated free appearances. Include
    # these in the ledger, rather than confusing the explicit seed list with
    # the complete opening roster. This reads metadata only and draws no RNG.
    date = (catalog['start_year'], catalog['start_month'])
    for pid, person in people.items():
        if pid in actual:
            continue
        if any(person['profile'].get(field) is None for field in
               ('health_max', 'martial_strength', 'intellect', 'virtue', 'terrain_affinity')):
            continue
        city = catalog.get('appearance_locations', {}).get(pid)
        windows = catalog.get('appearance_windows', {}).get(pid)
        resolve_death_year = False
        if windows is not None:
            current = next((row for row in windows if tuple(row['start']) <= date <= tuple(row['end'])), None)
            if current is None:
                continue
            city = current['city']
            resolve_death_year = current.get('resolve_death_year') is True
        birth, service, death = (person.get(field) for field in ('birth_year', 'service_year', 'death_year'))
        if (None in (birth, service, death) or birth > date[0] or service > date[0]
                or death < date[0] or (death == date[0] and not resolve_death_year) or city not in active):
            continue
        actual[pid] = dict(person_id=pid, name=person['name'], status='free', faction=None,
                           city=city, ruler=False, appearance_basis='dated_auto_appearance')
    return people, actual


def border_links(catalog, active):
    """List network adjacency, not a reconstructed geographic frontier line."""
    edges = {}

    def edge(a, b, origin, mode=None):
        if a == b or a not in active or b not in active:
            return
        a, b = sorted((a, b))
        if catalog['initial_owners'][a] == catalog['initial_owners'][b]:
            return
        row = edges.setdefault((a, b), dict(cities=[a, b],
            owners=[catalog['initial_owners'][a], catalog['initial_owners'][b]],
            modes=set(), link_sources=set()))
        row['link_sources'].add(origin)
        if mode:
            row['modes'].add(mode)

    for field in ('links', 'sea_links'):
        for pair in catalog.get(field, []):
            require(isinstance(pair, list) and len(pair) == 2,
                    catalog['id'] + ': invalid ' + field + ' pair')
            edge(*pair, field)
    for route in catalog.get('travel_routes', []):
        edge(route['from'], route['to'], 'travel_routes', route['mode'])
    return [dict(row, modes=sorted(row['modes']), link_sources=sorted(row['link_sources']))
            for _, row in sorted(edges.items())]


def compile_report():
    review = read(REFERENCE)
    require(review.get('schema') == 'tk2-scenario-history-review-v1', 'Unknown historical review schema')
    require(review.get('revision'), 'Historical review revision required')
    require(isinstance(review.get('limits'), list) and bool(review['limits']), 'Review limits required')
    for group, values in review['sources'].items():
        urls(values, 'source group ' + group)
    index = read(ROOT / 'game/config/campaigns/index.json')
    compiled_index = read(ROOT / 'game/data/campaigns/index.json')
    presentation_path = ROOT / 'game/assets/map-presentation.json'
    presentation = read(presentation_path)['city_names']
    entries = index['scenarios']
    require(len(entries) == 29 and len({row['id'] for row in entries}) == 29,
            'Require 29 unique current campaign sources')
    expected_files = {'campaigns/' + Path(row['file']).name for row in entries}
    require(set(compiled_index['catalogs']) == expected_files
            and len(compiled_index['catalogs']) == 29, 'Compiled campaign index is stale')
    catalogs = {}
    paths = {}
    for entry in entries:
        path = ROOT / 'game/data/campaigns' / Path(entry['file']).name
        data = read(path)
        require(data['id'] == entry['id'] and [data['start_year'], data['start_month']]
                == [entry['year'], entry['month']], entry['id'] + ': compiled identity/date mismatch')
        catalogs[data['id']], paths[data['id']] = data, path
    fictional = {ident for ident, data in catalogs.items()
                 if data.get('main_scenario', {}).get('fictional')
                 or data.get('main_scenario', {}).get('group') == 'if'}
    excluded = review['fictional_excluded']
    require(len(excluded) == 6 and len(set(excluded)) == 6 and set(excluded) == fictional,
            'Exactly the six current fictional scenarios must be excluded')
    decisions = review['scenarios']
    require(len(decisions) == 23 and len({row['id'] for row in decisions}) == 23
            and {row['id'] for row in decisions} == set(catalogs) - fictional,
            'Historical review must cover all 23 historical scenarios exactly once')
    by_id = {row['id']: row for row in decisions}
    reports = []
    counts = Counter()
    for entry in entries:
        ident = entry['id']
        if ident in fictional:
            continue
        data, decision = catalogs[ident], by_id[ident]
        require(decision['date'] == [data['start_year'], data['start_month']], ident + ': review date mismatch')
        active = set(data['active_cities'])
        require(len(active) == len(data['active_cities']), ident + ': duplicate active city')
        city_rows = {row['id']: row for row in data['cities']}
        factions = {row['id']: row for row in data['factions']}
        require(len(factions) == len(data['factions']) and active <= set(city_rows), ident + ': invalid city/faction identities')
        removed_factions = decision.get('removed_factions', [])
        require(all(fid not in factions for fid in removed_factions),
                ident + ': a reviewed retired faction remains selectable')
        for city in active:
            require(data['initial_owners'].get(city) in {*factions, 'neutral'}, ident + ': unknown city owner ' + city)
        names = display_names(data, presentation)
        people, opening = opening_people(data, active, factions)
        evidence_counts = Counter(row['placement_review']['historical_certainty']
                                  for row in data['era_assignments'].values())
        require(data['placement_completion']['reference_classes'] == dict(evidence_counts),
                ident + ': placement evidence summary is stale')
        changes = {field: latest(decision.get(field, []), key) for field, key in
                   (('new_factions', 'id'), ('city_changes', 'city'), ('officer_changes', 'person_id'))}
        for field, rows in changes.items():
            for row in rows:
                urls(row.get('source_urls'), ident + ' ' + field)
                require(isinstance(row.get('certainty'), str) and row['certainty'], ident + ': missing certainty')
        # owner_expectations is the final decision. A city can have intermediate
        # changes, such as restoring Ma Chao territory before separating Han Sui.
        expected_owners = {row['city']: row['owner'] for row in changes['city_changes']}
        expected_owners.update(decision.get('owner_expectations', {}))
        for city, owner in expected_owners.items():
            require(city in active and data['initial_owners'][city] == owner,
                    f'{ident}: final owner mismatch for {city}: expected {owner!r}, got {data["initial_owners"].get(city)!r}')
        for row in changes['new_factions']:
            fid, pid, city = row['id'], row['person_id'], row['city']
            require(fid in factions and city in active, ident + ': missing new faction ' + fid)
            require(factions[fid]['city'] == city and data['initial_owners'][city] == fid,
                    ident + ': new faction capital mismatch ' + fid)
            actual = opening.get(pid)
            require(actual and actual['faction'] == fid and actual['city'] == city and actual['ruler'],
                    ident + ': new faction ruler is not actually stationed in its capital: ' + pid)
            require(data['faction_rulers'].get(fid) == next(i for i, p in enumerate(data['people'])
                    if p['person_id'] == pid), ident + ': faction ruler runtime identity mismatch ' + fid)
        for row in changes['officer_changes']:
            pid, faction, city = row['person_id'], row.get('faction'), row.get('city')
            require(pid in people, ident + ': reviewed person missing from pool ' + pid)
            actual = opening.get(pid)
            if city is None:
                require(actual is None, ident + ': excluded person remains at opening ' + pid)
            else:
                require(actual is not None and actual['faction'] == faction and actual['city'] == city,
                        f'{ident}: final person placement mismatch for {pid}: expected {(faction, city)!r}, got {actual!r}')
                era = data.get('era_assignments', {}).get(pid, {})
                require(era.get('city') == city and era.get('faction') == faction,
                        ident + ': era assignment differs from actual opening ' + pid)
        city_changes = []
        for change in changes['city_changes']:
            before = next(row.get('before') for row in decision['city_changes'] if row['city'] == change['city'])
            city_changes.append(dict(change, before=before, owner=data['initial_owners'][change['city']]))
        changes['city_changes'] = city_changes
        faction_rows = []
        for fid, faction in factions.items():
            ruler_index = data['faction_rulers'][fid]
            require(isinstance(ruler_index, int) and 0 <= ruler_index < len(data['people']),
                    ident + ': invalid faction ruler index')
            ruler = data['people'][ruler_index]
            faction_rows.append(dict(id=fid, ruler=ruler['name'], person_id=ruler['person_id'],
                city=faction['city'], city_name=names[faction['city']],
                city_count=sum(data['initial_owners'][city] == fid for city in active),
                officer_count=sum(person['faction'] == fid for person in opening.values())))
        faction_rows.sort(key=lambda row: row['id'])
        borders = border_links(data, active)
        roster = [{**opening[pid], 'city_name': names[opening[pid]['city']]}
                  for pid in sorted(opening)]
        spotlight = []
        if decision['date'] == [212, 12]:
            for pid in ('san14-candidate-0632', 'san14-candidate-0854', 'san14-candidate-0274',
                        'san14-candidate-0771', 'san14-candidate-0760', 'san14-candidate-0770',
                        'san14-candidate-0393', 'san14-candidate-0078'):
                person = people[pid]
                spotlight.append(opening.get(pid, dict(person_id=pid, name=person['name'],
                    status=data.get('era_assignments', {}).get(pid, {}).get('status', 'not_in_opening'),
                    faction=None, city=None)))
        row = dict(id=ident, date=decision['date'], title=data['title'],
            title_ja=data.get('main_scenario', {}).get('title_i18n', {}).get('ja', decision['title']),
            catalog_file=paths[ident].relative_to(ROOT).as_posix(),
            catalog_sha256=sha256(paths[ident].read_bytes()).hexdigest(),
            factions=faction_rows, city_count=len(active),
            city_owners=[dict(city=city, name=names[city], owner=data['initial_owners'][city],
                neutral_label=data.get('city_history', {}).get(city, {}).get('neutral_label'))
                for city in sorted(active)],
            boundary_links=borders, opening_officers=roster,
            new_factions=changes['new_factions'], removed_factions=removed_factions,
            city_changes=changes['city_changes'],
            officer_changes=changes['officer_changes'], owner_expectations=expected_owners,
            notable_exclusions=spotlight, notes=decision.get('notes', []))
        reports.append(row)
        counts.update(cities=len(active), factions=len(factions), boundary_links=len(borders),
                      opening_officers=len(opening), new_factions=len(changes['new_factions']),
                      city_changes=len(changes['city_changes']), officer_changes=len(changes['officer_changes']),
                      city_change_records=len(decision.get('city_changes', [])),
                      officer_change_records=len(decision.get('officer_changes', [])))
    return dict(schema='tk2-scenario-history-audit-v1', review_revision=review['revision'],
        review_file=REFERENCE.relative_to(ROOT).as_posix(), review_sha256=sha256(REFERENCE.read_bytes()).hexdigest(),
        presentation_sha256=sha256(presentation_path.read_bytes()).hexdigest(),
        scope='Regional review and current-data consistency, not a complete attested city/month prefect list or a SAN14 export.',
        boundary_definition='Different opening owners connected by links, sea_links or travel_routes; each unordered city pair is listed once. These are network borders, not geographic administrative boundary polygons.',
        historical_count=23, fictional_excluded=sorted(fictional),
        summary=dict(counts), sources=review['sources'], limits=review['limits'], scenarios=reports)


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def source_links(values):
    return '、'.join(f'[史料{index}]({url})' for index, url in enumerate(dict.fromkeys(values), 1))


def markdown(report):
    summary = report['summary']
    conversion = read(ROOT / 'game/locales/zh-hant.json')['stages']

    def human(value):
        """Use traditional forms for Chinese proper names, not Japanese prose."""
        text = str(value)
        for stage in conversion:
            phrases, characters = stage['phrases'], stage['characters']
            if text in phrases:
                text = phrases[text]
            else:
                text = ''.join(characters.get(char, char) for char in text)
        return text

    lines = [
        '# 史実シナリオの勢力・境界都市レビュー（2026年10月25日）', '',
        '現在の史実23本を対象に、地方勢力、都市の初期所属と武将配置を確認する資料です。仮想6本は領土修正の対象から外します。'
        '地域単位の史料を現在の地図へ対応させたレビューであり、**すべての都市・すべての月の太守名簿が確定したという意味ではありません**。', '',
        '生成元は [レビュー決定表](../game/config/references/scenario-history-review.json)、'
        '照合結果は [全都市・境界経路・人物のJSON](scenario-history-audit-20261025.json)です。'
        '同じ人物を一度の修正で複数回動かした場合は最後の記録を採用し、都市は最終的な `owner_expectations` と照合します。', '',
        f"今回の記録は追加勢力{summary['new_factions']}件（シナリオごとの組合せ）、都市延べ{summary['city_change_records']}件"
        f"（最終の都市・シナリオ単位{summary['city_changes']}件）、人物延べ{summary['officer_change_records']}件"
        f"（同一シナリオ内の重複整理後{summary['officer_changes']}件）です。"
        '全都市一覧は変更対象以外も含みますが、変更のない都市を新たに逐月確証した件数とは数えません。', '',
        '## 対象と判定の意味', '',
        '| 区分 | 扱い |', '| --- | --- |',
        '| 史料 | 原典で確認できる所属・出来事。年が分かっても月や旬まで分かるとは限りません。 |',
        '| 演義 | 『三國演義』や既存ゲームの人物関係を遊びのため残したもの。正史の駐将名簿とは区別します。 |',
        '| 地域代理・本作配置 | 郡・地域の記録を固定都市へ写したものや、史料にない具体的駐防。 |',
        '| 待考 | 実効支配や移管月が未確定。中立表示も無人や人口ゼロを意味しません。 |', '',
        '207年の章陵を劉備に残す指定、208年8月を章陵帰曹の境界とする指定、小沛／譙郡の地域代理など、'
        '従来の明示されたゲーム設定は維持します。変更は新しい戦役の開始時に適用し、プレイ中の領土を史実へ強制的に戻しません。', '',
        '## 23本の開幕勢力', '',
        '| 開始年月 | シナリオ | 勢力の君主（本拠） | 都市／境界接続 | 今回の修正件数 |',
        '| --- | --- | --- | --- | --- |',
    ]
    for row in report['scenarios']:
        factions = '、'.join(f"{human(f['ruler'])}（{human(f['city_name'])}）" for f in row['factions'])
        amount = f"勢力{len(row['new_factions'])}・都市{len(row['city_changes'])}・人物{len(row['officer_changes'])}"
        lines.append('| ' + ' | '.join(map(cell, (f"{row['date'][0]}年{row['date'][1]}月", row['title_ja'],
            factions, f"{row['city_count']}／{len(row['boundary_links'])}", amount))) + ' |')
    lines += ['', '件数は本作データの変更記録です。同じ勢力を複数の年代に追加した場合は各開幕で1件と数えます。'
              'JSONは全開放都市の所有者、各勢力の全開幕武将、異なる所有者を結ぶ接続を収録します。'
              '境界接続は陸路・内河・海路の都市間隣接であり、行政区の境界線を復元したものではありません。', '']
    for section in CATEGORIES:
        lines += ['## ' + section, '']
        any_rows = False
        for row in report['scenarios']:
            names = {city['city']: city['name'] for city in row['city_owners']}
            chosen = []
            for change in row['city_changes']:
                if category(change['certainty']) == section:
                    chosen.append(f"都市 {human(names[change['city']])} `{change['city']}`：{change.get('before')} → {change['owner']}。"
                                  f"{change['note']} {source_links(change['source_urls'])}")
            for change in row['officer_changes']:
                if category(change['certainty']) == section:
                    after = change.get('faction') or ('在野' if change.get('city') else '開幕対象外')
                    location = names.get(change.get('city'), change.get('city') or '―')
                    chosen.append(f"人物 {human(change['name'])} `{change['person_id']}`：{after}／{human(location)}。"
                                  f"{change['note']} {source_links(change['source_urls'])}")
            if chosen:
                any_rows = True
                lines += [f"### {row['date'][0]}年{row['date'][1]}月・{row['title_ja']}", '']
                lines.extend('- ' + text for text in chosen)
                lines.append('')
        if not any_rows:
            lines += ['この区分の新規修正はありません。', '']
    shu = next(row for row in report['scenarios'] if row['date'] == [212, 12])
    lines += ['## 212年12月・入蜀争奪戦', '',
        '『資治通鑑』巻66の建安十七年十二月は、劉備が葭萌から南へ兵を返し、張松・楊懐・高沛の死を経て'
        '涪城に進んだ段階を記します。本作はこの出来事の後を開幕に採ります。**具体的な上・中・下旬は原典で確定したものではありません**。'
        '劉備が益州全域を領有した214年の配置を前倒ししません。'
        '[巻66](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[先主伝](https://zh.wikisource.org/wiki/三國志/卷32)、'
        '[霍峻伝](https://zh.wikisource.org/wiki/三國志/卷41)', '',
        '| 初期所属 | 開放都市 |', '| --- | --- |']
    for faction in [*shu['factions'], dict(id='neutral', ruler='中立・地方実控未確定')]:
        cities = [city for city in shu['city_owners'] if city['owner'] == faction['id']]
        if cities:
            listed = '、'.join(human(city['name']) + (f"（{city['neutral_label']}）" if city.get('neutral_label') else '') for city in cities)
            ruler_label = faction['ruler'] if faction['id'] == 'neutral' else human(faction['ruler'])
            lines.append(f"| {cell(ruler_label)}（{len(cities)}） | {cell(listed)} |")
    lines += ['', '上表は最終データの全都市一覧です。史料の州・郡・客軍の位置を一都市一所属へ写した配置も含みます。'
        '韓遂は馬騰・馬超の通常配下としてまとめず、212年末の馬超は固定郡城の証明がない残部として在野に残します。'
        '天水の韋康は『通鑑』の213年冀城陥落の系年を採りますが、『三國志』楊阜伝の十七年記とは相違があり、'
        'この選択を無条件に原典一致とはしません。皖城・廬江の移管月も214年の落城から逆算して確定しません。', '',
        '| 今回確認した人物 | 所属 | 駐点／扱い | 判定 |', '| --- | --- | --- | --- |']
    names = {city['city']: city['name'] for city in shu['city_owners']}
    for person in shu['officer_changes']:
        lines.append('| ' + ' | '.join(map(cell, (human(person['name']), person.get('faction') or '在野',
            human(names[person['city']]) if person.get('city') in names else '開幕対象外', person['certainty']))) + ' |')
    lines += ['', '張松・楊懐・高沛は上記の開幕段階では既に没しています。馬騰・馬休・馬鉄の212年5月の死も、'
              '211年潼関シナリオで存命であることとは分けます。諸葛亮・張飛・趙雲らの213年の入蜀を先取りしません。', '',
              '## 赤壁の荊南四郡', '',
              '人数は君主を含みます。史実の地方行政官を可操作の勢力として分け、演義人物も使って少人数勢力を構成します。'
              '全員が正史で同じ太守の部下だったとする名簿ではありません。', '',
              '| 郡・君主 | 開幕武将 | 人数 |', '| --- | --- | --- |']
    red = next(row for row in report['scenarios'] if row['id'] == 'mainland208-10')
    for fid, label in (('han_xuan', '長沙・韓玄'), ('jin_xuan', '武陵・金旋'),
                       ('zhao_fan', '桂陽・趙範'), ('liu_du', '零陵・劉度')):
        roster = [human(person['name']) for person in red['opening_officers'] if person['faction'] == fid]
        lines.append(f"| {label} | {cell('、'.join(roster))} | {len(roster)} |")
    lines += ['', '黄忠が曹操の荊州確保後に韓玄の指揮下にあったことは『黄忠伝』に記されています。'
        '一方、魏延の韓玄配下、鞏志、陳応・鮑隆、劉賢・邢道栄などの配属は演義・ゲーム互換です。劉磐は黄忠と攸県を守った原典記録があっても、'
        'この月の職位や韓玄の配下を断定せず長沙方面の在野とします。'
        '[先主伝](https://zh.wikisource.org/wiki/三國志/卷32)、[黄忠伝](https://zh.wikisource.org/wiki/三國志/卷36)、'
        '[『三國演義』第53回](https://zh.wikisource.org/wiki/三國演義/第053回)', '',
        '## 独立勢力にしていない地方勢力と未確定範囲', '',
        '- 張燕、烏丸、厳白虎、宋建や地方氐部は、各時期に現在の節点を一つ丸ごと与える証拠や人物・都市の対応が不足する場合、'
        '独立した都市勢力にしていません。不存在や、すべて曹操の直轄だったという意味ではありません。',
        '- 武都・陰平は215年以前の地方実控を中立で表す箇所があります。張魯・劉璋・曹操のどれかへ一律に塗り替える証明ではありません。',
        '- 221年の南中は名義上の蜀属と実効支配を分けます。張裔が223年まで数年呉にいた記録と、劉備死後に反乱をまとめる記録には、'
        '雍闓の初動年月を確定しにくい点があります。黄元の222年12月〜223年3月の反乱は、現在の開幕時点の間にあります。',
        '- 225年7月は孟獲を中心とする南中の戦局です。雍闓・高定・朱褒をこの月まで生存する君主として追加せず、牂牁と永昌の蜀方支配を分けます。',
        '- 士徽の反乱は226年で、225年7月の士燮や227年2月の呉属とは別です。263年5月は呂興に応じた交趾・九真・日南を地方叛軍として表し、'
        '264年の正式な魏の任命を先取りしません。呂興の独立した歴史人物IDと可操作勢力は未追加です。', '',
        '以下は決定表に保存した追加の制限です。', '']
    lines.extend('- ' + value for value in report['limits'])
    lines += ['', '## 再生成と照合', '', '```sh', 'python3 -B game/build_campaigns.py --check',
        'python3 -B tools/scenario-history/audit.py --write',
        'python3 -B tools/scenario-history/audit.py --check', '```', '',
        '`--check` はファイルを書き換えず、23本の漏れ・重複、仮想6本の除外、最終都市所属、追加勢力の君主と本拠、'
        '人物の最終所属・駐点、生成済みレポートの一致を検査します。乱数、プレイヤーのセーブ、ネットワークやゲーム命令は使いません。'
        '史料解釈自体の正しさを自動証明する検査ではありません。', '',
        '[2026年10月24日の19都市×19本レビュー](city-ownership-audit-20261024.md)は当時の基準として保存し、'
        '今回の23本の結果で過去の件数・年月を書き換えません。', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Read-only validation, including deterministic report parity')
    mode.add_argument('--write', action='store_true', help='Write the JSON and Japanese-primary Markdown reports (default)')
    args = parser.parse_args(argv)
    try:
        report = compile_report()
        outputs = ((REPORT_JSON, json.dumps(report, ensure_ascii=False, indent=2) + '\n'),
                   (REPORT_MD, markdown(report)))
        for path, value in outputs:
            if args.check:
                require(path.exists() and path.read_text(encoding='utf-8') == value,
                        str(path.relative_to(ROOT)) + ' is stale; run audit.py --write after rebuilding catalogs')
            else:
                path.write_text(value, encoding='utf-8')
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as error:
        print('Historical scenario audit failed: ' + str(error), file=sys.stderr)
        return 1
    print(json.dumps(dict(check=args.check, historical=23, fictional_excluded=6, **report['summary']), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
