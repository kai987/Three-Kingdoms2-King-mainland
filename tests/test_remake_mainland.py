"""Expanded gameplay acceptance. Fixture changes are explicit, never source facts."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog,GameError,digest
from remake.campaign_expansion import TACTICS
from remake.officers import OfficerProfile, PersonDefinition, initialize_officer, year_state, YearState
from remake.session import CampaignSession


class MainlandTests(unittest.TestCase):
    def setUp(self):
        self.game=Campaign(Catalog(ROOT/'game/data/mainland.json'))
        self.game.command('new',{'faction':'shu','seed':2026},0)

    def cmd(self,kind,payload=None):return self.game.command(kind,payload or {},self.game.revision)
    def ident(self,name):return next(i for i,r in self.game.catalog.by_id.items() if r['name']==name)

    def start(self,seed=None,terrain=None):
        if seed is not None:self.game.state.rng.state=seed  # Controlled deterministic gate fixture.
        actor=self.ident('赵云')
        self.cmd('allocate',{'city':'xiangyang','officer':actor,'troops':999})
        self.cmd('depart',{'source':'xiangyang','target':'nanyang','officers':[actor]})
        if terrain:self.game.catalog.map_cities['nanyang']['terrain']=terrain
        b=self.game.state.battle
        return {'battle_id':b['id'],'actor':actor,'target':b['defenders'][0]['id']}

    def finish(self):
        for _ in range(200):
            if self.game.state.phase=='result':
                b=self.game.state.battle;self.cmd('settle',{'battle_id':b['id']});return
            b=self.game.state.battle;own,foe=self.game._player_sides(self.game.state)
            a=next(u for u in b[own] if u['troops']>0 and u['id'] not in b['used'])
            t=next(u for u in b[foe] if u['troops']>0)
            self.cmd('attack',{'battle_id':b['id'],'actor':a['id'],'target':t['id']})
        self.fail('battle failed to terminate')

    def fixture_full_city(self,key):
        city=self.game.state.cities[key]
        for row in self.game.catalog.by_id.values():
            ident=row['runtime_id']
            if ident in self.game.state.officers:continue
            person=PersonDefinition(row['person_id'],'受控容量夹具',150,180,280)
            profile=OfficerProfile(80,60,60,60,0)
            self.game.catalog.definitions[person.person_id]=person;self.game.catalog.profiles[ident]=profile
            self.game.state.officers[ident]=initialize_officer(person,ident,profile,year=217,faction_id=city.owner,loyalty=70,rules=self.game.catalog.rules)
            city.roster.officer_ids.append(ident)
            if len(city.roster.officer_ids)==20:break
        self.game.validate(self.game.state)

    def test_96_live_cities_1000_library_and_no_guessed_profiles(self):
        s=self.game.state;v=self.game.view()
        self.assertEqual(len(s.cities),96);self.assertEqual(len(v['catalog']['library']),1000)
        self.assertEqual(v['catalog']['coverage']['configured_profiles'],52)
        self.assertEqual(v['catalog']['coverage']['pending_profiles'],948)
        self.assertEqual(len(s.officers),46)
        self.assertEqual(sum(len(c.roster.officer_ids) for c in s.cities.values()),41)
        self.assertTrue(all(not o.profile.missing for o in s.officers.values()))
        self.assertNotIn(self.ident('姜维'),s.officers)
        self.assertFalse(self.game.catalog.profiles[self.ident('曹操')].virtue==self.game.catalog.profiles[self.ident('曹操')].source_stats['charisma'])
        self.assertEqual(hashlib.sha256((ROOT/'game/assets/map.png').read_bytes()).hexdigest(),'30946ef6877db09f7fb44c7d0cfe729614983613619095428ff3a270c0881edd')

    def test_all96_cities_connected_including_existing_sea_lanes(self):
        seen=set();queue=['xiangyang']
        while queue:
            city=queue.pop()
            if city not in seen:
                seen.add(city);queue.extend(set(self.game._neighbors(city))-seen)
        self.assertEqual(seen,set(self.game.state.cities))
        self.assertIn('yizhou',seen);self.assertIn('zhuya',seen)
        self.assertEqual(len(self.game.catalog.data['sea_links']),7)

    def test_actual_sea_sortie_can_capture_an_island_and_settle(self):
        self.game.command('new',{'faction':'wu','seed':2026},self.game.revision)
        target='yizhou'
        source=next(edge[0] if edge[1]==target else edge[1] for edge in self.game.catalog.data['sea_links'] if target in edge)
        city=self.game.state.cities[source]
        self.assertEqual(city.owner,'wu')
        ids=city.roster.officer_ids[:1]
        self.assertTrue(ids)
        self.cmd('depart',{'source':source,'target':target,'officers':ids})
        self.assertEqual(self.game.state.phase,'result')
        bid=self.game.state.battle['id'];self.cmd('settle',{'battle_id':bid})
        self.assertEqual(self.game.state.cities[target].owner,'wu')
        self.assertEqual(self.game.state.cities[target].roster.officer_ids,ids)
        self.game.validate(self.game.state)

    def test_recruit_success_and_no_duplicate_under_stale_revision(self):
        ident=self.ident('崔州平');actor=self.ident('刘备');city=self.game.state.cities['xiangyang']
        before=city.gold
        self.cmd('recruit_officer',{'city':city.id,'actor':actor,'officer':ident})
        self.assertIn(ident,self.game.state.cities[city.id].roster.officer_ids)
        self.assertEqual(self.game.state.cities[city.id].gold,before-60)
        self.assertEqual(self.game.state.officers[ident].troops,0)
        self.assertNotIn(str(ident),self.game.state.extension['free_locations'])
        snap=self.game.to_dict();rev=self.game.revision
        with self.assertRaises(ValueError):self.game.command('recruit_officer',{'city':city.id,'actor':actor,'officer':ident},rev-1)
        self.assertEqual(snap,self.game.to_dict())

    def test_recruit_refusal_spends_exact_fee_once(self):
        ident=self.ident('崔州平');actor=self.ident('伊籍')
        seed=next(i for i in range(1,1000) if self._roll(i)>=90)
        self.game.state.rng.state=seed
        self.cmd('recruit_officer',{'city':'xiangyang','actor':actor,'officer':ident})
        self.assertIsNone(self.game.state.officers[ident].faction_id)
        self.assertEqual(self.game.state.cities['xiangyang'].gold,1140)
        self.assertEqual(self.game.state.rng.draws,1)
        before=self.game.to_dict()
        with self.assertRaises(ValueError):self.cmd('recruit_officer',{'city':'xiangyang','actor':actor,'officer':ident})
        self.assertEqual(before,self.game.to_dict())

    @staticmethod
    def _roll(seed):
        from remake.campaign import SeedRng
        return SeedRng(seed).next()%100

    def test_full_city_and_not_appeared_recruit_reject_without_rng_or_gold(self):
        self.fixture_full_city('xiangyang')
        for ident in [self.ident('崔州平'),self.ident('姜维')]:
            before=self.game.to_dict()
            with self.assertRaises(ValueError):self.cmd('recruit_officer',{'city':'xiangyang','actor':self.ident('刘备'),'officer':ident})
            self.assertEqual(before,self.game.to_dict())

    def test_enemy_defection_is_atomic_and_preserves_all_personal_resources(self):
        city=self.game.state.cities['xiangyang']
        ident=self.game._persuadable(self.game.state,city)[0]
        before=deepcopy(self.game.state.officers[ident]);ledger=deepcopy(self.game.state.soldiers)
        self.game.state.rng.state=next(i for i in range(1,1000) if self._roll(i)<5)
        self.cmd('persuade_officer',{'city':city.id,'actor':self.ident('刘备'),'officer':ident})
        after=self.game.state.officers[ident]
        self.assertEqual(after.faction_id,'shu');self.assertIn(ident,self.game.state.cities['xiangyang'].roster.officer_ids)
        self.assertEqual((before.health,before.troops,before.weapon_id,before.armor_id,before.experience),(after.health,after.troops,after.weapon_id,after.armor_id,after.experience))
        self.assertEqual(self.game.state.soldiers,ledger)
        self.assertEqual(sum(ident in c.roster.officer_ids for c in self.game.state.cities.values()),1)
        self.assertEqual(self.game.state.cities[city.id].gold,1100)

    def test_ruler_and_full_city_defection_refused_without_cost(self):
        for ident in [self.ident('曹操'),self.ident('孙权')]:
            before=self.game.to_dict()
            with self.assertRaises(ValueError):self.cmd('persuade_officer',{'city':'xiangyang','actor':self.ident('刘备'),'officer':ident})
            self.assertEqual(before,self.game.to_dict())
        city=self.game.state.cities['xiangyang'];ident=self.game._persuadable(self.game.state,city)[0]
        self.fixture_full_city(city.id);before=self.game.to_dict()
        with self.assertRaises(ValueError):self.cmd('persuade_officer',{'city':city.id,'actor':self.ident('刘备'),'officer':ident})
        self.assertEqual(before,self.game.to_dict())

    def test_transfer_friendly_path_preserves_army_and_prevents_chain_actions(self):
        ident=self.ident('赵云');before=deepcopy(self.game.state.soldiers)
        self.cmd('transfer',{'source':'xiangyang','target':'nanjun','officers':[ident]})
        self.assertIn(ident,self.game.state.cities['nanjun'].roster.officer_ids)
        self.assertNotIn(ident,self.game.state.cities['xiangyang'].roster.officer_ids)
        self.assertEqual(self.game.state.officers[ident].troops,300)
        self.assertEqual(self.game.state.cities['xiangyang'].grain,3795)
        self.assertEqual(self.game.state.soldiers,before)
        snapshot=self.game.to_dict()
        with self.assertRaises(ValueError):self.cmd('transfer',{'source':'nanjun','target':'bajun','officers':[ident]})
        self.assertEqual(snapshot,self.game.to_dict())

    def test_enemy_disconnected_and_full_destination_transfer_are_atomic(self):
        self.fixture_full_city('nanjun')
        for destination in ['nanjun','nanyang','yizhou']:
            before=self.game.to_dict()
            with self.assertRaises(ValueError):self.cmd('transfer',{'source':'xiangyang','target':destination,'officers':[self.ident('赵云')]})
            self.assertEqual(before,self.game.to_dict())

    def test_tactic_terrain_and_energy_rejection_do_not_spend_turn(self):
        args=self.start(terrain='plain')
        for tid in [4,9,10,12]:
            before=self.game.to_dict();rev=self.game.revision
            with self.assertRaises(ValueError):self.cmd('tactic',{**args,'tactic':tid})
            self.assertEqual(before,self.game.to_dict());self.assertEqual(rev,self.game.revision)
        self.game.state.battle['extended']['support'][str(args['actor'])]['energy']=0
        before=self.game.to_dict()
        with self.assertRaises(ValueError):self.cmd('tactic',{**args,'tactic':0})
        self.assertEqual(before,self.game.to_dict())

    def test_all16_tactics_complete_save_and_single_settlement(self):
        for tid,(_,_,effect,_) in enumerate(TACTICS):
            with self.subTest(tactic=tid):
                self.setUp();terrain='water' if tid in {4,10,12} else 'mountain' if tid==9 else 'plain'
                args=self.start(seed=1,terrain=terrain)
                # Use a deterministic gate pass, not a claimed natural roll.
                self.game.state.rng.state=next(i for i in range(1,1000) if self._roll(i)<5)
                self.cmd('tactic',{**args,'tactic':tid})
                self.game.validate(self.game.state)
                saved=self.game.export_save();twin=Campaign(self.game.catalog);twin.load_save(saved,0)
                self.assertEqual(self.game.to_dict(),twin.to_dict())
                if self.game.state.phase=='battle':self.cmd('retreat',{'battle_id':args['battle_id']})
                rev=self.game.revision;self.cmd('settle',{'battle_id':args['battle_id']});after=self.game.to_dict()
                self.game.command('settle',{'battle_id':args['battle_id']},rev)
                self.assertEqual(after,self.game.to_dict())
                self.game.validate(self.game.state)
                if effect=='surrender':
                    self.assertIsNone(self.game.state.officers[args['target']].faction_id)
                    self.assertGreater(self.game.state.cities['nanyang'].reserves,1200)

    def test_ambush_waits_for_later_counter_then_triggers_once(self):
        args=self.start();self.cmd('tactic',{**args,'tactic':11})
        b=self.game.state.battle
        self.assertIsNotNone(b['extended']['ambush'])
        self.assertFalse(any('触发' in l for l in b['log']))
        self.cmd('attack',args)
        self.assertIsNone(self.game.state.battle['extended']['ambush'])
        self.assertEqual(sum('十面埋伏触发' in l for l in self.game.state.battle['log']),1)

    def test_duel_accept_reject_and_exit_preserve_single_world(self):
        args=self.start(seed=1)
        self.cmd('duel_start',args)
        b=self.game.state.battle
        if b['extended']['duel'] is None:
            self.assertTrue(any('拒绝' in l for l in b['log']))
            self.game.state.rng.state=next(i for i in range(1,1000) if self._roll(i)<5)
            self.cmd('duel_start',args)
        self.assertIsNotNone(self.game.state.battle['extended']['duel'])
        before=self.game.to_dict()
        with self.assertRaises(ValueError):self.cmd('attack',args)
        self.assertEqual(before,self.game.to_dict())
        self.cmd('duel_action',{'battle_id':args['battle_id'],'move':'guard'})
        saved=self.game.export_save();twin=Campaign(self.game.catalog);twin.load_save(saved,0)
        self.assertEqual(self.game.to_dict(),twin.to_dict())
        payload={'battle_id':args['battle_id'],'move':'feint'}
        self.cmd('duel_action',payload);twin.command('duel_action',payload,twin.revision)
        self.assertEqual(self.game.to_dict(),twin.to_dict())
        self.cmd('duel_action',{'battle_id':args['battle_id'],'move':'withdraw'})
        self.assertIsNone(self.game.state.battle['extended']['duel'])
        self.assertEqual(self.game.state.battle['extended']['duel_history'][-1]['result'],'退出单挑')

    def test_duel_resolves_within20_rounds_without_permanent_death(self):
        args=self.start(seed=1);self.game.state.rng.state=next(i for i in range(1,1000) if self._roll(i)<5)
        self.cmd('duel_start',args)
        for n in range(20):
            if not self.game.state.battle['extended']['duel']:break
            self.cmd('duel_action',{'battle_id':args['battle_id'],'move':'strike'})
        self.assertIsNone(self.game.state.battle['extended']['duel'])
        if self.game.state.phase=='battle':self.cmd('retreat',{'battle_id':args['battle_id']})
        self.cmd('settle',{'battle_id':args['battle_id']})
        self.assertTrue(self.game.state.officers[args['actor']].alive)
        self.assertTrue(self.game.state.officers[args['target']].alive)

    def test_simultaneous_duel_rout_keeps_ownership_and_conserves_soldiers(self):
        city=self.game.state.cities['nanyang']
        for ident in city.roster.officer_ids[1:]:
            city.reserves+=self.game.state.officers[ident].troops;self.game.state.officers[ident].troops=0
        self.game.validate(self.game.state)
        args=self.start(seed=1)
        self.game.state.rng.state=next(i for i in range(1,1000) if self._roll(i)<5)
        self.cmd('duel_start',args)
        b=self.game.state.battle
        # Controlled low-HP fixture forces the simultaneous-rout boundary.
        for key in b['extended']['support']: b['extended']['support'][key]['health']=2
        self.cmd('duel_action',{'battle_id':b['id'],'move':'strike'})
        self.assertIsNone(self.game.state.battle['extended']['duel'])
        self.assertEqual(self.game.state.battle['extended']['duel_history'][-1]['result'],'双方负伤退场')
        if self.game.state.phase=='battle':self.cmd('retreat',{'battle_id':b['id']})
        self.cmd('settle',{'battle_id':b['id']})
        self.assertEqual(self.game.state.cities['nanyang'].owner,'wei')
        self.game.validate(self.game.state)

    def test_incoming_ai_battle_defender_controls_and_resume_month_once(self):
        self.cmd('end_turn');self.cmd('ai',{'turn':1})
        # Natural first-turn AI may choose another weak city. Continue until an
        # actual player-facing attack, without injecting a battle state.
        for _ in range(30):
            if self.game.state.phase in {'battle','result'}:break
            if self.game.state.phase=='city':self.cmd('end_turn')
            self.cmd('ai',{'turn':self.game.state.turn})
        self.assertIn(self.game.state.phase,{'battle','result'})
        b=self.game.state.battle
        self.assertNotEqual(b['attacker'],self.game.state.player)
        self.assertEqual(b['defender'],self.game.state.player)
        turn=self.game.state.turn;self.assertTrue(self.game.state.extension['ai_queue'])
        save=self.game.export_save();twin=Campaign(self.game.catalog);twin.load_save(save,0)
        self.assertEqual(self.game.to_dict(),twin.to_dict())
        if self.game.state.phase=='battle':self.cmd('retreat',{'battle_id':b['id']})
        self.cmd('settle',{'battle_id':b['id']})
        self.assertEqual(self.game.state.phase,'ai');self.assertEqual(self.game.state.turn,turn)
        self.assertNotIn(turn,self.game.state.completed_ai_turns)
        for _ in range(10):
            if self.game.state.turn>turn:break
            if self.game.state.phase=='ai':self.cmd('ai',{'turn':turn})
            elif self.game.state.phase=='battle':self.cmd('retreat',{'battle_id':self.game.state.battle['id']})
            elif self.game.state.phase=='result':self.cmd('settle',{'battle_id':self.game.state.battle['id']})
        self.assertEqual(self.game.state.turn,turn+1)
        after=self.game.to_dict();self.game.command('ai',{'turn':turn},0);self.assertEqual(after,self.game.to_dict())
        self.assertTrue(any(r['action']=='attack' for r in self.game.state.extension['ai_reports']))

    def test_semantic_expansion_save_tampering_is_rejected_atomically(self):
        args=self.start();original=self.game.to_dict()
        def envelope(edit):
            value=self.game.export_save();edit(value['state']);value['checksum']=digest({k:v for k,v in value.items() if k!='checksum'});return value
        edits=[lambda s:s['battle']['extended']['support'][str(args['actor'])].update(energy=99),
               lambda s:s['extension'].update(outcome='victory',),
               lambda s:s['extension']['leaders'].update(shu=self.ident('曹操')),
               lambda s:s['battle'].update(outcome='victory')]
        for edit in edits:
            with self.assertRaises(GameError):self.game.load_save(envelope(edit),self.game.revision)
            self.assertEqual(original,self.game.to_dict())

    def test_early_dead_crosses_year_without_revival_or_repeat_release(self):
        ident=self.ident('夏侯惇');o=self.game.state.officers[ident]
        city=next(c for c in self.game.state.cities.values() if ident in c.roster.officer_ids)
        city.reserves+=o.troops;city.roster.officer_ids.remove(ident);o.troops=0;o.health=0;o.alive=False;o.faction_id=None;o.loyalty=0
        self.game.validate(self.game.state)
        dead=deepcopy(o)
        # Controlled annual-boundary fixture uses the common month reducer;
        # this is not a UI claim of permanent combat death.
        for _ in range(38):
            self.game._complete_month(self.game.state);self.game._spawn_eligible(self.game.state);self.game._reconcile_factions(self.game.state);self.game.validate(self.game.state)
        self.assertEqual(self.game.state.officers[ident],dead)
        self.assertEqual(sum(f'remove_after_death_year:{o.person_id}:221'==e for e in self.game.state.year_events),1)

    def test_later_appearance_and_ruler_succession_follow_calendar(self):
        jiang=self.ident('姜维');leader=self.ident('曹操')
        for _ in range(98):
            self.game._complete_month(self.game.state);self.game._spawn_eligible(self.game.state);self.game._reconcile_factions(self.game.state);self.game.validate(self.game.state)
        self.assertEqual(self.game.state.year,226)
        self.assertIn(jiang,self.game.state.officers)
        self.assertIsNone(self.game.state.officers[jiang].faction_id)
        self.assertEqual(self.game.state.officers[jiang].troops,0)
        self.assertFalse(self.game.state.officers[leader].alive)
        self.assertNotEqual(self.game.state.extension['leaders']['wei'],leader)


class ScenarioSessionTests(unittest.TestCase):
    def setUp(self):self.session=CampaignSession([ROOT/'game/data/demo.json',ROOT/'game/data/mainland.json'])
    def test_old_slice_save_is_still_accepted_and_can_switch_back(self):
        s=self.session;s.command('new',{'faction':'shu','seed':7,'scenario':'jingxiang217-v1'},0)
        old=s.export_save();del old['state']['extension'];old['checksum']=digest({k:v for k,v in old.items() if k!='checksum'})
        s.command('new',{'faction':'wu','seed':9,'scenario':'mainland217-v1'},s.revision)
        self.assertEqual(len(s.game.state.cities),96)
        s.load_save(old,s.revision);self.assertEqual(len(s.game.state.cities),4)
        self.assertEqual(s.game.state.seed,7)
    def test_invalid_scenario_and_save_never_replace_current_game(self):
        s=self.session;s.command('new',{'faction':'shu','seed':1},0);before=s.view();old=s.game
        for action in [lambda:s.command('new',{'faction':'unknown','seed':1,'scenario':'jingxiang217-v1'},s.revision),lambda:s.load_save({'scenario':'other'},s.revision),lambda:s.load_save({'scenario':'jingxiang217-v1'},s.revision)]:
            with self.assertRaises(GameError):action()
            self.assertIs(s.game,old);self.assertEqual(s.view(),before)


if __name__=='__main__':unittest.main()
