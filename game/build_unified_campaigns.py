#!/usr/bin/env python3
"""Unify dated starts and reviewed postings without rewriting released saves."""
from collections import Counter
from copy import deepcopy

from build_campaigns import build_era, read, write
from remake.garrison_postings import apply_postings


def restore_extra_chapter(year):
    """Bring unique older dates onto the current map and completed profiles."""
    base = read('game/data/main-scenarios-v8/238-01.json')
    spec = read('game/config/campaign-generation-v3.json')
    spec['city_capacity'] = 30
    era = deepcopy(next(e for e in spec['eras'] if e['year'] == year))
    used = {city for f in era['factions'] for city in f['cities']}
    extra = set(base['initial_owners']) - used
    # These ten board nodes are northern/western additions to the old96 map.
    northern = {'xiping','zhangye','jiuquan','dunhuang','zhao','julu',
                'hejian','qinghe','yanmen','xinxing'}
    next(f for f in era['factions'] if f['id'] == 'wei')['cities'] += sorted(extra & northern)
    roster = {p['person_id']: p for p in read('expansion/officers/data/roster-candidates.json')['officers']}
    postings = read('game/config/era-postings.json')['postings'] + read('game/config/era-postings-v3.json')['postings']
    data = build_era(base, roster, era, spec, postings)
    data['main_scenario'] = dict(group='supplement', title=era['title'], adaptation=True,
        summary='合并旧版独有年代，使用统一地图、千人属性库、30人容量与行军规则。',
        official_source=None, setup_basis='retained_unique_legacy_date',
        roster_complete=False, profiles_complete=True)
    # Opening status is chapter-specific, not the238 metadata inherited above.
    for key, history in data['city_history'].items():
        history['opening'] = dict(owner=data['initial_owners'][key],
            basis='retained_legacy_date_with_current_board_adaptation',
            note='旧版独有年代沿用原势力配置；新增北方节点按当年曹魏区域补入。',
            sources=history['sources'])
        history['garrisons'] = []
    data['northern_expansion']['garrisons'] = []
    data['coverage']['pending_history'] = 0
    return data


def revise_184(data, spec):
    """SAN14 opening factions are game settings, not actual184 sovereignty."""
    factions = deepcopy(spec['factions'])
    owners = {key: 'neutral' for key in data['active_cities']}
    for faction in factions:
        for city in faction.pop('cities'):
            if owners[city] != 'neutral':
                raise ValueError('Overlapping reviewed184 city')
            owners[city] = faction['id']
    by_ruler = {f['source_ruler']: f for f in factions}
    people = {p['person_id']: p for p in data['people']}
    for row in data['initial_officers']:
        assignment = data['era_assignments'][row['person_id']]
        faction = by_ruler[assignment['source_ruler']]
        row['city'] = faction['city']
        row['ruler'] = people[row['person_id']]['name'] == faction['captain']
        assignment.update(faction=faction['id'], city=row['city'], membership_revision=None)
    data.update(factions=[{k:v for k,v in f.items() if k != 'source_ruler'} for f in factions],
        initial_owners=owners,
        faction_rulers={f['id']:next(p['runtime_id'] for p in people.values() if p['name']==f['captain']) for f in factions})
    data['era_metadata'].update(membership_revisions=[], merged_source_groups={},
        territory_review=spec['source_boundary'])
    for key, owner in owners.items():
        history = data['city_history'].setdefault(key, dict(detail='', names=[], sources=spec['sources']))
        history['opening'] = dict(owner=owner, basis='reviewed_SAN14_opening_adapted_to_expanded_board',
            note=spec['source_boundary'], sources=spec['sources'])
        history['garrisons'] = []
    data['main_scenario']['summary'] = '参考《三国志14》九势力17城开局，其余扩展节点留空；这属于游戏开局设定。'


def apply_reviewed_sources(data, spec):
    people = {}
    for person in data['people']:
        people.setdefault(person['name'], []).append(person['person_id'])
    count = 0
    for record in spec['postings']:
        if (record['year'], record['month']) != (data['start_year'], data['start_month']):
            continue
        if len(people[record['name']]) != 1:
            raise ValueError('Reviewed posting needs an unambiguous person identity')
        pid = people[record['name']][0]
        assignment = data['era_assignments'][pid]
        if assignment.get('source_ruler') != record['source_ruler']:
            continue
        # Source city is evidence for placement, never authority to change sides.
        assignment.update(source_city=record['city_source_name'], source_city_reference=record)
        count += 1
    return count


