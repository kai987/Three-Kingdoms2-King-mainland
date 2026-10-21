#!/usr/bin/env python3
"""Auditable DLC/IF campaign adaptations; never rewrite released catalogs.

Official pages supply dates and narrative premises, not private SAN14 setups.
Membership, map proxies, and future IF lifespan boundaries remain explicitly
labelled remake choices. Stable identities, profiles and dated city gates stay.
"""
from collections import Counter,defaultdict
from copy import deepcopy

from build_campaigns import read,write
from remake.garrison_postings import apply_postings
from remake.officers import PersonDefinition,YearState,year_state


ROOT_SOURCE='game/data/main-scenarios-v11/'
FOLDER='main-scenarios-v12/'
BIO='https://zh.wikisource.org/wiki/三國志'


def active_cities(data,year,month):
    return [row['id'] for row in data['cities'] if row['id'] not in data['city_foundings'] or
            (year,month)>=(data['city_foundings'][row['id']]['year'],data['city_foundings'][row['id']].get('month',1))]


def parent_city(data,key,active):
    seen=set()
    while key not in active and key in data['city_foundings'] and key not in seen:
        seen.add(key);key=data['city_foundings'][key]['parent']
    return key if key in active else None


def finish_audits(data, *, apply=True):
    if apply:
        audit=apply_postings(data)
        names={p['person_id']:p['name'] for p in data['people']}
        for record in audit['postings']:record['name']=names[record['person_id']]
        data['garrison_audit']=audit
        for key,history in data['city_history'].items():
            history['garrisons']=[r for r in audit['postings'] if r['city']==key]
        data['northern_expansion']['garrisons']=[r for r in audit['postings']
            if r['city'] in set(data['northern_expansion'].get('city_ids',[]))]
        data['southern_expansion']['garrisons']=[r for r in audit['postings']
            if r['city'] in set(data['southern_expansion']['city_ids'])]
    counts=Counter(data['initial_owners'][r['city']] for r in data['initial_officers'])
    for f in data['factions']:f['initial_officers']=counts[f['id']]
    statuses=Counter(r['status'] for r in data['era_assignments'].values())
    data['coverage'].update(initial_serving=len(data['initial_officers']),
        initial_free=len(data['initial_free_officers']),planned_serving=len(data['initial_officers']),
        planned_max_city_roster=max(Counter(r['city'] for r in data['initial_officers']).values(),default=0),
        pending_capacity=statuses['pending_capacity'],pending_history=statuses['pending_history'],
        pending_factions=[])
    data['era_metadata']['main_scenario']=deepcopy(data['main_scenario'])


