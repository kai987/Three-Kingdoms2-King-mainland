#!/usr/bin/env python3
"""Publish dated v8 chapters without changing any released catalog."""
from collections import Counter
from copy import deepcopy
from build_campaigns import read, write
from remake.travel import build_routes

NORTH = {'wei','anping','changshan','zhongshan','bohai','pingyuan','fanyang',
         'dai','taiyuan','xihe','shangdang','yan','yuyang','shanggu'}
DEFENSE = {
    'zhao': ['耿武','阴夔','李孚','审荣','吕旷','吕翔'],
    'julu': ['韩猛','高览','蒋义渠','眭元进','韩莒子','吕威璜'],
    'hejian': ['焦触','张南','孙礼','田豫'],
    'qinghe': ['朱灵','崔琰','崔林','王经'],
    'yanmen': ['吕布','高干','郝昭','王凌'],
    'xinxing': ['郝昭','王凌','温恢','孙资','毕轨'],
}


def distribute(data, spec):
    """Defense design, not invented historical appointments or new officers."""
    counts = Counter(r['city'] for r in data['initial_officers'])
    people = {r['person_id']: r for r in data['people']}
    cities = {c['id']: c for c in data['cities']}
    audit = []
    ordered = sorted(spec['cities'], key=lambda c: c['id'] != 'yanmen')
    for city in ordered:
        key = city['id']; owner = data['initial_owners'].get(key)
        if key not in data['active_cities'] or owner == 'neutral': continue
        # Qian Zhao's Yanmen appointment is attested for the227 chapter.
        preferred = '牵招' if key == 'yanmen' and data['start_year'] == 227 else None
        approved = [preferred] if preferred else DEFENSE[key]
        candidates = [r for r in data['initial_officers'] if not r.get('ruler')
                      and r['city'] in NORTH and (counts[r['city']] > 1 or preferred)
                      and data['initial_owners'][r['city']] == owner
                      and people[r['person_id']]['name'] in approved]
        if not candidates: continue
        xy = cities[key]['position']
        row = min(candidates, key=lambda r: (
            approved.index(people[r['person_id']]['name']),
            sum((a-b)**2 for a,b in zip(cities[r['city']]['position'], xy)),
            r['person_id']))
        origin = row['city']; row['city'] = key
        counts[origin] -= 1; counts[key] += 1
        basis = 'attested_yanmen_post_227' if preferred and people[row['person_id']]['name'] == preferred else 'authored_regional_defense_not_attested_post'
        record = dict(person_id=row['person_id'], name=people[row['person_id']]['name'],
                      origin=origin, city=key, faction=owner, basis=basis)
        audit.append(record)
        assignment = data['era_assignments'][row['person_id']]
        assignment.update(city=key, placement_basis=basis, posting_reference=record)
    return audit


def build():
    previous = read('game/data/main-scenarios-v7/index.json')
    spec = read('game/config/hebei-shanxi.json')
    route_spec = read('game/config/travel-map.json')
    route_spec['connections'] += spec['connections']
    paths, summary = [], []
    for filename in previous['catalogs']:
        data = deepcopy(read('game/data/' + filename)); year = data['start_year']
        chapter = next(s for s in spec['scenarios'] if (s['year'],s['month']) == (year,data['start_month']))
        data.update(id=data['id'].replace('-v7','-v8'), content_generation=8,
                    city_count=spec['city_count'], city_foundings=spec['city_foundings'],
                    added_city_ids=[c['id'] for c in spec['cities']],
                    regional_roads=spec['connections'], city_label_offsets=spec['label_offsets'])
        data['city_history'] = {}
        normal = read('game/config/city-economy.json')['tiers']['normal']
        for row in spec['cities']:
            key = row['id']
            data['cities'].append({k:deepcopy(row[k]) for k in ('id','name','position','terrain')})
            data['city_coordinates'][key] = row['coordinates']
            data['city_profiles'][key] = dict(tier='normal', label='普通城',
                basis='dated_northern_expansion_game_baseline', is_SAN14_starting_resources=False)
            data['initial_city_resources'][key] = deepcopy(normal['initial'])
            data['city_income'][key] = deepcopy(normal['monthly'])
            if key in chapter['owners']:
                data['active_cities'].append(key)
                data['initial_owners'][key] = chapter['owners'][key]
            data['city_history'][key] = dict(detail=row['detail'], names=row['names'], sources=row['sources'],
                opening=chapter['history'].get(key,dict(owner=None,basis='not_yet_established',
                    note='215年以前不设新兴郡城，地理区域仍由原晋阳节点表示。',sources=row['sources'])))
        for route in spec['connections']:
            edge = [route['from'],route['to']]
            if not any(set(e) == set(edge) for e in data['links']): data['links'].append(edge)
        data['travel_routes'] = build_routes(data, route_spec)
        garrisons = distribute(data, spec)
        for key, history in data['city_history'].items():
            history['garrisons'] = [r for r in garrisons if r['city'] == key]
        data['northern_expansion'] = dict(schema=spec['schema'], garrison_policy=spec['garrison_policy'],
            garrisons=garrisons, source_policy=spec['source_policy'], limits=spec['limits'])
        data['main_scenario'].update(setup_basis='independent_dated_106_city_adaptation',
            city_chronology_note='新增赵、钜鹿、河间、甘陵／清河、雁门、新兴；215年前开放105城，215年起106城。城名随年代更新；史料与开局归属说明见城池资料。')
        data['era_metadata']['main_scenario'] = data['main_scenario']
        data['design_notes'] = [n.replace('96城版','扩展地图版').replace('96节点疆界','地图节点疆界')
                                for n in data['design_notes'] if not n.startswith('已发布')]
        data['design_notes'] += [data['main_scenario']['city_chronology_note'],
            '新兴215年建郡继承当时晋阳实际归属，并从晋阳分出四分之一钱粮与预备兵；不强制改回历史势力，不复制武将或兵员。',
            '190、191年雁门为无法对应现有可玩势力的地方汉郡，以中立表示；不是史实无人管辖。其余新城按每个剧本独立配置归属。',
            '新增城驻防由现有同势力北方武将调配，不增加人物、带兵总数或虚构郡守任命；227年牵招驻雁门有史料依据。',
            '保留原100城位置、1352×1024底图与61份已发布目录；旧存档不自动增加城市，新内容需新开v8战役。']
        path = filename.replace('main-scenarios-v7/','main-scenarios-v8/')
        write('game/data/' + path, data); paths.append(path)
        prior = next(s for s in previous['summary'] if s['id'].replace('-v7','-v8') == data['id'])
        summary.append(dict(prior,id=data['id'],active_cities=len(data['active_cities']),
                            total_cities=spec['city_count'],garrisons=garrisons))
    result = dict(schema='main-scenario-index-v1', catalogs=paths,
                  default=previous['default'].replace('-v7','-v8'),summary=summary)
    write('game/data/main-scenarios-v8/index.json',result)
    return result


if __name__ == '__main__':
    import json
    result = build()
    print(json.dumps(dict(catalogs=len(result['catalogs']),default=result['default'])))
