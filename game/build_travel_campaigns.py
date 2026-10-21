#!/usr/bin/env python3
"""Publish separate v7 campaigns; never rewrite the fifty released catalogs."""
from copy import deepcopy
from build_campaigns import read, write
from remake.travel import build_routes


def build():
    index = read('game/data/main-scenarios-v6/index.json')
    spec = read('game/config/travel-map.json')
    plan = read('expansion/map/city-map-city-sea-plan-v42.json')
    coordinates = {c['key']: [c['lon'], c['lat']] for c in plan['cities']}
    coordinates.update({c['id']: c['coordinates'] for c in spec['cities']})
    paths, summary = [], []
    for filename in index['catalogs']:
        data = deepcopy(read('game/data/' + filename))
        data['id'] = data['id'].replace('-v6', '-v7')
        data['content_generation'] = 7
        data['world'] = spec['world']
        data['travel_rules'] = spec['rules']
        for city in data['cities']:
            if city['id'] in spec['city_moves']: city['position']=spec['city_moves'][city['id']]
        for row in spec['cities']:
            key = row['id']
            data['cities'].append({k: row[k] for k in ('id', 'name', 'position', 'terrain')})
            data['active_cities'].append(key)
            # No unverified local governors or memberships are invented. Early
            # independent Hexi administrations are represented as neutral cities.
            owner = 'han' if data['start_year'] == 184 else 'wei' if data['start_year'] >= 217 else 'neutral'
            data['initial_owners'][key] = owner
            data['city_profiles'][key] = dict(tier='normal', label='普通城',
                basis='new_northwest_node_gameplay_adaptation', is_SAN14_starting_resources=False)
            normal = read('game/config/city-economy.json')['tiers']['normal']
            data['initial_city_resources'][key] = normal['initial']
            data['city_income'][key] = normal['monthly']
        data['city_coordinates'] = coordinates
        for route in spec['connections']:
            edge = [route['from'], route['to']]
            if not any(set(e) == set(edge) for e in data['links']):
                data['links'].append(edge)
        data['travel_routes'] = build_routes(data, spec)
        data['main_scenario']['setup_basis'] = 'independent_100_city_adaptation_not_SAN14_export'
        data['main_scenario']['travel'] = spec['schema']
        data['era_metadata']['main_scenario'] = data['main_scenario']
        data['design_notes'].extend([
            'v7新增西平、张掖、酒泉、敦煌，与姑臧均匀放置原图西北；仅姑臧调整位置，其余95城坐标、1352×1024尺寸与地形像素不变。新节点归属是玩法配置，早期河西独立郡守未另立势力，暂用无主城表示。',
            '江东经番禺、高凉、合浦抵交趾；东冶仅为沿海中转点。226年浮海进军有实绩；269年建安海道出兵次年退还，不能当作全线成功通航证据。具体分段为本作航路改编。',
            '行军按地理坐标、陆路绕行系数、沿海航点与地形速度估算天数，按30日月回合向上取整结算；不是史实复原的日行军速率。',
            '在途部队保留出发城编制与容量，但不能守城或接受新指令；出发城失陷撤销行军，按战后撤离处理。死亡、目的城易主及满城均在到达时重新核对。',
            '已发布50份目录不变；旧存档不自动增加城市或改变行军规则，新内容需新开v7战役。'])
        path = filename.replace('main-scenarios-v6/', 'main-scenarios-v7/')
        write('game/data/' + path, data)
        paths.append(path)
        original = next(s for s in index['summary'] if s['id'].replace('-v6', '-v7') == data['id'])
        summary.append(dict(original, id=data['id']))
    result = dict(schema='main-scenario-index-v1', catalogs=paths,
                  default=index['default'].replace('-v6', '-v7'), summary=summary)
    write('game/data/main-scenarios-v7/index.json', result)
    return result


if __name__ == '__main__':
    import json
    print(json.dumps(build(), ensure_ascii=False))
