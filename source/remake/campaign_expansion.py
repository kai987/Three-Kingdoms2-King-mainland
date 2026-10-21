"""Independent mainland mechanics: personnel,16 tactics, duels and campaign AI.

Names/capacities reference the research; effects and balance below are explicit
remake designs. No original engine, ROM tables or control IR are loaded.
"""
from collections import deque
from .errors import GameError
from .officers import (YearState, experience_tier, initialize_officer, integer,
                       recruitment_loyalty, select_deployment, transfer_officers, year_state)

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
    @property
    def expanded(self):
        return bool(self.catalog.data['rules'].get('expanded_campaign'))

    def _require_expanded(self):
        if not self.expanded:
            raise GameError('请在九十六城扩展战役中使用这项操作。')

    def _initialize_expansion(self, state):
        state.extension = {'free_locations': {}, 'officer_actions': {},
                           'leaders': dict(self.catalog.data['faction_rulers']),
                           'ended_factions': [], 'ai_queue': [], 'ai_cursor': 0,
                           'ai_attacks': 0, 'ai_reports': [], 'outcome': None}
        self._spawn_eligible(state)

    def _spawn_eligible(self, state):
        """Annual eligibility never fills missing stats or revives existing IDs."""
        for ident, row in self.catalog.by_id.items():
            if ident in state.officers or self.catalog.profiles[ident].missing:
                continue
            person = self.catalog.definitions[row['person_id']]
            city = self.catalog.data['appearance_locations'].get(person.person_id)
            if year_state(person, state.year) != YearState.AVAILABLE or city not in state.cities:
                continue
            state.officers[ident] = initialize_officer(person, ident, self.catalog.profiles[ident], year=state.year, rules=self.catalog.rules)
            state.extension['free_locations'][str(ident)] = city
            self._note(state, f'{person.name}已到登场年代，在{self.catalog.map_cities[city]["name"]}待访。')

    def _neighbors(self, city):
        return sorted(next(iter(edge - {city})) for edge in self.catalog.links if city in edge)

    def _friendly_path(self, state, source, target, owner):
        queue = deque([[source]]); seen = {source}
        while queue:
            path = queue.popleft()
            if path[-1] == target: return path
            for nxt in self._neighbors(path[-1]):
                if nxt not in seen and nxt in state.cities and state.cities[nxt].owner == owner:
                    seen.add(nxt); queue.append(path + [nxt])
        return None

    def _personnel_actor(self, state, city, ident):
        integer(ident, 0, self.catalog.rules.runtime_capacity - 1, 'officer')
        if ident not in city.roster.officer_ids or not state.officers[ident].alive or state.officers[ident].health < 1:
            raise GameError('请选择本城健康的武将。')
        if state.extension['officer_actions'].get(str(ident)) == state.turn:
            raise GameError('这名武将本回合已处理人事或调动。')
        return state.officers[ident]

    def _free_candidates(self, state, city):
        near = {city.id} | {k for k in self._neighbors(city.id) if state.cities[k].owner in {city.owner, 'neutral'}}
        return [i for i, o in state.officers.items() if o.alive and o.faction_id is None
                and year_state(self.catalog.definitions[o.person_id],state.year) in {YearState.AVAILABLE, YearState.DEATH_YEAR_REVIEW}
                and state.extension['free_locations'].get(str(i)) in near]

    def _recruit_officer(self, state, payload):
        self._require_expanded()
        city = self._owned_city(state, payload.get('city'), action=True)
        actor = self._personnel_actor(state, city, payload.get('actor'))
        ident = integer(payload.get('officer'),0,self.catalog.rules.runtime_capacity-1,'target officer')
        if ident not in self._free_candidates(state, city):
            raise GameError('目标尚未登场、已仕官，或不在本城及可访问的邻城。')
        if len(city.roster.officer_ids) >= self.catalog.rules.city_officer_capacity:
            raise GameError('本城已满20人，招募未执行。')
        fee = self.catalog.data['rules']['recruit_officer_gold']
        if city.gold < fee: raise GameError('招募金钱不足。')
        candidate = state.officers[ident]
        chance = max(15,min(95,35 + actor.profile.virtue//2 + actor.profile.intellect//5 - candidate.profile.virtue//5))
        success = state.rng.next()%100 < chance
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
        self._note(state,f'{self.catalog.name(actor.runtime_id)}寻访{self.catalog.name(ident)}，招募{"成功" if success else "未获应允"}，花费{fee}金。')

    def _persuadable(self,state,city):
        neighbors=set(self._neighbors(city.id))
        return [ident for key in sorted(neighbors) for ident in state.cities[key].roster.officer_ids
                if state.cities[key].owner not in {city.owner,'neutral'}
                and state.officers[ident].alive and state.officers[ident].loyalty<100
                and ident not in state.extension['leaders'].values()]

    def _persuade_officer(self,state,payload):
        self._require_expanded()
        city=self._owned_city(state,payload.get('city'),action=True)
        actor=self._personnel_actor(state,city,payload.get('actor'))
        ident=integer(payload.get('officer'),0,self.catalog.rules.runtime_capacity-1,'target officer')
        if ident not in self._persuadable(state,city):raise GameError('只能劝降邻城的非君主敌将。')
        if len(city.roster.officer_ids)>=20:raise GameError('本城已满20人，劝降未执行。')
        fee=self.catalog.data['rules']['persuade_officer_gold']
        if city.gold<fee:raise GameError('劝降金钱不足。')
        self._attempt_defection(state,city,actor,ident)
        self._reconcile_factions(state)

    def _attempt_defection(self,state,city,actor,ident):
        fee=self.catalog.data['rules']['persuade_officer_gold']
        target=state.officers[ident]
        chance=max(5,min(75,50+(actor.profile.virtue-target.loyalty)//2+(actor.profile.intellect-target.profile.intellect)//4))
        success=state.rng.next()%100<chance
        city.gold-=fee;city.action_used=True
        state.extension['officer_actions'][str(actor.runtime_id)]=state.turn
        if success:
            origin=next(c for c in state.cities.values() if ident in c.roster.officer_ids)
            origin.roster.officer_ids.remove(ident);city.roster.officer_ids.append(ident)
            target.faction_id=city.owner
            leader=state.extension['leaders'][city.owner]
            target.loyalty=recruitment_loyalty(state.officers[leader].profile.virtue,target.loyalty)
            state.extension['officer_actions'][str(ident)]=state.turn
        self._note(state,f'{self.catalog.name(actor.runtime_id)}劝说{self.catalog.name(ident)}，{"转属成功" if success else "遭到拒绝"}，花费{fee}金。')

    def _transfer(self,state,payload):
        self._require_expanded()
        source=self._owned_city(state,payload.get('source'),action=True)
        destination=self._owned_city(state,payload.get('target'))
        ids=payload.get('officers')
        if source.id==destination.id or not isinstance(ids,list) or not ids or len(ids)!=len(set(ids)):
            raise GameError('请选择不同的目的城和不重复的调动名单。')
        for ident in ids: self._personnel_actor(state,source,ident)
        path=self._friendly_path(state,source.id,destination.id,state.player)
        if not path: raise GameError('两城之间没有连续的本方道路。')
        fee=(len(path)-1)*len(ids)*5
        if source.grain < fee: raise GameError('调动粮食不足。')
        transfer_officers(source.roster,destination.roster,ids)
        source.grain-=fee;source.action_used=True
        state.extension['officer_actions'].update({str(i):state.turn for i in ids})
        self._note(state,f'{len(ids)}名武将调往{self.catalog.map_cities[destination.id]["name"]}，经{len(path)-1}段道路，耗粮{fee}。')

    def _start_expanded_battle(self,state,source,target,ids):
        selected=select_deployment(source.roster,ids,state.officers)
        cost=max(1,sum(state.officers[i].troops for i in selected)//25)
        if source.grain<cost: raise GameError('出征粮食不足。')
        defenders=sorted((i for i in target.roster.officer_ids if state.officers[i].troops>0 and state.officers[i].health>0),key=lambda i:(-state.officers[i].troops,i))[:10]
        def units(ids): return [{'id':i,'troops':state.officers[i].troops,'start':state.officers[i].troops,'martial':state.officers[i].profile.martial_strength} for i in ids]
        support={str(i):{'health':state.officers[i].health,'energy':18,'stunned':0,'guard':0} for i in [*selected,*defenders]}
        state.battle_counter+=1
        state.battle={'id':f'battle-{state.battle_counter}','source':source.id,'target':target.id,'attacker':source.owner,'defender':target.owner,
                      'attackers':units(selected),'defenders':units(defenders),'used':[],'round':1,'outcome':None,'supply_cost':cost,
                      'log':[f'{self.catalog.map_cities[source.id]["name"]}向{self.catalog.map_cities[target.id]["name"]}出征。'],
                      'extended':{'support':support,'duel':None,'duel_history':[],'ambush':None,'surrenders':{},'withdrawn':None}}
        source.grain-=cost;source.action_used=True;state.phase='battle'
        state.extension['officer_actions'].update({str(i):state.turn for i in selected})
        self._note(state,state.battle['log'][0])
        if not defenders: state.battle['outcome']='victory';state.phase='result'

    def _player_sides(self,state):
        return ('attackers','defenders') if state.battle['attacker']==state.player else ('defenders','attackers')

    def _battle_selection(self,state,payload,*,allow_duel=False):
        self._require_expanded();b=state.battle
        if state.phase!='battle' or not b or payload.get('battle_id')!=b['id']:
            raise GameError('当前没有待操作的战斗。')
        if b['extended']['duel'] and not allow_duel: raise GameError('请先完成或退出当前单挑。')
        own,foe=self._player_sides(state)
        a_id=integer(payload.get('actor'),0,self.catalog.rules.runtime_capacity-1,'actor')
        t_id=integer(payload.get('target'),0,self.catalog.rules.runtime_capacity-1,'target')
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
        b=state.battle;x=b['extended'];support=x['support']
        enemies=[u for u in b[foe] if u['troops']>0]
        if not enemies or actor['troops']<=0:return
        enemy=max(enemies,key=lambda u:(u['troops'],-u['id']))
        if x['ambush']:
            trap=x['ambush'];ambusher=next(u for u in b['attackers']+b['defenders'] if u['id']==trap['actor'])
            if ambusher['troops']>0:
                loss=min(enemy['troops'],max(1,state.officers[trap['actor']].profile.intellect*2))
                enemy['troops']-=loss;b['log'].append(f'十面埋伏触发，{self.catalog.name(enemy["id"])}损兵{loss}。')
            x['ambush']=None
            if enemy['troops']<=0:return
        es=support[str(enemy['id'])];a=support[str(actor['id'])]
        if es['stunned']:
            es['stunned']-=1;b['log'].append(f'{self.catalog.name(enemy["id"])}受扰乱，本次不能反击。');return
        # Both sides use the same damage and resource rules. Defensive AI may
        # spend its saved energy to confuse or burn instead of normal retaliation.
        iq=state.officers[enemy['id']].profile.intellect
        if iq>=80 and es['energy']>=6 and state.rng.next()%4==0:
            es['energy']-=6
            loss=min(actor['troops'],max(1,iq*2));b['log'].append(f'{self.catalog.name(enemy["id"])}以要撃反制。')
        else: loss=self._damage(state,enemy,actor)
        if a['guard']:
            loss=max(1,loss//2);a['guard']-=1
        actor['troops']-=loss;b['log'].append(f'{self.catalog.name(enemy["id"])}反击，{self.catalog.name(actor["id"])}损兵{loss}。')

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
        s=b['extended']['support'][str(actor['id'])]
        if s['stunned']:
            s['stunned']-=1;b['log'].append(f'{self.catalog.name(actor["id"])}受扰乱，行动跳过。')
        else:
            loss=self._damage(state,actor,target)
            defense=b['extended']['support'][str(target['id'])]
            if defense['guard']:loss=max(1,loss//2);defense['guard']-=1
            target['troops']-=loss;b['log'].append(f'{self.catalog.name(actor["id"])}攻击{self.catalog.name(target["id"])}，损兵{loss}。')
        self._finish_action(state,actor,own,foe)

    def _tactic(self,state,payload):
        b,actor,target,own,foe=self._battle_selection(state,payload)
        tid=integer(payload.get('tactic'),0,15,'tactic')
        title,cost,effect,_=TACTICS[tid];x=b['extended'];support=x['support'];a=support[str(actor['id'])]
        terrain=self.catalog.map_cities[b['target']]['terrain']
        if a['stunned']:raise GameError('该部队受扰乱，不能施计；可执行普通行动恢复。')
        if a['energy']<cost:raise GameError('计略气力不足。')
        if effect in {'water','chain','flood'} and terrain!='water':raise GameError('此计略需要水地形。')
        if effect=='rock' and terrain!='mountain':raise GameError('落石需要山地形。')
        if effect in {'fire','inferno','trap'} and terrain=='water':raise GameError('该地形不能使用此计略。')
        if effect=='ambush' and (actor['troops']<100 or x['ambush']):raise GameError('设伏需要至少100兵，且当前没有伏兵。')
        enemies=[u for u in b[foe] if u['troops']>0];p=state.officers[actor['id']].profile;t=state.officers[target['id']]
        a['energy']-=cost
        chance=max(10,min(95,60+(p.intellect-t.profile.intellect)//2))
        if effect=='surrender':chance=max(5,min(80,40+(p.virtue-t.loyalty)//2))
        success=effect in {'ambush','guard'} or state.rng.next()%100<chance
        if not success:b['log'].append(f'{self.catalog.name(actor["id"])}施放{title}，未能奏效。')
        elif effect=='ambush':x['ambush']={'actor':actor['id']};b['log'].append('十面埋伏已设置，等待下一次敌方反击。')
        elif effect=='guard':a['guard']=2;b['log'].append(f'{title}使本队获得两次减伤。')
        elif effect in {'confuse','chain'}:
            victims=[target] if effect=='confuse' else [target]+[u for u in enemies if u is not target][:2]
            for u in victims:support[str(u['id'])]['stunned']=1
            b['log'].append(f'{title}扰乱{len(victims)}队，下次反击失效。')
        elif effect=='surrender':
            x['surrenders'][str(target['id'])]=target['troops'];target['troops']=0
            b['log'].append(f'{self.catalog.name(target["id"])}接受劝降；战后转在野，兵员入城。')
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
                b['log'].append(f'{title}命中{self.catalog.name(u["id"])}，损兵{loss}。')
        self._finish_action(state,actor,own,foe,respond=effect!='ambush')

    def _duel_start(self,state,payload):
        b,actor,target,own,foe=self._battle_selection(state,payload)
        a=state.officers[actor['id']].profile.martial_strength;t=state.officers[target['id']].profile.martial_strength
        if b['extended']['support'][str(actor['id'])]['stunned']:raise GameError('受扰乱部队不能挑战单挑。')
        # An opponent is free to refuse; refusal consumes the challenger's action.
        if state.rng.next()%100>=max(15,min(90,70+(t-a))):
            b['log'].append(f'{self.catalog.name(target["id"])}拒绝单挑。');self._finish_action(state,actor,own,foe);return
        b['extended']['duel']={'actor':actor['id'],'target':target['id'],'round':1,'log':['双方接受单挑。']}
        b['log'].append(f'{self.catalog.name(actor["id"])}与{self.catalog.name(target["id"])}开始单挑。')

    def _duel_action(self,state,payload):
        self._require_expanded();b=state.battle
        if state.phase!='battle' or not b or payload.get('battle_id')!=b['id'] or not b['extended']['duel']:raise GameError('当前没有单挑。')
        move=payload.get('move')
        if move not in {'strike','guard','feint','withdraw'}:raise GameError('单挑动作无效。')
        x=b['extended'];d=x['duel'];own,foe=self._player_sides(state)
        actor=next(u for u in b[own] if u['id']==d['actor']);target=next(u for u in b[foe] if u['id']==d['target'])
        a=x['support'][str(actor['id'])];t=x['support'][str(target['id'])]
        if move=='withdraw':result='退出单挑'
        else:
            reply=('strike','guard','feint')[state.rng.next()%3]
            def hit(first,second,attack,defense):
                martial=state.officers[first['id']].profile.martial_strength
                other=state.officers[second['id']].profile.martial_strength
                base=max(2,10+(martial-other)//6+state.rng.next()%7)
                if attack=='guard':base=max(1,base//3)
                if defense=='guard':base=max(1,base//3) if attack!='feint' else base+4
                if attack=='feint' and defense=='strike':base=max(1,base//2)
                return base
            damage=hit(actor,target,move,reply);received=hit(target,actor,reply,move)
            t['health']=max(1,t['health']-damage);a['health']=max(1,a['health']-received)
            labels={'strike':'突击','guard':'防守','feint':'佯攻'}
            d['log'].append(f'本方{labels[move]}，对方{labels[reply]}；体力损伤{received}/{damage}。');d['log'][:]=d['log'][-10:]
            d['round']+=1
            if a['health']==1:actor['troops']=0
            if t['health']==1:target['troops']=0
            result='双方负伤退场' if a['health']==1 and t['health']==1 else '本方单挑胜出' if t['health']==1 else '本方负伤败退' if a['health']==1 else '二十合未分胜负' if d['round']>20 else None
        if result:
            x['duel_history'].append({'actor':actor['id'],'target':target['id'],'result':result});x['duel_history'][:]=x['duel_history'][-20:]
            b['log'].append(result);x['duel']=None;self._finish_action(state,actor,own,foe,respond=False)

    def _expanded_retreat(self,state,payload):
        b=state.battle
        if state.phase!='battle' or not b or payload.get('battle_id')!=b['id']:raise GameError('当前不能退却。')
        own,_=self._player_sides(state)
        b['extended']['duel']=None;b['extended']['withdrawn']=own
        b['outcome']='retreat' if own=='attackers' else 'victory';state.phase='result'

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
            ident=int(key);owner_city=target if ident in target.roster.officer_ids else source
            owner_city.reserves+=amount;owner_city.roster.officer_ids.remove(ident)
            o=state.officers[ident];o.faction_id=None;o.loyalty=0;o.troops=0
            state.extension['free_locations'][key]=owner_city.id
        if b['outcome']=='victory':
            selected=[u['id'] for u in b['attackers'] if u['id'] not in map(int,x['surrenders'])]
            # Defenders escape to the nearest adjacent friendly city with room.
            for ident in list(target.roster.officer_ids):
                o=state.officers[ident]
                homes=[state.cities[k] for k in self._neighbors(target.id) if k!=source.id and state.cities[k].owner==target.owner and len(state.cities[k].roster.officer_ids)<20]
                if homes:
                    home=homes[0];home.roster.officer_ids.append(ident)
                else:
                    target.reserves+=o.troops;o.troops=0;o.faction_id=None;o.loyalty=0
                    state.extension['free_locations'][str(ident)]=target.id
            target.roster.officer_ids[:]=selected
            source.roster.officer_ids[:]=[i for i in source.roster.officer_ids if i not in selected]
            target.owner=b['attacker'];target.action_used=True
            self._note(state,f'{self.catalog.factions[b["attacker"]]["name"]}攻占{self.catalog.map_cities[target.id]["name"]}。')
        state.settled_battles.append(b['id'])
        incoming=b['attacker']!=state.player
        self._note(state,f'战果已结算，合计损兵{lost}，劝降兵员{sum(x["surrenders"].values())}入城。')
        state.battle=None;state.phase='ai' if incoming else 'city'
        self._reconcile_factions(state)

    def _reconcile_factions(self,state):
        x=state.extension
        for faction in sorted(self.catalog.factions):
            alive=[i for i,o in state.officers.items() if o.alive and o.faction_id==faction]
            cities=[c for c in state.cities.values() if c.owner==faction]
            if not alive or not cities:
                for c in cities:c.owner='neutral'
                x['leaders'][faction]=None
                if faction not in x['ended_factions']:
                    x['ended_factions'].append(faction);self._note(state,f'{self.catalog.factions[faction]["name"]}退出战役。')
            elif x['leaders'].get(faction) not in alive:
                leader=max(alive,key=lambda i:(state.officers[i].profile.virtue,-i));x['leaders'][faction]=leader
                state.officers[leader].loyalty=100;self._note(state,f'{self.catalog.name(leader)}接任势力主将。')
        if state.player in x['ended_factions']:
            state.phase='finished';x['outcome']='defeat'
        elif all(c.owner==state.player for c in state.cities.values()):
            state.phase='finished';x['outcome']='victory';self._note(state,'九十六城归一，战役胜利。')

    def _report_ai(self,state,city,action,target=None):
        state.extension['ai_reports'].append({'turn':state.turn,'city':city.id,'faction':city.owner,'action':action,'target':target})
        state.extension['ai_reports'][:]=state.extension['ai_reports'][-200:]

    def _expanded_ai(self,state,payload):
        if state.phase!='ai' or payload.get('turn')!=state.turn:raise GameError('当前不是待处理的电脑回合。')
        x=state.extension;r=self.catalog.data['rules']
        if not x['ai_queue']:
            x['ai_queue']=sorted(c.id for c in state.cities.values() if c.owner not in {state.player,'neutral'})
            x['ai_cursor']=0;x['ai_attacks']=0
        while x['ai_cursor']<len(x['ai_queue']):
            key=x['ai_queue'][x['ai_cursor']];x['ai_cursor']+=1;city=state.cities[key]
            if city.owner in {state.player,'neutral'} or city.action_used:continue
            ids=city.roster.officer_ids
            free=self._free_candidates(state,city)
            if ids and free and len(ids)<20 and city.gold>=r['recruit_officer_gold']:
                # Same success formula/loyalty as the player; failure costs gold.
                recruiter=max(ids,key=lambda i:state.officers[i].profile.virtue);actor=state.officers[recruiter];ident=free[0];o=state.officers[ident]
                chance=max(15,min(95,35+actor.profile.virtue//2+actor.profile.intellect//5-o.profile.virtue//5))
                city.gold-=r['recruit_officer_gold']
                if state.rng.next()%100<chance:
                    o.faction_id=city.owner;o.loyalty=recruitment_loyalty(actor.profile.virtue,o.loyalty);ids.append(ident);x['free_locations'].pop(str(ident),None)
                x['officer_actions'][str(recruiter)]=state.turn
                x['officer_actions'][str(ident)]=state.turn
                self._report_ai(state,city,'recruit_officer',str(ident));city.action_used=True;continue
            if ids and city.reserves<200 and city.gold>=20 and city.grain>=30:
                city.reserves+=100;state.soldiers['recruited']+=100;city.gold-=20;city.grain-=30
                self._report_ai(state,city,'recruit_soldiers')
            for ident in sorted(ids,key=lambda i:(state.officers[i].troops,i)):
                o=state.officers[ident];amount=min(80,city.reserves,600-o.troops)
                if amount>0 and city.gold>=4 and city.grain>=8:
                    o.troops+=amount;city.reserves-=amount;city.gold-=4;city.grain-=8
            army=sorted((i for i in ids if state.officers[i].troops>0 and state.officers[i].health>0 and x['officer_actions'].get(str(i))!=state.turn),key=lambda i:(-state.officers[i].troops,i))[:10]
            targets=[state.cities[k] for k in self._neighbors(key) if state.cities[k].owner!=city.owner]
            targets.sort(key=lambda c:(sum(state.officers[i].troops for i in c.roster.officer_ids),c.id))
            strength=sum(state.officers[i].troops for i in army)
            target=next((c for c in targets if strength>=max(150,sum(state.officers[i].troops for i in c.roster.officer_ids)*13//10)),None)
            if army and target and x['ai_attacks']<r['ai_max_attacks_per_turn'] and city.grain>=max(1,strength//25):
                x['ai_attacks']+=1;self._report_ai(state,city,'attack',target.id)
                self._start_expanded_battle(state,city,target,army)
                if target.owner==state.player:return  # Player controls the defending side.
                # AI-v-AI / empty-city combat uses the same troop formula and
                # settlement ledger, bounded to200 exchanges then an attacker retreat.
                b=state.battle
                for _ in range(200):
                    if state.phase=='result':break
                    a=max((u for u in b['attackers'] if u['troops']>0),key=lambda u:u['troops'])
                    t=max((u for u in b['defenders'] if u['troops']>0),key=lambda u:u['troops'])
                    t['troops']-=self._damage(state,a,t)
                    if t['troops']>0:a['troops']-=self._damage(state,t,a)
                    self._battle_result(state)
                if state.phase=='battle':b['outcome']='retreat';state.phase='result'
                self._expanded_settle(state,{'battle_id':b['id']})
                if state.phase=='finished':return
                state.phase='ai'
            elif any(x['officer_actions'].get(str(i))!=state.turn for i in ids) and len(ids)<20 and city.gold>=r['persuade_officer_gold'] and self._persuadable(state,city) and not any(report['turn']==state.turn and report['action']=='persuade_officer' for report in x['ai_reports']):
                actor=max((state.officers[i] for i in ids if x['officer_actions'].get(str(i))!=state.turn),key=lambda o:o.profile.virtue)
                target=min(self._persuadable(state,city),key=lambda i:state.officers[i].loyalty)
                self._attempt_defection(state,city,actor,target)
                self._report_ai(state,city,'persuade_officer',str(target))
                self._reconcile_factions(state)
                if state.phase=='finished':return
            elif len([i for i in ids if x['officer_actions'].get(str(i))!=state.turn])>1:
                friends=[state.cities[k] for k in self._neighbors(key) if state.cities[k].owner==city.owner and len(state.cities[k].roster.officer_ids)<20]
                friends.sort(key=lambda c:(len(c.roster.officer_ids),c.id))
                if friends and len(friends[0].roster.officer_ids)<len(ids)-1 and city.grain>=5:
                    ident=min((i for i in ids if x['officer_actions'].get(str(i))!=state.turn),key=lambda i:state.officers[i].troops);transfer_officers(city.roster,friends[0].roster,[ident]);city.grain-=5
                    x['officer_actions'][str(ident)]=state.turn
                    self._report_ai(state,city,'transfer',friends[0].id)
            city.action_used=True
        x['ai_queue']=[];x['ai_cursor']=0;x['ai_attacks']=0
        self._complete_month(state)
        self._spawn_eligible(state)
        for o in state.officers.values():
            if o.alive:o.health=min(o.profile.health_max,o.health+r['monthly_heal'])
        self._reconcile_factions(state)

    def _expanded_catalog_view(self,state):
        if not self.expanded:return {}
        library=[]
        for ident,row in self.catalog.by_id.items():
            person=self.catalog.definitions[row['person_id']];profile=self.catalog.profiles[ident]
            officer=state.officers.get(ident) if state else None
            library.append({'id':ident,'person_id':person.person_id,'name':person.name,'birth':person.birth_year,
                            'service':person.service_year,'death':person.death_year,'missing':list(profile.missing),
                            'year_state':year_state(person,state.year if state else self.catalog.data['start_year']).value,
                            'faction':officer.faction_id if officer else None,'alive':officer.alive if officer else None,
                            'location':state.extension['free_locations'].get(str(ident)) if state else self.catalog.data['appearance_locations'].get(person.person_id),
                            'martial':profile.martial_strength,'intellect':profile.intellect,'virtue':profile.virtue})
        return {'coverage':self.catalog.data['coverage'],'library':library,
                'tactics':[{'id':i,'name':t[0],'cost':t[1],'description':t[3]} for i,t in enumerate(TACTICS)],
                'persuadable':{c.id:self._persuadable(state,c) for c in state.cities.values() if c.owner==state.player} if state else {},
                'recruitable':{c.id:self._free_candidates(state,c) for c in state.cities.values() if c.owner==state.player} if state else {}}

    def _validate_expansion(self,state):
        x=state.extension
        if not self.expanded:
            if x!={}:raise ValueError('unexpected expanded data in legacy slice')
            return
        fields={'free_locations','officer_actions','leaders','ended_factions','ai_queue','ai_cursor','ai_attacks','ai_reports','outcome'}
        if not isinstance(x,dict) or set(x)!=fields:raise ValueError('expanded state fields')
        if not isinstance(x['free_locations'],dict) or not isinstance(x['officer_actions'],dict):raise ValueError('personnel state')
        for key,city in x['free_locations'].items():
            ident=int(key)
            if str(ident)!=key or ident not in state.officers or city not in state.cities or state.officers[ident].faction_id is not None:raise ValueError('free officer location')
        for ident,o in state.officers.items():
            if o.alive and o.faction_id is None and str(ident) not in x['free_locations']:raise ValueError('unlocated free officer')
            if o.alive and year_state(self.catalog.definitions[o.person_id],state.year) not in {YearState.AVAILABLE,YearState.DEATH_YEAR_REVIEW}:raise ValueError('unborn or retired free officer')
        for key,turn in x['officer_actions'].items():
            if str(int(key))!=key or int(key) not in state.officers:raise ValueError('officer action identity')
            integer(turn,1,state.turn,'officer action turn')
        if not isinstance(x['leaders'],dict) or set(x['leaders'])!=set(self.catalog.factions):raise ValueError('leader identities')
        if not isinstance(x['ended_factions'],list) or len(set(x['ended_factions']))!=len(x['ended_factions']) or not set(x['ended_factions'])<=set(self.catalog.factions):raise ValueError('ended factions')
        for faction,ident in x['leaders'].items():
            if faction in x['ended_factions']:
                if ident is not None or any(c.owner==faction for c in state.cities.values()):raise ValueError('ended faction retains holdings')
            else:
                self.catalog.rules.officer_id(ident)
                if ident not in state.officers or not state.officers[ident].alive or state.officers[ident].faction_id!=faction or state.officers[ident].loyalty!=100:raise ValueError('living leader required')
        if x['outcome'] not in {None,'victory','defeat'} or (state.phase=='finished')!=(x['outcome'] is not None):raise ValueError('campaign ending')
        if x['outcome']=='victory' and not all(c.owner==state.player for c in state.cities.values()):raise ValueError('false mainland victory')
        if x['outcome']=='defeat' and state.player not in x['ended_factions']:raise ValueError('false mainland defeat')
        queue=x['ai_queue']
        if not isinstance(queue,list) or len(queue)!=len(set(queue)) or not set(queue)<=set(state.cities):raise ValueError('AI queue')
        integer(x['ai_cursor'],0,len(queue),'AI cursor');integer(x['ai_attacks'],0,self.catalog.data['rules']['ai_max_attacks_per_turn'],'AI attacks')
        if queue and state.phase=='city':raise ValueError('AI continuation in city phase')
        if not isinstance(x['ai_reports'],list) or len(x['ai_reports'])>200:raise ValueError('AI report bounds')
        for r in x['ai_reports']:
            if set(r)!={'turn','city','faction','action','target'} or r['city'] not in state.cities or r['faction'] not in self.catalog.factions or r['action'] not in {'attack','recruit_officer','persuade_officer','recruit_soldiers','transfer'}:raise ValueError('AI report fields')
            integer(r['turn'],1,state.turn,'AI report turn')
            if r['target'] is not None and not isinstance(r['target'],str):raise ValueError('AI report target')
        b=state.battle
        if not b:return
        e=b['extended']
        if set(e)!={'support','duel','duel_history','ambush','surrenders','withdrawn'}:raise ValueError('battle extended fields')
        units={u['id']:u for u in b['attackers']+b['defenders']}
        if set(e['support'])!={str(i) for i in units}:raise ValueError('battle support identities')
        for key,s in e['support'].items():
            if set(s)!={'health','energy','stunned','guard'}:raise ValueError('battle support fields')
            integer(s['health'],1,state.officers[int(key)].health,'battle HP')
            integer(s['energy'],0,18,'battle energy');integer(s['stunned'],0,1,'battle confusion');integer(s['guard'],0,2,'battle shield')
        if e['withdrawn'] not in {None,'attackers','defenders'}:raise ValueError('battle withdrawal')
        if e['withdrawn']=='defenders' and b['outcome']!='victory':raise ValueError('defender withdrawal outcome')
        if e['withdrawn']=='attackers' and b['outcome']!='retreat':raise ValueError('attacker withdrawal outcome')
        if e['ambush'] is not None:
            if set(e['ambush'])!={'actor'} or type(e['ambush']['actor']) is not int or e['ambush']['actor'] not in units:raise ValueError('ambush identity')
        if not isinstance(e['surrenders'],dict):raise ValueError('surrender records')
        for key,troops in e['surrenders'].items():
            if str(int(key))!=key or int(key) not in units or units[int(key)]['troops']!=0:raise ValueError('surrender identity')
            integer(troops,1,units[int(key)]['start'],'surrendered troops')
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
