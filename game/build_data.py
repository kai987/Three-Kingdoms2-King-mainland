#!/usr/bin/env python3
"""Prepare the explicit standalone game's data allowlist, never a ROM image."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'game'


def main():
    plan = json.loads((ROOT / 'expansion/map/city-map-city-sea-plan-v42.json').read_text())
    roads = json.loads((ROOT / 'expansion/map/city-map-city-sea-roads-v42.json').read_text())
    profiles = json.loads((ROOT / 'expansion/officers/data/remake-profiles.json').read_text())['profiles']
    positions = {p['key']: p['center'] for p in plan['iconLayout']}
    # A stable permutation exercises IDs255/999 in real play, without truncating
    # or colliding with the1000-person catalog's other allocated IDs.
    bindings = {p['person_id']: p['runtime_id'] for p in profiles}
    by_id = {v: k for k, v in bindings.items()}
    for a, b in ((0, 255), (4, 999)):
        bindings[by_id[a]], bindings[by_id[b]] = b, a
    assert len(set(bindings.values())) == len(profiles) == 1000
    people = []
    for p in profiles:
        people.append({'person_id': p['person_id'], 'name': p['name'],
                       'runtime_id': bindings[p['person_id']],
                       'birth_year': p['chronology']['birth_year'],
                       'service_year': p['chronology']['service_year'],
                       'death_year': p['chronology']['death_year'],
                       'chronology_basis': p['chronology']['chronology_basis'],
                       'profile': p['profile']})
    cities = [{'id': c['key'], 'name': c['name'], 'position': positions[c['key']]}
              for c in plan['cities']]
    links = sorted({tuple(sorted((e['from'], e['to']))) for e in roads['directConnections']})
    active = ('nanyang', 'xiangyang', 'nanjun', 'jiangxia')
    data = {
        'schema': 'standalone-demo-data-v1', 'id': 'jingxiang217-v1',
        'title': '荆襄演练', 'start_year': 217, 'start_month': 11,
        'rules': {'city_officer_capacity': 20, 'battle_officers_per_side': 10,
                  'runtime_capacity': 1200, 'recruit_per_action': 100,
                  'recruit_gold_per_100': 20, 'recruit_grain_per_100': 30,
                  'battle_damage_percent': 32, 'monthly_gold_income': 35,
                  'monthly_grain_income': 90, 'ai_reinforce_max': 40},
        'factions': [
            {'id': 'wei', 'name': '曹军', 'captain': '夏侯惇', 'city': 'nanyang', 'color': '#916a47'},
            {'id': 'shu', 'name': '蜀军', 'captain': '刘备', 'city': 'xiangyang', 'color': '#4c7650'},
            {'id': 'wu', 'name': '吴军', 'captain': '甘宁', 'city': 'jiangxia', 'color': '#9b4b3d'}],
        'cities': cities, 'links': links, 'active_cities': list(active),
        'initial_owners': {'nanyang': 'wei', 'xiangyang': 'shu', 'nanjun': 'neutral', 'jiangxia': 'wu'},
        'initial_resources': {'gold': 1200, 'grain': 3800, 'reserves': 1200},
        'initial_officers': [
            {'person_id': 'san14-candidate-0124', 'city': 'nanyang', 'troops': 480},
            {'person_id': 'san14-candidate-0952', 'city': 'xiangyang', 'troops': 180, 'ruler': True},
            {'person_id': 'san14-candidate-0147', 'city': 'xiangyang', 'troops': 180},
            {'person_id': 'san14-candidate-0005', 'city': 'xiangyang', 'troops': 80},
            {'person_id': 'san14-candidate-0440', 'city': 'xiangyang', 'troops': 120},
            {'person_id': 'san14-candidate-0179', 'city': 'jiangxia', 'troops': 560},
            {'person_id': 'san14-candidate-0001', 'city': 'nanjun', 'troops': 120}],
        'people': people,
        'design_notes': [
            '本局是217年规则演练；四城归属、人物驻地、初始兵力资源均为本作测试设计，不是史实剧本。',
            '保留96城地图与1000人物总库；本局只开放相连四城、七名完整配置人物。',
            '普通攻击以现代可替换公式结算兵损，武将兵力归零为败退，不随机阵亡；计略、单挑、外交、复杂继承未接入。',
            '战斗期间出征武将保留原城占位；胜利后移驻目标城。守方败退者离开驻军、保留人物记录，不自动被招降。',
            '电脑每月执行一次整备/补兵，不在本切片主动攻城。',
            '未知死亡月份时，卒年单列待核并在次年清理；释放兵员回原城预备兵，战死记录不会复活。',
            '图形/按钮/输入/回合与保存均为现代实现；运行不读取ROM、原快照、控制IR或模拟器核心。']}
    (HERE / 'data').mkdir(exist_ok=True)
    (HERE / 'data/demo.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
    shutil.copy2(ROOT / 'expansion/map/city-map-96-city-sea-v42.png', HERE / 'assets/map.png')
    print(json.dumps({'people': len(people), 'map_cities': len(cities), 'play_cities': len(active),
                      'configured_officers': 7,
                      'data_sha256': hashlib.sha256((HERE / 'data/demo.json').read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
