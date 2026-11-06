"""Qimen public casts, real daily services, lifecycle and canonical save edges.

Real catalogue Zhuge Liang tier6 and native cells qualify ID15. The reused
controlled army fixture and explicit prior-condition/route boundaries are not
historical postings or natural-play claims. AP, actual seeded draws, day/food,
XP, casualty settlement, events and production validation are never stubbed.
Only an AI policy choosing WAIT isolates completed-day tests.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import battle_conditions as conditions,battle_grid,battle_supply,battle_allegiance,tactical_ai
from remake.campaign import Campaign,SeedRng
from remake.errors import GameError
from remake.officers import experience_tier
from campaign_fixtures import arrange_contact
from test_remake_chain_campaign import prepared as chain_prepared,command,seed_for,wait_day,rehash,ZHU_GE


def prepared(own='attackers'):
    game,roles,own,foe=chain_prepared(own);battle=game.state.battle
    assert tactical_ai.maximum_tactic(game.state.officers[ZHU_GE])==15
    positions=battle['extended']['tactical']['positions']
    positions[str(ZHU_GE)]=dict(x=1,y=2)
    positions[str(roles['center'])]=dict(x=3,y=2)
    assert battle_grid._field(battle)['classes'][2][3]==2
    game.validate(game.state)
    return game,roles,own,foe


def cast(game,roles,*,success=True):
    game.state.rng=SeedRng(seed_for(success))
    return command(game,'tactic',battle_id=game.state.battle['id'],actor=ZHU_GE,
                   target=roles['center'],tactic=15)


def unit(battle,ident):
    return next(u for side in battle_grid.SIDES for u in battle[side]if u['id']==ident)


def daily_event(game):
    return next(event for event in reversed(game.state.extension['events']['items'])
                if event['kind']=='tactic'and event['details'].get('qimen_phase')=='daily')


def expected_ticks(battle,identifiers,rng):
    """Explicit supplied order, original bounded arithmetic, no engine helper."""
    result=[]
    for ident in identifiers:
        before=unit(battle,ident)['troops'];requested=80+rng.next()%71
        after=max(0,before-requested)
        result.append(dict(id=str(ident),before=conditions.remaining(battle,ident),
            remaining=conditions.remaining(battle,ident)-1,troops_before=before,
            troops_after=after,loss=before-after))
    return result


class QimenCampaignTests(unittest.TestCase):
    def test_both_sides_pay_ten_ap_two_draws_and_create_only_target_qimen(self):
        for own in battle_grid.SIDES:
            with self.subTest(side=own):
                game,roles,own,_=prepared(own);battle=game.state.battle
                battle['extended']['support'][str(roles['center'])].update(stunned=1,guard=2)
                battle['extended']['support'][str(ZHU_GE)]['guard']=1
                game.state.rng=SeedRng(seed_for());before=deepcopy(game.state)
                rng=deepcopy(game.state.rng);rng.next();count=(6 if own=='attackers'else 5)+rng.next()%4
                order=[str(u['id'])for side in('defenders','attackers')for u in battle[side]]
                command(game,'tactic',battle_id=battle['id'],actor=ZHU_GE,target=roles['center'],tactic=15)
                state,battle=game.state,game.state.battle
                self.assertEqual(state.rng,rng);self.assertEqual(state.rng.draws,2)
                self.assertEqual(battle['extended']['tactical']['points'][own],10)
                self.assertEqual(conditions.view(battle),dict(schema=conditions.SCHEMA,day=1,
                    units={str(roles['center']):dict(kind='qimen',remaining=count)},high_order=order))
                self.assertEqual((battle['attackers'],battle['defenders']),(before.battle['attackers'],before.battle['defenders']))
                self.assertEqual(battle['extended']['support'],before.battle['extended']['support'])
                self.assertEqual(battle['extended']['supply'],before.battle['extended']['supply'])
                self.assertEqual(state.officers,before.officers);self.assertEqual(state.soldiers,before.soldiers)
                self.assertEqual(state.extension['events']['items'][-1]['details'],
                    dict(tactic=15,success=True,condition='qimen',condition_count=count,qimen_phase='cast'))
                game.validate(state)

    def test_failed_cast_has_one_draw_clears_selected_but_never_creates_high_order(self):
        game,roles,own,_=prepared();battle=game.state.battle
        conditions.apply(battle,roles['center'],own);conditions.apply_chain(battle,roles['near'],own,1)
        before=deepcopy(conditions.view(battle));support=deepcopy(battle['extended']['support'])
        with patch('remake.battle_conditions.apply_qimen',side_effect=AssertionError('A failed cast cannot apply')):
            cast(game,roles,success=False)
        before['units'].pop(str(roles['center']))
        self.assertEqual(conditions.view(game.state.battle),before)
        self.assertNotIn('high_order',conditions.view(game.state.battle))
        self.assertEqual(game.state.rng.draws,1)
        self.assertEqual(game.state.battle['extended']['tactical']['points'][own],10)
        self.assertEqual(game.state.battle['extended']['support'],support)
        self.assertEqual(game.state.extension['events']['items'][-1]['details'],
            dict(tactic=15,success=False,condition='qimen',condition_count=0,qimen_phase='cast'))
        game.validate(game.state)

    def test_rejected_before_ten_ap_preserves_state_rng_and_revision(self):
        game,roles,own,_=prepared();conditions.apply_chain(game.state.battle,roles['center'],own,1)
        game.state.battle['extended']['tactical']['points'][own]=9
        before,revision=game.export_save(),game.revision
        with self.assertRaises(GameError):
            command(game,'tactic',battle_id=game.state.battle['id'],actor=ZHU_GE,target=roles['center'],tactic=15)
        self.assertEqual(game.export_save(),before);self.assertEqual(game.revision,revision)

    def test_real_full_days_use_fixed_order_one_draw_each_and_sum_post_loss_bytes_before_half(self):
        game,roles,own,_=prepared();cast(game,roles);battle=game.state.battle
        conditions.apply_qimen(battle,roles['leaf'],own,1);conditions.apply_qimen(battle,roles['near'],own,2)
        # Initial defender order is near,leaf,...,center; neither numeric ID
        # order nor insertion order of the condition dict has this sequence.
        order=[roles[k]for k in('near','leaf','center')]
        self.assertNotEqual(order,sorted(order))
        for seed in range(1,100):
            probe=SeedRng(seed);ticks=expected_ticks(battle,order,probe)
            values=[tick['troops_after']%256 for tick in ticks]
            if sum(values)//2!=sum(v//2 for v in values):break
        else:self.fail('No odd-byte aggregation boundary')
        game.state.rng=SeedRng(seed);rng=deepcopy(game.state.rng)
        ticks=expected_ticks(battle,order,rng)
        before_exp=game.state.officers[ZHU_GE].experience
        profile=deepcopy(game.state.officers[ZHU_GE].profile)
        health=deepcopy(battle['extended']['support'])
        wait_day(game);battle=game.state.battle
        gain=sum(tick['troops_after']%256 for tick in ticks)//2
        self.assertEqual(game.state.rng,rng);self.assertEqual(game.state.rng.draws,3)
        self.assertEqual(game.state.officers[ZHU_GE].experience,before_exp+gain)
        self.assertEqual(game.state.officers[ZHU_GE].tier,experience_tier(before_exp+gain))
        self.assertEqual(game.state.officers[ZHU_GE].profile,profile)
        self.assertEqual(battle['extended']['support'],health)
        self.assertEqual(daily_event(game)['details'],dict(tactic=15,success=True,condition='qimen',
            qimen_phase='daily',qimen_ticks=ticks,experience_id=str(ZHU_GE),experience_gain=gain))
        for tick in ticks:
            self.assertEqual(unit(battle,int(tick['id']))['troops'],tick['troops_after'])
            self.assertEqual(conditions.remaining(battle,tick['id']),tick['remaining'])
        saved=game.export_save();self.assertEqual(conditions.advance_daily(game.state,battle),[])
        self.assertEqual(game.export_save(),saved)
        game.validate(game.state)

    def test_half_day_does_not_damage_or_draw_then_defender_end_does(self):
        game,roles,_,_=prepared();cast(game,roles);before=deepcopy(game.state)
        with patch.object(Campaign,'_run_tactical_ai_turn',return_value=None):
            command(game,'battle_wait',battle_id=game.state.battle['id'])
        self.assertEqual(game.state.rng,before.rng)
        self.assertEqual(conditions.view(game.state.battle),conditions.view(before.battle))
        self.assertEqual(game.state.battle['defenders'],before.battle['defenders'])
        self.assertEqual(game.state.battle['round'],1)
        with patch('remake.tactical_ai.choose_action',return_value=dict(kind='wait',actor=None,target=None,tactic=None,score=0)):
            game._run_tactical_ai_turn(game.state)
        self.assertEqual(game.state.battle['round'],2)
        self.assertEqual(game.state.rng.draws,before.rng.draws+1)
        self.assertEqual(conditions.remaining(game.state.battle,roles['center']),
                         conditions.remaining(before.battle,roles['center'])-1)

    def test_zero_soldier_target_still_in_slot_keeps_ticking_and_drawing(self):
        game,roles,_,_=prepared();cast(game,roles);battle=game.state.battle
        # Prior casualties are an explicit bounded fixture; the actual next
        # daily service must saturate, retain the slot and later sample at0.
        unit(battle,roles['center'])['troops']=1
        before_count=conditions.remaining(battle,roles['center']);before_draws=game.state.rng.draws
        wait_day(game);battle=game.state.battle
        self.assertEqual(unit(battle,roles['center'])['troops'],0)
        self.assertEqual(conditions.remaining(battle,roles['center']),before_count-1)
        self.assertEqual(game.state.rng.draws,before_draws+1)
        self.assertEqual(daily_event(game)['details']['qimen_ticks'][0]['loss'],1)
        wait_day(game);battle=game.state.battle
        self.assertEqual(conditions.remaining(battle,roles['center']),before_count-2)
        self.assertEqual(game.state.rng.draws,before_draws+2)
        tick=daily_event(game)['details']['qimen_ticks'][0]
        self.assertEqual((tick['troops_before'],tick['troops_after'],tick['loss']),(0,0,0))
        game.validate(game.state)

    def test_last_counter_still_applies_damage_before_expiring(self):
        game,roles,_,_=prepared();cast(game,roles);battle=game.state.battle
        battle['extended']['conditions']['units'][str(roles['center'])]['remaining']=1
        rng=deepcopy(game.state.rng);request=80+rng.next()%71;before=unit(battle,roles['center'])['troops']
        wait_day(game);battle=game.state.battle
        self.assertEqual(unit(battle,roles['center'])['troops'],max(0,before-request))
        self.assertEqual(conditions.remaining(battle,roles['center']),0)
        self.assertEqual(game.state.rng,rng)
        self.assertEqual(daily_event(game)['details']['qimen_ticks'][0]['remaining'],0)
        rng=deepcopy(game.state.rng);wait_day(game)
        self.assertEqual(game.state.rng,rng)
        game.validate(game.state)

    def test_zero_soldier_hp_one_source_still_drives_damage_and_experience(self):
        game,roles,_,_=prepared('defenders');cast(game,roles);battle=game.state.battle
        unit(battle,ZHU_GE)['troops']=0;battle['extended']['support'][str(ZHU_GE)]['health']=1
        self.assertEqual(conditions.qimen_source(game.state,battle),ZHU_GE)
        # Select a real seeded nonlethal first loss so this case also proves
        # positive XP still goes to the present zero-soldier commander.
        game.state.rng=SeedRng(next(seed for seed in range(1,100)if SeedRng(seed).next()%71<39))
        before_exp=game.state.officers[ZHU_GE].experience;draws=game.state.rng.draws
        wait_day(game)
        self.assertEqual(game.state.rng.draws,draws+1)
        self.assertGreater(game.state.officers[ZHU_GE].experience,before_exp)
        self.assertEqual(conditions.qimen_source(game.state,game.state.battle),ZHU_GE)
        game.validate(game.state)

    def test_absent_or_surrendered_source_pauses_high_but_low_clock_still_runs(self):
        for mode in('absent','surrendered'):
            with self.subTest(mode=mode):
                game,roles,own,_=prepared('defenders');cast(game,roles);battle=game.state.battle
                conditions.apply(battle,roles['near'],own)
                if mode=='absent':
                    battle['defenders'].remove(unit(battle,ZHU_GE))
                    battle['extended']['support'].pop(str(ZHU_GE))
                    battle['extended']['tactical']['positions'].pop(str(ZHU_GE))
                    battle['used'][:]=[ident for ident in battle['used']if ident!=ZHU_GE]
                    conditions.drop_removed(battle)  # Actual removed-slot boundary prunes order.
                else:
                    commander=unit(battle,ZHU_GE);commander['troops']=0
                    battle['extended']['surrenders'][str(ZHU_GE)]=commander['start']
                game._reconcile_factions(game.state);game.validate(game.state)
                self.assertIsNone(conditions.qimen_source(game.state,battle))
                before=deepcopy(game.state);count=conditions.remaining(battle,roles['center'])
                wait_day(game);battle=game.state.battle
                self.assertEqual(game.state.rng,before.rng)
                self.assertEqual(game.state.officers[ZHU_GE].experience,before.officers[ZHU_GE].experience)
                self.assertEqual(conditions.remaining(battle,roles['center']),count)
                self.assertEqual(conditions.remaining(battle,roles['near']),1)
                self.assertEqual(unit(battle,roles['center'])['troops'],unit(before.battle,roles['center'])['troops'])
                game.validate(game.state)

    def test_source_conversion_keeps_high_order_and_effect_and_exact_saved_continuation(self):
        game,roles,own,foe=prepared('defenders');cast(game,roles);battle=game.state.battle
        order=deepcopy(conditions.view(battle)['high_order'])
        battle_allegiance.convert(game,game.state,battle,battle[foe][0],unit(battle,ZHU_GE),foe,own)
        game._reconcile_factions(game.state);game.validate(game.state)
        self.assertEqual(conditions.qimen_source(game.state,battle),ZHU_GE)
        self.assertEqual(conditions.view(battle)['high_order'],order)
        saved=game.export_save();restored=Campaign(game.catalog)
        restored.load_save(json.loads(json.dumps(saved)),0)
        self.assertEqual(restored.export_save(),saved)
        self.assertEqual(conditions.view(restored.state.battle)['high_order'],order)
        response=wait_day(game);wait_day(restored)
        self.assertEqual(restored.export_save(),game.export_save())
        self.assertEqual(conditions.view(game.state.battle)['high_order'],order)
        self.assertEqual(game.state.rng.draws,saved['state']['rng']['draws']+1)
        # The real fixed beneficiary is now on the affected target's side.
        # Its daily receipt must remain distinct from an enemy-targeted cast;
        # otherwise the browser discards a legitimate same-side daily scene.
        scenes=[scene for scene in response['presentation']['scenes']if scene['effect']=='qimen_daily']
        self.assertEqual(len(scenes),1)
        scene=scenes[0]
        self.assertEqual((scene['kind'],scene['tactic'],scene['actor'],scene['target']),
                         ('tactic',15,ZHU_GE,roles['center']))
        self.assertTrue(scene['success']);self.assertFalse(scene['skipped'])
        before={row['id']:row for row in scene['before']['units']}
        self.assertEqual(before[ZHU_GE]['side'],before[roles['center']]['side'])
        self.assertEqual(scene['own'],before[ZHU_GE]['side'])

    def test_xp_caps_and_current_tier_sync_without_profile_or_battle_war_growth(self):
        for experience in(999,49998):
            with self.subTest(experience=experience):
                game,roles,_,_=prepared();cast(game,roles);state,battle=game.state,game.state.battle
                # Explicit legal growth boundary after an already-set effect.
                state.officers[ZHU_GE].experience=experience
                state.officers[ZHU_GE].tier=experience_tier(experience)
                profile=deepcopy(state.officers[ZHU_GE].profile);war=unit(battle,ZHU_GE)['martial']
                rng=deepcopy(state.rng);tick=expected_ticks(battle,[roles['center']],rng)[0]
                expected=min(49999,experience+(tick['troops_after']%256)//2)
                wait_day(game);state,battle=game.state,game.state.battle
                self.assertEqual(state.officers[ZHU_GE].experience,expected)
                self.assertEqual(state.officers[ZHU_GE].tier,experience_tier(expected))
                self.assertEqual(state.officers[ZHU_GE].profile,profile)
                self.assertEqual(unit(battle,ZHU_GE)['martial'],war)
                self.assertEqual(daily_event(game)['details']['experience_gain'],expected-experience)
                game.validate(state)

    def test_food_or_thirty_day_end_precedes_high_damage_rng_and_daily_event(self):
        for mode in('food','timeout'):
            with self.subTest(mode=mode):
                game,roles,own,_=prepared()
                if mode=='timeout':
                    for _ in range(29):wait_day(game)
                cast(game,roles);battle=game.state.battle
                if mode=='food':battle_supply.destroy(game.state,battle,own,battle['extended']['supply']['sides'][own]['remaining'])
                before=deepcopy(game.state);count=len(game.state.extension['events']['items'])
                wait_day(game)
                self.assertEqual(game.state.phase,'result')
                self.assertEqual(game.state.rng,before.rng)
                self.assertEqual(conditions.view(game.state.battle),conditions.view(before.battle))
                self.assertEqual(game.state.battle['defenders'],before.battle['defenders'])
                self.assertEqual(game.state.officers[ZHU_GE].experience,before.officers[ZHU_GE].experience)
                self.assertFalse(any(e['details'].get('qimen_phase')=='daily'for e in game.state.extension['events']['items'][count:]))
                game.validate(game.state)

    def test_qimen_only_blocks_movement_not_attack_tactic_or_direct_duel(self):
        for action in('attack','tactic','duel_start'):
            with self.subTest(action=action):
                game,roles,own,_=prepared();battle=game.state.battle
                conditions.apply_qimen(battle,ZHU_GE,'defenders',0)
                info=game.view()['catalog']['battle_tactical']['actors'][str(ZHU_GE)]
                self.assertTrue(info['can_act']);self.assertEqual(info['reachable'],[])
                saved=game.export_save()
                with self.assertRaises(GameError):command(game,'battle_move',battle_id=battle['id'],actor=ZHU_GE,x=2,y=2)
                self.assertEqual(game.export_save(),saved)
                if action=='tactic':cast(game,roles)
                else:
                    arrange_contact(game,actor=ZHU_GE,target=roles['center'])
                    game.state.rng=SeedRng(seed_for())
                    command(game,action,battle_id=battle['id'],actor=ZHU_GE,target=roles['center'])
                self.assertEqual(conditions.remaining(game.state.battle,ZHU_GE),5)
                if action=='attack':self.assertEqual(game.state.battle['extended']['siege']['stage'],'formation')
                elif action=='duel_start':self.assertIsNotNone(game.state.battle['extended']['duel'])
                game.validate(game.state)

    def test_recast_overwrites_and_contact_or_failed_other_tactic_clears_target_but_duel_does_not(self):
        for action in('recast','attack','tactic','duel_start'):
            with self.subTest(action=action):
                game,roles,_,_=prepared();cast(game,roles);battle=game.state.battle
                original=conditions.remaining(battle,roles['center']);order=deepcopy(conditions.view(battle)['high_order'])
                if action=='recast':
                    with patch.object(Campaign,'_run_tactical_ai_turn',return_value=None):cast(game,roles)
                    self.assertEqual(conditions.remaining(game.state.battle,roles['center']),original)
                elif action=='tactic':
                    # Another legal failed cast still clears before adjudication.
                    game.state.rng=SeedRng(seed_for(False))
                    command(game,'tactic',battle_id=battle['id'],actor=ZHU_GE,target=roles['center'],tactic=0)
                    self.assertEqual(conditions.remaining(game.state.battle,roles['center']),0)
                    self.assertEqual(game.state.rng.draws,1)
                else:
                    arrange_contact(game,actor=ZHU_GE,target=roles['center'])
                    game.state.rng=SeedRng(seed_for())
                    command(game,action,battle_id=battle['id'],actor=ZHU_GE,target=roles['center'])
                    self.assertEqual(conditions.remaining(game.state.battle,roles['center']),original if action=='duel_start'else 0)
                self.assertEqual(conditions.view(game.state.battle)['high_order'],order)
                game.validate(game.state)

    def test_day_casualties_are_settled_once_in_the_strategic_soldier_account(self):
        game,roles,_,_=prepared();cast(game,roles);before_lost=game.state.soldiers['lost']
        wait_day(game);battle=game.state.battle
        loss=sum(u['start']-u['troops']for side in battle_grid.SIDES for u in battle[side])
        self.assertGreater(loss,0);self.assertEqual(game.state.soldiers['lost'],before_lost)
        battle_id=battle['id'];command(game,'retreat',battle_id=battle_id)
        command(game,'settle',battle_id=battle_id)
        self.assertEqual(game.state.soldiers['lost'],before_lost+loss)
        saved=game.export_save();command(game,'settle',battle_id=battle_id)
        self.assertEqual(game.export_save(),saved)
        game.validate(game.state)

    def test_rehashed_bad_qimen_order_or_count_and_missing_grid_are_rejected_atomically(self):
        game,roles,_,_=prepared();cast(game,roles);saved=game.export_save();revision=game.revision
        for problem in('missing_order','duplicate_order','unknown_order','integer_order','short_order',
                       'kind','zero','count10','float_count','bool_count','extra_field','missing_grid'):
            with self.subTest(problem=problem):
                invalid=deepcopy(saved);extended=invalid['state']['battle']['extended'];row=extended['conditions']
                target=row['units'][str(roles['center'])]
                if problem=='missing_order':row.pop('high_order')
                elif problem=='duplicate_order':row['high_order'][1]=row['high_order'][0]
                elif problem=='unknown_order':row['high_order'][0]='not-a-participant'
                elif problem=='integer_order':row['high_order'][0]=int(row['high_order'][0])
                elif problem=='short_order':row['high_order'].pop()
                elif problem=='kind':target['kind']='unknown'
                elif problem=='zero':target['remaining']=0
                elif problem=='count10':target['remaining']=10
                elif problem=='float_count':target['remaining']=5.0
                elif problem=='bool_count':target['remaining']=True
                elif problem=='extra_field':target['requested']=80
                else:extended.pop('tactical');extended.pop('deployment',None)
                with self.assertRaises(GameError):game.load_save(rehash(invalid),game.revision)
                self.assertEqual(game.export_save(),saved);self.assertEqual(game.revision,revision)

    def test_old_guard_and_low_conditions_do_not_create_or_infer_qimen_on_load(self):
        game,roles,own,_=prepared();battle=game.state.battle
        battle['extended']['support'][str(ZHU_GE)].update(guard=2)
        battle['extended']['support'][str(roles['center'])].update(stunned=1,guard=1)
        conditions.apply(battle,roles['center'],own);conditions.apply_chain(battle,roles['near'],own,1)
        saved=game.export_save();restored=Campaign(game.catalog);restored.load_save(deepcopy(saved),0)
        self.assertEqual(restored.export_save(),saved)
        self.assertNotIn('high_order',conditions.view(restored.state.battle))
        self.assertTrue(all(row['kind']!='qimen'for row in conditions.view(restored.state.battle)['units'].values()))
        restored.view();restored.validate(restored.state)
        self.assertEqual(restored.export_save(),saved)


if __name__=='__main__':unittest.main()
