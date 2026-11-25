"""Atomic scenario switching. Failed new/load requests retain the current game."""
from threading import RLock
from . import city_development, domestic, economy_rules, grain_units, payroll, southern_mission
from .campaign import Campaign, Catalog, GameError, verified_save_content
from .map_presentation import city_names,presentation,faction_colors
from .city_economy import (frontier_outposts_view, garrison_grain, garrison_grain_cost, grain_balance,
                           monthly_income, opening_monthly_income, profile_at, profiles_at, stationed_troops, town_level)
from .officer_relations import opening_values
from .dated_events import visible_factions
from .treasures import opening_stock as opening_treasure_stock


DEFAULT_SCENARIO = 'mainland184-02'


def _agricultural_balance(factors, balance, bonus, active_bill, wage, facility):
    return dict(factors, damage=facility['damage'], regular_grain=balance['production'] - bonus,
                civil_bonus=bonus, civilian_grain=balance['civilian'], active_grain=active_bill,
                reserve_grain=balance['upkeep'] - active_bill, wage_gold=wage['gold'], wage_grain=wage['grain'],
                net_grain=balance['net'] - wage['grain'])


def _town_agriculture(detail):
    fields = ('population_cap', 'town_bonus_percent', 'civilian_grain', 'regular_grain', 'net_grain')
    return {key: detail[key] for key in fields}


def faction_resources(catalog, state=None):
    """Count city stocks and troops serving under the faction's officers."""
    totals = {key: dict(gold=0, grain=0, reserves=0, cities=0, troops=0) for key in catalog.factions}
    if state is not None:
        for city in state.cities.values():
            if city.owner not in totals:
                continue
            total = totals[city.owner]
            total['cities'] += 1
            for field in ('gold', 'grain', 'reserves'):
                total[field] += getattr(city, field)

        # Officers keep their troops while marching. Deployed troops are
        # tracked in battle units until the survivors are written back.
        deployed = {}
        if state.battle is not None:
            deployed = {unit['id']: unit['troops'] for side in ('attackers', 'defenders')
                        for unit in state.battle[side]}
        for ident, officer in state.officers.items():
            if officer.alive and officer.faction_id in totals:
                totals[officer.faction_id]['troops'] += deployed.get(ident, officer.troops)
        if southern_mission.OWNER in totals:
            totals[southern_mission.OWNER]['troops'] += southern_mission.in_transit_troops(state)
    else:
        data = catalog.data
        stocks, troops = catalog.opening_garrisons
        for key in data['active_cities']:
            owner = data['initial_owners'][key]
            if owner not in totals:
                continue
            total = totals[owner]
            total['cities'] += 1
            for field in ('gold', 'grain', 'reserves'):
                total[field] += grain_units.CURRENT * stocks[key][field] if field == 'grain' else stocks[key][field]
        for row in data['initial_officers']:
            owner = data['initial_owners'][row['city']]
            if owner in totals:
                totals[owner]['troops'] += troops[row['person_id']]
    return totals


def faction_officer_counts(catalog, state=None):
    """Count current living members once, including marching/battle officers.

    Personnel transfers are reflected by faction_id. Captive, free, neutral,
    dead and not-yet-instantiated people do not count.
    Opening previews use actual starting rosters, not planned era assignments.
    """
    members={key:set() for key in catalog.factions}
    if state is not None:
        for officer in state.officers.values():
            if officer.alive and officer.faction_id in members:
                members[officer.faction_id].add(officer.person_id)
    else:
        for row in catalog.data['initial_officers']:
            owner=catalog.data['initial_owners'][row['city']]
            if owner in members:members[owner].add(row['person_id'])
    return {key:len(people) for key,people in members.items()}


def preview_city_history(catalog):
    """Keep map hints and island summaries. The city endpoint serves full evidence."""
    result = {}
    for city, history in catalog.data.get('city_history', {}).items():
        hints = {key: history[key] for key in ('neutral_label', 'summary_i18n', 'detail_ja', 'chronology')
                 if key in history}
        basis = history.get('opening', {}).get('basis')
        if basis:
            hints['opening'] = {'basis': basis}
        if hints:
            result[city] = hints
    return result


