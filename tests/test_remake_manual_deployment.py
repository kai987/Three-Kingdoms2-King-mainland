"""Controlled native-rectangle placement services, without emulator claims.

These geometry fixtures use the current catalog's unchanged115 bindings and
recovered128 adjacent template pairs. Real campaign transactions are covered
separately; no map, historical profile or frozen gameplay oracle is rewritten.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake import battle_deployment as deployment,battle_grid as grid,battle_placement as placement
from remake.errors import GameError


class ManualDeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = json.loads((ROOT/'game/data/campaigns/208-10.json').read_text())
        cls.cities = {row['id']:row for row in data['cities']}
        cls.reference,cls.bindings = deployment._library()
        cls.representatives = {}
        for city,mid in cls.bindings.items():
            cls.representatives.setdefault(mid,city)

    def fixture(self,side='attackers',source='wuwei',target='jincheng',count=10):
        game = SimpleNamespace(catalog=SimpleNamespace(map_cities=deepcopy(self.cities)))
        battle = dict(id='controlled-placement',source=source,target=target,attacker='a',defender='d',
            attackers=[dict(id=i,start=300,troops=300,martial=60) for i in range(1,count+1)],
            defenders=[dict(id=i,start=300,troops=300,martial=60) for i in range(101,101+count)],
            used=[],round=1,outcome=None,extended=dict(duel=None,duel_history=[],ambush=None,
                surrenders={},withdrawn=None,support={}))
        units=battle['attackers']+battle['defenders']
        for unit in units:
            battle['extended']['support'][str(unit['id'])]=dict(health=80,energy=18,stunned=0,guard=0,morale=70)
        state=SimpleNamespace(player='a' if side=='attackers' else 'd',phase='battle',rng=12345,
            officers={unit['id']:SimpleNamespace(health=80) for unit in units})
        grid.initialize(game,state,battle,directional=True)
        return game,state,battle

    def start(self,*args,**kwargs):
        game,state,battle=self.fixture(*args,**kwargs)
        placement.initialize(game,state,battle)
        grid.validate(game,state,battle)
        return game,state,battle

    def confirm_current(self,game,state,battle,point=None):
        view=placement.view(game,state,battle)
        if point is None:
            point=battle['extended']['tactical']['positions'][str(view['actor'])]
        return placement.confirm(game,state,battle,view['actor'],point['x'],point['y'])

    def finish(self,game,state,battle):
        while placement.pending(battle):
            self.confirm_current(game,state,battle)

    def test_initialization_keeps_ai_and_only_current_human_without_rng_or_cost(self):
        for side in grid.SIDES:
            game,state,battle=self.fixture(side)
            original=deepcopy(battle)
            result=placement.initialize(game,state,battle)
            other='defenders' if side=='attackers' else 'attackers'
            row=battle['extended']['tactical']
            self.assertEqual(result,dict(schema=placement.SCHEMA,side=side,
                order=[str(unit['id']) for unit in battle[side]],confirmed=0))
            self.assertEqual(set(row['positions']),{str(unit['id']) for unit in battle[other]+battle[side][:1]})
            self.assertEqual((row['points'],row['passed'],row['side']),
                (original['extended']['tactical']['points'],dict(attackers=False,defenders=False),'attackers'))
            self.assertEqual((state.rng,battle['round'],battle['used']),(12345,1,[]))
            frozen=deepcopy(battle)
            self.assertEqual(placement.initialize(game,state,battle),result)
            self.assertEqual(battle,frozen)

    def test_every_native_pair_and_human_side_confirms_ten_without_default_exhaustion(self):
        count=0;minima={side:100 for side in grid.SIDES}
        for mid,city in self.reference.items():
            for neighbor in city['neighbors']:
                source=self.representatives[f"original-{neighbor['source_original_city_index']:02d}"]
                target=self.representatives[mid]
                for side in grid.SIDES:
                    game,state,battle=self.start(side,source,target)
                    own=deployment.placement_zone(game.catalog,battle,grid._field(battle),side)['defaults']
                    other='defenders' if side=='attackers' else 'attackers'
                    ai=deployment.placement_zone(game.catalog,battle,grid._field(battle),other)['defaults'][:10]
                    left=len({(p['x'],p['y']) for p in own}-{(p['x'],p['y']) for p in ai})-9
                    minima[side]=min(minima[side],left)
                    self.finish(game,state,battle)
                    self.assertEqual(len(battle['extended']['tactical']['positions']),20)
                    grid.validate(game,state,battle)
                    count+=1
        self.assertEqual((count,minima),(256,dict(attackers=4,defenders=5)))

    def test_all115_city_regions_have_visible_manual_cells_and_twenty_placeable_units(self):
        count=0
        for target,mid in self.bindings.items():
            neighbors={row['source_original_city_index'] for row in self.reference[mid]['neighbors']}
            source=next(city for city,sid in self.bindings.items()
                if city!=target and int(sid.removeprefix('original-')) not in neighbors)
            for side in grid.SIDES:
                game,state,battle=self.start(side,source,target)
                view=placement.view(game,state,battle)
                self.assertGreaterEqual(len(view['cells']),20)
                self.assertTrue(all(0<=p['x']<31 and 0<=p['y']<19 for p in view['cells']))
                self.finish(game,state,battle)
                grid.validate(game,state,battle)
            count+=1
        self.assertEqual(count,115)

    def test_future_units_do_not_occupy_cells_and_each_default_rescans_from_first(self):
        game,state,battle=self.start('defenders')
        view=placement.view(game,state,battle)
        first=deepcopy(battle['extended']['tactical']['positions'][str(view['actor'])])
        second=next(point for point in view['cells'] if point!=first)
        self.confirm_current(game,state,battle,second)
        self.assertEqual(battle['extended']['tactical']['positions']['102'],first)
        self.assertNotIn('103',battle['extended']['tactical']['positions'])
        self.assertEqual(placement.view(game,state,battle)['confirmed'],1)

    def test_opposing_defaults_are_fixed_before_any_human_units(self):
        target=self.representatives['original-07'];source=self.representatives['original-06']
        game,state,battle=self.fixture('defenders',source,target)
        own_first=deepcopy(battle['extended']['tactical']['positions']['101'])
        placement.initialize(game,state,battle)
        zone=deployment.placement_zone(game.catalog,battle,grid._field(battle),'attackers')
        for unit,point in zip(battle['attackers'],zone['defaults']):
            self.assertEqual(battle['extended']['tactical']['positions'][str(unit['id'])],point)
        occupied={tuple(p.values()) for p in battle['extended']['tactical']['positions'].values()}
        self.assertEqual(len(occupied),11)
        self.assertIn(own_first,battle['extended']['tactical']['positions'].values())

    def test_confirm_rejects_other_unit_occupied_outside_and_noninteger_atomically(self):
        game,state,battle=self.start()
        view=placement.view(game,state,battle);current=battle['extended']['tactical']['positions']['1']
        ai=battle['extended']['tactical']['positions']['101']
        for ident,x,y in [(2,current['x'],current['y']),('1',current['x'],current['y']),
                          (1,ai['x'],ai['y']),(1,-1,0),(1,31,0),(1,0,19),
                          (1,True,current['y']),(1,current['x'],1.0)]:
            before=deepcopy(battle)
            with self.assertRaises(GameError):placement.confirm(game,state,battle,ident,x,y)
            self.assertEqual(battle,before)
        self.confirm_current(game,state,battle)
        occupied=battle['extended']['tactical']['positions']['1']
        before=deepcopy(battle)
        with self.assertRaises(GameError):placement.confirm(game,state,battle,2,occupied['x'],occupied['y'])
        self.assertEqual(battle,before)

    def test_original_water_mountain_and_camp_commander_are_not_locked(self):
        seen=set()
        for target,mid in self.representatives.items():
            # representatives maps map IDs to cities; only select native pairs.
            city=self.reference[target]
            neighbor=city['neighbors'][0]
            source=self.representatives[f"original-{neighbor['source_original_city_index']:02d}"]
            for side in grid.SIDES:
                game,state,battle=self.start(side,source,mid,count=1)
                view=placement.view(game,state,battle);field=grid._field(battle)
                for terrain in (3,4):
                    point=next((p for p in view['cells'] if field['classes'][p['y']][p['x']]==terrain),None)
                    if point is not None and terrain not in seen:
                        self.confirm_current(game,state,battle,point);seen.add(terrain);break
                if side=='defenders' and placement.pending(battle):
                    camp=dict(zip(('x','y'),field['camp']))
                    self.assertEqual(battle['extended']['tactical']['positions']['101'],camp)
                    self.confirm_current(game,state,battle,next(p for p in view['cells'] if p!=camp))
            if seen=={3,4}:break
        self.assertEqual(seen,{3,4})

    def test_pending_view_is_pure_and_never_uses_paths_or_target_qualifiers(self):
        game,state,battle=self.start()
        before=deepcopy(battle)
        with (patch.object(grid,'_paths',side_effect=AssertionError('No future position paths')),
              patch.object(grid,'tactic_terrain_reason',side_effect=AssertionError('No future target'))):
            projected=grid.view(game,state,battle)
        self.assertEqual(battle,before)
        self.assertFalse(projected['can_end'])
        self.assertEqual(projected['placement'],placement.view(game,state,battle))
        for row in projected['actors'].values():
            self.assertFalse(row['can_act']);self.assertEqual(row['reachable'],[])
            self.assertEqual((row['attack_targets'],row['duel_targets']),([],[]))
            self.assertTrue(all(not ids for ids in row['tactic_targets'].values()))
        for actor in battle['attackers']:
            self.assertEqual(grid._action_reason(battle,actor,'attackers'),placement.REASON)

    def test_partial_json_roundtrip_and_completed_record_do_not_reopen(self):
        game,state,battle=self.start()
        self.confirm_current(game,state,battle)
        loaded=json.loads(json.dumps(battle))
        grid.validate(game,state,loaded)
        self.assertEqual(placement.view(game,state,loaded),placement.view(game,state,battle))
        self.finish(game,state,loaded)
        finished=deepcopy(loaded)
        self.assertFalse(placement.pending(loaded))
        self.assertEqual(placement.view(game,state,loaded)['cells'],[])
        self.assertIsNone(placement.view(game,state,loaded)['actor'])
        placement.initialize(game,state,loaded)
        self.assertEqual(loaded,finished)
        with self.assertRaises(GameError):placement.confirm(game,state,loaded,1,0,0)
        self.assertEqual(loaded,finished)

    def test_completed_record_uses_original_side_after_conversion_and_does_not_lock_positions(self):
        game,state,battle=self.start();self.finish(game,state,battle)
        unit=battle['attackers'].pop(0);battle['defenders'].append(unit)
        battle['extended']['defections']={'1':dict(original_side='attackers',side='defenders')}
        battle['attackers'].reverse();battle['round']=2;battle['used']=[2]
        battle['extended']['tactical']['positions']['1']=dict(x=0,y=0)
        unit['troops']=0
        placement.validate(game,state,battle)
        grid.validate(game,state,battle)
        self.assertFalse(placement.view(game,state,battle)['pending'])
        malformed=deepcopy(battle);malformed['extended']['placement']['order'][0]='101'
        with self.assertRaises(ValueError):placement.validate(game,state,malformed)

    def test_legacy_missing_stage_is_pure_and_missing_positions_remains_invalid(self):
        game,state,battle=self.fixture();before=deepcopy(battle)
        self.assertIsNone(placement.view(game,state,battle))
        self.assertFalse(placement.pending(battle));placement.validate(game,state,battle)
        self.assertEqual(battle,before)
        del battle['extended']['tactical']['positions']['1']
        with self.assertRaises(ValueError):grid.validate(game,state,battle)
        for missing in ('tactical','deployment'):
            game,state,battle=self.start();del battle['extended'][missing]
            with self.assertRaises(ValueError):placement.validate(game,state,battle)

    def test_ineligible_battles_do_not_create_a_stage(self):
        for change in ('not_player','empty_defenders','no_provenance','no_grid'):
            game,state,battle=self.fixture()
            if change=='not_player':state.player='spectator'
            elif change=='empty_defenders':battle['defenders']=[]
            elif change=='no_provenance':del battle['extended']['deployment']
            else:del battle['extended']['tactical']
            before=deepcopy(battle)
            self.assertIsNone(placement.initialize(game,state,battle))
            self.assertEqual(battle,before)

    def test_generated_runtime_identity_is_preserved_without_numeric_coercion(self):
        game,state,battle=self.fixture(count=1)
        unit=battle['attackers'][0];unit['id']='clerk-controlled-placement'
        state.officers[unit['id']]=state.officers.pop(1)
        battle['extended']['support'][unit['id']]=battle['extended']['support'].pop('1')
        battle['extended']['tactical']['positions'][unit['id']]=battle['extended']['tactical']['positions'].pop('1')
        placement.initialize(game,state,battle)
        view=placement.view(game,state,battle)
        self.assertEqual(view['actor'],'clerk-controlled-placement')
        self.confirm_current(game,state,battle)
        self.assertEqual(battle['extended']['placement']['order'],['clerk-controlled-placement'])
        grid.validate(game,state,battle)

    def test_strict_fields_order_counts_and_partial_positions(self):
        game,state,battle=self.start()
        changes=[lambda b:b['extended']['placement'].update(extra=1),
            lambda b:b['extended']['placement'].update(schema='bad'),
            lambda b:b['extended']['placement'].update(side='defenders'),
            lambda b:b['extended']['placement'].update(confirmed=True),
            lambda b:b['extended']['placement'].update(confirmed=-1),
            lambda b:b['extended']['placement'].update(confirmed=11),
            lambda b:b['extended']['placement'].update(order=['1']*10),
            lambda b:b['extended']['placement'].update(order=list(reversed(b['extended']['placement']['order']))),
            lambda b:b['extended']['placement']['order'].__setitem__(0,1),
            lambda b:b['extended']['tactical']['positions'].update({'2':dict(x=3,y=3)}),
            lambda b:b['extended']['tactical']['positions'].pop('1'),
            lambda b:b['extended']['tactical']['positions']['101'].update(x=0,y=0)]
        for change in changes:
            invalid=deepcopy(battle);change(invalid)
            before=deepcopy(invalid)
            with self.assertRaises(ValueError):grid.validate(game,state,invalid)
            self.assertEqual(invalid,before)

    def test_pending_requires_untouched_day_points_armies_support_and_no_effects(self):
        game,state,battle=self.start()
        changes=[lambda b:b.update(round=2),lambda b:b.update(used=[1]),lambda b:b.update(outcome='victory'),
            lambda b:b['attackers'][0].update(troops=299),
            lambda b:b['extended']['support']['1'].update(health=79),
            lambda b:b['extended']['support']['1'].update(energy=17),
            lambda b:b['extended']['support']['1'].update(stunned=1),
            lambda b:b['extended']['support']['1'].update(guard=1),
            lambda b:b['extended']['tactical']['points'].update(attackers=1),
            lambda b:b['extended']['tactical']['passed'].update(defenders=True),
            lambda b:b['extended']['tactical'].update(side='defenders'),
            lambda b:b['extended'].update(conditions={}),lambda b:b['extended'].update(siege={'x':1}),
            lambda b:b['extended'].update(duel={'x':1}),lambda b:b['extended'].update(surrenders={'1':100}),
            lambda b:b['extended'].update(occupation={'x':1}),
            lambda b:b['extended'].update(supply=dict(days=1,settlement=None))]
        for change in changes:
            invalid=deepcopy(battle);change(invalid)
            with self.assertRaises(ValueError):grid.validate(game,state,invalid)
        state.phase='result'
        with self.assertRaises(ValueError):grid.validate(game,state,battle)


if __name__=='__main__':
    unittest.main()
