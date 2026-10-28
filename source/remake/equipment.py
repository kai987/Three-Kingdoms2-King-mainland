"""Actual equipment, unique acquisitions and pure Web combat projections.

Original table values and acquisition conditions are kept separate from the
remake's documented weight/miss/retreat arithmetic. All people use these same
services; viewing an offer never advances campaign RNG.
"""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

from . import facility_equipment
from .errors import GameError
from . import command_books

SCHEMA = 'tk2-equipment-v1'
WEAPONS, ARMORS = facility_equipment.WEAPONS, facility_equipment.ARMORS
WEAPON_MAX, ARMOR_MAX = len(WEAPONS)-1, len(ARMORS)-1
item = facility_equipment.item
duel_adjustment = facility_equipment.duel_adjustment
RULES = dict(initial_policy='source_then_explicit_signature_then_remake_role',
    combat_enabled=True, initiative_roll_min=20, initiative_roll_max=30,
    weight_capacity_martial_divisor=10, burden_hit_percent=3,
    burden_evasion_percent=2, martial_hit_divisor=4,
    hit_min=10, hit_max=95, retreat_chance_per_weight=5,
    retreat_loss_weight_threshold=8, retreat_loss_weight_divisor=4,
    loot_resolution='duel_defeat_not_permanent_death',
    guaranteed_loot_draws=0, conditional_loot_draws=1)
HIT_MATRIX = {'sword': {'sword':70,'blade':75,'spear':60},
    'blade': {'sword':55,'blade':60,'spear':70},
    'spear': {'sword':80,'blade':50,'spear':60}}
SIGNATURES = {'san14-candidate-0952':24,'san14-candidate-0147':15,
    'san14-candidate-0656':23,'san14-candidate-0987':21,
    'san14-candidate-0709':25,'san14-candidate-0551':26,
    'san14-candidate-0557':26,'san14-candidate-0215':27,
    'san14-candidate-0271':28}
UNIQUE = {('weapon',i) for i in (5,6,7,14,15,22,23)} | {('armor',6),('armor',7)}
SHOP = {('weapon',15):('danyang','san14-candidate-0147','person',400),
    ('weapon',23):('fuling','san14-candidate-0656','person',400),
    ('weapon',22):('wuwei',90,'martial',350),
    ('armor',6):('yongchang',90,'virtue',350)}
CONDITIONS = {
    ('weapon',5):('單挑擊敗君主馬騰，必定取得；全局唯一。','君主の馬騰を一騎討ちで破ると必ず獲得。戦役に1点。'),
    ('weapon',6):('單挑擊敗君主曹操，30%機率取得；全局唯一。','君主の曹操を一騎討ちで破ると30%で獲得。戦役に1点。'),
    ('weapon',7):('顯示等級1–2的武將單挑擊敗君主董卓，必定取得；全局唯一。','表示段階1～2の武将で君主の董卓を一騎討ちで破ると必ず獲得。戦役に1点。'),
    ('weapon',14):('單挑擊敗劉備、馬騰、曹操、董卓以外的君主，50%機率取得；全局唯一。','劉備・馬騰・曹操・董卓以外の君主を一騎討ちで破ると50%で獲得。戦役に1点。'),
    ('weapon',15):('關羽專屬；建業武器屋400金，僅一把。初始已持有時不重複販售。','関羽専用。建業の武器屋で400金、1点のみ。初期所持済みなら重複販売しません。'),
    ('weapon',22):('武90以上；姑臧武器屋350金，僅一把。','武90以上。姑臧の武器屋で350金、1点のみ。'),
    ('weapon',23):('張飛專屬；涪陵武器屋400金，僅一把。初始已持有時不重複販售。','張飛専用。涪陵の武器屋で400金、1点のみ。初期所持済みなら重複販売しません。'),
    ('armor',6):('德90以上；永昌武器屋350金，僅一件。','徳90以上。永昌の武器屋で350金、1点のみ。'),
    ('armor',7):('單挑擊敗君主劉備，必定取得；全局唯一。','君主の劉備を一騎討ちで破ると必ず獲得。戦役に1点。')}


def _key(slot, ident):
    return f'{slot}:{ident}'