def retime(entry,spec):
    data=deepcopy(read(ROOT_SOURCE+entry['base']+'.json'))
    original=deepcopy(data)
    year,month=entry['year'],entry['month']
    title=entry['title_i18n']['zh-Hant']
    data.update(id=f'mainland{year}-{month:02d}-v12',content_generation=12,
        start_year=year,start_month=month,title=f'{year}年{month}月 · {title}')
    data['active_cities']=active_cities(data,year,month);active=set(data['active_cities'])
    factions={f['id']:deepcopy(f) for f in data['factions'] if f['id'] not in entry.get('remove_factions',[])}
    for f in entry['faction_upserts']:factions[f['id']]={**factions.get(f['id'],{}),**deepcopy(f)}
    owner_map=entry['owner_map']
    owners={key:owner_map.get(value,value) for key,value in data['initial_owners'].items() if key in active}
    # Use the authored city list, not the hash-randomized membership set:
    # newly opened263 cities must have identical JSON/save identities in every
    # process even when PYTHONHASHSEED differs between local builds and CI.
    for key in data['active_cities']:
        if key not in owners:
            parent=parent_city(data,data['city_foundings'][key]['parent'],active)
            owners[key]=owners.get(parent,'neutral')
    for rule in entry.get('takeover',[]):
        owners={key:rule['to'] if side==rule['owner'] else side for key,side in owners.items()}
    owners.update(entry['owners'])
    for key in owners:
        if key not in active:raise ValueError('DLC owner names unopened city: '+key)
        if owners[key] not in {*factions,'neutral'}:raise ValueError('DLC owner faction missing: '+owners[key])
    for f in factions.values():
        if f['city'] not in active:raise ValueError('DLC ruler seat not open')
        owners[f['city']]=f['id']
        f.pop('initial_officers',None)
        if 'name' not in f:f['name']=f['captain']+'勢力'
    data['factions']=list(factions.values());data['initial_owners']=owners
    by_name=defaultdict(list);by_pid={}
    for p in data['people']:
        by_pid[p['person_id']]=p
        for alias in {p['name'],*p.get('aliases',[])}:by_name[alias].append(p)
    aliases=entry.get('name_aliases',{})
    def identity(name,required=False):
        choices=by_name.get(aliases.get(name,name),[])
        if len(choices)==1:return choices[0]
        if required:raise ValueError('Unambiguous DLC identity required: '+name)
        return None
    chronology=[]
    for name,change in entry['chronology_overrides'].items():
        person=identity(name,True);original_value={key:person[key] for key in ('birth_year','service_year','death_year')}
        for key in original_value:
            if key in change:person[key]=change[key]
        record=dict(person_id=person['person_id'],name=person['name'],before=original_value,
            after={key:person[key] for key in original_value},basis=change['basis'],
            is_historical_correction=change.get('is_historical_correction',False),sources=change.get('sources',entry['source_urls']))
        chronology.append(record);person['scenario_chronology_override']=record
        person['chronology_basis']=person['chronology_basis']+'; scenario_specific_explicit_exception'
    excluded={identity(n,True)['person_id'] for n in entry['excluded_people']}
    members={};unrepresented=[];member_proofs={}
    for side,names in entry['members'].items():
        if side not in factions:raise ValueError('DLC member side absent')
        for name in names:
            person=identity(name)
            if person is None:
                unrepresented.append(dict(name=name,faction=side,reason='name_not_uniquely_in_1000_library'))
                continue
            pid=person['person_id']
            if pid in members and members[pid]!=side:raise ValueError('DLC member assigned twice')
            members[pid]=side;member_proofs[pid]='explicit_story_or_career_assignment_not_SAN14_export'
    for pid,side in entry.get('homonym_members',{}).items():
        if pid not in by_pid:raise ValueError('DLC named stable identity missing')
        members[pid]=side;member_proofs[pid]='explicit_stable_identity_homonym_disambiguation'
    for f in factions.values():
        person=identity(f['captain'],True);members[person['person_id']]=f['id'];member_proofs[person['person_id']]='explicit_chapter_ruler'
    ruler_ids={identity(f['captain'],True)['person_id']:f for f in factions.values()}
    assignments={};initial=[];free=[];locations={};ignored=[]
    for p in data['people']:
        pid=p['person_id'];prior=original['era_assignments'][pid]
        definition=PersonDefinition(pid,p['name'],p['birth_year'],p['service_year'],p['death_year'],p['chronology_basis'])
        ys=year_state(definition,year)
        available=ys in (YearState.AVAILABLE,YearState.DEATH_YEAR_REVIEW)
        # Retiming is a documented adaptation, not evidence that an allegiance
        # continued uninterrupted throughout the interval between snapshots.
        side=members.get(pid)
        basis=member_proofs.get(pid)
        if not side and prior.get('source_status')=='serving':
            old_side=prior.get('faction')
            mapped=entry.get('member_map',owner_map).get(old_side,old_side)
            if mapped in factions:
                side=mapped;basis='retimed_nearby_snapshot_membership_authorial_inference'
        location=parent_city(data,prior.get('city') or original['appearance_locations'].get(pid),active)
        if pid in excluded:
            side=None;location=None;status='scenario_excluded';reason='Explicit narrative absence; not automatically respawned.'
        elif not available:
            status='chronology_excluded';reason='Birth, service or death year excludes opening.'
        elif side:
            location=factions[side]['city']
            status='serving';reason=None
            initial.append(dict(person_id=pid,city=location,troops=300,ruler=pid in ruler_ids,
                resolve_death_year=ys==YearState.DEATH_YEAR_REVIEW))
        elif prior.get('source_status') in ('free','undiscovered','not_appeared') and location:
            status='free';reason='Existing source location retimed; current faction unassigned, not invented.'
            free.append(dict(person_id=pid,city=location,resolve_death_year=ys==YearState.DEATH_YEAR_REVIEW))
            basis='retimed_source_free_location_not_attested_post'
        else:
            status='pending_history';reason='No enabled faction/location reviewed for this chapter.'
            location=None
        if pid in members and not available:
            ignored.append(dict(person_id=pid,name=p['name'],faction=members[pid],year_state=ys.value))
        if location and pid not in excluded and (status in ('serving','free') or ys in (YearState.NOT_BORN,YearState.NOT_APPEARED)):
            locations[pid]=location
        assignments[pid]=dict(source_status='serving' if status=='serving' else prior.get('source_status'),
            source_ruler=factions[side]['captain'] if side else prior.get('source_ruler'),source_city=None,
            year_state=ys.value,faction=side,city=location,placement_basis=basis,status=status,reason=reason,
            death_year_resolved=bool(ys==YearState.DEATH_YEAR_REVIEW and status in ('serving','free')),
            posting_reference=None,membership_revision=None,scenario_membership_basis=basis,
            source_snapshot=original['id'])
    # Fail rather than silently assign a leader outside their eligibility.
    for pid,f in ruler_ids.items():
        if not any(r['person_id']==pid and r['ruler'] for r in initial):
            raise ValueError('DLC ruler not chronologically eligible: '+f['captain'])
    # A narrative retreat can compress a formerly large army into one or two
    # board nodes. Preserve the30-person rule and keep the remaining members
    # explicitly pending; never fabricate extra territory or spawn them free.
    pending_capacity=[]
    for side in factions:
        slots=sum(owner==side for owner in owners.values())*data['rules']['city_officer_capacity']
        rows=sorted((r for r in initial if assignments[r['person_id']]['faction']==side),
            key=lambda r:(not r['ruler'],r['person_id'] not in members,r['person_id']))
        for row in rows[slots:]:
            pid=row['person_id'];initial.remove(row);locations.pop(pid,None)
            assignments[pid].update(status='pending_capacity',city=None,
                reason='Narrative faction has insufficient30-person board seats; not spawned free.')
            pending_capacity.append(dict(person_id=pid,name=by_pid[pid]['name'],faction=side))
    data.update(initial_officers=initial,initial_free_officers=free,appearance_locations=locations,
        faction_rulers={f['id']:identity(f['captain'],True)['runtime_id'] for f in factions.values()},era_assignments=assignments)
    summary=entry['summary_i18n']['zh-Hant']
    data['main_scenario']=dict(group=entry['group'],title=title,title_i18n=entry['title_i18n'],
        summary=summary,summary_i18n=entry['summary_i18n'],fictional=entry['fictional'],
        official_source=entry.get('official_source',entry['source_urls'][0]),source_urls=entry['source_urls'],
        adaptation=True,setup_basis='explicit_DLC_story_premise_with_retimed_remake_snapshot',
        membership_basis=spec['membership_policy'],roster_complete=False,profiles_complete=True,
        virtue_default_policy='virtue-default-60-2026-10-21',scope=spec['scope'],
        category='user_custom' if entry.get('user_custom') else 'free_IF_update' if entry['group']=='if' else 'historical_DLC' if entry['group']=='dlc' else 'official_bonus',
        chronology_overrides=chronology,chronology_policy=spec['chronology_policy'],
        city_chronology_note=original['main_scenario'].get('city_chronology_note',''),
        story_note_i18n={'zh-Hant':'本作依官網年代與故事改編；領土、駐將、數值及未實作的事件均不是官方原始資料匯入。',
            'ja':'公式の年月と物語を基にした本作独自の改編です。領土・配属・数値や未実装のイベントは公式データの移植ではありません。'})
    for key in ('official_same_date_title','scope_note','user_custom'):
        if key in entry:data['main_scenario'][key]=entry[key]
    data['dlc_audit']=dict(schema='DLC-opening-audit-v1',source_snapshot=original['id'],
        official_source_boundary='Dates and premises only; no original SAN14 roster/economy export.',
        chronology_overrides=chronology,unrepresented_members=unrepresented,chronology_excluded_requested_members=ignored,
        explicit_memberships=[dict(person_id=pid,name=by_pid[pid]['name'],faction=side,basis=member_proofs[pid]) for pid,side in sorted(members.items())],
        excluded_people=sorted(excluded),pending_capacity=pending_capacity,
        career_references=entry.get('member_sources',[]))
    data['era_metadata'].update(source_scenario=f'remake-dlc-{year}-{month:02d}',
        source_snapshot_month=None,adapter_snapshot_years=[original['start_year']],membership_revisions=[],
        death_year_resolutions=[pid for pid,r in assignments.items() if r['death_year_resolved']],
        membership_basis=spec['membership_policy'],unimplemented_source_factions=[])
    for key,history in data['city_history'].items():
        history['opening']=dict(owner=owners.get(key),basis='DLC_independent_story_territory_adaptation' if key in active else 'not_yet_open',
            note=summary if key in active else '未到此城既定開放年月。',sources=entry['source_urls'])
    data['design_notes']=[
        '官網僅證明劇本名稱、年月與故事前提；本作不是《三國志14》資料、事件、配樂或動畫的直接匯入。',
        '千人身份、能力、德與適性沿用既定配置；每城30人、戰場每方10人及v11海陸行軍規則保留。',
        '新年代名冊採鄰近已發佈戰役重定年表，加上明列的故事與生涯配置；推定不冒充逐將官方駐城。',
        '除目錄內逐人記錄的官方遊戲或IF例外外，出生、出仕與死亡仍照常生效；沒有全庫復活。',
        'IF延壽的未來終年是本作十年遊戲邊界，不是官方或歷史確定卒年。',
        '沒有確定本篇歸屬者保留待考或既有在野來源，不按城池顏色倒推其已被招募。',
        '115城年代按原規則開放，舊地圖位置、路線、資源基線與全部已發佈目錄保持不變。']
    finish_audits(data)
    return data