class CampaignSession:
    def __init__(self, paths, *, initial_scenario=None, record_journal=True):
        self.record_journal = record_journal
        catalogs=[Catalog(path) for path in paths]
        if not catalogs:
            raise ValueError('Current campaign catalogs are required')
        self.catalogs={c.data['id']:c for c in catalogs}
        if len(self.catalogs)!=len(catalogs):
            raise ValueError('Duplicate current campaign id')
        if initial_scenario is None:
            # The full game always opens Yellow Turban. Partial catalog sets
            # used by tools/tests fall back by chronology, never caller order.
            initial_scenario = DEFAULT_SCENARIO if DEFAULT_SCENARIO in self.catalogs else min(
                self.catalogs, key=lambda key: (self.catalogs[key].data['start_year'],
                                               self.catalogs[key].data['start_month'], key))
        if not isinstance(initial_scenario, str) or initial_scenario not in self.catalogs:
            raise ValueError('Unknown initial scenario')
        self.game=Campaign(self.catalogs[initial_scenario], record_journal=self.record_journal)
        self.lock=RLock()
        self._opening_previews=None
        # Before a campaign starts, income depends only on the selected
        # catalog and the current default grain rules. Live views use state.
        self._opening_incomes={}

    @property
    def revision(self): return self.game.revision
    @property
    def journal(self): return self.game.journal
    def to_dict(self): return self.game.to_dict()

    def view(self):
        with self.lock:
            return self._decorate_view(self.game.view())

    def _decorate_view(self, result):
        with grain_units.using(self.game.state):
            return self._campaign_view(result)

    def _campaign_view(self, result):
        """Add session metadata to one fresh campaign response under our lock."""
        names=city_names(self.game.catalog,
            self.game.state.year if self.game.state else self.game.catalog.data['start_year'],
            self.game.state.month if self.game.state else self.game.catalog.data['start_month'])
        result['catalog']['cities']=[dict(c,name=names[c['id']],administrative_name=c['name'])
                                     for c in result['catalog']['cities']]
        result['catalog']['map_presentation']=presentation()
        date=self.game.state or self.game.catalog.data
        year=date.year if self.game.state else date['start_year']
        month=date.month if self.game.state else date['start_month']
        result['catalog']['city_profiles']=profiles_at(self.game.catalog.data,year,month)
        result['catalog']['frontier_outposts']=frontier_outposts_view(self.game.catalog.data,self.game.state)
        if self.game.state:
            state = self.game.state
            development = result['catalog']['city_development']['cities']
            city_keys = dict.fromkeys((*self.game.catalog.data.get('city_income', {}), *state.cities))
            income = {key: development[key]['income'] if key in development else monthly_income(self.game, key, state)
                      for key in city_keys}
            stationed = stationed_troops(self.game, state)
            upkeep = garrison_grain(self.game, state, stationed=stationed)
            result['catalog']['city_income'] = income
            balances, details = {}, {}
            for key, city in state.cities.items():
                town = town_level(self.game, state, key)
                bonus = domestic.earned_grain(state, key, income[key]) if city.owner != 'neutral' else 0
                population = development[key]['population']
                balance = grain_balance(income[key]['grain'] + bonus, upkeep[key], city.owner,
                                        population, town=town, state=state)
                balances[key] = balance
                factors = city_development.agriculture_details(self.game, state, key, town)
                if factors is None:
                    continue
                wage = payroll.monthly_due(state, city) if city.owner != 'neutral' else dict(gold=0, grain=0)
                active_bill = garrison_grain_cost(self.game.catalog.data, key, year, month, stationed.get(key, 0), 0)
                facility = result['catalog']['facilities']['cities'][key]
                details[key] = _agricultural_balance(factors, balance, bonus, active_bill, wage, facility)
                if town < 3 and city.owner == state.player:
                    next_town = town + 1
                    revised = monthly_income(self.game, key, state, town=next_town)
                    next_bonus = domestic.earned_grain(state, key, revised)
                    projection = grain_balance(revised['grain'] + next_bonus, upkeep[key], city.owner,
                                               population, town=next_town, state=state)
                    next_factors = economy_rules.TOWN_AGRICULTURE[next_town]
                    facility['develop']['agriculture'] = dict(
                        before=_town_agriculture(details[key]),
                        after=dict(population_cap=next_factors.population_cap,
                                   town_bonus_percent=next_factors.grain_bonus_percent,
                                   civilian_grain=projection['civilian'], regular_grain=revised['grain'],
                                   net_grain=projection['net'] - wage['grain']))
            result['catalog']['city_grain_balance'] = balances
            result['catalog']['city_agriculture'] = details
            from . import faction_economy, logistics_strategy, military_budget, war_recovery
            if logistics_strategy.enabled(state):
                owners = sorted({city.owner for city in state.cities.values()} - {'neutral'})
                reports, cities = {}, {}
                for owner in owners:
                    plan = faction_economy.plan(self.game, state, owner, stationed=stationed, incomes=income)
                    reports[owner] = plan.summary(state)
                    if logistics_strategy.war_recovery(state):
                        reports[owner]['recovery'] = war_recovery.Forecast(self.game,state,owner,plan).view()
                    for key, row in plan.budgets.items():
                        forecast = plan.cities[key]
                        row['deliveries'] = [[eta, amount] for eta, amount in forecast.receipts.items() if amount]
                        if owner != state.player and row['reserved_grain']:
                            row['offense'] = [order['target']
                                for order in state.extension['ai_strategy'][owner]['orders']
                                if order['source'] == key and order['march_id'] is None]
                        cities[key] = row
                result['catalog']['military_logistics'] = cities
                result['catalog']['faction_logistics'] = reports
            elif military_budget.enabled(state):
                result['catalog']['military_logistics'] = military_budget.budgets(
                    self.game,state,state.player,stationed=stationed,incomes=income)
        else:
            scenario = self.game.catalog.data['id']
            if scenario not in self._opening_incomes:
                self._opening_incomes[scenario] = {key: opening_monthly_income(self.game, key)
                    for key in self.game.catalog.data.get('city_income', {})}
            result['catalog']['city_income'] = {key: dict(income)
                for key, income in self._opening_incomes[scenario].items()}
        result['catalog']['road_additions']=self.game.catalog.data.get('road_additions',[])
        result['catalog']['world']=self.game.catalog.data.get('world')
        result['catalog']['scenario_id']=self.game.catalog.data['id']
        result['catalog']['faction_resources']=faction_resources(self.game.catalog,self.game.state)
        result['catalog']['faction_officers']=faction_officer_counts(self.game.catalog,self.game.state)
        result['catalog']['faction_colors']=faction_colors(self.game.catalog)
        result['catalog']['sea_routes']=self.game.catalog.data.get('sea_routes',[])
        result['catalog']['travel_hazards']=self.game.catalog.data.get('travel_hazards')
        for field in ('added_city_ids','regional_roads','river_routes','city_label_offsets','city_history'):
            result['catalog'][field]=self.game.catalog.data.get(field,[] if field in ('added_city_ids','regional_roads','river_routes') else {})
        result['catalog']['scenarios']=self._scenario_previews()
        return result

    def _scenario_previews(self):
        """Build immutable opening summaries once, retaining fresh view containers.

        Catalog files are fixed for the lifetime of a session. Opening names,
        ownership and membership never depend on the live month or command.
        Lists/maps built by the old view remain per-response copies, so callers
        cannot poison a later preview by editing one of those containers.
        """
        if self._opening_previews is None:
            self._opening_previews=[{'id':c.data['id'],'title':c.data['title'],
                                           'cities':len(c.data['active_cities']),
                                           'year':c.data['start_year'],'month':c.data['start_month'],
                                           'configured':c.data.get('coverage',{}).get('configured_profiles',8),
                                           'capacity':c.rules.city_officer_capacity,
                                           'serving':len(c.data['initial_officers']),
                                           'free':len(c.data.get('initial_free_officers',[])),
                                           'main_scenario':c.data.get('main_scenario'),
                                           'initial_owners':dict(c.data['initial_owners']),
                                           'active_cities':list(c.data['active_cities']),
                                           'city_names':city_names(c,c.data['start_year'],c.data['start_month']),
                                           'map_cities':list(c.map_cities.values()),
                                           'city_profiles':{key:{field:profile[field] for field in ('tier','kind') if field in profile}
                                               for key,profile in profiles_at(c.data,c.data['start_year'],c.data['start_month']).items()},
                                           'world':c.data.get('world'),
                                           'road_additions':c.data.get('road_additions',[]),
                                           'added_city_ids':c.data.get('added_city_ids',[]),
                                           'regional_roads':c.data.get('regional_roads',[]),
                                           'river_routes':c.data.get('river_routes',[]),
                                           'city_label_offsets':c.data.get('city_label_offsets',{}),
                                           'city_history':preview_city_history(c),
                                           'faction_resources':faction_resources(c),
                                           'faction_officers':faction_officer_counts(c),
                                           'faction_colors':faction_colors(c),
                                           'travel_hazards':c.data.get('travel_hazards'),
                                           'sea_routes':c.data.get('sea_routes',[]),
                                           'factions':[dict(f, ruler_person_id=c.by_id[c.data['faction_rulers'][f['id']]]['person_id'])
                                                       for f in visible_factions(c)]} for c in self.catalogs.values()]
        return [dict(row,
            initial_owners=dict(row['initial_owners']),
            active_cities=list(row['active_cities']),
            city_names=dict(row['city_names']),
            map_cities=list(row['map_cities']),
            city_profiles={key:dict(profile) for key,profile in row['city_profiles'].items()},
            faction_resources={key:dict(values) for key,values in row['faction_resources'].items()},
            faction_officers=dict(row['faction_officers']),
            faction_colors=dict(row['faction_colors']),
            factions=[dict(faction) for faction in row['factions']]) for row in self._opening_previews]

    def command(self, kind, payload, revision):
        with self.lock:
            if kind=='new':
                if not isinstance(payload,dict): raise GameError('操作参数无效。')
                scenario=payload.get('scenario',self.game.catalog.data['id'])
                if not isinstance(scenario,str) or scenario not in self.catalogs:raise GameError('请选择有效的战役。')
                if type(revision) is not int or revision!=self.revision:raise GameError('进度已更新。',409)
                candidate=Campaign(self.catalogs[scenario], record_journal=self.record_journal);candidate.revision=self.revision
                result=candidate.command(kind,payload,revision)
                self.game=candidate
            else:result=self.game.command(kind,payload,revision)
            return self._decorate_view(result)

    def export_save(self, *, compact=False):
        with self.lock:return self.game.export_save(compact=compact)

    def preview_city(self, scenario, city):
        """Read opening data for one city without creating a game or drawing RNG."""
        with self.lock, grain_units.using():
            if not isinstance(scenario,str) or scenario not in self.catalogs:
                raise GameError('请选择有效的战役。')
            c=self.catalogs[scenario];d=c.data
            if not isinstance(city,str) or city not in d['active_cities']:
                raise GameError('请选择本剧本开放的城池。')
            officers=[]
            stocks,troops=c.opening_garrisons
            from .equipment import initial_view
            from .city_development import opening_view
            from .facilities import opening_view as opening_facilities
            preview_game=self.game if c is self.game.catalog else Campaign(c)
            for row in d['initial_officers']:
                if row['city']!=city:continue
                ident=c.ids[row['person_id']];profile=c.profiles[ident]
                person=c.by_id[ident]
                officers.append(dict(id=ident,person_id=row['person_id'],name=c.name(ident),martial_strength=profile.martial_strength,
                                     intellect=profile.intellect,virtue=profile.virtue,troops=troops[row['person_id']],
                                     experience=0,tier=0,
                                     **opening_values(c,ident,
                                                         faction_id=d['initial_owners'][city],is_ruler=row.get('ruler',False)),
                                     is_ruler=bool(row.get('ruler')),equipment=initial_view(preview_game,row['person_id']),
                                     **({'regnal_title':person['regnal_title']} if 'regnal_title' in person else {})))
            owner=d['initial_owners'][city]
            treasure = opening_treasure_stock(d,city,owner,d['start_year'],d['start_month'])
            facilities=opening_facilities(d,city)
            facilities['services']=['hospital','market']+(['school','armory'] if facilities['town']>=2 else [])
            development = opening_view(c, city)
            income = opening_monthly_income(preview_game, city, development=development, facility=facilities)
            history=d.get('city_history',{}).get(city,{})
            neutral_name=history.get('neutral_label') or ('地方汉郡（中立）' if history.get('opening',{}).get('basis')=='unmapped_local_han_administration' else '无主')
            frontier=frontier_outposts_view(d).get(city)
            active = sum(o['troops'] for o in officers)
            upkeep = garrison_grain_cost(d, city, d['start_year'], d['start_month'], active,
                                        grain_units.stocks(stocks[city])['reserves'])
            balance = grain_balance(income['grain'], upkeep, owner, development['population'], town=facilities['town'])
            factors = city_development.agriculture_details(preview_game, None, city, facilities['town'], opening=development)
            agriculture = None
            if factors is not None:
                count = len(officers) if owner != 'neutral' else 0
                wage = {key: value * count for key, value in payroll.officer_wage(0).items()}
                active_bill = garrison_grain_cost(d, city, d['start_year'], d['start_month'], active if count else 0, 0)
                agriculture = _agricultural_balance(factors, balance, 0, active_bill, wage, facilities)
            prefect = d.get('initial_governors', {}).get(city)
            governor = c.ids[prefect['person_id']] if prefect else None
            return dict(scenario=scenario,title=d['title'],year=d['start_year'],month=d['start_month'],
                capacity=c.rules.city_officer_capacity, grain_people_per_day=grain_units.denominator(),
                city=dict(id=city,owner=owner,treasure=treasure,governor=governor,facilities=facilities,city_development=development,owner_name=c.factions[owner]['name'] if owner!='neutral' else neutral_name,
                    terrain=c.map_cities[city].get('terrain'),officers=officers,agriculture=agriculture,
                    profile=profile_at(d,city,d['start_year'],d['start_month']),income=income, grain_balance=balance,
                    history=d.get('city_history',{}).get(city),frontier_outpost=frontier,
                    **grain_units.stocks(stocks[city])))

    def preview_march(self, source, target, revision):
        """Quote from one player-owned city without spending a command or RNG."""
        from .march_preview import preview

        with self.lock, grain_units.using(self.game.state):
            if (not isinstance(revision, str) or not 1 <= len(revision) <= 16
                    or not revision.isascii() or not revision.isdecimal()):
                raise GameError('查询参数无效。')
            if int(revision) != self.revision:
                raise GameError('进度已更新，请重新选择操作。', 409)
            state = self.game.state
            if (state is None or not isinstance(source, str) or not isinstance(target, str)
                    or source not in state.cities or target not in state.cities
                    or state.cities[source].owner != state.player
                    or 'travel_rules' not in self.game.catalog.data):
                raise GameError('查询参数无效。')
            return preview(self.game, state, source, target, self.revision)

    def preview_transfer(self, payload):
        """Quote a transfer choice against one current order selection."""
        from .march_preview import preview_transfer

        with self.lock, grain_units.using(self.game.state):
            if (not isinstance(payload, dict)
                    or set(payload) != {'source', 'target', 'officers', 'route_mode', 'revision'}
                    or type(payload['revision']) is not int):
                raise GameError('操作参数无效。')
            if payload['revision'] != self.revision:
                raise GameError('进度已更新，请重新选择操作。', 409)
            state = self.game.state
            if state is None or 'travel_rules' not in self.game.catalog.data:
                raise GameError('查询参数无效。')
            source, target, ids = self.game._transfer_selection(state, payload)
            return preview_transfer(self.game, state, source.id, target.id, ids,
                                    payload['route_mode'], self.revision)

    def preview_logistics(self, payload):
        from . import logistics
        from .march_preview import preview_logistics

        with self.lock, grain_units.using(self.game.state):
            fields={'source','target','officers','route_mode','purpose','cargo','reserves','revision'}
            state=self.game.state
            if (not isinstance(payload,dict) or set(payload)!=fields or type(payload['revision']) is not int
                    or state is None or 'travel_rules' not in self.game.catalog.data):
                raise GameError('查询参数无效。')
            if self.revision!=payload['revision']:
                raise GameError('进度已更新，请重新选择操作。',409)
            source,target,ids,mode,purpose,cargo,reserves=(
                payload[key] for key in ('source','target','officers','route_mode','purpose','cargo','reserves'))
            if (not isinstance(source,str) or not isinstance(target,str) or source==target
                    or source not in state.cities or target not in state.cities
                    or state.cities[source].owner!=state.player
                    or not isinstance(mode,str) or mode not in self.game._travel_modes()
                    or not isinstance(purpose,str) or purpose not in ('attack','transfer','convoy')
                    or not isinstance(ids,list) or not 1<=len(ids)<=99
                    or any(type(ident) not in (int,str) for ident in ids) or len(set(ids))!=len(ids)
                    or any(type(value) is not int or not 0<=value<=logistics.LIMIT for value in (cargo,reserves))
                    or purpose!='convoy' and (cargo or reserves)
                    or purpose=='attack' and len(ids)>self.game.catalog.rules.battle_officers_per_side):
                raise GameError('查询参数无效。')
            city=state.cities[source]
            if purpose=='convoy':
                if any(ident not in logistics._eligible(self.game,state,city) for ident in ids):
                    raise GameError('请选择可参与运输的武将。')
            else:
                ids=[self.game._personnel_actor(state,city,ident).runtime_id for ident in ids]
            if purpose!='attack' and state.cities[target].owner!=state.player:
                raise GameError('请选择本方目的城。')
            return preview_logistics(self.game,state,source,target,ids,mode,purpose,cargo,reserves,self.revision)

    def load_save(self, save, revision):
        with self.lock:
            if type(revision) is not int or revision!=self.revision:raise GameError('进度已更新。',409)
            scenario=save.get('scenario') if isinstance(save,dict) else None
            if not isinstance(scenario, str) or scenario not in self.catalogs:
                verified_save_content(save)
                raise GameError('存档所属战役不可用，进度未改变。')
            candidate=Campaign(self.catalogs[scenario], record_journal=self.record_journal);candidate.revision=self.revision
            result=candidate.load_save(save,revision)
            self.game=candidate
            return self._decorate_view(result)
