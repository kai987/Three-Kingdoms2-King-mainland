"""Original AI setup at real arrivals, saved input provenance and old battles.

The current217 catalog is unchanged. Enemy/observer entry hands the departure
UI to the source owner only while staging a public march, just as the manual
deployment acceptance fixture does. This is explicit controlled setup, not a
claim that a natural strategic AI selected that march or historical roster.
"""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'source'),str(ROOT/'tests')]
from remake import battle_ai_deployment,battle_auto_deployment as automatic,battle_grid,battle_placement,battle_allegiance
from remake.campaign import Campaign,Catalog,SeedRng,digest
from remake.errors import GameError
from campaign_fixtures import controlled_catalog,confirm_default_placement

SOURCE,TARGET = 'baxi','hanzhong'
WAIT = dict(kind='wait',actor=None,target=None,tactic=None,score=0)


def command(game,kind,**payload):
    return game.command(kind,payload,game.revision)


def rehash(saved):
    saved['checksum'] = digest({key:value for key,value in saved.items() if key != 'checksum'})
    return saved


class AutoDeploymentCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = Catalog(ROOT/'game/data/campaigns/217-07.json')
        cls.catalog_hash = digest(cls.catalog.data)

    def ready(self,player='shu',*,count=3,catalog=None,source=SOURCE,target=TARGET):
        game = Campaign(catalog or self.catalog)
        command(game,'new',faction=player,seed=2026)
        owner = game.state.cities[source].owner
        ids = [ident for ident in game.state.cities[source].roster.officer_ids
               if game.state.officers[ident].troops > 0 and game.state.officers[ident].health > 0][:count]
        self.assertEqual(len(ids),count)
        game.state.player = owner
        command(game,'depart',source=source,target=target,officers=ids,route_mode='land')
        game.state.player = player
        march = deepcopy(game.state.extension['travel']['marches'][0])
        while game.state.turn < march['arrival_turn']:
            game._complete_turn(game.state);game._spawn_eligible(game.state);game._reconcile_factions(game.state)
        game.state.phase = 'arrivals'
        game.validate(game.state)
        return game,ids,march

    def arrived(self,player='shu',**options):
        game,ids,march = self.ready(player,**options)
        before = deepcopy(game.state)
        command(game,'arrivals')
        self.assertTrue(battle_placement.pending(game.state.battle))
        return game,ids,march,before

    def restored(self,game):
        saved = game.export_save(); other = Campaign(game.catalog)
        other.load_save(deepcopy(saved),0)
        self.assertEqual(other.export_save(),saved)
        return other

    def assert_bad_save(self,game,change):
        saved = deepcopy(game.export_save());change(saved['state']['battle'])
        rehash(saved);before = game.export_save();revision = game.revision
        with self.assertRaises(GameError):game.load_save(saved,revision)
        self.assertEqual(game.export_save(),before)
        self.assertEqual(game.revision,revision)

    def test_player_attack_ai_uses_original_plan_without_changing_human_order_or_resources(self):
        game,ids,march,before = self.arrived()
        state,battle = game.state,game.state.battle
        record = battle['extended']['auto_deployment']
        self.assertEqual(set(record),{'schema','sides'})
        self.assertEqual(record['schema'],automatic.SCHEMA)
        self.assertEqual(set(record['sides']),{'defenders'})
        self.assertEqual(record['sides']['defenders'],dict(binding=battle_ai_deployment.family_for('wei'),
            roster=[dict(id=str(unit['id']),martial=unit['martial']) for unit in battle['defenders']]))
        planned = battle_ai_deployment.plan(game.catalog,battle,battle_grid._field(battle),'defenders')
        points = battle['extended']['tactical']['positions']
        self.assertTrue(all(points[key] == point for key,point in planned['positions'].items()))
        self.assertEqual(battle['extended']['placement']['order'],[str(ident) for ident in ids])
        self.assertEqual([unit['id'] for unit in battle['attackers']],ids)
        self.assertEqual(set(points),set(planned['positions'])|{str(ids[0])})
        self.assertEqual(state.rng,before.rng)
        self.assertEqual(state.soldiers,before.soldiers)
        self.assertEqual(state.extension['command_books'],before.extension['command_books'])
        self.assertEqual(tuple(getattr(state,key) for key in ('year','month','day','turn')),
                         tuple(getattr(before,key) for key in ('year','month','day','turn')))
        self.assertEqual(state.cities[SOURCE].grain,before.cities[SOURCE].grain)
        defender = battle['extended']['supply']['sides']['defenders']
        self.assertEqual(state.cities[TARGET].grain,before.cities[TARGET].grain-defender['loaded'])
        self.assertEqual(battle['extended']['supply']['days'],0)
        self.assertEqual(digest(self.catalog.data),self.catalog_hash)

    def test_player_defense_waits_for_all_confirmations_before_one_attacker_ai_phase(self):
        game,ids,_ = self.ready('wei')
        with patch.object(game,'_run_tactical_ai_turn',wraps=game._run_tactical_ai_turn) as runner:
            command(game,'arrivals')
            self.assertEqual(runner.call_count,0)
            battle = game.state.battle
            self.assertEqual(set(battle['extended']['auto_deployment']['sides']),{'attackers'})
            plan = battle_ai_deployment.plan(game.catalog,battle,battle_grid._field(battle),'attackers')
            self.assertTrue(all(battle['extended']['tactical']['positions'][key] == point
                                for key,point in plan['positions'].items()))
            with patch('remake.tactical_ai.choose_action',return_value=WAIT):
                confirm_default_placement(game)
            self.assertEqual(runner.call_count,1)
            self.assertFalse(battle_placement.pending(game.state.battle))
            self.assertEqual(game.state.battle['extended']['tactical']['side'],'defenders')
            self.assertEqual(game.state.battle['round'],1)
            self.assertEqual(game.state.battle['extended']['supply']['days'],0)

    def test_actual_ai_ai_arrival_plans_defense_then_attack_without_a_human_stage(self):
        game,_,_ = self.ready('wu',catalog=controlled_catalog(),source='xiangyang',target='nanyang',count=1)
        snapshots = [];original = game._resolve_ai_battle
        def inspect(state):
            battle = state.battle; snapshots.append(deepcopy(battle))
            self.assertNotIn('placement',battle['extended'])
            self.assertEqual(set(battle['extended']['auto_deployment']['sides']),set(battle_grid.SIDES))
            field = battle_grid._field(battle)
            defense = battle_ai_deployment.plan(game.catalog,battle,field,'defenders')
            attack = battle_ai_deployment.plan(game.catalog,battle,field,'attackers',
                occupied=[(p['x'],p['y']) for p in defense['positions'].values()])
            self.assertEqual(battle['extended']['tactical']['positions'],
                             {**defense['positions'],**attack['positions']})
            self.assertEqual(state.rng.draws,0)
            return original(state)
        with patch.object(game,'_resolve_ai_battle',side_effect=inspect):command(game,'arrivals')
        self.assertEqual(len(snapshots),1)
        self.assertIn(snapshots[0]['id'],game.state.settled_battles)
        self.assertIsNone(game.state.battle)
        game.validate(game.state)

    def test_pending_roundtrip_freezes_inputs_and_confirmation_never_replans_live_units(self):
        game,_,_,_ = self.arrived()
        saved = game.export_save();before_rng = deepcopy(game.state.rng)
        before = deepcopy(game.state.battle['extended']['auto_deployment'])
        game = self.restored(game)
        quote = game.view()['catalog']['battle_tactical']['placement'];actor = quote['actor']
        point = game.state.battle['extended']['tactical']['positions'][str(actor)]
        with patch.object(SeedRng,'next',side_effect=AssertionError('Setup cannot draw RNG')):
            command(game,'battle_place',battle_id=game.state.battle['id'],actor=actor,**point)
        self.assertEqual(game.state.battle['extended']['auto_deployment'],before)
        self.assertEqual(game.state.rng,before_rng)
        self.assertEqual(game.state.battle['extended']['placement']['confirmed'],1)
        self.restored(game)
        self.assertEqual(saved['state']['battle']['extended']['placement']['confirmed'],0)

    def test_setup_and_explanation_are_pure_and_never_mutate_cached_sources(self):
        game,_,_,_ = self.arrived()
        before = game.export_save();catalog = digest(game.catalog.data)
        with patch.object(SeedRng,'next',side_effect=AssertionError('No view draws')):
            first = automatic.view(game,game.state,game.state.battle)
            self.assertEqual(automatic.view(game,game.state,game.state.battle),first)
            automatic.initialize(game,game.state,game.state.battle)
        self.assertEqual(game.export_save(),before)
        self.assertEqual(digest(game.catalog.data),catalog)
        first['sides']['defenders']['order'].reverse()
        self.assertNotEqual(first,automatic.view(game,game.state,game.state.battle))

    def test_malformed_receipts_positions_and_missing_grid_reject_atomically(self):
        game,_,_,_ = self.arrived()
        changes=[lambda b:b['extended']['auto_deployment'].update(extra=1),
            lambda b:b['extended']['auto_deployment'].update(schema='bad'),
            lambda b:b['extended']['auto_deployment'].update(sides={}),
            lambda b:b['extended']['auto_deployment']['sides']['defenders'].update(extra=1),
            lambda b:b['extended']['auto_deployment']['sides']['defenders']['binding'].update(family=True),
            lambda b:b['extended']['auto_deployment']['sides']['defenders']['binding'].update(policy='invented'),
            lambda b:b['extended']['auto_deployment']['sides']['defenders']['roster'][0].update(martial=True),
            lambda b:b['extended']['auto_deployment']['sides']['defenders']['roster'][0].update(martial=256),
            lambda b:b['extended']['auto_deployment']['sides']['defenders']['roster'][0].update(id='not-deployed'),
            lambda b:b['extended']['tactical']['positions'][str(b['defenders'][0]['id'])].update(x=0,y=0),
            lambda b:b['extended'].pop('tactical'),lambda b:b['extended'].pop('deployment')]
        for change in changes:self.assert_bad_save(game,change)

    def test_completed_receipt_keeps_moves_and_load_does_not_initialize_or_run_ai(self):
        game,_,_,_ = self.arrived();confirm_default_placement(game)
        battle = game.state.battle;actor = battle['attackers'][0]['id']
        before = deepcopy(battle['extended']['auto_deployment'])
        options = game.view()['catalog']['battle_tactical']['actors'][str(actor)]['reachable']
        point = min(options,key=lambda p:(p['cost'],p['y'],p['x']))
        command(game,'battle_move',battle_id=battle['id'],actor=actor,x=point['x'],y=point['y'])
        saved = game.export_save();restored = Campaign(game.catalog)
        with (patch.object(automatic,'initialize',side_effect=AssertionError('Load must not redeploy')),
              patch.object(restored,'_run_tactical_ai_turn',side_effect=AssertionError('Load must not run AI'))):
            restored.load_save(deepcopy(saved),0)
        self.assertEqual(restored.export_save(),saved)
        self.assertEqual(restored.state.battle['extended']['auto_deployment'],before)
        self.assertEqual(restored.state.battle['extended']['tactical']['positions'][str(actor)],dict(x=point['x'],y=point['y']))

    def test_saved_single_human_stage_is_required_and_explanation_uses_only_snapshot_martial(self):
        game,_,_,_ = self.arrived(count=1)
        # With one human unit the pending coordinate set is already complete;
        # removing the stage must still not turn an unconfirmed save into ready.
        self.assert_bad_save(game,lambda battle:battle['extended'].pop('placement'))
        confirm_default_placement(game)
        original = automatic.view(game,game.state,game.state.battle)
        controlled = deepcopy(game.state.battle)
        # Pure source-selection probe only: no inconsistent battle is saved or
        # committed. The explanation must retain the frozen initial martial.
        for unit in controlled['defenders']:
            unit['martial'] = 255-unit['martial']
        self.assertEqual(automatic.view(game,game.state,controlled),original)

    def test_completed_receipt_allows_conversion_and_observer_without_reordering(self):
        game,_,_,_ = self.arrived();confirm_default_placement(game)
        state,battle = game.state,game.state.battle
        victim = next(unit for unit in battle['defenders'] if unit['id'] not in state.extension['leaders'].values())
        receipt = deepcopy(battle['extended']['auto_deployment'])
        battle_allegiance.convert(game,state,battle,battle['attackers'][0],victim,'attackers','defenders')
        game.validate(state)
        self.assertEqual(battle['extended']['auto_deployment'],receipt)
        state.player = 'wu'
        with patch.object(battle_ai_deployment,'plan',side_effect=AssertionError('Completed validate must not replan')):
            game.validate(state)
        # The load response may derive an opening explanation from snapshots;
        # it must never install that plan over current authoritative positions.
        with patch.object(automatic,'initialize',side_effect=AssertionError('No observer redeployment')):
            self.restored(game)
        self.assertEqual(battle['extended']['auto_deployment'],receipt)

    def test_old_pending_without_new_receipt_retains_original_fixed_defaults(self):
        game,_,_ = self.ready();state = game.state
        # Explicit prior-release constructor: same existing directional grid,
        # then old manual initialization, with no automatic strategy request.
        march = state.extension['travel']['marches'].pop(0)
        game._start_expanded_battle(state,state.cities[SOURCE],state.cities[TARGET],march['officers'],
            paid=True,march_supply=march['supply'],arrival_city=SOURCE)
        battle_placement.initialize(game,state,state.battle)
        self.assertNotIn('auto_deployment',state.battle['extended'])
        before = game.export_save()
        with patch.object(battle_ai_deployment,'plan',side_effect=AssertionError('Old pending is not upgraded')):
            self.restored(game)
        self.assertEqual(game.export_save(),before)
        confirm_default_placement(game)
        self.assertNotIn('auto_deployment',game.state.battle['extended'])

    def test_private_and_empty_defense_battles_do_not_gain_a_new_receipt(self):
        game = Campaign(self.catalog);command(game,'new',faction='shu',seed=2026)
        state = game.state;ids=state.cities[SOURCE].roster.officer_ids[:1]
        game._start_expanded_battle(state,state.cities[SOURCE],state.cities[TARGET],ids)
        self.assertNotIn('auto_deployment',state.battle['extended'])
        self.restored(game)
        game = Campaign(controlled_catalog());command(game,'new',faction='wei',seed=2026)
        command(game,'allocate',city='nanyang',officer=123,troops=0)
        game.state.player='shu'
        command(game,'depart',source='xiangyang',target='nanyang',officers=[439],route_mode='land')
        march=game.state.extension['travel']['marches'][0]
        while game.state.turn<march['arrival_turn']:
            game._complete_turn(game.state);game._spawn_eligible(game.state);game._reconcile_factions(game.state)
        game.state.phase='arrivals';command(game,'arrivals')
        self.assertEqual(game.state.phase,'result')
        self.assertNotIn('auto_deployment',game.state.battle['extended'])

    def test_failed_plan_is_atomic_before_any_partial_manual_stage_is_committed(self):
        game,_,_ = self.ready();before = game.export_save();revision=game.revision
        with patch.object(battle_ai_deployment,'plan',side_effect=ValueError('Controlled bad native plan')):
            with self.assertRaises((ValueError,GameError)):command(game,'arrivals')
        self.assertEqual(game.export_save(),before)
        self.assertEqual(game.revision,revision)


if __name__=='__main__':unittest.main()
