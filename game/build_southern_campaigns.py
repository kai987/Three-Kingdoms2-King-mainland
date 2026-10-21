#!/usr/bin/env python3
"""Dated Wu/Shu map nodes; retain every released catalog for old saves."""
from collections import Counter
from copy import deepcopy

from build_campaigns import read, write
from remake.garrison_postings import apply_postings, PROXY_SOURCE_CITIES
from remake.travel import build_routes


def build():
    previous = read('game/data/main-scenarios-v9/index.json')
    spec = read('game/config/shu-wu-expansion.json')
    route_spec = read('game/config/travel-map.json')
    route_spec['connections'] += read('game/config/hebei-shanxi.json')['connections'] + spec['connections']
    tiers = read('game/config/city-economy.json')['tiers']
    paths, summary = [], []
    for filename in previous['catalogs']:
        data = deepcopy(read('game/data/' + filename))
        year, month = data['start_year'], data['start_month']
        data.update(id=data['id'].replace('-v9','-v10'), content_generation=10,
                    city_count=spec['city_count'])
        data['city_coordinates'].update(spec['coordinate_overrides'])
        data['added_city_ids'] += [c['id'] for c in spec['cities']]
        data['regional_roads'] += deepcopy(spec['connections'])
        data['city_label_offsets'].update(spec['label_offsets'])
        opening = next(r for r in spec['scenarios'] if (r['year'],r['month'])==(year,month))
        for row in spec['cities']:
            key = row['id']
            tier = row.get('economy_tier','normal')
            economy = tiers[tier]
            data['cities'].append({k:deepcopy(row[k]) for k in ('id','name','position','terrain')})
            data['city_coordinates'][key] = row['coordinates']
            data['city_profiles'][key] = dict(tier=tier,label=economy['label'],
                basis='dated_southern_node_game_baseline',administrative_level=row['kind'],
                is_SAN14_starting_resources=False)
            data['initial_city_resources'][key] = deepcopy(economy['initial'])
            data['city_income'][key] = deepcopy(economy['monthly'])
            founding = row.get('founding')
            if founding:
                data['city_foundings'][key] = dict(year=founding['year'],month=founding['month'],
                    parent=row['parent'],resource_divisor=4,
                    precision=founding['precision'],date_note=founding['note'])
            active = not founding or (year,month)>=(founding['year'],founding['month'])
            if active:
                data['active_cities'].append(key)
                data['initial_owners'][key] = opening['owners'][key]
            history = dict(detail=row['detail'],names=row['names'],sources=row['sources'],garrisons=[],
                kind=row['kind'],founding=founding,
                opening=dict(owner=opening['owners'].get(key),
                    basis='dated_southern_chapter_territory_adaptation' if active else 'not_yet_open',
                    note=opening['notes'][key] if active else founding['note'],sources=row['sources']))
            data['city_history'][key] = history
        for route in spec['connections']:
            edge = [route['from'],route['to']]
            if any(set(e)==set(edge) for e in data['links']):
                raise ValueError('Duplicate southern connection')
            data['links'].append(edge)
        data['travel_routes'] = build_routes(data,route_spec)
        for faction in data['factions']:
            if faction['id'] in opening.get('ruler_seats',{}):
                faction['city'] = opening['ruler_seats'][faction['id']]
        # These are newly represented places, not aliases for another board city.
        aliases = dict(spec['source_city_aliases'])
        audit = apply_postings(data,source_aliases=aliases,
            proxy_names=PROXY_SOURCE_CITIES - set(aliases))
        names = {p['person_id']:p['name'] for p in data['people']}
        for record in audit['postings']:
            record['name'] = names[record['person_id']]
        data['garrison_audit'] = audit
        for key,history in data['city_history'].items():
            history['garrisons'] = [r for r in audit['postings'] if r['city']==key]
        counts = Counter(data['initial_owners'][r['city']] for r in data['initial_officers'])
        for faction in data['factions']:
            faction['initial_officers'] = counts[faction['id']]
        data['northern_expansion']['garrisons'] = [r for r in audit['postings'] if r['city'] in data['northern_expansion'].get('city_ids', ('zhao','julu','hejian','qinghe','yanmen','xinxing'))]
        data['southern_expansion'] = dict(schema=spec['schema'],city_ids=[c['id'] for c in spec['cities']],
            source_policy=spec['source_policy'],coordinate_policy=spec['coordinate_policy'],
            chronology_policy=spec['chronology_policy'],opening=opening,
            garrisons=[r for r in audit['postings'] if r['city'] in {c['id'] for c in spec['cities']}])
        note='蜀地新增葭萌／汉寿、涪县、宕渠、南广；武昌221年4月开放。临海、临川257年起、建安260年起、吴兴266年起在长期战役按配置开放；日期精度见城池说明。'
        data['main_scenario'].update(setup_basis='dated_shu_wu_115_node_adaptation',
            city_chronology_note=note)
        data['era_metadata']['main_scenario'] = data['main_scenario']
        data['design_notes'] = [n for n in data['design_notes'] if not n.startswith('地图位置与地形保持原样')]
        data['design_notes'] += [note,
            '新增蜀地节点为汉代已有县城或军镇，不把宕渠、南广同名郡的短期设废当作城市出现与消失。葭萌采用刘备据蜀后汉寿名称的年代约定，非确定改名年月。',
            '武昌按221年四月改名置郡开放（同年八月筑城）；临海、临川按257年二月。建安、吴兴的开城月为明确标注的玩法时间点，不冒充史料确月。',
            '长期新城继承其父城当前实际归属并分出四分之一资源，不强制历史征服、变更君主或复制武将；旧106城坐标、底图和所有旧目录保留。',
            '江夏旅行坐标采用夏口方向军事区域代理，与鄂州武昌分开；不是声称夏口城在184年已经筑成或江夏历年郡治固定于此。']
        path=filename.replace('main-scenarios-v9/','main-scenarios-v10/')
        write('game/data/'+path,data);paths.append(path)
        summary.append(dict(id=data['id'],year=year,month=month,title=data['main_scenario']['title'],
            group=data['main_scenario']['group'],factions=len(data['factions']),
            active_cities=len(data['active_cities']),total_cities=spec['city_count'],
            serving=len(data['initial_officers']),free=len(data['initial_free_officers'])))
    result=dict(schema='main-scenario-index-v1',catalogs=paths,
        default=previous['default'].replace('-v9','-v10'),summary=summary)
    write('game/data/main-scenarios-v10/index.json',result)
    return result


if __name__=='__main__':
    import json
    result=build()
    print(json.dumps(dict(catalogs=len(result['catalogs']),default=result['default'])))
