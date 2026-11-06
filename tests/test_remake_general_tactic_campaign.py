"""Shared native gate through actual spatial commands, AI and exact saves.

Initial postings/intellect/tier and native cells are declared controlled inputs.
No success, payment, damage, generator or save validator is replaced. The old
nonspatial numerical interface is tested separately, never as a playable save.
"""
from copy import deepcopy
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import battle_grid,battle_conditions,tactic_effects,tactical_ai
from remake.campaign import Campaign,Catalog,SeedRng,digest
from remake.campaign_expansion import TACTICS
from remake.errors import GameError
from campaign_fixtures import controlled_catalog,arrange_tactic

GENERAL=tuple(i for i in range(16) if i not in (8,11))
CASTER=439
EXPERIENCE=(0,1000,2000,3500,5000,7500,10000,15000)
WAIT=dict(kind='wait',actor=None,target=None,tactic=None,score=0)


def command(game,kind,**payload):
    return game.command(kind,payload,game.revision)


def seed_for(sample):
    return next(seed for seed in range(1,10000) if SeedRng(seed).next()%100==sample)


def prepared(tid=2,own='attackers',*,intellect=99,target_intellect=60,tier=6):
    data=deepcopy(controlled_catalog().data)
    own_city='xiangyang' if own=='attackers' else 'nanyang'
    foe_city='nanyang' if own=='attackers' else 'xiangyang'
    for row in data['initial_officers']:
        if row['person_id']=='san14-candidate-0440':row['city']=own_city
        elif row['person_id'] in ('san14-candidate-0147','san14-candidate-0005'):row['city']=foe_city
        data['appearance_locations'][row['person_id']]=row['city']
    # Explicit numerical fixture, not a correction to historical catalog data.
    initial_people={row['person_id'] for row in data['initial_officers']}
    for person in data['people']:
        ident=person['runtime_id']
        if person['person_id'] in initial_people:
            person['profile']['intellect']=intellect if ident==CASTER else target_intellect
            person['profile']['basis']['intellect']='controlled shared-gate integration input'
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'shared-gate.json';path.write_text(json.dumps(data,ensure_ascii=False))
        catalog=Catalog(path)
    game=Campaign(catalog);game.state=game._new('shu' if own=='attackers' else 'wei',2026)
    state=game.state;state.officers[CASTER].experience=EXPERIENCE[tier];state.officers[CASTER].tier=tier
    selected=[CASTER] if own=='attackers' else list(state.cities['xiangyang'].roster.officer_ids)
    with patch.object(Campaign,'_run_tactical_ai_turn',return_value=None):
        game._start_expanded_battle(state,state.cities['xiangyang'],state.cities['nanyang'],selected)
    battle=state.battle;foe='defenders' if own=='attackers' else 'attackers'
    actor=next(unit for unit in battle[own] if unit['id']==CASTER)
    target=battle[foe][0]
    if tid==8:
        target=next(unit for unit in battle[foe] if unit['id'] not in state.extension['leaders'].values())
    arrange_tactic(game,tid,actor,target)
    battle['extended']['tactical']['points'][own]=20
    game.validate(state)
    return game,actor,target,own,foe


def distance(game,actor,target,value):
    """Move only the fixture caster to a free visible cell of exact distance."""
    battle=game.state.battle;positions=battle['extended']['tactical']['positions']
    point=positions[str(target['id'])]
    occupied={(p['x'],p['y']) for key,p in positions.items() if key!=str(actor['id'])}
    candidate=next((x,y) for y in range(19) for x in range(31)
        if (x,y) not in occupied and max(abs(x-point['x']),abs(y-point['y']))==value)
    positions[str(actor['id'])]=dict(x=candidate[0],y=candidate[1])
    game.validate(game.state)


