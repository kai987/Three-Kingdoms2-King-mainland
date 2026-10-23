"""Atomic scenario switching. Failed new/load requests retain the current game."""
from threading import RLock
from .campaign import Campaign, Catalog, GameError
from .map_presentation import city_names,presentation,faction_colors
from .city_economy import profiles_at,incomes_at


def faction_resources(catalog, state=None):
    totals={key:dict(gold=0,grain=0,reserves=0,cities=0) for key in catalog.factions}
    if state:
        rows=[(city.owner,city) for city in state.cities.values()]
        for owner,city in rows:
            if owner not in totals:continue
            totals[owner]['cities']+=1
            for field in ('gold','grain','reserves'):totals[owner][field]+=getattr(city,field)
    else:
        data=catalog.data
        for key in data['active_cities']:
            owner=data['initial_owners'][key]
            if owner not in totals:continue
            totals[owner]['cities']+=1
            values=data.get('initial_city_resources',{}).get(key,data['initial_resources'])
            for field in ('gold','grain','reserves'):totals[owner][field]+=values[field]
    return totals


def faction_officer_counts(catalog, state=None):
    """Count current living members once, including marching/battle officers.

    There is no separate captive pool: a personnel transfer is reflected by
    faction_id. Free, neutral, dead and not-yet-instantiated people do not count.
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


class CampaignSession:
    def __init__(self, paths):
        catalogs=[Catalog(path) for path in paths]
        if not catalogs:
            raise ValueError('Current campaign catalogs are required')
        self.catalogs={c.data['id']:c for c in catalogs}
        if len(self.catalogs)!=len(catalogs):
            raise ValueError('Duplicate current campaign id')
        self.game=Campaign(catalogs[-1])
        self.lock=RLock()
        self._opening_previews=None

    @property
    def revision(self): return self.game.revision
    @property
    def journal(self): return self.game.journal
    def to_dict(self): return self.game.to_dict()

    def view(self):
        with self.lock:
            return self._decorate_view(self.game.view())

    def _decorate_view(self, result):
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
        result['catalog']['city_income']=incomes_at(self.game.catalog.data,year,month)
        result['catalog']['road_additions']=self.game.catalog.data.get('road_additions',[])
        result['catalog']['world']=self.game.catalog.data.get('world')
        result['catalog']['scenario_id']=self.game.catalog.data['id']
        result['catalog']['faction_resources']=faction_resources(self.game.catalog,self.game.state)
        result['catalog']['faction_officers']=faction_officer_counts(self.game.catalog,self.game.state)
        result['catalog']['faction_colors']=faction_colors(self.game.catalog)
        result['catalog']['sea_routes']=self.game.catalog.data.get('sea_routes',[])
        result['catalog']['travel_hazards']=self.game.catalog.data.get('travel_hazards')
        for field in ('added_city_ids','regional_roads','city_label_offsets','city_history'):
            result['catalog'][field]=self.game.catalog.data.get(field,[] if field in ('added_city_ids','regional_roads') else {})
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
                                           'city_profiles':{key:{'tier':profile['tier']} for key,profile in c.data.get('city_profiles',{}).items()},
                                           'world':c.data.get('world'),
                                           'road_additions':c.data.get('road_additions',[]),
                                           'added_city_ids':c.data.get('added_city_ids',[]),
                                           'regional_roads':c.data.get('regional_roads',[]),
                                           'city_label_offsets':c.data.get('city_label_offsets',{}),
                                           'city_history':c.data.get('city_history',{}),
                                           'faction_resources':faction_resources(c),
                                           'faction_officers':faction_officer_counts(c),
                                           'faction_colors':faction_colors(c),
                                           'travel_hazards':c.data.get('travel_hazards'),
                                           'sea_routes':c.data.get('sea_routes',[]),
                                           'factions':list(c.factions.values())} for c in self.catalogs.values()]
        return [dict(row,
            initial_owners=dict(row['initial_owners']),
            active_cities=list(row['active_cities']),
            city_names=dict(row['city_names']),
            map_cities=list(row['map_cities']),
            city_profiles={key:dict(profile) for key,profile in row['city_profiles'].items()},
            faction_resources={key:dict(values) for key,values in row['faction_resources'].items()},
            faction_officers=dict(row['faction_officers']),
            faction_colors=dict(row['faction_colors']),
            factions=list(row['factions'])) for row in self._opening_previews]

    def command(self, kind, payload, revision):
        with self.lock:
            if kind=='new':
                if not isinstance(payload,dict): raise GameError('操作参数无效。')
                scenario=payload.get('scenario',self.game.catalog.data['id'])
                if not isinstance(scenario,str) or scenario not in self.catalogs:raise GameError('请选择有效的战役。')
                if type(revision) is not int or revision!=self.revision:raise GameError('进度已更新。',409)
                candidate=Campaign(self.catalogs[scenario]);candidate.revision=self.revision
                result=candidate.command(kind,payload,revision)
                self.game=candidate
            else:result=self.game.command(kind,payload,revision)
            return self._decorate_view(result)

    def export_save(self):
        with self.lock:return self.game.export_save()

    def preview_city(self, scenario, city):
        """Read opening data for one city without creating a game or drawing RNG."""
        with self.lock:
            if not isinstance(scenario,str) or scenario not in self.catalogs:
                raise GameError('请选择有效的战役。')
            c=self.catalogs[scenario];d=c.data
            if not isinstance(city,str) or city not in d['active_cities']:
                raise GameError('请选择本剧本开放的城池。')
            officers=[]
            for row in d['initial_officers']:
                if row['city']!=city:continue
                ident=c.ids[row['person_id']];profile=c.profiles[ident]
                officers.append(dict(id=ident,person_id=row['person_id'],name=c.name(ident),martial_strength=profile.martial_strength,
                                     intellect=profile.intellect,virtue=profile.virtue,troops=row['troops'],
                                     experience=0,tier=0,loyalty=100 if row.get('ruler') else 80,
                                     is_ruler=bool(row.get('ruler')),health=profile.health_max))
            owner=d['initial_owners'][city]
            return dict(scenario=scenario,title=d['title'],year=d['start_year'],month=d['start_month'],
                capacity=c.rules.city_officer_capacity,
                city=dict(id=city,owner=owner,owner_name=c.factions[owner]['name'] if owner!='neutral' else
                    '地方汉郡（中立）' if d.get('city_history',{}).get(city,{}).get('opening',{}).get('basis')=='unmapped_local_han_administration' else '无主',
                    terrain=c.map_cities[city].get('terrain'),officers=officers,
                    profile=d.get('city_profiles',{}).get(city),income=d.get('city_income',{}).get(city),history=d.get('city_history',{}).get(city),
                    **d.get('initial_city_resources',{}).get(city,d['initial_resources'])))

    def load_save(self, save, revision):
        with self.lock:
            if type(revision) is not int or revision!=self.revision:raise GameError('进度已更新。',409)
            scenario=save.get('scenario') if isinstance(save,dict) else None
            if not isinstance(scenario,str) or scenario not in self.catalogs:raise GameError('存档所属战役不可用，进度未改变。')
            candidate=Campaign(self.catalogs[scenario]);candidate.revision=self.revision
            result=candidate.load_save(save,revision)
            self.game=candidate
            return self._decorate_view(result)
