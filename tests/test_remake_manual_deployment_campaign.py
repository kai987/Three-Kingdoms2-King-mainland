"""Interactive arrivals place sequentially before any real tactical action.

Public departures and arrivals use the unchanged217 catalog, native grids,
officers, food ledger and atomic command/save path. Calendar preparation uses
the existing actual ten-day fixture services, excluding unrelated strategic
AI conquests. Defending-player/AI-only cases explicitly hand the departure
interface to the source owner, then restore the observer before arrival. This
is controlled test setup, not a historical roster or natural AI dispatch.
"""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import battle_allegiance,battle_deployment,battle_grid,battle_placement,tactical_ai
from remake.campaign import Campaign,Catalog,SeedRng,canonical,digest
from remake.campaign_expansion import TACTICS
from remake.errors import GameError
from campaign_fixtures import controlled_catalog

SOURCE,TARGET='baxi','hanzhong'


def command(game,kind,**payload):
    return game.command(kind,payload,game.revision)


def rehash(saved):
    saved['checksum']=digest({key:value for key,value in saved.items()if key!='checksum'})
    return saved


def unchanged_domain(game):
    """Only placement progress/coordinates may differ before confirmation."""
    raw=deepcopy(game.to_dict())
    raw['battle']['extended'].pop('placement',None)
    raw['battle']['extended']['tactical'].pop('positions')
    return canonical(raw)


def place_current(game,point=None):
    view=game.view()['catalog']['battle_tactical']['placement']
    assert view and view['pending']
    point=view['cells'][0]if point is None else point
    return command(game,'battle_place',battle_id=game.state.battle['id'],actor=view['actor'],**point)


def finish_placement(game):
    while battle_placement.pending(game.state.battle):place_current(game)


class ManualDeploymentCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=Catalog(ROOT/'game/data/campaigns/217-07.json')
        cls.catalog_sha=digest(cls.catalog.data)

    def ready_arrival(self,player='shu',*,count=3,catalog=None,source=SOURCE,target=TARGET):
        game=Campaign(catalog or self.catalog)
        command(game,'new',faction=player,seed=2026)
        owner=game.state.cities[source].owner
        ids=[ident for ident in game.state.cities[source].roster.officer_ids
             if game.state.officers[ident].troops>0 and game.state.officers[ident].health>0][:count]
        self.assertEqual(len(ids),count)
        # An actual enemy march is dispatched through the same public command;
        # only the setup's active human owner is explicitly handed over.
        game.state.player=owner
        command(game,'depart',source=source,target=target,officers=ids,route_mode='land')
        game.state.player=player
        march=game.state.extension['travel']['marches'][0]
        self.assertEqual(march['quote']['path'],[source,target])
        self.assertFalse(march['risks'])
        while game.state.turn<march['arrival_turn']:
            game._complete_turn(game.state)
            game._spawn_eligible(game.state)
            game._reconcile_factions(game.state)
        game.state.phase='arrivals';game.validate(game.state)
        return game,ids,deepcopy(march)

    def arrived(self,player='shu',**options):
        game,ids,march=self.ready_arrival(player,**options)
        before=deepcopy(game.state)
        command(game,'arrivals')
        self.assertEqual(game.state.phase,'battle')
        self.assertTrue(battle_placement.pending(game.state.battle))
        return game,ids,march,before

    def assert_atomic_error(self,game,kind,**payload):
        before,revision,journal=game.export_save(),game.revision,deepcopy(game.journal)
        with self.assertRaises(GameError):command(game,kind,**payload)
        self.assertEqual((game.export_save(),game.revision,game.journal),(before,revision,journal))

    def test_public_attacker_arrival_reserves_real_bags_once_and_does_not_start_ai(self):
        game,ids,march=self.ready_arrival();before=deepcopy(game.state)
        with patch.object(game,'_run_tactical_ai_turn',side_effect=AssertionError('No opening AI during placement')):
            command(game,'arrivals')
        state,battle=game.state,game.state.battle;row=battle['extended']['placement']
        self.assertEqual(row,dict(schema=battle_placement.SCHEMA,side='attackers',order=[str(i)for i in ids],confirmed=0))
        self.assertEqual(battle['round'],1)
        self.assertEqual(battle['extended']['deployment']['arrival_city'],march['quote']['path'][-2])
        self.assertEqual(state.rng,before.rng)
        self.assertEqual(state.soldiers,before.soldiers)
        self.assertEqual(state.extension['command_books'],before.extension['command_books'])
        self.assertFalse(state.extension['travel']['marches'])
        self.assertTrue(state.extension['travel']['battle_arrival'])
        bag=battle['extended']['supply']['sides']['attackers']
        self.assertEqual((bag['loaded'],bag['initial_credit']),(march['supply']['remaining'],march['supply']['credit_units']))
        self.assertEqual((bag['consumed'],bag['received'],bag['journal']),(0,0,[]))
        self.assertEqual(state.cities[SOURCE].grain,before.cities[SOURCE].grain)
        self.assertEqual(battle['extended']['supply']['days'],0)
        self.assertEqual(digest(self.catalog.data),self.catalog_sha)

    def test_future_human_units_do_not_occupy_cells_and_confirmation_changes_nothing_else(self):
        game,ids,_,_=self.arrived();battle=game.state.battle
        positions=battle['extended']['tactical']['positions']
        other_ids={str(unit['id'])for unit in battle['defenders']}
        self.assertEqual(set(positions),other_ids|{str(ids[0])})
        proposed=deepcopy(battle);proposed['extended'].pop('tactical')
        planned=battle_deployment.plan(game.catalog,proposed,battle_grid._field(battle),
                                      arrival_city=battle['extended']['deployment']['arrival_city'])
        future=planned['positions'][str(ids[1])]
        self.assertIn(future,game.view()['catalog']['battle_tactical']['placement']['cells'])
        before=unchanged_domain(game)
        response=place_current(game,future)
        self.assertNotIn('presentation',response,'Placement is not a priced tactical movement receipt')
        self.assertEqual(unchanged_domain(game),before)
        current=game.state.battle;progress=current['extended']['placement']
        self.assertEqual(progress['confirmed'],1)
        positions=current['extended']['tactical']['positions']
        self.assertEqual(set(positions),other_ids|{str(ids[0]),str(ids[1])})
        self.assertEqual(positions[str(ids[0])],future)
        self.assertNotEqual(positions[str(ids[1])],future,'Next default must skip the newly confirmed occupant')
        finish_placement(game)
        self.assertEqual(unchanged_domain(game),before)
        self.assertEqual(current['id'],game.state.battle['id'])
        self.assertEqual(game.state.battle['extended']['placement']['confirmed'],len(ids))
        self.assertEqual(len(game.state.battle['extended']['tactical']['positions']),len(ids)+len(game.state.battle['defenders']))
        game.validate(game.state)

    def test_defender_places_everyone_before_exactly_one_original_attacker_ai_phase(self):
        game,_,_=self.ready_arrival('wei')
        original=game._run_tactical_ai_turn
        with patch.object(game,'_run_tactical_ai_turn',wraps=original)as runner:
            command(game,'arrivals')
            self.assertEqual(runner.call_count,0)
            row=game.state.battle['extended']['placement']
            self.assertEqual((row['side'],row['confirmed']),('defenders',0))
            self.assertGreater(len(row['order']),1)
            self.assertEqual(game.state.battle['extended']['tactical']['side'],'attackers')
            before=unchanged_domain(game)
            for _ in range(len(row['order'])-1):
                place_current(game)
                self.assertEqual(runner.call_count,0)
                self.assertEqual(unchanged_domain(game),before)
            last=game.view()['catalog']['battle_tactical']['placement']
            point=last['cells'][0]
            final=dict(battle_id=game.state.battle['id'],actor=last['actor'],**point)
            command(game,'battle_place',**final)
            self.assertEqual(runner.call_count,1)
            self.assertFalse(battle_placement.pending(game.state.battle))
            self.assertEqual(game.state.battle['extended']['placement']['confirmed'],len(row['order']))
            self.assertEqual(game.state.battle['round'],1,'Opening attacker phase must not fabricate a full day')
            self.assertTrue(game.state.battle['extended'].get('siege')or
                            game.state.battle['extended']['tactical']['side']=='defenders')
            self.assert_atomic_error(game,'battle_place',**final)
            self.assertEqual(runner.call_count,1,'Repeated confirmation cannot execute another opening AI phase')
        game.validate(game.state)

    def test_every_other_public_operation_rejects_before_mutation_while_pending(self):
        game,ids,_,_=self.arrived();battle=game.state.battle
        target=battle['defenders'][0]['id']
        operations=[('attack',dict(actor=ids[0],target=target)),('tactic',dict(actor=ids[0],target=target,tactic=0)),
            ('duel_start',dict(actor=ids[0],target=target)),('duel_action',dict(move='strike')),
            ('retreat',{}),('battle_wait',{}),('battle_move',dict(actor=ids[0],x=0,y=0)),
            ('battle_facility',dict(actor=ids[0],action='treat')),('siege_form',dict(formation=0)),
            ('siege_orders',dict(orders={})),('siege_step',{}),('siege_withdraw',{}),('settle',{})]
        for kind,payload in operations:
            with self.subTest(command=kind):self.assert_atomic_error(game,kind,battle_id=battle['id'],**payload)
        for kind,payload in [('end_turn',{}),('arrivals',{}),('ai',dict(turn=game.state.turn)),
                             ('allocate',dict(city=SOURCE,officer=ids[0],troops=0))]:
            with self.subTest(command=kind):self.assert_atomic_error(game,kind,**payload)

    def test_pending_internal_ai_day_and_autoresolve_cannot_advance_or_choose_wait(self):
        game,_,_,_=self.arrived();battle=game.state.battle;before=game.export_save()
        with patch.object(SeedRng,'next',side_effect=AssertionError('Pending placement cannot draw RNG')):
            game._run_tactical_ai_turn(game.state)
            self.assertIsNone(tactical_ai.choose_action(game.state,battle,'attackers','defenders','plain',TACTICS,game=game))
            self.assertEqual(tactical_ai.candidates(game.state,battle,'attackers','defenders','plain',TACTICS),[])
            with self.assertRaises(GameError):game._end_tactical_side(game.state)
            with self.assertRaises(GameError):game._resolve_ai_battle(game.state)
        self.assertEqual(game.export_save(),before)
        board=game.view()['catalog']['battle_tactical']
        self.assertFalse(board['can_end'])
        self.assertTrue(all(not actor['can_act']and not actor['reachable']and actor['facility']is None
                            and not actor['attack_targets']and not actor['duel_targets']
                            for actor in board['actors'].values()))

    def test_place_rejects_wrong_order_enemy_repeat_bounds_types_and_extra_fields_atomically(self):
        game,ids,_,_=self.arrived();battle=game.state.battle
        quote=game.view()['catalog']['battle_tactical']['placement'];point=quote['cells'][0]
        valid=dict(battle_id=battle['id'],actor=quote['actor'],**point)
        enemy=battle['defenders'][0]['id']
        malformed=[dict(valid,actor=ids[1]),dict(valid,actor=enemy),dict(valid,actor=True),
            dict(valid,battle_id='other'),dict(valid,x=-1),dict(valid,x=31),dict(valid,y=19),
            dict(valid,x=True),dict(valid,y=1.0),dict(valid,extra=1)]
        malformed.append({key:value for key,value in valid.items()if key!='y'})
        for payload in malformed:
            with self.subTest(payload=payload):self.assert_atomic_error(game,'battle_place',**payload)
        command(game,'battle_place',**valid)
        self.assert_atomic_error(game,'battle_place',**valid)
        now=game.view()['catalog']['battle_tactical']['placement']
        occupied=game.state.battle['extended']['tactical']['positions'][str(ids[0])]
        self.assert_atomic_error(game,'battle_place',battle_id=battle['id'],actor=now['actor'],**occupied)

    def test_pending_exact_save_load_never_reinitializes_ai_coordinates_or_bags(self):
        game,_,_,_=self.arrived();place_current(game)
        before=game.export_save();restored=Campaign(self.catalog)
        with patch.object(restored,'_run_tactical_ai_turn',side_effect=AssertionError('Load cannot run opening AI')), \
                patch.object(battle_grid,'initialize',side_effect=AssertionError('Saved pending coordinates must be retained')):
            restored.load_save(deepcopy(before),restored.revision)
        self.assertEqual(canonical(restored.export_save()).encode(),canonical(before).encode())
        self.assertTrue(battle_placement.pending(restored.state.battle))
        for _ in range(2):restored.view()
        self.assertEqual(restored.export_save(),before)
        self.assertEqual(restored.state.battle['extended']['placement']['confirmed'],1)

    def test_rehashed_bad_phase_schema_cursor_positions_and_missing_grid_reject_atomically(self):
        game,_,_,_=self.arrived();place_current(game)
        valid=game.export_save();before,revision=deepcopy(valid),game.revision
        mutations=[lambda b:b['extended']['placement'].__setitem__('confirmed',True),
            lambda b:b['extended']['placement'].__setitem__('confirmed',-1),
            lambda b:b['extended']['placement'].__setitem__('confirmed',len(b['attackers'])),
            lambda b:b['extended']['placement'].__setitem__('schema','unknown'),
            lambda b:b['extended']['placement'].__setitem__('side','defenders'),
            lambda b:b['extended']['placement'].__setitem__('extra',0),
            lambda b:b['extended']['placement']['order'].__setitem__(1,b['extended']['placement']['order'][0]),
            lambda b:b.__setitem__('round',2),
            lambda b:b['extended']['tactical']['points'].__setitem__('attackers',0),
            lambda b:b['extended']['tactical']['positions'].pop(str(b['defenders'][0]['id']))]
        for mutate in mutations:
            broken=deepcopy(valid);mutate(broken['state']['battle']);rehash(broken)
            with self.subTest(mutation=mutate),self.assertRaises(GameError):game.load_save(broken,game.revision)
            self.assertEqual((game.export_save(),game.revision),(before,revision))
        broken=deepcopy(valid);extended=broken['state']['battle']['extended']
        extended.pop('tactical');extended.pop('deployment');rehash(broken)
        with patch.object(battle_grid,'initialize',side_effect=AssertionError('Modern placement must never take the legacy anchor migration')):
            with self.assertRaises(GameError):game.load_save(broken,game.revision)
        self.assertEqual((game.export_save(),game.revision),(before,revision))

    def test_ready_save_remains_ready_after_real_paid_move_and_load(self):
        game,_,_,_=self.arrived();finish_placement(game)
        battle=game.state.battle;actor=battle['attackers'][0]['id']
        board=game.view()['catalog']['battle_tactical'];placement=board['placement']
        self.assertFalse(placement['pending']);bounds=placement['bounds']
        choices=board['actors'][str(actor)]['reachable']
        outside=[point for point in choices if not(bounds['min_x']<=point['x']<bounds['max_x_exclusive']
                                                  and bounds['min_y']<=point['y']<bounds['max_y_exclusive'])]
        self.assertTrue(outside,'Ready armies may legally leave their initial rectangle')
        destination=min(outside,key=lambda point:(point['cost'],point['y'],point['x']))
        ap=battle['extended']['tactical']['points']['attackers']
        command(game,'battle_move',battle_id=battle['id'],actor=actor,x=destination['x'],y=destination['y'])
        self.assertEqual(game.state.battle['extended']['tactical']['points']['attackers'],ap-destination['cost'])
        saved=game.export_save();restored=Campaign(self.catalog);restored.load_save(deepcopy(saved),0)
        self.assertEqual(restored.export_save(),saved)
        self.assertFalse(battle_placement.pending(restored.state.battle))

    def test_ready_order_is_initial_identity_set_after_real_conversion_service(self):
        game,_,_,_=self.arrived();finish_placement(game)
        battle=game.state.battle;before=deepcopy(battle['extended']['placement'])
        actor,target=battle['attackers'][0],battle['defenders'][0]
        self.assertNotIn(target['id'],game.state.extension['leaders'].values())
        # The independent conversion suite exercises the success gate/public
        # tactic. Here its real post-success service isolates the changed
        # roster identity set; no battlefield position or initial order is reset.
        battle_allegiance.convert(game,game.state,battle,actor,target,'attackers','defenders')
        self.assertEqual(battle['extended']['placement'],before)
        self.assertIn(target,battle['attackers']);self.assertNotIn(target,battle['defenders'])
        game.validate(game.state)
        saved=game.export_save();restored=Campaign(self.catalog);restored.load_save(deepcopy(saved),0)
        self.assertEqual(restored.export_save(),saved)
        self.assertFalse(battle_placement.pending(restored.state.battle))

    def test_old_ready_and_private_preconfigured_constructor_never_enter_placement(self):
        game=Campaign(self.catalog);command(game,'new',faction='shu',seed=2026)
        state=game.state;ids=state.cities[SOURCE].roster.officer_ids[:3]
        game._start_expanded_battle(state,state.cities[SOURCE],state.cities[TARGET],ids)
        self.assertNotIn('placement',state.battle['extended'])
        self.assertEqual(len(state.battle['extended']['tactical']['positions']),len(state.battle['attackers'])+len(state.battle['defenders']))
        saved=game.export_save();restored=Campaign(self.catalog)
        with patch.object(battle_placement,'initialize',side_effect=AssertionError('Legacy load must not invent deployment')):
            restored.load_save(deepcopy(saved),restored.revision)
        self.assertEqual(restored.export_save(),saved)
        self.assertNotIn('placement',restored.state.battle['extended'])
        self.assert_atomic_error(restored,'battle_place',battle_id=state.battle['id'],actor=ids[0],x=0,y=0)

    def test_actual_ai_to_ai_arrival_uses_default_grid_and_resolves_without_pending(self):
        game,_,_=self.ready_arrival('wu',count=1,catalog=controlled_catalog(),source='xiangyang',target='nanyang')
        captured=[];original=game._resolve_ai_battle
        def inspect(state):
            captured.append(deepcopy(state.battle))
            self.assertNotIn('placement',state.battle['extended'])
            self.assertEqual(len(state.battle['extended']['tactical']['positions']),
                             len(state.battle['attackers'])+len(state.battle['defenders']))
            return original(state)
        with patch.object(game,'_resolve_ai_battle',side_effect=inspect):command(game,'arrivals')
        self.assertEqual(len(captured),1)
        self.assertIn(captured[0]['id'],game.state.settled_battles)
        self.assertIsNone(game.state.battle)
        self.assertEqual(game.state.phase,'city')
        game.validate(game.state)

    def test_empty_defense_arrival_still_goes_directly_to_result(self):
        game=Campaign(controlled_catalog());command(game,'new',faction='wei',seed=2026)
        command(game,'allocate',city='nanyang',officer=123,troops=0)
        game.state.player='shu'
        command(game,'depart',source='xiangyang',target='nanyang',officers=[439],route_mode='land')
        march=game.state.extension['travel']['marches'][0]
        while game.state.turn<march['arrival_turn']:
            game._complete_turn(game.state);game._spawn_eligible(game.state);game._reconcile_factions(game.state)
        game.state.phase='arrivals';command(game,'arrivals')
        self.assertEqual((game.state.phase,game.state.battle['outcome']),('result','victory'))
        self.assertNotIn('placement',game.state.battle['extended'])
        self.assertEqual(game.state.battle['defenders'],[])
        game.validate(game.state)


if __name__=='__main__':unittest.main()