def _normal(profile):
    martial = profile['martial_strength'] if isinstance(profile,dict) else profile.martial_strength
    return dict(weapon_id=16 if martial>=80 else 2 if martial>=60 else 0,
        armor_id=2 if martial>=80 else 1 if martial>=50 else 0,
        basis='remake_role_default; not_original_equipment')


def build_initials(people, original_records, appearance_profiles=None):
    """Join reviewed source IDs, with explicit requested signature overrides."""
    source = {row['person_id']:row for row in original_records if row.get('person_id')}
    if len(source) != sum(bool(row.get('person_id')) for row in original_records):
        raise ValueError('Duplicate original equipment identity')
    result = {}
    for person in people:
        pid=person['person_id'];profile=person.get('profile',person.get('stats',{}))
        row=_normal(profile)
        if pid in source:
            original=source[pid]
            weapon,armor=original['weapon_id'],original['armor_id']
            item('weapon',weapon);item('armor',armor)
            row=dict(weapon_id=weapon,armor_id=armor,basis='cnblogs_original_equipment_transcription',
                source=dict(source_row_id=original['source_row_id'],
                    weapon_id=weapon,armor_id=armor,weapon_label=original['weapon_label'],
                    armor_label=original['armor_label']))
        if pid in SIGNATURES:
            row.update(weapon_id=SIGNATURES[pid],basis='explicit_requested_novel_signature_override',
                signature=dict(person_id=pid,weapon_id=SIGNATURES[pid],
                    note='Requested novel equipment; numeric balance is a remake adaptation'))
        result[pid]=row
    return result


def _initial(game, officer):
    value=deepcopy(game.catalog.data.get('equipment_initial',{}).get(officer.person_id,
        _normal(officer.profile)))
    item('weapon',value['weapon_id']);item('armor',value['armor_id'])
    return value


def empty(game, state):
    return dict(schema=SCHEMA,initialized=[],uniques={},reserves={},loot_receipts=[])


def _pool(state):
    return state.extension['equipment']


def synchronize(game, state):
    pool=_pool(state)
    initialized=set(pool['initialized'])
    current={officer.person_id for officer in state.officers.values()}
    for officer in sorted(state.officers.values(),key=lambda o:o.person_id):
        if officer.person_id in initialized:
            continue
        row=_initial(game,officer)
        officer.weapon_id,officer.armor_id=row['weapon_id'],row['armor_id']
        for slot in ('weapon','armor'):
            ident=getattr(officer,slot+'_id')
            if (slot,ident) in UNIQUE:
                key=_key(slot,ident)
                if key in pool['uniques']:
                    raise ValueError('Duplicate initial unique equipment')
                pool['uniques'][key]=dict(slot=slot,item=ident,holder=officer.person_id,
                    turn=state.turn,method='initial')
        initialized.add(officer.person_id)
    # Normal lifecycle keeps deceased records. Removing an unused controlled
    # fixture person cannot leave a stale initialized reference behind.
    pool['initialized']=sorted(initialized & current)
    for pid in list(pool['reserves']):
        if pid not in current:
            del pool['reserves'][pid]


