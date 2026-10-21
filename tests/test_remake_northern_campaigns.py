"""Dated city domains, saved campaigns and northern chapter ownership."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog,digest
from remake.map_presentation import city_names
from remake.session import CampaignSession


class NorthernCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index=json.loads((ROOT/'game/data/main-scenarios-v8/index.json').read_text())
        cls.catalogs={}
        for path in cls.index['catalogs']:
            c=Catalog(ROOT/'game/data'/path);cls.catalogs[c.data['start_year']]=c

    def game(self,year=217,side='wei'):
        g=Campaign(self.catalogs[year]);g.command('new',dict(faction=side,seed=2026),0);return g

    def test_all102_starts_have_correct_domains_owners_and_no_duplicate_people(self):
        starts=0
        for year,c in self.catalogs.items():
            prior=Catalog(ROOT/('game/data/main-scenarios-v7/'+next(p.rsplit('/',1)[-1] for p in self.index['catalogs'] if f'/{year}-' in p)))
            self.assertEqual(len(c.map_cities),106)
            self.assertLess(c.map_cities['julu']['position'][1],c.map_cities['zhao']['position'][1])
            self.assertLess(c.map_cities['yanmen']['position'][1],c.map_cities['xinxing']['position'][1])
            self.assertLess(c.map_cities['xinxing']['position'][1],c.map_cities['taiyuan']['position'][1])
            self.assertEqual(c.data['people'],prior.data['people'])
            for key in prior.map_cities:self.assertEqual(c.map_cities[key],prior.map_cities[key])
            north='han' if year==184 else 'han_fu' if year==190 else 'yuan_shao' if year<=200 else 'wei'
            for key in ('zhao','julu','hejian','qinghe'):self.assertEqual(c.data['initial_owners'][key],north)
            expected_yan='han' if year==184 else 'neutral' if year in (190,191) else 'yuan_shao' if year<=200 else 'wei'
            self.assertEqual(c.data['initial_owners']['yanmen'],expected_yan)
            self.assertEqual(len(c.data['active_cities']),105 if year<215 else 106)
            self.assertEqual('xinxing' in c.data['active_cities'],year>=215)
            self.assertEqual({r['person_id'] for r in c.data['initial_officers']},{r['person_id'] for r in prior.data['initial_officers']})
            self.assertEqual(sum(r['troops'] for r in c.data['initial_officers']),sum(r['troops'] for r in prior.data['initial_officers']))
            for row in c.data['initial_officers']:
                self.assertEqual(c.data['initial_owners'][row['city']],prior.data['initial_owners'][next(r['city'] for r in prior.data['initial_officers'] if r['person_id']==row['person_id'])])
            for side in c.factions:
                g=Campaign(c);g.command('new',dict(faction=side,seed=2026),0);g.validate(g.state);starts+=1
        self.assertEqual(starts,102)

    def test_names_and_yanmen_independent_status_do_not_leak_into_old_catalogs(self):
        c=self.catalogs[217]
        for year,name in ((212,'赵国'),(213,'赵郡'),(231,'赵郡'),(232,'赵国')):
            self.assertEqual(city_names(c,year)['zhao'],name)
        for year,name in ((184,'甘陵'),(221,'甘陵'),(222,'清河'),(238,'清河')):
            self.assertEqual(city_names(c,year)['qinghe'],name)
        session=CampaignSession([ROOT/'game/data/main-scenarios-v8/190-01.json'])
        preview=session.preview_city('mainland190-01-v8','yanmen')
        self.assertEqual(preview['city']['owner'],'neutral')
        self.assertEqual(preview['city']['owner_name'],'地方汉郡（中立）')
        with self.assertRaises(ValueError):session.preview_city('mainland190-01-v8','xinxing')
        g=self.game(227)
        qian=next(i for i,p in g.catalog.by_id.items() if p['name']=='牵招')
        self.assertIn(qian,g.state.cities['yanmen'].roster.officer_ids)

    def test_unfounded_city_is_not_a_route_target_or_ai_neighbor(self):
        g=self.game(207);before=g.to_dict();rev=g.revision
        source=g.state.cities['taiyuan'];ident=source.roster.officer_ids[0]
        with self.assertRaises(ValueError):g.command('depart',dict(source=source.id,target='xinxing',officers=[ident]),rev)
        self.assertEqual(g.to_dict(),before);self.assertEqual(g.revision,rev)
        self.assertFalse(any('xinxing' in k for k in g.view()['catalog']['travel_quotes']))
        donor=g.state.cities['yanmen'];who=donor.roster.officer_ids[0]
        g.command('transfer',dict(source='yanmen',target='taiyuan',officers=[who]),g.revision)
        bad=g.export_save();row=bad['state']['extension']['travel']['marches'][0]
        path=['yanmen','xinxing','taiyuan']
        legs=[next(r for r in g.catalog.data['travel_routes'] if {r['from'],r['to']}=={a,b}) for a,b in zip(path,path[1:])]
        days=sum(r['days'] for r in legs)
        row['quote']=dict(path=path,routes=legs,days=days,months=(days+29)//30,
            distance_km=round(sum(r['distance_km'] for r in legs),1),grain_per_officer=10,modes=['land'])
        row['arrival_turn']=row['departure_turn']+row['quote']['months']
        bad['checksum']=digest({k:v for k,v in bad.items() if k!='checksum'})
        snapshot=g.to_dict()
        with self.assertRaises(ValueError):g.load_save(bad,g.revision)
        self.assertEqual(g.to_dict(),snapshot)
        g.command('end_turn',{},g.revision);g.command('ai',dict(turn=g.state.turn),g.revision)
        g.validate(g.state)
        self.assertFalse(any('xinxing' in row['quote']['path'] for row in g.state.extension['travel']['marches']))

    def test_long_calendar_foundation_inherits_actual_owner_and_conserves_resources(self):
        # Controlled calendar fixture isolates the215 boundary from conquest AI.
        g=self.game(200,'wu')
        while (g.state.year,g.state.month)<(214,12):
            g._complete_month(g.state);g._spawn_eligible(g.state);g._reconcile_factions(g.state)
        parent=g.state.cities['taiyuan']
        # Model a prior conquest using an empty donor, not a historical override.
        for ident in list(parent.roster.officer_ids):
            target=next(c for c in g.state.cities.values() if c.owner==parent.owner and c.id!=parent.id and len(c.roster.officer_ids)<30)
            parent.roster.officer_ids.remove(ident);target.roster.officer_ids.append(ident)
        parent.owner='wu';g.validate(g.state)
        before=g.export_save();twin=Campaign(g.catalog);twin.load_save(before,0)
        total=lambda s:sum(c.reserves for c in s.cities.values())+sum(o.troops for o in s.officers.values())
        old_total=total(g.state);old_draws=g.state.rng.draws
        g._complete_month(g.state);g._spawn_eligible(g.state);g._reconcile_factions(g.state)
        twin._complete_month(twin.state);twin._spawn_eligible(twin.state);twin._reconcile_factions(twin.state)
        g.validate(g.state);self.assertEqual(g.to_dict(),twin.to_dict())
        self.assertEqual((g.state.year,g.state.month),(215,1));self.assertEqual(len(g.state.cities),106)
        self.assertEqual(g.state.cities['xinxing'].owner,'wu');self.assertEqual(g.state.rng.draws,old_draws)
        # The new reserve pool came from晋阳; only regular monthly income adds troops.
        recruited=g.state.soldiers['recruited']-before['state']['soldiers']['recruited']
        self.assertEqual(total(g.state),old_total+recruited)
        snapshot=g.to_dict();g._open_dated_cities(g.state);self.assertEqual(g.to_dict(),snapshot)
        loaded=Campaign(g.catalog);loaded.load_save(g.export_save(),0);self.assertEqual(loaded.to_dict(),snapshot)
        bad=g.export_save();del bad['state']['cities']['xinxing']
        bad['checksum']=digest({k:v for k,v in bad.items() if k!='checksum'})
        with self.assertRaises(ValueError):loaded.load_save(bad,loaded.revision)
        self.assertEqual(loaded.to_dict(),snapshot)

    def test_rebuild_does_not_change_any_released_catalog_and_old_saves_load(self):
        files=list((ROOT/'game/data').rglob('*.json'))
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        subprocess.run([sys.executable,'-B','game/build_northern_campaigns.py'],cwd=ROOT,check=True,capture_output=True)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
        session=CampaignSession([ROOT/'game/data/main-scenarios-v7/217-07.json',ROOT/'game/data/main-scenarios-v8/217-07.json'])
        session.command('new',dict(scenario='mainland217-07-v7',faction='shu',seed=2026),0)
        saved=session.export_save();session.load_save(saved,session.revision)
        self.assertEqual(session.export_save(),saved);self.assertEqual(len(session.game.state.cities),100)


if __name__=='__main__':unittest.main()
