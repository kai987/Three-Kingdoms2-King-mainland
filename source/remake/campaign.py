"""Small independent campaign: typed state, transactions, battle and saved RNG.

Only the modern officer model and Python standard library are imported. All
rules newly designed for this playable slice are supplied in the demo catalog.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from threading import RLock

from .errors import GameError
from .campaign_expansion import ExpandedCampaign
from .travel import TravelCampaign
from .officers import (CityRoster, GameRules, OfficerProfile, PersonDefinition,
                       RuntimeOfficer, YearState, advance_year, experience_tier,
                       initialize_officer, integer, select_deployment, year_state)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@dataclass
class SeedRng:
    state: int
    draws: int = 0

    def next(self):
        x = self.state
        x ^= (x << 13) & 0xffffffff
        x ^= x >> 17
        x ^= (x << 5) & 0xffffffff
        self.state = x & 0xffffffff
        self.draws += 1
        return self.state


@dataclass
class City:
    id: str
    owner: str
    roster: CityRoster
    gold: int
    grain: int
    reserves: int
    action_used: bool = False


@dataclass
class CampaignState:
    player: str
    seed: int
    rng: SeedRng
    year: int
    month: int
    calendar_cursor: int
    turn: int = 1
    phase: str = 'city'
    cities: dict[str, City] = field(default_factory=dict)
    officers: dict[int, RuntimeOfficer] = field(default_factory=dict)
    battle: dict | None = None
    battle_counter: int = 0
    settled_battles: list[str] = field(default_factory=list)
    completed_ai_turns: list[int] = field(default_factory=list)
    year_events: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    extension: dict = field(default_factory=dict)
    soldiers: dict = field(default_factory=lambda: {'initial': 0, 'recruited': 0, 'lost': 0})


class Catalog:
    def __init__(self, path: Path):
        raw = Path(path).read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.data = json.loads(raw)
        assert self.data['schema'] in {'standalone-demo-data-v1', 'standalone-mainland-data-v1'}
        r = self.data['rules']
        self.rules = GameRules(r['city_officer_capacity'], r['battle_officers_per_side'], r['runtime_capacity'])
        self.by_id, self.definitions, self.profiles = {}, {}, {}
        for row in self.data['people']:
            ident = self.rules.officer_id(row['runtime_id'])
            person = PersonDefinition(row['person_id'], row['name'], row['birth_year'],
                                      row['service_year'], row['death_year'], row['chronology_basis'])
            assert ident not in self.by_id and person.person_id not in self.definitions
            self.by_id[ident] = row
            self.definitions[person.person_id] = person
            self.profiles[ident] = OfficerProfile(**row['profile'])
        self.ids = {row['person_id']: ident for ident, row in self.by_id.items()}
        self.factions = {f['id']: f for f in self.data['factions']}
        self.map_cities = {c['id']: c for c in self.data['cities']}
        self.links = {frozenset(e) for e in self.data['links']}
        expected = self.data.get('city_count', 100 if self.data.get('travel_rules') else 96)
        assert type(expected) is int and expected > 0
        expected_people = self.data.get('officer_count', 1000)
        integer(expected_people, 1, self.rules.runtime_capacity, 'catalog officer count')
        assert len(self.definitions) == expected_people and len(self.map_cities) == expected

    def active_city_ids(self, year, month=1):
        opened = set(self.data['active_cities'])
        for key, rule in self.data.get('city_foundings', {}).items():
            if (year,month) >= (rule['year'],rule.get('month',1)): opened.add(key)
            else: opened.discard(key)
        return [key for key in self.map_cities if key in opened]

    def name(self, ident):
        return self.by_id[ident]['name']


class Campaign(TravelCampaign, ExpandedCampaign):
    def __init__(self, catalog: Catalog):
        self.catalog = catalog
        self.state: CampaignState | None = None
        self.revision = 0
        self.lock = RLock()
        self.journal = []

    def _note(self, state, text):
        state.log.append(f'{state.year}年{state.month}月　{text}')
        state.log[:] = state.log[-200:]

    def _new(self, faction, seed):
        if faction not in self.catalog.factions:
            raise GameError('请选择一个势力。')
        integer(seed, 1, 0xffffffff, 'seed')
        d = self.catalog.data
        state = CampaignState(faction, seed, SeedRng(seed), d['start_year'], d['start_month'], d['start_year'])
        for key in d['active_cities']:
            resources = d.get('initial_city_resources',{}).get(key,d['initial_resources'])
            state.cities[key] = City(key, d['initial_owners'][key],
                                     CityRoster(key, rules=self.catalog.rules), **resources)
        for row in d['initial_officers']:
            ident = self.catalog.ids[row['person_id']]
            city = state.cities[row['city']]
            officer = initialize_officer(self.catalog.definitions[row['person_id']], ident,
                         self.catalog.profiles[ident], year=state.year, faction_id=city.owner,
                         is_ruler=row.get('ruler', False), loyalty=100 if row.get('ruler') else 80,
                         troops=row['troops'], rules=self.catalog.rules,
                         resolve_death_year=row.get('resolve_death_year', False))
            state.officers[ident] = officer
            city.roster.officer_ids.append(ident)
        state.soldiers['initial'] = sum(c.reserves for c in state.cities.values()) + sum(o.troops for o in state.officers.values())
        if self.expanded:
            self._initialize_expansion(state)
        if self.travelling:
            state.extension['travel'] = dict(counter=0, marches=[], battle_arrival=False)
            if self.catalog.data.get('travel_hazards'):
                state.extension['travel']['discovered'] = []
        self._note(state, f'开始{d["title"]}，选择{self.catalog.factions[faction]["name"]}。')
        return state

    def to_dict(self, state=None):
        state = state or self.state
        if state is None:
            return None
        value = asdict(state)
        value['officers'] = {str(k): v for k, v in value['officers'].items()}
        return value

    def view(self):
        with self.lock:
            state = self.state
            available = sum(year_state(p, state.year) == YearState.AVAILABLE for p in self.catalog.definitions.values()) if state else None
            return {'revision': self.revision, 'game': self.to_dict(),
                    'catalog': {'title': self.catalog.data['title'], 'factions': list(self.catalog.factions.values()),
                                'cities': list(self.catalog.map_cities.values()),
                                'active_cities': self.catalog.active_city_ids(
                                    state.year if state else self.catalog.data['start_year'],
                                    state.month if state else self.catalog.data['start_month']),
                                'links': self.catalog.data['links'], 'rules': self.catalog.data['rules'],
                                'notes': self.catalog.data['design_notes'], 'library_count': len(self.catalog.definitions),
                                'year_available': available,
                                **self._expanded_catalog_view(state), **self._travel_view(state),
                                'names': {str(i): self.catalog.name(i) for i in state.officers} if state else {}}}

    def command(self, kind, payload, revision):
        with self.lock:
            if not isinstance(payload, dict):
                raise GameError('操作参数无效。')
            # Domain idempotency survives saves and restores, even after the UI
            # has already advanced to another phase/revision.
            if self.state and kind == 'settle' and payload.get('battle_id') in self.state.settled_battles:
                return self.view()
            if self.state and kind == 'ai' and payload.get('turn') in self.state.completed_ai_turns:
                return self.view()
            if type(revision) is not int or revision != self.revision:
                raise GameError('进度已更新，请重新选择操作。', 409)
            before = self.to_dict()
            if kind == 'new':
                candidate = self._new(payload.get('faction'), payload.get('seed'))
            else:
                if self.state is None:
                    raise GameError('请先选择势力。')
                candidate = deepcopy(self.state)
                methods = {'persuade_officer': self._persuade_officer, 'recruit_officer': self._recruit_officer, 'transfer': self._transfer,
                           'tactic': self._tactic, 'duel_start': self._duel_start, 'duel_action': self._duel_action,
                           'allocate': self._allocate, 'recruit': self._recruit, 'depart': self._depart,
                           'attack': self._attack, 'retreat': self._retreat, 'settle': self._settle,
                           'end_turn': self._end_turn, 'ai': self._ai, 'arrivals': self._arrivals}
                if kind not in methods:
                    raise GameError('未提供这项操作。')
                methods[kind](candidate, payload)
            self.validate(candidate)
            self.state = candidate
            self.revision += 1
            self.journal.append({'kind': kind, 'revision': self.revision,
                                 'before_sha256': digest(before), 'after_sha256': digest(self.to_dict()),
                                 'rng_draws': candidate.rng.draws})
            return self.view()

    def _owned_city(self, state, key, *, action=False):
        if state.phase != 'city' or key not in state.cities:
            raise GameError('当前不能操作这座城。')
        city = state.cities[key]
        if city.owner != state.player:
            raise GameError('请选择本方城池。')
        if action and city.action_used:
            raise GameError('这座城本回合已行动。')
        return city

    def _allocate(self, state, payload):
        city = self._owned_city(state, payload.get('city'))
        ident = integer(payload.get('officer'), 0, self.catalog.rules.runtime_capacity - 1, 'officer')
        troops = integer(payload.get('troops'), 0, 999, 'troops')
        if ident not in city.roster.officer_ids:
            raise GameError('武将不在本城。')
        if ident in self._march_ids(state):
            raise GameError('武将正在行军，不能编兵。')
        officer = state.officers[ident]
        change = troops - officer.troops
        if change > city.reserves:
            raise GameError('本城预备兵不足。')
        officer.troops = troops
        city.reserves -= change
        self._note(state, f'{self.catalog.name(ident)}编兵为{troops}，本城预备兵{city.reserves}。')

    def _recruit(self, state, payload):
        city = self._owned_city(state, payload.get('city'), action=True)
        r = self.catalog.data['rules']
        if city.gold < r['recruit_gold_per_100'] or city.grain < r['recruit_grain_per_100']:
            raise GameError('金钱或粮食不足。')
        city.gold -= r['recruit_gold_per_100']
        city.grain -= r['recruit_grain_per_100']
        city.reserves += r['recruit_per_action']
        state.soldiers['recruited'] += r['recruit_per_action']
        city.action_used = True
        self._note(state, f'{self.catalog.map_cities[city.id]["name"]}征募{r["recruit_per_action"]}名预备兵。')

    def _depart(self, state, payload):
        source = self._owned_city(state, payload.get('source'), action=True)
        target_key = payload.get('target')
        hazard_rules = self.catalog.data.get('travel_hazards')
        if hazard_rules:
            adjacent = target_key in self._neighbors(source.id,state)
            exploring = (payload.get('route_mode') == 'explore' and
                         self._exploration_route(source.id,target_key) is not None)
        else:
            adjacent = frozenset((source.id,target_key)) in self.catalog.links
            exploring = False
        if target_key not in state.cities or not (adjacent or exploring):
            raise GameError('请选择相邻且已开放的城池。')
        target = state.cities[target_key]
        if target.owner == state.player:
            raise GameError('不能向本方城池出征。')
        ids = payload.get('officers')
        if not isinstance(ids, list) or any(type(i) is not int for i in ids):
            raise GameError('出征名单无效。')
        if self.expanded:
            for ident in ids: self._personnel_actor(state, source, ident)
            if self.travelling:
                self._queue_march(state, source, target, ids, 'attack', payload.get('route_mode','fastest'))
                return
            self._start_expanded_battle(state, source, target, ids)
            return
        selected = select_deployment(source.roster, ids, state.officers)
        cost = max(1, sum(state.officers[i].troops for i in selected) // 25)
        if source.grain < cost:
            raise GameError('出征粮食不足。')
        defenders = sorted(target.roster.officer_ids, key=lambda i: (-state.officers[i].troops, i))
        defenders = [i for i in defenders if state.officers[i].alive and state.officers[i].troops > 0][:self.catalog.rules.battle_officers_per_side]
        def units(group):
            return [{'id': i, 'troops': state.officers[i].troops, 'start': state.officers[i].troops,
                     'martial': state.officers[i].profile.martial_strength} for i in group]
        state.battle_counter += 1
        state.battle = {'id': f'battle-{state.battle_counter}', 'source': source.id, 'target': target.id,
                        'attacker': state.player, 'defender': target.owner, 'attackers': units(selected),
                        'defenders': units(defenders), 'used': [], 'round': 1, 'outcome': None,
                        'supply_cost': cost, 'log': ['出征已确认。选择本方部队和目标，再执行攻击。']}
        source.grain -= cost
        source.action_used = True
        state.phase = 'battle'
        self._note(state, f'向{self.catalog.map_cities[target.id]["name"]}出征，耗粮{cost}。')
        if not defenders:
            state.battle['outcome'] = 'victory'
            state.phase = 'result'

    def _damage(self, state, attacker, defender):
        spread = 90 + state.rng.next() % 21
        base = attacker['troops'] * (attacker['martial'] + 40) * self.catalog.data['rules']['battle_damage_percent'] * spread
        return min(defender['troops'], max(1, base // ((defender['martial'] + 80) * 10000)))

    def _attack(self, state, payload):
        if self.expanded:
            return self._expanded_attack(state, payload)
        battle = state.battle
        if state.phase != 'battle' or not battle or payload.get('battle_id') != battle['id']:
            raise GameError('当前没有可操作的战斗。')
        actor = next((u for u in battle['attackers'] if u['id'] == payload.get('actor')), None)
        target = next((u for u in battle['defenders'] if u['id'] == payload.get('target')), None)
        if not actor or not target or actor['troops'] <= 0 or target['troops'] <= 0 or actor['id'] in battle['used']:
            raise GameError('请选择尚未行动的部队和有效目标。')
        loss = self._damage(state, actor, target)
        target['troops'] -= loss
        battle['used'].append(actor['id'])
        battle['log'].append(f'{self.catalog.name(actor["id"])}攻击{self.catalog.name(target["id"])}，对方损兵{loss}。')
        enemies = [u for u in battle['defenders'] if u['troops'] > 0]
        if not enemies:
            battle['outcome'] = 'victory'
        else:
            enemy = max(enemies, key=lambda u: (u['troops'], -u['id']))
            loss = self._damage(state, enemy, actor)
            actor['troops'] -= loss
            battle['log'].append(f'{self.catalog.name(enemy["id"])}反击，本方损兵{loss}。')
            if not any(u['troops'] > 0 for u in battle['attackers']):
                battle['outcome'] = 'defeat'
        if battle['outcome']:
            state.phase = 'result'
        elif all(u['id'] in battle['used'] for u in battle['attackers'] if u['troops'] > 0):
            battle['used'] = []
            battle['round'] += 1
        battle['log'][:] = battle['log'][-80:]

    def _retreat(self, state, payload):
        if self.expanded:
            return self._expanded_retreat(state, payload)
        if state.phase != 'battle' or not state.battle or payload.get('battle_id') != state.battle['id']:
            raise GameError('当前不能退却。')
        state.battle['outcome'] = 'retreat'
        state.phase = 'result'

    def _settle(self, state, payload):
        if self.expanded:
            return self._expanded_settle(state, payload)
        battle = state.battle
        if state.phase != 'result' or not battle or payload.get('battle_id') != battle['id']:
            raise GameError('没有待接收的战果。')
        source, target = state.cities[battle['source']], state.cities[battle['target']]
        lost = 0
        for unit in battle['attackers'] + battle['defenders']:
            officer = state.officers[unit['id']]
            lost += unit['start'] - unit['troops']
            officer.troops = unit['troops']
            # Slice design: experience from actual enemy losses, not age.
            side = battle['defenders'] if unit in battle['attackers'] else battle['attackers']
            gain = sum(u['start'] - u['troops'] for u in side) // max(1, len(side) * 2)
            officer.experience = min(49999, officer.experience + gain)
            officer.tier = experience_tier(officer.experience)
        state.soldiers['lost'] += lost
        if battle['outcome'] == 'victory':
            selected = [u['id'] for u in battle['attackers']]
            if len(selected) > target.roster.rules.city_officer_capacity:
                raise GameError('目标城容量不足，战果未提交。')
            # Nondeployed garrison surrenders its remaining soldiers to the
            # city's reserve. Every removed troop has an explicit destination.
            for ident in target.roster.officer_ids:
                officer = state.officers[ident]
                target.reserves += officer.troops
                officer.troops = 0
                officer.faction_id = None
                officer.loyalty = 0
            target.roster.officer_ids[:] = selected
            source.roster.officer_ids[:] = [i for i in source.roster.officer_ids if i not in selected]
            target.owner = state.player
            target.action_used = True
            label = f'攻占{self.catalog.map_cities[target.id]["name"]}，出征武将移驻，城内资源随城接收。'
        else:
            label = '本方败退，武将返回原城。' if battle['outcome'] == 'defeat' else '本方退却，武将返回原城。'
        self._note(state, f'{label}本战合计损兵{lost}。')
        state.settled_battles.append(battle['id'])
        state.battle = None
        state.phase = 'city'

    def _end_turn(self, state, payload):
        if state.phase != 'city':
            raise GameError('请先完成当前操作或战果结算。')
        state.phase = 'ai'

    def _ai(self, state, payload):
        if self.expanded:
            return self._expanded_ai(state, payload)
        if state.phase != 'ai' or payload.get('turn') != state.turn:
            raise GameError('当前不是待处理的电脑回合。')
        r = self.catalog.data['rules']
        for city in state.cities.values():
            if city.owner in (state.player, 'neutral'):
                continue
            ids = [i for i in city.roster.officer_ids if state.officers[i].alive]
            if ids and city.reserves and city.gold >= 4 and city.grain >= 8:
                ident = ids[state.rng.next() % len(ids)]
                officer = state.officers[ident]
                amount = min(r['ai_reinforce_max'], city.reserves, 999 - officer.troops)
                officer.troops += amount
                city.reserves -= amount
                city.gold -= 4
                city.grain -= 8
                self._note(state, f'{self.catalog.factions[city.owner]["name"]}在{self.catalog.map_cities[city.id]["name"]}整备，{self.catalog.name(ident)}补兵{amount}。')
            else:
                self._note(state, f'{self.catalog.map_cities[city.id]["name"]}守军休整。')
        self._complete_month(state)

    def _open_dated_cities(self, state):
        """Split an existing actual territory; do not replay historical conquest."""
        for key, rule in self.catalog.data.get('city_foundings', {}).items():
            if (state.year,state.month) < (rule['year'],rule.get('month',1)) or key in state.cities: continue
            parent = state.cities[rule['parent']]
            resources = {}
            for field in ('gold','grain','reserves'):
                resources[field] = getattr(parent,field) // rule['resource_divisor']
                setattr(parent,field,getattr(parent,field)-resources[field])
            state.cities[key] = City(key,parent.owner,CityRoster(key,rules=self.catalog.rules),**resources)
            if key == 'xinxing' and 'month' not in rule:
                # Keep the released year-only event text and replay output.
                self._note(state,f'{self.catalog.map_cities[key]["name"]}建郡，承接晋阳当时归属与部分资源；未新增兵员或强制转属。')
            else:
                parent_name = self.catalog.map_cities[rule['parent']]['name']
                self._note(state,f'{self.catalog.map_cities[key]["name"]}建置，承接{parent_name}当时归属与部分资源；未新增兵员或强制转属。')

    def _complete_month(self, state):
        r = self.catalog.data['rules']
        state.completed_ai_turns.append(state.turn)
        state.month += 1
        if state.month == 13:
            state.month = 1
            state.year += 1
        self._open_dated_cities(state)
        if state.year > state.calendar_cursor:
            events = advance_year(self.catalog.definitions.values(), state.officers,
                                  [c.roster for c in state.cities.values()], state.calendar_cursor, state.year)
            count = 0
            for event in events:
                key = f'{event["event"]}:{event["person_id"]}:{event["year"]}'
                if key in state.year_events:
                    continue
                state.year_events.append(key)
                count += 1
                if event['event'] == 'remove_after_death_year':
                    released = event['released_troops']
                    if released:
                        if event['origin_city'] not in state.cities:
                            raise GameError('死亡兵员缺少接收城市，回合未提交。')
                        state.cities[event['origin_city']].reserves += released
                    name = self.catalog.definitions[event['person_id']].name
                    if event.get('already_dead'):
                        self._note(state, f'{name}此前已死亡，本年仅完成年代核对。')
                    else:
                        self._note(state, f'{name}到达寿命边界，释放兵员{released}归原城。')
            state.calendar_cursor = state.year
            self._note(state, f'新年更新人物库，记录{count}项年代事件；未自动招募或复活人物。')
        for city in state.cities.values():
            city.action_used = False
            if city.owner != 'neutral':
                income=self.catalog.data.get('city_income',{}).get(city.id,
                    {'gold':r['monthly_gold_income'],'grain':r['monthly_grain_income'],'reserves':0})
                city.gold += income['gold']
                city.grain += income['grain']
                city.reserves += income['reserves']
                state.soldiers['recruited'] += income['reserves']
        state.turn += 1
        state.phase = 'city'
        if self.travelling:
            self._prune_marches(state)
            if any(r['arrival_turn'] <= state.turn for r in state.extension['travel']['marches']):
                state.phase = 'arrivals'
        if not any(c.owner == state.player for c in state.cities.values()) or not any(o.alive and o.faction_id == state.player for o in state.officers.values()):
            state.phase = 'finished'
            self._note(state, '本方已无可用驻军，本次演练结束。')
        else:
            if self.catalog.data.get('city_income'):
                self._note(state,'电脑行动完成，轮到本方。各城按规模获得金钱、粮食与预备兵收入。')
            else:
                self._note(state, f'电脑行动完成，轮到本方。各城收获金钱{r["monthly_gold_income"]}、粮食{r["monthly_grain_income"]}。')

    def export_save(self):
        with self.lock:
            if self.state is None:
                raise GameError('请先开始演练。')
            value = {'format': 'three-kingdoms-remake-save', 'version': 1,
                     'catalog_sha256': self.catalog.sha256, 'scenario': self.catalog.data['id'],
                     'state': self.to_dict()}
            return {**value, 'checksum': digest(value)}

    def load_save(self, payload, revision):
        with self.lock:
            if type(revision) is not int or revision != self.revision:
                raise GameError('进度已更新，请重新读取。', 409)
            try:
                if not isinstance(payload, dict) or set(payload) != {'format', 'version', 'catalog_sha256', 'scenario', 'state', 'checksum'}:
                    raise ValueError('save envelope')
                content = {k: v for k, v in payload.items() if k != 'checksum'}
                if content['format'] != 'three-kingdoms-remake-save' or content['version'] != 1 or content['catalog_sha256'] != self.catalog.sha256 or content['scenario'] != self.catalog.data['id'] or digest(content) != payload['checksum']:
                    raise ValueError('save identity/checksum')
                raw = deepcopy(content['state'])
                raw['rng'] = SeedRng(**raw['rng'])
                officers = {}
                for key, row in raw['officers'].items():
                    ident = int(key)
                    if str(ident) != key or row['runtime_id'] != ident or row['person_id'] != self.catalog.by_id[ident]['person_id'] or row['profile'] != asdict(self.catalog.profiles[ident]):
                        raise ValueError('officer identity/profile')
                    row['profile'] = self.catalog.profiles[ident]
                    officers[ident] = RuntimeOfficer(**row)
                raw['officers'] = officers
                cities = {}
                for key, row in raw['cities'].items():
                    roster = row['roster']
                    if row['id'] != key or roster['city_id'] != key or roster['rules'] != asdict(self.catalog.rules):
                        raise ValueError('city identity/rules')
                    row['roster'] = CityRoster(key, roster['officer_ids'], self.catalog.rules)
                    cities[key] = City(**row)
                raw['cities'] = cities
                candidate = CampaignState(**raw)
                self.validate(candidate)
            except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
                raise GameError('存档无效，当前进度未改变。') from exc
            self.state = candidate
            self.revision += 1
            self.journal.append({'kind': 'load', 'revision': self.revision, 'after_sha256': digest(self.to_dict()), 'rng_draws': candidate.rng.draws})
            return self.view()

    def validate(self, state):
        self._validate_expansion(state)
        if state.player not in self.catalog.factions or state.phase not in ({'city', 'battle', 'result', 'ai', 'finished'} | ({'arrivals'} if self.travelling else set())):
            raise ValueError('campaign phase/player')
        integer(state.year, 1, 400, 'year')
        integer(state.month, 1, 12, 'month')
        integer(state.turn, 1, 1000000, 'turn')
        integer(state.seed, 1, 0xffffffff, 'seed')
        integer(state.rng.state, 1, 0xffffffff, 'rng state')
        integer(state.rng.draws, 0, 100000000, 'rng draws')
        elapsed = (state.year - self.catalog.data['start_year']) * 12 + state.month - self.catalog.data['start_month']
        if state.calendar_cursor != state.year or elapsed != state.turn - 1 or set(state.cities) != set(self.catalog.active_city_ids(state.year,state.month)):
            raise ValueError('calendar/city domain')
        if any(type(v) is not int or not 0 <= v <= 100000000 for v in state.soldiers.values()) or set(state.soldiers) != {'initial', 'recruited', 'lost'}:
            raise ValueError('soldier ledger')
        seen = set()
        for key, city in state.cities.items():
            city.roster.validate()
            if city.id != key or city.roster.city_id != key or city.roster.rules != self.catalog.rules or city.owner not in {*self.catalog.factions, 'neutral'} or type(city.action_used) is not bool:
                raise ValueError('city ownership/configuration')
            for value in (city.gold, city.grain, city.reserves):
                integer(value, 0, 100000000, 'city resource')
            if seen.intersection(city.roster.officer_ids):
                raise ValueError('duplicate global roster ownership')
            for ident in city.roster.officer_ids:
                officer = state.officers[ident]
                if not officer.alive or officer.faction_id != city.owner:
                    raise ValueError('city/officer faction mismatch')
            seen.update(city.roster.officer_ids)
        people = set()
        for ident, officer in state.officers.items():
            self.catalog.rules.officer_id(ident)
            if ident != officer.runtime_id or officer.person_id != self.catalog.by_id[ident]['person_id'] or officer.person_id in people or officer.profile != self.catalog.profiles[ident] or officer.profile.missing:
                raise ValueError('officer identity/profile')
            people.add(officer.person_id)
            for value, low, high in ((officer.health, 0, officer.profile.health_max), (officer.loyalty, 0, 100),
                                     (officer.troops, 0, 999), (officer.weapon_id, 0, 23), (officer.armor_id, 0, 7),
                                     (officer.experience, 0, 49999), (officer.tier, 0, 7)):
                integer(value, low, high, 'officer state')
            if officer.tier != experience_tier(officer.experience) or type(officer.alive) is not bool:
                raise ValueError('experience/alive')
            if officer.faction_id is not None and officer.faction_id not in {*self.catalog.factions, 'neutral'}:
                raise ValueError('unknown faction')
            if officer.faction_id is not None and year_state(self.catalog.definitions[officer.person_id], state.year) not in {YearState.AVAILABLE, YearState.DEATH_YEAR_REVIEW}:
                raise ValueError('officer annual membership')
            if ident not in seen and (officer.faction_id is not None or officer.troops != 0):
                raise ValueError('unassigned officer ownership/troops')
        current_soldiers = sum(c.reserves for c in state.cities.values()) + sum(o.troops for o in state.officers.values())
        if current_soldiers + state.soldiers['lost'] != state.soldiers['initial'] + state.soldiers['recruited']:
            raise ValueError('soldier conservation')
        for values in (state.settled_battles, state.completed_ai_turns, state.year_events):
            if not isinstance(values, list) or len(values) != len(set(values)) or len(values) > 10000:
                raise ValueError('duplicate event/settlement cursor')
        integer(state.battle_counter, 0, 1000000, 'battle counter')
        if state.completed_ai_turns != list(range(1, state.turn)):
            raise ValueError('AI committed turn cursor')
        expected_events = set()
        for p in self.catalog.definitions.values():
            for kind, year in (('birth', p.birth_year), ('service_eligible', p.service_year)):
                if year is not None and self.catalog.data['start_year'] < year <= state.calendar_cursor:
                    expected_events.add(f'{kind}:{p.person_id}:{year}')
        for officer in state.officers.values():
            p = self.catalog.definitions[officer.person_id]
            if p.death_year is not None and self.catalog.data['start_year'] < p.death_year + 1 <= state.calendar_cursor:
                expected_events.add(f'remove_after_death_year:{p.person_id}:{p.death_year + 1}')
                if officer.alive:
                    raise ValueError('historically retired officer revived')
        if set(state.year_events) != expected_events:
            raise ValueError('committed annual event cursor')
        if not isinstance(state.log, list) or len(state.log) > 200 or any(not isinstance(t, str) or len(t) > 500 for t in state.log):
            raise ValueError('log bounds')
        battle = state.battle
        if (state.phase in {'battle', 'result'}) != (battle is not None):
            raise ValueError('battle phase/occupancy')
        receipt_count = state.battle_counter - (1 if battle is not None else 0)
        if state.settled_battles != [f'battle-{i}' for i in range(1, receipt_count + 1)]:
            raise ValueError('settlement receipt sequence')
        if battle:
            base_fields = {'id', 'source', 'target', 'attacker', 'defender', 'attackers', 'defenders', 'used', 'round', 'outcome', 'supply_cost', 'log'}
            if set(battle) != base_fields | ({'extended'} if self.expanded else set()):
                raise ValueError('battle fields')
            if battle['id'] != f'battle-{state.battle_counter}' or battle['outcome'] not in {None, 'victory', 'defeat', 'retreat'}:
                raise ValueError('battle identity/outcome')
            integer(battle['round'], 1, 100000, 'battle round')
            integer(battle['supply_cost'], 1, 10000, 'supply cost')
            if not isinstance(battle['log'], list) or len(battle['log']) > 80 or any(not isinstance(t, str) or len(t) > 500 for t in battle['log']):
                raise ValueError('battle log')
            connected = (battle['target'] in self._neighbors(battle['source'], state)
                         if self.hazardous_travel else
                         frozenset((battle['source'], battle['target'])) in self.catalog.links)
            if battle['source'] == battle['target'] or not connected or battle['id'] in state.settled_battles:
                raise ValueError('battle location/receipt')
            if (not self.expanded and battle['attacker'] != state.player) or battle['attacker'] not in self.catalog.factions or state.cities[battle['source']].owner != battle['attacker'] or state.cities[battle['target']].owner != battle['defender']:
                raise ValueError('battle faction')
            if (state.phase == 'result') != (battle['outcome'] in {'victory', 'defeat', 'retreat'}):
                raise ValueError('battle outcome')
            all_ids = []
            for key, city_key in (('attackers', 'source'), ('defenders', 'target')):
                units = battle[key]
                if len(units) > self.catalog.rules.battle_officers_per_side or (key == 'attackers' and not units):
                    raise ValueError('battle side capacity')
                for unit in units:
                    if set(unit) != {'id', 'troops', 'start', 'martial'}:
                        raise ValueError('battle unit fields')
                    self.catalog.rules.officer_id(unit['id'])
                    integer(unit['start'], 1, 999, 'starting battle troops')
                    officer = state.officers[unit['id']]
                    if unit['id'] not in state.cities[battle[city_key]].roster.officer_ids or unit['start'] != officer.troops or unit['martial'] != officer.profile.martial_strength:
                        raise ValueError('deployed/reserved membership')
                    integer(unit['troops'], 0, unit['start'], 'battle troops')
                    all_ids.append(unit['id'])
            if len(all_ids) != len(set(all_ids)) or len(battle['used']) != len(set(battle['used'])) or not set(battle['used']) <= {u['id'] for u in battle[self._player_sides(state)[0] if self.expanded else 'attackers']}:
                raise ValueError('battle duplicate/turn ownership')
            attacking = any(u['troops'] > 0 for u in battle['attackers'])
            defending = any(u['troops'] > 0 for u in battle['defenders'])
            if state.phase == 'battle' and not (attacking and defending):
                raise ValueError('battle without active sides')
            withdrew = self.expanded and battle['extended']['withdrawn'] == 'defenders'
            if battle['outcome'] == 'victory' and ((defending and not withdrew) or not attacking):
                raise ValueError('victory before defenders rout')
            if battle['outcome'] == 'defeat' and (attacking or not defending):
                raise ValueError('defeat before attackers rout')
