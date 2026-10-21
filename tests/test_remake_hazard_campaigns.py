"""Published hazard catalogs, chart eligibility and read-only resource views."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog
from remake.route_hazards import route_allowed
from remake.session import CampaignSession,faction_resources


class HazardCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index=json.loads((ROOT/'game/data/main-scenarios-v11/index.json').read_text())
        cls.catalogs={}
        cls.prior={}
        for path in cls.index['catalogs']:
            c=Catalog(ROOT/'game/data'/path)
            cls.catalogs[c.data['start_year']]=c
            cls.prior[c.data['start_year']]=Catalog(ROOT/'game/data'/path.replace('-v11/','-v10/'))

    def game(self,year=217,side='shu'):
        game=Campaign(self.catalogs[year])
        game.command('new',dict(faction=side,seed=2026),0)
        return game

    def test_all13_chapters_and117_starts_preserve_people_cities_and_armies(self):
        self.assertEqual(len(self.index['catalogs']),13)
        self.assertEqual(len(set(self.index['catalogs'])),13)
        starts=0
        for year,catalog in self.catalogs.items():
            data=catalog.data;before=self.prior[year].data
            self.assertEqual(data['cities'],before['cities'])
            self.assertEqual(data['city_coordinates'],before['city_coordinates'])
            self.assertEqual(data['people'],before['people'])
            self.assertEqual(data['factions'],before['factions'])
            self.assertEqual(data['initial_officers'],before['initial_officers'])
            self.assertEqual(data['initial_free_officers'],before['initial_free_officers'])
            self.assertEqual(data['initial_owners'],before['initial_owners'])
            self.assertEqual(data['active_cities'],before['active_cities'])
            self.assertEqual(data['city_foundings'],before['city_foundings'])
            self.assertEqual(data['world']['width'],before['world']['width'])
            self.assertEqual(data['world']['height'],before['world']['height'])
            self.assertEqual(data['world']['background'],'/assets/map-navigation.png')
            for side in catalog.factions:
                game=Campaign(catalog)
                game.command('new',dict(faction=side,seed=2026),0)
                game.validate(game.state);starts+=1
                self.assertEqual(Counter(o.faction_id for o in game.state.officers.values() if o.faction_id),
                    Counter(data['initial_owners'][r['city']] for r in before['initial_officers']))
                self.assertEqual(sum(o.troops for o in game.state.officers.values()),
                    sum(r['troops'] for r in before['initial_officers']))
                self.assertEqual(game.state.rng.draws,0)
        self.assertEqual(starts,117)

    def test_special_roads_are_available_separately_and_yinping_reverse_is_forbidden(self):
        for year,catalog in self.catalogs.items():
            data=catalog.data
            ziwu=[r for r in data['travel_routes'] if r.get('special')=='ziwu']
            self.assertEqual(len(ziwu),1)
            self.assertEqual({ziwu[0]['from'],ziwu[0]['to']},{'hanzhong','jingzhao'})
            self.assertIn(frozenset(('hanzhong','jingzhao')),catalog.links)
            self.assertTrue(route_allowed(data,ziwu[0],'hanzhong','jingzhao'))
            self.assertTrue(route_allowed(data,ziwu[0],'jingzhao','hanzhong'))
            draw=next(r for r in data['regional_roads'] if {r['from'],r['to']}=={'hanzhong','jingzhao'})
            self.assertEqual(draw['draw'][0]['points'][0],catalog.map_cities[draw['from']]['position'])
            self.assertEqual(draw['draw'][-1]['points'][-1],catalog.map_cities[draw['to']]['position'])
            yinping=next(r for r in data['travel_routes'] if r.get('special')=='yinping')
            self.assertTrue(route_allowed(data,yinping,'yinping','shujun'))
            self.assertFalse(route_allowed(data,yinping,'shujun','yinping'))
        game=self.game()
        self.assertIsNone(game._travel_path(game.state,'shujun','yinping','shu','special'))
        # The one-way direct road must not forbid a distinct indirect land route.
        alternate=game._travel_path(game.state,'shujun','yinping','shu','land')
        if alternate:
            self.assertFalse(any(r.get('special')=='yinping' for r in alternate['routes']))

    def test_coastal_candidates_cover_only_eighteen_coastal_nodes_and_not_known_charts(self):
        catalog=self.catalogs[217];data=catalog.data
        coastal=data['travel_hazards']['coastal_cities']
        self.assertEqual(len(coastal),18)
        self.assertEqual(len(coastal),len(set(coastal)))
        self.assertNotIn('shujun',coastal)
        self.assertNotIn('hanzhong',coastal)
        self.assertTrue(set(coastal)<=set(catalog.map_cities))
        known={frozenset((r['from'],r['to'])) for r in data['sea_routes']}
        unknown={frozenset((r['from'],r['to'])) for r in data['exploration_routes']}
        self.assertFalse(known & unknown)
        self.assertEqual(len(known|unknown),18*17//2)
        self.assertIn(frozenset(('zhuya','yizhou')),unknown)
        self.assertNotIn(frozenset(('zhuya','yizhou')),known)
        ids=[]
        for key,rows in (('known',data['sea_routes']),('unknown',data['exploration_routes'])):
            for row in rows:
                ids.append(row['id'])
                self.assertTrue({row['from'],row['to']}<=set(coastal))
                self.assertEqual(row['discovery_candidate'],key=='unknown')
        self.assertEqual(len(ids),len(set(ids)))
        game=self.game()
        self.assertIsNone(game._exploration_route('shujun','yizhou'))
        self.assertIsNone(game._exploration_route('yizhou','yizhou'))
        self.assertIsNotNone(game._exploration_route('zhuya','yizhou'))
        self.assertEqual(game.state.extension['travel']['discovered'],[])

    def test_every_sea_chart_has_land_sea_land_geometry_at_actual_castles(self):
        for catalog in self.catalogs.values():
            data=catalog.data
            for row in data['sea_routes']+data['exploration_routes']:
                parts=row['draw']
                self.assertEqual([p['mode'] for p in parts],['land','sea','land'])
                self.assertEqual(parts[0]['points'][0],catalog.map_cities[row['from']]['position'])
                self.assertEqual(parts[-1]['points'][-1],catalog.map_cities[row['to']]['position'])
                self.assertEqual(parts[0]['points'][-1],parts[1]['points'][0])
                self.assertEqual(parts[1]['points'][-1],parts[2]['points'][0])
                self.assertGreater(row['sea_km'],0)
                self.assertGreaterEqual(row['land_km'],0)
                self.assertAlmostEqual(row['distance_km'],row['sea_km']+row['land_km'],places=1)
                for part in parts:
                    self.assertGreaterEqual(len(part['points']),2)
                    for x,y in part['points']:
                        self.assertGreaterEqual(x,0);self.assertLessEqual(x,data['world']['width'])
                        self.assertGreaterEqual(y,0);self.assertLessEqual(y,data['world']['height'])

    def test_future_linhai_never_appears_in_discovery_quotes_before_its_month(self):
        game=self.game(249,'wu')
        self.assertNotIn('linhai',game.state.cities)
        self.assertIsNone(game._travel_path(game.state,'kuaiji','linhai','wu','explore'))
        self.assertIsNone(game._travel_path(game.state,'linhai','yizhou','wu','explore',adjacent=True))
        before=game.export_save()
        quotes=game.view()['catalog']['travel_quotes']
        self.assertFalse(any('linhai' in q['path'] for q in quotes.values()))
        self.assertEqual(game.export_save(),before)
        self.assertFalse(any(r['id'] in game.state.extension['travel']['discovered']
                             for r in game.catalog.data['exploration_routes'] if 'linhai' in (r['from'],r['to'])))

    def test_faction_resources_read_opening_or_live_cities_without_rng_or_state_changes(self):
        session=CampaignSession([catalog_path for catalog_path in
            (ROOT/'game/data'/path for path in self.index['catalogs'])])
        before=session.to_dict();revision=session.revision
        for year,catalog in self.catalogs.items():
            expected={side:dict(gold=0,grain=0,reserves=0,cities=0) for side in catalog.factions}
            for key,owner in catalog.data['initial_owners'].items():
                if owner not in expected:continue
                expected[owner]['cities']+=1
                values=catalog.data['initial_city_resources'][key]
                for field in ('gold','grain','reserves'):expected[owner][field]+=values[field]
            self.assertEqual(faction_resources(catalog),expected)
        preview=session.view()
        for row in preview['catalog']['scenarios']:
            self.assertEqual(row['faction_resources'],faction_resources(session.catalogs[row['id']]))
        self.assertEqual(session.to_dict(),before);self.assertEqual(session.revision,revision)
        session.command('new',dict(scenario='mainland217-07-v11',faction='wu',seed=2026),session.revision)
        game=session.game;state=game.state
        # Controlled capture/resource fixture proves this is actual live control,
        # not a restatement of static scenario holdings.
        city=state.cities['yizhou'];self.assertEqual(city.roster.officer_ids,[])
        city.owner='wu';city.gold+=125;city.grain+=777;city.reserves+=111
        state.soldiers['recruited']+=111;game.validate(state)
        expected={side:dict(gold=0,grain=0,reserves=0,cities=0) for side in game.catalog.factions}
        for c in state.cities.values():
            if c.owner not in expected:continue
            expected[c.owner]['cities']+=1
            for field in ('gold','grain','reserves'):expected[c.owner][field]+=getattr(c,field)
        saved=session.export_save();rng=deepcopy(state.rng)
        self.assertEqual(session.view()['catalog']['faction_resources'],expected)
        self.assertEqual(session.view()['catalog']['faction_resources'],expected)
        session.preview_city('mainland217-07-v11','wujun')
        self.assertEqual(session.export_save(),saved);self.assertEqual(state.rng,rng)
        self.assertNotEqual(expected['wu'],faction_resources(game.catalog)['wu'])

    def test_rebuild_keeps_old107_files_and_v10_saves_with111_loaded_catalogs(self):
        # This is the released v11 namespace. Newer optional generations have
        # their own preservation tests and must not alter this111-catalog gate.
        paths=[p for p in (ROOT/'game/data').rglob('*.json')
               if not (p.parent.name.startswith('main-scenarios-v') and
                       int(p.parent.name.rsplit('v',1)[1])>11)]
        prior=[p for p in paths if p.parent.name!='main-scenarios-v11']
        self.assertEqual(len(prior),107)
        hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        subprocess.run([sys.executable,'-B','game/build_hazard_campaigns.py'],cwd=ROOT,
                       check=True,capture_output=True)
        self.assertEqual(hashes,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        catalogs=sorted((p for p in paths if p.name!='index.json'),
            key=lambda p:(p.parent.name=='main-scenarios-v11',p.name=='217-07.json',str(p)))
        self.assertEqual(len(catalogs),111)
        session=CampaignSession(catalogs)
        options=session.view()['catalog']['scenarios']
        self.assertEqual(len(options),111)
        self.assertEqual(sum(not row['archived'] for row in options),13)
        self.assertTrue(all(row['id'].endswith('-v11') for row in options if not row['archived']))
        session.command('new',dict(scenario='mainland217-07-v10',faction='shu',seed=2026),0)
        saved=session.export_save();before=session.to_dict()
        self.assertEqual(set(before['extension']['travel']),{'counter','marches','battle_arrival'})
        session.load_save(saved,session.revision)
        self.assertEqual(session.export_save(),saved)
        self.assertEqual(session.to_dict(),before)
        self.assertNotIn('travel_hazards',session.game.catalog.data)
        self.assertEqual(len(session.game.state.cities),110)


if __name__=='__main__':unittest.main()
