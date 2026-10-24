"""Independent mainland mechanics: personnel,16 tactics, duels and campaign AI.

Names/capacities reference the research; effects and balance below are explicit
remake designs. No original engine, ROM tables or control IR are loaded.
"""
from .errors import GameError
from . import presentation
from .officers import (YearState, experience_tier, initialize_officer, integer,
                       recruitment_loyalty, select_deployment, year_state,
                       parse_officer_ref, deserialize_officer_ref, ref_sort_key, is_generated_ref, appearance_values)

TACTICS = (
    ('火計',6,'fire','单体兵损，水地形不可用'), ('陥穽',5,'trap','单体体力损伤，平地或山地'),
    ('虚兵',4,'confuse','目标下一次反击失效'), ('要撃',6,'strike','单体兵损'),
    ('乱水',7,'water','水地形单体兵损'), ('火箭',8,'supply','烧毁敌军出发城部分粮食'),
    ('偽撃転殺',8,'feint','单体兵损并扰乱反击'), ('共殺',8,'area','攻击最多三支敌军'),
    ('籠絡',10,'surrender','劝降一支敌军；兵员缴入该城预备兵，武将战后在野'),
    ('落石',9,'rock','山地兵损及体力损伤'), ('連環',9,'chain','水地形最多三队反击失效'),
    ('十面埋伏',10,'ambush','兵数至少100，设伏后下一次反击触发，一次有效'),
    ('水攻',10,'flood','水地形敌军全体兵损'), ('連弩',8,'crossbow','攻击最多两支敌军'),
    ('劫火',12,'inferno','非水地形敌军全体兵损'), ('奇門遁甲',10,'guard','自身获得两次减伤保护'))