def build():
    spec=read('game/config/dlc-scenarios.json');previous=read(ROOT_SOURCE+'index.json')
    outputs=[]
    for filename in previous['catalogs']:
        data=deepcopy(read('game/data/'+filename));data['id']=data['id'].replace('-v11','-v12');data['content_generation']=12
        # Copy existing episodes byte-for-byte in substance: no retimed people,
        # resources, army counts, dates or ownership change for these13 starts.
        outputs.append(data)
    outputs.extend(retime(entry,spec) for entry in spec['entries'])
    if len({(d['start_year'],d['start_month']) for d in outputs})!=len(outputs):
        raise ValueError('Repeated dated DLC entry; merge duplicate225 instead')
    paths=[];summary=[]
    for data in sorted(outputs,key=lambda d:(d['start_year'],d['start_month'])):
        filename=FOLDER+f'{data["start_year"]}-{data["start_month"]:02d}.json'
        write('game/data/'+filename,data);paths.append(filename)
        meta=data['main_scenario']
        summary.append(dict(id=data['id'],year=data['start_year'],month=data['start_month'],title=meta['title'],
            group=meta['group'],fictional=meta.get('fictional',False),factions=len(data['factions']),
            active_cities=len(data['active_cities']),total_cities=data['city_count'],serving=len(data['initial_officers']),free=len(data['initial_free_officers'])))
    paths.sort(key=lambda p:p.endswith('/217-07.json'))
    result=dict(schema='main-scenario-index-v1',catalogs=paths,default='mainland217-07-v12',summary=summary)
    write('game/data/'+FOLDER+'index.json',result)
    return result


if __name__=='__main__':
    import json
    result=build();print(json.dumps(dict(catalogs=len(result['catalogs']),default=result['default'])))
