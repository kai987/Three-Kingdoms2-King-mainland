"""Hazard departures, exactly-once arrival losses, exploration and old saves."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog,digest
from remake.errors import GameError
from remake.route_hazards import evaluate_leg


class HazardMarchTests(unittest.TestCase):
    def catalog(self):
        data=json.loads((ROOT/'game/data/main-scenarios-v10/217-07.json').read_text())
        data['id']='hazard-march-fixture'
        data['travel_hazards']=dict(
            yinping=dict(from_='yinping'),
            ziwu=dict(rain_months=[7,8,9]),
            monsoon=dict(southwest_months=[5,6,7,8,9],northeast_months=[10,11,12,1,2,3],
                         storm_loss_percent=[80,90]),
            coastal_cities=['hepu','zhuya','yizhou','nanhai','kuaiji','wujun','jiaozhi'])
        data['travel_hazards']['yinping']={'from':'yinping','to':'shujun','time_multiplier':2,
            'survival_numerator':1,'survival_denominator':3}
        data['travel_routes'].append(dict(id='ziwu-fixture',**{'from':'hanzhong','to':'jingzhao'},
            mode='land',terrain='mountain',distance_km=300,land_km=300,sea_km=0,days=20,special='ziwu'))
        data['links'].append(['hanzhong','jingzhao'])
        data['exploration_routes']=[dict(id='explore:hepu:yizhou',**{'from':'hepu','to':'yizhou'},
            mode='sea',terrain='sea',distance_km=990,land_km=0,sea_km=990,days=17,exploration=True),
            dict(id='explore:zhuya:yizhou',**{'from':'zhuya','to':'yizhou'},mode='sea',terrain='sea',
                 distance_km=1200,land_km=0,sea_km=1200,days=20,exploration=True)]
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        path=Path(directory.name)/'fixture.json';path.write_text(json.dumps(data,ensure_ascii=False))
        return Catalog(path)

    def game(self,side='wu'):
        game=Campaign(self.catalog());game.command('new',dict(faction=side,seed=2026),0)
        return game

    def empty(self,game,key,owner):
        city=game.state.cities[key]
        for ident in list(city.roster.officer_ids):
            destination=next(c for c in game.state.cities.values() if c.id!=key and c.owner==city.owner
                             and len(c.roster.officer_ids)<30)
            destination.roster.officer_ids.append(ident)
        city.roster.officer_ids.clear();city.owner=owner
        game.validate(game.state)
        return city

    def set_troops(self,game,ids,amount):
        delta=0
        for ident in ids:
            delta+=amount-game.state.officers[ident].troops
            game.state.officers[ident].troops=amount
        self.assertGreaterEqual(delta,0)
        game.state.soldiers['recruited']+=delta

    def arrive(self,game):
        while game.state.turn<min(row['arrival_turn'] for row in game.state.extension['travel']['marches']):
            game._complete_month(game.state);game._spawn_eligible(game.state);game._reconcile_factions(game.state)
            game.validate(game.state)
        game.command('arrivals',{},game.revision)

    def test_directional_special_quotes_are_read_only_and_match_fast_view(self):
        game=self.game('wei');before=game.export_save()
        quote=game._travel_path(game.state,'yinping','shujun','wei','special',adjacent=True)
        self.assertIsNotNone(quote)
        self.assertEqual(quote['routes'][0]['days'],quote['routes'][0]['base_days']*2)
        self.assertIsNone(game._travel_path(game.state,'shujun','yinping','shu','special',adjacent=True))
        ziwu=game._travel_path(game.state,'hanzhong','jingzhao','wei','special')
        self.assertEqual(ziwu['days'],40)
        started=time.monotonic();view=game.view()
        self.assertLess(time.monotonic()-started,1.5)
        self.assertEqual(view['catalog']['travel_quotes']['hanzhong:jingzhao:special'],ziwu)
        self.assertEqual(game.export_save(),before)

    def test_yinping_loss_is_exact_and_is_not_reapplied_while_waiting_full_city(self):
        game=self.game('wei');source=game.state.cities['yinping'];target=self.empty(game,'shujun','wei')
        ids=source.roster.officer_ids[:3];self.set_troops(game,ids,900)
        game.command('transfer',dict(source='yinping',target='shujun',officers=ids,route_mode='special'),game.revision)
        target=game.state.cities['shujun']
        free=[int(i) for i in game.state.extension['free_locations']][:30]
        self.assertEqual(len(free),30)
        for ident in free:
            game.state.officers[ident].faction_id='wei';target.roster.officer_ids.append(ident)
            game.state.extension['free_locations'].pop(str(ident))
        game.validate(game.state);old_lost=game.state.soldiers['lost']
        self.arrive(game)
        self.assertEqual(sum(game.state.officers[i].troops for i in ids),900)
        self.assertEqual(game.state.soldiers['lost']-old_lost,1800)
        row=game.state.extension['travel']['marches'][0]
        self.assertTrue(all(r['applied'] for r in row['risks']))
        saved=game.export_save();copy=Campaign(game.catalog);copy.load_save(saved,0)
        self.assertEqual(copy.to_dict(),game.to_dict())
        game._complete_month(game.state);game.validate(game.state)
        game.command('arrivals',{},game.revision)
        self.assertEqual(game.state.soldiers['lost']-old_lost,1800)
        target=game.state.cities['shujun']
        for ident in free[:3]:
            target.roster.officer_ids.remove(ident);game.state.officers[ident].faction_id=None
            game.state.extension['free_locations'][str(ident)]=target.id
        game._complete_month(game.state);game.validate(game.state)
        game.command('arrivals',{},game.revision)
        self.assertFalse(game.state.extension['travel']['marches'])
        self.assertTrue(set(ids)<=set(game.state.cities['shujun'].roster.officer_ids))
        self.assertEqual(game.state.soldiers['lost']-old_lost,1800)

    def test_storm_draws_once_for_complete_multileg_voyage_and_never_in_preview(self):
        game=self.game();data=game.catalog.data
        raw=next(r for r in data['travel_routes'] if r['id']=='hepu:zhuya:sea')
        a=evaluate_leg(data,raw,'hepu','zhuya',7)
        b=evaluate_leg(data,data['exploration_routes'][1],'zhuya','yizhou',7)
        quote=game._quote(['hepu','zhuya','yizhou'],[a,b])
        before=game.state.rng.draws
        template=game._march_risks(quote)
        self.assertEqual(game.state.rng.draws,before)
        self.assertEqual(len(template),1)
        risks=game._march_risks(quote,game.state.rng)
        self.assertEqual(game.state.rng.draws,before+1)
        self.assertEqual(risks[0]['legs'],[0,1])
        self.assertTrue(10<=risks[0]['survival_numerator']<=20)

    def test_resolved_hazards_remain_valid_after_waiting_officer_dies(self):
        # Controlled calendar fixture isolates deaths while a full port/city
        # waits; it does not claim a natural multi-year military outcome.
        game=self.game('wei');target=self.empty(game,'shujun','wei')
        source=game.state.cities['yinping'];ids=source.roster.officer_ids[:3]
        self.set_troops(game,ids,900)
        game.command('transfer',dict(source='yinping',target='shujun',officers=ids,route_mode='special'),game.revision)
        target=game.state.cities['shujun']
        for text in list(game.state.extension['free_locations'])[:30]:
            ident=int(text);game.state.officers[ident].faction_id='wei'
            target.roster.officer_ids.append(ident);game.state.extension['free_locations'].pop(text)
        self.arrive(game)
        self.assertTrue(game.state.extension['travel']['marches'][0]['risks'][0]['applied'])
        while (game.state.year,game.state.month)<(220,1):
            game._complete_month(game.state);game._spawn_eligible(game.state);game._reconcile_factions(game.state)
            game.validate(game.state)
        self.assertFalse(game.state.officers[ids[0]].alive)
        row=game.state.extension['travel']['marches'][0]
        self.assertNotIn(ids[0],row['officers'])
        self.assertIn(str(ids[0]),row['risks'][0]['after'])
        # JSON object-key order is not state: canonicalizing must not change
        # the casualty allocation tie break or invalidate a genuine save.
        saved=json.loads(json.dumps(game.export_save(),sort_keys=True))
        loaded=Campaign(game.catalog);loaded.load_save(saved,0)
        self.assertEqual(loaded.to_dict(),game.to_dict())

    def test_exploration_reveals_only_after_successful_arrival_and_roundtrips(self):
        game=self.game();source=game.state.cities['hepu'];target=self.empty(game,'yizhou','wu')
        ident=source.roster.officer_ids[0]
        before=game.state.rng.draws
        quote=game._travel_path(game.state,source.id,target.id,'wu','explore')
        self.assertIsNotNone(quote);self.assertEqual(game.state.rng.draws,before)
        game.command('transfer',dict(source=source.id,target=target.id,officers=[ident],route_mode='explore'),game.revision)
        self.assertEqual(game.state.rng.draws,before+1)
        self.assertFalse(game.state.extension['travel']['discovered'])
        self.assertFalse(game.view()['catalog']['discovered_routes'])
        row=game.state.extension['travel']['marches'][0]
        keep=row['risks'][0]['survival_numerator']
        self.arrive(game)
        self.assertEqual(game.state.officers[ident].troops,300*keep//100)
        self.assertEqual(game.state.extension['travel']['discovered'],['explore:hepu:yizhou'])
        self.assertEqual(game.view()['catalog']['discovered_routes'][0]['id'],'explore:hepu:yizhou')
        self.assertIsNone(game._travel_path(game.state,'hepu','yizhou','wu','explore'))
        self.assertIsNotNone(game._travel_path(game.state,'hepu','yizhou','wu','sea'))
        loaded=Campaign(game.catalog);loaded.load_save(game.export_save(),0)
        self.assertEqual(loaded.to_dict(),game.to_dict())

    def test_failed_exploration_does_not_reveal_or_create_empty_battle(self):
        game=self.game();source=game.state.cities['hepu'];ident=source.roster.officer_ids[0]
        old=game.state.officers[ident].troops;game.state.officers[ident].troops=1
        game.state.soldiers['lost']+=old-1
        game.command('depart',dict(source='hepu',target='yizhou',officers=[ident],route_mode='explore'),game.revision)
        self.arrive(game)
        self.assertEqual(game.state.officers[ident].troops,0)
        self.assertIsNone(game.state.battle)
        self.assertFalse(game.state.extension['travel']['marches'])
        self.assertFalse(game.state.extension['travel']['discovered'])
        self.assertTrue(any('带兵全损' in note for note in game.state.log))

    def test_successful_unknown_sea_approach_can_fight_and_settle_enemy_city(self):
        game=self.game();source=game.state.cities['hepu'];ident=source.roster.officer_ids[0]
        game.command('depart',dict(source='hepu',target='yizhou',officers=[ident],route_mode='explore'),game.revision)
        self.assertEqual(game.state.cities['yizhou'].owner,'neutral')
        self.arrive(game)
        self.assertEqual(game.state.phase,'result')
        self.assertEqual(game.state.battle['outcome'],'victory')
        self.assertEqual(game.state.extension['travel']['discovered'],['explore:hepu:yizhou'])
        loaded=Campaign(game.catalog);loaded.load_save(game.export_save(),0)
        self.assertEqual(loaded.to_dict(),game.to_dict())
        game.command('settle',dict(battle_id=game.state.battle['id']),game.revision)
        self.assertEqual(game.state.cities['yizhou'].owner,'wu')
        game.validate(game.state)

    def test_altered_weather_casualties_or_discovery_saves_are_rejected_atomically(self):
        game=self.game();source=game.state.cities['hepu'];target=self.empty(game,'yizhou','wu')
        game.command('transfer',dict(source=source.id,target=target.id,
                     officers=[source.roster.officer_ids[0]],route_mode='explore'),game.revision)
        before=game.to_dict()
        for change in ('weather','ratio','receipt','discovery','date'):
            bad=game.export_save();travel=bad['state']['extension']['travel'];row=travel['marches'][0]
            if change=='weather':row['quote']['routes'][0]['days']+=1
            elif change=='ratio':row['risks'][0]['survival_numerator']=100
            elif change=='receipt':row['risks'][0]['applied']=True
            elif change=='discovery':travel['discovered'].append('not-a-real-coastal-route')
            else:row['departure_month']=4
            bad['checksum']=digest({k:v for k,v in bad.items() if k!='checksum'})
            with self.assertRaises(GameError):game.load_save(bad,game.revision)
            self.assertEqual(game.to_dict(),before)

    def test_released_catalogs_keep_legacy_travel_schema_and_quotes(self):
        game=Campaign(Catalog(ROOT/'game/data/main-scenarios-v10/217-07.json'))
        game.command('new',dict(faction='shu',seed=2026),0)
        self.assertEqual(set(game.state.extension['travel']),{'counter','marches','battle_arrival'})
        source=game.state.cities['jiameng'];ident=source.roster.officer_ids[0]
        game.command('transfer',dict(source=source.id,target='fuxian',officers=[ident]),game.revision)
        row=game.state.extension['travel']['marches'][0]
        self.assertNotIn('risks',row)
        self.assertTrue(all('hazard' not in leg for leg in row['quote']['routes']))
        saved=game.export_save();loaded=Campaign(game.catalog);loaded.load_save(saved,0)
        self.assertEqual(loaded.to_dict(),game.to_dict())


if __name__=='__main__':unittest.main()
