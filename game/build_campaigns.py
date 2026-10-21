#!/usr/bin/env python3
"""Build current-generation campaigns offline; released v1/v2 catalogs stay frozen.

Profiles are individual authored assessments. Membership revisions, source
snapshots, military-region hints and board proxies retain distinct provenance.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import json
import sys

from build_eras import ALIASES, PROXY

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.officers import PersonDefinition, YearState, convert_profile, year_state


def read(path): return json.loads((ROOT/path).read_text())
def write(path,value):
    path=ROOT/path;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n')


def prepare_profiles(base, batch):
    designs={p['person_id']:p for p in batch}
    assert len(designs)==len(batch) and len(designs)==120
    for p in base['people']:
        design=designs.get(p['person_id']);prior=p['profile']
        if design:
            if prior['virtue'] is not None:raise ValueError('New batch may not overwrite a released virtue')
            anchor=next(r for r in base['people'] if r['person_id']==design['calibration']['person_id'])
            if anchor['profile']['virtue']!=design['calibration']['virtue']:raise ValueError('Stale comparison anchor')
            p['virtue_design']=design
            p['aliases']=sorted(set(p.get('aliases',[])+[design['name'],design['display_alias']]))
        p['profile']=asdict(convert_profile(san14_stats=prior['source_stats'],legacy={'virtue':prior['virtue']},
            health_max=prior['health_max'],terrain_affinity=prior['terrain_affinity'],virtue_design=p['virtue_design']))
        if design:p['configuration']['virtue']='history_informed_authorial_rating_calibrated_individually'
    return sum(p['profile']['virtue'] is not None for p in base['people'])


def make_owners(cities,factions):
    owners={c:'neutral' for c in cities}
    for f in factions:
        for city in f['cities']:
            if city not in owners or owners[city]!='neutral':raise ValueError('Overlapping or unknown city '+city)
            owners[city]=f['id']
        if owners[f['city']]!=f['id']:raise ValueError('Leader seat must be owned')
    return owners


def build_era(base, roster, era, spec, postings):
    data=deepcopy(base);year=era['year'];sid=era['source_scenario']
    cities={c['id']:c for c in data['cities']};factions={}
    for i,f in enumerate(era['factions']):
        name=f.get('name',f['captain']+'势力')
        if year>=221 and f['id'] in ('wei','shu','wu'):name={'wei':'曹魏','shu':'蜀汉','wu':'孙吴'}[f['id']]
        factions[f['id']]={k:v for k,v in f.items() if k!='cities'}
        factions[f['id']].update(name=name,color=f.get('color',('#786985','#527d77','#9c774f','#8a8054')[i%4]))
    owners=make_owners(cities,era['factions'])
    rulers={f['captain']:f['id'] for f in factions.values()}
    by_name={p['name']:p for p in data['people']}
    source_factions={roster[by_name[n]['person_id']]['name_traditional']:f for n,f in rulers.items()}
    revisions=[r for r in spec['membership_revisions'] if r['year']==year]
    for rev in revisions:
        for name in rev['source_rulers']:source_factions[name]=rev['faction']
    assignments={};initial=[];free=[];locations={};counts=Counter()
    ordered=sorted(data['people'],key=lambda p:(p['name'] not in rulers,p['person_id']))
    for p in ordered:
        pid=p['person_id'];record=roster[pid];src=record['scenario_states'][sid]
        definition=PersonDefinition(pid,p['name'],p['birth_year'],p['service_year'],p['death_year'])
        ys=year_state(definition,year);ready=p['profile']['virtue'] is not None
        eligible=ys==YearState.AVAILABLE or ys==YearState.DEATH_YEAR_REVIEW and src['status'] in ('serving','free','undiscovered')
        faction=source_factions.get(src['ruler_source_name']) if src['status']=='serving' else None
        revision=next((r for r in revisions if src['ruler_source_name'] in r['source_rulers']),None)
        city=ALIASES.get(src['city_source_name']);basis='source_snapshot_city_to_board' if city else None
        if src['city_source_name'] in PROXY:basis='nearest_board_proxy_not_same_historical_city'
        home=(p.get('virtue_design') or {}).get('home_city')
        if not home:
            home=next((ALIASES[s['city_source_name']] for key,s in sorted(record['scenario_states'].items())
                       if key!='san14-251-01' and s['city_source_name'] in ALIASES),None)
        if not city and home:city=home;basis='authored_career_fallback_not_attested_post'
        if city and city not in cities:raise ValueError('Unknown career board city '+city)
        status='pending_profile' if not ready else 'chronology_excluded';reason=None;posting=None
        if eligible and src['status'] in ('serving','free','undiscovered'):
            if src['status']=='serving' and faction:
                posting=next((r for r in postings if r['person_id']==pid and r['start_year']<=year<=r['end_year']
                              and owners[r['city']]==faction),None)
                preferred=factions[faction]['city'] if p['name'] in rulers else posting['city'] if posting else city or factions[faction]['city']
                options=[c for c,o in owners.items() if o==faction and counts[c]<20]
                if options:
                    xy=cities[preferred]['position']
                    city=min(options,key=lambda c:(c!=preferred,(cities[c]['position'][0]-xy[0])**2+(cities[c]['position'][1]-xy[1])**2,c))
                    counts[city]+=1
                    basis='authored_leader_seat' if p['name'] in rulers else 'authored_faction_region_capacity20'
                    if posting and city==posting['city']:basis=posting['basis']
                    status='serving' if ready else 'pending_profile'
                    if ready:initial.append(dict(person_id=pid,city=city,troops=300,ruler=p['name'] in rulers,resolve_death_year=ys==YearState.DEATH_YEAR_REVIEW))
                else:
                    # A small historical camp may have only one board node.
                    # Never invent extra territory or silently overflow20 slots.
                    city=None;basis=None;status='pending_capacity';reason='Source faction exceeds available20-person board seats; pending assignment, never spawned free.'
            elif src['status']=='serving':
                status='pending_faction' if ready else 'pending_profile';reason='Source faction is not enabled; preserve original affiliation.'
            elif city:
                status='free' if ready else 'pending_profile'
                if ready:free.append(dict(person_id=pid,city=city,resolve_death_year=ys==YearState.DEATH_YEAR_REVIEW))
            elif ready:status='pending_location'
        if city and (status in ('serving','free') or ys in (YearState.NOT_BORN,YearState.NOT_APPEARED) and src['status']!='dead'):
            locations[pid]=city
        assignments[pid]=dict(source_status=src['status'],source_ruler=src['ruler_source_name'],source_city=src['city_source_name'],
            year_state=ys.value,faction=faction,city=city,placement_basis=basis,status=status,reason=reason,
            death_year_resolved=bool(ys==YearState.DEATH_YEAR_REVIEW and status in ('serving','free')),
            posting_reference=posting,membership_revision=revision)
    data.update(id=f'mainland{year}-v3',content_generation=3,title=f'{year}年 · {era["title"]}',start_year=year,start_month=era['month'],
        factions=list(factions.values()),initial_owners=owners,initial_officers=initial,initial_free_officers=free,appearance_locations=locations,
        faction_rulers={f['id']:by_name[f['captain']]['runtime_id'] for f in factions.values()},era_assignments=assignments)
    complete=sum(p['profile']['virtue'] is not None for p in data['people'])
    data['coverage'].update(configured_profiles=complete,pending_profiles=1000-complete,new_history_profiles=120,
        history_designs_total=complete-1,initial_serving=len(initial),initial_free=len(free),source_scenario=sid,
        planned_serving=sum(counts.values()),planned_max_city_roster=max(counts.values()),
        pending_capacity=sum(r['status']=='pending_capacity' for r in assignments.values()),
        pending_factions=sorted({r['source_ruler'] for r in assignments.values() if r['source_status']=='serving' and r['faction'] is None}))
    data['era_metadata'].update(source_scenario=sid,membership_revisions=revisions,
        death_year_resolutions=[pid for pid,r in assignments.items() if r['death_year_resolved']],
        source_snapshot_month=int(sid[-2:]),unimplemented_source_factions=data['coverage']['pending_factions'])
    data['design_notes']=[
      '新增120份逐人史料参考德评分；对照既有武将校准四维尺度，不复制魅力或统一默认德。低置信与裴注材料另标。',
      '势力来源、历史修订和具体驻城分开保存。出生、出仕、卒年仍为来源游戏设定，未认证的历史日期不强填。',
      '184年汉廷官军合并来源中的官军集团，章节改从3月起。190张鲁归刘焉部，194孙策归袁术部，200张绣集团归曹操。其余宏观军团仍是玩法配置。',
      '190张超的广陵代理到东海、194刘备的小沛代理到谯郡；兖州争夺以东郡吕布、陈留曹操表示，不能当作精确郡界。',
      '同一固定节点只能归一方。超过20个规划席位的来源成员留待驻城配置，不增领土、不变在野、不强行塞城。',
      '新登场者按配置地点以在野进入，不强制加入历史势力，不复活已退场人物；各年代开局不是中途强制历史事件。',
      '全部96城、每城20人、每方出战10人不变。v1/v2已发行目录保持原样，旧存档仍按各自目录哈希读取。']
    return data


def main():
    spec=read('game/config/campaign-generation-v3.json');base=read(spec['base'])
    complete=prepare_profiles(base,read(spec['profiles'])['profiles'])
    assert complete==spec['expected_complete']
    source=read('expansion/officers/data/roster-candidates.json');roster={r['person_id']:r for r in source['officers']}
    postings=read('game/config/era-postings.json')['postings']+read('game/config/era-postings-v3.json')['postings']
    paths=[];summary=[]
    for era in spec['eras']:
        data=build_era(base,roster,era,spec,postings)
        path=f'{spec["output"]}/{era["year"]}.json';write(path,data);paths.append(f'eras-v3/{era["year"]}.json')
        summary.append(dict(id=data['id'],year=era['year'],month=era['month'],title=data['title'],factions=len(data['factions']),**data['coverage'],
            statuses=dict(Counter(r['status'] for r in data['era_assignments'].values()))))
    write(f'{spec["output"]}/index.json',{'schema':'era-catalog-index-v1','catalogs':paths,'default':spec['default'],'summary':summary})
    write('expansion/officers/data/era-configuration-v3-audit.json',{'schema':'era-configuration-audit-v3','library':1000,'new_complete':120,'complete':complete,
        'remaining_virtue':1000-complete,'playable_eras':summary,'excluded_fantasy_scenario':'san14-251-01','released_v2_untouched':True})
    print(json.dumps({'complete':complete,'pending':1000-complete,'eras':[(s['year'],s['initial_serving'],s['initial_free'],s['pending_capacity']) for s in summary]},ensure_ascii=False))


if __name__=='__main__':main()
