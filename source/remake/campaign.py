"""Current campaign: typed state, atomic transactions, battles and saved RNG.

Only current campaign catalogs are accepted; gameplay parameters remain data-driven.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from threading import RLock
from types import SimpleNamespace

from .errors import GameError
from . import civil_staff, domestic, logistics, presentation, treasures, facilities, equipment, command_books, battle_grid
from .campaign_expansion import ExpandedCampaign
from .travel import TravelCampaign
from .city_economy import income_at
from .difficulty import DIFFICULTIES, catalog_choices, get_settings
from .events import empty as empty_events, emit as emit_event, transition as record_events, validate as validate_events
from .officers import (CityRoster, GameRules, OfficerProfile, PersonDefinition,
                       RuntimeOfficer, YearState, advance_year, experience_tier,
                       initialize_officer, integer, year_state, is_generated_ref,
                       parse_officer_ref, deserialize_officer_ref, ref_sort_key, appearance_values)


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
    day: int = 1
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
        if self.data.get('schema') != 'tk2-campaign-v1':
            raise ValueError('Unsupported campaign catalog schema')
        if not self.data.get('travel_rules') or not self.data.get('travel_hazards'):
            raise ValueError('Current geographic and hazard travel rules are required')
        if self.data.get('calendar_rules') != {'turn_days': 10, 'month_days': 30, 'turn_start_days': [1, 11, 21], 'monthly_settlement': 'month_rollover'}:
            raise ValueError('Current campaigns require fixed ten-day turns')
        r = self.data['rules']
        self.rules = GameRules(r['city_officer_capacity'], r['battle_officers_per_side'], r['runtime_capacity'])
        self.by_id, self.definitions, self.profiles = {}, {}, {}
        for row in self.data['people']:
            ident = integer(row['runtime_id'], 0, self.rules.runtime_capacity-1, 'historical officer ID')
            person = PersonDefinition(row['person_id'], row['name'], row['birth_year'],
                                      row['service_year'], row['death_year'], row['chronology_basis'])
            assert ident not in self.by_id and person.person_id not in self.definitions
            self.by_id[ident] = row
            self.definitions[person.person_id] = person
            self.profiles[ident] = OfficerProfile(**row['profile'])
            appearance_values(self.profiles[ident], row.get('initialization'))
        self.ids = {row['person_id']: ident for ident, row in self.by_id.items()}
        self.factions = {f['id']: f for f in self.data['factions']}
        self.map_cities = {c['id']: c for c in self.data['cities']}
        self.links = {frozenset(e) for e in self.data['links']}
        from . import dated_events
        dated_events.validate_source(self)
        expected = self.data['city_count']
        assert type(expected) is int and expected > 0
        expected_people = self.data['officer_count']
        integer(expected_people, 1, self.rules.runtime_capacity, 'catalog officer count')
        assert len(self.definitions) == expected_people and len(self.map_cities) == expected

    def active_city_ids(self, year, month=1):
        opened = set(self.data['active_cities'])
        for key, rule in self.data.get('city_foundings', {}).items():
            if (year,month) >= (rule['year'],rule.get('month',1)): opened.add(key)
            else: opened.discard(key)
        # Administrative abolition affects later scenario openings. An older
        # campaign keeps its existing node, troops and actual ownership.
        opening=(self.data['start_year'],self.data['start_month'])
        for key,rule in self.data.get('city_retirements',{}).items():
            if opening>=(rule['year'],rule.get('month',1)):opened.discard(key)
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
        period = {1: '上旬', 11: '中旬', 21: '下旬'}[state.day]
        state.log.append(f'{state.year}年{state.month}月{period}　{text}')
        state.log[:] = state.log[-200:]

    def _emit_event(self, state, kind, **values):
        return emit_event(self, state, kind, **values)

    def person_name(self, state, ident):
        return state.extension['civil_staff']['people'][ident]['name'] if is_generated_ref(ident) else self.catalog.name(ident)

    def faction_name(self, state, owner):
        from .dated_events import visible_factions
        return next((row['name'] for row in visible_factions(self.catalog,state) if row['id']==owner),
                    self.catalog.factions.get(owner,{}).get('name',owner))

    def person_definition(self, state, ident):
        return civil_staff.definition(state.extension['civil_staff']['people'][ident]) if is_generated_ref(ident) else self.catalog.definitions[self.catalog.by_id[ident]['person_id']]

    def person_profile(self, state, ident):
        base = civil_staff.officer_profile(state.extension['civil_staff']['people'][ident]) if is_generated_ref(ident) else self.catalog.profiles[ident]
        return facilities.learned_profile(state,ident,base)

    def all_person_definitions(self, state):
        return [*self.catalog.definitions.values(), *(civil_staff.definition(p) for p in state.extension.get('civil_staff', {}).get('people', {}).values())]

    def _city_occupancy(self, state, city):
        return len(city.roster.officer_ids)

    def _hire_staff(self, state, payload):
        city = self._owned_city(state, payload.get('city'), action=True)
        civil_staff.hire(self, state, city.id, payload.get('candidate'), state.player)

    def _reject_staff(self, state, payload):
        city = self._owned_city(state, payload.get('city'))
        civil_staff.reject(self, state, city.id, payload.get('candidate'), state.player)

    def _set_domestic(self, state, payload):
        from .domestic import set_policy
        set_policy(self,state,payload,state.player)

    def _set_logistics(self, state, payload):
        from .logistics import set_policy
        self._owned_city(state,payload.get('city'))
        set_policy(self,state,payload,state.player)

    def _dispatch_transport(self, state, payload):
        from .logistics import dispatch
        self._owned_city(state,payload.get('source'),action=True)
        dispatch(self,state,payload,state.player)

    def _supply_event(self,state,kind,*,unit_kind,unit_id,city,owner,grain=0,lost=0,
                      shortage_days=0,reason='city'):
        """Player-facing receipts for changes already made by the common service."""
        if owner != state.player or city not in state.cities:
            return
        details=dict(unit_kind=unit_kind,unit_id=unit_id,grain=grain,lost=lost,
                     shortage_days=shortage_days,reason=reason)
        items=state.extension.get('events',{}).get('items',[])
        previous=next((r for r in reversed(items) if r['turn']==state.turn
            and r['id']>=getattr(self,'_supply_event_floor',state.extension['events']['next_id'])
            and r['kind']==kind and r.get('details',{}).get('unit_kind')==unit_kind
            and r.get('details',{}).get('unit_id')==unit_id and r['city_ids']==[city]
            and r['details'].get('reason')==reason),None)
        if previous is not None:
            previous['details']['grain']+=grain
            previous['details']['lost']+=lost
            previous['details']['shortage_days']=shortage_days
            return
        self._emit_event(state,kind,city_ids=[city],factions=[owner],details=details)

    def _civil_staff_view(self, state):
        result = civil_staff.view(self, state)
        if state is None:
            return result
        for key, row in result['cities'].items():
            city = state.cities[key]
            available = [person for person in row['employees'] if person['working'] and person['health'] > 0]
            candidates = self._free_candidates(state, city) if city.owner == state.player else []
            row['searchable_staff'] = available
            row['search_targets'] = [dict(id=i, name=self.person_name(state, i),
                martial_strength=state.officers[i].profile.martial_strength,
                intellect=state.officers[i].profile.intellect,
                virtue=state.officers[i].profile.virtue,
                experience=state.officers[i].experience, troops=state.officers[i].troops)
                for i in candidates]
            reason = ('not_owned' if city.owner != state.player else
                      'wrong_phase' if state.phase != 'city' else
                      'command_books' if not command_books.can_spend(state, city.owner, 'staff_recruit') else
                      'no_available_staff' if not available else
                      'no_historical_candidate' if not candidates else
                      'city_full' if self._city_occupancy(state, city) >= self.catalog.rules.city_officer_capacity else
                      'insufficient_gold' if city.gold < self.catalog.data['rules']['recruit_officer_gold'] else None)
            row['can_search'] = reason is None
            row['search_blocked_reason'] = reason
        return result

    def _new(self, faction, seed, difficulty='normal'):
        from . import dated_events
        if faction not in {f['id'] for f in dated_events.visible_factions(self.catalog)}:
            raise GameError('请选择一个势力。')
        integer(seed, 1, 0xffffffff, 'seed')
        if not isinstance(difficulty, str) or difficulty not in DIFFICULTIES:
            raise GameError('请选择简单、普通或困难难度。')
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
                         is_ruler=row.get('ruler', False),
                         **appearance_values(self.catalog.profiles[ident], self.catalog.by_id[ident].get('initialization'),
                                             faction_id=city.owner, is_ruler=row.get('ruler', False)),
                         troops=row['troops'], rules=self.catalog.rules,
                         resolve_death_year=row.get('resolve_death_year', False))
            state.officers[ident] = officer
            city.roster.officer_ids.append(ident)
        state.soldiers['initial'] = sum(c.reserves for c in state.cities.values()) + sum(o.troops for o in state.officers.values())
        self._initialize_expansion(state)
        state.extension.update(difficulty=difficulty, ai_strategy={}, events=empty_events())
        state.extension['travel'] = dict(counter=0, marches=[], battle_arrival=False, discovered=[])
        state.extension['civil_staff'] = civil_staff.empty(self, state)
        state.extension['domestic'] = domestic.empty(self,state)
        state.extension['logistics'] = logistics.empty(self,state)
        state.extension['treasury'] = treasures.empty(self,state)
        # These are AI choices, not cheaper or stronger reward rules.
        for owner, policy in state.extension['treasury']['factions'].items():
            policy['enabled'] = owner != faction
        state.extension['facilities'] = facilities.empty(self,state)
        state.extension['equipment'] = equipment.empty(self,state)
        command_books.initialize(self, state)
        equipment.synchronize(self,state)
        for owner, policy in state.extension['facilities']['factions'].items():
            if owner != faction and d.get('facility_ai_default',True):
                policy.update(enabled=True,auto_develop=True,auto_study=True,auto_trade=True,auto_equip=True)
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
            from . import dated_events
            state = self.state
            available = sum(year_state(p, state.year) == YearState.AVAILABLE for p in self.catalog.definitions.values()) if state else None
            travel = self._travel_view(state)
            return {'revision': self.revision, 'game': self.to_dict(),
                    'catalog': {'title': self.catalog.data['title'], 'factions': dated_events.visible_factions(self.catalog,state),
                                'scheduled_factions':[self.catalog.factions[r['faction']] for r in dated_events.foundings(self.catalog)],
                                'cities': list(self.catalog.map_cities.values()),
                                'active_cities': self.catalog.active_city_ids(
                                    state.year if state else self.catalog.data['start_year'],
                                    state.month if state else self.catalog.data['start_month']),
                                'links': self.catalog.data['links'], 'rules': self.catalog.data['rules'],
                                'calendar_rules': self.catalog.data['calendar_rules'],
                                'difficulties': catalog_choices(),
                                'notes': self.catalog.data['design_notes'], 'library_count': len(self.catalog.definitions),
                                'year_available': available,
                                **self._expanded_catalog_view(state), **travel,
                                'civil_staff': self._civil_staff_view(state),
                                'domestic':domestic.view(self,state),
                                'logistics':logistics.view(self,state,travel_quotes=travel.get('travel_quotes',{})),
                                'treasury':treasures.view(self,state),
                                'facilities':facilities.view(self,state),
                                'equipment':equipment.view(self,state),
                                'command_books':command_books.view(self,state),
                                'battle_tactical':battle_grid.view(self,state,state.battle) if state else None,
                                'names': {str(i): self.person_name(state, i) for i in state.officers} if state else {}}}

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
            with presentation.capture(self) as scenes:
                before = self.to_dict()
                if kind == 'new':
                    candidate = self._new(payload.get('faction'), payload.get('seed'), payload.get('difficulty', 'normal'))
                else:
                    if self.state is None:
                        raise GameError('请先选择势力。')
                    candidate = deepcopy(self.state)
                    self._supply_event_floor=candidate.extension['events']['next_id']
                    methods = {'persuade_officer': self._persuade_officer, 'recruit_officer': self._recruit_officer, 'transfer': self._transfer,
                               'tactic': self._tactic, 'duel_start': self._duel_start, 'duel_action': self._duel_action,
                               'allocate': self._allocate, 'allocation_close':self._allocation_close,
                               'recruit': self._recruit, 'depart': self._depart,
                               'attack': self._attack, 'retreat': self._retreat, 'settle': self._settle,
                               'battle_move':self._battle_move, 'battle_wait':self._battle_wait,
                               **{action:self._siege_command(action) for action in
                                  ('siege_form','siege_orders','siege_step','siege_withdraw')},
                               'end_turn': self._end_turn, 'ai': self._ai, 'arrivals': self._arrivals,
                               'hire_staff': self._hire_staff, 'reject_staff': self._reject_staff,
                               'staff_recruit': self._staff_recruit, 'choose_successor': self._choose_successor,
                               'set_domestic':self._set_domestic,'set_logistics':self._set_logistics,
                               'dispatch_transport':self._dispatch_transport,
                               **{action: self._treasury_command(action) for action in
                                  ('search_treasure','reward_officer','sell_treasure','set_governor','set_treasury_policy')},
                               **{action:self._facility_command(action) for action in
                                  ('develop_town','treat_officer','study_officer','trade_grain',
                                   'buy_equipment','improve_prevention','set_facility_policy')},
                               'equip_owned':lambda state,payload:equipment.equip_owned(self,state,payload,state.player)}
                    if kind not in methods:
                        raise GameError('未提供这项操作。')
                    if kind not in ('allocate', 'allocation_close'):
                        command_books.close_allocation(candidate, candidate.player)
                    methods[kind](candidate, payload)
                    self._synchronize_siege(candidate)
                record_events(self, self.state, candidate, kind, payload)
                civil_staff.synchronize(self, candidate, opening=kind == 'new', monthly=candidate.day == 1)
                logistics.synchronize(self,candidate)
                domestic.synchronize(self,candidate)
                treasures.synchronize(self,candidate)
                facilities.synchronize(self,candidate)
                equipment.synchronize(self,candidate)
                self.validate(candidate)
                self.state = candidate
                self.revision += 1
                self.journal.append({'kind': kind, 'revision': self.revision,
                                     'before_sha256': digest(before), 'after_sha256': digest(self.to_dict()),
                                     'rng_draws': candidate.rng.draws})
                return presentation.response(self.view(), self.revision, scenes)

    def _owned_city(self, state, key, *, action=False):
        if state.extension.get('pending_succession', {}).get(state.player):
            raise GameError('请先选择继承君主。')
        if state.phase != 'city' or not isinstance(key,str) or key not in state.cities:
            raise GameError('当前不能操作这座城。')
        city = state.cities[key]
        if city.owner != state.player:
            raise GameError('请选择本方城池。')
        if action:
            command_books.require(state, city.owner)
        return city

    def _treasury_command(self, kind):
        service = {'search_treasure':treasures.search, 'reward_officer':treasures.reward,
                   'sell_treasure':treasures.sell, 'set_governor':treasures.set_governor,
                   'set_treasury_policy':treasures.set_policy}[kind]
        return lambda state, payload: service(self,state,payload,state.player)

    def _facility_command(self, kind):
        service = {'develop_town':facilities.develop, 'treat_officer':facilities.treat,
                   'study_officer':facilities.study, 'trade_grain':facilities.trade,
                   'buy_equipment':facilities.buy, 'improve_prevention':facilities.prevent,
                   'set_facility_policy':facilities.set_policy}[kind]
        return lambda state,payload: service(self,state,payload,state.player)

    def _allocate(self, state, payload):
        city = self._owned_city(state, payload.get('city'))
        batch = 'flow' in payload
        identity = payload.get('flow')
        if batch and identity is not None:
            command_books.require_allocation(state, city, identity)
        ident = parse_officer_ref(payload.get('officer'), self.catalog.rules)
        troops = integer(payload.get('troops'), 0, 999, 'troops')
        if ident not in city.roster.officer_ids:
            raise GameError('武将不在本城。')
        if ident in self._march_ids(state):
            raise GameError('武将正在行军，不能编兵。')
        officer = state.officers[ident]
        change = troops - officer.troops
        if change > city.reserves:
            raise GameError('本城预备兵不足。')
        if not change:
            return
        if not batch or identity is None:
            command_books.spend(state, city, 'allocate')
            if batch:
                command_books.open_allocation(state, city)
        officer.troops = troops
        city.reserves -= change
        self._note(state, f'{self.person_name(state, ident)}编兵为{troops}，本城预备兵{city.reserves}。')

    def _allocation_close(self, state, payload):
        if not isinstance(payload.get('city'), str) or not isinstance(payload.get('flow'), str):
            raise GameError('配兵流程已結束，請重新開啟編兵。')
        command_books.close_allocation(state, state.player, city=payload['city'], identity=payload['flow'])

    def _recruit(self, state, payload):
        city = self._owned_city(state, payload.get('city'), action=True)
        if 'allocation_flow' in payload and type(payload['allocation_flow']) is not bool:
            raise GameError('操作参数无效。')
        r = self.catalog.data['rules']
        if city.gold < r['recruit_gold_per_100'] or city.grain < r['recruit_grain_per_100']:
            raise GameError('金钱或粮食不足。')
        city.gold -= r['recruit_gold_per_100']
        city.grain -= r['recruit_grain_per_100']
        domestic.add_reserves(self,state,city,r['recruit_per_action'],recruited=True)
        command_books.spend(state, city, 'recruit')
        if payload.get('allocation_flow'):
            command_books.open_allocation(state, city)
        self._note(state, f'{self.catalog.map_cities[city.id]["name"]}征募{r["recruit_per_action"]}名预备兵。')

    def _depart(self, state, payload):
        source = self._owned_city(state, payload.get('source'), action=True)
        target_key = payload.get('target')
        adjacent = target_key in self._neighbors(source.id,state)
        exploring = (payload.get('route_mode') == 'explore' and
                     self._exploration_route(source.id,target_key) is not None)
        if target_key not in state.cities or not (adjacent or exploring):
            raise GameError('请选择相邻且已开放的城池。')
        target = state.cities[target_key]
        if target.owner == state.player:
            raise GameError('不能向本方城池出征。')
        ids = payload.get('officers')
        if not isinstance(ids, list) or any(not (type(i) is int or is_generated_ref(i)) for i in ids):
            raise GameError('出征名单无效。')
        for ident in ids:self._personnel_actor(state,source,ident)
        self._queue_march(state,source,target,ids,'attack',payload.get('route_mode','fastest'))

    def _damage(self, state, attacker, defender):
        spread = 90 + state.rng.next() % 21
        base = attacker['troops'] * (attacker['martial'] + 40) * self.catalog.data['rules']['battle_damage_percent'] * spread
        amount=max(1,base//((defender['martial']+80)*10000))
        support=(state.battle or {}).get('extended',{}).get('support',{}).get(str(attacker['id']),{})
        factor=max(80,min(110,100+(support.get('morale',70)-70)//3))
        return min(defender['troops'],max(1,amount*factor//100))

    def _attack(self, state, payload):
        return self._expanded_attack(state, payload)

    def _retreat(self, state, payload):
        return self._expanded_retreat(state, payload)

    def _settle(self, state, payload):
        return self._expanded_settle(state, payload)

    def _end_turn(self, state, payload):
        if state.extension.get('pending_succession', {}).get(state.player):
            raise GameError('请先选择继承君主。')
        if state.phase != 'city':
            raise GameError('请先完成当前操作或战果结算。')
        if 'domestic' in state.extension:
            from .domestic import finish_faction_turn
            finish_faction_turn(self,state,state.player)
        state.phase = 'ai'

    def _ai(self, state, payload):
        return self._expanded_ai(state, payload)

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
            facilities.synchronize(self,state)
            treasures.synchronize(self,state)
            treasures.inherit_city(state,key,parent.id)
            if key == 'xinxing' and 'month' not in rule:
                # Keep the released year-only event text and replay output.
                self._note(state,f'{self.catalog.map_cities[key]["name"]}建郡，承接晋阳当时归属与部分资源；未新增兵员或强制转属。')
            else:
                parent_name = self.catalog.map_cities[rule['parent']]['name']
                self._note(state,f'{self.catalog.map_cities[key]["name"]}建置，承接{parent_name}当时归属与部分资源；未新增兵员或强制转属。')

    def _monthly_calendar(self, state):
        """Monthly income, healing and dated events run only at month rollover."""
        r = self.catalog.data['rules']
        self._open_dated_cities(state)
        domestic.synchronize(self,state)
        if state.year > state.calendar_cursor:
            events = advance_year(self.all_person_definitions(state), state.officers,
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
                        home=state.cities[event['origin_city']]
                        domestic.add_reserves(self,state,home,released,morale_value=domestic.morale(state,home.id))
                    name = next(p.name for p in self.all_person_definitions(state) if p.person_id == event['person_id'])
                    if event.get('already_dead'):
                        self._note(state, f'{name}此前已死亡，本年仅完成年代核对。')
                    else:
                        self._note(state, f'{name}到达寿命边界，释放兵员{released}归原城。')
            state.calendar_cursor = state.year
            self._note(state, f'新年更新人物库，记录{count}项年代事件；未自动招募或复活人物。')
        for city in state.cities.values():
            if city.owner != 'neutral':
                income=income_at(self.catalog.data,city.id,state.year,state.month) or {
                    'gold':r['monthly_gold_income'],'grain':r['monthly_grain_income'],'reserves':0}
                income=facilities.adjusted_income(state,city.id,income)
                city.gold += income['gold']
                city.grain += income['grain']
                domestic.add_reserves(self,state,city,income['reserves'],recruited=True)
        existing = set(state.officers)
        self._spawn_eligible(state)
        for ident, officer in state.officers.items():
            if ident in existing and officer.alive:
                officer.health = min(officer.profile.health_max, officer.health + r['monthly_heal'])
        domestic.month_rollover(self,state)
        facilities.month_rollover(self,state)

    def _complete_turn(self, state):
        """Commit one fixed ten-day turn and begin the next strategic phase."""
        state.completed_ai_turns.append(state.turn)
        self._process_march_supply(state,through_turn=state.turn+1)
        state.day += 10
        month_changed = state.day > 30
        if month_changed:
            state.day = 1
            state.month += 1
            if state.month > 12:
                state.month = 1
                state.year += 1
            self._monthly_calendar(state)
        state.turn += 1
        if month_changed:
            from . import dated_events
            dated_events.process(self,state)
        self._resolve_supply_retreats(state)
        logistics.resolve_supply_retreats(self,state)
        for city in state.cities.values():
            city.action_used = False
        command_books.initialize(self, state)
        state.phase = 'city'
        self._prune_marches(state)
        logistics.synchronize(self,state)
        domestic.synchronize(self,state)
        treasures.synchronize(self,state)
        facilities.synchronize(self,state)
        equipment.synchronize(self,state)
        if logistics.due(state) or any(r['arrival_turn'] <= state.turn for r in state.extension['travel']['marches']):
            state.phase = 'arrivals'
        if not any(c.owner == state.player for c in state.cities.values()) or not any(o.alive and o.faction_id == state.player for o in state.officers.values()):
            state.phase = 'finished'
            self._note(state, '本方已无可用驻军，本次演练结束。')
        else:
            if month_changed:
                self._note(state,'新月结算：各城按规模获得金钱、粮食与预备兵收入，武将恢复体力。')
            self._note(state,'各势力本旬行动完成，进入下一旬战略阶段；每旬固定10天。')

    def export_save(self):
        with self.lock:
            if self.state is None:
                raise GameError('请先开始演练。')
            value = {'format': 'three-kingdoms-remake-save', 'version': 2,
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
                if content['format'] != 'three-kingdoms-remake-save' or type(content['version']) is not int or content['version'] not in (1, 2) or content['catalog_sha256'] != self.catalog.sha256 or content['scenario'] != self.catalog.data['id'] or digest(content) != payload['checksum']:
                    raise ValueError('save identity/checksum')
                raw = deepcopy(content['state'])
                # The current catalog's existing campaigns acquire the three
                # new presentation/AI preferences without replaying past events.
                # Historical catalog IDs/checksums remain unsupported.
                extension = raw['extension']
                legacy = content['version'] == 1
                if ('command_books' in extension) == legacy:
                    raise ValueError('Save format does not match its strategic-order ledger')
                extension.setdefault('difficulty', 'normal')
                extension.setdefault('ai_strategy', {})
                extension.setdefault('events', empty_events())
                raw['rng'] = SeedRng(**raw['rng'])
                officers = {}
                for key, row in raw['officers'].items():
                    ident = deserialize_officer_ref(key, self.catalog.rules)
                    expected = self.person_profile(SimpleNamespace(extension=extension), ident)
                    person_id = ident if is_generated_ref(ident) else self.catalog.by_id[ident]['person_id']
                    if row['runtime_id'] != ident or row['person_id'] != person_id or row['profile'] != asdict(expected):
                        raise ValueError('officer identity/profile')
                    row['profile'] = expected
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
                if legacy:
                    command_books.initialize(self, candidate, legacy=True)
                # Existing current-catalog battles had presentation-only flags.
                # Assign their first real cells once, preserving troops and RNG.
                if candidate.battle and 'tactical' not in candidate.battle['extended']:
                    tactical=battle_grid.initialize(self, candidate, candidate.battle)
                    # The former counter-based UI always saved on the player's
                    # decision. Do not strand an old defender behind an enemy
                    # turn that no command has been scheduled to execute.
                    own,_=self._player_sides(candidate)
                    tactical['side']=own
                    if own=='defenders':tactical['passed']['attackers']=True
                self.validate(candidate)
            except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
                raise GameError('存档无效，当前进度未改变。') from exc
            self.state = candidate
            self.revision += 1
            self.journal.append({'kind': 'load', 'revision': self.revision, 'after_sha256': digest(self.to_dict()), 'rng_draws': candidate.rng.draws})
            return self.view()

    def validate(self, state):
        get_settings(state)
        command_books.validate(self, state)
        civil_staff.validate(self, state)
        domestic.validate(self,state)
        logistics.validate(self,state)
        treasures.validate(self,state)
        facilities.validate(self,state)
        equipment.validate(self,state)
        validate_events(self, state)
        self._validate_expansion(state)
        if state.player not in self.catalog.factions or state.phase not in {'city', 'battle', 'result', 'ai', 'finished', 'arrivals'}:
            raise ValueError('campaign phase/player')
        integer(state.year, 1, 400, 'year')
        integer(state.month, 1, 12, 'month')
        integer(state.day, 1, 21, 'day')
        if state.day not in (1, 11, 21):
            raise ValueError('calendar ten-day period')
        integer(state.turn, 1, 1000000, 'turn')
        integer(state.seed, 1, 0xffffffff, 'seed')
        integer(state.rng.state, 1, 0xffffffff, 'rng state')
        integer(state.rng.draws, 0, 100000000, 'rng draws')
        elapsed = (state.year - self.catalog.data['start_year']) * 12 + state.month - self.catalog.data['start_month']
        if state.calendar_cursor != state.year or elapsed * 3 + (state.day - 1) // 10 != state.turn - 1 or set(state.cities) != set(self.catalog.active_city_ids(state.year,state.month)):
            raise ValueError('calendar/city domain')
        if any(type(v) is not int or not 0 <= v <= 100000000 for v in state.soldiers.values()) or set(state.soldiers) != {'initial', 'recruited', 'lost'}:
            raise ValueError('soldier ledger')
        seen = set()
        for key, city in state.cities.items():
            city.roster.validate()
            if self._city_occupancy(state, city) > self.catalog.rules.city_officer_capacity:
                raise ValueError('Combined officer and civil staff capacity exceeded')
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
            if ident != officer.runtime_id or officer.person_id != self.person_definition(state, ident).person_id or officer.person_id in people or officer.profile != self.person_profile(state, ident) or officer.profile.missing:
                raise ValueError('officer identity/profile')
            people.add(officer.person_id)
            for value, low, high in ((officer.health, 0, officer.profile.health_max), (officer.loyalty, 0, 100),
                                     (officer.troops, 0, 999), (officer.weapon_id, 0, len(equipment.WEAPONS)-1), (officer.armor_id, 0, len(equipment.ARMORS)-1),
                                     (officer.experience, 0, 49999), (officer.tier, 0, 7)):
                integer(value, low, high, 'officer state')
            if officer.tier != experience_tier(officer.experience) or type(officer.alive) is not bool:
                raise ValueError('experience/alive')
            if officer.faction_id is not None and officer.faction_id not in {*self.catalog.factions, 'neutral'}:
                raise ValueError('unknown faction')
            if officer.faction_id is not None and year_state(self.person_definition(state, ident), state.year) not in {YearState.AVAILABLE, YearState.DEATH_YEAR_REVIEW}:
                raise ValueError('officer annual membership')
            if ident not in seen and (officer.faction_id is not None or officer.troops != 0):
                raise ValueError('unassigned officer ownership/troops')
        current_soldiers = (sum(c.reserves for c in state.cities.values())
            +sum(o.troops for o in state.officers.values())+logistics.in_transit_reserves(state))
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
        for ident, officer in state.officers.items():
            p = self.person_definition(state, ident)
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
            if set(battle) != base_fields | {'extended'}:
                raise ValueError('battle fields')
            if battle['id'] != f'battle-{state.battle_counter}' or battle['outcome'] not in {None, 'victory', 'defeat', 'retreat'}:
                raise ValueError('battle identity/outcome')
            integer(battle['round'], 1, 100000, 'battle round')
            integer(battle['supply_cost'], 0, 10000, 'supply cost')
            if not isinstance(battle['log'], list) or len(battle['log']) > 80 or any(not isinstance(t, str) or len(t) > 500 for t in battle['log']):
                raise ValueError('battle log')
            connected = battle['target'] in self._neighbors(battle['source'], state)
            if battle['source'] == battle['target'] or not connected or battle['id'] in state.settled_battles:
                raise ValueError('battle location/receipt')
            if battle['attacker'] not in self.catalog.factions or state.cities[battle['source']].owner != battle['attacker'] or state.cities[battle['target']].owner != battle['defender']:
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
            if len(all_ids) != len(set(all_ids)) or len(battle['used']) != len(set(battle['used'])) or not set(battle['used']) <= {u['id'] for u in battle[self._player_sides(state)[0]]}:
                raise ValueError('battle duplicate/turn ownership')
            attacking = any(u['troops'] > 0 for u in battle['attackers'])
            defending = any(u['troops'] > 0 for u in battle['defenders'])
            if state.phase == 'battle' and not (attacking and defending):
                raise ValueError('battle without active sides')
            withdrew = battle['extended']['withdrawn'] == 'defenders'
            if battle['outcome'] == 'victory' and ((defending and not withdrew) or not attacking):
                raise ValueError('victory before defenders rout')
            if battle['outcome'] == 'defeat' and (attacking or not defending):
                raise ValueError('defeat before attackers rout')
