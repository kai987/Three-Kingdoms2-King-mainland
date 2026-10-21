"""Eleven chapter setups and real30-seat boundaries, with frozen old saves."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog,GameError,SeedRng
from remake.officers import CityRoster,GameRules,transfer_officers,select_deployment,virtue_score
from remake.session import CampaignSession


class MainScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index=json.loads((ROOT/'game/data/main-scenarios/index.json').read_text())
        cls.catalogs={Catalog(ROOT/'game/data'/p).data['start_year']:Catalog(ROOT/'game/data'/p) for p in cls.index['catalogs']}

    def game(self,year=217,side='shu'):
        g=Campaign(self.catalogs[year]);g.command('new',{'faction':side,'seed':2026},0);return g

    @staticmethod
    def ident(g,name):return next(i for i,p in g.catalog.by_id.items() if p['name']==name)

    def pack(self,g,city_key,total):
        """Controlled seating fixture: relocate existing friendly adults only."""
        city=g.state.cities[city_key]
        for donor in g.state.cities.values():
            if donor.id==city_key or donor.owner!=city.owner:continue
            for i in list(donor.roster.officer_ids):
                if len(city.roster.officer_ids)>=total:break
                if i in g.state.extension['leaders'].values():continue
                donor.roster.officer_ids.remove(i);city.roster.officer_ids.append(i)
        self.assertEqual(len(city.roster.officer_ids),total)
        g.validate(g.state)

    def test_official_scope_is_exactly7_base_and4_pk_with_correct_months(self):
        expected={184:2,190:1,194:6,200:1,207:9,217:7,227:2,191:10,208:10,219:7,238:1}
        self.assertEqual({y:c.data['start_month'] for y,c in self.catalogs.items()},expected)
        self.assertEqual(Counter(c.data['main_scenario']['group'] for c in self.catalogs.values()),{'base':7,'pk':4})
        for c in self.catalogs.values():
            self.assertEqual(c.rules.city_officer_capacity,30)
            self.assertEqual(c.rules.battle_officers_per_side,10)
            self.assertEqual(len(c.definitions),1000)
            self.assertEqual(len(c.map_cities),96)
            self.assertFalse(c.data['main_scenario']['roster_complete'])
            self.assertTrue(c.data['main_scenario']['official_source'].startswith('https://www.gamecity.'))

    def test_click_anchors_match_the_current96_rendered_castles(self):
        anchors=json.loads((ROOT/'game/assets/city-positions.json').read_text())
        plan=json.loads((ROOT/'expansion/map/city-map-city-sea-plan-v42.json').read_text())
        expected={c['key']:[c['displayArtX']-136,c['displayArtY']] for c in plan['cities']}
        self.assertEqual(anchors['positions'],expected)
        self.assertEqual(anchors['map_sha256'],hashlib.sha256((ROOT/'game/assets/map.png').read_bytes()).hexdigest())
        self.assertEqual(expected['wuwei'],[124,120])
        for c in self.catalogs.values():
            self.assertEqual({p['id']:p['position'] for p in c.data['cities']},expected)
        self.assertEqual(Catalog(ROOT/'game/data/eras-v3/217.json').map_cities['wuwei']['position'],[254,135])

    def test_all102_faction_starts_and28_catalog_saves_roundtrip(self):
        count=0
        for c in self.catalogs.values():
            for side in c.factions:
                g=Campaign(c);g.command('new',{'faction':side,'seed':2026},0);g.validate(g.state)
                self.assertTrue(all(len(city.roster.officer_ids)<=30 for city in g.state.cities.values()))
                self.assertTrue(all(not o.profile.missing for o in g.state.officers.values()))
                count+=1
        self.assertEqual(count,102)
        old=[ROOT/'game/data/demo.json',ROOT/'game/data/mainland.json']+sorted((ROOT/'game/data/eras').glob('[12]*.json'))+sorted((ROOT/'game/data/eras-v3').glob('[12]*.json'))
        paths=old+[ROOT/'game/data'/p for p in self.index['catalogs']]
        session=CampaignSession(paths);self.assertEqual(len(session.catalogs),28)
        for c in session.catalogs.values():
            side=next(iter(c.factions));session.command('new',{'faction':side,'seed':2026,'scenario':c.data['id']},session.revision)
            save=session.export_save();before=session.to_dict();session.load_save(save,session.revision)
            self.assertEqual(before,session.to_dict())
            self.assertEqual(session.game.catalog.rules.city_officer_capacity,30 if c.data.get('content_generation')==4 else 20)

    def test_three_event_boundaries_do_not_use_a_nearby_rulers_date(self):
        g=self.game(208);self.assertNotIn('liu_biao',g.catalog.factions)
        self.assertEqual(g.state.cities['jiangxia'].owner,'shu')
        self.assertEqual(g.state.cities['xiangyang'].owner,'wei')
        self.assertNotEqual(g.state.cities['changsha'].owner,'shu')
        g=self.game(219);self.assertEqual(g.state.cities['hanzhong'].owner,'shu')
        self.assertEqual(g.state.cities['wudu'].owner,'wei')
        self.assertEqual(g.state.cities['yinping'].owner,'wei')
        self.assertEqual(g.state.officers[self.ident(g,'王平')].faction_id,'shu')
        guan=self.ident(g,'关羽');self.assertIn(guan,g.state.cities['nanjun'].roster.officer_ids)
        self.assertTrue(g.catalog.data['era_assignments'][g.state.officers[guan].person_id]['death_year_resolved'])
        g=self.game(238,'gongsun')
        self.assertEqual(g.state.cities['wudu'].owner,'shu')
        self.assertEqual(g.state.cities['yinping'].owner,'shu')
        for n,side in [('曹叡','wei'),('公孙渊','gongsun'),('姜维','shu')]:
            self.assertEqual(g.state.officers[self.ident(g,n)].faction_id,side)
        self.assertNotIn(self.ident(g,'曹芳'),g.state.officers)
        self.assertNotIn(self.ident(g,'公孙恭'),g.state.officers)
        self.assertNotIn(self.ident(g,'诸葛亮'),g.state.officers)

    def test_unknown_membership_never_spawns_and_derived_membership_has_provenance(self):
        for y in (191,208,219,238):
            g=self.game(y,next(iter(self.catalogs[y].factions)))
            for pid,r in g.catalog.data['era_assignments'].items():
                if r['source_status']=='unreviewed':
                    self.assertNotIn(g.catalog.ids[pid],g.state.officers)
                    self.assertNotIn(pid,g.catalog.data['appearance_locations'])
                if r['status']=='serving':
                    self.assertIn(r['membership_resolution']['basis'],('reviewed_transition','chapter_leader_setup','bracketing_affiliation_agreement_inference'))
        design=json.loads((ROOT/'game/config/main-scenario-profile.json').read_text())
        self.assertEqual(virtue_score(design['dimensions']),design['virtue'])
        self.assertFalse(design['is_historical_fact'])

    def test_30th_recruit_accepted_31st_rejected_without_resources_or_rng(self):
        g=self.game();city='shujun';self.pack(g,city,29)
        free=next(i for i,o in g.state.officers.items() if o.faction_id is None)
        g.state.extension['free_locations'][str(free)]=city
        actor=self.ident(g,'刘备');g.state.rng.state=next(s for s in range(1,1000) if SeedRng(s).next()%100<15)
        g.command('recruit_officer',{'city':city,'actor':actor,'officer':free},g.revision)
        self.assertEqual(len(g.state.cities[city].roster.officer_ids),30)
        other=next(i for i,o in g.state.officers.items() if o.faction_id is None)
        g.state.extension['free_locations'][str(other)]=city
        g.state.cities[city].action_used=False;g.state.extension['officer_actions']={}
        before=g.to_dict()
        with self.assertRaisesRegex(GameError,'已满30人'):
            g.command('recruit_officer',{'city':city,'actor':actor,'officer':other},g.revision)
        self.assertEqual(before,g.to_dict())
        save=g.export_save();restored=Campaign(g.catalog);restored.load_save(save,0)
        self.assertEqual(g.to_dict(),restored.to_dict())

    def test_defection_into29_seats_is_attempted_and30_is_atomic_rejection(self):
        for count in (29,30):
            g=self.game();city='nanjun';self.pack(g,city,count)
            c=g.state.cities[city];enemy=g._persuadable(g.state,c)[0];actor=c.roster.officer_ids[0]
            g.state.rng.state=next(s for s in range(1,1000) if SeedRng(s).next()%100<5)
            before=g.to_dict()
            if count==29:
                g.command('persuade_officer',{'city':city,'actor':actor,'officer':enemy},g.revision)
                self.assertEqual(len(g.state.cities[city].roster.officer_ids),30)
            else:
                with self.assertRaisesRegex(GameError,'已满30人'):
                    g.command('persuade_officer',{'city':city,'actor':actor,'officer':enemy},g.revision)
                self.assertEqual(before,g.to_dict())

    def test_transfer_boundary_and_deployment_remain_independent(self):
        rules=GameRules(30,10,1200);a=CityRoster('a',[40,41],rules);b=CityRoster('b',range(29),rules)
        transfer_officers(a,b,[40]);self.assertEqual(len(b.officer_ids),30)
        with self.assertRaises(ValueError):transfer_officers(a,b,[41])
        self.assertEqual(a.officer_ids,[41])
        g=self.game();self.pack(g,'shujun',30);city=g.state.cities['shujun']
        self.assertEqual(len(select_deployment(city.roster,city.roster.officer_ids[:10],g.state.officers)),10)
        with self.assertRaises(ValueError):select_deployment(city.roster,city.roster.officer_ids[:11],g.state.officers)

    def test_ai_can_recruit_into30th_seat(self):
        g=self.game();city='wei';self.pack(g,city,29)
        free=next(i for i,o in g.state.officers.items() if o.faction_id is None)
        g.state.extension['free_locations'][str(free)]=city
        g.command('end_turn',{},g.revision)
        # Controlled queue isolates AI recruiting; use its real command/formula.
        for c in g.state.cities.values():c.action_used=c.id!=city
        g.state.rng.state=next(s for s in range(1,1000) if SeedRng(s).next()%100<15)
        g.command('ai',{'turn':g.state.turn},g.revision)
        self.assertEqual(len(g.state.cities[city].roster.officer_ids),30)
        self.assertEqual(g.state.officers[free].faction_id,'wei')
        self.assertTrue(any(r['city']==city and r['action']=='recruit_officer' for r in g.state.extension['ai_reports']))
        g.validate(g.state)

    def test_retreating_defender_can_use30th_friendly_seat(self):
        g=self.game();self.pack(g,'shujun',29)
        # Controlled battle fixture isolates the settlement branch. Actual units
        # and soldier totals are retained; no fabricated victory claim.
        target=g.state.cities['guanghan'];source=g.state.cities['jingzhao']
        self.assertIn('shujun',g._neighbors(target.id))
        if not target.roster.officer_ids:
            defender=next(c for c in g.state.cities.values() if c.owner=='shu' and c.id not in ('shujun',target.id) and c.roster.officer_ids)
            target.roster.officer_ids.append(defender.roster.officer_ids.pop())
        ident=target.roster.officer_ids[0]
        ids=source.roster.officer_ids[:1]
        if not ids:
            donor=next(c for c in g.state.cities.values() if c.owner=='wei' and c.roster.officer_ids)
            ids=[donor.roster.officer_ids.pop()];source.roster.officer_ids+=ids
        # Isolate one escape route, without corrupting city/officer ownership.
        neighbors=g._neighbors
        g._neighbors=lambda key,state=None:['shujun'] if key==target.id else neighbors(key,state)
        g._start_expanded_battle(g.state,source,target,ids)
        g.state.battle['outcome']='victory';g.state.phase='result'
        g._expanded_settle(g.state,{'battle_id':g.state.battle['id']})
        self.assertIn(ident,g.state.cities['shujun'].roster.officer_ids)
        self.assertEqual(len(g.state.cities['shujun'].roster.officer_ids),30)
        g.validate(g.state)

    def test_rebuild_preserves_old_catalog_bytes_and_is_deterministic(self):
        files=list((ROOT/'game/data').rglob('*.json'))
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        subprocess.run([sys.executable,'-B',str(ROOT/'game/build_main_scenarios.py')],cwd=ROOT,check=True,capture_output=True)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files})


if __name__=='__main__':unittest.main()