class ExpandedCampaign:
    def _initialize_expansion(self, state):
        state.extension = {'free_locations': {}, 'officer_actions': {},
                           'leaders': dict(self.catalog.data['faction_rulers']),
                           'ended_factions': [], 'ai_queue': [], 'ai_cursor': 0,
                           'ai_attacks': 0, 'ai_reports': [], 'outcome': None, 'pending_succession': {}}
        # A dated source snapshot can resolve the otherwise ambiguous death year
        # at scenario start. Later entry still uses the normal annual rules.
        for row in self.catalog.data.get('initial_free_officers', []):
            pid = row['person_id']; ident = self.catalog.ids[pid]
            if ident in state.officers or row['city'] not in state.cities:
                raise ValueError('duplicate or unlocated initial free officer')
            state.officers[ident] = initialize_officer(
                self.catalog.definitions[pid], ident, self.catalog.profiles[ident],
                **appearance_values(self.catalog.profiles[ident], self.catalog.by_id[ident].get('initialization')),
                year=state.year, rules=self.catalog.rules,
                resolve_death_year=row.get('resolve_death_year', False))
            state.extension['free_locations'][str(ident)] = row['city']
        self._spawn_eligible(state)

    def _spawn_eligible(self, state):
        """Annual eligibility never fills missing stats or revives existing IDs."""
        for ident, row in self.catalog.by_id.items():
            if ident in state.officers or self.catalog.profiles[ident].missing:
                continue
            person = self.catalog.definitions[row['person_id']]
            city = self.catalog.data['appearance_locations'].get(person.person_id)
            windows = self.catalog.data.get('appearance_windows', {}).get(person.person_id)
            resolve_death_year = False
            if windows is not None:
                current = next((w for w in windows if tuple(w['start']) <=
                    (state.year, state.month) <= tuple(w['end'])), None)
                if current is None:
                    continue
                city = current['city']
                resolve_death_year = current.get('resolve_death_year') is True
            ys = year_state(person, state.year)
            if (ys != YearState.AVAILABLE and not (ys == YearState.DEATH_YEAR_REVIEW
                    and resolve_death_year)) or city not in state.cities:
                continue
            state.officers[ident] = initialize_officer(person, ident, self.catalog.profiles[ident],
                **appearance_values(self.catalog.profiles[ident], row.get('initialization')),
                year=state.year, rules=self.catalog.rules, resolve_death_year=resolve_death_year)
            state.extension['free_locations'][str(ident)] = city
            self._note(state, f'{person.name}已到登场年代，在{self.catalog.map_cities[city]["name"]}待访。')

    def _neighbors(self, city, state=None):
        from .route_hazards import route_allowed
        neighbors=set()
        routes=self._known_routes(state)
        for route in routes:
            if city not in (route['from'],route['to']):continue
            target=route['to'] if city==route['from'] else route['from']
            if route_allowed(self.catalog.data,route,city,target):neighbors.add(target)
        return sorted(neighbors)

    def _personnel_actor(self, state, city, ident):
        ident = parse_officer_ref(ident, self.catalog.rules)
        if ident in self._march_ids(state): raise GameError('这名武将正在行军。')
        if ident not in city.roster.officer_ids or not state.officers[ident].alive or state.officers[ident].health < 1:
            raise GameError('请选择本城健康的武将。')
        if state.extension['officer_actions'].get(str(ident)) == state.turn:
            raise GameError('这名武将本回合已处理人事或调动。')
        return state.officers[ident]

    def _free_candidates(self, state, city):
        near = {city.id} | {k for k in self._neighbors(city.id,state) if k in state.cities and state.cities[k].owner in {city.owner, 'neutral'}}
        return [i for i, o in state.officers.items() if o.alive and o.faction_id is None
                and year_state(self.person_definition(state, i),state.year) in {YearState.AVAILABLE, YearState.DEATH_YEAR_REVIEW}
                and state.extension['free_locations'].get(str(i)) in near]

    def _recruit_officer(self, state, payload):
        city = self._owned_city(state, payload.get('city'), action=True)
        actor = self._personnel_actor(state, city, payload.get('actor'))
        self._attempt_recruitment(state, city, actor, payload.get('officer'))

    def _staff_recruit(self, state, payload):
        city = self._owned_city(state, payload.get('city'), action=True)
        self._staff_recruit_for_owner(state, city, payload.get('actor'), payload.get('officer'), state.player)

    def _staff_recruit_for_owner(self, state, city, actor_id, target_id, owner):
        if state.phase not in {'city', 'ai'} or city.owner != owner or owner == 'neutral' or city.action_used:
            raise GameError('当前不能由地方文吏执行寻访。')
        person = state.extension['civil_staff']['people'].get(actor_id) if isinstance(actor_id, str) else None
        if (not person or person['city'] != city.id or person['owner'] != owner
                or not person['working'] or person['health'] < 1 or person['action_turn'] == state.turn):
            raise GameError('请选择本城尚未行动且正常任职的文吏。')
        actor = self._personnel_actor(state, city, actor_id)
        self._attempt_recruitment(state, city, actor, target_id)

    def _attempt_recruitment(self, state, city, actor, target_id):
        """Historical officers and hired clerks use the same personnel formula."""
        ident = parse_officer_ref(target_id,self.catalog.rules)
        if ident not in self._free_candidates(state, city):
            raise GameError('目标尚未登场、已仕官，或不在本城及可访问的邻城。')
        if self._city_occupancy(state, city) >= self.catalog.rules.city_officer_capacity:
            raise GameError(f'本城已满{self.catalog.rules.city_officer_capacity}人，招募未执行。')
        fee = self.catalog.data['rules']['recruit_officer_gold']
        if city.gold < fee: raise GameError('招募金钱不足。')
        from .domestic import can_attempt,record_attempt
        if not can_attempt(state,city.owner,ident):raise GameError('本势力本旬已尝试招募该武将。')
        candidate = state.officers[ident]
        chance = max(15,min(95,35 + actor.profile.virtue//2 + actor.profile.intellect//5 - candidate.profile.virtue//5))
        success = state.rng.next()%100 < chance
        record_attempt(state,city.owner,ident,success)
        city.gold -= fee; city.action_used = True
        state.extension['officer_actions'][str(actor.runtime_id)] = state.turn
        if success:
            candidate.faction_id=city.owner
            leader = state.extension['leaders'].get(city.owner)
            virtue = state.officers[leader].profile.virtue if leader in state.officers else actor.profile.virtue
            candidate.loyalty=recruitment_loyalty(virtue,candidate.loyalty)
            city.roster.officer_ids.append(ident)
            state.extension['free_locations'].pop(str(ident),None)
            state.extension['officer_actions'][str(ident)] = state.turn
        actor_name = self.person_name(state, actor.runtime_id)
        self._note(state,f'{actor_name}寻访{self.person_name(state, ident)}，招募{"成功" if success else "未获应允"}，花费{fee}金。')

    def _persuadable(self,state,city):
        neighbors=set(self._neighbors(city.id,state)) & set(state.cities)
        return [ident for key in sorted(neighbors) for ident in state.cities[key].roster.officer_ids
                if state.cities[key].owner not in {city.owner,'neutral'}
                and state.officers[ident].alive and state.officers[ident].loyalty<100
                and ident not in self._march_ids(state)
                and ident not in state.extension['leaders'].values()]

    def _persuade_officer(self,state,payload):
        city=self._owned_city(state,payload.get('city'),action=True)
        actor=self._personnel_actor(state,city,payload.get('actor'))
        ident=parse_officer_ref(payload.get('officer'),self.catalog.rules)
        if ident not in self._persuadable(state,city):raise GameError('只能劝降邻城的非君主敌将。')
        if self._city_occupancy(state, city)>=self.catalog.rules.city_officer_capacity:
            raise GameError(f'本城已满{self.catalog.rules.city_officer_capacity}人，劝降未执行。')
        fee=self.catalog.data['rules']['persuade_officer_gold']
        if city.gold<fee:raise GameError('劝降金钱不足。')
        from .domestic import can_attempt,record_attempt
        if not can_attempt(state,city.owner,ident):raise GameError('本势力本旬已尝试招募该武将。')
        self._attempt_defection(state,city,actor,ident)
        self._reconcile_factions(state)

    def _attempt_defection(self,state,city,actor,ident):
        fee=self.catalog.data['rules']['persuade_officer_gold']
        if city.gold<fee:raise GameError('劝降金钱不足。')
        from .domestic import can_attempt,record_attempt
        if not can_attempt(state,city.owner,ident):raise GameError('本势力本旬已尝试招募该武将。')
        target=state.officers[ident]
        chance=max(5,min(75,50+(actor.profile.virtue-target.loyalty)//2+(actor.profile.intellect-target.profile.intellect)//4))
        success=state.rng.next()%100<chance
        record_attempt(state,city.owner,ident,success)
        city.gold-=fee;city.action_used=True
        state.extension['officer_actions'][str(actor.runtime_id)]=state.turn
        if success:
            origin=next(c for c in state.cities.values() if ident in c.roster.officer_ids)
            origin.roster.officer_ids.remove(ident);city.roster.officer_ids.append(ident)
            target.faction_id=city.owner
            leader=state.extension['leaders'][city.owner]
            target.loyalty=recruitment_loyalty(state.officers[leader].profile.virtue,target.loyalty)
            state.extension['officer_actions'][str(ident)]=state.turn
        self._note(state,f'{self.person_name(state, actor.runtime_id)}劝说{self.person_name(state, ident)}，{"转属成功" if success else "遭到拒绝"}，花费{fee}金。')

    def _transfer(self,state,payload):
        source=self._owned_city(state,payload.get('source'),action=True)
        destination=self._owned_city(state,payload.get('target'))
        ids=payload.get('officers')
        if source.id==destination.id or not isinstance(ids,list) or not ids or len(ids)!=len(set(ids)):
            raise GameError('请选择不同的目的城和不重复的调动名单。')
        for ident in ids: self._personnel_actor(state,source,ident)
        self._queue_march(state,source,destination,ids,'transfer',payload.get('route_mode','fastest'))

    def _start_expanded_battle(self,state,source,target,ids,*,paid=False):
        selected=select_deployment(source.roster,ids,state.officers)
        cost=0 if paid else max(1,sum(state.officers[i].troops for i in selected)//25)
        if not paid and source.grain<cost: raise GameError('出征粮食不足。')
        marching=self._march_ids(state)
        defenders=sorted((i for i in target.roster.officer_ids if i not in marching and state.officers[i].troops>0 and state.officers[i].health>0),key=lambda i:(-state.officers[i].troops,ref_sort_key(i)))[:10]
        def units(ids): return [{'id':i,'troops':state.officers[i].troops,'start':state.officers[i].troops,'martial':state.officers[i].profile.martial_strength} for i in ids]
        support={str(i):{'health':state.officers[i].health,'energy':18,'stunned':0,'guard':0} for i in [*selected,*defenders]}
        from .domestic import unit_morale
        for ident in [*selected,*defenders]:
            support[str(ident)]['morale']=unit_morale(self,state,ident)
        state.battle_counter+=1
        state.battle={'id':f'battle-{state.battle_counter}','source':source.id,'target':target.id,'attacker':source.owner,'defender':target.owner,
                      'attackers':units(selected),'defenders':units(defenders),'used':[],'round':1,'outcome':None,'supply_cost':cost,
                      'log':[f'{self.catalog.map_cities[source.id]["name"]}向{self.catalog.map_cities[target.id]["name"]}出征。'],
                      'extended':{'support':support,'duel':None,'duel_history':[],'ambush':None,'surrenders':{},'withdrawn':None}}
        if not paid: source.grain-=cost;source.action_used=True
        state.phase='battle'
        state.extension['officer_actions'].update({str(i):state.turn for i in selected})
        self._note(state,state.battle['log'][0])
        if state.player in (source.owner,target.owner):
            self._emit_event(state,'battle_started',person_ids=[state.officers[i].person_id for i in [*selected[:1],*defenders[:1]]],
                city_ids=[source.id,target.id],factions=[source.owner,target.owner],
                details=dict(battle_id=state.battle['id'],attacker=source.owner,defender=target.owner))
        if not defenders: state.battle['outcome']='victory';state.phase='result'
        # Deployment makes participants unavailable for local civil duties.
        from . import treasures
        treasures.synchronize(self,state)

    def _player_sides(self,state):
        return ('attackers','defenders') if state.battle['attacker']==state.player else ('defenders','attackers')

    def _battle_selection(self,state,payload,*,allow_duel=False):
        b=state.battle
        if state.phase!='battle' or not b or payload.get('battle_id')!=b['id']:
            raise GameError('当前没有待操作的战斗。')
        if b['extended']['duel'] and not allow_duel: raise GameError('请先完成或退出当前单挑。')
        own,foe=self._player_sides(state)
        a_id=parse_officer_ref(payload.get('actor'),self.catalog.rules)
        t_id=parse_officer_ref(payload.get('target'),self.catalog.rules)
        actor=next((u for u in b[own] if u['id']==a_id and u['troops']>0),None)
        target=next((u for u in b[foe] if u['id']==t_id and u['troops']>0),None)
        if actor is None or target is None or actor['id'] in b['used']:
            raise GameError('请选择未行动的本方部队与有效敌军。')
        return b,actor,target,own,foe

    def _battle_result(self,state):
        b=state.battle
        attacking=any(u['troops']>0 for u in b['attackers'])
        defending=any(u['troops']>0 for u in b['defenders'])
        if not attacking and not defending:
            b['outcome']='retreat';b['log'].append('双方部队均已败退，城池归属不变。')
        elif not defending: b['outcome']='victory'
        elif not any(u['troops']>0 for u in b['attackers']): b['outcome']='defeat'
        if b['outcome']: state.phase='result';b['extended']['duel']=None
        b['log'][:]=b['log'][-80:]

    def _counter(self,state,foe,actor):
        from .difficulty import get_settings
        from .tactical_ai import choose_action
        b=state.battle
        if actor['troops']<=0:return
        own='defenders' if foe=='attackers' else 'attackers'
        choice=choose_action(state,b,foe,own,self.catalog.map_cities[b['target']]['terrain'],TACTICS,
            settings=get_settings(state),damage_percent=self.catalog.data['rules']['battle_damage_percent'],responding=True)
        if choice:self._perform_battle_action(state,choice,foe,own,finish=False,counter=True)

    def _trigger_ambush(self,state,actor,own,*,counter=False):
        """A trap belongs to its actor's side; only an opposing action trips it."""
        b=state.battle;x=b['extended'];trap=x['ambush']
        if not trap:return
        side=next((key for key in ('attackers','defenders') if any(u['id']==trap['actor'] for u in b[key])),None)
        ambusher=next((u for key in ('attackers','defenders') for u in b[key] if u['id']==trap['actor']),None)
        if ambusher is None or ambusher['troops']<=0:x['ambush']=None;return
        if side==own:return
        before=presentation.snapshot(self,state)
        loss=min(actor['troops'],max(1,state.officers[trap['actor']].profile.intellect*2))
        actor['troops']-=loss;x['ambush']=None
        b['log'].append(f'十面埋伏触发，{self.person_name(state, actor["id"])}损兵{loss}。')
        presentation.record(self,state,before,kind='ambush',actor=ambusher['id'],
            target=actor['id'],own=side,counter=counter,tactic=11,effect='ambush')

    def _perform_battle_action(self,state,choice,own,foe,*,finish=False,counter=False):
        b=state.battle
        actor=next((u for u in b[own] if u['id']==choice['actor'] and u['troops']>0),None)
        target=next((u for u in b[foe] if u['id']==choice['target'] and u['troops']>0),None)
        if actor is None or target is None:return False
        if choice['kind']=='tactic':
            self._execute_tactic(state,actor,target,own,foe,choice['tactic'],finish=finish,counter=counter)
        else:self._execute_attack(state,actor,target,own,foe,finish=finish,counter=counter)
        return True

    def _finish_action(self,state,actor,own,foe,*,respond=True):
        b=state.battle
        if actor['id'] not in b['used']: b['used'].append(actor['id'])
        self._battle_result(state)
        if state.phase=='battle' and respond:self._counter(state,foe,actor)
        self._battle_result(state)
        if state.phase=='battle' and all(u['id'] in b['used'] for u in b[own] if u['troops']>0):
            b['used']=[];b['round']+=1
            for s in b['extended']['support'].values():s['energy']=min(18,s['energy']+4)
        b['log'][:]=b['log'][-80:]

    def _expanded_attack(self,state,payload):
        b,actor,target,own,foe=self._battle_selection(state,payload)
        self._execute_attack(state,actor,target,own,foe)

    def _execute_attack(self,state,actor,target,own,foe,*,finish=True,counter=False):
        b=state.battle
        self._trigger_ambush(state,actor,own,counter=counter)
        before=presentation.snapshot(self,state)
        if actor['troops']<=0:
            presentation.record(self,state,before,kind='attack',actor=actor['id'],
                target=target['id'],own=own,counter=counter,success=False,skipped=True)
            if finish:self._finish_action(state,actor,own,foe)
            else:self._battle_result(state)
            return
        s=b['extended']['support'][str(actor['id'])]
        skipped=bool(s['stunned'])
        if skipped:
            s['stunned']-=1;b['log'].append(f'{self.person_name(state, actor["id"])}受扰乱，行动跳过。')
        else:
            loss=self._damage(state,actor,target)
            defense=b['extended']['support'][str(target['id'])]
            if defense['guard']:loss=max(1,loss//2);defense['guard']-=1
            target['troops']-=loss;b['log'].append(f'{self.person_name(state, actor["id"])}{"反击" if counter else "攻击"}{self.person_name(state, target["id"])}，损兵{loss}。')
        presentation.record(self,state,before,kind='attack',actor=actor['id'],
            target=target['id'],own=own,counter=counter,success=not skipped,skipped=skipped)
        if finish:self._finish_action(state,actor,own,foe)
        else:self._battle_result(state)

    def _tactic(self,state,payload):
        b,actor,target,own,foe=self._battle_selection(state,payload)
        tid=integer(payload.get('tactic'),0,15,'tactic')
        self._execute_tactic(state,actor,target,own,foe,tid)

    def _execute_tactic(self,state,actor,target,own,foe,tid,*,finish=True,counter=False):
        from .tactical_ai import tactic_reason
        b=state.battle
        title,cost,effect,_=TACTICS[tid];x=b['extended'];support=x['support'];a=support[str(actor['id'])]
        terrain=self.catalog.map_cities[b['target']]['terrain']
        reason=tactic_reason(state,b,actor,target,own,foe,terrain,TACTICS[tid])
        if reason:raise GameError(reason)
        self._trigger_ambush(state,actor,own,counter=counter)
        before=presentation.snapshot(self,state)
        if actor['troops']<=0:
            presentation.record(self,state,before,kind='tactic',actor=actor['id'],
                target=target['id'],own=own,counter=counter,tactic=tid,effect=effect,
                success=False,skipped=True)
            if finish:self._finish_action(state,actor,own,foe)
            else:self._battle_result(state)
            return
        enemies=[u for u in b[foe] if u['troops']>0];p=state.officers[actor['id']].profile;t=state.officers[target['id']]
        a['energy']-=cost
        chance=max(10,min(95,60+(p.intellect-t.profile.intellect)//2))
        if effect=='surrender':chance=max(5,min(80,40+(p.virtue-t.loyalty)//2))
        success=effect in {'ambush','guard'} or state.rng.next()%100<chance
        if not success:b['log'].append(f'{self.person_name(state, actor["id"])}施放{title}，未能奏效。')
        elif effect=='ambush':x['ambush']={'actor':actor['id']};b['log'].append('十面埋伏已设置，等待下一次敌方反击。')
        elif effect=='guard':a['guard']=2;b['log'].append(f'{title}使本队获得两次减伤。')
        elif effect in {'confuse','chain'}:
            victims=[target] if effect=='confuse' else [target]+[u for u in enemies if u is not target][:2]
            for u in victims:support[str(u['id'])]['stunned']=1
            b['log'].append(f'{title}扰乱{len(victims)}队，下次反击失效。')
        elif effect=='surrender':
            x['surrenders'][str(target['id'])]=target['troops'];target['troops']=0
            b['log'].append(f'{self.person_name(state, target["id"])}接受劝降；战后转在野，兵员入城。')
        elif effect=='supply':
            receiver=state.cities[b['target'] if foe=='defenders' else b['source']]
            loss=min(receiver.grain,max(1,receiver.grain//8+p.intellect))
            receiver.grain-=loss;b['log'].append(f'火箭烧毁敌军城内粮食{loss}。')
        else:
            victims=([target]+[u for u in enemies if u is not target])[:3 if effect=='area' else 2 if effect=='crossbow' else 20 if effect in {'flood','inferno'} else 1]
            for u in victims:
                loss=min(u['troops'],max(1,p.intellect*(1 if effect=='trap' else 2)+(state.rng.next()%31)))
                if effect=='trap':loss=0
                u['troops']-=loss
                if effect in {'trap','rock'}:
                    hp=support[str(u['id'])];hp['health']=max(1,hp['health']-max(1,p.intellect//4))
                    if hp['health']==1:u['troops']=0
                if effect=='feint':support[str(u['id'])]['stunned']=1
                b['log'].append(f'{title}命中{self.person_name(state, u["id"])}，损兵{loss}。')
        if hasattr(self,'_emit_event') and state.player in (b['attacker'],b['defender']):
            self._emit_event(state,'tactic',person_ids=[state.officers[actor['id']].person_id,state.officers[target['id']].person_id],city_ids=[b['target']],
                factions=[b['attacker'],b['defender']],
                details={'tactic':tid,'success':success})
        presentation.record(self,state,before,kind='tactic',actor=actor['id'],
            target=target['id'],own=own,counter=counter,tactic=tid,effect=effect,success=success)
        if finish:self._finish_action(state,actor,own,foe,respond=effect!='ambush')
        else:self._battle_result(state)

    def _duel_start(self,state,payload):
        b,actor,target,own,foe=self._battle_selection(state,payload)
        a=state.officers[actor['id']].profile.martial_strength;t=state.officers[target['id']].profile.martial_strength
        if b['extended']['support'][str(actor['id'])]['stunned']:raise GameError('受扰乱部队不能挑战单挑。')
        before=presentation.snapshot(self,state)
        # An opponent is free to refuse; refusal consumes the challenger's action.
        if state.rng.next()%100>=max(15,min(90,70+(t-a))):
            b['log'].append(f'{self.person_name(state, target["id"])}拒绝单挑。')
            presentation.record(self,state,before,kind='duel_start',actor=actor['id'],target=target['id'],own=own,success=False)
            self._finish_action(state,actor,own,foe);return
        b['extended']['duel']={'actor':actor['id'],'target':target['id'],'round':1,'log':['双方接受单挑。']}
        b['log'].append(f'{self.person_name(state, actor["id"])}与{self.person_name(state, target["id"])}开始单挑。')
        presentation.record(self,state,before,kind='duel_start',actor=actor['id'],target=target['id'],own=own)

    def _duel_action(self,state,payload):
        b=state.battle
        if state.phase!='battle' or not b or payload.get('battle_id')!=b['id'] or not b['extended']['duel']:raise GameError('当前没有单挑。')
        move=payload.get('move')
        if move not in {'strike','guard','feint','withdraw','desperate'}:raise GameError('单挑动作无效。')
        x=b['extended'];d=x['duel'];own,foe=self._player_sides(state)
        actor=next(u for u in b[own] if u['id']==d['actor']);target=next(u for u in b[foe] if u['id']==d['target'])
        a=x['support'][str(actor['id'])];t=x['support'][str(target['id'])]
        before=presentation.snapshot(self,state);reply=None;success=True
        if move=='withdraw':result='退出单挑'
        else:
            # A wounded AI may replace its ordinary strike with the same risk
            # move. Reuse the existing choice draw: policy never samples RNG.
            reply=('strike','guard','feint')[state.rng.next()%3]
            if t['health']<=30 and reply=='strike':reply='desperate'
            def hit(first,second,attack,defense):
                # ROM bank23 category6: quality<30 doubles the strike; otherwise
                # the actor loses10..30 HP from low-five-bit rejection sampling.
                # The Web game keeps its established damage/equipment model and
                # health1=rout boundary rather than importing NES byte wrapping.
                quality=state.rng.next()%100 if attack=='desperate' else None
                martial=state.officers[first['id']].profile.martial_strength
                other=state.officers[second['id']].profile.martial_strength
                base=max(2,10+(martial-other)//6+state.rng.next()%7)
                from .facility_equipment import duel_adjustment
                equipped=state.officers[first['id']];protected=state.officers[second['id']]
                attack_bonus=duel_adjustment(equipped.weapon_id,equipped.armor_id,martial)['attack']
                defense_bonus=duel_adjustment(protected.weapon_id,protected.armor_id,other)['defense']
                base=max(2,base+attack_bonus-defense_bonus)
                if attack=='desperate':
                    if quality<30:base*=2
                    else:
                        while True:
                            loss=state.rng.next()&31
                            if loss<21:return 0,loss+10,False
                if attack=='guard':base=max(1,base//3)
                if defense=='guard':base=max(1,base//3) if attack!='feint' else base+4
                if attack=='feint' and defense=='strike':base=max(1,base//2)
                return base,0,True
            damage,self_loss,success=hit(actor,target,move,reply)
            received,enemy_self_loss,enemy_success=hit(target,actor,reply,move)
            t['health']=max(1,t['health']-damage-enemy_self_loss);a['health']=max(1,a['health']-received-self_loss)
            labels={'strike':'突击','guard':'防守','feint':'佯攻','desperate':'舍命一击'}
            if move=='desperate' and not success:d['log'].append(f'本方舍命一击失手，自损体力{self_loss}。')
            if reply=='desperate' and not enemy_success:d['log'].append(f'对方舍命一击失手，自损体力{enemy_self_loss}。')
            d['log'].append(f'本方{labels[move]}，对方{labels[reply]}；体力损伤{received+self_loss}/{damage+enemy_self_loss}。');d['log'][:]=d['log'][-10:]
            d['round']+=1
            if a['health']==1:actor['troops']=0
            if t['health']==1:target['troops']=0
            result='双方负伤退场' if a['health']==1 and t['health']==1 else '本方单挑胜出' if t['health']==1 else '本方负伤败退' if a['health']==1 else '二十合未分胜负' if d['round']>20 else None
        if result:
            x['duel_history'].append({'actor':actor['id'],'target':target['id'],'result':result});x['duel_history'][:]=x['duel_history'][-20:]
            b['log'].append(result);x['duel']=None
        presentation.record(self,state,before,kind='duel_action',actor=actor['id'],
            target=target['id'],own=own,move=move,reply=reply,success=success)
        if result:self._finish_action(state,actor,own,foe,respond=False)

    def _expanded_retreat(self,state,payload):
        b=state.battle
        if state.phase!='battle' or not b or payload.get('battle_id')!=b['id']:raise GameError('当前不能退却。')
        own,_=self._player_sides(state)
        before=presentation.snapshot(self,state)
        b['extended']['duel']=None;b['extended']['withdrawn']=own
        b['outcome']='retreat' if own=='attackers' else 'victory';state.phase='result'
        presentation.record(self,state,before,kind='retreat',own=own)

    def _expanded_settle(self,state,payload):
        b=state.battle
        if state.phase!='result' or not b or payload.get('battle_id')!=b['id']:raise GameError('没有待接收的战果。')
        source,target=state.cities[b['source']],state.cities[b['target']];x=b['extended']
        lost=sum(u['start']-u['troops'] for u in b['attackers']+b['defenders'])-sum(x['surrenders'].values())
        if lost<0:raise GameError('战果兵员账本异常。')
        for u in b['attackers']+b['defenders']:
            o=state.officers[u['id']];o.troops=u['troops'];o.health=x['support'][str(u['id'])]['health']
            o.experience=min(49999,o.experience+max(1,lost//max(1,len(b['attackers'])+len(b['defenders']))));o.tier=experience_tier(o.experience)
        state.soldiers['lost']+=lost
        for key,amount in x['surrenders'].items():
            ident=deserialize_officer_ref(key,self.catalog.rules);owner_city=target if ident in target.roster.officer_ids else source
            owner_city.reserves+=amount;owner_city.roster.officer_ids.remove(ident)
            o=state.officers[ident];o.faction_id=None;o.loyalty=0;o.troops=0
            state.extension['free_locations'][key]=owner_city.id
        if b['outcome']=='victory':
            selected=[u['id'] for u in b['attackers'] if str(u['id']) not in x['surrenders']]
            # Defenders escape to the nearest adjacent friendly city with room.
            for ident in list(target.roster.officer_ids):
                o=state.officers[ident]
                homes=[state.cities[k] for k in self._neighbors(target.id,state) if k in state.cities and k!=source.id and state.cities[k].owner==target.owner and self._city_occupancy(state,state.cities[k])<self.catalog.rules.city_officer_capacity]
                if homes:
                    home=homes[0];home.roster.officer_ids.append(ident)
                else:
                    target.reserves+=o.troops;o.troops=0;o.faction_id=None;o.loyalty=0
                    state.extension['free_locations'][str(ident)]=target.id
            target.roster.officer_ids[:]=selected
            source.roster.officer_ids[:]=[i for i in source.roster.officer_ids if i not in selected]
            target.owner=b['attacker'];target.action_used=True
            self._note(state,f'{self.catalog.factions[b["attacker"]]["name"]}攻占{self.catalog.map_cities[target.id]["name"]}。')
            self._emit_event(state,'city_captured',person_ids=[state.officers[i].person_id for i in selected[:1]],
                city_ids=[target.id],factions=[b['attacker'],b['defender']],
                details=dict(previous_owner=b['defender']),audience='world')
        state.settled_battles.append(b['id'])
        incoming=b['attacker']!=state.player
        self._note(state,f'战果已结算，合计损兵{lost}，劝降兵员{sum(x["surrenders"].values())}入城。')
        if state.player in (b['attacker'],b['defender']):
            self._emit_event(state,'battle_result',city_ids=[b['source'],b['target']],
                person_ids=[state.officers[u['id']].person_id for u in (b['attackers'][:1]+b['defenders'][:1])],
                factions=[b['attacker'],b['defender']],
                details=dict(battle_id=b['id'],outcome=b['outcome'],lost=lost,surrendered=sum(x['surrenders'].values())))
        state.battle=None;state.phase='ai' if incoming else 'city'
        travel=state.extension['travel']
        if travel['battle_arrival']:
            travel['battle_arrival']=False;state.phase='arrivals'
        self._prune_marches(state)
        self._reconcile_factions(state)

    def _reconcile_factions(self,state):
        x=state.extension
        for faction in sorted(self.catalog.factions):
            alive=[i for i,o in state.officers.items() if o.alive and o.faction_id==faction]
            cities=[c for c in state.cities.values() if c.owner==faction]
            if not alive or not cities:
                for c in cities:c.owner='neutral'
                x['leaders'][faction]=None
                x['pending_succession'].pop(faction,None)
                if faction not in x['ended_factions']:
                    x['ended_factions'].append(faction);self._note(state,f'{self.catalog.factions[faction]["name"]}退出战役。')
            elif x['leaders'].get(faction) not in alive:
                candidates=sorted(alive,key=lambda i:(-state.officers[i].profile.virtue,
                    -state.officers[i].profile.intellect,-state.officers[i].experience,ref_sort_key(i)))
                previous=x['leaders'].get(faction);leader=candidates[0];x['leaders'][faction]=leader
                old_loyalty=state.officers[leader].loyalty
                state.officers[leader].loyalty=100
                if faction==state.player:
                    x['pending_succession'][faction]=dict(previous=previous,candidates=candidates,
                        provisional=leader,previous_loyalty=old_loyalty)
                    self._note(state,'请为本方选择继承君主。')
                else:
                    self._note(state,f'{self.person_name(state, leader)}接任势力主将。')
        for faction,pending in list(x['pending_succession'].items()):
            pending['candidates']=[i for i in pending['candidates'] if i in state.officers and state.officers[i].alive and state.officers[i].faction_id==faction]
        if state.player in x['ended_factions']:
            state.phase='finished';x['outcome']='defeat'
        elif all(c.owner==state.player for c in state.cities.values()):
            state.phase='finished';x['outcome']='victory';self._note(state,f'{len(state.cities)}城归一，战役胜利。')
        if 'civil_staff' in x:
            from .civil_staff import synchronize
            synchronize(self, state, checks=False)
        if 'logistics' in x:
            from . import logistics,domestic
            logistics.synchronize(self,state)
            domestic.synchronize(self,state)
        if 'treasury' in x:
            from . import treasures
            treasures.synchronize(self,state)
        if 'facilities' in x:
            from . import facilities
            facilities.synchronize(self,state)

    def _choose_successor(self,state,payload):
        pending=state.extension['pending_succession'].get(state.player)
        if state.phase!='city' or not pending:
            raise GameError('当前没有待选择的继承君主。')
        ident=parse_officer_ref(payload.get('officer'),self.catalog.rules)
        if ident not in pending['candidates'] or not state.officers[ident].alive or state.officers[ident].faction_id!=state.player:
            raise GameError('请选择本方存活的继承人。')
        provisional=pending['provisional']
        if provisional!=ident and provisional in state.officers and state.officers[provisional].faction_id==state.player:
            state.officers[provisional].loyalty=min(99,pending['previous_loyalty'])
        state.extension['leaders'][state.player]=ident
        state.officers[ident].loyalty=100
        state.extension['pending_succession'].pop(state.player)
        previous=pending['previous']
        self._emit_event(state,'succession',person_ids=[state.officers[ident].person_id],factions=[state.player],
            details=dict(previous=state.officers[previous].person_id if previous in state.officers else None),audience='world')
        self._note(state,f'{self.person_name(state, ident)}接任势力主将。')

    def _report_ai(self,state,city,action,target=None):
        state.extension['ai_reports'].append({'turn':state.turn,'city':city.id,'faction':city.owner,'action':action,'target':target})
        state.extension['ai_reports'][:]=state.extension['ai_reports'][-200:]

    def _expanded_ai(self,state,payload):
        from .strategic_ai import run
        return run(self,state,payload)

    def _expanded_catalog_view(self,state):
        library=[]
        for ident,row in self.catalog.by_id.items():
            person=self.catalog.definitions[row['person_id']];profile=self.catalog.profiles[ident]
            officer=state.officers.get(ident) if state else None
            library.append({'id':ident,'person_id':person.person_id,'name':person.name,'birth':person.birth_year,
                            'service':person.service_year,'death':person.death_year,'missing':list(profile.missing),
                            'year_state':year_state(person,state.year if state else self.catalog.data['start_year']).value,
                            'faction':officer.faction_id if officer else None,'alive':officer.alive if officer else None,
                            'location':state.extension['free_locations'].get(str(ident)) if state else self.catalog.data['appearance_locations'].get(person.person_id),
                            'martial':profile.martial_strength,'intellect':officer.profile.intellect if officer else profile.intellect,'virtue':profile.virtue,
                            'base_intellect':profile.intellect,
                            'study_gain':officer.profile.intellect-profile.intellect if officer else 0,
                            'health_max':profile.health_max,'affinity':profile.terrain_affinity,
                            'aliases':sorted(set(row.get('aliases',[])+self.catalog.data.get(
                                'additional_person_aliases',{}).get(person.person_id,[]))),
                            'configuration':row.get('configuration',{}),
                            'ability_source':row.get('ability_source',{}),'chronology_basis':row.get('chronology_basis'),
                            'chronology_design':row.get('chronology_design'),
                            'virtue_design':row.get('virtue_design'), 'initialization':row.get('initialization'),
                            'era_assignment':self.catalog.data.get('era_assignments',{}).get(person.person_id)})
        return {'coverage':self.catalog.data['coverage'],'library':library,
                'tactics':[{'id':i,'name':t[0],'cost':t[1],'effect':t[2],'description':t[3]} for i,t in enumerate(TACTICS)],
                'persuadable':{c.id:self._persuadable(state,c) for c in state.cities.values() if c.owner==state.player} if state else {},
                'recruitable':{c.id:self._free_candidates(state,c) for c in state.cities.values() if c.owner==state.player} if state else {}}

    def _validate_expansion(self,state):
        x=state.extension
        fields={'free_locations','officer_actions','leaders','ended_factions','ai_queue','ai_cursor','ai_attacks','ai_reports','outcome','travel','difficulty','ai_strategy','events','civil_staff','pending_succession','domestic','logistics','treasury','facilities'}
        if not isinstance(x,dict) or set(x)!=fields:raise ValueError('expanded state fields')
        self._validate_travel(state)
        if not isinstance(x['free_locations'],dict) or not isinstance(x['officer_actions'],dict):raise ValueError('personnel state')
        for key,city in x['free_locations'].items():
            ident=deserialize_officer_ref(key,self.catalog.rules)
            if str(ident)!=key or ident not in state.officers or city not in state.cities or state.officers[ident].faction_id is not None:raise ValueError('free officer location')
        for ident,o in state.officers.items():
            if o.alive and o.faction_id is None and str(ident) not in x['free_locations']:raise ValueError('unlocated free officer')
            if o.alive and year_state(self.person_definition(state, ident),state.year) not in {YearState.AVAILABLE,YearState.DEATH_YEAR_REVIEW}:raise ValueError('unborn or retired free officer')
        for key,turn in x['officer_actions'].items():
            if deserialize_officer_ref(key,self.catalog.rules) not in state.officers:raise ValueError('officer action identity')
            integer(turn,1,state.turn,'officer action turn')
        if not isinstance(x['leaders'],dict) or set(x['leaders'])!=set(self.catalog.factions):raise ValueError('leader identities')
        if not isinstance(x['ended_factions'],list) or len(set(x['ended_factions']))!=len(x['ended_factions']) or not set(x['ended_factions'])<=set(self.catalog.factions):raise ValueError('ended factions')
        for faction,ident in x['leaders'].items():
            if faction in x['ended_factions']:
                if ident is not None or any(c.owner==faction for c in state.cities.values()):raise ValueError('ended faction retains holdings')
            else:
                self.catalog.rules.officer_id(ident)
                if ident not in state.officers or not state.officers[ident].alive or state.officers[ident].faction_id!=faction or state.officers[ident].loyalty!=100:raise ValueError('living leader required')
        if not isinstance(x['pending_succession'],dict) or not set(x['pending_succession'])<={state.player}:raise ValueError('pending succession faction')
        for faction,pending in x['pending_succession'].items():
            if (not isinstance(pending,dict) or set(pending)!={'previous','candidates','provisional','previous_loyalty'}
                    or not isinstance(pending['candidates'],list) or not pending['candidates']
                    or len(pending['candidates'])!=len(set(pending['candidates']))
                    or pending['provisional']!=x['leaders'][faction]
                    or any(i not in state.officers or not state.officers[i].alive or state.officers[i].faction_id!=faction for i in pending['candidates'])):raise ValueError('pending succession choices')
            integer(pending['previous_loyalty'],0,100,'provisional previous loyalty')
            if pending['previous'] is not None:
                parse_officer_ref(pending['previous'],self.catalog.rules)
                if pending['previous'] not in state.officers:raise ValueError('unknown previous ruler')
            for ident in pending['candidates']:
                parse_officer_ref(ident,self.catalog.rules)
        if x['outcome'] not in {None,'victory','defeat'} or (state.phase=='finished')!=(x['outcome'] is not None):raise ValueError('campaign ending')
        if x['outcome']=='victory' and not all(c.owner==state.player for c in state.cities.values()):raise ValueError('false mainland victory')
        if x['outcome']=='defeat' and state.player not in x['ended_factions']:raise ValueError('false mainland defeat')
        queue=x['ai_queue']
        if not isinstance(queue,list) or len(queue)!=len(set(queue)) or not set(queue)<=set(state.cities):raise ValueError('AI queue')
        from .difficulty import attack_budget
        from .strategic_ai import validate_strategies
        validate_strategies(self,state)
        integer(x['ai_cursor'],0,len(queue),'AI cursor');integer(x['ai_attacks'],0,attack_budget(self.catalog,state),'AI attacks')
        if queue and state.phase=='city':raise ValueError('AI continuation in city phase')
        if not isinstance(x['ai_reports'],list) or len(x['ai_reports'])>200:raise ValueError('AI report bounds')
        for r in x['ai_reports']:
            if set(r)!={'turn','city','faction','action','target'} or r['city'] not in state.cities or r['faction'] not in self.catalog.factions or r['action'] not in {'attack','recruit_officer','persuade_officer','recruit_soldiers','transfer','hire_staff','staff_recruit'}:raise ValueError('AI report fields')
            integer(r['turn'],1,state.turn,'AI report turn')
            if r['target'] is not None and not isinstance(r['target'],str):raise ValueError('AI report target')
        b=state.battle
        if not b:return
        e=b['extended']
        if set(e)!={'support','duel','duel_history','ambush','surrenders','withdrawn'}:raise ValueError('battle extended fields')
        units={u['id']:u for u in b['attackers']+b['defenders']}
        if set(e['support'])!={str(i) for i in units}:raise ValueError('battle support identities')
        for key,s in e['support'].items():
            if set(s)!={'health','energy','stunned','guard','morale'}:raise ValueError('battle support fields')
            integer(s['morale'],0,100,'battle morale')
            integer(s['health'],1,state.officers[deserialize_officer_ref(key,self.catalog.rules)].health,'battle HP')
            integer(s['energy'],0,18,'battle energy');integer(s['stunned'],0,1,'battle confusion');integer(s['guard'],0,2,'battle shield')
        if e['withdrawn'] not in {None,'attackers','defenders'}:raise ValueError('battle withdrawal')
        if e['withdrawn']=='defenders' and b['outcome']!='victory':raise ValueError('defender withdrawal outcome')
        if e['withdrawn']=='attackers' and b['outcome']!='retreat':raise ValueError('attacker withdrawal outcome')
        if e['ambush'] is not None:
            if set(e['ambush'])!={'actor'} or not (type(e['ambush']['actor']) is int or is_generated_ref(e['ambush']['actor'])) or e['ambush']['actor'] not in units:raise ValueError('ambush identity')
        if not isinstance(e['surrenders'],dict):raise ValueError('surrender records')
        for key,troops in e['surrenders'].items():
            if deserialize_officer_ref(key,self.catalog.rules) not in units or units[deserialize_officer_ref(key,self.catalog.rules)]['troops']!=0:raise ValueError('surrender identity')
            integer(troops,1,units[deserialize_officer_ref(key,self.catalog.rules)]['start'],'surrendered troops')
        if not isinstance(e['duel_history'],list) or len(e['duel_history'])>20:raise ValueError('duel history')
        for item in e['duel_history']:
            if set(item)!={'actor','target','result'} or item['actor'] not in units or item['target'] not in units or item['result'] not in {'退出单挑','本方单挑胜出','本方负伤败退','二十合未分胜负','双方负伤退场'}:raise ValueError('duel result')
        d=e['duel']
        if d is not None:
            own,foe=self._player_sides(state)
            if set(d)!={'actor','target','round','log'} or state.phase!='battle' or d['actor'] not in {u['id'] for u in b[own]} or d['target'] not in {u['id'] for u in b[foe]}:raise ValueError('duel participants')
            if units[d['actor']]['troops']<=0 or units[d['target']]['troops']<=0:raise ValueError('duel with routed participant')
            integer(d['round'],1,20,'duel round')
            if not isinstance(d['log'],list) or len(d['log'])>10 or any(not isinstance(v,str) or len(v)>500 for v in d['log']):raise ValueError('duel log')