class GeneralTacticCampaignTests(unittest.TestCase):
    def test_all_fourteen_failed_commands_on_both_sides_pay_only_real_ap_and_one_gate_draw(self):
        for own in battle_grid.SIDES:
            for tid in GENERAL:
                with self.subTest(side=own,tactic=tid):
                    game,actor,target,own,foe=prepared(tid,own)
                    game.state.rng=SeedRng(seed_for(99));before=deepcopy(game.state)
                    expected=deepcopy(before.rng);expected.next()
                    command(game,'tactic',battle_id=before.battle['id'],actor=actor['id'],target=target['id'],tactic=tid)
                    state,battle=game.state,game.state.battle
                    self.assertEqual(state.rng,expected)
                    self.assertEqual(battle['extended']['tactical']['points'][own],20-battle_grid.TACTIC_COSTS[tid])
                    self.assertEqual(battle['attackers'],before.battle['attackers'])
                    self.assertEqual(battle['defenders'],before.battle['defenders'])
                    self.assertEqual(battle['extended']['support'],before.battle['extended']['support'])
                    self.assertEqual(battle['extended']['supply'],before.battle['extended']['supply'])
                    self.assertEqual(state.cities,before.cities)
                    self.assertEqual(state.soldiers,before.soldiers)
                    self.assertEqual(state.extension['command_books'],before.extension['command_books'])
                    self.assertFalse(state.extension['events']['items'][-1]['details']['success'])

    def test_all_fourteen_successes_keep_existing_effect_draw_counts(self):
        # Each fixture has three enemies;7/10/12/14 connect all three.
        draws={0:2,1:2,2:1,3:2,4:2,5:2,6:2,7:4,9:2,10:4,12:4,13:2,14:4,15:2}
        for own in battle_grid.SIDES:
            for tid in GENERAL:
                with self.subTest(side=own,tactic=tid):
                    game,actor,target,own,foe=prepared(tid,own)
                    self.assertEqual(len(game.state.battle[foe]),3)
                    game.state.rng=SeedRng(seed_for(0))
                    command(game,'tactic',battle_id=game.state.battle['id'],actor=actor['id'],target=target['id'],tactic=tid)
                    self.assertEqual(game.state.rng.draws,draws[tid])
                    self.assertEqual(game.state.battle['extended']['tactical']['points'][own],20-battle_grid.TACTIC_COSTS[tid])
                    self.assertTrue(game.state.extension['events']['items'][-1]['details']['success'])

    def test_actual_distance_preview_and_ai_quote_use_native_probability(self):
        game,actor,target,own,foe=prepared()
        # Independently calculated fixed inputs:I99/60,tier6/0,shared bonus10.
        for steps,expected in ((1,71),(2,66),(3,61),(4,56),(5,51)):
            distance(game,actor,target,steps)
            self.assertEqual(tactic_effects.success_chance(game.state,game.state.battle,actor,target),expected)
            self.assertEqual(tactic_effects.preview(game.state,game.state.battle,actor,target,own,foe,2)['success_percent'],expected)
            self.assertEqual(tactical_ai._chance(game.state,actor,target,'confuse',game.state.battle),expected/100)
        self.assertEqual(tactic_effects.general_chance(game.state.officers[CASTER],game.state.officers[target['id']]),79)

    def test_signed_byte_boundary_changes_real_success_instead_of_clamping_early(self):
        # Actual profiles require intellect>=1:98-1+10+10+10=127,
        # while99-1+10+10+10=128 sets the final byte's sign bit.
        for intellect,tier,sample,expected,chance in ((98,5,94,True,95),(98,5,95,False,95),
                                                   (99,5,4,True,5),(99,5,5,False,5)):
            with self.subTest(intellect=intellect,tier=tier,sample=sample):
                game,actor,target,own,foe=prepared(intellect=intellect,target_intellect=1,tier=tier)
                self.assertEqual(tactic_effects.success_chance(game.state,game.state.battle,actor,target),chance)
                game.state.rng=SeedRng(seed_for(sample))
                command(game,'tactic',battle_id=game.state.battle['id'],actor=CASTER,target=target['id'],tactic=2)
                self.assertEqual(game.state.extension['events']['items'][-1]['details']['success'],expected)
                self.assertEqual(game.state.rng.draws,1)
                self.assertEqual(battle_conditions.remaining(game.state.battle,target['id']),3 if expected else 0)

    def test_distance_six_is_zero_pure_and_rejected_before_payment_or_rng(self):
        game,actor,target,own,foe=prepared();distance(game,actor,target,6)
        saved=game.export_save();revision=game.revision
        with patch.object(SeedRng,'next',side_effect=AssertionError('Out of range is not a roll')):
            self.assertEqual(tactic_effects.success_chance(game.state,game.state.battle,actor,target),0)
            with self.assertRaises(GameError):
                command(game,'tactic',battle_id=game.state.battle['id'],actor=CASTER,target=target['id'],tactic=2)
        self.assertEqual(game.export_save(),saved);self.assertEqual(game.revision,revision)

    def test_three_difficulties_and_observers_share_gate_without_preview_draws(self):
        game,actor,target,own,foe=prepared();distance(game,actor,target,4)
        for difficulty in ('easy','normal','hard'):
            game.state.extension['difficulty']=difficulty
            for player in ('shu','wei','wu'):
                game.state.player=player;saved=game.export_save()
                with patch.object(SeedRng,'next',side_effect=AssertionError('No candidate sampling')):
                    self.assertEqual(tactical_ai._chance(game.state,actor,target,'confuse',game.state.battle),.56)
                    self.assertEqual(tactic_effects.preview(game.state,game.state.battle,actor,target,own,foe,2)['success_percent'],56)
                    tactical_ai.candidates(game.state,game.state.battle,own,foe,'plain',TACTICS,depth=2,game=game)
                self.assertEqual(game.export_save(),saved)

    def test_actual_ai_turn_uses_same_threshold_sample_payment_and_real_side_boundary(self):
        for own in battle_grid.SIDES:
            for sample,success in ((70,True),(71,False)):
                with self.subTest(side=own,sample=sample):
                    player,actor,target,own,foe=prepared(own=own)
                    ai,aa,at,_,_=prepared(own=own)
                    ai.state.player='wei' if own=='attackers' else 'shu'
                    if own=='defenders':
                        ai.state.battle['extended']['tactical']['passed']['attackers']=True
                    player.state.rng=SeedRng(seed_for(sample));ai.state.rng=SeedRng(seed_for(sample))
                    command(player,'tactic',battle_id=player.state.battle['id'],actor=CASTER,target=target['id'],tactic=2)
                    choice=dict(kind='tactic',actor=CASTER,target=at['id'],tactic=2,score=1)
                    with patch('remake.tactical_ai.choose_action',side_effect=[choice,WAIT]):
                        ai._run_tactical_ai_turn(ai.state)
                    self.assertEqual(ai.state.rng,player.state.rng)
                    full_day=own=='defenders'
                    self.assertEqual(ai.state.battle['extended']['tactical']['points'][own],20 if full_day else 16)
                    self.assertEqual(ai.state.battle['extended']['tactical']['side'],foe)
                    self.assertEqual(ai.state.battle['round'],2 if full_day else 1)
                    self.assertEqual(ai.state.battle['extended']['supply']['days'],int(full_day))
                    self.assertEqual(ai.state.extension['events']['items'][-1]['details']['success'],success)
                    self.assertEqual(ai.state.battle['attackers'],player.state.battle['attackers'])
                    self.assertEqual(ai.state.battle['defenders'],player.state.battle['defenders'])
                    self.assertEqual(battle_conditions.remaining(ai.state.battle,at['id']),
                                     (1 if full_day else 3) if success else 0)
                    ai.validate(ai.state)

    def test_save_load_and_same_distance_continuation_keep_full_state_and_rng(self):
        game,actor,target,own,foe=prepared();distance(game,actor,target,5)
        game.state.rng=SeedRng(seed_for(70))  # Old79% would pass;native51% fails.
        command(game,'tactic',battle_id=game.state.battle['id'],actor=CASTER,target=target['id'],tactic=2)
        self.assertFalse(game.state.extension['events']['items'][-1]['details']['success'])
        saved=game.export_save();loaded=Campaign(game.catalog)
        with patch.object(SeedRng,'next',side_effect=AssertionError('No load draw')):
            loaded.load_save(deepcopy(saved),0)
        self.assertEqual(loaded.export_save(),saved)
        for current in (game,loaded):
            command(current,'tactic',battle_id=current.state.battle['id'],actor=CASTER,target=target['id'],tactic=2)
        self.assertEqual(game.export_save(),loaded.export_save())
        self.assertEqual(game.state.rng,loaded.state.rng)

    def test_conversion_is_independent_and_loyal71_still_costs_ap_without_rng(self):
        for loyalty,sample,success,draws in ((70,40,True,1),(70,41,False,1),(71,0,False,0)):
            game,actor,target,own,foe=prepared(8)
            game.state.officers[target['id']].loyalty=loyalty
            self.assertEqual(game.state.officers[CASTER].profile.virtue,93)
            self.assertEqual(tactic_effects.preview(game.state,game.state.battle,actor,target,own,foe,8)['success_percent'],41 if loyalty==70 else 0)
            game.state.rng=SeedRng(seed_for(sample))
            command(game,'tactic',battle_id=game.state.battle['id'],actor=CASTER,target=target['id'],tactic=8)
            self.assertEqual(game.state.rng.draws,draws)
            self.assertEqual(game.state.battle['extended']['tactical']['points'][own],10)
            result=next(event for event in reversed(game.state.extension['events']['items']) if event['kind']=='tactic')
            self.assertEqual(result['details']['success'],success)

    def test_ambush_remains_guaranteed_and_legacy_guard_retains_old_no_draw_model(self):
        game,actor,target,own,foe=prepared(11)
        before=deepcopy(game.state.rng)
        command(game,'tactic',battle_id=game.state.battle['id'],actor=CASTER,target=target['id'],tactic=11)
        self.assertEqual(game.state.rng,before)
        self.assertEqual(game.state.battle['extended']['ambush'],dict(actor=CASTER))
        self.assertEqual(game.state.battle['extended']['tactical']['points'][own],10)
        # Internal pre-grid numerical interface only,not exported/playable.
        game,actor,target,own,foe=prepared(15)
        battle=game.state.battle;battle['extended'].pop('tactical')
        before=deepcopy(game.state.rng);energy=battle['extended']['support'][str(CASTER)]['energy']
        self.assertEqual(tactical_ai._chance(game.state,actor,target,'guard',battle),1)
        self.assertEqual(tactical_ai._chance(game.state,actor,target,'fire',battle),.79)
        game._execute_tactic(game.state,actor,target,own,foe,15,finish=False)
        self.assertEqual(game.state.rng,before)
        self.assertEqual(battle['extended']['support'][str(CASTER)]['guard'],2)
        self.assertEqual(battle['extended']['support'][str(CASTER)]['energy'],energy-TACTICS[15][1])


if __name__=='__main__':unittest.main()
