"""Atomic scenario switching. Failed new/load requests retain the current game."""
from threading import RLock
from .campaign import Campaign, Catalog, GameError
from .map_presentation import city_names,presentation


class CampaignSession:
    def __init__(self, paths):
        catalogs=[Catalog(path) for path in paths]
        self.catalogs={c.data['id']:c for c in catalogs}
        self.game=Campaign(catalogs[-1])
        self.lock=RLock()

    @property
    def revision(self): return self.game.revision
    @property
    def journal(self): return self.game.journal
    def to_dict(self): return self.game.to_dict()

    def view(self):
        with self.lock:
            result=self.game.view()
            names=city_names(self.game.catalog,self.game.state.year if self.game.state else self.game.catalog.data['start_year'])
            result['catalog']['cities']=[dict(c,name=names[c['id']],administrative_name=c['name'])
                                         for c in result['catalog']['cities']]
            result['catalog']['map_presentation']=presentation()
            result['catalog']['city_profiles']=self.game.catalog.data.get('city_profiles',{})
            result['catalog']['city_income']=self.game.catalog.data.get('city_income',{})
            result['catalog']['road_additions']=self.game.catalog.data.get('road_additions',[])
            result['catalog']['world']=self.game.catalog.data.get('world')
            result['catalog']['scenario_id']=self.game.catalog.data['id']
            for field in ('added_city_ids','regional_roads','city_label_offsets','city_history'):
                result['catalog'][field]=self.game.catalog.data.get(field,[] if field in ('added_city_ids','regional_roads') else {})
            latest=max(c.data.get('content_generation',0) for c in self.catalogs.values())
            result['catalog']['scenarios']=[{'id':c.data['id'],'title':c.data['title'],
                                           'cities':len(c.data['active_cities']),
                                           'year':c.data['start_year'],'month':c.data['start_month'],
                                           'configured':c.data.get('coverage',{}).get('configured_profiles',8),
                                           'capacity':c.rules.city_officer_capacity,
                                           'serving':len(c.data['initial_officers']),
                                           'free':len(c.data.get('initial_free_officers',[])),
                                           'main_scenario':c.data.get('main_scenario'),
                                           'archived':c.data.get('content_generation',0)<latest,
                                           'initial_owners':dict(c.data['initial_owners']),
                                           'active_cities':list(c.data['active_cities']),
                                           'city_names':city_names(c,c.data['start_year']),
                                           'map_cities':list(c.map_cities.values()),
                                           'world':c.data.get('world'),
                                           'road_additions':c.data.get('road_additions',[]),
                                           'added_city_ids':c.data.get('added_city_ids',[]),
                                           'regional_roads':c.data.get('regional_roads',[]),
                                           'city_label_offsets':c.data.get('city_label_offsets',{}),
                                           'city_history':c.data.get('city_history',{}),
                                           'factions':list(c.factions.values())} for c in self.catalogs.values()]
            return result

    def command(self, kind, payload, revision):
        with self.lock:
            if kind=='new':
                if not isinstance(payload,dict): raise GameError('操作参数无效。')
                scenario=payload.get('scenario',self.game.catalog.data['id'])
                if not isinstance(scenario,str) or scenario not in self.catalogs:raise GameError('请选择有效的战役。')
                if type(revision) is not int or revision!=self.revision:raise GameError('进度已更新。',409)
                candidate=Campaign(self.catalogs[scenario]);candidate.revision=self.revision
                candidate.command(kind,payload,revision)
                self.game=candidate
            else:self.game.command(kind,payload,revision)
            return self.view()

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
                officers.append(dict(id=ident,name=c.name(ident),martial_strength=profile.martial_strength,
                                     intellect=profile.intellect,troops=row['troops']))
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
            candidate.load_save(save,revision)
            self.game=candidate
            return self.view()
