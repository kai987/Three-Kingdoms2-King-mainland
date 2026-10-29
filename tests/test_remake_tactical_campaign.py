"""Actual commands, arrivals, saves and AI all use the authoritative grid/AP."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, SeedRng, digest
from remake import battle_grid as grid, siege
from remake.errors import GameError
from campaign_fixtures import controlled_catalog, reach_battle, soldier_encounter_step
from test_remake_tactical_ai import battle as contact_battle


WAIT = dict(kind='wait', actor=None, target=None, tactic=None, score=0)


class TacticalCampaignTests(unittest.TestCase):
    def setUp(self):
        self.game = Campaign(controlled_catalog())
        self.command('new', faction='shu', seed=2026)
        self.command('depart', source='xiangyang', target='nanyang', officers=[146])
        reach_battle(self.game)

    def command(self, kind, **payload):
        return self.game.command(kind, payload, self.game.revision)

    def actors(self):
        battle = self.game.state.battle
        return battle, battle['attackers'][0], battle['defenders'][0]

    def approach(self, *, reserve=4):
        """Walk actual cheapest paths, legally passing days to retain attack AP."""
        for _ in range(100):
            state = self.game.state
            battle, actor, target = self.actors()
            source, distances, previous = grid._paths(state, battle, actor)
            point = battle['extended']['tactical']['positions'][str(target['id'])]
            goals = [(distances[p], p[1], p[0], p) for p in
                ((point['x']-1, point['y']), (point['x']+1, point['y']),
                 (point['x'], point['y']-1), (point['x'], point['y']+1)) if p in distances]
            goal = min(goals)[-1]
            if goal == source and battle['extended']['tactical']['points']['attackers'] >= reserve:
                return
            path = [goal]
            while path[-1] != source:
                path.append(previous[path[-1]])
            path.reverse()
            available = battle['extended']['tactical']['points']['attackers'] - reserve
            affordable = [p for p in path[1:] if distances[p] <= available]
            if affordable:
                x, y = affordable[-1]
                self.command('battle_move', battle_id=battle['id'], actor=actor['id'], x=x, y=y)
            else:
                # Isolate movement and player kernels from policy choices.
                # The real side/day/AP transition still executes normally.
                with patch('remake.tactical_ai.choose_action', return_value=WAIT):
                    self.command('battle_wait', battle_id=battle['id'])
        self.fail('The real army failed to reach contact in100valid commands')

    def test_real_arrival_rejects_remote_attack_before_rng_or_any_spending(self):
        battle, actor, target = self.actors()
        self.assertTrue(grid.attack_reason(battle, actor, target, 'attackers'))
        before, revision = self.game.export_save(), self.game.revision
        with self.assertRaises(GameError):
            self.command('attack', battle_id=battle['id'], actor=actor['id'], target=target['id'])
        self.assertEqual(self.game.export_save(), before)
        self.assertEqual(self.game.revision, revision)

    def test_real_move_spends_quoted_ap_without_rng_or_strategic_orders(self):
        battle, actor, _ = self.actors()
        options = self.game.view()['catalog']['battle_tactical']['actors'][str(actor['id'])]['reachable']
        destination = min(options, key=lambda p: (p['cost'], p['y'], p['x']))
        before = deepcopy(self.game.state)
        points = battle['extended']['tactical']['points']['attackers']
        self.command('battle_move', battle_id=battle['id'], actor=actor['id'],
            x=destination['x'], y=destination['y'])
        current = self.game.state.battle['extended']['tactical']
        self.assertEqual(current['points']['attackers'], points-destination['cost'])
        self.assertEqual(current['positions'][str(actor['id'])], {key: destination[key] for key in ('x', 'y')})
        self.assertEqual(self.game.state.rng, before.rng)
        self.assertEqual(self.game.state.extension['command_books'], before.extension['command_books'])
        self.assertEqual(self.game.state.soldiers, before.soldiers)

    def test_repeated_attacks_include_contact_replies_without_free_enemy_turn(self):
        # Reach an ordinary field contact through actual arrival, enemy-side
        # movement, player path quotes and real AP payments.
        b,_,target=self.actors()
        source,distances,_=grid._paths(self.game.state,b,target)
        terrain=grid._field(b)['classes']
        _,y,x=min((cost,y,x)for (x,y),cost in distances.items()
                  if (x,y)!=source and terrain[y][x]==2
                  and cost<=b['extended']['tactical']['points']['defenders'])
        def enemy_leaves_castle(state,battle,*args,**kwargs):
            point=battle['extended']['tactical']['positions'][str(target['id'])]
            return dict(kind='move',actor=target['id'],x=x,y=y)if point!=dict(x=x,y=y)else WAIT
        with patch('remake.tactical_ai.choose_action',side_effect=enemy_leaves_castle):
            self.command('battle_wait',battle_id=b['id'])
        self.approach(reserve=6)
        battle,actor,target=self.actors();before=deepcopy(self.game.state)
        points=battle['extended']['tactical']['points']['attackers'];contacts=0
        with patch.object(self.game,'_counter',side_effect=AssertionError('No free whole-side AI response')), \
                patch('remake.tactical_ai.choose_action',side_effect=AssertionError('No free enemy policy command')):
            for _ in range(2):
                battle,actor,target=self.actors()
                if self.game.state.phase!='battle' or not actor['troops'] or not target['troops']:break
                start=(actor['troops'],target['troops']);seed=self.game.state.rng.draws
                self.command('attack',battle_id=battle['id'],actor=actor['id'],target=target['id']);contacts+=1
                self.assertEqual(self.game.state.rng.draws,seed,'Opening formation has no damage draw')
                self.assertEqual(self.game.state.battle['extended']['siege']['mode'],'field')
                # The native pieces walk to contact. Both generals wait so
                # this assertion exercises soldier return fire, not a duel.
                orders={k:'wait'if k=='general'else'advance'for k in siege.KINDS}
                for _ in range(100):
                    row=self.game.state.battle['extended'].get('siege')
                    if row is None:break
                    row['orders']['defenders']['general']='wait'
                    row['piece_orders']['defenders']['d0']='wait'
                    soldier_encounter_step(self.game,orders=orders)
                    current=self.game.state.battle
                    if all(current[side][0]['troops']<start[i]for i,side in enumerate(grid.SIDES)):break
                battle,actor,target=self.actors()
                self.assertLess(actor['troops'],start[0]);self.assertLess(target['troops'],start[1])
                if battle['extended'].get('siege'):
                    self.command('siege_withdraw',battle_id=battle['id'])
                self.assertEqual(self.game.state.rng.draws,seed+2,'One encounter seeds both sides once')
        battle,actor,target=self.actors()
        self.assertGreaterEqual(contacts,1)
        self.assertLess(actor['troops'],before.battle['attackers'][0]['troops'])
        self.assertLess(target['troops'],before.battle['defenders'][0]['troops'])
        self.assertEqual(battle['extended']['tactical']['points']['attackers'],points-2*contacts)
        self.assertEqual(self.game.state.rng.draws,before.rng.draws+2*contacts)
        self.assertEqual(self.game.state.extension['command_books'],before.extension['command_books'])

    def test_wait_drives_real_enemy_movement_and_returns_control_to_player(self):
        battle, _, _ = self.actors()
        before = deepcopy(battle['extended']['tactical'])
        orders = deepcopy(self.game.state.extension['command_books'])
        with patch.object(self.game, '_execute_battle_move', wraps=self.game._execute_battle_move) as move:
            self.command('battle_wait', battle_id=battle['id'])
        current = self.game.state.battle['extended']['tactical']
        self.assertGreater(move.call_count, 0)
        self.assertEqual(current['side'], 'attackers')
        self.assertNotEqual(current['positions'], before['positions'])
        self.assertEqual(self.game.state.extension['command_books'], orders)
        self.game.validate(self.game.state)

    def test_save_roundtrip_preserves_cells_points_and_bootstraps_old_battle_once(self):
        battle, actor, _ = self.actors()
        destination = min(self.game.view()['catalog']['battle_tactical']['actors'][str(actor['id'])]['reachable'],
                          key=lambda p: (p['cost'], p['y'], p['x']))
        self.command('battle_move', battle_id=battle['id'], actor=actor['id'], x=destination['x'], y=destination['y'])
        saved = self.game.export_save()
        restored = Campaign(self.game.catalog)
        restored.load_save(saved, 0)
        self.assertEqual(restored.export_save(), saved)
        old = deepcopy(saved)
        del old['state']['battle']['extended']['tactical']
        old['checksum'] = digest({key: value for key, value in old.items() if key != 'checksum'})
        restored.load_save(old, restored.revision)
        self.assertEqual(vars(restored.state.rng), vars(self.game.state.rng))
        self.assertEqual(restored.state.soldiers, self.game.state.soldiers)
        self.assertEqual(restored.state.battle['attackers'], self.game.state.battle['attackers'])
        self.assertEqual(restored.state.battle['defenders'], self.game.state.battle['defenders'])
        self.assertIn('tactical', restored.state.battle['extended'])
        migrated = restored.export_save()
        restored.load_save(migrated, restored.revision)
        self.assertEqual(restored.export_save(), migrated)

    def test_bad_moves_and_present_malformed_tactical_save_are_rejected_atomically(self):
        battle, actor, target = self.actors()
        point = battle['extended']['tactical']['positions'][str(target['id'])]
        for x, y in ((-1, 0), (31, 0), (1, True), (point['x'], point['y'])):
            saved = self.game.export_save()
            with self.assertRaises(GameError):
                self.command('battle_move', battle_id=battle['id'], actor=actor['id'], x=x, y=y)
            self.assertEqual(self.game.export_save(), saved)
        saved = self.game.export_save()
        for edit in (
            lambda row: row.update(points={'attackers': True, 'defenders': 10}),
            lambda row: row.update(points={'attackers': 60, 'defenders': 10}),
            lambda row: row['positions'][str(actor['id'])].update(x=31),
            lambda row: row['positions'].update({str(actor['id']): deepcopy(point)}),
            lambda row: row.update(schema='bad'),
            lambda row: row.update(passed={'attackers': True, 'defenders': False}),
        ):
            bad = deepcopy(saved)
            edit(bad['state']['battle']['extended']['tactical'])
            bad['checksum'] = digest({key: value for key, value in bad.items() if key != 'checksum'})
            with self.assertRaises(GameError):
                self.game.load_save(bad, self.game.revision)
            self.assertEqual(self.game.export_save(), saved)

    def test_legacy_defender_battle_keeps_player_decision_without_replaying_enemy_turn(self):
        game = Campaign(controlled_catalog())
        game.command('new', dict(faction='shu', seed=2026), 0)
        game._start_expanded_battle(game.state, game.state.cities['nanyang'],
                                    game.state.cities['xiangyang'], [123])
        self.assertEqual(game.state.phase, 'battle')
        self.assertEqual(game._player_sides(game.state)[0], 'defenders')
        before = deepcopy(game.state)
        legacy = deepcopy(game.export_save())
        del legacy['state']['battle']['extended']['tactical']
        legacy['checksum'] = digest({key: value for key, value in legacy.items() if key != 'checksum'})
        restored = Campaign(game.catalog)
        restored.load_save(legacy, 0)
        tactical = restored.state.battle['extended']['tactical']
        self.assertEqual(tactical['side'], 'defenders')
        self.assertEqual(tactical['passed'], dict(attackers=True, defenders=False))
        self.assertEqual(restored.state.rng, before.rng)
        self.assertEqual(restored.state.soldiers, before.soldiers)
        self.assertEqual(restored.state.officers, before.officers)
        self.assertEqual(restored.state.extension['command_books'], before.extension['command_books'])
        self.assertEqual(restored.state.battle['attackers'], before.battle['attackers'])
        self.assertEqual(restored.state.battle['defenders'], before.battle['defenders'])
        view = restored.view()['catalog']['battle_tactical']
        self.assertTrue(view['can_end'])
        self.assertTrue(any(row['can_act'] for row in view['actors'].values()))
        migrated = restored.export_save()
        restored.load_save(migrated, restored.revision)
        self.assertEqual(restored.export_save(), migrated, 'Existing positions, passed sides and AP never refresh on reload')
        with patch('remake.tactical_ai.choose_action', return_value=WAIT):
            restored.command('battle_wait', dict(battle_id=restored.state.battle['id']), restored.revision)
        self.assertEqual(restored.state.phase, 'battle')
        self.assertEqual(restored.state.battle['round'], before.battle['round']+1)
        self.assertEqual(restored.state.battle['extended']['tactical']['side'], 'defenders')
        self.assertEqual(restored.state.rng, before.rng)
        self.assertEqual(restored.state.soldiers, before.soldiers)
        self.assertEqual(restored.state.extension['command_books'], before.extension['command_books'])
        restored.validate(restored.state)

    def test_thirty_day_limit_retreats_attackers_without_advancing_strategy_calendar(self):
        before = deepcopy(self.game.state)
        with patch('remake.tactical_ai.choose_action', return_value=WAIT):
            for _ in range(30):
                self.command('battle_wait', battle_id=self.game.state.battle['id'])
        state = self.game.state
        self.assertEqual(state.phase, 'result')
        self.assertEqual((state.battle['outcome'], state.battle['extended']['withdrawn']), ('retreat', 'attackers'))
        self.assertEqual((state.year, state.month, state.day, state.turn),
                         (before.year, before.month, before.day, before.turn))
        self.assertEqual(state.rng, before.rng)
        self.assertEqual(state.extension['command_books'], before.extension['command_books'])
        self.game.validate(state)

    def test_ai_versus_ai_uses_real_paths_shared_points_and_conserves_soldiers(self):
        game = Campaign(controlled_catalog())
        game.command('new', dict(faction='wu', seed=2026), 0)
        state = game.state
        game._start_expanded_battle(state, state.cities['xiangyang'], state.cities['nanyang'], [146])
        orders = deepcopy(state.extension['command_books'])
        with patch.object(game, '_execute_battle_move', wraps=game._execute_battle_move) as move, \
             patch.object(grid, 'spend', wraps=grid.spend) as spend:
            game._resolve_ai_battle(state)
        self.assertGreater(move.call_count, 0)
        self.assertEqual({call.args[1] for call in spend.call_args_list}, set(grid.SIDES))
        self.assertIsNone(state.battle)
        self.assertEqual(len(state.settled_battles), 1)
        self.assertEqual(state.extension['command_books'], orders)
        game.validate(state)
        current = sum(city.reserves for city in state.cities.values()) + sum(o.troops for o in state.officers.values())
        self.assertEqual(current + state.soldiers['lost'], state.soldiers['initial'] + state.soldiers['recruited'])


class ContactRetaliationTests(unittest.TestCase):
    """Real field formation/steps are bilateral, with one macro AP payment."""
    def setUp(self):
        self.game=contact_battle(three_enemies=False)

    def units(self):
        b=self.game.state.battle
        return b,b['attackers'][0],b['defenders'][0]

    def attack(self):
        b,actor,target=self.units()
        return self.game.command('attack',dict(battle_id=b['id'],actor=actor['id'],target=target['id']),self.game.revision)

    def prepare_contact(self,*,opened=False):
        """Explicit valid soldier-cell fixture; no HP/damage/RNG is set.

        The visible contact/formation commands run first. Two surviving front
        squads are then placed side by side to isolate native turn ordering
        from the separate movement tests. Every other original piece waits.
        """
        if not opened:self.attack()
        b,_,_=self.units()
        self.game.command('siege_form',dict(battle_id=b['id'],formation=3),self.game.revision)
        row=self.game.state.battle['extended']['siege']
        for side in siege.SIDES:
            row['orders'][side]={kind:'wait'for kind in siege.KINDS}
            row['piece_orders'][side]={p['id']:'wait'for p in row['units']if p['side']==side}
        next(p for p in row['units']if p['id']=='a1').update(x=6,y=4)
        next(p for p in row['units']if p['id']=='d1').update(x=7,y=4)
        self.game.validate(self.game.state)

    def cycle(self):
        b,_,_=self.units();row=b['extended']['siege']
        self.game.command('siege_orders',dict(battle_id=b['id'],piece_orders=dict(row['piece_orders']['attackers'])),self.game.revision)
        return self.game.command('siege_step',dict(battle_id=b['id']),self.game.revision)

    def scene(self,result):
        return next(scene for scene in result['presentation']['scenes']if scene['kind']=='soldier_step')

    def test_contact_attack_has_one_reply_two_real_draws_and_one_ap_payment(self):
        b,actor,target=self.units();before=deepcopy(self.game.state)
        with patch('remake.tactical_ai.choose_action',side_effect=AssertionError('No free enemy turn')), \
                patch.object(self.game,'_counter',side_effect=AssertionError('No legacy response')):
            self.prepare_contact();self.assertEqual(self.game.state.rng,before.rng)
            result=self.cycle()
        after,actor,target=self.units()
        self.assertLess(actor['troops'],before.battle['attackers'][0]['troops'])
        self.assertLess(target['troops'],before.battle['defenders'][0]['troops'])
        points=after['extended']['tactical']['points']
        self.assertEqual(points['attackers'],before.battle['extended']['tactical']['points']['attackers']-2)
        self.assertEqual(points['defenders'],before.battle['extended']['tactical']['points']['defenders'])
        self.assertEqual(after['extended']['tactical']['side'],'attackers')
        self.assertEqual(self.game.state.rng.draws,before.rng.draws+2)
        self.assertEqual(self.game.state.extension['command_books'],before.extension['command_books'])
        scene=self.scene(result);events=scene['soldiers']['after']['events']
        self.assertEqual([(e['actor'],e['target'],e['kind'])for e in events],[('a1','d1','melee'),('d1','a1','melee')])
        self.assertTrue(all(e['loss']>0 for e in events));self.assertEqual(scene['own'],'attackers')

    def test_reply_uses_surviving_troops_and_both_existing_guard_counters(self):
        b,actor,target=self.units();support=b['extended']['support']
        support[str(actor['id'])].update(guard=2,morale=100)
        support[str(target['id'])].update(guard=2,morale=25)
        self.prepare_contact();seen=[];original=siege._hit
        def observe(game,state,row,piece,victim,**kwargs):
            seen.append((piece['side'],piece['troops'],victim['troops'],state.battle['extended']['support'][str(siege._main(state.battle,row,piece['side'])['id'])]['morale']))
            return original(game,state,row,piece,victim,**kwargs)
        with patch('remake.siege._hit',side_effect=observe):result=self.cycle()
        b,actor,target=self.units();scene=self.scene(result);events=scene['soldiers']['after']['events']
        self.assertEqual([(r[0],r[3])for r in seen],[('attackers',100),('defenders',25)])
        self.assertEqual(seen[1][1],100-events[0]['loss'],'Killed soldiers never take part in the reply')
        self.assertEqual(b['extended']['support'][str(actor['id'])]['guard'],1)
        self.assertEqual(b['extended']['support'][str(target['id'])]['guard'],1)
        self.assertLess(next(p['troops']for p in scene['soldiers']['after']['units']if p['id']=='a1'),100)

    def test_routed_defender_cannot_reply_or_draw_a_second_damage_roll(self):
        b,actor,target=self.units();target['troops']=1
        troops,draws=actor['troops'],self.game.state.rng.draws
        self.prepare_contact();result=self.cycle();b,actor,target=self.units()
        self.assertEqual(target['troops'],0);self.assertEqual(actor['troops'],troops)
        self.assertEqual(self.game.state.rng.draws,draws+2,'Both attack bases seed once, no per-hit draws')
        self.assertEqual([e['actor']for e in self.scene(result)['soldiers']['after']['events']],['a1'])
        self.assertEqual((self.game.state.phase,b['outcome']),('result','victory'))

    def test_zero_defender_ap_does_not_disable_its_in_encounter_reply(self):
        b,actor,target=self.units();b['extended']['tactical']['points']['defenders']=0;troops=actor['troops']
        self.prepare_contact();result=self.cycle();b,actor,target=self.units()
        self.assertLess(actor['troops'],troops);self.assertEqual(b['extended']['tactical']['points']['defenders'],0)
        self.assertIn('d1',[e['actor']for e in self.scene(result)['soldiers']['after']['events']])

    def test_reply_does_not_activate_a_second_tactical_ambush_command(self):
        b,actor,target=self.units();b['extended']['ambush']=dict(actor=actor['id']);draws=self.game.state.rng.draws
        self.prepare_contact();result=self.cycle();b,actor,target=self.units()
        self.assertEqual([scene['kind']for scene in result['presentation']['scenes']],['soldier_step'])
        self.assertEqual(b['extended']['ambush'],dict(actor=actor['id']))
        self.assertEqual(self.game.state.rng.draws,draws+2)
        self.assertEqual(len(self.scene(result)['soldiers']['after']['events']),2)

    def test_reply_can_route_the_initiator_and_resolve_defeat(self):
        b,actor,target=self.units();actor['troops']=1;draws=self.game.state.rng.draws
        self.prepare_contact();result=self.cycle();b,actor,target=self.units()
        self.assertEqual(actor['troops'],0);self.assertGreater(target['troops'],0)
        self.assertEqual(self.game.state.rng.draws,draws+2)
        self.assertEqual([e['actor']for e in self.scene(result)['soldiers']['after']['events']],['a1','d1'])
        self.assertEqual((self.game.state.phase,b['outcome']),('result','defeat'))

    def test_stunned_defender_uses_its_one_skip_without_a_damage_draw(self):
        b,actor,target=self.units();b['extended']['support'][str(target['id'])]['stunned']=1
        troops,draws=actor['troops'],self.game.state.rng.draws
        self.prepare_contact();result=self.cycle();b,actor,target=self.units()
        self.assertEqual([e['actor']for e in self.scene(result)['soldiers']['after']['events']],['a1'])
        self.assertEqual(actor['troops'],troops)
        self.assertEqual(self.game.state.rng.draws,draws+2,'Seeds for both sides are independent of the skip')
        self.assertEqual(b['extended']['support'][str(target['id'])]['stunned'],0)

    def test_stunned_initiator_does_not_create_an_unprovoked_reply(self):
        b,actor,target=self.units();b['extended']['support'][str(actor['id'])]['stunned']=1
        before=deepcopy(b);draws=self.game.state.rng.draws;result=self.attack();b,actor,target=self.units()
        self.assertEqual([u['troops']for side in grid.SIDES for u in b[side]],[u['troops']for side in grid.SIDES for u in before[side]])
        self.assertEqual(self.game.state.rng.draws,draws);self.assertNotIn('siege',b['extended'])
        self.assertEqual(len(result['presentation']['scenes']),1);self.assertTrue(result['presentation']['scenes'][0]['skipped'])

    def test_ai_initiated_contact_uses_the_same_two_way_kernel(self):
        b,attacker,defender=self.units();b['extended']['tactical']['side']='defenders';before=deepcopy(self.game.state)
        self.game._perform_battle_action(self.game.state,dict(kind='attack',actor=defender['id'],target=attacker['id']),'defenders','attackers',finish=False,counter=True)
        self.assertEqual(self.game.state.rng,before.rng);self.prepare_contact(opened=True)
        with patch('remake.siege._hit',wraps=siege._hit)as damage:result=self.cycle()
        b,attacker,defender=self.units();events=self.scene(result)['soldiers']['after']['events']
        self.assertEqual(damage.call_count,2);self.assertEqual([e['actor']for e in events],['d1','a1'])
        self.assertLess(attacker['troops'],before.battle['attackers'][0]['troops']);self.assertLess(defender['troops'],before.battle['defenders'][0]['troops'])
        self.assertEqual(b['extended']['tactical']['points']['defenders'],before.battle['extended']['tactical']['points']['defenders']-2)
        self.assertEqual(b['extended']['tactical']['points']['attackers'],before.battle['extended']['tactical']['points']['attackers'])
        self.assertEqual(self.game.state.rng.draws,before.rng.draws+2)

    def test_tactics_do_not_receive_an_ordinary_contact_reply(self):
        from remake.campaign_expansion import TACTICS
        b,actor,target=self.units();troops=actor['troops'];points=deepcopy(b['extended']['tactical']['points'])
        with patch.object(self.game,'_contact_retaliation',side_effect=AssertionError('Not a melee encounter')):
            result=self.game.command('tactic',dict(battle_id=b['id'],actor=actor['id'],target=target['id'],tactic=0),self.game.revision)
        b,actor,target=self.units();self.assertEqual(actor['troops'],troops);self.assertNotIn('siege',b['extended'])
        self.assertTrue(all(scene['kind']=='tactic'for scene in result['presentation']['scenes']))
        self.assertEqual(b['extended']['tactical']['points']['attackers'],points['attackers']-TACTICS[0][1]);self.assertEqual(b['extended']['tactical']['points']['defenders'],points['defenders'])

    def test_contact_exchange_estimates_reply_risk_without_sampling_or_mutation(self):
        from remake.campaign_expansion import TACTICS
        from remake.tactical_ai import candidates,expected_contact_exchange
        b,actor,target=self.units();before=deepcopy(self.game.state)
        with patch.object(SeedRng,'next',side_effect=AssertionError('No RNG lookahead')):
            outgoing,reply=expected_contact_exchange(b,actor,target)
            row=next(row for row in candidates(self.game.state,b,'attackers','defenders','plain',TACTICS,depth=0)if row['kind']=='attack')
        self.assertGreater(outgoing,0);self.assertGreater(reply,0)
        self.assertLess(row['score'],outgoing,'AI accounts for the contact opponent replying');self.assertEqual(self.game.state,before)
        b['extended']['support'][str(target['id'])]['stunned']=1
        self.assertEqual(expected_contact_exchange(b,actor,target),(outgoing,0))

    def test_contact_save_and_stale_retry_never_repeat_retaliation(self):
        self.prepare_contact();self.cycle();saved=self.game.export_save();revision=self.game.revision
        restored=Campaign(self.game.catalog);restored.load_save(saved,0);self.assertEqual(restored.export_save(),saved)
        b,actor,target=self.units()
        with self.assertRaises(GameError):self.game.command('siege_step',dict(battle_id=b['id']),revision-1)
        self.assertEqual(self.game.export_save(),saved)
        for game in (self.game,restored):
            battle=game.state.battle;row=battle['extended']['siege']
            game.command('siege_orders',dict(battle_id=battle['id'],piece_orders=dict(row['piece_orders']['attackers'])),game.revision)
            game.command('siege_step',dict(battle_id=battle['id']),game.revision)
        self.assertEqual(restored.export_save(),self.game.export_save())


if __name__ == '__main__':
    unittest.main()
