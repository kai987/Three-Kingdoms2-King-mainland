#!/usr/bin/env python3
"""Offline96-city campaign builder. Keeps the original four-city catalog intact."""
from dataclasses import asdict
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.officers import PersonDefinition, YearState, convert_profile, year_state


def read(path): return json.loads((ROOT / path).read_text())


def main():
    data = read('game/data/demo.json')
    sea_routes = read('expansion/map/city-map-city-sea-links-v42.json')['routes']
    data['sea_links'] = [[r['from'],r['to']] for r in sea_routes]
    data['links'] = [list(edge) for edge in sorted({tuple(sorted(edge)) for edge in data['links']+data['sea_links']})]
    roster = {r['person_id']: r for r in read('expansion/officers/data/roster-candidates.json')['officers']}
    abilities = {r['person_id']: r for r in read('expansion/officers/data/san14-abilities.json')['abilities']}
    designs = {r['person_id']: r for r in read('expansion/officers/virtue-designs.json')['profiles']}
    extra = {r['person_id']: r for r in read('game/config/officer-designs.json')['profiles']}
    designs.update(extra)
    # These are explicit game initialization choices, not inferred historical HP.
    legacy = {r['person_id']: r['profile'] for r in data['people']}
    for p in data['people']:
        ident = p['person_id']; old = legacy[ident]; design = designs.get(ident)
        old_fields = {'health': old['health_max'], 'martial_strength': old['martial_strength'],
                      'intellect': old['intellect'], 'virtue': old['virtue'],
                      'terrain_affinity_code': old['terrain_affinity']}
        health = old['health_max'] or (80 if design else None)
        terrain = old['terrain_affinity'] if old['terrain_affinity'] is not None else (extra.get(ident, {}).get('terrain_affinity', 0) if design else None)
        profile = convert_profile(san14_stats=abilities[ident]['stats'], legacy=old_fields,
                                  health_max=health, terrain_affinity=terrain, virtue_design=design)
        p['profile'] = asdict(profile)
        p['ability_source'] = {k: abilities[ident][k] for k in ('source_url','source_name','join_method','independently_verified')}
        p['virtue_design'] = design
    shu = set('xiangyang nanjun hanzhong shujun bajun yunnan yongchang badong wudu zitong guanghan wenshan baxi qianwei jiangyang hanjia zhuti yuexi zangke jianning xinggu yinping fuling'.split())
    wu = set('jiangxia changsha lingling guiyang wuling danyang wujun kuaiji jiujiang yuzhang lujiang xindu poyang luling yidu qichun linhe nanhai gaoliang hepu jiaozhi yulin cangwu jiuzhen rinan'.split())
    neutral = set('yizhou zhuya lelang daifang liaodong'.split())
    owners = {c['id']: 'shu' if c['id'] in shu else 'wu' if c['id'] in wu else 'neutral' if c['id'] in neutral else 'wei' for c in data['cities']}
    capitals = {'wei':'nanyang','shu':'xiangyang','wu':'jiangxia'}
    hubs = {'wei':['nanyang','yingchuan','henei','jingzhao','tianshui','taiyuan'],
            'shu':['xiangyang','nanjun','hanzhong','shujun','bajun','zitong'],
            'wu':['jiangxia','danyang','wujun','kuaiji','changsha','yuzhang']}
    leaders = {'曹操':'wei','刘备':'shu','孙权':'wu'}
    source_factions = {'曹操':'wei','劉備':'shu','孫權':'wu'}
    aliases = {'成都':'shujun','建業':'danyang','吳':'wujun','洛陽':'henan','長安':'jingzhao','宛':'nanyang','襄陽':'xiangyang','江陵':'nanjun','晉陽':'taiyuan','許昌':'yingchuan','濮陽':'dongjun','天水':'tianshui','雲南':'yunnan','安定':'anding','汝南':'runan','會稽':'kuaiji','漢中':'hanzhong','梓潼':'zitong','武陵':'wuling','武威':'wuwei','建寧':'jianning','下邳':'xiapi','上庸':'xincheng'}
    city_names = {c['name']: c['id'] for c in data['cities']}
    locations, initial, counters = {}, [], dict.fromkeys(hubs, 0)
    future_defaults = {'姜维':'tianshui','邓艾':'runan','钟会':'yingchuan','陆抗':'jiangxia','诸葛恪':'danyang','刘禅':'shujun'}
    for p in data['people']:
        record = roster[p['person_id']]
        state = record['scenario_states']['san14-217-07']
        loc = aliases.get(state['city_source_name'], city_names.get(state['city_source_name']))
        if p['name'] in future_defaults: loc = future_defaults[p['name']]
        if p['name'] == '王异': loc = 'tianshui'
        if loc: locations[p['person_id']] = loc
        if any(p['profile'][k] is None for k in ('health_max','martial_strength','intellect','virtue','terrain_affinity')): continue
        definition = PersonDefinition(p['person_id'],p['name'],p['birth_year'],p['service_year'],p['death_year'])
        if year_state(definition,217) != YearState.AVAILABLE: continue
        f = source_factions.get(state['ruler_source_name'])
        if f:
            loc = capitals[f] if p['name'] in leaders else hubs[f][counters[f] % len(hubs[f])]
            counters[f] += 1
            locations[p['person_id']] = loc
            initial.append({'person_id':p['person_id'],'city':loc,'troops':300,'ruler':p['name'] in leaders})
        elif not loc:
            # An unknown location remains pending; never random-spawn a person.
            continue
    water = set('jiangxia nanjun badong danyang wujun kuaiji jiujiang lujiang poyang yizhou zhuya hepu nanhai lelang daifang jiaozhi rinan'.split())
    mountains = shu - {'xiangyang','nanjun'} | {'tianshui','longxi','wuwei','anding','taiyuan','shangdang','xincheng'}
    for c in data['cities']: c['terrain'] = 'water' if c['id'] in water else 'mountain' if c['id'] in mountains else 'plain'
    for f in data['factions']:
        f['name'] = {'wei':'曹魏','shu':'蜀汉','wu':'孙吴'}[f['id']]
        f['captain'] = {'wei':'曹操','shu':'刘备','wu':'孙权'}[f['id']]
    data.update(schema='standalone-mainland-data-v1',id='mainland217-v1',title='九十六城 · 扩展战役',start_year=217,start_month=11,
                active_cities=[c['id'] for c in data['cities']],initial_owners=owners,
                initial_officers=initial,appearance_locations=locations,
                faction_rulers={f: next(p['runtime_id'] for p in data['people'] if p['name']==n) for n,f in leaders.items()})
    data['rules'].update(expanded_campaign=True,recruit_officer_gold=60,persuade_officer_gold=100,monthly_heal=8,ai_max_attacks_per_turn=3)
    complete = [p for p in data['people'] if not any(p['profile'][k] is None for k in ('health_max','martial_strength','intellect','virtue','terrain_affinity'))]
    data['coverage'] = {'library':1000,'san14_abilities':1000,'configured_profiles':len(complete),'pending_profiles':1000-len(complete),'initial_serving':len(initial),'source_years':'third-party SAN14 settings; historical verification separate','virtue':'individually history-informed authorial game ratings, not SAN14 charisma'}
    data['design_notes'] = [
        '96城全部开放。千人库按年代筛选，仅属性和位置齐全者进入战局；待配置人物保留在总库，不随机填属性。',
        '本剧本为217年扩展规则试制。沿用固定地图，城池归属、驻地和地形类别是玩法配置，不是严格217年历史行政图。',
        'SAN14五维来自公开第三方数值表，武/知对应武力/智力；16种计略沿用已核实名称，效果与AI采用本重制版新规则。',
        '德逐人参考史料设计，其余人物不从魅力自动换算；生卒、出仕年份是来源游戏设定，月份未知时卒年次年退出。',
        '招募需当地或相邻中立/本方城的在野武将；转属沿己方连通道路一次提交。满城与失败输入不扣资源。',
        '单挑采用突击/防守/佯攻，体力归零为负伤败退；伤亡兵包含溃散，不随机永久杀死人物。',
        '电脑会招募、补兵、调兵、判断邻城兵力并出征；攻打玩家时暂停，交由玩家操作守军，结算后继续电脑回合。',
        '地图、容量20人、每方10人不变；没有运行ROM、原模拟器或控制IR。']
    path=ROOT/'game/data/mainland.json';path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps(data['coverage'],ensure_ascii=False))


if __name__=='__main__': main()
