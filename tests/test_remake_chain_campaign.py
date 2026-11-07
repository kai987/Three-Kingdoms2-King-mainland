"""Real ID10 transactions over native terrain, with explicit controlled armies.

Only initial postings, learned Zhuge Liang tier and battlefield cells are test
fixtures. Actual cast qualification, paid confirmation, seeded draws, connected
water traversal, condition service, day/meal hooks, events and save validation
remain enabled. A waiting policy isolates calendar tests without faking a day.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import battle_conditions as conditions,battle_grid,battle_supply,tactical_ai,battle_allegiance
from remake.campaign import Campaign,Catalog,SeedRng,digest
from remake.errors import GameError
from campaign_fixtures import controlled_catalog,arrange_contact

WAIT=dict(kind='wait',actor=None,target=None,tactic=None,score=0)
ZHU_GE=439


def command(game,kind,**payload):
    return game.command(kind,payload,game.revision)


def seed_for(success=True):
    return next(seed for seed in range(1,10000)
                if (SeedRng(seed).next()%100<5 if success else SeedRng(seed).next()%100>=95))


def prepared(own='attackers'):
    """An actual learned ID10 caster; no skill or damage service is mocked."""
    data=deepcopy(controlled_catalog().data)
    own_city='xiangyang'if own=='attackers'else'nanyang'
    foe_city='nanyang'if own=='attackers'else'xiangyang'
    for row in data['initial_officers']:
        if row['person_id']=='san14-candidate-0440':row['city']=own_city
        elif not row['ruler']:row['city']=foe_city
    # Two genuine catalogue identities make six opponents. These are declared
    # transaction postings, never a correction to the historical217 scenario.
    for pid in ('san14-candidate-0521','san14-candidate-0442'):
        data['initial_officers'].append(dict(person_id=pid,city=foe_city,troops=300,ruler=False))
    for row in data['initial_officers']:data['appearance_locations'][row['person_id']]=row['city']
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'chain-controlled.json'
        path.write_text(json.dumps(data,ensure_ascii=False))
        catalog=Catalog(path)
    game=Campaign(catalog);game.state=game._new('shu'if own=='attackers'else'wei',2026)
    state=game.state;state.officers[ZHU_GE].experience=10000;state.officers[ZHU_GE].tier=6
    source,target=state.cities['xiangyang'],state.cities['nanyang']
    selected=[ZHU_GE]if own=='attackers'else list(source.roster.officer_ids)
    with patch.object(Campaign,'_run_tactical_ai_turn',return_value=None):
        game._start_expanded_battle(state,source,target,selected)
    battle=state.battle;foe='defenders'if own=='attackers'else'attackers'
    opponents=battle[foe]
    assert len(opponents)==6
    assert tactical_ai.maximum_tactic(state.officers[ZHU_GE])>=10
    # Real original13 water cells. The leaf(12,2) has no adjacent occupied
    # water except through the non-water bridge(12,1). The near-water(11,0)
    # cannot reach that leaf on its own. BFS is center,bridge,near,leaf;
    # returned water order center,near,leaf deliberately differs from roster.
    roles=dict(center=opponents[3]['id'],near=opponents[0]['id'],bridge=opponents[4]['id'],
               leaf=opponents[1]['id'],disconnected=opponents[2]['id'],remote=opponents[5]['id'])
    points=dict(center=(11,1),near=(11,0),bridge=(12,1),leaf=(12,2),
                disconnected=(24,6),remote=(28,7))
    field=battle_grid._field(battle)
    for role in ('center','near','leaf','disconnected','remote'):
        x,y=points[role];assert field['classes'][y][x]==3,(role,points[role])
    assert field['classes'][1][12]not in(3,5)
    positions=battle['extended']['tactical']['positions']
    for role,ident in roles.items():
        x,y=points[role];positions[str(ident)]=dict(x=x,y=y)
    positions[str(ZHU_GE)]=dict(x=9,y=1)
    for unit in battle[own]:
        if unit['id']!=ZHU_GE:positions[str(unit['id'])]=dict(x=1,y=1)
    row=battle['extended']['tactical'];row['side']=own;row['points'][own]=20
    row['passed']={side:side=='attackers'and own=='defenders'for side in battle_grid.SIDES}
    game.validate(state)
    return game,roles,own,foe


def cast(game,roles,*,success=True):
    game.state.rng=SeedRng(seed_for(success))
    return command(game,'tactic',battle_id=game.state.battle['id'],actor=ZHU_GE,
                   target=roles['center'],tactic=10)


def expected_counts(rng,own,roles):
    """Explicit observed BFS-water order; never derives order from engine BFS."""
    rng.next()  # One general success gate.
    base=4 if own=='attackers'else 3
    return [(roles[role],base+rng.next()%2)for role in('center','near','leaf')]


def wait_day(game):
    with patch('remake.tactical_ai.choose_action',return_value=WAIT):
        return command(game,'battle_wait',battle_id=game.state.battle['id'])


def rehash(saved):
    saved['checksum']=digest({key:value for key,value in saved.items()if key!='checksum'})
    return saved


class ChainCampaignTests(unittest.TestCase):
    def test_both_sides_pay_nine_ap_and_one_gate_then_one_draw_per_bfs_water_target(self):
        for own in battle_grid.SIDES:
            with self.subTest(side=own):
                game,roles,own,foe=prepared(own);battle=game.state.battle
                for unit in battle[foe]:battle['extended']['support'][str(unit['id'])].update(stunned=1,guard=2)
                game.state.rng=SeedRng(seed_for());before=deepcopy(game.state)
                expected_rng=deepcopy(game.state.rng);counts=expected_counts(expected_rng,own,roles)
                command(game,'tactic',battle_id=battle['id'],actor=ZHU_GE,target=roles['center'],tactic=10)
                state,battle=game.state,game.state.battle
                self.assertEqual(state.rng,expected_rng);self.assertEqual(state.rng.draws,4)
                self.assertEqual(battle['extended']['tactical']['points'][own],11)
                self.assertEqual([conditions.remaining(battle,ident)for ident,_ in counts],[count for _,count in counts])
                self.assertTrue(all(conditions.kind(battle,ident)=='chain'for ident,_ in counts))
                self.assertEqual(battle['attackers'],before.battle['attackers'])
                self.assertEqual(battle['defenders'],before.battle['defenders'])
                self.assertEqual(battle['extended']['support'],before.battle['extended']['support'])
                self.assertEqual(battle['extended']['supply'],before.battle['extended']['supply'])
                self.assertEqual(state.officers,before.officers);self.assertEqual(state.soldiers,before.soldiers)
                self.assertEqual(state.extension['command_books'],before.extension['command_books'])
                self.assertEqual({k:(c.gold,c.grain,c.reserves)for k,c in state.cities.items()},
                                 {k:(c.gold,c.grain,c.reserves)for k,c in before.cities.items()})
                event=state.extension['events']['items'][-1]
                self.assertEqual(event['details'],dict(tactic=10,success=True,condition='chain',
                    condition_counts=[dict(id=str(ident),remaining=count)for ident,count in counts]))
                self.assertEqual(conditions.remaining(battle,roles['bridge']),0)
                self.assertEqual(conditions.remaining(battle,roles['disconnected']),0)
                game.validate(state)

    def test_secondary_water_phantom_is_overwritten_without_preclear_but_bridge_is_untouched(self):
        game,roles,own,_=prepared();battle=game.state.battle
        for role in ('center','near','bridge','leaf'):conditions.apply(battle,roles[role],own)
        conditions.apply_chain(battle,roles['disconnected'],own,1)
        initial=deepcopy(conditions.view(battle));seen=[];real=conditions.apply_chain
        def observe(current,ident,side,roll):
            seen.append((ident,conditions.kind(current,ident),conditions.remaining(current,ident)))
            return real(current,ident,side,roll)
        with patch('remake.battle_conditions.apply_chain',side_effect=observe):cast(game,roles)
        battle=game.state.battle
        self.assertEqual(seen,[(roles['center'],None,0),(roles['near'],'phantom',3),(roles['leaf'],'phantom',3)])
        self.assertEqual(conditions.view(battle)['units'][str(roles['bridge'])],initial['units'][str(roles['bridge'])])
        self.assertEqual(conditions.view(battle)['units'][str(roles['disconnected'])],initial['units'][str(roles['disconnected'])])
        self.assertEqual(game.state.rng.draws,4)
        game.validate(game.state)

    def test_failed_gate_only_clears_selected_and_never_samples_a_duration(self):
        game,roles,own,_=prepared();battle=game.state.battle
        for role in ('center','near','bridge','leaf'):conditions.apply(battle,roles[role],own)
        before=deepcopy(conditions.view(battle));support=deepcopy(battle['extended']['support'])
        with patch('remake.battle_conditions.apply_chain',side_effect=AssertionError('Failed gate cannot apply chain')):
            cast(game,roles,success=False)
        expected=deepcopy(before);expected['units'].pop(str(roles['center']))
        self.assertEqual(conditions.view(game.state.battle),expected)
        self.assertEqual(game.state.rng.draws,1)
        self.assertEqual(game.state.battle['extended']['tactical']['points'][own],11)
        self.assertEqual(game.state.battle['extended']['support'],support)
        self.assertEqual(game.state.extension['events']['items'][-1]['details'],
                         dict(tactic=10,success=False,condition='chain',condition_counts=[]))
        game.validate(game.state)

    def test_rejected_before_payment_preserves_selected_state_rng_and_revision(self):
        game,roles,own,_=prepared();conditions.apply(game.state.battle,roles['center'],own)
        game.state.battle['extended']['tactical']['points'][own]=8
        game.state.rng=SeedRng(seed_for())
        saved,revision=game.export_save(),game.revision
        with self.assertRaises(GameError):
            command(game,'tactic',battle_id=game.state.battle['id'],actor=ZHU_GE,target=roles['center'],tactic=10)
        self.assertEqual(game.export_save(),saved)
        self.assertEqual(game.revision,revision)

    def test_successful_recast_replaces_each_count_instead_of_stacking(self):
        game,roles,own,_=prepared();cast(game,roles)
        before=deepcopy(conditions.view(game.state.battle));game.state.rng=SeedRng(seed_for())
        expected_rng=deepcopy(game.state.rng);counts=expected_counts(expected_rng,own,roles)
        command(game,'tactic',battle_id=game.state.battle['id'],actor=ZHU_GE,target=roles['center'],tactic=10)
        self.assertEqual(game.state.battle['extended']['tactical']['points'][own],2)
        self.assertEqual(conditions.view(game.state.battle),before)
        self.assertEqual([conditions.remaining(game.state.battle,i)for i,_ in counts],[n for _,n in counts])
        self.assertEqual(game.state.rng,expected_rng)

    def test_half_day_preserves_count_and_full_days_expire_all_chain_counters_once(self):
        game,roles,_,_=prepared();cast(game,roles);first=deepcopy(conditions.view(game.state.battle))
        with patch.object(Campaign,'_run_tactical_ai_turn',return_value=None):
            command(game,'battle_wait',battle_id=game.state.battle['id'])
        self.assertEqual(conditions.view(game.state.battle),first)
        self.assertEqual(game.state.battle['round'],1)
        with patch('remake.tactical_ai.choose_action',return_value=WAIT):game._run_tactical_ai_turn(game.state)
        for elapsed in range(1,6):
            battle=game.state.battle
            self.assertEqual(battle['round'],1+elapsed)
            for key,row in first['units'].items():
                self.assertEqual(conditions.remaining(battle,key),max(0,row['remaining']-elapsed))
                if row['remaining']>elapsed:self.assertEqual(conditions.kind(battle,key),'chain')
            saved=game.export_save();self.assertEqual(conditions.advance_daily(game.state,battle),[])
            self.assertEqual(game.export_save(),saved)
            if elapsed<5:wait_day(game)
        self.assertEqual(conditions.view(game.state.battle)['units'],{})
        game.validate(game.state)

    def test_defending_cast_ticks_at_that_same_days_defender_end(self):
        game,roles,_,_=prepared('defenders');cast(game,roles)
        first=deepcopy(conditions.view(game.state.battle))
        with patch.object(Campaign,'_run_tactical_ai_turn',return_value=None):
            command(game,'battle_wait',battle_id=game.state.battle['id'])
        battle=game.state.battle;self.assertEqual((battle['round'],battle['extended']['tactical']['side']),(2,'attackers'))
        for key,row in first['units'].items():self.assertEqual(conditions.remaining(battle,key),row['remaining']-1)
        game.validate(game.state)

    def test_food_exhaustion_precedes_chain_day_scan(self):
        game,roles,own,_=prepared();cast(game,roles);battle=game.state.battle
        battle_supply.destroy(game.state,battle,own,battle['extended']['supply']['sides'][own]['remaining'])
        before=deepcopy(conditions.view(battle));rng=deepcopy(game.state.rng)
        wait_day(game)
        self.assertEqual((game.state.phase,game.state.battle['outcome']),('result','retreat'))
        self.assertEqual(conditions.view(game.state.battle),before);self.assertEqual(game.state.rng,rng)
        game.validate(game.state)

    def test_day_thirty_ends_without_advancing_a_new_chain(self):
        game,roles,_,_=prepared()
        for _ in range(29):wait_day(game)
        self.assertEqual(game.state.battle['round'],30)
        cast(game,roles);before=deepcopy(conditions.view(game.state.battle));rng=deepcopy(game.state.rng)
        wait_day(game)
        self.assertEqual((game.state.phase,game.state.battle['round']),('result',31))
        self.assertEqual(conditions.view(game.state.battle),before);self.assertEqual(game.state.rng,rng)
        self.assertEqual(game.state.battle['extended']['supply']['days'],30)
        game.validate(game.state)

    def test_chain_denies_public_move_but_not_an_actual_adjacent_attack(self):
        game,roles,own,foe=prepared();conditions.apply_chain(game.state.battle,ZHU_GE,foe,1)
        info=game.view()['catalog']['battle_tactical']['actors'][str(ZHU_GE)]
        self.assertEqual(info['reachable'],[]);self.assertTrue(info['can_act'])
        saved=game.export_save()
        with self.assertRaises(GameError):
            command(game,'battle_move',battle_id=game.state.battle['id'],actor=ZHU_GE,x=8,y=1)
        self.assertEqual(game.export_save(),saved)
        arrange_contact(game,actor=ZHU_GE,target=roles['center'])
        command(game,'attack',battle_id=game.state.battle['id'],actor=ZHU_GE,target=roles['center'])
        self.assertEqual(conditions.remaining(game.state.battle,ZHU_GE),4)
        self.assertEqual(game.state.battle['extended']['siege']['stage'],'formation')
        game.validate(game.state)

    def test_chain_actor_can_cast_and_keeps_its_own_condition(self):
        game,roles,_,foe=prepared();conditions.apply_chain(game.state.battle,ZHU_GE,foe,0)
        cast(game,roles)
        self.assertEqual(conditions.kind(game.state.battle,ZHU_GE),'chain')
        self.assertEqual(conditions.remaining(game.state.battle,ZHU_GE),3)
        self.assertEqual(conditions.kind(game.state.battle,roles['center']),'chain')
        self.assertEqual(game.state.rng.draws,4)
        game.validate(game.state)

    def test_mixed_condition_save_roundtrip_and_same_continuation_are_exact(self):
        game,roles,own,foe=prepared();cast(game,roles)
        conditions.apply(game.state.battle,roles['bridge'],own)
        conditions.apply(game.state.battle,ZHU_GE,foe)
        saved=game.export_save();game.view();game.validate(game.state)
        self.assertEqual(game.export_save(),saved)
        restored=Campaign(game.catalog);restored.load_save(json.loads(json.dumps(saved)),0)
        self.assertEqual(restored.export_save(),saved)
        wait_day(game);wait_day(restored)
        self.assertEqual(restored.export_save(),game.export_save())
        self.assertEqual(conditions.kind(restored.state.battle,roles['bridge']),'phantom')
        self.assertEqual(conditions.kind(restored.state.battle,roles['center']),'chain')

    def test_rehashed_invalid_kind_count_day_or_missing_grid_are_atomic(self):
        game,roles,_,_=prepared();cast(game,roles);saved=game.export_save();revision=game.revision
        for problem in ('kind','zero','count6','bool_count','float_count','missing_grid','future_day'):
            with self.subTest(problem=problem):
                invalid=deepcopy(saved);extended=invalid['state']['battle']['extended']
                unit=extended['conditions']['units'][str(roles['center'])]
                if problem=='kind':unit['kind']='invented'
                elif problem=='zero':unit['remaining']=0
                elif problem=='count6':unit['remaining']=6
                elif problem=='bool_count':unit['remaining']=True
                elif problem=='float_count':unit['remaining']=3.0
                elif problem=='missing_grid':extended.pop('tactical');extended.pop('deployment',None)
                else:extended['conditions']['day']=2
                with self.assertRaises(GameError):game.load_save(rehash(invalid),game.revision)
                self.assertEqual(game.export_save(),saved);self.assertEqual(game.revision,revision)

    def test_paid_confirmation_interrupted_by_real_ambush_only_clears_selected_without_draws(self):
        game,roles,own,_=prepared();battle=game.state.battle
        for role in ('center','near','bridge','leaf'):conditions.apply(battle,roles[role],own)
        # The real opposing ambusher is within five cells and has enough actual
        # intellect to rout the120-soldier caster. No damage or effect mock.
        trap=roles['leaf'];self.assertGreaterEqual(game.state.officers[trap].profile.intellect*2,120)
        battle['extended']['ambush']=dict(actor=trap)
        rng=deepcopy(game.state.rng)
        command(game,'tactic',battle_id=battle['id'],actor=ZHU_GE,target=roles['center'],tactic=10)
        battle=game.state.battle
        self.assertEqual(battle['extended']['tactical']['points'][own],11)
        self.assertEqual(game.state.phase,'result');self.assertEqual(battle['attackers'][0]['troops'],0)
        self.assertIsNone(battle['extended']['ambush']);self.assertEqual(game.state.rng,rng)
        self.assertEqual(conditions.remaining(battle,roles['center']),0)
        self.assertEqual([conditions.remaining(battle,roles[k])for k in('near','bridge','leaf')],[3,3,3])
        self.assertFalse(any(row['kind']=='chain'for row in conditions.view(battle)['units'].values()))
        game.validate(game.state)

    def test_ai_perform_path_and_public_command_share_actual_effect_payment_and_rng(self):
        for own in battle_grid.SIDES:
            with self.subTest(side=own):
                player,roles,own,foe=prepared(own);ai,ai_roles,_,_=prepared(own)
                player.state.rng=SeedRng(seed_for());ai.state.rng=deepcopy(player.state.rng)
                command(player,'tactic',battle_id=player.state.battle['id'],actor=ZHU_GE,target=roles['center'],tactic=10)
                with patch.object(ai,'_execute_tactic',wraps=ai._execute_tactic)as shared:
                    performed=ai._perform_battle_action(ai.state,dict(kind='tactic',actor=ZHU_GE,
                        target=ai_roles['center'],tactic=10),own,foe,finish=False,counter=True)
                self.assertTrue(performed);shared.assert_called_once()
                self.assertEqual(conditions.view(ai.state.battle),conditions.view(player.state.battle))
                self.assertEqual(ai.state.rng,player.state.rng)
                self.assertEqual(ai.state.battle['extended']['tactical']['points'],player.state.battle['extended']['tactical']['points'])
                self.assertEqual(ai.state.battle['extended']['support'],player.state.battle['extended']['support'])
                ai.validate(ai.state)

    def test_twelve_water_enemies_after_real_conversion_ledger_cast_and_save_exactly(self):
        from browser_soldier_fixture import _base
        game,_,actor=_base(1);state,battle=game.state,game.state.battle
        self.assertEqual((len(battle['attackers']),len(battle['defenders'])),(10,10))
        # Real catalogue Xun Yu is a special-group caster at tier3. The shared
        # successful-conversion service supplies an explicit earlier-battle
        # fixture, not an invented eleventh original deployment or a claim
        # that the separate loyalty/gate adjudication was executed here.
        state.officers[actor].experience=3500;state.officers[actor].tier=3
        self.assertGreaterEqual(tactical_ai.maximum_tactic(state.officers[actor]),10)
        convertibles=[unit for unit in battle['attackers']if unit['id']!=actor
                      and unit['id']not in state.extension['leaders'].values()][:2]
        self.assertEqual(len(convertibles),2)
        for unit in convertibles:
            battle_allegiance.convert(game,state,battle,battle['defenders'][0],unit,'defenders','attackers')
        game._reconcile_factions(state)
        self.assertEqual((len(battle['attackers']),len(battle['defenders'])),(8,12))
        self.assertEqual(len(battle['extended']['defections']),2)
        field=battle_grid._field(battle)
        cluster=[(x,y)for y in range(4,7)for x in range(24,28)]
        self.assertTrue(all(field['classes'][y][x]==3 for x,y in cluster))
        positions=battle['extended']['tactical']['positions']
        for unit,(x,y)in zip(battle['defenders'],cluster):positions[str(unit['id'])]=dict(x=x,y=y)
        positions[str(actor)]=dict(x=23,y=3)
        for index,unit in enumerate(unit for unit in battle['attackers']if unit['id']!=actor):
            positions[str(unit['id'])]=dict(x=index,y=0)
        row=battle['extended']['tactical'];row['side']='attackers'
        row['passed']=dict(attackers=False,defenders=False)
        target=battle['defenders'][0]['id']
        # Explicit breadth-first order of this rectangle; deliberately not
        # the row-major roster order used to place the twelve real units.
        order=[battle['defenders'][i]['id']for i in(0,1,4,2,5,8,3,6,9,7,10,11)]
        game.validate(state)
        preview=game.view()['catalog']['battle_tactical']['actors'][str(actor)]['tactic_previews']['10'][str(target)]
        self.assertEqual(preview['target_ids'],list(map(str,order)))
        self.assertEqual(preview['success_rng_draws'],13)
        state.rng=SeedRng(seed_for());expected_rng=deepcopy(state.rng)
        expected_rng.next();counts=[4+expected_rng.next()%2 for _ in order]
        ap=row['points']['attackers'];troops=deepcopy((battle['attackers'],battle['defenders']))
        command(game,'tactic',battle_id=battle['id'],actor=actor,target=target,tactic=10)
        state,battle=game.state,game.state.battle
        self.assertEqual(state.rng,expected_rng);self.assertEqual(state.rng.draws,13)
        self.assertEqual(battle['extended']['tactical']['points']['attackers'],ap-9)
        self.assertEqual((battle['attackers'],battle['defenders']),troops)
        self.assertEqual(len(conditions.view(battle)['units']),12)
        self.assertEqual([conditions.remaining(battle,ident)for ident in order],counts)
        self.assertEqual(state.extension['events']['items'][-1]['details'],
            dict(tactic=10,success=True,condition='chain',condition_counts=[
                dict(id=str(ident),remaining=count)for ident,count in zip(order,counts)]))
        saved=game.export_save();restored=Campaign(game.catalog)
        restored.load_save(json.loads(json.dumps(saved)),0)
        self.assertEqual(restored.export_save(),saved)
        self.assertEqual((len(restored.state.battle['attackers']),len(restored.state.battle['defenders'])),(8,12))
        self.assertEqual(restored.state.battle['extended']['defections'],battle['extended']['defections'])
        restored.validate(restored.state)


if __name__=='__main__':unittest.main()
