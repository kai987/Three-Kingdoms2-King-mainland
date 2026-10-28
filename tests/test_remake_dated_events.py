"""Once-only uprisings, non-coercion, exact monthly death and save receipts."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake.campaign import Campaign, Catalog, digest
from remake.errors import GameError
from remake import dated_events
from campaign_dated_fixtures import dated_catalog, SONG, BIAN, BEIGONG, LI, HAN


class Headless(Campaign):
    def view(self):
        return dict(revision=self.revision)


def step(game):
    prior=game.state.turn
    game.command('end_turn',{},game.revision)
    game.command('ai',dict(turn=prior),game.revision)


class DatedEventsTests(unittest.TestCase):
    def game(self,kind='founding'):
        game=Headless(dated_catalog(kind))
        game.command('new',dict(faction='shu' if kind=='retirement' else 'bian_zhang' if kind=='coup' else 'han',seed=2026),0)
        return game

    def test_february_has_five_local_people_and_only_nine_selectable_factions(self):
        catalog=Catalog(ROOT/'game/data/campaigns/184-02.json')
        self.assertEqual(len(catalog.factions),11)
        self.assertEqual(len(dated_events.visible_factions(catalog)),9)
        for faction in ('song_jian','bian_zhang'):
            with self.assertRaises(GameError):
                Headless(catalog).command('new',dict(faction=faction,seed=2026),0)
        game=Headless(catalog)
        game.command('new',dict(faction='han',seed=2026),0)
        for pid,city in ((SONG,'longxi'),(BIAN,'jincheng'),(BEIGONG,'jincheng'),(LI,'jincheng'),(HAN,'jincheng')):
            ident=catalog.ids[pid]; officer=game.state.officers[ident]
            self.assertTrue(officer.alive)
            self.assertIsNone(officer.faction_id)
            self.assertEqual((officer.troops,officer.loyalty),(0,0))
            self.assertEqual(game.state.extension['free_locations'][str(ident)],city)
            self.assertEqual(game.state.cities[city].owner,'neutral')
        game.validate(game.state)

    def test_november_forms_both_factions_once_and_roundtrips_before_and_after(self):
        game=self.game()
        for _ in range(2):
            step(game)
            self.assertEqual(game.state.extension['dated_events']['foundings'],{})
        saved=game.export_save(); loaded=Headless(game.catalog)
        loaded.load_save(saved,0)
        self.assertEqual(loaded.export_save(),saved)
        step(game);step(loaded)
        self.assertEqual(game.export_save(),loaded.export_save())
        self.assertEqual((game.state.year,game.state.month,game.state.day),(184,11,1))
        self.assertEqual(len(dated_events.visible_factions(game.catalog,game.state)),3)
        self.assertEqual(game.state.cities['tianshui'].owner,'bian_zhang')
        for side,city,pids in [('song_jian','longxi',[SONG]),('bian_zhang','jincheng',[BIAN,BEIGONG,LI,HAN])]:
            self.assertEqual(game.state.cities[city].owner,side)
            self.assertEqual({game.state.officers[i].person_id for i in game.state.cities[city].roster.officer_ids},set(pids))
            self.assertEqual(game.state.extension['leaders'][side],game.catalog.ids[pids[0]])
        events=[e for e in game.state.extension['events']['items'] if e['kind']=='faction_founded']
        self.assertEqual(len(events),2)
        self.assertTrue(all(e['turn']==4 and e['day']==1 for e in events))
        saved=game.export_save();loaded.load_save(saved,loaded.revision)
        self.assertEqual(loaded.export_save(),saved)
        receipt=deepcopy(game.state.extension['dated_events'])
        step(game)
        self.assertEqual(game.state.extension['dated_events'],receipt)
        self.assertEqual(len([e for e in game.state.extension['events']['items'] if e['kind']=='faction_founded']),2)

    def test_founding_itself_draws_no_rng_or_new_resources_or_people_or_soldiers(self):
        game=self.game()
        for _ in range(2):step(game)
        before=deepcopy(game.state)
        # Monthly settlement is disabled income in this controlled source. The
        # calendar method bypasses unrelated AI choices, not the event service.
        with patch.object(game.state.rng,'next',side_effect=AssertionError('founding used RNG')):
            game._complete_turn(game.state)
        game._reconcile_factions(game.state);game.validate(game.state)
        self.assertEqual(game.state.officers.keys(),before.officers.keys())
        self.assertEqual(game.state.soldiers,before.soldiers)
        for city in game.state.cities.values():
            prior=before.cities[city.id]
            self.assertEqual((city.gold,city.grain),(prior.gold,prior.grain))
            if city.id in {'jincheng','tianshui','longxi'}:
                assigned=sum(game.state.officers[i].troops for i in city.roster.officer_ids)
                self.assertEqual(city.reserves+assigned,prior.reserves)

    def test_occupied_city_and_recruited_leader_are_skipped_without_stealing(self):
        for mode in ('city','leader'):
            with self.subTest(mode=mode):
                game=self.game();ident=game.catalog.ids[SONG]
                if mode=='city':
                    game.state.cities['longxi'].owner='han'
                else:
                    officer=game.state.officers[ident];officer.faction_id='han';officer.loyalty=80
                    game.state.extension['free_locations'].pop(str(ident))
                    game.state.cities['henan'].roster.officer_ids.append(ident)
                game._reconcile_factions(game.state);game.validate(game.state)
                for _ in range(3):step(game)
                rule='song-jian-rise-184-11'
                row=game.state.extension['dated_events']['foundings'][rule]
                self.assertEqual(row['status'],'skipped')
                self.assertEqual(row['reason'],'city_occupied' if mode=='city' else 'leader_unavailable')
                self.assertEqual((row['members'],row['reserves']),([],0))
                self.assertNotIn('song_jian',{r['id'] for r in dated_events.visible_factions(game.catalog,game.state)})
                self.assertEqual(game.state.officers[ident].faction_id,'han' if mode=='leader' else None)

    def test_recruited_li_wenhou_stays_with_his_faction_but_bian_zhang_can_still_rise(self):
        game=self.game();ident=game.catalog.ids[LI]
        game.state.officers[ident].faction_id='han';game.state.officers[ident].loyalty=80
        game.state.extension['free_locations'].pop(str(ident))
        game.state.cities['henan'].roster.officer_ids.append(ident)
        for _ in range(3):step(game)
        self.assertEqual(game.state.officers[ident].faction_id,'han')
        self.assertEqual(game.state.extension['dated_events']['foundings']['liangzhou-revolt-184-11']['members'],[BIAN,BEIGONG,HAN])

    def test_secondary_city_occupied_prevents_taking_it_through_the_historical_script(self):
        game=self.game()
        game.state.cities['tianshui'].owner='han'
        game._reconcile_factions(game.state);game.validate(game.state)
        for _ in range(3):step(game)
        self.assertEqual(game.state.cities['tianshui'].owner,'han')
        self.assertEqual(game.state.cities['jincheng'].owner,'neutral')
        self.assertEqual(game.state.extension['dated_events']['foundings']['liangzhou-revolt-184-11']['reason'],'city_occupied')

    def test_december186_coup_removes_three_leaders_and_changes_ruler_without_new_resources(self):
        game=self.game('coup');city=game.state.cities['jincheng']
        reserves=city.reserves
        for _ in range(2):
            step(game)
            self.assertEqual(game.state.extension['leaders']['bian_zhang'],game.catalog.ids[BIAN])
        step(game)
        self.assertEqual((game.state.year,game.state.month,game.state.day),(186,12,1))
        for pid in (BIAN,BEIGONG,LI):
            officer=game.state.officers[game.catalog.ids[pid]]
            self.assertFalse(officer.alive);self.assertEqual(officer.troops,0)
        self.assertEqual(game.state.cities["jincheng"].reserves,reserves+900)
        self.assertEqual(game.state.extension['leaders']['bian_zhang'],game.catalog.ids[HAN])
        visible=next(r for r in dated_events.visible_factions(game.catalog,game.state) if r['id']=='bian_zhang')
        self.assertEqual(visible['captain'],'韩遂')
        self.assertEqual(visible['name'],'韩遂')
        self.assertEqual(visible['display_name'],'韩遂')
        self.assertEqual(visible['ruler_person_id'],HAN)
        self.assertEqual([e['kind'] for e in game.state.extension['events']['items']].count('faction_coup'),1)
        self.assertEqual([e['kind'] for e in game.state.extension['events']['items']].count('officer_death'),3)
        saved=game.export_save();loaded=Headless(game.catalog);loaded.load_save(saved,0)
        self.assertEqual(loaded.export_save(),saved)
        step(game)
        self.assertEqual([e['kind'] for e in game.state.extension['events']['items']].count('faction_coup'),1)

    def test_coup_does_not_kill_an_officer_already_recruited_by_another_faction(self):
        game=self.game('coup');ident=game.catalog.ids[LI]
        game.state.cities['jincheng'].roster.officer_ids.remove(ident)
        game.state.cities['henan'].roster.officer_ids.append(ident)
        game.state.officers[ident].faction_id='han';game.state.officers[ident].loyalty=80
        for _ in range(3):step(game)
        self.assertTrue(game.state.officers[ident].alive)
        self.assertEqual(game.state.officers[ident].faction_id,'han')
        self.assertEqual(game.state.extension['leaders']['bian_zhang'],game.catalog.ids[BIAN])
        row=game.state.extension['dated_events']['coups']['han-sui-coup-186-12']
        self.assertEqual((row['status'],row['released_troops']),('conditions_changed',0))

    def test_song_retires_in_october_upper_and_uses_normal_succession_and_death_event(self):
        game=self.game('retirement');ident=game.catalog.ids[SONG]
        reserves=game.state.cities['xiangyang'].reserves
        for _ in range(2):
            step(game)
            self.assertTrue(game.state.officers[ident].alive)
        step(game)
        self.assertEqual((game.state.year,game.state.month,game.state.day),(214,10,1))
        self.assertFalse(game.state.officers[ident].alive)
        self.assertEqual(game.state.officers[ident].troops,0)
        self.assertNotIn(ident,game.state.cities['xiangyang'].roster.officer_ids)
        self.assertEqual(game.state.cities['xiangyang'].reserves,reserves+300)
        self.assertEqual(game.state.extension['dated_events']['retirements'][SONG],dict(date=[214,10],turn=4,released=300))
        self.assertIn('shu',game.state.extension['pending_succession'])
        self.assertNotEqual(game.state.extension['leaders']['shu'],ident)
        self.assertEqual(len([e for e in game.state.extension['events']['items']
                              if e['kind']=='officer_death' and SONG in e['person_ids']]),1)
        saved=game.export_save();loaded=Headless(game.catalog);loaded.load_save(saved,0)
        self.assertEqual(loaded.export_save(),saved)
        successor=game.state.extension['leaders']['shu']
        game.command('choose_successor',dict(officer=successor),game.revision)
        while game.state.year==214:step(game)
        self.assertFalse(game.state.officers[ident].alive)
        self.assertEqual(game.state.extension['dated_events']['retirements'][SONG]['released'],300)
        self.assertEqual(len([e for e in game.state.extension['events']['items']
                              if e['kind']=='officer_death' and SONG in e['person_ids']]),1)

    def test_receipts_cannot_be_deleted_forged_or_applied_early_on_save_load(self):
        for kind in ('founding','retirement','coup'):
            game=self.game(kind)
            for _ in range(3):step(game)
            saved=game.export_save();loaded=Headless(game.catalog);loaded.load_save(saved,0)
            pool={'founding':'foundings','retirement':'retirements','coup':'coups'}[kind]
            key=next(iter(saved['state']['extension']['dated_events'][pool]))
            for mutation in ('missing','date','turn','count'):
                bad=deepcopy(saved);rows=bad['state']['extension']['dated_events'][pool]
                if mutation=='missing':rows.pop(key)
                elif mutation=='date':rows[key]['date'][1]-=1
                elif mutation=='turn':rows[key]['turn']=1
                else:rows[key][{'foundings':'reserves','retirements':'released','coups':'released_troops'}[pool]]=-1
                bad['checksum']=digest({k:v for k,v in bad.items() if k!='checksum'})
                with self.assertRaises(GameError):loaded.load_save(bad,loaded.revision)
                self.assertEqual(loaded.export_save(),saved)


if __name__=='__main__':unittest.main()
