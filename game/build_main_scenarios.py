#!/usr/bin/env python3
"""Offline, auditable adaptations of the eleven built-in historical chapters.

Official pages establish the chapter list and dates, not exported SAN14 setups.
Existing dated snapshots remain immutable. For new dates, only explicit reviewed
overrides or agreement across two dated snapshots can enable membership. That
agreement is labelled as an inference, never proof of continuous employment.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
import hashlib
from pathlib import Path

from build_campaigns import read, write, build_era
from remake.officers import convert_profile


def extend_profiles(base):
    """One necessary new leader; no default virtues for unreviewed officers."""
    design=read('game/config/main-scenario-profile.json')
    p=next(p for p in base['people'] if p['person_id']==design['person_id'])
    anchor=next(p for p in base['people'] if p['person_id']==design['calibration']['person_id'])
    if anchor['profile']['virtue']!=design['calibration']['virtue']:
        raise ValueError('Stale virtue calibration anchor')
    if p['profile']['virtue'] is not None:
        raise ValueError('Do not overwrite an existing profile')
    prior=p['profile'];p['virtue_design']=design
    p['profile']=asdict(convert_profile(san14_stats=prior['source_stats'],legacy={},
        health_max=prior['health_max'],terrain_affinity=prior['terrain_affinity'],virtue_design=design))
    p['configuration']['virtue']='history_informed_authorial_rating_calibrated_individually'


def resolve_memberships(base, snapshots, era, roster):
    """Build a separate adapter input; never mutate the original source rows."""
    sid=era['source_scenario'];before,after=(snapshots[y] for y in era['bracket'])
    names={p['name']:p for p in base['people']}
    rulers={f['id']:roster[names[f['captain']]['person_id']]['name_traditional'] for f in era['factions']}
    overrides={}
    for rule in era['roster_overrides']:
        if len(rule['person_ids'])!=len(rule['names']):raise ValueError('Override identity count')
        for pid,name in zip(rule['person_ids'],rule['names']):
            if pid not in roster:raise ValueError('Unknown scenario identity: '+pid)
            if pid in overrides:raise ValueError('Repeated scenario identity: '+pid)
            if next(p['name'] for p in base['people'] if p['person_id']==pid)!=name:
                raise ValueError('Scenario name/identity mismatch: '+pid)
            overrides[pid]=rule
    proofs={}
    for p in base['people']:
        pid=p['person_id'];a=before['era_assignments'][pid];b=after['era_assignments'][pid]
        status='unreviewed';side=None;city=None;basis='pending_history';rule=overrides.get(pid)
        if rule:
            status=rule.get('status','serving');side=rule['faction'];basis='reviewed_transition'
        elif a['source_status']==b['source_status']=='serving' and a['faction']==b['faction'] and a['faction'] in rulers:
            status='serving';side=a['faction'];basis='bracketing_affiliation_agreement_inference'
        elif a['source_status'] in ('free','undiscovered') and b['source_status'] in ('free','undiscovered') and a['source_city']==b['source_city'] and a['source_city']:
            status='free';city=a['source_city'];basis='bracketing_free_location_agreement_inference'
        # A chapter's named ruler is an explicit scenario setup, with its official
        # event outline as provenance, not inferred from a future successor.
        leader=next((f for f in era['factions'] if f['captain']==p['name']),None)
        if leader:status='serving';side=leader['id'];basis='chapter_leader_setup'
        roster[pid]['scenario_states'][sid]={'status':status,'ruler_source_name':rulers.get(side),
            'city_source_name':city,'raw':None}
        proofs[pid]={'basis':basis,'before_scenario':before['id'],'after_scenario':after['id'],
                     'before_status':a['source_status'],'after_status':b['source_status'],
                     'before_faction':a['faction'],'after_faction':b['faction'],'override':rule}
    return proofs


def build_all():
    spec=read('game/config/main-scenarios.json')
    old_spec=read('game/config/campaign-generation-v3.json')
    snapshots={e['year']:read(f'game/data/eras-v3/{e["year"]}.json') for e in old_spec['eras']}
    base=deepcopy(snapshots[217]);extend_profiles(base)
    anchors=read('game/assets/city-positions.json')
    image_path=Path(__file__).resolve().parent/'assets/map.png'
    if hashlib.sha256(image_path.read_bytes()).hexdigest()!=anchors['map_sha256']:
        raise ValueError('Rendered map and city anchors differ')
    if set(anchors['positions'])!={c['id'] for c in base['cities']}:
        raise ValueError('Incomplete rendered city anchors')
    for city in base['cities']:city['position']=anchors['positions'][city['id']]
    source=read('expansion/officers/data/roster-candidates.json')
    original_roster={r['person_id']:r for r in source['officers']}
    postings=read('game/config/era-postings.json')['postings']+read('game/config/era-postings-v3.json')['postings']
    # Same fixed board, carefully mapped battle theatres; not exact camps.
    postings+=read('game/config/main-scenario-postings.json')['postings']
    catalogs=[];summary=[]
    for requested in spec['eras']:
        era=deepcopy(requested);roster=deepcopy(original_roster);proofs={}
        if era['group']=='base':
            era['source_scenario']=snapshots[era['year']]['era_metadata']['source_scenario']
        else:proofs=resolve_memberships(base,snapshots,era,roster)
        legacy_spec=deepcopy(old_spec);legacy_spec['city_capacity']=spec['city_capacity']
        if era['group']=='pk':legacy_spec['membership_revisions']=[]
        data=build_era(base,roster,era,legacy_spec,postings)
        for pid,proof in proofs.items():
            row=data['era_assignments'][pid];row['membership_resolution']=proof
            if row['source_status']=='unreviewed':
                data['appearance_locations'].pop(pid,None)
                if row['year_state'] in ('available','death_year_review'):
                    row.update(status='pending_history',city=None,placement_basis=None,
                               reason='No reviewed transition or bracketing agreement at this date; not spawned.')
        ident=f'mainland{era["year"]}-{era["month"]:02d}-v4'
        data.update(id=ident,content_generation=4,title=f'{era["year"]}年{era["month"]}月 · {era["title"]}')
        configured=sum(p['profile']['virtue'] is not None for p in data['people'])
        data['coverage'].update(configured_profiles=configured,pending_profiles=1000-configured,
            history_designs_total=configured-1,new_history_profiles=1,
            pending_history=sum(r['status']=='pending_history' for r in data['era_assignments'].values()))
        data['main_scenario']={'group':era['group'],'title':era['title'],'official_source':era['official_source'],
            'summary':era['summary'],'adaptation':True,'setup_basis':'independent_96_city_adaptation_not_SAN14_export',
            'membership_basis':'dated_snapshot_with_reviewed_revisions' if era['group']=='base' else 'reviewed_overrides_and_labelled_bracketing_inference',
            'roster_complete':False,'scope':spec['scope']}
        data['era_metadata'].update(main_scenario=data['main_scenario'],membership_basis=data['main_scenario']['membership_basis'])
        if era.get('territory_review'):data['era_metadata']['territory_review']=era['territory_review']
        if era['group']=='pk':
            data['era_metadata'].update(source_snapshot_month=None,adapter_snapshot_years=era['bracket'])
        data['design_notes']=[
            '本篇年代与名称核对官方目录：原版7篇、威力加强版追加4篇；96城版为本作独立改编。',
            f'每城{spec["city_capacity"]}人；每方出战最多10人，含主将。招募、劝降、调动、战后撤离和AI统一使用本目录容量。',
            f'总人物库1000人，{configured}人属性齐全；其余缺德者不自动入场。开局人数以本剧本实际配置为准。',
            '新年代仅启用单独复核的转属或前后快照势力一致的推定成员；未确认的转属留待配置。推定不等于史实已证实。',
            '出生、出仕、卒年来自候选库游戏年份；同年死亡的开局在世情况单独解决。后续不强制历史转属与战果。',
            '驻城、96节点疆界和游戏数值属于本作玩法配置，未声称完整复刻三国志14的领地、事件或战斗系统。',
            '已发布的17份旧目录保持原样，旧存档仍沿用20人规则；新开本篇战役启用30人。']
        counts=Counter(data['initial_owners'][r['city']] for r in data['initial_officers'])
        for f in data['factions']:
            leader=next(p for p in data['people'] if p['name']==f['captain'])
            if not any(r['person_id']==leader['person_id'] and r.get('ruler') for r in data['initial_officers']):
                raise ValueError(f'Missing playable ruler: {ident} {f["captain"]}')
            f['initial_officers']=counts[f['id']]
        filename=f'main-scenarios/{era["year"]}-{era["month"]:02d}.json'
        catalogs.append(filename)
        summary.append({'id':ident,'year':era['year'],'month':era['month'],'title':era['title'],'group':era['group'],
            'factions':len(data['factions']),'serving':len(data['initial_officers']),'free':len(data['initial_free_officers']),
            'pending_history':data['coverage']['pending_history'],'configured_profiles':configured})
        write('game/data/'+filename,data)
    # Last catalog determines the initial screen; select the established217 era.
    catalogs.sort(key=lambda p:p=='main-scenarios/217-07.json')
    index={'schema':'main-scenario-index-v1','catalogs':catalogs,'default':spec['default'],'summary':summary}
    write('game/data/main-scenarios/index.json',index)
    return index


if __name__=='__main__':
    import json
    print(json.dumps(build_all(),ensure_ascii=False))