def combat_stats(officer):
    weapon,armor=item('weapon',officer.weapon_id),item('armor',officer.armor_id)
    martial=officer.profile.martial_strength
    if type(martial) is not int or not 1<=martial<=99:
        raise ValueError('Equipment martial bound')
    total=weapon['weight']+armor['weight']
    burden=max(0,total-martial//10)
    attack_penalty=max(0,(weapon['weight']*8-martial+9)//10) if officer.weapon_id else 0
    bonus=duel_adjustment(officer.weapon_id,officer.armor_id,martial)
    loss=min(max(0,officer.health-1),1+max(0,total-8)//4)
    return dict(base_martial=martial,weapon=weapon,armor=armor,
        attack_bonus=bonus['attack'],defense_bonus=bonus['defense'],
        total_weight=total,weight_penalty=attack_penalty,burden=burden,
        initiative_base=(officer.health+martial)//10-total,
        hit_penalty=burden*3,evasion_penalty=burden*2,
        retreat_health_min=0,retreat_health_max=loss,
        retreat_chance=min(100,total*5))


def _numbers(officer):
    """A stock preview needs no repeated item tables for every resident."""
    return {key:value for key,value in combat_stats(officer).items() if key not in ('weapon','armor')}


def duel_initiative(officer, roll):
    if type(roll) is not int or not 0<=roll<=10:
        raise ValueError('Equipment initiative roll')
    return combat_stats(officer)['initiative_base']+20+roll


def duel_hit_chance(attacker, defender):
    first,second=combat_stats(attacker),combat_stats(defender)
    base=HIT_MATRIX[first['weapon']['family']][second['weapon']['family']]
    chance=base+(first['base_martial']-second['base_martial'])//4-first['hit_penalty']+second['evasion_penalty']
    return max(10,min(95,chance))


def retreat_cost(officer, roll):
    if type(roll) is not int or not 0<=roll<=99:
        raise ValueError('Equipment retreat roll')
    stats=combat_stats(officer)
    return stats['retreat_health_max'] if roll<stats['retreat_chance'] else 0


def _reserve(state,pid):
    return _pool(state)['reserves'].setdefault(pid,dict(weapon=[],armor=[]))


def _store(state,pid,slot,ident):
    values=_reserve(state,pid)[slot]
    if ident not in values:
        values.append(ident);values.sort()


def _give(state,target,slot,ident,method):
    previous=getattr(target,slot+'_id')
    if previous==ident:
        raise GameError('這名武將已持有這件裝備。')
    _store(state,target.person_id,slot,previous)
    values=_reserve(state,target.person_id)[slot]
    if ident in values:values.remove(ident)
    setattr(target,slot+'_id',ident)
    if (slot,ident) in UNIQUE:
        _pool(state)['uniques'][_key(slot,ident)]=dict(slot=slot,item=ident,
            holder=target.person_id,turn=state.turn,method=method)
    return previous


def stock(town, slot):
    return [row for row in facility_equipment.stock(town,slot) if (slot,row['id']) not in UNIQUE]


def _reason(game,state,city,target,slot,ident,*,funds=True):
    merchandise=item(slot,ident)
    town=state.extension['facilities']['cities'][city.id]['town']
    if town<2:
        return ('本城尚未開放武器屋。','この都市では武器屋がまだ開いていません。')
    if (not target.alive or target.person_id not in {state.officers[i].person_id for i in city.roster.officer_ids}
            or target.faction_id!=city.owner):
        return ('請選擇本城所屬的在場武將。','この都市に所属する在場の武将を選択してください。')
    if getattr(target,slot+'_id')==ident or ident in _pool(state)['reserves'].get(target.person_id,{}).get(slot,[]):
        return ('這名武將已持有或保管這件裝備。','この武将は既にこの装備を所持または保管しています。')
    if (slot,ident) in UNIQUE:
        if _key(slot,ident) in _pool(state)['uniques']:
            return ('這件唯一裝備已被取得，不能重複購買。','この唯一装備は獲得済みで、重複購入できません。')
        rule=SHOP.get((slot,ident))
        if rule is None:
            return ('這件特殊裝備只能依條件取得，商店不販售。','この特殊装備は条件達成で獲得し、店では販売しません。')
        where,threshold,field,price=rule
        if city.id!=where:
            return ('這座城池不販售這件特殊裝備。','この都市ではこの特殊装備を販売していません。')
        if field=='person' and target.person_id!=threshold:
            return ('這件兵器只提供給指定武將。','この武器は指定武将専用です。')
        if field!='person' and getattr(target.profile,'martial_strength' if field=='martial' else 'virtue')<threshold:
            return ('武將能力未達購買條件。','武将の能力が購入条件に達していません。')
    elif ident not in {row['id'] for row in stock(town,slot)}:
        return ('本城武器屋沒有出售這件裝備。','この都市の武器屋ではこの装備を販売していません。')
    price=SHOP[(slot,ident)][3] if (slot,ident) in SHOP else merchandise['price']
    if funds and city.gold<price:
        return ('本城金錢不足，操作未執行。','都市の資金が不足しているため実行できません。')
    return ('','')


def purchase_quote(game,state,city,target,slot,ident):
    if isinstance(city,str):city=state.cities[city]
    if not hasattr(target,'person_id'):target=state.officers[target]
    item(slot,ident)
    tc,ja=_reason(game,state,city,target,slot,ident)
    if tc:raise GameError(tc)
    merchandise=item(slot,ident)
    price=SHOP[(slot,ident)][3] if (slot,ident) in SHOP else merchandise['price']
    before=combat_stats(target)
    after=combat_stats(replace(target,**{slot+'_id':ident}))
    return dict(merchandise,price=price,previous=getattr(target,slot+'_id'),
        before=before,after=after,eligible=True,reason_tc='',reason_ja='')


def claim_purchase(game,state,city,target,slot,ident):
    if isinstance(city,str):city=state.cities[city]
    if not hasattr(target,'person_id'):target=state.officers[target]
    tc,_=_reason(game,state,city,target,slot,ident,funds=False)
    if tc:raise GameError(tc)
    return _give(state,target,slot,ident,'purchase')


def owned_for(game,state,ident):
    officer=state.officers[ident]
    result=[]
    for slot,values in _pool(state)['reserves'].get(officer.person_id,{}).items():
        for value in values:
            row=item(slot,value)
            result.append(dict(row,slot=slot,item=value,
                before=combat_stats(officer),after=combat_stats(replace(officer,**{slot+'_id':value}))))
    return result


def equip_owned(game,state,payload,owner):
    from . import facilities
    facilities._payload(payload,{'city','actor','officer','slot','item'})
    city=facilities._city(game,state,payload['city'],owner,kind='equip_owned')
    actor=facilities._actor(game,state,city,payload['actor'])
    target=state.officers[facilities._target(game,state,city,payload['officer'])]
    slot,ident=payload['slot'],payload['item'];item(slot,ident)
    if ident not in _pool(state)['reserves'].get(target.person_id,{}).get(slot,[]):
        raise GameError('這名武將沒有保管這件備用裝備。')
    if (slot,ident) in UNIQUE and _pool(state)['uniques'].get(_key(slot,ident),{}).get('holder')!=target.person_id:
        raise GameError('唯一裝備持有人不符。')
    facilities._charge(state,city,actor,0,target.runtime_id,kind='equip_owned')
    previous=_give(state,target,slot,ident,'owned')
    details=dict(actor=state.officers[actor].person_id,target=target.person_id,
        from_person=target.person_id,slot=slot,item=ident,previous=previous,
        method='owned',battle_id=None,chance=0,roll=-1)
    game._emit_event(state,'equipment_acquired',city_ids=[city.id],factions=[owner],
        person_ids=list(dict.fromkeys([details['actor'],details['target']])),details=details)
    return details


def shop_stock(game,state,city,slot):
    from . import facilities
    if isinstance(city,str):city=state.cities[city]
    town=state.extension['facilities']['cities'][city.id]['town']
    offers=stock(town,slot)
    if town>=2:
        for (kind,ident),(where,_,_,price) in SHOP.items():
            if kind==slot and city.id==where:
                offers.append(dict(item(slot,ident),price=price))
    targets=[ident for ident in city.roster.officer_ids if facilities._resident(game,state,city,ident)]
    result=[]
    for offer in offers:
        ident=offer['id'];previews={};eligible=[];reasons={}
        for ref in targets:
            person=state.officers[ref]
            tc,ja=_reason(game,state,city,person,slot,ident)
            previews[str(ref)]=dict(before=_numbers(person),
                after=_numbers(replace(person,**{slot+'_id':ident})),
                eligible=not tc,reason_tc=tc,reason_ja=ja)
            if not tc:eligible.append(ref)
            else:reasons[str(ref)]=dict(tc=tc,ja=ja)
        condition=CONDITIONS.get((slot,ident),('',''))
        result.append(dict(offer,eligible_targets=eligible,reasons=reasons,
            preview_by_officer=previews,condition_tc=condition[0],condition_ja=condition[1],
            unique=(slot,ident) in UNIQUE,claimed=_key(slot,ident) in _pool(state)['uniques'],
            can_buy=bool(eligible)))
    return result


def _special(state=None):
    registry=_pool(state)['uniques'] if state is not None else {}
    return [dict(slot=slot,item=ident,**item(slot,ident),unique=True,
        claimed=_key(slot,ident) in registry,
        holder=registry.get(_key(slot,ident),{}).get('holder'),
        condition_tc=CONDITIONS[(slot,ident)][0],condition_ja=CONDITIONS[(slot,ident)][1])
        for slot,ident in sorted(UNIQUE)]


def initial_view(game,person_id):
    if person_id not in game.catalog.ids:raise ValueError('Unknown initial equipment person')
    row=game.catalog.by_id[game.catalog.ids[person_id]]
    profile=game.catalog.profiles[row['runtime_id']]
    officer=SimpleNamespace(profile=profile,person_id=person_id,
        health=row.get('initialization',{}).get('health',profile.health_max),
        **{k:v for k,v in _initial(game,SimpleNamespace(person_id=person_id,profile=profile)).items()
           if k in ('weapon_id','armor_id')})
    return dict(combat_stats(officer),scope='initial',person_id=person_id,
        initial=_initial(game,officer),owned=[])


def view(game,state):
    result=dict(schema=SCHEMA,rules=deepcopy(dict(RULES,**game.catalog.data.get('equipment_rules',{}))),items=dict(weapon=deepcopy(list(WEAPONS)),
        armor=deepcopy(list(ARMORS))),officers={},special=_special(state))
    if state is None:return result
    for ident,officer in state.officers.items():
        result['officers'][str(ident)]=dict(combat_stats(officer),scope='current',
            person_id=officer.person_id,initial=_initial(game,officer),owned=owned_for(game,state,ident))
    return result


def duel_loot(game,state,battle,winner,loser):
    winner=state.officers[winner];loser=state.officers[loser]
    leaders=state.extension.get('leaders',{})
    if leaders.get(loser.faction_id)!=loser.runtime_id or winner.faction_id==loser.faction_id:
        return None
    if loser.person_id=='san14-candidate-0771':slot,ident,chance='weapon',5,100
    elif loser.person_id=='san14-candidate-0521':slot,ident,chance='weapon',6,30
    elif loser.person_id=='san14-candidate-0736':
        if winner.tier+1>2:return None
        slot,ident,chance='weapon',7,100
    elif loser.person_id=='san14-candidate-0952':slot,ident,chance='armor',7,100
    else:slot,ident,chance='weapon',14,50
    pool=_pool(state);receipt=f'{battle["id"]}:{loser.person_id}:{slot}:{ident}'
    if receipt in pool['loot_receipts']:return None
    pool['loot_receipts'].append(receipt)
    claim=pool['uniques'].get(_key(slot,ident))
    if claim and claim['holder']!=loser.person_id:return None
    roll=state.rng.next()%100 if chance<100 else -1
    if roll>=chance:return None
    if claim:
        if getattr(loser,slot+'_id')==ident:
            candidates=pool['reserves'].get(loser.person_id,{}).get(slot,[])
            fallback=next((value for value in candidates if (slot,value) not in UNIQUE),0)
            if fallback in candidates:candidates.remove(fallback)
            setattr(loser,slot+'_id',fallback)
        else:
            pool['reserves'][loser.person_id][slot].remove(ident)
    previous=_give(state,winner,slot,ident,'duel')
    details=dict(actor=winner.person_id,target=winner.person_id,from_person=loser.person_id,
        slot=slot,item=ident,previous=previous,method='duel',battle_id=battle['id'],chance=chance,roll=roll)
    game._emit_event(state,'equipment_acquired',city_ids=[battle['target']],
        factions=[winner.faction_id],person_ids=[winner.person_id,loser.person_id],details=details)
    return details


def validate(game,state):
    override=game.catalog.data.get('equipment_rules',{})
    if not isinstance(override,dict) or set(override)-set(RULES):
        raise ValueError('Equipment rule fields')
    for key,value in override.items():
        if key=='combat_enabled':
            if type(value) is not bool:raise ValueError('Equipment combat switch')
        elif type(value) is not type(RULES[key]) or value!=RULES[key]:
            raise ValueError('Equipment fixed documented rule')
    initials=game.catalog.data.get('equipment_initial',{})
    if not isinstance(initials,dict):raise ValueError('Equipment initial fields')
    if 'people' in game.catalog.data and set(initials)!={row['person_id'] for row in game.catalog.data['people']}:
        raise ValueError('Equipment initial identity domain')
    for pid,initial in initials.items():
        if (not isinstance(pid,str) or not isinstance(initial,dict)
                or set(initial)-{'weapon_id','armor_id','basis','source','signature'}
                or not {'weapon_id','armor_id','basis'}<=set(initial)
                or not isinstance(initial['basis'],str) or not 1<=len(initial['basis'])<=200):
            raise ValueError('Equipment initial record')
        item('weapon',initial['weapon_id']);item('armor',initial['armor_id'])
        original=initial.get('source')
        if original is not None:
            if (not isinstance(original,dict) or set(original)!={'source_row_id','weapon_id','armor_id','weapon_label','armor_label'}
                    or type(original['weapon_id']) is not int or not 0<=original['weapon_id']<=23
                    or type(original['armor_id']) is not int or not 0<=original['armor_id']<=7
                    or any(not isinstance(original[key],str) or not 1<=len(original[key])<=200
                        for key in ('source_row_id','weapon_label','armor_label'))):
                raise ValueError('Equipment original source reference')
        signature=initial.get('signature')
        if signature is not None:
            if (not isinstance(signature,dict) or set(signature)!={'person_id','weapon_id','note'}
                    or pid not in SIGNATURES or signature['person_id']!=pid
                    or type(signature['weapon_id']) is not int or signature['weapon_id']!=SIGNATURES[pid]
                    or initial['weapon_id']!=signature['weapon_id']
                    or not isinstance(signature['note'],str) or not 1<=len(signature['note'])<=300):
                raise ValueError('Equipment signature source reference')
    pool=_pool(state)
    if (not isinstance(pool,dict) or set(pool)!={'schema','initialized','uniques','reserves','loot_receipts'}
            or pool['schema']!=SCHEMA):raise ValueError('Equipment schema')
    people={officer.person_id:officer for officer in state.officers.values()}
    initialized=pool['initialized']
    if (not isinstance(initialized,list) or any(not isinstance(pid,str) for pid in initialized)
            or initialized!=sorted(people)):raise ValueError('Equipment initialization domain')
    if not isinstance(pool['reserves'],dict) or set(pool['reserves'])-set(people):
        raise ValueError('Equipment reserve domain')
    holders={}
    for pid,officer in people.items():
        for slot in ('weapon','armor'):
            ident=getattr(officer,slot+'_id');item(slot,ident)
            if (slot,ident) in UNIQUE:
                holders.setdefault(_key(slot,ident),[]).append(pid)
        reserve=pool['reserves'].get(pid)
        if reserve is None:continue
        if not isinstance(reserve,dict) or set(reserve)!={'weapon','armor'}:
            raise ValueError('Equipment reserve fields')
        for slot,values in reserve.items():
            if (not isinstance(values,list) or len(values)>len(WEAPONS if slot=='weapon' else ARMORS)
                    or any(type(value) is not int for value in values)
                    or values!=sorted(set(values)) or getattr(officer,slot+'_id') in values):
                raise ValueError('Equipment reserve contents')
            for value in values:
                item(slot,value)
                if (slot,value) in UNIQUE:holders.setdefault(_key(slot,value),[]).append(pid)
    if (not isinstance(pool['uniques'],dict) or set(pool['uniques'])!=set(holders)
            or any(len(values)!=1 for values in holders.values())):
        raise ValueError('Equipment unique physical conservation')
    for key,row in pool['uniques'].items():
        if (not isinstance(row,dict) or set(row)!={'slot','item','holder','turn','method'}
                or (row['slot'],row['item']) not in UNIQUE or type(row['item']) is not int
                or key!=_key(row['slot'],row['item']) or row['holder']!=holders[key][0]
                or type(row['turn']) is not int or not 1<=row['turn']<=state.turn
                or row['method'] not in ('initial','purchase','duel','owned')):
            raise ValueError('Equipment unique ledger')
    receipts=pool['loot_receipts']
    if (not isinstance(receipts,list) or len(receipts)>9*max(1,getattr(state,'battle_counter',0))
            or any(not isinstance(value,str) or not 1<=len(value)<=200 for value in receipts)
            or len(set(receipts))!=len(receipts)):
        raise ValueError('Equipment loot receipt domain')
    known_battles=set(getattr(state,'settled_battles',[]))
    if state.battle:known_battles.add(state.battle['id'])
    for receipt in receipts:
        parts=receipt.rsplit(':',3)
        if len(parts)!=4:raise ValueError('Equipment loot receipt fields')
        battle_id,pid,slot,value=parts
        if (battle_id not in known_battles or pid not in people or not value.isascii()
                or not value.isdigit() or value!=str(int(value)) or (slot,int(value)) not in UNIQUE):
            raise ValueError('Equipment loot receipt identity')
