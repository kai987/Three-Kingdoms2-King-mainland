"""Atomic scenario switching. Failed new/load requests retain the current game."""
from threading import RLock
from .campaign import Campaign, Catalog, GameError


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
            result['catalog']['scenario_id']=self.game.catalog.data['id']
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

    def load_save(self, save, revision):
        with self.lock:
            if type(revision) is not int or revision!=self.revision:raise GameError('进度已更新。',409)
            scenario=save.get('scenario') if isinstance(save,dict) else None
            if not isinstance(scenario,str) or scenario not in self.catalogs:raise GameError('存档所属战役不可用，进度未改变。')
            candidate=Campaign(self.catalogs[scenario]);candidate.revision=self.revision
            candidate.load_save(save,revision)
            self.game=candidate
            return self.view()
