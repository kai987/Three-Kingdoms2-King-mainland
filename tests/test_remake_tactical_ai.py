"""Real battle effects are shared; tactical evaluation never samples the RNG."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign, SeedRng
from remake.campaign_expansion import TACTICS
from remake.difficulty import get_settings
from remake.tactical_ai import candidates, choose_action, legal_tactics, expected_attack
from campaign_fixtures import controlled_catalog


def battle(terrain='plain', *, three_enemies=True, player='shu', seed=2026):
    """Controlled identities/rosters; not a claim about historical deployment."""
    game=Campaign(controlled_catalog());game.state=game._new(player,seed)
    state=game.state;source=state.cities['xiangyang'];target=state.cities['nanyang']
    actor=146
    if three_enemies:
        # Move two non-rulers within this fixture to exercise area/chain limits.
        ids=[i for i in source.roster.officer_ids if i not in (actor,state.extension['leaders']['shu'])]
        for ident in ids:
            source.roster.officer_ids.remove(ident);target.roster.officer_ids.append(ident)
            state.officers[ident].faction_id=target.owner
    game.catalog.map_cities[target.id]['terrain']=terrain
    game._start_expanded_battle(state,source,target,[actor])
    return game


def actors(game,own='attackers'):
    b=game.state.battle;foe='defenders' if own=='attackers' else 'attackers'
    return b,b[own][0],b[foe][0],own,foe


def successful_rng(state):
    # A controlled seed with a first roll below the lowest actual 5% success
    # bound; execution still uses the real generator and all real damage draws.
    seed=next(i for i in range(1,10000) if SeedRng(i).next()%100<5)
    state.rng=SeedRng(seed)


class TacticalAiTests(unittest.TestCase):
    def test_every_tactic_is_a_legal_scored_candidate_on_its_terrain(self):
        found=set()
        for terrain in ('plain','mountain','water'):
            game=battle(terrain);state=game.state;b,a,t,own,foe=actors(game)
            before=game.to_dict()
            rows=candidates(state,b,own,foe,terrain,TACTICS,depth=2)
            tids={r['tactic'] for r in rows if r['kind']=='tactic'};found|=tids
            self.assertEqual(tids,set(legal_tactics(state,b,a,t,own,foe,terrain,TACTICS)))
            self.assertEqual(game.to_dict(),before)
            for row in rows:
                self.assertIn(row['actor'],{u['id'] for u in b[own]})
                self.assertIn(row['target'],{u['id'] for u in b[foe] if u['troops']>0})
        self.assertEqual(found,set(range(16)))

    def test_all16_candidates_execute_the_actual_player_effects(self):
        for tid,(_,cost,effect,_) in enumerate(TACTICS):
            terrain='water' if effect in {'water','chain','flood'} else 'mountain' if effect=='rock' else 'plain'
            for own in ('attackers','defenders'):
                with self.subTest(tactic=tid,side=own):
                    game=battle(terrain);state=game.state;b,a,t,own,foe=actors(game,own)
                    # Every actor has at least 100 troops in the controlled
                    # roster. Low health isolates trap/rock's routed-HP effect.
                    if effect in {'trap','rock'}:b['extended']['support'][str(t['id'])]['health']=2
                    successful_rng(state)
                    before=deepcopy(b);grain={key:c.grain for key,c in state.cities.items()}
                    row=next(r for r in candidates(state,b,own,foe,terrain,TACTICS,depth=2,responding=True)
                             if r['kind']=='tactic' and r['tactic']==tid and r['actor']==a['id'] and r['target']==t['id'])
                    self.assertTrue(game._perform_battle_action(state,row,own,foe,finish=False))
                    self.assertEqual(b['extended']['support'][str(a['id'])]['energy'],18-cost)
                    self.assertEqual(b['used'],[],'Counter/shared execution does not spend another player action')
                    if effect=='ambush':self.assertEqual(b['extended']['ambush'],{'actor':a['id']})
                    elif effect=='guard':self.assertEqual(b['extended']['support'][str(a['id'])]['guard'],2)
                    elif effect in {'confuse','chain'}:
                        count=sum(s['stunned'] for key,s in b['extended']['support'].items() if int(key) in {u['id'] for u in b[foe]})
                        self.assertEqual(count,min(len(b[foe]),1 if effect=='confuse' else 3))
                    elif effect=='supply':
                        city=b['target'] if foe=='defenders' else b['source']
                        self.assertLess(state.cities[city].grain,grain[city])
                        self.assertEqual(state.cities[b['source'] if city==b['target'] else b['target']].grain,grain[b['source'] if city==b['target'] else b['target']])
                    elif effect=='surrender':self.assertEqual(b['extended']['surrenders'][str(t['id'])],before[foe][0]['troops']);self.assertEqual(t['troops'],0)
                    else:self.assertLess(sum(u['troops'] for u in b[foe]),sum(u['troops'] for u in before[foe]))
                    if effect in {'trap','rock'}:self.assertEqual(t['troops'],0)
                    self.assertEqual(state.rng.draws,0 if effect in {'ambush','guard'} else 1+(0 if effect in {'confuse','chain','supply','surrender'} else min(len(b[foe]),3 if effect=='area' else 2 if effect=='crossbow' else 20 if effect in {'flood','inferno'} else 1)))

    def test_candidate_evaluation_never_calls_rng_or_changes_inputs(self):
        game=battle('water');state=game.state;b=state.battle;before=game.to_dict()
        with patch.object(SeedRng,'next',side_effect=AssertionError('RNG lookahead')):
            for own,foe in (('attackers','defenders'),('defenders','attackers')):
                for level in ('easy','normal','hard'):
                    state.extension['difficulty']=level
                    first=choose_action(state,b,own,foe,'water',TACTICS,settings=get_settings(state),responding=True)
                    self.assertEqual(first,choose_action(state,b,own,foe,'water',TACTICS,settings=get_settings(state),responding=True))
        state.extension['difficulty']=before['extension']['difficulty']
        self.assertEqual(game.to_dict(),before)

    def test_terrain_energy_stun_used_and_zero_troops_are_hard_bounds(self):
        game=battle('plain');state=game.state;b,a,t,own,foe=actors(game)
        self.assertFalse({4,9,10,12}&set(legal_tactics(state,b,a,t,own,foe,'plain',TACTICS)))
        support=b['extended']['support'][str(a['id'])];support['energy']=0
        self.assertEqual(legal_tactics(state,b,a,t,own,foe,'plain',TACTICS),[])
        support['energy']=18;support['stunned']=1
        choice=choose_action(state,b,own,foe,'plain',TACTICS)
        self.assertEqual(choice['kind'],'attack')
        draws=state.rng.draws;game._perform_battle_action(state,choice,own,foe,finish=False)
        self.assertEqual(state.rng.draws,draws);self.assertEqual(support['stunned'],0)
        b['used']=[a['id']];self.assertIsNone(choose_action(state,b,own,foe,'plain',TACTICS))
        self.assertIsNotNone(choose_action(state,b,own,foe,'plain',TACTICS,responding=True))
        b['extended']['duel']={'actor':a['id'],'target':t['id']}
        self.assertIsNone(choose_action(state,b,own,foe,'plain',TACTICS,responding=True))
        b['extended']['duel']=None
        a['troops']=0;self.assertEqual(candidates(state,b,own,foe,'plain',TACTICS,responding=True),[])

    def test_ambush_minimum_single_slot_and_side_ownership(self):
        for owner in ('attackers','defenders'):
            game=battle();state=game.state;b,a,t,own,foe=actors(game,owner)
            a['troops']=99;self.assertNotIn(11,legal_tactics(state,b,a,t,own,foe,'plain',TACTICS));a['troops']=100
            game._execute_tactic(state,a,t,own,foe,11,finish=False)
            self.assertNotIn(11,legal_tactics(state,b,a,t,own,foe,'plain',TACTICS))
            before=a['troops'];game._trigger_ambush(state,a,own)
            self.assertEqual(a['troops'],before);self.assertIsNotNone(b['extended']['ambush'])
            before=t['troops'];game._trigger_ambush(state,t,foe)
            expected=min(before,max(1,state.officers[a['id']].profile.intellect*2))
            self.assertEqual(t['troops'],before-expected);self.assertIsNone(b['extended']['ambush'])
            game._trigger_ambush(state,t,foe);self.assertEqual(t['troops'],before-expected,'One ambush never fires twice')

    def test_guard_supply_and_surrender_scoring_uses_current_state(self):
        game=battle();state=game.state;b,a,t,own,foe=actors(game)
        def score(tid):return next(r['score'] for r in candidates(state,b,own,foe,'plain',TACTICS,depth=2) if r['actor']==a['id'] and r['target']==t['id'] and r['tactic']==tid)
        normal=score(15);b['extended']['support'][str(a['id'])]['guard']=2
        self.assertLess(score(15),normal)
        state.cities[b['target']].grain=0;self.assertLess(score(5),0)
        t['troops']=0;self.assertNotIn(t['id'],{r['target'] for r in candidates(state,b,own,foe,'plain',TACTICS)})
        self.assertGreater(expected_attack(b,a,b[foe][1]),0)

    def test_counter_is_one_shared_action_and_seeded_execution_repeats(self):
        left=battle('mountain');right=battle('mountain')
        for game in (left,right):
            state=game.state;b,a,_,_,_=actors(game);draws=state.rng.draws
            choice=choose_action(state,b,'defenders','attackers','mountain',TACTICS,settings=get_settings(state),responding=True)
            enemy=next(u for u in b['defenders']if u['id']==choice['actor'])
            energy=b['extended']['support'][str(enemy['id'])]['energy']
            game._counter(state,'defenders',a)
            self.assertEqual(b['used'],[])
            if choice['kind']=='tactic':self.assertEqual(b['extended']['support'][str(enemy['id'])]['energy'],energy-TACTICS[choice['tactic']][1])
            self.assertGreater(state.rng.draws,draws)
        self.assertEqual(left.to_dict(),right.to_dict())

    def test_failed_tactic_costs_one_roll_and_emits_stable_person_ids(self):
        game=battle();state=game.state;b,a,t,own,foe=actors(game)
        state.rng=SeedRng(next(i for i in range(1,10000) if SeedRng(i).next()%100>=95))
        troops=[u['troops']for u in b[foe]]
        game._execute_tactic(state,a,t,own,foe,0,finish=False)
        self.assertEqual(state.rng.draws,1);self.assertEqual([u['troops']for u in b[foe]],troops)
        self.assertEqual(b['extended']['support'][str(a['id'])]['energy'],12)
        event=state.extension['events']['items'][-1]
        self.assertEqual(event['details'],{'tactic':0,'success':False})
        self.assertEqual(event['person_ids'],[state.officers[a['id']].person_id,state.officers[t['id']].person_id])
        self.assertEqual(set(event['factions']),{'shu','wei'})
        game.validate(state)

    def test_stunned_counter_spends_only_one_skip_without_drawing_rng(self):
        game=battle();state=game.state;b,a,_,_,_=actors(game)
        for enemy in b['defenders']:b['extended']['support'][str(enemy['id'])]['stunned']=1
        before=deepcopy(b);draws=state.rng.draws
        game._counter(state,'defenders',a)
        self.assertEqual(state.rng.draws,draws)
        self.assertEqual(sum(s['stunned']for s in b['extended']['support'].values()),len(b['defenders'])-1)
        self.assertEqual(b['used'],[])
        self.assertEqual([u['troops']for u in b['attackers']+b['defenders']],
                         [u['troops']for u in before['attackers']+before['defenders']])

    def test_real_player_action_roundtrip_keeps_counter_and_rng_deterministic(self):
        game=battle('mountain');game.validate(game.state)
        restored=Campaign(game.catalog);restored.load_save(game.export_save(),0)
        for current in (game,restored):
            b,a,t,_,_=actors(current)
            current.command('attack',{'battle_id':b['id'],'actor':a['id'],'target':t['id']},current.revision)
            current.validate(current.state)
        self.assertEqual(game.to_dict(),restored.to_dict())

    def test_ai_versus_ai_uses_both_sides_shared_effects_and_conserves_soldiers(self):
        # A successful opening surrender can legally end this one-unit fight
        # before the defenders act. Select a real RNG seed whose first roll
        # fails even the 80% surrender cap, so this fixture exercises both sides.
        seed=next(i for i in range(1,10000) if SeedRng(i).next()%100>=80)
        states=[]
        for _ in range(2):
            game=battle('mountain',three_enemies=False,player='wu',seed=seed);state=game.state
            with patch.object(game,'_perform_battle_action',wraps=game._perform_battle_action) as execute:
                game._resolve_ai_battle(state)
                self.assertLessEqual(execute.call_count,200)
                self.assertEqual({call.args[2] for call in execute.call_args_list},{'attackers','defenders'})
                self.assertTrue(any(call.args[1]['kind']=='tactic'for call in execute.call_args_list))
            self.assertIsNone(state.battle);self.assertEqual(len(state.settled_battles),1)
            game.validate(state)
            actual=sum(c.reserves for c in state.cities.values())+sum(o.troops for o in state.officers.values())
            self.assertEqual(actual+state.soldiers['lost'],state.soldiers['initial']+state.soldiers['recruited'])
            states.append(game.to_dict())
        self.assertEqual(states[0],states[1])

    def test_easy_policy_remains_ordinary_without_stat_or_resource_bonuses(self):
        game=battle('water');state=game.state;b=state.battle;state.extension['difficulty']='easy';before=game.to_dict()
        self.assertEqual(choose_action(state,b,'defenders','attackers','water',TACTICS,settings=get_settings(state),responding=True)['kind'],'attack')
        self.assertEqual(game.to_dict(),before)

    def test_autoresolve_nonprogress_stops_at200_without_invented_losses(self):
        game=battle(three_enemies=False,player='wu');state=game.state;initial=state.soldiers.copy()
        with patch.object(game,'_perform_battle_action',return_value=True)as execute:
            game._resolve_ai_battle(state)
            self.assertEqual(execute.call_count,200)
        self.assertIsNone(state.battle);self.assertEqual(state.soldiers,initial)
        self.assertEqual(state.settled_battles,['battle-1']);game.validate(state)


if __name__=='__main__':unittest.main()
