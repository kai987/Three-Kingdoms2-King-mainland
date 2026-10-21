"""Dated southern map expansion, same people, routes and saved-campaign guards."""
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
from remake.campaign import Campaign,Catalog,digest
from remake.map_presentation import city_names
from remake.session import CampaignSession


class SouthernCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index=json.loads((ROOT/'game/data/main-scenarios-v10/index.json').read_text())
        cls.spec=json.loads((ROOT/'game/config/shu-wu-expansion.json').read_text())
        cls.catalogs={}
        cls.prior={}
        for path in cls.index['catalogs']:
            catalog=Catalog(ROOT/'game/data'/path)
            year=catalog.data['start_year'];cls.catalogs[year]=catalog
            cls.prior[year]=Catalog(ROOT/'game/data'/path.replace('-v10/','-v9/'))

    def start(self,year=217,side='wei'):
        game=Campaign(self.catalogs[year])
        game.command('new',dict(faction=side,seed=2026),0)
        return game

    def test_all117_faction_starts_keep_original_map_people_and_armies(self):
        starts=0
        for year,catalog in self.catalogs.items():
            data=catalog.data;prior=self.prior[year].data
            self.assertEqual(len(catalog.map_cities),115)
            self.assertEqual(data['world'],prior['world'])
            for row in prior['cities']:
                self.assertEqual(catalog.map_cities[row['id']],row)
            self.assertTrue(set(map(frozenset,prior['links']))<=catalog.links)
            self.assertEqual(data['people'],prior['people'])
            self.assertEqual(data['initial_free_officers'],prior['initial_free_officers'])
            self.assertEqual({r['person_id']:r['troops'] for r in data['initial_officers']},
                             {r['person_id']:r['troops'] for r in prior['initial_officers']})
            self.assertEqual({r['person_id']:data['initial_owners'][r['city']] for r in data['initial_officers']},
                             {r['person_id']:prior['initial_owners'][r['city']] for r in prior['initial_officers']})
            expected=109 if year<215 else 110 if year<221 else 111
            self.assertEqual(len(catalog.active_city_ids(year,data['start_month'])),expected)
            for side in catalog.factions:
                game=Campaign(catalog)
                game.command('new',dict(faction=side,seed=2026),0)
                game.validate(game.state);starts+=1
                self.assertEqual(len(game.state.cities),expected)
                self.assertTrue(all(len(city.roster.officer_ids)<=30 for city in game.state.cities.values()))
        self.assertEqual(starts,117)

    def test_existing_shu_counties_have_independent_era_ownership_and_names(self):
        keys=('jiameng','fuxian','dangqu','nanguang')
        for year,catalog in self.catalogs.items():
            expected='neutral' if year==184 else 'liu_yan' if year in (190,191) else 'liu_zhang' if year<=208 else 'shu'
            for key in keys:
                self.assertIn(key,catalog.data['active_cities'])
                self.assertEqual(catalog.data['initial_owners'][key],expected)
                self.assertNotIn(key,catalog.data['city_foundings'])
                self.assertEqual(catalog.data['city_history'][key]['kind'],'county_military_town')
            self.assertEqual(city_names(catalog,year)['jiameng'],'葭萌' if year<215 else '汉寿')
        # Administrative commandery abolition must not erase the persistent town.
        catalog=self.catalogs[217]
        for year in (218,230,238,262,267):
            self.assertTrue(set(keys)<=set(catalog.active_city_ids(year,12)))

    def test_wuchang_opening_seat_and_city_economy_are_chapter_specific(self):
        for year in (221,227):
            catalog=self.catalogs[year];data=catalog.data
            self.assertEqual(data['initial_owners']['wuchang'],'wu')
            self.assertEqual(catalog.factions['wu']['city'],'wuchang')
            ruler=data['faction_rulers']['wu']
            person=catalog.by_id[ruler]['person_id']
            row=next(r for r in data['initial_officers'] if r['person_id']==person)
            self.assertTrue(row['ruler']);self.assertEqual(row['city'],'wuchang')
            self.assertEqual(data['city_profiles']['wuchang']['tier'],'large')
            for field in ('gold','grain','reserves'):
                self.assertGreater(data['initial_city_resources']['wuchang'][field],
                                   data['initial_city_resources']['fuxian'][field])
                self.assertGreater(data['city_income']['wuchang'][field],
                                   data['city_income']['fuxian'][field])
        for year in (238,249):
            self.assertEqual(self.catalogs[year].factions['wu']['city'],'danyang')

    def test_late_wu_openings_have_exact_game_dates_and_annotated_precision(self):
        catalog=self.catalogs[217]
        for date,count in (((184,2),109),((214,12),109),((215,1),110),
                           ((221,3),110),((221,4),111),((257,1),111),
                           ((257,2),113),((260,9),113),((260,10),114),
                           ((266,11),114),((266,12),115)):
            self.assertEqual(len(catalog.active_city_ids(*date)),count)
        expected={'wuchang':(221,4),'linhai':(257,2),'linchuan':(257,2),
                  'jianan':(260,10),'wuxing':(266,12)}
        for key,date in expected.items():
            rule=catalog.data['city_foundings'][key]
            self.assertEqual((rule['year'],rule['month']),date)
        for key in ('jianan','wuxing'):
            self.assertNotEqual(catalog.data['city_foundings'][key]['precision'],'attested_annal_month')
            self.assertTrue(catalog.data['city_foundings'][key]['date_note'])

    def test_unopened_cities_cannot_be_targets_or_route_intermediates(self):
        game=self.start(249,'wu')
        closed={'linhai','linchuan','jianan','wuxing'}
        self.assertFalse(closed.intersection(game.state.cities))
        self.assertTrue(any(r['to'] in closed or r['from'] in closed
                            for r in game.catalog.data['travel_routes']))
        quotes=game.view()['catalog']['travel_quotes']
        self.assertTrue(all(not closed.intersection(q['path']) for q in quotes.values()))
        source=next(c for c in game.state.cities.values() if c.owner=='wu' and c.roster.officer_ids)
        ident=source.roster.officer_ids[0]
        for kind in ('transfer','depart'):
            before=game.to_dict();revision=game.revision
            with self.assertRaises(ValueError):
                game.command(kind,dict(source=source.id,target='linhai',officers=[ident]),revision)
            self.assertEqual(game.to_dict(),before);self.assertEqual(game.revision,revision)
        game.command('end_turn',{},game.revision)
        game.command('ai',dict(turn=game.state.turn),game.revision)
        game.validate(game.state)
        self.assertTrue(all(not closed.intersection(row['quote']['path'])
                            for row in game.state.extension['travel']['marches']))

    def test_actual_opening_dates_inherit_enemy_parent_and_conserve_resources(self):
        # Calendar-only fixtures exclude conquest AI. They verify monthly event
        # services and actual-owner inheritance, not natural decades of play.
        cases=((217,(221,4),('wuchang',)),
               (249,(257,2),('linhai','linchuan')),
               (249,(260,10),('jianan',)),
               (249,(266,12),('wuxing',)))
        for start,date,keys in cases:
            with self.subTest(date=date):
                game=self.start(start,'wei')
                previous=(date[0],date[1]-1)
                while (game.state.year,game.state.month)<previous:
                    game._complete_month(game.state)
                    game._spawn_eligible(game.state);game._reconcile_factions(game.state)
                self.assertEqual((game.state.year,game.state.month),previous)
                pairs={key:game.catalog.data['city_foundings'][key]['parent'] for key in keys}
                for parent_id in pairs.values():
                    parent=game.state.cities[parent_id]
                    for ident in list(parent.roster.officer_ids):
                        recipient=next(c for c in game.state.cities.values() if c.owner==parent.owner
                            and c.id!=parent.id and len(c.roster.officer_ids)<30)
                        parent.roster.officer_ids.remove(ident);recipient.roster.officer_ids.append(ident)
                    parent.owner='wei'  # Controlled prior conquest, not a historical override.
                game.validate(game.state)
                self.assertFalse(set(keys).intersection(game.state.cities))
                before=game.export_save()
                resources={p:{field:getattr(game.state.cities[p],field) for field in ('gold','grain','reserves')}
                           for p in pairs.values()}
                old_soldiers=sum(c.reserves for c in game.state.cities.values())+sum(o.troops for o in game.state.officers.values())
                old_draws=game.state.rng.draws
                game._complete_month(game.state)
                game._spawn_eligible(game.state);game._reconcile_factions(game.state)
                game.validate(game.state)
                self.assertEqual((game.state.year,game.state.month),date)
                self.assertEqual(game.state.rng.draws,old_draws)
                for key,parent_id in pairs.items():
                    child=game.state.cities[key];parent=game.state.cities[parent_id]
                    self.assertEqual(child.owner,'wei')
                    self.assertEqual(child.roster.officer_ids,[])
                    for field in ('gold','grain','reserves'):
                        income=sum(game.catalog.data['city_income'][c][field] for c in (key,parent_id))
                        self.assertEqual(getattr(child,field)+getattr(parent,field),resources[parent_id][field]+income)
                gained=game.state.soldiers['recruited']-before['state']['soldiers']['recruited']
                self.assertEqual(sum(c.reserves for c in game.state.cities.values())+
                                 sum(o.troops for o in game.state.officers.values()),old_soldiers+gained)
                snapshot=game.to_dict();game._open_dated_cities(game.state)
                self.assertEqual(game.to_dict(),snapshot)
                loaded=Campaign(game.catalog);loaded.load_save(game.export_save(),0)
                self.assertEqual(loaded.to_dict(),snapshot)
                early=deepcopy(before)
                for key in keys:early['state']['cities'][key]=deepcopy(snapshot['cities'][key])
                early['checksum']=digest({k:v for k,v in early.items() if k!='checksum'})
                with self.assertRaises(ValueError):loaded.load_save(early,loaded.revision)
                self.assertEqual(loaded.to_dict(),snapshot)

    def test_rebuild_preserves_all_catalogs_and_v9_save_is_not_migrated(self):
        paths=list((ROOT/'game/data').rglob('*.json'))
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        subprocess.run([sys.executable,'-B','game/build_southern_campaigns.py'],cwd=ROOT,
                       check=True,capture_output=True)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        session=CampaignSession([ROOT/'game/data/main-scenarios-v9/217-07.json',
                                 ROOT/'game/data/main-scenarios-v10/217-07.json'])
        session.command('new',dict(scenario='mainland217-07-v9',faction='shu',seed=2026),0)
        save=session.export_save();session.load_save(save,session.revision)
        self.assertEqual(session.export_save(),save)
        self.assertEqual(len(session.game.state.cities),106)
        self.assertFalse({'jiameng','fuxian','dangqu','nanguang'}.intersection(session.game.state.cities))


if __name__=='__main__':unittest.main()
