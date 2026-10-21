#!/usr/bin/env python3
"""Offline era catalogs. Source faction snapshots and authored placement stay separate.

Never edits legacy catalogs or weakens their save hashes. All randomness belongs
in the game; data generation is deterministic and uses only committed inputs.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.officers import PersonDefinition, YearState, convert_profile, year_state


def read(path): return json.loads((ROOT / path).read_text())
def write(path, value):
    (ROOT / path).write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')

# Source cities are usually county seats. Proxies are explicit board conversions,
# not assertions that historical 新野、广陵、小沛 were the same city as a board node.
ALIASES = dict(zip(
    '上庸 下邳 交趾 北平 北海 南海 南皮 吳 壽春 天水 安定 宛 小沛 平原 廣陵 廬江 建安 建寧 建業 成都 新野 晉陽 會稽 柴桑 桂陽 梓潼 武威 武陵 永安 汝南 江夏 江州 江陵 洛陽 漢中 濮陽 薊 襄平 襄陽 許昌 鄴 長安 長沙 陳留 雲南 零陵'.split(),
    'xincheng xiapi jiaozhi yuyang beihai nanhai bohai wujun jiujiang tianshui anding nanyang qiao pingyuan donghai lujiang kuaiji jianning danyang shujun nanyang taiyuan kuaiji yuzhang guiyang zitong wuwei wuling badong runan jiangxia bajun nanjun henan hanzhong dongjun yan liaodong xiangyang yingchuan wei jingzhao changsha chenliu yunnan lingling'.split()))
PROXY = {'小沛', '廣陵', '建安'}
SHU = set('hanzhong shujun bajun badong wudu zitong guanghan wenshan baxi qianwei jiangyang hanjia zhuti yuexi zangke jianning xinggu yinping fuling yunnan yongchang'.split())
WU = set('danyang wujun kuaiji jiujiang yuzhang lujiang xindu poyang luling qichun nanhai gaoliang hepu yulin cangwu linhe'.split())
JING = set('xiangyang nanjun jiangxia changsha lingling guiyang wuling yidu'.split())
JIAO = set('jiaozhi jiuzhen rinan'.split())
NORTH = set('fanyang bohai wei qi beihai taiyuan xihe yan yuyang shanggu dai liaoxi changshan zhongshan anping pingyuan jinan'.split())
WEST = set('wuwei anding tianshui jincheng longxi'.split())
# Stable faction keys are maintained across rulers. Historical state names only
# apply after their foundation, so pre220 UI uses 曹操 rather than 曹魏.
FACTIONS = {
 'wei': ('曹操', 'yingchuan', '#916a47'), 'shu': ('刘备', 'xiapi', '#4c7650'),
 'wu': ('孙策', 'wujun', '#9b4b3d'), 'yuan_shao': ('袁绍', 'wei', '#686d91'),
 'liu_biao': ('刘表', 'xiangyang', '#7c7091'), 'liu_zhang': ('刘璋', 'shujun', '#598d84'),
 'ma_teng': ('马腾', 'wuwei', '#a68b47'), 'zhang_lu': ('张鲁', 'hanzhong', '#596b83'),
 'shi_xie': ('士燮', 'jiaozhi', '#927d58'), 'gongsun': ('公孙度', 'liaodong', '#788455')}
ERA_SPECS = [
 (200, 1, '官渡前夕', {'yuan_shao':{},'wei':{},'shu':{},'wu':{},'liu_biao':{},'liu_zhang':{},'ma_teng':{},'zhang_lu':{},'shi_xie':{},'gongsun':{}}),
 (207, 9, '三顾之时', {'wei':{'city':'wei'},'shu':{'city':'yiyang'},'wu':{'captain':'孙权'},'liu_biao':{},'liu_zhang':{},'ma_teng':{},'zhang_lu':{},'shi_xie':{},'gongsun':{'captain':'公孙康'}}),
 (221, 7, '夷陵前夕', {'wei':{'captain':'曹丕','city':'henan'},'shu':{'city':'shujun'},'wu':{'captain':'孙权','city':'jiangxia'},'shi_xie':{},'gongsun':{'captain':'公孙恭'}}),
 (227, 2, '出师北伐', {'wei':{'captain':'曹叡','city':'henan'},'shu':{'captain':'刘禅','city':'shujun'},'wu':{'captain':'孙权','city':'jiangxia'},'gongsun':{'captain':'公孙恭'}}),
 (249, 1, '正始之变', {'wei':{'captain':'曹芳','city':'henan'},'shu':{'captain':'刘禅','city':'shujun'},'wu':{'captain':'孙权','city':'danyang'}}),
 # Default comes last; legacy mainland217-v1 remains separately selectable.
 (217, 7, '汉中争衡', {'wei':{'city':'wei'},'shu':{'city':'shujun'},'wu':{'captain':'孙权','city':'danyang'},'shi_xie':{},'gongsun':{'captain':'公孙恭'}}),
]


def ownership(base, year, factions):
    owners = {c['id']: 'wei' for c in base['cities']}
    for cities, f in [(SHU,'liu_zhang' if year <= 207 else 'shu'), (WU,'wu'),
                      (JING,'liu_biao' if year <= 207 else 'wu'), (JIAO,'shi_xie'),
                      (WEST,'ma_teng' if year <= 207 else 'wei'), ({'liaodong'},'gongsun')]:
        for c in cities: owners[c] = f if f in factions else 'neutral'
    for c in ('yizhou','zhuya','lelang','daifang'): owners[c] = 'neutral'
    if year == 200:
        for c in NORTH: owners[c] = 'yuan_shao'
        owners['xiapi'] = 'shu'
    if year == 207: owners['yiyang'] = 'shu'
    if year <= 207: owners['hanzhong'] = 'zhang_lu'
    if year == 217:
        owners['hanzhong'] = 'wei'  # Taken by Liu Bei in219, not already Shu in217.
        for c in ('nanjun','yidu','wuling','lingling'): owners[c] = 'shu'
    if year >= 221:
        for c in ('xiangyang',): owners[c] = 'wei'
    if year >= 217: owners['xiangyang'] = 'wei'
    if year <= 227:
        for c in ('wudu','yinping'): owners[c] = 'wei'
    if year >= 227:
        for c in JIAO: owners[c] = 'wu'
    for f in factions.values(): owners[f['city']] = f['id']
    return owners


def main():
    base = read('game/data/mainland.json')
    source = read('expansion/officers/data/roster-candidates.json')
    roster = {p['person_id']: p for p in source['officers']}
    batch = read('game/config/officer-batch2.json')['profiles']
    policy = read('game/config/initialization-policy.json')
    postings = read('game/config/era-postings.json')['postings']
    designs = {p['person_id']: p for p in batch}
    assert len(designs) == 96
    city_by_id = {c['id']: c for c in base['cities']}
    by_name = {p['name']: p for p in base['people']}
    for p in base['people']:
        old = p['profile']; design = designs.get(p['person_id'])
        profile = convert_profile(san14_stats=old['source_stats'],
             legacy={'virtue':old['virtue']},
             health_max=old['health_max'] if old['health_max'] is not None else policy['health_max'],
             terrain_affinity=old['terrain_affinity'] if old['terrain_affinity'] is not None else (design['terrain_affinity'] if design else policy['terrain_affinity']),
             virtue_design=design or p['virtue_design'])
        p['profile'] = asdict(profile)
        if design: p['virtue_design'] = design
        p['aliases'] = sorted(set(roster[p['person_id']]['search_aliases'] + ([design['name']] if design else [])))
        p['configuration'] = {
          'health':'retained_legacy_or_previous_design' if old['health_max'] is not None else 'remake_baseline_80',
          'affinity':'retained_previous_design' if old['terrain_affinity'] is not None else 'explicit_career_design' if design else 'remake_plain_default_0',
          'virtue':'history_informed_authorial_rating' if p['virtue_design'] else 'legacy_pending_history_review' if profile.virtue is not None else 'pending_individual_evidence',
          'is_historical_measurement':False}
    complete = sum(not any(p['profile'][k] is None for k in ('health_max','martial_strength','intellect','virtue','terrain_affinity')) for p in base['people'])
    assert complete == 148
    paths=[]; summaries=[]
    for year,month,title,config in ERA_SPECS:
        data=deepcopy(base); sid=f'san14-{year}-{month:02}'
        factions={}
        for key, override in config.items():
            name,city,color=FACTIONS[key]
            f=dict(id=key,name=name,captain=name,city=city,color=color);f.update(override)
            f['name']=f['captain']+'势力'
            if year>=221 and key in ('wei','shu','wu'): f['name']={'wei':'曹魏','shu':'蜀汉','wu':'孙吴'}[key]
            factions[key]=f
        owners=ownership(data,year,factions)
        rulers={f['captain']:f['id'] for f in factions.values()}
        source_rulers={roster[by_name[n]['person_id']]['name_traditional']:key for n,key in rulers.items()}
        merged={}
        if year==207:
            merged={n:'liu_biao' for n in ('韓玄','趙範','金旋','劉度')}
        if year==249: merged={'司馬懿':'wei','曹爽':'wei'}
        source_rulers.update(merged)
        assigned=[];locations={};states={};counts=Counter();death_resolutions=[]
        # Leaders first, so no small capacity fallback can evict a ruler.
        ordered=sorted(data['people'],key=lambda p:(p['name'] not in rulers,p['person_id']))
        for p in ordered:
            pid=p['person_id'];record=roster[pid];src=record['scenario_states'][sid]
            person=PersonDefinition(pid,p['name'],p['birth_year'],p['service_year'],p['death_year'])
            ys=year_state(person,year);ready=p['profile']['virtue'] is not None
            f=source_rulers.get(src['ruler_source_name']) if src['status']=='serving' else None
            city=ALIASES.get(src['city_source_name']);basis='source_snapshot_city_to_board' if city else None
            if src['city_source_name'] in PROXY: basis='nearest_board_proxy_not_same_historical_city'
            home=designs.get(pid,{}).get('home_city')
            if not home:
                # Earliest known source location is a design fallback only, never
                # a sourced residence at the current date or a birth-year claim.
                home=next((ALIASES[s['city_source_name']] for k,s in sorted(record['scenario_states'].items()) if k!='san14-251-01' and s['city_source_name'] in ALIASES),None)
            if not city and home: city=home;basis='authored_home_or_career_fallback'
            eligible=ys==YearState.AVAILABLE or (ys==YearState.DEATH_YEAR_REVIEW and src['status'] in ('serving','free','undiscovered'))
            status='pending_profile' if not ready else 'chronology_excluded'
            reason=None; posting=None
            if eligible and src['status'] in ('serving','free','undiscovered'):
                if src['status']=='serving' and f:
                    candidates=[c for c,o in owners.items() if o==f and counts[c]<20]
                    if not candidates: raise ValueError(f'No capacity for {pid} in {f}')
                    posting=next((r for r in postings if r['person_id']==pid and r['start_year']<=year<=r['end_year'] and owners[r['city']]==f),None)
                    preferred=factions[f]['city'] if p['name'] in rulers else posting['city'] if posting else city or factions[f]['city']
                    xy=city_by_id[preferred]['position']
                    city=min(candidates,key=lambda c:(c!=preferred,(city_by_id[c]['position'][0]-xy[0])**2+(city_by_id[c]['position'][1]-xy[1])**2,c))
                    basis='authored_faction_seat' if p['name'] in rulers else 'authored_faction_region_with_capacity_20'
                    if posting and city==posting['city']: basis=posting['basis']
                    if ready:
                        assigned.append(dict(person_id=pid,city=city,troops=300,ruler=p['name'] in rulers,resolve_death_year=ys==YearState.DEATH_YEAR_REVIEW))
                    counts[city]+=1;status='serving' if ready else 'pending_profile'
                elif src['status']=='serving':
                    status='pending_faction' if ready else 'pending_profile';reason='source ruler not yet enabled; never silently reassign to another faction'
                elif city:
                    status='free' if ready else 'pending_profile'
                else:status='pending_location' if ready else 'pending_profile'
            elif ready and eligible:reason='source snapshot does not allow appearance; source status wins'
            # Future entrants use a fixed fallback as free officers, not a forced
            # historical defection after the player has changed history.
            if city and (status in ('serving','free') or
                         ys in (YearState.NOT_BORN, YearState.NOT_APPEARED) and src['status']!='dead'):
                locations[pid]=city
            states[pid]=dict(source_status=src['status'],source_ruler=src['ruler_source_name'],source_city=src['city_source_name'],year_state=ys.value,
                faction=f,city=city,placement_basis=basis,status=status,reason=reason,
                death_year_resolved=bool(ys==YearState.DEATH_YEAR_REVIEW and status in ('serving','free')),
                posting_reference=posting)
            if states[pid]['death_year_resolved']:death_resolutions.append(pid)
        data.update(id=f'mainland{year}-v2',title=f'{year}年 · {title}',start_year=year,start_month=month,
            factions=list(factions.values()),initial_owners=owners,initial_officers=assigned,appearance_locations=locations,
            initial_free_officers=[{'person_id':pid,'city':r['city'],'resolve_death_year':r['death_year_resolved']} for pid,r in states.items() if r['status']=='free'],
            faction_rulers={f['id']:by_name[f['captain']]['runtime_id'] for f in factions.values()},era_assignments=states)
        data['coverage'].update(configured_profiles=complete,pending_profiles=1000-complete,health_configured=1000,affinity_configured=1000,
            new_history_profiles=96,initial_serving=len(assigned),initial_free=sum(s['status']=='free' for s in states.values()),source_scenario=sid,
            planned_serving=sum(counts.values()),planned_max_city_roster=max(counts.values()),
            pending_factions=sorted({s['source_ruler'] for s in states.values() if s['status']=='pending_faction'}))
        data['design_notes']=[
          '体力缺项统一使用本作80初始满体力；适性缺项默认0平地，逐人有战区依据时配置1山/2水。均为可调游戏规则，不冒充史料数值。',
          '德为逐人四维史料参考的生涯综合游戏评分，不以魅力批量补齐；尚缺德的人物留在总库。',
          '本局按所选年代的第三方SAN14快照安排势力；驻城使用来源地名映射或明确的势力区域配置，不声称逐县复原历史驻军。',
          '207年刘备屯新野，固定96城不含新野且南阳属曹，暂以义阳为独立城代理；四郡太守并入刘表宏观势力。249年司马懿、曹爽为魏内政治集团，并入曹芳势力，不凭空建立两个领土国家。',
          '卒年月份不明时只用注明该人物仍在世的年代快照解决开局资格；进入次年退出。新登场者在配置城以在野身份待访；不会强制叛投历史势力或复活。',
          '96城位置、原版图标、陆海路及20人城容量、每方10人保持既定规则；保留旧版两个剧本以读取旧存档。']
        data['era_metadata']={'source_scenario':sid,'membership_basis':'third_party_SAN14_game_snapshot_not_independently_verified_history',
            'placement_basis':'authored_macro_region_game_setup_not_certified_historical_posting','merged_source_groups':merged,
            'death_year_resolutions':death_resolutions,'unimplemented_source_factions':sorted({s['ruler_source_name'] for p in source['officers'] for s in [p['scenario_states'][sid]] if s['status']=='serving' and s['ruler_source_name'] not in source_rulers})}
        path=f'game/data/eras/{year}.json';write(path,data);paths.append(f'eras/{year}.json')
        summary=dict(id=data['id'],year=year,month=month,title=data['title'],**data['coverage'],status_counts=dict(Counter(r['status'] for r in states.values())))
        summaries.append(summary)
    write('game/data/eras/index.json',{'schema':'era-catalog-index-v1','catalogs':paths,'default':'mainland217-v2','summary':summaries})
    write('expansion/officers/data/era-configuration-audit.json',{'schema':'era-configuration-audit-v1','library':1000,'new_complete':96,'complete':complete,'remaining_virtue':1000-complete,'health_missing':0,'affinity_missing':0,
        'playable_eras':summaries,'not_yet_playable_source_scenarios':['san14-184-01','san14-190-01','san14-194-06'],
        'excluded_fantasy_scenario':'san14-251-01','notes':['All1000 source-era memberships retained in each catalog; unresolved source faction / placement / chronology is explicit.','No current save or legacy catalog is rewritten.']})
    print(json.dumps({'complete':complete,'pending_virtue':1000-complete,'eras':[(s['year'],s['initial_serving'],s['initial_free']) for s in summaries]},ensure_ascii=False))


if __name__=='__main__':
    (ROOT/'game/data/eras').mkdir(exist_ok=True)
    main()
