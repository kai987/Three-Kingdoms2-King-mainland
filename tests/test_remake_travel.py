"""Delayed arrivals, geographic routing, interrupted campaigns and old saves."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog,digest
from remake.errors import GameError
from remake.travel import build_routes,kilometers


class TravelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=Catalog(ROOT/'game/data/main-scenarios-v7/217-07.json')

    def game(self,faction='shu'):
        g=Campaign(self.catalog);g.command('new',dict(faction=faction,seed=2026),0)
        return g

    def cmd(self,g,kind,**payload):
        return g.command(kind,payload,g.revision)

    def month(self,g):
        # Isolate travel/calendar from AI purchases. Natural AI is exercised
        # separately, so deterministic arrival tests can inspect exact fees.
        g._complete_month(g.state);g.validate(g.state)

    def finish_arrivals(self,g):
        for _ in range(50):
            if g.state.phase=='arrivals':self.cmd(g,'arrivals')
            elif g.state.phase=='battle':self.cmd(g,'retreat',battle_id=g.state.battle['id'])
            elif g.state.phase=='result':self.cmd(g,'settle',battle_id=g.state.battle['id'])
            else:return
        self.fail('arrival queue did not drain')

    def test_all102_new_starts_have100_cities_only_wuwei_moves_people_unchanged(self):
        index=json.loads((ROOT/'game/data/main-scenarios-v7/index.json').read_text());count=0
        for path in index['catalogs']:
            c=Catalog(ROOT/'game/data'/path)
            old=Catalog(ROOT/'game/data'/path.replace('-v7/','-v6/'))
            self.assertEqual(len(c.map_cities),100)
            self.assertEqual(c.data['world'],dict(x=0,y=0,width=1352,height=1024,background='/assets/map-campaign.png'))
            for key in old.map_cities:
                if key!='wuwei':self.assertEqual(c.map_cities[key],old.map_cities[key])
            self.assertEqual(c.map_cities['wuwei']['position'],[200,182])
            self.assertEqual(c.data['initial_officers'],old.data['initial_officers'])
            self.assertEqual(c.data['people'],old.data['people'])
            for faction in c.factions:
                g=Campaign(c);self.cmd(g,'new',faction=faction,seed=2026)
                g.validate(g.state);count+=1
        self.assertEqual(count,102)

    def test_rebuild_keeps_all_released_catalogs_byte_identical(self):
        files=list((ROOT/'game/data').rglob('*.json'))
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        subprocess.run([sys.executable,'-B','game/build_travel_campaigns.py'],cwd=ROOT,check=True,capture_output=True)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files})

    def test_geography_ignores_screen_scaling_and_has_distinct_land_sea_choices(self):
        spec=json.loads((ROOT/'game/config/travel-map.json').read_text())
        data=deepcopy(self.catalog.data)
        for c in data['cities']:c['position']=[-999,999]
        self.assertEqual(build_routes(data,spec),self.catalog.data['travel_routes'])
        self.assertGreater(kilometers([98.5,39.74],[94.66,40.14]),300)
        sea_only=[r for r in data['travel_routes'] if {r['from'],r['to']}=={'kuaiji','nanhai'}]
        self.assertEqual([r['mode'] for r in sea_only],['sea'])
        self.assertEqual({r['mode'] for r in data['travel_routes'] if {r['from'],r['to']}=={'nanhai','gaoliang'}},{'land','sea'})
        self.assertEqual({r['terrain'] for r in data['travel_routes'] if {r['from'],r['to']}=={'jiuquan','dunhuang'}},{'desert'})

    def test_solid_port_roads_join_the_two_ends_of_each_sea_lane(self):
        spec=json.loads((ROOT/'game/config/travel-map.json').read_text())
        positions=json.loads((ROOT/'game/assets/city-positions.json').read_text())['positions']
        for row in (r for r in spec['connections'] if r['mode']=='sea'):
            land,sea,landing=row['draw']
            self.assertEqual([land['mode'],sea['mode'],landing['mode']],['land','sea','land'])
            self.assertEqual(land['points'][0],positions[row['from']])
            self.assertEqual(landing['points'][-1],positions[row['to']])
            self.assertEqual(land['points'][-1],sea['points'][0])
            self.assertEqual(landing['points'][0],sea['points'][-1])

    def test_attack_waits_and_cannot_be_issued_or_allocated_twice(self):
        g=self.game();city=g.state.cities['shujun'];ident=city.roster.officer_ids[0]
        before=city.grain;cost=max(1,g.state.officers[ident].troops//25)
        self.cmd(g,'depart',source=city.id,target='yinping',officers=[ident])
        self.assertEqual(g.state.phase,'city');self.assertIsNone(g.state.battle)
        self.assertEqual(g.state.cities[city.id].grain,before-cost)
        original=g.to_dict()
        with self.assertRaises(GameError):self.cmd(g,'allocate',city=city.id,officer=ident,troops=1)
        with self.assertRaises(GameError):self.cmd(g,'depart',source=city.id,target='yinping',officers=[ident])
        self.assertEqual(g.to_dict(),original)
        self.month(g);self.assertEqual(g.state.phase,'arrivals')
        before_arrival=g.state.cities[city.id].grain
        self.cmd(g,'arrivals');self.assertEqual(g.state.phase,'result')
        self.assertEqual(g.state.cities[city.id].grain,before_arrival)
        battle=g.state.battle['id'];self.cmd(g,'settle',battle_id=battle)
        settled=g.to_dict();self.cmd(g,'settle',battle_id=battle)
        self.assertEqual(g.to_dict(),settled)
        self.finish_arrivals(g);self.assertEqual(g.state.cities['yinping'].owner,'shu')

    def test_long_coastal_transfer_crosses_months_and_survives_save_reload(self):
        g=self.game('wu');source=g.state.cities['kuaiji'];target=g.state.cities['jiaozhi']
        # The dated southern governor is a separate faction. A controlled allied
        # city fixture exercises friendly sea transport without inventing history.
        for key in ['nanhai','gaoliang','hepu','jiaozhi']:
            for i in g.state.cities[key].roster.officer_ids:
                g.state.officers[i].faction_id='wu'
            g.state.cities[key].owner='wu'
        g._reconcile_factions(g.state)
        ident=source.roster.officer_ids[0]
        self.cmd(g,'transfer',source=source.id,target=target.id,officers=[ident])
        row=g.state.extension['travel']['marches'][0]
        self.assertGreater(row['quote']['months'],1)
        self.assertIn('sea',row['quote']['modes'])
        arrival=row['arrival_turn']
        while g.state.turn<arrival:
            self.month(g)
            if g.state.turn<arrival:self.assertIn(ident,g.state.cities[source.id].roster.officer_ids)
            saved=g.export_save();before=g.to_dict();g.load_save(saved,g.revision);self.assertEqual(before,g.to_dict())
        self.cmd(g,'arrivals');self.assertIn(ident,g.state.cities[target.id].roster.officer_ids)
        self.assertNotIn(ident,g.state.cities[source.id].roster.officer_ids)
        self.assertFalse(g.state.extension['travel']['marches'])

    def test_no_land_route_over_the_sea_and_invalid_orders_are_atomic(self):
        g=self.game('wu');city=g.state.cities['kuaiji'];ident=city.roster.officer_ids[0]
        before=g.to_dict()
        with self.assertRaises(GameError):self.cmd(g,'depart',source='kuaiji',target='yizhou',officers=[ident],route_mode='land')
        self.assertEqual(g.to_dict(),before)

    def test_new_enemy_ownership_cancels_transfer(self):
        g=self.game();source=g.state.cities['shujun'];target=g.state.cities['yinping'];target.owner='shu'
        ids=list(source.roster.officer_ids[:2])
        self.cmd(g,'transfer',source=source.id,target=target.id,officers=ids)
        self.month(g)
        # Reassign the formerly empty target; no officer identity is changed.
        target=g.state.cities['yinping'];target.owner='neutral'
        self.cmd(g,'arrivals')
        self.assertFalse(g.state.extension['travel']['marches'])
        self.assertTrue(set(ids)<=set(g.state.cities['shujun'].roster.officer_ids))
        self.assertTrue(any('目的城已易主' in t for t in g.state.log))

    def test_marching_force_does_not_defend_and_source_capture_cancels_its_order(self):
        g=self.game();g.state.cities['yinping'].owner='wei'
        source=g.state.cities['shujun'];ident=source.roster.officer_ids[0]
        self.cmd(g,'transfer',source=source.id,target='yunnan',officers=[ident])
        # Wei's staged column departs Hanzhong; the direct adjacent approach
        # is used to trigger an actual attack on Chengdu's reserved force.
        enemy=g.state.cities['guanghan']
        for i in list(enemy.roster.officer_ids):
            g.state.cities['baxi'].roster.officer_ids.append(i)
        enemy.roster.officer_ids.clear();enemy.owner='wei'
        origin=g.state.cities['hanzhong'];e=origin.roster.officer_ids[0]
        origin.roster.officer_ids.remove(e);enemy.roster.officer_ids.append(e)
        g._queue_march(g.state,enemy,source,[e],'attack')
        # Process the shorter Guanghan approach first.
        self.month(g);self.cmd(g,'arrivals')
        self.assertEqual(g.state.battle['attacker'],'wei')
        self.assertNotIn(ident,[u['id'] for u in g.state.battle['defenders']])
        self.finish_arrivals(g);g.validate(g.state)
        self.assertEqual(g.state.cities['shujun'].owner,'wei')
        self.assertFalse(g.state.extension['travel']['marches'])
        self.assertTrue(any('出发城失陷' in text for text in g.state.log))

    def test_full_destination_waits_then_admits_once_space_is_available(self):
        g=self.game();source=g.state.cities['shujun'];target=g.state.cities['yinping'];target.owner='shu'
        ident=source.roster.officer_ids[0]
        self.cmd(g,'transfer',source=source.id,target=target.id,officers=[ident])
        target=g.state.cities['yinping']
        for city in g.state.cities.values():
            if city.owner!='shu' or city.id in {source.id,target.id}:continue
            for i in list(city.roster.officer_ids):
                if len(target.roster.officer_ids)==30:break
                city.roster.officer_ids.remove(i);target.roster.officer_ids.append(i)
        self.month(g);self.cmd(g,'arrivals')
        self.assertEqual(g.state.phase,'city');self.assertEqual(len(g.state.extension['travel']['marches']),1)
        target=g.state.cities['yinping'];i=target.roster.officer_ids.pop()
        g.state.cities['shujun'].roster.officer_ids.append(i)
        self.month(g);self.cmd(g,'arrivals')
        self.assertIn(ident,g.state.cities['yinping'].roster.officer_ids)
        self.assertFalse(g.state.extension['travel']['marches']);g.validate(g.state)

    def test_tampered_arrival_and_duplicate_force_saves_are_rejected(self):
        g=self.game();ident=g.state.cities['shujun'].roster.officer_ids[0]
        self.cmd(g,'depart',source='shujun',target='yinping',officers=[ident])
        before=g.to_dict()
        for change in ('eta','duplicate'):
            save=g.export_save();marches=save['state']['extension']['travel']['marches']
            if change=='eta':marches[0]['arrival_turn']+=1
            else:marches.append(deepcopy(marches[0]))
            save['checksum']=digest({k:v for k,v in save.items() if k!='checksum'})
            with self.assertRaises(GameError):g.load_save(save,g.revision)
            self.assertEqual(g.to_dict(),before)

    def test_natural_ai_continuation_keeps_months_receipts_and_soldiers_consistent(self):
        g=self.game()
        for _ in range(15):
            if g.state.phase=='finished':break
            self.finish_arrivals(g)
            if g.state.phase=='finished':break
            self.cmd(g,'end_turn');self.cmd(g,'ai',turn=g.state.turn)
            self.finish_arrivals(g)
            g.validate(g.state)
        self.assertGreaterEqual(g.state.turn,12)
        self.assertGreater(g.state.extension['travel']['counter'],0)
        self.assertEqual(g.state.completed_ai_turns,list(range(1,g.state.turn)))


if __name__=='__main__':unittest.main()