def build():
    previous = read('game/data/main-scenarios-v8/index.json')
    review = read('game/config/unified-scenario-review.json')
    postings = read('game/config/reviewed-san14-postings.json')
    starts = [deepcopy(read('game/data/' + path)) for path in previous['catalogs']]
    starts += [restore_extra_chapter(year) for year in (221,249)]
    paths, summary = [], []
    for data in sorted(starts, key=lambda d:(d['start_year'],d['start_month'])):
        year, month = data['start_year'], data['start_month']
        data.update(id=f'mainland{year}-{month:02d}-v9', content_generation=9)
        data['title'] = f'{year}年{month}月 · {data["main_scenario"]["title"]}'
        if year == 184:
            revise_184(data, review['184'])
        if year == 200:
            # Preserve Wei officers' allegiance when correcting the territory.
            for row in data['initial_officers']:
                if row['city'] == 'shangdang':
                    row['city'] = next(f['city'] for f in data['factions'] if f['id']=='wei')
                    data['era_assignments'][row['person_id']]['city'] = row['city']
            data['initial_owners']['shangdang'] = 'yuan_shao'
            data['city_history']['shangdang'] = dict(detail='上党郡节点', names=[],
                sources=review['200']['sources'], opening=dict(owner='yuan_shao',
                basis='reviewed_guandu_bingzhou_territory', note=review['200']['note'],
                sources=review['200']['sources']), garrisons=[])
        reviewed = apply_reviewed_sources(data, postings)
        audit = apply_postings(data)
        names = {p['person_id']:p['name'] for p in data['people']}
        for row in audit['postings']:
            row['name'] = names[row['person_id']]
        data['garrison_audit'] = audit
        # Older regional postings remain readable as historical provenance;
        # the actual initial roster is exclusively the new audited allocation.
        for key, history in data['city_history'].items():
            history['garrisons'] = [row for row in audit['postings'] if row['city']==key]
        data['northern_expansion']['garrisons'] = [row for row in audit['postings'] if row['city'] in data['added_city_ids']]
        data['northern_expansion']['garrison_policy'] = 'Current opening assignments are recorded in garrison_audit; source-first then same-faction frontier balance.'
        counts = Counter(data['initial_owners'][r['city']] for r in data['initial_officers'])
        for faction in data['factions']:
            faction['initial_officers'] = counts[faction['id']]
        data['coverage'].update(initial_serving=len(data['initial_officers']),
            planned_serving=len(data['initial_officers']),
            planned_max_city_roster=max(Counter(r['city'] for r in data['initial_officers']).values()))
        data['main_scenario'].update(setup_basis='unified_dated_board_with_reviewed_postings',
            garrison_basis='reviewed_source_city_then_even_enemy_frontier',
            reviewed_source_city_records=reviewed)
        data['era_metadata']['main_scenario'] = data['main_scenario']
        data['design_notes'] = [
            '统一13个不同年代开局：官方本篇7篇、加强版追加4篇，以及旧版独有221年与249年。重复版本只保留存档兼容，不再列为新开局。',
            '全库1000人保留既定德、武、知、体力和适性；开局仍受出生、出仕、死亡及势力配置约束，每城30人、战场每方10人。',
            '公开攻略逐将驻城仅作为注明来源的游戏配置参考；并非官方存档导出。无对应驻城者均匀补到与其他非中立势力接壤的城市，无此类前线或已满员时再均分到己方其他城市。',
            '君主固定在本剧本本营；227年牵招雁门任职保留。不会因驻城参考改变所属势力或生成新武将，30人满员时顺延到其他己城。',
            '184年改用九势力17城游戏开局，扩展节点不自动继承大范围汉廷领土；孙坚等独立集团是《三国志14》设定，不等于当年的独立国家。',
            '官渡开局上党改属袁绍。其余既有疆界仍为扩展地图玩法配置，尚未声称全部复刻《三国志14》。',
            '地图位置与地形保持原样；215年前105城，215年起106城。旧存档仍按原目录、容量和规则继续，不自动转换。']
        path = f'main-scenarios-v9/{year}-{month:02d}.json'
        write('game/data/' + path, data); paths.append(path)
        summary.append(dict(id=data['id'],year=year,month=month,title=data['main_scenario']['title'],
            group=data['main_scenario']['group'],factions=len(data['factions']),
            active_cities=len(data['active_cities']),serving=len(data['initial_officers']),
            free=len(data['initial_free_officers']),reviewed_source_city_records=reviewed))
    default='mainland217-07-v9'
    paths.sort(key=lambda p:p.endswith('/217-07.json'))
    result=dict(schema='main-scenario-index-v1',catalogs=paths,default=default,summary=summary)
    write('game/data/main-scenarios-v9/index.json',result)
    return result


if __name__ == '__main__':
    import json
    result=build()
    print(json.dumps(dict(catalogs=len(result['catalogs']),default=result['default'])))
